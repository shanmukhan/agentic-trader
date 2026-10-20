"""Transactional paper broker and risk boundary. Never accepts a broker execution client."""

import hashlib
import json
import sqlite3
import threading
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any

from trading_agent.execution.costs import Charges, down, up
from trading_agent.market_data.calendar import IST, SessionCalendar
from trading_agent.models import Candidate, Instrument, Quote, RiskDecision, stamp, utc
from trading_agent.persistence.database import Database
from trading_agent.risk.limits import size
from trading_agent.risk.policy import policy_fingerprint
from trading_agent.settings import Settings

if TYPE_CHECKING:
    from trading_agent.ml.features import FeatureVector
    from trading_agent.ml.inference import ResearchModel

D = Decimal
PENDING = "state IN ('ACCEPTED','PARTIAL')"


class IntentConflict(ValueError):
    """An intent ID was reused for different economic instructions."""


class PaperBroker:
    def __init__(
        self,
        db: Database,
        settings: Settings,
        calendar: SessionCalendar,
        recovery_time: datetime | None = None,
        *,
        model: "ResearchModel | None" = None,
        automation: str | None = None,
    ):
        self.db, self.settings, self.calendar = db, settings, calendar
        self.model = model
        self.automation = automation
        self.charges = Charges()
        self.lock = threading.RLock()
        self.connected = False  # explicitly NOT restored; reconnect must provide fresh data
        self.faulted = False
        self.bad_symbols: set[str] = set()
        self.seen_symbols: set[str] = set()
        # Account policy cannot silently change across restarts.
        signature = policy_fingerprint(settings)
        with db.transaction() as tx:
            existing = tx.execute("SELECT value FROM meta WHERE key='policy_hash'").fetchone()
            if not existing and tx.execute("SELECT 1 FROM orders LIMIT 1").fetchone():
                raise RuntimeError("missing account policy fingerprint")
            if existing and existing[0] != signature:
                raise ValueError("risk policy changed: use a new paper account database")
            charges = tx.execute("SELECT value FROM meta WHERE key='charges_version'").fetchone()
            if existing and (not charges or charges[0] != self.charges.version):
                raise RuntimeError("missing or changed account charge schedule")
            db.set(tx, "policy_hash", signature)
            db.set(tx, "charges_version", self.charges.version)
            model_row = tx.execute("SELECT value FROM meta WHERE key='model_version'").fetchone()
            model_schema = tx.execute(
                "SELECT value FROM meta WHERE key='model_gate_schema'"
            ).fetchone()
            if bool(model_schema) != bool(model_row) or model_schema and model_schema[0] != "1":
                raise RuntimeError("missing or unsupported account model gate metadata")
            if (
                not model_schema
                and tx.execute(
                    "SELECT 1 FROM events WHERE kind='model_decision' LIMIT 1"
                ).fetchone()
            ):
                raise RuntimeError("missing account model gate fingerprint")
            model_version = model.version if model else "none"
            if model_row and model_row[0] != model_version:
                raise ValueError("account model changed; use a new research account")
            if not model_row and model and tx.execute("SELECT 1 FROM orders LIMIT 1").fetchone():
                raise ValueError("cannot attach a model to an existing unscored account")
            db.set(tx, "model_version", model_version)
            db.set(tx, "model_gate_schema", "1")
            auto_row = tx.execute("SELECT value FROM meta WHERE key='automation_hash'").fetchone()
            auto_events = tx.execute(
                "SELECT 1 FROM events WHERE kind='automation_start' LIMIT 1"
            ).fetchone()
            if bool(auto_row) != bool(auto_events):
                raise RuntimeError("missing account automation fingerprint")
            if auto_row and auto_row[0] != automation:
                raise ValueError("automation changed or removed; use the bound paper controller")
            if (
                not auto_row
                and automation
                and tx.execute("SELECT 1 FROM orders LIMIT 1").fetchone()
            ):
                raise ValueError("automation requires an unused dedicated paper account")
            # Pending orders from a dead process are cancelled before processing new signals.
            for row in tx.execute(f"SELECT * FROM orders WHERE {PENDING}").fetchall():
                self._cancel(tx, row, stamp(recovery_time or datetime.now(UTC)), "RESTART_RECOVERY")

    def set_connected(self, connected: bool) -> None:
        with self.lock:
            if not connected or connected != self.connected:
                self.seen_symbols.clear()
            self.connected = connected

    def register(self, instruments: list[Instrument]) -> None:
        with self.lock, self.db.transaction() as tx:
            for item in instruments:
                existing = tx.execute(
                    "SELECT * FROM instruments WHERE symbol=? OR token=?", (item.symbol, item.token)
                ).fetchall()
                if any(
                    row["symbol"] != item.symbol
                    or row["token"] != item.token
                    or D(row["tick"]) != item.tick_size
                    for row in existing
                ):
                    raise ValueError("instrument mapping changed; review a new catalog/database")
                tx.execute(
                    "INSERT OR IGNORE INTO instruments VALUES (?,?,?)",
                    (item.symbol, item.token, str(item.tick_size)),
                )

    def _quote(self, tx: sqlite3.Connection, symbol: str) -> Quote | None:
        row = tx.execute("SELECT payload FROM quotes WHERE symbol=?", (symbol,)).fetchone()
        return Quote.model_validate_json(row[0]) if row else None

    def _fresh(self, quote: Quote | None, now: datetime) -> bool:
        if (
            quote is None
            or quote.symbol in self.bad_symbols
            or quote.symbol not in self.seen_symbols
        ):
            return False
        age = self.settings.max_quote_age_seconds
        return (
            0 <= (now - quote.exchange_time).total_seconds() <= age
            and 0 <= (now - quote.received_time).total_seconds() <= age
        )

    def _tick(self, tx: sqlite3.Connection, symbol: str) -> Decimal:
        row = tx.execute("SELECT tick FROM instruments WHERE symbol=?", (symbol,)).fetchone()
        if row is None:
            raise ValueError("unknown instrument")
        return D(row[0])

    def _sell_price(self, tx: sqlite3.Connection, symbol: str, bid: Decimal) -> Decimal:
        return max(
            self._tick(tx, symbol),
            down(bid * (1 - self.settings.slippage_bps / 10000), self._tick(tx, symbol)),
        )

    def _snapshot(self, tx: sqlite3.Connection, now: datetime) -> dict[str, Any]:
        cash = D(self.db.get(tx, "cash"))
        reserved = D(0)
        pending_risk = D(0)
        pending_exposure = D(0)
        for row in tx.execute(f"SELECT * FROM orders WHERE {PENDING} AND side='BUY'"):
            reserved += D(row["reserved_cash"])
            pending_risk += D(row["reserved_risk"])
            pending_exposure += D(row["cap"]) * (row["quantity"] - row["filled"])
        positions = []
        value, exposure, open_risk = D(0), D(0), D(0)
        fresh = True
        for row in tx.execute("SELECT * FROM positions ORDER BY symbol"):
            quote = self._quote(tx, row["symbol"])
            fresh = fresh and self._fresh(quote, now)
            mark = quote.bid if quote else D(row["cost"]) / row["quantity"]
            exit_price = self._sell_price(tx, row["symbol"], mark)
            net = exit_price * row["quantity"] - self.charges.fee(
                "SELL", exit_price * row["quantity"]
            )
            stop_price = self._sell_price(tx, row["symbol"], D(row["stop"]))
            stop_net = stop_price * row["quantity"] - self.charges.fee(
                "SELL", stop_price * row["quantity"]
            )
            value += net
            exposure += max(mark * row["quantity"], D(row["cost"]))
            open_risk += max(D(0), net - stop_net)
            positions.append(
                {
                    **dict(row),
                    "liquidation_value": str(net),
                    "unrealized_pnl": str(net - D(row["cost"])),
                }
            )
        equity = cash + value
        return {
            "mode": "paper",
            "cash": str(cash),
            "reserved_cash": str(reserved),
            "available_cash": str(cash - reserved),
            "equity": str(equity),
            "positions": positions,
            "exposure": str(exposure + pending_exposure),
            "reserved_risk": str(open_risk + pending_risk),
            "day_pnl": str(equity - D(self.db.get(tx, "day_equity"))),
            "realized_pnl": self.db.get(tx, "total_realized"),
            "fees": self.db.get(tx, "fees"),
            "valuation_fresh": fresh,
            "feed_connected": self.connected,
            "faulted": self.faulted,
            "kill": self.db.get(tx, "kill") == "true",
            "kill_reason": self.db.get(tx, "kill_reason"),
            "loss_streak": int(self.db.get(tx, "loss_streak")),
            "day": self.db.get(tx, "day"),
            "charges_version": self.charges.version,
        }

    def snapshot(self, now: datetime) -> dict[str, Any]:
        with self.lock, self.db.transaction() as tx:
            return self._snapshot(tx, utc(now))

    def _roll_day(self, tx: sqlite3.Connection, now: datetime) -> None:
        today = now.astimezone(IST).date().isoformat()
        if self.db.get(tx, "day") == today:
            return
        if tx.execute("SELECT 1 FROM positions LIMIT 1").fetchone():
            self._kill(tx, stamp(now), "OVERNIGHT_POSITION")
            return
        for row in tx.execute(f"SELECT * FROM orders WHERE {PENDING}").fetchall():
            self._cancel(tx, row, stamp(now), "SESSION_ROLLOVER")
        self.db.set(tx, "day", today)
        self.db.set(tx, "day_equity", self.db.get(tx, "cash"))
        self.db.set(tx, "day_realized", "0")
        self.db.set(tx, "loss_streak", "0")

    def _entry_reasons(
        self, tx: sqlite3.Connection, quote: Quote | None, now: datetime
    ) -> list[str]:
        s = self.settings
        reasons = []
        if self.faulted:
            reasons.append("DATABASE_FAULT")
        if not self.connected:
            reasons.append("FEED_DISCONNECTED")
        if self.db.get(tx, "kill") == "true":
            reasons.append("KILL_SWITCH")
        if not self._fresh(quote, now):
            reasons.append("STALE_OR_MISSING_QUOTE")
        if not self.calendar.is_open(now):
            reasons.append("UNKNOWN_OR_CLOSED_SESSION")
        local = now.astimezone(IST)
        bounds = self.calendar.bounds(now)
        if not s.entry_start <= local.time() < s.entry_end:
            reasons.append("OUTSIDE_ENTRY_WINDOW")
        if bounds and now >= bounds[1] - timedelta(minutes=15):
            reasons.append("EARLY_CLOSE_CUTOFF")
        snapshot = self._snapshot(tx, now)
        if not snapshot["valuation_fresh"]:
            reasons.append("STALE_PORTFOLIO_VALUATION")
        if D(snapshot["exposure"]) > s.max_total_notional:
            reasons.append("TOTAL_EXPOSURE_LIMIT")
        if D(snapshot["day_pnl"]) <= -s.daily_loss_limit:
            reasons.append("DAILY_LOSS_LIMIT")
        if int(self.db.get(tx, "loss_streak")) >= s.max_consecutive_losses:
            reasons.append("LOSS_STREAK")
        if self.db.get(tx, "day") != local.date().isoformat():
            reasons.append("UNRESOLVED_PREVIOUS_SESSION")
        if quote:
            if quote.ask_size == 0 or quote.bid_size == 0:
                reasons.append("NO_LIQUIDITY")
            if (quote.ask - quote.bid) / quote.bid * 10000 > s.max_spread_bps:
                reasons.append("SPREAD_TOO_WIDE")
        return reasons

    def submit(
        self,
        candidate: Candidate,
        now: datetime,
        *,
        features: "FeatureVector | None" = None,
        automation: str | None = None,
    ) -> dict[str, Any]:
        now = utc(now)
        normalized = candidate.model_dump(mode="json")
        normalized["stop"] = format(candidate.stop.normalize(), "f")
        normalized["target"] = format(candidate.target.normalize(), "f")
        if features is not None:
            normalized["features"] = features.model_dump(mode="json")
        fingerprint = hashlib.sha256(json.dumps(normalized, sort_keys=True).encode()).hexdigest()
        try:
            with self.lock, self.db.transaction() as tx:
                old = tx.execute(
                    "SELECT * FROM orders WHERE id=?", (candidate.intent_id,)
                ).fetchone()
                if old:
                    if old["fingerprint"] != fingerprint:
                        raise IntentConflict("intent ID has different instructions")
                    return dict(old)
                self._roll_day(tx, now)
                quote = self._quote(tx, candidate.symbol)
                reasons = self._entry_reasons(tx, quote, now)
                if self.automation and automation != self.automation:
                    reasons.append("AUTOMATION_CONTROLLER_REQUIRED")
                age = (now - candidate.decision_time).total_seconds()
                if not 0 <= age <= self.settings.max_quote_age_seconds:
                    reasons.append("STALE_OR_FUTURE_DECISION")
                if self.model:
                    model_reasons = self.model.authorize(
                        candidate,
                        features,
                        now=now,
                        policy_sha256=policy_fingerprint(self.settings),
                        charges_version=self.charges.version,
                    )
                    reasons.extend(model_reasons)
                    self.db.event(
                        tx,
                        stamp(now),
                        "model_decision",
                        candidate.intent_id,
                        {
                            "model_sha256": self.model.version,
                            "reasons": model_reasons,
                            "features": features.model_dump(mode="json") if features else None,
                        },
                    )
                elif candidate.requires_ml:
                    reasons.append("MODEL_UNAVAILABLE")
                if tx.execute(
                    "SELECT 1 FROM positions WHERE symbol=?", (candidate.symbol,)
                ).fetchone():
                    reasons.append("POSITION_ALREADY_EXISTS")
                pending_symbols = {
                    r[0]
                    for r in tx.execute(f"SELECT symbol FROM orders WHERE {PENDING} AND side='BUY'")
                }
                held_symbols = {r[0] for r in tx.execute("SELECT symbol FROM positions")}
                if (
                    len(held_symbols | pending_symbols | {candidate.symbol})
                    > self.settings.max_positions
                ):
                    reasons.append("POSITION_LIMIT")
                if candidate.symbol in pending_symbols:
                    reasons.append("ENTRY_ALREADY_PENDING")
                decision = RiskDecision(allowed=False, reasons=tuple(reasons))
                if not reasons and quote:
                    tick = self._tick(tx, candidate.symbol)
                    price = up(quote.ask * (1 + self.settings.slippage_bps / 10000), tick)
                    if candidate.stop % tick or candidate.target % tick:
                        decision = RiskDecision(allowed=False, reasons=("INVALID_TICK_SIZE",))
                    elif candidate.stop >= quote.bid:
                        decision = RiskDecision(allowed=False, reasons=("STOP_ALREADY_TRIGGERED",))
                    else:
                        snapshot = self._snapshot(tx, now)
                        remaining = (
                            self.settings.daily_loss_limit
                            + D(snapshot["day_pnl"])
                            - D(snapshot["reserved_risk"])
                        )
                        decision = size(
                            price=price,
                            stop_fill=self._sell_price(tx, candidate.symbol, candidate.stop),
                            target_fill=self._sell_price(tx, candidate.symbol, candidate.target),
                            cash=D(snapshot["available_cash"]),
                            exposure_room=self.settings.max_total_notional
                            - D(snapshot["exposure"]),
                            position_cap=self.settings.max_position_notional,
                            risk_budget=max(D(0), min(self.settings.max_trade_risk, remaining)),
                            charges=self.charges,
                        )
                state = "ACCEPTED" if decision.allowed else "REJECTED"
                reason = ",".join(decision.reasons)
                tx.execute(
                    "INSERT INTO orders (id,fingerprint,symbol,side,state,quantity,cap,stop,"
                    "target,reserved_cash,reserved_risk,created,reason) VALUES "
                    "(?,?,?,'BUY',?,?,?,?,?,?,?,?,?)",
                    (
                        candidate.intent_id,
                        fingerprint,
                        candidate.symbol,
                        state,
                        decision.quantity,
                        str(decision.price_cap),
                        str(candidate.stop),
                        str(candidate.target),
                        str(decision.cash_reservation),
                        str(decision.risk_reservation),
                        stamp(now),
                        reason,
                    ),
                )
                self.db.event(
                    tx,
                    stamp(now),
                    "candidate",
                    candidate.intent_id,
                    candidate.model_dump(mode="json"),
                )
                self.db.event(
                    tx, stamp(now), "order_state", candidate.intent_id, {"state": "CREATED"}
                )
                self.db.event(
                    tx,
                    stamp(now),
                    "risk_decision",
                    candidate.intent_id,
                    decision.model_dump(mode="json"),
                )
                self.db.event(
                    tx,
                    stamp(now),
                    "order_state",
                    candidate.intent_id,
                    {"state": state, "reason": reason},
                )
                return dict(
                    tx.execute("SELECT * FROM orders WHERE id=?", (candidate.intent_id,)).fetchone()
                )
        except (sqlite3.Error, RuntimeError):
            self.faulted = True
            self.connected = False
            raise

    def _cancel(self, tx: sqlite3.Connection, order: sqlite3.Row, now: str, reason: str) -> None:
        tx.execute(
            "UPDATE orders SET state='CANCELLED',reserved_cash='0',reserved_risk='0',"
            "reason=? WHERE id=?",
            (reason, order["id"]),
        )
        self.db.event(tx, now, "order_state", order["id"], {"state": "CANCELLED", "reason": reason})

    def cancel(self, intent: str, now: datetime) -> dict[str, Any]:
        with self.lock, self.db.transaction() as tx:
            row = tx.execute("SELECT * FROM orders WHERE id=?", (intent,)).fetchone()
            if row is None:
                raise KeyError(intent)
            if row["state"] in ("ACCEPTED", "PARTIAL"):
                self._cancel(tx, row, stamp(now), "OPERATOR_CANCEL")
            return dict(tx.execute("SELECT * FROM orders WHERE id=?", (intent,)).fetchone())

    def _exit(self, tx: sqlite3.Connection, symbol: str, now: datetime, reason: str) -> None:
        for order in tx.execute(
            f"SELECT * FROM orders WHERE {PENDING} AND side='BUY' AND symbol=?", (symbol,)
        ).fetchall():
            self._cancel(tx, order, stamp(now), reason)
        if tx.execute(
            f"SELECT 1 FROM orders WHERE {PENDING} AND side='SELL' AND symbol=?", (symbol,)
        ).fetchone():
            return
        position = tx.execute("SELECT * FROM positions WHERE symbol=?", (symbol,)).fetchone()
        if position is None:
            return
        previous_event = tx.execute("SELECT seq FROM events ORDER BY seq DESC LIMIT 1").fetchone()
        sequence = (previous_event[0] if previous_event else 0) + 1
        identity = f"exit:{symbol}:{stamp(now)}:{sequence}"
        tx.execute(
            "INSERT INTO orders (id,fingerprint,symbol,side,state,quantity,cap,stop,target,"
            "reserved_cash,reserved_risk,created,reason) VALUES "
            "(?,?,?,'SELL','ACCEPTED',?,'0',?,?,'0','0',?,?)",
            (
                identity,
                identity,
                symbol,
                position["quantity"],
                position["stop"],
                position["target"],
                stamp(now),
                reason,
            ),
        )
        self.db.event(tx, stamp(now), "order_state", identity, {"state": "CREATED"})
        self.db.event(
            tx, stamp(now), "order_state", identity, {"state": "ACCEPTED", "reason": reason}
        )

    def _kill(self, tx: sqlite3.Connection, now: str, reason: str) -> None:
        if self.db.get(tx, "kill") != "true":
            self.db.set(tx, "kill", "true")
            self.db.set(tx, "kill_reason", reason)
            self.db.event(tx, now, "kill_switch", "system", {"enabled": True, "reason": reason})
        for row in tx.execute(f"SELECT * FROM orders WHERE {PENDING} AND side='BUY'").fetchall():
            self._cancel(tx, row, now, reason)
        for row in tx.execute("SELECT symbol FROM positions").fetchall():
            self._exit(tx, row[0], datetime.fromisoformat(now), reason)

    def kill(self, now: datetime, reason: str = "OPERATOR_KILL") -> None:
        with self.lock, self.db.transaction() as tx:
            self._kill(tx, stamp(now), reason)

    def reset_kill(self, now: datetime) -> None:
        with self.lock, self.db.transaction() as tx:
            if (
                tx.execute("SELECT 1 FROM positions").fetchone()
                or tx.execute(f"SELECT 1 FROM orders WHERE {PENDING}").fetchone()
            ):
                raise ValueError("flatten positions and resolve pending orders before reset")
            self._roll_day(tx, utc(now))
            snapshot = self._snapshot(tx, utc(now))
            if D(snapshot["day_pnl"]) <= -self.settings.daily_loss_limit:
                raise ValueError("daily loss limit still breached")
            if snapshot["loss_streak"] >= self.settings.max_consecutive_losses:
                raise ValueError("loss streak still breached; wait for next session")
            if self.faulted:
                raise ValueError("database fault requires verified restart")
            self.db.set(tx, "kill", "false")
            self.db.set(tx, "kill_reason", "")
            self.db.event(tx, stamp(now), "kill_switch", "system", {"enabled": False})

    def flatten(self, now: datetime) -> None:
        self.kill(now, "OPERATOR_FLATTEN")

    def _watch(self, tx: sqlite3.Connection, now: datetime) -> None:
        self._roll_day(tx, now)
        snapshot = self._snapshot(tx, now)
        if D(snapshot["day_pnl"]) <= -self.settings.daily_loss_limit:
            self._kill(tx, stamp(now), "DAILY_LOSS_LIMIT")
        if snapshot["loss_streak"] >= self.settings.max_consecutive_losses:
            self._kill(tx, stamp(now), "LOSS_STREAK")
        bounds = self.calendar.bounds(now)
        flatten = now.astimezone(IST).time() >= self.settings.flatten_at
        if bounds and now >= bounds[1] - timedelta(minutes=15):
            flatten = True
        for order in tx.execute(f"SELECT * FROM orders WHERE {PENDING} AND side='BUY'").fetchall():
            if (
                now - datetime.fromisoformat(order["created"])
            ).total_seconds() >= self.settings.order_ttl_seconds or flatten:
                self._cancel(tx, order, stamp(now), "EXPIRED_OR_SESSION_END")
        if flatten or snapshot["kill"]:
            for row in tx.execute("SELECT symbol FROM positions").fetchall():
                self._exit(tx, row[0], now, "SESSION_END" if flatten else "KILL_SWITCH")

    def poll(self, now: datetime) -> None:
        try:
            with self.lock, self.db.transaction() as tx:
                self._watch(tx, utc(now))
        except (sqlite3.Error, RuntimeError):
            self.faulted = True
            self.connected = False
            raise

    def ingest(self, quote: Quote, now: datetime) -> bool:
        now = utc(now)
        try:
            with self.lock, self.db.transaction() as tx:
                catalog = tx.execute(
                    "SELECT token FROM instruments WHERE symbol=?", (quote.symbol,)
                ).fetchone()
                if not catalog or catalog[0] != quote.token:
                    self.bad_symbols.add(quote.symbol)
                    raise ValueError("instrument mapping mismatch")
                tick = self._tick(tx, quote.symbol)
                if any(price % tick for price in (quote.last, quote.bid, quote.ask)):
                    self.bad_symbols.add(quote.symbol)
                    raise ValueError("quote price violates instrument tick size")
                previous = self._quote(tx, quote.symbol)
                if previous and quote.exchange_time <= previous.exchange_time:
                    if quote == previous:
                        return False
                    self.bad_symbols.add(quote.symbol)
                    self.db.event(
                        tx,
                        stamp(now),
                        "data_quality",
                        quote.symbol,
                        {"reason": "DUPLICATE_OR_OUT_OF_ORDER"},
                    )
                    return False
                same_day = (
                    previous
                    and previous.exchange_time.astimezone(IST).date()
                    == quote.exchange_time.astimezone(IST).date()
                )
                if same_day and previous and quote.volume < previous.volume:
                    self.bad_symbols.add(quote.symbol)
                    self.db.event(
                        tx,
                        stamp(now),
                        "data_quality",
                        quote.symbol,
                        {"reason": "VOLUME_REGRESSION"},
                    )
                    return False
                if (
                    not 0
                    <= (now - quote.received_time).total_seconds()
                    <= self.settings.max_quote_age_seconds
                ):
                    self.bad_symbols.add(quote.symbol)
                    return False
                self.bad_symbols.discard(quote.symbol)
                self.seen_symbols.add(quote.symbol)
                tx.execute(
                    "INSERT INTO quotes VALUES (?,?,?) ON CONFLICT(symbol) DO UPDATE SET "
                    "time=excluded.time,payload=excluded.payload",
                    (quote.symbol, stamp(quote.exchange_time), quote.model_dump_json()),
                )
                self.db.event(tx, stamp(now), "quote", quote.symbol, quote.model_dump(mode="json"))
                self._watch(tx, now)
                position = tx.execute(
                    "SELECT * FROM positions WHERE symbol=?", (quote.symbol,)
                ).fetchone()
                if position and (
                    quote.bid <= D(position["stop"]) or quote.bid >= D(position["target"])
                ):
                    self._exit(
                        tx,
                        quote.symbol,
                        now,
                        "STOP" if quote.bid <= D(position["stop"]) else "TARGET",
                    )
                # Stop cancellation also covers a not-yet-filled entry.
                for order in tx.execute(
                    f"SELECT * FROM orders WHERE {PENDING} AND side='BUY' AND symbol=?",
                    (quote.symbol,),
                ).fetchall():
                    if quote.bid <= D(order["stop"]) or quote.bid >= D(order["target"]):
                        self._cancel(tx, order, stamp(now), "STOP_OR_TARGET_BEFORE_FILL")
                self._process(tx, quote, now)
                self._watch(tx, now)
                return True
        except (sqlite3.Error, RuntimeError):
            self.faulted = True
            self.connected = False
            raise

    def _process(self, tx: sqlite3.Connection, quote: Quote, now: datetime) -> None:
        if not self._fresh(quote, now) or not self.connected or not self.calendar.is_open(now):
            return
        liquidity = {"BUY": quote.ask_size, "SELL": quote.bid_size}
        orders = tx.execute(
            f"SELECT * FROM orders WHERE {PENDING} AND symbol=? ORDER BY created,id",
            (quote.symbol,),
        ).fetchall()
        for order in orders:
            created = datetime.fromisoformat(order["created"])
            if quote.exchange_time <= created or quote.exchange_time < created + timedelta(
                milliseconds=self.settings.latency_ms
            ):
                continue
            side = order["side"]
            if side == "BUY":
                reasons = self._entry_reasons(tx, quote, now)
                if reasons:
                    self._cancel(tx, order, stamp(now), ",".join(reasons))
                    continue
                price = up(
                    quote.ask * (1 + self.settings.slippage_bps / 10000),
                    self._tick(tx, quote.symbol),
                )
                if price > D(order["cap"]):
                    self._cancel(tx, order, stamp(now), "PRICE_CAP_EXCEEDED")
                    continue
            else:
                price = self._sell_price(tx, quote.symbol, quote.bid)
            quantity = min(order["quantity"] - order["filled"], liquidity[side])
            if quantity <= 0:
                continue
            liquidity[side] -= quantity
            self._fill(tx, order, quantity, price, now)

    def _fill(
        self, tx: sqlite3.Connection, order: sqlite3.Row, qty: int, price: Decimal, now: datetime
    ) -> None:
        turnover = D(order["turnover"]) + price * qty
        fees_total = self.charges.fee(order["side"], turnover)
        fee = fees_total - D(order["fees"])
        cash = D(self.db.get(tx, "cash"))
        position = tx.execute(
            "SELECT * FROM positions WHERE symbol=?", (order["symbol"],)
        ).fetchone()
        if order["side"] == "BUY":
            cash -= price * qty + fee
            cost = price * qty + fee + (D(position["cost"]) if position else D(0))
            total_qty = qty + (position["quantity"] if position else 0)
            tx.execute(
                "INSERT INTO positions VALUES (?,?,?,?,?,?) ON CONFLICT(symbol) DO UPDATE SET "
                "quantity=excluded.quantity,cost=excluded.cost",
                (order["symbol"], total_qty, str(cost), order["stop"], order["target"], stamp(now)),
            )
        else:
            if position is None or qty > position["quantity"]:
                raise RuntimeError("paper sell exceeds position")
            cash += price * qty - fee
            # Pro-rata cost allocation remains exact: final sale takes the entire residual basis.
            cost = (
                D(position["cost"])
                if qty == position["quantity"]
                else D(position["cost"]) * D(qty) / position["quantity"]
            )
            realized = price * qty - fee - cost
            for key in ("total_realized", "day_realized"):
                self.db.set(tx, key, D(self.db.get(tx, key)) + realized)
            # Count one completed exit order as one trade, including earlier partial exit P&L.
            pnl_key = "trade_pnl:" + order["symbol"] + ":" + position["opened"]
            old = tx.execute("SELECT value FROM meta WHERE key=?", (pnl_key,)).fetchone()
            accumulated = (D(old[0]) if old else D(0)) + realized
            self.db.set(tx, pnl_key, accumulated)
            if qty == position["quantity"]:
                tx.execute("DELETE FROM positions WHERE symbol=?", (order["symbol"],))
                streak = int(self.db.get(tx, "loss_streak")) + 1 if accumulated < 0 else 0
                self.db.set(tx, "loss_streak", streak)
            else:
                tx.execute(
                    "UPDATE positions SET quantity=quantity-?,cost=? WHERE symbol=?",
                    (qty, str(D(position["cost"]) - cost), order["symbol"]),
                )
        if cash < 0:
            raise RuntimeError("negative paper cash invariant")
        filled = order["filled"] + qty
        remaining = order["quantity"] - filled
        state = "FILLED" if remaining == 0 else "PARTIAL"
        cap = D(order["cap"])
        reserve_cash = (
            cap * remaining + self.charges.fee("BUY", turnover + cap * remaining) - fees_total
            if remaining and order["side"] == "BUY"
            else D(0)
        )
        reserve_risk = (
            D(order["reserved_risk"]) * D(remaining) / (order["quantity"] - order["filled"])
        )
        tx.execute(
            "UPDATE orders SET state=?,filled=?,turnover=?,fees=?,reserved_cash=?,"
            "reserved_risk=? WHERE id=?",
            (
                state,
                filled,
                str(turnover),
                str(fees_total),
                str(reserve_cash),
                str(reserve_risk),
                order["id"],
            ),
        )
        tx.execute(
            "INSERT INTO fills(order_id,time,quantity,price,fees) VALUES (?,?,?,?,?)",
            (order["id"], stamp(now), qty, str(price), str(fee)),
        )
        self.db.set(tx, "cash", cash)
        self.db.set(tx, "fees", D(self.db.get(tx, "fees")) + fee)
        self.db.event(
            tx,
            stamp(now),
            "fill",
            order["id"],
            {"quantity": qty, "price": str(price), "fees": str(fee)},
        )
        self.db.event(tx, stamp(now), "order_state", order["id"], {"state": state})

    def orders(self) -> list[dict[str, Any]]:
        with self.lock, self.db.transaction() as tx:
            return [dict(row) for row in tx.execute("SELECT * FROM orders ORDER BY created,id")]
