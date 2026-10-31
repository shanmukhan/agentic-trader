"""Fault-injection checks using invented account and source evidence."""

import json
from copy import deepcopy
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from preparation_support import TEST_NOW
from pydantic import ValidationError

from trading_agent.api.app import create_app
from trading_agent.desk.contracts import digest
from trading_agent.desk.preparation import DownloadRequest
from trading_agent.operations import supervisor
from trading_agent.operations.report import validate_download
from trading_agent.operations.schedule import ScheduledDownload


@pytest.fixture
def downloaded(preparation_factory):
    s = preparation_factory()
    s.setup.check_profile()
    s.prep.start(
        DownloadRequest(
            universe="nifty100", request_id="d" * 32, revision=s.desk.revision, acknowledged=True
        )
    )
    s.prep.thread.join(5)
    assert s.prep.state["state"] == "ready_for_review"
    return s


def test_source_date_history_and_snapshot_clocks_are_distinct(downloaded):
    s = downloaded
    valid = validate_download(s.prep, TEST_NOW)
    assert valid["same_ist_date"] and valid["coverage_valid"]
    tomorrow = validate_download(s.prep, TEST_NOW + timedelta(days=1))
    assert not tomorrow["same_ist_date"] and not tomorrow["coverage_valid"]
    after_close = TEST_NOW.replace(hour=12)
    assert not validate_download(s.prep, after_close)["coverage_valid"]
    s.prep.state["snapshot_at"] = (TEST_NOW + timedelta(seconds=1)).isoformat()
    with pytest.raises(ValueError, match="future source"):
        validate_download(s.prep, TEST_NOW)


@pytest.mark.parametrize("damage", ["duplicate", "missing", "future", "hash", "source", "symlink"])
def test_source_validator_rejects_broken_evidence(downloaded, damage, tmp_path):
    s = downloaded
    folder = s.prep.root / s.prep.state["job_id"]
    path = folder / "draft.json"
    draft = json.loads(path.read_text())
    if damage == "duplicate":
        draft["records"].append(draft["records"][0])
    elif damage == "missing":
        draft["eligible"].append({"symbol": "NSE:MISSING"})
    elif damage == "future":
        draft["records"][0]["price_available_at"] = (TEST_NOW + timedelta(seconds=1)).isoformat()
    elif damage == "hash":
        s.prep.state["preview_sha256"] = "0" * 64
    elif damage == "source":
        (folder / "holidays.json").write_text("{}")
    elif damage == "symlink":
        path.unlink()
        replacement = tmp_path / "replacement"
        replacement.write_text(json.dumps(draft))
        path.symlink_to(replacement)
    if damage not in {"hash", "source", "symlink"}:
        path.write_text(json.dumps(draft))
        s.prep.state["preview_sha256"] = digest(draft)
    with pytest.raises((ValueError, KeyError)):
        validate_download(s.prep, TEST_NOW)


@pytest.fixture
def status(preparation_factory):
    from conftest import TOKEN

    s = preparation_factory()
    with TestClient(
        create_app(s.engine, clock=lambda: TEST_NOW, desk=s.desk, setup=s.setup, background=False),
        base_url="http://127.0.0.1",
    ) as c:
        return c.get("/api/operations", headers={"Authorization": "Bearer " + TOKEN}).json()


@pytest.mark.parametrize(
    "condition,code",
    [
        ("feed", "FEED_DISCONNECTED"),
        ("quotes", "UNUSABLE_QUOTES"),
        ("basis", "BASIS_REVIEW_REQUIRED"),
        ("exit", "UNRESOLVED_EXITS"),
        ("fault", "ACCOUNT_FAULT_OR_KILL"),
        ("ledger", "LEDGER_INVALID_OR_UNAVAILABLE"),
        ("preparation", "PREPARATION_NEEDS_REVIEW"),
    ],
)
def test_watchdog_actionable_conditions(status, condition, code):
    report = deepcopy(status)
    report["session"]["open_now"] = True
    if condition == "feed":
        report["account"]["feed_connected"] = False
    elif condition == "quotes":
        report["unusable_quotes"] = ["NSE:A000"]
    elif condition == "basis":
        report["missing_basis_reviews"] = ["NSE:A000"]
    elif condition == "exit":
        report["protective_exits"] = [{"symbol": "NSE:A000", "quantity": 3}]
    elif condition == "fault":
        report["account"]["faulted"] = True
    elif condition == "ledger":
        report["checks"].append({"id": "ledger", "status": "BLOCKED"})
    else:
        report["preparation"] = {"state": "interrupted"}
    assert code in supervisor.alerts(report)


def test_closed_market_does_not_claim_feed_fault_and_intraday_exposure_is_distinct(status):
    report = deepcopy(status)
    report["session"]["open_now"] = False
    report["account"]["feed_connected"] = False
    report["account"]["positions"] = [{"symbol": "NSE:A000", "quantity": 3}]
    report["horizon"] = "long_term"
    assert "FEED_DISCONNECTED" not in supervisor.alerts(report)
    assert "INTRADAY_RESIDUAL_EXPOSURE" not in supervisor.alerts(report)
    report["horizon"] = "intraday"
    assert "INTRADAY_RESIDUAL_EXPOSURE" in supervisor.alerts(report)


def test_supervisor_refuses_clock_skew_and_clears_alert_after_recovery(
    status, preparation_factory, monkeypatch, tmp_path
):
    s = preparation_factory()
    report = deepcopy(status)
    report["observed_at"] = (TEST_NOW - timedelta(minutes=5)).isoformat()
    monkeypatch.setattr(supervisor, "collect", lambda *a, **k: report)
    output = tmp_path / "watch"
    assert supervisor.supervise(s.engine.settings, output, lambda: TEST_NOW, once=True)[
        "alerts"
    ] == ["SERVICE_UNAVAILABLE_OR_IDENTITY_INVALID"]
    report["observed_at"] = TEST_NOW.isoformat()
    recovered = supervisor.supervise(
        s.engine.settings, output, lambda: TEST_NOW + timedelta(seconds=1), once=True
    )
    assert "SERVICE_UNAVAILABLE_OR_IDENTITY_INVALID" not in recovered["alerts"]
    events = [json.loads(p.read_text()) for p in output.glob("alert-*.json")]
    assert any("SERVICE_UNAVAILABLE_OR_IDENTITY_INVALID" in e["cleared"] for e in events)


def test_scheduled_request_rejects_unknown_authority_inputs():
    body = {"session_date": "2026-10-23", "universe": "nifty100", "acknowledged": True}
    for extra in ({"mode": "automatic"}, {"basis_reviewed": True}, {"model_path": "/tmp/model"}):
        with pytest.raises(ValidationError):
            ScheduledDownload.model_validate({**body, **extra})
    for value in (False, 1, "true"):
        with pytest.raises(ValidationError):
            ScheduledDownload.model_validate({**body, "acknowledged": value})


def test_daily_reports_keep_preopen_and_afterclose_evidence_distinct(
    status, preparation_factory, monkeypatch, tmp_path
):
    s = preparation_factory()
    report = deepcopy(status)
    monkeypatch.setattr(supervisor, "collect", lambda *a, **k: report)
    folder = tmp_path / "monitor"
    for hour, phase in ((2, "before-open"), (5, "open"), (11, "after-close")):
        observed = TEST_NOW.replace(hour=hour)
        report["observed_at"] = observed.isoformat()
        report["session"]["open_now"] = phase == "open"
        supervisor.supervise(
            s.engine.settings, folder, lambda observed=observed: observed, once=True
        )
        target = folder / ("daily-" + report["session"]["date"] + "-" + phase)
        assert (target / "manifest.json").is_file()


def test_installed_strategy_backup_includes_source_and_referenced_data(downloaded, tmp_path):
    from trading_agent.desk.preparation import InstallRequest
    from trading_agent.operations.backup import create_package, restore_drill

    s = downloaded
    job = s.prep.state
    s.prep.install(
        InstallRequest(
            preview_sha256=job["preview_sha256"],
            revision=s.desk.revision,
            strategy_mode="rules",
            calendar_csv=job["calendar_csv"],
            reference="INVENTED offline test review",
            calendar_reviewed=True,
            basis_reviewed=True,
            policy_reviewed=True,
        )
    )
    s.engine.db.close()
    create_package(s.engine.settings, s.setup.config, tmp_path / "package", TEST_NOW)
    manifest = json.loads((tmp_path / "package" / "manifest.json").read_text())
    originals = {r["original"] for r in manifest["references"]}
    assert any(p.endswith("profile.toml") for p in originals)
    assert any(p.endswith("daily/daily.jsonl") for p in originals)
    assert any(p.endswith("constituents.csv") for p in originals)
    assert any(p.endswith("active.json") for p in originals)
    assert (
        restore_drill(s.engine.settings, tmp_path / "package", tmp_path / "restore")["state"]
        == "verified"
    )
