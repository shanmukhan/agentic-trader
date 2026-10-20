import json
import subprocess
import sys
from datetime import timedelta

from conftest import NOW, TOKEN, candidate
from fastapi.testclient import TestClient

from trading_agent.api.app import create_app

AUTH = {"Authorization": "Bearer " + TOKEN}


def test_console_is_authenticated_consistent_bounded_and_read_only(engine):
    for i in range(202):
        engine.submit(candidate(f"entry-{i}"), NOW)
    before = engine.orders()
    with TestClient(
        create_app(engine, clock=lambda: NOW, background=False), base_url="http://127.0.0.1"
    ) as client:
        assert client.get("/api/console").status_code == 401
        response = client.get("/api/console", headers=AUTH)
        assert response.status_code == 200
        view = response.json()
        assert view["schema_version"] == 1 and view["observed_at"].startswith("2026-10-20T04:30")
        assert view["account"]["mode"] == "paper"
        assert len(view["orders"]) == view["order_limit"] == 200
        assert view["orders_truncated"]
        assert view["orders"][0]["id"] == "entry-201"
        assert view["quotes"][0]["fresh"]
        assert view["entry_readiness"] == {"ready": True, "reasons": []}
        assert response.headers["Cache-Control"] == "no-store"
        assert TOKEN not in response.text
    assert engine.orders() == before


def test_console_disconnected_stale_and_kill_reasons(engine):
    engine.set_connected(False)
    engine.kill(NOW)
    with TestClient(
        create_app(engine, clock=lambda: NOW + timedelta(seconds=6), background=False),
        base_url="http://127.0.0.1",
    ) as client:
        view = client.get("/api/console", headers=AUTH).json()
        assert not view["entry_readiness"]["ready"]
        assert {"FEED_DISCONNECTED", "KILL_SWITCH", "STALE_OR_MISSING_QUOTE"} <= set(
            view["entry_readiness"]["reasons"]
        )
        assert not view["quotes"][0]["fresh"]


def test_console_automation_stays_disarmed_and_poll_never_arms(paper_factory):
    from trading_agent.paper.demo import WARM, demo_quote, warmup

    feed = paper_factory()
    feed.connection(True, WARM)
    feed.on_quote(demo_quote(WARM), WARM)
    feed.on_candles(warmup(), WARM)
    before = dict(feed.counts)
    with TestClient(
        create_app(feed.engine, clock=lambda: WARM, background=False, automation=feed),
        base_url="http://127.0.0.1",
    ) as client:
        view = client.get("/api/console", headers=AUTH).json()
        assert view["automation"]["enabled"] and not view["automation"]["armed"]
        assert "AUTOMATION_DISARMED" in view["entry_readiness"]["reasons"]
        assert dict(feed.counts) == before
        assert not feed.armed


def test_static_assets_private_headers_and_no_external_scripts(engine):
    with TestClient(
        create_app(engine, clock=lambda: NOW, background=False), base_url="http://127.0.0.1"
    ) as client:
        html = client.get("/")
        assert 'name="viewport"' in html.text
        assert 'id="confirm"' in html.text
        assert "style-src 'self'" in html.headers["content-security-policy"]
        assert "unsafe-inline" not in html.headers["content-security-policy"]
        for path, content_type in [
            ("/dashboard.js", "application/javascript"),
            ("/dashboard.css", "text/css"),
        ]:
            response = client.get(path)
            assert response.status_code == 200
            assert content_type in response.headers["content-type"]
            assert response.headers["cache-control"] == "no-store"
        script = client.get("/dashboard.js").text
        for forbidden in ("innerHTML", "localStorage", "sessionStorage", "document.cookie"):
            assert forbidden not in script
        assert "@media(max-width:640px)" in client.get("/dashboard.css").text
        assert (
            client.get("/api/console", headers={**AUTH, "Host": "evil.example"}).status_code == 400
        )


def test_preflight_cli_does_not_initialize_missing_account_or_expose_secrets(tmp_path):
    config = tmp_path / "config.toml"
    missing = tmp_path / "missing" / "paper.db"
    config.write_text(f"database = {json.dumps(str(missing))}\n")
    output = tmp_path / "evidence"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "trading_agent.main",
            "--config",
            str(config),
            "preflight",
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    report = json.loads(result.stdout)
    assert not report["local_checks_passed"] and not report["ready_for_live"]
    assert not missing.parent.exists()
    assert json.loads((output / "manifest.json").read_text())["state"] == "finished"
    repeated = subprocess.run(
        [
            sys.executable,
            "-m",
            "trading_agent.main",
            "--config",
            str(config),
            "preflight",
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
    )
    assert repeated.returncode == 1 and "Traceback" not in repeated.stderr


def test_strict_preflight_keeps_report_and_exits_two_for_blocked_checks(tmp_path):
    config = tmp_path / "config.toml"
    config.write_text(f"database = {json.dumps(str(tmp_path / 'absent.db'))}\n")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "trading_agent.main",
            "--config",
            str(config),
            "preflight",
            "--strict",
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert not json.loads(result.stdout)["local_checks_passed"]
    assert not result.stderr
