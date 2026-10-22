"""Invented local chart inputs; these tests do not constitute broker/market acceptance."""

import json
import sqlite3
from datetime import datetime, timedelta
from decimal import Decimal as D

import pytest
from conftest import NOW

from trading_agent.api.analysis import BAR_LIMIT, _averages, analysis_snapshot
from trading_agent.daily_research.dataset import DailyDataset
from trading_agent.market_data.repository import store_candles
from trading_agent.models import Candle, stamp


def test_sma_keeps_exact_decimal_values_and_waits_for_full_window():
    closes = [D("9007199254740993.0001") + D(i) / 10000 for i in range(55)]
    bars = _averages([{"close": str(close)} for close in closes])
    assert bars[18]["sma20"] is None and bars[48]["sma50"] is None
    assert D(bars[19]["sma20"]) == sum(closes[:20]) / 20
    assert D(bars[54]["sma20"]) == sum(closes[-20:]) / 20
    assert D(bars[54]["sma50"]) == sum(closes[-50:]) / 50
    assert bars[54]["close"] == str(closes[54])


def test_daily_chart_filters_future_availability_and_incomplete_sessions(desk_factory):
    desk, _, directory = desk_factory()
    rows = [json.loads(row) for row in (directory / "daily.jsonl").read_text().splitlines()]
    first = next(row for row in rows if row["symbol"] == "NSE:DEMO")
    first["basis_reviewed_at"] = stamp(NOW + timedelta(hours=1))
    future = {**first, "session": NOW.date().isoformat()}
    future.update(
        price_available_at=stamp(NOW.replace(hour=11)),
        basis_reviewed_at=stamp(NOW.replace(hour=11)),
    )
    rows.append(future)
    (directory / "daily.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows))
    desk.research.dataset = DailyDataset(directory)
    view = analysis_snapshot(desk, NOW, symbol="NSE:DEMO")
    assert view["data_state"] == "available" and len(view["bars"]) == 3
    assert view["bars"][0]["close"] == "498"
    assert all(bar["session"] < NOW.date().isoformat() for bar in view["bars"])
    assert all(datetime.fromisoformat(bar["available_at"]) <= NOW for bar in view["bars"])
    assert view["source"]["synthetic"] and "not live quotes" in view["message"]
    assert view["quote"]["usable"]


def test_changed_daily_input_reports_unavailable_without_changing_account(desk_factory):
    desk, _, directory = desk_factory()
    with sqlite3.connect(desk.engine.settings.database) as db:
        before = list(db.iterdump())
    (directory / "daily.jsonl").write_text((directory / "daily.jsonl").read_text() + "\n")
    view = analysis_snapshot(desk, NOW, symbol="NSE:DEMO")
    assert view["data_state"] == "unavailable" and not view["bars"]
    assert "integrity" in view["message"] and not desk.engine.faulted
    assert desk.mode == "manual"
    with sqlite3.connect(desk.engine.settings.database) as db:
        assert list(db.iterdump()) == before
        assert D(db.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0]) == D(25000)


@pytest.mark.parametrize("minutes", [1, 5])
def test_minute_chart_is_bounded_and_excludes_unknown_volume_gaps_and_incomplete(
    desk_factory, minutes
):
    desk, _, _ = desk_factory()
    e = desk.engine
    end = NOW.replace(hour=4, minute=30)
    candles = [
        Candle(
            symbol="NSE:DEMO",
            start=end - timedelta(minutes=minutes * (365 - i)),
            minutes=minutes,
            open=D("500.0001") + D(i) / 10000,
            high=D("501"),
            low=D("499"),
            close=D("500.0001") + D(i) / 10000,
            volume=100 + i,
        )
        for i in range(365)
    ]
    store_candles(e.db, candles, end)
    with e.db.transaction() as tx:
        for index, quality in [(-1, "gap"), (-2, "unknown_initial_volume")]:
            bad = candles[index].model_copy(update={"quality": quality})
            tx.execute(
                "UPDATE candles SET payload=? WHERE symbol=? AND start=? AND minutes=?",
                (bad.model_dump_json(), bad.symbol, stamp(bad.start), minutes),
            )
        unfinished = candles[-3].model_copy(update={"completed": False})
        tx.execute(
            "UPDATE candles SET payload=? WHERE symbol=? AND start=? AND minutes=?",
            (unfinished.model_dump_json(), unfinished.symbol, stamp(unfinished.start), minutes),
        )
        future = candles[-1].model_copy(update={"start": end, "completed": False})
        tx.execute(
            "INSERT INTO candles VALUES (?,?,?,?)",
            (future.symbol, stamp(future.start), minutes, future.model_dump_json()),
        )
    view = analysis_snapshot(desk, end, symbol="NSE:DEMO", timeframe=f"{minutes}m")
    assert len(view["bars"]) == BAR_LIMIT and view["truncated"]
    assert view["excluded_candles"] == 3 and view["data_state"] == "available"
    assert view["source"]["synthetic"] is None
    assert "provenance is not recorded" in view["message"]
    assert view["bars"][-1]["time"] == stamp(candles[-4].start)
    assert view["bars"][0]["sma50"] is not None
    assert D(view["bars"][-1]["sma20"]) == sum(c.close for c in candles[-23:-3]) / 20
    assert all(bar["quality"] == "ok" for bar in view["bars"])


def test_malformed_minute_chart_is_unavailable_without_faulting_or_repairing(desk_factory):
    desk, _, _ = desk_factory()
    e = desk.engine
    with e.db.transaction() as tx:
        tx.execute(
            "INSERT INTO candles VALUES (?,?,?,?)",
            ("NSE:DEMO", stamp(NOW - timedelta(minutes=1)), 1, '{"close":"invalid"}'),
        )
    with sqlite3.connect(e.settings.database) as db:
        before = list(db.iterdump())
    view = analysis_snapshot(desk, NOW, symbol="NSE:DEMO", timeframe="1m")
    assert view["data_state"] == "unavailable" and not view["bars"]
    assert not e.faulted and e.connected and desk.mode == "manual"
    with sqlite3.connect(e.settings.database) as db:
        assert list(db.iterdump()) == before
