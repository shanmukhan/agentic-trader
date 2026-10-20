"""Causal, incremental five-minute rule hypotheses. No broker or execution dependency."""

import hashlib
import json
import tomllib
from collections import deque
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

from pydantic import ConfigDict, Field, model_validator

from trading_agent.execution.costs import down, up
from trading_agent.features.indicators import Indicators
from trading_agent.market_data.calendar import IST, SessionCalendar
from trading_agent.models import Candidate, Candle, DomainModel, Instrument, Quote, stamp, utc

D = Decimal
RULE_VERSION = "completed-5m-rules-v1"


class StrategySettings(DomainModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)
    hypothesis: Literal["opening_range_breakout", "vwap_continuation"] = "opening_range_breakout"
    indicator_period: int = Field(default=14, ge=2, le=100)
    volume_lookback: int = Field(default=5, ge=2, le=100)
    opening_minutes: int = Field(default=15, ge=5, le=60, multiple_of=5)
    min_relative_volume: Decimal = Field(default=D("1.2"), ge=1, le=10)
    min_bar_volume: int = Field(default=1000, ge=1)
    min_turnover: Decimal = Field(default=D("1000000"), ge=0)
    min_price: Decimal = Field(default=D("10"), gt=0)
    max_price: Decimal = Field(default=D("10000"), gt=0)
    min_atr_bps: Decimal = Field(default=D("5"), gt=0)
    max_atr_bps: Decimal = Field(default=D("300"), gt=0, le=2000)
    stop_atr_multiple: Decimal = Field(default=D("1.5"), ge=1, le=5)
    reward_risk_multiple: Decimal = Field(default=D("2"), ge=1, le=5)
    max_quote_gap_bps: Decimal = Field(default=D("50"), gt=0, le=500)
    max_spread_bps: Decimal = Field(default=D("30"), gt=0, le=1000)
    max_data_age_seconds: int = Field(default=5, ge=1, le=60)
    max_candidates_per_symbol_day: int = Field(default=1, ge=1, le=10)

    @model_validator(mode="after")
    def ordered(self) -> "StrategySettings":
        if self.min_price >= self.max_price or self.min_atr_bps >= self.max_atr_bps:
            raise ValueError("strategy bounds must increase")
        return self

    @classmethod
    def load(cls, path: Path) -> "StrategySettings":
        with path.open("rb") as file:
            return cls.model_validate(tomllib.load(file))

    def digest(self) -> str:
        values = self.model_dump()
        for key, value in values.items():
            if isinstance(value, Decimal):
                values[key] = format(value.normalize(), "f")
        return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


class Evaluation(DomainModel):
    time: datetime
    candle_end: datetime
    symbol: str
    reasons: tuple[str, ...]
    features: dict[str, Any]
    candidate: Candidate | None = None


@dataclass
class SymbolState:
    day: date
    indicators: Indicators
    volumes: deque[int]
    previous: Candle | None = None
    opening_high: Decimal | None = None
    opening_count: int = 0
    emitted: int = 0
    poisoned: bool = False
    count: int = 0
    volume_sum: int = 0


class RuleStrategy:
    def __init__(self, settings: StrategySettings, calendar: SessionCalendar):
        self.settings, self.calendar = settings, calendar
        self.states: dict[str, SymbolState] = {}
        self.config_hash = settings.digest()

    def evaluate(
        self,
        candle: Candle,
        *,
        now: datetime,
        quote: Quote | None,
        instrument: Instrument,
        connected: bool,
    ) -> Evaluation:
        now = utc(now)
        end = candle.start + timedelta(minutes=5)
        if candle.minutes != 5 or not candle.completed or end > now:
            raise ValueError("strategy requires a completed five-minute candle available by now")
        if candle.symbol != instrument.symbol or quote and quote.symbol != candle.symbol:
            raise ValueError("strategy instrument mismatch")
        bounds = self.calendar.bounds(candle.start)
        if not bounds or candle.start < bounds[0] or end > bounds[1]:
            raise ValueError("candle is outside a reviewed exchange session")
        if any(
            price % instrument.tick_size
            for price in (candle.open, candle.high, candle.low, candle.close)
        ):
            raise ValueError("candle violates the instrument tick grid")
        s = self.settings
        day = candle.start.astimezone(IST).date()
        state = self.states.get(candle.symbol)
        if state and day < state.day:
            raise ValueError("strategy session moved backward")
        if state is None or state.day != day:
            state = SymbolState(
                day, Indicators(s.indicator_period), deque(maxlen=s.volume_lookback)
            )
            self.states[candle.symbol] = state
        previous = state.previous
        if previous and candle.start <= previous.start:
            raise ValueError("duplicate or out-of-order strategy candle")
        expected = previous.start + timedelta(minutes=5) if previous else bounds[0]
        if candle.start != expected or candle.quality != "ok":
            state.poisoned = True
        state.previous = candle
        if state.poisoned:
            return Evaluation(
                time=now,
                candle_end=end,
                symbol=candle.symbol,
                reasons=("DATA_GAP_OR_QUALITY",),
                features={},
            )
        previous_ema = state.indicators.ema
        values = state.indicators.update(candle)
        state.count += 1
        opening_end = bounds[0] + timedelta(minutes=s.opening_minutes)
        if end <= opening_end:
            state.opening_high = max(state.opening_high or candle.high, candle.high)
            state.opening_count += 1
        mean = D(state.volume_sum) / len(state.volumes) if state.volumes else D(0)
        relative_volume = D(candle.volume) / mean if mean else None
        if len(state.volumes) == s.volume_lookback:
            state.volume_sum -= state.volumes[0]
        state.volumes.append(candle.volume)
        state.volume_sum += candle.volume
        ema, atr, vwap = state.indicators.ema, state.indicators.atr, state.indicators.vwap
        features: dict[str, Any] = {
            **values,
            "bar_count": state.count,
            "relative_volume": relative_volume,
            "prior_mean_volume": mean,
            "opening_high": state.opening_high,
            "feature_time": stamp(end),
        }
        reasons = []
        if state.count < max(s.indicator_period, s.volume_lookback + 1) or atr is None:
            reasons.append("WARMUP")
        if (now - end).total_seconds() > s.max_data_age_seconds:
            reasons.append("STALE_CANDLE")
        if now.astimezone(IST).date() != day:
            reasons.append("STALE_SESSION")
        if not connected:
            reasons.append("FEED_DISCONNECTED")
        usable_quote = quote is not None and all(
            0 <= (now - t).total_seconds() <= s.max_data_age_seconds
            for t in (quote.exchange_time, quote.received_time)
        )
        if not usable_quote:
            reasons.append("STALE_OR_MISSING_QUOTE")
        if quote:
            if quote.token != instrument.token:
                raise ValueError("quote token differs from the catalog")
            if not quote.bid_size or not quote.ask_size:
                reasons.append("NO_LIQUIDITY")
            if (quote.ask - quote.bid) / quote.bid * 10000 > s.max_spread_bps:
                reasons.append("SPREAD_TOO_WIDE")
            if abs(quote.ask - candle.close) / candle.close * 10000 > s.max_quote_gap_bps:
                reasons.append("QUOTE_CANDLE_PRICE_GAP")
        if not s.min_price <= candle.close <= s.max_price:
            reasons.append("PRICE_FILTER")
        if candle.volume < s.min_bar_volume or candle.close * candle.volume < s.min_turnover:
            reasons.append("TURNOVER_FILTER")
        if relative_volume is None or relative_volume < s.min_relative_volume:
            reasons.append("RELATIVE_VOLUME_FILTER")
        if atr is not None and not s.min_atr_bps <= atr / candle.close * 10000 <= s.max_atr_bps:
            reasons.append("VOLATILITY_FILTER")
        if (
            ema is None
            or vwap is None
            or previous_ema is None
            or not candle.close > ema > previous_ema
            or candle.close <= vwap
        ):
            reasons.append("TREND_FILTER")
        if s.hypothesis == "opening_range_breakout":
            if (
                end <= opening_end
                or state.opening_count != s.opening_minutes // 5
                or state.opening_high is None
                or previous is None
                or not previous.close <= state.opening_high < candle.close
            ):
                reasons.append("NO_OPENING_RANGE_CROSS")
        elif (
            previous is None
            or previous_ema is None
            or previous.low > previous_ema
            or candle.close <= previous.high
        ):
            reasons.append("NO_VWAP_CONTINUATION")
        if state.emitted >= s.max_candidates_per_symbol_day:
            reasons.append("DAILY_CANDIDATE_LIMIT")
        candidate = None
        if not reasons and atr is not None:
            stop = down(candle.close - atr * s.stop_atr_multiple, instrument.tick_size)
            target = up(
                candle.close + (candle.close - stop) * s.reward_risk_multiple, instrument.tick_size
            )
            if stop <= 0 or quote is None or stop >= quote.bid or target <= quote.ask:
                reasons.append("INVALID_STOP_OR_TARGET")
            else:
                key = f"{RULE_VERSION}:{self.config_hash}:{candle.symbol}:{stamp(end)}"
                candidate = Candidate(
                    intent_id="rule:" + hashlib.sha256(key.encode()).hexdigest()[:48],
                    symbol=candle.symbol,
                    stop=stop,
                    target=target,
                    decision_time=now,
                    reason=f"{s.hypothesis}; completed candle {stamp(end)}",
                    model_version=f"{RULE_VERSION}:{self.config_hash[:12]}",
                )
                state.emitted += 1
        return Evaluation(
            time=now,
            candle_end=end,
            symbol=candle.symbol,
            reasons=tuple(reasons),
            features=features,
            candidate=candidate,
        )
