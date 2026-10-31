"""Invented time/quotes. Reading guidance cannot arm a mode or change saved finances."""

import sqlite3
from contextlib import closing
from datetime import timedelta
from decimal import Decimal

from conftest import NOW, TOKEN
from fastapi.testclient import TestClient

from trading_agent.api.app import create_app

AUTH = {"Authorization": "Bearer " + TOKEN}


def test_mode_guidance_tracks_server_time_without_changing_entire_persisted_account(desk_factory):
    desk, _, _ = desk_factory()
    engine = desk.engine
    clock = [NOW - timedelta(hours=2, minutes=15)]  # 07:45 IST, reviewed open at 09:15.

    def persisted():
        with closing(sqlite3.connect(engine.settings.database)) as db:
            assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert Decimal(
                db.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0]
            ) == Decimal("25000.00")
            assert db.execute("SELECT count(*) FROM orders").fetchone()[0] == 0
            assert db.execute("SELECT count(*) FROM fills").fetchone()[0] == 0
            return list(db.iterdump())

    with TestClient(
        create_app(engine, desk=desk, clock=lambda: clock[0], background=False),
        base_url="http://127.0.0.1",
    ) as client:
        before = persisted()
        for moment in (NOW - timedelta(hours=2, minutes=15), NOW - timedelta(minutes=40)):
            clock[0] = moment
            response = client.get("/api/desk", headers=AUTH).json()
            guidance = response["readiness"]["mode_guidance"]
            assert guidance["next_entry_at"] == "2026-10-20T09:30:00+05:30"
            assert guidance["automatic_start"] is False
            assert "OUTSIDE_ENTRY_WINDOW" in {item["code"] for item in guidance["items"]}
            for mode in ("approval", "automatic"):
                blocked = client.post(
                    "/api/desk/mode",
                    headers=AUTH,
                    json={"mode": mode, "revision": response["revision"], "acknowledged": True},
                )
                assert blocked.status_code == 409
            assert persisted() == before and desk.mode == "manual"
        clock[0] = NOW - timedelta(minutes=30)  # 09:30: no usable quote available yet.
        response = client.get("/api/desk", headers=AUTH).json()
        assert response["readiness"]["mode_guidance"]["next_entry_at"] is None
        assert response["readiness"]["can_start"] is False
        clock[0] = NOW  # Existing invented quote is fresh; readiness clears without arming.
        response = client.get("/api/desk", headers=AUTH).json()
        assert response["readiness"]["mode_guidance"]["state"] == "ready"
        assert response["readiness"]["can_start"] is True
        assert response["mode"] == "manual"
        assert persisted() == before
