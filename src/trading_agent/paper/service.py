"""History I/O is outside the quote/risk lock. Only the feed owns subscription I/O."""

import logging
import threading
from collections.abc import Callable
from datetime import datetime, timedelta
from time import perf_counter, perf_counter_ns
from typing import Any

from trading_agent.broker.readonly_kite import QuoteStream, ReadOnlyKite
from trading_agent.models import Quote
from trading_agent.paper.runtime import PaperFeed


class PaperService:
    def __init__(self, runtime: PaperFeed, broker: ReadOnlyKite, clock: Callable[[], datetime]):
        self.runtime, self.broker, self.clock = runtime, broker, clock
        self.stop = threading.Event()
        self.thread: threading.Thread | None = None
        self.loaded_boundary: datetime | None = None
        self.last_attempt: datetime | None = None
        self.next_request = 0.0
        self.stream: Any = QuoteStream(
            list(runtime.catalog.values()),
            self.quote,
            self.connection,
            clock,
            on_unusable=self.unusable,
            stream_limit=runtime.engine.settings.stream_limit,
        )

    def unusable(self, symbol: str) -> None:
        with self.runtime.engine.lock:
            if self.stop.is_set() or self.runtime.closed:
                return
            self.runtime.engine.invalidate_quote(symbol)
            self.runtime.tick(self.clock())

    def quote(self, quote: Quote) -> None:
        began = perf_counter_ns()
        with self.runtime.engine.lock:
            if self.stop.is_set():
                return
            try:
                self.runtime.on_quote(quote, self.clock())
            finally:
                self.runtime.timings.observe("feed_callback", (perf_counter_ns() - began) / 1e6)

    def connection(self, connected: bool) -> None:
        with self.runtime.engine.lock:
            if self.runtime.closed:
                return
            self.runtime.connection(
                connected and not self.stop.is_set(), self.clock(), shutdown=self.stop.is_set()
            )
            if not connected:
                self.loaded_boundary = None

    def refresh_history(self) -> bool:
        """One bounded attempt, also callable synchronously for deterministic testing."""
        with self.runtime.engine.lock:
            now = self.clock()
            engine = self.runtime.engine
            if (
                self.stop.is_set()
                or engine.faulted
                or not engine.connected
                or not engine.calendar.is_open(now)
            ):
                return False
            boundary = now.replace(second=0, microsecond=0, minute=now.minute // 5 * 5)
            bounds = engine.calendar.bounds(now)
            assert bounds is not None
            if boundary <= bounds[0] or self.loaded_boundary == boundary:
                return False
            if (
                self.last_attempt
                and (now - self.last_attempt).total_seconds()
                < self.runtime.settings.history_retry_seconds
            ):
                return False
            self.last_attempt = now
            # Detect reconnects occurring while HTTP calls are in flight.
            generation = self.runtime.counts["connection_generation"]
        began = perf_counter_ns()
        candles = []
        try:
            for instrument in self.runtime.catalog.values():
                delay = max(0.0, self.next_request - perf_counter())
                if self.stop.wait(delay):
                    return False
                self.next_request = perf_counter() + self.runtime.settings.history_spacing_ms / 1000
                candles.extend(
                    self.broker.get_historical_candles(instrument, bounds[0], boundary, 5, now)
                )
            with engine.lock:
                if (
                    self.stop.is_set()
                    or not engine.connected
                    or generation != self.runtime.counts["connection_generation"]
                ):
                    return False
                observed = self.clock()
                # A fixed boundary must be complete for the entire reviewed universe.
                expected = int((boundary - bounds[0]).total_seconds() / 300)
                for symbol in self.runtime.catalog:
                    bars = [c for c in candles if c.symbol == symbol]
                    if len(bars) != expected or {c.start for c in bars} != {
                        bounds[0] + timedelta(minutes=5 * i) for i in range(expected)
                    }:
                        raise ValueError("incomplete historical session response")
                self.runtime.on_candles(candles, observed)
                self.loaded_boundary = boundary
                return True
        except Exception:
            with engine.lock:
                if not self.stop.is_set() and not engine.faulted:
                    self.runtime.history_failed(self.clock())
            logging.getLogger(__name__).error("paper history refresh failed; automation disarmed")
            return False
        finally:
            with engine.lock:
                self.runtime.timings.observe("history_fetch", (perf_counter_ns() - began) / 1e6)

    def _history(self) -> None:
        while not self.stop.is_set():
            try:
                self.refresh_history()
            except Exception:
                with self.runtime.engine.lock:
                    if not self.stop.is_set():
                        self.runtime.fail(self.clock())
                logging.getLogger(__name__).error("paper history worker failed; entries blocked")
            self.stop.wait(1)

    def start(self) -> None:
        if self.thread is not None:
            raise RuntimeError("paper service already started")
        self.thread = threading.Thread(target=self._history, name="paper-history", daemon=True)
        self.thread.start()
        try:
            self.stream.start()
        except BaseException:
            self.close()
            raise

    def close(self) -> None:
        self.stop.set()
        self.stream.close()
        if self.thread:
            # Each history request is bounded by the read-only HTTP timeout.
            # The worker checks stop between requests; at most one request remains.
            self.thread.join(timeout=12)
            if self.thread.is_alive():
                raise RuntimeError("history worker did not stop; keep account storage open")
        with self.runtime.engine.lock:
            self.runtime.close(self.clock())
