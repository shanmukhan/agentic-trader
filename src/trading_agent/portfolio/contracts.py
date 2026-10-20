"""Immutable reviewed instructions; no automatic funding or investment selection."""

import hashlib
import json
from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import Field, model_validator

from trading_agent.models import DomainModel, Money, Symbol

Identifier = Annotated[str, Field(min_length=1, max_length=100, pattern=r"^[A-Za-z0-9_.:-]+$")]
Reference = Annotated[str, Field(min_length=3, max_length=300, pattern=r".*\S.*")]
Budget = Annotated[
    Decimal, Field(gt=0, le=10_000_000, max_digits=10, decimal_places=2, allow_inf_nan=False)
]


def plain(value: DomainModel) -> dict:
    from trading_agent.corporate_actions.contracts import plain as canonical

    return canonical(value.model_dump())


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


class Contribution(DomainModel):
    intent_id: Identifier
    symbol: Symbol
    budget: Budget
    reference: Reference
    stop: Money | None = None
    target: Money | None = None
    plan_id: Identifier | None = None
    occurrence: date | None = None

    @model_validator(mode="after")
    def context(self) -> "Contribution":
        if (self.stop is None) != (self.target is None):
            raise ValueError("provide both new-holding stop and target, or neither")
        if (self.plan_id is None) != (self.occurrence is None):
            raise ValueError("plan and occurrence must be supplied together")
        if self.plan_id and (self.stop is not None or self.target is not None):
            raise ValueError("SIP protections come from the saved plan or existing holding")
        return self


class Approval(DomainModel):
    request: Contribution
    preview_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class SIPPlan(DomainModel):
    plan_id: Identifier
    symbol: Symbol
    budget: Budget
    sessions: tuple[date, ...] = Field(min_length=1, max_length=120)
    stop_pct: Decimal = Field(gt=0, le=50, max_digits=6, decimal_places=2, allow_inf_nan=False)
    target_pct: Decimal = Field(gt=0, le=100, max_digits=6, decimal_places=2, allow_inf_nan=False)
    reference: Reference

    @model_validator(mode="after")
    def ordered(self) -> "SIPPlan":
        if self.sessions != tuple(sorted(set(self.sessions))):
            raise ValueError("SIP session dates must be unique and increasing")
        return self


class CancelPlan(DomainModel):
    plan_id: Identifier
    reference: Reference


def occurrence_request(plan: SIPPlan, day: date) -> Contribution:
    return Contribution(
        intent_id="sip-" + digest([plan.plan_id, day.isoformat()])[:48],
        symbol=plan.symbol,
        budget=plan.budget,
        reference=plan.reference,
        plan_id=plan.plan_id,
        occurrence=day,
    )
