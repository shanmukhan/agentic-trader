import json
import os
import subprocess
import sys
from datetime import timedelta

from conftest import NOW, TOKEN, candidate, quote
from fastapi.testclient import TestClient

from trading_agent.api.app import create_app

AUTH = {"Authorization": "Bearer " + TOKEN}


def test_authenticated_operator_flow(engine):
    current = [NOW]
    app = create_app(engine, clock=lambda: current[0], background=False)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        assert client.get("/health").json() == {"status": "alive", "mode": "paper"}
        assert client.get("/ready").status_code == 200
        assert client.get("/api/status").status_code == 401
        response = client.post(
            "/api/paper/intents", headers=AUTH, json=candidate().model_dump(mode="json")
        )
        assert response.json()["state"] == "ACCEPTED"
        assert (
            client.post(
                "/api/paper/intents",
                headers=AUTH,
                json=candidate(target="520").model_dump(mode="json"),
            ).status_code
            == 409
        )
        current[0] += timedelta(seconds=1)
        engine.ingest(quote(1), current[0])
        assert client.get("/api/status", headers=AUTH).json()["positions"][0]["quantity"] == 10
        assert client.post("/api/control/kill", headers=AUTH).json()["kill"]
        assert client.post("/api/control/reset", headers=AUTH).status_code == 409
        current[0] += timedelta(seconds=1)
        engine.ingest(quote(2), current[0])
        assert client.post("/api/control/reset", headers=AUTH).status_code == 200
        assert client.get("/api/status", headers=AUTH).json()["positions"] == []
        assert client.get("/api/paper/orders", headers=AUTH).json()


def test_cross_origin_host_validation_and_no_live_route(engine):
    with TestClient(
        create_app(engine, clock=lambda: NOW, background=False), base_url="http://127.0.0.1"
    ) as client:
        assert (
            client.post(
                "/api/control/kill", headers={**AUTH, "Origin": "https://evil.example"}
            ).status_code
            == 403
        )
        assert (
            client.get("/api/status", headers={**AUTH, "Host": "evil.example"}).status_code == 400
        )
        assert client.post("/api/live/orders", headers=AUTH).status_code == 404
        assert client.get("/openapi.json").status_code == 404
        response = client.get("/")
        assert response.status_code == 200 and "Paper trading" in response.text
        assert response.headers["Cache-Control"] == "no-store"
        assert client.get("/dashboard.js").status_code == 200


def test_app_starts_without_broker_or_operator_credentials(engine_factory):
    from pydantic import SecretStr

    engine = engine_factory()
    engine.settings = engine.settings.model_copy(update={"operator_token": SecretStr("")})
    engine.set_connected(False)
    with TestClient(
        create_app(engine, clock=lambda: NOW, background=False), base_url="http://127.0.0.1"
    ) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/ready").status_code == 503
        assert client.get("/api/status").status_code == 503


def test_cli_demo_and_non_paper_mode(tmp_path):
    command = [
        sys.executable,
        "-m",
        "trading_agent.main",
        "demo",
        "--directory",
        str(tmp_path / "demo"),
    ]
    result = subprocess.run(command, text=True, capture_output=True, check=True)
    report = json.loads(result.stdout)
    assert report["snapshot"]["positions"] == []
    assert len(report["fills"]) == 2
    assert (tmp_path / "demo" / "events.jsonl").exists()
    result = subprocess.run(
        command, text=True, capture_output=True, env={**os.environ, "TRADING_MODE": "live"}
    )
    assert result.returncode == 1 and "Traceback" not in result.stderr


def test_unexpected_failure_latches_fault_and_redacts_response(engine, monkeypatch):
    def broken(*args):
        raise RuntimeError("private-third-party-detail")

    monkeypatch.setattr(engine, "snapshot", broken)
    app = create_app(engine, clock=lambda: NOW, background=False)
    with TestClient(app, base_url="http://127.0.0.1", raise_server_exceptions=False) as client:
        result = client.get("/api/status", headers=AUTH)
        assert result.status_code == 503 and "private-third-party-detail" not in result.text
        assert engine.faulted and not engine.connected


def test_watchdog_queues_close_without_ticks(engine, monkeypatch):
    import threading

    engine.submit(candidate(), NOW)
    engine.ingest(quote(1), NOW + timedelta(seconds=1))
    closing = NOW.replace(hour=9, minute=45)
    observed = threading.Event()
    original = engine.poll

    def poll(now):
        original(now)
        observed.set()

    monkeypatch.setattr(engine, "poll", poll)
    with TestClient(
        create_app(engine, clock=lambda: closing), base_url="http://127.0.0.1"
    ) as client:
        assert observed.wait(3), "background risk watchdog did not run"
        assert client.get("/health").status_code == 200
        assert engine.orders()[-1]["side"] == "SELL"
        assert engine.snapshot(closing)["positions"]
