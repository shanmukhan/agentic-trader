"""Bounded corporate-action input; ratios and net receipts are never inferred."""

import hashlib
import json
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from pydantic import Field, field_validator, model_validator

from trading_agent.models import DomainModel, Symbol, stamp, utc

Identifier = Annotated[str, Field(pattern=r"^[A-Za-z0-9_.:-]{1,100}$")]
Reference = Annotated[str, Field(min_length=3, max_length=500, pattern=r".*\S.*")]
Cash = Annotated[Decimal, Field(ge=0, max_digits=16, decimal_places=2, allow_inf_nan=False)]


def plain(value: Any) -> Any:
    """Canonicalize typed input for stable economic idempotency across decimal scales."""

    def scalar(item: Any) -> str:
        if isinstance(item, Decimal):
            return format(item.normalize(), "f")
        if isinstance(item, datetime):
            return stamp(item)
        if isinstance(item, date):
            return item.isoformat()
        raise TypeError("unsupported corporate-action value")

    return json.loads(json.dumps(value, default=scalar, sort_keys=True))


def digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(plain(value), sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


class Action(DomainModel):
    action_id: Identifier
    ex_date: date
    record_date: date
    announced_at: datetime
    reference: Reference

    @field_validator("announced_at")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        return utc(value)

    @model_validator(mode="after")
    def dates(self) -> "Action":
        from trading_agent.market_data.calendar import IST

        if (
            self.record_date < self.ex_date
            or self.announced_at.astimezone(IST).date() > self.ex_date
        ):
            raise ValueError("reviewed ex/record/announcement dates are inconsistent")
        return self


class ShareAction(Action):
    kind: Literal["split", "bonus"]
    numerator: int = Field(gt=0, le=10000, strict=True)
    denominator: int = Field(gt=0, le=10000, strict=True)
    credit_date: date

    @model_validator(mode="after")
    def shares(self) -> "ShareAction":
        if self.kind == "split" and self.numerator <= self.denominator:
            raise ValueError("split ratio is new shares per old share and must increase shares")
        if self.credit_date < self.record_date:
            raise ValueError("share credit cannot precede record date")
        return self


class DividendAction(Action):
    kind: Literal["dividend"]
    per_share: Cash = Field(gt=0)
    withholding: Cash  # reviewed total deduction for this paper entitlement, not a tax estimate
    payment_date: date

    @model_validator(mode="after")
    def payment(self) -> "DividendAction":
        if self.payment_date < self.record_date:
            raise ValueError("dividend payment cannot precede record date")
        return self


class ActionBatch(DomainModel):
    batch_id: Identifier
    symbol: Symbol
    quarantine_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    reviewed_at: datetime
    reference: Reference
    covers_all_actions: Literal[True]
    actions: tuple[Annotated[ShareAction | DividendAction, Field(discriminator="kind")], ...] = (
        Field(min_length=1, max_length=20)
    )

    @field_validator("reviewed_at")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        return utc(value)

    @field_validator("covers_all_actions", mode="before")
    @classmethod
    def complete(cls, value: Any) -> Literal[True]:
        if value is not True:
            raise ValueError("explicit true coverage assertion required")
        return True

    @model_validator(mode="after")
    def ordered(self) -> "ActionBatch":
        if len({action.action_id for action in self.actions}) != len(self.actions):
            raise ValueError("duplicate action identity in batch")
        days = [action.ex_date for action in self.actions]
        if days != sorted(days) or any(
            action.announced_at > self.reviewed_at for action in self.actions
        ):
            raise ValueError("actions must be chronological and announced before review")
        return self


class CashReceipt(DomainModel):
    payment_id: Identifier
    claim_id: Identifier
    paid_date: date
    net_amount: Cash
    reviewed_at: datetime
    reference: Reference

    @field_validator("reviewed_at")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        return utc(value)
