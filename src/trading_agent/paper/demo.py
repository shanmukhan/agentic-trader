"""Synthetic normal, outage, silence and unclean-restart drills. No credentials or I/O feed."""

import json
from datetime import date, datetime, time, timedelta
from decimal import Decimal as D
from pathlib import Path
from typing import Any

from trading_agent.execution.paper_broker import PaperBroker
from trading_agent.market_data.calendar import IST, SessionCalendar
from trading_agent.models import Candle, Instrument, Quote, utc
from trading_agent.paper.config import FeedSettings, feed_identity
from trading_agent.paper.report import paper_report
from trading_agent.paper.runtime import PaperFeed
from trading_agent.persistence.database import Database
from trading_agent.settings import Settings
from trading_agent.strategy.rules import StrategySettings

OPEN = utc(datetime(2026, 10, 20, 9, 15, tzinfo=IST))
WARM = OPEN + timedelta(minutes=70)
SIGNAL = WARM + timedelta(minutes=5)
INSTRUMENT = Instrument(symbol="NSE:DEMO", token=1, tick_size=D(".05"))


def demo_quote(
    now: datetime,
    *,
    bid: str = "500",
    ask_size: int = 100,
    bid_size: int = 100,
    volume: int = 28000,
) -> Quote:
    price = D(bid)
    return Quote(
        symbol=INSTRUMENT.symbol,
        token=1,
        exchange_time=now,
        received_time=now,
        last=price,
        bid=price,
        ask=price + D(".05"),
        bid_size=bid_size,
        ask_size=ask_size,
        volume=volume,
    )


def warmup() -> list[Candle]:
    return [
        Candle(
            symbol=INSTRUMENT.symbol,
            start=OPEN + timedelta(minutes=5 * i),
            minutes=5,
            open=D(500),
            high=D("500.50"),
            low=D("499.50"),
            close=D(500),
            volume=2000,
        )
        for i in range(14)
    ]


def signal_candle() -> Candle:
    return Candle(
        symbol=INSTRUMENT.symbol,
        start=WARM,
        minutes=5,
        open=D(500),
        high=D("501.50"),
        low=D("499.50"),
        close=D(501),
        volume=5000,
    )


def open_demo_feed(directory: Path, now: datetime = WARM) -> PaperFeed:
    policy = Settings(database=directory / "paper.sqlite3")
    calendar = SessionCalendar(
        {date(2026, 10, 20): (time(9, 15), time(15, 30))},
        {date(2026, 10, 20): "invented paper runtime fixture"},
    )
    config, strategy = FeedSettings(), StrategySettings()
    _, signature = feed_identity([INSTRUMENT], strategy, config, None, True)
    db = Database(policy.database, policy.starting_cash)
    try:
        engine = PaperBroker(db, policy, calendar, recovery_time=now, automation=signature)
        engine.register([INSTRUMENT])
        return PaperFeed(
            engine,
            instruments=[INSTRUMENT],
            strategy=strategy,
            settings=config,
            now=now,
            synthetic=True,
        )
    except BaseException:
        db.close()
        raise


def prepare_signal(feed: PaperFeed, *, candle: Candle | None = None) -> None:
    selected = candle or signal_candle()
    feed.connection(True, WARM)
    feed.on_quote(demo_quote(WARM), WARM)
    feed.on_candles(warmup(), WARM)
    feed.arm(WARM)
    for second in range(1, 301):
        now = WARM + timedelta(seconds=second)
        feed.on_quote(
            demo_quote(
                now,
                bid=str(selected.close) if second == 300 else "500",
                volume=28000 + selected.volume * second // 300,
            ),
            now,
        )
        if second % 60 == 0:
            feed.tick(now)
    feed.on_candles([selected], SIGNAL)


def run_paper_demo(directory: Path) -> dict[str, Any]:
    directory.mkdir(parents=True, exist_ok=False, mode=0o700)
    results = {}
    for scenario in ("partial_fills", "disconnect", "silence", "restart"):
        folder = directory / scenario
        feed = open_demo_feed(folder)
        try:
            prepare_signal(feed)
            entry = next(order for order in feed.engine.orders() if order["side"] == "BUY")
            if entry["state"] != "ACCEPTED":
                raise RuntimeError("synthetic paper drill failed to produce an accepted proposal")
            if scenario == "restart":
                # An unclean process loss: deliberately omit runtime shutdown to exercise recovery.
                feed.engine.db.close()
                feed = open_demo_feed(folder, SIGNAL + timedelta(seconds=1))
                feed.connection(True, SIGNAL + timedelta(seconds=1))
                feed.on_quote(
                    demo_quote(SIGNAL + timedelta(seconds=2), bid="501", volume=33200),
                    SIGNAL + timedelta(seconds=2),
                )
                if feed.armed or any(
                    order["state"] in {"ACCEPTED", "PARTIAL"} for order in feed.engine.orders()
                ):
                    raise RuntimeError("restart revived an old paper entry")
                ended = SIGNAL + timedelta(seconds=3)
            else:
                now = SIGNAL + timedelta(seconds=1)
                feed.on_quote(
                    demo_quote(
                        now,
                        bid="501",
                        ask_size=2 if scenario == "partial_fills" else 100,
                        volume=33100,
                    ),
                    now,
                )
                if scenario == "partial_fills":
                    for second, bid, depth in (
                        (2, "501", 100),
                        (3, "508", 100),
                        (4, "508", 1),
                        (5, "508", 100),
                    ):
                        now = SIGNAL + timedelta(seconds=second)
                        feed.on_quote(
                            demo_quote(
                                now,
                                bid=bid,
                                ask_size=2,
                                bid_size=depth,
                                volume=33000 + 100 * second,
                            ),
                            now,
                        )
                    ended = now
                else:
                    interrupted = SIGNAL + timedelta(seconds=2 if scenario == "disconnect" else 7)
                    if scenario == "disconnect":
                        feed.connection(False, interrupted)
                    else:
                        feed.tick(interrupted, force_telemetry=True)
                    if not feed.engine.snapshot(interrupted)["positions"]:
                        raise RuntimeError("outage fabricated a liquidation")
                    resumed = interrupted + timedelta(seconds=1)
                    if scenario == "disconnect":
                        feed.connection(True, resumed)
                    feed.on_quote(demo_quote(resumed, bid="500", volume=34000), resumed)
                    if feed.armed or feed.engine.snapshot(resumed)["positions"]:
                        raise RuntimeError(
                            "recovery failed to fill a queued exit or rearmed entries"
                        )
                    ended = resumed + timedelta(seconds=1)
            feed.close(ended)
            report = paper_report(feed.engine.db, folder / "evidence")
            results[scenario] = {
                "cash": report["cash"],
                "metrics": report["metrics"],
                "incidents": report["incident_counts"],
                "gates": report["gates"],
            }
        finally:
            feed.engine.db.close()
    summary = {
        "synthetic": True,
        "ready_for_live": False,
        "directory": str(directory),
        "scenarios": results,
    }
    (directory / "summary.json").write_text(json.dumps(summary, indent=2, default=str) + "\n")
    (directory / "summary.md").write_text(
        "# Synthetic paper-feed drills\n\n"
        "Invented data and virtual money. No empirical validation or live readiness.\n\n"
        "Verified: partial entry/exit, disconnect with holdings, silent quote feed, "
        "and unclean pending-entry restart. "
        "Each scenario retains a ledger and evidence/report.md.\n"
    )
    return summary
