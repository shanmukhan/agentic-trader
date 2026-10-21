"""Durable proposals and bounded paper authority. No broker execution transport exists."""

import json
import secrets
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from trading_agent.desk.accounting import prepared_fingerprint, reconcile_desk
from trading_agent.desk.contracts import digest
from trading_agent.desk.research import Research
from trading_agent.execution.costs import down, up
from trading_agent.execution.paper_broker import PENDING, PaperBroker
from trading_agent.market_data.calendar import IST
from trading_agent.ml.features import make_features
from trading_agent.models import Candidate, Candle, Instrument, Quote, RiskDecision, stamp, utc
from trading_agent.risk.policy import policy_fingerprint

D = Decimal
TERMINAL = {"submitted", "rejected", "cancelled", "expired", "blocked"}


class DeskError(ValueError):
    pass


class TradingDesk:
    def __init__(
        self,
        engine: PaperBroker,
        now: datetime,
        *,
        profile: Path | None = None,
        automation: Any = None,
        synthetic: bool = False,
        clock: Callable[[], datetime] | None = None,
    ):
        self.engine, self.automation = engine, automation
        self.research: Research | None = None
        self.problem = "NO_ANALYSIS_PROFILE"
        self.revision = secrets.token_hex(16)
        self.mode = "automatic" if automation else "manual"
        self.mode_day = now.astimezone(IST).date()
        self.synthetic = synthetic or bool(automation and automation.synthetic)
        self.clock = clock if clock else None if self.synthetic else lambda: datetime.now(UTC)
        self.reason = "STARTUP_DISARMED"
        self.last_analysis: str | None = None
        self.analysis_error: str | None = None
        if profile and not automation:
            try:
                self.research = Research(engine, profile, now, synthetic=synthetic)
                self.problem = ""
            except Exception:
                self.problem = "ANALYSIS_PROFILE_INVALID_OR_UNAVAILABLE"
        if automation:
            self.problem = ""
        with engine.lock, engine.db.transaction() as tx:
            reconcile_desk(tx)
            for row in tx.execute(
                "SELECT payload FROM desk_decisions "
                "WHERE state IN ('awaiting_approval','authorized')"
            ).fetchall():
                record = json.loads(row[0])
                order = (
                    tx.execute(
                        "SELECT id,state,fingerprint FROM orders WHERE id=?", (record["intent_id"],)
                    ).fetchone()
                    if record["state"] == "authorized"
                    else None
                )
                if order and order["fingerprint"] != prepared_fingerprint(record):
                    raise RuntimeError("recovered decision differs from committed order")
                record.update(
                    state=("rejected" if order["state"] == "REJECTED" else "submitted")
                    if order
                    else "cancelled",
                    order_id=order["id"] if order else None,
                    outcome="RESTART_RECOVERY_NO_REPLAY",
                )
                self._save(tx, record, now)

    @property
    def identity(self) -> str:
        return (
            self.research.identity
            if self.research
            else self.automation.digest
            if self.automation
            else "unconfigured"
        )

    @property
    def execution_tokens(self) -> tuple[int, ...]:
        return (
            tuple(i.token for i in self.automation.catalog.values())
            if self.automation
            else self.engine.settings.stream_tokens
        )

    def _save(self, tx: Any, record: dict[str, Any], now: datetime) -> None:
        record["updated_at"] = stamp(now)
        tx.execute(
            "INSERT INTO desk_decisions VALUES (?,?,?,?) ON CONFLICT(id) "
            "DO UPDATE SET state=excluded.state,payload=excluded.payload",
            (
                record["id"],
                record["created_at"],
                record["state"],
                json.dumps(record, sort_keys=True, default=str),
            ),
        )
        self.engine.db.event(tx, stamp(now), "desk_decision", record["id"], record)

    def _get(self, tx: Any, identity: str) -> dict[str, Any]:
        row = tx.execute("SELECT payload FROM desk_decisions WHERE id=?", (identity,)).fetchone()
        if not row:
            raise DeskError("Unknown trade decision.")
        return dict(json.loads(row[0]))

    def blockers(self, now: datetime) -> list[str]:
        e = self.engine
        reasons = []
        if self.problem:
            reasons.append(self.problem)
        if self.analysis_error:
            reasons.append(self.analysis_error)
        if e.faulted:
            reasons.append("ACCOUNT_FAULTED")
        if not e.connected:
            reasons.append("FEED_DISCONNECTED")
        if not e.calendar.is_open(now):
            reasons.append("UNKNOWN_OR_CLOSED_SESSION")
        if not e.settings.entry_start <= now.astimezone(IST).time() < e.settings.entry_end:
            reasons.append("OUTSIDE_ENTRY_WINDOW")
        if e.snapshot(now)["kill"]:
            reasons.append("KILL_SWITCH")
        with e.lock, e.db.transaction() as tx:
            selected = (
                [
                    e._quote(tx, r[0])
                    for r in tx.execute(
                        "SELECT symbol FROM instruments WHERE token IN ("
                        + ",".join("?" for _ in self.execution_tokens)
                        + ")",
                        self.execution_tokens,
                    )
                ]
                if self.execution_tokens
                else []
            )
            if not selected:
                reasons.append("NO_EXECUTION_SHORTLIST")
            elif not any(e._fresh(q, now) for q in selected):
                reasons.append("NO_FRESH_EXECUTION_QUOTES")
        if self.research:
            day = now.astimezone(IST).date()
            sessions = {s.day: (s.open, s.close) for s in self.research.dataset.manifest.sessions}
            if day not in sessions or sessions[day] != e.calendar.sessions.get(day):
                reasons.append("RESEARCH_CALENDAR_NOT_CURRENT")
            model = self.research.model
            if model and (
                now <= model.artifact.available_after
                or now - model.artifact.validated_through
                > timedelta(days=self.research.profile.max_model_age_days)
            ):
                reasons.append("ML_MODEL_NOT_CURRENT")
            with e.lock, e.db.transaction() as tx:
                reviewed = {s.symbol for s in self.research.profile.shares}
                if any(r[0] not in reviewed for r in tx.execute("SELECT symbol FROM positions")):
                    reasons.append("UNSUPPORTED_HELD_ASSET_CLASS")
        return reasons

    def set_mode(self, mode: str, now: datetime, expected_revision: str) -> dict[str, Any]:
        with self.engine.lock:
            if expected_revision != self.revision:
                raise DeskError("Mode changed in another request. Refresh and review again.")
            if mode not in ("manual", "approval", "automatic"):
                raise DeskError("Choose manual, approval or automatic paper mode.")
            if mode != "manual":
                reasons = self.blockers(now)
                if reasons:
                    raise DeskError("Cannot start paper decisions: " + ", ".join(reasons))
            self.pause(now, "MODE_CHANGED")
            if mode != "manual" and self.automation:
                try:
                    self.automation.arm(now)
                except ValueError:
                    raise DeskError(
                        "Intraday controller is not ready. "
                        "Check history, quotes and risk safeguards."
                    ) from None
                self.automation.dispatch = self.offer
            self.mode, self.mode_day, self.reason = (
                mode,
                now.astimezone(IST).date(),
                "OPERATOR_MODE_CHANGE",
            )
            with self.engine.db.transaction() as tx:
                self.engine.db.event(
                    tx,
                    stamp(now),
                    "desk_mode",
                    "system",
                    {"mode": mode, "revision": self.revision, "profile": self.identity},
                )
            return self.view(now)

    def pause(self, now: datetime, reason: str) -> None:
        with self.engine.lock:
            # Revoke authority even if durable cancellation encounters an I/O fault.
            self.mode, self.reason, self.revision = "manual", reason, secrets.token_hex(16)
            if self.automation:
                self.automation.disarm(now, reason)
            with self.engine.db.transaction() as tx:
                for row in tx.execute(
                    "SELECT payload FROM desk_decisions WHERE state='awaiting_approval'"
                ).fetchall():
                    record = json.loads(row[0])
                    record.update(state="cancelled", outcome=reason)
                    self._save(tx, record, now)
                # Cancel desk buys; retain held shares and protective exits.
                for row in tx.execute(
                    "SELECT o.* FROM orders o JOIN desk_decisions d "
                    "ON json_extract(d.payload,'$.order_id')=o.id "
                    "WHERE o.side='BUY' AND o.state IN ('ACCEPTED','PARTIAL')"
                ).fetchall():
                    self.engine._cancel(tx, row, stamp(now), reason)

    def tick(self, now: datetime) -> None:
        with self.engine.lock:
            if self.mode != "manual" and (
                self.mode_day != now.astimezone(IST).date()
                or self.engine.faulted
                or not self.engine.connected
                or self.engine.snapshot(now)["kill"]
                or self.automation
                and not self.automation.armed
                or any(
                    reason
                    in {
                        "NO_FRESH_EXECUTION_QUOTES",
                        "ML_MODEL_NOT_CURRENT",
                        "UNSUPPORTED_HELD_ASSET_CLASS",
                    }
                    for reason in self.blockers(now)
                )
            ):
                self.pause(now, "SESSION_FEED_OR_RISK_PAUSE")
            with self.engine.db.transaction() as tx:
                for row in tx.execute(
                    "SELECT payload FROM desk_decisions WHERE state='awaiting_approval' AND time<?",
                    (stamp(now),),
                ).fetchall():
                    record = json.loads(row[0])
                    if now > datetime.fromisoformat(record["expires_at"]):
                        record.update(state="expired", outcome="APPROVAL_WINDOW_ENDED")
                        self._save(tx, record, now)

    def offer(
        self,
        candidate: Candidate | None,
        now: datetime,
        context: dict[str, Any],
        *,
        symbol: str | None = None,
        side: str = "BUY",
    ) -> dict[str, Any] | None:
        with self.engine.lock:
            if self.mode == "manual" or self.mode_day != now.astimezone(IST).date():
                return None
            symbol = candidate.symbol if candidate else symbol
            if not symbol or side not in ("BUY", "SELL"):
                raise DeskError("Invalid internal trade proposal.")
            identity = digest(
                [
                    self.identity,
                    symbol,
                    side,
                    now.astimezone(IST).date().isoformat(),
                    context.get(
                        "signal_key", candidate.intent_id if candidate else context["reason"]
                    ),
                ]
            )[:48]
            with self.engine.db.transaction() as tx:
                old = tx.execute(
                    "SELECT payload FROM desk_decisions WHERE id=?", (identity,)
                ).fetchone()
                if old:
                    return json.loads(old[0])
                if (
                    tx.execute(
                        "SELECT count(*) FROM desk_decisions WHERE state='awaiting_approval'"
                    ).fetchone()[0]
                    >= 100
                ):
                    return None
                quote = self.engine._quote(tx, symbol)
                seconds = self.research.profile.approval_seconds if self.research else 120
                record = {
                    "id": identity,
                    "intent_id": candidate.intent_id if candidate else "desk-exit-" + identity,
                    "created_at": stamp(now),
                    "expires_at": stamp(now + timedelta(seconds=seconds)),
                    "symbol": symbol,
                    "side": side,
                    "horizon": self.engine.settings.investment_horizon,
                    "state": "awaiting_approval",
                    "mode": self.mode,
                    "revision": self.revision,
                    "profile": self.identity,
                    "candidate": candidate.model_dump(mode="json") if candidate else None,
                    "context": context,
                    "reference_quote": quote.model_dump(mode="json") if quote else None,
                    "order_id": None,
                    "outcome": "WAITING_FOR_OPERATOR"
                    if self.mode == "approval"
                    else "AUTOMATIC_RISK_CHECK",
                }
                self._save(tx, record, now)
            if self.mode == "automatic":
                try:
                    review = self.preview(identity, now)
                    if review["review"]["allowed"]:
                        return self.approve(identity, review["preview_sha256"], now, automatic=True)
                    with self.engine.db.transaction() as tx:
                        record = self._get(tx, identity)
                        record.update(
                            state="blocked", outcome=", ".join(review["review"]["reasons"])
                        )
                        self._save(tx, record, now)
                except DeskError:
                    with self.engine.db.transaction() as tx:
                        record = self._get(tx, identity)
                        record.update(state="blocked", outcome="EXECUTION_REVALIDATION_FAILED")
                        self._save(tx, record, now)
            return record

    def _prepare(
        self, tx: Any, record: dict[str, Any], now: datetime, quantity_limit: int | None = None
    ) -> tuple[Candidate | None, Any, RiskDecision, dict[str, Any]]:
        e, symbol = self.engine, record["symbol"]
        reasons = []
        if (
            record["profile"] != self.identity
            or record["revision"] != self.revision
            or record["mode"] != self.mode
            or self.mode == "manual"
        ):
            reasons.append("MODE_OR_POLICY_CHANGED")
        if now > datetime.fromisoformat(record["expires_at"]) or now < datetime.fromisoformat(
            record["created_at"]
        ):
            reasons.append("APPROVAL_WINDOW_ENDED")
        quote = e._quote(tx, symbol)
        if not e.connected or not e._fresh(quote, now):
            reasons.append("STALE_OR_MISSING_QUOTE")
        if not self.synthetic and quote and quote.source != "kite":
            reasons.append("REAL_FEED_REQUIRED")
        catalog = tx.execute("SELECT * FROM instruments WHERE symbol=?", (symbol,)).fetchone()
        if not catalog or catalog["token"] not in self.execution_tokens:
            reasons.append("SYMBOL_OUTSIDE_EXECUTION_SHORTLIST")
        if catalog and catalog["token"] & 255 != 1:
            reasons.append("UNSUPPORTED_FEED_INSTRUMENT")
        if e.faulted:
            reasons.append("ACCOUNT_FAULTED")
        if self.automation and not self.automation.armed:
            reasons.append("AUTOMATION_NOT_READY")
        if self.research and symbol not in {s.symbol for s in self.research.profile.shares}:
            reasons.append("EQUITY_SHARE_CLASS_NOT_REVIEWED")
        reference = (
            Quote.model_validate(record["reference_quote"]) if record["reference_quote"] else None
        )
        drift = self.research.profile.max_price_drift_bps if self.research else D(20)
        moved = (
            (quote.bid / reference.bid if record["side"] == "SELL" else quote.ask / reference.ask)
            if quote and reference
            else D(1)
        )
        if abs(moved - 1) * 10000 > drift:
            reasons.append("PRICE_MOVED_REVIEW_NEW_PROPOSAL")
        if record["side"] == "SELL":
            holding = tx.execute("SELECT * FROM positions WHERE symbol=?", (symbol,)).fetchone()
            if not holding or dict(holding) != record["context"].get("holding"):
                reasons.append("HOLDING_CHANGED")
            if tx.execute(
                f"SELECT 1 FROM orders WHERE {PENDING} AND side='SELL' AND symbol=?", (symbol,)
            ).fetchone():
                reasons.append("EXIT_ALREADY_QUEUED")
            if not e.calendar.is_open(now):
                reasons.append("UNKNOWN_OR_CLOSED_SESSION")
            return (
                None,
                None,
                RiskDecision(
                    allowed=not reasons,
                    reasons=tuple(reasons),
                    quantity=holding["quantity"] if holding else 0,
                ),
                {"quote": quote.model_dump(mode="json") if quote else None},
            )
        candidate = Candidate.model_validate(record["candidate"]).model_copy(
            update={"decision_time": utc(now)}
        )
        if tx.execute("SELECT 1 FROM orders WHERE id=?", (candidate.intent_id,)).fetchone():
            reasons.append("DUPLICATE_INTENT")
        features: Any = None
        probability = None
        if quote:
            reasons.extend(e._entry_reasons(tx, quote, now))
            if tx.execute(
                f"SELECT 1 FROM orders WHERE {PENDING} AND side='BUY' AND symbol=?", (symbol,)
            ).fetchone():
                reasons.append("ENTRY_ALREADY_PENDING")
            if tx.execute("SELECT 1 FROM positions WHERE symbol=?", (symbol,)).fetchone():
                reasons.append("POSITION_ALREADY_EXISTS")
            count = tx.execute(
                "SELECT count(DISTINCT symbol) FROM (SELECT symbol FROM positions UNION "
                "SELECT symbol FROM orders WHERE state IN ('ACCEPTED','PARTIAL') AND side='BUY')"
            ).fetchone()[0]
            if count >= e.settings.max_positions:
                reasons.append("POSITION_LIMIT")
            if self.research:
                context = record["context"]
                if context["kind"] == "daily":
                    if (
                        abs(quote.ask / D(context["screen"]["last_close"]) - 1) * 10000
                        > self.research.profile.long_term.max_entry_gap_bps
                    ):
                        reasons.append("DAILY_ENTRY_GAP")
                elif (
                    abs(quote.ask / D(context["candle"]["close"]) - 1) * 10000
                    > self.research.profile.intraday.max_quote_gap_bps
                ):
                    reasons.append("QUOTE_CANDLE_PRICE_GAP")
        model: Any = self.research.model if self.research else e.model
        if model and quote and catalog:
            if (
                now <= model.artifact.available_after
                or now - model.artifact.validated_through
                > timedelta(
                    days=self.research.profile.max_model_age_days
                    if self.research
                    else self.automation.settings.max_model_age_days
                )
            ):
                reasons.append("ML_MODEL_NOT_CURRENT")
            try:
                candidate = candidate.model_copy(
                    update={"model_version": model.version, "requires_ml": e.model is not None}
                )
                if record["context"]["kind"] == "intraday":
                    candle = Candle.model_validate(record["context"]["candle"])
                    bounds = e.calendar.bounds(now)
                    if bounds is None:
                        raise ValueError
                    features = make_features(
                        candidate=candidate,
                        candle=candle,
                        candle_end=candle.start + timedelta(minutes=5),
                        features=record["context"]["features"],
                        quote=quote,
                        instrument=Instrument(
                            symbol=symbol, token=catalog["token"], tick_size=catalog["tick"]
                        ),
                        opened=bounds[0],
                        policy=e.settings,
                    )
                    probability = model.score(features)
                    reasons.extend(
                        model.authorize(
                            candidate.model_copy(update={"requires_ml": True}),
                            features,
                            now=now,
                            policy_sha256=policy_fingerprint(e.settings),
                            charges_version=e.charges.version,
                        )
                    )
                else:
                    from trading_agent.desk.signals import daily_vector

                    features = daily_vector(candidate, quote, record["context"]["screen"], now, e)
                    probability = model.score(features)
                    if probability < model.artifact.threshold:
                        reasons.append("MODEL_BELOW_THRESHOLD")
            except Exception:
                reasons.append("ML_CONTEXT_UNAVAILABLE")
        decision = RiskDecision(allowed=False, reasons=tuple(dict.fromkeys(reasons)))
        if not reasons and quote:
            decision = e._size_entry(tx, candidate, quote, now, quantity_limit=quantity_limit)
        return (
            candidate,
            features,
            decision,
            {
                "quote": quote.model_dump(mode="json") if quote else None,
                "model_score": probability,
                "model_version": model.version if model else None,
                "model_threshold": model.artifact.threshold if model else None,
            },
        )

    def preview(self, identity: str, now: datetime) -> dict[str, Any]:
        with self.engine.lock:
            if self.automation and self.automation.readiness(now):
                raise DeskError("AUTOMATION_NOT_READY: inspect intraday data and safeguards.")
            with self.engine.db.transaction() as tx:
                record = self._get(tx, identity)
                if record["state"] != "awaiting_approval":
                    raise DeskError(
                        "This proposal is no longer awaiting approval. Inspect its activity."
                    )
                candidate, features, decision, details = self._prepare(tx, record, now)
                review = decision.model_dump(mode="json")
                if decision.allowed and record["side"] == "BUY":
                    assert details["quote"] is not None
                    tick = self.engine._tick(tx, record["symbol"])
                    drift = self.research.profile.max_price_drift_bps if self.research else D(20)
                    reference = Quote.model_validate(record["reference_quote"])
                    max_ask = down(reference.ask * (1 + drift / 10000), tick)
                    cap = up(max_ask * (1 + self.engine.settings.slippage_bps / 10000), tick)
                    review.update(
                        maximum_quantity=decision.quantity,
                        maximum_price=str(cap),
                        maximum_cash=str(
                            cap * decision.quantity
                            + self.engine.charges.fee("BUY", cap * decision.quantity)
                        ),
                        maximum_risk=str(self.engine.settings.max_trade_risk),
                    )
                record["review"] = {**review, **details}
                record["preview_sha256"] = digest(
                    [self.revision, record["id"], record["review"], secrets.token_hex(16)]
                )
                self._save(tx, record, now)
                return record

    def approve(
        self, identity: str, preview_hash: str, now: datetime, *, automatic: bool = False
    ) -> dict[str, Any]:
        with self.engine.lock:
            with self.engine.db.transaction() as tx:
                existing = self._get(tx, identity)
                if existing["state"] in TERMINAL:
                    return existing
            if self.automation and self.automation.readiness(now):
                raise DeskError("AUTOMATION_NOT_READY: inspect intraday data and safeguards.")
            with self.engine.db.transaction() as tx:
                record = self._get(tx, identity)
                if record["state"] in TERMINAL:
                    return record  # Idempotent after a lost HTTP response; never replay an order.
                if record["mode"] == "automatic" and not automatic:
                    raise DeskError("Automatic proposals are handled by the running paper policy.")
                if record.get("preview_sha256") != preview_hash or not record.get("review", {}).get(
                    "allowed"
                ):
                    raise DeskError("Preview this proposal again before approving.")
                review = record["review"]
                candidate, features, decision, details = self._prepare(
                    tx, record, now, review.get("maximum_quantity")
                )
                if not decision.allowed:
                    raise DeskError("Approval blocked: " + ", ".join(decision.reasons))
                if record["side"] == "BUY" and (
                    decision.price_cap > D(review["maximum_price"])
                    or decision.cash_reservation > D(review["maximum_cash"])
                    or decision.risk_reservation > D(review["maximum_risk"])
                ):
                    raise DeskError("Trade exceeds your reviewed bounds. Preview again.")
                if record["side"] == "SELL":
                    self.engine._exit(tx, record["symbol"], now, record["context"]["reason"])
                    order = tx.execute(
                        f"SELECT id FROM orders WHERE {PENDING} AND side='SELL' AND symbol=?",
                        (record["symbol"],),
                    ).fetchone()
                    record.update(
                        state="submitted",
                        order_id=order[0],
                        outcome="EXIT_QUEUED",
                        authorized_by="automatic" if automatic else "operator",
                        execution=details,
                    )
                    self._save(tx, record, now)
                    return record
                assert candidate is not None
                record.update(
                    state="authorized",
                    authorized_by="automatic" if automatic else "operator",
                    execution=details,
                    prepared_candidate=candidate.model_dump(mode="json"),
                    prepared_features=features.model_dump(mode="json") if features else None,
                )
                self._save(tx, record, now)
            # The account lock spans authorization, independent broker risk and linkage.
            # A crash here expires unsubmitted authority; a committed order is recovered by its ID.
            observed = utc(self.clock()) if self.clock else utc(now)
            model = self.research.model if self.research else self.engine.model
            age_days = (
                self.research.profile.max_model_age_days
                if self.research
                else self.automation.settings.max_model_age_days
                if self.automation
                else 30
            )
            if (
                observed < now
                or (observed - now).total_seconds() > self.engine.settings.max_quote_age_seconds
                or observed > datetime.fromisoformat(record["expires_at"])
                or observed.astimezone(IST).date() != self.mode_day
                or model
                and observed - model.artifact.validated_through > timedelta(days=age_days)
            ):
                with self.engine.db.transaction() as tx:
                    record.update(
                        state="expired",
                        outcome="AUTHORIZATION_DELAY_OR_CLOCK_CHANGED",
                        execution_observed_at=stamp(observed),
                    )
                    self._save(tx, record, max(observed, now))
                return record
            order = self.engine.submit(
                candidate,
                observed,
                features=features if self.engine.model else None,
                automation=self.engine.automation,
                quantity_limit=review["maximum_quantity"],
                _decision_reference=record["id"],
            )
            with self.engine.db.transaction() as tx:
                record.update(
                    state="rejected" if order["state"] == "REJECTED" else "submitted",
                    order_id=order["id"],
                    outcome=order["reason"] or order["state"],
                )
                self._save(tx, record, observed)
            return record

    def reject(self, identity: str, now: datetime) -> dict[str, Any]:
        with self.engine.lock, self.engine.db.transaction() as tx:
            record = self._get(tx, identity)
            if record["state"] == "awaiting_approval":
                record.update(state="rejected", outcome="OPERATOR_DECLINED")
                self._save(tx, record, now)
            return record

    def view(self, now: datetime) -> dict[str, Any]:
        with self.engine.lock, self.engine.db.transaction() as tx:
            tokens = self.execution_tokens
            selected = (
                [
                    dict(r)
                    for r in tx.execute(
                        "SELECT symbol,token,tick FROM instruments WHERE token IN ("
                        + ",".join("?" for _ in tokens)
                        + ") ORDER BY symbol",
                        tokens,
                    )
                ]
                if tokens
                else []
            )
            shortlist = self.shortlist(tx)
            records = [
                json.loads(r[0])
                for r in tx.execute(
                    "SELECT payload FROM desk_decisions ORDER BY rowid DESC LIMIT 100"
                )
            ]
        # Snapshot opens another transaction; do not nest it in the view transaction.
        result = self.research.result if self.research else None
        return {
            "mode": self.mode,
            "revision": self.revision,
            "mode_reason": self.reason,
            "horizon": self.engine.settings.investment_horizon,
            "observed_at": stamp(now),
            "blockers": self.blockers(now),
            "selected": selected,
            "decisions": records,
            "decisions_limit": 100,
            "selection_basis": "reviewed_daily_screen" if result else "operator_watchlist",
            "profile_name": self.research.profile.name if self.research else None,
            "strategy_mode": self.research.profile.strategy_mode
            if self.research
            else "rules_ml"
            if self.engine.model
            else "rules"
            if self.automation
            else "unconfigured",
            "model_available": bool(self.research.model if self.research else self.engine.model),
            "bound_intraday_controller": self.automation is not None,
            "discovery": result,
            "shortlist": shortlist,
            "last_analysis": self.last_analysis,
            "account": self.engine.snapshot(now),
            "automatic_active": self.mode != "manual"
            and not self.blockers(now)
            and (self.automation.armed if self.automation else True),
        }

    def shortlist(self, tx: Any) -> dict[str, Any] | None:
        if not self.research:
            return None
        ranked = sorted(
            (r for r in self.research.result["rows"] if r["rank"]), key=lambda r: r["rank"]
        )
        catalog = {r[0]: r[1] for r in tx.execute("SELECT symbol,token FROM instruments")}
        matched = [r for r in ranked if r["symbol"] in catalog and catalog[r["symbol"]] & 255 == 1]
        matched_symbols = {r["symbol"] for r in matched}
        held = {r[0] for r in tx.execute("SELECT symbol FROM positions")}
        symbols = sorted(held)
        for row in matched:
            if (
                row["symbol"] in catalog
                and catalog[row["symbol"]] & 255 == 1
                and row["symbol"] not in symbols
                and len(symbols) < 10
            ):
                symbols.append(row["symbol"])
        plan = {
            "symbols": symbols,
            "held_symbols": sorted(held),
            "profile": self.identity,
            "revision": self.revision,
            "ranked_candidates": len(ranked),
            "catalog_candidates": len(matched),
            "unmatched": [r["symbol"] for r in ranked if r["symbol"] not in matched_symbols],
        }
        return {**plan, "preview_sha256": digest(plan)}
