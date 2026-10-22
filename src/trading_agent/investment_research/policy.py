"""Strict, versioned investment-policy drafts without execution authority.

Specifying every value records an operator's proposed policy. It does not prove
the strategy, establish data coverage, activate an account or enable a replay.
The semantic identity intentionally excludes the display label and storage data.
"""

import hashlib
import json
import re
from decimal import ROUND_HALF_EVEN, Context, Decimal, Inexact, localcontext
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator, model_validator

SCHEMA_VERSION = 1
POLICY_FAMILY = "nse-investment-policy-v2"
DECISION_SEMANTICS = "investment-decisions-v2.1"
HASH_DOMAIN = "agentic-trader.investment-policy"


def _choice(name: str, label: str, group: str, *options: tuple[str, str]) -> dict[str, Any]:
    return {
        "name": name,
        "label": label,
        "group": group,
        "kind": "choice",
        "choices": [{"value": value, "label": text} for value, text in options],
    }


def _integer(
    name: str, label: str, group: str, minimum: int, maximum: int, unit: str
) -> dict[str, Any]:
    return {
        "name": name,
        "label": label,
        "group": group,
        "kind": "integer",
        "minimum": minimum,
        "maximum": maximum,
        "step": 1,
        "unit": unit,
    }


def _decimal(
    name: str,
    label: str,
    group: str,
    minimum: str,
    maximum: str,
    *,
    unit: str = "%",
    scale: int = 4,
    exclusive_minimum: bool = False,
    exclusive_maximum: bool = False,
) -> dict[str, Any]:
    return {
        "name": name,
        "label": label,
        "group": group,
        "kind": "decimal",
        "minimum": minimum,
        "maximum": maximum,
        "step": "0.01" if scale == 2 else "0.0001",
        "scale": scale,
        "unit": unit,
        "exclusive_minimum": exclusive_minimum,
        "exclusive_maximum": exclusive_maximum,
    }


POLICY_FIELDS: list[dict[str, Any]] = [
    _choice(
        "horizon_unit",
        "Holding horizon unit",
        "Horizon and reviews",
        ("months", "Months"),
        ("years", "Years"),
    ),
    {
        **_integer(
            "horizon_count",
            "Holding horizon",
            "Horizon and reviews",
            1,
            1200,
            "selected horizon units",
        ),
        "unit_limits": {
            "months": {"minimum": 1, "maximum": 1200},
            "years": {"minimum": 1, "maximum": 100},
        },
    },
    _choice(
        "review_cadence",
        "Review cadence",
        "Horizon and reviews",
        ("monthly", "Monthly"),
        ("quarterly", "Quarterly"),
    ),
    _choice(
        "review_session_rule",
        "Review session",
        "Horizon and reviews",
        ("first_reviewed_session", "First reviewed exchange session in the period"),
        ("last_reviewed_session", "Last reviewed exchange session in the period"),
    ),
    _choice(
        "missed_cycle_policy",
        "Missed review cycle",
        "Horizon and reviews",
        ("skip", "Skip the missed cycle"),
    ),
    _choice(
        "price_basis",
        "Screening price basis",
        "Screening",
        ("share_adjusted_close", "Share-adjusted daily close"),
    ),
    _choice("strategy_mode", "Strategy mode", "Screening", ("rules_only", "Rules only")),
    _integer("momentum_sessions", "Momentum lookback", "Screening", 2, 1000, "sessions"),
    _integer("trend_sessions", "Trend lookback", "Screening", 2, 1000, "sessions"),
    _decimal("min_momentum_pct", "Minimum momentum", "Screening", "-100", "10000"),
    _decimal(
        "min_average_turnover",
        "Minimum average daily turnover",
        "Screening",
        "0",
        "1000000000000",
        unit="INR",
        scale=2,
    ),
    _decimal(
        "max_daily_volatility_pct",
        "Maximum daily volatility",
        "Screening",
        "0",
        "100",
        exclusive_minimum=True,
    ),
    _decimal("cash_reserve_pct", "Minimum cash reserve", "Allocation", "0", "100"),
    _decimal(
        "max_invested_pct",
        "Maximum invested allocation",
        "Allocation",
        "0",
        "100",
        exclusive_minimum=True,
    ),
    _decimal(
        "max_stock_weight_pct",
        "Maximum weight per stock",
        "Allocation",
        "0",
        "100",
        exclusive_minimum=True,
    ),
    _decimal(
        "max_sector_weight_pct",
        "Maximum weight per sector",
        "Allocation",
        "0",
        "100",
        exclusive_minimum=True,
    ),
    _integer("max_positions", "Maximum held stocks", "Allocation", 1, 10, "stocks"),
    _choice(
        "unknown_sector_policy",
        "Unknown sector",
        "Allocation",
        ("block_new_entries", "Block new entries until the sector is known"),
    ),
    _decimal(
        "max_entry_gap_bps",
        "Maximum entry price gap",
        "Execution and exits",
        "0",
        "5000",
        unit="basis points",
        exclusive_minimum=True,
    ),
    _decimal(
        "stop_pct",
        "Stop-loss distance",
        "Execution and exits",
        "0",
        "100",
        exclusive_minimum=True,
        exclusive_maximum=True,
    ),
    _decimal(
        "target_pct",
        "Profit-target distance",
        "Execution and exits",
        "0",
        "1000",
        exclusive_minimum=True,
    ),
    _decimal(
        "max_drawdown_pct",
        "Maximum portfolio drawdown",
        "Execution and exits",
        "0",
        "100",
        exclusive_minimum=True,
    ),
    _choice(
        "screen_exit",
        "Stock fails the review screen",
        "Execution and exits",
        ("request_exit", "Request an exit"),
        ("hold", "Continue holding"),
    ),
    _choice(
        "universe_exit",
        "Stock leaves the reviewed universe",
        "Execution and exits",
        ("request_exit", "Request an exit"),
        ("block_for_review", "Block for operator review"),
    ),
    _choice(
        "horizon_action",
        "Holding horizon reached",
        "Execution and exits",
        ("request_exit", "Request an exit"),
        ("review_only", "Require a review"),
    ),
]

_SPECS = {row["name"]: row for row in POLICY_FIELDS}
_DECIMAL_TEXT = re.compile(r"[+-]?(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]{1,3})?\Z")
_CONTEXT = Context(prec=34, rounding=ROUND_HALF_EVEN)
_CONTEXT.traps[Inexact] = True


class PolicyParameters(BaseModel):
    """Every financial and scheduling input is unset until explicitly supplied."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    horizon_unit: Literal["months", "years"] | None = None
    horizon_count: int | None = None
    review_cadence: Literal["monthly", "quarterly"] | None = None
    review_session_rule: Literal["first_reviewed_session", "last_reviewed_session"] | None = None
    missed_cycle_policy: Literal["skip"] | None = None
    price_basis: Literal["share_adjusted_close"] | None = None
    strategy_mode: Literal["rules_only"] | None = None
    momentum_sessions: int | None = None
    trend_sessions: int | None = None
    min_momentum_pct: str | None = None
    min_average_turnover: str | None = None
    max_daily_volatility_pct: str | None = None
    cash_reserve_pct: str | None = None
    max_invested_pct: str | None = None
    max_stock_weight_pct: str | None = None
    max_sector_weight_pct: str | None = None
    max_positions: int | None = None
    unknown_sector_policy: Literal["block_new_entries"] | None = None
    max_entry_gap_bps: str | None = None
    stop_pct: str | None = None
    target_pct: str | None = None
    max_drawdown_pct: str | None = None
    screen_exit: Literal["request_exit", "hold"] | None = None
    universe_exit: Literal["request_exit", "block_for_review"] | None = None
    horizon_action: Literal["request_exit", "review_only"] | None = None

    @field_validator("*", mode="before")
    @classmethod
    def validate_parameter(cls, value: Any, info: ValidationInfo) -> Any:
        if value is None:
            return None
        spec = _SPECS[info.field_name]
        if spec["kind"] == "integer" and (
            type(value) is not int or not spec["minimum"] <= value <= spec["maximum"]
        ):
            raise ValueError(
                f"{info.field_name} requires an integer from {spec['minimum']} "
                f"through {spec['maximum']}"
            )
        if spec["kind"] != "decimal":
            return value
        if not isinstance(value, str) or len(value) > 80 or not _DECIMAL_TEXT.fullmatch(value):
            raise ValueError(f"{info.field_name} requires an exact bounded decimal string")
        exponent = re.search(r"[eE]([+-]?[0-9]+)$", value)
        if exponent and abs(int(exponent.group(1))) > 18:
            raise ValueError("decimal exponent must be between -18 and 18")
        try:
            with localcontext(_CONTEXT):
                number = Decimal(value)
                minimum, maximum = Decimal(spec["minimum"]), Decimal(spec["maximum"])
                if (
                    not number.is_finite()
                    or number < minimum
                    or number > maximum
                    or (spec["exclusive_minimum"] and number == minimum)
                    or (spec["exclusive_maximum"] and number == maximum)
                ):
                    raise ValueError(f"{info.field_name} is outside its permitted range")
                canonical = number.quantize(Decimal(1).scaleb(-spec["scale"]))
                return format(canonical.copy_abs() if canonical.is_zero() else canonical, "f")
        except ArithmeticError:
            raise ValueError(
                f"{info.field_name} permits at most {spec['scale']} decimal places"
            ) from None

    @model_validator(mode="after")
    def validate_relationships(self) -> Self:
        if (
            self.horizon_unit == "years"
            and self.horizon_count is not None
            and self.horizon_count > 100
        ):
            raise ValueError("a years-based holding horizon cannot exceed 100 years")
        with localcontext(_CONTEXT):
            invested = self.max_invested_pct
            reserve = self.cash_reserve_pct
            if (
                invested is not None
                and reserve is not None
                and Decimal(invested) + Decimal(reserve) > 100
            ):
                raise ValueError("maximum invested allocation plus cash reserve exceeds 100%")
            stock = self.max_stock_weight_pct
            sector = self.max_sector_weight_pct
            for label, weight in (("stock", stock), ("sector", sector)):
                if (
                    invested is not None
                    and weight is not None
                    and Decimal(weight) > Decimal(invested)
                ):
                    raise ValueError(f"maximum {label} weight exceeds maximum invested allocation")
            if stock is not None and sector is not None and Decimal(stock) > Decimal(sector):
                raise ValueError("maximum stock weight exceeds maximum sector weight")
        return self


class InvestmentPolicyDraft(BaseModel):
    """A named draft, distinct from a live policy or a legacy replay policy."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    label: str | None = Field(default=None, max_length=120)
    parameters: PolicyParameters = Field(default_factory=PolicyParameters)

    @field_validator("label")
    @classmethod
    def normalize_label(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if any(ord(character) < 32 or ord(character) == 127 for character in value):
            raise ValueError("draft label cannot contain control characters")
        return value.strip() or None


def inspect_draft(payload: dict[str, Any]) -> dict[str, Any]:
    """Validate, canonicalize and identify a proposed policy without side effects."""
    draft = InvestmentPolicyDraft.model_validate(payload)
    parameters = draft.parameters.model_dump()
    missing = [row["name"] for row in POLICY_FIELDS if parameters[row["name"]] is None]
    identity = {
        "domain": HASH_DOMAIN,
        "schema_version": SCHEMA_VERSION,
        "family": POLICY_FAMILY,
        "decision_semantics": DECISION_SEMANTICS,
        "parameters": parameters,
    }
    digest = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
    ).hexdigest()
    return {
        "schema_version": SCHEMA_VERSION,
        "family": POLICY_FAMILY,
        "decision_semantics": DECISION_SEMANTICS,
        "parameters": parameters,
        "label": draft.label,
        "draft_sha256": digest,
        "policy_version_id": None if missing else digest,
        "state": "incomplete" if missing else "specified",
        "missing_fields": missing,
        "activation_supported": False,
        "backtest_supported": False,
        "limitations": [
            "A specified draft is a proposal, not an active or approved investment policy.",
            "This draft cannot activate an account, place orders or run a backtest.",
            "Investment decisions v2.1 and months-to-years execution are not implemented.",
            "Data coverage, sector classifications, fees and strategy suitability are unverified.",
        ],
    }
