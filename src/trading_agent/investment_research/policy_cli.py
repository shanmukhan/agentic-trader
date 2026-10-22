"""Bounded local policy/calendar inspection; no account, job or broker is opened."""

import hashlib
from datetime import date, datetime
from pathlib import Path
from typing import Any

from trading_agent.investment_research.policy import inspect_draft
from trading_agent.investment_research.policy_schedule import preview_schedule
from trading_agent.investment_research.policy_store import MAX_RECORD_BYTES, strict_json
from trading_agent.research_jobs.registry import read_bytes


def inspect_policy_file(
    draft: Path,
    calendar: Path | None = None,
    start: date | None = None,
    as_of: datetime | None = None,
) -> dict[str, Any]:
    if any(value is not None for value in (calendar, start, as_of)) and not all(
        value is not None for value in (calendar, start, as_of)
    ):
        raise ValueError("calendar preview requires --calendar, --start and --as-of together")
    original = read_bytes(draft, MAX_RECORD_BYTES)
    inspected = inspect_draft(strict_json(original))
    result: dict[str, Any] = {
        "schema_version": 1,
        "draft": inspected,
        "input_sha256": {"draft": hashlib.sha256(original).hexdigest()},
        "schedule": None,
        "account_changed": False,
        "execution_authorized": False,
    }
    if calendar is not None and start is not None and as_of is not None:
        content = read_bytes(calendar, 128 * 1024)
        result["input_sha256"]["calendar"] = hashlib.sha256(content).hexdigest()
        result["schedule"] = preview_schedule(
            inspected["parameters"], start, strict_json(content), as_of
        )
    return result
