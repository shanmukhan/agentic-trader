"""Bounded local benchmark declarations and causal, same-basis comparisons.

This adapter neither downloads data nor certifies a provider or a storage licence.
The caller chooses the local artifact; no path is included in its public result.
Analytical ratios use 34-digit Decimal precision and ROUND_HALF_EVEN, with final
percentages rounded once to 12 decimal places. They are not account money.
"""

import hashlib
import ipaddress
import json
import os
import re
import stat
from datetime import date, datetime
from decimal import ROUND_HALF_EVEN, Decimal, localcontext
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from trading_agent.market_data.calendar import IST
from trading_agent.models import stamp, utc

MAX_BYTES = 8_000_000
MAX_ROWS = 10_000
MAX_LOOKBACK = 2_520
DECIMAL_PRECISION = 34
PERCENT_PLACES = 12
METHOD = "investment-benchmark-relative-wealth-v1"
_LEVEL = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?\Z")
_ANALYTICAL_LEVEL = re.compile(r"(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[Ee][+-]?[0-9]{1,4})?\Z")
_MANIFEST_FIELDS = {
    "schema_version",
    "series_id",
    "title",
    "provider",
    "source_url",
    "license_reference",
    "currency",
    "return_type",
    "synthetic",
    "published_at",
    "available_at",
    "rows",
}
_ROW_FIELDS = {"session", "level", "close_at", "available_at"}
_LIMITATIONS = [
    "Provider, source URL and licence reference are local declarations, not verified entitlements.",
    "No data is downloaded, interpolated or forward-filled.",
    "A benchmark level is analytical evidence, not an executable stock price or account value.",
]


def _fields(value: object, fields: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError(f"{label} requires exactly the declared schema fields")
    return value


def _text(value: object, label: str, limit: int = 500) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{label} must be a bounded nonblank string")
    if any(ord(char) < 32 for char in value):
        raise ValueError(f"{label} contains a control character")
    return value


def _time(value: object) -> datetime:
    if not isinstance(value, str) or len(value) > 64:
        raise ValueError("benchmark timestamps must be bounded aware ISO strings")
    try:
        return utc(datetime.fromisoformat(value))
    except (ValueError, OverflowError) as exc:
        raise ValueError("benchmark timestamps must be aware ISO strings") from exc


def _day(value: object) -> date:
    if not isinstance(value, str) or len(value) != 10:
        raise ValueError("benchmark sessions must be YYYY-MM-DD strings")
    try:
        result = date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("benchmark sessions must be YYYY-MM-DD strings") from exc
    if result.isoformat() != value:
        raise ValueError("benchmark sessions must be canonical dates")
    return result


def _level(value: object) -> Decimal:
    if not isinstance(value, str) or len(value) > 42 or not _LEVEL.fullmatch(value):
        raise ValueError("index levels require positive plain decimal strings")
    parts = value.split(".")
    if len(value.replace(".", "").lstrip("0")) > 28 or (len(parts) == 2 and len(parts[1]) > 12):
        raise ValueError("index levels exceed 28 digits or 12 decimal places")
    level = Decimal(value)
    if level <= 0:
        raise ValueError("index levels must be positive")
    return level


def _stock_level(value: object) -> Decimal:
    """Keep the caller's 34-digit analytical TRI without display quantization."""
    if not isinstance(value, str) or len(value) > 128 or not _ANALYTICAL_LEVEL.fullmatch(value):
        raise ValueError("stock index levels require bounded analytical decimal strings")
    result = Decimal(value)
    if (
        result <= 0
        or len(result.as_tuple().digits) > DECIMAL_PRECISION
        or not -128 <= result.adjusted() <= 128
    ):
        raise ValueError("stock index levels exceed positive 34-digit analytical precision bounds")
    return result


def _source_url(value: object) -> str:
    source = _text(value, "source_url", 2000)
    try:
        parsed = urlsplit(source)
        host = parsed.hostname
        if (
            parsed.scheme != "https"
            or not host
            or "." not in host
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or parsed.port not in (None, 443)
            or host.endswith(".local")
            or host.endswith(".localhost")
        ):
            raise ValueError("source_url must be a public HTTPS provenance URL")
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError("source_url must name a provider host, not an IP address")
    except ValueError as exc:
        raise ValueError("source_url must be a public HTTPS provenance URL") from exc
    return source


def _unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate benchmark JSON field")
        result[key] = value
    return result


def _nonfinite(value: str) -> None:
    raise ValueError("nonfinite benchmark JSON value")


def _identity(info: os.stat_result) -> tuple[int, int, int, int, int]:
    return info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns


def _read_artifact(path: Path) -> tuple[bytes, str]:
    """Read twice from one nonblocking/no-follow descriptor and check its path identity."""
    before = path.stat(follow_symlinks=False)
    if not stat.S_ISREG(before.st_mode) or before.st_size > MAX_BYTES:
        raise ValueError("benchmark artifact must be a bounded regular nonsymlink file")
    flags = os.O_RDONLY | os.O_NONBLOCK | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags), "rb") as handle:
        opened = os.fstat(handle.fileno())
        if not stat.S_ISREG(opened.st_mode) or _identity(before) != _identity(opened):
            raise RuntimeError("benchmark artifact changed before loading")
        content = handle.read(MAX_BYTES + 1)
        if len(content) > MAX_BYTES:
            raise ValueError("benchmark artifact exceeds its read budget")
        digest = hashlib.sha256(content).hexdigest()
        handle.seek(0)
        checked = handle.read(MAX_BYTES + 1)
        after = os.fstat(handle.fileno())
    current = path.stat(follow_symlinks=False)
    if (
        hashlib.sha256(checked).hexdigest() != digest
        or _identity(opened) != _identity(after)
        or _identity(after) != _identity(current)
        or not stat.S_ISREG(current.st_mode)
    ):
        raise RuntimeError("benchmark artifact changed during loading")
    return content, digest


def load_benchmark(path: Path, as_of: datetime) -> dict[str, Any]:
    """Validate an immutable local snapshot and expose only causally available rows.

    Malformed input raises ValueError; file I/O or concurrent mutation errors are
    left for the caller to report as unavailable without faulting an account.
    """
    now = utc(as_of)
    content, digest = _read_artifact(path)
    try:
        payload = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=_unique,
            parse_float=Decimal,
            parse_constant=_nonfinite,
        )
    except (UnicodeError, json.JSONDecodeError, RecursionError) as exc:
        raise ValueError("benchmark artifact must contain bounded valid UTF-8 JSON") from exc
    data = _fields(payload, _MANIFEST_FIELDS, "benchmark manifest")
    if type(data["schema_version"]) is not int or data["schema_version"] != 1:
        raise ValueError("unsupported benchmark schema version")
    if data["currency"] != "INR" or data["return_type"] not in (
        "gross_total_return",
        "net_total_return",
        "price",
    ):
        raise ValueError("benchmark requires INR and an explicit supported return convention")
    if type(data["synthetic"]) is not bool:
        raise ValueError("benchmark synthetic must be a boolean")
    series: dict[str, Any] = {
        key: _text(data[key], key)
        for key in ("series_id", "title", "provider", "license_reference")
    }
    series.update(
        source_url=_source_url(data["source_url"]),
        currency=data["currency"],
        return_type=data["return_type"],
        synthetic=data["synthetic"],
        provenance_state="declared_unverified",
    )
    published, available = _time(data["published_at"]), _time(data["available_at"])
    if available < published:
        raise ValueError("benchmark availability cannot precede publication")
    series.update(published_at=stamp(published), available_at=stamp(available))
    supplied = data["rows"]
    if not isinstance(supplied, list) or not 1 <= len(supplied) <= MAX_ROWS:
        raise ValueError("benchmark requires between 1 and 10000 rows")
    rows: list[dict[str, Any]] = []
    previous: date | None = None
    for raw in supplied:
        row = _fields(raw, _ROW_FIELDS, "benchmark row")
        session = _day(row["session"])
        if previous is not None and session <= previous:
            raise ValueError("benchmark sessions must be unique and chronological")
        previous = session
        _level(row["level"])
        close, known = _time(row["close_at"]), _time(row["available_at"])
        if close.astimezone(IST).date() != session or known < close:
            raise ValueError(
                "benchmark rows require their actual session close before availability"
            )
        dependency = max(available, known)
        if dependency <= now and close <= now:
            rows.append(
                {
                    "session": session.isoformat(),
                    "level": row["level"],
                    "close_at": stamp(close),
                    "available_at": stamp(dependency),
                }
            )
    if _read_artifact(path)[1] != digest:
        raise RuntimeError("benchmark artifact changed during validation")
    return {
        "schema_version": 1,
        "state": "available" if rows else "unavailable",
        "reason": None if rows else "No benchmark sessions were available at this as-of time.",
        "as_of": stamp(now),
        "series": series,
        "input_identity": {"sha256": digest, "size_bytes": len(content)},
        "rows": rows,
        "coverage": {
            "available_rows": len(rows),
            "excluded_future_rows": len(supplied) - len(rows),
            "first_session": rows[0]["session"] if rows else None,
            "last_session": rows[-1]["session"] if rows else None,
        },
        "limitations": list(_LIMITATIONS),
    }


def _percentage(factor: Decimal) -> str:
    percent = (factor - 1) * 100
    # Formatting a legitimate very large ratio needs room for its integer digits
    # as well as its 12 display places; it must not fail the analytical snapshot.
    with localcontext() as context:
        context.prec = max(DECIMAL_PRECISION, percent.adjusted() + 1 + PERCENT_PLACES)
        value = percent.quantize(Decimal("0.000000000001"))
        return format(value, "f")


def compare_benchmark(
    stock_rows: list[dict[str, Any]],
    benchmark: dict[str, Any],
    lookback: int = 20,
) -> dict[str, Any]:
    """Compare complete matched gross INR TRI intervals, never skipping a gap.

    Stock rows are the caller's reviewed daily sequence. A missing date in either
    sequence inside the requested window makes the comparison unavailable. This
    function does not invent an exchange calendar when both sequences omit a date.
    """
    result: dict[str, Any] = {
        "state": "unavailable",
        "reason_code": None,
        "reason": None,
        "method": METHOD,
        "interval": "1d",
        "lookback": lookback,
        "currency": "INR",
        "return_type": "gross_total_return",
        "decimal_precision": DECIMAL_PRECISION,
        "rounding": "ROUND_HALF_EVEN",
        "percent_decimal_places": PERCENT_PLACES,
        "relative_strength_pct": None,
        "stock_growth": None,
        "benchmark_growth": None,
        "stock_return_pct": None,
        "benchmark_return_pct": None,
        "window_start": None,
        "window_end": None,
        "matched_sessions": [],
        "available_at": None,
        "as_of": benchmark.get("as_of"),
        "benchmark": {
            "series": benchmark.get("series"),
            "input_identity": benchmark.get("input_identity"),
        },
        "limitations": [
            *_LIMITATIONS,
            "Gross index returns exclude stock execution costs, investor fees and tax.",
            "Session completeness relies on the caller's reviewed stock session sequence.",
        ],
    }

    def unavailable(code: str, reason: str) -> dict[str, Any]:
        result.update(reason_code=code, reason=reason)
        return result

    if type(lookback) is not int or not 1 <= lookback <= MAX_LOOKBACK:
        return unavailable("invalid_lookback", "Lookback must be between 1 and 2520 intervals.")
    if benchmark.get("state") != "available":
        return unavailable(
            "benchmark_unavailable", "No admissible benchmark snapshot is available."
        )
    series = benchmark.get("series", {})
    if series.get("currency") != "INR" or series.get("return_type") != "gross_total_return":
        return unavailable(
            "incompatible_basis", "Comparison requires gross total-return indices in INR."
        )
    try:
        now = _time(benchmark["as_of"])
        declared = _time(series["available_at"])
        if declared > now:
            return unavailable(
                "benchmark_unavailable", "Benchmark declaration is not yet available."
            )
        known_stock: list[dict[str, Any]] = []
        previous: date | None = None
        for row in stock_rows:
            day = _day(row["session"])
            if previous is not None and day <= previous:
                raise ValueError("stock sessions must be unique and chronological")
            previous = day
            level = _stock_level(row["total_return_index"])
            known = _time(row["available_at"])
            if type(row["segment_break"]) is not bool:
                raise ValueError("stock segment_break must be a boolean")
            if (
                row.get("currency", "INR") != "INR"
                or row.get("return_type", "gross_total_return") != "gross_total_return"
            ):
                return unavailable("incompatible_basis", "Stock and benchmark return bases differ.")
            if known <= now and day <= now.astimezone(IST).date():
                known_stock.append({**row, "_level": level, "_known": known})
        available_benchmark: dict[str, dict[str, Any]] = {}
        previous = None
        for row in benchmark["rows"]:
            day = _day(row["session"])
            if previous is not None and day <= previous:
                raise ValueError("benchmark sessions must be unique and chronological")
            previous = day
            level, known = _level(row["level"]), _time(row["available_at"])
            close = _time(row["close_at"])
            if close.astimezone(IST).date() != day or known < close:
                raise ValueError("invalid benchmark session clocks")
            if max(known, declared, close) <= now:
                available_benchmark[row["session"]] = {**row, "_level": level, "_known": known}
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        return unavailable("invalid_input", f"Comparison input is invalid: {exc}")
    if len(known_stock) < lookback + 1:
        return unavailable("insufficient_history", "The requested stock window is not complete.")
    window = known_stock[-(lookback + 1) :]
    sessions = [row["session"] for row in window]
    result.update(window_start=sessions[0], window_end=sessions[-1])
    if any(row["segment_break"] for row in window[1:]):
        return unavailable(
            "segment_break", "The requested window crosses a stock return-basis break."
        )
    common = [day for day in available_benchmark if sessions[0] <= day <= sessions[-1]]
    if common != sessions:
        return unavailable(
            "session_gap", "Stock and benchmark sessions differ inside the requested window."
        )
    with localcontext() as context:
        context.prec = DECIMAL_PRECISION
        context.rounding = ROUND_HALF_EVEN
        stock_growth = window[-1]["_level"] / window[0]["_level"]
        benchmark_growth = (
            available_benchmark[sessions[-1]]["_level"] / available_benchmark[sessions[0]]["_level"]
        )
        relative = stock_growth / benchmark_growth
        result.update(
            state="available",
            relative_strength_pct=_percentage(relative),
            stock_growth=format(stock_growth, "f"),
            benchmark_growth=format(benchmark_growth, "f"),
            stock_return_pct=_percentage(stock_growth),
            benchmark_return_pct=_percentage(benchmark_growth),
            matched_sessions=sessions,
            available_at=stamp(
                max(
                    declared,
                    *(row["_known"] for row in window),
                    *(available_benchmark[day]["_known"] for day in sessions),
                )
            ),
        )
    return result
