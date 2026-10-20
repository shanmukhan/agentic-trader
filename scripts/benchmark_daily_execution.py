"""Measure full durable delivery replay and cached causal daily screening separately."""

import argparse
import json
import math
import platform
import tempfile
from pathlib import Path
from time import perf_counter_ns

from trading_agent.daily_execution.contracts import DailyStrategy
from trading_agent.daily_execution.dataset import ExecutionDataset, QuoteEvent
from trading_agent.daily_execution.demo import create_execution_demo
from trading_agent.daily_execution.runner import run_daily
from trading_agent.daily_execution.timeline import DailyTimeline
from trading_agent.daily_research.dataset import DailyDataset
from trading_agent.settings import Settings


def summary(values: list[float]) -> dict[str, float]:
    ordered = sorted(values)
    return {
        "p50_ms": ordered[math.ceil(len(values) * 0.5) - 1],
        "p95_ms": ordered[math.ceil(len(values) * 0.95) - 1],
        "p99_ms": ordered[math.ceil(len(values) * 0.99) - 1],
        "max_ms": ordered[-1],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=10)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 5 <= args.samples <= 100:
        parser.error("use 5..100 samples")
    strategy, policy = DailyStrategy(), Settings.load("config/long-term.toml")
    with tempfile.TemporaryDirectory(prefix="daily-execution-benchmark-") as folder:
        root = Path(folder)
        daily, execution, _ = create_execution_demo(root / "inputs", sessions=3)
        timings = []
        for index in range(args.samples):
            start = perf_counter_ns()
            report = run_daily(
                ExecutionDataset(execution, DailyDataset(daily)),
                strategy=strategy,
                policy=policy,
                output=root / str(index),
            )
            timings.append((perf_counter_ns() - start) / 1_000_000)
        source = ExecutionDataset(execution, DailyDataset(daily))
        timeline = DailyTimeline(
            source.daily, {i.symbol for i in source.manifest.instruments}, strategy.screen
        )
        first = next(e for e in source.events() if isinstance(e, QuoteEvent))
        timeline.advance(first.time)
        screens = []
        for _ in range(1000):
            start = perf_counter_ns()
            timeline.screen(first.quote.symbol, first.time)
            screens.append((perf_counter_ns() - start) / 1_000_000)
        result = {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "synthetic": True,
            "sessions": 3,
            "symbols": 3,
            "daily_bars": 219,
            "quotes": 36,
            "completed_trades": report["metrics"]["completed_trades"],
            "replay_samples": args.samples,
            "replay": summary(timings),
            "cached_screen_samples": 1000,
            "cached_screen": summary(screens),
            "includes": (
                "replay: input parse/validation/hashes, FULL SQLite fills/reconcile, reports "
                "and artifact hashes; cached screen: warmed single-symbol metrics"
            ),
            "excludes": (
                "fixture creation, network, intratick events, ML fitting, label trials, "
                "real feed and Pi"
            ),
        }
        if args.output:
            with args.output.open("x") as file:
                file.write(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
