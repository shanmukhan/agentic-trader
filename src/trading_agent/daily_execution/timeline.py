"""Advance daily information once by its availability clock, with late-row rebuilds."""

from bisect import bisect_right
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from trading_agent.daily_research.analysis import DailyPolicy, Window
from trading_agent.daily_research.dataset import DailyBar, DailyDataset
from trading_agent.market_data.calendar import IST
from trading_agent.models import utc


class DailyTimeline:
    def __init__(self, dataset: DailyDataset, symbols: set[str], policy: DailyPolicy):
        self.policy = policy
        self.sessions = tuple(session.day for session in dataset.manifest.sessions)
        self.closes = [
            datetime.combine(session.day, session.close, IST)
            for session in dataset.manifest.sessions
        ]
        self.indices = {day: index for index, day in enumerate(self.sessions)}
        self.members = {
            symbol: [item for item in dataset.manifest.universe if item.symbol == symbol]
            for symbol in symbols
        }
        self.membership_dates = {
            symbol: [item.effective_session for item in members]
            for symbol, members in self.members.items()
        }
        self.bars = {
            (bar.symbol, bar.session): bar for bar in dataset.bars() if bar.symbol in symbols
        }
        self.pending = sorted(
            self.bars.values(), key=lambda bar: (bar.available_at, bar.session, bar.symbol)
        )
        self.available: dict[str, dict[int, DailyBar]] = {symbol: {} for symbol in symbols}
        self.windows: dict[str, Window] = {}
        self.window_available: dict[str, datetime] = {}
        self.position = 0
        self.latest_indices = {symbol: -1 for symbol in symbols}
        self.clock: datetime | None = None
        self.rebuilds = 0

    def membership(self, symbol: str, day: date, as_of: datetime | None = None) -> Any:
        index = bisect_right(self.membership_dates[symbol], day) - 1
        while index >= 0 and as_of and self.members[symbol][index].known_at > as_of:
            index -= 1
        return self.members[symbol][index] if index >= 0 else None

    def included(self, symbol: str, day: date, now: datetime) -> bool:
        member = self.membership(symbol, day, now)
        return bool(member and member.included)

    def _add(self, bar: DailyBar, index: int) -> None:
        member = self.membership(bar.symbol, bar.session)
        if not member or not member.included:
            self.windows.pop(bar.symbol, None)
            return
        window = self.windows.get(bar.symbol)
        if window and (
            window.last_index != index - 1
            or window.last
            and window.last.session < member.effective_session
        ):
            window = None
        if window is None:
            window = self.windows[bar.symbol] = Window(self.policy)
            self.window_available[bar.symbol] = bar.available_at
        else:
            self.window_available[bar.symbol] = max(
                self.window_available[bar.symbol], bar.available_at
            )
        window.add(bar, index)

    def advance(self, now: datetime) -> None:
        now = utc(now)
        if self.clock and now < self.clock:
            raise ValueError("daily information clock cannot move backward")
        while self.position < len(self.pending) and self.pending[self.position].available_at <= now:
            bar = self.pending[self.position]
            index = self.indices[bar.session]
            old = self.available[bar.symbol]
            late = index < self.latest_indices[bar.symbol]
            self.latest_indices[bar.symbol] = max(index, self.latest_indices[bar.symbol])
            old[index] = bar
            if late:
                self.rebuilds += 1
                self.windows.pop(bar.symbol, None)
                for day_index, available in sorted(old.items()):
                    self._add(available, day_index)
            else:
                self._add(bar, index)
            self.position += 1
        self.clock = now

    def screen(self, symbol: str, now: datetime) -> dict[str, Any]:
        self.advance(now)
        current = now.astimezone(IST).date()
        index = bisect_right(self.closes, now) - 1
        if not self.included(symbol, current, now):
            return {"status": "outside_universe", "reasons": ["OUTSIDE_CURRENT_UNIVERSE"]}
        window = self.windows.get(symbol)
        if index < 0 or not window or not window.last or window.last_index != index:
            return {"status": "needs_data", "reasons": ["LATEST_DAILY_SESSION_UNAVAILABLE"]}
        result = window.metrics()
        result.update(
            last_close=str(window.last.close),
            last_session=window.last.session.isoformat(),
            available_at=self.window_available[symbol].isoformat(),
        )
        return result

    def benefit(self, symbol: str, day: date) -> tuple[Decimal, Decimal]:
        """Structural consistency only; this future row never supplies a decision feature."""
        bar = self.bars.get((symbol, day))
        return (
            (Decimal(bar.share_numerator) / bar.share_denominator, bar.cash_per_previous_share)
            if bar
            else (Decimal(1), Decimal(0))
        )
