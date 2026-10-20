"""Invented split, bonus/fraction, dividend and restart lifecycle in an isolated account."""

import json
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from trading_agent.corporate_actions.contracts import ActionBatch, CashReceipt, digest
from trading_agent.corporate_actions.service import apply_batch, record_receipt
from trading_agent.execution.paper_broker import PaperBroker
from trading_agent.paper.long_term_demo import (
    START,
    delivery_quote,
    delivery_review,
    open_delivery_demo,
)
from trading_agent.paper.long_term_report import long_term_report
from trading_agent.persistence.database import Database


def corporate_actions_demo(directory: Path) -> dict[str, Any]:
    engine = open_delivery_demo(directory)
    settings, calendar = engine.settings, engine.calendar
    try:
        for offset, name in ((1, "split-dividend"), (2, "bonus-fraction")):
            now = START + timedelta(days=offset)
            delivery_review(engine, now, clear=False)
            with engine.db.transaction() as tx:
                quarantine = json.loads(engine.db.get(tx, "lt_quarantine:NSE:DEMO"))
            common = {
                "ex_date": now.date().isoformat(),
                "record_date": now.date().isoformat(),
                "announced_at": START.isoformat(),
                "reference": "INVENTED issuer notice",
            }
            actions: list[dict[str, Any]] = [
                {
                    **common,
                    "action_id": name,
                    "kind": "split" if offset == 1 else "bonus",
                    "numerator": 2 if offset == 1 else 1,
                    "denominator": 1 if offset == 1 else 3,
                    "credit_date": now.date().isoformat(),
                }
            ]
            if offset == 1:
                actions.append(
                    {
                        **common,
                        "action_id": "dividend",
                        "kind": "dividend",
                        "per_share": "2.00",
                        "withholding": "5.60",
                        "payment_date": "2026-10-22",
                    }
                )
            request = ActionBatch.model_validate(
                {
                    "batch_id": name,
                    "symbol": "NSE:DEMO",
                    "quarantine_sha256": digest(quarantine),
                    "reviewed_at": now.isoformat(),
                    "reference": "INVENTED complete basis review",
                    "covers_all_actions": True,
                    "actions": actions,
                }
            )
            (directory / f"{name}.json").write_text(request.model_dump_json(indent=2) + "\n")
            engine.db.close()
            db = Database(settings.database, settings.starting_cash)
            try:
                apply_batch(db, settings, calendar, request, now)
                assert apply_batch(db, settings, calendar, request, now)["idempotent"]
            finally:
                db.close()
            db = Database(settings.database, settings.starting_cash)
            engine = PaperBroker(db, settings, calendar, recovery_time=now)
            delivery_review(engine, now)
            engine.set_connected(True)
            engine.ingest(
                delivery_quote(now + timedelta(seconds=1), bid="250" if offset == 1 else "188"),
                now + timedelta(seconds=1),
            )
        exit_at = START + timedelta(days=2, seconds=1)
        engine.exit_holding("NSE:DEMO", exit_at)
        engine.ingest(
            delivery_quote(exit_at + timedelta(seconds=1), bid="188", volume=1100),
            exit_at + timedelta(seconds=1),
        )
        engine.db.close()
        db = Database(settings.database, settings.starting_cash)
        try:
            for name, claim, amount, offset in (
                ("dividend-cash", "dividend", "50.40", 2),
                ("fraction-cash", "bonus-fraction", "62.50", 3),
            ):
                now = START + timedelta(days=offset, seconds=3)
                receipt = CashReceipt(
                    payment_id=name,
                    claim_id=claim,
                    paid_date=now.date(),
                    net_amount=Decimal(amount),
                    reviewed_at=now,
                    reference="INVENTED reviewed net bank receipt",
                )
                (directory / f"{name}.json").write_text(receipt.model_dump_json(indent=2) + "\n")
                record_receipt(db, settings, receipt, now)
                assert record_receipt(db, settings, receipt, now)["idempotent"]
            report = long_term_report(db, directory / "evidence")
            result = {
                "synthetic": True,
                "ready_for_live": False,
                "cash": report["cash"],
                "realized_pnl": report["realized_pnl"],
                "income_received": report["income_received"],
                "fraction_realized_pnl": report["fraction_realized_pnl"],
                "positions": len(report["positions"]),
                "receivable": report["receivable"],
                "unvalued_fractional_claims": report["unvalued_fractional_claims"],
            }
            (directory / "summary.json").write_text(
                json.dumps(result, indent=2, sort_keys=True) + "\n"
            )
            (directory / "summary.md").write_text(
                "# Invented corporate-action lifecycle\n\n"
                "Paper only; no market-return, demat, bank or live acceptance evidence.\n\n"
                "14 shares become 28 after a split, then 37 plus a 1/3-share claim after a bonus. "
                "Whole shares exit; separately reviewed net dividend/fraction receipts "
                "complete the ledger.\n"
            )
            return result
        finally:
            db.close()
    finally:
        engine.db.close()
