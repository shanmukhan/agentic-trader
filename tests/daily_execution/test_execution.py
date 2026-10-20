import json
import sqlite3
from contextlib import closing
from datetime import datetime, timedelta
from decimal import Decimal

import pytest

from trading_agent.daily_execution.contracts import DailySample, DailyStrategy, DailyVector
from trading_agent.daily_execution.dataset import ExecutionDataset, QuoteEvent
from trading_agent.daily_execution.runner import run_daily
from trading_agent.daily_execution.runtime import TradingClock
from trading_agent.daily_execution.timeline import DailyTimeline
from trading_agent.daily_research.dataset import DailyDataset
from trading_agent.market_data.calendar import IST
from trading_agent.persistence.database import Database
from trading_agent.settings import Settings

D = Decimal


def events(path):
    return [json.loads(line) for line in (path / "events.jsonl").read_text().splitlines()]


def write_events(path, rows):
    (path / "events.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))


def replay(execution_inputs, tmp_path, daily_policy, daily_strategy, rows=None, *, labels=False):
    daily, execution, _ = execution_inputs
    if rows is not None:
        write_events(execution, rows)
    return run_daily(
        ExecutionDataset(execution, DailyDataset(daily)),
        strategy=daily_strategy,
        policy=daily_policy,
        output=tmp_path / "result",
        labels=labels,
    )


def test_delivery_replay_exact_ledger_later_fills_and_private_artifacts(
    execution_inputs, tmp_path, daily_policy, daily_strategy
):
    before = daily_policy.database.exists()
    report = replay(execution_inputs, tmp_path, daily_policy, daily_strategy)
    assert report["status"] == "complete" and all(report["gates"].values())
    assert len(report["trades"]) == 9 and report["synthetic"]
    assert report["ready_for_live"] is report["external_acceptance_verified"] is False
    assert daily_policy.database.exists() == before
    cash = D(report["final_snapshot"]["cash"])
    assert cash == daily_policy.starting_cash + sum(t["net_pnl"] for t in report["trades"])
    assert D(report["final_snapshot"]["fees"]) > 0
    output = tmp_path / "result"
    for path in output.iterdir():
        assert path.stat().st_mode & 0o777 == 0o600
    with closing(sqlite3.connect(output / "paper.sqlite3")) as connection:
        for created, filled in connection.execute(
            "SELECT o.created, f.time FROM orders o JOIN fills f ON f.order_id=o.id"
        ):
            assert datetime.fromisoformat(filled) > datetime.fromisoformat(created)
    # Reconstruct independently from persisted financial events after reopening.
    db = Database(output / "paper.sqlite3", daily_policy.starting_cash)
    try:
        with db.transaction() as tx:
            db.reconcile(tx)
    finally:
        db.close()


def test_independent_labels_include_adverse_paths_and_never_trade_observer(
    execution_inputs, tmp_path, daily_policy, daily_strategy
):
    report = replay(execution_inputs, tmp_path, daily_policy, daily_strategy, labels=True)
    output = tmp_path / "result"
    samples = [
        DailySample.model_validate_json(s)
        for s in (output / "samples.jsonl").read_text().splitlines()
    ]
    assert report["label_counts"] == {"LABELED": 9}
    assert sum(s.target for s in samples) == 6
    assert all(s.net_pnl < 0 and s.exit_reason == "STOP" for s in samples if s.target == 0)
    assert report["final_snapshot"]["cash"] == "25000.00"
    assert report["trades"] == []
    assert len(list((output / "trials").glob("*/paper.sqlite3"))) == 9


@pytest.mark.parametrize("labels", [False, True])
def test_source_exhaustion_never_invents_liquidation(
    execution_inputs, tmp_path, daily_policy, daily_strategy, labels
):
    rows = events(execution_inputs[1])[:10]  # review, proposal, then actual entry fills
    report = replay(execution_inputs, tmp_path, daily_policy, daily_strategy, rows, labels=labels)
    if labels:
        assert report["label_counts"] == {"SOURCE_ENDED": 3}
        assert not (tmp_path / "result/samples.jsonl").read_text()
        with closing(
            sqlite3.connect(next((tmp_path / "result/trials").glob("*/paper.sqlite3")))
        ) as db:
            assert db.execute("SELECT COUNT(*) FROM positions").fetchone()[0] == 1
    else:
        assert report["status"] == "incomplete"
        assert report["final_snapshot"]["positions"] and not report["trades"]


@pytest.mark.parametrize("fault", ["disconnect", "kill", "quote_gap", "stale"])
def test_label_censoring_preserves_unresolved_accounts(
    execution_inputs, tmp_path, daily_policy, daily_strategy, fault
):
    rows = events(execution_inputs[1])[:10]
    now = datetime.fromisoformat(rows[-1]["time"]) + timedelta(seconds=1)
    if fault in {"disconnect", "kill"}:
        rows.append(
            {
                "type": "connection" if fault == "disconnect" else "kill",
                "time": now.isoformat(),
                **({"connected": False} if fault == "disconnect" else {}),
            }
        )
    else:
        quotes = [dict(row) for row in rows[-3:]]
        for row in quotes:
            row["quote"] = dict(row["quote"])
            at = now + (timedelta(seconds=60) if fault == "quote_gap" else timedelta())
            row["time"] = row["quote"]["received_time"] = at.isoformat()
            row["quote"]["exchange_time"] = (
                at - timedelta(seconds=10) if fault == "stale" else at
            ).isoformat()
        rows += quotes
    report = replay(execution_inputs, tmp_path, daily_policy, daily_strategy, rows, labels=True)
    reason = {
        "disconnect": "INTERRUPTED",
        "kill": "INTERRUPTED",
        "quote_gap": "QUOTE_GAP",
        "stale": "STALE_QUOTE",
    }[fault]
    assert report["label_counts"] == {reason: 3}
    assert not (tmp_path / "result/samples.jsonl").read_text()


def test_partial_and_unfilled_labels_are_excluded(
    execution_inputs, tmp_path, daily_policy, daily_strategy
):
    rows = events(execution_inputs[1])[:16]
    for row in rows:
        if row["type"] == "quote" and row["time"] != rows[4]["time"]:
            row["quote"]["ask_size"] = 1
    # A clock after expiry cancels residual entry; the exit still uses observed bid depth.
    at = datetime.fromisoformat(rows[-1]["time"]) + timedelta(seconds=60)
    rows.append({"type": "clock", "time": at.isoformat()})
    report = replay(execution_inputs, tmp_path, daily_policy, daily_strategy, rows, labels=True)
    assert sum(report["label_counts"].values()) == 3
    assert "LABELED" not in report["label_counts"]


@pytest.mark.parametrize("fault", ["backward", "unknown_date", "token", "candle", "duplicate_key"])
def test_invalid_execution_fails_without_completion_manifest(
    execution_inputs, tmp_path, daily_policy, daily_strategy, fault
):
    daily, execution, _ = execution_inputs
    rows = events(execution)
    if fault == "backward":
        rows[5]["time"] = rows[0]["time"]
        rows[5]["quote"]["received_time"] = rows[0]["time"]
    elif fault == "unknown_date":
        rows[0]["time"] = "2030-01-01T09:00:00+05:30"
    elif fault == "token":
        rows[4]["quote"]["token"] = 9999
    elif fault == "candle":
        rows[0] = {"type": "candle", "time": rows[0]["time"]}
    write_events(execution, rows)
    if fault == "duplicate_key":
        (execution / "events.jsonl").write_text(
            '{"type":"clock","type":"kill","time":"2025-03-24T10:00:00+05:30"}\n'
        )
    with pytest.raises(ValueError):
        run_daily(
            ExecutionDataset(execution, DailyDataset(daily)),
            strategy=daily_strategy,
            policy=daily_policy,
            output=tmp_path / "bad",
        )
    assert not (tmp_path / "bad/manifest.json").exists()


@pytest.mark.parametrize("fault", ["kind", "calendar", "catalog", "synthetic", "symlink"])
def test_execution_bundle_identity_and_paths(execution_inputs, fault):
    daily, execution, _ = execution_inputs
    manifest = json.loads((execution / "manifest.json").read_text())
    if fault == "kind":
        manifest.pop("kind")
    elif fault == "calendar":
        manifest["sessions"][0]["source"] = "different review"
    elif fault == "catalog":
        manifest["instruments"][0]["symbol"] = "NSE:UNKNOWN"
    elif fault == "synthetic":
        manifest["synthetic"] = False
    else:
        (execution / "events.jsonl").rename(execution / "actual")
        (execution / "events.jsonl").symlink_to(execution / "actual")
    (execution / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        ExecutionDataset(execution, DailyDataset(daily))


def test_policy_and_output_boundaries(execution_source, tmp_path, daily_strategy):
    with pytest.raises(ValueError, match="long-term"):
        run_daily(
            execution_source, strategy=daily_strategy, policy=Settings(), output=tmp_path / "bad"
        )
    with pytest.raises(ValueError, match="outside"):
        run_daily(
            execution_source,
            strategy=daily_strategy,
            policy=Settings(investment_horizon="long_term"),
            output=execution_source.directory / "bad",
        )


def test_coverage_clock_excludes_closed_hours_and_weekends(execution_source):
    from trading_agent.market_data.calendar import SessionCalendar

    clock = TradingClock(
        SessionCalendar(
            {s.day: (s.open, s.close) for s in execution_source.daily.manifest.sessions}
        )
    )
    days = tuple(clock.opens)
    start = clock.closes[4] - timedelta(seconds=2)
    end = days[5] + timedelta(seconds=3)
    assert (end - start).total_seconds() > 48 * 3600
    assert clock.seconds(start, end) == 5
    with pytest.raises(ValueError, match="backward"):
        clock.seconds(end, start)


def test_daily_features_ignore_future_prices_and_require_latest_available_session(
    execution_source, daily_strategy
):
    source = execution_source
    first = next(e for e in source.events() if isinstance(e, QuoteEvent))
    symbols = {i.symbol for i in source.manifest.instruments}
    timeline = DailyTimeline(source.daily, symbols, daily_strategy.screen)
    result = timeline.screen(first.quote.symbol, first.time)
    assert result["status"] == "research_candidate"
    assert result["last_session"] < first.time.astimezone(IST).date().isoformat()
    with pytest.raises(ValueError, match="backward"):
        timeline.screen(first.quote.symbol, first.time - timedelta(seconds=1))
    # Delaying yesterday's review makes the entire latest session unavailable.
    bars = source.daily.directory / "daily.jsonl"
    rows = [json.loads(line) for line in bars.read_text().splitlines()]
    for row in rows:
        if row["symbol"] == first.quote.symbol and row["session"] == result["last_session"]:
            row["basis_reviewed_at"] = (first.time + timedelta(hours=1)).isoformat()
        elif (
            row["symbol"] == first.quote.symbol
            and row["session"] == source.daily.manifest.sessions[30].day.isoformat()
        ):
            row["basis_reviewed_at"] = (first.time + timedelta(minutes=30)).isoformat()
        elif row["session"] >= first.time.astimezone(IST).date().isoformat():
            for key in ("open", "high", "low", "close"):
                row[key] = str(D(row[key]) * 10)
    bars.write_text("".join(json.dumps(row) + "\n" for row in rows))
    delayed = DailyTimeline(DailyDataset(source.daily.directory), symbols, daily_strategy.screen)
    assert delayed.screen(first.quote.symbol, first.time)["status"] == "needs_data"
    later = delayed.screen(first.quote.symbol, first.time + timedelta(hours=2))
    assert later["last_close"] == result["last_close"]
    assert datetime.fromisoformat(later["available_at"]) > first.time
    assert delayed.rebuilds == 1
    assert {k: v for k, v in later.items() if k != "available_at"} == {
        k: v for k, v in result.items() if k != "available_at"
    }
    # Premarket clocks must not consume a removal first known later that morning.
    manifest_path = source.daily.directory / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    day = first.time.astimezone(IST).date()
    known = datetime.combine(day, datetime.min.time(), IST).replace(hour=9, minute=14)
    manifest["universe"].append(
        {
            "symbol": first.quote.symbol,
            "effective_session": day.isoformat(),
            "included": False,
            "known_at": known.isoformat(),
            "reference": "invented preopen removal",
        }
    )
    manifest_path.write_text(json.dumps(manifest))
    memberships = DailyTimeline(
        DailyDataset(source.daily.directory), symbols, daily_strategy.screen
    )
    assert memberships.included(first.quote.symbol, day, known - timedelta(minutes=1))
    assert not memberships.included(first.quote.symbol, day, known)


@pytest.mark.parametrize(
    "change",
    [
        {"max_hold_sessions": 0},
        {"max_active_labels": 1000},
        {"max_samples": True},
        {"stop_pct": "0"},
    ],
)
def test_strategy_bounds(change):
    with pytest.raises(ValueError):
        DailyStrategy.model_validate(change)


def test_daily_vector_cannot_contain_outcomes_or_intraday_schema(daily_ml_demo):
    raw = json.loads((daily_ml_demo[0] / "labels/samples.jsonl").read_text().splitlines()[0])
    vector = raw["features"]
    vector["outcome"] = 1
    with pytest.raises(ValueError):
        DailyVector.model_validate(vector)
    vector.pop("outcome")
    vector["version"] = "intraday-features-v1"
    with pytest.raises(ValueError):
        DailyVector.model_validate(vector)


@pytest.mark.parametrize("fault", ["price", "benefit"])
def test_daily_execution_structural_basis_disagreement_cannot_finish(
    execution_inputs, tmp_path, daily_policy, daily_strategy, fault
):
    daily, execution, _ = execution_inputs
    rows = events(execution)
    day = rows[4]["quote"]["exchange_time"][:10]
    path = daily / "daily.jsonl"
    bars = [json.loads(line) for line in path.read_text().splitlines()]
    for bar in bars:
        if bar["session"] == day:
            if fault == "price":
                for key in ("open", "high", "low", "close"):
                    bar[key] = str(D(bar[key]) * 2)
            else:
                bar["share_numerator"] = 2
    path.write_text("".join(json.dumps(bar) + "\n" for bar in bars))
    with pytest.raises(ValueError, match="contradicts|disagree"):
        replay(execution_inputs, tmp_path, daily_policy, daily_strategy)
    assert not (tmp_path / "result/manifest.json").exists()


def test_overnight_session_limit_queues_exit_and_waits_for_later_quote(
    execution_inputs, tmp_path, daily_policy, daily_strategy
):
    rows = events(execution_inputs[1])
    # Hold through the first close: only actual entry quotes on day one. Later
    # quotes remain unchanged on day two, so the session horizon causes the exit.
    first = rows[:10]
    tomorrow = rows[16:25]
    for row in tomorrow:
        if row["type"] == "quote":
            original = next(
                r
                for r in first
                if r["type"] == "quote" and r["quote"]["symbol"] == row["quote"]["symbol"]
            )
            for key in ("last", "bid", "ask"):
                row["quote"][key] = original["quote"][key]
    strategy = daily_strategy.model_copy(
        update={"max_hold_sessions": 1, "max_open_quote_gap_seconds": 21600}
    )
    report = replay(execution_inputs, tmp_path, daily_policy, strategy, first + tomorrow)
    assert len(report["trades"]) == 3
    assert all(trade["exit_reason"] == "DAILY_HOLDING_LIMIT" for trade in report["trades"])
    assert all(trade["exit_time"][:10] > trade["entry_time"][:10] for trade in report["trades"])
    assert not report["final_snapshot"]["positions"]


def test_simultaneous_rank_and_independent_capacity_are_explicit(
    execution_inputs, tmp_path, daily_policy, daily_strategy
):
    strategy = daily_strategy.model_copy(update={"max_active_labels": 1})
    report = replay(execution_inputs, tmp_path, daily_policy, strategy, labels=True)
    assert report["label_counts"] == {"LABELED": 3, "CAPACITY_EXCLUDED": 6}
    requested = [row for row in report["decisions"] if row.get("label_trial_requested")]
    assert [row["symbol"] for row in requested[:3]] == ["NSE:FAST", "NSE:MID", "NSE:SLOW"]
    assert [row["simultaneous_rank"] for row in requested[:3]] == [1, 2, 3]


@pytest.mark.parametrize("labels", [False, True])
def test_execution_source_split_before_new_entry_uses_reviewed_calendar_and_raw_basis(
    execution_inputs, tmp_path, daily_policy, daily_strategy, labels
):
    from trading_agent.corporate_actions.contracts import digest
    from trading_agent.execution.costs import down, up
    from trading_agent.execution.delivery import HoldingReview

    daily, execution, _ = execution_inputs
    rows = events(execution)
    review_row = rows[3]
    assert review_row["review"]["symbol"] == "NSE:FAST"
    now = datetime.fromisoformat(review_row["time"])
    quarantine = HoldingReview.model_validate(
        {**review_row["review"], "no_corporate_action": False}
    )
    replacement = {**review_row, "review": quarantine.model_dump(mode="json")}
    action = {
        "type": "action",
        "time": review_row["time"],
        "batch": {
            "batch_id": "source-split",
            "symbol": "NSE:FAST",
            "quarantine_sha256": digest(quarantine.model_dump(mode="json")),
            "reviewed_at": now.isoformat(),
            "reference": "invented complete source review",
            "covers_all_actions": True,
            "actions": [
                {
                    "action_id": "source-shares",
                    "kind": "split",
                    "ex_date": now.date().isoformat(),
                    "record_date": now.date().isoformat(),
                    "credit_date": now.date().isoformat(),
                    "announced_at": (now - timedelta(days=1)).isoformat(),
                    "reference": "invented two for one",
                    "numerator": 2,
                    "denominator": 1,
                }
            ],
        },
    }
    rows[3:4] = [replacement, action, review_row]
    for row in rows:
        if row["type"] == "quote" and row["quote"]["symbol"] == "NSE:FAST":
            for key in ("last", "bid", "ask"):
                round_tick = up if key == "ask" else down
                row["quote"][key] = str(round_tick(D(row["quote"][key]) / 2, D(".05")))
    path = daily / "daily.jsonl"
    bars = [json.loads(line) for line in path.read_text().splitlines()]
    for bar in bars:
        if bar["symbol"] == "NSE:FAST" and bar["session"] >= now.date().isoformat():
            for key in ("open", "high", "low", "close"):
                bar[key] = str((D(bar[key]) / 2).quantize(D(".0001")))
            if bar["session"] == now.date().isoformat():
                bar["share_numerator"] = 2
    path.write_text("".join(json.dumps(bar) + "\n" for bar in bars))
    report = replay(execution_inputs, tmp_path, daily_policy, daily_strategy, rows, labels=labels)
    assert report["status"] == "complete"
    if labels:
        assert report["label_counts"] == {"LABELED": 9}
    else:
        assert len(report["trades"]) == 9
