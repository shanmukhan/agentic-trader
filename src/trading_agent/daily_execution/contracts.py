"""Daily strategy and feature identity; financially separate from intraday models."""

import hashlib
import json
import math
import tomllib
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator

from trading_agent.daily_research.analysis import DailyPolicy
from trading_agent.ml.features import Finite
from trading_agent.models import DomainModel, Symbol, utc

FEATURE_VERSION = "daily-delivery-features-v1"
FEATURE_NAMES = (
    "momentum_pct",
    "trend_distance_pct",
    "daily_volatility_pct",
    "log_average_turnover",
    "spread_bps",
    "entry_gap_bps",
    "stop_distance_bps",
    "target_distance_bps",
    "minutes_since_open",
    "log_price",
    "history_sessions",
    "gross_reward_risk",
)


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


class DailyStrategy(DomainModel):
    version: Literal["daily-delivery-momentum-v1"] = "daily-delivery-momentum-v1"
    screen: DailyPolicy = DailyPolicy()
    stop_pct: Decimal = Field(default=Decimal(2), gt=0, le=30, allow_inf_nan=False)
    target_pct: Decimal = Field(default=Decimal(4), gt=0, le=100, allow_inf_nan=False)
    max_entry_gap_bps: Decimal = Field(default=Decimal(100), gt=0, le=5000, allow_inf_nan=False)
    max_hold_sessions: int = Field(default=20, ge=1, le=252, strict=True)
    max_open_quote_gap_seconds: int = Field(default=30, ge=1, le=21600, strict=True)
    max_active_labels: int = Field(default=32, ge=1, le=64, strict=True)
    max_samples: int = Field(default=2000, ge=1, le=10000, strict=True)

    @classmethod
    def load(cls, path: Path) -> "DailyStrategy":
        with path.open("rb") as file:
            return cls.model_validate(tomllib.load(file))

    def digest(self) -> str:
        return digest(self.model_dump(mode="json"))


class DailyVector(DomainModel):
    version: Literal["daily-delivery-features-v1"] = "daily-delivery-features-v1"
    symbol: Symbol
    time: datetime
    daily_session: date
    available_at: datetime
    candidate_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    values: tuple[Finite, ...] = Field(min_length=12, max_length=12)

    @field_validator("time", "available_at")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        return utc(value)

    @model_validator(mode="after")
    def causal(self) -> "DailyVector":
        from trading_agent.market_data.calendar import IST

        if self.available_at > self.time or self.daily_session >= self.time.astimezone(IST).date():
            raise ValueError("daily features require a prior completed available session")
        return self


class DailySample(DomainModel):
    id: str = Field(pattern=r"^[a-f0-9]{64}$")
    features: DailyVector
    label_end: datetime
    target: Literal[0, 1]
    net_pnl: Decimal = Field(allow_inf_nan=False)
    exit_reason: str = Field(min_length=1, max_length=100)

    @field_validator("label_end")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        return utc(value)

    @field_validator("target", mode="before")
    @classmethod
    def binary(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("target must be an integer binary label")
        return value

    @model_validator(mode="after")
    def interval(self) -> "DailySample":
        if self.label_end <= self.features.time or self.target != int(
            self.exit_reason == "TARGET" and self.net_pnl > 0
        ):
            raise ValueError(
                "daily label interval/outcome differs from completed net target semantics"
            )
        return self


def finite_features(values: tuple[Decimal | int | float, ...]) -> tuple[float, ...]:
    result = tuple(float(value) for value in values)
    if any(not math.isfinite(value) or abs(value) > 1e9 for value in result):
        raise ValueError("daily feature exceeds its finite supported range")
    return result
