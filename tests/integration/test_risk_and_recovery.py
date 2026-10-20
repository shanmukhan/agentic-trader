import sqlite3
from datetime import date, time, timedelta
from decimal import Decimal as D

import pytest
from conftest import NOW, candidate, quote
from unit.test_candles_features import candle

from trading_agent.execution.paper_broker import PaperBroker
from trading_agent.market_data.calendar import SessionCalendar
from trading_agent.market_data.repository import store_candles
from trading_agent.persistence.database import Database


@pytest.mark.parametrize(
    "changes,reason",
    [
        ({"stop": "501"}, "STOP_ALREADY_TRIGGERED"),
        ({"stop": "495.01"}, "INVALID_TICK_SIZE"),
        ({"requires_ml": True}, "MODEL_UNAVAILABLE"),
        ({"now": NOW - timedelta(seconds=6)}, "STALE_OR_FUTURE_DECISION"),
        ({"now": NOW + timedelta(seconds=1)}, "STALE_OR_FUTURE_DECISION"),
        ({"target": "499"}, "INVALID_STOP_OR_TARGET"),
    ],
)
def test_invalid_candidates(engine, changes, reason):
    order = engine.submit(candidate(**changes), NOW)
    assert order["state"] == "REJECTED" and reason in order["reason"]


def test_stale_and_out_of_order_market_data(engine):
    result = engine.submit(candidate(now=NOW + timedelta(seconds=6)), NOW + timedelta(seconds=6))
    assert "STALE_OR_MISSING_QUOTE" in result["reason"]
    assert not engine.ingest(quote(-1), NOW)
    result = engine.submit(candidate("bad-data"), NOW)
    assert "STALE_OR_MISSING_QUOTE" in result["reason"]
    engine.ingest(quote(1), NOW + timedelta(seconds=1))
    assert (
        engine.submit(
            candidate("recovered", now=NOW + timedelta(seconds=1)), NOW + timedelta(seconds=1)
        )["state"]
        == "ACCEPTED"
    )


def test_volume_regression_and_mapping_mismatch(engine):
    assert not engine.ingest(quote(1, volume=999), NOW + timedelta(seconds=1))
    with pytest.raises(ValueError):
        engine.ingest(quote(1, token=99), NOW + timedelta(seconds=1))
    with pytest.raises(ValueError):
        engine.ingest(quote(1, bid="499.94"), NOW + timedelta(seconds=1))


def test_session_calendar_and_entry_boundaries(engine):
    engine.calendar = SessionCalendar({})
    assert "UNKNOWN_OR_CLOSED_SESSION" in engine.submit(candidate(), NOW)["reason"]
    engine.calendar = SessionCalendar({date(2026, 10, 20): (time(9, 15), time(10, 10))})
    assert "EARLY_CLOSE_CUTOFF" in engine.submit(candidate("early"), NOW)["reason"]
    engine.calendar = SessionCalendar({date(2026, 10, 20): (time(9, 15), time(15, 30))})
    late = NOW.replace(hour=9, minute=0)  # 14:30 IST, end is exclusive
    engine.ingest(quote(base=late), late)
    assert "OUTSIDE_ENTRY_WINDOW" in engine.submit(candidate("late", now=late), late)["reason"]


def test_position_count_and_total_exposure_reservations(engine_factory):
    engine = engine_factory(max_trade_risk=D(200), daily_loss_limit=D(500))
    engine.ingest(quote(symbol="NSE:SECOND", token=2), NOW)
    engine.ingest(quote(symbol="NSE:THIRD", token=3), NOW)
    for identity, symbol in (("first", "NSE:DEMO"), ("second", "NSE:SECOND")):
        assert engine.submit(candidate(identity, symbol=symbol), NOW)["state"] == "ACCEPTED"
    assert "POSITION_LIMIT" in engine.submit(candidate("third", symbol="NSE:THIRD"), NOW)["reason"]
    state = engine.snapshot(NOW)
    assert D(state["exposure"]) <= 20000 and D(state["reserved_cash"]) <= 25000


def test_daily_unrealized_loss_persistently_kills(engine_factory):
    engine = engine_factory(daily_loss_limit=D(70))
    engine.submit(candidate(), NOW)
    engine.ingest(quote(1), NOW + timedelta(seconds=1))
    engine.ingest(quote(2, bid="490", ask="490.05"), NOW + timedelta(seconds=2))
    state = engine.snapshot(NOW + timedelta(seconds=2))
    assert state["kill"] and state["kill_reason"] == "DAILY_LOSS_LIMIT"
    engine.ingest(quote(3, bid="490", ask="490.05"), NOW + timedelta(seconds=3))
    with pytest.raises(ValueError, match="daily loss"):
        engine.reset_kill(NOW + timedelta(seconds=3))


def test_loss_streak_and_day_reset(engine_factory):
    engine = engine_factory(max_consecutive_losses=1)
    engine.submit(candidate(), NOW)
    engine.ingest(quote(1), NOW + timedelta(seconds=1))
    engine.flatten(NOW + timedelta(seconds=2))
    engine.ingest(quote(3), NOW + timedelta(seconds=3))
    with pytest.raises(ValueError, match="loss streak"):
        engine.reset_kill(NOW + timedelta(seconds=3))
    engine.reset_kill(NOW + timedelta(days=1))
    assert engine.snapshot(NOW + timedelta(days=1))["loss_streak"] == 0


def test_watchdog_session_flatten_and_overnight_block(engine):
    engine.submit(candidate(), NOW)
    engine.ingest(quote(1), NOW + timedelta(seconds=1))
    close = NOW.replace(hour=9, minute=45)  # 15:15 IST
    engine.poll(close)
    assert engine.orders()[-1]["side"] == "SELL"
    assert engine.snapshot(close)["positions"]  # no synthetic wall-clock fill
    engine.poll(NOW + timedelta(days=1))
    assert engine.snapshot(NOW + timedelta(days=1))["kill_reason"] == "OVERNIGHT_POSITION"


def test_restart_reconciles_and_kill_survives(engine):
    engine.submit(candidate(), NOW)
    engine.ingest(quote(1, ask_size=3), NOW + timedelta(seconds=1))
    engine.kill(NOW + timedelta(seconds=2))
    settings, calendar = engine.settings, engine.calendar
    engine.db.close()
    db = Database(settings.database, settings.starting_cash)
    try:
        recovered = PaperBroker(db, settings, calendar)
        state = recovered.snapshot(NOW + timedelta(seconds=2))
        assert state["kill"] and state["positions"][0]["quantity"] == 3
        assert not state["feed_connected"]
        assert not any(row["state"] in ("ACCEPTED", "PARTIAL") for row in recovered.orders())
        recovered.poll(NOW + timedelta(seconds=3))
        assert recovered.orders()[-1]["side"] == "SELL"
    finally:
        db.close()


def test_atomic_rollback_on_disk_full(engine, monkeypatch):
    engine.submit(candidate(), NOW)
    original = engine._fill

    def fail_after_fill(*args, **kwargs):
        original(*args, **kwargs)
        raise sqlite3.OperationalError("database or disk is full")

    monkeypatch.setattr(engine, "_fill", fail_after_fill)
    with pytest.raises(sqlite3.OperationalError):
        engine.ingest(quote(1), NOW + timedelta(seconds=1))
    assert engine.faulted and not engine.connected
    state = engine.snapshot(NOW)
    assert state["cash"] == "25000" and not state["positions"]
    assert engine.orders()[0]["state"] == "ACCEPTED"
    with engine.db.transaction() as tx:
        assert tx.execute("SELECT COUNT(*) FROM fills").fetchone()[0] == 0
        engine.db.reconcile(tx)


def test_backup_restores_cash_positions_and_detects_corruption(engine, tmp_path):
    engine.submit(candidate(), NOW)
    engine.ingest(quote(1), NOW + timedelta(seconds=1))
    backup = tmp_path / "backup.db"
    engine.db.backup(backup)
    restored = Database(backup, engine.settings.starting_cash)
    try:
        with restored.transaction() as tx:
            assert tx.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            restored.reconcile(tx)
    finally:
        restored.close()
    with sqlite3.connect(backup) as tx:
        tx.execute("UPDATE meta SET value='999' WHERE key='cash'")
    tx.close()
    with pytest.raises(RuntimeError, match="reconciliation"):
        Database(backup, engine.settings.starting_cash)


def test_exclusive_owner_and_policy_changes(engine):
    with pytest.raises(RuntimeError, match="owned"):
        Database(engine.settings.database, engine.settings.starting_cash)
    changed = engine.settings.model_copy(update={"max_trade_risk": D(63)})
    with pytest.raises(ValueError, match="policy changed"):
        PaperBroker(engine.db, changed, engine.calendar)


def test_candle_ingestion_idempotent_and_future_rejected(engine):
    value = candle()
    assert store_candles(engine.db, [value], NOW + timedelta(minutes=5)) == 1
    assert store_candles(engine.db, [value], NOW + timedelta(minutes=5)) == 0
    with pytest.raises(ValueError):
        store_candles(engine.db, [value], NOW)
    with pytest.raises(ValueError):
        store_candles(
            engine.db, [value.model_copy(update={"close": D(103)})], NOW + timedelta(minutes=5)
        )
