"""Validated domain values. Money is Decimal; public timestamps must be timezone-aware."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

IST_NAME = "Asia/Kolkata"
Money = Annotated[Decimal, Field(gt=0, max_digits=16, decimal_places=4, allow_inf_nan=False)]
Symbol = Annotated[str, Field(pattern=r"^NSE:[A-Z0-9&_.-]{1,30}$")]


def utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("timezone-aware timestamp required")
    return value.astimezone(UTC)


def stamp(value: datetime) -> str:
    return utc(value).isoformat(timespec="microseconds")


class DomainModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Quote(DomainModel):
    symbol: Symbol
    token: int = Field(gt=0, strict=True)
    exchange_time: datetime
    received_time: datetime
    last: Money
    bid: Money
    ask: Money
    bid_size: int = Field(ge=0, strict=True)
    ask_size: int = Field(ge=0, strict=True)
    volume: int = Field(ge=0, strict=True)  # cumulative session volume, NOT tick volume
    source: Literal["kite", "replay"] = "replay"

    @field_validator("exchange_time", "received_time")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        return utc(value)

    @model_validator(mode="after")
    def valid(self) -> "Quote":
        if self.ask < self.bid:
            raise ValueError("crossed market")
        if self.exchange_time > self.received_time + timedelta(seconds=1):
            raise ValueError("exchange clock is ahead of receipt")
        return self

    def ordered_kite_second_update(self, previous: "Quote") -> bool:
        """Kite has whole-second exchange clocks; socket receipt orders book updates.

        This does not advance exchange time or grant a second fill/liquidity budget.
        Replay inputs retain their strict exchange-time ordering.
        """
        return (
            self.source == previous.source == "kite"
            and self.symbol == previous.symbol
            and self.token == previous.token
            and self.exchange_time == previous.exchange_time
            and self.exchange_time.microsecond == 0
            and self.received_time > previous.received_time
        )


class Candidate(DomainModel):
    intent_id: str = Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.:-]+$")
    symbol: Symbol
    stop: Money
    target: Money
    decision_time: datetime
    reason: str = Field(min_length=1, max_length=300)
    requires_ml: bool = False
    model_version: str = Field(default="phase1-stub", min_length=1, max_length=128)

    @field_validator("decision_time")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        return utc(value)


class Candle(DomainModel):
    symbol: Symbol
    start: datetime
    minutes: Literal[1, 5]
    open: Money
    high: Money
    low: Money
    close: Money
    volume: int = Field(ge=0, strict=True)
    completed: bool = True
    quality: str = "ok"

    @field_validator("start")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        return utc(value)

    @model_validator(mode="after")
    def valid(self) -> "Candle":
        if self.low > min(self.open, self.close) or self.high < max(self.open, self.close):
            raise ValueError("inconsistent OHLC")
        if self.low > self.high or self.start.second or self.start.microsecond:
            raise ValueError("invalid candle bounds")
        if self.start.minute % self.minutes:
            raise ValueError("unaligned candle")
        return self


class Instrument(DomainModel):
    symbol: Symbol
    token: int = Field(gt=0, strict=True)
    tick_size: Money
    lot_size: Literal[1] = 1


class RiskDecision(DomainModel):
    allowed: bool
    reasons: tuple[str, ...]
    quantity: int = 0
    price_cap: Decimal = Decimal("0")
    cash_reservation: Decimal = Decimal("0")
    risk_reservation: Decimal = Decimal("0")
