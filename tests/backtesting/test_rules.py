from datetime import time, timedelta
from decimal import Decimal as D

import pytest
from pydantic import ValidationError

from trading_agent.backtesting.dataset import CandleEvent, QuoteEvent
from trading_agent.market_data.calendar import IST
from trading_agent.strategy.rules import RuleStrategy, StrategySettings


def evaluations(dataset, settings=None, transform=None):
    settings = settings or StrategySettings()
    strategy = RuleStrategy(settings, dataset.manifest.calendar())
    latest, result = {}, []
    for event in dataset.events():
        if isinstance(event, QuoteEvent):
            latest[event.quote.symbol] = event.quote
        elif isinstance(event, CandleEvent):
            quote = latest.get(event.candle.symbol)
            candle, quote = transform(event.candle, quote) if transform else (event.candle, quote)
            result.append(
                strategy.evaluate(
                    candle,
                    now=event.time,
                    quote=quote,
                    instrument=dataset.manifest.instruments[0],
                    connected=True,
                )
            )
    return result


@pytest.mark.parametrize("hypothesis", ["opening_range_breakout", "vwap_continuation"])
def test_hypotheses_generate_only_after_complete_warmup(research_dataset, hypothesis):
    settings = StrategySettings(hypothesis=hypothesis)
    result = evaluations(research_dataset, settings)
    signals = [r for r in result if r.candidate]
    assert len(signals) == 2
    assert all(r.features["bar_count"] == 14 for r in signals)
    assert all(r.candidate.decision_time >= r.candle_end for r in signals)
    assert signals[0].features["relative_volume"] == D("2.5")
    assert signals[0].features["prior_mean_volume"] == 2000  # excludes this 5000-volume bar
    assert signals[0].features["opening_high"] == D("500.5")  # excludes later breakout high
    assert signals[0].candidate.stop == D("499.35")
    assert signals[0].candidate.target == D("504.30")
    assert not signals[0].candidate.requires_ml


@pytest.mark.parametrize(
    "changes",
    [
        {"indicator_period": 1},
        {"opening_minutes": 17},
        {"hypothesis": "magical_returns"},
        {"min_relative_volume": "NaN"},
        {"min_price": "10001"},
        {"max_atr_bps": "1"},
        {"min_turnover": "Infinity"},
        {"max_candidates_per_symbol_day": 0},
        {"extra": True},
    ],
)
def test_strategy_settings_fail_closed(changes):
    with pytest.raises(ValidationError):
        StrategySettings(**changes)


@pytest.mark.parametrize(
    "quote_change,reason",
    [
        ({"bid": D(490)}, "SPREAD_TOO_WIDE"),
        ({"ask_size": 0}, "NO_LIQUIDITY"),
        ({"received_time": None}, "STALE_OR_MISSING_QUOTE"),
        ({"ask": D(510), "bid": D("509.95")}, "QUOTE_CANDLE_PRICE_GAP"),
    ],
)
def test_missing_or_untradable_quotes_block_candidates(research_dataset, quote_change, reason):
    def change(candle, quote):
        quote = None if "received_time" in quote_change else quote.model_copy(update=quote_change)
        return candle, quote

    result = evaluations(research_dataset, transform=change)
    assert not any(r.candidate for r in result)
    assert reason in result[13].reasons


def test_one_bad_candle_blocks_rest_of_session_and_next_day_resets(research_dataset):
    first_day = research_dataset.manifest.sessions[0].day

    def change(candle, quote):
        local = candle.start.astimezone(IST)
        if local.date() == first_day and local.hour == 9 and local.minute == 20:
            candle = candle.model_copy(update={"quality": "gap"})
        return candle, quote

    result = evaluations(research_dataset, transform=change)
    assert all("DATA_GAP_OR_QUALITY" in r.reasons for r in result[1:14])
    assert len([r for r in result if r.candidate]) == 1


def test_no_future_incomplete_duplicate_or_off_grid_candles(research_dataset):
    strategy = RuleStrategy(StrategySettings(), research_dataset.manifest.calendar())
    event = next(e for e in research_dataset.events() if isinstance(e, CandleEvent))
    instrument = research_dataset.manifest.instruments[0]
    kwargs = dict(now=event.time, quote=None, instrument=instrument, connected=False)
    for candle in (
        event.candle.model_copy(update={"completed": False}),
        event.candle.model_copy(update={"minutes": 1}),
        event.candle.model_copy(update={"close": D("500.001")}),
    ):
        with pytest.raises(ValueError):
            strategy.evaluate(candle, **kwargs)
    with pytest.raises(ValueError):
        strategy.evaluate(event.candle, **{**kwargs, "now": event.time - timedelta(seconds=1)})
    strategy.evaluate(event.candle, **kwargs)
    with pytest.raises(ValueError, match="duplicate"):
        strategy.evaluate(event.candle, **kwargs)


def test_missing_opening_bar_disables_session(research_dataset):
    strategy = RuleStrategy(StrategySettings(), research_dataset.manifest.calendar())
    events = [e for e in research_dataset.events() if isinstance(e, CandleEvent)]
    for event in events[1:14]:
        result = strategy.evaluate(
            event.candle,
            now=event.time,
            quote=None,
            instrument=research_dataset.manifest.instruments[0],
            connected=True,
        )
        assert result.reasons == ("DATA_GAP_OR_QUALITY",) and result.candidate is None


def test_vwap_hypothesis_requires_prior_pullback(research_dataset):
    def no_pullback(candle, quote):
        if candle.start.astimezone(IST).time() == time(10, 15):
            candle = candle.model_copy(
                update={
                    "open": D("500.20"),
                    "close": D("500.20"),
                    "high": D("500.40"),
                    "low": D("500.10"),
                }
            )
        return candle, quote

    orb = evaluations(research_dataset, transform=no_pullback)
    trend = evaluations(
        research_dataset, StrategySettings(hypothesis="vwap_continuation"), no_pullback
    )
    assert len([r for r in orb if r.candidate]) == 2
    assert not any(r.candidate for r in trend)
    assert "NO_VWAP_CONTINUATION" in trend[13].reasons
