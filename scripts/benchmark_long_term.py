"""Populated overnight-policy timing; synthetic data, SQLite FULL, no network."""

import argparse
import json
import math
import platform
import tempfile
from datetime import timedelta
from pathlib import Path
from time import perf_counter_ns

from trading_agent.corporate_actions.contracts import ActionBatch, digest
from trading_agent.corporate_actions.service import apply_batch
from trading_agent.paper.long_term_demo import (
    START,
    delivery_quote,
    delivery_review,
    open_delivery_demo,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=2000)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--corporate-actions",
        action="store_true",
        help="include unpaid dividend caches in held-account timing",
    )
    args = parser.parse_args()
    if not 100 <= args.samples <= 10000:
        parser.error("use 100..10000 observations within the invented session")
    with tempfile.TemporaryDirectory(prefix="long-term-benchmark-") as temporary:
        engine = open_delivery_demo(Path(temporary) / "account")
        try:
            base = START
            if args.corporate_actions:
                base += timedelta(days=1)
                delivery_review(engine, base, clear=False)
                with engine.db.transaction() as tx:
                    quarantine = json.loads(engine.db.get(tx, "lt_quarantine:NSE:DEMO"))
                batch = ActionBatch.model_validate(
                    {
                        "batch_id": "benchmark",
                        "symbol": "NSE:DEMO",
                        "quarantine_sha256": digest(quarantine),
                        "reviewed_at": base.isoformat(),
                        "reference": "INVENTED benchmark only",
                        "covers_all_actions": True,
                        "actions": [
                            {
                                "action_id": "benchmark-dividend",
                                "kind": "dividend",
                                "ex_date": base.date().isoformat(),
                                "record_date": base.date().isoformat(),
                                "announced_at": START.isoformat(),
                                "reference": "INVENTED dividend",
                                "per_share": "1",
                                "withholding": "0",
                                "payment_date": "2026-10-22",
                            }
                        ],
                    }
                )
                apply_batch(engine.db, engine.settings, engine.calendar, batch, base)
                delivery_review(engine, base)
            times = []
            for index in range(args.samples):
                now = base + timedelta(seconds=index + 2)
                quote = delivery_quote(now, volume=1200 + index * 100)
                start = perf_counter_ns()
                engine.ingest(quote, now)
                times.append((perf_counter_ns() - start) / 1_000_000)
            with engine.db.transaction() as tx:
                engine.db.reconcile(tx)
            values = sorted(times)
            report = {
                "samples": len(values),
                "python": platform.python_version(),
                "platform": platform.platform(),
                "architecture": platform.machine(),
                "p50_ms": values[math.ceil(len(values) * 0.50) - 1],
                "p95_ms": values[math.ceil(len(values) * 0.95) - 1],
                "p99_ms": values[math.ceil(len(values) * 0.99) - 1],
                "max_ms": values[-1],
                "synchronous": "FULL",
                "includes": "quote, reviews, held valuation, risk, durable clock/equity, journal",
                "excludes": "construction, parsing, callback contention, network/history and Pi",
                "held_shares": engine.snapshot(now)["positions"][0]["quantity"],
                "unpaid_dividend": engine.snapshot(now)["long_term"]["receivable"],
                "corporate_actions": args.corporate_actions,
            }
            if args.output:
                with args.output.open("x") as file:
                    file.write(json.dumps(report, indent=2) + "\n")
            print(json.dumps(report, indent=2))
        finally:
            engine.db.close()


if __name__ == "__main__":
    main()
