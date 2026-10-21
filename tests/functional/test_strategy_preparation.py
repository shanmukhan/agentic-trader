from datetime import timedelta
from decimal import Decimal as D

import pytest
from conftest import TOKEN, quote
from fastapi.testclient import TestClient
from preparation_support import TEST_NOW

from trading_agent.api.app import create_app
from trading_agent.desk.signals import AnalysisWorker
from trading_agent.execution.delivery import HoldingReview
from trading_agent.persistence.database import Database

AUTH = {"Authorization": "Bearer " + TOKEN}


def begin(c, app):
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
