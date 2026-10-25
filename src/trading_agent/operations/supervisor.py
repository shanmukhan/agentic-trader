"""Independent loopback supervisor. No order, confirmation, connection or mode endpoints."""

import json
import os
import sys
import threading
from datetime import datetime, time
from pathlib import Path
from typing import Any

from trading_agent.market_data.calendar import IST
from trading_agent.models import stamp
from trading_agent.operations.report import account_id
from trading_agent.operations.storage import durable_write as private_write
from trading_agent.persistence.locking import lock_exclusive
from trading_agent.risk.policy import policy_fingerprint
from trading_agent.settings import Settings

MAX_RESPONSE = 4_000_000


def request(settings: Settings, method: str, path: str, body: Any = None) -> dict[str, Any]:
    import httpx

    host = "[::1]" if settings.host == "::1" else "127.0.0.1"
    # No redirects, environment proxies or user-supplied hosts: never forward the bearer token.
    with (
        httpx.Client(timeout=20, follow_redirects=False, trust_env=False) as client,
        client.stream(
            method,
            f"http://{host}:{settings.port}{path}",
            headers={"Authorization": "Bearer " + settings.operator_token.get_secret_value()},
            json=body,
        ) as response,
    ):
        response.raise_for_status()
        data = bytearray()
        for chunk in response.iter_bytes():
            data.extend(chunk)
            if len(data) > MAX_RESPONSE:
                raise ValueError("operations response exceeds budget")
        value = json.loads(data)
        if not isinstance(value, dict):
            raise ValueError("invalid operations response")
        return value


def collect(settings: Settings, *, audit: bool = True) -> dict[str, Any]:
    result = request(settings, "GET", "/api/operations?audit=" + str(audit).lower())
    if (
        result.get("schema_version") != 1
        or result.get("account_id") != account_id(settings.database)
        or result.get("policy_sha256") != policy_fingerprint(settings)
    ):
        raise ValueError("operations service account mismatch")
    return result


def alerts(report: dict[str, Any]) -> list[str]:
    result = []
    account = report["account"]
    if account["faulted"] or account["kill"]:
        result.append("ACCOUNT_FAULT_OR_KILL")
    if report["session"]["open_now"]:
        if not account["feed_connected"]:
            result.append("FEED_DISCONNECTED")
        if report["unusable_quotes"]:
            result.append("UNUSABLE_QUOTES")
        if report["missing_basis_reviews"]:
            result.append("BASIS_REVIEW_REQUIRED")
        if any(c["id"] == "broker" and c["status"] != "PASS" for c in report["checks"]):
            result.append("BROKER_CHECK_REQUIRED")
    if report["protective_exits"] or report["pending_sells"]:
        result.append("UNRESOLVED_EXITS")
    if (
        report["horizon"] == "intraday"
        and account["positions"]
        and not report["session"]["open_now"]
    ):
        result.append("INTRADAY_RESIDUAL_EXPOSURE")
    if any(c["id"] == "ledger" and c["status"] == "BLOCKED" for c in report["checks"]):
        result.append("LEDGER_INVALID_OR_UNAVAILABLE")
    if report["decision_mode"] == "manual" and report["blockers"]:
        result.append("DECISIONS_PAUSED_OR_NOT_READY")
    if report["preparation"].get("state") in {"failed", "interrupted", "cancelled"}:
        result.append("PREPARATION_NEEDS_REVIEW")
    return sorted(set(result))


def write_report(report: dict[str, Any], output: Path) -> None:
    import hashlib

    from trading_agent.operations.backup import write_new

    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    markdown = (
        "# Daily paper operations report\n\n"
        f"Observed: {report['observed_at']}. Account: {report['account_id']}.\n\n"
        f"Trading authority: {report['trading_authorization']}. Report grants no authority.\n\n"
        "| Check | Status | Reason | Detail |\n|---|---|---|---|\n"
        + "".join(
            f"| {c['id']} | {c['status']} | {c['reason_code']} | {c['detail']} |\n"
            for c in report["checks"]
        )
        + f"\nCash: {report['account']['cash']}; fees: {report['account']['fees']}; "
        + f"pending orders: {report['pending_orders']}; "
        + f"held symbols: {len(report['account']['positions'])}.\n\n"
        + "Account and ledger audit can be separate snapshots; compare their journal sequences.\n\n"
        + "".join("- " + line + "\n" for line in report["limits"])
    )
    payloads = {
        "report.json": (json.dumps(report, indent=2, sort_keys=True) + "\n").encode(),
        "report.md": markdown.encode(),
    }
    for name, data in payloads.items():
        write_new(output / name, data)
    manifest = {
        "schema_version": 1,
        "state": "finished",
        "ready_for_live": False,
        "sha256": {name: hashlib.sha256(data).hexdigest() for name, data in payloads.items()},
    }
    write_new(output / "manifest.json", (json.dumps(manifest, sort_keys=True) + "\n").encode())


def supervise(
    settings: Settings,
    output: Path,
    clock: Any,
    *,
    interval: int = 10,
    download_universe: str | None = None,
    after: time = time(8, 30),
    once: bool = False,
    stop: threading.Event | None = None,
) -> dict[str, Any]:
    """Deduplicated transition alerts and durable acquisition intent. One owner per state folder."""

    if (
        not 5 <= interval <= 300
        or not settings.operator_token.get_secret_value()
        or after.tzinfo is not None
        or after.second
        or after.microsecond
    ):
        raise ValueError("supervisor needs an operator token and 5–300 second interval")
    if output.is_symlink():
        raise ValueError("unsafe supervisor directory")
    output.mkdir(parents=True, exist_ok=True, mode=0o700)
    if output.stat().st_mode & 0o077:
        raise ValueError("supervisor directory must be private")
    fd = os.open(output / "owner.lock", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        lock_exclusive(fd)
        state_path = output / "state.json"
        from trading_agent.desk.preparation import bounded

        state = json.loads(bounded(state_path, 10000)) if state_path.exists() else {}
        expected = account_id(settings.database)
        if state and state.get("account_id") != expected:
            raise ValueError("supervisor directory belongs to a different account")
        configuration = {"download_universe": download_universe, "after": after.isoformat()}
        # Explicit CLI options may enable/disable acquisition, but never clear a dated
        # attempt/unknown outcome. Server receipts bind the actual day's universe too.
        state.update(account_id=expected, schedule=configuration)
        stopped = stop or threading.Event()
        while True:
            now: datetime = clock()
            try:
                report = collect(settings, audit=False)
                age = (now - datetime.fromisoformat(report["observed_at"])).total_seconds()
                if not -2 <= age <= 30:
                    raise ValueError("stale service evidence or clock skew")
                current = alerts(report)
                local = now.astimezone(IST)
                # Full audits are separate from ten-second liveness polling. Store evidence
                # at most once per five minutes and publish a daily open/closed snapshot.
                if (
                    not state.get("audited_at")
                    or (now - datetime.fromisoformat(state["audited_at"])).total_seconds() >= 300
                ):
                    audited = collect(settings, audit=True)
                    current.extend(alerts(audited))
                    private_write(output / "audit.json", json.dumps(audited, sort_keys=True) + "\n")
                    state["audited_at"] = stamp(now)
                    state["audit_alerts"] = [
                        a for a in alerts(audited) if a == "LEDGER_INVALID_OR_UNAVAILABLE"
                    ]
                    session = report["session"]
                    if not session["reviewed"]:
                        phase = "no-session"
                    elif now < datetime.fromisoformat(session["open"]):
                        phase = "before-open"
                    elif now < datetime.fromisoformat(session["close"]):
                        phase = "open"
                    else:
                        phase = "after-close"
                    day_key = local.date().isoformat() + "-" + phase
                    if day_key not in state.get("daily_reports", []):
                        target = output / ("daily-" + day_key)
                        # Completion marker resolves an interruption after report publication.
                        if not (target / "manifest.json").exists():
                            write_report(audited, target)
                        state["daily_reports"] = [*state.get("daily_reports", [])[-31:], day_key]
                current.extend(state.get("audit_alerts", []))
                if (
                    download_universe
                    and local.time() >= after
                    and report["session"]["reviewed"]
                    and report["session"]["close"]
                    and now < datetime.fromisoformat(report["session"]["close"])
                ):
                    day = local.date().isoformat()
                    if state.get("download_date") != day:
                        # Persist before a possibly accepted/timed-out HTTP request.
                        state.update(download_date=day, download_state="outcome_unknown")
                        private_write(state_path, json.dumps(state) + "\n")
                        try:
                            outcome = request(
                                settings,
                                "POST",
                                "/api/operations/download",
                                {
                                    "session_date": day,
                                    "universe": download_universe,
                                    "acknowledged": True,
                                },
                            )
                            state["download_state"] = outcome["state"]
                            state["download_request_id"] = outcome.get("request_id")
                        except Exception:
                            current.append("SCHEDULED_DOWNLOAD_NEEDS_REVIEW")
                job = report.get("preparation", {})
                if (
                    state.get("download_request_id")
                    and job.get("request_id") == state["download_request_id"]
                ):
                    state["download_state"] = job["state"]
                if state.get("download_state") in {"outcome_unknown", "failed", "interrupted"}:
                    current.append("SCHEDULED_DOWNLOAD_NEEDS_REVIEW")
                private_write(output / "latest.json", json.dumps(report, sort_keys=True) + "\n")
            except Exception:
                current = ["SERVICE_UNAVAILABLE_OR_IDENTITY_INVALID"]
            current = sorted(set(current))
            if current != state.get("alerts"):
                event = {
                    "observed_at": stamp(now),
                    "account_id": expected,
                    "alerts": current,
                    "cleared": sorted(set(state.get("alerts", [])) - set(current)),
                }
                # One durable file per transition; no raw exception text, tokens or broker values.
                event_path = output / ("alert-" + now.strftime("%Y%m%dT%H%M%S%f") + ".json")
                if event_path.exists():
                    raise ValueError("alert timestamp already exists")
                private_write(event_path, json.dumps(event) + "\n")
                print(json.dumps(event), file=sys.stderr, flush=True)
            state.update(alerts=current, observed_at=stamp(now))
            private_write(state_path, json.dumps(state, sort_keys=True) + "\n")
            if once or stopped.wait(interval):
                return state
    finally:
        os.close(fd)
