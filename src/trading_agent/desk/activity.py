"""Read-only cursor pages of actual orders/fills and their original decision reasons."""

import json
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from trading_agent.models import stamp

D = Decimal


def activity(engine: Any, now: datetime, before: int = 0, limit: int = 50) -> dict[str, Any]:
    if not 1 <= limit <= 100 or before < 0:
        raise ValueError("Invalid activity page.")
    with engine.lock, engine.db.transaction() as tx:
        rows = tx.execute(
            "SELECT rowid AS cursor,* FROM orders "
            + ("WHERE rowid<? " if before else "")
            + "ORDER BY rowid DESC LIMIT ?",
            (before, limit + 1) if before else (limit + 1,),
        ).fetchall()
        entries = []
        for row in rows[:limit]:
            order = dict(row)
            decision = tx.execute(
                "SELECT payload FROM desk_decisions WHERE json_extract(payload,'$.order_id')=? "
                "ORDER BY rowid DESC LIMIT 1",
                (order["id"],),
            ).fetchone()
            original = tx.execute(
                "SELECT payload FROM events WHERE entity=? AND kind='candidate' "
                "ORDER BY seq LIMIT 1",
                (order["id"],),
            ).fetchone()
            legacy = tx.execute(
                "SELECT 1 FROM events WHERE entity=? AND kind='automation_candidate' LIMIT 1",
                (order["id"],),
            ).fetchone()
            fills = [
                dict(r)
                for r in tx.execute(
                    "SELECT * FROM fills WHERE order_id=? ORDER BY seq DESC LIMIT 101",
                    (order["id"],),
                )
            ]
            turnover, fees = D(order["turnover"]), D(order["fees"])
            debit = turnover + fees if order["side"] == "BUY" else -(turnover - fees)
            entries.append(
                {
                    "order": order,
                    "decision": json.loads(decision[0]) if decision else None,
                    "origin": "desk"
                    if decision
                    else "bound_intraday_automation"
                    if legacy
                    else "manual_instruction"
                    if original or order["reason"].startswith("OPERATOR_")
                    else "protective_control",
                    "original_instruction": json.loads(original[0]) if original else None,
                    "fills": fills[:100],
                    "fills_truncated": len(fills) > 100,
                    "average_fill_price": str(
                        (turnover / order["filled"]).quantize(D(".0001"), rounding=ROUND_HALF_UP)
                    )
                    if order["filled"]
                    else None,
                    "cash_debit": str(debit),
                    "cash_debit_explanation": "Positive is cash spent; negative is cash received. "
                    "This is cash flow, not trade profit.",
                }
            )
        return {
            "observed_at": stamp(now),
            "entries": entries,
            "next_before": rows[limit - 1]["cursor"] if len(rows) > limit else None,
            "limit": limit,
            "paper_only": True,
        }


def fill_page(engine: Any, identity: str, before: int = 0) -> dict[str, Any]:
    with engine.lock, engine.db.transaction() as tx:
        if not tx.execute("SELECT 1 FROM orders WHERE id=?", (identity,)).fetchone():
            raise KeyError(identity)
        rows = [
            dict(r)
            for r in tx.execute(
                "SELECT * FROM fills WHERE order_id=? "
                + ("AND seq<? " if before else "")
                + "ORDER BY seq DESC LIMIT 101",
                (identity, before) if before else (identity,),
            )
        ]
        return {
            "order_id": identity,
            "fills": rows[:100],
            "next_before": rows[99]["seq"] if len(rows) > 100 else None,
        }
