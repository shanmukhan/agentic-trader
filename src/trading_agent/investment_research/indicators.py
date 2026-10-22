"""Causal, fixed-precision indicators for an already eligible OHLCV series.

This module does not acquire data or decide whether an observation was available.
The caller supplies complete observations in chronological order on one coherent
price/share basis and marks each discontinuity with ``segment_break=True``.  The
break resets every window and recursive seed before calculating that observation.
All percentages are percentages (``1`` means one percent), not return fractions.
"""

from collections import deque
from dataclasses import dataclass, field
from decimal import MAX_EMAX, MIN_EMIN, ROUND_HALF_EVEN, Context, Decimal, localcontext
from typing import Any

FORMULA_VERSION = "investment-indicators-v2.1"

INDICATOR_DEFINITIONS: dict[str, dict[str, Any]] = {
    **{
        f"sma{period}": {
            "formula": "Arithmetic mean of the last n consecutive closes",
            "lookback": period,
            "first_valid_bar": period,
        }
        for period in (20, 50, 200)
    },
    **{
        f"ema{period}": {
            "formula": "SMA seed; then alpha*close+(1-alpha)*previous, alpha=2/(n+1)",
            "lookback": period,
            "first_valid_bar": period,
        }
        for period in (12, 26)
    },
    "rsi14": {
        "formula": "Wilder mean gain/loss over 14 close differences; 100-100/(1+gain/loss)",
        "lookback": 14,
        "first_valid_bar": 15,
        "zero_gain_loss": "Both zero: 50; only loss zero: 100; only gain zero: 0",
    },
    "macd": {
        "formula": "SMA-seeded EMA12 minus SMA-seeded EMA26",
        "first_valid_bar": 26,
    },
    "macd_signal": {
        "formula": "SMA-seeded EMA9 of valid MACD values",
        "lookback": 9,
        "first_valid_bar": 34,
    },
    "macd_histogram": {"formula": "MACD minus signal", "first_valid_bar": 34},
    "atr14": {
        "formula": (
            "Wilder mean of max(high-low, abs(high-previous_close), abs(low-previous_close))"
        ),
        "lookback": 14,
        "first_valid_bar": 15,
        "seed": "Arithmetic mean of the first 14 true ranges, each requiring a previous close",
    },
    "support20": {
        "formula": "Minimum low of the prior 20 bars; current bar excluded",
        "lookback": 20,
        "first_valid_bar": 21,
    },
    "resistance20": {
        "formula": "Maximum high of the prior 20 bars; current bar excluded",
        "lookback": 20,
        "first_valid_bar": 21,
    },
    "drawdown_pct": {
        "formula": "100*(close/running_segment_peak_close-1)",
        "first_valid_bar": 1,
    },
    "max_drawdown_pct": {
        "formula": "Most negative drawdown_pct since the current segment began",
        "first_valid_bar": 1,
    },
    "volatility20_pct": {
        "formula": "100*population standard deviation of 20 simple consecutive close returns",
        "lookback": 20,
        "first_valid_bar": 21,
        "annualized": False,
    },
}

_ZERO = Decimal(0)
_ONE = Decimal(1)
_HUNDRED = Decimal(100)
_CONTEXT = Context(prec=34, rounding=ROUND_HALF_EVEN, Emin=MIN_EMIN, Emax=MAX_EMAX)


def _number(row: dict[str, Any], name: str, index: int, *, positive: bool) -> Decimal:
    raw = row.get(name)
    if isinstance(raw, bool) or not isinstance(raw, str | int | Decimal):
        raise ValueError(f"Bar {index}: {name} must be a finite decimal string or integer")
    try:
        value = Decimal(raw)
    except (ValueError, ArithmeticError):
        raise ValueError(f"Bar {index}: {name} must be a finite decimal") from None
    if not value.is_finite() or (value <= 0 if positive else value < 0):
        requirement = "positive" if positive else "nonnegative"
        raise ValueError(f"Bar {index}: {name} must be finite and {requirement}")
    return value


def _text(value: Decimal | None) -> str | None:
    # str retains the calculation precision without expanding huge exponents.
    return None if value is None else str(value.copy_abs() if value.is_zero() else value)


@dataclass
class _EMA:
    period: int
    seed: list[Decimal] = field(default_factory=list)
    value: Decimal | None = None

    def update(self, value: Decimal) -> Decimal | None:
        if self.value is None:
            self.seed.append(value)
            if len(self.seed) == self.period:
                self.value = sum(self.seed, _ZERO) / self.period
                self.seed.clear()
        else:
            alpha = Decimal(2) / (self.period + 1)
            self.value = alpha * value + (_ONE - alpha) * self.value
        return self.value


@dataclass
class _Wilder:
    period: int = 14
    seed: list[Decimal] = field(default_factory=list)
    value: Decimal | None = None

    def update(self, value: Decimal) -> Decimal | None:
        if self.value is None:
            self.seed.append(value)
            if len(self.seed) == self.period:
                self.value = sum(self.seed, _ZERO) / self.period
                self.seed.clear()
        else:
            self.value = ((self.period - 1) * self.value + value) / self.period
        return self.value


@dataclass
class _Segment:
    closes: deque[Decimal] = field(default_factory=lambda: deque(maxlen=200))
    highs: deque[Decimal] = field(default_factory=lambda: deque(maxlen=20))
    lows: deque[Decimal] = field(default_factory=lambda: deque(maxlen=20))
    returns: deque[Decimal] = field(default_factory=lambda: deque(maxlen=20))
    ema12: _EMA = field(default_factory=lambda: _EMA(12))
    ema26: _EMA = field(default_factory=lambda: _EMA(26))
    signal: _EMA = field(default_factory=lambda: _EMA(9))
    gain: _Wilder = field(default_factory=_Wilder)
    loss: _Wilder = field(default_factory=_Wilder)
    atr: _Wilder = field(default_factory=_Wilder)
    previous_close: Decimal | None = None
    peak: Decimal | None = None
    worst_drawdown: Decimal = _ZERO

    def update(self, high: Decimal, low: Decimal, close: Decimal) -> dict[str, str | None]:
        result: dict[str, Decimal | None] = dict.fromkeys(INDICATOR_DEFINITIONS)
        if len(self.lows) == 20:
            result["support20"] = min(self.lows)
            result["resistance20"] = max(self.highs)
        self.highs.append(high)
        self.lows.append(low)
        self.closes.append(close)
        for period in (20, 50, 200):
            if len(self.closes) >= period:
                result[f"sma{period}"] = sum(list(self.closes)[-period:], _ZERO) / period

        result["ema12"] = self.ema12.update(close)
        result["ema26"] = self.ema26.update(close)
        if self.ema12.value is not None and self.ema26.value is not None:
            line = self.ema12.value - self.ema26.value
            result["macd"] = line
            result["macd_signal"] = self.signal.update(line)
            if self.signal.value is not None:
                result["macd_histogram"] = line - self.signal.value

        if self.previous_close is not None:
            change = close - self.previous_close
            gain = self.gain.update(max(change, _ZERO))
            loss = self.loss.update(max(-change, _ZERO))
            if gain is not None and loss is not None:
                if loss.is_zero():
                    result["rsi14"] = Decimal(50) if gain.is_zero() else _HUNDRED
                elif gain.is_zero():
                    result["rsi14"] = _ZERO
                else:
                    result["rsi14"] = _HUNDRED - _HUNDRED / (_ONE + gain / loss)
            true_range = max(
                high - low, abs(high - self.previous_close), abs(low - self.previous_close)
            )
            result["atr14"] = self.atr.update(true_range)
            self.returns.append(close / self.previous_close - _ONE)
            if len(self.returns) == 20:
                mean = sum(self.returns, _ZERO) / 20
                variance = sum(((value - mean) ** 2 for value in self.returns), _ZERO) / 20
                result["volatility20_pct"] = variance.sqrt() * _HUNDRED
        self.previous_close = close
        self.peak = close if self.peak is None else max(self.peak, close)
        drawdown = (close / self.peak - _ONE) * _HUNDRED
        self.worst_drawdown = min(self.worst_drawdown, drawdown)
        result["drawdown_pct"] = drawdown
        result["max_drawdown_pct"] = self.worst_drawdown
        return {name: _text(value) for name, value in result.items()}


def indicator_series(bars: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Copy input records and add indicators, using a private 34-digit context.

    OHLC must be positive finite decimal strings, integers or ``Decimal`` values;
    volume must be finite and nonnegative. Floats and booleans are refused. Each
    high/low must contain both open and close. Inputs are never modified. Ordering,
    exchange-calendar eligibility, availability and corporate-action basis checks
    belong to the caller; arbitrary record metadata is copied through unchanged.
    """
    if not isinstance(bars, list):
        raise ValueError("bars must be a list of OHLCV records")
    output: list[dict[str, Any]] = []
    segment = _Segment()
    with localcontext(_CONTEXT):
        for index, row in enumerate(bars):
            if not isinstance(row, dict):
                raise ValueError(f"Bar {index}: expected an OHLCV record")
            if not isinstance(row.get("segment_break", False), bool):
                raise ValueError(f"Bar {index}: segment_break must be a boolean")
            values = {
                name: _number(row, name, index, positive=True)
                for name in ("open", "high", "low", "close")
            }
            _number(row, "volume", index, positive=False)
            if not (
                values["low"]
                <= min(values["open"], values["close"])
                <= max(values["open"], values["close"])
                <= values["high"]
            ):
                raise ValueError(f"Bar {index}: high/low must contain open and close")
            if row.get("segment_break", False):
                segment = _Segment()
            output.append({**row, **segment.update(values["high"], values["low"], values["close"])})
    return output
