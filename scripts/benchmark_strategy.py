"""Measure completed-candle rule analysis without network, disk or fixture parsing."""

import argparse
import json
import platform
from datetime import date, datetime, time, timedelta
from decimal import Decimal as D
from pathlib import Path
from time import perf_counter_ns

from trading_agent.market_data.calendar import IST, SessionCalendar
from trading_agent.models import Candle, Instrument, Quote, utc
from trading_agent.strategy.rules import RuleStrategy, StrategySettings


def benchmark(samples=2000):
    days = [date(2026, 10, 20) + timedelta(days=i) for i in range((samples + 74) // 75)]
    calendar = SessionCalendar({day: (time(9, 15), time(15, 30)) for day in days})
    instrument = Instrument(symbol="NSE:DEMO", token=1, tick_size=D(".05"))
    results = {}
    for hypothesis in ("opening_range_breakout", "vwap_continuation"):
        strategy = RuleStrategy(StrategySettings(hypothesis=hypothesis), calendar)
        elapsed, emitted = [], 0
        for index in range(samples):
            day, minute = days[index // 75], index % 75
            start = utc(datetime.combine(day, time(9, 15), IST) + timedelta(minutes=minute * 5))
            end = start + timedelta(minutes=5)
            close = D(500 if minute < 13 else 501)
            candle = Candle(
                symbol="NSE:DEMO",
                start=start,
                minutes=5,
                open=close,
                high=close + D(".5"),
                low=close - D(".5"),
                close=close,
                volume=5000 if minute == 13 else 2000,
            )
            quote = Quote(
                symbol="NSE:DEMO",
                token=1,
                exchange_time=end,
                received_time=end,
                last=close,
                bid=close,
                ask=close + D(".05"),
                bid_size=100,
                ask_size=100,
                volume=2000 * (minute + 1) + (3000 if minute >= 13 else 0),
            )
            before = perf_counter_ns()
            result = strategy.evaluate(
                candle, now=end, quote=quote, instrument=instrument, connected=True
            )
            elapsed.append(perf_counter_ns() - before)
            emitted += int(result.candidate is not None)
        elapsed.sort()
        results[hypothesis] = {
            "samples": samples,
            "candidates": emitted,
            "p50_ms": elapsed[len(elapsed) // 2] / 1e6,
            "p95_ms": elapsed[min(len(elapsed) - 1, int(len(elapsed) * 0.95))] / 1e6,
            "p99_ms": elapsed[min(len(elapsed) - 1, int(len(elapsed) * 0.99))] / 1e6,
        }
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "rules": results,
        "limitations": "Synthetic single-symbol completed-candle evaluation; "
        "excludes Pydantic input construction, input decoding, disk, risk execution and network",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=2000)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 100 <= args.samples <= 100000:
        parser.error("use 100 to 100000 samples")
    result = benchmark(args.samples)
    serialized = json.dumps(result, indent=2) + "\n"
    print(serialized, end="")
    if args.output:
        args.output.write_text(serialized)
