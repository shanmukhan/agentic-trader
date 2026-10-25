"""Delivery fee and trusted-equity evidence stay consistent across frame commits."""

import sqlite3
from contextlib import closing
from datetime import timedelta
from decimal import Decimal as D

import pytest
from conftest import NOW, candidate, quote

from trading_agent.execution.delivery import HoldingReview
from trading_agent.persistence.database import Database


def persisted(engine):
    with closing(sqlite3.connect(engine.db.path)) as connection:
        return {
            table: connection.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
            for table in ("meta", "quotes", "events", "orders", "fills", "positions")
        }


def reviewed_account(factory):
    engine = factory()
    engine.review_holding(
        HoldingReview(
            symbol="NSE:DEMO",
            session_date=NOW.date(),
            no_corporate_action=True,
            reference="invented frame comparison review",
        ),
        NOW,
    )
    engine.ingest(quote(), NOW)
    engine.submit(candidate("delivery-frame", stop="490", target="510"), NOW)
    return engine


def test_delivery_frame_matches_sequential_fees_trusted_equity_and_protective_exit(
    long_term_factory,
):
    sequential, batched = [reviewed_account(long_term_factory) for _ in range(2)]
    ticks = [quote(1, ask_size=1), quote(2, bid="510", ask="510.05")]
    now = NOW + timedelta(seconds=2)
    expected = [sequential.ingest(item, now) for item in ticks]
    assert batched.ingest_batch(ticks, now) == expected == [True, True]
    for engine in (sequential, batched):
        engine.ingest(quote(3, bid="510", ask="510.05"), NOW + timedelta(seconds=3))
    assert persisted(batched) == persisted(sequential)
    with closing(sqlite3.connect(batched.db.path)) as connection:
        sides = connection.execute(
            "SELECT o.side,f.quantity,f.price,f.fees FROM fills f JOIN orders o ON f.order_id=o.id"
        ).fetchall()
        assert [side for side, *_ in sides] == ["BUY", "SELL"]
        cash = D("25000") + sum(
            (
                D(price) * qty * (-1 if side == "BUY" else 1) - D(fee)
                for side, qty, price, fee in sides
            ),
            D(0),
        )
        assert (
            D(connection.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0]) == cash
        )
        assert D(
            connection.execute("SELECT value FROM meta WHERE key='fees'").fetchone()[0]
        ) == sum((D(fee) for *_, fee in sides), D(0))
        assert connection.execute("SELECT COUNT(*) FROM positions").fetchone()[0] == 0
        connection.row_factory = sqlite3.Row
        Database.reconcile(connection)


def test_failed_delivery_frame_rolls_back_trusted_clocks_and_fill(long_term_factory):
    engine = reviewed_account(long_term_factory)
    before = persisted(engine)
    with pytest.raises(ValueError, match="mapping mismatch"):
        engine.ingest_batch(
            [quote(1, ask_size=1), quote(2, symbol="NSE:SECOND", token=3)],
            NOW + timedelta(seconds=2),
        )
    assert persisted(engine) == before
    assert not engine.seen_symbols
    assert {"NSE:DEMO", "NSE:SECOND"} <= engine.bad_symbols
