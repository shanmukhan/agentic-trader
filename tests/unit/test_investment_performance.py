"""Closed-form daily-series examples; no real-market performance acceptance."""

from copy import deepcopy
from datetime import date, timedelta
from decimal import ROUND_DOWN, Context, Decimal, Inexact, localcontext
from fractions import Fraction

import pytest

from trading_agent.investment_research.performance import (
    performance_summary,
    unavailable_performance,
)


def point(session, equity, *, opening=False, complete=True, **extra):
    return {
        "session": session,
        "time": f"{session}T15:30:00+05:30",
        "equity": equity,
        "complete": complete,
        "opening": opening,
        **extra,
    }


def small_path():
    sessions = ["2026-10-19", "2026-10-20", "2026-10-21", "2026-10-22"]
    points = [
        point(s, v, opening=i == 0)
        for i, (s, v) in enumerate(zip(sessions, ["1000", "1100", "990", "1089"], strict=True))
    ]
    return points, sessions[1:]


def summary(points=None, expected=None, **kwargs):
    if points is None:
        points, expected = small_path()
    return performance_summary(points, expected, "1000", flows_known_zero=True, **kwargs)


def assert_near(actual, expected, tolerance="1e-28"):
    with localcontext(Context(prec=60)):
        assert abs(Decimal(actual) - expected) < Decimal(tolerance)


def test_compounded_total_and_drawdown_not_sum_of_returns_or_end_loss():
    points, expected = small_path()
    original = deepcopy(points)
    actual = summary(points, expected)
    assert Decimal(actual["metrics"]["total_return_pct"]["value"]) == Decimal("8.9")
    assert Decimal(actual["metrics"]["maximum_drawdown_pct"]["value"]) == Decimal("10")
    assert actual["drawdown"] == {
        "amount": "110",
        "peak_session": "2026-10-20",
        "trough_session": "2026-10-21",
        "duration_calendar_days": 1,
    }
    assert [Decimal(row["value"]) for row in actual["daily_returns"]] == [
        Decimal(".1"),
        Decimal("-.1"),
        Decimal(".1"),
    ]
    assert points == original


def test_short_sample_risk_is_separate_provisional_and_closed_form_verified():
    actual = summary(risk_free_daily="0", sortino_target_daily="0")
    for key in ("cagr_pct", "annualized_volatility_pct", "sharpe", "sortino"):
        assert actual["metrics"][key]["value"] is None
        assert actual["metrics"][key]["reason_codes"] == ["INSUFFICIENT_OBSERVATIONS"]
    samples = [Fraction(1, 10), Fraction(-1, 10), Fraction(1, 10)]
    mean = sum(samples) / len(samples)
    variance = sum((value - mean) ** 2 for value in samples) / (len(samples) - 1)
    downside_variance = sum(min(0, value) ** 2 for value in samples) / len(samples)
    with localcontext(Context(prec=60)):
        dmean = Decimal(mean.numerator) / mean.denominator
        std = (Decimal(variance.numerator) / variance.denominator).sqrt()
        downside = (Decimal(downside_variance.numerator) / downside_variance.denominator).sqrt()
        factor = Decimal(252).sqrt()
        provisional = actual["provisional_metrics"]
        assert_near(provisional["annualized_volatility_pct"]["value"], std * factor * 100)
        assert_near(provisional["sharpe"]["value"], dmean / std * factor)
        assert_near(provisional["sortino"]["value"], dmean / downside * factor)
        assert all(row["provisional"] for row in provisional.values())


@pytest.mark.parametrize("gap_kind", ["missing", "null", "incomplete", "zero"])
def test_internal_gap_keeps_endpoint_return_but_disables_path_metrics(gap_kind):
    points, expected = small_path()
    if gap_kind == "missing":
        del points[1]
    elif gap_kind == "null":
        points[1]["equity"] = None
    elif gap_kind == "zero":
        points[1]["equity"] = "0"
    else:
        points[1]["complete"] = False
    actual = summary(points, expected)
    assert Decimal(actual["metrics"]["total_return_pct"]["value"]) == Decimal("8.9")
    assert actual["coverage"]["state"] == "incomplete"
    for name in ("maximum_drawdown_pct", "annualized_volatility_pct", "sharpe", "sortino"):
        assert actual["metrics"][name]["value"] is None
        assert actual["metrics"][name]["reason_codes"] == ["INCOMPLETE_SERIES"]
    assert actual["daily_returns"] == []
    assert actual["provisional_metrics"] == {}
    assert (
        actual["points"][1]["equity"] == points[1]["equity"]
        if gap_kind != "missing"
        else actual["points"][1]["equity"] is None
    )


def test_missing_session_endpoints_can_support_cagr_but_not_drawdown():
    points = [point("2024-01-01", "1000", opening=True), point("2025-01-01", "1100")]
    actual = summary(points, ["2024-06-03", "2025-01-01"])
    assert actual["coverage"]["elapsed_calendar_days"] == 366  # Leap-year day count.
    with localcontext(Context(prec=60)):
        expected = ((Decimal("1.1") ** (Decimal("365.25") / 366)) - 1) * 100
        assert_near(actual["metrics"]["cagr_pct"]["value"], expected)
    assert actual["metrics"]["maximum_drawdown_pct"]["value"] is None


def test_unknown_or_explicitly_unsupported_external_flows_disable_every_return():
    points, expected = small_path()
    actual = performance_summary(points, expected, "1000")
    assert actual["state"] == "unavailable"
    assert all(row["value"] is None for row in actual["metrics"].values())
    assert all(
        row["reason_codes"] == ["UNSUPPORTED_EXTERNAL_FLOW"] for row in actual["metrics"].values()
    )
    assert actual["coverage"]["flows_known_zero"] is False
    assert actual["daily_returns"] == []


def annual_path():
    opening = date(2023, 12, 29)
    # Caller-sourced synthetic session set; the implementation does not guess it.
    days = [
        opening + timedelta(days=i)
        for i in range(1, 369)
        if (opening + timedelta(days=i)).weekday() < 5
    ]
    return [
        point(opening.isoformat(), "1000", opening=True),
        *(point(day.isoformat(), "1000") for day in days),
    ], [day.isoformat() for day in days]


def test_all_cash_annual_zero_volatility_and_undefined_sharpe_and_sortino():
    points, expected = annual_path()
    actual = summary(points, expected, risk_free_daily="0", sortino_target_daily="0")
    assert actual["coverage"]["state"] == "complete"
    assert len(actual["daily_returns"]) >= 252
    for key in (
        "total_return_pct",
        "cagr_pct",
        "maximum_drawdown_pct",
        "annualized_volatility_pct",
    ):
        assert Decimal(actual["metrics"][key]["value"]) == 0
    assert actual["metrics"]["sharpe"]["reason_codes"] == ["ZERO_VARIANCE"]
    assert actual["metrics"]["sortino"]["reason_codes"] == ["NO_DOWNSIDE_OBSERVATIONS"]
    assert actual["provisional_metrics"] == {}


def test_primary_ratios_require_explicit_risk_free_and_downside_target():
    points, expected = annual_path()
    # Nonconstant levels produce nonzero variance without constructing inexact money.
    for index, row in enumerate(points[1:]):
        row["equity"] = str(1000 + index % 3)
    actual = summary(points, expected)
    assert actual["metrics"]["annualized_volatility_pct"]["state"] == "available"
    assert actual["metrics"]["sharpe"]["reason_codes"] == ["RISK_FREE_NOT_CONFIGURED"]
    assert actual["metrics"]["sortino"]["reason_codes"] == ["DOWNSIDE_TARGET_NOT_CONFIGURED"]


def test_long_elapsed_time_with_only_three_daily_samples_is_not_primary_annual_risk():
    points, _ = small_path()
    points[-1] = point("2027-10-22", "1089")
    expected = [row["session"] for row in points[1:]]
    actual = summary(points, expected)
    assert actual["metrics"]["cagr_pct"]["state"] == "available"
    assert actual["metrics"]["annualized_volatility_pct"]["value"] is None
    assert actual["provisional_metrics"]["annualized_volatility_pct"]["state"] == "available"


def test_monthly_requires_declared_range_then_compounds_only_full_reviewed_month():
    points = [
        point("2026-09-30", "1000", opening=True),
        point("2026-10-05", "1100"),
        point("2026-10-30", "990"),
    ]
    expected = [row["session"] for row in points[1:]]
    unspecified = summary(points, expected)
    assert unspecified["monthly_returns"]["reason_codes"] == ["MONTH_COVERAGE_NOT_DECLARED"]
    actual = summary(points, expected, coverage_start="2026-09-30", coverage_end="2026-10-31")
    september, october = actual["monthly_returns"]["rows"]
    assert september["value"] is None
    assert september["reason_codes"] == ["PARTIAL_MONTH"]
    assert october["coverage"] == "complete_month"
    assert Decimal(october["value"]) == Decimal("-1")  # 10% then -10%, not zero.
    assert october["expected_sessions"] == 2
    gap = summary(
        [points[0], points[-1]], expected, coverage_start="2026-09-30", coverage_end="2026-10-31"
    )
    assert gap["monthly_returns"]["rows"][1]["reason_codes"] == ["INCOMPLETE_SERIES"]


def test_no_annualization_from_few_profitable_days_and_no_weakened_policy():
    actual = summary(annualization=1)
    assert actual["metrics"]["annualized_volatility_pct"]["value"] is None
    with pytest.raises(ValueError, match="365"):
        summary(minimum_annual_days=1)


def test_missing_final_or_opening_point_does_not_infer_endpoint_zero():
    points, expected = small_path()
    actual = summary(points[:-1], expected)
    assert actual["metrics"]["total_return_pct"]["value"] is None
    assert actual["metrics"]["total_return_pct"]["reason_codes"] == ["INCOMPLETE_ENDPOINTS"]
    points[0]["equity"] = None
    actual = summary(points, expected)
    assert actual["metrics"]["total_return_pct"]["value"] is None
    assert actual["points"][0]["equity"] is None


def test_empty_and_event_time_evidence_never_pretend_daily_metrics_available():
    empty = performance_summary([], [], "1000")
    assert empty["metrics"]["total_return_pct"]["value"] is None
    event = unavailable_performance("EVENT_TIME_NOT_DAILY_CUTS", "Observed event snapshots only.")
    assert event["state"] == "unavailable"
    assert event["metrics"]["annualized_volatility_pct"]["reason_codes"] == [
        "EVENT_TIME_NOT_DAILY_CUTS"
    ]
    assert event["daily_returns"] == []


@pytest.mark.parametrize("equity", ["0", "-1"])
def test_nonpositive_equity_cannot_form_return_denominator(equity):
    points, expected = small_path()
    points[-1]["equity"] = equity
    actual = summary(points, expected)
    assert actual["metrics"]["total_return_pct"]["reason_codes"] == ["NONPOSITIVE_BASE"]


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate",
        "reversed",
        "naive",
        "wrong_date",
        "float",
        "missing_opening",
        "changed_seed",
        "outside_calendar",
        "duplicate_calendar",
        "incomplete_type",
    ],
)
def test_bad_daily_schema_or_calendar_is_rejected(mutation):
    points, expected = small_path()
    if mutation == "duplicate":
        points.insert(1, deepcopy(points[0]))
    elif mutation == "reversed":
        points.reverse()
    elif mutation == "naive":
        points[1]["time"] = "2026-10-20T15:30:00"
    elif mutation == "wrong_date":
        points[1]["time"] = "2026-10-19T15:30:00+05:30"
    elif mutation == "float":
        points[1]["equity"] = 1100.0
    elif mutation == "missing_opening":
        points[0]["opening"] = False
    elif mutation == "changed_seed":
        points[0]["equity"] = "999"
    elif mutation == "outside_calendar":
        expected.remove(points[1]["session"])
    elif mutation == "duplicate_calendar":
        expected.append(expected[-1])
    else:
        points[1]["complete"] = 1
    with pytest.raises(ValueError):
        summary(points, expected)


def test_independent_decimal_context_preserves_results_and_caller_settings():
    expected = summary(risk_free_daily="0", sortino_target_daily="0")
    with localcontext() as ctx:
        ctx.prec = 3
        ctx.rounding = ROUND_DOWN
        ctx.traps[Inexact] = True
        assert summary(risk_free_daily="0", sortino_target_daily="0") == expected
        assert ctx.prec == 3 and ctx.rounding == ROUND_DOWN and ctx.traps[Inexact]
