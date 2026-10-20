"""Invented daily data: winners, exclusions, gaps, illiquidity and reviewed benefits."""

import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from trading_agent.daily_research.analysis import DailyPolicy, write_analysis
from trading_agent.daily_research.dataset import DailyBar, DailyDataset, DailyManifest
from trading_agent.market_data.calendar import IST

D = Decimal


def create_daily_demo(directory: Path, *, sessions: int = 90) -> datetime:
    directory.mkdir(parents=True, exist_ok=False, mode=0o700)
    days: list[date] = []
    day = date(2026, 5, 4)
    while len(days) < sessions:
        if day.weekday() < 5:
            days.append(day)
        day += timedelta(days=1)
    symbols = ["NSE:DECLINE", "NSE:EXITED", "NSE:GAPPED", "NSE:REENTRY", "NSE:THIN", "NSE:TREND"]
    memberships = []
    for symbol in symbols:
        memberships.append(
            {
                "symbol": symbol,
                "effective_session": days[0].isoformat(),
                "included": True,
                "known_at": datetime.combine(
                    days[0] - timedelta(days=1), time(12), IST
                ).isoformat(),
                "reference": "INVENTED original point-in-time membership",
            }
        )
    for symbol, index, included in (
        ("NSE:EXITED", 60, False),
        ("NSE:REENTRY", 35, False),
        ("NSE:REENTRY", 75, True),
    ):
        if index < len(days):
            memberships.append(
                {
                    "symbol": symbol,
                    "effective_session": days[index].isoformat(),
                    "included": included,
                    "known_at": datetime.combine(
                        days[index] - timedelta(days=1), time(12), IST
                    ).isoformat(),
                    "reference": "INVENTED historical universe change",
                }
            )
    manifest = DailyManifest.model_validate(
        {
            "source": "INVENTED daily research fixture",
            "notes": "Weekdays/prices/benefits are invented; no market or execution evidence.",
            "synthetic": True,
            "sessions": [
                {
                    "day": day.isoformat(),
                    "open": "09:15",
                    "close": "15:30",
                    "source": "INVENTED calendar; not actual holidays",
                }
                for day in days
            ],
            "universe": memberships,
        }
    )
    (directory / "manifest.json").write_text(manifest.model_dump_json(indent=2) + "\n")
    previous = {symbol: D(500) for symbol in symbols}
    with (directory / "daily.jsonl").open("x") as file:
        for index, day in enumerate(days):
            for symbol in symbols:
                factor = 2 if symbol == "NSE:TREND" and index == 35 else 1
                cash = D(2) if symbol == "NSE:TREND" and index == 60 else D(0)
                close = (
                    (
                        previous[symbol] * (D(".995") if symbol == "NSE:DECLINE" else D("1.003"))
                        - cash
                    )
                    / factor
                ).quantize(D(".0001"))
                previous[symbol] = close
                if symbol == "NSE:GAPPED" and index in (31, sessions - 1):
                    continue
                closed = datetime.combine(day, time(15, 30), IST)
                bar = DailyBar(
                    symbol=symbol,
                    session=day,
                    open=close,
                    high=(close * D("1.01")).quantize(D(".0001")),
                    low=(close * D(".99")).quantize(D(".0001")),
                    close=close,
                    volume=100 if symbol == "NSE:THIN" else 100000,
                    price_available_at=closed + timedelta(minutes=10),
                    basis_reviewed_at=closed + timedelta(minutes=5),
                    basis_reference="INVENTED complete period benefit review",
                    share_numerator=factor,
                    share_denominator=1,
                    cash_per_previous_share=cash,
                )
                file.write(bar.model_dump_json() + "\n")
    return datetime.combine(days[-1], time(16), IST)


def daily_research_demo(directory: Path) -> dict[str, Any]:
    directory.mkdir(parents=True, exist_ok=False, mode=0o700)
    as_of = create_daily_demo(directory / "dataset")
    result = write_analysis(
        DailyDataset(directory / "dataset"), DailyPolicy(), as_of, directory / "report"
    )
    (directory / "summary.json").write_text(
        json.dumps(
            {
                "synthetic": True,
                "as_of": result["as_of"],
                "candidate_count": result["candidate_count"],
                "statuses": {row["symbol"]: row["status"] for row in result["rows"]},
            },
            indent=2,
        )
        + "\n"
    )
    return result
