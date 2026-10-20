"""Opt-in overnight paper policy composed with the existing transactional broker."""

import json
import sqlite3
from datetime import datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from trading_agent.execution.delivery import HoldingReview, dp_key, review_key
from trading_agent.market_data.calendar import IST
from trading_agent.models import Quote, stamp, utc

if TYPE_CHECKING:
    from trading_agent.execution.paper_broker import PaperBroker

PENDING = "state IN ('ACCEPTED','PARTIAL')"
D = Decimal


class LongTermBook:
    def __init__(self, engine: "PaperBroker") -> None:
        self.engine = engine

    def bind(self, tx: sqlite3.Connection, now: datetime) -> None:
        from trading_agent.corporate_actions.service import validate_calendar

        e = self.engine
        validate_calendar(tx, e.calendar)
        held = list(
            tx.execute(
                "SELECT p.symbol,i.token FROM positions p "
                "LEFT JOIN instruments i ON i.symbol=p.symbol"
            )
        )
        if any(row["token"] is None for row in held):
            raise RuntimeError("held instrument missing from the long-term catalog")
        if e.settings.stream_tokens and any(
            row["token"] not in e.settings.stream_tokens for row in held
        ):
            raise ValueError("the selected long-term feed must include every held symbol")
        existing = tx.execute("SELECT value FROM meta WHERE key='long_term_schema'").fetchone()
        if existing:
            if existing[0] != "1":
                raise RuntimeError("unsupported long-term policy schema")
            self.advance_clock(tx, now)
            for row in tx.execute("SELECT key,value FROM meta WHERE key GLOB 'lt_session:*'"):
                day = datetime.fromisoformat(row[0].removeprefix("lt_session:")).date()
                self.pin_session(tx, datetime.combine(day, datetime.min.time(), IST))
        else:
            if tx.execute("SELECT 1 FROM meta WHERE key='policy_hash'").fetchone():
                raise ValueError("long-term policy requires a new dedicated paper account")
            for key, value in {
                "long_term_schema": "1",
                "lt_peak_equity": str(e.settings.starting_cash),
                "lt_last_equity": str(e.settings.starting_cash),
                "lt_last_equity_time": stamp(now),
                "lt_last_clock": stamp(now),
            }.items():
                e.db.set(tx, key, value)
            e.db.event(
                tx,
                stamp(now),
                "long_term_start",
                "system",
                {"schema_version": 1, "charges_version": e.charges.version},
            )

    def advance_clock(self, tx: sqlite3.Connection, now: datetime) -> None:
        old = datetime.fromisoformat(self.engine.db.get(tx, "lt_last_clock"))
        if now < old:
            raise ValueError("long-term clock cannot move backward")
        if now > old:
            self.engine.db.set(tx, "lt_last_clock", stamp(now))

    def pin_session(self, tx: sqlite3.Connection, now: datetime) -> dict[str, str]:
        e = self.engine
        day = now.astimezone(IST).date()
        bounds = e.calendar.bounds(now)
        if not bounds:
            raise ValueError("long-term review requires a reviewed exchange session")
        definition = {
            "open": bounds[0].isoformat(),
            "close": bounds[1].isoformat(),
            "source": e.calendar.sources.get(day, ""),
        }
        key = "lt_session:" + day.isoformat()
        old = tx.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        if old and json.loads(old[0]) != definition:
            raise ValueError("previously used long-term session definition changed")
        if not old:
            e.db.set(tx, key, json.dumps(definition, sort_keys=True))
        return definition

    def reviewed(self, tx: sqlite3.Connection, symbol: str, now: datetime) -> bool:
        if tx.execute("SELECT 1 FROM meta WHERE key=?", ("lt_quarantine:" + symbol,)).fetchone():
            return False
        key = review_key(now.astimezone(IST).date().isoformat(), symbol)
        row = tx.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        return bool(row and HoldingReview.model_validate_json(row[0]).no_corporate_action)

    def review(self, review: HoldingReview, now: datetime) -> dict[str, Any]:
        e = self.engine
        now = utc(now)
        if review.session_date != now.astimezone(IST).date():
            raise ValueError("review must apply to the current IST date")
        with e.lock, e.db.transaction() as tx:
            catalog = tx.execute(
                "SELECT token FROM instruments WHERE symbol=?", (review.symbol,)
            ).fetchone()
            if (
                not catalog
                or e.settings.stream_tokens
                and catalog[0] not in e.settings.stream_tokens
            ):
                raise ValueError("review requires a registered symbol in the selected universe")
            self.roll_day(tx, now)
            definition = self.pin_session(tx, now)
            quarantine = "lt_quarantine:" + review.symbol
            quarantined = tx.execute("SELECT 1 FROM meta WHERE key=?", (quarantine,)).fetchone()
            if quarantined and review.no_corporate_action:
                raise ValueError(
                    "unresolved corporate action: apply a reviewed offline action batch"
                )
            if not review.no_corporate_action and not quarantined:
                e.db.set(tx, quarantine, review.model_dump_json())
            key = review_key(review.session_date.isoformat(), review.symbol)
            payload = review.model_dump(mode="json")
            previous_quote = e._quote(tx, review.symbol)
            old = tx.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
            if (
                not old
                or json.loads(old[0]) != payload
                or (not review.no_corporate_action and not quarantined)
            ):
                e.db.set(tx, key, json.dumps(payload, sort_keys=True))
                e.db.event(
                    tx,
                    stamp(now),
                    "long_term_review",
                    review.symbol,
                    {
                        "review": payload,
                        "session": definition,
                        "basis_time": stamp(previous_quote.exchange_time)
                        if previous_quote
                        else None,
                    },
                )
            if not review.no_corporate_action:
                e.bad_symbols.add(review.symbol)
                for order in tx.execute(
                    f"SELECT * FROM orders WHERE {PENDING} AND side='BUY' AND symbol=?",
                    (review.symbol,),
                ).fetchall():
                    e._cancel(tx, order, stamp(now), "LONG_TERM_REVIEW_BLOCKED")
            return {"review": payload, "paper_only": True, "corporate_actions_applied": False}

    def roll_day(self, tx: sqlite3.Connection, now: datetime) -> None:
        e = self.engine
        self.advance_clock(tx, now)
        today = now.astimezone(IST).date().isoformat()
        if e.db.get(tx, "day") == today or not e.calendar.bounds(now):
            return
        # Anchor the new day to the last fully trusted observation, BEFORE any new
        # quote replaces yesterday's mark. Opening gaps must not vanish in a rebase.
        for order in tx.execute(f"SELECT * FROM orders WHERE {PENDING} AND side='BUY'").fetchall():
            e._cancel(tx, order, stamp(now), "LONG_TERM_SESSION_ROLLOVER")
        e.db.set(tx, "day", today)
        e.db.set(tx, "day_equity", e.db.get(tx, "lt_last_equity"))
        e.db.set(tx, "day_realized", "0")
        e.db.set(tx, "loss_streak", "0")
        e.db.event(
            tx,
            stamp(now),
            "long_term_session",
            "system",
            {
                "day": today,
                "opening_reference": e.db.get(tx, "lt_last_equity"),
                "reference_time": e.db.get(tx, "lt_last_equity_time"),
            },
        )

    def before_quote(self, tx: sqlite3.Connection, quote: Quote, now: datetime) -> bool:
        self.roll_day(tx, now)
        basis = tx.execute(
            "SELECT value FROM meta WHERE key=?", ("lt_basis_after:" + quote.symbol,)
        ).fetchone()
        if basis and quote.exchange_time <= datetime.fromisoformat(basis[0]):
            self.engine.bad_symbols.add(quote.symbol)
            return False
        if quote.exchange_time.astimezone(IST).date() != now.astimezone(
            IST
        ).date() or not self.reviewed(tx, quote.symbol, now):
            e = self.engine
            e.bad_symbols.add(quote.symbol)
            e.db.event(
                tx,
                stamp(now),
                "long_term_quote_blocked",
                quote.symbol,
                {"reason": "LONG_TERM_REVIEW_REQUIRED"},
            )
            return False
        self.pin_session(tx, now)
        return True

    def sale_fee(
        self, tx: sqlite3.Connection, symbol: str, turnover: Decimal, now: datetime
    ) -> Decimal:
        e = self.engine
        total = e.charges.fee("SELL", turnover)
        charged = tx.execute(
            "SELECT 1 FROM meta WHERE key=?",
            (dp_key(now.astimezone(IST).date().isoformat(), symbol),),
        ).fetchone()
        return total - (e.charges.dp_sell if charged and turnover > 0 else D(0))

    def order_fees(
        self,
        tx: sqlite3.Connection,
        order: sqlite3.Row,
        turnover: Decimal,
        now: datetime,
        *,
        record: bool,
    ) -> Decimal:
        e = self.engine
        total = e.charges.fee(order["side"], turnover)
        if order["side"] == "BUY":
            return total
        key = "lt_order_dp:" + order["id"]
        old = tx.execute("SELECT value FROM meta WHERE key=?", (key,)).fetchone()
        allocated = D(old[0]) if old else D(0)
        day_key = dp_key(now.astimezone(IST).date().isoformat(), order["symbol"])
        charged = tx.execute("SELECT 1 FROM meta WHERE key=?", (day_key,)).fetchone()
        if not charged:
            allocated += e.charges.dp_sell
            if record:
                e.db.set(tx, key, allocated)
                e.db.set(tx, day_key, order["id"])
                e.db.event(
                    tx,
                    stamp(now),
                    "delivery_dp_charge",
                    order["id"],
                    {"symbol": order["symbol"], "amount": str(e.charges.dp_sell)},
                )
        return total - e.charges.dp_sell + allocated

    def can_sell(
        self, tx: sqlite3.Connection, order: sqlite3.Row, qty: int, price: Decimal, now: datetime
    ) -> bool:
        total = self.order_fees(tx, order, D(order["turnover"]) + price * qty, now, record=False)
        if D(self.engine.db.get(tx, "cash")) + price * qty < total - D(order["fees"]):
            self.engine.db.event(
                tx,
                stamp(now),
                "long_term_exit_blocked",
                order["id"],
                {"reason": "INSUFFICIENT_EXIT_FEE_CASH"},
            )
            return False
        return True

    def latch_exit(self, tx: sqlite3.Connection, symbol: str, now: datetime, reason: str) -> None:
        e = self.engine
        position = tx.execute("SELECT opened FROM positions WHERE symbol=?", (symbol,)).fetchone()
        if position:
            key = f"lt_exit:{symbol}:{position[0]}"
            if not tx.execute("SELECT 1 FROM meta WHERE key=?", (key,)).fetchone():
                e.db.set(tx, key, reason)
                e.db.event(
                    tx,
                    stamp(now),
                    "long_term_exit_requested",
                    symbol,
                    {"reason": reason, "opened": position[0]},
                )

    def decorate(self, tx: sqlite3.Connection, now: datetime, snapshot: dict[str, Any]) -> None:
        from trading_agent.corporate_actions.accounting import pending_claims

        e = self.engine
        claims = pending_claims(tx)
        snapshot["equity"] = str(D(snapshot["equity"]) + D(claims["receivable"]))
        snapshot["day_pnl"] = str(D(snapshot["equity"]) - D(e.db.get(tx, "day_equity")))
        snapshot["valuation_fresh"] = (
            snapshot["valuation_fresh"] and not claims["unvalued_fractional_claims"]
        )
        reserve = e.charges.dp_sell * e.settings.max_positions
        snapshot["available_cash"] = str(max(D(0), D(snapshot["available_cash"]) - reserve))
        snapshot["delivery_fee_buffer"] = str(reserve)
        peak = D(e.db.get(tx, "lt_peak_equity"))
        snapshot["long_term"] = {
            "peak_equity": str(peak),
            "observed_drawdown": str(max(D(0), peak - D(snapshot["equity"]))),
            "drawdown_limit": str(e.settings.long_term_drawdown_limit),
            "last_trusted_equity": e.db.get(tx, "lt_last_equity"),
            "last_trusted_equity_time": e.db.get(tx, "lt_last_equity_time"),
            "daily_reference": e.db.get(tx, "day_equity"),
            "quarantined_symbols": [
                row[0].removeprefix("lt_quarantine:")
                for row in tx.execute(
                    "SELECT key FROM meta WHERE key GLOB 'lt_quarantine:*' LIMIT 11"
                )
            ],
            **claims,
            "corporate_actions_applied": bool(
                tx.execute("SELECT 1 FROM meta WHERE key='corporate_actions_schema'").fetchone()
            ),
            "income_received": (
                tx.execute("SELECT value FROM meta WHERE key='lt_income_received'").fetchone()
                or ["0"]
            )[0],
            "settlement_verified": False,
        }

    def watch(self, tx: sqlite3.Connection, now: datetime) -> None:
        e = self.engine
        self.roll_day(tx, now)
        snapshot = e._snapshot(tx, now)
        if snapshot["valuation_fresh"]:
            equity = D(snapshot["equity"])
            peak = max(D(e.db.get(tx, "lt_peak_equity")), equity)
            e.db.set(tx, "lt_peak_equity", peak)
            e.db.set(tx, "lt_last_equity", equity)
            e.db.set(tx, "lt_last_equity_time", stamp(now))
            if peak - equity >= e.settings.long_term_drawdown_limit:
                e._kill(tx, stamp(now), "LONG_TERM_DRAWDOWN_LIMIT")
            if D(snapshot["day_pnl"]) <= -e.settings.daily_loss_limit:
                e._kill(tx, stamp(now), "DAILY_LOSS_LIMIT")
        if snapshot["loss_streak"] >= e.settings.max_consecutive_losses:
            e._kill(tx, stamp(now), "LOSS_STREAK")
        local = now.astimezone(IST)
        bounds = e.calendar.bounds(now)
        closed = not e.calendar.is_open(now) or local.time() >= e.settings.entry_end
        if bounds and now >= bounds[1] - timedelta(minutes=15):
            closed = True
        for order in tx.execute(f"SELECT * FROM orders WHERE {PENDING} AND side='BUY'").fetchall():
            if (
                closed
                or (now - datetime.fromisoformat(order["created"])).total_seconds()
                >= e.settings.order_ttl_seconds
            ):
                e._cancel(tx, order, stamp(now), "EXPIRED_OR_SESSION_END")
        for position in tx.execute("SELECT * FROM positions").fetchall():
            latch = tx.execute(
                "SELECT value FROM meta WHERE key=?",
                (f"lt_exit:{position['symbol']}:{position['opened']}",),
            ).fetchone()
            if latch or e.db.get(tx, "kill") == "true":
                e._exit(tx, position["symbol"], now, latch[0] if latch else "KILL_SWITCH")
