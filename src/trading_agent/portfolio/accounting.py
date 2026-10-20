"""SELECT-only reconstruction of contribution approvals and SIP occurrence authority."""

import json
import sqlite3
from datetime import datetime, time
from decimal import Decimal

from trading_agent.execution.costs import delivery_charges
from trading_agent.market_data.calendar import IST
from trading_agent.models import Candidate, Quote, RiskDecision, utc
from trading_agent.portfolio.contracts import (
    CancelPlan,
    Contribution,
    SIPPlan,
    digest,
    occurrence_request,
    plain,
)

D = Decimal


def reconcile(tx: sqlite3.Connection) -> set[str]:
    meta = dict(tx.execute("SELECT key,value FROM meta"))
    tables = {
        r[0]
        for r in tx.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name IN ('portfolio_requests','sip_plans')"
        )
    }
    events = list(
        tx.execute(
            "SELECT * FROM events WHERE kind IN "
            "('portfolio_contribution','sip_plan_created','sip_plan_cancelled') ORDER BY seq"
        )
    )
    rows_present = any(tx.execute(f"SELECT 1 FROM {name} LIMIT 1").fetchone() for name in tables)
    if not (meta.get("portfolio_schema") or events or rows_present):
        return set()
    if (
        meta.get("portfolio_schema") != "1"
        or not events
        or meta.get("investment_horizon") != "long_term"
        or len(tables) != 2
    ):
        raise RuntimeError("missing or unsupported portfolio accounting authority")
    plans = {}
    cancellations = set()
    contributions = set()
    occurrences = set()
    for event in events:
        payload = json.loads(event["payload"])
        now = utc(datetime.fromisoformat(event["time"]))
        if event["kind"] == "sip_plan_created":
            plan = SIPPlan.model_validate(payload["request"])
            row = tx.execute("SELECT * FROM sip_plans WHERE id=?", (event["entity"],)).fetchone()
            if (
                not row
                or row["id"] in plans
                or row["id"] != plan.plan_id
                or row["time"] != event["time"]
                or json.loads(row["request"]) != plain(plan)
                or json.loads(row["sessions"]) != payload["sessions"]
                or set(payload["sessions"]) != {day.isoformat() for day in plan.sessions}
                or plan.sessions[0] < now.astimezone(IST).date()
            ):
                raise RuntimeError("SIP plan reconstruction failed")
            for definition in payload["sessions"].values():
                if not definition["source"].strip() or not time(9) <= time.fromisoformat(
                    definition["open"]
                ) < time.fromisoformat(definition["close"]) <= time(16):
                    raise RuntimeError("invalid SIP session definition")
            plans[plan.plan_id] = plan
        elif event["kind"] == "sip_plan_cancelled":
            cancel_request = CancelPlan.model_validate(payload)
            if (
                cancel_request.plan_id != event["entity"]
                or cancel_request.plan_id not in plans
                or cancel_request.plan_id in cancellations
            ):
                raise RuntimeError("invalid SIP cancellation authority")
            cancellations.add(cancel_request.plan_id)
        else:
            request = Contribution.model_validate(payload["request"])
            row = tx.execute(
                "SELECT * FROM portfolio_requests WHERE id=?", (event["entity"],)
            ).fetchone()
            order = tx.execute("SELECT * FROM orders WHERE id=?", (event["entity"],)).fetchone()
            preview = payload["preview"]
            candidate = Candidate.model_validate(preview["candidate"])
            quote = Quote.model_validate(preview["quote"])
            decision = RiskDecision.model_validate(preview["decision"])
            if (
                not row
                or not order
                or request.intent_id in contributions
                or row["id"] != request.intent_id
                or row["time"] != event["time"]
                or row["time"] != order["created"]
                or json.loads(row["request"]) != plain(request)
                or json.loads(row["preview"]) != preview
                or preview["request"] != plain(request)
                or preview["preview_sha256"]
                != digest({k: v for k, v in preview.items() if k != "preview_sha256"})
            ):
                raise RuntimeError("contribution approval reconstruction failed")
            expected_cash = decision.price_cap * decision.quantity + delivery_charges().fee(
                "BUY", decision.price_cap * decision.quantity
            )
            if (
                not decision.allowed
                or decision.quantity <= 0
                or expected_cash != decision.cash_reservation
                or expected_cash > request.budget
                or request.symbol != candidate.symbol
                or candidate.symbol != quote.symbol
                or candidate.intent_id != request.intent_id
                or candidate.decision_time != quote.received_time
                or max(quote.exchange_time, quote.received_time) > now
                or preview["policy_sha256"] != meta["policy_hash"]
                or preview["charges_version"] != meta["charges_version"]
                or (
                    order["symbol"],
                    order["side"],
                    order["quantity"],
                    D(order["cap"]),
                    D(order["stop"]),
                    D(order["target"]),
                )
                != (
                    request.symbol,
                    "BUY",
                    decision.quantity,
                    decision.price_cap,
                    candidate.stop,
                    candidate.target,
                )
            ):
                raise RuntimeError("contribution order differs from its reviewed economics")
            holding = preview["holding"]
            if holding and (D(holding["stop"]), D(holding["target"])) != (
                candidate.stop,
                candidate.target,
            ):
                raise RuntimeError("contribution changed existing holding protections")
            if row["plan_id"] != request.plan_id or row["occurrence"] != (
                str(request.occurrence) if request.occurrence else None
            ):
                raise RuntimeError("contribution occurrence identity changed")
            if request.plan_id:
                saved_plan = plans.get(request.plan_id)
                key = request.plan_id, request.occurrence
                if (
                    not saved_plan
                    or saved_plan.plan_id in cancellations
                    or request.occurrence != now.astimezone(IST).date()
                    or request.occurrence not in saved_plan.sessions
                    or preview["plan"] != plain(saved_plan)
                    or key in occurrences
                    or plain(request) != plain(occurrence_request(saved_plan, request.occurrence))
                ):
                    raise RuntimeError("SIP occurrence lacked active scheduled authority")
                occurrences.add(key)
            elif preview["plan"] is not None:
                raise RuntimeError("manual contribution has unexpected SIP authority")
            contributions.add(request.intent_id)
    if (
        len(plans) != tx.execute("SELECT COUNT(*) FROM sip_plans").fetchone()[0]
        or len(contributions) != tx.execute("SELECT COUNT(*) FROM portfolio_requests").fetchone()[0]
        or cancellations != {r[0] for r in tx.execute("SELECT id FROM sip_plans WHERE cancelled=1")}
    ):
        raise RuntimeError("portfolio accounting journal is incomplete")
    return contributions
