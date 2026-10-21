"""Allowlisted official Kite HTTP/WebSocket protocols without an order-capable SDK.

The official SDK's pinned vulnerable transport is intentionally not installed.
See docs/threat-model.md and docs/implementation-plan.md for the audited deviation.
"""

import csv
import hashlib
import io
import json
import os
import struct
import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any, Literal, Protocol, cast
from urllib.parse import urlencode

from trading_agent.market_data.calendar import IST
from trading_agent.models import Candle, Instrument, Quote, utc


class BrokerUnavailable(RuntimeError):
    pass


class BrokerReadOnly(Protocol):
    def get_profile(self) -> dict[str, Any]: ...
    def get_instruments(self) -> list[Instrument]: ...
    def get_historical_candles(
        self, instrument: Instrument, start: datetime, end: datetime, minutes: int, as_of: datetime
    ) -> list[Candle]: ...


class RestrictedKiteHTTP:
    """Only named reads and the manual session-token exchange can reach the network."""

    def __init__(self, api_key: str, access_token: str = ""):
        self.api_key, self.access_token = api_key, access_token

    def _request(
        self,
        route: str,
        method: str,
        *,
        params: dict[str, Any] | None = None,
        token: int = 0,
        interval: str = "",
    ) -> Any:
        import httpx

        paths = {
            ("user.profile", "GET"): "/user/profile",
            ("market.instruments", "GET"): "/instruments/NSE",
            ("api.token", "POST"): "/session/token",
        }
        path = paths.get((route, method))
        if (
            (route, method) == ("market.historical", "GET")
            and token > 0
            and interval in ("minute", "5minute")
        ):
            path = f"/instruments/historical/{int(token)}/{interval}"
        if path is None:
            raise BrokerUnavailable("operation outside read-only route allowlist")
        if route != "api.token" and not self.access_token:
            raise BrokerUnavailable("missing authenticated read session")
        headers = {"X-Kite-Version": "3"}
        if self.access_token:
            headers["Authorization"] = f"token {self.api_key}:{self.access_token}"
        try:
            with httpx.Client(timeout=10, follow_redirects=False, trust_env=False) as client:
                response = client.request(
                    method,
                    "https://api.kite.trade" + path,
                    headers=headers,
                    params=params if method == "GET" else None,
                    data=params if method == "POST" else None,
                )
                response.raise_for_status()
                if len(response.content) > 20_000_000:
                    raise BrokerUnavailable("oversized broker response")
                if route == "market.instruments":
                    return response.text
                payload = response.json()
                if payload.get("status") != "success":
                    raise BrokerUnavailable("unsuccessful broker response")
                return payload["data"]
        except Exception:
            raise BrokerUnavailable(
                "broker request unavailable; check session and entitlement"
            ) from None

    def profile(self) -> Any:
        return self._request("user.profile", "GET")

    def instruments(self, exchange: str) -> list[dict[str, Any]]:
        if exchange != "NSE":
            raise BrokerUnavailable("only NSE cash catalog supported")
        rows = csv.DictReader(io.StringIO(self._request("market.instruments", "GET")))
        return [
            {
                **row,
                "instrument_token": int(row["instrument_token"]),
                "lot_size": int(row["lot_size"]),
            }
            for row in rows
        ]

    def historical_data(
        self,
        token: int,
        start: datetime,
        end: datetime,
        interval: str,
        *,
        continuous: bool,
        oi: bool,
    ) -> list[dict[str, Any]]:
        if continuous or oi:
            raise BrokerUnavailable("derivative data unsupported")
        data = self._request(
            "market.historical",
            "GET",
            token=token,
            interval=interval,
            params={
                "from": start.strftime("%Y-%m-%d %H:%M:%S"),
                "to": end.strftime("%Y-%m-%d %H:%M:%S"),
                "continuous": 0,
                "oi": 0,
            },
        )
        return [
            dict(
                zip(
                    ("date", "open", "high", "low", "close", "volume"),
                    [datetime.fromisoformat(row[0]), *row[1:]],
                    strict=True,
                )
            )
            for row in data["candles"]
        ]

    def login_url(self) -> str:
        return "https://kite.zerodha.com/connect/login?" + urlencode(
            {"v": 3, "api_key": self.api_key}
        )

    def generate_session(self, request_token: str, *, api_secret: str) -> Any:
        checksum = hashlib.sha256((self.api_key + request_token + api_secret).encode()).hexdigest()
        return self._request(
            "api.token",
            "POST",
            params={"api_key": self.api_key, "request_token": request_token, "checksum": checksum},
        )


def make_client(api_key: str, access_token: str = "") -> RestrictedKiteHTTP:
    return RestrictedKiteHTTP(api_key, access_token)


class ReadOnlyKite:
    def __init__(self, api_key: str, access_token: str):
        if not api_key or not access_token:
            raise BrokerUnavailable("missing broker session; complete manual login")
        self._client = make_client(api_key, access_token)

    @classmethod
    def from_environment(cls) -> "ReadOnlyKite":
        return cls(os.environ.get("KITE_API_KEY", ""), os.environ.get("KITE_ACCESS_TOKEN", ""))

    def get_profile(self) -> dict[str, Any]:
        try:
            result = self._client.profile()
            return {"authenticated": True, "broker": str(result["broker"])}
        except Exception:
            raise BrokerUnavailable("broker session unavailable; reauthenticate manually") from None

    def get_instruments(self) -> list[Instrument]:
        try:
            rows = self._client.instruments("NSE")
            return [
                Instrument(
                    symbol="NSE:" + row["tradingsymbol"],
                    token=row["instrument_token"],
                    tick_size=Decimal(str(row["tick_size"])),
                )
                for row in rows
                if row["exchange"] == "NSE"
                and row["segment"] == "NSE"
                and row["instrument_type"] == "EQ"
                and row["lot_size"] == 1
            ]
        except Exception:
            raise BrokerUnavailable("instrument catalog unavailable or invalid") from None

    def get_historical_candles(
        self, instrument: Instrument, start: datetime, end: datetime, minutes: int, as_of: datetime
    ) -> list[Candle]:
        start, end, as_of = utc(start), utc(end), utc(as_of)
        if minutes not in (1, 5) or not start < end <= as_of or end - start > timedelta(days=30):
            raise ValueError("use 1m/5m intervals with past ranges of at most 30 days")
        try:
            rows = self._client.historical_data(
                instrument.token,
                start.astimezone(IST),
                end.astimezone(IST),
                "minute" if minutes == 1 else "5minute",
                continuous=False,
                oi=False,
            )
            candles = [
                Candle(
                    symbol=instrument.symbol,
                    start=row["date"],
                    minutes=cast(Literal[1, 5], minutes),
                    open=Decimal(str(row["open"])),
                    high=Decimal(str(row["high"])),
                    low=Decimal(str(row["low"])),
                    close=Decimal(str(row["close"])),
                    volume=row["volume"],
                )
                for row in rows
            ]
        except Exception:
            raise BrokerUnavailable(
                "historical data unavailable, unentitled or malformed"
            ) from None
        complete = [
            c
            for c in candles
            if start <= c.start <= end and c.start + timedelta(minutes=minutes) <= as_of
        ]
        if len({c.start for c in complete}) != len(complete):
            raise BrokerUnavailable("duplicate historical candles")
        ordered = sorted(complete, key=lambda c: c.start)
        for index in range(1, len(ordered)):
            if ordered[index].start - ordered[index - 1].start != timedelta(minutes=minutes):
                ordered[index] = ordered[index].model_copy(update={"quality": "gap"})
        return ordered


def login_url(api_key: str) -> str:
    if not api_key:
        raise BrokerUnavailable("KITE_API_KEY is required")
    return make_client(api_key).login_url()


def exchange_token(api_key: str, api_secret: str, request_token: str) -> str:
    if not all((api_key, api_secret, request_token)):
        raise BrokerUnavailable("manual login credentials are incomplete")
    try:
        session = make_client(api_key).generate_session(request_token, api_secret=api_secret)
        return str(session["access_token"])
    except Exception:
        raise BrokerUnavailable("token exchange failed; repeat supported manual login") from None


def _parse_binary(
    message: bytes, instruments: dict[int, Instrument], received: datetime
) -> tuple[list[Quote], list[str]]:
    """Strict full packets; empty-sided books are observations, not executable quotes.

    Skip those books without inventing depth or disconnecting a healthy transport.
    Framing, instrument identity and all remaining Quote validation stay strict.
    """
    if len(message) == 1:  # documented heartbeat
        return [], []
    if len(message) < 2:
        raise ValueError("truncated quote header")
    count = struct.unpack_from(">H", message, 0)[0]
    offset, result = 2, []
    unusable = []
    if count > 10:
        raise ValueError("unexpected packet count")
    for _ in range(count):
        if offset + 2 > len(message):
            raise ValueError("truncated packet length")
        length = struct.unpack_from(">H", message, offset)[0]
        offset += 2
        if length != 184 or offset + length > len(message):
            raise ValueError("full-mode 184-byte equity quote required")
        packet = message[offset : offset + length]
        offset += length

        def integer(start: int, data: bytes = packet) -> int:
            return int(struct.unpack_from(">I", data, start)[0])

        token = integer(0)
        if token not in instruments or token & 255 != 1:
            raise ValueError("unknown or non-NSE equity token")
        item = instruments[token]
        if any(integer(start) == 0 for start in (64, 68, 124, 128)):
            unusable.append(item.symbol)
            continue
        result.append(
            Quote(
                symbol=item.symbol,
                token=token,
                exchange_time=datetime.fromtimestamp(integer(60), UTC),
                received_time=received,
                last=Decimal(integer(4)) / 100,
                volume=integer(16),
                bid=Decimal(integer(68)) / 100,
                bid_size=integer(64),
                ask=Decimal(integer(128)) / 100,
                ask_size=integer(124),
                source="kite",
            )
        )
    if offset != len(message):
        raise ValueError("unexpected trailing quote bytes")
    # A conflicting batch cannot restore freshness for an empty-sided symbol.
    return [quote for quote in result if quote.symbol not in unusable], unusable


def parse_binary(
    message: bytes, instruments: dict[int, Instrument], received: datetime
) -> list[Quote]:
    """Return only executable full quotes from a structurally valid batch."""
    return _parse_binary(message, instruments, received)[0]


class QuoteStream:
    def __init__(
        self,
        instruments: list[Instrument],
        on_quote: Callable[[Quote], None],
        on_connection: Callable[[bool], None],
        clock: Callable[[], datetime],
        *,
        credentials: tuple[str, str] | None = None,
        on_unusable: Callable[[str], None] | None = None,
    ):
        self.instruments = {item.token: item for item in instruments}
        if not 1 <= len(self.instruments) <= 10:
            raise ValueError("stream requires one to ten reviewed instruments")
        key, token = (
            credentials
            if credentials is not None
            else (os.environ.get("KITE_API_KEY", ""), os.environ.get("KITE_ACCESS_TOKEN", ""))
        )
        if not key or not token:
            raise BrokerUnavailable("missing broker stream credentials")
        self._url = "wss://ws.kite.trade/?" + urlencode({"api_key": key, "access_token": token})
        self._on_quote, self._on_connection, self._clock = on_quote, on_connection, clock
        self._on_unusable = on_unusable
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._socket: Any = None
        self._status_lock = threading.Lock()
        self._diagnostics: dict[str, Any] = {
            "state": "connecting",
            "failures": 0,
            "last_failure": None,
            "last_message_at": None,
            "unusable_quotes": 0,
        }

    def diagnostics(self) -> dict[str, Any]:
        """Credential-free transport state; never include broker messages or URLs."""
        with self._status_lock:
            return dict(self._diagnostics)

    def _status(self, **values: Any) -> None:
        with self._status_lock:
            self._diagnostics.update(values)

    def _run(self) -> None:
        from websockets.sync.client import connect

        attempts = 0
        while not self._stop.is_set() and attempts < 10:
            phase = "connect"
            try:
                self._status(state="connecting" if not attempts else "retrying")
                with connect(
                    self._url,
                    open_timeout=5,
                    close_timeout=2,
                    max_size=65536,
                    max_queue=16,
                    proxy=None,
                    compression=None,
                ) as socket:
                    self._socket = socket
                    phase = "subscribe"
                    tokens = list(self.instruments)
                    socket.send(json.dumps({"a": "subscribe", "v": tokens}))
                    socket.send(json.dumps({"a": "mode", "v": ["full", tokens]}))
                    self._on_connection(True)
                    self._status(state="connected")
                    while not self._stop.is_set():
                        phase = "receive"
                        message = socket.recv(timeout=5)
                        self._status(last_message_at=utc(self._clock()).isoformat())
                        if isinstance(message, str):
                            phase = "control"
                            payload = json.loads(message)
                            if payload.get("type") == "error":
                                raise BrokerUnavailable("broker streaming session failed")
                            continue
                        phase = "parse"
                        quotes, unusable = _parse_binary(message, self.instruments, self._clock())
                        with self._status_lock:
                            self._diagnostics["unusable_quotes"] += len(unusable)
                        phase = "process"
                        if self._on_unusable:
                            for symbol in unusable:
                                self._on_unusable(symbol)
                        for quote in quotes:
                            self._on_quote(quote)
                        attempts = 0
                        self._status(failures=0)
            except Exception as error:
                # Exception strings can include authenticated URLs; never log them.
                from websockets.exceptions import InvalidStatus

                attempts += 1
                code = (
                    "handshake_rejected"
                    if isinstance(error, InvalidStatus)
                    else "timeout"
                    if isinstance(error, TimeoutError)
                    else "broker_rejected"
                    if isinstance(error, BrokerUnavailable)
                    else "invalid_data"
                    if phase in ("parse", "control")
                    else "processing_error"
                    if phase == "process"
                    else "connection_lost"
                )
                self._status(
                    state="failed" if attempts >= 10 else "retrying",
                    failures=attempts,
                    last_failure=code,
                )
            finally:
                self._socket = None
                self._on_connection(False)
            if attempts < 10:
                self._stop.wait(min(30, 2**attempts))
        if self._stop.is_set():
            self._status(state="stopped")

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError("stream already started")
        self._thread = threading.Thread(target=self._run, name="kite-readonly-feed", daemon=True)
        self._thread.start()

    def close(self) -> None:
        self._stop.set()
        self._status(state="stopped")
        self._on_connection(False)
        if self._socket:
            self._socket.close()
        if self._thread:
            self._thread.join(timeout=8)
