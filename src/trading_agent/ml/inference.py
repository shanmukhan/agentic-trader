"""Strict JSON-only model loading and constant-work inference; no NumPy/sklearn imports."""

import hashlib
import math
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator

from trading_agent.backtesting.dataset import digest_file
from trading_agent.ml.contracts import NumericVector
from trading_agent.ml.features import (
    FEATURE_NAMES,
    FEATURE_VERSION,
    FeatureVector,
    Finite,
    candidate_fingerprint,
)
from trading_agent.ml.schema import LabelPolicy
from trading_agent.models import Candidate, DomainModel, utc


class ModelUnavailable(ValueError):
    pass


class PhaseOneScorer:
    version = "phase1-stub"

    def score(self, features: dict[str, object]) -> float:
        raise ModelUnavailable("no verified model configured")


def sigmoid(value: float) -> float:
    if not math.isfinite(value):
        raise ModelUnavailable("non-finite model score")
    if value >= 0:
        return 1 / (1 + math.exp(-value))
    exp = math.exp(value)
    return exp / (1 + exp)


class Coefficients(DomainModel):
    means: tuple[Finite, ...]
    scales: tuple[Finite, ...]
    weights: tuple[Finite, ...]
    intercept: Finite
    calibration_slope: Finite
    calibration_intercept: Finite

    @model_validator(mode="after")
    def dimensions(self) -> "Coefficients":
        if any(
            len(values) != len(FEATURE_NAMES) for values in (self.means, self.scales, self.weights)
        ) or any(value <= 0 for value in self.scales):
            raise ValueError("invalid coefficient dimensions or nonpositive scaling")
        return self

    def probability(self, features: NumericVector) -> float:
        value = self.intercept + sum(
            (x - m) / s * w
            for x, m, s, w in zip(
                features.values, self.means, self.scales, self.weights, strict=True
            )
        )
        return sigmoid(self.calibration_slope * value + self.calibration_intercept)


class Artifact(DomainModel):
    schema_version: Literal[1] = 1
    algorithm: Literal["standardized-logistic-sigmoid-v1"] = "standardized-logistic-sigmoid-v1"
    feature_version: Literal["candidate-features-v1"] = "candidate-features-v1"
    feature_names: tuple[str, ...] = FEATURE_NAMES
    coefficients: Coefficients
    label_policy: LabelPolicy
    synthetic: bool = Field(strict=True)
    strategy_sha256: str
    policy_sha256: str
    charges_version: str
    samples_manifest_sha256: str
    training_sha256: str
    code_sha256: str
    fit_label_end: datetime
    validation_label_end: datetime
    validated_through: datetime
    available_after: datetime
    embargo_minutes: int = Field(ge=1, le=1440)
    threshold: Finite = Field(gt=0.5, lt=1)

    @field_validator(
        "fit_label_end", "validation_label_end", "validated_through", "available_after"
    )
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        return utc(value)

    @model_validator(mode="after")
    def identity(self) -> "Artifact":
        if self.feature_names != FEATURE_NAMES or self.feature_version != FEATURE_VERSION:
            raise ValueError("unsupported feature schema")
        if (
            not self.fit_label_end < self.validation_label_end <= self.validated_through
            or self.available_after
            != self.validated_through + timedelta(minutes=self.embargo_minutes)
        ):
            raise ValueError("invalid fit/validation/availability window")
        return self


class ArtifactManifest(DomainModel):
    schema_version: Literal[1] = 1
    model_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    validation_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class ResearchModel:
    def __init__(self, artifact: Artifact, version: str):
        self.artifact, self.version = artifact, version

    def score(self, features: FeatureVector) -> float:
        if features.time <= self.artifact.available_after:
            raise ModelUnavailable("model validation/embargo is not available at decision time")
        return self.artifact.coefficients.probability(features)

    def authorize(
        self,
        candidate: Candidate,
        features: FeatureVector | None,
        *,
        now: datetime,
        policy_sha256: str,
        charges_version: str,
    ) -> tuple[str, ...]:
        if not candidate.requires_ml:
            return ("MODEL_REQUIRED",)
        if (
            features is None
            or features.symbol != candidate.symbol
            or features.time != candidate.decision_time
            or features.time > now
            or features.candidate_sha256 != candidate_fingerprint(candidate)
        ):
            return ("MODEL_FEATURE_CONTEXT",)
        if (
            candidate.model_version != self.version
            or policy_sha256 != self.artifact.policy_sha256
            or charges_version != self.artifact.charges_version
        ):
            return ("MODEL_CONTEXT_MISMATCH",)
        try:
            probability = self.score(features)
        except ModelUnavailable:
            return ("MODEL_NOT_YET_AVAILABLE",)
        return () if probability >= self.artifact.threshold else ("MODEL_BELOW_THRESHOLD",)


def load_model(
    directory: Path,
    *,
    strategy_sha256: str,
    policy_sha256: str,
    charges_version: str,
    allow_synthetic: bool = False,
) -> ResearchModel:
    from trading_agent.ml.validation import ValidationReport

    root = directory.resolve()

    def read(name: str) -> bytes:
        path = root / name
        if path.is_symlink():
            raise ModelUnavailable("artifact files must be local")
        with path.open("rb") as file:
            raw = file.read(2_000_001)
        if len(raw) > 2_000_000:
            raise ModelUnavailable("oversized model artifact")
        return raw

    manifest_raw = read("manifest.json")
    manifest = ArtifactManifest.model_validate_json(manifest_raw)
    raw, validation_raw = read("model.json"), read("validation.json")
    version = hashlib.sha256(raw).hexdigest()
    if (
        version != manifest.model_sha256
        or hashlib.sha256(validation_raw).hexdigest() != manifest.validation_sha256
    ):
        raise ModelUnavailable("model or validation hash mismatch")
    artifact = Artifact.model_validate_json(raw)
    report = ValidationReport.model_validate_json(validation_raw)
    report.verify(artifact, version)
    gates = report.gates
    if (
        not gates["walk_forward"]
        or not gates["holdout"]
        or gates["non_synthetic"] != (not artifact.synthetic)
    ):
        raise ModelUnavailable("model failed the predeclared validation policy")
    if artifact.synthetic and not allow_synthetic:
        raise ModelUnavailable("synthetic model requires explicit offline override")
    if (artifact.strategy_sha256, artifact.policy_sha256, artifact.charges_version) != (
        strategy_sha256,
        policy_sha256,
        charges_version,
    ):
        raise ModelUnavailable("strategy, risk policy or fee schedule differs from training")
    if (
        digest_file(root / "manifest.json") != hashlib.sha256(manifest_raw).hexdigest()
        or digest_file(root / "model.json") != version
        or digest_file(root / "validation.json") != manifest.validation_sha256
    ):
        raise ModelUnavailable("model changed during loading")
    return ResearchModel(artifact, version)
