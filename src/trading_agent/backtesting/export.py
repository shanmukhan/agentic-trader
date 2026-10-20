"""Export market data without starting an engine or cancelling source account orders."""

import heapq
import json
from collections.abc import Iterator
from datetime import datetime, timedelta
from pathlib import Path

from trading_agent.backtesting.dataset import (
    CandleEvent,
    ClockEvent,
    ConnectionEvent,
    Event,
    Manifest,
    QuoteEvent,
    Session,
    bounded_lines,
    write_bundle,
)
from trading_agent.market_data.calendar import IST, SessionCalendar
from trading_agent.models import Candle, Instrument, Quote, stamp, utc
from trading_agent.persistence.database import Database


def export_dataset(
    db: Database,
    calendar: SessionCalendar,
    *,
    start: datetime,
    end: datetime,
    symbols: tuple[str, ...],
    output: Path,
    source: str,
    candle_file: Path | None = None,
) -> dict[str, int]:
    start, end = utc(start), utc(end)
    if not start < end or not symbols or len(set(symbols)) != len(symbols) or len(symbols) > 10:
        raise ValueError("provide a positive range and one to ten unique symbols")
    placeholders = ",".join("?" for _ in symbols)
    with db.transaction() as tx:
        automated = (
            tx.execute("SELECT value FROM meta WHERE key='automation_hash'").fetchone() is not None
        )
        if automated and candle_file:
            raise ValueError("automated exports require recorded candle availability; no override")
        availability: dict[tuple[str, datetime], datetime] = {}
        auto_synthetic = False
        if automated:
            declaration = tx.execute(
                "SELECT payload FROM events WHERE kind='automation_start' LIMIT 1"
            ).fetchone()
            if declaration is None:
                raise RuntimeError("missing automation provenance")
            auto_synthetic = json.loads(declaration[0])["synthetic"]
            for row in tx.execute(
                "SELECT entity,time,payload FROM events WHERE kind='feed_evaluation' ORDER BY seq"
            ):
                payload = json.loads(row["payload"])
                key = row["entity"], datetime.fromisoformat(payload["candle_end"])
                availability.setdefault(key, datetime.fromisoformat(row["time"]))
        instruments = tuple(
            Instrument(symbol=row["symbol"], token=row["token"], tick_size=row["tick"])
            for row in tx.execute(
                f"SELECT * FROM instruments WHERE symbol IN ({placeholders}) ORDER BY symbol",
                symbols,
            )
        )
        if len(instruments) != len(symbols):
            raise ValueError("export symbol is missing from the source catalog")
        sessions = tuple(
            Session(
                day=day,
                open=times[0],
                close=times[1],
                source=calendar.sources.get(day, "programmatic calendar; review provenance"),
            )
            for day, times in sorted(calendar.sessions.items())
            if start.astimezone(IST).date() <= day <= end.astimezone(IST).date()
        )
        origins = {
            row[0]
            for row in tx.execute(
                "SELECT DISTINCT json_extract(payload,'$.source') "
                "FROM events WHERE kind='quote' AND time>=? AND time<? "
                f"AND entity IN ({placeholders})",
                (stamp(start), stamp(end), *symbols),
            )
        }
        manifest = Manifest(
            source=source,
            synthetic=origins != {"kite"} or auto_synthetic,
            instruments=instruments,
            sessions=sessions,
            data_notes="Raw market-data export, not source-account order replay. "
            + (
                "Recorded connection history and first observed candle availability are preserved. "
                if automated
                else "Connection history is unavailable; quote gaps are checked. "
                "Historical candles are assumed available at close, not later download time. "
            )
            + "Fee history is not verified. "
            "Exclude corporate-action days and review point-in-time universe selection. "
            + (
                "External verified candle file supplied."
                if candle_file
                else "Stored source candles used."
            ),
        )
        counts = {"quote": 0, "candle": 0}

        def quotes() -> Iterator[tuple[datetime, int, str, Event]]:
            query = (
                "SELECT time,payload FROM events WHERE kind='quote' AND time>=? AND time<? "
                f"AND entity IN ({placeholders}) ORDER BY time,seq"
            )
            for row in tx.execute(query, (stamp(start), stamp(end), *symbols)):
                now = datetime.fromisoformat(row["time"])
                event = QuoteEvent(time=now, quote=Quote.model_validate_json(row["payload"]))
                counts["quote"] += 1
                yield now, 0, event.quote.symbol, event

        def candles() -> Iterator[tuple[datetime, int, str, Event]]:
            if candle_file:
                values = (
                    Candle.model_validate_json(line) for _, line in bounded_lines(candle_file)
                )
                yield from selected_candles(values)
            else:
                rows = tx.execute(
                    f"SELECT payload FROM candles WHERE minutes=5 AND symbol "
                    f"IN ({placeholders}) ORDER BY start,symbol",
                    symbols,
                )
                selected = selected_candles(Candle.model_validate_json(row[0]) for row in rows)
                if automated:
                    # Backfill can publish many old candles together. Receipt order, not start
                    # order, determines causal replay; preserve chronological bars within ties.
                    yield from sorted(
                        selected, key=lambda item: (item[0], item[3].candle.start, item[2])
                    )
                else:
                    yield from selected

        def selected_candles(
            values: Iterator[Candle],
        ) -> Iterator[tuple[datetime, int, str, CandleEvent]]:
            previous: tuple[datetime, str] | None = None
            for candle in values:
                if candle.symbol not in symbols or candle.start < start:
                    continue
                closed = candle.start + timedelta(minutes=5)
                if closed >= end:
                    continue
                key = closed, candle.symbol
                if previous is not None and key <= previous:
                    raise ValueError("export candles must be sorted and unique by start,symbol")
                previous = key
                if automated:
                    if (candle.symbol, closed) not in availability:
                        raise ValueError("stored candle has no recorded observation clock")
                    available = availability[candle.symbol, closed]
                else:
                    available = closed
                if available >= end:
                    continue
                event = CandleEvent(time=available, candle=candle)
                counts["candle"] += 1
                yield available, 1, candle.symbol, event

        def events() -> Iterator[Event]:
            connected = True
            if automated:
                last = tx.execute(
                    "SELECT payload FROM events WHERE kind='feed_connection' AND time<? "
                    "ORDER BY seq DESC LIMIT 1",
                    (stamp(start),),
                ).fetchone()
                connected = bool(last and json.loads(last[0])["connected"])
            yield ConnectionEvent(time=start, connected=connected)
            # Explicit key prevents comparing pydantic events at tied timestamps.
            for _, _, _, event in heapq.merge(
                connections(), quotes(), candles(), key=lambda item: item[:2]
            ):
                yield event
            if not all(counts.values()):
                raise ValueError(
                    "export requires both five-minute candles AND observed quote events"
                )
            yield ClockEvent(time=end)

        def connections() -> Iterator[tuple[datetime, int, str, Event]]:
            if automated:
                for row in tx.execute(
                    "SELECT time,payload FROM events WHERE kind='feed_connection' "
                    "AND time>=? AND time<? ORDER BY time,seq",
                    (stamp(start), stamp(end)),
                ):
                    now = datetime.fromisoformat(row["time"])
                    yield (
                        now,
                        -1,
                        "",
                        ConnectionEvent(
                            time=now, connected=json.loads(row["payload"])["connected"]
                        ),
                    )

        write_bundle(output, manifest, events())
    return counts
