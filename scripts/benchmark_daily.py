"""End-to-end offline daily parse/validation/analysis/hash timing on an invented bundle."""

import argparse
import json
import math
import platform
import tempfile
from pathlib import Path
from time import perf_counter_ns

from trading_agent.daily_research.analysis import DailyPolicy, analyze
from trading_agent.daily_research.dataset import DailyDataset
from trading_agent.daily_research.demo import create_daily_demo


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=30)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 5 <= args.samples <= 100:
        parser.error("use 5..100 samples")
    with tempfile.TemporaryDirectory(prefix="daily-analysis-benchmark-") as folder:
        path = Path(folder) / "daily"
        as_of = create_daily_demo(path)
        timings = []
        for _ in range(args.samples):
            start = perf_counter_ns()
            report = analyze(DailyDataset(path), DailyPolicy(), as_of)
            timings.append((perf_counter_ns() - start) / 1_000_000)
        values = sorted(timings)
        result = {
            "samples": len(values),
            "python": platform.python_version(),
            "platform": platform.platform(),
            "sessions": 90,
            "symbols": 6,
            "bars": 538,
            "p50_ms": values[math.ceil(len(values) * 0.5) - 1],
            "p95_ms": values[math.ceil(len(values) * 0.95) - 1],
            "p99_ms": values[math.ceil(len(values) * 0.99) - 1],
            "max_ms": values[-1],
            "candidate_count": report["candidate_count"],
            "includes": "loading, strict validation, universe/basis, ranking, input/Python hashes",
            "excludes": "input creation, HTML writing, network/history, execution and actual Pi",
        }
        if args.output:
            with args.output.open("x") as file:
                file.write(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
