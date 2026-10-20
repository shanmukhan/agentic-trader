"""Versioned, streaming data bundles with explicit receipt/candle-availability clocks."""

import hashlib
from collections.abc import Iterator
from datetime import date, datetime, time, timedelta
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, TypeAdapter, field_validator, model_validator

from trading_agent.market_data.calendar import SessionCalendar
from trading_agent.models import Candle, DomainModel, Instrument, Quote, utc


class Session(DomainModel):
    day: date
    open: time
    close: time
    source: str = Field(min_length=1, max_length=1000)

    @model_validator(mode="after")
    def valid(self) -> "Session":
        if self.open.tzinfo is not None or self.close.tzinfo is not None:
            raise ValueError("session clock times must be local IST without an offset")
        SessionCalendar({self.day: (self.open, self.close)})
        return self


class Manifest(DomainModel):
    schema_version: Literal[1] = 1
    source: str = Field(min_length=1, max_length=2000)
    price_basis: Literal["unadjusted"] = "unadjusted"
    data_notes: str = Field(min_length=1, max_length=4000)
    synthetic: bool = Field(strict=True)  # A provenance declaration, not authentication proof.
    instruments: tuple[Instrument, ...] = Field(min_length=1, max_length=10)
    sessions: tuple[Session, ...] = Field(min_length=1, max_length=10000)
    events_file: Literal["events.jsonl"] = "events.jsonl"

    @model_validator(mode="after")
    def unique(self) -> "Manifest":
        if len({i.symbol for i in self.instruments}) != len(self.instruments) or len(
            {i.token for i in self.instruments}
        ) != len(self.instruments):
            raise ValueError("dataset instruments must have unique symbols and tokens")
        if len({s.day for s in self.sessions}) != len(self.sessions):
            raise ValueError("duplicate dataset session")
        return self

    def calendar(self) -> SessionCalendar:
        return SessionCalendar({s.day: (s.open, s.close) for s in self.sessions})


class TimedEvent(DomainModel):
    time: datetime

    @field_validator("time")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        return utc(value)


class QuoteEvent(TimedEvent):
    type: Literal["quote"] = "quote"
    quote: Quote

    @model_validator(mode="after")
    def receipt(self) -> "QuoteEvent":
        if self.quote.received_time > self.time or self.quote.exchange_time > self.time:
            raise ValueError("quote event cannot precede exchange or observed receipt time")
        return self


class CandleEvent(TimedEvent):
    type: Literal["candle"] = "candle"
    candle: Candle

    @model_validator(mode="after")
    def completed(self) -> "CandleEvent":
        if (
            self.candle.minutes != 5
            or not self.candle.completed
            or self.candle.start + timedelta(minutes=5) > self.time
        ):
            raise ValueError("candle event must be available after its five-minute close")
        return self


class ConnectionEvent(TimedEvent):
    type: Literal["connection"] = "connection"
    connected: bool = Field(strict=True)


class ClockEvent(TimedEvent):
    type: Literal["clock"] = "clock"


class KillEvent(TimedEvent):
    type: Literal["kill"] = "kill"


Event = QuoteEvent | CandleEvent | ConnectionEvent | ClockEvent | KillEvent
TaggedEvent = Annotated[Event, Field(discriminator="type")]
EVENT: TypeAdapter[Event] = TypeAdapter(TaggedEvent)  # type: ignore[arg-type]


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while chunk := file.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def bounded_lines(path: Path) -> Iterator[tuple[int, bytes]]:
    with path.open("rb") as file:
        number = 0
        while line := file.readline(65537):
            number += 1
            if len(line) > 65536 or not line.strip():
                raise ValueError(f"invalid event line {number}")
            yield number, line


class Dataset:
    def __init__(self, directory: Path):
        self.directory = directory.resolve()
        self.manifest_path = self.directory / "manifest.json"
        if self.manifest_path.is_symlink():
            raise ValueError("manifest must be local to the dataset")
        with self.manifest_path.open("rb") as file:
            manifest_bytes = file.read(1_000_001)
        if len(manifest_bytes) > 1_000_000:
            raise ValueError("oversized dataset manifest")
        self.manifest = Manifest.model_validate_json(manifest_bytes)
        self.events_path = self.directory / self.manifest.events_file
        if self.events_path.is_symlink():
            raise ValueError("events file must be local to the dataset")
        self.hashes = {
            "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "events_sha256": digest_file(self.events_path),
        }

    def events(self) -> Iterator[Event]:
        previous = None
        symbols = {i.symbol: i for i in self.manifest.instruments}
        calendar = self.manifest.calendar()
        for number, line in bounded_lines(self.events_path):
            try:
                event = EVENT.validate_json(line)
            except ValueError:
                raise ValueError(f"invalid event schema on line {number}") from None
            if previous is not None and event.time < previous:
                raise ValueError(f"event clock moved backward on line {number}")
            if isinstance(event, QuoteEvent | CandleEvent):
                item = event.quote if isinstance(event, QuoteEvent) else event.candle
                if item.symbol not in symbols:
                    raise ValueError("event symbol is outside the declared universe")
                market_time = (
                    event.quote.exchange_time
                    if isinstance(event, QuoteEvent)
                    else event.candle.start
                )
                if calendar.bounds(market_time) is None:
                    raise ValueError("market event has no reviewed session date")
                if (
                    isinstance(event, QuoteEvent)
                    and event.quote.token != symbols[item.symbol].token
                ):
                    raise ValueError("event token differs from declared catalog")
            previous = event.time
            yield event
        if previous is None:
            raise ValueError("dataset contains no events")

    def assert_unchanged(self) -> None:
        if self.hashes != {
            "manifest_sha256": digest_file(self.manifest_path),
            "events_sha256": digest_file(self.events_path),
        }:
            raise ValueError("dataset changed during the research run")


def write_bundle(directory: Path, manifest: Manifest, events: Iterator[Event]) -> None:
    directory.mkdir(parents=True, exist_ok=False, mode=0o700)
    with (directory / "events.jsonl").open("x") as file:
        for event in events:
            file.write(event.model_dump_json() + "\n")
    # A failed generator must not leave a loadable, falsely complete data bundle.
    (directory / "manifest.json").write_text(manifest.model_dump_json(indent=2) + "\n")
