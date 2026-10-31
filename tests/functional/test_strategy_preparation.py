import json
import sqlite3
from contextlib import closing
from datetime import timedelta
from decimal import Decimal as D
from types import SimpleNamespace

import pytest
from conftest import TOKEN, quote
from fastapi.testclient import TestClient
from preparation_support import TEST_NOW

from trading_agent.api.app import create_app
from trading_agent.desk.preparation import Preparation
from trading_agent.desk.signals import AnalysisWorker
from trading_agent.execution.delivery import HoldingReview
from trading_agent.persistence.database import Database

AUTH = {"Authorization": "Bearer " + TOKEN}


def test_connection_status_reads_report_transitions_without_provider_calls_or_ledger_changes(
    preparation_factory, monkeypatch
):
    s = preparation_factory()

    def forbidden():
        raise AssertionError("Status polling must not contact a broker")

    monkeypatch.setattr(s.setup, "broker", forbidden)
    app = create_app(s.engine, clock=lambda: TEST_NOW, setup=s.setup, desk=s.desk, background=False)
    with TestClient(app, base_url="http://127.0.0.1") as c:
        with closing(sqlite3.connect(s.engine.settings.database)) as db:
            before = list(db.iterdump())
        diagnostic = {}
        s.setup.stream = SimpleNamespace(diagnostics=lambda: dict(diagnostic), close=lambda: None)
        for state in ("connecting", "connected", "retrying", "failed"):
            diagnostic.update(state=state, failures=10 if state == "failed" else 0)
            s.engine.set_connected(state == "connected")
            response = c.get("/api/setup", headers=AUTH)
            assert response.status_code == 200
            assert response.json()["feed_diagnostics"]["state"] == state
            assert response.json()["feed_connected"] is (state == "connected")
        with closing(sqlite3.connect(s.engine.settings.database)) as db:
            assert list(db.iterdump()) == before


def begin(c, app):
    assert c.post("/api/setup/profile", headers=AUTH, json={}).status_code == 200
    initial = c.get("/api/desk", headers=AUTH).json()
    response = c.post(
        "/api/desk/preparation/download",
        headers=AUTH,
        json={
            "universe": "nifty100",
            "request_id": "c" * 32,
            "revision": initial["revision"],
            "acknowledged": True,
        },
    )
    assert response.status_code == 200
    app.state.preparation.thread.join(5)
    job = c.get("/api/desk", headers=AUTH).json()["preparation"]["job"]
    assert job["state"] == "ready_for_review"
    return job


def install_body(job, revision):
    return {
        "preview_sha256": job["preview_sha256"],
        "revision": revision,
        "strategy_mode": "rules",
        "calendar_csv": job["calendar_csv"],
        "reference": "INVENTED functional source review",
        "calendar_reviewed": True,
        "basis_reviewed": True,
        "policy_reviewed": True,
    }


@pytest.mark.parametrize("mode", ["approval", "automatic"])
def test_browser_download_review_install_basis_mode_and_independently_reconciled_fill(
    preparation_factory,
    mode,
):
    s = preparation_factory("long_term")
    e = s.engine
    app = create_app(e, clock=lambda: s.clock[0], setup=s.setup, desk=s.desk, background=False)
    with TestClient(app, base_url="http://127.0.0.1") as c:
        before = e.snapshot(TEST_NOW)
        job = begin(c, app)
        status = c.get("/api/desk", headers=AUTH).json()
        assert status["mode"] == "manual" and "NO_ANALYSIS_PROFILE" in status["blockers"]
        body = install_body(job, status["revision"])
        installed = c.post("/api/desk/preparation/install", headers=AUTH, json=body)
        assert installed.status_code == 200, installed.text
        status = c.get("/api/desk", headers=AUTH).json()
        assert status["mode"] == "manual" and status["strategy_mode"] == "rules"
        assert "NO_ANALYSIS_PROFILE" not in status["blockers"]
        assert "LONG_TERM_REVIEW_REQUIRED" in status["blockers"]
        assert status["readiness"]["quotes"][0]["basis_reviewed"] is False
        assert e.snapshot(TEST_NOW) == before and not e.orders()
        # Actual UI install retry returns the same result, without switching or submitting twice.
        assert c.post("/api/desk/preparation/install", headers=AUTH, json=body).status_code == 200
        e.review_holding(
            HoldingReview(
                symbol="NSE:A000",
                session_date=TEST_NOW.date(),
                no_corporate_action=True,
                reference="INVENTED current execution review",
            ),
            TEST_NOW,
        )
        e.ingest(
            quote(base=TEST_NOW, symbol="NSE:A000", token=257).model_copy(
                update={"source": "kite"}
            ),
            TEST_NOW,
        )
        status = c.get("/api/desk", headers=AUTH).json()
        assert not status["blockers"], status["blockers"]
        changed = c.post(
            "/api/desk/mode",
            headers=AUTH,
            json={"mode": mode, "revision": status["revision"], "acknowledged": True},
        )
        assert changed.status_code == 200
        worker = AnalysisWorker(s.desk, s.setup, lambda: s.clock[0])
        worker.evaluate(TEST_NOW)
        proposal = c.get("/api/desk", headers=AUTH).json()["decisions"][0]
        assert proposal["side"] == "BUY"
        if mode == "approval":
            assert proposal["state"] == "awaiting_approval" and not e.orders()
            base = "/api/desk/decisions/" + proposal["id"]
            preview = c.post(base + "/preview", headers=AUTH, json={}).json()
            assert preview["review"]["allowed"], preview["review"]
            result = c.post(
                base + "/approve", headers=AUTH, json={"preview_sha256": preview["preview_sha256"]}
            )
            assert result.status_code == 200
        else:
            assert proposal["state"] == "submitted" and proposal["authorized_by"] == "automatic"
        assert e.orders()[0]["state"] == "ACCEPTED"
        s.clock[0] += timedelta(seconds=1)
        e.ingest(
            quote(base=s.clock[0], symbol="NSE:A000", token=257).model_copy(
                update={"source": "kite"}
            ),
            s.clock[0],
        )
        entry = c.get("/api/activity", headers=AUTH).json()["entries"][0]
        assert entry["order"]["state"] == "FILLED" and entry["decision"]["mode"] == mode
        cash_debit = sum(D(f["price"]) * f["quantity"] + D(f["fees"]) for f in entry["fills"])
        assert D(entry["cash_debit"]) == cash_debit
        assert D(e.snapshot(s.clock[0])["cash"]) == D("25000") - cash_debit
        with e.db.transaction() as tx:
            Database.reconcile(tx)


def test_preparation_auth_origin_and_review_validation_do_not_change_financial_state(
    preparation_factory,
):
    s = preparation_factory()
    app = create_app(s.engine, clock=lambda: TEST_NOW, setup=s.setup, desk=s.desk, background=False)
    with TestClient(app, base_url="http://127.0.0.1") as c:
        for operation in ("download", "install", "cancel"):
            path = "/api/desk/preparation/" + operation
            assert c.post(path, json={}).status_code == 401
            assert (
                c.post(path, json={}, headers={**AUTH, "Origin": "https://evil.test"}).status_code
                == 403
            )
        assert c.get("/preparation.js").status_code == 200
        job = begin(c, app)
        body = install_body(job, s.desk.revision)
        for field in ("calendar_reviewed", "basis_reviewed", "policy_reviewed"):
            assert (
                c.post(
                    "/api/desk/preparation/install", headers=AUTH, json={**body, field: False}
                ).status_code
                == 422
            )
        assert (
            c.post(
                "/api/desk/preparation/install",
                headers=AUTH,
                json={**body, "model_directory": "/arbitrary"},
            ).status_code
            == 422
        )
        assert (
            c.post(
                "/api/desk/preparation/install",
                headers=AUTH,
                json={**body, "strategy_mode": "rules_ml"},
            ).status_code
            == 409
        )
        assert not s.engine.orders() and s.desk.mode == "manual" and s.desk.research is None


def test_installed_profile_survives_restart_but_never_restores_automatic_authority(
    preparation_factory,
):
    s = preparation_factory()
    app = create_app(s.engine, clock=lambda: TEST_NOW, setup=s.setup, desk=s.desk, background=False)
    with TestClient(app, base_url="http://127.0.0.1") as c:
        job = begin(c, app)
        response = c.post(
            "/api/desk/preparation/install", headers=AUTH, json=install_body(job, s.desk.revision)
        )
        assert response.status_code == 200
    restarted = create_app(s.engine, clock=lambda: TEST_NOW, setup=s.setup, background=False)
    with TestClient(restarted, base_url="http://127.0.0.1") as c:
        status = c.get("/api/desk", headers=AUTH).json()
        assert (
            status["profile_name"] and status["mode"] == "manual" and not status["automatic_active"]
        )
        assert not status["model_available"] and status["strategy_mode"] == "rules"
        assert not s.engine.orders()


def test_failed_session_download_persists_then_explicit_retry_recovers_without_account_changes(
    preparation_factory, monkeypatch
):
    s = preparation_factory()
    app = create_app(s.engine, clock=lambda: TEST_NOW, setup=s.setup, desk=s.desk, background=False)

    def persisted():
        with closing(sqlite3.connect(s.engine.settings.database)) as db:
            assert D(db.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0]) == D(
                "25000.00"
            )
            return list(db.iterdump())

    original_profile = s.broker.get_profile
    s.setup.check_profile()

    def unavailable():
        raise RuntimeError("INVENTED-private-token must not appear in status")

    monkeypatch.setattr(s.broker, "get_profile", unavailable)
    with TestClient(app, base_url="http://127.0.0.1") as c:
        before = persisted()
        initial = c.get("/api/desk", headers=AUTH).json()
        body = dict(
            universe="nifty100",
            request_id="e" * 32,
            revision=initial["revision"],
            acknowledged=True,
        )
        assert c.post("/api/desk/preparation/download", headers=AUTH, json=body).status_code == 200
        prep = app.state.preparation
        prep.thread.join(5)
        assert not prep.thread.is_alive()
        status = c.get("/api/desk", headers=AUTH).json()
        job = status["preparation"]["job"]
        assert job["state"] == "failed" and job["stage"] == "broker_session"
        assert job["error"] == "BROKER_SESSION_UNAVAILABLE" and job["completed"] == 0
        assert status["preparation"]["download_prerequisites"]["ready"] is False
        assert s.setup.verified is False and s.setup.verified_at is None
        assert not s.requests and not s.broker.calls
        saved = json.loads((prep.root / "latest.json").read_text())
        assert saved["state"] == "failed" and saved["error"] == job["error"]
        assert "INVENTED-private-token" not in json.dumps(saved) + json.dumps(status)
        restarted = Preparation(s.desk, s.setup, lambda: TEST_NOW)
        assert restarted.view()["job"]["state"] == "failed" and restarted.thread is None
        # Replaying a lost response keeps the original failure, without a new broker read.
        assert (
            c.post("/api/desk/preparation/download", headers=AUTH, json=body).json()["job"][
                "job_id"
            ]
            == job["job_id"]
        )
        monkeypatch.setattr(s.broker, "get_profile", original_profile)
        assert c.post("/api/setup/profile", headers=AUTH, json={}).status_code == 200
        retry = c.post(
            "/api/desk/preparation/download", headers=AUTH, json={**body, "request_id": "f" * 32}
        )
        assert retry.status_code == 200
        prep.thread.join(5)
        recovered = c.get("/api/desk", headers=AUTH).json()["preparation"]["job"]
        assert recovered["state"] == "ready_for_review" and recovered["error"] is None
        assert recovered["job_id"] != job["job_id"]
        assert s.desk.mode == "manual" and s.desk.research is None
        assert persisted() == before


def test_session_prerequisite_is_visible_and_enforced_before_any_download_files_or_provider_reads(
    preparation_factory, monkeypatch
):
    s = preparation_factory()
    profile_calls = []
    original = s.broker.get_profile

    def profile():
        profile_calls.append(True)
        return original()

    monkeypatch.setattr(s.broker, "get_profile", profile)
    app = create_app(s.engine, clock=lambda: TEST_NOW, setup=s.setup, desk=s.desk, background=False)
    with TestClient(app, base_url="http://127.0.0.1") as c:
        with closing(sqlite3.connect(s.engine.settings.database)) as db:
            before = list(db.iterdump())
        status = c.get("/api/desk", headers=AUTH).json()
        for _ in range(2):
            readiness = c.get("/api/desk", headers=AUTH).json()["preparation"][
                "download_prerequisites"
            ]
            assert readiness["ready"] is False and readiness["session_verified"] is False
            assert readiness["catalog_count"] > 0
        body = dict(
            universe="nifty100", request_id="a" * 32, revision=status["revision"], acknowledged=True
        )
        rejected = c.post("/api/desk/preparation/download", headers=AUTH, json=body)
        assert rejected.status_code == 409 and "prerequisite incomplete" in rejected.text
        assert not profile_calls and not s.requests and not s.broker.calls
        prep = app.state.preparation
        assert prep.state is None and prep.thread is None and not prep.root.exists()
        assert c.post("/api/setup/profile", headers=AUTH, json={}).status_code == 200
        assert (
            c.get("/api/desk", headers=AUTH).json()["preparation"]["download_prerequisites"][
                "ready"
            ]
            is True
        )
        assert profile_calls == [True]
        assert c.post("/api/desk/preparation/download", headers=AUTH, json=body).status_code == 200
        prep.thread.join(5)
        assert prep.view()["job"]["state"] == "ready_for_review"
        assert len(profile_calls) == 2
        with closing(sqlite3.connect(s.engine.settings.database)) as db:
            assert D(db.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0]) == D(
                "25000.00"
            )
            assert list(db.iterdump()) == before
