"""Delivery paper contracts and startup verification. No broker order capability."""

import json
import sqlite3
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import Field

from trading_agent.corporate_actions.contracts import ActionBatch, digest
from trading_agent.execution.costs import delivery_charges
from trading_agent.market_data.calendar import IST
from trading_agent.models import DomainModel, Symbol


class HoldingReview(DomainModel):
    symbol: Symbol
    session_date: date
    no_corporate_action: bool = Field(strict=True)
    reference: str = Field(min_length=3, max_length=300, pattern=r".*\S.*")


class HoldingExit(DomainModel):
    symbol: Symbol


def review_key(day: str, symbol: str) -> str:
    return f"lt_review:{day}:{symbol}"


def dp_key(day: str, symbol: str) -> str:
    return f"lt_dp:{day}:{symbol}"


def reconcile_delivery(tx: sqlite3.Connection) -> None:
    """Rebuild delivery fee/day markers and review authority from the durable ledger."""
    meta = {row[0]: row[1] for row in tx.execute("SELECT key,value FROM meta")}
    evidence = bool(
        tx.execute("SELECT 1 FROM events WHERE kind='long_term_start' LIMIT 1").fetchone()
    )
    has_markers = any(key.startswith("lt_") for key in meta) or "long_term_schema" in meta
    if meta.get("investment_horizon") != "long_term":
        if evidence or has_markers:
            raise RuntimeError("missing long-term account horizon")
        return
    charges = delivery_charges()
    if (
        not evidence
        or meta.get("long_term_schema") != "1"
        or meta.get("charges_version") != charges.version
    ):
        raise RuntimeError("missing or unsupported delivery account metadata")
    for key in ("lt_peak_equity", "lt_last_equity", "lt_last_equity_time", "lt_last_clock"):
        if key not in meta:
            raise RuntimeError("missing long-term accounting checkpoint")
    if any(not Decimal(meta[key]).is_finite() for key in ("lt_peak_equity", "lt_last_equity")):
        raise RuntimeError("non-finite long-term equity checkpoint")
    if Decimal(meta["lt_peak_equity"]) < max(
        Decimal(meta["initial_cash"]), Decimal(meta["lt_last_equity"])
    ):
        raise RuntimeError("invalid durable equity high-water mark")
    for key in ("lt_last_equity_time", "lt_last_clock"):
        if datetime.fromisoformat(meta[key]).utcoffset() is None:
            raise RuntimeError("invalid long-term checkpoint clock")
    fills = list(
        tx.execute(
            "SELECT f.*,o.side,o.symbol FROM fills f JOIN orders o "
            "ON o.id=f.order_id ORDER BY f.seq"
        )
    )
    active: dict[str, dict[str, Any]] = {}
    sessions: dict[str, Any] = {}
    quarantines: dict[str, Any] = {}
    index = 0
    for event in tx.execute(
        "SELECT * FROM events WHERE kind IN "
        "('long_term_review','fill','corporate_action_batch') ORDER BY seq"
    ):
        payload = json.loads(event["payload"])
        if event["kind"] == "long_term_review":
            review = HoldingReview.model_validate(payload["review"])
            day = review.session_date.isoformat()
            if datetime.fromisoformat(event["time"]).astimezone(IST).date() != review.session_date:
                raise RuntimeError("review clock differs from reviewed session")
            quarantine = "lt_quarantine:" + review.symbol
            if review.no_corporate_action and quarantine in quarantines:
                raise RuntimeError("corporate-action quarantine was bypassed")
            if not review.no_corporate_action:
                quarantines.setdefault(quarantine, review.model_dump(mode="json"))
            active[review_key(day, review.symbol)] = review.model_dump(mode="json")
            if day in sessions and sessions[day] != payload["session"]:
                raise RuntimeError("changed reviewed session definition")
            sessions[day] = payload["session"]
        elif event["kind"] == "corporate_action_batch":
            batch = ActionBatch.model_validate(payload["request"])
            key = "lt_quarantine:" + batch.symbol
            if (
                key not in quarantines
                or digest(quarantines[key]) != batch.quarantine_sha256
                or payload["quarantine"] != quarantines[key]
            ):
                raise RuntimeError("corporate-action resolution lacks matching quarantine")
            del quarantines[key]
        else:
            if index >= len(fills):
                raise RuntimeError("extra delivery fill event")
            fill = fills[index]
            index += 1
            if (
                event["entity"],
                event["time"],
                payload["quantity"],
                Decimal(payload["price"]),
                Decimal(payload["fees"]),
            ) != (
                fill["order_id"],
                fill["time"],
                fill["quantity"],
                Decimal(fill["price"]),
                Decimal(fill["fees"]),
            ):
                raise RuntimeError("delivery fill journal differs from ledger")
            day = datetime.fromisoformat(fill["time"]).astimezone(IST).date().isoformat()
            authority = active.get(review_key(day, fill["symbol"]))
            if not authority or not authority["no_corporate_action"]:
                raise RuntimeError("delivery fill lacked active price-basis review")
    if index != len(fills):
        raise RuntimeError("missing delivery fill journal")
    stored_reviews = {
        key: json.loads(value) for key, value in meta.items() if key.startswith("lt_review:")
    }
    if active != stored_reviews or sessions != {
        key.removeprefix("lt_session:"): json.loads(value)
        for key, value in meta.items()
        if key.startswith("lt_session:")
    }:
        raise RuntimeError("delivery review metadata differs from journal")
    if quarantines != {
        key: json.loads(value) for key, value in meta.items() if key.startswith("lt_quarantine:")
    }:
        raise RuntimeError("corporate-action quarantine differs from journal")
    latches = {}
    for event in tx.execute(
        "SELECT entity,payload FROM events WHERE kind='long_term_exit_requested' ORDER BY seq"
    ):
        payload = json.loads(event["payload"])
        latches[f"lt_exit:{event['entity']}:{payload['opened']}"] = payload["reason"]
    if latches != {key: value for key, value in meta.items() if key.startswith("lt_exit:")}:
        raise RuntimeError("durable holding exit differs from journal")
    expected_days: dict[str, str] = {}
    expected_dp: dict[str, Decimal] = {}
    turnover: dict[str, Decimal] = {}
    fees: dict[str, Decimal] = {}
    for fill in fills:
        order = fill["order_id"]
        turnover[order] = (
            turnover.get(order, Decimal(0)) + Decimal(fill["price"]) * fill["quantity"]
        )
        total = charges.fee(fill["side"], turnover[order])
        if fill["side"] == "SELL":
            day = datetime.fromisoformat(fill["time"]).astimezone(IST).date().isoformat()
            key = dp_key(day, fill["symbol"])
            if key not in expected_days:
                expected_days[key] = order
                expected_dp[order] = expected_dp.get(order, Decimal(0)) + charges.dp_sell
            total += expected_dp.get(order, Decimal(0)) - charges.dp_sell
        if total - fees.get(order, Decimal(0)) != Decimal(fill["fees"]):
            raise RuntimeError("delivery fill fee schedule reconciliation failed")
        fees[order] = total
    if expected_days != {
        key: value for key, value in meta.items() if key.startswith("lt_dp:")
    } or expected_dp != {
        key.removeprefix("lt_order_dp:"): Decimal(value)
        for key, value in meta.items()
        if key.startswith("lt_order_dp:")
    }:
        raise RuntimeError("delivery DP charge metadata differs from fills")
