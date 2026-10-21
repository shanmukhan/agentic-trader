import json
from decimal import Decimal
from unittest.mock import Mock

import pytest
from conftest import NOW, TOKEN
from fastapi.testclient import TestClient

from trading_agent.api.app import create_app
from trading_agent.api.setup import SetupService

AUTH = {"Authorization": "Bearer " + TOKEN}


@pytest.fixture
def setup_client(engine, tmp_path):
    config = tmp_path / "manual.toml"
    values = engine.settings.model_dump(mode="json", exclude={"operator_token"})
    config.write_text("".join(f"{key} = {json.dumps(value)}\n" for key, value in values.items()))
    service = SetupService(engine, config, lambda: NOW)
    app = create_app(engine, clock=lambda: NOW, background=False, setup=service, stream=service)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        yield client, service


def test_setup_shell_auth_origin_and_secret_validation(setup_client):
    client, service = setup_client
    for path in ("/setup", "/setup.js", "/kite-callback.js"):
        r = client.get(path)
        assert r.status_code == 200
        assert r.headers["Cache-Control"] == "no-store"
        assert "default-src 'self'" in r.headers["Content-Security-Policy"]
    assert client.get("/api/setup").status_code == 401
    body = {"api_key": "unitkey", "api_secret": "unitsecret"}
    assert client.post("/api/setup/credentials", json=body).status_code == 401
    assert (
        client.post(
            "/api/setup/credentials", headers={**AUTH, "Origin": "https://evil.test"}, json=body
        ).status_code
        == 403
    )
    for invalid in ({**body, "unknown": "sensitivevalue"}, {"api_key": body}, ["sensitivevalue"]):
        r = client.post("/api/setup/credentials", headers=AUTH, json=invalid)
        assert r.status_code == 409
        assert "sensitivevalue" not in r.text and "unitsecret" not in r.text
    r = client.post(
        "/api/setup/credentials", headers=AUTH, content='{"api_secret":"' + "x" * 9000 + '"}'
    )
    assert r.status_code == 409 and "xxx" not in r.text
    assert not service.path.exists()


def test_full_browser_setup_flow_is_readonly_for_finances(setup_client, monkeypatch):
    client, service = setup_client
    upstream = Mock()
    upstream.get_instruments.return_value = []
    monkeypatch.setattr("trading_agent.api.setup.ReadOnlyKite", lambda *args: upstream)
    monkeypatch.setattr("trading_agent.api.setup.exchange_token", lambda *args: "sessionvalue")
    monkeypatch.setattr("trading_agent.api.setup.QuoteStream", lambda *a, **k: Mock())
    before = client.get("/api/status", headers=AUTH).json()
    for operation, body in (
        ("credentials", {"api_key": "unitkey", "api_secret": "unitsecret"}),
        ("symbols", {"symbols": ["DEMO", "SECOND"]}),
    ):
        r = client.post("/api/setup/" + operation, headers=AUTH, json=body)
        assert r.status_code == 200, r.text
        assert "unitsecret" not in r.text
    login = client.post("/api/setup/login", headers=AUTH, json={}).json()
    r = client.post(
        "/api/setup/exchange",
        headers=AUTH,
        json={"request_token": "onetimerequest", "state": login["state"]},
    )
    assert r.status_code == 200 and "sessionvalue" not in r.text
    assert (
        client.post(
            "/api/setup/exchange",
            headers=AUTH,
            json={"request_token": "onetimerequest", "state": login["state"]},
        ).status_code
        == 409
    )
    for operation in ("profile", "catalog", "connect", "disconnect"):
        r = client.post("/api/setup/" + operation, headers=AUTH, json={})
        assert r.status_code == 200, r.text
    after = client.get("/api/status", headers=AUTH).json()
    for key in ("cash", "fees", "positions", "reserved_cash", "reserved_risk"):
        assert after[key] == before[key]
    assert client.get("/api/paper/orders", headers=AUTH).json() == []
    assert not service.engine.faulted


def test_upstream_failure_is_redacted_without_disabling_existing_risk_engine(
    setup_client, monkeypatch
):
    client, service = setup_client
    monkeypatch.setattr(service, "broker", Mock(side_effect=RuntimeError("private-token-value")))
    r = client.post("/api/setup/profile", headers=AUTH, json={})
    assert r.status_code == 409 and "private-token-value" not in r.text
    assert not service.engine.faulted


def test_operator_help_explicitly_distinguishes_broker_tokens(setup_client):
    client, _ = setup_client
    for path in ("/", "/portfolio", "/setup"):
        text = client.get(path).text
        assert "TRADING_OPERATOR_TOKEN" in text
        assert "Zerodha" in text
    assert client.post("/api/live/orders", headers=AUTH).status_code == 404


def test_calendar_api_requires_explicit_attestation_and_preserves_existing_definitions(
    setup_client,
):
    client, service = setup_client
    service.engine.calendar.sources = {
        day: "invented session" for day in service.engine.calendar.sessions
    }
    body = {
        "date": "2026-10-22",
        "open": "09:15",
        "close": "15:30",
        "source": "invented reviewed NSE notice",
        "reviewed": True,
    }
    assert (
        client.post(
            "/api/setup/session", headers=AUTH, json={**body, "reviewed": "true"}
        ).status_code
        == 409
    )
    response = client.post("/api/setup/session", headers=AUTH, json=body)
    assert response.status_code == 200
    original = service.engine.settings.calendar
    assert client.post("/api/setup/session", headers=AUTH, json=body).status_code == 200
    assert service.engine.settings.calendar == original
    assert (
        client.post("/api/setup/session", headers=AUTH, json={**body, "close": "15:00"}).status_code
        == 409
    )
    assert Decimal(service.engine.snapshot(NOW)["cash"]) == Decimal("25000.00")


def test_setup_disabled_for_apps_without_the_manual_manager(engine):
    with TestClient(create_app(engine, background=False), base_url="http://127.0.0.1") as client:
        assert client.get("/setup").status_code == 200
        response = client.get("/api/setup", headers=AUTH)
        assert response.status_code == 409
        assert "manual service" in response.json()["detail"]


def test_open_browser_uses_only_local_url(engine, monkeypatch):
    timer = Mock()
    monkeypatch.setattr("trading_agent.api.app.threading.Timer", timer)
    with TestClient(
        create_app(engine, background=False, open_browser=True), base_url="http://127.0.0.1"
    ):
        timer.return_value.start.assert_called_once()
        assert timer.call_args.kwargs["args"] == ["http://127.0.0.1:8000/"]
