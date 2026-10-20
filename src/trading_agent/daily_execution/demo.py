"""Invented adverse/positive delivery executions and separate chronological daily ML."""

import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from trading_agent.daily_execution.contracts import DailyStrategy
from trading_agent.daily_execution.dataset import (
    ConnectionEvent,
    ExecutionDataset,
    ExecutionManifest,
    QuoteEvent,
    ReviewEvent,
)
from trading_agent.daily_execution.model import DailySamples, load_daily_model, train_daily
from trading_agent.daily_execution.runner import run_daily
from trading_agent.daily_research.dataset import DailyBar, DailyDataset, DailyManifest
from trading_agent.execution.costs import down, up
from trading_agent.execution.delivery import HoldingReview
from trading_agent.market_data.calendar import IST
from trading_agent.ml.schema import TrainingSettings
from trading_agent.models import Instrument, Quote
from trading_agent.settings import Settings

D = Decimal


def create_execution_demo(directory: Path, *, sessions: int = 50) -> tuple[Path, Path, Path]:
    directory.mkdir(parents=True, exist_ok=False, mode=0o700)
    daily, execution, future = (directory / name for name in ("daily", "execution", "future"))
    daily.mkdir(mode=0o700)
    days: list[date] = []
    day = date(2025, 1, 6)
    while len(days) < 55 + sessions + 15:
        if day.weekday() < 5:
            days.append(day)
        day += timedelta(days=1)
    instruments = [
        Instrument(symbol=symbol, token=index + 1, tick_size=D(".05"))
        for index, symbol in enumerate(("NSE:SLOW", "NSE:MID", "NSE:FAST"))
    ]
    manifest = DailyManifest.model_validate(
        {
            "source": "INVENTED daily delivery fixture",
            "notes": "Invented calendar/quotes/labels; no market-edge evidence.",
            "synthetic": True,
            "sessions": [
                {
                    "day": day.isoformat(),
                    "open": "09:15",
                    "close": "15:30",
                    "source": "INVENTED execution/research session",
                }
                for day in days
            ],
            "universe": [
                {
                    "symbol": item.symbol,
                    "effective_session": days[0].isoformat(),
                    "included": True,
                    "known_at": datetime.combine(
                        days[0] - timedelta(days=1), time(12), IST
                    ).isoformat(),
                    "reference": "INVENTED historical inclusion",
                }
                for item in instruments
            ],
        }
    )
    (daily / "manifest.json").write_text(manifest.model_dump_json(indent=2) + "\n")
    closes: dict[tuple[str, date], Decimal] = {}
    prices = {item.symbol: D(500) for item in instruments}
    with (daily / "daily.jsonl").open("x") as file:
        for day in days:
            for item in sorted(instruments, key=lambda item: item.symbol):
                growth = {"NSE:SLOW": D("1.003"), "NSE:MID": D("1.005"), "NSE:FAST": D("1.007")}[
                    item.symbol
                ]
                prices[item.symbol] = (prices[item.symbol] * growth).quantize(D(".0001"))
                price = prices[item.symbol]
                closes[item.symbol, day] = price
                closed = datetime.combine(day, time(15, 30), IST)
                bar = DailyBar(
                    symbol=item.symbol,
                    session=day,
                    open=price,
                    high=(price * D("1.12")).quantize(D(".0001")),
                    low=(price * D(".88")).quantize(D(".0001")),
                    close=price,
                    volume=100000,
                    price_available_at=closed + timedelta(minutes=5),
                    basis_reviewed_at=closed,
                    basis_reference="INVENTED complete period review",
                    share_numerator=1,
                    share_denominator=1,
                    cash_per_previous_share=D(0),
                )
                file.write(bar.model_dump_json() + "\n")
    for folder, indices in (
        (execution, range(55, 55 + sessions)),
        (future, range(60 + sessions, 70 + sessions)),
    ):
        folder.mkdir(mode=0o700)
        selected = [manifest.sessions[index] for index in indices]
        em = ExecutionManifest(
            source="INVENTED observed quote fixture",
            data_notes="Invented four-tick entry/exit clusters; no external acceptance.",
            synthetic=True,
            instruments=tuple(instruments),
            sessions=tuple(selected),
        )
        with (folder / "events.jsonl").open("x") as file:
            for index in indices:
                now = datetime.combine(days[index], time(10), IST)
                if index == indices.start:
                    file.write(
                        ConnectionEvent(
                            time=now - timedelta(seconds=2), connected=True
                        ).model_dump_json()
                        + "\n"
                    )
                for item in instruments:
                    file.write(
                        ReviewEvent(
                            time=now - timedelta(seconds=1),
                            review=HoldingReview(
                                symbol=item.symbol,
                                session_date=days[index],
                                no_corporate_action=True,
                                reference="INVENTED clear basis",
                            ),
                        ).model_dump_json()
                        + "\n"
                    )
                for second in range(4):
                    for item in instruments:
                        price = up(closes[item.symbol, days[index - 1]], D(".05"))
                        bid = price
                        if second >= 2:
                            bid = (
                                down(price * D(".975"), D(".05"))
                                if item.symbol == "NSE:SLOW"
                                else up(price * D("1.05"), D(".05"))
                            )
                        at = now + timedelta(seconds=second)
                        quote = Quote(
                            symbol=item.symbol,
                            token=item.token,
                            exchange_time=at,
                            received_time=at,
                            last=bid,
                            bid=bid,
                            ask=bid + D(".05"),
                            bid_size=1000,
                            ask_size=1000,
                            volume=100000 + second * 1000,
                            source="replay",
                        )
                        file.write(QuoteEvent(time=at, quote=quote).model_dump_json() + "\n")
        (folder / "manifest.json").write_text(em.model_dump_json(indent=2) + "\n")
    return daily, execution, future


def execution_demo(directory: Path, *, with_ml: bool = False) -> dict[str, Any]:
    directory.mkdir(parents=True, exist_ok=False, mode=0o700)
    daily, execution, future = create_execution_demo(directory / "inputs")
    policy = Settings.load("config/long-term.toml")
    strategy = DailyStrategy.load(Path("config/daily-strategy.toml"))
    source = ExecutionDataset(execution, DailyDataset(daily))
    portfolio = run_daily(source, strategy=strategy, policy=policy, output=directory / "portfolio")
    labels = run_daily(
        source, strategy=strategy, policy=policy, output=directory / "labels", labels=True
    )
    result: dict[str, Any] = {
        "synthetic": True,
        "ready_for_live": False,
        "portfolio_cash": portfolio["final_snapshot"]["cash"],
        "completed_trades": portfolio["metrics"]["completed_trades"],
        "label_counts": labels["label_counts"],
    }
    if with_ml:
        validation = train_daily(
            DailySamples(directory / "labels"),
            settings=TrainingSettings.load(Path("config/daily-ml-demo.toml")),
            output=directory / "model",
        )
        model = load_daily_model(
            directory / "model", strategy=strategy, policy=policy, allow_synthetic=True
        )
        scored = run_daily(
            ExecutionDataset(future, DailyDataset(daily)),
            strategy=strategy,
            policy=policy,
            output=directory / "scored",
            model=model,
        )
        result.update(
            validation_gates=validation["gates"],
            scored_cash=scored["final_snapshot"]["cash"],
            scored_completed_trades=scored["metrics"]["completed_trades"],
        )
    (directory / "summary.json").write_text(json.dumps(result, indent=2) + "\n")
    return result
