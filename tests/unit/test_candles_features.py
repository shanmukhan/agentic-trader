from datetime import timedelta
from decimal import Decimal as D

import pytest
from conftest import NOW, quote

from trading_agent.features.indicators import Indicators
from trading_agent.market_data.candles import CandleBuilder
from trading_agent.models import Candle


def candle(index=0, **changes):
    values = dict(
        symbol="NSE:DEMO",
        start=NOW + timedelta(minutes=5 * index),
        minutes=5,
        open=D(100),
        high=D(104),
        low=D(98),
        close=D(102),
        volume=100,
    )
    values.update(changes)
    return Candle(**values)


def test_ema_atr_vwap_against_hand_calculation():
    feature = Indicators(period=2)
    first = feature.update(candle())
    assert first["ema"] is None and first["atr"] is None
    assert first["vwap"] == D(304) / 3
    second = feature.update(
        candle(1, open=D(103), high=D(108), low=D(102), close=D(105), volume=200)
    )
    assert second["ema"] == 104
    assert second["atr"] == 6
    assert second["vwap"] == ((D(304) / 3 * 100) + (D(315) / 3 * 200)) / 300


@pytest.mark.parametrize("value", [candle(completed=False), candle(quality="gap")])
def test_bad_feature_input(value):
    with pytest.raises(ValueError):
        Indicators().update(value)


def test_feature_gap_order_symbol_and_session_reset():
    feature = Indicators(2)
    feature.update(candle())
    for value in (candle(), candle(2), candle(1, symbol="NSE:SECOND")):
        with pytest.raises(ValueError):
            feature.update(value)
    feature.update(candle(288))
    assert feature.count == 1


def test_cumulative_volume_never_counted_as_tick_volume():
    builder = CandleBuilder(1)
    assert builder.update(quote()) == []
    builder.update(quote(10))
    completed = builder.update(quote(60))
    assert len(completed) == 1 and completed[0].completed
    assert completed[0].volume == 1000
    assert completed[0].quality == "unknown_initial_volume"
    assert builder.active["NSE:DEMO"].volume == 5000
    with pytest.raises(ValueError):
        builder.update(quote(60))


def test_gap_is_flagged_and_active_candles_not_emitted_early():
    builder = CandleBuilder(5)
    builder.update(quote())
    result = builder.update(quote(600))
    assert result[0].quality == "gap"
    assert not builder.flush(NOW + timedelta(minutes=11))
    assert builder.flush(NOW + timedelta(minutes=15))[0].completed
