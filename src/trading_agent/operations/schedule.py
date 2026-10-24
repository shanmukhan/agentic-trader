"""At most one scheduled acquisition attempt per IST day; never install or authorize."""

import json
from datetime import datetime
from typing import Any, Literal

from pydantic import Field, field_validator

from trading_agent.api.setup import SetupError
from trading_agent.desk.preparation import DownloadRequest, bounded
from trading_agent.market_data.calendar import IST
from trading_agent.models import DomainModel, stamp
from trading_agent.observability.preflight import _account
from trading_agent.operations.storage import durable_write as private_write


class ScheduledDownload(DomainModel):
    session_date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    universe: Literal["nifty100", "nifty500"]
    acknowledged: Literal[True]

    @field_validator("acknowledged", mode="before")
    @classmethod
    def explicit_acknowledgement(cls, value: Any) -> Any:
        if value is not True:
            raise ValueError("Explicit read-only acquisition acknowledgement required.")
        return value


def scheduled_download(prep: Any, body: ScheduledDownload, now: datetime) -> dict[str, Any]:
    """Persist intent before provider I/O. Unknown outcomes are reconciled, never replayed."""
    import secrets

    from trading_agent.operations.report import validate_download

    day = now.astimezone(IST).date().isoformat()
    if body.session_date != day:
        raise SetupError("Scheduled acquisition requires the current IST date.")
    e, setup = prep.desk.engine, prep.setup
    if setup is None:
        raise SetupError("Scheduled acquisition needs the manual broker setup service.")
    root = e.settings.database.with_suffix(".operations")
    with prep.lock, setup.lock:
        if root.is_symlink():
            raise SetupError("Refusing unsafe operations storage.")
        path = root / (day + ".json")
        if path.exists() or path.is_symlink():
            saved = json.loads(bounded(path, 10000))
            if saved["universe"] != body.universe:
                raise SetupError("This day's scheduled universe is already bound. Review manually.")
            job = prep.state or {}
            if job.get("request_id") == saved["request_id"]:
                saved = {**saved, "state": job["state"], "job_id": job.get("job_id")}
            elif saved["state"] == "claimed":
                saved["state"] = "outcome_unknown"
            return saved
        with e.lock:
            prep._manual(prep.desk.revision)
            revision = prep.desk.revision
            if prep.profile_override or prep.desk.installing:
                raise SetupError("Custom profile or active setup requires manual review.")
            bounds = e.calendar.bounds(now)
            if not bounds or now >= bounds[1]:
                raise SetupError(
                    "Scheduled acquisition requires today's saved session before close."
                )
            with e.db.transaction() as tx:
                selected = {
                    r["symbol"]
                    for r in tx.execute("SELECT symbol,token FROM instruments")
                    if r["token"] in prep.desk.execution_tokens
                }
                held = {r[0] for r in tx.execute("SELECT symbol FROM positions")}
                if (
                    not selected
                    or len(selected) != len(prep.desk.execution_tokens)
                    or not held <= selected
                ):
                    raise SetupError(
                        "Resolve catalog mappings and held-symbol subscriptions first."
                    )
                if (
                    e.faulted
                    or e.db.get(tx, "kill") == "true"
                    or tx.execute(
                        "SELECT 1 FROM orders WHERE state IN ('ACCEPTED','PARTIAL') LIMIT 1"
                    ).fetchone()
                ):
                    raise SetupError(
                        "Resolve account faults/kill/pending orders before scheduled preparation."
                    )
        # Reuse a valid run instead of issuing provider calls on a repeated scheduler invocation.
        try:
            valid = validate_download(prep, now)
        except Exception:
            valid = {}
        if (
            valid
            and valid["same_ist_date"]
            and valid["coverage_valid"]
            and (prep.state or {}).get("universe") == body.universe
        ):
            return {"state": "reused", "session_date": day, "job_id": prep.state["job_id"]}
        if prep.thread and prep.thread.is_alive():
            raise SetupError("Another download is already active. Inspect it before scheduling.")
        ledger = _account(e.settings)
        if not all(
            ledger[k]
            for k in (
                "horizon_matches",
                "risk_policy_matches",
                "charges_match",
                "initial_cash_matches",
            )
        ):
            raise SetupError("Scheduled preflight account identity failed.")
        setup.check_profile()  # Read-only probe; no login, refresh, exchange or retry loop.
        request_id = secrets.token_hex(16)
        saved = {
            "state": "claimed",
            "session_date": day,
            "universe": body.universe,
            "request_id": request_id,
            "observed_at": stamp(now),
        }
        private_write(path, json.dumps(saved) + "\n")
        try:
            result = prep.start(
                DownloadRequest(
                    universe=body.universe,
                    request_id=request_id,
                    revision=revision,
                    acknowledged=True,
                )
            )
            saved.update(state=result["job"]["state"], job_id=result["job"]["job_id"])
            private_write(path, json.dumps(saved) + "\n")
        except Exception:
            # The durable claim remains. An error may follow provider/thread creation.
            raise SetupError(
                "Scheduled acquisition outcome needs inspection; no automatic retry."
            ) from None
        return saved
