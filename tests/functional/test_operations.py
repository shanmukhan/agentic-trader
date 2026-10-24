"""Invented local accounts only: no broker, market or device acceptance."""

import hashlib
import json
import sqlite3
from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from conftest import TOKEN, candidate, quote
from fastapi.testclient import TestClient
from preparation_support import TEST_NOW

from trading_agent.api.app import create_app
from trading_agent.main import execute, parser
from trading_agent.observability.preflight import _account
from trading_agent.operations import supervisor
from trading_agent.operations.backup import create_package, restore_drill
from trading_agent.operations.report import account_id

AUTH = {"Authorization": "Bearer " + TOKEN}


def rows(engine):
    with engine.db.transaction() as tx:
        return {
            table: [tuple(r) for r in tx.execute(f"SELECT * FROM {table}")]
            for table in ("meta", "events", "orders", "fills", "positions", "desk_decisions")
        }


def app_for(s):
    return create_app(
        s.engine, clock=lambda: s.clock[0], setup=s.setup, desk=s.desk, background=False
    )


def test_operations_report_is_read_only_authenticated_and_independently_reconciled(
    preparation_factory,
):
    s = preparation_factory("long_term")
    before = rows(s.engine)
    with TestClient(app_for(s), base_url="http://127.0.0.1") as client:
        assert client.get("/api/operations").status_code == 401
        response = client.get("/api/operations?audit=true", headers=AUTH)
        assert response.status_code == 200, response.text
        report = response.json()
        states = {c["id"]: c["status"] for c in report["checks"]}
        assert states["ledger"] == "PASS" and states["strategy_data"] == "BLOCKED"
        assert states["broker"] == "NEEDS REVIEW"
        assert report["trading_authorization"] == "NOT AUTHORIZED"
        assert Decimal(report["ledger_audit"]["cash"]) == Decimal("25000.00")
        assert not report["ready_for_live"] and not report["external_acceptance_verified"]
        assert rows(s.engine) == before
        s.setup.check_profile()
        checked = client.get("/api/operations", headers=AUTH).json()
        assert datetime.fromisoformat(checked["broker_checked_at"]) == s.clock[0]
        s.clock[0] += timedelta(days=1)
        expired = client.get("/api/operations", headers=AUTH).json()
        assert next(c for c in expired["checks"] if c["id"] == "broker")["status"] == "NEEDS REVIEW"
        assert all(
            secret not in response.text for secret in (TOKEN, "INVENTED-secret", "INVENTED-token")
        )


def test_scheduled_download_is_durable_once_per_day_and_stops_before_authority(preparation_factory):
    s = preparation_factory("long_term")
    app = app_for(s)
    body = {
        "session_date": TEST_NOW.date().isoformat(),
        "universe": "nifty100",
        "acknowledged": True,
    }
    before = rows(s.engine)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        path = "/api/operations/download"
        assert client.post(path, json=body).status_code == 401
        assert (
            client.post(
                path, json=body, headers={**AUTH, "Origin": "https://evil.test"}
            ).status_code
            == 403
        )
        assert (
            client.post(path, json={**body, "acknowledged": False}, headers=AUTH).status_code == 422
        )
        assert (
            client.post(path, json={**body, "session_date": "2026-01-01"}, headers=AUTH).status_code
            == 409
        )
        first = client.post(path, json=body, headers=AUTH)
        assert first.status_code == 200, first.text
        app.state.preparation.thread.join(5)
        calls = list(s.broker.calls)
        again = client.post(path, json=body, headers=AUTH).json()
        assert again["job_id"] == first.json()["job_id"]
        assert again["state"] == "ready_for_review" and s.broker.calls == calls
        report = client.get("/api/operations?audit=true", headers=AUTH).json()
        assert report["source_validation"]["coverage_valid"]
        assert report["source_validation"]["same_ist_date"]
        assert report["decision_mode"] == "manual" and s.desk.research is None
        assert rows(s.engine) == before
        state_path = s.engine.settings.database.with_suffix(".operations") / (
            body["session_date"] + ".json"
        )
        assert state_path.stat().st_mode & 0o077 == 0
        draft = app.state.preparation.root / first.json()["job_id"] / "actions.json"
        draft.write_text("[]")
        changed = client.get("/api/operations?audit=true", headers=AUTH).json()
        assert (
            next(c for c in changed["checks"] if c["id"] == "strategy_data")["status"] == "BLOCKED"
        )
        assert (
            client.post(path, json={**body, "universe": "nifty500"}, headers=AUTH).status_code
            == 409
        )


def test_interrupted_claim_is_not_replayed_and_does_not_cancel_orders(
    preparation_factory, monkeypatch
):
    s = preparation_factory()
    app = app_for(s)
    monkeypatch.setattr(
        app.state.preparation, "start", lambda body: (_ for _ in ()).throw(TimeoutError())
    )
    body = {
        "session_date": TEST_NOW.date().isoformat(),
        "universe": "nifty100",
        "acknowledged": True,
    }
    before = rows(s.engine)
    with TestClient(app, base_url="http://127.0.0.1") as client:
        assert client.post("/api/operations/download", json=body, headers=AUTH).status_code == 409
        again = client.post("/api/operations/download", json=body, headers=AUTH)
        assert again.json()["state"] == "outcome_unknown"
        assert not s.broker.calls and rows(s.engine) == before


def test_backup_and_restore_preserve_pending_orders_exact_money_and_original(
    preparation_factory, tmp_path
):
    s = preparation_factory()
    e = s.engine
    e.ingest(quote(base=TEST_NOW, symbol="NSE:A000", token=257), TEST_NOW)
    e.submit(candidate(now=TEST_NOW, symbol="NSE:A000"), TEST_NOW)
    before = rows(e)
    settings = e.settings
    source_path = settings.database
    # Running owner prevents backup rather than recovering/cancelling pending entries.
    with pytest.raises(BlockingIOError):
        create_package(settings, s.setup.config, tmp_path / "blocked", TEST_NOW)
    assert rows(e) == before
    e.db.close()
    package = tmp_path / "backup"
    result = create_package(settings, s.setup.config, package, TEST_NOW)
    assert result["pending_orders"] == 1 and Decimal(result["cash"]) == Decimal("25000")
    assert result["verified"]
    assert all(p.stat().st_mode & 0o077 == 0 for p in package.rglob("*") if p.is_file())
    manifest = json.loads((package / "manifest.json").read_text())
    assert not manifest["credentials_included"]
    assert {r["role"] for r in manifest["references"]} == {"config", "calendar"}
    assert all(
        hashlib.sha256((package / name).read_bytes()).hexdigest() == digest
        for name, digest in manifest["files"].items()
    )
    restored = restore_drill(settings, package, tmp_path / "drill")
    assert restored["pending_orders"] == 1 and restored["fees"] == "0"
    assert not restored["service_started"] and not restored["paths_rebound"]
    with sqlite3.connect(source_path) as tx:
        assert tx.execute("SELECT state FROM orders").fetchone()[0] == "ACCEPTED"
        assert tx.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0] == result["cash"]
    with pytest.raises(FileExistsError):
        create_package(settings, s.setup.config, package, TEST_NOW)
    (package / "ledger.sqlite3").write_bytes(b"corrupted")
    with pytest.raises(ValueError):
        restore_drill(settings, package, tmp_path / "corrupt-drill")
    assert not (tmp_path / "corrupt-drill").exists()


def test_supervisor_detects_dead_service_and_deduplicates_alerts(
    preparation_factory, monkeypatch, tmp_path, capsys
):
    s = preparation_factory()
    monkeypatch.setattr(
        supervisor, "collect", lambda *a, **k: (_ for _ in ()).throw(TimeoutError("secret"))
    )
    output = tmp_path / "supervision"
    first = supervisor.supervise(s.engine.settings, output, lambda: TEST_NOW, once=True)
    second = supervisor.supervise(
        s.engine.settings, output, lambda: TEST_NOW + timedelta(seconds=10), once=True
    )
    assert first["alerts"] == second["alerts"] == ["SERVICE_UNAVAILABLE_OR_IDENTITY_INVALID"]
    assert len(list(output.glob("alert-*.json"))) == 1
    assert "secret" not in capsys.readouterr().err
    assert s.desk.mode == "manual" and not s.engine.orders()


def test_supervisor_timeout_after_acceptance_never_retries_download(
    preparation_factory, monkeypatch, tmp_path
):
    s = preparation_factory()
    with TestClient(app_for(s), base_url="http://127.0.0.1") as client:
        report = client.get("/api/operations", headers=AUTH).json()
    posts = []
    monkeypatch.setattr(supervisor, "collect", lambda *a, **k: report)

    def timeout(*args):
        posts.append(args)
        raise TimeoutError("unknown outcome")

    monkeypatch.setattr(supervisor, "request", timeout)
    output = tmp_path / "supervision"
    state = supervisor.supervise(
        s.engine.settings, output, lambda: TEST_NOW, once=True, download_universe="nifty100"
    )
    assert state["download_state"] == "outcome_unknown"
    supervisor.supervise(
        s.engine.settings,
        output,
        lambda: TEST_NOW + timedelta(seconds=10),
        once=True,
        download_universe="nifty100",
    )
    assert len(posts) == 1


def test_daily_report_cli_uses_running_service_without_owning_recovery(
    preparation_factory, monkeypatch, tmp_path
):
    s = preparation_factory()
    monkeypatch.setenv("TRADING_OPERATOR_TOKEN", TOKEN)
    before = _account(s.engine.settings)
    with TestClient(app_for(s), base_url="http://127.0.0.1") as client:
        report = client.get("/api/operations?audit=true", headers=AUTH).json()
    monkeypatch.setattr(supervisor, "collect", lambda *a, **k: report)
    out = tmp_path / "daily"
    result = execute(
        parser().parse_args(["--config", str(s.setup.config), "daily-report", "--output", str(out)])
    )
    assert result["output"] == str(out) and (out / "manifest.json").is_file()
    assert _account(s.engine.settings) == before
    assert account_id(s.engine.settings.database) == report["account_id"]


@pytest.mark.parametrize("state", ["PARTIAL", "FILLED", "CANCELLED", "REJECTED"])
def test_backup_exact_fill_money_and_lifecycle_states(preparation_factory, tmp_path, state):
    s = preparation_factory()
    e, now = s.engine, TEST_NOW
    e.ingest(quote(base=now, symbol="NSE:A000", token=257), now)
    if state == "REJECTED":
        e.set_connected(False)
    order = e.submit(candidate(now=now, symbol="NSE:A000"), now)
    if state in {"PARTIAL", "FILLED"}:
        e.ingest(
            quote(
                1, base=now, symbol="NSE:A000", token=257, ask_size=3 if state == "PARTIAL" else 100
            ),
            now + timedelta(seconds=1),
        )
    if state == "CANCELLED":
        e.cancel(order["id"], now + timedelta(seconds=1))
    with e.db.transaction() as tx:
        assert tx.execute("SELECT state FROM orders").fetchone()[0] == state
        debit = sum(
            (
                Decimal(r[0]) * r[1] + Decimal(r[2])
                for r in tx.execute("SELECT price,quantity,fees FROM fills")
            ),
            Decimal(0),
        )
        assert Decimal(e.db.get(tx, "cash")) == Decimal("25000") - debit
    expected = rows(e)
    e.db.close()
    result = create_package(e.settings, s.setup.config, tmp_path / "backup", now)
    assert Decimal(result["cash"]) == Decimal("25000") - debit
    restore_drill(e.settings, tmp_path / "backup", tmp_path / "restore")
    with sqlite3.connect(tmp_path / "restore" / "ledger.sqlite3") as tx:
        for table, values in expected.items():
            assert tx.execute(f"SELECT * FROM {table}").fetchall() == values


def test_backup_write_failure_has_no_completion_marker_or_account_changes(
    preparation_factory, tmp_path, monkeypatch
):
    from trading_agent.operations import backup

    s = preparation_factory()
    before = _account(s.engine.settings)
    s.engine.db.close()
    monkeypatch.setattr(backup, "write_new", lambda *a: (_ for _ in ()).throw(OSError("disk full")))
    with pytest.raises(OSError):
        create_package(s.engine.settings, s.setup.config, tmp_path / "failed", TEST_NOW)
    assert not (tmp_path / "failed" / "manifest.json").exists()
    assert _account(s.engine.settings) == before


def test_scheduled_download_refuses_pending_orders_without_cancelling_them(preparation_factory):
    s = preparation_factory()
    s.engine.ingest(quote(base=TEST_NOW, symbol="NSE:A000", token=257), TEST_NOW)
    s.engine.submit(candidate(now=TEST_NOW, symbol="NSE:A000"), TEST_NOW)
    before = rows(s.engine)
    with TestClient(app_for(s), base_url="http://127.0.0.1") as client:
        response = client.post(
            "/api/operations/download",
            headers=AUTH,
            json={
                "session_date": TEST_NOW.date().isoformat(),
                "universe": "nifty100",
                "acknowledged": True,
            },
        )
        assert response.status_code == 409
        assert rows(s.engine) == before and not s.broker.calls
