"""Quote-executed daily portfolio replay or independent fixed-horizon label trials."""

import csv
import hashlib
import json
import os
from datetime import datetime
from itertools import groupby
from pathlib import Path
from typing import TYPE_CHECKING, Any, TextIO

from pydantic import SecretStr

from trading_agent.backtesting.report import (
    Performance,
    code_digest,
    journal_digest,
    ledger_results,
)
from trading_agent.daily_execution.contracts import DailyStrategy
from trading_agent.daily_execution.dataset import ExecutionDataset, QuoteEvent
from trading_agent.daily_execution.labels import Labels
from trading_agent.daily_execution.runtime import ResearchRuntime
from trading_agent.daily_execution.strategy import DailyDecisions
from trading_agent.daily_execution.timeline import DailyTimeline
from trading_agent.execution.paper_broker import PaperBroker
from trading_agent.market_data.calendar import IST
from trading_agent.models import stamp
from trading_agent.persistence.database import Database
from trading_agent.risk.policy import policy_fingerprint, policy_values
from trading_agent.settings import Settings

if TYPE_CHECKING:
    from trading_agent.daily_execution.model import DailyModel


def private_stream(path: Path, *, newline: str | None = None) -> TextIO:
    return os.fdopen(
        os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "w", newline=newline
    )


def private_text(path: Path, content: str) -> None:
    with os.fdopen(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "w") as file:
        file.write(content)
        file.flush()
        os.fsync(file.fileno())


def finish_manifest(output: Path, names: list[str], **metadata: Any) -> None:
    hashes = {}
    for name in names:
        with (output / name).open("rb") as file:
            hashes[name] = hashlib.file_digest(file, "sha256").hexdigest()
    private_text(
        output / "manifest.json",
        json.dumps(
            {
                "schema_version": 1,
                "state": "finished",
                "ready_for_live": False,
                **metadata,
                "sha256": hashes,
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
    )


def run_daily(
    dataset: ExecutionDataset,
    *,
    strategy: DailyStrategy,
    policy: Settings,
    output: Path,
    labels: bool = False,
    model: "DailyModel | None" = None,
) -> dict[str, Any]:
    if policy.investment_horizon != "long_term":
        raise ValueError("daily delivery research requires a long-term policy")
    if model and labels:
        raise ValueError("independent labels cannot be selected by a model")
    if model:
        model.check_context(strategy, policy)
        if model.artifact.synthetic and not dataset.manifest.synthetic:
            raise ValueError("synthetic daily models may only score synthetic evidence")
    output = output.resolve()
    if output.exists() or any(
        output.is_relative_to(root) for root in (dataset.directory, dataset.daily.directory)
    ):
        raise ValueError("research output must be new and outside both source bundles")
    timeline = DailyTimeline(
        dataset.daily, {item.symbol for item in dataset.manifest.instruments}, strategy.screen
    )
    events = dataset.events()
    first_event = next(events)
    if model and first_event.time <= model.artifact.available_after:
        raise ValueError("daily scored replay must start after validation plus embargo")
    output.mkdir(parents=True, mode=0o700)
    isolated = policy.model_copy(
        update={
            "database": output / "paper.sqlite3",
            "operator_token": SecretStr(""),
            "stream_tokens": tuple(item.token for item in dataset.manifest.instruments),
        }
    )
    db = Database(isolated.database, isolated.starting_cash)
    manager: Labels | None = None
    now = first_event.time
    try:
        engine = PaperBroker(
            db, isolated, dataset.manifest.calendar(), recovery_time=first_event.time
        )
        engine.register(list(dataset.manifest.instruments))
        runtime = ResearchRuntime(engine, timeline, strategy, observer=labels)
        decisions = DailyDecisions(runtime)
        performance = Performance(policy.starting_cash)
        session_days = set()
        decision_rows: list[dict[str, Any]] = []
        from itertools import chain

        with (
            private_stream(output / "decisions.jsonl") as decision_file,
            private_stream(output / "equity.csv", newline="") as equity_file,
            private_stream(output / "samples.jsonl") as samples_file,
            private_stream(output / "label_audit.jsonl") as audit_file,
        ):
            writer = csv.writer(equity_file)
            writer.writerow(["time", "equity", "cash", "valuation_fresh", "known_receivable"])
            if labels:
                manager = Labels(runtime, output, samples_file, audit_file)
            for now, group in groupby(chain((first_event,), events), key=lambda event: event.time):
                if not labels:
                    decisions.exits_due(now)
                accepted = {}
                for event in group:
                    if manager:
                        manager.feed(event)
                    if runtime.feed(event) and isinstance(event, QuoteEvent):
                        accepted[event.quote.symbol] = event.quote
                    if isinstance(event, QuoteEvent):
                        session_days.add(event.time.astimezone(IST).date())
                proposals = []
                for symbol, quote in sorted(accepted.items()):
                    proposal = decisions.proposal(quote, now)
                    if proposal:
                        payload, candidate, vector = proposal
                        if candidate and vector:
                            probability = model.score(vector) if model else None
                            score = (
                                probability
                                if probability is not None
                                else float(payload["screen"]["gross_total_return_pct"])
                            )
                            proposals.append(
                                (score, symbol, payload, candidate, vector, quote, probability)
                            )
                        else:
                            decision_rows.append(payload)
                            decision_file.write(json.dumps(payload, sort_keys=True) + "\n")
                for rank, (_, _, payload, candidate, vector, quote, probability) in enumerate(
                    sorted(proposals, key=lambda item: (-item[0], item[1])), 1
                ):
                    payload.update(
                        simultaneous_rank=rank,
                        model_sha256=model.version if model else None,
                        probability=probability,
                    )
                    if model and probability is not None and probability < model.artifact.threshold:
                        payload["reasons"].append("DAILY_MODEL_BELOW_THRESHOLD")
                    elif manager:
                        manager.start(candidate, vector, quote)
                        payload["label_trial_requested"] = True
                    else:
                        order = engine.submit(candidate, now)
                        payload.update(
                            order_id=order["id"],
                            order_state=order["state"],
                            risk_reasons=order["reason"],
                        )
                    with db.transaction() as tx:
                        db.event(
                            tx, stamp(now), "daily_strategy_decision", candidate.intent_id, payload
                        )
                    decision_rows.append(payload)
                    decision_file.write(json.dumps(payload, sort_keys=True) + "\n")
                engine.poll(now)
                snapshot = engine.snapshot(now)
                if snapshot["valuation_fresh"]:
                    performance.observe(snapshot)
                else:
                    performance.stale_valuations += 1
                writer.writerow(
                    [
                        stamp(now),
                        snapshot["equity"],
                        snapshot["cash"],
                        snapshot["valuation_fresh"],
                        snapshot["long_term"]["receivable"],
                    ]
                )
            if manager:
                manager.close(now)
            for file in (decision_file, equity_file, samples_file, audit_file):
                file.flush()
                os.fsync(file.fileno())
        dataset.assert_unchanged()
        with db.transaction() as tx:
            db.reconcile(tx)
            unpaid = sum(
                json.loads(row[0])["paid_id"] is None
                for row in tx.execute("SELECT value FROM meta WHERE key GLOB 'lt_claim:*'")
            )
            income = (
                tx.execute("SELECT value FROM meta WHERE key='lt_income_received'").fetchone()
                or ["0"]
            )[0]
        trades, metrics = ledger_results(db)
        from decimal import Decimal

        gates = {
            "flat_no_pending_orders": not snapshot["positions"] and metrics["pending_orders"] == 0,
            "claims_resolved": unpaid == 0,
            "final_valuation_fresh": snapshot["valuation_fresh"],
            "held_quote_coverage": runtime.counts["held_quote_gaps"]
            == runtime.counts["held_disconnects"]
            == 0,
            "quote_quality": runtime.counts["stale_quotes"]
            == runtime.counts["rejected_quotes"]
            == 0,
        }
        if manager:
            gates["label_intervals_resolved"] = not any(
                count
                for status, count in manager.counts.items()
                if status
                not in {
                    "LABELED",
                    "RISK_REJECTED",
                    "CAPACITY_EXCLUDED",
                    "UNFILLED",
                    "PARTIAL_ENTRY",
                }
            )
        synthetic = (
            dataset.manifest.synthetic
            or dataset.daily.manifest.synthetic
            or runtime.counts["non_kite_quotes"] > 0
        )
        report: dict[str, Any] = {
            "schema_version": 1,
            "kind": "daily-delivery-labels-v1" if labels else "daily-delivery-replay-v1",
            "mode": "paper",
            "status": "complete" if all(gates.values()) else "incomplete",
            "synthetic": synthetic,
            "ready_for_live": False,
            "external_acceptance_verified": False,
            "strategy": strategy.model_dump(mode="json"),
            "strategy_sha256": strategy.digest(),
            "risk_policy": policy_values(isolated),
            "risk_policy_sha256": policy_fingerprint(isolated),
            "charges_version": engine.charges.version,
            "model_sha256": model.version if model else None,
            "model_available_after": stamp(model.artifact.available_after) if model else None,
            "code_sha256": code_digest(),
            "input_hashes": {"daily": dataset.daily.hashes, "execution": dataset.hashes},
            "first_event": stamp(first_event.time),
            "source_available_through": stamp(now),
            "sessions": [day.isoformat() for day in dataset.sessions],
            "observed_quote_sessions": len(session_days),
            "source_session_close": stamp(
                max(
                    datetime.combine(session.day, session.close, IST)
                    for session in dataset.manifest.sessions
                )
            ),
            "event_counts": dict(runtime.counts),
            "daily_late_row_rebuilds": timeline.rebuilds,
            "gates": gates,
            "metrics": {
                **metrics,
                "initial_cash": str(policy.starting_cash),
                "net_observed_pnl": str(Decimal(snapshot["equity"]) - policy.starting_cash),
                "observed_drawdown": str(performance.drawdown),
                "stale_valuation_observations": performance.stale_valuations,
                "unpaid_claims": unpaid,
                "income_received": income,
            },
            "final_snapshot": snapshot,
            "trades": trades,
            "decisions": decision_rows,
            "label_counts": dict(manager.counts) if manager else {},
            "journal_sha256": journal_digest(db),
            "limitations": [
                "Later quotes, adverse prices, fees and depth drive fills; OHLC never fills.",
                "Sparse quotes miss intratick moves; coverage thresholds are explicit assumptions.",
                "Unfinished exposure persists; no final close is invented to complete a report.",
                "Label sums are independent counterfactual trials, not portfolio returns.",
                "Account-specific cash events censor labels; tax/payment values are never guessed.",
                "Source review, historical costs, custody and device acceptance are unverified.",
            ],
        }
        db.close()
        from trading_agent.daily_execution.report import render

        private_text(
            output / "report.json", json.dumps(report, indent=2, sort_keys=True, default=str) + "\n"
        )
        private_text(output / "index.html", render(report))
        private_text(
            output / "report.md",
            "# Daily delivery research\n\n"
            + f"{report['status']}; synthetic: {synthetic}; live: false.\n\n"
            + (
                f"Independent trials: {report['label_counts']}. "
                "Portfolio return is not measured.\n\n"
                if labels
                else f"Observed P&L: {report['metrics']['net_observed_pnl']}; "
                + f"cash: {snapshot['cash']}; fees: {snapshot['fees']}.\n\n"
            )
            + "".join("- " + line + "\n" for line in report["limitations"]),
        )
        context = {
            key: report[key]
            for key in (
                "kind",
                "synthetic",
                "strategy",
                "strategy_sha256",
                "risk_policy",
                "risk_policy_sha256",
                "charges_version",
                "code_sha256",
                "input_hashes",
                "source_available_through",
                "source_session_close",
                "sessions",
                "label_counts",
            )
        }
        private_text(output / "context.json", json.dumps(context, indent=2, sort_keys=True) + "\n")
        dataset.assert_unchanged()
        finish_manifest(
            output,
            [
                "paper.sqlite3",
                "report.json",
                "context.json",
                "index.html",
                "report.md",
                "decisions.jsonl",
                "equity.csv",
                "samples.jsonl",
                "label_audit.jsonl",
            ],
            kind=report["kind"],
            synthetic=synthetic,
        )
        return report
    finally:
        if manager:
            for trial in manager.active[:]:
                trial.runtime.engine.db.close()
        db.close()
