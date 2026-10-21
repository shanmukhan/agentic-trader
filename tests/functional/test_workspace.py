from conftest import NOW, TOKEN
from fastapi.testclient import TestClient

from trading_agent.api.app import create_app

AUTH = {"Authorization": "Bearer " + TOKEN}


def test_workspace_shell_assets_and_scoped_framing(engine):
    before = engine.snapshot(NOW)
    with TestClient(
        create_app(engine, clock=lambda: NOW, background=False), base_url="http://127.0.0.1"
    ) as client:
        for path in ("/workspace", "/workspace.js", "/workspace-bridge.js"):
            response = client.get(path)
            assert response.status_code == 200
            assert response.headers["X-Frame-Options"] == "DENY"
            assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
            assert response.headers["Cache-Control"] == "no-store"
            assert TOKEN not in response.text
        for path in ("/console", "/setup", "/portfolio", "/desk", "/activity"):
            response = client.get(path)
            assert response.status_code == 200
            assert response.headers["X-Frame-Options"] == "SAMEORIGIN"
            assert "frame-ancestors 'self'" in response.headers["Content-Security-Policy"]
            assert "workspace-bridge.js" in response.text
        shell = client.get("/workspace").text
        for label in (
            "Start here",
            "Trading desk",
            "Buy / sell activity",
            "Advanced controls",
            "Broker &amp; data",
            "Purchases &amp; SIP",
        ):
            assert label in shell
        assert "No automatic entry schedule" in shell
        assert engine.snapshot(NOW) == before


def test_workspace_metadata_uses_actual_manual_policy_and_no_private_values(engine):
    with TestClient(
        create_app(engine, clock=lambda: NOW, background=False), base_url="http://127.0.0.1"
    ) as client:
        assert client.get("/api/workspace").status_code == 401
        response = client.get("/api/workspace", headers=AUTH)
        data = response.json()
        assert data["mode"] == "paper"
        assert data["entry_start"] == "09:30" and data["entry_end"] == "14:30"
        assert data["max_quote_age_seconds"] == engine.settings.max_quote_age_seconds
        assert not data["automation_enabled"] and data["candidate_cap_per_symbol_day"] is None
        assert data["calendar_today"] and data["calendar_open"]
        assert TOKEN not in response.text
        assert not {"cash", "positions", "api_key", "access_token"}.intersection(data)


def test_workspace_automation_frequency_is_current_config_not_a_promised_trade(paper_factory):
    feed = paper_factory()
    with TestClient(
        create_app(feed.engine, clock=lambda: feed.last_time, background=False, automation=feed),
        base_url="http://127.0.0.1",
    ) as client:
        data = client.get("/api/workspace", headers=AUTH).json()
        assert data["automation_enabled"] and not data["automation_armed"]
        assert data["candidate_cap_per_symbol_day"] == feed.strategy.max_candidates_per_symbol_day
