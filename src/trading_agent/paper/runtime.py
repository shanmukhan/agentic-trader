"""One serialized supervised paper pipeline. It has no network execution capability."""

import json
from collections import Counter
from datetime import date, datetime, timedelta
from time import perf_counter_ns
from typing import Any

from trading_agent.backtesting.report import Performance, code_digest
from trading_agent.execution.paper_broker import PENDING, PaperBroker
from trading_agent.market_data.calendar import IST
from trading_agent.market_data.repository import store_candles
from trading_agent.ml.features import make_features
from trading_agent.models import Candle, Instrument, Quote, stamp, utc
from trading_agent.paper.config import FeedSettings, feed_identity
from trading_agent.paper.metrics import Timings
from trading_agent.strategy.rules import RuleStrategy, StrategySettings


class PaperFeed:
    def __init__(
        self,
        engine: PaperBroker,
        *,
        instruments: list[Instrument],
        strategy: StrategySettings,
        settings: FeedSettings,
        now: datetime,
        synthetic: bool = False,
    ):
        if not 1 <= len(instruments) <= 10 or len({i.symbol for i in instruments}) != len(
            instruments
        ):
            raise ValueError("automation requires one to ten unique reviewed instruments")
        if engine.model and engine.model.artifact.synthetic and not synthetic:
            raise ValueError("synthetic models cannot be attached to a connected feed")
        self.engine, self.settings, self.strategy = engine, settings, strategy
        self.catalog = {item.symbol: item for item in instruments}
        self.synthetic = synthetic
        self.rules = RuleStrategy(strategy, engine.calendar)
        self.armed = False
        self.armed_day: date | None = None
        self.reason = "STARTUP"
        self.closed = False
        self.latest: dict[str, Quote] = {}
        self.last_bar: dict[str, Candle] = {}
        self.counts: Counter[str] = Counter()
        self.timings = Timings(settings.processing_budget_ms)
        self.performance = Performance(engine.settings.starting_cash)
        self.last_telemetry = utc(now)
        self.last_time = utc(now)
        identity, self.digest = feed_identity(
            instruments,
            strategy,
            settings,
            engine.model.version if engine.model else None,
            synthetic,
        )
        self.identity = identity
        if engine.automation != self.digest:
            raise ValueError("paper broker is not bound to this automation policy")
        with engine.lock, engine.db.transaction() as tx:
            old = tx.execute("SELECT value FROM meta WHERE key='automation_hash'").fetchone()
            has_events = tx.execute(
                "SELECT 1 FROM events WHERE kind='automation_start' LIMIT 1"
            ).fetchone()
            if bool(old) != bool(has_events):
                raise RuntimeError("missing automation identity")
            if old and old[0] != self.digest:
                raise ValueError("automation policy changed; use a new paper account")
            if not old and tx.execute("SELECT 1 FROM orders LIMIT 1").fetchone():
                raise ValueError("automation requires an unused dedicated paper account")
            engine.db.set(tx, "automation_hash", self.digest)
            engine.db.event(
                tx,
                stamp(now),
                "automation_start",
                "system",
                {**identity, "automation_sha256": self.digest, "code_sha256": code_digest()},
            )
        self._calendar_identity(now)
        self.disarm(now, "STARTUP")

    def _clock(self, now: datetime) -> datetime:
        now = utc(now)
        if now < self.last_time:
            self.engine.faulted = True
            self.engine.set_connected(False)
            self.armed = False
            self.reason = "CLOCK_REGRESSION"
            raise ValueError("paper runtime clock moved backward")
        self.last_time = now
        return now

    def _event(
        self, now: datetime, kind: str, payload: dict[str, Any], entity: str = "system"
    ) -> None:
        with self.engine.db.transaction() as tx:
            self.engine.db.event(tx, stamp(now), kind, entity, payload)

    def _cancel_entries(self, now: datetime) -> None:
        with self.engine.db.transaction() as tx:
            for row in tx.execute(
                f"SELECT * FROM orders WHERE {PENDING} AND side='BUY'"
            ).fetchall():
                self.engine._cancel(tx, row, stamp(now), self.reason)

    def disarm(self, now: datetime, reason: str = "OPERATOR_DISARM") -> None:
        with self.engine.lock:
            now = self._clock(now)
            changed = self.armed or self.reason != reason or reason == "STARTUP"
            self.armed, self.armed_day, self.reason = False, None, reason
            self._cancel_entries(now)
            if changed:
                self._event(now, "automation_state", {"armed": False, "reason": reason})

    def fail(self, now: datetime) -> None:
        # Failure handling must still block entries when the journal itself is unavailable.
        self.armed = False
        self.reason = "RUNTIME_FAULT"
        self.engine.faulted = True
        self.engine.set_connected(False)
        try:
            self._event(now, "automation_fault", {"reason": "RUNTIME_FAULT"})
            self._cancel_entries(now)
        except Exception:
            pass

    def _calendar_identity(self, now: datetime) -> None:
        bounds = self.engine.calendar.bounds(now)
        if not bounds:
            return
        day = now.astimezone(IST).date()
        value = json.dumps(
            {
                "open": stamp(bounds[0]),
                "close": stamp(bounds[1]),
                "source": self.engine.calendar.sources.get(day, "operator-declared session"),
            },
            sort_keys=True,
        )
        with self.engine.db.transaction() as tx:
            key = "automation_calendar:" + day.isoformat()
            old = tx.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
            if old and old[0] != value:
                raise ValueError("a previously used session calendar changed")
            self.engine.db.set(tx, key, value)

    def readiness(self, now: datetime) -> tuple[str, ...]:
        with self.engine.lock:
            now = utc(now)
            reasons = []
            snapshot = self.engine.snapshot(now)
            if self.closed:
                reasons.append("STOPPED")
            if self.engine.faulted:
                reasons.append("RUNTIME_FAULT")
            if not self.engine.connected:
                reasons.append("FEED_DISCONNECTED")
            if snapshot["kill"]:
                reasons.append("KILL_SWITCH")
            if not self.engine.calendar.is_open(now):
                reasons.append("UNKNOWN_OR_CLOSED_SESSION")
            local = now.astimezone(IST)
            if (
                not self.engine.settings.entry_start
                <= local.time()
                < self.engine.settings.entry_end
            ):
                reasons.append("OUTSIDE_ENTRY_WINDOW")
            bounds = self.engine.calendar.bounds(now)
            if bounds and now >= bounds[1] - timedelta(minutes=15):
                reasons.append("EARLY_CLOSE_CUTOFF")
            if self.engine.model:
                artifact = self.engine.model.artifact
                if now <= artifact.available_after:
                    reasons.append("MODEL_NOT_YET_AVAILABLE")
                if now - artifact.validated_through > timedelta(
                    days=self.settings.max_model_age_days
                ):
                    reasons.append("MODEL_TOO_OLD")
            for symbol in self.catalog:
                quote = self.latest.get(symbol)
                if not quote or not self.engine._fresh(quote, now):
                    reasons.append("STALE_UNIVERSE_QUOTE")
                candle, state = self.last_bar.get(symbol), self.rules.states.get(symbol)
                boundary = now.replace(second=0, microsecond=0, minute=now.minute // 5 * 5)
                if (
                    not candle
                    or not state
                    or state.day != local.date()
                    or state.poisoned
                    or state.count
                    < max(self.strategy.indicator_period, self.strategy.volume_lookback + 1)
                    or candle.start + timedelta(minutes=5) != boundary
                ):
                    reasons.append("HISTORY_NOT_READY")
            return tuple(dict.fromkeys(reasons))

    def arm(self, now: datetime) -> dict[str, Any]:
        with self.engine.lock:
            now = self._clock(now)
            self._calendar_identity(now)
            reasons = self.readiness(now)
            if reasons:
                raise ValueError("cannot arm paper automation: " + ",".join(reasons))
            self.armed, self.armed_day, self.reason = (
                True,
                now.astimezone(IST).date(),
                "OPERATOR_ARM",
            )
            self._event(now, "automation_state", {"armed": True, "reason": self.reason})
            return self.status(now)

    def connection(self, connected: bool, now: datetime, *, shutdown: bool = False) -> None:
        try:
            with self.engine.lock:
                now = self._clock(now)
                self.engine.set_connected(connected)
                self.counts["connection_generation"] += 1
                self.counts["connections" if connected else "disconnects"] += 1
                self._event(now, "feed_connection", {"connected": connected})
                if not connected:
                    self.disarm(now, "SHUTDOWN" if shutdown else "FEED_DISCONNECTED")
                    self.latest.clear()
                    self.last_bar.clear()
                    self.rules = RuleStrategy(self.strategy, self.engine.calendar)
                    if self.engine.snapshot(now)["positions"]:
                        self.engine.kill(now, "FEED_DISCONNECTED")
        except Exception:
            self.fail(now)
            raise

    def _guard(self, now: datetime) -> None:
        snapshot = self.engine.snapshot(now)
        if (
            self.armed
            and self.engine.model
            and now - self.engine.model.artifact.validated_through
            > timedelta(days=self.settings.max_model_age_days)
        ):
            self.disarm(now, "MODEL_TOO_OLD")
        if self.armed and self.armed_day != now.astimezone(IST).date():
            self.disarm(now, "SESSION_CHANGED")
        if snapshot["kill"] or self.engine.faulted:
            self.disarm(now, "KILL_SWITCH" if snapshot["kill"] else "RUNTIME_FAULT")
        stale = [
            symbol for symbol, quote in self.latest.items() if not self.engine._fresh(quote, now)
        ]
        if self.armed and (stale or len(self.latest) != len(self.catalog)):
            self.disarm(now, "STALE_UNIVERSE_QUOTE")
        if any(
            position["symbol"] in stale or position["symbol"] not in self.latest
            for position in snapshot["positions"]
        ):
            self.engine.kill(now, "STALE_POSITION_QUOTE")
        if self.armed and (
            not self.engine.calendar.is_open(now)
            or now.astimezone(IST).time() >= self.engine.settings.entry_end
        ):
            self.disarm(now, "ENTRY_WINDOW_ENDED")

    def on_quote(self, quote: Quote, now: datetime) -> bool:
        began = perf_counter_ns()
        try:
            with self.engine.lock:
                now = self._clock(now)
                if self.closed or self.engine.faulted:
                    return False
                if quote.symbol not in self.catalog or (
                    not self.synthetic and quote.source != "kite"
                ):
                    raise ValueError("unexpected source or universe for paper feed")
                self._guard(now)  # Detect a gap before the first resumed quote can fill an entry.
                previous = self.latest.get(quote.symbol)
                accepted = self.engine.ingest(quote, now)
                self.counts["quotes_received"] += 1
                if accepted:
                    self.latest[quote.symbol] = quote
                    self.counts["quotes_accepted"] += 1
                    self.performance.observe(self.engine.snapshot(now))
                    if not self.engine._fresh(quote, now):
                        self.counts["stale_quotes"] += 1
                        self.disarm(now, "STALE_UNIVERSE_QUOTE")
                        if self.engine.snapshot(now)["positions"]:
                            self.engine.kill(now, "STALE_POSITION_QUOTE")
                elif quote != previous:
                    self.counts["quotes_rejected"] += 1
                    self.disarm(now, "QUOTE_QUALITY")
                    self.latest.pop(quote.symbol, None)
                self.timings.observe(
                    "receipt_to_callback",
                    max(0.0, (now - quote.received_time).total_seconds() * 1000),
                )
                return accepted
        except Exception:
            self.fail(now)
            raise
        finally:
            with self.engine.lock:
                self.timings.observe("quote_processing", (perf_counter_ns() - began) / 1e6)

    def history_failed(self, now: datetime) -> None:
        with self.engine.lock:
            now = self._clock(now)
            self.counts["history_failures"] += 1
            self.disarm(now, "HISTORY_UNAVAILABLE")
            self._event(now, "history_failure", {"reason": "HISTORY_UNAVAILABLE"})

    def on_candles(self, candles: list[Candle], now: datetime) -> None:
        began = perf_counter_ns()
        try:
            with self.engine.lock:
                now = self._clock(now)
                if self.closed or self.engine.faulted:
                    return
                self._calendar_identity(now)
                self._guard(now)
                if len(candles) > 1000 or any(
                    c.symbol not in self.catalog
                    or c.minutes != 5
                    or c.start.astimezone(IST).date() != now.astimezone(IST).date()
                    for c in candles
                ):
                    raise ValueError("invalid or oversized current-session history batch")
                store_candles(self.engine.db, candles, now)
                proposals = []
                with self.engine.db.transaction() as tx:
                    used = Counter(
                        json.loads(row[0])["symbol"]
                        for row in tx.execute(
                            "SELECT payload FROM events WHERE kind='automation_candidate' "
                            "AND time>=? AND time<?",
                            (
                                stamp(
                                    datetime.combine(
                                        now.astimezone(IST).date(), datetime.min.time(), IST
                                    )
                                ),
                                stamp(
                                    datetime.combine(
                                        now.astimezone(IST).date() + timedelta(days=1),
                                        datetime.min.time(),
                                        IST,
                                    )
                                ),
                            ),
                        )
                    )
                for candle in sorted(candles, key=lambda item: (item.start, item.symbol)):
                    if candle.symbol not in self.catalog or candle.minutes != 5:
                        raise ValueError("history must match the reviewed 5m universe")
                    previous = self.last_bar.get(candle.symbol)
                    if previous and candle.start <= previous.start:
                        continue  # store_candles already checked equality of every revision.
                    if candle.start.astimezone(IST).date() != now.astimezone(IST).date():
                        raise ValueError("history must be for the current session")
                    allowed = (
                        self.armed
                        and used[candle.symbol] < self.strategy.max_candidates_per_symbol_day
                    )
                    result = self.rules.evaluate(
                        candle,
                        now=now,
                        quote=self.latest.get(candle.symbol),
                        instrument=self.catalog[candle.symbol],
                        connected=self.engine.connected,
                        entries_enabled=allowed,
                    )
                    self.last_bar[candle.symbol] = candle
                    self.counts["candles_evaluated"] += 1
                    self._event(
                        now, "feed_evaluation", result.model_dump(mode="json"), candle.symbol
                    )
                    if result.candidate:
                        candidate, vector, probability = result.candidate, None, 1.0
                        if self.engine.model:
                            candidate = candidate.model_copy(
                                update={
                                    "requires_ml": True,
                                    "model_version": self.engine.model.version,
                                }
                            )
                            bounds = self.engine.calendar.bounds(now)
                            assert bounds is not None
                            vector = make_features(
                                candidate=candidate,
                                candle=candle,
                                candle_end=result.candle_end,
                                features=result.features,
                                quote=self.latest[candle.symbol],
                                instrument=self.catalog[candle.symbol],
                                opened=bounds[0],
                                policy=self.engine.settings,
                            )
                            probability = self.engine.model.score(vector)
                        proposals.append((probability, candidate, vector))
                # A model's age/readiness must hold on every decision, not only on operator arm.
                if proposals and self.readiness(now):
                    self.disarm(now, "DECISION_NOT_READY")
                    return
                for rank, (probability, candidate, vector) in enumerate(
                    sorted(
                        proposals, key=lambda item: (-item[0], item[1].symbol, item[1].intent_id)
                    ),
                    1,
                ):
                    self._event(
                        now,
                        "automation_candidate",
                        {
                            "symbol": candidate.symbol,
                            "candidate": candidate.model_dump(mode="json"),
                            "probability": probability if self.engine.model else None,
                            "rank": rank,
                        },
                        candidate.intent_id,
                    )
                    self.engine.submit(candidate, now, features=vector, automation=self.digest)
                self.counts["candidates"] += len(proposals)
        except Exception:
            self.fail(now)
            raise
        finally:
            with self.engine.lock:
                self.timings.observe("candle_processing", (perf_counter_ns() - began) / 1e6)

    def tick(self, now: datetime, *, force_telemetry: bool = False) -> None:
        try:
            with self.engine.lock:
                now = self._clock(now)
                if self.engine.faulted:
                    return
                self._guard(now)
                self.engine.poll(now)
                self.performance.observe(self.engine.snapshot(now))
                if (
                    force_telemetry
                    or (now - self.last_telemetry).total_seconds()
                    >= self.settings.telemetry_seconds
                ):
                    self._event(now, "paper_telemetry", self.status(now))
                    self.last_telemetry = now
        except Exception:
            self.fail(now)
            raise

    def status(self, now: datetime) -> dict[str, Any]:
        with self.engine.lock:
            return {
                "enabled": True,
                "mode": "paper",
                "armed": self.armed,
                "reason": self.reason,
                "synthetic": self.synthetic,
                "automation_sha256": self.digest,
                "model_sha256": self.engine.model.version if self.engine.model else None,
                "readiness_reasons": list(self.readiness(now)),
                "counts": dict(self.counts),
                "timings": self.timings.snapshot(),
                "snapshot": self.engine.snapshot(now),
                "performance": {
                    "peak": str(self.performance.peak),
                    "drawdown": str(self.performance.drawdown),
                    "drawdown_pct": str(self.performance.drawdown_pct),
                    "observations": self.performance.observations,
                    "stale_valuations": self.performance.stale_valuations,
                },
                "last_candles": {
                    symbol: stamp(candle.start) for symbol, candle in self.last_bar.items()
                },
            }

    def close(self, now: datetime) -> None:
        with self.engine.lock:
            if self.closed:
                return
            self.disarm(now, "SHUTDOWN")
            self.closed = True
            self.engine.set_connected(False)
            self.tick(now, force_telemetry=True)
            self._event(now, "automation_stop", {"reason": "SHUTDOWN"})
