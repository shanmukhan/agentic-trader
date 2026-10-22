"""Explain the installed prior-daily screen without assigning scores or authority.

The predicates and tie rule mirror ``daily_research.analysis.Window.metrics`` and
``desk.research.Research.refresh``. This helper reads already published facts; it
does not run a screen, validate source inputs, re-rank rows or approve instruments.
"""

from collections.abc import Callable
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from operator import ge, gt, le
from typing import Any

METHOD_ID = "legacy-prior-daily-momentum-v1"


def _number(value: Any) -> tuple[str | None, Decimal | None]:
    # Decimal(float) would preserve a binary approximation and could silently turn
    # an exact threshold comparison into a different result. Refuse such inputs.
    if isinstance(value, bool) or not isinstance(value, str | int | Decimal):
        return None, None
    try:
        number = Decimal(value)
    except (InvalidOperation, ValueError):
        return None, None
    if not number.is_finite():
        return None, None
    return str(value), number


def _comparison(
    metric: str,
    observed: Any,
    threshold: Any,
    rule: str,
    compare: Callable[[Decimal, Decimal], bool],
    detail: str,
) -> dict[str, Any]:
    observed_text, observed_number = _number(observed)
    threshold_text, threshold_number = _number(threshold)
    state = (
        "unavailable"
        if observed_number is None or threshold_number is None
        else "passed"
        if compare(observed_number, threshold_number)
        else "failed"
    )
    return {
        "metric": metric,
        "observed": observed_text,
        "rule": rule,
        "threshold": threshold_text,
        "state": state,
        "detail": detail
        + (
            " Comparison unavailable: a finite exact observed value or threshold is missing."
            if state == "unavailable"
            else ""
        ),
    }


def _share_class(row: dict[str, Any]) -> dict[str, Any]:
    reasons = row.get("reasons")
    rejected = isinstance(reasons, list) and "EQUITY_SHARE_CLASS_NOT_REVIEWED" in reasons
    reviewed = row.get("equity_share_class_reviewed")
    if rejected or reviewed is False:
        state, observed = "failed", "not_reviewed"
        detail = "The published row explicitly lacks the required equity share-class review."
    elif reviewed is True:
        state, observed = "passed", "reviewed"
        detail = "An explicit positive equity share-class review is present in the input row."
    else:
        state, observed = "unavailable", None
        detail = (
            "No explicit positive equity share-class review is included in this row. "
            "Numeric screen results and an existing rank are not independent review evidence."
        )
    return {
        "metric": "equity_share_class_reviewed",
        "observed": observed,
        "rule": "A reviewed equity share class is required for the execution shortlist",
        "threshold": "reviewed",
        "state": state,
        "detail": detail,
    }


def explain_ranking(rows: list[dict[str, Any]], policy: dict[str, Any]) -> dict[str, Any]:
    """Copy rows and expose exact evidence for the existing screen's predicates.

    Missing/invalid fields remain unavailable. Thresholds come from the supplied
    installed policy, never guessed defaults. ``status`` and ``rank`` are retained
    even if a row's incomplete or contradictory facts cannot explain that status.
    """
    momentum_sessions = _number(policy.get("momentum_sessions"))[0]
    trend_sessions = _number(policy.get("trend_sessions"))[0]
    momentum_window = momentum_sessions or "unrecorded"
    trend_window = trend_sessions or "unrecorded"
    explained = []
    for original in rows:
        row = deepcopy(original)
        row["evidence"] = [
            _comparison(
                "gross_total_return_pct",
                row.get("gross_total_return_pct"),
                "0",
                "gross_total_return_pct > 0",
                gt,
                f"Gross analytical total return over {momentum_window} sessions must be "
                "strictly positive; zero fails. Reviewed share/cash benefits are included "
                "before execution costs and tax.",
            ),
            _comparison(
                "index_level",
                row.get("index_level"),
                row.get("trend_index_average"),
                "index_level >= trend_index_average",
                ge,
                f"The analytical total-return index must equal or exceed its "
                f"{trend_window}-session average; equality passes.",
            ),
            _comparison(
                "average_turnover",
                row.get("average_turnover"),
                policy.get("min_average_turnover"),
                "average_turnover >= min_average_turnover",
                ge,
                f"Average raw close times share volume over {momentum_window} sessions "
                "must meet the installed turnover minimum; equality passes.",
            ),
            _comparison(
                "daily_volatility_pct",
                row.get("daily_volatility_pct"),
                policy.get("max_daily_volatility_pct"),
                "daily_volatility_pct <= max_daily_volatility_pct",
                le,
                f"Population standard deviation of {momentum_window} analytical daily "
                "total returns, in percent, must not exceed the installed maximum; "
                "equality passes. This measure is not annualized.",
            ),
            _share_class(row),
        ]
        explained.append(row)
    return {
        "method_id": METHOD_ID,
        "detail": (
            "Explanation of the installed prior-daily momentum, trend, turnover and "
            "volatility screen. Existing row order, statuses and ranks are preserved; "
            "no new score or eligibility decision is calculated. A research candidate "
            "is not an order, forecast, backtest or investment approval."
        ),
        "tie_rule": (
            "The legacy screen ranks research_candidate rows by gross_total_return_pct "
            "descending, then symbol ascending for equal returns, after excluding "
            "unreviewed equity share classes. This explanation does not re-rank rows."
        ),
        "thresholds": {
            "momentum_sessions": momentum_sessions,
            "trend_sessions": trend_sessions,
            "momentum_min_exclusive_pct": "0",
            "min_average_turnover": _number(policy.get("min_average_turnover"))[0],
            "max_daily_volatility_pct": _number(policy.get("max_daily_volatility_pct"))[0],
        },
        "rows": explained,
    }
