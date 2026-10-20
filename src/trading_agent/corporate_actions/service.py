"""Exclusive offline, atomic paper adjustments. No broker, network or order submission."""

import json
import sqlite3
from datetime import datetime, time
from decimal import Decimal
from pathlib import Path
from typing import Any

from trading_agent.corporate_actions.accounting import D, derive_batch, derive_receipt
from trading_agent.corporate_actions.contracts import ActionBatch, CashReceipt, digest, plain
from trading_agent.market_data.calendar import IST, SessionCalendar
from trading_agent.models import Quote, stamp, utc
from trading_agent.persistence.database import Database
from trading_agent.risk.policy import policy_fingerprint
from trading_agent.settings import Settings


def load_request(path: Path, contract: type[ActionBatch] | type[CashReceipt]) -> Any:
    if path.is_symlink() or not path.is_file():
        raise ValueError("reviewed action input must be a regular local file")
    with path.open("rb") as file:
        data = file.read(65537)
    if len(data) > 65536:
        raise ValueError("corporate-action input exceeds 64 KiB")

    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate JSON field in reviewed financial input")
            result[key] = value
        return result

    def finite(value: str) -> None:
        raise ValueError("non-finite JSON value")

    return contract.model_validate(
        json.loads(
            data.decode("utf-8"),
            object_pairs_hook=unique,
            parse_float=Decimal,
            parse_constant=finite,
        )
    )


def checked_account(tx: sqlite3.Connection, settings: Settings, now: datetime) -> None:
    if (
        settings.investment_horizon != "long_term"
        or Database.get(tx, "investment_horizon") != "long_term"
    ):
        raise ValueError("corporate actions require a long-term paper account")
    if Database.get(tx, "policy_hash") != policy_fingerprint(settings):
        raise ValueError("account risk policy differs from configured policy")
    if now < datetime.fromisoformat(Database.get(tx, "lt_last_clock")):
        raise ValueError("long-term clock cannot move backward")


def session_definitions(batch: ActionBatch, calendar: SessionCalendar) -> dict[str, Any]:
    result = {}
    for action in batch.actions:
        now = datetime.combine(action.ex_date, time(12), IST)
        bounds = calendar.bounds(now)
        if not bounds or not calendar.sources.get(action.ex_date, "").strip():
            raise ValueError("corporate ex-date requires a sourced reviewed exchange session")
        result[action.ex_date.isoformat()] = {
            "open": bounds[0].isoformat(),
            "close": bounds[1].isoformat(),
            "source": calendar.sources[action.ex_date],
        }
    return result


def validate_calendar(tx: sqlite3.Connection, calendar: SessionCalendar) -> None:
    if not tx.execute("SELECT 1 FROM meta WHERE key='corporate_actions_schema'").fetchone():
        return
    for row in tx.execute("SELECT request,payload FROM corporate_batches"):
        batch = ActionBatch.model_validate_json(row[0])
        if session_definitions(batch, calendar) != json.loads(row[1])["sessions"]:
            raise ValueError("previously used corporate-action session definition changed")


def refresh_claims(tx: sqlite3.Connection) -> None:
    receivable, unknown = D(0), 0
    for row in tx.execute("SELECT value FROM meta WHERE key GLOB 'lt_claim:*'"):
        claim = json.loads(row[0])
        if claim["paid_id"] is None:
            if claim["amount"] is None:
                unknown += 1
            else:
                receivable += D(claim["amount"])
    Database.set(tx, "lt_receivable", receivable)
    Database.set(tx, "lt_unvalued_fraction_count", unknown)


def apply_batch(
    db: Database,
    settings: Settings,
    calendar: SessionCalendar,
    batch: ActionBatch,
    now: datetime,
) -> dict[str, Any]:
    now = utc(now)
    request = plain(batch.model_dump())
    with db.transaction() as tx:
        db.reconcile(tx)
        checked_account(tx, settings, now)
        old = tx.execute("SELECT * FROM corporate_batches WHERE id=?", (batch.batch_id,)).fetchone()
        if old:
            if json.loads(old["request"]) != request:
                raise ValueError("batch identity reused with different input")
            return {"idempotent": True, "paper_only": True, **json.loads(old["payload"])}
        validate_calendar(tx, calendar)
        sessions = session_definitions(batch, calendar)
        for day, definition in sessions.items():
            pinned = tx.execute(
                "SELECT value FROM meta WHERE key=?", ("lt_session:" + day,)
            ).fetchone()
            if pinned and json.loads(pinned[0]) != definition:
                raise ValueError("previously reviewed session definition changed")
        quarantine = tx.execute(
            "SELECT value FROM meta WHERE key=?", ("lt_quarantine:" + batch.symbol,)
        ).fetchone()
        if not quarantine or digest(json.loads(quarantine[0])) != batch.quarantine_sha256:
            raise ValueError("current quarantine evidence hash is required")
        tick = tx.execute("SELECT tick FROM instruments WHERE symbol=?", (batch.symbol,)).fetchone()
        if not tick:
            raise ValueError("corporate action requires a registered instrument")
        first_ex = batch.actions[0].ex_date
        for row in tx.execute("SELECT value FROM meta WHERE key GLOB 'lt_claim:*'"):
            claim = json.loads(row[0])
            if (
                claim["symbol"] == batch.symbol
                and claim["kind"] == "fraction"
                and not claim["paid_id"]
            ):
                raise ValueError("settle the existing fractional claim before another action batch")
        for row in tx.execute(
            "SELECT payload FROM events WHERE kind='quote' AND entity=?", (batch.symbol,)
        ):
            if Quote.model_validate_json(row[0]).exchange_time.astimezone(IST).date() >= first_ex:
                raise ValueError(
                    "accepted ex-date quote: rebuild reviewed history in a new account"
                )
        for row in tx.execute(
            "SELECT f.time FROM fills f JOIN orders o ON o.id=f.order_id WHERE o.symbol=?",
            (batch.symbol,),
        ):
            if datetime.fromisoformat(row[0]).astimezone(IST).date() >= first_ex:
                raise ValueError("ex-date fill prevents retroactive corporate adjustment")
        for row in tx.execute("SELECT request FROM corporate_batches"):
            previous = ActionBatch.model_validate_json(row[0])
            if {action.action_id for action in previous.actions} & {
                action.action_id for action in batch.actions
            }:
                raise ValueError("action identity already used")
            if previous.symbol == batch.symbol and previous.actions[-1].ex_date >= first_ex:
                raise ValueError(
                    "same-date and earlier actions must be reviewed in one ordered batch"
                )
        position = tx.execute("SELECT * FROM positions WHERE symbol=?", (batch.symbol,)).fetchone()
        result = derive_batch(batch, dict(position) if position else None, D(tick[0]), now)
        payload = {
            "request": request,
            "quarantine": json.loads(quarantine[0]),
            "sessions": sessions,
            "result": result,
        }
        tx.execute(
            "INSERT INTO corporate_batches VALUES (?,?,?,?,?)",
            (
                batch.batch_id,
                stamp(now),
                batch.symbol,
                json.dumps(request, sort_keys=True),
                json.dumps(payload, sort_keys=True),
            ),
        )
        db.set(tx, "corporate_actions_schema", "1")
        for key in ("lt_income_received", "lt_fraction_realized"):
            if not tx.execute("SELECT 1 FROM meta WHERE key=?", (key,)).fetchone():
                db.set(tx, key, "0")
        if result["after"]:
            after = result["after"]
            tx.execute(
                "UPDATE positions SET quantity=?,cost=?,stop=?,target=? WHERE symbol=?",
                (
                    after["quantity"],
                    after["cost"],
                    after["stop"],
                    after["target"],
                    batch.symbol,
                ),
            )
        for claim in result["claims"]:
            db.set(tx, "lt_claim:" + claim["claim_id"], json.dumps(claim, sort_keys=True))
        refresh_claims(tx)
        for row in tx.execute(
            "SELECT id FROM orders WHERE symbol=? AND state IN ('ACCEPTED','PARTIAL')",
            (batch.symbol,),
        ).fetchall():
            tx.execute(
                "UPDATE orders SET state='CANCELLED',reserved_cash='0',reserved_risk='0',"
                "reason='CORPORATE_ACTION_BASIS' WHERE id=?",
                (row[0],),
            )
            db.event(
                tx,
                stamp(now),
                "order_state",
                row[0],
                {"state": "CANCELLED", "reason": "CORPORATE_ACTION_BASIS"},
            )
        # No adjusted quote is fabricated, and stale intraday candles cannot cross the basis.
        tx.execute("DELETE FROM quotes WHERE symbol=?", (batch.symbol,))
        tx.execute("DELETE FROM candles WHERE symbol=?", (batch.symbol,))
        tx.execute("DELETE FROM meta WHERE key=?", ("lt_quarantine:" + batch.symbol,))
        db.set(tx, "lt_basis_after:" + batch.symbol, stamp(now))
        db.set(tx, "lt_last_clock", stamp(now))
        db.event(tx, stamp(now), "corporate_action_batch", batch.batch_id, payload)
        db.reconcile(tx)
        return {"idempotent": False, "paper_only": True, **payload}


def record_receipt(
    db: Database,
    settings: Settings,
    receipt: CashReceipt,
    now: datetime,
) -> dict[str, Any]:
    now = utc(now)
    request = plain(receipt.model_dump())
    with db.transaction() as tx:
        db.reconcile(tx)
        checked_account(tx, settings, now)
        old = tx.execute(
            "SELECT * FROM corporate_payments WHERE id=?", (receipt.payment_id,)
        ).fetchone()
        if old:
            if json.loads(old["request"]) != request:
                raise ValueError("payment identity reused with different input")
            return {"idempotent": True, "paper_only": True, **json.loads(old["payload"])}
        row = tx.execute(
            "SELECT value FROM meta WHERE key=?", ("lt_claim:" + receipt.claim_id,)
        ).fetchone()
        if not row:
            raise ValueError("unknown corporate-action entitlement")
        claim = json.loads(row[0])
        payload = derive_receipt(receipt, claim, now)
        tx.execute(
            "INSERT INTO corporate_payments VALUES (?,?,?,?,?)",
            (
                receipt.payment_id,
                stamp(now),
                receipt.claim_id,
                json.dumps(request, sort_keys=True),
                json.dumps(payload, sort_keys=True),
            ),
        )
        db.set(tx, "cash", D(db.get(tx, "cash")) + receipt.net_amount)
        db.set(tx, "total_realized", D(db.get(tx, "total_realized")) + D(payload["capital_pnl"]))
        db.set(tx, "lt_income_received", D(db.get(tx, "lt_income_received")) + D(payload["income"]))
        db.set(
            tx,
            "lt_fraction_realized",
            D(db.get(tx, "lt_fraction_realized")) + D(payload["capital_pnl"]),
        )
        if db.get(tx, "day") == now.astimezone(IST).date().isoformat():
            db.set(tx, "day_realized", D(db.get(tx, "day_realized")) + D(payload["capital_pnl"]))
        claim["paid_id"], claim["received"] = receipt.payment_id, payload["cash"]
        db.set(tx, "lt_claim:" + receipt.claim_id, json.dumps(claim, sort_keys=True))
        refresh_claims(tx)
        db.set(tx, "lt_last_clock", stamp(now))
        db.event(tx, stamp(now), "corporate_cash_receipt", receipt.payment_id, payload)
        db.reconcile(tx)
        return {"idempotent": False, "paper_only": True, **payload}
