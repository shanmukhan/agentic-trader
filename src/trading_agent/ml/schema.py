"""Typed interval labels and predeclared training/validation policy."""

import hashlib
import json
import tomllib
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import ConfigDict, Field, field_validator, model_validator

from trading_agent.ml.features import FeatureVector
from trading_agent.models import DomainModel, utc


class LabelPolicy(DomainModel):
    horizon_minutes: int = Field(default=30, ge=1, le=120)
    max_active: int = Field(default=100, ge=1, le=100)


class Sample(DomainModel):
    id: str = Field(min_length=1, max_length=100)
    features: FeatureVector
    label_end: datetime
    target: Literal[0, 1]
    net_pnl: Decimal = Field(allow_inf_nan=False)
    exit_reason: Literal["TARGET", "STOP", "LABEL_TIME_LIMIT", "SESSION_END"]

    @field_validator("target", mode="before")
    @classmethod
    def strict_target(cls, value: object) -> object:
        if type(value) is not int:
            raise ValueError("target must be an integer binary outcome")
        return value

    @field_validator("label_end")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        return utc(value)

    @model_validator(mode="after")
    def interval(self) -> "Sample":
        if self.label_end <= self.features.time:
            raise ValueError("label interval must end after its decision")
        expected = int(self.exit_reason == "TARGET" and self.net_pnl > 0)
        if self.target != expected:
            raise ValueError("target must mean a profitable target exit before stop/time")
        return self


class TrainingSettings(DomainModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)
    min_train_sessions: int = Field(default=30, ge=5)
    calibration_sessions: int = Field(default=10, ge=2)
    validation_sessions: int = Field(default=10, ge=2)
    walk_forward_folds: int = Field(default=3, ge=2, le=10)
    holdout_sessions: int = Field(default=20, ge=2)
    embargo_minutes: int = Field(default=30, ge=1, le=1440)
    min_train_samples: int = Field(default=100, ge=10)
    min_calibration_samples: int = Field(default=30, ge=4)
    min_evaluation_samples: int = Field(default=30, ge=4)
    min_class_samples: int = Field(default=5, ge=2)
    min_selected_samples: int = Field(default=10, ge=2)
    probability_threshold: float = Field(default=0.6, gt=0.5, lt=1)
    min_auc: float = Field(default=0.55, ge=0.5, le=1)
    max_calibration_error: float = Field(default=0.15, gt=0, le=0.5)
    regularization_c: float = Field(default=1, gt=0, le=100)
    max_iterations: int = Field(default=2000, ge=100, le=10000)

    @classmethod
    def load(cls, path: Path) -> "TrainingSettings":
        with path.open("rb") as file:
            return cls.model_validate(tomllib.load(file))

    def digest(self) -> str:
        return hashlib.sha256(json.dumps(self.model_dump(), sort_keys=True).encode()).hexdigest()
