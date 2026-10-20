from datetime import timedelta
from decimal import Decimal

from conftest import NOW, TOKEN, quote
from fastapi.testclient import TestClient

from trading_agent.api.app import create_app
from trading_agent.execution.delivery import HoldingReview
from trading_agent.portfolio.service import view

AUTH = {"Authorization": "Bearer " + TOKEN}


def test_contribution_and_sip_api_complete_review_confirmation_and_fill(long_term_factory):
    e = long_term_factory()
    e.review_holding(
        HoldingReview(
            symbol="NSE:DEMO",
            session_date=NOW.date(),
            no_corporate_action=True,
            reference="invented clear basis",
        ),
        NOW,
    )
    e.ingest(quote(), NOW)
    current = [NOW]
    with TestClient(create_app(e, clock=lambda: current[0]), base_url="http://127.0.0.1") as client:
        for path in ["/portfolio", "/portfolio.js", "/money.js"]:
            response = client.get(path)
            assert (
                response.status_code == 200
                and "default-src" in response.headers["content-security-policy"]
            )
        assert client.get("/api/paper/portfolio").status_code == 401
        r = {
            "intent_id": "api-contrib",
            "symbol": "NSE:DEMO",
            "budget": "2000",
            "stop": "490",
            "target": "600",
            "reference": "reviewed test",
        }
        proposal = client.post("/api/paper/portfolio/preview", headers=AUTH, json=r)
        assert proposal.status_code == 200, proposal.text
        data = proposal.json()
        assert data["decision"]["quantity"] == 3
        assert not e.orders()
        body = {"request": r, "preview_sha256": data["preview_sha256"]}
        blocked = client.post(
            "/api/paper/portfolio/contributions",
            headers=AUTH | {"Origin": "https://untrusted.example"},
            json=body,
        )
        assert blocked.status_code == 403 and not e.orders()
        order = client.post("/api/paper/portfolio/contributions", headers=AUTH, json=body)
        assert order.status_code == 200 and order.json()["state"] == "ACCEPTED"
        current[0] += timedelta(seconds=1)
        e.ingest(quote(1), current[0])
        assert (
            client.post("/api/paper/portfolio/contributions", headers=AUTH, json=body).json()[
                "filled"
            ]
            == 3
        )
        add = {
            "intent_id": "api-add",
            "symbol": "NSE:DEMO",
            "budget": "1000",
            "reference": "reviewed addition",
        }
        data = client.post("/api/paper/portfolio/preview", headers=AUTH, json=add).json()
        assert data["decision"]["quantity"] == 1
        assert (
            client.post(
                "/api/paper/portfolio/contributions",
                headers=AUTH,
                json={"request": add, "preview_sha256": data["preview_sha256"]},
            ).status_code
            == 200
        )
        current[0] += timedelta(seconds=1)
        e.ingest(quote(2), current[0])
        result = client.get("/api/paper/portfolio", headers=AUTH).json()
        assert len(result["lots"]) == 2 and result["account"]["positions"][0]["quantity"] == 4
        assert sum(Decimal(lot["original_cost"]) for lot in result["lots"]) == Decimal(
            25000
        ) - Decimal(result["account"]["cash"])
        plan = {
            "plan_id": "api-sip",
            "symbol": "NSE:DEMO",
            "budget": "1000",
            "sessions": [NOW.date().isoformat()],
            "stop_pct": "2",
            "target_pct": "4",
            "reference": "explicit reviewed date",
        }
        assert client.post("/api/paper/portfolio/plans", headers=AUTH, json=plan).status_code == 200
        due = client.get("/api/paper/portfolio", headers=AUTH).json()["plans"][0]["occurrences"][0]
        assert due["status"] == "DUE"
        assert (
            client.post(
                "/api/paper/portfolio/plans/cancel",
                headers=AUTH,
                json={"plan_id": "api-sip", "reference": "operator cancellation"},
            ).status_code
            == 200
        )
        assert view(e, current[0])["plans"][0]["cancelled"]
        assert (
            client.post(
                "/api/paper/portfolio/preview", headers=AUTH, json={**add, "budget": "NaN"}
            ).status_code
            == 422
        )
    with e.db.transaction() as tx:
        e.db.reconcile(tx)


def test_portfolio_api_rejects_intraday_and_expired_approval(engine):
    with TestClient(create_app(engine, clock=lambda: NOW), base_url="http://127.0.0.1") as client:
        assert client.get("/api/paper/portfolio", headers=AUTH).status_code == 409
        assert (
            client.post(
                "/api/paper/portfolio/preview",
                headers=AUTH,
                json={
                    "intent_id": "bad",
                    "symbol": "NSE:DEMO",
                    "budget": "1000",
                    "reference": "test",
                },
            ).status_code
            == 409
        )
