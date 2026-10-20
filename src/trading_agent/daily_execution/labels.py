"""Independent delivery trials, explicit censoring and reproducible sample evidence."""

import json
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, TextIO

from pydantic import SecretStr

from trading_agent.backtesting.report import journal_digest, ledger_results
from trading_agent.corporate_actions.contracts import DividendAction
from trading_agent.daily_execution.contracts import DailySample, DailyVector, digest
from trading_agent.daily_execution.dataset import (
    ActionEvent,
    ConnectionEvent,
    Event,
    KillEvent,
    QuoteEvent,
    ReceiptEvent,
    ReviewEvent,
)
from trading_agent.daily_execution.runtime import ResearchRuntime
from trading_agent.execution.paper_broker import PaperBroker
from trading_agent.market_data.calendar import IST
from trading_agent.models import Candidate, Quote, stamp
from trading_agent.persistence.database import Database


@dataclass
class Trial:
    id: str
    runtime: ResearchRuntime
    candidate: Candidate
    features: DailyVector
    deadline: datetime | None
    last_quote: Quote


class Labels:
    def __init__(self, observer: ResearchRuntime, output: Path, samples: TextIO, audit: TextIO):
        self.observer, self.output, self.samples, self.audit = observer, output, samples, audit
        (output / "trials").mkdir(mode=0o700)
        self.active: list[Trial] = []
        self.counts: Counter[str] = Counter()
        self.attempted = 0

    def _audit(self, trial_id: str, status: str, **values: Any) -> None:
        self.counts[status] += 1
        self.audit.write(
            json.dumps({"id": trial_id, "status": status, **values}, sort_keys=True, default=str)
            + "\n"
        )

    def start(self, candidate: Candidate, features: DailyVector, quote: Quote) -> None:
        r = self.observer
        trial_id = digest({"candidate": features.candidate_sha256, "strategy": r.strategy.digest()})
        self.attempted += 1
        if (
            self.attempted > r.strategy.max_samples
            or len(self.active) >= r.strategy.max_active_labels
        ):
            self._audit(trial_id, "CAPACITY_EXCLUDED")
            return
        folder = self.output / "trials" / trial_id
        folder.mkdir(mode=0o700)
        settings = r.engine.settings.model_copy(
            update={"database": folder / "paper.sqlite3", "operator_token": SecretStr("")}
        )
        db = Database(settings.database, settings.starting_cash)
        try:
            engine = PaperBroker(
                db, settings, r.engine.calendar, recovery_time=candidate.decision_time
            )
            with r.engine.db.transaction() as tx:
                row = tx.execute(
                    "SELECT * FROM instruments WHERE symbol=?", (candidate.symbol,)
                ).fetchone()
            from trading_agent.models import Instrument

            engine.register(
                [Instrument(symbol=row["symbol"], token=row["token"], tick_size=row["tick"])]
            )
            runtime = ResearchRuntime(engine, r.timeline, r.strategy)
            engine.set_connected(r.engine.connected)
            day = candidate.decision_time.astimezone(IST).date()
            review = r.reviews[(candidate.symbol, day)]
            runtime.feed(ReviewEvent(time=candidate.decision_time, review=review))
            # This trial starts on the already reviewed current raw basis; prior actions
            # affected no trial shares and must not be applied retroactively to a new buy.
            runtime.effects.update(r.effects)
            runtime.feed(QuoteEvent(time=candidate.decision_time, quote=quote))
            order = engine.submit(candidate, candidate.decision_time)
            index = r.timeline.indices[day] + r.strategy.max_hold_sessions
            deadline = None
            if index < len(r.timeline.sessions):
                deadline = datetime.combine(r.timeline.sessions[index], settings.entry_start, IST)
            trial = Trial(trial_id, runtime, candidate, features, deadline, quote)
            self.active.append(trial)
            if order["state"] == "REJECTED":
                self.finish(trial, candidate.decision_time, "RISK_REJECTED")
        except BaseException:
            db.close()
            raise

    def feed(self, event: Event) -> None:
        for trial in self.active[:]:
            r, now = trial.runtime, event.time
            symbol = trial.candidate.symbol
            reason = None
            relevant = True
            if (
                isinstance(event, ConnectionEvent)
                and not event.connected
                or isinstance(event, KillEvent)
            ):
                reason = "INTERRUPTED"
            elif isinstance(event, ActionEvent):
                relevant = event.batch.symbol == symbol
                if relevant and any(
                    isinstance(action, DividendAction) for action in event.batch.actions
                ):
                    reason = "ACCOUNT_SPECIFIC_CASH_ACTION"
            elif isinstance(event, ReceiptEvent):
                relevant = self.observer.claim_symbols.get(event.receipt.claim_id) == symbol
                if relevant:
                    reason = "ACCOUNT_SPECIFIC_CASH_RECEIPT"
            elif isinstance(event, ReviewEvent):
                relevant = event.review.symbol == symbol
            elif isinstance(event, QuoteEvent):
                relevant = event.quote.symbol == symbol
                if relevant:
                    if (
                        r.clock.seconds(trial.last_quote.received_time, now)
                        > r.strategy.max_open_quote_gap_seconds
                    ):
                        reason = "QUOTE_GAP"
                    if any(
                        not 0
                        <= (now - clock).total_seconds()
                        <= r.engine.settings.max_quote_age_seconds
                        for clock in (event.quote.exchange_time, event.quote.received_time)
                    ):
                        reason = "STALE_QUOTE"
            if reason:
                self.finish(trial, now, reason)
                continue
            day = now.astimezone(IST).date()
            if (trial.deadline and now >= trial.deadline) or not r.timeline.included(
                symbol, day, now
            ):
                reason_text = (
                    "DAILY_LABEL_TIME_LIMIT"
                    if trial.deadline and now >= trial.deadline
                    else "DAILY_LABEL_UNIVERSE_EXIT"
                )
                with r.engine.lock, r.engine.db.transaction() as tx:
                    for order in tx.execute(
                        "SELECT * FROM orders WHERE side='BUY' AND state IN ('ACCEPTED','PARTIAL')"
                    ).fetchall():
                        r.engine._cancel(tx, order, stamp(now), reason_text)
                    r.engine._exit(tx, symbol, now, reason_text)
            if relevant:
                accepted = r.feed(event)
                if isinstance(event, QuoteEvent):
                    if not accepted and event.quote != trial.last_quote:
                        self.finish(trial, now, "QUOTE_QUALITY")
                        continue
                    trial.last_quote = event.quote
            else:
                r.engine.poll(now)
            snapshot = r.engine.snapshot(now)
            pending = any(order["state"] in {"ACCEPTED", "PARTIAL"} for order in r.engine.orders())
            if not snapshot["positions"] and not pending:
                self.finish(trial, now)

    def finish(self, trial: Trial, now: datetime, censor: str | None = None) -> None:
        engine = trial.runtime.engine
        try:
            with engine.db.transaction() as tx:
                engine.db.reconcile(tx)
                entry = dict(
                    tx.execute(
                        "SELECT * FROM orders WHERE id=?", (trial.candidate.intent_id,)
                    ).fetchone()
                )
                claims = [
                    json.loads(row[0])
                    for row in tx.execute("SELECT value FROM meta WHERE key GLOB 'lt_claim:*'")
                ]
            trades, _ = ledger_results(engine.db)
            snapshot = engine.snapshot(now)
            status = censor or (
                "UNFILLED"
                if entry["filled"] == 0
                else "PARTIAL_ENTRY"
                if entry["filled"] != entry["quantity"]
                else "UNSETTLED_CLAIM"
                if any(claim["paid_id"] is None for claim in claims)
                else "UNFINISHED"
                if snapshot["positions"] or len(trades) != 1
                else "LABELED"
            )
            sample = None
            if status == "LABELED":
                trade = trades[0]
                sample = DailySample(
                    id=trial.id,
                    features=trial.features,
                    label_end=datetime.fromisoformat(trade["exit_time"]),
                    target=1 if trade["exit_reason"] == "TARGET" and trade["net_pnl"] > 0 else 0,
                    net_pnl=trade["net_pnl"],
                    exit_reason=trade["exit_reason"],
                )
                self.samples.write(sample.model_dump_json() + "\n")
            self._audit(
                trial.id,
                status,
                decision_time=stamp(trial.features.time),
                observed_through=stamp(now),
                candidate=trial.candidate.model_dump(mode="json"),
                sample=sample.model_dump(mode="json") if sample else None,
                entry=entry,
                positions=snapshot["positions"],
                cash=snapshot["cash"],
                journal_sha256=journal_digest(engine.db),
            )
        finally:
            engine.db.close()
            self.active.remove(trial)

    def close(self, now: datetime) -> None:
        for trial in self.active[:]:
            self.finish(trial, now, "SOURCE_ENDED")
