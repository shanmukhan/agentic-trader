import sqlite3
import subprocess
import sys
from datetime import timedelta

import pytest
from conftest import NOW, candidate, quote

from trading_agent.execution.paper_broker import PaperBroker
from trading_agent.persistence.database import Database


def test_actual_process_death_rolls_back_uncommitted_cash(engine):
    path, settings, calendar = engine.db.path, engine.settings, engine.calendar
    engine.submit(candidate(), NOW)
    engine.db.close()
    code = """
import os,sys
from decimal import Decimal
from pathlib import Path
from trading_agent.persistence.database import Database
db=Database(Path(sys.argv[1]),Decimal('25000'))
with db.transaction() as tx:
    tx.execute("UPDATE meta SET value='0' WHERE key='cash'")
    os._exit(7)
"""
    result = subprocess.run([sys.executable, "-c", code, str(path)], check=False)
    assert result.returncode == 7
    restored = Database(path, settings.starting_cash)
    try:
        recovered = PaperBroker(restored, settings, calendar)
        assert recovered.snapshot(NOW)["cash"] == "25000"
        assert recovered.orders()[0]["state"] == "CANCELLED"
        assert recovered.submit(candidate(), NOW)["state"] == "CANCELLED"
    finally:
        restored.close()


@pytest.mark.parametrize(
    "mutation,expected",
    [
        ("DELETE FROM meta WHERE key='kill'", "missing required"),
        ("UPDATE positions SET cost='1'", "cost and P&L"),
        ("UPDATE meta SET value='1' WHERE key='fees'", "cost and P&L"),
        ("UPDATE orders SET turnover='1'", "turnover"),
    ],
)
def test_corrupted_durable_state_fails_closed(engine, mutation, expected):
    engine.submit(candidate(), NOW)
    engine.ingest(quote(1), NOW + timedelta(seconds=1))
    path, cash = engine.db.path, engine.settings.starting_cash
    engine.db.close()
    connection = sqlite3.connect(path)
    try:
        connection.execute(mutation)
        connection.commit()
    finally:
        connection.close()
    with pytest.raises(RuntimeError, match=expected):
        Database(path, cash)
