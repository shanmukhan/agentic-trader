"""Validate stored research diagnostics without importing training dependencies."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from trading_agent.ml.contracts import ValidationIdentity
from trading_agent.ml.schema import TrainingSettings
from trading_agent.models import DomainModel, utc

Probability = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
StrictBool = Annotated[bool, Field(strict=True)]


class ReliabilityBin(DomainModel):
    lower: Probability
    upper: Probability
    count: int = Field(ge=0)
    mean_probability: Probability | None
    fraction_positive: Probability | None

    @model_validator(mode="after")
    def populated(self) -> "ReliabilityBin":
        if (self.mean_probability is not None) != bool(self.count) or (
            self.fraction_positive is not None
        ) != bool(self.count):
            raise ValueError("invalid reliability bin population")
        if (
            self.mean_probability is not None
            and not self.lower <= self.mean_probability <= self.upper
        ):
            raise ValueError("probability lies outside its reliability bin")
        return self


class Metrics(DomainModel):
    count: int = Field(ge=1)
    positive_count: int = Field(ge=0)
    roc_auc: Probability | None
    brier: Probability
    baseline_probability_from_training_only: Probability
    baseline_brier: Probability
    log_loss: float = Field(ge=0, allow_inf_nan=False)
    expected_calibration_error: Probability
    reliability_bins: tuple[ReliabilityBin, ...] = Field(min_length=10, max_length=10)
    selected_count: int = Field(ge=0)
    selected_net_pnl: Decimal = Field(allow_inf_nan=False)
    gates: dict[str, StrictBool]
    passed: StrictBool

    def verify(self, cfg: TrainingSettings) -> bool:
        expected = {
            "sample_count": self.count >= cfg.min_evaluation_samples,
            "both_classes": min(self.positive_count, self.count - self.positive_count)
            >= cfg.min_class_samples,
            "auc": self.roc_auc is not None and self.roc_auc >= cfg.min_auc,
            "brier_over_train_baseline": self.brier < self.baseline_brier,
            "calibration": self.expected_calibration_error <= cfg.max_calibration_error,
            "selected_count": self.selected_count >= cfg.min_selected_samples,
            "selected_counterfactual_pnl": self.selected_net_pnl > 0,
        }
        if (
            self.positive_count > self.count
            or self.selected_count > self.count
            or sum(item.count for item in self.reliability_bins) != self.count
        ):
            raise ValueError("inconsistent validation counts")
        error = 0.0
        for index, item in enumerate(self.reliability_bins):
            if item.lower != index / 10 or item.upper != (index + 1) / 10:
                raise ValueError("invalid reliability bin bounds")
            if (
                item.count
                and item.mean_probability is not None
                and item.fraction_positive is not None
            ):
                error += (
                    item.count / self.count * abs(item.mean_probability - item.fraction_positive)
                )
        if abs(error - self.expected_calibration_error) > 1e-10:
            raise ValueError("inconsistent calibration error")
        if self.gates != expected or self.passed != all(expected.values()):
            raise ValueError("stored gates disagree with validation metrics")
        return self.passed


class SplitDiagnostics(DomainModel):
    name: str
    train_count: int = Field(ge=1)
    calibration_count: int = Field(ge=1)
    train_first: datetime
    train_last: datetime
    train_label_end: datetime
    calibration_first: datetime
    calibration_last: datetime
    calibration_label_end: datetime
    evaluation_first: datetime
    evaluation_last: datetime
    evaluation_label_end: datetime
    purged_train: int = Field(ge=0)
    purged_calibration: int = Field(ge=0)
    metrics: Metrics

    @field_validator(
        "train_first",
        "train_last",
        "train_label_end",
        "calibration_first",
        "calibration_last",
        "calibration_label_end",
        "evaluation_first",
        "evaluation_last",
        "evaluation_label_end",
    )
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        return utc(value)


class ValidationReport(DomainModel):
    schema_version: Literal[1]
    ready_for_live: Literal[False]
    research_approved: StrictBool
    model_sha256: str
    training_sha256: str
    settings: TrainingSettings
    samples_manifest_sha256: str
    samples_counts: dict[str, int]
    source_available_through: datetime
    validation_session_end: datetime
    synthetic: StrictBool
    runtime: dict[str, str]
    gates: dict[str, StrictBool]
    splits: tuple[SplitDiagnostics, ...] = Field(min_length=3, max_length=11)

    @field_validator("source_available_through", "validation_session_end")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        return utc(value)

    def verify(self, artifact: ValidationIdentity, version: str) -> None:
        cfg = self.settings
        if (
            self.model_sha256 != version
            or self.training_sha256 != cfg.digest()
            or self.training_sha256 != artifact.training_sha256
            or self.samples_manifest_sha256 != artifact.samples_manifest_sha256
            or self.synthetic != artifact.synthetic
            or cfg.embargo_minutes != artifact.embargo_minutes
            or cfg.probability_threshold != artifact.threshold
        ):
            raise ValueError("validation and artifact identity differ")
        if len(self.splits) != cfg.walk_forward_folds + 1:
            raise ValueError("validation fold count mismatch")
        passed = []
        for index, split in enumerate(self.splits):
            expected_name = "holdout" if index == len(self.splits) - 1 else f"fold_{index + 1}"
            gap = timedelta(minutes=cfg.embargo_minutes)
            if (
                split.name != expected_name
                or split.train_count < cfg.min_train_samples
                or split.calibration_count < cfg.min_calibration_samples
                or not split.train_first <= split.train_last < split.train_label_end
                or not split.calibration_first
                <= split.calibration_last
                < split.calibration_label_end
                or not split.evaluation_first <= split.evaluation_last < split.evaluation_label_end
                or split.train_label_end + gap >= split.calibration_first
                or split.calibration_label_end + gap >= split.evaluation_first
            ):
                raise ValueError("invalid chronological validation window or sample count")
            passed.append(split.metrics.verify(cfg))
        expected = {
            "walk_forward": all(passed[:-1]),
            "holdout": passed[-1],
            "non_synthetic": not artifact.synthetic,
        }
        if self.gates != expected or self.research_approved != all(expected.values()):
            raise ValueError("validation summary differs from diagnostic gates")
        final = self.splits[-1]
        if (
            artifact.fit_label_end != max(final.train_label_end, final.calibration_label_end)
            or artifact.validation_label_end != final.evaluation_label_end
            or artifact.validated_through
            != max(
                final.evaluation_label_end,
                self.source_available_through,
                self.validation_session_end,
            )
        ):
            raise ValueError("model availability differs from validation evidence")
