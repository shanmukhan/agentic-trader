import hashlib
import json
import subprocess
import sys
from datetime import timedelta

import pytest
from conftest import NOW, TOKEN, candidate, quote
from fastapi.testclient import TestClient

from trading_agent.api.app import create_app
from trading_agent.backtesting.report import journal_digest
from trading_agent.execution.delivery import HoldingReview
from trading_agent.observability.preflight import preflight
from trading_agent.paper.long_term_report import long_term_report

AUTH = {"Authorization": "Bearer " + TOKEN}


def test_long_term_api_review_entry_overnight_and_individual_exit(long_term_factory):
    engine = long_term_factory()
    current = [NOW]
    with TestClient(
        create_app(engine, clock=lambda: current[0], background=False), base_url="http://127.0.0.1"
    ) as client:
        payload = {
            "symbol": "NSE:DEMO",
            "session_date": "2026-10-20",
            "no_corporate_action": True,
            "reference": "synthetic reviewed raw basis",
        }
        assert client.post("/api/paper/long-term/reviews", json=payload).status_code == 401
        assert (
            client.post(
                "/api/paper/long-term/reviews",
                headers={**AUTH, "Origin": "https://evil.example"},
                json=payload,
            ).status_code
            == 403
        )
        assert (
            client.post(
                "/api/paper/long-term/reviews",
                headers=AUTH,
                json={**payload, "no_corporate_action": 1},
            ).status_code
            == 422
        )
        assert (
            client.post("/api/paper/long-term/reviews", headers=AUTH, json=payload).status_code
            == 200
        )
        engine.ingest(quote(), NOW)
        response = client.post(
            "/api/paper/intents",
            headers=AUTH,
            json=candidate(stop="490", target="600").model_dump(mode="json"),
        )
        assert response.json()["state"] == "ACCEPTED"
        current[0] += timedelta(seconds=1)
        engine.ingest(quote(1), current[0])
        current[0] = NOW + timedelta(days=1)
        engine.poll(current[0])
        view = client.get("/api/console", headers=AUTH).json()
        assert view["account"]["investment_horizon"] == "long_term"
        assert view["account"]["positions"] and not view["account"]["kill"]
        assert "LONG_TERM_REVIEW_REQUIRED" in view["entry_readiness"]["reasons"]
        assert (
            client.post(
                "/api/paper/long-term/reviews",
                headers=AUTH,
                json={**payload, "session_date": "2026-10-21"},
            ).status_code
            == 200
        )
        engine.ingest(quote(base=current[0]), current[0])
        response = client.post(
            "/api/paper/long-term/exit", headers=AUTH, json={"symbol": "NSE:DEMO"}
        )
        assert response.json()["exit_queued"]
        repeated = client.post(
            "/api/paper/long-term/exit", headers=AUTH, json={"symbol": "NSE:DEMO"}
        )
        assert repeated.json()["order"]["id"] == response.json()["order"]["id"]
        assert (
            client.post(
                "/api/paper/long-term/exit",
                headers=AUTH,
                json={"symbol": "NSE:DEMO", "quantity": 100},
            ).status_code
            == 422
        )
        next_quote = quote(1, base=current[0])
        current[0] += timedelta(seconds=1)
        engine.ingest(next_quote, current[0])
        assert client.get("/api/status", headers=AUTH).json()["positions"] == []
        assert (
            client.post(
                "/api/paper/long-term/exit", headers=AUTH, json={"symbol": "NSE:DEMO"}
            ).status_code
            == 404
        )


def test_intraday_account_refuses_delivery_controls(engine):
    with TestClient(
        create_app(engine, clock=lambda: NOW, background=False), base_url="http://127.0.0.1"
    ) as client:
        payload = {
            "symbol": "NSE:DEMO",
            "session_date": "2026-10-20",
            "no_corporate_action": True,
            "reference": "reviewed test",
        }
        assert (
            client.post("/api/paper/long-term/reviews", headers=AUTH, json=payload).status_code
            == 409
        )
        assert (
            client.post(
                "/api/paper/long-term/exit", headers=AUTH, json={"symbol": "NSE:DEMO"}
            ).status_code
            == 409
        )


def test_quarantine_cannot_be_cleared_by_a_later_api_review(long_term_factory):
    engine = long_term_factory()
    with TestClient(
        create_app(engine, clock=lambda: NOW, background=False), base_url="http://127.0.0.1"
    ) as client:
        payload = {
            "symbol": "NSE:DEMO",
            "session_date": "2026-10-20",
            "no_corporate_action": False,
            "reference": "known action",
        }
        assert (
            client.post("/api/paper/long-term/reviews", headers=AUTH, json=payload).status_code
            == 200
        )
        assert (
            client.post(
                "/api/paper/long-term/reviews",
                headers=AUTH,
                json={**payload, "no_corporate_action": True},
            ).status_code
            == 409
        )
        assert not engine.faulted


def test_long_term_report_preserves_pending_orders_and_emits_private_hashed_evidence(
    long_term_factory, tmp_path
):
    engine = long_term_factory()
    engine.review_holding(
        HoldingReview(
            symbol="NSE:DEMO",
            session_date=NOW.date(),
            no_corporate_action=True,
            reference="test review",
        ),
        NOW,
    )
    engine.ingest(quote(), NOW)
    engine.submit(candidate(stop="490", target="600"), NOW)
    before = journal_digest(engine.db)
    order = engine.orders()
    output = tmp_path / "evidence"
    result = long_term_report(engine.db, output)
    assert result["metrics"]["pending_orders"] == 1 and result["synthetic"]
    assert not result["ready_for_live"] and not result["settlement_verified"]
    assert engine.orders() == order and before == journal_digest(engine.db)
    manifest = json.loads((output / "manifest.json").read_text())
    for name, digest in manifest["sha256"].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == digest
        assert (output / name).stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        long_term_report(engine.db, output)


def test_delivery_preflight_matches_horizon_costs_without_recovering(long_term_factory, tmp_path):
    engine = long_term_factory()
    path = tmp_path / "calendar.csv"
    path.write_text("date,open,close,source\n2026-10-20,09:15,15:30,reviewed fixture\n")
    tmp_path.chmod(0o700)
    settings = engine.settings.model_copy(update={"calendar": path})
    report = preflight(settings, NOW)
    assert report["local_checks_passed"]
    assert report["account"]["investment_horizon"] == "long_term"
    mismatch = preflight(settings.model_copy(update={"investment_horizon": "intraday"}), NOW)
    states = {check["id"]: check["state"] for check in mismatch["checks"]}
    assert states["horizon_matches"] == "blocked" and states["charges_match"] == "blocked"


def test_cli_long_term_demo_and_report_source_are_isolated(tmp_path):
    directory = tmp_path / "drills"
    cmd = [sys.executable, "-m", "trading_agent.main"]
    result = subprocess.run(
        cmd + ["long-term-demo", "--directory", str(directory)],
        capture_output=True,
        text=True,
        check=True,
    )
    summary = json.loads(result.stdout)
    assert summary["synthetic"] and not summary["ready_for_live"]
    assert summary["scenarios"]["overnight_restart"]["cash"] == "25379.54"
    assert summary["scenarios"]["opening_gap"]["cash"] == "24261.40"
    assert summary["scenarios"]["corporate_action"]["positions"] == 1
    config = directory / "overnight_restart" / "account.toml"
    report = subprocess.run(
        cmd + ["--config", str(config), "long-term-report", "--output", str(tmp_path / "report")],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(report.stdout)["dp_days"] == 1
    failed = subprocess.run(
        cmd + ["long-term-demo", "--directory", str(directory)], capture_output=True, text=True
    )
    assert failed.returncode == 1 and "Traceback" not in failed.stderr


@pytest.mark.parametrize("command", ["backtest", "ml-demo", "paper-init", "serve"])
def test_intraday_automation_commands_refused_with_long_term_config(tmp_path, command):
    config = tmp_path / "account.toml"
    db = tmp_path / "must-not-exist.sqlite3"
    config.write_text('investment_horizon="long_term"\ndatabase=' + json.dumps(str(db)) + "\n")
    args = {
        "backtest": ["absent-dataset", "--output", str(tmp_path / "output")],
        "ml-demo": [],
        "paper-init": ["--rule-only"],
        "serve": ["--stream", "--automate", "--rule-only"],
    }[command]
    result = subprocess.run(
        [sys.executable, "-m", "trading_agent.main", "--config", str(config), command, *args],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1 and "Traceback" not in result.stderr
    assert not db.exists()
