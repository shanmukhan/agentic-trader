from datetime import datetime, timedelta

from trading_agent.models import Candle, stamp
from trading_agent.persistence.database import Database


def store_candles(db: Database, candles: list[Candle], as_of: datetime) -> int:
    count = 0
    with db.transaction() as tx:
        for candle in candles:
            if not candle.completed or candle.start + timedelta(minutes=candle.minutes) > as_of:
                raise ValueError("historical candle is incomplete or in the future")
            existing = tx.execute(
                "SELECT payload FROM candles WHERE symbol=? AND start=? AND minutes=?",
                (candle.symbol, stamp(candle.start), candle.minutes),
            ).fetchone()
            if existing:
                if Candle.model_validate_json(existing[0]) != candle:
                    raise ValueError("conflicting candle revision requires review")
                continue
            tx.execute(
                "INSERT INTO candles VALUES (?,?,?,?)",
                (candle.symbol, stamp(candle.start), candle.minutes, candle.model_dump_json()),
            )
            count += 1
    return count


def load_candles(db: Database, symbol: str, minutes: int) -> list[Candle]:
    with db.transaction() as tx:
        return [
            Candle.model_validate_json(row[0])
            for row in tx.execute(
                "SELECT payload FROM candles WHERE symbol=? AND minutes=? ORDER BY start",
                (symbol, minutes),
            )
        ]
