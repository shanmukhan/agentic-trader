"""Causal rule candidates, labeled by independent real paper execution paths."""

import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any, TextIO

from trading_agent.backtesting.dataset import (
    CandleEvent,
    ConnectionEvent,
    Dataset,
    KillEvent,
    QuoteEvent,
    digest_file,
)
from trading_agent.backtesting.report import code_digest, journal_digest, ledger_results
from trading_agent.execution.paper_broker import PaperBroker
from trading_agent.market_data.calendar import IST
from trading_agent.ml.features import FeatureVector, make_features
from trading_agent.ml.samples import SampleManifest
from trading_agent.ml.schema import LabelPolicy, Sample
from trading_agent.models import Quote, stamp
from trading_agent.persistence.database import Database
from trading_agent.risk.policy import policy_fingerprint, policy_values
from trading_agent.settings import Settings
from trading_agent.strategy.rules import RuleStrategy, StrategySettings


@dataclass
class Trial:
    id: str
    features: FeatureVector
    engine: PaperBroker
    temporary: TemporaryDirectory[str]
    deadline: datetime
    last_quote: Quote


def finish(
    trial: Trial,
    now: datetime,
    censor: str | None,
    samples: TextIO,
    audit: TextIO,
    counts: Counter[str],
) -> None:
    """Persist enough execution evidence before destroying only this temporary account."""
    engine, db = trial.engine, trial.engine.db
    try:
        with db.transaction() as tx:
            db.reconcile(tx)
            fills = [dict(row) for row in tx.execute("SELECT * FROM fills ORDER BY seq")]
        trades, metrics = ledger_results(db)
        orders = engine.orders()
        snapshot = engine.snapshot(now)
        if censor is None:
            if len(trades) != 1 or snapshot["positions"] or metrics["pending_orders"]:
                censor = "UNRESOLVED_OR_UNFILLED"
            elif trades[0]["exit_reason"] not in {
                "TARGET",
                "STOP",
                "LABEL_TIME_LIMIT",
                "SESSION_END",
            }:
                censor = "OTHER_RISK_EXIT"
        if censor is None:
            trade = trades[0]
            sample = Sample(
                id=trial.id,
                features=trial.features,
                label_end=datetime.fromisoformat(trade["exit_time"]),
                target=1 if trade["exit_reason"] == "TARGET" and trade["net_pnl"] > 0 else 0,
                net_pnl=trade["net_pnl"],
                exit_reason=trade["exit_reason"],
            )
            samples.write(sample.model_dump_json() + "\n")
            counts["labeled"] += 1
            counts[f"target_{sample.target}"] += 1
        else:
            counts["censored"] += 1
            counts[f"censored:{censor}"] += 1
        audit.write(
            json.dumps(
                {
                    "id": trial.id,
                    "features": trial.features.model_dump(mode="json"),
                    "deadline": stamp(trial.deadline),
                    "censor_reason": censor,
                    "orders": orders,
                    "fills": fills,
                    "snapshot": snapshot,
                    "journal_sha256": journal_digest(db),
                },
                sort_keys=True,
                default=str,
            )
            + "\n"
        )
    finally:
        db.close()
        trial.temporary.cleanup()


def build_samples(
    dataset: Dataset,
    *,
    strategy: StrategySettings,
    policy: Settings,
    output: Path,
    labels: LabelPolicy | None = None,
) -> dict[str, Any]:
    labels = labels or LabelPolicy()
    output = output.resolve()
    if output.is_relative_to(dataset.directory):
        raise ValueError("labels must be outside the raw dataset")
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    counts: Counter[str] = Counter()
    calendar = dataset.manifest.calendar()
    catalog = {item.symbol: item for item in dataset.manifest.instruments}
    rules = RuleStrategy(strategy, calendar)
    active: list[Trial] = []
    latest: dict[str, Quote] = {}
    connected = False
    now: datetime | None = None
    # The observer validates quotes but never submits an order.
    observer_db = Database(output / "observer.sqlite3", policy.starting_cash)
    observer = PaperBroker(observer_db, policy, calendar)
    observer.register(list(catalog.values()))
    try:
        with (
            (output / "samples.jsonl").open("x") as samples,
            (output / "label_audit.jsonl").open("x") as audit,
        ):
            for event in dataset.events():
                now = event.time
                for trial in active[:]:
                    censor = None
                    if (
                        isinstance(event, ConnectionEvent)
                        and not event.connected
                        or isinstance(event, KillEvent)
                    ):
                        censor = "INTERRUPTED"
                    if (
                        isinstance(event, CandleEvent)
                        and event.candle.symbol == trial.features.symbol
                        and event.candle.quality != "ok"
                    ):
                        censor = "CANDLE_QUALITY"
                    if now >= trial.deadline:
                        trial.engine.kill(trial.deadline, "LABEL_TIME_LIMIT")
                    if (
                        isinstance(event, QuoteEvent)
                        and event.quote.symbol == trial.features.symbol
                    ):
                        if (
                            now - trial.last_quote.received_time
                        ).total_seconds() > policy.max_quote_age_seconds:
                            censor = "QUOTE_GAP"
                        if any(
                            (now - t).total_seconds() > policy.max_quote_age_seconds
                            for t in (event.quote.exchange_time, event.quote.received_time)
                        ):
                            censor = "STALE_QUOTE"
                        if censor is None:
                            accepted = trial.engine.ingest(event.quote, now)
                            if not accepted and event.quote != trial.last_quote:
                                censor = "QUOTE_QUALITY"
                            trial.last_quote = event.quote
                    trial.engine.poll(now)
                    snapshot = trial.engine.snapshot(now)
                    pending = any(
                        order["state"] in {"ACCEPTED", "PARTIAL"} for order in trial.engine.orders()
                    )
                    if censor or not snapshot["positions"] and not pending:
                        finish(trial, now, censor, samples, audit, counts)
                        active.remove(trial)
                if isinstance(event, ConnectionEvent):
                    connected = event.connected
                    observer.set_connected(connected)
                    latest.clear()
                elif isinstance(event, KillEvent):
                    connected = False
                    latest.clear()
                    observer.set_connected(False)
                elif isinstance(event, QuoteEvent):
                    previous = latest.get(event.quote.symbol)
                    if observer.ingest(event.quote, now):
                        latest[event.quote.symbol] = event.quote
                    elif event.quote != previous:
                        latest.pop(event.quote.symbol, None)
                elif isinstance(event, CandleEvent):
                    evaluation = rules.evaluate(
                        event.candle,
                        now=now,
                        quote=latest.get(event.candle.symbol),
                        instrument=catalog[event.candle.symbol],
                        connected=connected,
                    )
                    candidate = evaluation.candidate
                    if candidate is None:
                        continue
                    counts["candidates"] += 1
                    if len(active) >= labels.max_active:
                        raise ValueError(
                            "too many overlapping labels; raise bounded label capacity explicitly"
                        )
                    quote = latest[candidate.symbol]
                    bounds = calendar.bounds(now)
                    assert bounds is not None
                    features = make_features(
                        candidate=candidate,
                        candle=event.candle,
                        candle_end=evaluation.candle_end,
                        features=evaluation.features,
                        quote=quote,
                        instrument=catalog[candidate.symbol],
                        opened=bounds[0],
                        policy=policy,
                    )
                    temporary = TemporaryDirectory(prefix="label-", dir=output)
                    db = Database(Path(temporary.name) / "paper.sqlite3", policy.starting_cash)
                    engine = PaperBroker(db, policy, calendar)
                    engine.register(list(catalog.values()))
                    engine.set_connected(True)
                    engine.ingest(quote, now)
                    deadline = min(
                        now + timedelta(minutes=labels.horizon_minutes),
                        bounds[1] - timedelta(minutes=15),
                        datetime.combine(now.astimezone(IST).date(), policy.flatten_at, IST),
                    )
                    trial = Trial(candidate.intent_id, features, engine, temporary, deadline, quote)
                    active.append(trial)
                    order = engine.submit(candidate, now)
                    if order["state"] == "REJECTED":
                        finish(trial, now, "RISK_REJECTED", samples, audit, counts)
                        active.remove(trial)
            assert now is not None
            for trial in active[:]:
                finish(trial, now, "DATASET_END", samples, audit, counts)
                active.remove(trial)
        dataset.assert_unchanged()
        manifest = SampleManifest(
            synthetic=dataset.manifest.synthetic,
            source_hashes=dataset.hashes,
            source_description=dataset.manifest.source,
            source_manifest=dataset.manifest,
            source_available_through=now,
            strategy_settings=strategy,
            risk_policy=policy_values(policy),
            strategy_sha256=strategy.digest(),
            policy_sha256=policy_fingerprint(policy),
            charges_version=observer.charges.version,
            code_sha256=code_digest(),
            label_policy=labels,
            sessions=tuple(sorted(session.day for session in dataset.manifest.sessions)),
            counts=dict(counts),
            samples_sha256=digest_file(output / "samples.jsonl"),
            audit_sha256=digest_file(output / "label_audit.jsonl"),
        )
        manifest_json = manifest.model_dump_json(indent=2) + "\n"
        if len(manifest_json.encode()) > 1_000_000:
            raise ValueError("sample manifest exceeds its load limit")
        (output / "manifest.json").write_text(manifest_json)
        return manifest.model_dump(mode="json")
    finally:
        for trial in active:
            trial.engine.db.close()
            trial.temporary.cleanup()
        observer_db.close()
