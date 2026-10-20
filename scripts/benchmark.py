"""Reproducible local measurements; no broker credentials or network required."""

import argparse
import json
import platform
import sqlite3
import tempfile
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal as D
from pathlib import Path
from time import perf_counter_ns

from trading_agent.execution.paper_broker import PaperBroker
from trading_agent.features.indicators import Indicators
from trading_agent.market_data.calendar import SessionCalendar
from trading_agent.models import Candle, Instrument, Quote
from trading_agent.persistence.database import Database
from trading_agent.settings import Settings


def summarize(values):
    ordered = sorted(values)
    return {
        "count": len(values),
        "p50_ms": ordered[len(ordered) // 2] / 1e6,
        "p95_ms": ordered[min(len(ordered) - 1, int(len(ordered) * 0.95))] / 1e6,
        "p99_ms": ordered[min(len(ordered) - 1, int(len(ordered) * 0.99))] / 1e6,
    }


def benchmark(samples=2000):
    start = datetime(2026, 10, 20, 4, 30, tzinfo=UTC)
    feature_times, ingest_times = [], []
    indicator = Indicators()
    for index in range(samples):
        candle = Candle(
            symbol="NSE:DEMO",
            start=start + timedelta(minutes=5 * index),
            minutes=5,
            open=D(500),
            high=D(501),
            low=D(499),
            close=D(500),
            volume=100,
        )
        before = perf_counter_ns()
        indicator.update(candle)
        feature_times.append(perf_counter_ns() - before)
    with tempfile.TemporaryDirectory(prefix="agentic-benchmark-") as directory:
        settings = Settings(database=Path(directory) / "bench.sqlite3")
        db = Database(settings.database, settings.starting_cash)
        try:
            engine = PaperBroker(
                db, settings, SessionCalendar({date(2026, 10, 20): (time(9, 15), time(15, 30))})
            )
            engine.register([Instrument(symbol="NSE:DEMO", token=1, tick_size=D(".05"))])
            engine.set_connected(True)
            for index in range(samples):
                now = start + timedelta(seconds=index)
                quote = Quote(
                    symbol="NSE:DEMO",
                    token=1,
                    exchange_time=now,
                    received_time=now,
                    last=D(500),
                    bid=D("499.95"),
                    ask=D(500),
                    bid_size=100,
                    ask_size=100,
                    volume=1000 + index * 100,
                )
                before = perf_counter_ns()
                engine.ingest(quote, now)
                ingest_times.append(perf_counter_ns() - before)
        finally:
            db.close()
    return {
        "platform": platform.platform(),
        "python": platform.python_version(),
        "sqlite": sqlite3.sqlite_version,
        "durability": "WAL + synchronous=FULL",
        "indicator_update": summarize(feature_times),
        "quote_validation_journal_risk_commit": summarize(ingest_times),
        "limitations": "Synthetic single-symbol feed, empty portfolio; excludes network and ML",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=2000)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 100 <= args.samples <= 10000:
        parser.error("use 100 to 10000 samples")
    result = benchmark(args.samples)
    serialized = json.dumps(result, indent=2) + "\n"
    print(serialized, end="")
    if args.output:
        args.output.write_text(serialized)
