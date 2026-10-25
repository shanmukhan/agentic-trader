import csv
import json
import sqlite3
import struct
import tomllib
from contextlib import closing, nullcontext
from decimal import Decimal
from unittest.mock import Mock

import pytest
from conftest import NOW, TOKEN, candidate
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
    stream = Mock()
    stream.diagnostics.return_value = {"state": "connecting", "failures": 0}
    monkeypatch.setattr("trading_agent.api.setup.QuoteStream", lambda *a, **k: stream)
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


def test_symbol_selection_roundtrips_toml_and_preserves_persisted_ledger(setup_client):
    client, service = setup_client
    content = service.config.read_text().replace(
        "stream_tokens = []",
        '"stream_tokens" = [\n] # reviewed feed selection',
    )
    service.config.write_text("# private account settings\n" + content)

    def persisted_finances():
        with closing(sqlite3.connect(service.engine.settings.database)) as connection:
            return {
                table: connection.execute(f"SELECT * FROM {table}").fetchall()
                for table in ("meta", "orders", "fills", "positions")
            }

    before = persisted_finances()
    response = client.post("/api/setup/symbols", headers=AUTH, json={"symbols": ["DEMO", "SECOND"]})
    assert response.status_code == 200, response.text
    saved = service.config.read_text()
    assert saved.startswith("# private account settings\n")
    assert "# reviewed feed selection" in saved
    assert tomllib.loads(saved)["stream_tokens"] == [1, 2]
    assert service.engine.settings.stream_tokens == (1, 2)
    assert persisted_finances() == before


def test_configured_maximum_selection_exceeds_old_body_limit_without_relaxing_secrets(setup_client):
    client, service = setup_client
    service.engine.settings = service.engine.settings.model_copy(update={"stream_limit": 3000})
    service.config.write_text(
        service.config.read_text().replace("stream_limit = 10", "stream_limit = 3000")
    )
    catalog = [(f"NSE:CAPACITY{index:022d}", 513 + 256 * index, ".05") for index in range(3000)]
    with service.engine.db.transaction() as tx:
        tx.executemany("INSERT INTO instruments VALUES (?,?,?)", catalog)

    def persisted_finances():
        with closing(sqlite3.connect(service.engine.settings.database)) as connection:
            return {
                table: connection.execute(f"SELECT * FROM {table}").fetchall()
                for table in ("meta", "orders", "fills", "positions", "events")
            }

    before = persisted_finances()
    symbols = [symbol for symbol, _, _ in catalog]
    content = json.dumps({"symbols": symbols}).encode()
    assert 8192 < len(content) < 128 * 1024
    response = client.post("/api/setup/symbols", headers=AUTH, content=content)
    assert response.status_code == 200, response.text
    assert response.json()["stream_limit"] == 3000 and len(response.json()["selected"]) == 3000
    saved = service.config.read_bytes()
    assert tomllib.loads(saved.decode())["stream_tokens"] == [token for _, token, _ in catalog]
    assert service.engine.settings.stream_tokens == tuple(token for _, token, _ in catalog)
    assert persisted_finances() == before

    for operation, body in (
        ("symbols", json.dumps({"symbols": symbols + ["NSE:EXTRA"]})),
        ("symbols", json.dumps({"symbols": ["SENSITIVE" * 17000]})),
        ("credentials", json.dumps({"api_secret": "SENSITIVE" * 1100})),
        ("exchange", json.dumps({"request_token": "SENSITIVE" * 1100})),
    ):
        rejected = client.post("/api/setup/" + operation, headers=AUTH, content=body)
        assert rejected.status_code == 409 and "SENSITIVE" not in rejected.text
        assert service.config.read_bytes() == saved
        assert persisted_finances() == before


def test_empty_depth_keeps_feed_online_without_filling_pending_order(setup_client, monkeypatch):
    import websockets.sync.client

    from trading_agent.broker.readonly_kite import QuoteStream

    client, service = setup_client
    service.select_symbols({"symbols": ["DEMO"]})
    service.values = {"api_key": "unitkey", "api_secret": "unitsecret", "access_token": "session"}
    service.engine.submit(candidate(), NOW)
    service.engine.set_connected(False)
    before = client.get("/api/status", headers=AUTH).json()
    orders = client.get("/api/paper/orders", headers=AUTH).json()
    monkeypatch.setattr("trading_agent.api.setup.ReadOnlyKite", lambda *args: Mock())
    monkeypatch.setattr(QuoteStream, "start", lambda self: None)
    assert client.post("/api/setup/connect", headers=AUTH, json={}).status_code == 200
    packet = bytearray(184)
    for offset, value in ((0, 1), (4, 50000), (60, int(NOW.timestamp())), (64, 100), (68, 49995)):
        struct.pack_into(">I", packet, offset, value)
    # Missing ask price/quantity observed on the real after-hours feed.
    message = struct.pack(">HH", 1, 184) + packet
    socket = Mock()
    calls = 0
    observed = []

    def recv(**kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return message
        assert service.stream is not None
        observed.append(
            (
                client.get("/api/setup", headers=AUTH).json(),
                set(service.engine.seen_symbols),
                set(service.engine.bad_symbols),
                client.get("/api/paper/orders", headers=AUTH).json(),
            )
        )
        service.stream._stop.set()
        return b"\x00"

    socket.recv.side_effect = recv
    monkeypatch.setattr(websockets.sync.client, "connect", lambda *a, **k: nullcontext(socket))
    assert service.stream is not None
    monkeypatch.setattr(service.stream._stop, "wait", lambda timeout: service.stream._stop.set())
    service.stream._run()
    assert calls == 2 and socket.send.call_count == 2
    assert len(observed) == 1
    status, seen, bad, observed_orders = observed[0]
    assert status["feed_connected"] and status["stream_requested"]
    assert status["feed_diagnostics"]["state"] == "connected"
    assert status["feed_diagnostics"]["unusable_quotes"] == 1
    assert status["feed_diagnostics"]["last_message_at"] == NOW.isoformat()
    assert status["feed_diagnostics"]["failures"] == 0
    assert not seen and bad == {"NSE:DEMO"} and observed_orders == orders
    after = client.get("/api/status", headers=AUTH).json()
    for field in ("cash", "fees", "positions", "reserved_cash", "reserved_risk"):
        assert after[field] == before[field]
    assert Decimal(after["cash"]) == Decimal("25000.00")
    assert Decimal(after["fees"]) == Decimal("0")
    assert client.get("/api/paper/orders", headers=AUTH).json() == orders
    assert not service.engine.faulted


def test_upstream_failure_is_redacted_without_disabling_existing_risk_engine(
    setup_client, monkeypatch
):
    client, service = setup_client
    monkeypatch.setattr(service, "broker", Mock(side_effect=RuntimeError("private-token-value")))
    r = client.post("/api/setup/profile", headers=AUTH, json={})
    assert r.status_code == 409 and "private-token-value" not in r.text
    assert not service.engine.faulted


def test_saved_session_check_failure_and_retry_preserve_persisted_account(
    setup_client, monkeypatch
):
    client, service = setup_client
    service._save_values(
        {"api_key": "unitkey", "api_secret": "unitsecret", "access_token": "savedtoken"}
    )
    credentials = service.path.read_bytes()
    config = service.config.read_bytes()

    def persisted():
        with sqlite3.connect(service.engine.settings.database) as db:
            cash = db.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0]
            assert Decimal(cash) == Decimal("25000.00")
            return list(db.iterdump())

    before = persisted()
    upstream = Mock()
    monkeypatch.setattr(service, "broker", lambda: upstream)
    response = client.post("/api/setup/profile", headers=AUTH, json={})
    assert response.status_code == 200 and response.json()["profile_verified_this_run"]
    upstream.get_profile.side_effect = RuntimeError("private-upstream-savedtoken")
    response = client.post("/api/setup/profile", headers=AUTH, json={})
    assert response.status_code == 409 and "profile check failed" in response.json()["detail"]
    assert "savedtoken" not in response.text
    status = client.get("/api/setup", headers=AUTH).json()
    assert not status["profile_verified_this_run"] and status["access_token_available"]
    upstream.get_profile.side_effect = None
    response = client.post("/api/setup/profile", headers=AUTH, json={})
    assert response.status_code == 200 and response.json()["profile_verified_this_run"]
    assert "savedtoken" not in response.text and "unitsecret" not in response.text
    assert upstream.get_profile.call_count == 3
    assert persisted() == before
    assert service.path.read_bytes() == credentials and service.config.read_bytes() == config
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


def test_standard_hours_are_only_saved_with_review_and_do_not_change_accounting(setup_client):
    client, service = setup_client
    service.engine.calendar.sources = {
        day: "invented existing session" for day in service.engine.calendar.sessions
    }
    config_before = service.config.read_bytes()
    body = {
        "date": "2026-10-22",
        "open": "09:15",
        "close": "15:30",
        "source": "invented standard-hours review",
        "reviewed": False,
    }

    def persisted():
        with sqlite3.connect(service.engine.settings.database) as db:
            assert Decimal(
                db.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0]
            ) == Decimal("25000.00")
            return list(db.iterdump())

    before = persisted()
    response = client.post("/api/setup/session", headers=AUTH, json=body)
    assert response.status_code == 409
    assert service.config.read_bytes() == config_before and persisted() == before
    response = client.post("/api/setup/session", headers=AUTH, json={**body, "reviewed": True})
    assert response.status_code == 200
    with service.engine.settings.calendar.open(newline="") as file:
        saved = [row for row in csv.DictReader(file) if row["date"] == body["date"]]
    assert len(saved) == 1
    assert saved[0]["open"] == "09:15" and saved[0]["close"] == "15:30"
    assert saved[0]["source"] == body["source"]
    assert persisted() == before


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
        assert timer.call_args.kwargs["args"] == ["http://127.0.0.1:8000/workspace"]
