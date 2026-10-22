"""Reopen and reconcile immutable artifacts before publishing bounded JSON evidence."""

import csv
import hashlib
import io
import json
import sqlite3
from collections.abc import Iterator
from contextlib import closing, contextmanager
from datetime import datetime
from decimal import Decimal, DecimalException
from pathlib import Path
from typing import Any, cast

from trading_agent.backtesting.report import ledger_results
from trading_agent.corporate_actions.accounting import pending_claims
from trading_agent.daily_execution.contracts import DailyStrategy
from trading_agent.execution.costs import charges_for, down
from trading_agent.execution.delivery import dp_key
from trading_agent.investment_research.performance import unavailable_performance
from trading_agent.market_data.calendar import IST
from trading_agent.models import Quote
from trading_agent.persistence.database import Database
from trading_agent.research_jobs.isolation import LIMITS
from trading_agent.research_jobs.registry import (
    LIMITATIONS,
    file_hash,
    read_bytes,
    read_private_json,
)
from trading_agent.risk.policy import policy_fingerprint
from trading_agent.settings import Settings

NAMES = {
    "paper.sqlite3",
    "report.json",
    "context.json",
    "index.html",
    "report.md",
    "decisions.jsonl",
    "equity.csv",
    "samples.jsonl",
    "label_audit.jsonl",
}


class _ReadLedger:
    """The existing episode calculator receives only this already-open readonly transaction."""

    def __init__(self, tx: sqlite3.Connection):
        self.tx = tx

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        yield self.tx


def _money(value: Any) -> Decimal:
    if not isinstance(value, str):
        raise ValueError("financial evidence requires exact decimal strings")
    amount = Decimal(value)
    if not amount.is_finite():
        raise ValueError("nonfinite financial evidence")
    return amount


def _final_equity(
    tx: sqlite3.Connection, snapshot: dict[str, Any], policy: Settings, now: datetime
) -> Decimal:
    """Rebuild net liquidation values from durable holdings, quotes and DP charge evidence."""
    charges = charges_for(policy)
    total = _money(Database.get(tx, "cash"))
    claims = pending_claims(tx)
    if snapshot["long_term"]["receivable"] != claims["receivable"] or (
        snapshot["long_term"]["unvalued_fractional_claims"] != claims["unvalued_fractional_claims"]
    ):
        raise ValueError("report claims differ from ledger")
    reported = {position["symbol"]: position for position in snapshot["positions"]}
    for row in tx.execute("SELECT * FROM positions"):
        quote_row = tx.execute(
            "SELECT payload FROM quotes WHERE symbol=?", (row["symbol"],)
        ).fetchone()
        quote = Quote.model_validate_json(quote_row[0]) if quote_row else None
        mark = quote.bid if quote else _money(row["cost"]) / row["quantity"]
        tick = _money(
            tx.execute("SELECT tick FROM instruments WHERE symbol=?", (row["symbol"],)).fetchone()[
                0
            ]
        )
        price = max(tick, down(mark * (1 - policy.slippage_bps / 10000), tick))
        turnover = price * row["quantity"]
        fee = charges.fee("SELL", turnover)
        if tx.execute(
            "SELECT 1 FROM meta WHERE key=?",
            (dp_key(now.astimezone(IST).date().isoformat(), row["symbol"]),),
        ).fetchone():
            fee -= charges.dp_sell
        net = turnover - fee
        if _money(reported[row["symbol"]]["liquidation_value"]) != net or (
            _money(reported[row["symbol"]]["unrealized_pnl"]) != net - _money(row["cost"])
        ):
            raise ValueError("report holding valuation differs from ledger")
        if snapshot["valuation_fresh"] is True and (
            quote is None
            or not all(
                0 <= (now - instant).total_seconds() <= policy.max_quote_age_seconds
                for instant in (quote.exchange_time, quote.received_time)
            )
        ):
            raise ValueError("report incorrectly declares a fresh holding valuation")
        total += net
    if snapshot["valuation_fresh"] is True and claims["unvalued_fractional_claims"]:
        raise ValueError("report incorrectly declares valued fractional claims")
    if snapshot["charges_version"] != charges.version:
        raise ValueError("report charges differ from immutable policy")
    return total + _money(claims["receivable"])


def verify_report(output: Path, record: dict[str, Any], job_id: str) -> dict[str, Any]:
    """Return bounded reconciled evidence; malformed financial artifacts fail closed."""
    try:
        return _verify_report(output, record, job_id)
    except (
        AttributeError,
        DecimalException,
        IndexError,
        KeyError,
        RuntimeError,
        sqlite3.Error,
        TypeError,
    ) as exc:
        raise ValueError("report evidence is malformed or failed ledger reconciliation") from exc


def _verify_report(output: Path, record: dict[str, Any], job_id: str) -> dict[str, Any]:
    """No recovery engine, writes, executable HTML or arbitrary artifact names are served."""
    if output.is_symlink() or not output.is_dir() or output.absolute() != output.resolve():
        raise ValueError("report output must be a regular directory without symlink ancestors")
    manifest = read_private_json(output / "manifest.json", 64 * 1024)
    if manifest.get("state") != "finished" or set(manifest.get("sha256", {})) != NAMES:
        raise ValueError("report manifest is incomplete")
    if manifest.get("ready_for_live") is not False:
        raise ValueError("report unexpectedly declares live authority")
    files = list(output.iterdir())
    names = {path.name for path in files}
    allowed = NAMES | {"manifest.json", "paper.sqlite3.lock"}
    if (
        not NAMES | {"manifest.json"} <= names
        or not names <= allowed
        or any(path.is_symlink() or not path.is_file() for path in files)
    ):
        raise ValueError("report artifacts are not regular files")
    lock = output / "paper.sqlite3.lock"
    if lock.exists() and lock.stat().st_size != 0:
        raise ValueError("report lock artifact is invalid")
    if sum(path.stat().st_size for path in files) > LIMITS["max_output_bytes"]:
        raise ValueError("report exceeds combined output limit")
    for name in NAMES:
        if file_hash(output / name, LIMITS["max_file_bytes"]) != manifest["sha256"][name]:
            raise ValueError("report artifact integrity failed")
    report = read_private_json(output / "report.json", LIMITS["max_file_bytes"])
    expected_inputs = {
        "daily": {
            name: record["source_hashes"]["daily/" + name]
            for name in ("manifest.json", "daily.jsonl")
        },
        "execution": {
            name: record["source_hashes"]["execution/" + name]
            for name in ("manifest.json", "events.jsonl")
        },
    }
    strategy = DailyStrategy.model_validate(record["strategy"])
    policy = Settings.model_validate(record["policy"])
    if (
        report.get("input_hashes") != expected_inputs
        or report.get("strategy") != record["strategy"]
        or report.get("strategy_sha256") != strategy.digest()
        or report.get("risk_policy") != record["policy"]
        or report.get("risk_policy_sha256") != policy_fingerprint(policy)
        or report.get("mode") != "paper"
        or report.get("ready_for_live") is not False
        or report.get("external_acceptance_verified") is not False
        or report.get("synthetic") != record["public"]["synthetic"]
        or report.get("code_sha256") != record["runtime"]["code_sha256"]
        or report.get("charges_version") != record["runtime"]["charges"]["version"]
    ):
        raise ValueError("report differs from its immutable request")
    if report.get("kind") != "daily-delivery-replay-v1" or report.get("status") not in {
        "complete",
        "incomplete",
    }:
        raise ValueError("report kind or status is unsupported")
    if (
        manifest.get("kind") != report["kind"]
        or manifest.get("synthetic") is not report["synthetic"]
    ):
        raise ValueError("report manifest provenance differs from report")
    gates = report["gates"]
    if (
        not isinstance(gates, dict)
        or set(gates)
        != {
            "flat_no_pending_orders",
            "claims_resolved",
            "final_valuation_fresh",
            "held_quote_coverage",
            "quote_quality",
        }
        or any(type(value) is not bool for value in gates.values())
    ):
        raise ValueError("report completeness gates are invalid")
    if report["status"] != ("complete" if all(gates.values()) else "incomplete"):
        raise ValueError("report status differs from completeness gates")
    now = datetime.fromisoformat(report["source_available_through"])
    if now.tzinfo is None:
        raise ValueError("report valuation time requires a timezone")
    with closing(
        sqlite3.connect((output / "paper.sqlite3").as_uri() + "?mode=ro&immutable=1", uri=True)
    ) as tx:
        tx.row_factory = sqlite3.Row
        tx.execute("PRAGMA query_only=ON")
        if tx.execute("PRAGMA quick_check").fetchone()[0] != "ok":
            raise ValueError("report ledger failed SQLite integrity")
        tx.execute("BEGIN")
        Database.reconcile(tx)
        snapshot = report["final_snapshot"]
        if _money(Database.get(tx, "initial_cash")) != policy.starting_cash:
            raise ValueError("report initial cash differs from immutable policy")
        for key, meta in (("cash", "cash"), ("fees", "fees"), ("realized_pnl", "total_realized")):
            if _money(snapshot[key]) != _money(Database.get(tx, meta)):
                raise ValueError("report financial summary differs from ledger")
        if len(snapshot["positions"]) != len({item["symbol"] for item in snapshot["positions"]}):
            raise ValueError("report contains duplicate positions")
        positions = {
            row["symbol"]: (row["quantity"], Decimal(row["cost"]))
            for row in tx.execute("SELECT * FROM positions")
        }
        if positions != {
            row["symbol"]: (row["quantity"], Decimal(row["cost"])) for row in snapshot["positions"]
        }:
            raise ValueError("report positions differ from ledger")
        if _money(snapshot["equity"]) != _final_equity(tx, snapshot, policy, now):
            raise ValueError("report equity differs from ledger valuation")
        expected_trades, expected_metrics = ledger_results(cast(Database, _ReadLedger(tx)))
        expected_metrics.update(
            initial_cash=str(policy.starting_cash),
            net_observed_pnl=str(_money(snapshot["equity"]) - policy.starting_cash),
            income_received=(
                tx.execute("SELECT value FROM meta WHERE key='lt_income_received'").fetchone()
                or ["0"]
            )[0],
            unpaid_claims=sum(
                json.loads(row[0])["paid_id"] is None
                for row in tx.execute("SELECT value FROM meta WHERE key GLOB 'lt_claim:*'")
            ),
        )
        if set(report["metrics"]) != set(expected_metrics) | {
            "observed_drawdown",
            "stale_valuation_observations",
        }:
            raise ValueError("report metric fields differ from supported evidence")
        if (
            gates["flat_no_pending_orders"]
            is not (not positions and expected_metrics["pending_orders"] == 0)
            or gates["claims_resolved"] is not (expected_metrics["unpaid_claims"] == 0)
            or gates["final_valuation_fresh"] is not snapshot["valuation_fresh"]
        ):
            raise ValueError("report completeness gates differ from ledger")
        for name, expected in expected_metrics.items():
            normalized = json.loads(json.dumps(expected, default=str))
            if report["metrics"].get(name) != normalized:
                raise ValueError("report metrics differ from ledger")
        if report["trades"] != json.loads(json.dumps(expected_trades, default=str)):
            raise ValueError("report trade episodes differ from ledger")
        journal = hashlib.sha256()
        for row in tx.execute("SELECT * FROM events ORDER BY seq"):
            journal.update((json.dumps(dict(row), sort_keys=True) + "\n").encode())
        if journal.hexdigest() != report["journal_sha256"]:
            raise ValueError("report journal differs from ledger")
        orders = [
            dict(row) for row in tx.execute("SELECT * FROM orders ORDER BY created,id LIMIT 1001")
        ]
        fills = [dict(row) for row in tx.execute("SELECT * FROM fills ORDER BY seq LIMIT 1001")]
    curve, drawdown = [], []
    peak, maximum_drawdown, stale = policy.starting_cash, Decimal(0), 0
    previous = None
    content = read_bytes(output / "equity.csv", LIMITS["max_file_bytes"]).decode("utf-8")
    reader = csv.DictReader(io.StringIO(content, newline=""))
    if reader.fieldnames != ["time", "equity", "cash", "valuation_fresh", "known_receivable"]:
        raise ValueError("report curve fields are invalid")
    for index, row in enumerate(reader):
        if index >= LIMITS["max_rows"]:
            raise ValueError("report curve exceeds its input bound")
        at = datetime.fromisoformat(row["time"])
        if at.tzinfo is None or previous is not None and at <= previous:
            raise ValueError("report curve time is invalid")
        previous = at
        equity = _money(row["equity"])
        if equity < 0 or _money(row["cash"]) < 0 or _money(row["known_receivable"]) < 0:
            raise ValueError("report curve is invalid")
        if row["valuation_fresh"] not in {"True", "False"}:
            raise ValueError("report valuation flag is invalid")
        fresh = row["valuation_fresh"] == "True"
        curve.append({**row, "valuation_fresh": fresh})
        loss = percent = None
        if fresh:
            peak = max(peak, equity)
            loss = peak - equity
            percent = loss / peak * 100
            maximum_drawdown = max(maximum_drawdown, loss)
        else:
            stale += 1
        drawdown.append(
            {
                "time": row["time"],
                "valuation_fresh": fresh,
                "drawdown": str(loss) if loss is not None else None,
                "drawdown_pct": str(percent) if percent is not None else None,
            }
        )
    if not curve or (
        _money(curve[-1]["equity"]) != _money(snapshot["equity"])
        or _money(curve[-1]["cash"]) != _money(snapshot["cash"])
        or _money(curve[-1]["known_receivable"]) != _money(snapshot["long_term"]["receivable"])
        or curve[-1]["valuation_fresh"] is not snapshot["valuation_fresh"]
        or curve[-1]["time"] != report["source_available_through"]
        or curve[0]["time"] != report["first_event"]
    ):
        raise ValueError("report final valuation differs from curve")
    if (
        _money(report["metrics"]["observed_drawdown"]) != maximum_drawdown
        or report["metrics"]["stale_valuation_observations"] != stale
    ):
        raise ValueError("report observed drawdown differs from fresh curve observations")
    # Hashes are checked again after the SQLite and curve reads, before publication.
    for name in NAMES:
        if file_hash(output / name, LIMITS["max_file_bytes"]) != manifest["sha256"][name]:
            raise ValueError("report artifacts changed during verification")
    if read_private_json(output / "manifest.json", 64 * 1024) != manifest:
        raise ValueError("report manifest changed during verification")
    public = record["public"]
    result = {
        "schema_version": 1,
        "report_id": job_id,
        "resource_id": public["resource_id"],
        "resource_sha256": public["resource_sha256"],
        "summary": report["metrics"],
        "status": report["status"],
        "synthetic": report["synthetic"],
        "final_snapshot": snapshot,
        "equity_curve": curve[-3000:],
        "drawdown_curve": drawdown[-3000:],
        "trades": report["trades"][:1000],
        "orders": orders[:1000],
        "fills": fills[:1000],
        "provenance": {
            **public["provenance"],
            "synthetic": report["synthetic"],
            "strategy_sha256": report["strategy_sha256"],
            "code_sha256": report["code_sha256"],
            "risk_policy_sha256": report["risk_policy_sha256"],
            "charges_version": report["charges_version"],
            "input_hashes": expected_inputs,
            "first_event": report["first_event"],
            "last_event": report["source_available_through"],
            "fee_schedule_matches_historical_dates": False,
        },
        "performance": unavailable_performance(
            "EVENT_TIME_NOT_DAILY_CUTS",
            "Event-time observations are not reviewed daily valuation cuts.",
        ),
        "truncation": {
            "curve": len(curve) > 3000,
            "orders": len(orders) > 1000,
            "fills": len(fills) > 1000,
            "trades": len(report["trades"]) > 1000,
        },
        "limitations": [
            *LIMITATIONS,
            *report["limitations"],
            "Observed equity/P&L and drawdown are event-time legacy measurements; "
            "they are not reviewed daily-cut investment performance. Stale observations have no "
            "drawdown value and do not update the fresh-observation high-water mark.",
        ],
        "artifact_sha256": manifest["sha256"]["report.json"],
    }
    if len(json.dumps(result).encode()) > 4 * 1024**2:
        raise ValueError("public report exceeds bounded response limit")
    return result
