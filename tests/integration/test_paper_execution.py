from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from decimal import Decimal as D

import pytest
from conftest import NOW, candidate, quote

from trading_agent.execution.paper_broker import IntentConflict


def test_reserved_then_partial_then_filled_and_flat(engine):
    order = engine.submit(candidate(), NOW)
    assert order["state"] == "ACCEPTED" and order["quantity"] == 10
    assert engine.snapshot(NOW)["positions"] == []
    assert D(engine.snapshot(NOW)["reserved_cash"]) > 5000
    engine.ingest(quote(1, ask_size=3), NOW + timedelta(seconds=1))
    assert engine.orders()[0]["state"] == "PARTIAL"
    assert engine.snapshot(NOW + timedelta(seconds=1))["positions"][0]["quantity"] == 3
    engine.ingest(quote(2), NOW + timedelta(seconds=2))
    assert engine.orders()[0]["state"] == "FILLED"
    engine.flatten(NOW + timedelta(seconds=2))
    engine.ingest(quote(3, bid_size=4), NOW + timedelta(seconds=3))
    assert engine.snapshot(NOW + timedelta(seconds=3))["positions"][0]["quantity"] == 6
    engine.ingest(quote(4), NOW + timedelta(seconds=4))
    state = engine.snapshot(NOW + timedelta(seconds=4))
    assert state["positions"] == [] and state["reserved_cash"] == "0"
    assert D(state["cash"]) < 25000 and state["loss_streak"] == 1
    assert state["kill"]
    with engine.db.transaction() as tx:
        engine.db.reconcile(tx)
        fee = D(tx.execute("SELECT fees FROM orders WHERE side='BUY'").fetchone()[0])
        assert fee == engine.charges.fee("BUY", D("5002.50"))


def test_duplicate_intents_and_ticks_do_not_duplicate_money(engine):
    first = engine.submit(candidate(), NOW)
    assert engine.submit(candidate(), NOW) == first
    with pytest.raises(IntentConflict):
        engine.submit(candidate(target="520"), NOW)
    engine.ingest(quote(1), NOW + timedelta(seconds=1))
    before = engine.snapshot(NOW + timedelta(seconds=1))
    assert not engine.ingest(quote(1), NOW + timedelta(seconds=1))
    assert engine.snapshot(NOW + timedelta(seconds=1)) == before


def test_equivalent_decimal_formats_and_timezones_share_intent(engine):
    from zoneinfo import ZoneInfo

    first = engine.submit(candidate(), NOW)
    alternate = candidate(
        stop="495.0000", target="510.00", now=NOW.astimezone(ZoneInfo("Asia/Kolkata"))
    )
    assert engine.submit(alternate, NOW) == first


def test_parallel_submissions_cannot_oversubscribe(engine):
    with ThreadPoolExecutor(max_workers=8) as pool:
        orders = list(pool.map(lambda i: engine.submit(candidate(f"entry{i}"), NOW), range(20)))
    assert sum(order["state"] == "ACCEPTED" for order in orders) == 1


@pytest.mark.parametrize(
    "delta,bid,ask,reason",
    [
        (1, "500.95", "501", "PRICE_CAP_EXCEEDED"),
        (1, "490", "490.05", "STOP_OR_TARGET_BEFORE_FILL"),
        (31, "499.95", "500", "EXPIRED_OR_SESSION_END"),
    ],
)
def test_unfillable_entry_cancelled(engine, delta, bid, ask, reason):
    engine.submit(candidate(), NOW)
    engine.ingest(quote(delta, bid=bid, ask=ask), NOW + timedelta(seconds=delta))
    order = engine.orders()[0]
    assert order["state"] == "CANCELLED" and order["reason"] == reason
    assert engine.snapshot(NOW + timedelta(seconds=delta))["cash"] == "25000"


def test_cancel_idempotent_and_stop_gap_fills_at_bid(engine):
    engine.submit(candidate("cancelled"), NOW)
    assert engine.cancel("cancelled", NOW)["state"] == "CANCELLED"
    assert engine.cancel("cancelled", NOW)["state"] == "CANCELLED"
    engine.submit(candidate(), NOW)
    engine.ingest(quote(1), NOW + timedelta(seconds=1))
    engine.ingest(quote(2, bid="480", ask="480.05"), NOW + timedelta(seconds=2))
    assert engine.snapshot(NOW + timedelta(seconds=2))["positions"]
    engine.ingest(quote(3, bid="479", ask="479.05"), NOW + timedelta(seconds=3))
    state = engine.snapshot(NOW + timedelta(seconds=3))
    assert not state["positions"] and D(state["realized_pnl"]) < -200
    with engine.db.transaction() as tx:
        price = D(tx.execute("SELECT price FROM fills ORDER BY seq DESC LIMIT 1").fetchone()[0])
        assert price < D(479)


def test_no_fill_on_same_quote_latency_or_disconnected_feed(engine):
    engine.submit(candidate(), NOW)
    assert not engine.ingest(quote(), NOW)
    engine.set_connected(False)
    engine.ingest(quote(1), NOW + timedelta(seconds=1))
    assert not engine.snapshot(NOW + timedelta(seconds=1))["positions"]
    engine.set_connected(True)
    assert (
        "STALE_OR_MISSING_QUOTE"
        in engine.submit(
            candidate("reconnect", now=NOW + timedelta(seconds=1)), NOW + timedelta(seconds=1)
        )["reason"]
    )


def test_kill_blocks_entries_and_waits_for_liquidity_to_flatten(engine):
    engine.submit(candidate(), NOW)
    engine.ingest(quote(1), NOW + timedelta(seconds=1))
    engine.kill(NOW + timedelta(seconds=2))
    assert (
        engine.submit(
            candidate("after-kill", now=NOW + timedelta(seconds=2)), NOW + timedelta(seconds=2)
        )["state"]
        == "REJECTED"
    )
    engine.ingest(quote(3, bid_size=0), NOW + timedelta(seconds=3))
    assert engine.snapshot(NOW + timedelta(seconds=3))["positions"]
    with pytest.raises(ValueError):
        engine.reset_kill(NOW + timedelta(seconds=3))
    engine.ingest(quote(4), NOW + timedelta(seconds=4))
    engine.reset_kill(NOW + timedelta(seconds=4))
    assert not engine.snapshot(NOW + timedelta(seconds=4))["kill"]


def test_zero_latency_still_requires_a_strictly_later_exchange_quote(engine_factory):
    engine = engine_factory(latency_ms=0)
    decision = NOW + timedelta(seconds=1)
    engine.submit(candidate(now=decision), decision)
    engine.ingest(quote(1), decision)
    assert not engine.snapshot(decision)["positions"]
    engine.ingest(quote(2), NOW + timedelta(seconds=2))
    assert engine.snapshot(NOW + timedelta(seconds=2))["positions"]
