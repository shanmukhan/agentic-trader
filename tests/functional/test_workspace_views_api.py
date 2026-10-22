"""Authenticated read-model contract; no broker, market or device acceptance claims."""

import sqlite3
from contextlib import closing
from datetime import timedelta
from decimal import Decimal as D

from conftest import NOW, TOKEN, candidate, quote
from fastapi.testclient import TestClient

from trading_agent.api.app import create_app

AUTH = {"Authorization": "Bearer " + TOKEN}


def persisted(engine):
    with closing(sqlite3.connect(engine.settings.database)) as db:
        assert D(db.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0]) == D(25000)
        assert db.execute("SELECT count(*) FROM orders").fetchone()[0] == 0
        assert db.execute("SELECT count(*) FROM fills").fetchone()[0] == 0
        return list(db.iterdump())


def test_authenticated_no_store_read_redacts_paths_and_secrets_and_advertises_real_capabilities(
    desk_factory,
):
    desk, profile, directory = desk_factory()
    engine = desk.engine
    with TestClient(
        create_app(engine, clock=lambda: NOW, background=False, desk=desk),
        base_url="http://127.0.0.1",
    ) as client:
        before = persisted(engine)
        assert client.get("/api/workspace/views").status_code == 401
        response = client.get("/api/workspace/views", headers=AUTH)
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["x-frame-options"] == "DENY"
        result = response.json()
        assert result["schema_version"] == 1
        assert result["capabilities"]["discovery"]["state"] == "available"
        assert result["capabilities"]["backtests"]["state"] == "registered_jobs"
        assert "verified runtime" in result["capabilities"]["backtests"]["detail"]
        assert result["capabilities"]["settings"]["state"] == "read_only"
        for key in ("fundamentals", "allocation", "benchmark"):
            assert result["capabilities"][key]["state"] == "unsupported"
        for private in (TOKEN, str(profile), str(directory), str(engine.settings.database)):
            assert private not in response.text
        assert not {"api_key", "api_secret", "access_token", "operator_token"}.intersection(
            result["settings"]
        )
        assert result["settings"]["limits"]["max_trade_risk"] == "62.50"
        assert result["settings"]["limits"]["max_positions"] == 2
        assert result["portfolio"]["performance"]["total_return_pct"] is None
        assert client.post("/api/workspace/views", headers=AUTH, json={}).status_code == 405
        assert persisted(engine) == before


def test_allocation_http_uses_only_owned_shares_actual_cash_and_accepted_bid(engine):
    """Invented partial fill; independent persisted money before/after read and expiry."""
    engine.submit(candidate(), NOW)
    instant = NOW + timedelta(seconds=1)
    engine.ingest(quote(1, ask_size=3), instant)
    clock = [instant]
    with TestClient(
        create_app(engine, clock=lambda: clock[0], background=False),
        base_url="http://127.0.0.1",
    ) as client:
        with closing(sqlite3.connect(engine.settings.database)) as db:
            db.row_factory = sqlite3.Row
            fills = db.execute("SELECT quantity,price,fees FROM fills").fetchall()
            cost = sum((D(f["price"]) * f["quantity"] + D(f["fees"]) for f in fills), D(0))
            cash = D("25000") - cost
            quantity = sum(f["quantity"] for f in fills)
            assert quantity == 3
            assert D(db.execute("SELECT cost FROM positions").fetchone()[0]) == cost
            assert D(db.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0]) == cash
            reservation = D(db.execute("SELECT reserved_cash FROM orders").fetchone()[0])
            before = list(db.iterdump())
        result = client.get("/api/workspace/views", headers=AUTH).json()["portfolio"]
        allocation = result["allocation"]
        assert allocation["state"] == "available"
        assert D(allocation["allocation_base"]) == cash + quantity * D("499.95")
        assert D(allocation["cash_balance"]) == cash
        assert D(allocation["commitments"]["reserved_cash"]) == reservation > 0
        assert allocation["positions"][0]["quantity"] == quantity
        assert result["performance"]["daily_metrics"]["metrics"]["cagr_pct"]["value"] is None
        clock[0] += timedelta(seconds=10)
        stale = client.get("/api/workspace/views", headers=AUTH).json()["portfolio"]["allocation"]
        assert stale["state"] == "unavailable"
        assert stale["cash_weight_pct"] is None
        assert stale["positions"][0]["weight_pct"] is None
        with closing(sqlite3.connect(engine.settings.database)) as db:
            assert list(db.iterdump()) == before


def test_http_read_past_proposal_expiry_preserves_mode_revision_materialization_and_cash(
    desk_factory, monkeypatch
):
    desk, _, _ = desk_factory()
    desk.set_mode("approval", NOW, desk.revision)
    decision = desk.offer(candidate(), NOW, {"kind": "intraday", "signal_key": "test"})
    engine = desk.engine
    now = NOW + timedelta(minutes=10)
    with TestClient(
        create_app(engine, clock=lambda: now, background=False, desk=desk),
        base_url="http://127.0.0.1",
    ) as client:
        before = persisted(engine)
        memory = (desk.mode, desk.revision, desk.reason, desk.last_analysis, engine.faulted)

        def prohibited(*args, **kwargs):
            raise AssertionError("A read must not run account/strategy workflows")

        monkeypatch.setattr(desk, "view", prohibited)
        monkeypatch.setattr(desk, "tick", prohibited)
        monkeypatch.setattr(desk.research, "refresh", prohibited)
        monkeypatch.setattr(engine, "poll", prohibited)
        response = client.get("/api/workspace/views", headers=AUTH)
        assert response.status_code == 200
        result = response.json()
        assert result["settings"]["decision_mode"] == "approval"
        assert result["dashboard"]["recent_decisions"][0]["id"] == decision["id"]
        assert result["dashboard"]["recent_decisions"][0]["state"] == "awaiting_approval"
        assert (desk.mode, desk.revision, desk.reason, desk.last_analysis, engine.faulted) == memory
        assert persisted(engine) == before


def test_read_failure_is_sanitized_without_generic_handler_revoking_authority(
    desk_factory, monkeypatch
):
    desk, _, _ = desk_factory()
    desk.set_mode("approval", NOW, desk.revision)
    engine = desk.engine
    with TestClient(
        create_app(engine, clock=lambda: NOW, background=False, desk=desk),
        base_url="http://127.0.0.1",
    ) as client:
        before = persisted(engine)
        memory = (desk.mode, desk.revision, desk.reason, engine.connected, engine.faulted)

        def broken_read(tx, now):
            raise OSError("sensitive local path and credential: " + TOKEN)

        monkeypatch.setattr(engine, "_snapshot", broken_read)
        response = client.get("/api/workspace/views", headers=AUTH)
        assert response.status_code == 503 and TOKEN not in response.text
        assert "sensitive local path" not in response.text
        assert (desk.mode, desk.revision, desk.reason, engine.connected, engine.faulted) == memory
        assert persisted(engine) == before
