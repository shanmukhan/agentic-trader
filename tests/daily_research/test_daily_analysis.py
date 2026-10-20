import hashlib
import json
from datetime import UTC, datetime, timedelta
from decimal import Decimal as D

import pytest

from trading_agent.daily_research.analysis import DailyPolicy, analyze, write_analysis
from trading_agent.daily_research.dashboard import render
from trading_agent.daily_research.dataset import DailyBar, DailyDataset, DailyManifest
from trading_agent.daily_research.demo import create_daily_demo, daily_research_demo


@pytest.fixture
def daily_bundle(tmp_path):
    directory = tmp_path / "daily"
    as_of = create_daily_demo(directory)
    return DailyDataset(directory), as_of


def revise(dataset, transform):
    rows = [json.loads(line) for line in dataset.bars_path.read_text().splitlines()]
    rows = transform(rows)
    dataset.bars_path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    return DailyDataset(dataset.directory)


def test_complete_daily_demo_reports_all_statuses_without_execution(tmp_path):
    report = daily_research_demo(tmp_path / "demo")
    states = {row["symbol"]: row for row in report["rows"]}
    assert report["candidate_count"] == 1 and states["NSE:TREND"]["rank"] == 1
    assert D(states["NSE:TREND"]["gross_total_return_pct"]) > 6
    assert states["NSE:TREND"]["observations"] == 90
    assert states["NSE:EXITED"]["status"] == "outside_universe"
    assert states["NSE:REENTRY"]["reasons"] == ["INSUFFICIENT_CONSECUTIVE_HISTORY"]
    assert states["NSE:REENTRY"]["observations"] == 15
    assert states["NSE:GAPPED"]["reasons"] == ["LATEST_SESSION_UNAVAILABLE_OR_MISSING"]
    assert "LOW_AVERAGE_TURNOVER" in states["NSE:THIN"]["reasons"]
    assert "NONPOSITIVE_MOMENTUM" in states["NSE:DECLINE"]["reasons"]
    assert not report["execution_simulated"] and not report["model_validated"]
    assert not report["ready_for_live"] and report["synthetic"]
    folder = tmp_path / "demo/report"
    manifest = json.loads((folder / "manifest.json").read_text())
    for name, expected in manifest["sha256"].items():
        assert hashlib.sha256((folder / name).read_bytes()).hexdigest() == expected
        assert (folder / name).stat().st_mode & 0o777 == 0o600


def test_future_valid_data_changes_no_as_of_features_or_ranks(daily_bundle):
    dataset, _ = daily_bundle
    as_of = datetime(2026, 7, 1, 11, tzinfo=UTC)
    before = analyze(dataset, DailyPolicy(), as_of)

    def future(rows):
        for row in rows:
            if row["session"] > "2026-07-01":
                row.update(
                    open="999", high="999", low="999", close="999", cash_per_previous_share="100"
                )
        return rows

    changed = revise(dataset, future)
    after = analyze(changed, DailyPolicy(), as_of)
    assert after["rows"] == before["rows"]
    assert after["candidate_count"] == before["candidate_count"]
    assert after["dataset"]["sha256"] != before["dataset"]["sha256"]


def test_reviewed_split_and_dividend_preserve_constant_gross_wealth(daily_bundle):
    dataset, as_of = daily_bundle

    def flat(rows):
        for row in rows:
            if row["symbol"] != "NSE:TREND":
                continue
            day = row["session"]
            raw = "100" if day < "2026-06-22" else "50" if day < "2026-07-27" else "48"
            row.update(open=raw, high=raw, low=raw, close=raw)
            row.update(
                share_numerator=2 if day == "2026-06-22" else 1,
                share_denominator=1,
                cash_per_previous_share="2" if day == "2026-07-27" else "0",
            )
        return rows

    dataset = revise(dataset, flat)
    report = analyze(dataset, DailyPolicy(momentum_sessions=60), as_of)
    row = next(row for row in report["rows"] if row["symbol"] == "NSE:TREND")
    assert D(row["index_level"]) == 100 and D(row["gross_total_return_pct"]) == 0
    assert D(row["daily_volatility_pct"]) == 0


@pytest.mark.parametrize("clock_field", ["price_available_at", "basis_reviewed_at"])
def test_late_price_or_basis_cannot_enter_current_screen(daily_bundle, clock_field):
    dataset, as_of = daily_bundle

    def late(rows):
        rows[-1][clock_field] = (as_of + timedelta(days=1)).isoformat()
        return rows

    dataset = revise(dataset, late)
    report = analyze(dataset, DailyPolicy(), as_of)
    row = next(row for row in report["rows"] if row["symbol"] == "NSE:TREND")
    assert row["status"] == "needs_data" and "gross_total_return_pct" not in row
    assert report["quality"]["unavailable_rows"] == 1


def test_missing_middle_session_restarts_only_affected_history(daily_bundle):
    dataset, as_of = daily_bundle
    dataset = revise(
        dataset,
        lambda rows: [
            row
            for row in rows
            if not (row["symbol"] == "NSE:TREND" and row["session"] == "2026-08-03")
        ],
    )
    report = analyze(dataset, DailyPolicy(), as_of)
    row = next(row for row in report["rows"] if row["symbol"] == "NSE:TREND")
    assert row["status"] == "needs_data" and row["observations"] < 50
    assert report["quality"]["window_resets_after_gaps"] >= 1


def test_empty_as_of_is_explicit_and_naive_clock_is_refused(daily_bundle):
    dataset, _ = daily_bundle
    report = analyze(dataset, DailyPolicy(), datetime(2026, 1, 1, tzinfo=UTC))
    assert report["rows"] == [] and report["latest_reviewed_completed_session"] is None
    assert report["candidate_count"] == 0
    with pytest.raises(ValueError, match="aware"):
        analyze(dataset, DailyPolicy(), datetime(2026, 10, 1))


@pytest.mark.parametrize(
    "mutation",
    [
        {"volume": True},
        {"close": "NaN"},
        {"close": "0"},
        {"high": "1"},
        {"share_numerator": True},
        {"share_denominator": 2},
        {"cash_per_previous_share": "-1"},
        {"price_available_at": "2026-05-04T09:00:00"},
        {"extra": "unreviewed"},
        {"basis_reference": "   "},
    ],
)
def test_daily_bar_contract_refuses_invalid_financial_input(daily_bundle, mutation):
    dataset, _ = daily_bundle
    row = json.loads(dataset.bars_path.read_text().splitlines()[0])
    with pytest.raises(ValueError):
        DailyBar.model_validate({**row, **mutation})


@pytest.mark.parametrize(
    "kind",
    ["duplicate", "reversed", "unknown_symbol", "before_close", "huge_line", "extra_json_key"],
)
def test_stream_validation_is_strict_and_never_fakes_a_report(daily_bundle, tmp_path, kind):
    dataset, as_of = daily_bundle
    rows = [json.loads(line) for line in dataset.bars_path.read_text().splitlines()]
    if kind == "duplicate":
        rows.insert(1, rows[0])
    if kind == "reversed":
        rows.reverse()
    if kind == "unknown_symbol":
        rows[0]["symbol"] = "NSE:UNKNOWN"
    if kind == "before_close":
        rows[0]["price_available_at"] = "2026-05-04T01:00:00Z"
    if kind == "huge_line":
        rows[0]["basis_reference"] = "x" * 65537
    dataset.bars_path.write_text("".join(json.dumps(row) + "\n" for row in rows))
    if kind == "extra_json_key":
        text = dataset.bars_path.read_text().replace(
            '"volume": 100000', '"volume": 100000, "volume": 1', 1
        )
        dataset.bars_path.write_text(text)
    dataset = DailyDataset(dataset.directory)
    with pytest.raises(ValueError):
        write_analysis(dataset, DailyPolicy(), as_of, tmp_path / "invalid-report")
    assert not (tmp_path / "invalid-report/manifest.json").exists()


@pytest.mark.parametrize(
    "kind", ["duplicate_session", "late_membership", "repeated_membership", "synthetic_integer"]
)
def test_universe_and_calendar_are_point_in_time_contracts(daily_bundle, kind):
    dataset, _ = daily_bundle
    payload = dataset.manifest.model_dump(mode="json")
    if kind == "duplicate_session":
        payload["sessions"].append(payload["sessions"][0])
    if kind == "late_membership":
        payload["universe"][0]["known_at"] = "2026-05-05T12:00:00Z"
    if kind == "repeated_membership":
        payload["universe"].append(payload["universe"][0])
    if kind == "synthetic_integer":
        payload["synthetic"] = 1
    with pytest.raises(ValueError):
        DailyManifest.model_validate(payload)


def test_changed_source_and_existing_output_fail_without_finished_manifest(
    daily_bundle, tmp_path, monkeypatch
):
    dataset, as_of = daily_bundle
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(ValueError):
        write_analysis(dataset, DailyPolicy(), as_of, existing)
    with pytest.raises(ValueError):
        write_analysis(dataset, DailyPolicy(), as_of, dataset.directory / "nested")
    monkeypatch.setattr(dataset, "fingerprints", lambda: {})
    with pytest.raises(RuntimeError, match="changed"):
        write_analysis(dataset, DailyPolicy(), as_of, tmp_path / "mutated")
    assert not (tmp_path / "mutated/manifest.json").exists()


def test_symlinked_daily_source_is_not_followed(daily_bundle):
    dataset, _ = daily_bundle
    original = dataset.bars_path.rename(dataset.directory / "elsewhere.jsonl")
    dataset.bars_path.symlink_to(original)
    with pytest.raises(ValueError, match="bounded regular"):
        DailyDataset(dataset.directory)


def test_offline_html_escapes_untrusted_references_and_binds_csp(daily_bundle):
    dataset, as_of = daily_bundle
    report = analyze(dataset, DailyPolicy(), as_of)
    report["dataset"]["source"] = '</script><img src=x onerror="attack()">{{SCRIPT}}'
    html = render(report)
    assert "</script><img" not in html and "\\u003c/script" in html
    assert "Content-Security-Policy" in html and "script-src 'sha256-" in html
    assert 'aria-live="polite"' in html and 'tabindex="0"' in html
    assert "fetch(" not in html and "innerHTML" not in html
