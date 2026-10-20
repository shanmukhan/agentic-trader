"""Explicit allowlist of reviewed exchange sessions, including early closes."""

import csv
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

from trading_agent.models import IST_NAME, utc

IST = ZoneInfo(IST_NAME)


class SessionCalendar:
    def __init__(
        self, sessions: dict[date, tuple[time, time]], sources: dict[date, str] | None = None
    ):
        self.sessions = dict(sessions)
        self.sources = dict(sources or {})
        for opened, closed in self.sessions.values():
            if not time(9, 0) <= opened < closed <= time(16, 0):
                raise ValueError("invalid exchange session")

    @classmethod
    def load(cls, path: Path) -> "SessionCalendar":
        sessions = {}
        sources = {}
        with path.open(newline="") as file:
            for row in csv.DictReader(file):
                day = date.fromisoformat(row["date"])
                if day in sessions or not row["source"].strip():
                    raise ValueError("duplicate or unreviewed session")
                sessions[day] = (time.fromisoformat(row["open"]), time.fromisoformat(row["close"]))
                sources[day] = row["source"].strip()
        return cls(sessions, sources)

    def bounds(self, now: datetime) -> tuple[datetime, datetime] | None:
        local = utc(now).astimezone(IST)
        session = self.sessions.get(local.date())
        if session is None:
            return None
        return (
            datetime.combine(local.date(), session[0], IST),
            datetime.combine(local.date(), session[1], IST),
        )

    def is_open(self, now: datetime) -> bool:
        bounds = self.bounds(now)
        return bool(bounds and bounds[0] <= now < bounds[1])
