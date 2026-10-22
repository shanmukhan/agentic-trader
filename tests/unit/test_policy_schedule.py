"""Synthetic declared calendars; these tests do not certify exchange sessions."""

from copy import deepcopy
from datetime import UTC, date, datetime, timedelta

import pytest

from trading_agent.investment_research.policy_schedule import preview_schedule

AS_OF = datetime(2026, 10, 22, 12, tzinfo=UTC)


def parameters(**changes):
    return {
        "horizon_count": 2,
        "horizon_unit": "months",
        "review_cadence": "monthly",
        "review_session_rule": "first_reviewed_session",
        "missed_cycle_policy": "skip",
        **changes,
    }


def calendar(sessions=(), *, first="2026-01-01", last="2026-12-31", **changes):
    return {
        "coverage_start": first,
        "coverage_end": last,
        "sessions": list(sessions),
        "known_at": "2026-01-01T00:00:00+00:00",
        "reference": "Synthetic explicitly complete calendar declaration",
        **changes,
    }


def preview(config=None, declared=None, start=date(2026, 1, 1), as_of=AS_OF):
    return preview_schedule(config or parameters(), start, declared or calendar(), as_of)


def test_first_declared_sessions_use_sparse_sourced_dates_instead_of_weekdays():
    # The source intentionally declares unusual dates. There is no weekday inference.
    declared = calendar(["2026-01-04", "2026-01-21", "2026-02-08", "2026-02-27"])
    actual = preview(declared=declared)
    assert actual["state"] == "available"
    assert actual["horizon_end"] == "2026-03-01"
    assert [row["review_date"] for row in actual["cycles"]] == ["2026-01-04", "2026-02-08"]
    assert actual["required_coverage"] == {
        "coverage_start": "2026-01-01",
        "coverage_end": "2026-02-28",
        "bounds": "inclusive_complete_calendar_periods",
    }
    assert actual["calendar"]["source_verified"] is False
    assert "unverified" in actual["calendar"]["declaration"]
    assert actual["execution_authorized"] is actual["policy_activated"] is False


def test_last_session_preserves_nonstandard_holiday_gaps_without_guessing():
    actual = preview(
        parameters(review_session_rule="last_reviewed_session"),
        calendar(["2026-01-02", "2026-01-23", "2026-02-03", "2026-02-20"]),
    )
    assert [row["review_date"] for row in actual["cycles"]] == ["2026-01-23", "2026-02-20"]


@pytest.mark.parametrize(
    ("start", "count", "unit", "expected"),
    [
        (date(2024, 1, 31), 1, "months", "2024-02-29"),
        (date(2024, 1, 31), 2, "months", "2024-03-31"),
        (date(2026, 1, 31), 1, "months", "2026-02-28"),
        (date(2024, 2, 29), 1, "years", "2025-02-28"),
        (date(2024, 2, 29), 4, "years", "2028-02-29"),
        (date(2026, 12, 31), 2, "months", "2027-02-28"),
    ],
)
def test_horizon_uses_original_anchor_month_end_and_leap_day(start, count, unit, expected):
    actual = preview(
        parameters(horizon_count=count, horizon_unit=unit),
        calendar(first="2024-01-01", last="2028-12-31"),
        start,
    )
    assert actual["horizon_end"] == expected
    assert "original_day_clamped" in actual["horizon_semantics"]


def test_quarterly_periods_are_calendar_quarters_and_first_session_before_start_skips():
    actual = preview(
        parameters(horizon_count=6, review_cadence="quarterly"),
        calendar(["2026-01-07", "2026-03-12", "2026-04-08", "2026-06-19", "2026-07-06"]),
        date(2026, 2, 10),
    )
    assert actual["horizon_end"] == "2026-08-10"
    assert actual["required_coverage"]["coverage_end"] == "2026-09-30"
    assert [(row["period_start"], row["period_end"]) for row in actual["cycles"]] == [
        ("2026-01-01", "2026-03-31"),
        ("2026-04-01", "2026-06-30"),
        ("2026-07-01", "2026-09-30"),
    ]
    assert [row["state"] for row in actual["cycles"]] == ["skipped", "scheduled", "scheduled"]
    assert actual["cycles"][0]["candidate_date"] == "2026-01-07"
    assert actual["cycles"][0]["review_date"] is None
    assert actual["cycles"][0]["reason_codes"] == ["CANDIDATE_BEFORE_START_SKIP"]
    # A later session in the starting quarter is not repurposed as catch-up.
    assert "2026-03-12" not in [row["review_date"] for row in actual["cycles"]]


def test_quarterly_last_and_exclusive_horizon_end_skip_equal_and_later_dates():
    config = parameters(
        horizon_count=6, review_cadence="quarterly", review_session_rule="last_reviewed_session"
    )
    actual = preview(
        config,
        calendar(["2026-03-31", "2026-06-25", "2026-08-10"]),
        date(2026, 2, 10),
    )
    assert [row["review_date"] for row in actual["cycles"]] == ["2026-03-31", "2026-06-25", None]
    assert actual["cycles"][2]["candidate_date"] == actual["horizon_end"]
    assert actual["cycles"][2]["reason_codes"] == ["CANDIDATE_AT_OR_AFTER_HORIZON_END_SKIP"]
    later = preview(config, calendar(["2026-09-30"]), date(2026, 2, 10))
    assert later["cycles"][2]["state"] == "skipped"
    assert later["cycles"][2]["review_date"] is None


def test_candidate_equal_start_is_included_and_end_boundary_period_is_excluded():
    actual = preview(declared=calendar(["2026-01-01", "2026-02-01", "2026-03-01"]))
    assert [row["review_date"] for row in actual["cycles"]] == ["2026-01-01", "2026-02-01"]
    assert len(actual["cycles"]) == 2


def test_partial_calendar_cannot_establish_first_or_last_even_with_observed_candidate():
    for rule in ("first_reviewed_session", "last_reviewed_session"):
        actual = preview(
            parameters(review_session_rule=rule),
            calendar(["2026-01-31", "2026-02-02"], first="2026-01-02", last="2026-02-27"),
        )
        assert actual["state"] == "unavailable"
        assert actual["reason_codes"] == ["REVIEW_PERIOD_NOT_COVERED"]
        assert all(row["candidate_date"] is None for row in actual["cycles"])
        assert all(row["coverage"] == "insufficient_coverage" for row in actual["cycles"])


def test_horizon_inside_month_still_requires_full_month_calendar_coverage():
    actual = preview(
        parameters(horizon_count=1),
        calendar(["2026-01-20", "2026-02-02"], first="2026-01-01", last="2026-02-15"),
        date(2026, 1, 15),
    )
    assert actual["state"] == "partial"
    assert actual["horizon_end"] == "2026-02-15"
    assert actual["required_coverage"]["coverage_end"] == "2026-02-28"
    assert [row["state"] for row in actual["cycles"]] == ["scheduled", "unavailable"]


def test_quarterly_requires_full_quarter_not_just_full_starting_month():
    actual = preview(
        parameters(horizon_count=1, review_cadence="quarterly"),
        calendar(["2026-01-05"], first="2026-01-01", last="2026-01-31"),
    )
    assert actual["required_coverage"]["coverage_end"] == "2026-03-31"
    assert actual["cycles"][0]["state"] == "unavailable"
    assert actual["cycles"][0]["candidate_date"] is None


def test_empty_complete_period_is_no_session_without_invented_weekday():
    actual = preview()
    assert actual["state"] == "available"
    assert all(row["state"] == "no_session" for row in actual["cycles"])
    assert all(row["review_date"] is row["candidate_date"] is None for row in actual["cycles"])
    assert all(row["reason_codes"] == ["NO_REVIEWED_SESSIONS"] for row in actual["cycles"])


def test_session_omitted_inside_declared_complete_period_is_unverified_not_reconstructed():
    actual = preview(declared=calendar(["2026-01-23"]))
    assert actual["cycles"][0]["review_date"] == "2026-01-23"
    assert actual["calendar"]["source_verified"] is False
    assert "unverified" in actual["calendar"]["declaration"]


def test_calendar_future_knowledge_is_unavailable_without_leaking_candidates():
    actual = preview(declared=calendar(["2026-01-03"], known_at="2026-10-22T12:00:01+00:00"))
    assert actual["state"] == "unavailable"
    assert actual["reason_codes"] == ["CALENDAR_NOT_KNOWN_AT_AS_OF"]
    assert all(row["candidate_date"] is None for row in actual["cycles"])
    assert all(row["state"] == "unavailable" for row in actual["cycles"])


def test_equal_knowledge_time_with_different_offsets_is_allowed_for_future_dates():
    actual = preview(
        declared=calendar(
            ["2027-01-07"],
            first="2027-01-01",
            last="2027-12-31",
            known_at="2026-10-22T17:30:00+05:30",
        ),
        start=date(2027, 1, 1),
    )
    assert actual["cycles"][0]["review_date"] == "2027-01-07"
    assert actual["calendar"]["source_verified"] is False


@pytest.mark.parametrize(
    "missing",
    [
        "horizon_count",
        "horizon_unit",
        "review_cadence",
        "review_session_rule",
        "missed_cycle_policy",
    ],
)
@pytest.mark.parametrize("kind", ["absent", "null"])
def test_unresolved_parameters_are_explicit_without_defaults(missing, kind):
    config = parameters()
    if kind == "absent":
        del config[missing]
    else:
        config[missing] = None
    actual = preview(config)
    assert actual["state"] == "unavailable"
    assert actual["missing_fields"] == [missing]
    assert actual["reason_codes"] == ["MISSING_SCHEDULE_PARAMETERS"]
    assert actual["horizon_end"] is None
    assert actual["cycles"] == []


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("horizon_count", True),
        ("horizon_count", "2"),
        ("horizon_count", 2.0),
        ("horizon_count", 0),
        ("horizon_count", -1),
        ("horizon_unit", "days"),
        ("horizon_unit", ["months"]),
        ("review_cadence", "weekly"),
        ("review_cadence", True),
        ("review_session_rule", "first_session"),
        ("review_session_rule", ""),
        ("missed_cycle_policy", "catch_up"),
        ("missed_cycle_policy", False),
    ],
)
def test_invalid_schedule_parameter_types_and_enums_reject(field, value):
    with pytest.raises(ValueError):
        preview(parameters(**{field: value}))


def test_whole_canonical_draft_other_fields_do_not_change_schedule_or_mutate_input():
    config = parameters(capital_limit="10000.00", strategy_id="unexecuted-future-policy")
    declared = calendar(["2026-01-05", "2026-02-09"])
    before_config, before_calendar = deepcopy(config), deepcopy(declared)
    actual = preview(config, declared)
    assert list(actual["parameters"]) == [
        "horizon_count",
        "horizon_unit",
        "review_cadence",
        "review_session_rule",
        "missed_cycle_policy",
    ]
    assert config == before_config
    assert declared == before_calendar
    actual["parameters"]["horizon_count"] = 77
    assert config == before_config


def test_limit_returns_no_partial_schedule_instead_of_silently_truncating():
    actual = preview(parameters(horizon_count=401), calendar(first="2026-01-01", last="2060-12-31"))
    assert actual["state"] == "unavailable"
    assert actual["reason_codes"] == ["CYCLE_LIMIT_EXCEEDED"]
    assert actual["cycle_count"] == 401
    assert actual["cycles"] == []


def test_exact_cycle_limit_and_quarterly_multi_year_contract():
    declared = calendar(first="2026-01-01", last="2125-12-31")
    actual = preview(
        parameters(horizon_count=100, horizon_unit="years", review_cadence="quarterly"), declared
    )
    assert actual["state"] == "available"
    assert actual["cycle_count"] == len(actual["cycles"]) == 400
    assert actual["horizon_end"] == "2126-01-01"
    assert actual["required_coverage"]["coverage_end"] == "2125-12-31"
    midperiod = preview(parameters(horizon_count=400), declared, date(2026, 1, 15))
    assert midperiod["reason_codes"] == ["CYCLE_LIMIT_EXCEEDED"]
    assert midperiod["cycle_count"] == 401


def test_date_upper_boundary_has_explicit_unavailable_state():
    actual = preview(
        parameters(horizon_count=1, horizon_unit="years"),
        calendar(first="9999-01-01", last="9999-12-31"),
        date(9999, 1, 1),
    )
    assert actual["state"] == "unavailable"
    assert actual["reason_codes"] == ["HORIZON_END_OUT_OF_RANGE"]
    assert actual["cycles"] == []


@pytest.mark.parametrize(
    "changes",
    [
        {"coverage_start": "2026-1-01"},
        {"coverage_end": "2026-02-30"},
        {"coverage_start": "2027-01-01"},
        {"reference": "  "},
        {"reference": 42},
        {"reference": "x" * 501},
        {"known_at": "2026-01-01T00:00:00"},
        {"known_at": "2026-01-01"},
        {"known_at": None},
        {"known_at": "nonsenseT"},
        {"known_at": "2026-01-01T00:00:00+00:00" + "x" * 65},
        {"sessions": "2026-01-01"},
        {"sessions": ["2026-01-02", "2026-01-02"]},
        {"sessions": ["2026-01-03", "2026-01-02"]},
        {"sessions": ["2025-12-31"]},
        {"sessions": ["2027-01-01"]},
        {"sessions": [date(2026, 1, 2)]},
        {"sessions": ["2026-01-02"] * 5001},
        {"extra": True},
    ],
)
def test_calendar_schema_dates_bounds_knowledge_reference_and_size_are_strict(changes):
    with pytest.raises(ValueError):
        preview(declared=calendar(**changes))


def test_calendar_missing_declaration_field_is_invalid_even_with_missing_policy():
    declared = calendar()
    del declared["coverage_end"]
    with pytest.raises(ValueError):
        preview_schedule({}, date(2026, 1, 1), declared, AS_OF)


@pytest.mark.parametrize(
    ("config", "start", "as_of"),
    [
        ([], date(2026, 1, 1), AS_OF),
        (parameters(), "2026-01-01", AS_OF),
        (parameters(), datetime(2026, 1, 1, tzinfo=UTC), AS_OF),
        (parameters(), date(2026, 1, 1), datetime(2026, 1, 1)),
        (parameters(), date(2026, 1, 1), "2026-01-01T00:00:00+00:00"),
    ],
)
def test_invalid_clock_start_and_parameter_container_reject(config, start, as_of):
    with pytest.raises(ValueError):
        preview_schedule(config, start, calendar(), as_of)


def test_exact_session_limit_without_weekday_or_market_validation():
    first = date(2020, 1, 1)
    sessions = [(first + timedelta(days=i)).isoformat() for i in range(5000)]
    actual = preview(
        declared=calendar(
            sessions, first=sessions[0], last=sessions[-1], known_at="2020-01-01T00:00:00Z"
        ),
    )
    assert actual["state"] == "available"
    assert actual["cycles"][0]["review_date"] == "2026-01-01"
