"""Predeclared paper operations policy; economic limits remain in Settings."""

import hashlib
import json
import tomllib
from pathlib import Path

from pydantic import Field

from trading_agent.models import DomainModel, Instrument
from trading_agent.strategy.rules import RULE_VERSION, StrategySettings

RUNTIME_VERSION = "supervised-paper-feed-v1"


class FeedSettings(DomainModel):
    history_retry_seconds: int = Field(default=5, ge=1, le=60, strict=True)
    history_spacing_ms: int = Field(default=400, ge=350, le=5000, strict=True)
    telemetry_seconds: int = Field(default=60, ge=1, le=3600, strict=True)
    processing_budget_ms: int = Field(default=50, ge=1, le=1000, strict=True)
    max_model_age_days: int = Field(default=30, ge=1, le=365, strict=True)
    evidence_min_sessions: int = Field(default=20, ge=20, le=1000, strict=True)
    evidence_min_trades: int = Field(default=30, ge=30, le=10000, strict=True)

    @classmethod
    def load(cls, path: Path) -> "FeedSettings":
        with path.open("rb") as file:
            return cls.model_validate(tomllib.load(file))

    def digest(self) -> str:
        return hashlib.sha256(json.dumps(self.model_dump(), sort_keys=True).encode()).hexdigest()


def feed_identity(
    instruments: list[Instrument],
    strategy: StrategySettings,
    settings: FeedSettings,
    model_version: str | None,
    synthetic: bool,
) -> tuple[dict, str]:
    identity = {
        "version": RUNTIME_VERSION,
        "rule_version": RULE_VERSION,
        "strategy": strategy.model_dump(mode="json"),
        "feed_policy": settings.model_dump(),
        "instruments": [
            item.model_dump(mode="json") for item in sorted(instruments, key=lambda i: i.symbol)
        ],
        "model_sha256": model_version,
        "synthetic": synthetic,
    }
    return identity, hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
