"""Synthetic reviewed sessions; display guidance never changes financial authority."""

from datetime import date, datetime, time

import pytest

from trading_agent.desk.mode_guidance import mode_guidance
from trading_agent.market_data.calendar import IST

DAY = date(2026, 10, 29)
SESSIONS = {DAY: (time(9, 15), time(15, 30)), date(2026, 10, 30): (time(9, 15), time(15, 30))}


def guide(hour, minute, blockers, sessions=None):
    return mode_guidance(
        datetime(2026, 10, 29, hour, minute, tzinfo=IST),
        blockers,
        SESSIONS if sessions is None else sessions,
        time(9, 30),
        time(14, 30),
    )


@pytest.mark.parametrize("hour,minute", [(7, 45), (9, 15), (9, 29)])
def test_before_entry_names_actual_reviewed_start_not_socket_or_market_open(hour, minute):
    result = guide(hour, minute, ["OUTSIDE_ENTRY_WINDOW", "NO_FRESH_EXECUTION_QUOTES"])
    assert result["next_entry_at"] == "2026-10-29T09:30:00+05:30"
    assert result["state"] == "waiting"
    assert result["automatic_start"] is False
    assert result["entry_window"] == "09:30–14:30 IST"


def test_open_entry_waits_for_quotes_without_sending_user_to_tomorrow():
    result = guide(9, 30, ["NO_FRESH_EXECUTION_QUOTES"])
    assert result["next_entry_at"] is None
    assert result["title"] == "Waiting for usable market data"
    assert result["items"][0]["target"] == "broker"


def test_after_entry_cutoff_uses_next_reviewed_day_and_does_not_guess_missing_dates():
    result = guide(14, 30, ["OUTSIDE_ENTRY_WINDOW"])
    assert result["next_entry_at"] == "2026-10-30T09:30:00+05:30"
    result = guide(16, 0, ["OUTSIDE_ENTRY_WINDOW"], {DAY: SESSIONS[DAY]})
    assert result["next_entry_at"] is None
    assert result["state"] == "action_required"
    assert result["items"][-1]["code"] == "NEXT_SESSION_REVIEW_REQUIRED"


def test_special_session_intersects_entry_window_and_excludes_empty_intersections():
    result = guide(7, 0, ["OUTSIDE_ENTRY_WINDOW"], {DAY: (time(11), time(13))})
    assert result["next_entry_at"] == "2026-10-29T11:00:00+05:30"
    result = guide(7, 0, ["OUTSIDE_ENTRY_WINDOW"], {DAY: (time(15), time(16))})
    assert result["next_entry_at"] is None
    assert result["state"] == "action_required"


def test_missing_review_is_an_action_even_when_the_clock_says_market_hours():
    result = guide(10, 0, ["UNKNOWN_OR_CLOSED_SESSION"], {})
    assert result["state"] == "action_required"
    assert result["next_entry_at"] is None
    assert result["items"][0]["target"] == "broker"


def test_all_blockers_have_actionable_or_waiting_explanations_and_unknown_codes_fail_closed():
    blockers = [
        "FEED_DISCONNECTED",
        "KILL_SWITCH",
        "LONG_TERM_REVIEW_REQUIRED",
        "NO_EXECUTION_SHORTLIST",
        "STRATEGY_INSTALLING",
        "FUTURE_UNKNOWN_GATE",
    ]
    result = guide(10, 0, blockers)
    assert {row["code"] for row in result["items"]} == set(blockers)
    assert result["state"] == "action_required"
    assert result["automatic_start"] is False
    assert {row["target"] for row in result["items"]} >= {"broker", "risk", "strategy"}
    ready = guide(10, 0, [])
    assert ready["state"] == "ready" and ready["items"] == []
    assert ready["next_entry_at"] is None and ready["automatic_start"] is False
