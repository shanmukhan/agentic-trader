"""Synthetic positive and negative sessions for functional verification, never model evidence."""

from collections.abc import Iterator
from datetime import date, datetime, time, timedelta
from decimal import Decimal as D
from pathlib import Path

from trading_agent.backtesting.dataset import (
    CandleEvent,
    ClockEvent,
    ConnectionEvent,
    Event,
    Manifest,
    QuoteEvent,
    Session,
    write_bundle,
)
from trading_agent.market_data.calendar import IST
from trading_agent.models import Candle, Instrument, Quote, utc
from trading_agent.strategy.rules import StrategySettings


def demo_events(settings: StrategySettings) -> Iterator[Event]:
    bars = max(
        settings.indicator_period, settings.volume_lookback + 1, settings.opening_minutes // 5 + 1
    )
    for day, winning in ((date(2026, 10, 20), True), (date(2026, 10, 21), False)):
        opened = utc(datetime.combine(day, time(9, 15), IST))
        yield ConnectionEvent(time=opened, connected=True)
        volume = 0
        for index in range(bars):
            is_signal = index == bars - 1
            start, close = opened + timedelta(minutes=5 * index), D(501 if is_signal else 500)
            end = start + timedelta(minutes=5)
            bar = Candle(
                symbol="NSE:DEMO",
                start=start,
                minutes=5,
                open=D(500),
                high=D("501.50") if is_signal else D("500.50"),
                low=D("499.50"),
                close=close,
                volume=5000 if is_signal else 2000,
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
        for second, bid in (
            (1, D(501)),
            (2, D(506) if winning else D(497)),
            (3, D(506) if winning else D("496.95")),
        ):
            now = end + timedelta(seconds=second)
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
                    volume=volume + second * 100,
                ),
            )
        yield ClockEvent(time=utc(datetime.combine(day, time(15, 15), IST)))


def create_demo_dataset(directory: Path, settings: StrategySettings) -> None:
    manifest = Manifest(
        source="synthetic-phase2-functional-fixture",
        synthetic=True,
        data_notes="Invented candles and quotes; one winning and one losing session. "
        "Not exchange observations or a profitability experiment.",
        instruments=(Instrument(symbol="NSE:DEMO", token=1, tick_size=D(".05")),),
        sessions=tuple(
            Session(
                day=date(2026, 10, day),
                open=time(9, 15),
                close=time(15, 30),
                source="synthetic fixture session",
            )
            for day in (20, 21)
        ),
    )
    write_bundle(directory, manifest, demo_events(settings))
