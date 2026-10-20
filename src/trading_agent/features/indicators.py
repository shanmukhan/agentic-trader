from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal

from trading_agent.market_data.calendar import IST
from trading_agent.models import Candle

D = Decimal


@dataclass
class Indicators:
    period: int = 14
    ema: Decimal | None = None
    atr: Decimal | None = None
    vwap: Decimal | None = None
    count: int = 0
    _previous_close: Decimal | None = None
    _last: datetime | None = None
    _symbol: str | None = None
    _minutes: int | None = None
    _pv: Decimal = D(0)
    _volume: int = 0
    _trs: list[Decimal] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.period < 1:
            raise ValueError("period must be positive")

    def update(self, candle: Candle) -> dict[str, Decimal | str | None]:
        if not candle.completed or candle.quality != "ok":
            raise ValueError("only completed good-quality candles accepted")
        if self._symbol and (candle.symbol != self._symbol or candle.minutes != self._minutes):
            raise ValueError("indicator instance belongs to one symbol and timeframe")
        if self._last and candle.start <= self._last:
            raise ValueError("duplicate or out-of-order feature input")
        new_day = (
            self._last and self._last.astimezone(IST).date() != candle.start.astimezone(IST).date()
        )
        if (
            self._last
            and not new_day
            and candle.start != self._last + timedelta(minutes=candle.minutes)
        ):
            raise ValueError("missing candle; rewarm the indicator")
        if new_day:
            self.ema, self.atr, self.vwap = None, None, None
            self.count, self._volume, self._pv = 0, 0, D(0)
            self._trs.clear()
            self._previous_close = None
        tr = candle.high - candle.low
        if self._previous_close is not None:
            tr = max(
                tr, abs(candle.high - self._previous_close), abs(candle.low - self._previous_close)
            )
        self.ema = (
            candle.close
            if self.ema is None
            else self.ema + D(2) / (self.period + 1) * (candle.close - self.ema)
        )
        if self.atr is None:
            self._trs.append(tr)
            if len(self._trs) == self.period:
                self.atr = sum(self._trs, D(0)) / self.period
                self._trs.clear()
        else:
            self.atr = (self.atr * (self.period - 1) + tr) / self.period
        self._volume += candle.volume
        self._pv += (candle.high + candle.low + candle.close) / 3 * candle.volume
        self.vwap = self._pv / self._volume if self._volume else None
        self._previous_close, self._last = candle.close, candle.start
        self._symbol, self._minutes = candle.symbol, candle.minutes
        self.count += 1
        return {
            "feature_version": "completed-ohlcv-v1",
            "ema": self.ema if self.count >= self.period else None,
            "atr": self.atr,
            "vwap": self.vwap,
        }
