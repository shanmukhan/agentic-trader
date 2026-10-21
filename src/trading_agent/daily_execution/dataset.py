"""Bounded causal quote/control evidence for offline delivery research."""

import hashlib
from collections.abc import Iterator
from datetime import date
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, TypeAdapter, model_validator

from trading_agent.backtesting.dataset import (
    ClockEvent,
    ConnectionEvent,
    KillEvent,
    Manifest,
    QuoteEvent,
    TimedEvent,
)
from trading_agent.corporate_actions.contracts import ActionBatch, CashReceipt
from trading_agent.daily_research.dataset import DailyDataset, read_json
from trading_agent.execution.delivery import HoldingReview
from trading_agent.market_data.calendar import SessionCalendar


class ReviewEvent(TimedEvent):
    type: Literal["review"] = "review"
    review: HoldingReview


class ActionEvent(TimedEvent):
    type: Literal["action"] = "action"
    batch: ActionBatch


class ReceiptEvent(TimedEvent):
    type: Literal["receipt"] = "receipt"
    receipt: CashReceipt


Event = (
    QuoteEvent | ConnectionEvent | ClockEvent | KillEvent | ReviewEvent | ActionEvent | ReceiptEvent
)
TaggedEvent = Annotated[Event, Field(discriminator="type")]
EVENT: TypeAdapter[Event] = TypeAdapter(TaggedEvent)  # type: ignore[arg-type]


class ExecutionManifest(Manifest):
    kind: Literal["daily-delivery-execution-v1"] = "daily-delivery-execution-v1"

    def calendar(self) -> SessionCalendar:
        return SessionCalendar(
            {s.day: (s.open, s.close) for s in self.sessions},
            {s.day: s.source for s in self.sessions},
        )

    @model_validator(mode="after")
    def reviewed(self) -> "ExecutionManifest":
        if tuple(session.day for session in self.sessions) != tuple(
            sorted(session.day for session in self.sessions)
        ) or any(not session.source.strip() for session in self.sessions):
            raise ValueError("execution sessions require chronological sourced definitions")
        return self


class ExecutionDataset:
    def __init__(self, directory: Path, daily: DailyDataset):
        if daily.manifest.universe_kind != "point_in_time":
            raise ValueError(
                "Prospective constituent snapshots cannot establish "
                "historical execution/ML evidence."
            )
        if directory.is_symlink():
            raise ValueError("execution bundle must not be a symlink")
        self.directory = directory.resolve()
        self.daily = daily
        self.manifest_path = directory / "manifest.json"
        self.events_path = directory / "events.jsonl"
        self.hashes = self.fingerprints()
        with self.manifest_path.open(encoding="utf-8") as file:
            raw = file.read(1_000_001)
        if len(raw.encode()) > 1_000_000:
            raise ValueError("oversized execution manifest")
        value = read_json(raw)
        if not isinstance(value, dict) or value.get("kind") != "daily-delivery-execution-v1":
            raise ValueError("expected an explicit daily delivery execution bundle")
        self.manifest = ExecutionManifest.model_validate(value)
        self.session_dates = frozenset(session.day for session in self.manifest.sessions)
        sessions = {session.day: session for session in daily.manifest.sessions}
        for session in self.manifest.sessions:
            if sessions.get(session.day) != session:
                raise ValueError("daily/execution reviewed calendars must agree exactly")
        symbols = {member.symbol for member in daily.manifest.universe}
        if not {item.symbol for item in self.manifest.instruments} <= symbols:
            raise ValueError("execution catalog is outside the daily universe")
        if not self.manifest.synthetic and daily.manifest.synthetic:
            raise ValueError("synthetic daily input cannot be declared real execution research")
        self.assert_unchanged()

    def fingerprints(self) -> dict[str, str]:
        hashes = {}
        for path, limit in ((self.manifest_path, 1_000_000), (self.events_path, 256_000_000)):
            if (
                path.is_symlink()
                or not path.is_file()
                or path.resolve().parent != self.directory
                or path.stat().st_size > limit
            ):
                raise ValueError("execution input must be bounded regular local files")
            with path.open("rb") as file:
                hashes[path.name] = hashlib.file_digest(file, "sha256").hexdigest()
        return hashes

    @property
    def sessions(self) -> tuple[date, ...]:
        return tuple(session.day for session in self.manifest.sessions)

    def events(self) -> Iterator[Event]:
        from trading_agent.market_data.calendar import IST

        previous = None
        symbols = {item.symbol: item for item in self.manifest.instruments}
        calendar = self.manifest.calendar()
        consumed = 0
        with self.events_path.open(encoding="utf-8") as file:
            while raw := file.readline(65537):
                consumed += len(raw.encode())
                if len(raw.encode()) > 65536 or consumed > 256_000_000:
                    raise ValueError("execution input exceeds its read budget")
                event = EVENT.validate_python(read_json(raw))
                if previous is not None and event.time < previous:
                    raise ValueError("execution clock moved backward")
                if event.time.astimezone(IST).date() not in self.session_dates:
                    raise ValueError("execution event is outside its reviewed session dates")
                if isinstance(event, QuoteEvent):
                    quote = event.quote
                    instrument = symbols.get(quote.symbol)
                    if (
                        not instrument
                        or quote.token != instrument.token
                        or not calendar.is_open(quote.exchange_time)
                        or quote.exchange_time.astimezone(IST).date()
                        != event.time.astimezone(IST).date()
                    ):
                        raise ValueError("quote must match catalog/current reviewed open session")
                if isinstance(event, ReviewEvent) and event.review.symbol not in symbols:
                    raise ValueError("review symbol outside execution catalog")
                if isinstance(event, ActionEvent) and event.batch.symbol not in symbols:
                    raise ValueError("action symbol outside execution catalog")
                previous = event.time
                yield event
        if previous is None:
            raise ValueError("empty execution evidence")

    def assert_unchanged(self) -> None:
        if self.fingerprints() != self.hashes or self.daily.fingerprints() != self.daily.hashes:
            raise RuntimeError("daily or execution evidence changed during research")
