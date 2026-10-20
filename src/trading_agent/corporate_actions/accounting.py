"""Deterministic entitlement derivation and ordered reconstruction from durable evidence."""

import json
import sqlite3
from collections.abc import Iterator
from datetime import datetime
from decimal import Decimal
from fractions import Fraction
from typing import Any

from trading_agent.corporate_actions.contracts import (
    ActionBatch,
    CashReceipt,
    DividendAction,
    plain,
)
from trading_agent.execution.costs import down, up
from trading_agent.market_data.calendar import IST
from trading_agent.models import Quote, stamp, utc

D = Decimal


def derive_batch(
    batch: ActionBatch,
    position: dict[str, Any] | None,
    tick: Decimal,
    now: datetime,
) -> dict[str, Any]:
    batch = ActionBatch.model_validate(plain(batch.model_dump()))
    now = utc(now)
    today = now.astimezone(IST).date()
    reviewed_day = batch.reviewed_at.astimezone(IST).date()
    if batch.reviewed_at > now or any(
        action.record_date > min(today, reviewed_day) for action in batch.actions
    ):
        raise ValueError("review and record dates cannot be in the future")
    before = dict(position) if position else None
    after = dict(position) if position else None
    claims: list[dict[str, Any]] = []
    for index, action in enumerate(batch.actions):
        qty = after["quantity"] if after else 0
        claim: dict[str, Any] = {
            "claim_id": action.action_id,
            "batch_id": batch.batch_id,
            "symbol": batch.symbol,
            "paid_id": None,
            "basis": "0",
            "numerator": 0,
            "denominator": 1,
        }
        if isinstance(action, DividendAction):
            gross = action.per_share * qty
            if action.withholding > gross:
                raise ValueError("withholding exceeds this paper dividend entitlement")
            if qty:
                claims.append(
                    {
                        **claim,
                        "kind": "dividend",
                        "gross": str(gross),
                        "withholding": str(action.withholding),
                        "amount": str(gross - action.withholding),
                        "payable_from": action.payment_date.isoformat(),
                        "entitled_quantity": qty,
                    }
                )
            continue
        if action.credit_date > min(today, reviewed_day):
            raise ValueError("reviewed share credit date has not arrived")
        factor = Fraction(action.numerator, action.denominator)
        if action.kind == "bonus":
            factor += 1
        exact = qty * factor
        whole, remainder = divmod(exact.numerator, exact.denominator)
        if whole > 2**31 - 1:
            raise ValueError("corporate action exceeds supported holding size")
        if after:
            # Assign whole paise to the claim; the holding retains the exact residual.
            fraction_basis = down(D(after["cost"]) * D(remainder) / exact.numerator)
            after["quantity"] = whole
            after["cost"] = str(D(after["cost"]) - fraction_basis)
            # Price levels remain conservative and on the registered instrument tick.
            ratio = D(factor.denominator) / factor.numerator
            after["stop"] = str(down(D(after["stop"]) * ratio, tick))
            after["target"] = str(up(D(after["target"]) * ratio, tick))
            if D(after["stop"]) <= 0 or D(after["target"]) <= D(after["stop"]):
                raise ValueError("adjusted protective levels are outside supported ticks")
            if remainder:
                if index != len(batch.actions) - 1:
                    raise ValueError("fractional entitlement must be the final action in a batch")
                claims.append(
                    {
                        **claim,
                        "kind": "fraction",
                        "amount": None,
                        "basis": str(fraction_basis),
                        "numerator": remainder,
                        "denominator": exact.denominator,
                        "payable_from": action.credit_date.isoformat(),
                    }
                )
    return {"before": before, "after": after, "claims": claims}


def derive_receipt(receipt: CashReceipt, claim: dict[str, Any], now: datetime) -> dict[str, Any]:
    receipt = CashReceipt.model_validate(plain(receipt.model_dump()))
    now = utc(now)
    if receipt.reviewed_at > now or not (
        datetime.fromisoformat(claim["payable_from"]).date()
        <= receipt.paid_date
        <= min(now.astimezone(IST).date(), receipt.reviewed_at.astimezone(IST).date())
    ):
        raise ValueError("receipt dates precede entitlement or are in the future")
    if claim["paid_id"]:
        raise ValueError("entitlement has already been paid")
    if claim["kind"] == "dividend" and receipt.net_amount != D(claim["amount"]):
        raise ValueError("receipt differs from frozen net dividend entitlement")
    return {
        "claim_id": receipt.claim_id,
        "cash": str(receipt.net_amount),
        "income": str(receipt.net_amount if claim["kind"] == "dividend" else D(0)),
        "capital_pnl": str(
            receipt.net_amount - D(claim["basis"]) if claim["kind"] == "fraction" else D(0)
        ),
    }


def steps(tx: sqlite3.Connection) -> Iterator[tuple[str, dict[str, Any]]]:
    """Retain legacy fill-only accounts; LT2 interleaves table-backed actions by journal seq."""
    fills = tx.execute(
        "SELECT f.*,o.side,o.symbol,o.stop,o.target,o.reason,o.cap,o.created "
        "FROM fills f JOIN orders o "
        "ON o.id=f.order_id ORDER BY f.seq"
    )
    enabled = tx.execute("SELECT 1 FROM meta WHERE key='corporate_actions_schema'").fetchone()
    evidence = tx.execute(
        "SELECT 1 FROM events WHERE kind IN ('corporate_action_batch','corporate_cash_receipt') "
        "LIMIT 1"
    ).fetchone()
    tables = {
        row[0]
        for row in tx.execute(
            "SELECT name FROM sqlite_master WHERE type='table' "
            "AND name IN ('corporate_batches','corporate_payments')"
        )
    }
    rows_present = any(tx.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone() for table in tables)
    if not (enabled or evidence or rows_present):
        yield from (("fill", dict(row)) for row in fills)
        return
    if not enabled or not evidence or len(tables) != 2:
        raise RuntimeError("missing corporate-action accounting evidence")
    meta = dict(tx.execute("SELECT key,value FROM meta"))
    if meta.get("investment_horizon") != "long_term" or meta["corporate_actions_schema"] != "1":
        raise RuntimeError("unsupported corporate-action account binding")
    counts = {"corporate_batches": 0, "corporate_payments": 0}
    fill = iter(fills)
    for event in tx.execute(
        "SELECT * FROM events WHERE kind IN "
        "('fill','corporate_action_batch','corporate_cash_receipt') ORDER BY seq"
    ):
        if event["kind"] == "fill":
            row = next(fill, None)
            if row is None:
                raise RuntimeError("extra financial fill journal")
            payload = json.loads(event["payload"])
            if (
                event["entity"] != row["order_id"]
                or event["time"] != row["time"]
                or payload
                != {"quantity": row["quantity"], "price": row["price"], "fees": row["fees"]}
            ):
                raise RuntimeError("financial fill journal differs from ledger")
            yield "fill", dict(row)
            continue
        table = (
            "corporate_batches"
            if event["kind"] == "corporate_action_batch"
            else "corporate_payments"
        )
        row = tx.execute(f"SELECT * FROM {table} WHERE id=?", (event["entity"],)).fetchone()
        if (
            not row
            or row["time"] != event["time"]
            or json.loads(row["payload"]) != json.loads(event["payload"])
        ):
            raise RuntimeError("corporate-action journal differs from financial ledger")
        counts[table] += 1
        yield event["kind"], {**dict(row), "event_seq": event["seq"]}
    if next(fill, None) is not None or any(
        counts[table] != tx.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in counts
    ):
        raise RuntimeError("missing or duplicate financial journal evidence")


class Ledger:
    """Reconstruct current economics without trusting materialized cash/positions/claims."""

    def __init__(self, tx: sqlite3.Connection):
        self._tx = tx
        from trading_agent.portfolio.accounting import reconcile

        self.contributions = reconcile(tx)
        self.entry_orders: dict[str, str] = {}
        meta = dict(tx.execute("SELECT key,value FROM meta"))
        self.cash = D(meta["initial_cash"])
        self.positions: dict[str, dict[str, Any]] = {}
        self.turnovers: dict[str, Decimal] = {}
        self.order_fees: dict[str, Decimal] = {}
        self.fees, self.realized, self.income, self.fraction_pnl = (D(0) for _ in range(4))
        self.claims: dict[str, dict[str, Any]] = {}
        self.bases: dict[str, str] = {}
        action_ids: set[str] = set()
        applied_dates: dict[str, Any] = {}
        fill_dates: dict[str, Any] = {}
        for kind, row in steps(tx):
            if kind == "fill":
                self.fill(row)
                fill_dates[row["symbol"]] = (
                    datetime.fromisoformat(row["time"]).astimezone(IST).date()
                )
                continue
            payload = json.loads(row["payload"])
            now = utc(datetime.fromisoformat(row["time"]))
            if kind == "corporate_action_batch":
                batch = ActionBatch.model_validate_json(row["request"])
                if (
                    batch.batch_id != row["id"]
                    or batch.symbol != row["symbol"]
                    or plain(batch.model_dump()) != payload["request"]
                ):
                    raise RuntimeError("corporate-action ledger identity mismatch")
                ids = {action.action_id for action in batch.actions}
                if ids & action_ids or batch.actions[0].ex_date <= applied_dates.get(
                    batch.symbol, datetime.min.date()
                ):
                    raise RuntimeError("duplicate or out-of-order corporate action")
                action_ids.update(ids)
                applied_dates[batch.symbol] = batch.actions[-1].ex_date
                first_ex = batch.actions[0].ex_date
                if fill_dates.get(batch.symbol, datetime.min.date()) >= first_ex:
                    raise RuntimeError("corporate adjustment crossed an ex-date fill")
                for quote_row in tx.execute(
                    "SELECT payload FROM events WHERE kind='quote' AND entity=? AND seq<?",
                    (batch.symbol, row["event_seq"]),
                ):
                    if (
                        Quote.model_validate_json(quote_row[0]).exchange_time.astimezone(IST).date()
                        >= first_ex
                    ):
                        raise RuntimeError("corporate adjustment crossed an accepted ex-date quote")
                if any(
                    claim["symbol"] == batch.symbol
                    and claim["kind"] == "fraction"
                    and claim["paid_id"] is None
                    for claim in self.claims.values()
                ):
                    raise RuntimeError("corporate action crossed an unresolved fractional claim")
                if set(payload["sessions"]) != {
                    action.ex_date.isoformat() for action in batch.actions
                }:
                    raise RuntimeError("corporate action is missing reviewed ex-date sessions")
                for day, definition in payload["sessions"].items():
                    opened, closed = (
                        utc(datetime.fromisoformat(definition[key])) for key in ("open", "close")
                    )
                    if (
                        not definition["source"].strip()
                        or opened >= closed
                        or any(
                            value.astimezone(IST).date().isoformat() != day
                            for value in (opened, closed)
                        )
                    ):
                        raise RuntimeError("invalid corporate-action session evidence")
                tick = tx.execute(
                    "SELECT tick FROM instruments WHERE symbol=?", (batch.symbol,)
                ).fetchone()
                if not tick:
                    raise RuntimeError("corporate-action instrument missing")
                expected = derive_batch(batch, self.positions.get(batch.symbol), D(tick[0]), now)
                if expected != payload["result"]:
                    raise RuntimeError("corporate-action entitlement reconstruction failed")
                if expected["after"]:
                    self.positions[batch.symbol] = expected["after"]
                self.claims.update({claim["claim_id"]: claim for claim in expected["claims"]})
                self.bases["lt_basis_after:" + batch.symbol] = stamp(now)
            else:
                receipt = CashReceipt.model_validate_json(row["request"])
                if receipt.payment_id != row["id"] or receipt.claim_id != row["claim_id"]:
                    raise RuntimeError("corporate receipt ledger identity mismatch")
                claim = self.claims.get(receipt.claim_id)
                if claim is None:
                    raise RuntimeError("receipt has no entitlement")
                expected = derive_receipt(receipt, claim, now)
                if expected != payload:
                    raise RuntimeError("corporate cash receipt reconstruction failed")
                self.cash += D(expected["cash"])
                self.income += D(expected["income"])
                self.fraction_pnl += D(expected["capital_pnl"])
                self.realized += D(expected["capital_pnl"])
                claim["paid_id"] = receipt.payment_id
                claim["received"] = expected["cash"]
        if "corporate_actions_schema" in meta:
            if self.claims != {
                key.removeprefix("lt_claim:"): json.loads(value)
                for key, value in meta.items()
                if key.startswith("lt_claim:")
            } or self.bases != {
                key: value for key, value in meta.items() if key.startswith("lt_basis_after:")
            }:
                raise RuntimeError("corporate claims or price-basis metadata differ from ledger")
            if (
                D(meta.get("lt_income_received", "NaN")) != self.income
                or D(meta.get("lt_fraction_realized", "NaN")) != self.fraction_pnl
            ):
                raise RuntimeError("corporate income reconciliation failed")
            receivable = sum(
                (
                    D(claim["amount"])
                    for claim in self.claims.values()
                    if claim["paid_id"] is None and claim["amount"] is not None
                ),
                D(0),
            )
            unknown = sum(
                claim["paid_id"] is None and claim["amount"] is None
                for claim in self.claims.values()
            )
            if D(meta.get("lt_receivable", "NaN")) != receivable or meta.get(
                "lt_unvalued_fraction_count"
            ) != str(unknown):
                raise RuntimeError("corporate receivable cache differs from ledger")
        elif any(
            key.startswith(("lt_claim:", "lt_basis_after:"))
            or key
            in {
                "lt_receivable",
                "lt_unvalued_fraction_count",
                "lt_income_received",
                "lt_fraction_realized",
            }
            for key in meta
        ):
            raise RuntimeError("missing corporate-action schema")

    def fill(self, row: dict[str, Any]) -> None:
        symbol, qty = row["symbol"], row["quantity"]
        value, fee = D(row["price"]) * qty, D(row["fees"])
        if not value.is_finite() or not fee.is_finite() or value <= 0 or fee < 0:
            raise RuntimeError("invalid persisted fill")
        old = self.positions.get(symbol)
        if row["side"] == "BUY":
            if row["order_id"] in self.contributions:
                if D(row["price"]) > D(row["cap"]) or utc(
                    datetime.fromisoformat(row["time"])
                ) <= utc(datetime.fromisoformat(row["created"])):
                    raise RuntimeError(
                        "contribution fill exceeded its cap or preceded execution authority"
                    )
                if row["order_id"] not in self.turnovers:
                    preview = json.loads(
                        self._tx.execute(
                            "SELECT preview FROM portfolio_requests WHERE id=?", (row["order_id"],)
                        ).fetchone()[0]
                    )
                    if old != preview["holding"]:
                        raise RuntimeError(
                            "contribution holding basis changed before its first fill"
                        )
            if (
                old
                and row["order_id"] != self.entry_orders[symbol]
                and row["order_id"] not in self.contributions
            ):
                raise RuntimeError("holding addition lacks a reviewed contribution")
            if old is None:
                self.entry_orders[symbol] = row["order_id"]
            self.positions[symbol] = {
                "symbol": symbol,
                "quantity": qty + (old["quantity"] if old else 0),
                "cost": str(value + fee + (D(old["cost"]) if old else D(0))),
                "stop": old["stop"] if old else row["stop"],
                "target": old["target"] if old else row["target"],
                "opened": old["opened"] if old else row["time"],
            }
            self.cash -= value + fee
        else:
            if old is None or qty > old["quantity"]:
                raise RuntimeError("sell exceeds persisted holding")
            basis = (
                D(old["cost"])
                if qty == old["quantity"]
                else D(old["cost"]) * D(qty) / old["quantity"]
            )
            self.realized += value - fee - basis
            self.cash += value - fee
            if qty == old["quantity"]:
                del self.positions[symbol]
            else:
                old["quantity"] -= qty
                old["cost"] = str(D(old["cost"]) - basis)
        self.fees += fee
        self.turnovers[row["order_id"]] = self.turnovers.get(row["order_id"], D(0)) + value
        self.order_fees[row["order_id"]] = self.order_fees.get(row["order_id"], D(0)) + fee


def pending_claims(tx: sqlite3.Connection) -> dict[str, Any]:
    """O(1) polling summary; caches are maintained atomically and independently verified."""
    values = dict(
        tx.execute(
            "SELECT key,value FROM meta WHERE key IN ('lt_receivable','lt_unvalued_fraction_count')"
        )
    )
    return {
        "receivable": values.get("lt_receivable", "0"),
        "unvalued_fractional_claims": int(values.get("lt_unvalued_fraction_count", "0")),
    }
