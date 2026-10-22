"""Immutable, causal price research. No account, broker or executable policy owner."""

import hashlib
import json
import os
from bisect import bisect_right
from collections import defaultdict
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_EVEN, Context, Decimal, localcontext
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from trading_agent.daily_research.dataset import DailyBar, DailyDataset, read_json
from trading_agent.investment_research.benchmark import compare_benchmark, load_benchmark
from trading_agent.investment_research.indicators import (
    FORMULA_VERSION,
    INDICATOR_DEFINITIONS,
    indicator_series,
)
from trading_agent.market_data.calendar import IST
from trading_agent.models import DomainModel, stamp, utc

Interval = Literal["1d", "1w", "1mo"]
CONTEXT_FILE = "investment-context.json"
BENCHMARK_FILE = "investment-benchmark.json"
SERIES_VERSION = "investment-price-series-v1"
PRECISION = Context(prec=34, rounding=ROUND_HALF_EVEN)


class CalendarCoverage(DomainModel):
    start: date
    end: date
    available_at: datetime
    reference: str = Field(min_length=3, max_length=2000, pattern=r".*\S.*")
    completeness_reviewed: bool = Field(strict=True)

    @field_validator("available_at")
    @classmethod
    def aware(cls, value: datetime) -> datetime:
        return utc(value)

    @model_validator(mode="after")
    def ordered(self) -> "CalendarCoverage":
        if not self.completeness_reviewed:
            raise ValueError("Calendar completeness needs explicit review.")
        if self.end < self.start:
            raise ValueError("Calendar coverage must be chronological.")
        return self


class ResearchContext(DomainModel):
    schema_version: Literal[1]
    dataset_sha256: dict[str, str]
    calendar: CalendarCoverage
    benchmark_file: Literal["investment-benchmark.json"] | None = None
    benchmark_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def bindings(self) -> "ResearchContext":
        if set(self.dataset_sha256) != {"manifest.json", "daily.jsonl"} or any(
            len(value) != 64 or any(c not in "0123456789abcdef" for c in value)
            for value in self.dataset_sha256.values()
        ):
            raise ValueError("Context needs both exact daily input hashes.")
        if bool(self.benchmark_file) != bool(self.benchmark_sha256):
            raise ValueError("Benchmark file and content hash must be declared together.")
        return self


def _read_context(dataset: DailyDataset, path: Path) -> tuple[ResearchContext, str]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 128_000:
        raise ValueError("Research context must be a bounded regular file.")
    with path.open("rb") as source:
        content = source.read(128_001)
    if len(content) > 128_000:
        raise ValueError("Research context exceeds its read budget.")
    context = ResearchContext.model_validate(read_json(content.decode("utf-8")))
    if context.dataset_sha256 != dataset.hashes:
        raise ValueError("Research context does not bind the installed daily inputs.")
    identity = hashlib.sha256(content).hexdigest()
    _verify_file(path, identity, 128_000)
    return context, identity


def _verify_file(path: Path, identity: str, limit: int) -> None:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ValueError("Research evidence file changed.")
    with path.open("rb") as source:
        content = source.read(limit + 1)
    if len(content) > limit or hashlib.sha256(content).hexdigest() != identity:
        raise ValueError("Research evidence changed while reading.")


def _eligible(dataset: DailyDataset, symbol: str, now: datetime) -> list[dict[str, Any]]:
    manifest = dataset.manifest
    sessions = {item.day: item for item in manifest.sessions}
    indices = {day: index for index, day in enumerate(sessions)}
    members = [m for m in manifest.universe if m.symbol == symbol and m.known_at <= now]
    dates = [m.effective_session for m in members]
    snapshot = manifest.universe_kind == "prospective_snapshot"
    rows: list[dict[str, Any]] = []
    previous_index: int | None = None
    previous_membership: date | None = None
    previous: DailyBar | None = None
    tri = Decimal(100)
    dependency: datetime | None = None
    for bar in dataset.bars():
        if bar.symbol != symbol:
            continue
        session = sessions[bar.session]
        close_at = datetime.combine(session.day, session.close, IST)
        member_index = (0 if members else -1) if snapshot else bisect_right(dates, bar.session) - 1
        if close_at > now or member_index < 0 or not members[member_index].included:
            continue
        member = members[member_index]
        available = max(bar.available_at, member.known_at)
        if available > now:
            continue
        index = indices[bar.session]
        broken = (
            previous_index is None
            or index != previous_index + 1
            or (not snapshot and previous_membership != member.effective_session)
        )
        if broken:
            tri, dependency = Decimal(100), available
        else:
            assert previous is not None and dependency is not None
            tri *= (
                bar.close * Decimal(bar.share_numerator) / Decimal(bar.share_denominator)
                + bar.cash_per_previous_share
            ) / previous.close
            dependency = max(dependency, available)
        rows.append(
            {
                "time": stamp(close_at),
                "session": bar.session.isoformat(),
                **{key: str(getattr(bar, key)) for key in ("open", "high", "low", "close")},
                "volume": str(bar.volume),
                "raw_volume": bar.volume,
                "available_at": stamp(available),
                "tri_available_at": stamp(dependency),
                "total_return_index": str(tri),
                "segment_break": broken,
                "share_factor": str(Decimal(bar.share_numerator) / Decimal(bar.share_denominator)),
                "quality": "reviewed_share_adjusted_daily",
            }
        )
        previous, previous_index, previous_membership = bar, index, member.effective_session
    # Adjust each complete segment into its last known share units. Cash dividends
    # affect only the separate gross index, never the OHLC/share adjustment.
    factor = Decimal(1)
    action_available: datetime | None = None
    for row in reversed(rows):
        own_available = datetime.fromisoformat(row["available_at"])
        for key in ("open", "high", "low", "close"):
            row["raw_" + key] = row[key]
            row[key] = str(Decimal(row[key]) / factor)
        row["volume"] = str(Decimal(row["volume"]) * factor)
        if action_available:
            row["available_at"] = stamp(max(own_available, action_available))
        if row["segment_break"]:
            factor, action_available = Decimal(1), None
        else:
            current_factor = Decimal(row["share_factor"])
            factor *= current_factor
            if current_factor != 1:
                action_available = max(own_available, action_available or own_available)
    return rows


def _period(day: date, interval: Interval) -> tuple[date, date, str]:
    if interval == "1w":
        start = day - timedelta(days=day.weekday())
        return start, start + timedelta(days=6), start.isoformat()
    start = day.replace(day=1)
    end = (day.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1)
    return start, end, start.strftime("%Y-%m")


def _aggregate(
    dataset: DailyDataset,
    rows: list[dict[str, Any]],
    now: datetime,
    interval: Interval,
    coverage: CalendarCoverage | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    expected: dict[str, list[Any]] = defaultdict(list)
    periods: dict[str, tuple[date, date]] = {}
    for session in dataset.manifest.sessions:
        if datetime.combine(session.day, session.open, IST) > now:
            break
        start, end, key = _period(session.day, interval)
        expected[key].append(session)
        periods[key] = start, end
    # Include later reviewed sessions in a period that has already begun.
    for session in dataset.manifest.sessions:
        start, end, key = _period(session.day, interval)
        if key in expected and session not in expected[key]:
            expected[key].append(session)
    by_day = {row["session"]: row for row in rows}
    result, excluded = [], []
    reset = True
    for key, sessions in expected.items():
        start, end = periods[key]
        present = [by_day[s.day.isoformat()] for s in sessions if s.day.isoformat() in by_day]
        verified = bool(
            coverage
            and coverage.available_at <= now
            and coverage.start <= start
            and coverage.end >= end
        )
        future = any(datetime.combine(s.day, s.close, IST) > now for s in sessions)
        state, reason = "incomplete", "PERIOD_INPUT_MISSING_OR_UNAVAILABLE"
        if not verified:
            state, reason = "unavailable", "CALENDAR_COVERAGE_UNVERIFIED"
        elif future:
            state, reason = "partial", "PERIOD_NOT_COMPLETE"
        elif len(present) == len(sessions) and not any(r["segment_break"] for r in present[1:]):
            assert coverage is not None
            item = {
                "time": present[-1]["time"],
                "session": present[-1]["session"],
                "period": key,
                "open": present[0]["open"],
                "high": str(max(Decimal(r["high"]) for r in present)),
                "low": str(min(Decimal(r["low"]) for r in present)),
                "close": present[-1]["close"],
                "volume": str(sum((Decimal(r["volume"]) for r in present), Decimal(0))),
                "available_at": stamp(
                    max(
                        coverage.available_at,
                        *(datetime.fromisoformat(r["available_at"]) for r in present),
                    )
                ),
                "segment_break": reset or present[0]["segment_break"],
                "partial": False,
                "observations": len(present),
                "quality": "reviewed_share_adjusted_" + interval,
            }
            result.append(item)
            reset = False
            continue
        excluded.append(
            {
                "period": key,
                "state": state,
                "reason": reason,
                "observations": len(present),
                "expected_sessions": len(sessions),
            }
        )
        reset = True
    return result, excluded


def _indicator_status(bars: list[dict[str, Any]], basis: str) -> dict[str, Any]:
    last = bars[-1] if bars else {}
    return {
        key: {
            **definition,
            "value": last.get(key),
            "state": "available"
            if last.get(key) is not None
            else "warming_up"
            if bars
            else "unavailable",
            "reason": None
            if last.get(key) is not None
            else "INSUFFICIENT_CONSECUTIVE_HISTORY"
            if bars
            else "NO_COMPLETE_BARS",
            "basis": basis,
            "available_at": last.get("indicator_available_at"),
        }
        for key, definition in INDICATOR_DEFINITIONS.items()
    }


def series_snapshot(
    dataset: DailyDataset,
    symbol: str,
    as_of: datetime,
    *,
    timeframe: Interval = "1d",
    context_path: Path | None = None,
    benchmark_path: Path | None = None,
) -> dict[str, Any]:
    """Calculate from complete saved dependencies; no network or account is reachable."""
    now = utc(as_of)
    if timeframe not in {"1d", "1w", "1mo"}:
        raise ValueError("Research supports daily, weekly and monthly intervals.")
    if symbol not in {m.symbol for m in dataset.manifest.universe}:
        raise ValueError("Symbol is not declared by the saved dataset.")
    if dataset.fingerprints() != dataset.hashes:
        raise ValueError("Daily research input changed.")
    default_context = dataset.directory / CONTEXT_FILE
    context_path = context_path or (
        default_context if default_context.exists() or default_context.is_symlink() else None
    )
    context, context_hash = _read_context(dataset, context_path) if context_path else (None, None)
    coverage = context.calendar if context and context.calendar.available_at <= now else None
    if context and context.benchmark_file:
        benchmark_path = benchmark_path or dataset.directory / context.benchmark_file
    with localcontext(PRECISION):
        daily = _eligible(dataset, symbol, now)
        complete, partial = (
            (daily, [])
            if timeframe == "1d"
            else _aggregate(dataset, daily, now, timeframe, coverage)
        )
        bars = indicator_series(complete)
    # A recursive feature depends on every observation since the segment's seed.
    dependency = None
    for row in bars:
        available = datetime.fromisoformat(row["available_at"])
        dependency = (
            available if row["segment_break"] or dependency is None else max(dependency, available)
        )
        row["indicator_available_at"] = stamp(dependency)
    benchmark: dict[str, Any] = {
        "state": "unavailable",
        "reason": "BENCHMARK_NOT_CONFIGURED",
        "relative_strength_pct": None,
        "detail": "No compatible sourced benchmark is configured. Missing strength is not zero.",
    }
    benchmark_identity = None
    if benchmark_path and (not context or coverage):
        loaded = load_benchmark(benchmark_path, now)
        benchmark_identity = loaded["input_identity"]["sha256"]
        if context and context.benchmark_sha256 and context.benchmark_sha256 != benchmark_identity:
            raise ValueError("Benchmark does not match the reviewed context hash.")
        stock = [{**r, "available_at": r["tri_available_at"]} for r in daily]
        if loaded["series"]["synthetic"] != dataset.manifest.synthetic:
            benchmark = {
                "state": "unavailable",
                "reason": "SOURCE_PROVENANCE_MISMATCH",
                "relative_strength_pct": None,
            }
        else:
            benchmark = compare_benchmark(stock, loaded, lookback=20)
        benchmark["detail"] = "Comparison uses 20 matched DAILY intervals. " + (
            benchmark.get("reason")
            or "Relative wealth growth uses compatible gross INR indices, before account fees/tax."
        )
        benchmark["metadata"] = loaded["series"]
        _verify_file(benchmark_path, benchmark_identity, 8_000_000)
    if benchmark_path and context and not coverage:
        benchmark["reason"] = "CONTEXT_NOT_YET_AVAILABLE"
        benchmark["detail"] = "Benchmark configuration review is not available at this as-of."
    if context_path and context_hash:
        _verify_file(context_path, context_hash, 128_000)
    if dataset.fingerprints() != dataset.hashes:
        raise ValueError("Daily research input changed while calculating.")
    basis = "Causal share-adjusted OHLC within each consecutive segment; cash dividends excluded"
    identity = {
        "series_version": SERIES_VERSION,
        "formula_version": FORMULA_VERSION,
        "calculation_sha256": {
            name: hashlib.sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
            for name in ("series.py", "indicators.py", "benchmark.py")
        },
        "dataset_sha256": dataset.hashes,
        "context_sha256": context_hash,
        "benchmark_sha256": benchmark_identity,
        "symbol": symbol,
        "timeframe": timeframe,
        "as_of": stamp(now),
    }
    input_id = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    evidence = []
    if bars:
        last = bars[-1]
        for key in ("sma50", "sma200"):
            if last[key] is not None:
                relationship = (
                    "at or above" if Decimal(last["close"]) >= Decimal(last[key]) else "below"
                )
                evidence.append(
                    f"Latest adjusted close {last['close']} is {relationship} "
                    f"{key.upper()} {last[key]}; descriptive trend evidence."
                )
        if last["macd_histogram"] is not None:
            evidence.append(
                f"MACD histogram is {last['macd_histogram']}; "
                "a line/signal difference, not a trade instruction."
            )
        evidence.append(
            f"Price drawdown since this segment's peak: {last['drawdown_pct']}%. "
            "Cash dividends are excluded from this price measure."
        )
    verified = bool(coverage)
    expected = [
        s.day.isoformat()
        for s in dataset.manifest.sessions
        if datetime.combine(s.day, s.close, IST) <= now
    ]
    included = {r["session"] for r in daily}
    quality = {
        "declared_completed_sessions": len(expected),
        "available_daily_bars": len(daily),
        "missing_or_unavailable_sessions": sum(day not in included for day in expected),
        "latest_expected_session": expected[-1] if expected else None,
        "latest_included_session": daily[-1]["session"] if daily else None,
    }
    coverage_detail = (
        "Calendar completeness is a local review assertion; not external certification. "
        if verified
        else "Weekly/monthly completion needs hash-bound calendar coverage; no dates are guessed. "
    ) + (
        f"Latest included session: {quality['latest_included_session'] or 'none'}; "
        f"latest declared completed session: {quality['latest_expected_session'] or 'none'}. "
        f"{quality['missing_or_unavailable_sessions']} declared sessions lack eligible stock bars."
    )
    return {
        "schema_version": 1,
        "observed_at": stamp(now),
        "symbol": symbol,
        "timeframe": timeframe,
        "bars": bars,
        "data_state": "available" if bars else "missing",
        "source": {
            "description": dataset.manifest.source,
            "synthetic": dataset.manifest.synthetic,
            "price_basis": basis,
            "volume_basis": "Share units adjusted inversely to OHLC within each segment",
            "kind": "immutable_investment_research",
        },
        "research": {
            "series_version": SERIES_VERSION,
            "formula_version": FORMULA_VERSION,
            "snapshot_id": input_id,
            "inputs": identity,
            "basis": basis,
            "indicator_status": _indicator_status(bars, basis),
            "coverage": {
                "calendar_verified": verified,
                "detail": coverage_detail,
                "daily_quality": quality,
                "calendar_reference": coverage.reference if coverage else None,
                "calendar_available_at": stamp(coverage.available_at) if coverage else None,
                "seed_origin": bars[0]["session"] if bars else None,
                "computed_bars": len(bars),
            },
            "partial_periods": partial,
            "benchmark": benchmark,
            "fundamentals": {"state": "unavailable", "reason": "LICENSED_SOURCE_NOT_CONFIGURED"},
            "explanations": [
                *evidence,
                "Saved price indicators do not authorize orders or predict profit probabilities.",
                "Windows reset at missing sessions, unavailable data or membership re-entry.",
                "OHLC/volume use known share actions; cash affects only the separate gross index.",
                "Drawdown/volatility use adjusted closes, not account returns; no annualization.",
                "Current constituents do not establish historical point-in-time membership."
                if dataset.manifest.universe_kind == "prospective_snapshot"
                else "Point-in-time membership is declared; external completeness is unverified.",
                "Execution strategy/rank, hold cap, risk and ML identities are unchanged.",
            ],
        },
        "limitations": [
            "Research only: no orders, network, account changes or profit validation.",
            "Input source, membership, basis and calendar completeness are review assertions.",
            "Adjusted bars depend on all share actions used at this as-of; not past fill prices.",
            "Unknown calendar coverage, missing bars and insufficient warmup remain unavailable.",
            "Gross index assumes same-close reinvestment before fees/tax/settlement delays.",
        ],
    }


def write_series_report(
    dataset: DailyDataset,
    symbol: str,
    as_of: datetime,
    output: Path,
    *,
    timeframe: Interval = "1d",
    context_path: Path | None = None,
    benchmark_path: Path | None = None,
) -> dict[str, Any]:
    if output.exists() or output.is_symlink() or output.resolve().is_relative_to(dataset.directory):
        raise ValueError("Research output must be a new directory outside its daily source.")
    result = series_snapshot(
        dataset,
        symbol,
        as_of,
        timeframe=timeframe,
        context_path=context_path,
        benchmark_path=benchmark_path,
    )
    output.mkdir(parents=True, mode=0o700)
    artifacts = {
        "report.json": json.dumps(result, indent=2, sort_keys=True) + "\n",
        "report.md": "# Saved investment price research\n\n"
        + f"{symbol}; {timeframe}; as of {result['observed_at']}.\n\n"
        + "\n".join("- " + item for item in result["limitations"])
        + "\n",
    }
    hashes = {}
    for name, content in artifacts.items():
        with os.fdopen(
            os.open(output / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w"
        ) as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        hashes[name] = hashlib.sha256(content.encode()).hexdigest()
    manifest = (
        json.dumps(
            {
                "schema_version": 1,
                "state": "finished",
                "snapshot_id": result["research"]["snapshot_id"],
                "sha256": hashes,
                "execution_simulated": False,
                "ready_for_live": False,
            },
            indent=2,
        )
        + "\n"
    )
    with os.fdopen(
        os.open(output / "manifest.json", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w"
    ) as file:
        file.write(manifest)
        file.flush()
        os.fsync(file.fileno())
    return result
