"""Synthetic feed/history timing. No historical warmup may submit a paper instruction."""

import sqlite3
import threading
import time
from contextlib import closing
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

from trading_agent.desk.signals import AnalysisWorker
from trading_agent.market_data.repository import store_candles
from trading_agent.paper.demo import SIGNAL, WARM, demo_quote, signal_candle, warmup


def drain(worker, desk, clock, target=1):
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        worker.evaluate(clock[0])
        if getattr(desk, "intraday_status", {}).get("seeded") == target:
            return
        time.sleep(0.01)
    raise AssertionError("Warmup did not complete")


def money(engine):
    with closing(sqlite3.connect(engine.settings.database)) as db:
        return {
            k: Decimal(v)
            for k, v in db.execute(
                "SELECT key,value FROM meta WHERE key IN ('cash','fees','initial_cash')"
            )
        }


def test_slow_warmup_never_replays_and_new_live_bar_uses_fresh_clock_and_exact_fills(desk_factory):
    desk, _, _ = desk_factory()
    e = desk.engine
    clock = [WARM]
    e.ingest(demo_quote(WARM), WARM)
    desk.set_mode("automatic", WARM, desk.revision)
    began = threading.Event()
    release = threading.Event()
    calls = []

    def history(*args):
        calls.append(args)
        began.set()
        assert release.wait(3)
        return warmup()

    setup = SimpleNamespace(
        uses_persisted_candles=True,
        profile_revision=1,
        broker=lambda: SimpleNamespace(get_historical_candles=history),
    )
    worker = AnalysisWorker(desk, setup, lambda: clock[0])
    before = money(e)
    try:
        worker.evaluate(clock[0])
        assert began.wait(1)
        assert worker.live.thread.is_alive()
        # A six-second provider delay does not block evaluation or change finances.
        clock[0] = WARM + timedelta(seconds=6)
        e.ingest(demo_quote(clock[0], volume=29000), clock[0])
        worker.evaluate(clock[0])
        assert not e.orders() and money(e) == before
        release.set()
        drain(worker, desk, clock)
        assert not e.orders() and not desk.view(clock[0])["decisions"]
        assert money(e) == before
        assert len(calls) == 1
        clock[0] = SIGNAL
        e.ingest(demo_quote(SIGNAL, bid="501", volume=33000), SIGNAL)
        store_candles(e.db, [signal_candle()], SIGNAL)
        worker.evaluate(SIGNAL)
        assert len(calls) == 1, "No REST acquisition may delay a completed live-bar decision"
        decisions = desk.view(SIGNAL)["decisions"]
        assert len(decisions) == 1 and decisions[0]["state"] == "submitted"
        assert len(e.orders()) == 1 and e.orders()[0]["state"] == "ACCEPTED"
        worker.evaluate(SIGNAL)
        assert len(e.orders()) == 1
        later = SIGNAL + timedelta(seconds=1)
        e.ingest(demo_quote(later, bid="501", volume=34000), later)
        with closing(sqlite3.connect(e.settings.database)) as db:
            fills = db.execute("SELECT price,quantity,fees FROM fills").fetchall()
            assert fills
            debit = sum((Decimal(p) * q + Decimal(f) for p, q, f in fills), Decimal(0))
            assert money(e)["cash"] == Decimal("25000") - debit
            assert money(e)["fees"] == sum((Decimal(f) for _, _, f in fills), Decimal(0))
            assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    finally:
        release.set()
        worker.close()


def test_old_live_candle_does_not_bypass_five_second_freshness(desk_factory):
    desk, _, _ = desk_factory()
    e = desk.engine
    clock = [WARM]
    e.ingest(demo_quote(WARM), WARM)
    desk.set_mode("automatic", WARM, desk.revision)
    setup = SimpleNamespace(
        uses_persisted_candles=True,
        profile_revision=1,
        broker=lambda: SimpleNamespace(get_historical_candles=lambda *args: warmup()),
    )
    worker = AnalysisWorker(desk, setup, lambda: clock[0])
    try:
        drain(worker, desk, clock)
        clock[0] = SIGNAL + timedelta(seconds=6)
        e.ingest(demo_quote(clock[0], bid="501", volume=33000), clock[0])
        store_candles(e.db, [signal_candle()], clock[0])
        worker.evaluate(clock[0])
        assert not e.orders() and not desk.view(clock[0])["decisions"]
        detail = desk.intraday_status["symbols"][0]
        assert "STALE_CANDLE" in detail["reasons"]
        assert money(e)["cash"] == Decimal("25000")
    finally:
        worker.close()


def test_manual_mode_and_late_history_results_cannot_dispatch_old_signals(desk_factory):
    desk, _, _ = desk_factory()
    e = desk.engine
    clock = [WARM]
    e.ingest(demo_quote(WARM), WARM)
    desk.set_mode("automatic", WARM, desk.revision)
    began = threading.Event()
    release = threading.Event()

    def history(*args):
        began.set()
        assert release.wait(3)
        return warmup()

    setup = SimpleNamespace(
        uses_persisted_candles=True,
        profile_revision=1,
        broker=lambda: SimpleNamespace(get_historical_candles=history),
    )
    worker = AnalysisWorker(desk, setup, lambda: clock[0])
    try:
        worker.evaluate(clock[0])
        assert began.wait(1)
        desk.set_mode("manual", clock[0], desk.revision)
        release.set()
        drain(worker, desk, clock)
        clock[0] = SIGNAL
        e.ingest(demo_quote(SIGNAL, bid="501", volume=33000), SIGNAL)
        store_candles(e.db, [signal_candle()], SIGNAL)
        worker.evaluate(SIGNAL)
        assert desk.mode == "manual" and not e.orders() and not desk.view(SIGNAL)["decisions"]
        assert "ENTRIES_DISABLED" in desk.intraday_status["symbols"][0]["reasons"]
        assert money(e)["cash"] == Decimal("25000")
    finally:
        release.set()
        worker.close()


def test_bad_live_bar_requires_resynchronization_without_inventing_a_candle(desk_factory):
    desk, _, _ = desk_factory()
    e = desk.engine
    clock = [WARM]
    e.ingest(demo_quote(WARM), WARM)
    desk.set_mode("automatic", WARM, desk.revision)
    setup = SimpleNamespace(
        uses_persisted_candles=True,
        profile_revision=1,
        broker=lambda: SimpleNamespace(get_historical_candles=lambda *args: warmup()),
    )
    worker = AnalysisWorker(desk, setup, lambda: clock[0])
    try:
        drain(worker, desk, clock)
        clock[0] = SIGNAL
        e.ingest(demo_quote(SIGNAL, bid="501", volume=33000), SIGNAL)
        store_candles(
            e.db, [signal_candle().model_copy(update={"quality": "unknown_initial_volume"})], SIGNAL
        )
        worker.evaluate(SIGNAL)
        assert worker.live.last == {}
        assert not e.orders() and not desk.view(SIGNAL)["decisions"]
        assert money(e)["cash"] == Decimal("25000")
    finally:
        worker.close()


def test_incomplete_history_stays_blocked_and_retries_are_bounded_while_manual(desk_factory):
    desk, _, _ = desk_factory()
    e = desk.engine
    clock = [WARM]
    e.ingest(demo_quote(WARM), WARM)
    calls = []

    def incomplete(*args):
        calls.append(args)
        return warmup()[:-1]

    setup = SimpleNamespace(
        uses_persisted_candles=True,
        profile_revision=1,
        broker=lambda: SimpleNamespace(get_historical_candles=incomplete),
    )
    worker = AnalysisWorker(desk, setup, lambda: clock[0])
    try:
        with closing(sqlite3.connect(e.settings.database)) as db:
            before = list(db.iterdump())
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            worker.evaluate(clock[0])
            status = getattr(desk, "intraday_status", {})
            if status.get("symbols") and status["symbols"][0]["state"] == "history_unavailable":
                break
            time.sleep(0.01)
        assert desk.intraday_status["seeded"] == 0
        assert desk.intraday_status["symbols"][0]["reasons"] == ["HISTORY_WARMUP_INCOMPLETE"]
        assert desk.analysis_error == "INTRADAY_HISTORY_UNAVAILABLE"
        for _ in range(5):
            worker.evaluate(clock[0])
        assert len(calls) == 1 and desk.mode == "manual"
        with closing(sqlite3.connect(e.settings.database)) as db:
            assert list(db.iterdump()) == before
    finally:
        worker.close()
