"""Invented learnable data to exercise the entire workflow, never evidence of an edge."""

from collections.abc import Iterator
from datetime import date, datetime, time, timedelta
from decimal import Decimal as D
from pathlib import Path
from typing import Any

from trading_agent.backtesting.dataset import (
    CandleEvent,
    ClockEvent,
    ConnectionEvent,
    Dataset,
    Event,
    Manifest,
    QuoteEvent,
    Session,
    write_bundle,
)
from trading_agent.backtesting.runner import run_backtest
from trading_agent.execution.costs import Charges
from trading_agent.market_data.calendar import IST
from trading_agent.ml.inference import load_model
from trading_agent.ml.labeling import build_samples
from trading_agent.ml.samples import Samples
from trading_agent.ml.schema import TrainingSettings
from trading_agent.ml.training import train_model
from trading_agent.models import Candle, Instrument, Quote, utc
from trading_agent.risk.policy import policy_fingerprint
from trading_agent.settings import Settings
from trading_agent.strategy.rules import StrategySettings


def synthetic_days(count: int) -> tuple[date, ...]:
    days: list[date] = []
    day = date(2026, 6, 1)
    while len(days) < count:
        if day.weekday() < 5:
            days.append(day)
        day += timedelta(days=1)
    return tuple(days)


def training_events(days: tuple[date, ...], strategy: StrategySettings) -> Iterator[Event]:
    bars = max(
        strategy.indicator_period, strategy.volume_lookback + 1, strategy.opening_minutes // 5 + 1
    )
    for index, day in enumerate(days):
        winning = index % 2 == 0
        opened = utc(datetime.combine(day, time(9, 15), IST))
        yield ConnectionEvent(time=opened, connected=True)
        volume = 0
        signal = D("501.50") if winning else D("500.75")
        for bar_index in range(bars):
            start = opened + timedelta(minutes=5 * bar_index)
            end = start + timedelta(minutes=5)
            is_signal = bar_index == bars - 1
            close = signal if is_signal else D(500)
            bar = Candle(
                symbol="NSE:DEMO",
                start=start,
                minutes=5,
                open=D(500),
                high=close + D(".50"),
                low=D("499.50"),
                close=close,
                volume=(6000 if winning else 3000) if is_signal else 2000,
            )
            volume += bar.volume
            quote = Quote(
                symbol=bar.symbol,
                token=1,
                exchange_time=end,
                received_time=end,
                last=close,
                bid=close,
                ask=close + D(".05"),
                bid_size=100,
                ask_size=100,
                volume=volume,
            )
            yield QuoteEvent(time=end, quote=quote)
            yield CandleEvent(time=end, candle=bar)
        for second in (1, 2, 3):
            now = end + timedelta(seconds=second)
            bid = signal if second == 1 else D(508) if winning else D(495)
            yield QuoteEvent(
                time=now,
                quote=Quote(
                    symbol="NSE:DEMO",
                    token=1,
                    exchange_time=now,
                    received_time=now,
                    last=bid,
                    bid=bid,
                    ask=bid + D(".05"),
                    bid_size=100,
                    ask_size=100,
                    volume=volume + 100 * second,
                ),
            )
        yield ClockEvent(time=utc(datetime.combine(day, time(15, 15), IST)))


def create_ml_dataset(directory: Path, days: tuple[date, ...], strategy: StrategySettings) -> None:
    manifest = Manifest(
        source="synthetic-phase3-functional-fixture",
        synthetic=True,
        data_notes="Invented correlation between completed signal features and later prices. "
        "Only a software test: no empirical market performance or calibration claim.",
        instruments=(Instrument(symbol="NSE:DEMO", token=1, tick_size=D(".05")),),
        sessions=tuple(
            Session(
                day=day, open=time(9, 15), close=time(15, 30), source="invented functional session"
            )
            for day in days
        ),
    )
    write_bundle(directory, manifest, training_events(days, strategy))


def run_ml_demo(
    directory: Path, *, strategy: StrategySettings, training: TrainingSettings, policy: Settings
) -> dict[str, Any]:
    directory.mkdir(parents=True, exist_ok=False, mode=0o700)
    training_days = (
        training.min_train_sessions
        + training.calibration_sessions
        + training.validation_sessions * training.walk_forward_folds
        + training.holdout_sessions
    )
    if training_days > 1000:
        raise ValueError("synthetic demo session count exceeds 1000")
    days = synthetic_days(training_days + 10)
    create_ml_dataset(directory / "training-data", days[:training_days], strategy)
    create_ml_dataset(directory / "future-data", days[training_days:], strategy)
    labels = build_samples(
        Dataset(directory / "training-data"),
        strategy=strategy,
        policy=policy,
        output=directory / "samples",
    )
    validation = train_model(
        Samples(directory / "samples"), settings=training, output=directory / "model"
    )
    model = load_model(
        directory / "model",
        strategy_sha256=strategy.digest(),
        policy_sha256=policy_fingerprint(policy),
        charges_version=Charges().version,
        allow_synthetic=True,
    )
    baseline = run_backtest(
        Dataset(directory / "future-data"),
        strategy=strategy,
        policy=policy,
        output=directory / "baseline",
    )
    scored = run_backtest(
        Dataset(directory / "future-data"),
        strategy=strategy,
        policy=policy,
        output=directory / "scored",
        model=model,
    )
    return {
        "directory": str(directory),
        "synthetic": True,
        "ready_for_live": False,
        "label_counts": labels["counts"],
        "validation_gates": validation["gates"],
        "baseline_metrics": baseline["metrics"],
        "scored_metrics": scored["metrics"],
    }
