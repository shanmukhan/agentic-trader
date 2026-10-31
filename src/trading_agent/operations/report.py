"""Read-only daily evidence. Never tick the desk, expire proposals, or recover orders."""

import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from trading_agent import __version__
from trading_agent.desk.preparation import bounded
from trading_agent.execution.quote_status import quote_status
from trading_agent.market_data.calendar import IST
from trading_agent.models import stamp, utc
from trading_agent.observability.preflight import _account
from trading_agent.risk.policy import policy_fingerprint


def account_id(database: Path) -> str:
    return hashlib.sha256(str(database.resolve()).encode()).hexdigest()


def validate_download(preparation: Any, now: datetime) -> dict[str, Any]:
    """Validate each freshness invariant separately, including actual per-symbol coverage."""
    job = preparation.state or {}
    if job.get("state") not in {"ready_for_review", "installed"}:
        raise ValueError("download not ready")
    from trading_agent.desk.contracts import digest

    root = preparation.root
    directory = root / job["job_id"]
    if root.is_symlink() or directory.is_symlink():
        raise ValueError("unsafe source directory")
    draft = json.loads(bounded(directory / "draft.json", 50_000_000))
    if digest(draft) != job["preview_sha256"]:
        raise ValueError("draft changed")
    names = {"constituents.csv", "holidays.json", "actions.json"}
    if set(draft["source_hashes"]) != names:
        raise ValueError("missing official sources")
    for name, expected in draft["source_hashes"].items():
        raw = bounded(directory / name, 5_000_000).encode()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError("source changed")
    days = [
        s["day"]
        for s in draft["sessions"]
        if datetime.combine(
            datetime.fromisoformat(s["day"]).date(),
            datetime.strptime(s["close"], "%H:%M:%S").time(),
            IST,
        )
        <= now
    ]
    expected_days = set(days[-60:])
    coverage: dict[str, set[str]] = {}
    for row in draft["records"]:
        if datetime.fromisoformat(row["price_available_at"]) > now:
            raise ValueError("future price evidence")
        observed = coverage.setdefault(row["symbol"], set())
        if row["session"] in observed:
            raise ValueError("duplicate daily candle")
        observed.add(row["session"])
    if not expected_days or set(coverage) != {s["symbol"] for s in draft["eligible"]}:
        raise ValueError("incomplete universe")
    if datetime.fromisoformat(job["snapshot_at"]) > now:
        raise ValueError("future source evidence")
    return {
        "hashes_valid": True,
        "same_ist_date": datetime.fromisoformat(job["snapshot_at"]).astimezone(IST).date()
        == now.astimezone(IST).date(),
        "coverage_valid": bool(coverage) and all(d == expected_days for d in coverage.values()),
        "latest_completed_session": max(expected_days),
        "history_end": job["history_end"],
        "snapshot_at": job["snapshot_at"],
        "eligible_symbols": len(coverage),
        "excluded_symbols": len(job["excluded"]),
    }


def operations_report(
    desk: Any, setup: Any, preparation: Any, guided: Any, now: datetime, *, audit: bool = False
) -> dict[str, Any]:
    now = utc(now)
    e = desk.engine
    checks: list[dict[str, Any]] = []

    def add(key: str, state: str, code: str, detail: str) -> None:
        checks.append(
            dict(id=key, status=state, reason_code=code, detail=detail, observed_at=stamp(now))
        )

    # Follow the same lock order as guided setup; never acquire setup/preparation under engine.
    with preparation.lock, setup.lock if setup else preparation.lock, e.lock:
        job = dict(preparation.state or {})
        with e.db.transaction() as tx:
            account = e._snapshot(tx, now)
            execution_tokens = frozenset(desk.execution_tokens)
            selected = [
                dict(r)
                for r in tx.execute("SELECT symbol,token FROM instruments ORDER BY symbol")
                if r["token"] in execution_tokens
            ]
            held = {p["symbol"] for p in account["positions"]}
            selected_symbols = {s["symbol"] for s in selected}
            # Always include holdings, even if an externally changed selection omitted them.
            quotes = [quote_status(e, tx, s, now) for s in sorted(held | selected_symbols)]
            for q in quotes:
                quote = e._quote(tx, q["symbol"])
                q["held"] = q["symbol"] in held
                q["bid_size"] = quote.bid_size if quote else None
                q["ask_size"] = quote.ask_size if quote else None
            orders = [
                dict(r) for r in tx.execute("SELECT * FROM orders ORDER BY rowid DESC LIMIT 201")
            ]
            pending_count = tx.execute(
                "SELECT COUNT(*) FROM orders WHERE state IN ('ACCEPTED','PARTIAL')"
            ).fetchone()[0]
            exits = [
                {"symbol": p["symbol"], "quantity": p["quantity"], "reason": r[0]}
                for p in account["positions"]
                if (
                    r := tx.execute(
                        "SELECT value FROM meta WHERE key=?",
                        (f"lt_exit:{p['symbol']}:{p['opened']}",),
                    ).fetchone()
                )
            ]
            # Intraday pending protective sells have no long-term exit latch.
            sells = [
                dict(r)
                for r in tx.execute(
                    "SELECT id,symbol,quantity,filled,reason FROM orders "
                    "WHERE side='SELL' AND state IN ('ACCEPTED','PARTIAL')"
                )
            ]
            awaiting = tx.execute(
                "SELECT COUNT(*) FROM desk_decisions WHERE state='awaiting_approval'"
            ).fetchone()[0]
            sequence = tx.execute("SELECT COALESCE(MAX(seq),0) FROM events").fetchone()[0]
        blockers = desk.blockers(now)
        bounds = e.calendar.bounds(now)
        session = {
            "date": now.astimezone(IST).date().isoformat(),
            "reviewed": bounds is not None,
            "open_now": e.calendar.is_open(now),
            "open": stamp(bounds[0]) if bounds else None,
            "close": stamp(bounds[1]) if bounds else None,
        }
        broker_checked = getattr(setup, "verified_at", None)
        broker_ok = bool(
            setup
            and setup.verified
            and broker_checked
            and broker_checked.astimezone(IST).date() == now.astimezone(IST).date()
            and broker_checked <= now
        )
        add(
            "service",
            "PASS",
            "SERVICE_RESPONDING",
            "Account owner responded; this is a point-in-time observation.",
        )
        add(
            "risk",
            "BLOCKED" if e.faulted or account["kill"] else "PASS",
            "ACCOUNT_FAULT_OR_KILL" if e.faulted or account["kill"] else "NO_ACCOUNT_FAULT",
            "Inspect risk faults and kill reason; a report never resets them.",
        )
        add(
            "session",
            "PASS" if bounds else "NEEDS REVIEW",
            "SESSION_REVIEWED" if bounds else "SESSION_UNKNOWN",
            "Use the saved reviewed calendar; special notices still require operator review.",
        )
        add(
            "broker",
            "PASS" if broker_ok else "NEEDS REVIEW",
            "BROKER_CHECKED_TODAY" if broker_ok else "BROKER_CHECK_REQUIRED",
            "A dated profile check does not prove data entitlement or continuing validity.",
        )
        add(
            "catalog",
            "PASS"
            if selected and len(selected) == len(desk.execution_tokens) and held <= selected_symbols
            else "BLOCKED",
            "CATALOG_AND_HELD_COVERAGE"
            if selected and held <= selected_symbols
            else "CATALOG_OR_HELD_COVERAGE_MISSING",
            "Every selected token must resolve, and every holding must remain subscribed.",
        )
        basis = [q["symbol"] for q in quotes if q["basis_reviewed"] is False]
        add(
            "basis",
            "NEEDS REVIEW" if basis else "PASS",
            "BASIS_REVIEW_REQUIRED" if basis else "BASIS_CHECKED",
            "Current-day basis reviews remain explicit; automation never clears quarantine.",
        )
        unusable = [q["symbol"] for q in quotes if not q["usable"]]
        add(
            "quotes",
            "PASS" if quotes and not unusable else "BLOCKED",
            "ALL_QUOTES_USABLE" if quotes and not unusable else "UNUSABLE_QUOTES",
            "All selected and held symbols need usable quotes; closed-market blocking is expected.",
        )
        add(
            "pending_orders",
            "NEEDS REVIEW" if pending_count else "PASS",
            "PENDING_ORDERS" if pending_count else "NO_PENDING_ORDERS",
            "Pending or partially filled orders remain obligations, never assumed fills.",
        )
        add(
            "protective_exits",
            "NEEDS REVIEW" if exits or sells else "PASS",
            "UNRESOLVED_EXITS" if exits or sells else "NO_REQUESTED_EXIT_RESIDUE",
            "Requested exits require later usable quotes and actual fills.",
        )
        add(
            "policy",
            "PASS" if desk.research else "NEEDS REVIEW",
            "INSTALLED_POLICY" if desk.research else "POLICY_REVIEW_REQUIRED",
            "Installation, source/basis review and mode activation require separate authorization.",
        )
        sources: dict[str, Any] | None = None
        if audit:
            try:
                sources = validate_download(preparation, now)
                valid = all(sources[k] for k in ("hashes_valid", "same_ist_date", "coverage_valid"))
                add(
                    "strategy_data",
                    "PASS" if valid else "BLOCKED",
                    "CURRENT_SOURCE_COVERAGE" if valid else "SOURCE_DATE_OR_COVERAGE_STALE",
                    "Checked source hashes, current IST date and each eligible symbol's sessions.",
                )
            except Exception:
                add(
                    "strategy_data",
                    "BLOCKED",
                    "SOURCE_INVALID_OR_UNAVAILABLE",
                    "Download current sources; missing, changed or invalid evidence is blocked.",
                )
        else:
            add(
                "strategy_data",
                "NEEDS REVIEW",
                "SOURCE_AUDIT_NOT_RUN",
                "Run daily-report for source hashes and full coverage validation.",
            )
        guided_state = guided.view() if guided else None
        result = {
            "schema_version": 1,
            "version": __version__,
            "observed_at": stamp(now),
            "account_id": account_id(e.settings.database),
            "policy_sha256": policy_fingerprint(e.settings),
            "horizon": e.settings.investment_horizon,
            "session": session,
            "account": account,
            "decision_mode": desk.mode,
            "revision": desk.revision,
            "blockers": blockers,
            "trading_authorization": "AUTHORIZED"
            if desk.mode != "manual" and not blockers
            else "NOT AUTHORIZED",
            "checks": checks,
            "quotes": quotes,
            "selected_symbols": sorted(selected_symbols),
            "missing_basis_reviews": basis,
            "unusable_quotes": unusable,
            "orders": [
                {**r, "remaining_quantity": r["quantity"] - r["filled"]} for r in orders[:200]
            ],
            "orders_truncated": len(orders) > 200,
            "pending_orders": pending_count,
            "protective_exits": exits,
            "pending_sells": sells,
            "awaiting_approval": awaiting,
            "journal_sequence": sequence,
            "broker_checked_at": stamp(broker_checked) if broker_checked else None,
            "preparation": job,
            "source_validation": sources,
            "guided_setup": guided_state,
            "ready_for_live": False,
            "external_acceptance_verified": False,
            "limits": [
                "A report is not permission to trade or proof of executable protection.",
                "No proposal expiry, recovery, setup confirmation or mode change is run.",
                "Clock synchronization, notices and data entitlement require external evidence.",
                "No external notification service is configured; supervisor alerts are local.",
            ],
        }
    # Do not hold the quote/risk lock during full SQLite verification.
    if audit:
        try:
            ledger = _account(e.settings)
            valid = all(
                ledger[k]
                for k in (
                    "initial_cash_matches",
                    "risk_policy_matches",
                    "charges_match",
                    "horizon_matches",
                )
            )
            result["ledger_audit"] = ledger
            add(
                "ledger",
                "PASS" if valid else "BLOCKED",
                "LEDGER_RECONCILED" if valid else "ACCOUNT_IDENTITY_MISMATCH",
                "A separate read-only ledger snapshot verified exact accounting and authorization.",
            )
        except Exception:
            add(
                "ledger",
                "BLOCKED",
                "LEDGER_INVALID_OR_UNAVAILABLE",
                "Accounting/integrity verification failed or is unavailable; preserve evidence.",
            )
    else:
        add(
            "ledger",
            "NEEDS REVIEW",
            "LEDGER_AUDIT_NOT_RUN",
            "Run daily-report for full read-only ledger verification.",
        )
    return result
