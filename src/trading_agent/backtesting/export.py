"""Export market data without starting an engine or cancelling source account orders."""

import heapq
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
            synthetic=origins != {"kite"},
            instruments=instruments,
            sessions=sessions,
            data_notes="Raw market-data export, not source-account order replay. "
            "Connection history "
            "is unavailable; quote gaps/freshness are checked. Historical candles are assumed "
            "available at close, not at their later download time. Fee history is not verified. "
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
                yield from selected_candles(Candle.model_validate_json(row[0]) for row in rows)

        def selected_candles(
            values: Iterator[Candle],
        ) -> Iterator[tuple[datetime, int, str, Event]]:
            previous: tuple[datetime, str] | None = None
            for candle in values:
                if candle.symbol not in symbols or candle.start < start:
                    continue
                available = candle.start + timedelta(minutes=5)
                if available >= end:
                    continue
                key = available, candle.symbol
                if previous is not None and key <= previous:
                    raise ValueError("export candles must be sorted and unique by start,symbol")
                previous = key
                event = CandleEvent(time=available, candle=candle)
                counts["candle"] += 1
                yield available, 1, candle.symbol, event

        def events() -> Iterator[Event]:
            yield ConnectionEvent(time=start, connected=True)
            # Explicit key prevents comparing pydantic events at tied timestamps.
            for _, _, _, event in heapq.merge(quotes(), candles(), key=lambda item: item[:2]):
                yield event
            if not all(counts.values()):
                raise ValueError(
                    "export requires both five-minute candles AND observed quote events"
                )
            yield ClockEvent(time=end)

        write_bundle(output, manifest, events())
    return counts
