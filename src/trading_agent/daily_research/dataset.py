"""Reviewed raw daily bars and explicitly dated universe/basis evidence."""

import hashlib
import json
from collections.abc import Iterator
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator, model_validator

from trading_agent.backtesting.dataset import Session
from trading_agent.market_data.calendar import IST
from trading_agent.models import DomainModel, Money, Symbol, utc


def read_json(data: str) -> object:
    def unique(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate research JSON field")
            result[key] = value
        return result

    def finite(value: str) -> None:
        raise ValueError("nonfinite research JSON value")

    return json.loads(data, object_pairs_hook=unique, parse_float=Decimal, parse_constant=finite)


class Membership(DomainModel):
    symbol: Symbol
    effective_session: date
    included: bool = Field(strict=True)
    known_at: datetime
    reference: str = Field(min_length=3, max_length=500, pattern=r".*\S.*")

    @field_validator("known_at")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        return utc(value)


class DailyManifest(DomainModel):
    schema_version: Literal[1] = 1
    source: str = Field(min_length=3, max_length=2000, pattern=r".*\S.*")
    notes: str = Field(min_length=3, max_length=4000, pattern=r".*\S.*")
    synthetic: bool = Field(strict=True)
    universe_kind: Literal["point_in_time", "prospective_snapshot"] = "point_in_time"
    price_basis: Literal["raw-with-explicit-period-benefits"] = "raw-with-explicit-period-benefits"
    sessions: tuple[Session, ...] = Field(min_length=1, max_length=5000)
    universe: tuple[Membership, ...] = Field(min_length=1, max_length=10000)
    bars_file: Literal["daily.jsonl"] = "daily.jsonl"

    @model_validator(mode="after")
    def chronology(self) -> "DailyManifest":
        sessions = {session.day: session for session in self.sessions}
        if any(not session.source.strip() for session in self.sessions):
            raise ValueError("daily sessions require a nonblank reviewed source")
        if len(sessions) != len(self.sessions) or list(sessions) != sorted(sessions):
            raise ValueError("daily sessions must be unique and chronological")
        if len({member.symbol for member in self.universe}) > 500:
            raise ValueError("daily universe exceeds 500 symbols")
        previous: dict[str, Membership] = {}
        for member in self.universe:
            session = sessions.get(member.effective_session)
            if not session or (
                self.universe_kind == "point_in_time"
                and member.known_at > datetime.combine(session.day, session.open, IST)
            ):
                raise ValueError("membership must be knowable before its reviewed session opens")
            old = previous.get(member.symbol)
            if self.universe_kind == "prospective_snapshot" and (old or not member.included):
                raise ValueError("prospective snapshots require one current inclusion per symbol")
            if old and (
                member.effective_session <= old.effective_session or member.included == old.included
            ):
                raise ValueError("membership transitions must alternate on increasing sessions")
            if old is None and not member.included:
                raise ValueError("first universe event must include the symbol")
            previous[member.symbol] = member
        return self


class DailyBar(DomainModel):
    symbol: Symbol
    session: date
    open: Money
    high: Money
    low: Money
    close: Money
    volume: int = Field(ge=0, le=10**12, strict=True)
    price_available_at: datetime
    basis_reviewed_at: datetime
    basis_reference: str = Field(min_length=3, max_length=500, pattern=r".*\S.*")
    share_numerator: int = Field(gt=0, le=10000, strict=True)
    share_denominator: int = Field(gt=0, le=10000, strict=True)
    cash_per_previous_share: Decimal = Field(
        ge=0, max_digits=16, decimal_places=4, allow_inf_nan=False
    )

    @field_validator("price_available_at", "basis_reviewed_at")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        return utc(value)

    @model_validator(mode="after")
    def prices(self) -> "DailyBar":
        if (
            self.low > min(self.open, self.close)
            or self.high < max(self.open, self.close)
            or self.low > self.high
        ):
            raise ValueError("inconsistent daily OHLC bounds")
        if self.share_numerator < self.share_denominator:
            raise ValueError("consolidations require a later reviewed research schema")
        return self

    @property
    def available_at(self) -> datetime:
        return max(self.price_available_at, self.basis_reviewed_at)


class DailyDataset:
    def __init__(self, directory: Path):
        if directory.is_symlink():
            raise ValueError("daily bundle directory must not be a symlink")
        self.directory = directory.resolve()
        self.manifest_path = directory / "manifest.json"
        self.bars_path = directory / "daily.jsonl"
        for path, limit in ((self.manifest_path, 2_000_000), (self.bars_path, 256_000_000)):
            if (
                path.is_symlink()
                or not path.is_file()
                or path.resolve().parent != self.directory
                or path.stat().st_size > limit
            ):
                raise ValueError("research bundle paths must be bounded regular local files")
        self.hashes = self.fingerprints()
        with self.manifest_path.open(encoding="utf-8") as file:
            content = file.read(2_000_001)
        if len(content.encode("utf-8")) > 2_000_000:
            raise ValueError("daily manifest exceeds its read budget")
        self.manifest = DailyManifest.model_validate(read_json(content))
        if self.fingerprints() != self.hashes:
            raise RuntimeError("daily manifest changed during loading")

    def fingerprints(self) -> dict[str, str]:
        values = {}
        for path in (self.manifest_path, self.bars_path):
            if path.is_symlink() or path.resolve().parent != self.directory:
                raise ValueError("research input path changed")
            with path.open("rb") as file:
                values[path.name] = hashlib.file_digest(file, "sha256").hexdigest()
        return values

    def bars(self) -> Iterator[DailyBar]:
        sessions = {session.day: session for session in self.manifest.sessions}
        symbols = {member.symbol for member in self.manifest.universe}
        previous: tuple[date, str] | None = None
        consumed = 0
        with self.bars_path.open(encoding="utf-8") as file:
            while line := file.readline(65537):
                consumed += len(line.encode("utf-8"))
                if consumed > 256_000_000:
                    raise ValueError("daily research input exceeds its read budget")
                if len(line.encode("utf-8")) > 65536:
                    raise ValueError("daily research line exceeds 64 KiB")
                bar = DailyBar.model_validate(read_json(line))
                key = bar.session, bar.symbol
                session = sessions.get(bar.session)
                if bar.symbol not in symbols or session is None or previous and key <= previous:
                    raise ValueError(
                        "daily rows require declared symbols/sessions and strict date-symbol order"
                    )
                if bar.price_available_at < datetime.combine(session.day, session.close, IST):
                    raise ValueError("daily price cannot be available before the reviewed close")
                previous = key
                yield bar
