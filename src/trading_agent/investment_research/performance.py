"""Explicit daily-cut performance, separate from legacy event-time equity evidence.

The caller supplies a reviewed session calendar, an explicit opening baseline and
a no-external-flow declaration. This module never invents sessions, values, flows
or baseline observations. All calculations use a private 34-digit, HALF_EVEN
Decimal context; annualized research estimates stay separate from primary metrics.
"""

import re
from calendar import monthrange
from datetime import date, datetime
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from typing import Any

from trading_agent.market_data.calendar import IST

METHOD = "portfolio-daily-net-liquidation-performance-v1"
_CONTEXT = Context(prec=34, rounding=ROUND_HALF_EVEN)
_DECIMAL = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[Ee][+-]?[0-9]{1,3})?\Z")
_METRICS = {
    "total_return_pct": ("percent", "endpoint-net-equity-return-v1"),
    "cagr_pct": ("percent", "endpoint-cagr-365.25-v1"),
    "maximum_drawdown_pct": ("percent", "complete-daily-maximum-drawdown-v1"),
    "annualized_volatility_pct": ("percent", "sample-daily-volatility-annualized-v1"),
    "sharpe": ("ratio", "daily-excess-return-sample-sharpe-v1"),
    "sortino": ("ratio", "daily-target-downside-all-samples-sortino-v1"),
}


def _decimal(value: object, label: str) -> Decimal:
    if not isinstance(value, str) or len(value) > 128 or not _DECIMAL.fullmatch(value):
        raise ValueError(f"{label} must be a bounded finite Decimal string")
    try:
        result = Decimal(value)
    except ArithmeticError as exc:
        raise ValueError(f"{label} must be a bounded finite Decimal string") from exc
    if not result.is_finite() or not -64 <= result.adjusted() <= 64:
        raise ValueError(f"{label} must be a bounded finite Decimal string")
    return result


def _date(value: object) -> date:
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError("sessions and coverage bounds require canonical YYYY-MM-DD dates")
    try:
        result = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("sessions and coverage bounds require canonical YYYY-MM-DD dates") from exc
    if result.isoformat() != value:
        raise ValueError("sessions and coverage bounds require canonical YYYY-MM-DD dates")
    return result


def _metric(name: str, value: Decimal | None, reason: str | None = None) -> dict[str, Any]:
    unit, method = _METRICS[name]
    return {
        "value": str(value) if value is not None else None,
        "state": "available" if value is not None else "unavailable",
        "unit": unit,
        "reason_codes": [reason] if reason else [],
        "method_id": method,
    }


def unavailable_performance(reason_code: str, detail: str) -> dict[str, Any]:
    """Represent missing daily evidence honestly, including event-time-only jobs."""
    return {
        "state": "unavailable",
        "method_id": METHOD,
        "decimal_precision": 34,
        "rounding": ROUND_HALF_EVEN,
        "metrics": {name: _metric(name, None, reason_code) for name in _METRICS},
        "provisional_metrics": {},
        "coverage": {"state": "incomplete", "reason_codes": [reason_code]},
        "points": [],
        "daily_returns": [],
        "drawdown": None,
        "monthly_returns": {"state": "unavailable", "reason_codes": [reason_code], "rows": []},
        "detail": detail,
        "limitations": [
            "Existing event-time equity.csv observations are not accepted daily valuation cuts.",
            "No missing prices, sessions, baseline or external-flow history is inferred.",
        ],
    }


def _months(
    parsed: dict[str, dict[str, Any]],
    expected: list[str],
    opening: dict[str, Any],
    start: str | None,
    end: str | None,
    flows_known_zero: bool,
) -> dict[str, Any]:
    if start is None or end is None:
        return {
            "state": "unavailable",
            "reason_codes": ["MONTH_COVERAGE_NOT_DECLARED"],
            "rows": [],
        }
    first, last = _date(start), _date(end)
    if first > last or first > _date(opening["session"]) or last < _date(expected[-1]):
        raise ValueError("monthly coverage bounds must include the entire declared series")
    if (last - first).days > 36600:
        raise ValueError("monthly coverage cannot exceed 100 calendar years")
    rows: list[dict[str, Any]] = []
    year, month = first.year, first.month
    prior = opening
    while (year, month) <= (last.year, last.month):
        month_first = date(year, month, 1)
        month_last = date(year, month, monthrange(year, month)[1])
        sessions = [s for s in expected if _date(s).year == year and _date(s).month == month]
        full = first <= month_first and last >= month_last
        reason = None
        value = None
        if not full or _date(prior["session"]) >= month_first:
            reason = "PARTIAL_MONTH"
        elif not sessions:
            reason = "NO_REVIEWED_SESSIONS"
        elif not flows_known_zero:
            reason = "UNSUPPORTED_EXTERNAL_FLOW"
        elif not prior["eligible"] or any(not parsed.get(s, {}).get("eligible") for s in sessions):
            reason = "INCOMPLETE_SERIES"
        else:
            value = (parsed[sessions[-1]]["value"] / prior["value"] - 1) * 100
        rows.append(
            {
                "month": f"{year:04d}-{month:02d}",
                "value": str(value) if value is not None else None,
                "unit": "percent",
                "state": "available" if value is not None else "unavailable",
                "coverage": "complete_month" if full else "partial_month",
                "reason_codes": [reason] if reason else [],
                "start_session": prior["session"],
                "end_session": sessions[-1] if sessions else None,
                "expected_sessions": len(sessions),
                "method_id": "complete-reviewed-month-compounded-return-v1",
            }
        )
        if sessions:
            # A missing month-end is a gap, not a licence to use an older mark.
            prior = parsed.get(sessions[-1], {"session": sessions[-1], "eligible": False})
        year, month = (year + 1, 1) if month == 12 else (year, month + 1)
    available = sum(row["state"] == "available" for row in rows)
    return {
        "state": "available"
        if rows and available == len(rows)
        else "partial"
        if available
        else "unavailable",
        "reason_codes": [] if rows and available == len(rows) else ["INCOMPLETE_MONTH_COVERAGE"],
        "rows": rows,
    }


def performance_summary(
    points: list[dict[str, Any]],
    expected_sessions: list[str],
    initial_equity: str,
    *,
    annualization: int = 252,
    risk_free_daily: str | None = None,
    minimum_annual_days: int = 365,
    flows_known_zero: bool = False,
    sortino_target_daily: str | None = None,
    coverage_start: str | None = None,
    coverage_end: str | None = None,
) -> dict[str, Any]:
    """Measure explicit daily-cut net equity with exact, nullable evidence.

    ``expected_sessions`` is the complete caller-sourced ordered session calendar,
    excluding the opening baseline. Points are strictly ordered by session/time;
    each has ``session``, offset-aware ISO ``time``, ``equity`` (Decimal string or
    null), and a boolean ``complete``. Only the first has ``opening: True``; its
    complete equity must equal ``initial_equity``. The baseline must precede all
    expected sessions. Missing expected points stay explicit gaps. Comparability
    of the caller's single valuation method/currency/account is a prerequisite.

    No-flow history must be explicitly declared. Configured constant risk-free
    and downside-target rates are daily fractions, labelled research assumptions.
    Primary annualized measures require >=252 consecutive returns and >=365 days
    (or the larger configured threshold). Shorter mathematical estimates appear
    only in ``provisional_metrics``. Monthly results require explicit calendar
    range bounds; weekdays and holidays are never guessed.
    """
    initial = _decimal(initial_equity, "initial_equity")
    if type(annualization) is not int or not 1 <= annualization <= 3660:
        raise ValueError("annualization must be a positive bounded integer convention")
    if type(minimum_annual_days) is not int or minimum_annual_days < 365:
        raise ValueError("primary annualization requires at least 365 calendar days")
    if type(flows_known_zero) is not bool:
        raise ValueError("flows_known_zero must be explicitly boolean")
    rf = _decimal(risk_free_daily, "risk_free_daily") if risk_free_daily is not None else None
    target = (
        _decimal(sortino_target_daily, "sortino_target_daily")
        if sortino_target_daily is not None
        else None
    )
    if not isinstance(points, list) or not isinstance(expected_sessions, list):
        raise ValueError("daily points and expected sessions must be lists")
    if len(points) > 25_001 or len(expected_sessions) > 25_000:
        raise ValueError("daily performance is limited to 25,000 reviewed sessions")
    expected_days = [_date(s) for s in expected_sessions]
    if expected_days != sorted(set(expected_days)):
        raise ValueError("expected sessions must be strictly ordered and unique")
    if not points:
        return unavailable_performance(
            "NO_DAILY_VALUATIONS", "No explicit daily-cut equity series is supplied."
        )
    parsed: dict[str, dict[str, Any]] = {}
    expected_set = set(expected_sessions)
    previous_time: datetime | None = None
    previous_day: date | None = None
    for index, point in enumerate(points):
        if not isinstance(point, dict):
            raise ValueError("each daily point must be an object")
        day = _date(point.get("session"))
        raw_time = point.get("time")
        if not isinstance(raw_time, str) or len(raw_time) > 64:
            raise ValueError("daily point time must be an aware ISO timestamp")
        try:
            observed = datetime.fromisoformat(raw_time)
        except ValueError as exc:
            raise ValueError("daily point time must be an aware ISO timestamp") from exc
        if observed.tzinfo is None or observed.utcoffset() is None:
            raise ValueError("daily point time must be an aware ISO timestamp")
        if observed.astimezone(IST).date() != day:
            raise ValueError("daily point time must belong to its declared IST session")
        if (
            previous_day is not None
            and previous_time is not None
            and (day <= previous_day or observed <= previous_time)
        ):
            raise ValueError("daily point sessions and times must be strictly increasing")
        if type(point.get("complete")) is not bool:
            raise ValueError("daily completeness must be explicitly boolean")
        if "opening" in point and type(point["opening"]) is not bool:
            raise ValueError("opening baseline marker must be boolean")
        if index == 0:
            if point.get("opening") is not True:
                raise ValueError("daily series requires an explicit opening baseline")
            if expected_days and day >= expected_days[0]:
                raise ValueError("opening baseline must precede expected daily sessions")
        elif point.get("opening") is True or day.isoformat() not in expected_set:
            raise ValueError(
                "only reviewed expected daily sessions may follow the opening baseline"
            )
        value = (
            _decimal(point["equity"], "daily equity") if point.get("equity") is not None else None
        )
        if index == 0 and point["complete"] and value is not None and value != initial:
            raise ValueError("complete opening baseline must equal declared initial equity")
        parsed[day.isoformat()] = {
            "session": day.isoformat(),
            "time": raw_time,
            "value": value,
            "eligible": point["complete"] and value is not None and value > 0,
            "equity": point.get("equity"),
            "complete": point["complete"],
            "opening": index == 0,
        }
        previous_time, previous_day = observed, day
    opening = next(iter(parsed.values()))
    if not expected_sessions:
        return unavailable_performance(
            "INSUFFICIENT_OBSERVATIONS", "An opening baseline alone has no return interval."
        )
    final = parsed.get(expected_sessions[-1])
    missing = [s for s in expected_sessions if s not in parsed]
    incomplete = [s for s in expected_sessions if s in parsed and not parsed[s]["eligible"]]
    complete_path = opening["eligible"] and not missing and not incomplete
    endpoints = opening["eligible"] and final is not None and final["eligible"] and initial > 0
    elapsed = (_date(expected_sessions[-1]) - _date(opening["session"])).days
    result = unavailable_performance(
        "INCOMPLETE_SERIES", "Explicit daily-cut net-equity measurements; no execution authority."
    )
    result["coverage"] = {
        "state": "complete" if complete_path else "incomplete",
        "opening_session": opening["session"],
        "end_session": expected_sessions[-1],
        "elapsed_calendar_days": elapsed,
        "expected_sessions": len(expected_sessions),
        "observed_sessions": sum(s in parsed for s in expected_sessions),
        "missing_sessions": missing,
        "incomplete_sessions": incomplete,
        "flows_known_zero": flows_known_zero,
        "reason_codes": [] if complete_path else ["INCOMPLETE_SERIES"],
    }
    result["points"] = [
        {key: row[key] for key in ("session", "time", "equity", "complete", "opening")}
        for row in [
            opening,
            *(
                parsed.get(
                    s,
                    {
                        "session": s,
                        "time": None,
                        "equity": None,
                        "complete": False,
                        "opening": False,
                    },
                )
                for s in expected_sessions
            ),
        ]
    ]
    metrics = result["metrics"]
    with localcontext(_CONTEXT):
        endpoint_reason = (
            "UNSUPPORTED_EXTERNAL_FLOW"
            if not flows_known_zero
            else "NONPOSITIVE_BASE"
            if initial <= 0
            or any(
                row and row["value"] is not None and row["value"] <= 0 for row in (opening, final)
            )
            else "INCOMPLETE_ENDPOINTS"
            if not endpoints
            else None
        )
        if endpoint_reason:
            metrics["total_return_pct"] = _metric("total_return_pct", None, endpoint_reason)
            metrics["cagr_pct"] = _metric("cagr_pct", None, endpoint_reason)
        else:
            assert final is not None
            ratio = final["value"] / initial
            metrics["total_return_pct"] = _metric("total_return_pct", (ratio - 1) * 100)
            metrics["cagr_pct"] = (
                _metric("cagr_pct", (ratio ** (Decimal("365.25") / elapsed) - 1) * 100)
                if elapsed >= minimum_annual_days
                else _metric("cagr_pct", None, "INSUFFICIENT_OBSERVATIONS")
            )
        path_reason = (
            "UNSUPPORTED_EXTERNAL_FLOW"
            if not flows_known_zero
            else "INCOMPLETE_SERIES"
            if not complete_path
            else None
        )
        if path_reason:
            for name in ("maximum_drawdown_pct", "annualized_volatility_pct", "sharpe", "sortino"):
                metrics[name] = _metric(name, None, path_reason)
        else:
            values = [opening, *(parsed[s] for s in expected_sessions)]
            returns = [
                b["value"] / a["value"] - 1 for a, b in zip(values, values[1:], strict=False)
            ]
            result["daily_returns"] = [
                {"session": session, "value": str(value), "unit": "fraction"}
                for session, value in zip(expected_sessions, returns, strict=True)
            ]
            peak = values[0]
            worst = Decimal(0)
            drawdown = {
                "amount": "0",
                "peak_session": peak["session"],
                "trough_session": peak["session"],
                "duration_calendar_days": 0,
            }
            for row in values[1:]:
                if row["value"] > peak["value"]:
                    peak = row
                decline = 1 - row["value"] / peak["value"]
                if decline > worst:
                    worst = decline
                    drawdown = {
                        "amount": str(peak["value"] - row["value"]),
                        "peak_session": peak["session"],
                        "trough_session": row["session"],
                        "duration_calendar_days": (
                            _date(row["session"]) - _date(peak["session"])
                        ).days,
                    }
            metrics["maximum_drawdown_pct"] = _metric("maximum_drawdown_pct", worst * 100)
            result["drawdown"] = drawdown
            n = len(returns)
            annual_eligible = n >= 252 and elapsed >= minimum_annual_days
            estimates: dict[str, dict[str, Any]] = {}
            if n < 2:
                estimates = {
                    name: _metric(name, None, "INSUFFICIENT_OBSERVATIONS")
                    for name in ("annualized_volatility_pct", "sharpe", "sortino")
                }
            else:
                mean = sum(returns, Decimal(0)) / n
                variance = sum(((value - mean) ** 2 for value in returns), Decimal(0)) / (n - 1)
                deviation = variance.sqrt()
                annual_factor = Decimal(annualization).sqrt()
                estimates["annualized_volatility_pct"] = _metric(
                    "annualized_volatility_pct", deviation * annual_factor * 100
                )
                estimates["sharpe"] = (
                    _metric("sharpe", None, "RISK_FREE_NOT_CONFIGURED")
                    if rf is None
                    else _metric("sharpe", None, "ZERO_VARIANCE")
                    if not deviation
                    else _metric("sharpe", (mean - rf) / deviation * annual_factor)
                )
                if target is None:
                    estimates["sortino"] = _metric(
                        "sortino", None, "DOWNSIDE_TARGET_NOT_CONFIGURED"
                    )
                else:
                    downside = (
                        sum((min(Decimal(0), value - target) ** 2 for value in returns), Decimal(0))
                        / n
                    ).sqrt()
                    estimates["sortino"] = (
                        _metric("sortino", (mean - target) / downside * annual_factor)
                        if downside
                        else _metric("sortino", None, "NO_DOWNSIDE_OBSERVATIONS")
                    )
            for name, estimate in estimates.items():
                if annual_eligible:
                    metrics[name] = estimate
                else:
                    metrics[name] = _metric(name, None, "INSUFFICIENT_OBSERVATIONS")
                    result["provisional_metrics"][name] = {**estimate, "provisional": True}
        result["monthly_returns"] = _months(
            parsed, expected_sessions, opening, coverage_start, coverage_end, flows_known_zero
        )
    available = sum(metric["state"] == "available" for metric in metrics.values())
    result["state"] = (
        "available" if available == len(metrics) else "partial" if available else "unavailable"
    )
    result["annualization"] = {
        "sessions_per_year_convention": annualization,
        "minimum_primary_returns": 252,
        "minimum_primary_calendar_days": minimum_annual_days,
        "cagr_days_per_year": "365.25",
        "risk_free_daily": risk_free_daily,
        "risk_free_source": "explicit constant research assumption" if rf is not None else None,
        "sortino_target_daily": sortino_target_daily,
        "sortino_downside_denominator": "all daily return samples",
    }
    return result
