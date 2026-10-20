"""Populated paper pipeline, partial fills, risk, telemetry and FULL durable writes."""

import argparse
import json
import platform
from datetime import timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from time import perf_counter_ns

from trading_agent.paper.demo import SIGNAL, demo_quote, open_demo_feed, prepare_signal


def benchmark(samples: int) -> dict:
    with TemporaryDirectory(prefix="paper-benchmark-") as temporary:
        feed = open_demo_feed(Path(temporary))
        try:
            prepare_signal(feed)
            elapsed = []
            for index in range(samples):
                now = SIGNAL + timedelta(seconds=index + 1)
                quote = demo_quote(now, bid="501", ask_size=1, volume=33100 + 100 * index)
                before = perf_counter_ns()
                feed.on_quote(quote, now)
                if index % 60 == 0:
                    feed.tick(now, force_telemetry=True)
                elapsed.append((perf_counter_ns() - before) / 1e6)
            with feed.engine.db.transaction() as tx:
                feed.engine.db.reconcile(tx)
                fills = tx.execute("SELECT count(*) FROM fills").fetchone()[0]
            holdings = feed.engine.snapshot(now)["positions"]
            if not holdings or fills < 2:
                raise RuntimeError("benchmark did not exercise partial fills and a held position")
            elapsed.sort()
            return {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "durability": "SQLite WAL + synchronous=FULL",
                "samples": samples,
                "partial_fill_count": fills,
                "held_quantity": holdings[0]["quantity"],
                **{
                    f"p{p}_ms": elapsed[min(samples - 1, int(samples * p / 100))]
                    for p in (50, 95, 99)
                },
                "limitations": "Synthetic one-symbol paper pipeline with a populated account; "
                "includes "
                "quote/risk/accounting, observed performance and periodic telemetry commits. "
                "Excludes object construction, socket parsing, callback contention, history HTTP, "
                "network and target-device behavior. No empirical fill calibration.",
            }
        finally:
            feed.engine.db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--samples", type=int, default=2000)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 100 <= args.samples <= 10000:
        parser.error("use 100 to 10000 samples")
    serialized = json.dumps(benchmark(args.samples), indent=2) + "\n"
    print(serialized, end="")
    if args.output:
        args.output.write_text(serialized)
