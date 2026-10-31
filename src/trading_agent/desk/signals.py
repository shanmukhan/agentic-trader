"""Causal proposals and background analysis; never network I/O under risk locks."""

import hashlib
import math
import threading
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any

from trading_agent.daily_execution.contracts import DailyVector, finite_features
from trading_agent.execution.costs import down, up
from trading_agent.market_data.calendar import IST
from trading_agent.ml.features import candidate_fingerprint
from trading_agent.models import Candidate, Instrument, Quote, stamp
from trading_agent.strategy.rules import RuleStrategy

D = Decimal


def daily_vector(
    candidate: Candidate, quote: Quote, screen: dict[str, Any], now: datetime, engine: Any
) -> DailyVector:
    bounds = engine.calendar.bounds(now)
    if bounds is None:
        raise ValueError("No reviewed open session.")
    gap = (quote.ask / D(screen["last_close"]) - 1) * 10000
    return DailyVector(
        symbol=quote.symbol,
        time=now,
        daily_session=datetime.fromisoformat(screen["last_session"]).date(),
        available_at=datetime.fromisoformat(screen["available_at"]),
        candidate_sha256=candidate_fingerprint(candidate),
        values=finite_features(
            (
                D(screen["gross_total_return_pct"]),
                (D(screen["index_level"]) / D(screen["trend_index_average"]) - 1) * 100,
                D(screen["daily_volatility_pct"]),
                math.log1p(float(screen["average_turnover"])),
                (quote.ask - quote.bid) / quote.bid * 10000,
                gap,
                (quote.ask - candidate.stop) / quote.ask * 10000,
                (candidate.target - quote.ask) / quote.ask * 10000,
                (now - bounds[0]).total_seconds() / 60,
                math.log(float(quote.ask)),
                screen["observations"],
                (candidate.target - quote.ask) / (quote.ask - candidate.stop),
            )
        ),
    )


class AnalysisWorker:
    def __init__(self, desk: Any, setup: Any, clock: Any):
        self.desk, self.setup, self.clock = desk, setup, clock
        self.stop = threading.Event()
        self.thread: threading.Thread | None = None
        self.refreshed: datetime | None = None
        self.boundary: datetime | None = None
        self.attempt: datetime | None = None
        from trading_agent.desk.live_intraday import LiveIntraday

        self.live = (
            LiveIntraday(desk, setup, clock, self.stop)
            if getattr(setup, "uses_persisted_candles", False) is True
            else None
        )

    def start(self) -> None:
        self.thread = threading.Thread(target=self._run, name="paper-analysis", daemon=True)
        self.thread.start()

    def _run(self) -> None:
        while not self.stop.is_set():
            try:
                self.evaluate(self.clock())
            except Exception:
                # Never publish third-party exception text or credentials.
                with self.desk.engine.lock:
                    self.desk.analysis_error = "ANALYSIS_FAILED_CHECK_PROFILE_AND_DATA"
                    self.desk.pause(self.clock(), "ANALYSIS_FAILURE")
            self.stop.wait(1)

    def close(self) -> None:
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=12)
        if self.live:
            self.live.close()

    def evaluate(self, now: datetime) -> None:
        d, e, research = self.desk, self.desk.engine, self.desk.research
        if not research:
            return
        revision = d.revision
        if not self.refreshed or now - self.refreshed >= timedelta(seconds=60):
            research.refresh(now)  # Parsing/hashing/ranking outside the execution lock.
            self.refreshed = now
            d.last_analysis, d.analysis_error = stamp(now), None
        if self.live and not e.long_term:
            with e.lock:
                if not e.connected or not e.calendar.is_open(now):
                    return
                execution_tokens = set(d.execution_tokens)
                with e.db.transaction() as tx:
                    selected = [
                        Instrument(symbol=r["symbol"], token=r["token"], tick_size=r["tick"])
                        for r in tx.execute("SELECT * FROM instruments")
                        if r["token"] in execution_tokens
                    ]
                allow_entries = d.mode != "manual" and not any(
                    reason != "INTRADAY_HISTORY_UNAVAILABLE" for reason in d.blockers(now)
                )
            self.live.evaluate(now, selected, revision, allow_entries=allow_entries)
            return
        with e.lock:
            if d.mode == "manual" or any(
                reason != "INTRADAY_HISTORY_UNAVAILABLE" for reason in d.blockers(now)
            ):
                return
            execution_tokens = set(d.execution_tokens)
            with e.db.transaction() as tx:
                selected = [
                    Instrument(symbol=r["symbol"], token=r["token"], tick_size=r["tick"])
                    for r in tx.execute("SELECT * FROM instruments")
                    if r["token"] in execution_tokens
                ]
        if e.long_term:
            research.ensure_symbols({i.symbol for i in selected}, now)
            self.daily(now, selected, revision)
        elif self.setup:
            if self.live:
                self.live.evaluate(now, selected, revision)
            else:
                self.intraday(now, selected, revision)

    def daily(self, now: datetime, selected: list[Instrument], revision: str) -> None:
        d, e, research = self.desk, self.desk.engine, self.desk.research
        assert research is not None
        key = (now.astimezone(IST).date(), revision)
        # Revisit fresh-quote availability, but durable per-symbol keys prevent repeated proposals.
        profile = research.profile
        rows = sorted(
            research.result["rows"], key=lambda row: (row["rank"] or 10000, row["symbol"])
        )
        eligible = {item.symbol: item for item in selected}
        for row in rows:
            symbol = row["symbol"]
            if self.stop.is_set() or symbol not in eligible:
                continue
            with e.lock:
                if revision != d.revision or d.mode == "manual":
                    return
                with e.db.transaction() as tx:
                    quote = e._quote(tx, symbol)
                    holding_row = tx.execute(
                        "SELECT * FROM positions WHERE symbol=?", (symbol,)
                    ).fetchone()
                    holding = dict(holding_row) if holding_row else None
                    if not quote or not e._fresh(quote, now):
                        continue
                screen = research.timeline.screen(symbol, now)
                if holding:
                    opened = datetime.fromisoformat(holding["opened"]).astimezone(IST).date()
                    age = research.timeline.indices.get(key[0], -1) - research.timeline.indices.get(
                        opened, -100000
                    )
                    reason = (
                        "DAILY_SCREEN_EXIT"
                        if screen["status"] == "screened_out"
                        else "DAILY_HOLDING_LIMIT"
                        if opened in research.timeline.indices
                        and age >= profile.long_term.max_hold_sessions
                        else None
                    )
                    if reason:
                        d.offer(
                            None,
                            now,
                            {
                                "kind": "daily",
                                "holding": holding,
                                "screen": screen,
                                "reason": reason,
                                "signal_key": "daily-exit",
                            },
                            symbol=symbol,
                            side="SELL",
                        )
                    continue
                if screen["status"] != "research_candidate":
                    continue
                if datetime.fromisoformat(screen["last_session"]).date() >= key[0]:
                    continue
                gap = (quote.ask / D(screen["last_close"]) - 1) * 10000
                if abs(gap) > profile.long_term.max_entry_gap_bps:
                    continue
                stop = down(
                    quote.ask * (1 - profile.long_term.stop_pct / 100), eligible[symbol].tick_size
                )
                target = up(
                    quote.ask * (1 + profile.long_term.target_pct / 100), eligible[symbol].tick_size
                )
                if not 0 < stop < quote.bid <= quote.ask < target:
                    continue
                candidate = Candidate(
                    intent_id="desk-daily-"
                    + hashlib.sha256(f"{research.identity}:{key[0]}:{symbol}".encode()).hexdigest()[
                        :40
                    ],
                    symbol=symbol,
                    stop=stop,
                    target=target,
                    decision_time=now,
                    model_version=profile.long_term.version + ":" + profile.long_term.digest()[:12],
                    reason="Prior daily momentum/trend/liquidity screen; "
                    "fresh quote; delivery risk checks",
                )
                d.offer(
                    candidate,
                    now,
                    {
                        "kind": "daily",
                        "screen": screen,
                        "signal_key": "daily-entry",
                        "rank": row["rank"],
                    },
                )

    def intraday(self, now: datetime, selected: list[Instrument], revision: str) -> None:
        d, e, research = self.desk, self.desk.engine, self.desk.research
        assert research is not None
        boundary = now.replace(second=0, microsecond=0, minute=now.minute // 5 * 5)
        if boundary == self.boundary or self.attempt and now - self.attempt < timedelta(seconds=10):
            return
        bounds = e.calendar.bounds(now)
        if not bounds or boundary <= bounds[0]:
            return
        self.attempt = now
        candles = []
        # Official historical read quota: serialized requests spaced >=400 ms.
        for item in selected:
            if self.stop.is_set():
                return
            try:
                candles.extend(
                    self.setup.broker().get_historical_candles(item, bounds[0], boundary, 5, now)
                )
            except Exception:
                d.analysis_error = "INTRADAY_HISTORY_UNAVAILABLE"
                return
            if self.stop.wait(0.4):
                return
        observed = self.clock()
        with e.lock:
            if self.stop.is_set() or revision != d.revision or d.mode == "manual":
                return
            if d.blockers(observed):
                # A recovered history read may clear its own prior availability error.
                if d.analysis_error != "INTRADAY_HISTORY_UNAVAILABLE":
                    return
                d.analysis_error = None
                if d.blockers(observed):
                    return
            symbols = {item.symbol: item for item in selected}
            rules = RuleStrategy(research.profile.intraday, e.calendar)
            for candle in sorted(candles, key=lambda c: (c.start, c.symbol)):
                with e.db.transaction() as tx:
                    quote = e._quote(tx, candle.symbol)
                ranked = next(
                    (r for r in research.result["rows"] if r["symbol"] == candle.symbol), None
                )
                result = rules.evaluate(
                    candle,
                    now=observed,
                    quote=quote,
                    instrument=symbols[candle.symbol],
                    connected=e.connected,
                    entries_enabled=bool(
                        ranked
                        and ranked["status"] == "research_candidate"
                        and candle.start + timedelta(minutes=5) == boundary
                    ),
                )
                if result.candidate:
                    d.offer(
                        result.candidate,
                        observed,
                        {
                            "kind": "intraday",
                            "candle": candle.model_dump(mode="json"),
                            "features": result.features,
                            "rank": ranked["rank"] if ranked else None,
                            "signal_key": observed.astimezone(IST).date().isoformat(),
                        },
                    )
            self.boundary, d.last_analysis, d.analysis_error = boundary, stamp(observed), None
