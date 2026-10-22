import sqlite3
from datetime import timedelta
from decimal import Decimal as D

import pytest
from conftest import NOW, candidate, quote

from trading_agent.market_data.candles import CandleBuilder
from trading_agent.persistence.database import Database


def kite(second=0, **kwargs):
    return quote(second, **kwargs).model_copy(update={"source": "kite"})


def persisted(engine):
    with sqlite3.connect(engine.settings.database) as db:
        return list(db.iterdump())


def test_unchanged_repeat_does_not_invalidate_or_renew_quote_or_clear_a_quality_failure(engine):
    before = persisted(engine)
    repeat = quote().model_copy(update={"received_time": NOW + timedelta(milliseconds=200)})
    assert not engine.ingest(repeat, repeat.received_time)
    assert engine._fresh(quote(), repeat.received_time)
    assert persisted(engine) == before
    late = repeat.model_copy(update={"received_time": NOW + timedelta(seconds=6)})
    assert not engine.ingest(late, late.received_time)
    assert not engine._fresh(quote(), late.received_time)
    engine.invalidate_quote("NSE:DEMO")
    assert not engine.ingest(repeat, repeat.received_time)
    assert not engine._fresh(quote(), repeat.received_time)
    assert persisted(engine) == before


def test_ordered_kite_books_share_a_second_without_reusing_fill_liquidity(engine_factory):
    e = engine_factory(max_trade_risk=D(250), daily_loss_limit=D(500))
    assert e.ingest(kite(1), NOW + timedelta(seconds=1))
    order = e.submit(
        candidate("one-second-depth", now=NOW + timedelta(seconds=1)), NOW + timedelta(seconds=1)
    )
    assert order["quantity"] > 2
    first = kite(2, ask_size=1)
    assert e.ingest(first, first.received_time)
    assert e.orders()[0]["filled"] == 1
    with sqlite3.connect(e.settings.database) as db:
        financial_before = [
            db.execute("SELECT * FROM " + table).fetchall()
            for table in ("orders", "fills", "positions")
        ]
        cash_before = db.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0]
    tied = first.model_copy(
        update={
            "received_time": first.received_time + timedelta(milliseconds=200),
            "ask_size": 50,
            "volume": first.volume + 1,
        }
    )
    assert e.ingest(tied, tied.received_time)
    with sqlite3.connect(e.settings.database) as db:
        assert [
            db.execute("SELECT * FROM " + table).fetchall()
            for table in ("orders", "fills", "positions")
        ] == financial_before
        assert db.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0] == cash_before
    assert e._fresh(tied, tied.received_time)
    assert e.ingest(kite(3, ask_size=1), NOW + timedelta(seconds=3))
    assert e.orders()[0]["filled"] == 2
    with sqlite3.connect(e.settings.database) as db:
        rows = db.execute("SELECT price,quantity,fees FROM fills").fetchall()
        debit = sum((D(price) * quantity + D(fees) for price, quantity, fees in rows), D(0))
        assert (
            D(db.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0])
            == D("25000") - debit
        )
        assert len(rows) == 2
    with e.db.transaction() as tx:
        Database.reconcile(tx)


@pytest.mark.parametrize("change", ["old_exchange", "old_receipt", "replay", "volume_regression"])
def test_tied_update_exception_does_not_accept_backwards_or_ambiguous_input(engine_factory, change):
    e = engine_factory()
    first = kite(1)
    assert e.ingest(first, first.received_time)
    update = first.model_copy(
        update={
            "ask_size": first.ask_size + 1,
            "received_time": first.received_time + timedelta(milliseconds=100),
        }
    )
    if change == "old_exchange":
        update = update.model_copy(update={"exchange_time": NOW})
    elif change == "old_receipt":
        update = update.model_copy(update={"received_time": first.received_time})
    elif change == "replay":
        update = update.model_copy(update={"source": "replay"})
    else:
        update = update.model_copy(update={"volume": first.volume - 1})
    assert not e.ingest(update, NOW + timedelta(seconds=2))
    assert not e._fresh(first, NOW + timedelta(seconds=2))
    assert not e.orders()


def test_same_second_candle_updates_preserve_actual_high_low_and_incremental_volume():
    builder = CandleBuilder(1)
    first = kite()
    assert builder.update(first) == []
    tied = first.model_copy(
        update={
            "last": D("501"),
            "volume": 1010,
            "received_time": NOW + timedelta(milliseconds=100),
        }
    )
    assert builder.update(tied) == []
    assert builder.active["NSE:DEMO"].high == D("501")
    assert builder.active["NSE:DEMO"].volume == 10
    with pytest.raises(ValueError, match="non-monotonic"):
        builder.update(tied.model_copy(update={"last": D("499")}))
    with pytest.raises(ValueError, match="volume regression"):
        builder.update(
            tied.model_copy(
                update={"volume": 1009, "received_time": NOW + timedelta(milliseconds=200)}
            )
        )


def test_same_second_stop_latches_protection_but_waits_for_new_timestamp_to_sell(engine_factory):
    e = engine_factory(max_trade_risk=D(250), daily_loss_limit=D(500))
    e.ingest(kite(1), NOW + timedelta(seconds=1))
    e.submit(candidate("tied-stop", now=NOW + timedelta(seconds=1)), NOW + timedelta(seconds=1))
    first = kite(2, ask_size=1)
    e.ingest(first, first.received_time)
    cash_after_buy = e.snapshot(first.received_time)["cash"]
    stopped = first.model_copy(
        update={
            "received_time": first.received_time + timedelta(milliseconds=200),
            "bid": D("494"),
            "ask": D("494.05"),
            "last": D("494.05"),
            "volume": first.volume + 1,
        }
    )
    assert e.ingest(stopped, stopped.received_time)
    orders = e.orders()
    assert next(o for o in orders if o["side"] == "BUY")["state"] == "CANCELLED"
    sell = next(o for o in orders if o["side"] == "SELL")
    assert sell["state"] == "ACCEPTED" and sell["filled"] == 0
    assert e.snapshot(stopped.received_time)["cash"] == cash_after_buy
    later = kite(3, bid="494", ask="494.05")
    assert e.ingest(later, later.received_time)
    assert next(o for o in e.orders() if o["side"] == "SELL")["state"] == "FILLED"
    with sqlite3.connect(e.settings.database) as db:
        fills = db.execute(
            "SELECT o.side,f.price,f.quantity,f.fees FROM fills f JOIN orders o ON o.id=f.order_id"
        ).fetchall()
        expected = D("25000") + sum(
            (
                (D(price) * quantity if side == "SELL" else -D(price) * quantity) - D(fees)
                for side, price, quantity, fees in fills
            ),
            D(0),
        )
        assert len(fills) == 2
        assert D(db.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0]) == expected
        assert db.execute("SELECT count(*) FROM positions").fetchone()[0] == 0
    with e.db.transaction() as tx:
        Database.reconcile(tx)
