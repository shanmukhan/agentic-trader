"""Invented calendar declarations; actual CLI I/O without account/network effects."""

import hashlib
import json
import os
import socket
import subprocess
import sys
from datetime import UTC, date, datetime

import pytest

from trading_agent.investment_research.policy_cli import inspect_policy_file


@pytest.fixture
def inputs(tmp_path):
    draft = tmp_path / "draft.json"
    draft.write_text(
        json.dumps(
            {
                "label": "INVENTED month-end plan",
                "parameters": {
                    "horizon_unit": "months",
                    "horizon_count": 3,
                    "review_cadence": "monthly",
                    "review_session_rule": "last_reviewed_session",
                    "missed_cycle_policy": "skip",
                    "min_average_turnover": "999999999999.99",
                },
            }
        )
    )
    calendar = tmp_path / "calendar.json"
    calendar.write_text(
        json.dumps(
            {
                "coverage_start": "2026-10-01",
                "coverage_end": "2027-01-31",
                "sessions": [
                    "2026-10-01",
                    "2026-10-30",
                    "2026-11-02",
                    "2026-11-30",
                    "2026-12-01",
                    "2026-12-31",
                    "2027-01-04",
                    "2027-01-29",
                ],
                "known_at": "2026-10-20T00:00:00Z",
                "reference": "INVENTED sparse complete calendar assertion",
            }
        )
    )
    return draft, calendar


def test_actual_cli_reports_exact_choices_calendar_dates_hashes_without_account_creation(
    tmp_path, inputs
):
    draft, calendar = inputs
    account = tmp_path / "operator.sqlite3"
    config = tmp_path / "operator.toml"
    config.write_text(f"database = {json.dumps(str(account))}\n")
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "trading_agent.main",
            "--config",
            str(config),
            "investment-policy",
            str(draft),
            "--calendar",
            str(calendar),
            "--start",
            "2026-10-31",
            "--as-of",
            "2026-10-22T00:00:00Z",
        ],
        capture_output=True,
        text=True,
        check=True,
        env={key: value for key, value in os.environ.items() if not key.startswith("TRADING_")},
    )
    output = json.loads(result.stdout)
    assert output["draft"]["parameters"]["min_average_turnover"] == "999999999999.99"
    assert output["draft"]["parameters"]["cash_reserve_pct"] is None
    assert output["draft"]["activation_supported"] is False
    schedule = output["schedule"]
    assert schedule["horizon_end"] == "2027-01-31"
    assert [row["review_date"] for row in schedule["cycles"]] == [
        None,
        "2026-11-30",
        "2026-12-31",
        "2027-01-29",
    ]
    assert schedule["cycles"][0]["reason_codes"] == ["CANDIDATE_BEFORE_START_SKIP"]
    assert schedule["calendar"]["source_verified"] is False
    assert output["input_sha256"] == {
        "draft": hashlib.sha256(draft.read_bytes()).hexdigest(),
        "calendar": hashlib.sha256(calendar.read_bytes()).hexdigest(),
    }
    assert output["account_changed"] is output["execution_authorized"] is False
    assert {path.name: path.read_bytes() for path in tmp_path.iterdir()} == before
    assert not account.exists() and not account.with_suffix(".investment-policies").exists()


def test_inspection_has_no_network_and_does_not_invent_missing_schedule_or_values(
    inputs, monkeypatch
):
    draft, calendar = inputs

    def prohibited(*args, **kwargs):
        pytest.fail("policy inspection must not use network transport")

    monkeypatch.setattr(socket, "socket", prohibited)
    before = draft.read_bytes(), calendar.read_bytes()
    result = inspect_policy_file(draft)
    assert result["schedule"] is None
    assert result["draft"]["policy_version_id"] is None
    result = inspect_policy_file(
        draft, calendar, date(2026, 10, 31), datetime(2026, 10, 22, tzinfo=UTC)
    )
    assert result["schedule"]["state"] == "available"
    assert (draft.read_bytes(), calendar.read_bytes()) == before


@pytest.mark.parametrize(
    "flags",
    ["calendar", "start", "as_of", "naive", "duplicate", "bad_decimal", "oversized", "symlink"],
)
def test_invalid_cli_inspection_returns_no_success_or_new_files(inputs, tmp_path, flags):
    draft, calendar = inputs
    args = {}
    if flags == "calendar":
        args["calendar"] = calendar
    elif flags == "start":
        args["start"] = date(2026, 10, 31)
    elif flags == "as_of":
        args["as_of"] = datetime(2026, 10, 22, tzinfo=UTC)
    elif flags == "naive":
        args.update(calendar=calendar, start=date(2026, 10, 31), as_of=datetime(2026, 10, 22))
    elif flags == "duplicate":
        draft.write_text('{"parameters":{},"parameters":{}}')
    elif flags == "bad_decimal":
        draft.write_text('{"parameters":{"cash_reserve_pct":1.25}}')
    elif flags == "oversized":
        draft.write_bytes(b" " * (32 * 1024 + 1))
    else:
        alias = tmp_path / "alias.json"
        alias.symlink_to(draft)
        draft = alias
    before = set(tmp_path.iterdir())
    with pytest.raises((ValueError, OSError)):
        inspect_policy_file(draft, **args)
    assert set(tmp_path.iterdir()) == before
