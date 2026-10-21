"""Server-selected reviewed data policy; browser requests cannot supply filesystem paths."""

import hashlib
import json
import tomllib
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator

from trading_agent.daily_execution.contracts import DailyStrategy
from trading_agent.models import DomainModel, Symbol, utc
from trading_agent.strategy.rules import StrategySettings


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


class ShareReview(DomainModel):
    symbol: Symbol
    kind: Literal["equity_share"]
    reviewed_at: datetime
    reference: str = Field(min_length=3, max_length=300)

    @field_validator("reviewed_at")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        return utc(value)


class AnalysisProfile(DomainModel):
    name: str = Field(min_length=3, max_length=100)
    daily_dataset: Path
    shares: tuple[ShareReview, ...] = Field(min_length=1, max_length=500)
    strategy_mode: Literal["rules", "rules_ml"] = "rules_ml"
    model_directory: Path | None = None
    intraday: StrategySettings = StrategySettings()
    long_term: DailyStrategy = DailyStrategy()
    approval_seconds: int = Field(default=120, ge=15, le=300, strict=True)
    max_price_drift_bps: Decimal = Field(default=Decimal(20), gt=0, le=100)
    max_model_age_days: int = Field(default=30, ge=1, le=365, strict=True)

    @classmethod
    def load(cls, path: Path) -> "AnalysisProfile":
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 2_000_000:
            raise ValueError("Analysis profile must be a bounded regular local TOML file.")
        with path.open("rb") as file:
            profile = cls.model_validate(tomllib.load(file))
        if len({s.symbol for s in profile.shares}) != len(profile.shares):
            raise ValueError("Analysis share reviews must be unique.")
        return profile


class ModeRequest(DomainModel):
    mode: Literal["manual", "approval", "automatic"]
    revision: str = Field(pattern=r"^[a-f0-9]{32}$")
    acknowledged: bool = Field(strict=True)

    @model_validator(mode="after")
    def acknowledged_mode(self) -> "ModeRequest":
        if not self.acknowledged:
            raise ValueError("Explicit mode acknowledgement is required.")
        return self


class DecisionAction(DomainModel):
    preview_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
