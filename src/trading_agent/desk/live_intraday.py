"""Warm historical indicators off the decision path; evaluate only new live candles.

Official history seeds state with entries disabled. It can never replay a missed buy.
Completed, quality-checked stream candles and fresh quotes retain all existing gates.
"""

import queue
import threading
from datetime import datetime, timedelta
from typing import Any

from trading_agent.market_data.calendar import IST
from trading_agent.models import Candle, stamp
from trading_agent.strategy.rules import RuleStrategy


class LiveIntraday:
    def __init__(self, desk: Any, setup: Any, clock: Any, stop: threading.Event):
        self.desk, self.setup, self.clock, self.stop = desk, setup, clock, stop
        self.jobs: queue.Queue = queue.Queue(maxsize=500)
        self.results: queue.Queue = queue.Queue(maxsize=500)
        self.thread: threading.Thread | None = None
        self.context: Any = None
        self.pending: set[str] = set()
        self.last: dict[str, datetime] = {}
        self.retry: dict[str, datetime] = {}
        self.details: dict[str, dict[str, Any]] = {}
        self.rules: RuleStrategy | None = None

    def close(self) -> None:
        if self.thread:
            self.thread.join(timeout=12)

    def _read(self) -> None:
        while not self.stop.is_set():
            try:
                context, item, start, end, as_of = self.jobs.get(timeout=0.2)
            except queue.Empty:
                continue
            if context != self.context:
                continue
            result: tuple[Any, str, list[Candle], str | None]
            try:
                bars = self.setup.broker().get_historical_candles(item, start, end, 5, as_of)
                if not bars or bars[-1].start + timedelta(minutes=5) != end:
                    result = context, item.symbol, [], "HISTORY_WARMUP_INCOMPLETE"
                else:
                    result = context, item.symbol, bars, None
            except Exception:
                result = context, item.symbol, [], "HISTORY_WARMUP_UNAVAILABLE"
            while not self.stop.is_set() and context == self.context:
                try:
                    self.results.put(result, timeout=0.2)
                    break
                except queue.Full:
                    continue

    @staticmethod
    def _drain(values: queue.Queue) -> None:
        while True:
            try:
                values.get_nowait()
            except queue.Empty:
                return

    def _schedule(self, item: Any, start: datetime, boundary: datetime, now: datetime) -> None:
        if item.symbol in self.pending or self.retry.get(item.symbol, now) > now:
            return
        if boundary <= start:
            return
        try:
            self.jobs.put_nowait((self.context, item, start, boundary, now))
        except queue.Full:
            return
        self.pending.add(item.symbol)
        self.details[item.symbol] = {
            "symbol": item.symbol,
            "state": "warming_up",
            "reasons": ["HISTORY_WARMUP"],
        }

    def evaluate(
        self, now: datetime, selected: list[Any], revision: str, *, allow_entries: bool = True
    ) -> None:
        d, e, research = self.desk, self.desk.engine, self.desk.research
        if research is None:
            return
        bounds = e.calendar.bounds(now)
        if not bounds:
            return
        boundary = now.replace(second=0, microsecond=0, minute=now.minute // 5 * 5)
        context = (
            bounds[0],
            revision,
            research.identity,
            tuple(i.token for i in selected),
            self.setup.profile_revision,
        )
        if context != self.context:
            self.context = context
            self._drain(self.jobs)
            self._drain(self.results)
            self.pending.clear()
            self.last.clear()
            self.retry.clear()
            self.details.clear()
            self.rules = RuleStrategy(research.profile.intraday, e.calendar)
        if self.thread is None:
            self.thread = threading.Thread(
                target=self._read, name="intraday-history-warmup", daemon=True
            )
            self.thread.start()
        assert self.rules is not None
        instruments = {i.symbol: i for i in selected}
        while True:
            try:
                generation, symbol, bars, error = self.results.get_nowait()
            except queue.Empty:
                break
            if generation != self.context or symbol not in instruments:
                continue
            self.pending.discard(symbol)
            try:
                if (
                    error
                    or not bars
                    or bars[0].start != bounds[0]
                    or any(b.quality != "ok" for b in bars)
                ):
                    raise ValueError("history unavailable")
                self.rules.states.pop(symbol, None)
                for bar in bars:
                    self.rules.evaluate(
                        bar,
                        now=self.clock(),
                        quote=None,
                        instrument=instruments[symbol],
                        connected=e.connected,
                        entries_enabled=False,
                    )
                self.last[symbol] = bars[-1].start
                self.details[symbol] = {
                    "symbol": symbol,
                    "state": "waiting_live_candle",
                    "reasons": ["WAITING_NEW_LIVE_CANDLE"],
                }
            except Exception:
                self.last.pop(symbol, None)
                self.retry[symbol] = now + timedelta(seconds=30)
                self.details[symbol] = {
                    "symbol": symbol,
                    "state": "history_unavailable",
                    "reasons": [error or "HISTORY_WARMUP_INVALID"],
                }
        for item in selected:
            if item.symbol not in self.last:
                self._schedule(item, bounds[0], boundary, now)
        # The feed already persists completed 5m bars. No REST acquisition is in this path.
        with e.db.read_snapshot() as tx:
            rows = list(
                tx.execute(
                    "SELECT symbol,start,payload FROM candles WHERE minutes=5 AND start>=? "
                    "ORDER BY start,symbol",
                    (stamp(bounds[0]),),
                )
            )
        for row in rows:
            symbol = row[0]
            if symbol not in self.last or symbol not in instruments:
                continue
            bar = Candle.model_validate_json(row[2])
            if bar.start <= self.last[symbol]:
                continue
            if bar.quality != "ok" or bar.start != self.last[symbol] + timedelta(minutes=5):
                self.last.pop(symbol, None)
                self._schedule(instruments[symbol], bounds[0], boundary, self.clock())
                continue
            observed = self.clock()
            with e.lock, e.db.transaction() as tx:
                quote = e._quote(tx, symbol)
            ranked = next((r for r in research.result["rows"] if r["symbol"] == symbol), None)
            result = self.rules.evaluate(
                bar,
                now=observed,
                quote=quote,
                instrument=instruments[symbol],
                connected=e.connected,
                entries_enabled=bool(
                    allow_entries
                    and ranked
                    and ranked["status"] == "research_candidate"
                    and bar.start + timedelta(minutes=5) == boundary
                ),
            )
            self.last[symbol] = bar.start
            self.details[symbol] = {
                "symbol": symbol,
                "state": "evaluated",
                "evaluated_at": stamp(observed),
                "candle_end": stamp(result.candle_end),
                "reasons": list(result.reasons),
                "candidate": result.candidate is not None,
            }
            if result.candidate:
                with e.lock:
                    current = self.clock()
                    if revision != d.revision or d.mode == "manual" or d.blockers(current):
                        continue
                    d.offer(
                        result.candidate,
                        current,
                        {
                            "kind": "intraday",
                            "candle": bar.model_dump(mode="json"),
                            "features": result.features,
                            "rank": ranked["rank"] if ranked else None,
                            "signal_key": observed.astimezone(IST).date().isoformat(),
                        },
                    )
        if (
            selected
            and not self.last
            and any(row.get("state") == "history_unavailable" for row in self.details.values())
        ):
            d.analysis_error = "INTRADAY_HISTORY_UNAVAILABLE"
        elif self.last and d.analysis_error == "INTRADAY_HISTORY_UNAVAILABLE":
            d.analysis_error = None
        explanations = {
            "HISTORY_WARMUP": "Loading indicator history; old purchases are never replayed.",
            "WAITING_NEW_LIVE_CANDLE": "History ready; waiting for a newly completed live candle.",
            "HISTORY_WARMUP_UNAVAILABLE": "History unavailable; check broker access.",
            "HISTORY_WARMUP_INCOMPLETE": "Waiting for complete indicator seed history.",
            "HISTORY_WARMUP_INVALID": "History is incomplete or invalid; this stock stays blocked.",
            "WARMUP": "More completed candles are needed for indicator warm-up.",
            "STALE_CANDLE": "The candle arrived after the five-second decision limit.",
            "TREND_FILTER": "The required trend conditions are not met.",
            "RELATIVE_VOLUME_FILTER": "Trading volume is below the strategy threshold.",
            "TURNOVER_FILTER": "Candle volume or turnover is below the strategy threshold.",
            "NO_OPENING_RANGE_CROSS": "Price has not made the required opening-range crossing.",
            "STALE_OR_MISSING_QUOTE": "A fresh usable quote is still needed.",
            "ENTRIES_DISABLED": "This stock is not currently eligible for new strategy entries.",
            "DATA_GAP_OR_QUALITY": "A data gap or quality issue prevents a reliable signal.",
        }
        for detail in self.details.values():
            detail["explanation"] = (
                " ".join(
                    explanations.get(code, code.replace("_", " ").capitalize())
                    for code in detail.get("reasons", [])
                )
                or "Candidate signal produced; independent execution and risk checks still apply."
            )
        d.intraday_status = {
            "source": "completed_live_candles",
            "checked_at": stamp(self.clock()),
            "tracked": len(selected),
            "seeded": len(self.last),
            "warming_up": len(self.pending),
            "symbols": [
                self.details.get(
                    i.symbol,
                    {"symbol": i.symbol, "state": "waiting_history", "reasons": ["HISTORY_WARMUP"]},
                )
                for i in selected
            ],
            "history_does_not_replay_entries": True,
        }
