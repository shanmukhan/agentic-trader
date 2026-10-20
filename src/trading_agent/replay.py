"""Deterministic offline event runner; every time source comes from the fixture."""

import hashlib
import json
from collections.abc import Iterable
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from trading_agent.execution.paper_broker import PaperBroker
from trading_agent.market_data.calendar import SessionCalendar
from trading_agent.market_data.candles import CandleBuilder
from trading_agent.market_data.repository import store_candles
from trading_agent.models import Candidate, Instrument, Quote, stamp, utc
from trading_agent.persistence.database import Database
from trading_agent.settings import Settings


def run_events(engine: PaperBroker, events: Iterable[dict[str, Any]]) -> dict[str, Any]:
    builders = (CandleBuilder(1), CandleBuilder(5))
    previous: datetime | None = None
    for event in events:
        now = utc(datetime.fromisoformat(event["time"]))
        if previous and now < previous:
            raise ValueError("replay clock moved backward")
        kind = event["type"]
        if kind == "connection":
            if not isinstance(event["connected"], bool):
                raise ValueError("connected must be boolean")
            engine.set_connected(event["connected"])
        elif kind == "quote":
            quote = Quote.model_validate(event["quote"])
            if engine.ingest(quote, now):
                for builder in builders:
                    store_candles(engine.db, builder.update(quote), now)
        elif kind == "candidate":
            engine.submit(Candidate.model_validate(event["candidate"]), now)
        elif kind == "kill":
            engine.kill(now)
        elif kind != "clock":
            raise ValueError("unknown replay event type")
        engine.poll(now)
        previous = now
    if previous is None:
        raise ValueError("empty replay")
    with engine.db.transaction() as tx:
        journal = [dict(row) for row in tx.execute("SELECT * FROM events ORDER BY seq")]
        fills = [dict(row) for row in tx.execute("SELECT * FROM fills ORDER BY seq")]
    return {
        "snapshot": engine.snapshot(previous),
        "orders": engine.orders(),
        "fills": fills,
        "journal_sha256": hashlib.sha256(json.dumps(journal, sort_keys=True).encode()).hexdigest(),
    }


def demo(directory: Path) -> dict[str, Any]:
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    path = directory / "demo.sqlite3"
    if path.exists():
        raise ValueError("demo directory already has an account; select a new directory")
    settings = Settings(database=path)
    db = Database(path, settings.starting_cash)
    calendar = SessionCalendar({date(2026, 10, 20): (time(9, 15), time(15, 30))})
    engine = PaperBroker(db, settings, calendar)
    engine.register([Instrument(symbol="NSE:DEMO", token=1, tick_size=Decimal("0.05"))])
    start = datetime(2026, 10, 20, 4, 30, tzinfo=UTC)
    events: list[dict[str, Any]] = [{"type": "connection", "time": stamp(start), "connected": True}]
    for second, bid, ask in (
        (0, "499.95", "500"),
        (1, "499.95", "500"),
        (2, "499.95", "500"),
        (3, "511", "511.05"),
        (4, "511", "511.05"),
    ):
        now = start + timedelta(seconds=second)
        quote = Quote(
            symbol="NSE:DEMO",
            token=1,
            exchange_time=now,
            received_time=now,
            last=Decimal(ask),
            bid=Decimal(bid),
            ask=Decimal(ask),
            bid_size=100,
            ask_size=100,
            volume=1000 + second * 100,
        )
        events.append({"type": "quote", "time": stamp(now), "quote": quote.model_dump(mode="json")})
        if second == 0:
            candidate = Candidate(
                intent_id="demo-entry",
                symbol="NSE:DEMO",
                stop=Decimal("495"),
                target=Decimal("510"),
                decision_time=now,
                reason="synthetic functional demonstration",
            )
            events.append(
                {
                    "type": "candidate",
                    "time": stamp(now),
                    "candidate": candidate.model_dump(mode="json"),
                }
            )
    try:
        result = run_events(engine, events)
        (directory / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
        (directory / "report.json").write_text(json.dumps(result, indent=2) + "\n")
        return result
    finally:
        db.close()
