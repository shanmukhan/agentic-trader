"""Explicit TOML configuration. Environment may only supply mode, path and secrets."""

import os
import tomllib
from datetime import time
from decimal import Decimal
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator


class Settings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    mode: Literal["paper"] = "paper"
    investment_horizon: Literal["intraday", "long_term"] = "intraday"
    long_term_drawdown_limit: Decimal = Field(default=Decimal("2500.00"), gt=0)
    database: Path = Path("data/paper.sqlite3")
    host: Literal["127.0.0.1", "::1"] = "127.0.0.1"
    port: int = Field(default=8000, ge=1024, le=65535)
    public_origin: str = ""
    public_path: str = Field(default="", pattern=r"^(?:/[a-z][a-z0-9-]*)?$")
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
    stream_limit: int = Field(default=10, ge=1, le=3000, strict=True)
    stream_tokens: tuple[Annotated[int, Field(gt=0, strict=True)], ...] = ()
    operator_token: SecretStr = SecretStr("")

    @model_validator(mode="after")
    def validate_policy(self) -> "Settings":
        if self.public_origin:
            origin = urlsplit(self.public_origin)
            if (
                origin.scheme != "https"
                or not origin.hostname
                or origin.username is not None
                or origin.password is not None
                or origin.path
                or origin.query
                or origin.fragment
                or origin.netloc != origin.hostname
                or self.public_origin != "https://" + origin.hostname
                or not origin.hostname.isascii()
                or not all(c.isalnum() or c in ".-" for c in origin.hostname)
            ):
                raise ValueError(
                    "public_origin must be an exact HTTPS hostname without path or port"
                )
        if self.public_path and not self.public_origin:
            raise ValueError("public_path requires an explicit HTTPS public_origin")
        values = (
            self.starting_cash,
            self.max_trade_risk,
            self.daily_loss_limit,
            self.max_position_notional,
            self.max_total_notional,
            self.slippage_bps,
            self.max_spread_bps,
            self.long_term_drawdown_limit,
        )
        if any(not value.is_finite() for value in values):
            raise ValueError("non-finite policy value")
        if not time(9, 15) <= self.entry_start < self.entry_end < self.flatten_at <= time(15, 30):
            raise ValueError("invalid NSE session policy")
        if not self.max_trade_risk <= self.daily_loss_limit < self.starting_cash:
            raise ValueError("invalid loss budgets")
        if not self.max_position_notional <= self.max_total_notional <= self.starting_cash:
            raise ValueError("unleveraged exposure limits required")
        if self.investment_horizon == "long_term" and not (
            self.daily_loss_limit <= self.long_term_drawdown_limit < self.starting_cash
        ):
            raise ValueError("long-term drawdown limit must cover daily loss and be below capital")
        if self.order_ttl_seconds * 1000 <= self.latency_ms:
            raise ValueError("order TTL must exceed latency")
        if (
            any(token <= 0 for token in self.stream_tokens)
            or len(self.stream_tokens) > self.stream_limit
            or len(set(self.stream_tokens)) != len(self.stream_tokens)
        ):
            raise ValueError(
                f"provide up to {self.stream_limit} distinct positive instrument tokens"
            )
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
        for name in ("public_origin", "public_path"):
            if os.environ.get("TRADING_" + name.upper()):
                values[name] = os.environ["TRADING_" + name.upper()]
        return cls.model_validate(values)
