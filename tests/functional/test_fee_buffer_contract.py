"""A known zero intraday reserve remains exact money, not missing evidence."""

import sqlite3
from contextlib import closing
from decimal import Decimal

import pytest
from conftest import NOW, TOKEN
from fastapi.testclient import TestClient

from trading_agent.api.app import create_app

AUTH = {"Authorization": "Bearer " + TOKEN}


@pytest.mark.parametrize("horizon,expected", [("intraday", "0"), ("long_term", "76.70")])
def test_account_console_and_allocation_share_exact_derived_fee_buffer(
    engine_factory, long_term_factory, horizon, expected
):
    engine = long_term_factory() if horizon == "long_term" else engine_factory()
    with TestClient(
        create_app(engine, clock=lambda: NOW, background=False), base_url="http://127.0.0.1"
    ) as client:
        with closing(sqlite3.connect(engine.settings.database)) as check:
            before = list(check.iterdump())
            persisted_cash = Decimal(
                check.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0]
            )
            assert persisted_cash == Decimal("25000")
        account = client.get("/api/status", headers=AUTH).json()
        console = client.get("/api/console", headers=AUTH).json()["account"]
        portfolio = client.get("/api/workspace/views", headers=AUTH).json()["portfolio"]
        for snapshot in (account, console, portfolio):
            assert snapshot["delivery_fee_buffer"] == expected
            assert isinstance(snapshot["delivery_fee_buffer"], str)
            assert Decimal(snapshot["cash"]) == persisted_cash
            assert Decimal(snapshot["available_cash"]) == persisted_cash - Decimal(expected)
        allocation = portfolio["allocation"]
        assert allocation["commitments"]["delivery_fee_buffer"] == expected
        assert Decimal(allocation["allocation_base"]) == persisted_cash
        assert allocation["cash_weight_pct"] == "100"
        with closing(sqlite3.connect(engine.settings.database)) as check:
            assert list(check.iterdump()) == before
            assert check.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0
            assert check.execute("SELECT COUNT(*) FROM fills").fetchone()[0] == 0
