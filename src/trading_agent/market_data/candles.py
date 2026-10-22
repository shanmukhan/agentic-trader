"""Incremental bounded-memory 1m/5m candles from cumulative-volume quotes."""

from datetime import datetime, timedelta
from typing import Literal, cast

from trading_agent.market_data.calendar import IST
from trading_agent.models import Candle, Quote


class CandleBuilder:
    def __init__(self, minutes: int):
        if minutes not in (1, 5):
            raise ValueError("only 1m and 5m supported")
        self.minutes = cast(Literal[1, 5], minutes)
        self.active: dict[str, Candle] = {}
        self.previous: dict[str, Quote] = {}

    def update(self, quote: Quote) -> list[Candle]:
        previous = self.previous.get(quote.symbol)
        if (
            previous
            and quote.exchange_time <= previous.exchange_time
            and not quote.ordered_kite_second_update(previous)
        ):
            raise ValueError("non-monotonic candle input")
        same_day = (
            previous
            and previous.exchange_time.astimezone(IST).date()
            == quote.exchange_time.astimezone(IST).date()
        )
        if same_day and previous and quote.volume < previous.volume:
            raise ValueError("volume regression")
        volume = quote.volume - previous.volume if same_day and previous else 0
        start = quote.exchange_time.replace(
            second=0,
            microsecond=0,
            minute=quote.exchange_time.minute // self.minutes * self.minutes,
        )
        current = self.active.get(quote.symbol)
        completed = []
        quality = "ok" if same_day else "unknown_initial_volume"
        if current and current.start != start:
            gap = (start - current.start) > timedelta(minutes=self.minutes)
            completed.append(
                current.model_copy(
                    update={"completed": True, "quality": "gap" if gap else current.quality}
                )
            )
            current = None
            if gap:
                quality = "gap"
        if current:
            self.active[quote.symbol] = current.model_copy(
                update={
                    "high": max(current.high, quote.last),
                    "low": min(current.low, quote.last),
                    "close": quote.last,
                    "volume": current.volume + volume,
                }
            )
        else:
            self.active[quote.symbol] = Candle(
                symbol=quote.symbol,
                start=start,
                minutes=self.minutes,
                open=quote.last,
                high=quote.last,
                low=quote.last,
                close=quote.last,
                volume=volume,
                completed=False,
                quality=quality,
            )
        self.previous[quote.symbol] = quote
        return completed

    def flush(self, watermark: datetime) -> list[Candle]:
        """Use only a trusted exchange/replay watermark; never wall-clock fabricate data."""
        result = []
        for symbol, candle in list(self.active.items()):
            if candle.start + timedelta(minutes=self.minutes) <= watermark:
                result.append(candle.model_copy(update={"completed": True}))
                del self.active[symbol]
        return result
