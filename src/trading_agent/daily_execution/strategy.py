"""One prior-daily proposal per symbol/session, using fresh observed quote context."""

import math
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from trading_agent.daily_execution.contracts import DailyVector, finite_features
from trading_agent.daily_execution.runtime import ResearchRuntime
from trading_agent.execution.costs import down, up
from trading_agent.market_data.calendar import IST
from trading_agent.ml.features import candidate_fingerprint
from trading_agent.models import Candidate, Quote, stamp

D = Decimal


class DailyDecisions:
    def __init__(self, runtime: ResearchRuntime):
        self.runtime = runtime
        self.used: set[tuple[str, date]] = set()
        self.exits: set[tuple[str, str, date]] = set()

    def exits_due(self, now: datetime) -> None:
        r, day = self.runtime, now.astimezone(IST).date()
        e = r.engine
        if not e.calendar.is_open(now) or now.astimezone(IST).time() < e.settings.entry_start:
            return
        with e.db.transaction() as tx:
            positions = [dict(row) for row in tx.execute("SELECT * FROM positions")]
        for position in positions:
            key = position["symbol"], position["opened"], day
            if key in self.exits:
                continue
            self.exits.add(key)
            self.used.add((position["symbol"], day))
            opened = datetime.fromisoformat(position["opened"]).astimezone(IST).date()
            age = r.timeline.indices[day] - r.timeline.indices[opened]
            screen = r.timeline.screen(position["symbol"], now)
            reason = (
                "DAILY_HOLDING_LIMIT"
                if age >= r.strategy.max_hold_sessions
                else "DAILY_SCREEN_EXIT"
                if screen["status"] != "research_candidate"
                else None
            )
            if reason:
                with e.lock, e.db.transaction() as tx:
                    e._exit(tx, position["symbol"], now, reason)
                    e.db.event(
                        tx,
                        stamp(now),
                        "daily_strategy_exit",
                        position["symbol"],
                        {"reason": reason},
                    )

    def proposal(
        self, quote: Quote, now: datetime
    ) -> tuple[dict[str, Any], Candidate | None, DailyVector | None] | None:
        r, e, s = self.runtime, self.runtime.engine, self.runtime.strategy
        local = now.astimezone(IST)
        key = quote.symbol, local.date()
        if (
            key in self.used
            or not e.calendar.is_open(now)
            or not e.settings.entry_start <= local.time() < e.settings.entry_end
        ):
            return None
        with e.db.transaction() as tx:
            current = e._quote(tx, quote.symbol)
            if current != quote or not e._fresh(current, now):
                return None
        self.used.add(key)
        screen = r.timeline.screen(quote.symbol, now)
        payload: dict[str, Any] = {
            "symbol": quote.symbol,
            "time": stamp(now),
            "screen": screen,
            "reasons": list(screen["reasons"]),
        }
        if screen["status"] != "research_candidate":
            return payload, None, None
        # Current-day applied actions convert yesterday's raw reference, never a future close.
        factor, cash = r.effects.get(key, (D(1), D(0)))
        reference = (D(screen["last_close"]) - cash) / factor
        if reference <= 0:
            payload["reasons"].append("UNSUPPORTED_REFERENCE_BASIS")
            return payload, None, None
        gap = (quote.ask / reference - 1) * 10000
        if abs(gap) > s.max_entry_gap_bps:
            payload["reasons"].append("DAILY_ENTRY_GAP")
            return payload, None, None
        with e.db.transaction() as tx:
            tick = e._tick(tx, quote.symbol)
        stop = down(quote.ask * (1 - s.stop_pct / 100), tick)
        target = up(quote.ask * (1 + s.target_pct / 100), tick)
        if stop <= 0 or not stop < quote.ask < target:
            payload["reasons"].append("UNREPRESENTABLE_PRICE_LEVELS")
            return payload, None, None
        candidate = Candidate(
            intent_id=f"daily-{local.date()}-{quote.symbol}",
            symbol=quote.symbol,
            stop=stop,
            target=target,
            decision_time=now,
            reason="prior completed daily momentum/trend; independent delivery risk",
        )
        opened = e.calendar.bounds(now)
        assert opened is not None
        values = finite_features(
            (
                D(screen["gross_total_return_pct"]),
                (D(screen["index_level"]) / D(screen["trend_index_average"]) - 1) * 100,
                D(screen["daily_volatility_pct"]),
                math.log1p(float(screen["average_turnover"])),
                (quote.ask - quote.bid) / quote.bid * 10000,
                gap,
                (quote.ask - stop) / quote.ask * 10000,
                (target - quote.ask) / quote.ask * 10000,
                (now - opened[0]).total_seconds() / 60,
                math.log(float(quote.ask)),
                screen["observations"],
                (target - quote.ask) / (quote.ask - stop),
            )
        )
        vector = DailyVector(
            symbol=quote.symbol,
            time=now,
            daily_session=date.fromisoformat(screen["last_session"]),
            available_at=datetime.fromisoformat(screen["available_at"]),
            candidate_sha256=candidate_fingerprint(candidate),
            values=values,
        )
        payload.update(
            candidate=candidate.model_dump(mode="json"), features=vector.model_dump(mode="json")
        )
        return payload, candidate, vector
