"""Invented source fixtures validate research arithmetic, never external acceptance."""

import hashlib
import json
from datetime import date, datetime, time, timedelta
from decimal import ROUND_DOWN, Decimal, Inexact, localcontext
from pathlib import Path
from typing import Any

import pytest

from trading_agent.backtesting.dataset import Session
from trading_agent.daily_research.dataset import DailyBar, DailyDataset, DailyManifest, Membership
from trading_agent.investment_research import series
from trading_agent.investment_research.series import series_snapshot, write_series_report
from trading_agent.market_data.calendar import IST
from trading_agent.models import stamp

D = Decimal
SYMBOL = "NSE:SYNTHETIC"
REVIEWED_DAYS = [
    "2025-01-06",
    "2025-01-07",
    "2025-01-08",
    "2025-01-09",
    "2025-01-10",
    "2025-01-13",
    "2025-01-14",
    "2025-01-15",
    "2025-01-16",
    "2025-01-17",
    "2025-01-20",
    "2025-01-21",
    "2025-01-22",
    "2025-01-23",
    "2025-01-24",
    "2025-01-27",
    "2025-01-28",
    "2025-01-29",
    "2025-01-30",
    "2025-01-31",
    "2025-02-03",
    "2025-02-04",
    "2025-02-05",
    "2025-02-06",
    "2025-02-07",
    "2025-02-10",
    "2025-02-11",
    "2025-02-12",
    "2025-02-13",
    "2025-02-14",
]


def clock(day: str | date, value: str = "16:00:00") -> datetime:
    return datetime.combine(
        date.fromisoformat(day) if isinstance(day, str) else day, time.fromisoformat(value), IST
    )


def create_daily_dataset(
    directory: Path,
    days: list[str],
    *,
    changes: dict[int, dict[str, Any]] | None = None,
    omitted: set[int] | None = None,
    membership: list[tuple[int, bool]] | None = None,
    closes: dict[int, str] | None = None,
) -> DailyDataset:
    directory.mkdir()
    sessions = tuple(
        Session(
            day=date.fromisoformat(day),
            open=time(9, 15),
            close=time.fromisoformat((closes or {}).get(index, "15:30:00")),
            source="Invented explicitly reviewed session; not an exchange source",
        )
        for index, day in enumerate(days)
    )
    manifest = DailyManifest(
        source="Synthetic Phase 4 arithmetic fixture",
        notes="Invented prices and calendar; no broker, external completeness or market acceptance",
        synthetic=True,
        sessions=sessions,
        universe=tuple(
            Membership(
                symbol=SYMBOL,
                effective_session=sessions[index].day,
                included=included,
                known_at=clock(days[index], "08:00:00"),
                reference="Synthetic membership review",
            )
            for index, included in membership or [(0, True)]
        ),
    )
    records = []
    for index, session in enumerate(sessions):
        if index in (omitted or set()):
            continue
        close = datetime.combine(session.day, session.close, IST)
        values = dict(
            symbol=SYMBOL,
            session=session.day,
            open=D(100 + index),
            high=D(103 + index),
            low=D(97 + index),
            close=D(101 + index),
            volume=10 * (index + 1),
            price_available_at=close + timedelta(minutes=1),
            basis_reviewed_at=close + timedelta(minutes=2),
            basis_reference="Invented reviewed no-action or supported benefit terms",
            share_numerator=1,
            share_denominator=1,
            cash_per_previous_share=D(0),
        )
        values.update((changes or {}).get(index, {}))
        records.append(DailyBar(**values))
    (directory / "manifest.json").write_text(manifest.model_dump_json(), encoding="utf-8")
    (directory / "daily.jsonl").write_text(
        "".join(record.model_dump_json() + "\n" for record in records), encoding="utf-8"
    )
    return DailyDataset(directory)


def write_context(
    dataset: DailyDataset,
    start: str,
    end: str,
    available_at: datetime,
    **changes: Any,
) -> Path:
    payload = {
        "schema_version": 1,
        "dataset_sha256": dataset.hashes,
        "calendar": {
            "start": start,
            "end": end,
            "available_at": stamp(available_at),
            "reference": "Synthetic explicit completeness assertion; not external certification",
            "completeness_reviewed": True,
        },
    }
    payload.update(changes)
    target = dataset.directory / "investment-context.json"
    target.write_text(json.dumps(payload), encoding="utf-8")
    return target


def saved_inputs(dataset: DailyDataset) -> dict[str, bytes]:
    return {path.name: path.read_bytes() for path in dataset.directory.iterdir() if path.is_file()}


def test_daily_close_price_and_basis_availability_boundaries(tmp_path: Path):
    dataset = create_daily_dataset(tmp_path / "daily", REVIEWED_DAYS[:3])
    before = saved_inputs(dataset)
    assert not series_snapshot(dataset, SYMBOL, clock(REVIEWED_DAYS[0], "15:29:59"))["bars"]
    assert not series_snapshot(dataset, SYMBOL, clock(REVIEWED_DAYS[0], "15:31:59"))["bars"]
    result = series_snapshot(dataset, SYMBOL, clock(REVIEWED_DAYS[0], "15:32:00"))
    assert len(result["bars"]) == 1
    first = result["bars"][0]
    assert first["session"] == REVIEWED_DAYS[0]
    assert first["time"] == stamp(clock(REVIEWED_DAYS[0], "15:30:00"))
    assert first["available_at"] == stamp(clock(REVIEWED_DAYS[0], "15:32:00"))
    assert first["indicator_available_at"] == first["available_at"]
    assert D(first["total_return_index"]) == 100 and first["segment_break"] is True
    assert result["research"]["coverage"]["calendar_verified"] is False
    assert result["source"]["synthetic"] is True
    assert saved_inputs(dataset) == before


def test_membership_exclusion_and_reentry_reset_all_evidence(tmp_path: Path):
    dataset = create_daily_dataset(
        tmp_path / "daily", REVIEWED_DAYS, membership=[(0, True), (12, False), (15, True)]
    )
    result = series_snapshot(dataset, SYMBOL, clock(REVIEWED_DAYS[-1]))
    rows = result["bars"]
    assert [row["session"] for row in rows] == REVIEWED_DAYS[:12] + REVIEWED_DAYS[15:]
    reentry = rows[12]
    assert reentry["session"] == REVIEWED_DAYS[15]
    assert reentry["segment_break"] is True
    assert D(reentry["total_return_index"]) == 100
    assert reentry["ema12"] is None and reentry["atr14"] is None
    assert rows[-1]["rsi14"] is not None
    assert rows[-1]["sma20"] is None


@pytest.mark.parametrize("missing_kind", ["missing", "price_late", "basis_late"])
def test_missing_or_unavailable_reviewed_session_breaks_instead_of_bridging(
    tmp_path: Path, missing_kind: str
):
    changes = {}
    omitted = set()
    if missing_kind == "missing":
        omitted.add(13)
    else:
        field = "price_available_at" if missing_kind == "price_late" else "basis_reviewed_at"
        changes[13] = {field: clock("2025-03-03")}
    dataset = create_daily_dataset(
        tmp_path / "daily", REVIEWED_DAYS, changes=changes, omitted=omitted
    )
    before = saved_inputs(dataset)
    result = series_snapshot(dataset, SYMBOL, clock(REVIEWED_DAYS[-1]))
    rows = result["bars"]
    assert REVIEWED_DAYS[13] not in [row["session"] for row in rows]
    after_gap = next(row for row in rows if row["session"] == REVIEWED_DAYS[14])
    assert after_gap["segment_break"] is True
    assert D(after_gap["total_return_index"]) == 100
    assert after_gap["ema12"] is None and after_gap["atr14"] is None
    assert rows[-1]["sma20"] is None
    assert saved_inputs(dataset) == before


def test_known_split_adjusts_all_ohlc_and_inverse_volume_cash_only_changes_tri(tmp_path: Path):
    dataset = create_daily_dataset(
        tmp_path / "daily",
        REVIEWED_DAYS[:3],
        changes={
            0: dict(open="100", high="110", low="90", close="100", volume=10),
            1: dict(
                open="49",
                high="51",
                low="48",
                close="49",
                volume=20,
                share_numerator=2,
                cash_per_previous_share="2",
            ),
            2: dict(
                open="48", high="50", low="47", close="48", volume=30, cash_per_previous_share="1"
            ),
        },
    )
    original = saved_inputs(dataset)
    before_split = series_snapshot(dataset, SYMBOL, clock(REVIEWED_DAYS[0]))["bars"]
    assert D(before_split[0]["close"]) == 100
    rows = series_snapshot(dataset, SYMBOL, clock(REVIEWED_DAYS[2]))["bars"]
    assert [D(rows[0][key]) for key in ("open", "high", "low", "close", "volume")] == [
        50,
        55,
        45,
        50,
        20,
    ]
    assert [D(rows[0]["raw_" + key]) for key in ("open", "high", "low", "close")] == [
        100,
        110,
        90,
        100,
    ]
    assert rows[0]["raw_volume"] == 10
    assert [D(row["close"]) for row in rows] == [50, 49, 48]
    assert [D(row["volume"]) for row in rows] == [20, 20, 30]
    assert [D(row["total_return_index"]) for row in rows] == [100, 100, 100]
    assert [D(row["drawdown_pct"]) for row in rows] == [0, -2, -4]
    # Prior adjusted OHLC is available only when that later share action is known.
    assert rows[0]["available_at"] == stamp(clock(REVIEWED_DAYS[1], "15:32:00"))
    # Gross-return history uses its own causal dependency clock, not chart restatement clocks.
    assert rows[0]["tri_available_at"] == stamp(clock(REVIEWED_DAYS[0], "15:32:00"))
    assert rows[2]["tri_available_at"] == stamp(clock(REVIEWED_DAYS[2], "15:32:00"))
    assert saved_inputs(dataset) == original


def test_later_split_never_adjusts_a_separate_history_segment(tmp_path: Path):
    dataset = create_daily_dataset(
        tmp_path / "daily",
        REVIEWED_DAYS[:5],
        omitted={2},
        changes={
            4: dict(open="52", high="54", low="50", close="53", share_numerator=2),
        },
    )
    rows = series_snapshot(dataset, SYMBOL, clock(REVIEWED_DAYS[4]))["bars"]
    assert [D(row["close"]) for row in rows] == [101, 102, D("52"), 53]
    assert rows[2]["segment_break"] is True
    assert rows[0]["available_at"] == stamp(clock(REVIEWED_DAYS[0], "15:32:00"))
    assert rows[2]["available_at"] == stamp(clock(REVIEWED_DAYS[4], "15:32:00"))


def test_valid_future_price_action_and_availability_perturbation_preserve_prior_bars(
    tmp_path: Path,
):
    original = create_daily_dataset(tmp_path / "first", REVIEWED_DAYS)
    changed = create_daily_dataset(
        tmp_path / "second",
        REVIEWED_DAYS,
        changes={
            29: dict(
                open="500",
                high="600",
                low="400",
                close="550",
                volume=999999,
                share_numerator=3,
                cash_per_previous_share="3",
                basis_reviewed_at=clock("2025-03-03"),
            ),
        },
    )
    as_of = clock(REVIEWED_DAYS[26])
    first = series_snapshot(original, SYMBOL, as_of)
    second = series_snapshot(changed, SYMBOL, as_of)
    assert first["bars"] == second["bars"]
    assert first["research"]["indicator_status"] == second["research"]["indicator_status"]


def test_weekly_ohlcv_with_holidays_early_close_and_cross_year_coverage(tmp_path: Path):
    days = ["2025-12-29", "2025-12-30", "2026-01-02"]
    dataset = create_daily_dataset(
        tmp_path / "daily",
        days,
        closes={2: "13:00:00"},
        changes={
            0: dict(open="100", high="110", low="90", close="105", volume=10),
            1: dict(open="105", high="120", low="100", close="108", volume=20),
            2: dict(open="108", high="119", low="104", close="116", volume=30),
        },
    )
    known = clock(days[2], "13:03:00")
    write_context(dataset, "2025-12-29", "2026-01-04", known)
    before = saved_inputs(dataset)
    result = series_snapshot(dataset, SYMBOL, known, timeframe="1w")
    assert result["research"]["partial_periods"] == []
    assert len(result["bars"]) == 1
    row = result["bars"][0]
    assert row["period"] == "2025-12-29" and row["session"] == "2026-01-02"
    assert row["time"] == stamp(clock(days[2], "13:00:00"))
    assert [D(row[key]) for key in ("open", "high", "low", "close", "volume")] == [
        100,
        120,
        90,
        116,
        60,
    ]
    assert row["observations"] == 3 and row["partial"] is False
    assert row["available_at"] == stamp(known)
    assert result["research"]["coverage"]["calendar_verified"] is True
    assert saved_inputs(dataset) == before


def test_share_adjustment_happens_before_weekly_ohlcv_aggregation(tmp_path: Path):
    days = REVIEWED_DAYS[:3]
    dataset = create_daily_dataset(
        tmp_path / "daily",
        days,
        changes={
            0: dict(open="100", high="110", low="90", close="100", volume=10),
            1: dict(open="50", high="55", low="45", close="52", volume=20, share_numerator=2),
            2: dict(open="52", high="60", low="50", close="58", volume=30),
        },
    )
    write_context(dataset, "2025-01-06", "2025-01-12", clock(days[-1]))
    result = series_snapshot(dataset, SYMBOL, clock(days[-1]), timeframe="1w")
    assert len(result["bars"]) == 1
    assert [D(result["bars"][0][key]) for key in ("open", "high", "low", "close", "volume")] == [
        50,
        60,
        45,
        58,
        70,
    ]


def test_monthly_ohlcv_uses_reviewed_month_end_not_weekday_guess(tmp_path: Path):
    days = [
        "2025-11-03",
        "2025-11-04",
        "2025-11-06",
        "2025-11-07",
        "2025-11-10",
        "2025-11-11",
        "2025-11-12",
        "2025-11-13",
        "2025-11-14",
        "2025-11-17",
        "2025-11-18",
        "2025-11-19",
        "2025-11-20",
        "2025-11-21",
        "2025-11-24",
        "2025-11-25",
        "2025-11-26",
        "2025-11-27",
        "2025-11-28",
    ]
    dataset = create_daily_dataset(tmp_path / "daily", days, closes={18: "13:00:00"})
    write_context(dataset, "2025-11-01", "2025-11-30", clock(days[0], "08:00:00"))
    result = series_snapshot(dataset, SYMBOL, clock(days[-1], "13:03:00"), timeframe="1mo")
    assert len(result["bars"]) == 1
    row = result["bars"][0]
    assert row["period"] == "2025-11" and row["session"] == "2025-11-28"
    assert [D(row[key]) for key in ("open", "high", "low", "close", "volume")] == [
        100,
        121,
        97,
        119,
        1900,
    ]
    assert row["observations"] == 19
    assert row["time"] == stamp(clock(days[-1], "13:00:00"))


def test_month_boundary_keeps_separate_periods_and_actual_last_session_labels(tmp_path: Path):
    days = ["2025-01-30", "2025-01-31", "2025-02-03", "2025-02-28"]
    dataset = create_daily_dataset(tmp_path / "daily", days)
    write_context(dataset, "2025-01-01", "2025-02-28", clock(days[0], "08:00:00"))
    rows = series_snapshot(dataset, SYMBOL, clock(days[-1]), timeframe="1mo")["bars"]
    assert [row["period"] for row in rows] == ["2025-01", "2025-02"]
    assert [row["session"] for row in rows] == ["2025-01-31", "2025-02-28"]
    assert [row["observations"] for row in rows] == [2, 2]
    assert [D(row["volume"]) for row in rows] == [30, 70]


@pytest.mark.parametrize(
    "mode, reason",
    [
        ("none", "CALENDAR_COVERAGE_UNVERIFIED"),
        ("midweek_start", "CALENDAR_COVERAGE_UNVERIFIED"),
        ("short_end", "CALENDAR_COVERAGE_UNVERIFIED"),
        ("future_review", "CALENDAR_COVERAGE_UNVERIFIED"),
        ("current", "PERIOD_NOT_COMPLETE"),
        ("missing", "PERIOD_INPUT_MISSING_OR_UNAVAILABLE"),
    ],
)
def test_partial_incomplete_or_unverified_periods_cannot_emit_a_complete_bar(
    tmp_path: Path, mode: str, reason: str
):
    dataset = create_daily_dataset(
        tmp_path / "daily", REVIEWED_DAYS[:5], omitted={2} if mode == "missing" else None
    )
    as_of = clock(REVIEWED_DAYS[2]) if mode == "current" else clock(REVIEWED_DAYS[4])
    if mode != "none":
        write_context(
            dataset,
            "2025-01-08" if mode == "midweek_start" else "2025-01-06",
            "2025-01-10" if mode == "short_end" else "2025-01-12",
            clock("2025-01-13") if mode == "future_review" else clock("2025-01-06", "08:00:00"),
        )
    result = series_snapshot(dataset, SYMBOL, as_of, timeframe="1w")
    assert result["bars"] == []
    assert result["research"]["partial_periods"][0]["reason"] == reason
    assert result["data_state"] == "missing"


def test_matching_omission_from_rows_and_manifest_does_not_prove_calendar_completeness(
    tmp_path: Path,
):
    # Neither source contains Tuesday. Equality alone cannot prove a holiday.
    dataset = create_daily_dataset(tmp_path / "daily", ["2025-01-06", "2025-01-08", "2025-01-10"])
    result = series_snapshot(dataset, SYMBOL, clock("2025-01-10"), timeframe="1w")
    assert result["bars"] == []
    assert result["research"]["coverage"]["calendar_verified"] is False
    assert "no dates are guessed" in result["research"]["coverage"]["detail"]


def test_missing_middle_period_resets_recursive_weekly_seed(tmp_path: Path):
    dataset = create_daily_dataset(tmp_path / "daily", REVIEWED_DAYS[:15], omitted={6})
    write_context(dataset, "2025-01-06", "2025-01-26", clock("2025-01-06", "08:00:00"))
    result = series_snapshot(dataset, SYMBOL, clock(REVIEWED_DAYS[14]), timeframe="1w")
    assert [row["period"] for row in result["bars"]] == ["2025-01-06", "2025-01-20"]
    assert [row["segment_break"] for row in result["bars"]] == [True, True]
    assert result["research"]["partial_periods"][0]["period"] == "2025-01-13"


@pytest.mark.parametrize("kind", ["mismatch", "duplicate", "symlink"])
def test_context_identity_duplicate_or_symlink_rejected_without_mutation(tmp_path: Path, kind: str):
    dataset = create_daily_dataset(tmp_path / "daily", REVIEWED_DAYS[:5])
    path = write_context(dataset, "2025-01-06", "2025-01-12", clock("2025-01-06", "08:00:00"))
    if kind == "mismatch":
        payload = json.loads(path.read_text())
        payload["dataset_sha256"]["daily.jsonl"] = "0" * 64
        path.write_text(json.dumps(payload))
    elif kind == "duplicate":
        path.write_text(
            path.read_text().replace(
                '"schema_version": 1,', '"schema_version": 1, "schema_version": 1,'
            )
        )
    else:
        target = tmp_path / "real-context.json"
        path.rename(target)
        path.symlink_to(target)
    before = saved_inputs(dataset)
    with pytest.raises(ValueError):
        series_snapshot(dataset, SYMBOL, clock(REVIEWED_DAYS[-1]), timeframe="1w")
    assert saved_inputs(dataset) == before


def test_duplicate_daily_row_is_not_a_second_observation(tmp_path: Path):
    original = create_daily_dataset(tmp_path / "daily", REVIEWED_DAYS[:3])
    path = original.directory / "daily.jsonl"
    lines = path.read_text().splitlines()
    path.write_text("\n".join([lines[0], lines[0], *lines[1:]]) + "\n")
    dataset = DailyDataset(original.directory)
    before = saved_inputs(dataset)
    with pytest.raises(ValueError, match="strict date-symbol order"):
        series_snapshot(dataset, SYMBOL, clock(REVIEWED_DAYS[-1]))
    assert saved_inputs(dataset) == before


def test_input_content_mutation_and_symlink_are_detected(tmp_path: Path):
    dataset = create_daily_dataset(tmp_path / "daily", REVIEWED_DAYS[:3])
    path = dataset.directory / "daily.jsonl"
    original = path.read_bytes()
    path.write_bytes(original + b"\n")
    with pytest.raises(ValueError, match="input changed"):
        series_snapshot(dataset, SYMBOL, clock(REVIEWED_DAYS[-1]))
    path.write_bytes(original)
    target = tmp_path / "real-daily.jsonl"
    path.rename(target)
    path.symlink_to(target)
    with pytest.raises(ValueError, match="path changed"):
        series_snapshot(dataset, SYMBOL, clock(REVIEWED_DAYS[-1]))


@pytest.mark.parametrize("value", [False, 0, 1, "true", "false", None])
def test_calendar_completeness_requires_actual_boolean_true(tmp_path: Path, value: Any):
    dataset = create_daily_dataset(tmp_path / "daily", REVIEWED_DAYS[:5])
    path = write_context(dataset, "2025-01-06", "2025-01-12", clock("2025-01-06", "08:00:00"))
    context = json.loads(path.read_text())
    context["calendar"]["completeness_reviewed"] = value
    path.write_text(json.dumps(context))
    before = saved_inputs(dataset)
    with pytest.raises(ValueError):
        series_snapshot(dataset, SYMBOL, clock(REVIEWED_DAYS[-1]), timeframe="1w")
    assert saved_inputs(dataset) == before


def test_future_context_does_not_read_or_activate_benchmark_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    dataset = create_daily_dataset(tmp_path / "daily", REVIEWED_DAYS[:5])
    write_context(
        dataset,
        "2025-01-06",
        "2025-01-12",
        clock("2025-01-13"),
        benchmark_file="investment-benchmark.json",
        benchmark_sha256="0" * 64,
    )

    def forbidden(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("A future benchmark binding cannot be read or activated")

    monkeypatch.setattr(series, "load_benchmark", forbidden)
    result = series_snapshot(dataset, SYMBOL, clock(REVIEWED_DAYS[4]))
    assert result["bars"]
    assert result["research"]["benchmark"]["reason"] == "CONTEXT_NOT_YET_AVAILABLE"
    assert result["research"]["inputs"]["benchmark_sha256"] is None


def test_series_is_independent_of_ambient_decimal_context_and_never_changes_it(tmp_path: Path):
    dataset = create_daily_dataset(
        tmp_path / "daily",
        REVIEWED_DAYS,
        changes={
            18: dict(share_numerator=3, share_denominator=2, cash_per_previous_share="1.25"),
        },
    )
    expected = series_snapshot(dataset, SYMBOL, clock(REVIEWED_DAYS[-1]))
    before = saved_inputs(dataset)
    manifest = dataset.manifest.model_dump_json()
    hashes = dict(dataset.hashes)
    with localcontext() as context:
        context.prec = 6
        context.rounding = ROUND_DOWN
        context.traps[Inexact] = True
        original = context.copy()
        assert series_snapshot(dataset, SYMBOL, clock(REVIEWED_DAYS[-1])) == expected
        assert context.prec == original.prec and context.rounding == original.rounding
        assert context.flags == original.flags and context.traps == original.traps
    assert dataset.manifest.model_dump_json() == manifest
    assert dataset.hashes == hashes and saved_inputs(dataset) == before


def test_report_persists_exact_snapshot_and_independent_hashes_outside_source(tmp_path: Path):
    dataset = create_daily_dataset(tmp_path / "daily", REVIEWED_DAYS[:3])
    before = saved_inputs(dataset)
    output = tmp_path / "report"
    result = write_series_report(dataset, SYMBOL, clock(REVIEWED_DAYS[-1]), output)
    assert json.loads((output / "report.json").read_text()) == result
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["state"] == "finished" and manifest["ready_for_live"] is False
    assert manifest["execution_simulated"] is False
    assert manifest["sha256"] == {
        name: hashlib.sha256((output / name).read_bytes()).hexdigest()
        for name in ("report.json", "report.md")
    }
    assert saved_inputs(dataset) == before
    with pytest.raises(ValueError, match="new directory"):
        write_series_report(dataset, SYMBOL, clock(REVIEWED_DAYS[-1]), output)
    with pytest.raises(ValueError, match="outside its daily source"):
        write_series_report(dataset, SYMBOL, clock(REVIEWED_DAYS[-1]), dataset.directory / "nested")
