"""Reviewable genuine-data acquisition, without mode changes or trading authority."""

import csv
import io
import json
import os
import re
import secrets
import threading
from copy import deepcopy
from datetime import datetime, time
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, model_validator

from trading_agent.api.setup import SetupError, private_write
from trading_agent.backtesting.dataset import Session
from trading_agent.daily_research.dataset import DailyBar, DailyManifest, Membership
from trading_agent.desk import sources
from trading_agent.desk.contracts import digest
from trading_agent.desk.research import Research
from trading_agent.market_data.calendar import IST, SessionCalendar
from trading_agent.models import DomainModel, Instrument, stamp


class DownloadRequest(DomainModel):
    universe: Literal["nifty100", "nifty500"]
    request_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    revision: str = Field(pattern=r"^[a-f0-9]{32}$")
    acknowledged: bool = Field(strict=True)

    @model_validator(mode="after")
    def review(self) -> "DownloadRequest":
        if not self.acknowledged:
            raise ValueError("Acknowledge the read-only download.")
        return self


class InstallRequest(DomainModel):
    preview_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    revision: str = Field(pattern=r"^[a-f0-9]{32}$")
    strategy_mode: Literal["rules", "rules_ml"]
    calendar_csv: str = Field(min_length=30, max_length=30000)
    reference: str = Field(min_length=3, max_length=300, pattern=r"^[^\r\n]+$")
    calendar_reviewed: bool = Field(strict=True)
    basis_reviewed: bool = Field(strict=True)
    policy_reviewed: bool = Field(strict=True)
    correct_unused_calendar: bool = Field(default=False, strict=True)

    @model_validator(mode="after")
    def reviewed(self) -> "InstallRequest":
        if not (self.calendar_reviewed and self.basis_reviewed and self.policy_reviewed):
            raise ValueError("Calendar, action/basis and strategy reviews are required.")
        if len(self.reference.strip()) < 3:
            raise ValueError("Enter a nonblank review reference.")
        return self


def storage(engine: Any) -> Path:
    return engine.settings.database.with_suffix(".analysis")


def bounded(path: Path, limit: int) -> str:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise SetupError("Preparation files are missing, changed or oversized. Download again.")
    with path.open(encoding="utf-8", newline="") as file:
        value = file.read(limit + 1)
    if len(value.encode()) > limit:
        raise SetupError("Preparation files exceed the read budget. Download again.")
    return value


def unused_calendar(tx: Any) -> bool:
    """A deliberately conservative correction gate; any account-use evidence prevents it."""
    tables = (
        "orders",
        "fills",
        "positions",
        "quotes",
        "candles",
        "corporate_batches",
        "corporate_payments",
        "portfolio_requests",
        "sip_plans",
        "desk_decisions",
    )
    return (
        not any(tx.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone() for table in tables)
        and not tx.execute("SELECT 1 FROM meta WHERE key GLOB 'lt_session:*' LIMIT 1").fetchone()
    )


def saved_profile(engine: Any) -> Path | None:
    """Only a server-owned immutable job path can be selected by the saved pointer."""
    root = storage(engine)
    pointer = root / "active.json"
    if not pointer.exists() and not pointer.is_symlink():
        return None
    if root.is_symlink() or pointer.is_symlink() or pointer.stat().st_size > 10000:
        raise SetupError("Invalid saved strategy selection; inspect local preparation files.")
    value = json.loads(bounded(pointer, 10000))
    identity = value["job_id"]
    if not isinstance(identity, str) or not re.fullmatch(r"[a-f0-9]{32}", identity):
        raise SetupError("Invalid saved strategy selection; inspect local preparation files.")
    path = root / identity / "profile.toml"
    if (
        path.parent.is_symlink()
        or path.is_symlink()
        or digest(bounded(path, 2_000_000)) != value["profile_sha256"]
    ):
        raise SetupError("Saved strategy inputs changed; inspect local preparation files.")
    from trading_agent.daily_research.dataset import DailyDataset

    if DailyDataset(path.parent / "daily").hashes != value.get("daily_sha256"):
        raise SetupError("Saved strategy data changed; download and review again.")
    return path


class Preparation:
    def __init__(self, desk: Any, setup: Any, clock: Any):
        self.desk, self.setup, self.clock = desk, setup, clock
        self.root = storage(desk.engine)
        self.lock = threading.RLock()
        self.stop = threading.Event()
        self.thread: threading.Thread | None = None
        self.state: dict[str, Any] | None = None
        self.model_path = os.environ.get("TRADING_PREPARATION_MODEL", "")
        self.profile_override = bool(os.environ.get("TRADING_ANALYSIS_PROFILE", ""))
        path = self.root / "latest.json"
        if path.exists():
            try:
                if self.root.is_symlink() or path.is_symlink() or path.stat().st_size > 2_000_000:
                    raise ValueError
                self.state = json.loads(bounded(path, 2_000_000))
                if not re.fullmatch(r"[a-f0-9]{32}", self.state["job_id"]):
                    raise ValueError
                if self.state["state"] == "downloading":
                    self.state.update(state="interrupted", error="DOWNLOAD_INTERRUPTED")
            except Exception:
                self.state = {"state": "failed", "error": "SAVED_PREPARATION_INVALID"}

    def _persist(self, **updates: Any) -> None:
        with self.lock:
            assert self.state is not None
            self.state.update(deepcopy(updates), updated_at=stamp(self.clock()))
            private_write(self.root / "latest.json", json.dumps(self.state, sort_keys=True) + "\n")

    def view(self) -> dict[str, Any]:
        with self.lock:
            job = deepcopy(self.state)
        if job and job.get("started_at"):
            end = (
                self.clock()
                if job["state"] == "downloading"
                else datetime.fromisoformat(job["updated_at"])
            )
            job["elapsed_seconds"] = max(
                0, (end - datetime.fromisoformat(job["started_at"])).total_seconds()
            )
        conflicts = []
        can_correct = False
        e = self.desk.engine
        if job and job.get("calendar_csv") and getattr(e, "calendar", None):
            with e.lock, e.db.transaction() as tx:
                for row in csv.DictReader(io.StringIO(job["calendar_csv"])):
                    day = datetime.fromisoformat(row["date"]).date()
                    old = e.calendar.sessions.get(day)
                    if old and (old[0].strftime("%H:%M"), old[1].strftime("%H:%M")) != (
                        row["open"],
                        row["close"],
                    ):
                        conflicts.append(
                            {
                                "date": row["date"],
                                "existing": old[0].strftime("%H:%M")
                                + "–"
                                + old[1].strftime("%H:%M"),
                                "proposed": row["open"] + "–" + row["close"],
                            }
                        )
                can_correct = bool(conflicts) and unused_calendar(tx)
        return {
            "available": self.setup is not None and self.desk.automation is None,
            "ml_configured": bool(self.model_path),
            "profile_override": self.profile_override,
            "calendar_conflicts": conflicts,
            "can_correct_unused_calendar": can_correct,
            "job": job,
            "sources": {
                "universe": "https://www.niftyindices.com/indices/equity/broad-based-indices/"
                + ("nifty-100" if job and job.get("universe") == "nifty100" else "nifty-500"),
                "calendar": sources.HOLIDAY_PAGE,
                "hours": sources.HOURS,
                "actions": sources.ACTION_PAGE,
                "history": "https://kite.trade/docs/connect/v3/historical/",
            },
        }

    def _manual(self, revision: str) -> None:
        if self.setup is None or self.desk.automation is not None:
            raise SetupError("Preparation requires the manual read-only broker setup service.")
        if self.desk.mode != "manual" or revision != self.desk.revision:
            raise SetupError("Choose Manual and refresh before preparing or installing a strategy.")
        self.setup._manual()

    def start(self, body: DownloadRequest) -> dict[str, Any]:
        with self.lock:
            if self.state and self.state.get("request_id") == body.request_id:
                if self.state.get("universe") != body.universe:
                    raise SetupError(
                        "Download request identity was reused with a different universe."
                    )
                return self.view()  # Lost HTTP responses cannot create a second download.
            with self.desk.engine.lock:
                self._manual(body.revision)
                with self.desk.engine.db.transaction() as tx:
                    catalog = {
                        r["symbol"]: Instrument(
                            symbol=r["symbol"], token=r["token"], tick_size=r["tick"]
                        )
                        for r in tx.execute("SELECT * FROM instruments")
                        if r["token"] & 255 == 1
                    }
            if not catalog:
                raise SetupError("Download the NSE catalog in Broker & data first.")
            if self.thread and self.thread.is_alive():
                raise SetupError("A download is already running. Wait or cancel it first.")
            assert self.setup is not None
            with self.setup.lock:
                if not self.setup.values["access_token"]:
                    raise SetupError("Verify a saved broker session in Broker & data first.")
                broker = (
                    self.setup.broker()
                )  # Freeze this run's read session outside account locks.
            if self.root.is_symlink():
                raise SetupError("Refusing a symbolic-link preparation directory.")
            identity = secrets.token_hex(16)
            directory = self.root / identity
            directory.mkdir(parents=True, mode=0o700)
            self.stop = threading.Event()
            self.state = {
                "job_id": identity,
                "request_id": body.request_id,
                "universe": body.universe,
                "state": "downloading",
                "stage": "official_sources",
                "completed": 0,
                "total": 0,
                "eligible": 0,
                "excluded": [],
                "error": None,
                "started_at": stamp(self.clock()),
            }
            self._persist()
            self.thread = threading.Thread(
                target=self._run,
                args=(directory, broker, catalog, body.universe),
                name="history-preparation",
                daemon=True,
            )
            self.thread.start()
            return self.view()

    def _run(
        self, directory: Path, broker: Any, catalog: dict[str, Instrument], universe: str
    ) -> None:
        try:
            self._download(directory, broker, catalog, universe)
        except sources.SourceUnavailable as error:
            self._persist(state="failed", error=str(error))
        except Exception:
            self._persist(state="failed", error="HISTORY_OR_PREPARATION_FAILED")

    def _download(
        self, directory: Path, broker: Any, catalog: dict[str, Instrument], universe: str
    ) -> None:
        now = self.clock()
        today = now.astimezone(IST).date()
        try:
            broker.get_profile()
        except Exception:
            raise sources.SourceUnavailable("BROKER_SESSION_UNAVAILABLE") from None
        raw_universe = sources.public_read(sources.UNIVERSES[universe])
        class_exclusions: list[dict[str, str]] = []
        members = sources.constituents(raw_universe, universe, exclusions=class_exclusions)
        raw_calendar = sources.public_read(sources.HOLIDAYS)
        sessions = sources.proposed_sessions(raw_calendar, today)
        completed = [s for s in sessions if datetime.combine(s.day, s.close, IST) <= now]
        completed = completed[-60:]
        first = completed[0].day
        sessions = [s for s in sessions if s.day >= first]
        raw_actions = sources.public_read(
            sources.ACTIONS,
            {
                "index": "equities",
                "from_date": first.strftime("%d-%m-%Y"),
                "to_date": today.strftime("%d-%m-%Y"),
            },
        )
        affected = sources.action_symbols(raw_actions, first, today)
        for name, raw in (
            ("constituents.csv", raw_universe),
            ("holidays.json", raw_calendar),
            ("actions.json", raw_actions),
        ):
            private_write(directory / name, raw.decode("utf-8"))
        import hashlib

        source_hashes = {
            name: hashlib.sha256((directory / name).read_bytes()).hexdigest()
            for name in ("constituents.csv", "holidays.json", "actions.json")
        }
        constituent_count = len(members) + len(class_exclusions)
        excluded, selected = list(class_exclusions), []
        for member in members:
            symbol = member["symbol"]
            reason = (
                "CORPORATE_ACTION_IN_HISTORY"
                if symbol in affected
                else "CATALOG_MATCH_MISSING"
                if symbol not in catalog
                else None
            )
            if reason:
                excluded.append({"symbol": symbol, "reason": reason})
            else:
                selected.append(member)
        self._persist(
            stage="daily_history",
            total=len(selected),
            excluded=excluded,
            source_hashes=source_hashes,
            constituent_rows=constituent_count,
            history_start=first.isoformat(),
            history_end=completed[-1].day.isoformat(),
            retrieved_at=stamp(self.clock()),
        )
        start = datetime.combine(first, time(0), IST)
        end = datetime.combine(completed[-1].day, time(15, 30), IST)
        records, eligible = [], []
        expected = {s.day.isoformat() for s in completed}
        for index, member in enumerate(selected):
            if self.stop.is_set():
                self._persist(state="cancelled", error=None)
                return
            if self.clock().astimezone(IST).date() != today:
                raise sources.SourceUnavailable("DOWNLOAD_DATE_CHANGED")
            symbol = member["symbol"]
            try:
                rows = broker.get_daily_history(catalog[symbol], start, end, self.clock())
                received = stamp(self.clock())
                for row in rows:
                    row["price_available_at"] = received
            except Exception:
                # Stop at first failure; don't turn an expired session into 500 failed requests.
                raise sources.SourceUnavailable("BROKER_DAILY_HISTORY_UNAVAILABLE") from None
            actual = {r["session"] for r in rows}
            if actual != expected:
                excluded.append({"symbol": symbol, "reason": "INCOMPLETE_DAILY_HISTORY"})
            else:
                records.extend(rows)
                eligible.append(member)
            self._persist(
                completed=index + 1,
                eligible=len(eligible),
                excluded=excluded,
                current_symbol=symbol,
            )
        if self.stop.is_set():
            self._persist(state="cancelled", error=None)
            return
        if self.clock().astimezone(IST).date() != today:
            raise sources.SourceUnavailable("DOWNLOAD_DATE_CHANGED")
        if not eligible:
            raise sources.SourceUnavailable("NO_ELIGIBLE_HISTORY")
        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\n")
        writer.writerow(("date", "open", "close"))
        for session in sessions:
            writer.writerow(
                (
                    session.day.isoformat(),
                    session.open.strftime("%H:%M"),
                    session.close.strftime("%H:%M"),
                )
            )
        draft = {
            "sessions": [s.model_dump(mode="json") for s in sessions],
            "eligible": eligible,
            "records": sorted(records, key=lambda r: (r["session"], r["symbol"])),
            "universe": universe,
            "known_at": stamp(self.clock()),
            "source_hashes": source_hashes,
        }
        private_write(directory / "draft.json", json.dumps(draft, sort_keys=True) + "\n")
        preview = digest(draft)
        self._persist(
            state="ready_for_review",
            stage="review",
            calendar_csv=output.getvalue(),
            preview_sha256=preview,
            symbols=[r["symbol"] for r in eligible],
            completed_sessions=len(completed),
            snapshot_at=draft["known_at"],
        )

    def cancel(self) -> dict[str, Any]:
        self.stop.set()
        with self.lock:
            if self.state and self.state.get("state") == "downloading":
                self._persist(cancel_requested=True)
        return self.view()

    def close(self) -> None:
        self.stop.set()
        if self.thread:
            self.thread.join(timeout=1)

    def install(self, body: InstallRequest) -> dict[str, Any]:
        with self.lock:
            # Keep the old strategy from gaining authority while a new policy is validated.
            if self.state and self.state.get("state") == "installed":
                return self._install(body)
            with self.desk.engine.lock:
                self._manual(body.revision)
                previous = self.desk.installing
                self.desk.installing = True
            try:
                return self._install(body)
            finally:
                with self.desk.engine.lock:
                    self.desk.installing = previous

    def _install(self, body: InstallRequest) -> dict[str, Any]:
        with self.lock:
            if self.profile_override:
                raise SetupError(
                    "A custom TRADING_ANALYSIS_PROFILE is set. Clear that override "
                    "and restart before switching to a UI-managed strategy."
                )
            state = self.state
            if not state or state.get("state") not in ("ready_for_review", "installed"):
                raise SetupError("Finish a genuine data download before reviewing a strategy.")
            # Bind retries to the entire submitted policy/calendar/review, not just its data hash.
            installation = digest(body.model_dump(mode="json", exclude={"revision"}))
            if state.get("state") == "installed":
                if state.get("installation_sha256") == installation:
                    return self.view()
                raise SetupError(
                    "This data run is already installed. Download a new immutable run to change it."
                )
            self._manual(body.revision)
            now = self.clock()
            if (
                datetime.fromisoformat(state["snapshot_at"]).astimezone(IST).date()
                != now.astimezone(IST).date()
            ):
                raise SetupError(
                    "The download is from another IST date. "
                    "Prepare fresh sources before installation."
                )
            directory = self.root / state["job_id"]
            if self.root.is_symlink() or directory.is_symlink():
                raise SetupError("Refusing symbolic-link preparation inputs.")
            draft = json.loads(bounded(directory / "draft.json", 50_000_000))
            if (
                digest(draft) != body.preview_sha256
                or body.preview_sha256 != state["preview_sha256"]
            ):
                raise SetupError("The source plan changed. Download and review again.")
            import hashlib

            if set(draft["source_hashes"]) != {"constituents.csv", "holidays.json", "actions.json"}:
                raise SetupError("Official source identity changed. Download and review again.")
            if any(
                hashlib.sha256(bounded(directory / name, 5_000_000).encode()).hexdigest() != value
                for name, value in draft["source_hashes"].items()
            ):
                raise SetupError("Official source evidence changed. Download and review again.")
            try:
                rows = list(csv.DictReader(io.StringIO(body.calendar_csv)))
                reference = body.reference.strip()
                sessions = [
                    Session.model_validate(
                        {
                            "day": row["date"],
                            "open": row["open"],
                            "close": row["close"],
                            "source": reference,
                        }
                    )
                    for row in rows
                ]
                days = [s.day for s in sessions]
                if days != sorted(set(days)) or not 51 <= len(days) <= 120:
                    raise ValueError
                if any(not time(9, 15) <= s.open < s.close <= time(15, 30) for s in sessions):
                    raise ValueError
                history_days = {
                    datetime.fromisoformat(r["session"]).date() for r in draft["records"]
                }
                if not history_days <= set(days):
                    raise ValueError  # Cannot erase evidence of an observed trading session.
                if set(days) - {datetime.fromisoformat(s["day"]).date() for s in draft["sessions"]}:
                    # Additional sessions require a new complete acquisition.
                    raise ValueError
            except Exception:
                raise SetupError(
                    "Review chronological date/open/close CSV. Keep every downloaded session; "
                    "supported hours are 09:15–15:30 IST."
                ) from None
            if body.strategy_mode == "rules_ml" and not self.model_path:
                raise SetupError(
                    "No validated model is installed. Configure TRADING_PREPARATION_MODEL "
                    "or explicitly choose the experimental rules policy."
                )
            with self.setup.lock, self.desk.engine.lock:
                self._manual(body.revision)
                if self.clock().astimezone(IST).date() != now.astimezone(IST).date():
                    raise SetupError("IST date changed during validation. Prepare fresh sources.")
                e = self.desk.engine
                if self.setup.stream:
                    raise SetupError(
                        "Disconnect market data before installing the reviewed strategy/calendar. "
                        "Holdings are retained; reconnect explicitly afterwards."
                    )
                with e.db.transaction() as tx:
                    if tx.execute(
                        "SELECT 1 FROM orders WHERE state IN ('ACCEPTED','PARTIAL')"
                    ).fetchone():
                        raise SetupError(
                            "Resolve pending paper orders before installing a new strategy."
                        )
                    conflicts = [
                        s
                        for s in sessions
                        if s.day in e.calendar.sessions
                        and e.calendar.sessions[s.day] != (s.open, s.close)
                    ]
                    if conflicts and not (body.correct_unused_calendar and unused_calendar(tx)):
                        raise SetupError(
                            "A proposed date conflicts with the saved account calendar. "
                            "Review the displayed differences; explicit correction is allowed only "
                            "for an unused account without quote, review or execution history."
                        )
            bundle = directory / "daily"
            bundle.mkdir(exist_ok=True, mode=0o700)
            manifest = DailyManifest(
                source="Kite day history + official NSE Indices constituent snapshot",
                notes="Prospective current constituents only. Not historical membership/ML "
                "validation. All symbols with any returned action in the full history interval "
                "were excluded. Operator reviewed source coverage/calendar/basis: " + reference,
                synthetic=False,
                universe_kind="prospective_snapshot",
                sessions=tuple(sessions),
                universe=tuple(
                    Membership(
                        symbol=m["symbol"],
                        effective_session=sessions[0].day,
                        included=True,
                        known_at=draft["known_at"],
                        reference=sources.UNIVERSES[draft["universe"]],
                    )
                    for m in draft["eligible"]
                ),
            )
            private_write(bundle / "manifest.json", manifest.model_dump_json(indent=2) + "\n")
            bars = []
            for row in draft["records"]:
                bar = DailyBar.model_validate(
                    {**row, "basis_reviewed_at": stamp(now), "basis_reference": reference}
                )
                bars.append(bar.model_dump_json())
            private_write(bundle / "daily.jsonl", "\n".join(bars) + "\n")
            lines = [
                "name = " + json.dumps("Reviewed " + draft["universe"] + " paper strategy"),
                "daily_dataset = " + json.dumps(str(bundle.resolve())),
                "strategy_mode = " + json.dumps(body.strategy_mode),
            ]
            if body.strategy_mode == "rules_ml":
                lines.append(
                    "model_directory = " + json.dumps(str(Path(self.model_path).resolve()))
                )
            for member in draft["eligible"]:
                lines.extend(
                    [
                        "[[shares]]",
                        "symbol = " + json.dumps(member["symbol"]),
                        'kind = "equity_share"',
                        "reviewed_at = " + json.dumps(stamp(now)),
                        "reference = "
                        + json.dumps(sources.UNIVERSES[draft["universe"]] + " / " + member["isin"]),
                    ]
                )
            path = directory / "profile.toml"
            private_write(path, "\n".join(lines) + "\n")
            try:
                # Data/model loading and broad screening never hold the quote/risk lock.
                research = Research(self.desk.engine, path, now)
            except Exception:
                raise SetupError(
                    "The data or selected model failed validation. No strategy was installed; "
                    "inspect coverage and matching model evidence."
                ) from None
            with self.setup.lock, self.desk.engine.lock:
                self._manual(body.revision)
                if self.setup.stream:
                    raise SetupError(
                        "Feed state changed during validation. Disconnect and review again."
                    )
                if self.clock().astimezone(IST).date() != now.astimezone(IST).date():
                    raise SetupError("IST date changed during validation. Prepare fresh sources.")
                e = self.desk.engine
                with e.db.transaction() as tx:
                    if tx.execute(
                        "SELECT 1 FROM orders WHERE state IN ('ACCEPTED','PARTIAL')"
                    ).fetchone():
                        raise SetupError(
                            "Orders changed during validation. "
                            "Resolve pending orders and review again."
                        )
                    correction_allowed = body.correct_unused_calendar and unused_calendar(tx)
                combined = dict(e.calendar.sessions)
                refs = dict(e.calendar.sources)
                for s in sessions:
                    if s.day in combined and combined[s.day] != (s.open, s.close):
                        if not correction_allowed:
                            raise SetupError(
                                "Account calendar changed or was used during validation. "
                                "Review again."
                            )
                        refs[s.day] = reference
                    combined[s.day] = (s.open, s.close)
                    refs.setdefault(s.day, reference)
                if any(not refs.get(day, "").strip() for day in combined):
                    raise SetupError(
                        "Existing calendar lacks source references. "
                        "Review it locally before installation."
                    )
                calendar_path = directory / "sessions.csv"
                output = io.StringIO()
                writer = csv.writer(output)
                writer.writerow(("date", "open", "close", "source"))
                for day, bounds in sorted(combined.items()):
                    writer.writerow(
                        (
                            day.isoformat(),
                            bounds[0].strftime("%H:%M"),
                            bounds[1].strftime("%H:%M"),
                            refs[day],
                        )
                    )
                private_write(calendar_path, output.getvalue())
                # Configuration first, pointer second. Any interrupted install remains Manual.
                self.setup._persist_config(calendar=str(calendar_path.resolve()))
                e.calendar = SessionCalendar(combined, refs)
                e.settings = e.settings.model_copy(update={"calendar": calendar_path.resolve()})
                self.desk.pause(self.clock(), "REVIEWED_STRATEGY_INSTALLED")
                private_write(
                    self.root / "active.json",
                    json.dumps(
                        {
                            "job_id": state["job_id"],
                            "profile_sha256": digest(path.read_text()),
                            "daily_sha256": research.dataset.hashes,
                        }
                    )
                    + "\n",
                )
                self.desk.research, self.desk.problem, self.desk.analysis_error = research, "", None
                self.desk.last_analysis = stamp(now)
                self._persist(
                    state="installed",
                    installation_sha256=installation,
                    strategy_mode=body.strategy_mode,
                    review_reference=reference,
                    calendar_csv=body.calendar_csv,
                    installed_at=stamp(self.clock()),
                    installed_revision=self.desk.revision,
                )
            return self.view()
