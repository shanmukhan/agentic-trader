"""Preview policy review dates from an explicit, unverified calendar declaration.

This module does not infer exchange sessions, place orders, activate a policy or
certify a calendar. The caller validates the remaining draft policy fields; only
the five fields needed for a date preview are read here. Dates describe planned
reviews, never execution times or a claim that a future session will occur.
"""

from bisect import bisect_left, bisect_right
from calendar import monthrange
from datetime import date, datetime, timedelta
from typing import Any

METHOD = "reviewed-calendar-policy-schedule-v1"
MAX_CYCLES = 400
MAX_SESSIONS = 5000
_FIELDS = (
    "horizon_count",
    "horizon_unit",
    "review_cadence",
    "review_session_rule",
    "missed_cycle_policy",
)
_CALENDAR_FIELDS = {"coverage_start", "coverage_end", "sessions", "known_at", "reference"}


def _day(value: object, label: str) -> date:
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError(f"{label} must be a canonical YYYY-MM-DD date")
    try:
        result = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"{label} must be a canonical YYYY-MM-DD date") from exc
    if result.isoformat() != value:
        raise ValueError(f"{label} must be a canonical YYYY-MM-DD date")
    return result


def _calendar(calendar: dict[str, Any]) -> tuple[date, date, list[date], datetime]:
    if not isinstance(calendar, dict) or set(calendar) != _CALENDAR_FIELDS:
        raise ValueError(
            "calendar requires only coverage_start/end, sessions, known_at and reference"
        )
    first = _day(calendar["coverage_start"], "coverage_start")
    last = _day(calendar["coverage_end"], "coverage_end")
    if first > last:
        raise ValueError("calendar coverage_start cannot follow coverage_end")
    sessions = calendar["sessions"]
    if not isinstance(sessions, list) or len(sessions) > MAX_SESSIONS:
        raise ValueError("calendar sessions must be a list of at most 5000 declared session dates")
    days = [_day(value, "session") for value in sessions]
    if days != sorted(set(days)):
        raise ValueError("calendar sessions must be unique and strictly chronological")
    if any(day < first or day > last for day in days):
        raise ValueError("every declared session must be inside the inclusive coverage bounds")
    reference = calendar["reference"]
    if not isinstance(reference, str) or not reference.strip() or len(reference) > 500:
        raise ValueError("calendar reference must be a nonblank string of at most 500 characters")
    raw_known = calendar["known_at"]
    if not isinstance(raw_known, str) or len(raw_known) > 64 or "T" not in raw_known:
        raise ValueError("calendar known_at must be an offset-aware ISO timestamp")
    try:
        known_at = datetime.fromisoformat(raw_known)
    except ValueError as exc:
        raise ValueError("calendar known_at must be an offset-aware ISO timestamp") from exc
    if known_at.utcoffset() is None:
        raise ValueError("calendar known_at must be an offset-aware ISO timestamp")
    return first, last, days, known_at


def _month_index(day: date) -> int:
    return (day.year - 1) * 12 + day.month - 1


def _period_bounds(index: int, months: int) -> tuple[date, date]:
    year_index, month_index = divmod(index * months, 12)
    year, first_month = year_index + 1, month_index + 1
    last_month = first_month + months - 1
    return date(year, first_month, 1), date(year, last_month, monthrange(year, last_month)[1])


def preview_schedule(
    parameters: dict[str, Any], start: date, calendar: dict[str, Any], as_of: datetime
) -> dict[str, Any]:
    """Resolve months/years and monthly/quarterly reviews without execution effects.

    All five date parameters are required; missing or null values stay unresolved.
    Additional parameters belong to the caller's separately validated draft and
    are not interpreted here. ``start`` is inclusive and the calendar anniversary
    ``horizon_end`` exclusive. The anniversary uses the original start day,
    clamped only in its target month (for example 31 January + 2 months is 31 March).

    The calendar declares *continuous, complete* session coverage between its
    inclusive bounds. This operator assertion is labelled unverified, not checked
    against a provider. An entire calendar month/quarter must be covered to choose
    its first/last reviewed session, even when the investment horizon cuts through
    that period. Candidate reviews before start or at/after end are skipped; no
    catch-up date is invented. An explicitly covered empty period has no session.
    """
    if not isinstance(parameters, dict):
        raise ValueError("parameters must be an object")
    if type(start) is not date:
        raise ValueError("start must be a date, without a time component")
    if not isinstance(as_of, datetime) or as_of.utcoffset() is None:
        raise ValueError("as_of must be an offset-aware datetime")
    coverage_start, coverage_end, days, known_at = _calendar(calendar)
    selected = {field: parameters.get(field) for field in _FIELDS}
    missing = [field for field, value in selected.items() if value is None]
    count = selected["horizon_count"]
    if count is not None and (type(count) is not int or count < 1):
        raise ValueError("horizon_count must be a positive integer")
    enums = {
        "horizon_unit": {"months", "years"},
        "review_cadence": {"monthly", "quarterly"},
        "review_session_rule": {"first_reviewed_session", "last_reviewed_session"},
        "missed_cycle_policy": {"skip"},
    }
    for field, choices in enums.items():
        value = selected[field]
        if value is not None and (not isinstance(value, str) or value not in choices):
            raise ValueError(f"{field} must be one of {', '.join(sorted(choices))}")
    result: dict[str, Any] = {
        "schema_version": 1,
        "method_id": METHOD,
        "state": "unavailable",
        "reason_codes": [],
        "parameters": selected,
        "missing_fields": missing,
        "start": start.isoformat(),
        "horizon_end": None,
        "horizon_semantics": "start_inclusive_anniversary_end_exclusive_original_day_clamped",
        "required_coverage": None,
        "calendar": {
            "coverage_start": coverage_start.isoformat(),
            "coverage_end": coverage_end.isoformat(),
            "known_at": known_at.isoformat(),
            "reference": calendar["reference"],
            "declaration": "operator_provided_continuous_complete_coverage_claim_unverified",
            "source_verified": False,
        },
        "cycles": [],
        "cycle_limit": MAX_CYCLES,
        "execution_authorized": False,
        "policy_activated": False,
        "limitations": [
            "Calendar completeness and future sessions are operator declarations, "
            "not certified exchange facts.",
            "Review dates are previews only; no account policy, orders or "
            "execution times are created.",
            "Uncovered periods remain unresolved; missing sessions and "
            "catch-up dates are never inferred.",
        ],
    }
    if missing:
        result["reason_codes"] = ["MISSING_SCHEDULE_PARAMETERS"]
        return result

    assert isinstance(count, int)  # Validated above; absent values returned without a schedule.
    duration_months = count * (12 if selected["horizon_unit"] == "years" else 1)
    end_index = _month_index(start) + duration_months
    end_year_index, end_month_index = divmod(end_index, 12)
    if end_year_index >= 9999:
        result["reason_codes"] = ["HORIZON_END_OUT_OF_RANGE"]
        return result
    end_year, end_month = end_year_index + 1, end_month_index + 1
    end = date(end_year, end_month, min(start.day, monthrange(end_year, end_month)[1]))
    result["horizon_end"] = end.isoformat()
    period_months = 1 if selected["review_cadence"] == "monthly" else 3
    first_period = _month_index(start) // period_months
    last_period = _month_index(end - timedelta(days=1)) // period_months
    result["cycle_count"] = last_period - first_period + 1
    needed_first, _ = _period_bounds(first_period, period_months)
    _, needed_last = _period_bounds(last_period, period_months)
    result["required_coverage"] = {
        "coverage_start": needed_first.isoformat(),
        "coverage_end": needed_last.isoformat(),
        "bounds": "inclusive_complete_calendar_periods",
    }
    if result["cycle_count"] > MAX_CYCLES:
        result["reason_codes"] = ["CYCLE_LIMIT_EXCEEDED"]
        return result

    rows: list[dict[str, Any]] = []
    for period in range(first_period, last_period + 1):
        first, last = _period_bounds(period, period_months)
        complete = coverage_start <= first and coverage_end >= last
        row: dict[str, Any] = {
            "period_start": first.isoformat(),
            "period_end": last.isoformat(),
            "coverage": "complete_period" if complete else "insufficient_coverage",
            "state": "unavailable",
            "candidate_date": None,
            "review_date": None,
            "reason_codes": [],
        }
        if known_at > as_of:
            row["reason_codes"] = ["CALENDAR_NOT_KNOWN_AT_AS_OF"]
        elif not complete:
            row["reason_codes"] = ["REVIEW_PERIOD_NOT_COVERED"]
        else:
            left, right = bisect_left(days, first), bisect_right(days, last)
            if left == right:
                row.update(state="no_session", reason_codes=["NO_REVIEWED_SESSIONS"])
            else:
                candidate = days[
                    left
                    if selected["review_session_rule"] == "first_reviewed_session"
                    else right - 1
                ]
                row["candidate_date"] = candidate.isoformat()
                if candidate < start:
                    row.update(state="skipped", reason_codes=["CANDIDATE_BEFORE_START_SKIP"])
                elif candidate >= end:
                    row.update(
                        state="skipped", reason_codes=["CANDIDATE_AT_OR_AFTER_HORIZON_END_SKIP"]
                    )
                else:
                    row.update(state="scheduled", review_date=candidate.isoformat())
        rows.append(row)
    resolved = sum(row["state"] != "unavailable" for row in rows)
    result.update(
        state="available" if resolved == len(rows) else "partial" if resolved else "unavailable",
        cycles=rows,
        reason_codes=sorted(
            {code for row in rows if row["state"] == "unavailable" for code in row["reason_codes"]}
        ),
    )
    return result
