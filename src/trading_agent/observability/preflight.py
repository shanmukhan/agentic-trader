"""Local acceptance diagnostics with a bounded, read-only SQLite snapshot.

Never construct Database/PaperBroker, acquire account ownership, recover orders,
contact Kite, load executable artifacts, or claim external/live acceptance.
"""

import hashlib
import json
import os
import platform
import shutil
import sqlite3
import stat
import sys
import time
from contextlib import closing
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from trading_agent.execution.costs import Charges
from trading_agent.market_data.calendar import SessionCalendar
from trading_agent.models import stamp, utc
from trading_agent.persistence.database import Database
from trading_agent.risk.policy import policy_fingerprint
from trading_agent.settings import Settings

MIN_FREE_BYTES = 1024**3
DATABASE_BUDGET_SECONDS = 5


def sqlite_wal_fix_present(version: tuple[int, ...]) -> bool:
    """Official WAL-reset fixes, including the two documented backport branches."""
    return version >= (3, 51, 3) or (
        version[:2] in ((3, 44), (3, 50))
        and version >= ((3, 44, 6) if version[:2] == (3, 44) else (3, 50, 7))
    )


def _account(settings: Settings) -> dict[str, Any]:
    # as_uri escapes '?'/'#' so a filesystem name cannot inject SQLite parameters.
    uri = settings.database.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True, timeout=1, isolation_level=None)) as tx:
        tx.row_factory = sqlite3.Row
        tx.execute("PRAGMA query_only=ON")
        tx.execute("PRAGMA trusted_schema=OFF")
        deadline = time.monotonic() + DATABASE_BUDGET_SECONDS
        tx.set_progress_handler(lambda: int(time.monotonic() >= deadline), 1000)
        tx.execute("BEGIN")
        schema = tx.execute("PRAGMA user_version").fetchone()[0]
        if schema != 1:
            raise ValueError("unsupported database schema")
        if tx.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise ValueError("database integrity failure")
        Database.reconcile(tx)  # SELECT-only accounting verifier; no initialization/recovery.
        meta = {row[0]: row[1] for row in tx.execute("SELECT key,value FROM meta")}
        model_metadata = meta.get("model_gate_schema") == "1" and bool(meta.get("model_version"))
        auto_events = bool(
            tx.execute("SELECT 1 FROM events WHERE kind='automation_start' LIMIT 1").fetchone()
        )
        result = {
            "schema_version": schema,
            "journal_sequence": tx.execute("SELECT COALESCE(MAX(seq),0) FROM events").fetchone()[0],
            "cash": meta["cash"],
            "fees": meta["fees"],
            "pending_orders": tx.execute(
                "SELECT COUNT(*) FROM orders WHERE state IN ('ACCEPTED','PARTIAL')"
            ).fetchone()[0],
            "positions": tx.execute("SELECT COUNT(*) FROM positions").fetchone()[0],
            "initial_cash_matches": Decimal(meta["initial_cash"]) == settings.starting_cash,
            "risk_policy_matches": meta.get("policy_hash") == policy_fingerprint(settings),
            "charges_match": meta.get("charges_version") == Charges().version,
            "model_metadata_valid": model_metadata,
            "automation_metadata_valid": bool(meta.get("automation_hash")) == auto_events,
            "automation_bound": bool(meta.get("automation_hash")),
            "model_bound": meta.get("model_version") not in (None, "none"),
            "catalog_tokens": [row[0] for row in tx.execute("SELECT token FROM instruments")],
        }
        if time.monotonic() >= deadline:
            raise TimeoutError("account read exceeded query budget")
        return result


def preflight(settings: Settings, now: datetime) -> dict[str, Any]:
    now = utc(now)
    checks: list[dict[str, Any]] = []

    def add(key: str, passed: bool | None, detail: str, *, required: bool = True) -> None:
        checks.append(
            {
                "id": key,
                "state": "unverified" if passed is None else "passed" if passed else "blocked",
                "required": required,
                "detail": detail,
            }
        )

    add("python", sys.version_info[:2] == (3, 13), "Supported runtime: Python 3.13.x.")
    add(
        "sqlite_wal_fix",
        sqlite_wal_fix_present(sqlite3.sqlite_version_info),
        "Require SQLite 3.51.3+, or documented 3.50.7/3.44.6 branch fixes; "
        "unidentified vendor backports need separate review.",
    )
    add(
        "operator_token",
        bool(settings.operator_token.get_secret_value()),
        "A configured operator token is required for private account access.",
    )
    add(
        "paper_loopback",
        settings.mode == "paper" and settings.host in {"127.0.0.1", "::1"},
        "Paper mode and loopback-only listener.",
    )
    calendar_open = False
    try:
        calendar = SessionCalendar.load(settings.calendar)
        add("calendar_file", True, "Reviewed calendar parsed; unknown dates remain closed.")
        add(
            "session_today",
            bool(calendar.bounds(now)),
            "A reviewed IST session for today is required for entries.",
            required=False,
        )
        calendar_open = calendar.is_open(now)
    except (OSError, ValueError, KeyError):
        add("calendar_file", False, "Calendar could not be loaded or validated.")
    disk_free = None
    try:
        parent = settings.database.absolute().parent
        while not parent.exists():
            parent = parent.parent
        disk_free = shutil.disk_usage(parent).free
        add(
            "disk_headroom",
            disk_free >= MIN_FREE_BYTES,
            "At least 1 GiB free on the account volume; this is a floor, not retention sizing.",
        )
    except OSError:
        add("disk_headroom", False, "Account volume capacity could not be inspected.")
    account = None
    try:
        exists = settings.database.is_file() and not settings.database.is_symlink()
        add(
            "account_exists",
            exists,
            "An existing regular account file is required; never create it here.",
        )
        if exists:
            private = not stat.S_IMODE(settings.database.stat().st_mode) & 0o077
            parent_private = not stat.S_IMODE(settings.database.parent.stat().st_mode) & 0o077
            add(
                "private_storage",
                private and parent_private,
                "Account file and immediate parent must deny group/other permissions.",
            )
            account = _account(settings)
            add(
                "account_integrity",
                True,
                "SQLite integrity and exact ledger accounting reconciled.",
            )
            for key in (
                "initial_cash_matches",
                "risk_policy_matches",
                "charges_match",
                "model_metadata_valid",
                "automation_metadata_valid",
            ):
                add(
                    key,
                    account[key],
                    "Stored identity must match the configured policy and supported markers.",
                )
            tokens = settings.stream_tokens
            add(
                "stream_catalog",
                bool(tokens)
                and len(set(tokens)) == len(tokens)
                and set(tokens) <= set(account.pop("catalog_tokens")),
                "Supervised feed needs distinct reviewed tokens present in this account's catalog.",
                required=account["automation_bound"],
            )
            add(
                "flat_account",
                not account["pending_orders"] and not account["positions"],
                "Review pending orders/holdings before recovery; both remain intact.",
                required=False,
            )
    except (OSError, sqlite3.Error, ValueError, RuntimeError, KeyError, ArithmeticError):
        # Never include raw errors: local corrupt values/paths can contain secrets.
        add(
            "account_integrity",
            False,
            "Account unreadable, unsupported, inconsistent, busy or over the query budget.",
        )
    for key, detail in (
        (
            "broker_entitlement",
            "Manual Kite login/profile, history entitlement and full quotes need evidence.",
        ),
        (
            "target_device_recovery",
            "Target-device boot, storage, power-loss and recovery drills remain operator-run.",
        ),
        (
            "fill_cost_calibration",
            "Real matching quotes/depth and costs must calibrate virtual fills.",
        ),
        (
            "sustained_paper_acceptance",
            "Review sustained feed coverage, model/research evidence and paper-report results.",
        ),
    ):
        add(key, None, detail, required=False)
    return {
        "schema_version": 1,
        "observed_at": stamp(now),
        "mode": "paper",
        "ready_for_live": False,
        "external_acceptance_verified": False,
        "local_checks_passed": all(c["state"] == "passed" for c in checks if c["required"]),
        "calendar_open_now": calendar_open,
        "runtime": {
            "python": platform.python_version(),
            "sqlite": sqlite3.sqlite_version,
            "system": platform.system(),
            "architecture": platform.machine(),
        },
        "disk_free_bytes": disk_free,
        "risk_policy_sha256": policy_fingerprint(settings),
        "account": account,
        "checks": checks,
        "limitations": [
            "A point-in-time local diagnostic is not permission to arm or trade.",
            "No broker request, expiry probe, model validation or feed freshness check is run.",
            "Startup still verifies strategy/feed/model/calendar identity. No recovery runs here.",
            "SQLite uses normal WAL locking/shared memory. No immutable/nolock modes are used.",
            "Reads consume I/O and can delay WAL recycling; run outside busy entry periods.",
        ],
    }


def write_preflight(report: dict[str, Any], output: Path) -> None:
    """Exclusive private artifacts; manifest is the last completion marker."""
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    payload = (json.dumps(report, indent=2, sort_keys=True) + "\n").encode()
    markdown = (
        "# Local paper preflight\n\n"
        "PAPER ONLY. External acceptance and live readiness: false.\n\n"
        f"Observed at: {report['observed_at']}. "
        f"Local checks passed: {report['local_checks_passed']}.\n\n"
        "| Check | State | Required locally | Detail |\n|---|---|---|---|\n"
        + "".join(
            f"| {c['id']} | {c['state']} | {c['required']} | {c['detail']} |\n"
            for c in report["checks"]
        )
        + "\n## Limits\n\n"
        + "".join(f"- {line}\n" for line in report["limitations"])
    ).encode()
    artifacts = {"report.json": payload, "report.md": markdown}
    manifest = {
        "schema_version": 1,
        "state": "finished",
        "ready_for_live": False,
        "sha256": {name: hashlib.sha256(data).hexdigest() for name, data in artifacts.items()},
    }
    artifacts["manifest.json"] = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    for name, data in artifacts.items():
        fd = os.open(output / name, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "wb") as file:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
