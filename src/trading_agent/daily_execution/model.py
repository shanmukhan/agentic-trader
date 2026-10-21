"""Separate daily JSON model identity, validated offline and used by bounded paper decisions."""

import hashlib
import platform
from collections import Counter
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from trading_agent.daily_execution.contracts import (
    FEATURE_NAMES,
    DailySample,
    DailyStrategy,
    DailyVector,
    digest,
)
from trading_agent.daily_research.dataset import read_json
from trading_agent.execution.costs import delivery_charges
from trading_agent.ml.features import candidate_fingerprint
from trading_agent.ml.inference import Coefficients, ModelUnavailable
from trading_agent.ml.schema import TrainingSettings
from trading_agent.ml.splits import chronological_splits
from trading_agent.ml.validation import Metrics, SplitDiagnostics, ValidationReport
from trading_agent.models import Candidate, DomainModel, utc
from trading_agent.risk.policy import policy_fingerprint
from trading_agent.settings import Settings


def bounded(path: Path, limit: int = 2_000_000) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError("research artifact must be a regular nonsymlink file")
    with path.open("rb") as file:
        raw = file.read(limit + 1)
    if len(raw) > limit:
        raise ValueError("oversized research artifact")
    return raw


class DailyArtifact(DomainModel):
    schema_version: Literal[1] = 1
    kind: Literal["daily-delivery-model-v1"] = "daily-delivery-model-v1"
    feature_version: Literal["daily-delivery-features-v1"] = "daily-delivery-features-v1"
    feature_names: tuple[str, ...] = FEATURE_NAMES
    coefficients: Coefficients
    synthetic: bool = Field(strict=True)
    strategy_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    policy_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    charges_version: str
    samples_manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    training_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    code_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    fit_label_end: datetime
    validation_label_end: datetime
    validated_through: datetime
    available_after: datetime
    embargo_minutes: int = Field(ge=1, le=1440, strict=True)
    threshold: float = Field(gt=0.5, lt=1, allow_inf_nan=False)

    @field_validator(
        "fit_label_end", "validation_label_end", "validated_through", "available_after"
    )
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        return utc(value)

    @model_validator(mode="after")
    def identity(self) -> "DailyArtifact":
        if (
            self.feature_names != FEATURE_NAMES
            or not self.fit_label_end < self.validation_label_end <= self.validated_through
            or self.available_after
            != self.validated_through + timedelta(minutes=self.embargo_minutes)
        ):
            raise ValueError("daily model feature or availability identity mismatch")
        return self


class DailyValidation(ValidationReport):
    kind: Literal["daily-delivery-validation-v1"] = "daily-delivery-validation-v1"


class DailyModel:
    def __init__(self, artifact: DailyArtifact, version: str):
        self.artifact, self.version = artifact, version

    def check_context(self, strategy: DailyStrategy, policy: Settings) -> None:
        if policy.investment_horizon != "long_term" or (
            self.artifact.strategy_sha256,
            self.artifact.policy_sha256,
            self.artifact.charges_version,
        ) != (strategy.digest(), policy_fingerprint(policy), delivery_charges().version):
            raise ModelUnavailable("daily strategy, horizon, risk or fees differ from the model")

    def score(self, vector: DailyVector) -> float:
        if vector.time <= self.artifact.available_after:
            raise ModelUnavailable("daily model is unavailable before validation plus embargo")
        return self.artifact.coefficients.probability(vector)


def load_daily_model(
    directory: Path, *, strategy: DailyStrategy, policy: Settings, allow_synthetic: bool = False
) -> DailyModel:
    if directory.is_symlink():
        raise ModelUnavailable("daily model directory must not be a symlink")
    manifest_raw = bounded(directory / "manifest.json")
    manifest = read_json(manifest_raw.decode())
    if (
        not isinstance(manifest, dict)
        or manifest.get("kind") != "daily-delivery-validation-v1"
        or manifest.get("state") != "finished"
    ):
        raise ModelUnavailable("not a finished daily model artifact")
    raw, validation_raw = bounded(directory / "model.json"), bounded(directory / "validation.json")
    version = hashlib.sha256(raw).hexdigest()
    for name, data in (("model.json", raw), ("validation.json", validation_raw)):
        if manifest.get("sha256", {}).get(name) != hashlib.sha256(data).hexdigest():
            raise ModelUnavailable("daily model or diagnostics hash mismatch")
    artifact = DailyArtifact.model_validate(read_json(raw.decode()))
    report = DailyValidation.model_validate(read_json(validation_raw.decode()))
    report.verify(artifact, version)
    if (
        not report.gates["walk_forward"]
        or not report.gates["holdout"]
        or artifact.synthetic
        and not allow_synthetic
    ):
        raise ModelUnavailable("daily validation failed or synthetic override is missing")
    if manifest.get("synthetic") is not artifact.synthetic:
        raise ModelUnavailable("daily manifest provenance differs from model")
    model = DailyModel(artifact, version)
    model.check_context(strategy, policy)
    if (
        bounded(directory / "manifest.json") != manifest_raw
        or bounded(directory / "model.json") != raw
        or bounded(directory / "validation.json") != validation_raw
    ):
        raise ModelUnavailable("daily model changed during loading")
    return model


class DailySamples:
    def __init__(self, directory: Path):
        if directory.is_symlink():
            raise ValueError("daily sample directory must not be a symlink")
        self.directory = directory.resolve()
        self.manifest_raw = bounded(directory / "manifest.json")
        manifest = read_json(self.manifest_raw.decode())
        if (
            not isinstance(manifest, dict)
            or manifest.get("kind") != "daily-delivery-labels-v1"
            or manifest.get("state") != "finished"
        ):
            raise ValueError("expected finished independent daily labels")
        self.hashes = manifest["sha256"]
        if set(self.hashes) != {
            "paper.sqlite3",
            "report.json",
            "context.json",
            "index.html",
            "report.md",
            "decisions.jsonl",
            "equity.csv",
            "samples.jsonl",
            "label_audit.jsonl",
        }:
            raise ValueError("daily sample artifact list mismatch")
        context = read_json(bounded(directory / "context.json").decode())
        if not isinstance(context, dict):
            raise ValueError("daily sample context must be an object")
        self.context = context
        self.assert_unchanged()
        strategy = DailyStrategy.model_validate(self.context["strategy"])
        if (
            strategy.digest() != self.context["strategy_sha256"]
            or self.context["synthetic"] is not manifest.get("synthetic")
            or self.context["kind"] != "daily-delivery-labels-v1"
        ):
            raise ValueError("daily sample context identity mismatch")
        policy = Settings.model_validate(self.context["risk_policy"])
        if (
            policy.investment_horizon != "long_term"
            or policy_fingerprint(policy) != self.context["risk_policy_sha256"]
            or self.context["charges_version"] != delivery_charges().version
        ):
            raise ValueError("daily labels have inconsistent financial identity")
        self.strategy = strategy
        self.sessions = tuple(date.fromisoformat(day) for day in self.context["sessions"])
        if not self.sessions or self.sessions != tuple(sorted(set(self.sessions))):
            raise ValueError("daily label sessions must be unique and chronological")
        self.digest = hashlib.sha256(self.manifest_raw).hexdigest()

    def assert_unchanged(self) -> None:
        if bounded(self.directory / "manifest.json") != self.manifest_raw:
            raise ValueError("daily sample manifest changed")
        for name, expected in self.hashes.items():
            path = self.directory / name
            if (
                path.is_symlink()
                or not path.is_file()
                or path.resolve().parent != self.directory
                or path.stat().st_size > 256_000_000
            ):
                raise ValueError("daily sample files must be bounded and local")
            with path.open("rb") as file:
                if hashlib.file_digest(file, "sha256").hexdigest() != expected:
                    raise ValueError("daily sample artifact changed")

    def read(self) -> list[DailySample]:
        rows: list[DailySample] = []
        with (self.directory / "samples.jsonl").open() as file:
            while raw := file.readline(65537):
                if len(raw.encode()) > 65536 or len(rows) >= self.strategy.max_samples:
                    raise ValueError("daily sample read budget exceeded")
                rows.append(DailySample.model_validate(read_json(raw)))
        audits = {}
        with (self.directory / "label_audit.jsonl").open() as file:
            while raw := file.readline(65537):
                if len(raw.encode()) > 65536:
                    raise ValueError("oversized daily label audit")
                entry = read_json(raw)
                if not isinstance(entry, dict):
                    raise ValueError("invalid daily label audit")
                if entry["id"] in audits:
                    raise ValueError("duplicate daily label audit identity")
                audits[entry["id"]] = entry
        if len({row.id for row in rows}) != len(rows) or len(rows) != self.context[
            "label_counts"
        ].get("LABELED", 0):
            raise ValueError("daily labels count/identity mismatch")
        from trading_agent.market_data.calendar import IST

        for row in rows:
            audit = audits.get(row.id)
            if (
                not audit
                or audit["status"] != "LABELED"
                or DailySample.model_validate(audit["sample"]) != row
                or row.features.time.astimezone(IST).date() not in self.sessions
                or row.label_end > datetime.fromisoformat(self.context["source_available_through"])
            ):
                raise ValueError("daily sample lacks matching causal completion audit")
            candidate = Candidate.model_validate(audit["candidate"])
            if (
                row.id
                != digest(
                    {"candidate": row.features.candidate_sha256, "strategy": self.strategy.digest()}
                )
                or candidate_fingerprint(candidate) != row.features.candidate_sha256
                or candidate.symbol != row.features.symbol
                or candidate.decision_time != row.features.time
            ):
                raise ValueError("daily sample candidate/feature identity differs from its audit")
            entry = audit["entry"]
            policy = Settings.model_validate(self.context["risk_policy"])
            if (
                entry["filled"] != entry["quantity"]
                or entry["quantity"] <= 0
                or row.net_pnl != Decimal(audit["cash"]) - policy.starting_cash
                or audit["positions"]
            ):
                raise ValueError("daily completion audit does not reconcile its net filled outcome")
        if (
            dict(Counter(audit["status"] for audit in audits.values()))
            != self.context["label_counts"]
        ):
            raise ValueError("daily label audit counts disagree with the context")
        self.assert_unchanged()
        return sorted(rows, key=lambda row: (row.features.time, row.id))


def train_daily(
    samples: DailySamples, *, settings: TrainingSettings, output: Path
) -> dict[str, Any]:
    from trading_agent.backtesting.report import code_digest
    from trading_agent.daily_execution.report import render
    from trading_agent.daily_execution.runner import finish_manifest, private_text
    from trading_agent.ml.training import evaluate, fit

    if output.exists() or output.resolve().is_relative_to(samples.directory):
        raise ValueError("daily model output must be new and outside source labels")
    rows = samples.read()
    splits = chronological_splits(rows, samples.sessions, settings)
    output.mkdir(parents=True, mode=0o700)
    diagnostics = []
    context = samples.context
    source_end = datetime.fromisoformat(context["source_available_through"])
    session_end = datetime.fromisoformat(context["source_session_close"])
    for split in splits:
        coefficients = fit(split, settings)
        if split.name == "holdout":
            label_end = max(row.label_end for row in split.evaluation)
            through = max(label_end, source_end, session_end)
            artifact = DailyArtifact(
                coefficients=coefficients,
                synthetic=context["synthetic"],
                strategy_sha256=context["strategy_sha256"],
                policy_sha256=context["risk_policy_sha256"],
                charges_version=context["charges_version"],
                samples_manifest_sha256=samples.digest,
                training_sha256=settings.digest(),
                code_sha256=code_digest(),
                fit_label_end=max(row.label_end for row in (*split.train, *split.calibration)),
                validation_label_end=label_end,
                validated_through=through,
                available_after=through + timedelta(minutes=settings.embargo_minutes),
                embargo_minutes=settings.embargo_minutes,
                threshold=settings.probability_threshold,
            )
            # The final coefficients are frozen before reading holdout outcome diagnostics.
            private_text(output / "model.json", artifact.model_dump_json(indent=2) + "\n")
        metrics = evaluate(
            split.evaluation,
            coefficients,
            sum(row.target for row in split.train) / len(split.train),
            settings,
        )
        diagnostic = SplitDiagnostics(
            name=split.name,
            train_count=len(split.train),
            calibration_count=len(split.calibration),
            train_first=min(row.features.time for row in split.train),
            train_last=max(row.features.time for row in split.train),
            train_label_end=max(row.label_end for row in split.train),
            calibration_first=min(row.features.time for row in split.calibration),
            calibration_last=max(row.features.time for row in split.calibration),
            calibration_label_end=max(row.label_end for row in split.calibration),
            evaluation_first=min(row.features.time for row in split.evaluation),
            evaluation_last=max(row.features.time for row in split.evaluation),
            evaluation_label_end=max(row.label_end for row in split.evaluation),
            purged_train=split.purged_train,
            purged_calibration=split.purged_calibration,
            metrics=Metrics.model_validate(metrics),
        )
        diagnostics.append(diagnostic)
    gates = {
        "walk_forward": all(split.metrics.passed for split in diagnostics[:-1]),
        "holdout": diagnostics[-1].metrics.passed,
        "non_synthetic": not context["synthetic"],
    }
    report = DailyValidation(
        schema_version=1,
        ready_for_live=False,
        research_approved=all(gates.values()),
        model_sha256=hashlib.sha256((output / "model.json").read_bytes()).hexdigest(),
        training_sha256=settings.digest(),
        settings=settings,
        samples_manifest_sha256=samples.digest,
        samples_counts=context["label_counts"],
        source_available_through=source_end,
        validation_session_end=session_end,
        synthetic=context["synthetic"],
        runtime={
            "python": platform.python_version(),
            "pipeline": "daily-delivery-v1",
        },
        gates=gates,
        splits=tuple(diagnostics),
    )
    report.verify(artifact, report.model_sha256)
    samples.assert_unchanged()
    private_text(output / "validation.json", report.model_dump_json(indent=2) + "\n")
    payload = report.model_dump(mode="json")
    private_text(output / "index.html", render(payload))
    private_text(
        output / "validation.md",
        "# Daily model validation\n\nOffline research only; live: false.\n\n"
        + f"Synthetic: {report.synthetic}; statistical gates: {gates}.\n\n"
        + "Independent selected-label P&L is not portfolio performance. Whole-session splits "
        "purge overlapping outcomes and embargo adjacent data. No parameter search "
        "or failed-model override.\n",
    )
    finish_manifest(
        output,
        ["model.json", "validation.json", "validation.md", "index.html"],
        kind="daily-delivery-validation-v1",
        synthetic=context["synthetic"],
    )
    return payload
