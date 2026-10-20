"""Hash-verified interval-label bundles. Completion manifest is written last."""

import hashlib
from datetime import date, datetime
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from trading_agent.backtesting.dataset import Manifest, bounded_lines, digest_file
from trading_agent.market_data.calendar import IST
from trading_agent.ml.schema import LabelPolicy, Sample
from trading_agent.models import DomainModel, utc
from trading_agent.risk.policy import policy_fingerprint
from trading_agent.settings import Settings
from trading_agent.strategy.rules import StrategySettings


class SampleManifest(DomainModel):
    schema_version: Literal[1] = 1
    synthetic: bool = Field(strict=True)
    source_hashes: dict[str, str]
    source_description: str
    source_manifest: Manifest
    source_available_through: datetime
    strategy_settings: StrategySettings
    risk_policy: dict[str, Any]
    strategy_sha256: str
    policy_sha256: str
    charges_version: str
    code_sha256: str
    label_policy: LabelPolicy
    sessions: tuple[date, ...] = Field(min_length=1, max_length=10000)
    counts: dict[str, int]
    samples_sha256: str
    audit_sha256: str

    @field_validator("source_available_through")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        return utc(value)

    @model_validator(mode="after")
    def ordered(self) -> "SampleManifest":
        if tuple(sorted(set(self.sessions))) != self.sessions:
            raise ValueError("sample sessions must be unique and chronological")
        if (
            self.sessions != tuple(sorted(session.day for session in self.source_manifest.sessions))
            or self.synthetic != self.source_manifest.synthetic
            or self.strategy_settings.digest() != self.strategy_sha256
            or policy_fingerprint(Settings.model_validate(self.risk_policy)) != self.policy_sha256
        ):
            raise ValueError("sample provenance/configuration mismatch")
        n = self.counts
        if (
            any(value < 0 for value in n.values())
            or n.get("candidates", 0) != n.get("labeled", 0) + n.get("censored", 0)
            or n.get("labeled", 0) != n.get("target_0", 0) + n.get("target_1", 0)
            or n.get("censored", 0)
            != sum(value for key, value in n.items() if key.startswith("censored:"))
        ):
            raise ValueError("inconsistent sample outcome counts")
        return self


class Samples:
    def __init__(self, directory: Path):
        self.directory = directory.resolve()
        paths = [
            self.directory / name
            for name in ("manifest.json", "samples.jsonl", "label_audit.jsonl")
        ]
        if any(path.is_symlink() for path in paths):
            raise ValueError("sample bundle must contain local regular files")
        with paths[0].open("rb") as file:
            raw = file.read(1_000_001)
        if len(raw) > 1_000_000:
            raise ValueError("oversized sample manifest")
        self.manifest = SampleManifest.model_validate_json(raw)
        self.digest = hashlib.sha256(raw).hexdigest()
        self.assert_unchanged()

    def assert_unchanged(self) -> None:
        m = self.manifest
        if (
            digest_file(self.directory / "manifest.json") != self.digest
            or digest_file(self.directory / "samples.jsonl") != m.samples_sha256
            or digest_file(self.directory / "label_audit.jsonl") != m.audit_sha256
        ):
            raise ValueError("sample bundle changed or failed its hashes")

    def read(self) -> list[Sample]:
        rows, ids = [], set()
        calendar = self.manifest.source_manifest.calendar()
        symbols = {item.symbol for item in self.manifest.source_manifest.instruments}
        for number, line in bounded_lines(self.directory / "samples.jsonl"):
            if number > 1_000_000:
                raise ValueError("training sample limit exceeded")
            sample = Sample.model_validate_json(line)
            bounds = calendar.bounds(sample.features.time)
            if (
                sample.features.symbol not in symbols
                or bounds is None
                or not bounds[0] < sample.features.candle_end <= sample.features.time < bounds[1]
            ):
                raise ValueError("sample feature context is outside the declared universe/session")
            if (
                sample.id in ids
                or sample.features.time.astimezone(IST).date() not in self.manifest.sessions
            ):
                raise ValueError("duplicate sample or undeclared decision session")
            ids.add(sample.id)
            rows.append(sample)
        if len(rows) != self.manifest.counts.get("labeled", 0):
            raise ValueError("sample count differs from manifest")
        self.assert_unchanged()
        return sorted(rows, key=lambda row: (row.features.time, row.features.symbol, row.id))
