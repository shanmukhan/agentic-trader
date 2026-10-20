"""Source-preserving overnight-account evidence, separate from intraday automation reports."""

import hashlib
import json
import os
from collections import Counter
from pathlib import Path
from typing import Any

from trading_agent.backtesting.report import journal_digest, ledger_results
from trading_agent.corporate_actions.accounting import pending_claims
from trading_agent.corporate_actions.contracts import digest
from trading_agent.persistence.database import Database


def long_term_report(db: Database, output: Path) -> dict[str, Any]:
    with db.transaction() as tx:
        db.reconcile(tx)
        if db.get(tx, "investment_horizon") != "long_term":
            raise ValueError("long-term report requires a delivery paper account")
        if tx.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("account integrity failure")
        meta = {row[0]: row[1] for row in tx.execute("SELECT key,value FROM meta")}
        claims_summary = pending_claims(tx)
        batches = [
            {"id": row[0], "time": row[1], **json.loads(row[2])}
            for row in tx.execute("SELECT id,time,payload FROM corporate_batches ORDER BY time,id")
        ]
        positions = [dict(row) for row in tx.execute("SELECT * FROM positions ORDER BY symbol")]
        sources: Counter[str] = Counter()
        for row in tx.execute("SELECT payload FROM events WHERE kind='quote'"):
            sources[json.loads(row[0])["source"]] += 1
        incidents = {
            row[0]: row[1]
            for row in tx.execute(
                "SELECT kind,COUNT(*) FROM events WHERE kind IN "
                "('long_term_quote_blocked','long_term_exit_blocked',"
                "'data_quality','kill_switch') GROUP BY kind"
            )
        }
    trades, metrics = ledger_results(db)
    report: dict[str, Any] = {
        "schema_version": 2,
        "mode": "paper",
        "investment_horizon": "long_term",
        "ready_for_live": False,
        "external_acceptance_verified": False,
        "settlement_verified": False,
        "synthetic": meta.get("long_term_demo") == "true" or set(sources) != {"kite"},
        "quote_sources": dict(sources),
        "risk_policy_sha256": meta["policy_hash"],
        "charges_version": meta["charges_version"],
        "cash": meta["cash"],
        "fees": meta["fees"],
        "realized_pnl": meta["total_realized"],
        "income_received": meta.get("lt_income_received", "0"),
        "fraction_realized_pnl": meta.get("lt_fraction_realized", "0"),
        **claims_summary,
        "corporate_action_batches": batches,
        "corporate_claims": {
            key.removeprefix("lt_claim:"): json.loads(value)
            for key, value in meta.items()
            if key.startswith("lt_claim:")
        },
        "positions": positions,
        "metrics": metrics,
        "last_trusted_equity": meta["lt_last_equity"],
        "last_trusted_equity_time": meta["lt_last_equity_time"],
        "observed_peak_equity": meta["lt_peak_equity"],
        "quarantines": {
            key.removeprefix("lt_quarantine:"): json.loads(value)
            for key, value in meta.items()
            if key.startswith("lt_quarantine:")
        },
        "quarantine_sha256": {
            key.removeprefix("lt_quarantine:"): digest(json.loads(value))
            for key, value in meta.items()
            if key.startswith("lt_quarantine:")
        },
        "dp_days": sum(key.startswith("lt_dp:") for key in meta),
        "incident_counts": incidents,
        "journal_sha256": journal_digest(db),
        "limitations": [
            "Virtual holdings only; real custody and settlement are unverified.",
            "Last trusted equity is a past observation, not an official closing valuation.",
            "Only explicitly reviewed offline split/bonus/dividend batches are applied.",
            "Unpaid dividends are nonspendable; fractional claims have no invented value.",
            "Trade metrics exclude dividend income and separately reported fraction receipts.",
            "Share credit/entitlement assertions do not prove real demat or bank balances.",
            "Costs are estimates; personal taxes, AMC and unusual settlements are excluded.",
            "No validated daily strategy, long-term ML or automatic rebalancing is supplied.",
        ],
    }
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    artifacts = {
        "report.json": json.dumps(report, indent=2, sort_keys=True, default=str) + "\n",
        "trades.jsonl": "".join(
            json.dumps(trade, sort_keys=True, default=str) + "\n" for trade in trades
        ),
        "report.md": "# Long-term paper account report\n\n"
        "PAPER ONLY. Live/external/settlement acceptance: false.\n\n"
        + f"Cash: {report['cash']}; realized P&L: {report['realized_pnl']}; "
        + f"fees: {report['fees']}.\n\n"
        + f"Dividend income received: {report['income_received']}; known unpaid receivables: "
        + f"{report['receivable']}; unvalued fractional claims: "
        + f"{report['unvalued_fractional_claims']}.\n\n"
        + f"Open holdings: {len(positions)}; pending orders: {metrics['pending_orders']}; "
        + f"DP symbol/days: {report['dp_days']}.\n\n"
        + "## Measurement limits\n\n"
        + "".join("- " + item + "\n" for item in report["limitations"]),
    }
    for name, content in artifacts.items():
        with os.fdopen(
            os.open(output / name, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "w"
        ) as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
    if journal_digest(db) != report["journal_sha256"]:
        raise RuntimeError("source journal changed during reporting")
    manifest = {
        "schema_version": 1,
        "state": "finished",
        "ready_for_live": False,
        "sha256": {
            name: hashlib.sha256(content.encode()).hexdigest()
            for name, content in artifacts.items()
        },
    }
    with os.fdopen(
        os.open(output / "manifest.json", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "w"
    ) as file:
        file.write(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
        file.flush()
        os.fsync(file.fileno())
    return report
