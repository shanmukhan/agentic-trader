import json
import subprocess
import sys
from datetime import timedelta

import pytest
from conftest import TOKEN, candidate
from fastapi.testclient import TestClient

from trading_agent.api.app import create_app
from trading_agent.main import execute, open_automated, parser
from trading_agent.paper.demo import INSTRUMENT, SIGNAL, WARM, demo_quote, prepare_signal, warmup
from trading_agent.persistence.database import Database
from trading_agent.settings import Settings

AUTH = {"Authorization": "Bearer " + TOKEN}


def test_authenticated_arm_disarm_readiness_and_manual_entry_block(paper_factory):
    feed = paper_factory()
    current = [WARM]
    feed.connection(True, WARM)
    feed.on_quote(demo_quote(WARM), WARM)
    app = create_app(feed.engine, clock=lambda: current[0], background=False, automation=feed)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        assert client.get("/api/paper/automation").status_code == 401
        assert client.post("/api/paper/automation/arm", headers=AUTH).status_code == 409
        feed.on_candles(warmup(), WARM)
        assert client.get("/ready").status_code == 503
        response = client.post("/api/paper/automation/arm", headers=AUTH)
        assert response.status_code == 200 and response.json()["armed"]
        assert client.get("/ready").status_code == 200 and not feed.engine.faulted
        assert client.get("/api/paper/automation", headers=AUTH).json()["armed"]
        assert (
            client.post(
                "/api/paper/intents", headers=AUTH, json=candidate(now=WARM).model_dump(mode="json")
            ).status_code
            == 409
        )
        assert (
            client.post(
                "/api/paper/automation/disarm", headers={**AUTH, "Origin": "https://evil.example"}
            ).status_code
            == 403
        )
        assert client.post("/api/paper/automation/disarm", headers=AUTH).status_code == 200
        assert client.get("/ready").status_code == 503
        assert client.post("/api/paper/automation/arm", headers=AUTH).status_code == 200
        assert client.post("/api/control/kill", headers=AUTH).status_code == 200
        assert not feed.armed
        assert client.post("/api/control/reset", headers=AUTH).status_code == 200
        assert not feed.armed and client.get("/ready").status_code == 503
        assert "Arm paper automation" in client.get("/").text
    assert feed.closed and not feed.armed


def test_manual_service_cannot_arm_and_background_watchdog_disarms_stale_feed(
    paper_factory, engine
):
    with TestClient(
        create_app(engine, clock=lambda: WARM, background=False), base_url="http://127.0.0.1"
    ) as client:
        assert not client.get("/api/paper/automation", headers=AUTH).json()["enabled"]
        assert client.post("/api/paper/automation/arm", headers=AUTH).status_code == 409
    feed = paper_factory()
    prepare_signal(feed)
    now = SIGNAL + timedelta(seconds=6)
    import threading

    observed = threading.Event()
    original = feed.tick

    def tick(now, **kwargs):
        original(now, **kwargs)
        observed.set()

    feed.tick = tick
    with TestClient(
        create_app(feed.engine, clock=lambda: now, automation=feed), base_url="http://127.0.0.1"
    ):
        assert observed.wait(3)
        assert not feed.armed and feed.engine.orders()[0]["state"] == "CANCELLED"


def test_paper_cli_demo_reports_and_source_preserving_report(tmp_path):
    path = tmp_path / "demo"
    service = tmp_path / "service.sqlite3"
    config = tmp_path / "paper.toml"
    config.write_text(f'database="{service}"\n')
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "trading_agent.main",
            "--config",
            str(config),
            "paper-demo",
            "--directory",
            str(path),
        ],
        text=True,
        capture_output=True,
        check=True,
    )
    summary = json.loads(result.stdout)
    assert summary["synthetic"] and not summary["ready_for_live"]
    assert set(summary["scenarios"]) == {"partial_fills", "disconnect", "silence", "restart"}
    assert summary["scenarios"]["partial_fills"]["cash"] == "25023.24"
    assert summary["scenarios"]["restart"]["cash"] == "25000"
    assert not summary["scenarios"]["restart"]["gates"]["clean_shutdowns"]
    assert not service.exists()
    source_config = tmp_path / "source.toml"
    source_config.write_text(f'database="{path / "partial_fills/paper.sqlite3"}"\n')
    report = execute(
        parser().parse_args(
            ["--config", str(source_config), "paper-report", "--output", str(tmp_path / "report")]
        )
    )
    assert not report["ready_for_live"] and (tmp_path / "report/report.md").is_file()
    assert not report["gates"]["model_bound"]


@pytest.mark.parametrize("options", [[], ["--model", "not-a-model", "--rule-only"]])
def test_automation_requires_explicit_model_choice_and_transport(tmp_path, options):
    from pydantic import SecretStr

    policy = Settings(database=tmp_path / "account", operator_token=SecretStr(TOKEN))
    args = parser().parse_args(["serve", "--automate", "--stream", *options])
    with pytest.raises(ValueError, match="exactly one"):
        open_automated(policy, args)
    assert not policy.database.exists()
    args = parser().parse_args(["serve", "--automate", "--rule-only"])
    with pytest.raises(ValueError, match="--stream"):
        open_automated(policy, args)


def test_configured_rule_feed_opens_dedicated_disarmed_account(tmp_path, monkeypatch):
    from pydantic import SecretStr

    calendar = tmp_path / "sessions.csv"
    calendar.write_text("date,open,close,source\n2026-10-20,09:15,15:30,reviewed test\n")
    settings = Settings(
        database=tmp_path / "account.sqlite3",
        calendar=calendar,
        stream_tokens=(1,),
        operator_token=SecretStr(TOKEN),
    )
    db = Database(settings.database, settings.starting_cash)
    with db.transaction() as tx:
        tx.execute("INSERT INTO instruments VALUES (?,?,?)", (INSTRUMENT.symbol, 1, ".05"))
    db.close()
    monkeypatch.setattr("trading_agent.main.clock", lambda: WARM)
    args = parser().parse_args(["serve", "--stream", "--automate", "--rule-only"])
    db, engine, feed = open_automated(settings, args)
    try:
        assert not feed.armed and not feed.synthetic and not engine.model
        assert feed.digest == engine.automation
        with pytest.raises(ValueError, match="source"):
            feed.on_quote(demo_quote(WARM), WARM)
    finally:
        db.close()


def test_paper_init_creates_bound_account_without_manual_model_binding(
    tmp_path, monkeypatch, research_model
):
    from trading_agent.ml.inference import ResearchModel

    policy_file = tmp_path / "paper.toml"
    database = tmp_path / "auto.sqlite3"
    calendar = tmp_path / "sessions.csv"
    calendar.write_text("date,open,close,source\n2026-10-20,09:15,15:30,reviewed fixture\n")
    policy_file.write_text(f'database="{database}"\ncalendar="{calendar}"\nstream_tokens=[1]\n')
    monkeypatch.setenv("TRADING_OPERATOR_TOKEN", TOKEN)
    monkeypatch.setattr("trading_agent.main.clock", lambda: WARM)
    from unittest.mock import Mock

    broker = Mock()
    broker.get_instruments.return_value = [INSTRUMENT]
    monkeypatch.setattr("trading_agent.main.ReadOnlyKite.from_environment", lambda: broker)
    verified = ResearchModel(
        research_model.artifact.model_copy(update={"synthetic": False}), research_model.version
    )
    # The loader is mocked at this service boundary; artifact validation has its own suite.
    monkeypatch.setattr("trading_agent.ml.inference.load_model", lambda *a, **k: verified)
    args = parser().parse_args(
        ["--config", str(policy_file), "paper-init", "--model", "reviewed-model"]
    )
    result = execute(args)
    assert result["cash"] == "25000" and not result["armed"]
    assert result["model_sha256"] == verified.version
    with pytest.raises(ValueError, match="new database"):
        execute(args)
    broker.get_instruments.assert_called_once()
    settings = Settings.load(policy_file)
    serving = parser().parse_args(["serve", "--stream", "--automate", "--model", "reviewed-model"])
    db, engine, feed = open_automated(settings, serving)
    try:
        assert engine.model and engine.model.version == verified.version
        assert not feed.armed and not feed.synthetic and not engine.orders()
        with db.transaction() as tx:
            assert (
                tx.execute("SELECT value FROM meta WHERE key='model_version'").fetchone()[0]
                == verified.version
            )
    finally:
        db.close()


def test_connected_service_refuses_actual_synthetic_artifact(ml_demo, tmp_path):
    from pydantic import SecretStr

    settings = Settings(database=tmp_path / "never-created", operator_token=SecretStr(TOKEN))
    args = parser().parse_args(
        ["serve", "--stream", "--automate", "--model", str(ml_demo[0] / "model")]
    )
    with pytest.raises(ValueError, match="synthetic"):
        open_automated(settings, args)
    assert not settings.database.exists()
