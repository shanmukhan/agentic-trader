"""Frame batching preserves complete causal and exact financial evidence."""

import sqlite3
from contextlib import closing
from datetime import timedelta
from decimal import Decimal as D

import pytest
from conftest import NOW, candidate, quote

from trading_agent.persistence.database import Database


def persisted(engine):
    with closing(sqlite3.connect(engine.db.path)) as tx:
        return {
            table: tx.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
            for table in ("meta", "quotes", "orders", "fills", "positions", "events")
        }


def test_batch_matches_sequential_ticks_including_intraframe_target_and_partial_fill(
    engine_factory,
):
    sequential, batched = engine_factory(), engine_factory()
    for engine in (sequential, batched):
        engine.submit(candidate("frame-order"), NOW)
    ticks = [quote(1, ask_size=1), quote(2, bid="510", ask="510.05")]
    now = NOW + timedelta(seconds=3)
    expected = [sequential.ingest(q, now) for q in ticks]
    statements = []
    batched.db.connection.set_trace_callback(statements.append)
    assert batched.ingest_batch(ticks, now) == expected == [True, True]
    batched.db.connection.set_trace_callback(None)
    assert statements.count("BEGIN IMMEDIATE") == statements.count("COMMIT") == 1
    assert persisted(batched) == persisted(sequential)
    assert any(order["side"] == "SELL" for order in batched.orders())
    # The protective exit is durable immediately; latency requires a later quote to fill it.
    for engine in (sequential, batched):
        engine.ingest(quote(4, bid="510", ask="510.05"), NOW + timedelta(seconds=4))
    assert persisted(batched) == persisted(sequential)
    with closing(sqlite3.connect(batched.db.path)) as tx:
        fills = tx.execute(
            "SELECT o.side,f.quantity,f.price,f.fees FROM fills f JOIN orders o ON o.id=f.order_id"
        ).fetchall()
        assert [side for side, *_ in fills] == ["BUY", "SELL"]
        cash = D("25000") + sum(
            (
                D(price) * qty * (-1 if side == "BUY" else 1) - D(fee)
                for side, qty, price, fee in fills
            ),
            D(0),
        )
        assert D(tx.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0]) == cash
        assert tx.execute("SELECT COUNT(*) FROM positions").fetchone()[0] == 0
        assert tx.execute("SELECT COUNT(*) FROM events WHERE kind='quote'").fetchone()[0] == 4
        tx.row_factory = sqlite3.Row
        Database.reconcile(tx)


def test_failed_batch_rolls_back_earlier_fill_and_revokes_frame_symbols(engine):
    engine.submit(candidate("rollback-frame"), NOW)
    before = persisted(engine)
    good = quote(1, ask_size=1)
    wrong_mapping = quote(2, symbol="NSE:SECOND", token=3)
    with pytest.raises(ValueError, match="mapping mismatch"):
        engine.ingest_batch([good, wrong_mapping], NOW + timedelta(seconds=2))
    assert persisted(engine) == before
    assert {"NSE:DEMO", "NSE:SECOND"} <= engine.bad_symbols
    assert not {"NSE:DEMO", "NSE:SECOND"} & engine.seen_symbols
    assert not engine._fresh(quote(), NOW + timedelta(seconds=2))
    assert not engine.faulted


def test_batch_sql_failure_does_not_publish_partial_financial_state(engine, monkeypatch):
    engine.submit(candidate("disk-failure-frame"), NOW)
    before = persisted(engine)
    original = engine.db.event

    def fail(tx, time, kind, entity, payload):
        if kind == "quote" and entity == "NSE:SECOND":
            raise sqlite3.OperationalError("invented write failure")
        original(tx, time, kind, entity, payload)

    monkeypatch.setattr(engine.db, "event", fail)
    with pytest.raises(sqlite3.OperationalError):
        engine.ingest_batch(
            [quote(1, ask_size=1), quote(2, symbol="NSE:SECOND", token=2)],
            NOW + timedelta(seconds=2),
        )
    assert persisted(engine) == before
    assert engine.faulted and not engine.connected


def test_batch_retains_second_resolution_order_and_single_liquidity_budget(engine):
    engine.submit(candidate("tied-frame"), NOW)
    first = quote(1, ask_size=1).model_copy(update={"source": "kite"})
    second = first.model_copy(
        update={
            "received_time": first.received_time + timedelta(milliseconds=100),
            "ask_size": 100,
            "volume": first.volume + 1,
        }
    )
    assert engine.ingest_batch([first, second, second], second.received_time) == [True, True, False]
    with closing(sqlite3.connect(engine.db.path)) as tx:
        assert tx.execute("SELECT filled FROM orders WHERE id='tied-frame'").fetchone()[0] == 1
        assert tx.execute("SELECT COUNT(*) FROM events WHERE kind='quote'").fetchone()[0] == 3


def test_batch_is_bounded_before_opening_a_transaction(engine):
    before = persisted(engine)
    for ticks in ([], [quote(1)] * (engine.settings.stream_limit + 1)):
        with pytest.raises(ValueError, match="stream limit"):
            engine.ingest_batch(ticks, NOW)
    assert persisted(engine) == before


def test_connected_batch_rechecks_processing_time_before_each_quote(engine):
    engine.submit(candidate("aging-frame"), NOW)
    ticks = [quote(1, symbol="NSE:SECOND", token=2), quote(1, ask_size=100)]
    times = iter([NOW + timedelta(seconds=1), NOW + timedelta(seconds=7)])
    assert engine.ingest_batch(ticks, NOW + timedelta(seconds=1), clock=lambda: next(times)) == [
        True,
        False,
    ]
    assert engine.orders()[0]["filled"] == 0
    assert "NSE:DEMO" in engine.bad_symbols
    with closing(sqlite3.connect(engine.db.path)) as tx:
        assert tx.execute("SELECT COUNT(*) FROM fills").fetchone()[0] == 0
        assert D(tx.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0]) == D("25000")


def test_batch_processing_clock_regression_rolls_back_earlier_quotes(engine):
    before = persisted(engine)
    times = iter([NOW + timedelta(seconds=2), NOW + timedelta(seconds=1)])
    with pytest.raises(ValueError, match="clock moved backward"):
        engine.ingest_batch([quote(1), quote(2)], NOW, clock=lambda: next(times))
    assert persisted(engine) == before
    assert not engine.seen_symbols and "NSE:DEMO" in engine.bad_symbols
