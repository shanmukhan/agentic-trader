"""Invented overnight, gap and corporate-action drills; never opens a service account."""

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from trading_agent.execution.delivery import HoldingReview
from trading_agent.execution.paper_broker import PaperBroker
from trading_agent.market_data.calendar import IST, SessionCalendar
from trading_agent.models import Candidate, Instrument, Quote
from trading_agent.paper.long_term_report import long_term_report
from trading_agent.persistence.database import Database
from trading_agent.settings import Settings

START = datetime(2026, 10, 20, 4, 30, tzinfo=UTC)


def delivery_review(engine: PaperBroker, now: datetime, *, clear: bool = True) -> None:
    engine.review_holding(
        HoldingReview(
            symbol="NSE:DEMO",
            session_date=now.astimezone(IST).date(),
            no_corporate_action=clear,
            reference="INVENTED fixture: no market acceptance",
        ),
        now,
    )


def delivery_quote(
    now: datetime, *, bid: str = "500", depth: int = 100, volume: int = 1000
) -> Quote:
    return Quote(
        symbol="NSE:DEMO",
        token=1,
        exchange_time=now,
        received_time=now,
        last=Decimal(bid),
        bid=Decimal(bid),
        ask=Decimal(bid) + Decimal(".05"),
        bid_size=depth,
        ask_size=depth,
        volume=volume,
        source="replay",
    )


def open_delivery_demo(directory: Path) -> PaperBroker:
    directory.mkdir(parents=True, exist_ok=False, mode=0o700)
    calendar_path = directory / "sessions.csv"
    days = [date(2026, 10, 20) + timedelta(days=offset) for offset in (0, 1, 2, 3, 6)]
    calendar_path.write_text(
        "date,open,close,source\n"
        + "".join(day.isoformat() + ",09:15,15:30,invented demonstration session\n" for day in days)
    )
    settings = Settings.load("config/long-term.toml").model_copy(
        update={
            "database": (directory / "paper.sqlite3").resolve(),
            "calendar": calendar_path.resolve(),
            "stream_tokens": (1,),
        }
    )
    # Never copy an operator token inherited from the shell into the demo or config.
    from pydantic import SecretStr

    settings = settings.model_copy(update={"operator_token": SecretStr("")})
    values = settings.model_dump(mode="json", exclude={"operator_token"})
    (directory / "account.toml").write_text(
        "".join(key + " = " + json.dumps(value) + "\n" for key, value in values.items())
    )
    db = Database(settings.database, settings.starting_cash)
    try:
        engine = PaperBroker(db, settings, SessionCalendar.load(calendar_path), recovery_time=START)
        with db.transaction() as tx:
            db.set(tx, "long_term_demo", "true")
        engine.register([Instrument(symbol="NSE:DEMO", token=1, tick_size=Decimal(".05"))])
        engine.set_connected(True)
        delivery_review(engine, START)
        engine.ingest(delivery_quote(START), START)
        order = engine.submit(
            Candidate(
                intent_id="overnight-entry",
                symbol="NSE:DEMO",
                stop=Decimal("490"),
                target=Decimal("600"),
                decision_time=START,
                reason="INVENTED overnight lifecycle drill",
            ),
            START,
        )
        if order["state"] != "ACCEPTED":
            raise RuntimeError("synthetic delivery entry failed")
        engine.ingest(
            delivery_quote(START + timedelta(seconds=1), volume=1100), START + timedelta(seconds=1)
        )
        return engine
    except BaseException:
        db.close()
        raise


def long_term_demo(directory: Path) -> dict[str, Any]:
    directory.mkdir(parents=True, exist_ok=False, mode=0o700)
    summary = {}
    for name in ("overnight_restart", "opening_gap", "corporate_action"):
        engine = open_delivery_demo(directory / name)
        try:
            engine.poll(START.replace(hour=9, minute=45))
            if not engine.snapshot(START.replace(hour=9, minute=45))["positions"]:
                raise RuntimeError("long-term holding was incorrectly flattened")
            if name == "overnight_restart":
                friday = START + timedelta(days=3)
                delivery_review(engine, friday)
                engine.ingest(delivery_quote(friday, bid="520"), friday)
                engine.poll(START + timedelta(days=4))
                monday = START + timedelta(days=6)
                delivery_review(engine, monday)
                engine.ingest(delivery_quote(monday, bid="530"), monday)
                engine.exit_holding("NSE:DEMO", monday)
                partial = monday + timedelta(seconds=1)
                engine.ingest(delivery_quote(partial, bid="530", depth=3, volume=1100), partial)
                settings, calendar = engine.settings, engine.calendar
                engine.db.close()
                reopened = Database(settings.database, settings.starting_cash)
                try:
                    engine = PaperBroker(reopened, settings, calendar, recovery_time=partial)
                except BaseException:
                    reopened.close()
                    raise
                engine.poll(partial)
                engine.set_connected(True)
                now = monday + timedelta(seconds=2)
                engine.ingest(delivery_quote(now, bid="530", volume=1200), now)
            elif name == "opening_gap":
                now = START + timedelta(days=1)
                delivery_review(engine, now)
                engine.ingest(delivery_quote(now, bid="450"), now)
                now += timedelta(seconds=1)
                engine.ingest(delivery_quote(now, bid="450", volume=1100), now)
            else:
                now = START + timedelta(days=1)
                delivery_review(engine, now, clear=False)
                if engine.ingest(delivery_quote(now, bid="250"), now):
                    raise RuntimeError("unadjusted corporate-action price was accepted")
            snapshot = engine.snapshot(now)
            report = long_term_report(engine.db, directory / name / "evidence")
            summary[name] = {
                "cash": snapshot["cash"],
                "positions": len(snapshot["positions"]),
                "kill": snapshot["kill"],
                "dp_days": report["dp_days"],
                "quarantines": sorted(report["quarantines"]),
            }
        finally:
            engine.db.close()
    result = {"synthetic": True, "ready_for_live": False, "scenarios": summary}
    (directory / "summary.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    (directory / "summary.md").write_text(
        "# Synthetic long-term paper drills\n\n"
        "Invented lifecycle evidence only. No market model, broker access or live readiness.\n\n"
        "Verified overnight/weekend holding, partial-exit restart, "
        "opening-gap kill and persistent corporate-action quarantine.\n"
    )
    return result
