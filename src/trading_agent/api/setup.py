"""Authenticated manual-account setup. No order, arming or risk-override capability."""

import csv
import hashlib
import io
import json
import os
import re
import secrets
import tempfile
import threading
import time
import tomllib
from collections.abc import Callable
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import tomlkit

from trading_agent import __version__
from trading_agent.broker.readonly_kite import (
    QuoteStream,
    ReadOnlyKite,
    exchange_token,
    login_url,
)
from trading_agent.execution.paper_broker import PaperBroker
from trading_agent.market_data.calendar import IST, SessionCalendar
from trading_agent.market_data.candles import CandleBuilder
from trading_agent.market_data.repository import store_candles
from trading_agent.models import Instrument, Quote, stamp


class SetupError(ValueError):
    """Only deliberately written, credential-free messages may reach the UI."""


def private_write(path: Path, content: str) -> None:
    """Atomic replacement: secrets are private from creation, including failures."""
    if path.is_symlink():
        raise SetupError("Refusing a symbolic-link setup file.")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor, temporary = tempfile.mkstemp(prefix=".setup-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


class SetupService:
    uses_persisted_candles = True

    def __init__(
        self,
        engine: PaperBroker,
        config: Path,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ):
        self.engine, self.config, self.clock = engine, config, clock
        self.path = engine.settings.database.with_suffix(".kite.json")
        self.lock = threading.RLock()
        self.stream: QuoteStream | None = None
        self.started = False
        self.connection_observer: Callable[[bool], None] | None = None
        self.verified = False
        self.verified_at: datetime | None = None
        self.profile_revision = 0
        self.nonce: tuple[str, float] | None = None
        self.values = {
            "api_key": os.environ.get("KITE_API_KEY", ""),
            "api_secret": os.environ.get("KITE_API_SECRET", ""),
            "access_token": os.environ.get("KITE_ACCESS_TOKEN", ""),
        }
        if self.path.exists() or self.path.is_symlink():
            if self.path.is_symlink() or self.path.stat().st_mode & 0o077:
                raise SetupError("Broker setup file must be a private regular file.")
            try:
                saved = json.loads(self.path.read_text())
                if set(saved) != set(self.values) or any(
                    not isinstance(value, str) or len(value) > 256 for value in saved.values()
                ):
                    raise ValueError
                self.values = saved
            except Exception:
                raise SetupError(
                    "Stored broker setup is invalid; preserve it for local review."
                ) from None

    def _manual(self) -> None:
        if self.engine.automation or self.engine.model:
            raise SetupError(
                "Setup changes require a manual account; use the bound automation workflow."
            )

    def _save_values(self, values: dict[str, str]) -> None:
        private_write(self.path, json.dumps(values) + "\n")
        self.values = values

    def _persist_config(self, **updates: Any) -> None:
        # The path is server-selected, never supplied by a browser. Preserve comments.
        if self.config.is_symlink():
            raise SetupError("Refusing a symbolic-link account config.")
        if not updates or set(updates) - {
            "stream_tokens",
            "calendar",
            "stream_limit",
            "automatic_universe",
        }:
            raise SetupError("Setup can only change the reviewed calendar and feed selection.")
        try:
            document = tomlkit.parse(self.config.read_text())
        except tomlkit.exceptions.ParseError:
            raise SetupError(
                "Account config is invalid TOML; review it locally before retrying."
            ) from None
        for key, value in updates.items():
            document[key] = value
        text = tomlkit.dumps(document)
        from trading_agent.settings import Settings

        proposed = tomllib.loads(text)
        proposed["operator_token"] = self.engine.settings.operator_token
        validated = Settings.model_validate(proposed)
        from trading_agent.risk.policy import policy_fingerprint

        if policy_fingerprint(validated) != policy_fingerprint(self.engine.settings):
            raise SetupError(
                "Financial policy changed outside setup; restart with a reviewed config."
            )
        private_write(self.config, text)

    def status(self) -> dict[str, Any]:
        with self.lock, self.engine.lock, self.engine.db.transaction() as tx:
            tokens = self.engine.settings.stream_tokens
            selected = []
            if tokens:
                placeholders = ",".join("?" for _ in tokens)
                selected = [
                    dict(row)
                    for row in tx.execute(
                        f"SELECT symbol,token,tick FROM instruments "
                        f"WHERE token IN ({placeholders}) ORDER BY symbol",
                        tokens,
                    )
                ]
            day = self.clock().astimezone(IST).date()
            return {
                "ui_version": __version__,
                "account_id": hashlib.sha256(
                    str(self.engine.settings.database.resolve()).encode()
                ).hexdigest(),
                "manual": not bool(self.engine.automation or self.engine.model),
                "credentials_configured": bool(
                    self.values["api_key"] and self.values["api_secret"]
                ),
                "access_token_available": bool(self.values["access_token"]),
                "profile_verified_this_run": self.verified,
                "profile_checked_at": stamp(self.verified_at) if self.verified_at else None,
                "feed_connected": self.engine.connected,
                "stream_requested": self.stream is not None,
                "feed_diagnostics": self.stream.diagnostics() if self.stream else None,
                "catalog_count": tx.execute("SELECT count(*) FROM instruments").fetchone()[0],
                "stream_limit": self.engine.settings.stream_limit,
                "automatic_universe": self.engine.settings.automatic_universe,
                "selected": selected,
                "today": day.isoformat(),
                "sessions": [
                    {
                        "date": d.isoformat(),
                        "open": bounds[0].isoformat(timespec="minutes"),
                        "close": bounds[1].isoformat(timespec="minutes"),
                        "source": self.engine.calendar.sources.get(d, ""),
                    }
                    for d, bounds in sorted(self.engine.calendar.sessions.items())
                    if d >= day
                ][:31],
                "calendar_today": day in self.engine.calendar.sessions,
            }

    def save_credentials(self, body: dict[str, Any]) -> None:
        with self.lock:
            self._manual()
            if set(body) != {"api_key", "api_secret"} or any(
                not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,256}", value)
                for value in body.values()
            ):
                raise SetupError(
                    "Enter only a valid API key and API secret; values are not echoed."
                )
            if self.stream:
                raise SetupError("Disconnect the feed before replacing app credentials.")
            self._save_values({**body, "access_token": ""})
            self.verified = False
            self.verified_at = None
            self.profile_revision += 1
            self.nonce = None

    def begin_login(self) -> dict[str, str]:
        with self.lock:
            self._manual()
            if self.stream:
                raise SetupError("Disconnect the feed before starting a replacement broker login.")
            if not self.values["api_key"] or not self.values["api_secret"]:
                raise SetupError("Save your Kite API key and secret first.")
            state = secrets.token_urlsafe(32)
            self.nonce = (state, time.monotonic() + 300)
            return {
                "login_url": login_url(self.values["api_key"])
                + "&"
                + urlencode({"redirect_params": urlencode({"setup_state": state})}),
                "state": state,
            }

    def exchange(self, body: dict[str, Any]) -> None:
        with self.lock:
            self._manual()
            if set(body) != {"request_token", "state"} or any(
                not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,256}", value)
                for value in body.values()
            ):
                raise SetupError("Enter only the request_token value, not the whole redirect URL.")
            if (
                not self.nonce
                or time.monotonic() > self.nonce[1]
                or not secrets.compare_digest(self.nonce[0], body["state"])
            ):
                raise SetupError(
                    "Login attempt expired or was already used. Start a new Kite login."
                )
            if self.stream:
                raise SetupError("Disconnect the feed before replacing its session.")
            self.nonce = None  # Never replay an uncertain one-time exchange.
            try:
                token = exchange_token(
                    self.values["api_key"], self.values["api_secret"], body["request_token"]
                )
                if not isinstance(token, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,256}", token):
                    raise ValueError
                ReadOnlyKite(self.values["api_key"], token).get_profile()
            except Exception:
                raise SetupError(
                    "Kite token exchange/profile failed. Start a new manual login; "
                    "check your app and subscription."
                ) from None
            self._save_values({**self.values, "access_token": token})
            self.verified = True
            self.verified_at = self.clock()
            self.profile_revision += 1

    def broker(self) -> ReadOnlyKite:
        return ReadOnlyKite(self.values["api_key"], self.values["access_token"])

    def check_profile(self) -> None:
        with self.lock:
            self.profile_revision += 1
            try:
                self.broker().get_profile()
            except Exception:
                self.verified = False
                self.verified_at = None
                raise SetupError(
                    "Kite profile check failed. Complete a fresh login; profile success "
                    "alone does not verify data entitlement."
                ) from None
            self.verified = True
            self.verified_at = self.clock()

    def import_catalog(self) -> int:
        with self.lock:
            self._manual()
            if self.stream:
                raise SetupError("Disconnect the feed before refreshing the catalog.")
            try:
                catalog = self.broker().get_instruments()
                self.engine.register(catalog)
                with self.engine.lock, self.engine.db.transaction() as tx:
                    self.engine.db.set(tx, "nse_catalog_imported_at", stamp(self.clock()))
            except Exception:
                raise SetupError(
                    "Catalog import failed or a mapping changed. Preserve the account and "
                    "review the catalog; no mapping is silently replaced."
                ) from None
            return len(catalog)

    def select_symbols(self, body: dict[str, Any], *, automatic_nifty50: bool = False) -> None:
        with self.lock, self.engine.lock:
            self._manual()
            raw = body.get("symbols")
            limit = (
                max(50, len(raw) if isinstance(raw, list) else 0, self.engine.settings.stream_limit)
                if automatic_nifty50
                else self.engine.settings.stream_limit
            )
            if set(body) != {"symbols"} or not isinstance(raw, list) or not 1 <= len(raw) <= limit:
                raise SetupError(f"Select one to {limit} distinct catalog symbols.")
            if any(not isinstance(s, str) or len(s) > 34 for s in raw):
                raise SetupError("Use NSE symbols from the catalog.")
            symbols = [s if s.startswith("NSE:") else "NSE:" + s for s in raw]
            if len(set(symbols)) != len(symbols):
                raise SetupError("Duplicate symbols are not allowed.")
            if self.stream:
                raise SetupError("Disconnect the feed before changing its selection.")
            with self.engine.db.transaction() as tx:
                if tx.execute(
                    "SELECT 1 FROM orders WHERE state IN ('ACCEPTED','PARTIAL')"
                ).fetchone():
                    raise SetupError("Resolve pending orders before changing the feed selection.")
                held = {row[0] for row in tx.execute("SELECT symbol FROM positions")}
                if not held.issubset(symbols):
                    raise SetupError("The selection must include every currently held symbol.")
                tokens = []
                for symbol in symbols:
                    row = tx.execute(
                        "SELECT token FROM instruments WHERE symbol=?", (symbol,)
                    ).fetchone()
                    if row is None:
                        raise SetupError("A selected symbol is missing from the imported catalog.")
                    tokens.append(row[0])
            updates: dict[str, Any] = {"stream_tokens": tokens}
            if automatic_nifty50:
                updates.update(stream_limit=limit, automatic_universe="nifty50")
            else:
                updates["automatic_universe"] = "custom"
            self._persist_config(**updates)
            self.engine.settings = self.engine.settings.model_copy(
                update={**updates, "stream_tokens": tuple(tokens)}
            )

    def select_official_nifty50(self, guard: Callable[[], None]) -> dict[str, Any]:
        """Choose the whole official basket; clients never supply its stock names."""
        from trading_agent.desk import sources

        raw = sources.public_read(sources.UNIVERSES["nifty50"])
        exclusions: list[dict[str, str]] = []
        members = sources.constituents(raw, "nifty50", exclusions=exclusions)
        if exclusions:
            raise SetupError(
                "The official basket includes an unsupported constituent. "
                "Review source coverage before changing the universe."
            )
        with self.lock, self.engine.lock:
            guard()
            with self.engine.db.read_snapshot() as tx:
                catalog = {r[0]: r[1] for r in tx.execute("SELECT symbol,token FROM instruments")}
                held = {r[0] for r in tx.execute("SELECT symbol FROM positions")}
            missing = [
                m["symbol"]
                for m in members
                if m["symbol"] not in catalog or catalog[m["symbol"]] & 255 != 1
            ]
            if missing:
                raise SetupError(
                    "Official Nifty 50 members are missing from the NSE equity catalog. "
                    "Import the catalog before applying the basket."
                )
            symbols = sorted({m["symbol"] for m in members} | held)
            self.select_symbols({"symbols": symbols}, automatic_nifty50=True)
            source = self.path.with_suffix(".nifty50.csv")
            private_write(source, raw.decode("utf-8"))
            return {
                "universe": "nifty50",
                "members": len(members),
                "monitored": len(symbols),
                "held_symbols_retained": sorted(held),
                "source": sources.UNIVERSES["nifty50"],
                "source_sha256": hashlib.sha256(raw).hexdigest(),
                "selected_at": stamp(self.clock()),
            }

    def add_session(self, body: dict[str, Any]) -> None:
        with self.lock, self.engine.lock:
            self._manual()
            try:
                if (
                    set(body) != {"date", "open", "close", "source", "reviewed"}
                    or body["reviewed"] is not True
                ):
                    raise ValueError
                if any(not isinstance(body[k], str) for k in ("date", "open", "close", "source")):
                    raise ValueError
                day = date.fromisoformat(body["date"])
                reference = body["source"].strip()
                if (
                    day < self.clock().astimezone(IST).date()
                    or not 3 <= len(reference) <= 300
                    or any(c in reference for c in "\r\n")
                ):
                    raise ValueError
                from datetime import time as clock_time

                bounds = (
                    clock_time.fromisoformat(body["open"]),
                    clock_time.fromisoformat(body["close"]),
                )
                if not clock_time(9, 15) <= bounds[0] < bounds[1] <= clock_time(15, 30):
                    raise ValueError
                proposed = SessionCalendar(
                    {**self.engine.calendar.sessions, day: bounds},
                    {**self.engine.calendar.sources, day: reference},
                )
            except Exception:
                raise SetupError(
                    "Confirm a reviewed current/future NSE date, supported 09:15–15:30 "
                    "times and a source reference."
                ) from None
            old = self.engine.calendar.sessions.get(day)
            if old and (old != bounds or self.engine.calendar.sources.get(day) != reference):
                raise SetupError(
                    "Existing session definitions cannot be changed in setup; "
                    "preserve used account history."
                )
            if old:
                return  # An equivalent reviewed definition is an idempotent no-op.
            if any(not proposed.sources.get(d) for d in proposed.sessions):
                raise SetupError(
                    "Existing calendar lacks source references; review it locally first."
                )
            path = self.engine.settings.database.with_name(
                self.engine.settings.database.stem + ".sessions-" + secrets.token_hex(6) + ".csv"
            )
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow(("date", "open", "close", "source"))
            for d, (opened, closed) in sorted(proposed.sessions.items()):
                writer.writerow(
                    (
                        d.isoformat(),
                        opened.isoformat(timespec="minutes"),
                        closed.isoformat(timespec="minutes"),
                        proposed.sources.get(d, ""),
                    )
                )
            try:
                private_write(path, output.getvalue())
                self._persist_config(calendar=str(path))
            except Exception:
                raise SetupError(
                    "Calendar save failed. Existing configured session definitions "
                    "remain unchanged."
                ) from None
            self.engine.calendar = proposed
            self.engine.settings = self.engine.settings.model_copy(update={"calendar": path})

    def prepare_stream(self) -> None:
        with self.lock:
            self._manual()
            if self.stream:
                raise SetupError(
                    "A feed is already requested. Refresh its status or disconnect before retrying."
                )
            tokens = self.engine.settings.stream_tokens
            if not tokens:
                raise SetupError("Select at least one catalog symbol before connecting the feed.")
            with self.engine.lock, self.engine.db.transaction() as tx:
                catalog = [
                    Instrument(symbol=r["symbol"], token=r["token"], tick_size=r["tick"])
                    for r in tx.execute("SELECT * FROM instruments")
                    if r["token"] in tokens
                ]
                held = {r[0] for r in tx.execute("SELECT symbol FROM positions")}
            if len(catalog) != len(tokens) or not held.issubset({i.symbol for i in catalog}):
                raise SetupError("The selected catalog must include every held symbol.")
            self.check_profile()
            builders = (CandleBuilder(1), CandleBuilder(5))

            def ingest(quote: Quote) -> None:
                ingest_batch([quote])

            def ingest_batch(quotes: list[Quote]) -> None:
                with self.engine.lock:
                    # Include callback lock wait in quote freshness, never freeze an earlier clock.
                    now = self.clock()
                    try:
                        accepted = self.engine.ingest_batch(quotes, now, clock=self.clock)
                        candles = []
                        for quote, valid in zip(quotes, accepted, strict=True):
                            if not valid:
                                continue
                            for builder in builders:
                                candles.extend(builder.update(quote))
                        if candles:
                            store_candles(self.engine.db, candles, now)
                    except Exception:
                        self.engine.faulted = True
                        self.engine.set_connected(False)
                        raise

            def connected(value: bool) -> None:
                with self.engine.lock:
                    self.engine.set_connected(value)
                    if not value:
                        for builder in builders:
                            builder.active.clear()
                            builder.previous.clear()
                    if self.connection_observer:
                        self.connection_observer(value)

            def unusable(symbol: str) -> None:
                with self.engine.lock:
                    self.engine.invalidate_quote(symbol)
                    for builder in builders:
                        builder.active.pop(symbol, None)
                        builder.previous.pop(symbol, None)

            self.stream = QuoteStream(
                catalog,
                ingest,
                connected,
                self.clock,
                credentials=(self.values["api_key"], self.values["access_token"]),
                on_unusable=unusable,
                stream_limit=self.engine.settings.stream_limit,
                on_quotes=ingest_batch,
            )

    def connect(self) -> None:
        with self.lock:
            self.prepare_stream()
            if self.started:
                try:
                    assert self.stream is not None
                    self.stream.start()
                except Exception:
                    self.stream = None
                    self.engine.set_connected(False)
                    raise SetupError(
                        "Feed startup failed. Inspect status before retrying."
                    ) from None

    def disconnect(self) -> None:
        with self.lock:
            self._manual()
            if self.stream:
                self.stream.close()
                self.stream = None
            self.engine.set_connected(False)
            if self.connection_observer:
                self.connection_observer(False)

    def start(self) -> None:
        with self.lock:
            self.started = True
            if self.stream:
                self.stream.start()

    def close(self) -> None:
        self.disconnect()
        self.started = False


def mount_setup(
    app: Any, service: SetupService | None, authorized: Callable[..., Any], assets: Any = None
) -> None:
    from importlib.resources import files

    from fastapi import Depends, Request
    from fastapi.responses import HTMLResponse, JSONResponse
    from starlette.concurrency import run_in_threadpool

    assets = assets or files("trading_agent.api").joinpath("static")

    @app.exception_handler(SetupError)
    async def setup_error(request: Request, exc: SetupError) -> JSONResponse:
        return JSONResponse({"detail": str(exc)}, 409)

    @app.get("/setup", response_class=HTMLResponse)
    def page() -> str:
        return assets.joinpath("setup.html").read_text()

    @app.get("/setup.js")
    def javascript() -> HTMLResponse:
        return HTMLResponse(
            assets.joinpath("setup.js").read_text(), media_type="application/javascript"
        )

    @app.get("/kite-callback.js")
    def callback() -> HTMLResponse:
        return HTMLResponse(
            assets.joinpath("kite-callback.js").read_text(), media_type="application/javascript"
        )

    def available() -> SetupService:
        if service is None:
            raise SetupError("Broker setup is available on the CLI-started manual service only.")
        return service

    @app.get("/api/setup", dependencies=[Depends(authorized)])
    def status() -> dict[str, Any]:
        return available().status()

    @app.post("/api/setup/{operation}", dependencies=[Depends(authorized)])
    async def operate(operation: str, request: Request) -> dict[str, Any]:
        # Custom parsing prevents framework validation errors from echoing submitted secrets.
        current = available()
        # Canonical JSON for 3,000 maximum-length NSE symbols fits below 128 KiB.
        # Credential/session and all other mutations retain the original 8 KiB ceiling.
        request_limit = (
            max(8192, min(128 * 1024, 64 + current.engine.settings.stream_limit * 40))
            if operation == "symbols"
            else 8192
        )
        content = bytearray()
        async for part in request.stream():
            content.extend(part)
            if len(content) > request_limit:
                raise SetupError("Setup request is too large.")
        try:
            body = json.loads(content or b"{}")
            if not isinstance(body, dict):
                raise ValueError
        except Exception:
            raise SetupError("Invalid setup request; no submitted values are echoed.") from None

        def perform() -> dict[str, Any]:
            try:
                if operation == "credentials":
                    current.save_credentials(body)
                elif operation == "exchange":
                    current.exchange(body)
                elif operation == "symbols":
                    current.select_symbols(body)
                elif operation == "session":
                    current.add_session(body)
                else:
                    if body:
                        raise SetupError("This action accepts no additional fields.")
                    if operation == "login":
                        return current.begin_login()
                    if operation == "profile":
                        current.check_profile()
                    elif operation == "catalog":
                        current.import_catalog()
                    elif operation == "connect":
                        current.connect()
                    elif operation == "disconnect":
                        current.disconnect()
                    else:
                        raise SetupError("Unknown setup action.")
                return current.status()
            except SetupError:
                raise
            except Exception:
                raise SetupError(
                    "Setup action failed. Refresh status before retrying; "
                    "submitted secrets are withheld."
                ) from None

        return await run_in_threadpool(perform)
