"""One explicit, expiring review coordinates existing setup controls; never arms trading."""

import hashlib
import json
import secrets
import threading
from copy import deepcopy
from datetime import datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator

from trading_agent.api.setup import SetupError, private_write
from trading_agent.daily_execution.contracts import DailyStrategy
from trading_agent.daily_research.analysis import DailyPolicy, Window
from trading_agent.daily_research.dataset import DailyBar
from trading_agent.desk.contracts import digest
from trading_agent.desk.preparation import InstallRequest, bounded, saved_profile
from trading_agent.execution.delivery import HoldingReview
from trading_agent.market_data.calendar import IST
from trading_agent.models import DomainModel, stamp
from trading_agent.risk.policy import policy_fingerprint
from trading_agent.strategy.rules import StrategySettings


class GuidedPreview(DomainModel):
    revision: str = Field(pattern=r"^[a-f0-9]{32}$")
    strategy_mode: Literal["rules", "rules_ml"]


class GuidedConfirm(DomainModel):
    preview_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    acknowledged: bool = Field(strict=True)

    @model_validator(mode="after")
    def review(self) -> "GuidedConfirm":
        if not self.acknowledged:
            raise ValueError("Review and acknowledge the complete setup summary.")
        return self


class GuidedSetup:
    def __init__(self, preparation: Any):
        self.prep = preparation
        self.desk, self.setup, self.clock = preparation.desk, preparation.setup, preparation.clock
        self.path = preparation.root / "guided.json"
        self.lock = threading.RLock()
        self.state: dict[str, Any] | None = None
        if self.path.exists():
            try:
                self.state = json.loads(bounded(self.path, 100000))
                if self.state["state"] in ("applying", "review"):
                    self.state.update(state="interrupted", message="Review again after restart.")
            except Exception:
                self.state = {
                    "state": "interrupted",
                    "message": "Saved setup is invalid. Review again.",
                }

    def view(self) -> dict[str, Any] | None:
        # Status reads need not wait for model/disk/broker work. Never expose the private binding.
        value = deepcopy(self.state)
        if value:
            value.pop("binding", None)
        return value

    def _save(self, **updates: Any) -> None:
        self.state = {**(self.state or {}), **updates}
        private_write(self.path, json.dumps(self.state, sort_keys=True) + "\n")

    def _draft(self) -> dict[str, Any]:
        p, now = self.prep, self.clock()
        job = p.state
        if not job or job.get("state") not in ("ready_for_review", "installed"):
            raise SetupError("Finish downloading strategy data first.")
        if (
            datetime.fromisoformat(job["snapshot_at"]).astimezone(IST).date()
            != now.astimezone(IST).date()
        ):
            raise SetupError("Download fresh sources for today before using guided setup.")
        directory = p.root / job["job_id"]
        if p.root.is_symlink() or directory.is_symlink():
            raise SetupError("Preparation inputs changed. Download again.")
        draft = json.loads(bounded(directory / "draft.json", 50_000_000))
        if digest(draft) != job["preview_sha256"] or set(draft["source_hashes"]) != {
            "constituents.csv",
            "holidays.json",
            "actions.json",
        }:
            raise SetupError("Preparation inputs changed. Download again.")
        for name, expected in draft["source_hashes"].items():
            if (
                hashlib.sha256(bounded(directory / name, 5_000_000).encode()).hexdigest()
                != expected
            ):
                raise SetupError("Official source evidence changed. Download again.")
        return draft

    def _model(self, mode: str) -> None:
        if mode != "rules_ml":
            return
        if not self.prep.model_path:
            raise SetupError(
                "No validated ML model is configured. Choose Rules only explicitly "
                "or install a matching model."
            )
        from trading_agent.daily_execution.model import load_daily_model
        from trading_agent.ml.inference import load_model

        e = self.desk.engine
        try:
            if e.long_term:
                load_daily_model(
                    Path(self.prep.model_path), strategy=DailyStrategy(), policy=e.settings
                )
            else:
                load_model(
                    Path(self.prep.model_path),
                    strategy_sha256=StrategySettings().digest(),
                    policy_sha256=policy_fingerprint(e.settings),
                    charges_version=e.charges.version,
                )
        except Exception:
            raise SetupError(
                "The selected ML model failed validation. Nothing was disconnected or installed."
            ) from None

    def _plan(self, body: GuidedPreview) -> tuple[dict[str, Any], str]:
        p, e, now = self.prep, self.desk.engine, self.clock()
        p._manual(body.revision)
        if p.profile_override:
            raise SetupError("Clear TRADING_ANALYSIS_PROFILE and restart before guided setup.")
        draft = self._draft()
        if p.state["state"] == "installed":
            if p.state["strategy_mode"] != body.strategy_mode or not self.desk.research:
                raise SetupError("Download a new data run to change the installed policy.")
            if saved_profile(e) != p.root / p.state["job_id"] / "profile.toml":
                raise SetupError("Installed strategy changed. Download and review again.")
        self._model(body.strategy_mode)
        # Pure analytical preview: no source/basis review assertion or profile is persisted.
        sessions = [
            s
            for s in draft["sessions"]
            if datetime.combine(
                datetime.fromisoformat(s["day"]).date(), time.fromisoformat(s["close"]), IST
            )
            <= now
        ]
        latest = max((s["day"] for s in sessions), default=None)
        bars = [DailyBar.model_validate(row) for row in draft["records"]]
        if not bars or max(b.session.isoformat() for b in bars) != latest:
            raise SetupError("A newly completed session needs fresh history. Download again.")
        windows: dict[str, Window] = {}
        for bar in sorted(bars, key=lambda b: (b.symbol, b.session)):
            if bar.available_at > now:
                raise SetupError("History is not yet available. Download again.")
            windows.setdefault(bar.symbol, Window(DailyPolicy())).add(bar, 0)
        ranked = sorted(
            (
                symbol
                for symbol, window in windows.items()
                if window.metrics()["status"] == "research_candidate"
            ),
            key=lambda symbol: (
                -Decimal(windows[symbol].metrics()["gross_total_return_pct"]),
                symbol,
            ),
        )
        view = p.view()
        conflicts = view["calendar_conflicts"]
        if conflicts and not view["can_correct_unused_calendar"]:
            raise SetupError(
                "Saved hours have already been used. Review the calendar in Advanced; "
                "guided setup cannot overwrite history."
            )
        with e.lock, e.db.transaction() as tx:
            p._manual(body.revision)
            if e.faulted or e.db.get(tx, "kill") == "true":
                raise SetupError("Resolve the account fault or kill switch before guided setup.")
            if tx.execute("SELECT 1 FROM orders WHERE state IN ('ACCEPTED','PARTIAL')").fetchone():
                raise SetupError(
                    "Resolve pending paper orders first. Guided setup cannot cancel them."
                )
            positions = [dict(r) for r in tx.execute("SELECT * FROM positions ORDER BY symbol")]
            held = sorted(r["symbol"] for r in positions)
            eligible = {m["symbol"] for m in draft["eligible"]}
            if not set(held) <= eligible:
                raise SetupError(
                    "Held symbols lack this run’s supported source coverage. Use Advanced review; "
                    "holdings will be preserved."
                )
            catalog = [dict(r) for r in tx.execute("SELECT * FROM instruments ORDER BY symbol")]
            tokens = {r["symbol"]: r["token"] for r in catalog}
            matched = [s for s in ranked if s in tokens and tokens[s] & 255 == 1]
            if draft["universe"] == "nifty50":
                matched = [
                    m["symbol"]
                    for m in draft.get("members", draft["eligible"])
                    if m["symbol"] in tokens and tokens[m["symbol"]] & 255 == 1
                ]
                if len(matched) != len(draft.get("members", draft["eligible"])):
                    raise SetupError(
                        "A Nifty 50 constituent is missing from the equity catalog. "
                        "Import the catalog before applying the automatic basket."
                    )
                symbols = held + [s for s in matched if s not in held]
            else:
                symbols = (
                    held
                    + [s for s in matched if s not in held][
                        : max(0, e.settings.stream_limit - len(held))
                    ]
                )
            if not matched or not symbols:
                raise SetupError(
                    "No stocks pass the reviewed screening rules. Nothing was changed; "
                    "do not force a trade."
                )
            reviews, manual = [], []
            for symbol in symbols:
                if (
                    symbol not in eligible
                    or not e.long_term
                    or e.long_term.reviewed(tx, symbol, now)
                ):
                    continue
                q = e._quote(tx, symbol)
                quarantined = tx.execute(
                    "SELECT 1 FROM meta WHERE key=?", ("lt_quarantine:" + symbol,)
                ).fetchone()
                if (
                    symbol in held
                    or quarantined
                    or q
                    and q.exchange_time.astimezone(IST).date().isoformat()
                    < p.state["history_start"]
                ):
                    manual.append(symbol)
                elif e.calendar.bounds(now) or any(
                    s["day"] == now.astimezone(IST).date().isoformat() for s in draft["sessions"]
                ):
                    reviews.append(symbol)
                else:
                    manual.append(symbol)
            binding = digest(
                {
                    "job": p.state["preview_sha256"],
                    "installed": p.state.get("installation_sha256"),
                    "revision": self.desk.revision,
                    "policy": policy_fingerprint(e.settings),
                    "selection": e.settings.stream_tokens,
                    "positions": positions,
                    "catalog": catalog,
                    "cash": e.db.get(tx, "cash"),
                    "orders": [
                        dict(r) for r in tx.execute("SELECT id,state FROM orders ORDER BY id")
                    ],
                    "reviews": [
                        tuple(r)
                        for r in tx.execute(
                            "SELECT key,value FROM meta WHERE key GLOB 'lt_review:*' "
                            "OR key GLOB 'lt_quarantine:*' OR key GLOB 'lt_session:*' ORDER BY key"
                        )
                    ],
                    "calendar": sorted(
                        (str(k), str(v), e.calendar.sources.get(k))
                        for k, v in e.calendar.sessions.items()
                    ),
                    "broker": digest(self.setup.values),
                }
            )
            plan = {
                "job_id": p.state["job_id"],
                "universe": draft["universe"],
                "strategy_mode": body.strategy_mode,
                "symbols": symbols,
                "held_symbols": held,
                "basis_reviews": reviews,
                "manual_basis_reviews": manual,
                "calendar_conflicts": conflicts,
                "calendar_csv": p.state["calendar_csv"],
                "sources": view["sources"],
                "eligible": len(eligible),
                "completed_sessions": p.state["completed_sessions"],
                "history_start": p.state["history_start"],
                "history_end": p.state["history_end"],
                "session_date": now.astimezone(IST).date().isoformat(),
                "cash": e.db.get(tx, "cash"),
                "horizon": e.settings.investment_horizon,
                "entry_start": str(e.settings.entry_start),
                "entry_end": str(e.settings.entry_end),
                "stays_manual": True,
            }
        return plan, binding

    def preview(self, body: GuidedPreview) -> dict[str, Any]:
        with self.lock, self.prep.lock, self.setup.lock if self.setup else self.lock:
            if self.state and self.state["state"] == "applying":
                raise SetupError("Setup is still applying. Refresh status before retrying.")
            plan, binding = self._plan(body)
            value = {
                "plan": plan,
                "binding": binding,
                "revision": body.revision,
                "expires_at": stamp(self.clock() + timedelta(seconds=120)),
                "nonce": secrets.token_hex(16),
            }
            self.state = {**value, "preview_sha256": digest(value), "state": "review"}
            self._save()
            return self.view() or {}

    def confirm(self, body: GuidedConfirm) -> dict[str, Any]:
        with self.lock, self.prep.lock, self.setup.lock if self.setup else self.lock:
            state = self.state
            if not state or state.get("preview_sha256") != body.preview_sha256:
                raise SetupError("Setup preview changed. Review again.")
            if state["state"] == "complete":
                return self.view() or {}  # A lost response cannot reconnect/review twice.
            if state["state"] != "review":
                raise SetupError(
                    "This attempt already stopped or was interrupted. Refresh and review again."
                )
            if self.clock() >= datetime.fromisoformat(state["expires_at"]):
                raise SetupError("Setup review expired. Review again; no action was taken.")
            plan, binding = self._plan(
                GuidedPreview(
                    revision=state["revision"], strategy_mode=state["plan"]["strategy_mode"]
                )
            )
            if binding != state["binding"] or plan != state["plan"]:
                raise SetupError(
                    "Account, sources or shortlist changed. Review again; no action was taken."
                )
            e, p = self.desk.engine, self.prep
            with e.lock:
                p._manual(state["revision"])
                self.desk.installing = True
            try:
                self._save(
                    state="applying",
                    phase="Disconnecting market data",
                    message="Applying confirmed setup; trading stays Manual.",
                )
                self.setup.disconnect()  # No engine lock while joining the streaming worker.
                checked, current = self._plan(
                    GuidedPreview(revision=state["revision"], strategy_mode=plan["strategy_mode"])
                )
                if current != binding or checked != plan:
                    raise SetupError("Account changed while disconnecting. Review again.")
                reference = "Guided source/calendar/policy review " + body.preview_sha256
                if p.state["state"] != "installed":
                    self._save(phase="Installing strategy and reviewed calendar")
                    p.install(
                        InstallRequest(
                            preview_sha256=p.state["preview_sha256"],
                            revision=state["revision"],
                            strategy_mode=plan["strategy_mode"],
                            calendar_csv=plan["calendar_csv"],
                            reference=reference,
                            calendar_reviewed=True,
                            basis_reviewed=True,
                            policy_reviewed=True,
                            correct_unused_calendar=bool(plan["calendar_conflicts"]),
                        )
                    )
                    revision = p.state["installed_revision"]
                else:
                    revision = state["revision"]
                self._save(phase="Applying ranked execution shortlist")
                with e.lock, e.db.transaction() as tx:
                    p._manual(revision)
                    actual = self.desk.shortlist(tx)
                    if not actual or actual["symbols"] != plan["symbols"]:
                        raise SetupError(
                            "The installed shortlist differs. Review again before selecting stocks."
                        )
                self.setup.select_symbols(
                    {"symbols": plan["symbols"]},
                    automatic_nifty50=plan.get("universe") == "nifty50",
                )
                self._save(phase="Saving today’s explicitly confirmed price-basis reviews")
                with e.lock:
                    p._manual(revision)
                    if self.clock().astimezone(IST).date().isoformat() != plan["session_date"]:
                        raise SetupError("IST date changed. Review today’s basis again.")
                    for symbol in plan["basis_reviews"]:
                        with e.db.transaction() as tx:
                            q = e._quote(tx, symbol)
                            if (
                                tx.execute(
                                    "SELECT 1 FROM positions WHERE symbol=?", (symbol,)
                                ).fetchone()
                                or tx.execute(
                                    "SELECT 1 FROM meta WHERE key=?", ("lt_quarantine:" + symbol,)
                                ).fetchone()
                                or q
                                and q.exchange_time.astimezone(IST).date().isoformat()
                                < plan["history_start"]
                            ):
                                raise SetupError(
                                    "Price-basis eligibility changed. Review the affected "
                                    "symbol in Advanced controls."
                                )
                        e.review_holding(
                            HoldingReview(
                                symbol=symbol,
                                session_date=plan["session_date"],
                                no_corporate_action=True,
                                reference=reference,
                            ),
                            self.clock(),
                        )
                self._save(phase="Requesting market-data connection")
                with e.lock:
                    p._manual(revision)
                self.setup.connect()
                self._save(
                    state="complete",
                    phase="Setup complete",
                    message="Strategy and shortlist are ready; feed connection requested. Manual "
                    "stays selected. Wait for an open entry session and fresh usable quotes, "
                    "resolve any remaining reviews, then choose Approval or Automatic.",
                )
            except Exception as error:
                reason = (
                    str(error)
                    if isinstance(error, SetupError)
                    else "Validation or persistence failed. Inspect local setup files."
                )
                self._save(
                    state="stopped",
                    message="Setup stopped during: "
                    + (self.state or {}).get("phase", "saving confirmation")
                    + ". "
                    + reason
                    + " Earlier saved steps remain. Refresh readiness and review again; "
                    "no trading mode or automatic retry was activated.",
                )
                raise SetupError((self.state or {})["message"]) from None
            finally:
                with e.lock:
                    self.desk.installing = False
            return self.view() or {}
