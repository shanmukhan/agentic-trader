import sqlite3
from datetime import timedelta
from decimal import Decimal as D

from conftest import NOW, TOKEN, candidate, quote
from fastapi.testclient import TestClient

from trading_agent.api.app import create_app
from trading_agent.execution.delivery import HoldingReview
from trading_agent.models import Instrument
from trading_agent.portfolio.contracts import Contribution
from trading_agent.portfolio.service import preview

AUTH = {"Authorization": "Bearer " + TOKEN}


def financial_rows(engine):
    with sqlite3.connect(engine.settings.database) as tx:
        return {
            table: tx.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()
            for table in ("orders", "fills", "positions")
        } | {"cash": tx.execute("SELECT value FROM meta WHERE key='cash'").fetchone()}


def save(client, symbols):
    state = client.get("/api/desk/watchlist", headers=AUTH).json()
    return client.post(
        "/api/desk/watchlist",
        headers=AUTH,
        json={
            "symbols": symbols,
            "revision": state["safety"]["revision"],
            "acknowledged": True,
        },
    )


def test_catalog_auth_confirmation_literal_search_and_reads_preserve_finances(engine):
    with TestClient(
        create_app(engine, clock=lambda: NOW, background=False), base_url="http://127.0.0.1"
    ) as client:
        before = financial_rows(engine)
        assert client.get("/api/desk/watchlist").status_code == 401
        assert client.get("/api/desk/watchlist/catalog").status_code == 401
        page = client.get("/watchlist")
        assert page.status_code == 200 and 'id="ack"' in page.text
        assert page.headers["X-Frame-Options"] == "SAMEORIGIN"
        catalog = client.get("/api/desk/watchlist/catalog?q=demo", headers=AUTH).json()
        assert [r["symbol"] for r in catalog["items"]] == ["NSE:DEMO"]
        assert client.get("/api/desk/watchlist/catalog?q=%25", headers=AUTH).json()["matches"] == 0
        current = client.get("/api/desk/watchlist", headers=AUTH).json()
        payload = {
            "symbols": ["NSE:DEMO"],
            "revision": current["safety"]["revision"],
            "acknowledged": False,
        }
        assert client.post("/api/desk/watchlist", headers=AUTH, json=payload).status_code == 409
        payload["acknowledged"] = True
        assert (
            client.post(
                "/api/desk/watchlist", headers={**AUTH, "Origin": "https://evil.test"}, json=payload
            ).status_code
            == 403
        )
        assert save(client, ["NSE:UNKNOWN"]).status_code == 409
        assert save(client, ["NSE:DEMO", "NSE:DEMO"]).status_code == 409
        assert financial_rows(engine) == before


def test_manual_api_cannot_bypass_watchlist_and_replacement_cancels_reserved_buys(engine):
    engine.register([Instrument(symbol="NSE:OTHER", token=257, tick_size=D(".05"))])
    engine.ingest(quote(symbol="NSE:OTHER", token=257), NOW)
    with TestClient(
        create_app(engine, clock=lambda: NOW, background=False), base_url="http://127.0.0.1"
    ) as client:
        assert save(client, ["NSE:DEMO"]).status_code == 200
        rejected = client.post(
            "/api/paper/intents",
            headers=AUTH,
            json=candidate("outside", symbol="NSE:OTHER").model_dump(mode="json"),
        ).json()
        assert rejected["state"] == "REJECTED" and "SYMBOL_OUTSIDE_WATCHLIST" in rejected["reason"]
        accepted = client.post(
            "/api/paper/intents", headers=AUTH, json=candidate("pending").model_dump(mode="json")
        ).json()
        assert accepted["state"] == "ACCEPTED"
        current = client.get("/api/desk/watchlist", headers=AUTH).json()
        assert save(client, []).status_code == 200
        stale = client.post(
            "/api/desk/watchlist",
            headers=AUTH,
            json={
                "symbols": ["NSE:DEMO"],
                "revision": current["safety"]["revision"],
                "acknowledged": True,
            },
        )
        assert stale.status_code == 409
        engine.ingest(quote(1), NOW + timedelta(seconds=1))
        with sqlite3.connect(engine.settings.database) as tx:
            assert tx.execute(
                "SELECT state,reserved_cash,reserved_risk FROM orders WHERE id='pending'"
            ).fetchone() == ("CANCELLED", "0", "0")
            assert tx.execute("SELECT count(*) FROM fills").fetchone()[0] == 0
            assert tx.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0] == "25000"


def test_contributions_obey_watchlist_and_held_stock_can_exit_after_removal(long_term_factory):
    engine = long_term_factory(stream_tokens=(1,))
    engine.review_holding(
        HoldingReview(
            symbol="NSE:DEMO",
            session_date=NOW.date(),
            no_corporate_action=True,
            reference="invented clear basis",
        ),
        NOW,
    )
    engine.ingest(quote(), NOW)
    now = [NOW]
    with TestClient(
        create_app(engine, clock=lambda: now[0], background=False), base_url="http://127.0.0.1"
    ) as client:
        request = Contribution(
            intent_id="scheduled",
            symbol="NSE:DEMO",
            budget="2000",
            reference="invented existing cash",
            stop="490",
            target="550",
        )
        assert "WATCHLIST_EMPTY" in preview(engine, request, NOW)["decision"]["reasons"]
        assert save(client, ["NSE:DEMO"]).status_code == 200
        assert (
            engine.submit(candidate("holding", stop="490", target="550"), NOW)["state"]
            == "ACCEPTED"
        )
        now[0] += timedelta(seconds=1)
        engine.ingest(quote(1), now[0])
        assert save(client, []).status_code == 200
        value = client.get("/api/desk/watchlist", headers=AUTH).json()
        assert value["held_outside_watchlist"] == ["NSE:DEMO"]
        assert (
            client.post(
                "/api/paper/long-term/exit", headers=AUTH, json={"symbol": "NSE:DEMO"}
            ).status_code
            == 200
        )
        now[0] += timedelta(seconds=1)
        engine.ingest(quote(2), now[0])
        with sqlite3.connect(engine.settings.database) as tx:
            assert tx.execute("SELECT count(*) FROM positions").fetchone()[0] == 0
            assert tx.execute("SELECT side,state FROM orders WHERE side='SELL'").fetchone() == (
                "SELL",
                "FILLED",
            )


def test_strategy_cannot_offer_a_buy_outside_watchlist(desk_factory):
    desk, _, _ = desk_factory()
    desk.engine.safety.enable(NOW)
    with desk.engine.db.transaction() as tx:
        desk.engine.safety.replace(tx, ["NSE:DEMO"], 1, NOW)
    desk.mode = "automatic"
    assert (
        desk.offer(
            candidate("outside-strategy", symbol="NSE:BROAD"), NOW, {"signal_key": "invented"}
        )
        is None
    )
    with sqlite3.connect(desk.engine.settings.database) as tx:
        assert tx.execute("SELECT count(*) FROM desk_decisions").fetchone()[0] == 0
        assert tx.execute("SELECT count(*) FROM orders").fetchone()[0] == 0


def test_drawdown_resume_requires_current_acknowledgement_and_keeps_data_block(engine):
    with TestClient(
        create_app(engine, clock=lambda: NOW, background=False), base_url="http://127.0.0.1"
    ) as client:
        assert save(client, ["NSE:DEMO"]).status_code == 200
        with engine.lock, engine.db.transaction() as tx:
            engine.safety.observe(tx, NOW, {"equity": "18750", "valuation_fresh": True})
            engine.safety.block_data(tx, NOW, "INVENTED_INVALID_PRICE")
        state = client.get("/api/desk/watchlist", headers=AUTH).json()
        revision = state["safety"]["revision"]
        assert state["safety"]["paused"]
        assert (
            client.post(
                "/api/desk/safety/resume",
                headers=AUTH,
                json={
                    "revision": revision,
                    "acknowledged": False,
                },
            ).status_code
            == 409
        )
        assert (
            client.post(
                "/api/desk/safety/resume",
                headers=AUTH,
                json={
                    "revision": revision - 1,
                    "acknowledged": True,
                },
            ).status_code
            == 409
        )
        result = client.post(
            "/api/desk/safety/resume",
            headers=AUTH,
            json={
                "revision": revision,
                "acknowledged": True,
            },
        )
        assert result.status_code == 200
        assert result.json()["mode"] == "manual"
        assert not result.json()["safety"]["paused"]
        assert result.json()["safety"]["data_blocked_today"]
        with sqlite3.connect(engine.settings.database) as tx:
            assert tx.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0] == "25000"
            assert tx.execute("SELECT count(*) FROM orders").fetchone()[0] == 0
