"""Streaming, causal daily screening. No return forecast or executable trade is produced."""

import json
import os
import tomllib
from bisect import bisect_right
from collections import defaultdict, deque
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from pydantic import Field

from trading_agent.backtesting.report import code_digest
from trading_agent.daily_research.dataset import DailyBar, DailyDataset
from trading_agent.market_data.calendar import IST
from trading_agent.models import DomainModel, stamp, utc

D = Decimal


class DailyPolicy(DomainModel):
    momentum_sessions: int = Field(default=20, ge=2, le=252, strict=True)
    trend_sessions: int = Field(default=50, ge=2, le=252, strict=True)
    min_average_turnover: Decimal = Field(
        default=D("10000000"), ge=0, allow_inf_nan=False, max_digits=20, decimal_places=2
    )
    max_daily_volatility_pct: Decimal = Field(default=D("5"), gt=0, le=100, allow_inf_nan=False)

    @classmethod
    def load(cls, path: Path) -> "DailyPolicy":
        with path.open("rb") as file:
            return cls.model_validate(tomllib.load(file))


class Window:
    def __init__(self, policy: DailyPolicy):
        self.policy = policy
        self.last: DailyBar | None = None
        self.last_index = -2
        self.levels: deque[Decimal] = deque()
        self.returns: deque[Decimal] = deque()
        self.turnovers: deque[Decimal] = deque()
        self.level = D(100)
        self.trend_sum = self.return_sum = self.square_sum = self.turnover_sum = D(0)
        self.trend: deque[Decimal] = deque()
        self.observations = 0

    def add(self, bar: DailyBar, index: int) -> None:
        self.observations += 1
        p = self.policy
        if self.last:
            # Benefits use the previous period's share units. No adjusted future close is read.
            ratio = (
                bar.close * bar.share_numerator / bar.share_denominator
                + bar.cash_per_previous_share
            ) / self.last.close
            change = ratio - 1
            self.level *= ratio
            self.returns.append(change)
            self.return_sum += change
            self.square_sum += change * change
            if len(self.returns) > p.momentum_sessions:
                old = self.returns.popleft()
                self.return_sum -= old
                self.square_sum -= old * old
        self.levels.append(self.level)
        if len(self.levels) > p.momentum_sessions + 1:
            self.levels.popleft()
        self.trend.append(self.level)
        self.trend_sum += self.level
        if len(self.trend) > p.trend_sessions:
            self.trend_sum -= self.trend.popleft()
        turnover = bar.close * bar.volume
        self.turnovers.append(turnover)
        self.turnover_sum += turnover
        if len(self.turnovers) > p.momentum_sessions:
            self.turnover_sum -= self.turnovers.popleft()
        self.last, self.last_index = bar, index

    def metrics(self) -> dict[str, Any]:
        p = self.policy
        if len(self.levels) < p.momentum_sessions + 1 or len(self.trend) < p.trend_sessions:
            return {
                "status": "needs_data",
                "reasons": ["INSUFFICIENT_CONSECUTIVE_HISTORY"],
                "observations": self.observations,
            }
        momentum = (self.levels[-1] / self.levels[0] - 1) * 100
        trend = self.trend_sum / len(self.trend)
        n = D(len(self.returns))
        volatility = max(D(0), self.square_sum / n - (self.return_sum / n) ** 2).sqrt() * 100
        turnover = self.turnover_sum / len(self.turnovers)
        reasons = []
        if momentum <= 0:
            reasons.append("NONPOSITIVE_MOMENTUM")
        if self.level < trend:
            reasons.append("BELOW_TREND_AVERAGE")
        if turnover < p.min_average_turnover:
            reasons.append("LOW_AVERAGE_TURNOVER")
        if volatility > p.max_daily_volatility_pct:
            reasons.append("HIGH_DAILY_VOLATILITY")
        return {
            "status": "research_candidate" if not reasons else "screened_out",
            "reasons": reasons,
            "observations": self.observations,
            "gross_total_return_pct": str(momentum),
            "index_level": str(self.level),
            "trend_index_average": str(trend),
            "daily_volatility_pct": str(volatility),
            "average_turnover": str(turnover),
        }


def analyze(dataset: DailyDataset, policy: DailyPolicy, as_of: datetime) -> dict[str, Any]:
    as_of = utc(as_of)
    manifest = dataset.manifest
    sessions = [
        session
        for session in manifest.sessions
        if datetime.combine(session.day, session.close, IST) <= as_of
    ]
    indices = {session.day: index for index, session in enumerate(sessions)}
    transitions: dict[str, list[Any]] = defaultdict(list)
    for member in manifest.universe:
        if member.known_at <= as_of:
            transitions[member.symbol].append(member)
    effective_dates = {
        symbol: [member.effective_session for member in members]
        for symbol, members in transitions.items()
    }
    windows: dict[str, Window] = {}
    ignored_future = unavailable = gaps = 0
    # Membership is evaluated at each bar's session, preserving historical exclusions/re-entry.
    for bar in dataset.bars():
        if bar.session not in indices:
            ignored_future += 1
            continue
        members = transitions.get(bar.symbol, [])
        active_index = bisect_right(effective_dates.get(bar.symbol, []), bar.session) - 1
        if active_index < 0 or not members[active_index].included:
            windows.pop(bar.symbol, None)
            continue
        if bar.available_at > as_of:
            unavailable += 1
            windows.pop(bar.symbol, None)
            continue
        index = indices[bar.session]
        window = windows.get(bar.symbol)
        included_from = members[active_index].effective_session
        if window and (
            window.last_index != index - 1 or window.last and window.last.session < included_from
        ):
            gaps += 1
            window = None
        if window is None:
            window = windows[bar.symbol] = Window(policy)
        window.add(bar, index)
    rows = []
    latest = sessions[-1].day if sessions else None
    for symbol in sorted(transitions):
        effective = [
            member
            for member in transitions[symbol]
            if latest and member.effective_session <= latest
        ]
        if not effective:
            continue
        row: dict[str, Any] = {
            "symbol": symbol,
            "rank": None,
            "membership_effective_session": effective[-1].effective_session.isoformat(),
        }
        if not effective[-1].included:
            row.update(status="outside_universe", reasons=["EXCLUDED_BY_POINT_IN_TIME_UNIVERSE"])
        elif (
            symbol not in windows
            or (last := windows[symbol].last) is None
            or last.session != latest
        ):
            row.update(status="needs_data", reasons=["LATEST_SESSION_UNAVAILABLE_OR_MISSING"])
        else:
            window = windows[symbol]
            row.update(window.metrics())
            assert window.last is not None
            row.update(
                last_session=window.last.session.isoformat(),
                last_close=str(window.last.close),
                available_at=stamp(window.last.available_at),
            )
        rows.append(row)
    ranked = sorted(
        (row for row in rows if row["status"] == "research_candidate"),
        key=lambda row: (-D(row["gross_total_return_pct"]), row["symbol"]),
    )
    for index, row in enumerate(ranked, 1):
        row["rank"] = index
    if dataset.fingerprints() != dataset.hashes:
        raise RuntimeError("daily input changed during analysis")
    return {
        "schema_version": 1,
        "kind": "daily_research_screen",
        "as_of": stamp(as_of),
        "latest_reviewed_completed_session": latest.isoformat() if latest else None,
        "synthetic": manifest.synthetic,
        "ready_for_live": False,
        "execution_simulated": False,
        "model_validated": False,
        "policy": policy.model_dump(mode="json"),
        "dataset": {"source": manifest.source, "notes": manifest.notes, "sha256": dataset.hashes},
        "code_sha256": code_digest(),
        "candidate_count": len(ranked),
        "rows": rows,
        "quality": {
            "declared_completed_sessions": len(sessions),
            "ignored_future_rows": ignored_future,
            "unavailable_rows": unavailable,
            "window_resets_after_gaps": gaps,
            "calendar_age_days": (as_of.astimezone(IST).date() - latest).days if latest else None,
        },
        "limitations": [
            "Gross analytical total returns include reviewed period benefits before fees and tax.",
            "The index assumes same-close reinvestment and ignores payment/settlement delays.",
            "A screen is not a trade, forecast, backtest or approved investment model.",
            "No daily OHLC path or executable order/fill is inferred.",
            "Source, universe and basis review are assertions, not external verification.",
            "Latest session is the latest declared completed date; review calendar completeness.",
        ],
    }


def write_analysis(
    dataset: DailyDataset, policy: DailyPolicy, as_of: datetime, output: Path
) -> dict[str, Any]:
    from trading_agent.daily_research.dashboard import render

    if output.exists() or output.resolve().is_relative_to(dataset.directory):
        raise ValueError("daily output must be a new directory outside its source bundle")
    result = analyze(dataset, policy, as_of)
    output.mkdir(parents=True, mode=0o700)
    artifacts = {
        "report.json": json.dumps(result, indent=2, sort_keys=True) + "\n",
        "index.html": render(result),
        "report.md": "# Daily research screen\n\n"
        + f"As of {result['as_of']}; latest declared completed session "
        + f"{result['latest_reviewed_completed_session']}.\n\n"
        + f"Research candidates: {result['candidate_count']}. Execution simulated: false.\n\n"
        + "".join("- " + item + "\n" for item in result["limitations"]),
    }
    hashes = {}
    import hashlib

    for name, content in artifacts.items():
        with os.fdopen(
            os.open(output / name, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "w"
        ) as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        hashes[name] = hashlib.sha256(content.encode()).hexdigest()
    if dataset.fingerprints() != dataset.hashes:
        raise RuntimeError("daily input changed during reporting; no completed manifest written")
    with os.fdopen(
        os.open(output / "manifest.json", os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "w"
    ) as file:
        file.write(
            json.dumps(
                {
                    "schema_version": 1,
                    "state": "finished",
                    "sha256": hashes,
                    "ready_for_live": False,
                },
                indent=2,
            )
            + "\n"
        )
        file.flush()
        os.fsync(file.fileno())
    return result
