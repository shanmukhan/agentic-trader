"""Invented full-mode packets through the real setup callbacks; no broker connection."""

import json
import sqlite3
import struct
from datetime import timedelta
from decimal import Decimal as D
from unittest.mock import Mock

from conftest import NOW, TOKEN, candidate, quote
from fastapi.testclient import TestClient

from trading_agent.api.app import create_app
from trading_agent.api.setup import SetupService
from trading_agent.broker.readonly_kite import QuoteStream, parse_binary
from trading_agent.models import Instrument
from trading_agent.persistence.database import Database

AUTH = {"Authorization": "Bearer " + TOKEN}


def packet(second, step):
    body = bytearray(184)
    for offset, value in [
        (0, 1),
        (4, 50000),
        (16, 1000 + 100 * second + step),
        (60, int((NOW + timedelta(seconds=second)).timestamp())),
        (64, 100),
        (68, 49995),
        (124, 100 + step),
        (128, 50000),
    ]:
        struct.pack_into(">I", body, offset, value)
    return struct.pack(">HH", 1, 184) + body


def test_live_second_resolution_packets_do_not_cancel_approval_but_backwards_data_still_does(
    desk_factory,
    tmp_path,
    monkeypatch,
):
    desk, _, _ = desk_factory()
    e = desk.engine
    clock = [NOW + timedelta(seconds=1)]
    config = tmp_path / "ordered.toml"
    config.write_text(
        "".join(
            k + " = " + json.dumps(v) + "\n"
            for k, v in e.settings.model_dump(mode="json", exclude={"operator_token"}).items()
        )
    )
    setup = SetupService(e, config, lambda: clock[0])
    setup.values = {
        "api_key": "unitkey",
        "api_secret": "unitsecret",
        "access_token": "unit-session",
    }
    monkeypatch.setattr("trading_agent.api.setup.ReadOnlyKite", lambda *a: Mock())
    monkeypatch.setattr(QuoteStream, "start", lambda self: None)
    instrument = Instrument(symbol="NSE:DEMO", token=1, tick_size=D("0.05"))
    with TestClient(
        create_app(
            e, clock=lambda: clock[0], background=False, desk=desk, setup=setup, stream=setup
        ),
        base_url="http://127.0.0.1",
    ) as client:
        assert client.post("/api/setup/connect", headers=AUTH, json={}).status_code == 200
        assert setup.stream is not None
        setup.stream._on_connection(True)
        setup.stream._on_quote(quote(1).model_copy(update={"source": "kite"}))
        response = client.post(
            "/api/desk/mode",
            headers=AUTH,
            json={
                "mode": "approval",
                "revision": desk.revision,
                "acknowledged": True,
            },
        )
        assert response.status_code == 200
        decision = desk.offer(
            candidate("stream-proposal", now=clock[0]),
            clock[0],
            {"kind": "intraday", "signal_key": "stream-fixture"},
        )
        assert decision["state"] == "awaiting_approval"
        for second in range(1, 9):
            for step in range(3):
                clock[0] = NOW + timedelta(seconds=second, milliseconds=step * 200)
                update = parse_binary(packet(second, step), {1: instrument}, clock[0])[0]
                setup.stream._on_quote(update)
                desk.tick(clock[0])
                assert desk.mode == "approval" and not e.faulted
        status = client.get("/api/desk", headers=AUTH).json()
        assert status["decisions"][0]["state"] == "awaiting_approval"
        assert status["readiness"]["quotes"][0]["usable"]
        with sqlite3.connect(e.settings.database) as db:
            assert (
                db.execute("SELECT count(*) FROM events WHERE kind='data_quality'").fetchone()[0]
                == 0
            )
            assert D(db.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0]) == D(
                "25000.00"
            )
            assert db.execute("SELECT count(*) FROM orders").fetchone()[0] == 0
            assert db.execute("SELECT count(*) FROM fills").fetchone()[0] == 0
        clock[0] += timedelta(milliseconds=200)
        setup.stream._on_quote(parse_binary(packet(7, 0), {1: instrument}, clock[0])[0])
        desk.tick(clock[0])
        status = client.get("/api/desk", headers=AUTH).json()
        assert status["mode"] == "manual"
        assert status["decisions"][0]["state"] == "cancelled"
        assert status["decisions"][0]["pause_reasons"] == ["NO_FRESH_EXECUTION_QUOTES"]
        assert not e.orders() and D(e.snapshot(clock[0])["cash"]) == D("25000.00")
        with e.db.transaction() as tx:
            Database.reconcile(tx)
