"""Durable operator restrictions layered over the account's bound economic policy.

Enabled for CLI/API accounts, retained on restart, and never enabled implicitly for
isolated historical research. All mutation helpers require the engine lock and tx.
"""

import json
from datetime import datetime, time, timedelta
from decimal import ROUND_DOWN, Decimal
from typing import Any

from trading_agent.market_data.calendar import IST
from trading_agent.models import stamp

D = Decimal
KEY = "operator_safety_v1"


class OperatorSafety:
    def __init__(self, engine: Any):
        self.engine = engine

    def state(self, tx: Any) -> dict[str, Any] | None:
        row = tx.execute("SELECT value FROM meta WHERE key=?", (KEY,)).fetchone()
        if not row:
            if tx.execute("SELECT 1 FROM meta WHERE key='operator_safety_required'").fetchone():
                raise RuntimeError("missing durable operator safety state")
            return None
        try:
            state = json.loads(row[0])
            if (
                state.get("schema_version") != 1
                or type(state.get("revision")) is not int
                or type(state.get("paused")) is not bool
                or not isinstance(state.get("symbols"), list)
                or any(not isinstance(s, str) or not s.startswith("NSE:") for s in state["symbols"])
                or len(set(state["symbols"])) != len(state["symbols"])
                or not isinstance(state["blocked_day"], str)
                or not isinstance(state["pause_reason"], str)
                or not isinstance(state["data_reason"], str)
                or not D(state["peak_equity"]).is_finite()
                or D(state["peak_equity"]) <= 0
            ):
                raise ValueError
        except (ValueError, KeyError, TypeError, ArithmeticError, AttributeError):
            raise RuntimeError("invalid durable operator safety state") from None
        return state

    def save(self, tx: Any, state: dict[str, Any]) -> None:
        self.engine.db.set(tx, KEY, json.dumps(state, sort_keys=True))

    def enable(self, now: datetime) -> None:
        e = self.engine
        with e.lock, e.db.transaction() as tx:
            if self.state(tx) is not None:
                return
            snapshot = e._snapshot(tx, now)
            peak = e.settings.starting_cash
            if snapshot["valuation_fresh"]:
                peak = max(peak, D(snapshot["equity"]))
            row = tx.execute("SELECT value FROM meta WHERE key='lt_peak_equity'").fetchone()
            if row:
                peak = max(peak, D(row[0]))
            self.save(
                tx,
                {
                    "schema_version": 1,
                    "revision": 1,
                    "symbols": [],
                    "peak_equity": str(peak),
                    "paused": False,
                    "pause_reason": "",
                    "blocked_day": "",
                    "data_reason": "",
                    "enabled_at": stamp(now),
                },
            )
            e.db.set(tx, "operator_safety_required", "1")
            # An upgrade cannot leave previously authorized buys executable.
            self.cancel_buys(tx, now, "WATCHLIST_REVIEW_REQUIRED")
            e.db.event(tx, stamp(now), "operator_safety_enabled", "system", {"peak": str(peak)})
            self.observe(tx, now, snapshot)

    def count(self, tx: Any, now: datetime) -> int:
        day = now.astimezone(IST).date()
        start = datetime.combine(day, time(), IST)
        end = start + timedelta(days=1)
        # Accepted intents consume a slot even if cancelled without a fill. Replays,
        # partial fills and rejected intents never consume additional slots.
        return int(
            tx.execute(
                "SELECT count(*) FROM orders WHERE side='BUY' AND quantity>0 "
                "AND created>=? AND created<?",
                (stamp(start), stamp(end)),
            ).fetchone()[0]
        )

    def allows(self, tx: Any, symbol: str) -> bool:
        state = self.state(tx)
        return state is None or symbol in state["symbols"]

    def reasons(self, tx: Any, now: datetime, *, for_fill: bool = False) -> list[str]:
        state = self.state(tx)
        if state is None:
            return []
        reasons = []
        if not state["symbols"]:
            reasons.append("WATCHLIST_EMPTY")
        if state["paused"]:
            reasons.append("SAFETY_PAUSED")
        if state["blocked_day"] == now.astimezone(IST).date().isoformat():
            reasons.append("DATA_QUALITY_DAY_BLOCK")
        if not for_fill and self.count(tx, now) >= 5:
            reasons.append("DAILY_TRADE_LIMIT")
        return reasons

    def budget(self, tx: Any, snapshot: dict[str, Any]) -> Decimal:
        if self.state(tx) is None:
            return D(snapshot["available_cash"])
        return max(D(0), D(snapshot["equity"]) * D("0.25")).quantize(D("0.01"), rounding=ROUND_DOWN)

    def cancel_buys(self, tx: Any, now: datetime, reason: str) -> None:
        for row in tx.execute(
            "SELECT * FROM orders WHERE side='BUY' AND state IN ('ACCEPTED','PARTIAL')"
        ).fetchall():
            self.engine._cancel(tx, row, stamp(now), reason)

    def observe(self, tx: Any, now: datetime, snapshot: dict[str, Any]) -> None:
        state = self.state(tx)
        if state is None or not snapshot["valuation_fresh"]:
            return
        equity = D(snapshot["equity"])
        peak = max(D(state["peak_equity"]), equity)
        changed = peak != D(state["peak_equity"])
        state["peak_equity"] = str(peak)
        if not state["paused"] and equity <= peak * D("0.75"):
            state.update(paused=True, pause_reason="PEAK_DRAWDOWN_25_PERCENT")
            state["revision"] += 1
            changed = True
            self.cancel_buys(tx, now, "SAFETY_PAUSED")
            self.engine.db.event(
                tx,
                stamp(now),
                "safety_pause",
                "system",
                {
                    "equity": str(equity),
                    "peak_equity": str(peak),
                    "limit_pct": "25",
                },
            )
        if changed:
            self.save(tx, state)

    def block_data(self, tx: Any, now: datetime, reason: str) -> None:
        state = self.state(tx)
        if state is None:
            return
        day = now.astimezone(IST).date().isoformat()
        if state["blocked_day"] != day:
            state.update(blocked_day=day, data_reason=reason, revision=state["revision"] + 1)
            self.save(tx, state)
            self.engine.db.event(
                tx,
                stamp(now),
                "safety_data_block",
                "system",
                {
                    "day": day,
                    "reason": reason,
                },
            )
        self.cancel_buys(tx, now, "DATA_QUALITY_DAY_BLOCK")

    def replace(self, tx: Any, symbols: list[str], revision: int, now: datetime) -> None:
        state = self.state(tx)
        if state is None or revision != state["revision"]:
            raise ValueError("Watchlist or safety state changed. Refresh and review again.")
        if len(symbols) > 3000 or len(set(symbols)) != len(symbols):
            raise ValueError("Choose up to 3000 distinct NSE catalog symbols.")
        for symbol in symbols:
            if (
                not symbol.startswith("NSE:")
                or not tx.execute(
                    "SELECT 1 FROM instruments WHERE symbol=? AND (token & 255)=1", (symbol,)
                ).fetchone()
            ):
                raise ValueError("Choose supported NSE instruments from the imported catalog.")
        state.update(symbols=sorted(symbols), revision=state["revision"] + 1)
        self.save(tx, state)
        self.cancel_buys(tx, now, "WATCHLIST_CHANGED_REVIEW_REQUIRED")
        self.engine.db.event(
            tx,
            stamp(now),
            "watchlist_changed",
            "system",
            {
                "symbols": state["symbols"],
                "revision": state["revision"],
            },
        )

    def resume(self, tx: Any, revision: int, now: datetime) -> None:
        state = self.state(tx)
        if state is None or state["revision"] != revision or not state["paused"]:
            raise ValueError("Safety state changed. Refresh and review again.")
        self.engine.db.reconcile(tx)
        snapshot = self.engine._snapshot(tx, now)
        if not snapshot["valuation_fresh"] or D(snapshot["equity"]) <= 0 or self.engine.faulted:
            raise ValueError("A reconciled account with a current positive valuation is required.")
        # The operator acknowledges a new reference. Independent kill/daily-loss
        # gates and the current day's data lockout remain in force.
        state.update(
            paused=False,
            pause_reason="",
            peak_equity=snapshot["equity"],
            revision=state["revision"] + 1,
        )
        self.save(tx, state)
        self.engine.db.event(
            tx,
            stamp(now),
            "safety_resumed",
            "system",
            {
                "new_peak_equity": snapshot["equity"],
                "revision": state["revision"],
            },
        )

    def view(self, tx: Any, now: datetime, snapshot: dict[str, Any]) -> dict[str, Any] | None:
        state = self.state(tx)
        if state is None:
            return None
        peak = D(state["peak_equity"])
        return {
            **state,
            "entries_today": self.count(tx, now),
            "max_entries_per_day": 5,
            "max_order_pct": "25",
            "max_order_cost": str(self.budget(tx, snapshot)),
            "drawdown_limit_pct": "25",
            "drawdown_pct": str(max(D(0), (peak - D(snapshot["equity"])) / peak * 100)),
            "valuation_fresh": snapshot["valuation_fresh"],
            "data_blocked_today": state["blocked_day"] == now.astimezone(IST).date().isoformat(),
            "external_cash_flows_supported": False,
        }
