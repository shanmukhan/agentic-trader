"""Authenticated read-only analysis, using invented saved data, with independent ledger checks."""

import sqlite3
from datetime import timedelta
from decimal import Decimal as D

from conftest import NOW, TOKEN, candidate
from fastapi.testclient import TestClient

from trading_agent.api.app import create_app
from trading_agent.desk.service import TradingDesk

AUTH = {"Authorization": "Bearer " + TOKEN}


def persisted(engine):
    with sqlite3.connect(engine.settings.database) as db:
        assert D(db.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0]) == D(25000)
        assert db.execute("SELECT count(*) FROM orders").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM fills").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM positions").fetchone()[0] == 0
        return list(db.iterdump())


def test_analysis_shell_public_data_authorized_whitelisted_and_no_get_side_effects(desk_factory):
    desk, _, _ = desk_factory()
    engine = desk.engine
    now = [NOW]
    with TestClient(
        create_app(engine, clock=lambda: now[0], background=False, desk=desk),
        base_url="http://127.0.0.1",
    ) as client:
        before = persisted(engine)
        for route in ("/analysis", "/analysis.js"):
            shell = client.get(route)
            assert shell.status_code == 200 and TOKEN not in shell.text
        assert client.get("/analysis").headers["x-frame-options"] == "SAMEORIGIN"
        assert client.get("/api/analysis").status_code == 401
        view = client.get("/api/analysis", headers=AUTH).json()
        assert view["symbol"] == "NSE:DEMO" and view["timeframe"] == "1d"
        assert len(view["bars"]) == 4 and view["quote"]["usable"]
        assert view["bars"][-1]["close"] == "500"
        assert view["screen"]["symbol"] == "NSE:DEMO"
        # BROAD has research history but no streaming subscription or invented live quote.
        broad = client.get("/api/analysis?symbol=NSE:BROAD", headers=AUTH).json()
        assert len(broad["bars"]) == 4 and not broad["quote"]["subscribed"]
        assert broad["quote"]["last"] is None and not broad["quote"]["usable"]
        minute = client.get("/api/analysis?timeframe=1m", headers=AUTH).json()
        assert minute["bars"] == [] and minute["data_state"] == "missing"
        assert "allow complete intervals" in minute["message"]
        assert client.get("/api/analysis?symbol=NSE:SECOND", headers=AUTH).status_code == 404
        for query in ("symbol=../../secret", "symbol=NSE:demo", "timeframe=15m"):
            assert client.get("/api/analysis?" + query, headers=AUTH).status_code == 422
        assert client.post("/api/analysis", headers=AUTH, json={}).status_code == 405
        now[0] += timedelta(seconds=10)
        stale = client.get("/api/analysis", headers=AUTH).json()
        assert stale["quote"]["status"] == "STALE_QUOTE"
        assert len(stale["bars"]) == 4 and not stale["quote"]["usable"]
        assert persisted(engine) == before


def test_analysis_empty_setup_explains_recovery_and_does_not_choose_catalog_stock(engine_factory):
    engine = engine_factory(stream_tokens=())
    desk = TradingDesk(engine, NOW)
    with TestClient(
        create_app(engine, clock=lambda: NOW, background=False, desk=desk),
        base_url="http://127.0.0.1",
    ) as client:
        before = persisted(engine)
        view = client.get("/api/analysis", headers=AUTH).json()
        assert not view["symbols"] and view["symbol"] is None and view["quote"] is None
        assert view["data_state"] == "missing" and not view["bars"]
        assert "prepare strategy data" in view["message"]
        assert client.get("/api/analysis?symbol=NSE:DEMO", headers=AUTH).status_code == 404
        assert persisted(engine) == before


def test_reading_analysis_does_not_refresh_strategy_or_expire_approval(desk_factory):
    desk, _, _ = desk_factory()
    desk.set_mode("approval", NOW, desk.revision)
    decision = desk.offer(candidate(), NOW, {"kind": "intraday", "candle": {"close": "500"}})
    assert decision["state"] == "awaiting_approval"
    engine = desk.engine
    # Even a request observed beyond proposal expiry must remain a pure data read.
    # Only the existing strategy/watchdog workflow may expire or act on decisions.
    with TestClient(
        create_app(engine, clock=lambda: NOW + timedelta(minutes=10), background=False, desk=desk),
        base_url="http://127.0.0.1",
    ) as client:
        before = persisted(engine)
        view = client.get("/api/analysis", headers=AUTH).json()
        assert view["data_state"] == "available" and not view["quote"]["usable"]
        assert desk.mode == "approval" and desk.last_analysis is None
        assert persisted(engine) == before
        with sqlite3.connect(engine.settings.database) as db:
            row = db.execute("SELECT state FROM desk_decisions WHERE id=?", (decision["id"],))
            assert row.fetchone()[0] == "awaiting_approval"
