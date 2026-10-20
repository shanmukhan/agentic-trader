import json
from datetime import timedelta
from decimal import Decimal as D

import pytest
from conftest import changed_dataset

from trading_agent.backtesting.dataset import CandleEvent, QuoteEvent
from trading_agent.backtesting.runner import run_backtest
from trading_agent.models import Candle
from trading_agent.settings import Settings
from trading_agent.strategy.rules import StrategySettings


def run(dataset, output, **changes):
    return run_backtest(
        dataset, strategy=StrategySettings(), policy=Settings(**changes), output=output
    )


def test_functional_net_results_and_determinism(research_dataset, tmp_path):
    a = run(research_dataset, tmp_path / "a")
    b = run(research_dataset, tmp_path / "b")
    assert a == b
    assert (tmp_path / "a/report.json").read_bytes() == (tmp_path / "b/report.json").read_bytes()
    assert a["metrics"]["completed_trades"] == 2
    assert a["metrics"]["winning_trades"] == a["metrics"]["losing_trades"] == 1
    assert a["metrics"]["net_pnl"] == "-25.97"
    assert a["final_snapshot"]["cash"] == "24974.03"
    assert a["final_snapshot"]["fees"] == "20.27"
    assert a["metrics"]["max_drawdown"] == "98.43"
    assert not a["ready_for_live"] and a["status"] == "complete"
    assert not a["research_gates"]["non_synthetic"]
    trades = [json.loads(line) for line in (tmp_path / "a/trades.jsonl").read_text().splitlines()]
    assert sum(D(t["net_pnl"]) for t in trades) == D(a["metrics"]["net_pnl"])
    assert sum(D(t["fees"]) for t in trades) == D(a["final_snapshot"]["fees"])


def test_future_quote_change_cannot_change_prior_decisions(research_dataset, tmp_path):
    def edit(events):
        last_quote_index = max(i for i, e in enumerate(events) if isinstance(e, QuoteEvent))
        q = events[last_quote_index]
        events[last_quote_index] = QuoteEvent(
            time=q.time,
            quote=q.quote.model_copy(update={"bid": D(480), "ask": D("480.05"), "last": D(480)}),
        )
        return events

    altered = changed_dataset(research_dataset, tmp_path / "changed", edit)
    run(research_dataset, tmp_path / "baseline")
    run(altered, tmp_path / "altered")
    assert (tmp_path / "baseline/decisions.jsonl").read_bytes() == (
        tmp_path / "altered/decisions.jsonl"
    ).read_bytes()


def test_risk_gate_cannot_be_overridden_by_strategy(research_dataset, tmp_path):
    result = run(research_dataset, tmp_path / "small-risk", max_trade_risk=D(".10"))
    assert result["event_counts"]["candidates"] == 2
    assert result["metrics"]["completed_trades"] == 0
    assert result["metrics"]["rejection_reasons"]["ZERO_QUANTITY"] == 2
    assert result["final_snapshot"]["cash"] == "25000"


def test_truncated_data_preserves_position_and_marks_report_incomplete(research_dataset, tmp_path):
    def cut(events):
        # Stop immediately after the first post-signal fill quote.
        signal = [e for e in events if isinstance(e, CandleEvent)][13]
        return [e for e in events if e.time <= signal.time + timedelta(seconds=1)]

    truncated = changed_dataset(research_dataset, tmp_path / "truncated", cut)
    result = run(truncated, tmp_path / "run")
    assert result["status"] == "incomplete" and not result["research_gates"]["flat_at_end"]
    assert result["final_snapshot"]["positions"]
    assert result["metrics"]["completed_trades"] == 0


def test_ohlc_stop_target_touches_do_not_fabricate_execution(research_dataset, tmp_path):
    def change(events):
        signal = [e for e in events if isinstance(e, CandleEvent)][13]
        result = [e for e in events if e.time <= signal.time + timedelta(seconds=1)]
        candle = Candle(
            symbol="NSE:DEMO",
            start=signal.time,
            minutes=5,
            open=D(501),
            high=D(600),
            low=D(100),
            close=D(501),
            volume=5000,
        )
        result.append(CandleEvent(time=signal.time + timedelta(minutes=5), candle=candle))
        return result

    altered = changed_dataset(research_dataset, tmp_path / "ohlc", change)
    result = run(altered, tmp_path / "run")
    assert result["metrics"]["completed_trades"] == 0
    assert len(result["final_snapshot"]["positions"]) == 1
    assert not result["research_gates"]["no_stale_valuations"]


def test_failed_run_has_no_success_report_and_preserves_source(research_dataset, tmp_path):
    original = research_dataset.events_path.read_bytes()
    research_dataset.events_path.write_bytes(original + b'{"type":"made-up"}\n')
    output = tmp_path / "failed"
    with pytest.raises(ValueError):
        run(research_dataset, output)
    assert json.loads((output / "run.json").read_text())["state"] == "failed"
    assert not (output / "report.json").exists()
    assert research_dataset.events_path.read_bytes() == original + b'{"type":"made-up"}\n'


def test_output_is_exclusive_and_cannot_pollute_input(research_dataset, tmp_path):
    with pytest.raises(ValueError, match="outside"):
        run(research_dataset, research_dataset.directory / "run")
    output = tmp_path / "existing"
    output.mkdir()
    with pytest.raises(FileExistsError):
        run(research_dataset, output)


def test_candle_only_backtest_is_rejected_instead_of_inventing_prices(research_dataset, tmp_path):
    candles = changed_dataset(
        research_dataset,
        tmp_path / "candles-only",
        lambda events: [e for e in events if isinstance(e, CandleEvent)],
    )
    with pytest.raises(ValueError, match="both"):
        run(candles, tmp_path / "run")
