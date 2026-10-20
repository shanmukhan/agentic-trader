"""Review exact account/quote context before each separately funded paper purchase."""

import json
import sqlite3
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from trading_agent.execution.costs import down, up
from trading_agent.market_data.calendar import IST
from trading_agent.models import Candidate, RiskDecision, stamp, utc
from trading_agent.portfolio.contracts import (
    Approval,
    CancelPlan,
    Contribution,
    SIPPlan,
    digest,
    occurrence_request,
    plain,
)
from trading_agent.risk.policy import policy_fingerprint

if TYPE_CHECKING:
    from trading_agent.execution.paper_broker import PaperBroker

D = Decimal


def require_account(engine: "PaperBroker") -> None:
    if not engine.long_term or engine.model or engine.automation:
        raise ValueError("contributions require a manual long-term paper account")


def prepare(
    engine: "PaperBroker", tx: sqlite3.Connection, request: Contribution, now: datetime
) -> dict[str, Any]:
    require_account(engine)
    now = utc(now)
    quote = engine._quote(tx, request.symbol)
    position = tx.execute("SELECT * FROM positions WHERE symbol=?", (request.symbol,)).fetchone()
    reasons = engine._entry_reasons(tx, quote, now)
    if tx.execute("SELECT 1 FROM orders WHERE id=?", (request.intent_id,)).fetchone():
        reasons.append("INTENT_ALREADY_RECORDED")
    held = {r[0] for r in tx.execute("SELECT symbol FROM positions")}
    pending = {
        r[0]
        for r in tx.execute(
            "SELECT symbol FROM orders WHERE side='BUY' AND state IN ('ACCEPTED','PARTIAL')"
        )
    }
    if request.symbol in pending:
        reasons.append("ENTRY_ALREADY_PENDING")
    if len(held | pending | {request.symbol}) > engine.settings.max_positions:
        reasons.append("POSITION_LIMIT")
    if (
        position
        and tx.execute(
            "SELECT 1 FROM meta WHERE key=?", (f"lt_exit:{request.symbol}:{position['opened']}",)
        ).fetchone()
    ):
        reasons.append("HOLDING_EXIT_ALREADY_REQUESTED")
    if tx.execute(
        "SELECT 1 FROM orders WHERE symbol=? AND side='SELL' AND state IN ('ACCEPTED','PARTIAL')",
        (request.symbol,),
    ).fetchone():
        reasons.append("HOLDING_EXIT_ALREADY_PENDING")
    plan = None
    if request.plan_id:
        assert request.occurrence is not None
        row = tx.execute("SELECT * FROM sip_plans WHERE id=?", (request.plan_id,)).fetchone()
        if not row:
            raise ValueError("unknown SIP plan")
        plan = SIPPlan.model_validate_json(row["request"])
        if plain(request) != plain(occurrence_request(plan, request.occurrence)):
            raise ValueError("SIP instruction differs from its saved occurrence")
        if (
            row["cancelled"]
            or request.occurrence != now.astimezone(IST).date()
            or request.occurrence not in plan.sessions
        ):
            reasons.append("SIP_NOT_DUE_OR_CANCELLED")
        if tx.execute(
            "SELECT 1 FROM portfolio_requests WHERE plan_id=? AND occurrence=?",
            (request.plan_id, str(request.occurrence)),
        ).fetchone():
            reasons.append("SIP_OCCURRENCE_ALREADY_RECORDED")
    elif request.intent_id.startswith("sip-"):
        raise ValueError("reserved SIP intent namespace")
    stop, target = request.stop, request.target
    if position:
        stop, target = D(position["stop"]), D(position["target"])
        if request.stop is not None and (request.stop, request.target) != (stop, target):
            reasons.append("HOLDING_PROTECTIONS_CANNOT_CHANGE")
    elif plan and quote:
        tick = engine._tick(tx, request.symbol)
        stop = down(quote.ask * (1 - plan.stop_pct / 100), tick)
        target = up(quote.ask * (1 + plan.target_pct / 100), tick)
    if stop is None or target is None or stop <= 0:
        reasons.append("NEW_HOLDING_PROTECTIONS_REQUIRED")
    candidate = None
    decision = RiskDecision(allowed=False, reasons=tuple(dict.fromkeys(reasons)))
    if not reasons and quote and stop is not None and target is not None:
        candidate = Candidate(
            intent_id=request.intent_id,
            symbol=request.symbol,
            stop=stop,
            target=target,
            decision_time=quote.received_time,
            reason="reviewed cash-budget contribution",
        )
        decision = engine._size_entry(tx, candidate, quote, now, budget=request.budget, add=True)
    snapshot = engine._snapshot(tx, now)
    payload = {
        "schema_version": 1,
        "request": plain(request),
        "candidate": candidate.model_dump(mode="json") if candidate else None,
        "decision": decision.model_dump(mode="json"),
        "holding": dict(position) if position else None,
        "quote": quote.model_dump(mode="json") if quote else None,
        "available_cash": snapshot["available_cash"],
        "exposure": snapshot["exposure"],
        "reserved_risk": snapshot["reserved_risk"],
        "day_pnl": snapshot["day_pnl"],
        "kill": snapshot["kill"],
        "policy_sha256": policy_fingerprint(engine.settings),
        "charges_version": engine.charges.version,
        "day": snapshot["day"],
        "quote_fresh": engine._fresh(quote, now),
        "plan": plain(plan) if plan else None,
    }
    return {**payload, "preview_sha256": digest(payload)}


def preview(engine: "PaperBroker", request: Contribution, now: datetime) -> dict[str, Any]:
    with engine.lock, engine.db.transaction() as tx:
        return prepare(engine, tx, request, now)


def confirm(engine: "PaperBroker", approval: Approval, now: datetime) -> dict[str, Any]:
    require_account(engine)
    with engine.lock:
        with engine.db.transaction() as tx:
            old = tx.execute(
                "SELECT * FROM portfolio_requests WHERE id=?", (approval.request.intent_id,)
            ).fetchone()
            if old:
                if (
                    json.loads(old["request"]) != plain(approval.request)
                    or json.loads(old["preview"])["preview_sha256"] != approval.preview_sha256
                ):
                    raise ValueError(
                        "contribution intent was already used with different instructions"
                    )
                return dict(tx.execute("SELECT * FROM orders WHERE id=?", (old["id"],)).fetchone())
            result = prepare(engine, tx, approval.request, now)
            if (
                result["preview_sha256"] != approval.preview_sha256
                or not result["decision"]["allowed"]
            ):
                raise ValueError("preview changed, expired or blocked: review a fresh preview")
            candidate = Candidate.model_validate(result["candidate"])
        return engine.submit(candidate, now, _contribution=approval)


def record(
    engine: "PaperBroker", tx: sqlite3.Connection, approval: Approval, now: datetime
) -> None:
    result = prepare(engine, tx, approval.request, now)
    # Called immediately before the broker inserts its order, in the same writer transaction.
    if result["preview_sha256"] != approval.preview_sha256 or not result["decision"]["allowed"]:
        raise ValueError("preview changed, expired or blocked: review a fresh preview")
    engine.db.set(tx, "portfolio_schema", "1")
    values = (
        approval.request.intent_id,
        stamp(now),
        json.dumps(plain(approval.request), sort_keys=True),
        json.dumps(result, sort_keys=True),
        approval.request.plan_id,
        str(approval.request.occurrence) if approval.request.occurrence else None,
    )
    tx.execute("INSERT INTO portfolio_requests VALUES (?,?,?,?,?,?)", values)
    engine.db.event(
        tx,
        stamp(now),
        "portfolio_contribution",
        approval.request.intent_id,
        {"request": plain(approval.request), "preview": result},
    )


def create_plan(engine: "PaperBroker", plan: SIPPlan, now: datetime) -> dict[str, Any]:
    require_account(engine)
    now = utc(now)
    with engine.lock, engine.db.transaction() as tx:
        old = tx.execute("SELECT * FROM sip_plans WHERE id=?", (plan.plan_id,)).fetchone()
        if old:
            if json.loads(old["request"]) != plain(plan):
                raise ValueError("SIP plan ID already has different instructions")
            return {"plan": plain(plan), "cancelled": bool(old["cancelled"])}
        if engine.faulted or plan.sessions[0] < now.astimezone(IST).date():
            raise ValueError("SIP plan requires a healthy account and current/future session dates")
        if not tx.execute("SELECT 1 FROM instruments WHERE symbol=?", (plan.symbol,)).fetchone():
            raise ValueError("register the SIP instrument before saving a plan")
        if (
            tx.execute("SELECT COUNT(*) FROM sip_plans WHERE cancelled=0").fetchone()[0] >= 32
            or tx.execute("SELECT COUNT(*) FROM sip_plans").fetchone()[0] >= 1000
        ):
            raise ValueError("SIP plan capacity reached")
        definitions = {}
        for day in plan.sessions:
            bounds = engine.calendar.sessions.get(day)
            source = engine.calendar.sources.get(day, "")
            if not bounds or not source:
                raise ValueError("every SIP date needs a sourced reviewed exchange session")
            definitions[day.isoformat()] = {
                "open": bounds[0].isoformat(),
                "close": bounds[1].isoformat(),
                "source": source,
            }
        assert engine.long_term is not None
        engine.long_term.advance_clock(tx, now)
        engine.db.set(tx, "portfolio_schema", "1")
        tx.execute(
            "INSERT INTO sip_plans VALUES (?,?,?,?,0)",
            (
                plan.plan_id,
                stamp(now),
                json.dumps(plain(plan), sort_keys=True),
                json.dumps(definitions, sort_keys=True),
            ),
        )
        engine.db.event(
            tx,
            stamp(now),
            "sip_plan_created",
            plan.plan_id,
            {"request": plain(plan), "sessions": definitions},
        )
        return {"plan": plain(plan), "cancelled": False}


def cancel_plan(engine: "PaperBroker", request: CancelPlan, now: datetime) -> dict[str, Any]:
    require_account(engine)
    with engine.lock, engine.db.transaction() as tx:
        row = tx.execute("SELECT * FROM sip_plans WHERE id=?", (request.plan_id,)).fetchone()
        if not row:
            raise ValueError("unknown SIP plan")
        if not row["cancelled"]:
            assert engine.long_term is not None
            engine.long_term.advance_clock(tx, utc(now))
            for order in tx.execute(
                "SELECT o.* FROM orders o JOIN portfolio_requests p ON o.id=p.id "
                "WHERE p.plan_id=? AND o.state IN ('ACCEPTED','PARTIAL')",
                (request.plan_id,),
            ).fetchall():
                engine._cancel(tx, order, stamp(now), "SIP_PLAN_CANCELLED")
            tx.execute("UPDATE sip_plans SET cancelled=1 WHERE id=?", (request.plan_id,))
            engine.db.event(tx, stamp(now), "sip_plan_cancelled", request.plan_id, plain(request))
        return {"plan_id": request.plan_id, "cancelled": True}


def validate_calendar(tx: sqlite3.Connection, engine: "PaperBroker") -> None:
    for row in tx.execute("SELECT sessions FROM sip_plans WHERE cancelled=0"):
        for day, definition in json.loads(row[0]).items():
            from datetime import date

            value = date.fromisoformat(day)
            bounds = engine.calendar.sessions.get(value)
            if not bounds or definition != {
                "open": bounds[0].isoformat(),
                "close": bounds[1].isoformat(),
                "source": engine.calendar.sources.get(value, ""),
            }:
                raise ValueError("previously planned SIP session changed or is missing")


def view(engine: "PaperBroker", now: datetime) -> dict[str, Any]:
    require_account(engine)
    today = utc(now).astimezone(IST).date()
    with engine.lock, engine.db.transaction() as tx:
        snapshot = engine._snapshot(tx, utc(now))
        orders = [
            {**dict(row), "actual_debit": str(D(row["turnover"]) + D(row["fees"]))}
            for row in tx.execute(
                "SELECT o.*,p.request FROM orders o JOIN portfolio_requests p ON p.id=o.id "
                "ORDER BY o.rowid DESC LIMIT 101"
            )
        ]
        lots = [
            {
                "lot_id": row["id"],
                "symbol": row["symbol"],
                "original_quantity": row["filled"],
                "original_cost": str(D(row["turnover"]) + D(row["fees"])),
                "fees": row["fees"],
                "order_state": row["state"],
                "ordered_at": row["created"],
                "plan_id": row["plan_id"],
            }
            for row in tx.execute(
                "SELECT o.*,p.plan_id FROM orders o LEFT JOIN portfolio_requests p ON p.id=o.id "
                "WHERE o.side='BUY' AND o.filled>0 ORDER BY o.rowid DESC LIMIT 101"
            )
        ]
        plans = []
        for row in tx.execute("SELECT * FROM sip_plans ORDER BY cancelled,id LIMIT 65"):
            plan = SIPPlan.model_validate_json(row["request"])
            attempts = {
                r["occurrence"]: dict(r)
                for r in tx.execute(
                    "SELECT p.occurrence,o.id,o.state,o.filled,o.quantity "
                    "FROM portfolio_requests p "
                    "JOIN orders o ON o.id=p.id WHERE p.plan_id=?",
                    (plan.plan_id,),
                )
            }
            dates = []
            for day in plan.sessions:
                attempt = attempts.get(day.isoformat())
                status = (
                    attempt["state"]
                    if attempt
                    else "CANCELLED"
                    if row["cancelled"]
                    else "MISSED"
                    if day < today
                    else "DUE"
                    if day == today
                    else "UPCOMING"
                )
                dates.append(
                    {
                        "session": day.isoformat(),
                        "status": status,
                        "order": attempt,
                        "request": plain(occurrence_request(plan, day))
                        if status == "DUE"
                        else None,
                    }
                )
            plans.append(
                {"plan": plain(plan), "cancelled": bool(row["cancelled"]), "occurrences": dates}
            )
        return {
            "schema_version": 1,
            "observed_at": stamp(now),
            "account": snapshot,
            "lots": lots[:100],
            "orders": orders[:100],
            "orders_truncated": len(orders) > 100,
            "lots_truncated": len(lots) > 100,
            "plans": plans[:64],
            "plans_truncated": len(plans) > 64,
            "ready_for_live": False,
        }
