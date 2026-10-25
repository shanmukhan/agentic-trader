import json
import sqlite3
from contextlib import contextmanager
from datetime import timedelta
from decimal import Decimal as D

from conftest import NOW, TOKEN, candidate, quote
from fastapi.testclient import TestClient

from trading_agent.api.app import create_app
from trading_agent.persistence.database import Database

AUTH = {"Authorization": "Bearer " + TOKEN}


def test_next_day_incoming_quotes_report_review_block_on_both_views_without_account_changes(
    desk_factory,
):
    desk, _, _ = desk_factory(horizon="long_term")
    e = desk.engine
    now = NOW + timedelta(days=1)
    incoming = quote(1).model_copy(update={"exchange_time": now, "received_time": now})
    assert not e.ingest(incoming, now)

    def persisted():
        with sqlite3.connect(e.settings.database) as db:
            assert D(db.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0]) == D(
                "25000"
            )
            assert db.execute("SELECT count(*) FROM orders").fetchone()[0] == 0
            assert db.execute("SELECT count(*) FROM fills").fetchone()[0] == 0
            return list(db.iterdump())

    with TestClient(
        create_app(e, clock=lambda: now, background=False, desk=desk),
        base_url="http://127.0.0.1",
    ) as client:
        before = persisted()
        overview = client.get("/api/desk", headers=AUTH).json()
        console = client.get("/api/console", headers=AUTH).json()
        for result in (overview["readiness"]["quotes"][0], console["quotes"][0]):
            assert result["status"] == "PRICE_BASIS_REVIEW_REQUIRED"
            assert not result["usable"] and result["basis_reviewed"] is False
            assert "Incoming quotes cannot be accepted" in result["detail"]
        checks = {row["key"]: row for row in overview["readiness"]["checks"]}
        assert overview["readiness"]["session_open"]
        assert "Resolve today's price-basis reviews" in overview["readiness"]["next_action"]
        assert "blocked before storage" in checks["quotes"]["detail"]
        assert checks["selection"]["href"] == "#execution-shortlist"
        assert persisted() == before


def test_new_tabs_are_public_shells_but_controls_are_authenticated(desk_factory):
    desk, _, _ = desk_factory()
    e = desk.engine
    with TestClient(
        create_app(e, clock=lambda: NOW, background=False, desk=desk), base_url="http://127.0.0.1"
    ) as c:
        for path in ["/desk", "/activity", "/desk.js"]:
            r = c.get(path)
            assert r.status_code == 200 and TOKEN not in r.text
        for path in ["/api/desk", "/api/desk/alerts", "/api/activity"]:
            assert c.get(path).status_code == 401
        body = {"mode": "automatic", "revision": desk.revision, "acknowledged": True}
        assert c.post("/api/desk/mode", json=body).status_code == 401
        assert (
            c.post(
                "/api/desk/mode", headers={**AUTH, "Origin": "https://evil.test"}, json=body
            ).status_code
            == 403
        )
        for invalid in [False, 1, "true"]:
            assert (
                c.post(
                    "/api/desk/mode", headers=AUTH, json={**body, "acknowledged": invalid}
                ).status_code
                == 422
            )
        assert desk.mode == "manual" and not e.orders() and not e.faulted


def test_browser_approval_to_later_fill_activity_and_idempotent_retry(desk_factory):
    desk, _, _ = desk_factory()
    e = desk.engine
    clock = [NOW]
    with TestClient(
        create_app(e, clock=lambda: clock[0], background=False, desk=desk),
        base_url="http://127.0.0.1",
    ) as c:
        status = c.get("/api/desk", headers=AUTH).json()
        body = {"mode": "approval", "revision": status["revision"], "acknowledged": True}
        assert c.post("/api/desk/mode", headers=AUTH, json=body).status_code == 200
        assert c.post("/api/desk/mode", headers=AUTH, json=body).status_code == 409
        record = desk.offer(candidate(), NOW, {"kind": "intraday", "candle": {"close": "500"}})
        path = "/api/desk/decisions/" + record["id"]
        review = c.post(path + "/preview", headers=AUTH, json={}).json()
        assert review["review"]["allowed"] and not e.orders()
        approved = c.post(
            path + "/approve", headers=AUTH, json={"preview_sha256": review["preview_sha256"]}
        )
        assert approved.status_code == 200 and approved.json()["authorized_by"] == "operator"
        first = c.get("/api/activity", headers=AUTH).json()["entries"][0]
        assert first["order"]["state"] == "ACCEPTED" and first["fills"] == []
        clock[0] += timedelta(seconds=1)
        e.ingest(quote(1), clock[0])
        page = c.get("/api/activity", headers=AUTH).json()
        row = page["entries"][0]
        assert row["order"]["state"] == "FILLED" and row["decision"]["mode"] == "approval"
        assert row["original_instruction"]["reason"] == candidate().reason
        assert D(row["cash_debit"]) == D(row["order"]["turnover"]) + D(row["order"]["fees"])
        assert D(e.snapshot(clock[0])["cash"]) == D("25000") - D(row["cash_debit"])
        assert (
            c.post(
                path + "/approve", headers=AUTH, json={"preview_sha256": review["preview_sha256"]}
            ).json()["order_id"]
            == row["order"]["id"]
        )
        assert len(e.orders()) == 1
        for query in ["?limit=101", "?before=-1"]:
            assert c.get("/api/activity" + query, headers=AUTH).status_code == 422
        with e.db.transaction() as tx:
            Database.reconcile(tx)


def test_activity_cursor_keeps_rejected_orders_and_reads_do_not_trade(desk_factory):
    desk, _, _ = desk_factory()
    e = desk.engine
    for n in range(4):
        e.submit(candidate("manual-" + str(n), stop="600"), NOW)
    before = e.snapshot(NOW)
    with TestClient(
        create_app(e, clock=lambda: NOW, background=False, desk=desk), base_url="http://127.0.0.1"
    ) as c:
        first = c.get("/api/activity?limit=2", headers=AUTH).json()
        second = c.get(
            "/api/activity?limit=2&before=" + str(first["next_before"]), headers=AUTH
        ).json()
        ids = [r["order"]["id"] for r in first["entries"] + second["entries"]]
        assert len(set(ids)) == 4 and second["next_before"] is None
        assert all(
            r["order"]["state"] == "REJECTED" and not r["fills"]
            for r in first["entries"] + second["entries"]
        )
        c.get("/api/desk", headers=AUTH)
        assert e.snapshot(NOW) == before


def test_every_fill_is_accessible_through_bounded_cursor_pages(engine_factory):
    e = engine_factory(
        max_trade_risk=D(250), daily_loss_limit=D(500), latency_ms=1, order_ttl_seconds=300
    )
    current = NOW + timedelta(seconds=1)
    e.ingest(quote(1, ask="50", bid="49.95"), current)
    order = e.submit(candidate("many-fills", now=current, stop="49.90", target="52"), current)
    assert order["quantity"] > 101
    for n in range(1, 102):
        now = current + timedelta(milliseconds=10 * n)
        e.ingest(
            quote(1, ask="50", bid="49.95", ask_size=1, volume=2000 + n).model_copy(
                update={"exchange_time": now, "received_time": now}
            ),
            now,
        )
    with TestClient(
        create_app(e, clock=lambda: now, background=False), base_url="http://127.0.0.1"
    ) as c:
        activity = c.get("/api/activity", headers=AUTH).json()["entries"][0]
        assert activity["fills_truncated"] and len(activity["fills"]) == 100
        page = c.get(
            "/api/activity/orders/many-fills/fills?before=" + str(activity["fills"][-1]["seq"]),
            headers=AUTH,
        ).json()
        assert len(page["fills"]) == 1 and page["next_before"] is None
        assert len({f["seq"] for f in activity["fills"] + page["fills"]}) == 101
        assert c.get("/api/activity/orders/unknown/fills", headers=AUTH).status_code == 404
        with e.db.transaction() as tx:
            Database.reconcile(tx)


def test_ranked_shortlist_binds_review_and_preserves_holdings_without_trading(
    desk_factory, tmp_path
):
    import json

    from trading_agent.api.setup import SetupService

    desk, _, _ = desk_factory()
    e = desk.engine
    config = tmp_path / "ui.toml"
    config.write_text(
        "".join(
            k + " = " + json.dumps(v) + "\n"
            for k, v in e.settings.model_dump(mode="json", exclude={"operator_token"}).items()
        )
    )
    setup = SetupService(e, config, lambda: NOW)
    e.submit(candidate("held"), NOW)
    e.ingest(quote(1), NOW + timedelta(seconds=1))
    assert e.snapshot(NOW + timedelta(seconds=1))["positions"]
    e.set_connected(False)
    before = e.snapshot(NOW + timedelta(seconds=1))
    orders = e.orders()
    with TestClient(
        create_app(
            e, clock=lambda: NOW + timedelta(seconds=1), background=False, desk=desk, setup=setup
        ),
        base_url="http://127.0.0.1",
    ) as c:
        plan = c.get("/api/desk", headers=AUTH).json()["shortlist"]
        assert plan["symbols"][0] == "NSE:DEMO" and plan["held_symbols"] == ["NSE:DEMO"]
        assert (
            c.post(
                "/api/desk/shortlist", headers=AUTH, json={"preview_sha256": "0" * 64}
            ).status_code
            == 409
        )
        assert e.settings.stream_tokens == (1,)
        response = c.post(
            "/api/desk/shortlist", headers=AUTH, json={"preview_sha256": plan["preview_sha256"]}
        )
        assert response.status_code == 200
        assert set(e.settings.stream_tokens) == {1, 257} and 513 not in e.settings.stream_tokens
        assert e.snapshot(NOW + timedelta(seconds=1)) == before and e.orders() == orders
        with e.db.transaction() as tx:
            Database.reconcile(tx)


def test_brief_feed_disconnect_revokes_mode_before_watchdog_poll(desk_factory, tmp_path):
    import json

    from trading_agent.api.setup import SetupService

    desk, _, _ = desk_factory()
    e = desk.engine
    config = tmp_path / "feed.toml"
    config.write_text(
        "".join(
            k + " = " + json.dumps(v) + "\n"
            for k, v in e.settings.model_dump(mode="json", exclude={"operator_token"}).items()
        )
    )
    setup = SetupService(e, config, lambda: NOW)
    with TestClient(
        create_app(e, clock=lambda: NOW, background=False, desk=desk, setup=setup),
        base_url="http://127.0.0.1",
    ) as c:
        desk.set_mode("automatic", NOW, desk.revision)
        assert c.post("/api/setup/disconnect", headers=AUTH, json={}).status_code == 200
        assert desk.mode == "manual"
        e.set_connected(True)
        e.ingest(quote(1), NOW + timedelta(seconds=1))
        assert desk.mode == "manual"


def test_proposal_alerts_are_authenticated_bounded_metadata_and_never_expire_or_trade(desk_factory):
    desk, _, _ = desk_factory()
    engine = desk.engine
    desk.set_mode("approval", NOW, desk.revision)
    record = desk.offer(candidate(), NOW, {"kind": "intraday", "candle": {"close": "500"}})
    now = NOW + timedelta(minutes=3)

    def persisted():
        with sqlite3.connect(engine.settings.database) as db:
            assert D(db.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0]) == D(
                "25000"
            )
            assert db.execute("SELECT count(*) FROM orders").fetchone()[0] == 0
            assert db.execute("SELECT count(*) FROM fills").fetchone()[0] == 0
            return list(db.iterdump())

    with TestClient(
        create_app(engine, clock=lambda: now, background=False, desk=desk),
        base_url="http://127.0.0.1",
    ) as client:
        before = persisted()
        assert client.get("/api/desk/alerts").status_code == 401
        response = client.get("/api/desk/alerts", headers=AUTH)
        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 100
        assert data["decisions"] == [
            {"id": record["id"], "state": "awaiting_approval", "expires_at": record["expires_at"]}
        ]
        assert data["observed_at"] > record["expires_at"]
        assert persisted() == before


def test_proposal_alert_metadata_prioritizes_pending_and_caps_large_history(
    desk_factory, monkeypatch
):
    desk, _, _ = desk_factory()
    desk.set_mode("approval", NOW, desk.revision)
    pending = desk.offer(candidate(), NOW, {"kind": "intraday", "candle": {"close": "500"}})
    with desk.engine.db.transaction() as tx:
        for index in range(105):
            record = {**pending, "id": f"history-{index}", "state": "expired"}
            tx.execute(
                "INSERT INTO desk_decisions VALUES (?,?,?,?)",
                (record["id"], pending["created_at"], "expired", json.dumps(record)),
            )
    queries = []
    snapshot = desk.engine.db.read_snapshot

    @contextmanager
    def traced_snapshot():
        with snapshot() as tx:
            tx.set_trace_callback(queries.append)
            yield tx

    monkeypatch.setattr(desk.engine.db, "read_snapshot", traced_snapshot)
    with TestClient(
        create_app(desk.engine, clock=lambda: NOW, background=False, desk=desk),
        base_url="http://127.0.0.1",
    ) as client:
        records = client.get("/api/desk/alerts", headers=AUTH).json()["decisions"]
        assert len(records) == 100
        assert records[0]["id"] == pending["id"]
        assert records[1]["id"] == "history-104"
        assert all(set(row) == {"id", "state", "expires_at"} for row in records)
        query = next(q for q in queries if q.startswith("SELECT payload FROM desk_decisions"))
        with snapshot() as tx:
            plan = " ".join(row[3] for row in tx.execute("EXPLAIN QUERY PLAN " + query))
        assert "desk_alert_priority" in plan and "TEMP B-TREE" not in plan
