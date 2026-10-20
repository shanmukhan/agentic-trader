"""Source-preserving operational evidence; never startup recovery or live approval."""

import json
from collections import Counter
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from trading_agent.backtesting.report import journal_digest, ledger_results
from trading_agent.market_data.calendar import IST
from trading_agent.persistence.database import Database


def paper_report(db: Database, output: Path) -> dict[str, Any]:
    with db.transaction() as tx:
        db.reconcile(tx)
        if tx.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("account integrity failure")
        rows = tx.execute(
            "SELECT time,kind,entity,payload FROM events WHERE kind IN "
            "('automation_start','automation_stop','automation_state','feed_connection',"
            "'history_failure','automation_fault','paper_telemetry','automation_candidate','quote',"
            "'data_quality','kill_switch') ORDER BY seq"
        )
        starts: list[dict[str, Any]] = []
        telemetry: list[dict[str, Any]] = []
        failures: Counter[str] = Counter()
        quote_sources: Counter[str] = Counter()
        days, active_run, armed_days = set(), -1, set()
        stopped_runs: set[int] = set()
        duplicate_stops = 0
        counts: Counter[str] = Counter()
        for row in rows:
            kind, payload = row["kind"], json.loads(row["payload"])
            counts[kind] += 1
            if kind == "automation_start":
                starts.append(payload)
                active_run += 1
            elif kind == "paper_telemetry":
                telemetry.append({"run": active_run, "time": row["time"], **payload})
            elif kind == "automation_stop":
                if active_run in stopped_runs or active_run < 0:
                    duplicate_stops += 1
                stopped_runs.add(active_run)
            elif kind == "quote":
                quote_sources[payload["source"]] += 1
                days.add(
                    datetime.fromisoformat(payload["exchange_time"])
                    .astimezone(IST)
                    .date()
                    .isoformat()
                )
            elif kind == "automation_state":
                if payload["armed"]:
                    armed_days.add(
                        datetime.fromisoformat(row["time"]).astimezone(IST).date().isoformat()
                    )
                elif payload["reason"] not in {
                    "STARTUP",
                    "SHUTDOWN",
                    "OPERATOR_DISARM",
                    "ENTRY_WINDOW_ENDED",
                    "SESSION_CHANGED",
                }:
                    failures[payload["reason"]] += 1
            elif kind in {"automation_fault", "data_quality", "history_failure"}:
                failures[kind] += 1
        if not starts:
            raise ValueError("no supervised paper automation evidence in this account")
        positions = [dict(row) for row in tx.execute("SELECT * FROM positions ORDER BY symbol")]
        cash = db.get(tx, "cash")
        realized, fees = db.get(tx, "total_realized"), db.get(tx, "fees")
        automation_hash = db.get(tx, "automation_hash")
        policy_hash = db.get(tx, "policy_hash")
    trades, metrics = ledger_results(db)
    windows = [
        {"time": item["time"], "run": item["run"], "timings": item["timings"]} for item in telemetry
    ]
    budgets = [start["feed_policy"]["processing_budget_ms"] for start in starts]
    local_stages = {"feed_callback", "quote_processing", "candle_processing"}
    timed = [
        timing
        for item in telemetry
        for name, timing in item["timings"].items()
        if name in local_stages
    ]
    sufficient = any(
        item["timings"].get("quote_processing", {}).get("total_count", 0) >= 100
        for item in telemetry
    )
    latest_by_run = {}
    for item in telemetry:
        latest_by_run[item["run"]] = item
    final_snapshots = [item["snapshot"] for item in latest_by_run.values()]
    max_drawdown = max(
        (Decimal(item["performance"]["drawdown"]) for item in telemetry), default=Decimal(0)
    )
    gates = {
        "non_synthetic": all(not start["synthetic"] for start in starts)
        and set(quote_sources) == {"kite"},
        "minimum_armed_sessions": len(armed_days)
        >= starts[-1]["feed_policy"]["evidence_min_sessions"],
        "minimum_completed_trades": len(trades) >= starts[-1]["feed_policy"]["evidence_min_trades"],
        "flat": not positions and metrics["pending_orders"] == 0,
        "clean_shutdowns": len(stopped_runs) == len(starts) and duplicate_stops == 0,
        "no_recorded_incidents": not failures,
        "no_stale_observed_valuations": all(
            item["performance"]["stale_valuations"] == 0 for item in telemetry
        ),
        "latency_evidence": sufficient
        and bool(timed)
        and all(
            item["p99_ms"] <= min(budgets)
            and item["over_budget_count"] / item["total_count"] <= 0.01
            for item in timed
        ),
        "model_bound": all(start["model_sha256"] is not None for start in starts),
        "net_realized_positive": Decimal(realized) > 0,
    }
    report: dict[str, Any] = {
        "schema_version": 1,
        "mode": "paper",
        "ready_for_live": False,
        "external_acceptance_verified": False,
        "preliminary_gates_passed": all(gates.values()),
        "automation_sha256": automation_hash,
        "risk_policy_sha256": policy_hash,
        "runs": starts,
        "event_counts": dict(counts),
        "incident_counts": dict(failures),
        "quote_sources": dict(quote_sources),
        "observed_quote_sessions": sorted(days),
        "armed_sessions": sorted(armed_days),
        "gates": gates,
        "metrics": metrics,
        "cash": cash,
        "realized_pnl": realized,
        "fees": fees,
        "open_positions": positions,
        "max_observed_run_drawdown": str(max_drawdown),
        "last_run_snapshots": final_snapshots,
        "latency_windows": windows,
        "journal_sha256": journal_digest(db),
        "limitations": [
            "Virtual fills and current fee assumptions require empirical calibration.",
            "Latency percentiles cover recent windows of at most 512 observations per stage, "
            "not global quantiles.",
            "Telemetry before a crash may be missing; drawdown is observed per process run, "
            "not a complete cross-restart equity path.",
            "Observed/armed dates do not prove full-session coverage. Real broker, device "
            "and recovery acceptance need separate review.",
        ],
    }
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    (output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True, default=str) + "\n"
    )
    (output / "trades.jsonl").write_text(
        "".join(json.dumps(trade, sort_keys=True, default=str) + "\n" for trade in trades)
    )
    (output / "report.md").write_text(
        "# Supervised paper operations report\n\n"
        "PAPER ONLY. External acceptance and live readiness: false.\n\n"
        f"Virtual cash: {cash}; realized P&L: {realized}; fees: {fees}.\n\n"
        "| Preliminary gate | Passed |\n|---|---|\n"
        + "".join(f"| {key} | {value} |\n" for key, value in gates.items())
        + "\n## Measurement limits\n\n"
        + "".join(f"- {line}\n" for line in report["limitations"])
        + "\nInspect report.json for incidents, retained latency windows, "
        "configuration and journal identities.\n"
    )
    if journal_digest(db) != report["journal_sha256"]:
        raise RuntimeError("source journal changed during reporting")
    (output / "run.json").write_text('{"state":"finished","ready_for_live":false}\n')
    return report
