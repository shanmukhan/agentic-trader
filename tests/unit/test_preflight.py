import hashlib
import json
import sqlite3
from datetime import timedelta
from decimal import Decimal

import pytest
from conftest import NOW, TOKEN, candidate

from trading_agent.observability import preflight as module
from trading_agent.observability.preflight import preflight, sqlite_wal_fix_present, write_preflight
from trading_agent.settings import Settings


def checks(report):
    return {item["id"]: item["state"] for item in report["checks"]}


def calendar_file(engine):
    path = engine.settings.database.parent / "calendar.csv"
    path.write_text("date,open,close,source\n2026-10-20,09:15,15:30,reviewed test\n")
    engine.settings.database.parent.chmod(0o700)
    return engine.settings.model_copy(update={"calendar": path})


def test_live_owner_read_includes_wal_and_preserves_pending_account(engine, monkeypatch):
    settings = calendar_file(engine)
    engine.submit(candidate(), NOW)
    before = engine.orders()
    with engine.db.transaction() as tx:
        event_count = tx.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    monkeypatch.setenv("KITE_ACCESS_TOKEN", "private-broker-token-never-output")
    report = preflight(settings, NOW)
    assert report["local_checks_passed"]
    assert report["account"]["pending_orders"] == 1
    assert checks(report)["flat_account"] == "blocked"
    assert checks(report)["broker_entitlement"] == "unverified"
    assert report["calendar_open_now"]
    assert not report["external_acceptance_verified"] and not report["ready_for_live"]
    assert engine.orders() == before
    with engine.db.transaction() as tx:
        assert tx.execute("SELECT COUNT(*) FROM events").fetchone()[0] == event_count
    assert TOKEN not in json.dumps(report)
    assert "private-broker-token" not in json.dumps(report)


def test_missing_account_and_calendar_never_create_any_source(tmp_path):
    settings = Settings(
        database=tmp_path / "absent" / "paper.db", calendar=tmp_path / "missing.csv"
    )
    report = preflight(settings, NOW)
    assert not report["local_checks_passed"]
    assert checks(report)["account_exists"] == "blocked"
    assert checks(report)["calendar_file"] == "blocked"
    assert checks(report)["operator_token"] == "blocked"
    assert not settings.database.parent.exists()


def test_unknown_session_is_explicit_and_does_not_claim_ready(engine):
    settings = calendar_file(engine)
    report = preflight(settings, NOW + timedelta(days=3))
    assert report["local_checks_passed"]
    assert not report["calendar_open_now"]
    assert checks(report)["session_today"] == "blocked"
    assert not report["ready_for_live"]


@pytest.mark.parametrize(
    "version,patched",
    [
        ((3, 53, 1), True),
        ((3, 51, 3), True),
        ((3, 51, 2), False),
        ((3, 50, 7), True),
        ((3, 50, 6), False),
        ((3, 44, 6), True),
        ((3, 44, 5), False),
        ((3, 45, 0), False),
    ],
)
def test_official_sqlite_fix_branches(version, patched):
    assert sqlite_wal_fix_present(version) is patched


def test_policy_marker_permissions_and_sqlite_check(engine, monkeypatch):
    settings = calendar_file(engine)
    changed = settings.model_copy(update={"max_trade_risk": Decimal("60.00")})
    engine.db.path.chmod(0o644)
    monkeypatch.setattr(sqlite3, "sqlite_version_info", (3, 51, 2))
    report = preflight(changed, NOW)
    assert not report["local_checks_passed"]
    assert checks(report)["risk_policy_matches"] == "blocked"
    assert checks(report)["private_storage"] == "blocked"
    assert checks(report)["sqlite_wal_fix"] == "blocked"


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE meta SET value='1' WHERE key='cash'",
        "DELETE FROM meta WHERE key='fees'",
        "PRAGMA user_version=99",
    ],
)
def test_corruption_and_unknown_schema_fail_without_repair(engine, mutation):
    settings = calendar_file(engine)
    with engine.db.transaction() as tx:
        tx.execute(mutation)
    report = preflight(settings, NOW)
    assert not report["local_checks_passed"]
    assert checks(report)["account_integrity"] == "blocked"


def test_disk_floor_and_budget_fail_conservatively(engine, monkeypatch):
    settings = calendar_file(engine)
    usage = module.shutil.disk_usage(settings.database.parent)
    monkeypatch.setattr(module.shutil, "disk_usage", lambda p: usage._replace(free=1))
    monkeypatch.setattr(module, "DATABASE_BUDGET_SECONDS", 0)
    report = preflight(settings, NOW)
    assert checks(report)["disk_headroom"] == "blocked"
    assert checks(report)["account_integrity"] == "blocked"


def test_symlink_account_is_refused_without_opening_target(engine, tmp_path):
    path = tmp_path / "linked.db"
    path.symlink_to(engine.settings.database)
    report = preflight(engine.settings.model_copy(update={"database": path}), NOW)
    assert checks(report)["account_exists"] == "blocked"
    assert report["account"] is None


def test_report_is_exclusive_private_hash_complete_and_never_contains_token(engine, tmp_path):
    report = preflight(calendar_file(engine), NOW)
    output = tmp_path / "evidence"
    write_preflight(report, output)
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["state"] == "finished" and not manifest["ready_for_live"]
    assert output.stat().st_mode & 0o777 == 0o700
    for name, digest in manifest["sha256"].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == digest
        assert TOKEN not in (output / name).read_text()
        assert (output / name).stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        write_preflight(report, output)


def test_failed_artifact_write_has_no_completion_manifest(engine, tmp_path, monkeypatch):
    original = module.os.fsync
    calls = []

    def fail_second(fd):
        calls.append(fd)
        if len(calls) == 2:
            raise OSError("simulated storage fault")
        original(fd)

    monkeypatch.setattr(module.os, "fsync", fail_second)
    output = tmp_path / "incomplete"
    with pytest.raises(OSError):
        write_preflight(preflight(calendar_file(engine), NOW), output)
    assert not (output / "manifest.json").exists()
