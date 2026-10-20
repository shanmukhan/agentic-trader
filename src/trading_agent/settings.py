"""Explicit TOML configuration. Environment may only supply mode, path and secrets."""

import os
import tomllib
from datetime import time
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    mode: Literal["paper"] = "paper"
    database: Path = Path("data/paper.sqlite3")
    host: Literal["127.0.0.1", "::1"] = "127.0.0.1"
    port: int = Field(default=8000, ge=1024, le=65535)
    starting_cash: Decimal = Field(default=Decimal("25000"), gt=0, le=10000000)
    max_trade_risk: Decimal = Field(default=Decimal("62.50"), gt=0)
    daily_loss_limit: Decimal = Field(default=Decimal("250"), gt=0)
    max_position_notional: Decimal = Field(default=Decimal("10000"), gt=0)
    max_total_notional: Decimal = Field(default=Decimal("20000"), gt=0)
    max_positions: int = Field(default=2, ge=1, le=10)
    max_consecutive_losses: int = Field(default=3, ge=1, le=100)
    max_quote_age_seconds: int = Field(default=5, ge=1, le=60)
    max_spread_bps: Decimal = Field(default=Decimal("30"), gt=0, le=1000)
    slippage_bps: Decimal = Field(default=Decimal("5"), ge=0, le=1000)
    latency_ms: int = Field(default=100, ge=0, le=60000)
    order_ttl_seconds: int = Field(default=30, ge=1, le=300)
    entry_start: time = time(9, 30)
    entry_end: time = time(14, 30)
    flatten_at: time = time(15, 15)
    calendar: Path = Path("config/sessions.csv")
    stream_tokens: tuple[int, ...] = ()
    operator_token: SecretStr = SecretStr("")

    @model_validator(mode="after")
    def validate_policy(self) -> "Settings":
        values = (
            self.starting_cash,
            self.max_trade_risk,
            self.daily_loss_limit,
            self.max_position_notional,
            self.max_total_notional,
            self.slippage_bps,
            self.max_spread_bps,
        )
        if any(not value.is_finite() for value in values):
            raise ValueError("non-finite policy value")
        if not time(9, 15) <= self.entry_start < self.entry_end < self.flatten_at <= time(15, 30):
            raise ValueError("invalid NSE session policy")
        if not self.max_trade_risk <= self.daily_loss_limit < self.starting_cash:
            raise ValueError("invalid loss budgets")
        if not self.max_position_notional <= self.max_total_notional <= self.starting_cash:
            raise ValueError("unleveraged exposure limits required")
        if self.order_ttl_seconds * 1000 <= self.latency_ms:
            raise ValueError("order TTL must exceed latency")
        if any(token <= 0 for token in self.stream_tokens) or len(self.stream_tokens) > 10:
            raise ValueError("provide up to ten positive instrument tokens")
        token = self.operator_token.get_secret_value()
        if token and len(token) < 32:
            raise ValueError("operator token requires at least 32 characters")
        return self

    @classmethod
    def load(cls, path: str | Path | None = None) -> "Settings":
        selected = Path(path or os.environ.get("TRADING_CONFIG", "config/paper.toml"))
        with selected.open("rb") as file:
            values = tomllib.load(file)
        values["mode"] = os.environ.get("TRADING_MODE", values.get("mode", "paper"))
        values["operator_token"] = os.environ.get("TRADING_OPERATOR_TOKEN", "")
        return cls.model_validate(values)
