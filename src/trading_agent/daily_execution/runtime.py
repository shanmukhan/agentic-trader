"""Reuse the transactional delivery broker for all research financial effects."""

from bisect import bisect_right
from collections import Counter
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from trading_agent.corporate_actions.contracts import DividendAction
from trading_agent.corporate_actions.service import apply_batch, record_receipt
from trading_agent.daily_execution.contracts import DailyStrategy
from trading_agent.daily_execution.dataset import (
    ActionEvent,
    ConnectionEvent,
    Event,
    KillEvent,
    QuoteEvent,
    ReceiptEvent,
    ReviewEvent,
)
from trading_agent.daily_execution.timeline import DailyTimeline
from trading_agent.execution.paper_broker import PaperBroker
from trading_agent.market_data.calendar import IST, SessionCalendar
from trading_agent.models import Quote

D = Decimal


class TradingClock:
    def __init__(self, calendar: SessionCalendar):
        self.opens = [
            datetime.combine(day, bounds[0], IST)
            for day, bounds in sorted(calendar.sessions.items())
        ]
        self.closes = [
            datetime.combine(day, bounds[1], IST)
            for day, bounds in sorted(calendar.sessions.items())
        ]
        self.prefix = [0.0]
        for opened, closed in zip(self.opens, self.closes, strict=True):
            self.prefix.append(self.prefix[-1] + (closed - opened).total_seconds())

    def at(self, now: datetime) -> float:
        index = bisect_right(self.opens, now) - 1
        return (
            self.prefix[index]
            + min(
                (now - self.opens[index]).total_seconds(),
                (self.closes[index] - self.opens[index]).total_seconds(),
            )
            if index >= 0
            else 0.0
        )

    def seconds(self, start: datetime, end: datetime) -> float:
        if end < start:
            raise ValueError("coverage clock moved backward")
        return self.at(end) - self.at(start)


class ResearchRuntime:
    def __init__(
        self,
        engine: PaperBroker,
        timeline: DailyTimeline,
        strategy: DailyStrategy,
        *,
        observer: bool = False,
    ):
        self.engine, self.timeline, self.strategy, self.observer = (
            engine,
            timeline,
            strategy,
            observer,
        )
        self.latest: dict[str, Quote] = {}
        self.reviews: dict[tuple[str, date], Any] = {}
        self.effects: dict[tuple[str, date], tuple[Decimal, Decimal]] = {}
        self.claim_symbols: dict[str, str] = {}
        self.counts: Counter[str] = Counter()
        self.clock = TradingClock(engine.calendar)

    def feed(self, event: Event) -> bool:
        e, now = self.engine, event.time
        accepted = False
        self.counts[event.type] += 1
        if isinstance(event, ConnectionEvent):
            if not event.connected:
                with e.db.transaction() as tx:
                    if tx.execute("SELECT 1 FROM positions LIMIT 1").fetchone():
                        self.counts["held_disconnects"] += 1
            e.set_connected(event.connected)
            self.latest.clear()
        elif isinstance(event, ReviewEvent):
            e.review_holding(event.review, now)
            self.reviews[(event.review.symbol, event.review.session_date)] = event.review
        elif isinstance(event, ActionEvent):
            batch = event.batch
            if self.observer:
                # This observer never owns shares: zero entitlement implies zero deduction.
                batch = batch.model_copy(
                    update={
                        "actions": tuple(
                            action.model_copy(update={"withholding": D(0)})
                            if isinstance(action, DividendAction)
                            else action
                            for action in batch.actions
                        )
                    }
                )
            apply_batch(e.db, e.settings, e.calendar, batch, now)
            grouped: dict[date, tuple[Decimal, Decimal]] = {}
            for action in event.batch.actions:
                factor, cash = grouped.get(action.ex_date, (D(1), D(0)))
                if isinstance(action, DividendAction):
                    cash += action.per_share * factor
                else:
                    factor *= D(action.numerator) / action.denominator + (
                        1 if action.kind == "bonus" else 0
                    )
                grouped[action.ex_date] = factor, cash
                self.claim_symbols[action.action_id] = event.batch.symbol
            self.effects.update(
                {(event.batch.symbol, day): values for day, values in grouped.items()}
            )
            self.latest.pop(event.batch.symbol, None)
        elif isinstance(event, ReceiptEvent):
            if self.observer:
                if (
                    event.receipt.claim_id not in self.claim_symbols
                    or event.receipt.reviewed_at > now
                    or event.receipt.paid_date > now.astimezone(IST).date()
                ):
                    raise ValueError(
                        "receipt needs a preceding source action and observed payment clocks"
                    )
            else:
                record_receipt(e.db, e.settings, event.receipt, now)
        elif isinstance(event, KillEvent):
            e.kill(now)
        elif isinstance(event, QuoteEvent):
            quote = event.quote
            day = now.astimezone(IST).date()
            daily_bar = self.timeline.bars.get((quote.symbol, day))
            if daily_bar and not daily_bar.low <= quote.last <= daily_bar.high:
                raise ValueError("observed last trade contradicts the declared daily OHLC range")
            review = self.reviews.get((quote.symbol, day))
            if (
                review
                and review.no_corporate_action
                and (quote.symbol, day) in self.timeline.bars
                and self.effects.get((quote.symbol, day), (D(1), D(0)))
                != self.timeline.benefit(quote.symbol, day)
            ):
                raise ValueError("daily benefits and the applied execution price basis disagree")
            old = self.latest.get(quote.symbol)
            if (
                old
                and self.clock.seconds(old.received_time, now)
                > self.strategy.max_open_quote_gap_seconds
            ):
                with e.db.transaction() as tx:
                    held = tx.execute(
                        "SELECT 1 FROM positions WHERE symbol=?", (quote.symbol,)
                    ).fetchone()
                if held:
                    self.counts["held_quote_gaps"] += 1
            if any(
                not 0 <= (now - clock).total_seconds() <= e.settings.max_quote_age_seconds
                for clock in (quote.exchange_time, quote.received_time)
            ):
                self.counts["stale_quotes"] += 1
            accepted = e.ingest(quote, now)
            if accepted:
                self.latest[quote.symbol] = quote
            elif old != quote:
                self.counts["rejected_quotes"] += 1
            if quote.source != "kite":
                self.counts["non_kite_quotes"] += 1
        e.poll(now)
        return accepted
