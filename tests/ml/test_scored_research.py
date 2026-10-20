import json
from decimal import Decimal as D

import pytest

from trading_agent.backtesting.dataset import CandleEvent, Dataset, QuoteEvent, write_bundle
from trading_agent.backtesting.runner import run_backtest
from trading_agent.ml.features import FEATURE_NAMES
from trading_agent.ml.inference import Artifact, Coefficients, ResearchModel
from trading_agent.models import Instrument
from trading_agent.risk.policy import policy_fingerprint
from trading_agent.settings import Settings
from trading_agent.strategy.rules import StrategySettings


def test_same_time_candidates_rank_before_risk_and_never_fill_on_signal(
    research_dataset, research_model, tmp_path
):
    policy = Settings(max_positions=1)
    template = research_model.artifact.model_dump()
    # Deterministic research fixture: relative volume alone sets score.
    coeff = Coefficients(
        means=(0.0,) * 12,
        scales=(1.0,) * 12,
        weights=tuple(1.0 if name == "relative_volume" else 0.0 for name in FEATURE_NAMES),
        intercept=0.0,
        calibration_slope=1.0,
        calibration_intercept=0.0,
    )
    model = ResearchModel(
        Artifact(
            **(template | {"coefficients": coeff, "policy_sha256": policy_fingerprint(policy)})
        ),
        "f" * 64,
    )
    manifest = research_dataset.manifest.model_copy(
        update={
            "instruments": (
                *research_dataset.manifest.instruments,
                Instrument(symbol="NSE:SECOND", token=2, tick_size=D(".05")),
            )
        }
    )
    events = []
    for event in research_dataset.events():
        events.append(event)
        if isinstance(event, QuoteEvent):
            events.append(
                QuoteEvent(
                    time=event.time,
                    quote=event.quote.model_copy(update={"symbol": "NSE:SECOND", "token": 2}),
                )
            )
        if isinstance(event, CandleEvent):
            events.append(
                CandleEvent(
                    time=event.time,
                    candle=event.candle.model_copy(
                        update={
                            "symbol": "NSE:SECOND",
                            "volume": 10000 if event.candle.volume == 5000 else event.candle.volume,
                        }
                    ),
                )
            )
    write_bundle(tmp_path / "two", manifest, iter(events))
    report = run_backtest(
        Dataset(tmp_path / "two"),
        strategy=StrategySettings(),
        policy=policy,
        output=tmp_path / "run",
        model=model,
    )
    decisions = [
        json.loads(line) for line in (tmp_path / "run/decisions.jsonl").read_text().splitlines()
    ]
    candidates = [row for row in decisions if row.get("candidate")]
    assert [row["symbol"] for row in candidates] == ["NSE:SECOND", "NSE:DEMO"] * 2
    assert [row["ml_rank"] for row in candidates] == [1, 2] * 2
    assert [row["risk_order_state"] for row in candidates] == ["ACCEPTED", "REJECTED"] * 2
    assert report["metrics"]["rejection_reasons"]["POSITION_LIMIT"] == 2
    trades = [json.loads(line) for line in (tmp_path / "run/trades.jsonl").read_text().splitlines()]
    assert all(trade["symbol"] == "NSE:SECOND" for trade in trades)
    assert all(
        trade["entry_time"] > row["time"]
        for trade, row in zip(trades, candidates[::2], strict=True)
    )


def test_scored_backtest_is_deterministic_and_cannot_start_before_validation(
    ml_demo, research_model, tmp_path
):
    dataset = Dataset(ml_demo[0] / "future-data")
    kwargs = dict(strategy=StrategySettings(), policy=Settings(), model=research_model)
    a = run_backtest(dataset, output=tmp_path / "a", **kwargs)
    b = run_backtest(dataset, output=tmp_path / "b", **kwargs)
    assert a == b and a["model_sha256"] == research_model.version
    assert a["status"] == "complete" and a["metrics"]["completed_trades"] == 5
    assert a["metrics"]["rejection_reasons"] == {"MODEL_BELOW_THRESHOLD": 5}
    with pytest.raises(ValueError, match="start after"):
        run_backtest(Dataset(ml_demo[0] / "training-data"), output=tmp_path / "too-early", **kwargs)
    assert json.loads((tmp_path / "too-early/run.json").read_text())["state"] == "failed"
    with pytest.raises(ValueError, match="context"):
        run_backtest(
            dataset,
            strategy=StrategySettings(),
            policy=Settings(latency_ms=200),
            output=tmp_path / "changed-policy",
            model=research_model,
        )
    assert not (tmp_path / "changed-policy").exists()


def test_later_price_changes_cannot_change_earlier_ml_scores(ml_demo, research_model, tmp_path):
    from conftest import changed_dataset

    dataset = Dataset(ml_demo[0] / "future-data")
    events = list(dataset.events())
    last_quote = max(index for index, event in enumerate(events) if isinstance(event, QuoteEvent))
    changed = events[last_quote]
    events[last_quote] = QuoteEvent(
        time=changed.time,
        quote=changed.quote.model_copy(update={"bid": D(480), "ask": D("480.05"), "last": D(480)}),
    )
    altered = changed_dataset(dataset, tmp_path / "altered", lambda _: events)
    kwargs = dict(strategy=StrategySettings(), policy=Settings(), model=research_model)
    run_backtest(dataset, output=tmp_path / "a", **kwargs)
    run_backtest(altered, output=tmp_path / "b", **kwargs)
    assert (tmp_path / "a/decisions.jsonl").read_bytes() == (
        tmp_path / "b/decisions.jsonl"
    ).read_bytes()
