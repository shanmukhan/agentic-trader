"""Invented account evidence only. Added without running at the operator's request."""

import json
import sqlite3
from datetime import timedelta
from decimal import Decimal as D

import pytest
from conftest import NOW, candidate, quote

from trading_agent.execution.paper_broker import PaperBroker
from trading_agent.risk.operator_safety import KEY


def permit(engine):
    engine.safety.enable(NOW)
    with engine.lock, engine.db.transaction() as tx:
        revision = engine.safety.state(tx)["revision"]
        engine.safety.replace(tx, ["NSE:DEMO"], revision, NOW)


def persisted(engine):
    with sqlite3.connect(engine.settings.database) as tx:
        return json.loads(tx.execute("SELECT value FROM meta WHERE key=?", (KEY,)).fetchone()[0])


def test_watchlist_empty_unknown_and_restart_fail_closed(engine):
    engine.safety.enable(NOW)
    denied = engine.submit(candidate(), NOW)
    assert denied["state"] == "REJECTED"
    assert "WATCHLIST_EMPTY" in denied["reason"]
    assert "SYMBOL_OUTSIDE_WATCHLIST" in denied["reason"]
    permit(engine)
    recovered = PaperBroker(engine.db, engine.settings, engine.calendar, recovery_time=NOW)
    recovered.safety.enable(NOW)
    assert persisted(engine)["symbols"] == ["NSE:DEMO"]
    with recovered.db.transaction() as tx:
        assert recovered.safety.allows(tx, "NSE:DEMO")
        assert not recovered.safety.allows(tx, "NSE:SECOND")
        recovered.db.set(tx, KEY, "invalid JSON")
    with pytest.raises(RuntimeError, match="invalid durable"):
        recovered.submit(candidate("corrupt"), NOW)
    assert recovered.faulted


def test_order_cost_includes_fees_and_never_exceeds_quarter_of_equity(engine_factory):
    engine = engine_factory(max_trade_risk=D("250"), daily_loss_limit=D("500"))
    permit(engine)
    before = D(engine.snapshot(NOW)["equity"])
    order = engine.submit(candidate(stop="490", target="550"), NOW)
    assert order["state"] == "ACCEPTED" and order["quantity"] == 12
    assert D(order["reserved_cash"]) <= before / 4
    engine.ingest(quote(1), NOW + timedelta(seconds=1))
    with sqlite3.connect(engine.settings.database) as tx:
        cost, cash = tx.execute(
            "SELECT cost,(SELECT value FROM meta WHERE key='cash') FROM positions"
        ).fetchone()
        fills = tx.execute("SELECT quantity,price,fees FROM fills").fetchall()
    independently_costed = sum((D(q) * D(price) + D(fee) for q, price, fee in fills), D(0))
    assert D(cost) == independently_costed <= before / 4
    assert D(cash) == before - independently_costed >= 0


def test_fifth_entry_can_fill_but_sixth_is_rejected_and_retries_do_not_count(engine):
    permit(engine)
    for index in range(5):
        intent = candidate(f"slot-{index}")
        order = engine.submit(intent, NOW)
        assert order["state"] == "ACCEPTED"
        assert engine.submit(intent, NOW)["id"] == order["id"]
        if index < 4:
            engine.cancel(order["id"], NOW)
    assert "DAILY_TRADE_LIMIT" in engine.submit(candidate("sixth"), NOW)["reason"]
    engine.ingest(quote(1), NOW + timedelta(seconds=1))
    with sqlite3.connect(engine.settings.database) as tx:
        assert tx.execute("SELECT filled,state FROM orders WHERE id='slot-4'").fetchone() == (
            10,
            "FILLED",
        )
        assert (
            tx.execute("SELECT count(*) FROM orders WHERE side='BUY' AND quantity>0").fetchone()[0]
            == 5
        )


def test_drawdown_boundary_is_persistent_and_requires_explicit_reference_reset(engine):
    permit(engine)
    with engine.lock, engine.db.transaction() as tx:
        engine.safety.observe(tx, NOW, {"equity": "18750.01", "valuation_fresh": True})
        assert not engine.safety.state(tx)["paused"]
        engine.safety.observe(tx, NOW, {"equity": "18750", "valuation_fresh": True})
    state = persisted(engine)
    assert state["paused"] and state["peak_equity"] == "25000"
    with engine.lock, engine.db.transaction() as tx:
        engine.safety.observe(tx, NOW, {"equity": "26000", "valuation_fresh": True})
        assert engine.safety.state(tx)["paused"]
        engine.safety.block_data(tx, NOW, "INVENTED_BAD_PRICE")
        revision = engine.safety.state(tx)["revision"]
        with pytest.raises(ValueError, match="changed"):
            engine.safety.resume(tx, revision - 1, NOW)
        engine.safety.resume(tx, revision, NOW)
        assert "DATA_QUALITY_DAY_BLOCK" in engine.safety.reasons(tx, NOW)
    assert not persisted(engine)["paused"]
    with sqlite3.connect(engine.settings.database) as tx:
        assert tx.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0] == "25000"
        assert tx.execute("SELECT count(*) FROM fills").fetchone()[0] == 0


def test_invalid_frame_locks_day_after_rollback_and_valid_prices_cannot_clear_it(engine):
    permit(engine)
    with pytest.raises(ValueError, match="tick size"):
        engine.ingest(quote(1, ask="500.01"), NOW + timedelta(seconds=1))
    engine.ingest(quote(2), NOW + timedelta(seconds=2))
    assert (
        "DATA_QUALITY_DAY_BLOCK"
        in engine.submit(
            candidate("after-data", now=NOW + timedelta(seconds=2)), NOW + timedelta(seconds=2)
        )["reason"]
    )
    assert persisted(engine)["blocked_day"] == "2026-10-20"
    tomorrow = NOW + timedelta(days=1)
    engine.ingest(quote(base=tomorrow), tomorrow)
    assert engine.submit(candidate("next-day", now=tomorrow), tomorrow)["state"] == "ACCEPTED"


def test_missing_safety_record_cannot_be_silently_reinitialized(engine):
    permit(engine)
    with engine.db.transaction() as tx:
        tx.execute("DELETE FROM meta WHERE key=?", (KEY,))
    with pytest.raises(RuntimeError, match="missing durable"):
        engine.safety.enable(NOW)
