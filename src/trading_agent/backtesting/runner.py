"""Streaming chronological research with the SAME risk/accounting path as paper execution."""

import csv
import json
import platform
import sqlite3
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from pydantic import VERSION as PYDANTIC_VERSION
from pydantic import SecretStr

from trading_agent import __version__
from trading_agent.backtesting.dataset import (
    CandleEvent,
    ConnectionEvent,
    Dataset,
    KillEvent,
    QuoteEvent,
)
from trading_agent.backtesting.report import (
    Performance,
    code_digest,
    journal_digest,
    ledger_results,
    write_report,
)
from trading_agent.execution.paper_broker import PaperBroker
from trading_agent.market_data.calendar import IST
from trading_agent.models import Quote, stamp
from trading_agent.persistence.database import Database
from trading_agent.settings import Settings
from trading_agent.strategy.rules import RULE_VERSION, RuleStrategy, StrategySettings


def run_backtest(
    dataset: Dataset, *, strategy: StrategySettings, policy: Settings, output: Path
) -> dict[str, Any]:
    output = output.resolve()
    if output.is_relative_to(dataset.directory):
        raise ValueError("research output must be outside the input dataset")
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    isolated = policy.model_copy(
        update={"database": output / "paper.sqlite3", "operator_token": SecretStr("")}
    )
    db = Database(isolated.database, isolated.starting_cash)
    try:
        engine = PaperBroker(db, isolated, dataset.manifest.calendar())
        engine.register(list(dataset.manifest.instruments))
        rules = RuleStrategy(strategy, engine.calendar)
        catalog = {i.symbol: i for i in dataset.manifest.instruments}
        latest: dict[str, Quote] = {}
        counts: Counter[str] = Counter()
        reasons: Counter[str] = Counter()
        days: set[str] = set()
        performance = Performance(policy.starting_cash)
        first: datetime | None = None
        last: datetime | None = None
        last_snapshot: dict[str, Any] | None = None
        with (
            (output / "decisions.jsonl").open("x") as decisions,
            (output / "equity.csv").open("x", newline="") as equity_file,
        ):
            equity = csv.writer(equity_file)
            equity.writerow(["time", "equity", "cash", "reserved_cash", "valuation_fresh"])
            for event in dataset.events():
                now = event.time
                first, last = first or now, now
                counts[event.type] += 1
                if isinstance(event, ConnectionEvent):
                    engine.set_connected(event.connected)
                    latest.clear()
                elif isinstance(event, QuoteEvent):
                    old = latest.get(event.quote.symbol)
                    if any(
                        (now - t).total_seconds() > policy.max_quote_age_seconds
                        for t in (event.quote.exchange_time, event.quote.received_time)
                    ):
                        counts["stale_quote_events"] += 1
                    if (
                        old
                        and (now - old.received_time).total_seconds() > policy.max_quote_age_seconds
                        and last_snapshot
                        and any(
                            p["symbol"] == event.quote.symbol for p in last_snapshot["positions"]
                        )
                    ):
                        counts["held_quote_gaps"] += 1
                    if engine.ingest(event.quote, now):
                        latest[event.quote.symbol] = event.quote
                    else:
                        counts["ignored_quotes"] += 1
                        if old != event.quote:
                            counts["rejected_quote_events"] += 1
                    days.add(event.quote.exchange_time.astimezone(IST).date().isoformat())
                elif isinstance(event, CandleEvent):
                    evaluation = rules.evaluate(
                        event.candle,
                        now=now,
                        quote=latest.get(event.candle.symbol),
                        instrument=catalog[event.candle.symbol],
                        connected=engine.connected,
                    )
                    payload = evaluation.model_dump(mode="json")
                    reasons.update(evaluation.reasons)
                    with db.transaction() as tx:
                        db.event(
                            tx, stamp(now), "strategy_evaluation", event.candle.symbol, payload
                        )
                    if evaluation.candidate:
                        order = engine.submit(evaluation.candidate, now)
                        payload["risk_order_state"], payload["risk_reasons"] = (
                            order["state"],
                            order["reason"],
                        )
                        counts["candidates"] += 1
                    decisions.write(json.dumps(payload, sort_keys=True) + "\n")
                    days.add(event.candle.start.astimezone(IST).date().isoformat())
                elif isinstance(event, KillEvent):
                    engine.kill(now)
                engine.poll(now)
                snapshot = engine.snapshot(now)
                performance.observe(snapshot)
                equity.writerow(
                    [
                        stamp(now),
                        snapshot["equity"],
                        snapshot["cash"],
                        snapshot["reserved_cash"],
                        snapshot["valuation_fresh"],
                    ]
                )
                last_snapshot = snapshot
        if first is None or last is None or last_snapshot is None:
            raise ValueError("empty research dataset")
        if not counts["quote"] or not counts["candle"]:
            raise ValueError(
                "strategy backtests require both completed candles and observed quotes"
            )
        dataset.assert_unchanged()
        with db.transaction() as tx:
            db.reconcile(tx)
            policy_hash = db.get(tx, "policy_hash")
        trades, metrics = ledger_results(db)
        metrics.update(
            {
                "initial_cash": str(policy.starting_cash),
                "net_pnl": str(Decimal(last_snapshot["equity"]) - policy.starting_cash),
                "return_pct": str(
                    (Decimal(last_snapshot["equity"]) / policy.starting_cash - 1) * 100
                ),
                "max_drawdown": str(performance.drawdown),
                "max_drawdown_pct": str(performance.drawdown_pct),
                "stale_valuation_observations": performance.stale_valuations,
                "observed_session_count": len(days),
            }
        )
        gates = {
            "flat_at_end": not last_snapshot["positions"] and not metrics["pending_orders"],
            "candle_quality": reasons["DATA_GAP_OR_QUALITY"] == 0,
            "held_quote_continuity": counts["held_quote_gaps"] == 0,
            "no_stale_valuations": performance.stale_valuations == 0,
            "quote_quality": counts["rejected_quote_events"] == counts["stale_quote_events"] == 0,
            "non_synthetic": not dataset.manifest.synthetic,
            "minimum_research_sample": len(days) >= 20 and len(trades) >= 30,
        }
        complete = all(
            gates[name]
            for name in (
                "flat_at_end",
                "candle_quality",
                "held_quote_continuity",
                "no_stale_valuations",
                "quote_quality",
            )
        )
        policy_values = isolated.model_dump(
            mode="json",
            exclude={"operator_token", "database", "host", "port", "calendar", "stream_tokens"},
        )
        report = {
            "schema_version": 1,
            "rule_version": RULE_VERSION,
            "runtime": {
                "application": __version__,
                "python": platform.python_version(),
                "sqlite": sqlite3.sqlite_version,
                "pydantic": PYDANTIC_VERSION,
            },
            "mode": "paper",
            "status": "complete" if complete else "incomplete",
            "ready_for_live": False,
            "dataset": dataset.manifest.model_dump(mode="json"),
            "input_hashes": dataset.hashes,
            "code_sha256": code_digest(),
            "strategy": strategy.model_dump(mode="json"),
            "strategy_sha256": strategy.digest(),
            "risk_policy": policy_values,
            "risk_policy_sha256": policy_hash,
            "charges_version": engine.charges.version,
            "charge_schedule_observed_on": str(engine.charges.observed_on),
            "fee_schedule_matches_historical_dates": "not_verified",
            "first_event": stamp(first),
            "last_event": stamp(last),
            "event_counts": dict(sorted(counts.items())),
            "strategy_reasons": dict(sorted(reasons.items())),
            "research_gates": gates,
            "metrics": metrics,
            "final_snapshot": last_snapshot,
            "journal_sha256": journal_digest(db),
        }
        write_report(output, report, trades)
        (output / "run.json").write_text(
            json.dumps({"state": "finished", "status": report["status"]}) + "\n"
        )
        return report
    except BaseException as error:
        (output / "run.json").write_text(
            json.dumps({"state": "failed", "error_type": type(error).__name__}) + "\n"
        )
        raise
    finally:
        db.close()
