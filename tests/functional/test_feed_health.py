"""Local synthetic health/error checks; no broker requests or real market evidence."""

import logging
import sqlite3
import threading
from datetime import timedelta
from decimal import Decimal as D

import pytest
from conftest import NOW, TOKEN, candidate, quote
from fastapi.testclient import TestClient

from trading_agent.api.app import create_app

AUTH = {"Authorization": "Bearer " + TOKEN}


def test_feed_status_requires_auth_and_does_not_read_or_write_account(engine, monkeypatch):
    now = NOW + timedelta(milliseconds=1500)
    app = create_app(engine, clock=lambda: now, background=False)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        assert client.get("/api/feed/status").status_code == 401
        with sqlite3.connect(engine.settings.database) as check:
            before = check.execute("SELECT COUNT(*) FROM events").fetchone()[0]
        with monkeypatch.context() as patch:

            def forbidden(*args, **kwargs):
                raise AssertionError("health poll must not inspect the ledger")

            patch.setattr(engine.db, "read_snapshot", forbidden)
            patch.setattr(engine.db, "transaction", forbidden)
            patch.setattr(engine, "snapshot", forbidden)
            result = client.get("/api/feed/status", headers=AUTH)
        assert result.status_code == 200
        assert result.json() == {
            "schema_version": 1,
            "observed_at": now.isoformat(timespec="microseconds"),
            "connected": True,
            "feed_connected": True,
            "faulted": False,
            "last_tick_at": NOW.isoformat(timespec="microseconds"),
            "last_tick_ms": 1500,
            "last_tick_recent": True,
        }
        assert result.headers["Cache-Control"] == "no-store"
        with sqlite3.connect(engine.settings.database) as check:
            assert check.execute("SELECT COUNT(*) FROM events").fetchone()[0] == before
            assert check.execute("SELECT COUNT(*) FROM orders").fetchone()[0] == 0
            assert (
                D(check.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0]) == 25000
            )


def test_feed_age_does_not_renew_for_repeats_rollback_or_reconnect(engine):
    assert not engine.ingest(quote(), NOW + timedelta(seconds=1))
    assert engine.last_tick_received_at == NOW
    with pytest.raises(ValueError, match="mapping"):
        engine.ingest_batch(
            [quote(1), quote(1, symbol="NSE:SECOND", token=999)], NOW + timedelta(seconds=1)
        )
    assert engine.last_tick_received_at == NOW
    with sqlite3.connect(engine.settings.database) as check:
        assert check.execute("SELECT time FROM quotes WHERE symbol='NSE:DEMO'").fetchone()[
            0
        ] == NOW.isoformat(timespec="microseconds")
    current = [NOW + timedelta(seconds=6)]
    with TestClient(
        create_app(engine, clock=lambda: current[0], background=False),
        base_url="http://127.0.0.1",
    ) as client:
        state = client.get("/api/feed/status", headers=AUTH).json()
        assert state["last_tick_ms"] == 6000 and not state["last_tick_recent"]
        engine.set_connected(False)
        engine.set_connected(True)
        state = client.get("/api/feed/status", headers=AUTH).json()
        assert state["connected"] and state["last_tick_at"] is None
        assert state["last_tick_ms"] is None and not state["last_tick_recent"]
        assert engine.ingest(quote(6), current[0])
        assert client.get("/api/feed/status", headers=AUTH).json()["last_tick_recent"]
        current[0] -= timedelta(seconds=1)
        state = client.get("/api/feed/status", headers=AUTH).json()
        assert state["last_tick_ms"] is None and not state["last_tick_recent"]
        engine.faulted = True
        assert not client.get("/api/feed/status", headers=AUTH).json()["last_tick_recent"]


def test_expected_request_errors_never_fault_or_disconnect_engine(engine):
    with TestClient(
        create_app(engine, clock=lambda: NOW, background=False), base_url="http://127.0.0.1"
    ) as client:
        requests = [
            ("GET", "/missing-route", AUTH, None, 404),
            ("GET", "/api/status", {}, None, 401),
            ("POST", "/api/paper/intents", AUTH, {"unexpected": True}, 422),
            ("POST", "/api/paper/intents", AUTH, "malformed-json", 422),
            ("POST", "/api/control/kill", {**AUTH, "Origin": "https://invalid.test"}, None, 403),
        ]
        for method, path, headers, body, expected in requests:
            arguments = {"content": body} if isinstance(body, str) else {"json": body}
            assert (
                client.request(method, path, headers=headers, **arguments).status_code == expected
            )
            assert not engine.faulted and engine.connected
        assert (
            client.post(
                "/api/paper/intents",
                headers=AUTH,
                json=candidate("still-working").model_dump(mode="json"),
            ).json()["state"]
            == "ACCEPTED"
        )


def test_watchdog_failure_logs_traceback_and_blocks_entries(engine, monkeypatch, caplog):
    observed = threading.Event()

    def broken(now):
        observed.set()
        raise RuntimeError("invented watchdog failure")

    monkeypatch.setattr(engine, "poll", broken)
    caplog.set_level(logging.ERROR, logger="trading_agent.api.app")
    with TestClient(create_app(engine, clock=lambda: NOW), base_url="http://127.0.0.1"):
        assert observed.wait(3)
        # Acquire the same lock to wait until the watchdog has left its risk operation.
        # Logging happens just afterward; the record is checked following joined shutdown.
    records = [record for record in caplog.records if "watchdog failed" in record.message]
    assert records and records[0].exc_info and "invented watchdog failure" in caplog.text
    assert engine.faulted and not engine.connected


def test_gap_through_stop_exits_below_stop_and_persists_exact_accounting(engine):
    assert engine.submit(candidate("gap-entry"), NOW)["quantity"] == 10
    assert engine.ingest(quote(1), NOW + timedelta(seconds=1))
    # A protective stop triggers below 495. The stop cannot be a minimum sale price.
    assert engine.ingest(quote(2, bid="489.95", ask="490"), NOW + timedelta(seconds=2))
    assert engine.ingest(quote(3, bid="489.95", ask="490"), NOW + timedelta(seconds=3))
    with sqlite3.connect(engine.settings.database) as check:
        fills = check.execute("SELECT quantity,price,fees FROM fills ORDER BY seq").fetchall()
        assert [(qty, D(price), D(fee)) for qty, price, fee in fills] == [
            (10, D("500.25"), D("2.11")),
            (10, D("489.70"), D("3.15")),
        ]
        assert check.execute("SELECT COUNT(*) FROM positions").fetchone()[0] == 0
        assert check.execute("SELECT state,reason FROM orders WHERE side='SELL'").fetchone() == (
            "FILLED",
            "STOP",
        )
        cash = D(check.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0])
        assert cash == D("24889.24")
        assert cash == D("25000") - D("5002.50") - D("2.11") + D("4897.00") - D("3.15")
