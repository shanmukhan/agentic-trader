"""Isolated HTTP flow with invented sources, profile authentication and execution quotes."""

from datetime import timedelta
from decimal import Decimal as D

import pytest
from conftest import TOKEN, quote
from fastapi.testclient import TestClient

from trading_agent.api.app import create_app
from trading_agent.desk.signals import AnalysisWorker
from trading_agent.persistence.database import Database

AUTH = {"Authorization": "Bearer " + TOKEN}
BASE = "/api/desk/preparation/guided/"


@pytest.mark.parametrize("mode", ["approval", "automatic"])
def test_one_setup_confirmation_then_separate_mode_choice_and_later_accounted_fill(
    preparation_factory,
    mode,
):
    s = preparation_factory("long_term")
    app = create_app(
        s.engine, clock=lambda: s.clock[0], setup=s.setup, desk=s.desk, background=False
    )
    with TestClient(app, base_url="http://127.0.0.1") as c:
        revision = c.get("/api/desk", headers=AUTH).json()["revision"]
        r = c.post(
            "/api/desk/preparation/download",
            headers=AUTH,
            json={
                "universe": "nifty100",
                "request_id": "e" * 32,
                "revision": revision,
                "acknowledged": True,
            },
        )
        assert r.status_code == 200
        app.state.preparation.thread.join(5)
        preview = c.post(
            BASE + "preview", headers=AUTH, json={"revision": revision, "strategy_mode": "rules"}
        )
        assert preview.status_code == 200, preview.text
        plan = preview.json()
        assert not s.engine.orders() and s.desk.research is None
        r = c.post(
            BASE + "confirm",
            headers=AUTH,
            json={"preview_sha256": plan["preview_sha256"], "acknowledged": True},
        )
        assert r.status_code == 200, r.text
        assert r.json()["state"] == "complete"
        status = c.get("/api/desk", headers=AUTH).json()
        assert status["mode"] == "manual" and not status["automatic_active"]
        assert status["guided_setup"]["state"] == "complete"
        assert {r["symbol"] for r in status["selected"]} == set(plan["plan"]["symbols"])
        assert not s.engine.orders() and D(s.engine.snapshot(s.clock[0])["cash"]) == D("25000")
        assert s.setup.stream is not None  # Requested, not proof of fresh usable quotes.
        s.engine.set_connected(True)  # INVENTED WebSocket callback; no broker network is opened.
        for symbol in plan["plan"]["symbols"]:
            index = int(symbol[-3:])
            s.engine.ingest(
                quote(base=s.clock[0], symbol=symbol, token=257 + index * 256).model_copy(
                    update={"source": "kite"}
                ),
                s.clock[0],
            )
        status = c.get("/api/desk", headers=AUTH).json()
        assert not status["blockers"], status["blockers"]
        r = c.post(
            "/api/desk/mode",
            headers=AUTH,
            json={"mode": mode, "revision": status["revision"], "acknowledged": True},
        )
        assert r.status_code == 200
        AnalysisWorker(s.desk, s.setup, lambda: s.clock[0]).evaluate(s.clock[0])
        decision = c.get("/api/desk", headers=AUTH).json()["decisions"][0]
        if mode == "approval":
            assert not s.engine.orders()
            path = "/api/desk/decisions/" + decision["id"]
            review = c.post(path + "/preview", headers=AUTH, json={}).json()
            assert review["review"]["allowed"]
            assert (
                c.post(
                    path + "/approve",
                    headers=AUTH,
                    json={"preview_sha256": review["preview_sha256"]},
                ).status_code
                == 200
            )
        assert s.engine.orders()
        s.clock[0] += timedelta(seconds=1)
        for symbol in plan["plan"]["symbols"]:
            s.engine.ingest(
                quote(
                    base=s.clock[0], symbol=symbol, token=257 + int(symbol[-3:]) * 256
                ).model_copy(update={"source": "kite"}),
                s.clock[0],
            )
        with s.engine.db.transaction() as tx:
            fills = list(tx.execute("SELECT * FROM fills"))
            assert fills
            independent_debit = sum(
                (D(f["price"]) * f["quantity"] + D(f["fees"]) for f in fills), D(0)
            )
            assert D(s.engine.db.get(tx, "cash")) == D("25000") - independent_debit
            Database.reconcile(tx)


def test_guided_endpoints_require_local_authority_and_explicit_acknowledgement(preparation_factory):
    s = preparation_factory()
    app = create_app(
        s.engine, clock=lambda: s.clock[0], setup=s.setup, desk=s.desk, background=False
    )
    with TestClient(app, base_url="http://127.0.0.1") as c:
        for operation in ("preview", "confirm"):
            assert c.post(BASE + operation, json={}).status_code == 401
            assert (
                c.post(
                    BASE + operation, json={}, headers={**AUTH, "Origin": "https://evil.test"}
                ).status_code
                == 403
            )
        for acknowledged in (False, "true", 1):
            assert (
                c.post(
                    BASE + "confirm",
                    headers=AUTH,
                    json={"preview_sha256": "a" * 64, "acknowledged": acknowledged},
                ).status_code
                == 422
            )
        assert (
            c.post(
                BASE + "confirm",
                headers=AUTH,
                json={
                    "preview_sha256": "a" * 64,
                    "acknowledged": True,
                    "symbols": ["NSE:ARBITRARY"],
                },
            ).status_code
            == 422
        )
        assert not s.engine.orders() and s.desk.mode == "manual"
