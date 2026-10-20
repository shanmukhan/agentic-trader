"""Fixed causal feature schema. Floats are used for analysis, never account money."""

import hashlib
import json
import math
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import Field, field_validator, model_validator

from trading_agent.execution.costs import down, up
from trading_agent.models import Candidate, Candle, DomainModel, Instrument, Quote, Symbol, utc
from trading_agent.settings import Settings

FEATURE_VERSION: Literal["candidate-features-v1"] = "candidate-features-v1"
FEATURE_NAMES = (
    "vwap_distance_bps",
    "ema_distance_bps",
    "atr_bps",
    "relative_volume",
    "candle_range_bps",
    "candle_return_bps",
    "spread_bps",
    "quote_gap_bps",
    "stop_distance_bps",
    "net_reward_risk",
    "minutes_since_open",
    "log_turnover",
)
Finite = Annotated[float, Field(strict=True, allow_inf_nan=False, ge=-1e9, le=1e9)]


class FeatureVector(DomainModel):
    version: Literal["candidate-features-v1"] = FEATURE_VERSION
    symbol: Symbol
    time: datetime
    candle_end: datetime
    candidate_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    values: tuple[Finite, ...] = Field(min_length=len(FEATURE_NAMES), max_length=len(FEATURE_NAMES))

    @field_validator("time", "candle_end")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        return utc(value)

    @model_validator(mode="after")
    def causal(self) -> "FeatureVector":
        if self.candle_end > self.time:
            raise ValueError("feature candle is not complete at decision time")
        return self


def candidate_fingerprint(candidate: Candidate) -> str:
    payload = candidate.model_dump(mode="json", exclude={"requires_ml", "model_version"})
    for name in ("stop", "target"):
        payload[name] = format(getattr(candidate, name).normalize(), "f")
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def make_features(
    *,
    candidate: Candidate,
    candle: Candle,
    candle_end: datetime,
    features: dict[str, Any],
    quote: Quote,
    instrument: Instrument,
    opened: datetime,
    policy: Settings,
) -> FeatureVector:
    from trading_agent.execution.costs import Charges

    required = ("ema", "vwap", "atr", "relative_volume")
    if any(features.get(key) is None for key in required):
        raise ValueError("missing completed-candle feature")
    if (
        not candle.completed
        or candle.minutes != 5
        or candle.quality != "ok"
        or candle_end != candle.start + timedelta(minutes=5)
        or opened > candle.start
        or candle.symbol != candidate.symbol
        or quote.symbol != candidate.symbol
        or instrument.symbol != candidate.symbol
        or instrument.token != quote.token
    ):
        raise ValueError("feature symbol/completion mismatch")
    d = Decimal
    ema, vwap, atr, volume = (d(str(features[key])) for key in required)
    if any(not value.is_finite() or value <= 0 for value in (ema, vwap, atr, volume)):
        raise ValueError("invalid completed-candle feature")
    close = candle.close
    entry = up(quote.ask * (1 + policy.slippage_bps / 10000), instrument.tick_size)
    stop = down(candidate.stop * (1 - policy.slippage_bps / 10000), instrument.tick_size)
    target = down(candidate.target * (1 - policy.slippage_bps / 10000), instrument.tick_size)
    loss = entry - stop + Charges().round_trip(entry, stop, 1)
    if (
        loss <= 0
        or quote.exchange_time > candidate.decision_time
        or quote.received_time > candidate.decision_time
    ):
        raise ValueError("invalid causal price/risk context")
    values = (
        (close - vwap) / close * 10000,
        (close - ema) / close * 10000,
        atr / close * 10000,
        volume,
        (candle.high - candle.low) / close * 10000,
        (close - candle.open) / candle.open * 10000,
        (quote.ask - quote.bid) / quote.bid * 10000,
        (quote.ask - close) / close * 10000,
        (entry - stop) / entry * 10000,
        (target - entry - Charges().round_trip(entry, target, 1)) / loss,
        d(str((candidate.decision_time - opened).total_seconds())) / 60,
        d(str(math.log1p(float(close * candle.volume)))),
    )
    return FeatureVector(
        symbol=candle.symbol,
        time=candidate.decision_time,
        candle_end=candle_end,
        candidate_sha256=candidate_fingerprint(candidate),
        values=tuple(float(value) for value in values),
    )
