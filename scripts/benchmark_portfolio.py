"""Populated read-only contribution preview and durable confirm/fill latency, separately."""

import argparse
import json
import math
import platform
import tempfile
from datetime import datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from time import perf_counter_ns

from trading_agent.execution.delivery import HoldingReview
from trading_agent.execution.paper_broker import PaperBroker
from trading_agent.market_data.calendar import IST, SessionCalendar
from trading_agent.models import Instrument, Quote
from trading_agent.persistence.database import Database
from trading_agent.portfolio.contracts import Approval, Contribution
from trading_agent.portfolio.service import confirm, preview
from trading_agent.settings import Settings

D = Decimal
BASE_PRICE = D(500)


def quantiles(values: list[float]) -> dict[str, float]:
    values.sort()
    return {
        "p50_ms": values[math.ceil(len(values) * 0.5) - 1],
        "p95_ms": values[math.ceil(len(values) * 0.95) - 1],
        "p99_ms": values[math.ceil(len(values) * 0.99) - 1],
        "max_ms": values[-1],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=1000)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if not 100 <= args.samples <= 10000:
        parser.error("use 100..10000 samples")
    with tempfile.TemporaryDirectory(prefix="portfolio-benchmark-") as folder:
        settings = Settings.load("config/long-term.toml").model_copy(
            update={"database": Path(folder) / "paper.sqlite3"}
        )
        db = Database(settings.database, settings.starting_cash)
        now = datetime(2026, 10, 20, 10, tzinfo=IST)
        calendar = SessionCalendar(
            {now.date(): (time(9, 15), time(15, 30))}, {now.date(): "INVENTED benchmark session"}
        )
        e = PaperBroker(db, settings, calendar, recovery_time=now)
        e.register([Instrument(symbol="NSE:DEMO", token=1, tick_size=D(".05"))])
        e.set_connected(True)
        e.review_holding(
            HoldingReview(
                symbol="NSE:DEMO",
                session_date=now.date(),
                no_corporate_action=True,
                reference="INVENTED clear benchmark basis",
            ),
            now,
        )
        index = 0

        def market(bid: Decimal = BASE_PRICE) -> None:
            nonlocal index, now
            index += 1
            now += timedelta(seconds=1)
            q = Quote(
                symbol="NSE:DEMO",
                token=1,
                exchange_time=now,
                received_time=now,
                last=bid,
                bid=bid,
                ask=bid + D(".1"),
                bid_size=100,
                ask_size=100,
                volume=index * 100,
                source="replay",
            )
            e.ingest(q, now)

        try:
            for _ in range(1000):
                market()
            timings = []
            for i in range(args.samples):
                r = Contribution(
                    intent_id=f"preview-{i}",
                    symbol="NSE:DEMO",
                    budget=D(2000),
                    stop=D(490),
                    target=D(600),
                    reference="invented timing",
                )
                start = perf_counter_ns()
                result = preview(e, r, now)
                timings.append((perf_counter_ns() - start) / 1e6)
                assert result["decision"]["allowed"]
            executions = []
            for i in range(20):
                r = Contribution(
                    intent_id=f"base-{i}",
                    symbol="NSE:DEMO",
                    budget=D(2000),
                    stop=D(490),
                    target=D(600),
                    reference="invented base lot",
                )
                p = preview(e, r, now)
                confirm(e, Approval(request=r, preview_sha256=p["preview_sha256"]), now)
                market()
                add = Contribution(
                    intent_id=f"add-{i}",
                    symbol="NSE:DEMO",
                    budget=D(1000),
                    reference="invented addition timing",
                )
                p = preview(e, add, now)
                start = perf_counter_ns()
                confirm(e, Approval(request=add, preview_sha256=p["preview_sha256"]), now)
                market()
                executions.append((perf_counter_ns() - start) / 1e6)
                e.exit_holding("NSE:DEMO", now)
                market(D(550))
                market()
            with db.transaction() as tx:
                db.reconcile(tx)
            result = {
                "python": platform.python_version(),
                "platform": platform.platform(),
                "synthetic": True,
                "populated_quotes": 1000,
                "preview_samples": args.samples,
                "preview": quantiles(timings),
                "confirm_fill_samples": 20,
                "confirm_fill": quantiles(executions),
                "includes": (
                    "preview: lock/SQLite read transaction, exact sizing/risk/hash; "
                    "confirm/fill: revalidation, FULL durable approval/order/fill, "
                    "quote/watch accounting"
                ),
                "excludes": (
                    "initialization, warmup, baseline purchases/exits, network, browser and Pi"
                ),
            }
            if args.output:
                with args.output.open("x") as file:
                    file.write(json.dumps(result, indent=2) + "\n")
            print(json.dumps(result, indent=2))
        finally:
            db.close()


if __name__ == "__main__":
    main()
