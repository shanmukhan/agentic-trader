"""Bounded official discovery reads. These URLs cannot be supplied by browser clients."""

import csv
import io
import json
from datetime import date, datetime, time, timedelta
from typing import Any

from trading_agent.backtesting.dataset import Session
from trading_agent.models import Symbol

UNIVERSE_SIZES = {"nifty50": 50, "nifty100": 100, "nifty500": 500}
UNIVERSES = {
    "nifty50": "https://www.niftyindices.com/IndexConstituent/ind_nifty50list.csv",
    "nifty100": "https://www.niftyindices.com/IndexConstituent/ind_nifty100list.csv",
    "nifty500": "https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv",
}
HOLIDAYS = "https://www.nseindia.com/api/holiday-master?type=trading"
ACTIONS = "https://www.nseindia.com/api/corporates-corporateActions"
HOURS = "https://www.nseindia.com/static/market-data/market-timings"
ACTION_PAGE = "https://www.nseindia.com/companies-listing/corporate-filings-actions"
HOLIDAY_PAGE = "https://www.nseindia.com/resources/exchange-communication-holidays"


class SourceUnavailable(ValueError):
    """No third-party error text, HTTP headers or credentials may reach the UI."""


def public_read(url: str, params: dict[str, str] | None = None) -> bytes:
    import httpx

    if url not in {*UNIVERSES.values(), HOLIDAYS, ACTIONS}:
        raise SourceUnavailable("SOURCE_NOT_ALLOWED")
    try:
        with (
            httpx.Client(timeout=15, follow_redirects=False, trust_env=False) as client,
            client.stream(
                "GET",
                url,
                params=params,
                headers={"User-Agent": "Mozilla/5.0", "Accept": "application/json,text/csv,*/*"},
            ) as response,
        ):
            response.raise_for_status()
            output = bytearray()
            for chunk in response.iter_bytes():
                output.extend(chunk)
                if len(output) > 5_000_000:
                    raise ValueError
            return bytes(output)
    except Exception:
        raise SourceUnavailable("OFFICIAL_SOURCE_UNAVAILABLE") from None


def constituents(
    raw: bytes, universe: str, *, exclusions: list[dict[str, str]] | None = None
) -> list[dict[str, str]]:
    from pydantic import TypeAdapter

    try:
        rows = list(csv.DictReader(io.StringIO(raw.decode("utf-8-sig"))))
        limit = UNIVERSE_SIZES[universe]
        # Temporary demerger constituents can take the official file above its named count.
        if not limit * 0.9 <= len(rows) <= limit * 1.1:
            raise ValueError
        result, rejected = [], []
        seen = set()
        for row in rows:
            symbol = TypeAdapter(Symbol).validate_python("NSE:" + row["Symbol"])
            if symbol in seen or not row["Company Name"].strip():
                raise ValueError
            seen.add(symbol)
            isin = row["ISIN Code"]
            reason = (
                "UNSUPPORTED_SHARE_SERIES"
                if row["Series"] != "EQ"
                else "UNSUPPORTED_SHARE_IDENTIFIER"
                if len(isin) != 12 or not isin.startswith("INE")
                else None
            )
            if reason:
                rejected.append({"symbol": symbol, "reason": reason})
                continue
            result.append({"symbol": symbol, "isin": isin, "name": row["Company Name"]})
        if not result or len(result) > 500:
            raise ValueError
        if exclusions is not None:
            exclusions.extend(rejected)
        return sorted(result, key=lambda r: r["symbol"])
    except Exception:
        raise SourceUnavailable("UNIVERSE_RESPONSE_INVALID") from None


def proposed_sessions(raw: bytes, today: date) -> list[Session]:
    """A reviewable proposal, never an automatically approved execution calendar."""
    try:
        rows = json.loads(raw)["CM"]
        if not isinstance(rows, list) or not 5 <= len(rows) <= 100:
            raise ValueError
        holidays = {datetime.strptime(r["tradingDate"], "%d-%b-%Y").date() for r in rows}
        if len(holidays) != len(rows) or any(d.year != today.year for d in holidays):
            raise ValueError
        start = max(date(today.year, 1, 1), today - timedelta(days=120))
        end = min(date(today.year, 12, 31), today + timedelta(days=7))
        sessions = []
        day = start
        while day <= end:
            if day.weekday() < 5 and day not in holidays:
                sessions.append(
                    Session(day=day, open=time(9, 15), close=time(15, 30), source=HOLIDAY_PAGE)
                )
            day += timedelta(days=1)
        if len([s for s in sessions if s.day < today]) < 51:
            raise ValueError
        return sessions
    except Exception:
        raise SourceUnavailable("CALENDAR_RESPONSE_INVALID_OR_TOO_SHORT") from None


def action_symbols(raw: bytes, start: date, end: date) -> set[str]:
    """Exclude every returned action kind; never guess a split/dividend adjustment."""
    try:
        rows: Any = json.loads(raw)
        # An empty page cannot establish coverage of the whole NSE equity market.
        if not isinstance(rows, list) or not 1 <= len(rows) <= 100_000:
            raise ValueError
        symbols = set()
        for row in rows:
            day = datetime.strptime(row["exDate"], "%d-%b-%Y").date()
            if not row["symbol"] or not row["subject"]:
                raise ValueError
            if start <= day <= end:
                symbols.add("NSE:" + row["symbol"])
        if not symbols:
            raise ValueError
        return symbols
    except Exception:
        raise SourceUnavailable("ACTION_RESPONSE_INVALID_OR_EMPTY") from None
