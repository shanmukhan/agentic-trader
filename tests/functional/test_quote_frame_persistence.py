"""Manual stream callbacks retain both exact fills and completed-candle evidence."""

import json
import sqlite3
from contextlib import closing
from datetime import timedelta
from decimal import Decimal as D
from unittest.mock import Mock

from conftest import NOW, TOKEN, candidate, quote
from fastapi.testclient import TestClient

from trading_agent.api.app import create_app
from trading_agent.api.setup import SetupService
from trading_agent.models import Candle, Instrument
from trading_agent.persistence.database import Database


def test_manual_frame_commits_once_and_keeps_fill_and_completed_candle_evidence(
    engine,
    tmp_path,
    monkeypatch,
):
    config = tmp_path / "manual-frame.toml"
    config.write_text(
        "".join(
            key + " = " + json.dumps(value) + "\n"
            for key, value in engine.settings.model_dump(
                mode="json", exclude={"operator_token"}
            ).items()
        )
    )
    current = [NOW + timedelta(seconds=1)]
    setup = SetupService(engine, config, lambda: current[0])
    setup.values = {"api_key": "invented", "api_secret": "invented", "access_token": "invented"}
    engine.register([Instrument(symbol="NSE:OTHER", token=257, tick_size=D(".05"))])
    setup.select_symbols({"symbols": ["DEMO", "OTHER"]})
    monkeypatch.setattr("trading_agent.api.setup.ReadOnlyKite", lambda *args: Mock())
    setup.prepare_stream()
    stream = setup.stream
    assert stream is not None and stream._on_quotes is not None
    stream._on_connection(True)
    engine.ingest(quote(), NOW)
    engine.submit(candidate("callback-frame"), NOW)
    statements = []
    engine.db.connection.set_trace_callback(statements.append)
    stream._on_quotes([quote(1, ask_size=1), quote(1, symbol="NSE:OTHER", token=257)])
    engine.db.connection.set_trace_callback(None)
    assert statements.count("BEGIN IMMEDIATE") == statements.count("COMMIT") == 1
    current[0] = NOW + timedelta(seconds=61)
    stream._on_quotes([quote(61), quote(61, symbol="NSE:OTHER", token=257)])
    with closing(sqlite3.connect(engine.db.path)) as persisted:
        assert (
            persisted.execute("SELECT filled FROM orders WHERE id='callback-frame'").fetchone()[0]
            == 1
        )
        fills = persisted.execute("SELECT quantity,price,fees FROM fills").fetchall()
        assert len(fills) == 1
        cash = D("25000") - sum((D(price) * qty + D(fee) for qty, price, fee in fills), D(0))
        assert D(persisted.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0]) == cash
        candles = [
            Candle.model_validate_json(row[0])
            for row in persisted.execute("SELECT payload FROM candles")
        ]
        assert {candle.symbol for candle in candles} == {"NSE:DEMO", "NSE:OTHER"}
        assert all(
            candle.minutes == 1 and candle.start == NOW and candle.completed for candle in candles
        )
        assert (
            persisted.execute("SELECT COUNT(*) FROM events WHERE kind='quote'").fetchone()[0] == 5
        )
        persisted.row_factory = sqlite3.Row
        Database.reconcile(persisted)
    setup.close()


def test_authenticated_order_read_uses_committed_snapshot_during_active_writer(engine):
    with (
        TestClient(
            create_app(engine, clock=lambda: NOW, background=False), base_url="http://127.0.0.1"
        ) as client,
        engine.db.transaction() as writer,
    ):
        engine.db.set(writer, "uncommitted_read_probe", "private")
        response = client.get("/api/paper/orders", headers={"Authorization": "Bearer " + TOKEN})
        assert response.status_code == 200 and response.json() == []
        assert response.headers["Cache-Control"] == "no-store"
