"""Synthetic arithmetic fixtures; these do not establish market/source acceptance."""

from copy import deepcopy
from decimal import ROUND_DOWN, Decimal, Inexact, getcontext, localcontext
from fractions import Fraction
from typing import Any

import pytest

from trading_agent.investment_research import (
    FORMULA_VERSION,
    INDICATOR_DEFINITIONS,
    indicator_series,
)

D = Decimal
F = Fraction


def bars(closes: list[str | int | Decimal]) -> list[dict[str, Any]]:
    # Test construction is deliberately outside the production arithmetic code.
    with localcontext() as context:
        context.prec = 100
        return [
            {
                "session": f"synthetic-{index}",
                "available_at": f"synthetic-availability-{index}",
                "open": str(D(close)),
                "high": str(D(close) + 2),
                "low": str(D(close) - 2),
                "close": str(D(close)),
                "volume": str(index * 7),
                "source": {"synthetic": True},
            }
            for index, close in enumerate(closes)
        ]


def decimal_fraction(value: Fraction) -> Decimal:
    with localcontext() as context:
        context.prec = 90
        return D(value.numerator) / D(value.denominator)


def close_to(actual: str | None, expected: Fraction | Decimal) -> None:
    assert actual is not None
    exact = decimal_fraction(expected) if isinstance(expected, Fraction) else expected
    with localcontext() as context:
        context.prec = 90
        assert abs(D(actual) - exact) <= max(D(1), abs(exact)) * D("1e-30")


def weighted_average(values: list[Fraction], period: int, alpha: Fraction) -> Fraction | None:
    """Independent closed-form weights, rather than the implementation's recurrence."""
    if len(values) < period:
        return None
    tail = values[period:]
    persistence = 1 - alpha
    return sum(values[:period], F(0)) / period * persistence ** len(tail) + sum(
        (
            alpha * value * persistence ** (len(tail) - index - 1)
            for index, value in enumerate(tail)
        ),
        F(0),
    )


def test_formula_identity_and_exact_warmup_boundaries():
    assert FORMULA_VERSION == "investment-indicators-v2.1"
    assert INDICATOR_DEFINITIONS["volatility20_pct"]["annualized"] is False
    result = indicator_series(bars([100] * 205))
    for name, definition in INDICATOR_DEFINITIONS.items():
        first = definition["first_valid_bar"] - 1
        assert all(row[name] is None for row in result[:first]), name
        assert all(row[name] is not None for row in result[first:]), name
    for row in result:
        for name in ("sma20", "sma50", "sma200", "ema12", "ema26"):
            if row[name] is not None:
                assert D(row[name]) == 100
        for name in ("macd", "macd_signal", "macd_histogram", "volatility20_pct"):
            if row[name] is not None:
                assert D(row[name]) == 0
        if row["rsi14"] is not None:
            assert D(row["rsi14"]) == 50
        if row["atr14"] is not None:
            assert D(row["atr14"]) == 4


def test_all_indicators_match_independent_fraction_reference():
    closes = [100 + (index % 11) * 3 + index // 11 for index in range(78)]
    records = bars(closes)
    result = indicator_series(records)
    points = [F(value) for value in closes]
    gains = [
        max(later - earlier, 0) for earlier, later in zip(points[:-1], points[1:], strict=True)
    ]
    losses = [
        max(earlier - later, 0) for earlier, later in zip(points[:-1], points[1:], strict=True)
    ]
    true_ranges = [
        max(F(4), abs(later + 2 - earlier), abs(later - 2 - earlier))
        for earlier, later in zip(points[:-1], points[1:], strict=True)
    ]
    macd_values: list[Fraction] = []
    for end, row in enumerate(result, 1):
        prefix = points[:end]
        for period in (20, 50, 200):
            if end >= period:
                close_to(row[f"sma{period}"], sum(prefix[-period:], F(0)) / period)
        for period in (12, 26):
            ema = weighted_average(prefix, period, F(2, period + 1))
            if ema is not None:
                close_to(row[f"ema{period}"], ema)
        if end >= 26:
            fast = weighted_average(prefix, 12, F(2, 13))
            slow = weighted_average(prefix, 26, F(2, 27))
            assert fast is not None and slow is not None
            line = fast - slow
            macd_values.append(line)
            close_to(row["macd"], line)
            signal = weighted_average(macd_values, 9, F(1, 5))
            if signal is not None:
                close_to(row["macd_signal"], signal)
                close_to(row["macd_histogram"], line - signal)
        if end >= 15:
            gain = weighted_average(gains[: end - 1], 14, F(1, 14))
            loss = weighted_average(losses[: end - 1], 14, F(1, 14))
            atr = weighted_average(true_ranges[: end - 1], 14, F(1, 14))
            assert gain is not None and loss is not None and atr is not None
            close_to(row["rsi14"], 100 - F(100) / (1 + gain / loss))
            close_to(row["atr14"], atr)
        if end >= 21:
            previous = prefix[-21:-1]
            close_to(row["support20"], min(previous) - 2)
            close_to(row["resistance20"], max(previous) + 2)
            returns = [
                later / earlier - 1
                for earlier, later in zip(prefix[-21:-1], prefix[-20:], strict=True)
            ]
            mean = sum(returns, F(0)) / 20
            variance = sum(((value - mean) ** 2 for value in returns), F(0)) / 20
            with localcontext() as context:
                context.prec = 90
                expected_volatility = decimal_fraction(variance).sqrt() * 100
            close_to(row["volatility20_pct"], expected_volatility)
        close_to(row["drawdown_pct"], (prefix[-1] / max(prefix) - 1) * 100)
        worst = min((prefix[index] / max(prefix[: index + 1]) - 1) * 100 for index in range(end))
        close_to(row["max_drawdown_pct"], worst)


@pytest.mark.parametrize(
    "closes, expected", [([100 + i for i in range(35)], 100), ([100 - i for i in range(35)], 0)]
)
def test_rsi_zero_gain_or_loss(closes: list[int], expected: int):
    result = indicator_series(bars(closes))
    assert all(D(row["rsi14"]) == expected for row in result[14:])


def test_support_and_resistance_exclude_current_bar():
    records = bars([100] * 22)
    records[20].update(high="999", low="1")
    result = indicator_series(records)
    assert result[19]["support20"] is None
    assert D(result[20]["support20"]) == 98
    assert D(result[20]["resistance20"]) == 102
    assert D(result[21]["support20"]) == 1
    assert D(result[21]["resistance20"]) == 999


def test_drawdown_peak_recovery_and_percent_units():
    result = indicator_series(bars([100, 80, 120, 90, 130]))
    assert [D(row["drawdown_pct"]) for row in result] == [0, -20, 0, -25, 0]
    assert [D(row["max_drawdown_pct"]) for row in result] == [0, -20, -20, -25, -25]


def test_segment_break_resets_every_window_and_recursive_history():
    records = bars([100 + index % 5 for index in range(250)])
    records[211]["segment_break"] = True
    result = indicator_series(records)
    assert result[211:] == indicator_series(records[211:])
    for key in INDICATOR_DEFINITIONS:
        if key not in ("drawdown_pct", "max_drawdown_pct"):
            assert result[211][key] is None
    assert D(result[211]["drawdown_pct"]) == D(result[211]["max_drawdown_pct"]) == 0
    assert result[249]["sma50"] is None
    assert result[249]["sma200"] is None


def test_coherent_split_adjusted_inputs_do_not_create_a_false_price_gap():
    # These are invented already-adjusted inputs, not action-verification evidence.
    adjusted = bars([50] * 35)
    raw = bars([100] * 17 + [50] * 18)
    for row in adjusted[:17]:
        row.update(high="51", low="49", volume=str(int(row["volume"]) * 2))
    for row in adjusted[17:]:
        row.update(high="51", low="49")
    coherent = indicator_series(adjusted)
    inconsistent = indicator_series(raw)
    assert D(coherent[-1]["rsi14"]) == 50
    assert D(coherent[-1]["atr14"]) == 2
    assert D(coherent[-1]["max_drawdown_pct"]) == 0
    assert D(coherent[-1]["volatility20_pct"]) == 0
    assert D(inconsistent[-1]["max_drawdown_pct"]) == -50


def test_future_prefix_invariance_and_inputs_never_mutated():
    records = bars([100 + index % 7 for index in range(230)])
    saved = deepcopy(records)
    first = indicator_series(records[:210])
    records[-1].update(open="100000", close="100000", high="100002", low="99998")
    result = indicator_series(records)
    assert result[:210] == first
    assert records[:-1] == saved[:-1]
    assert all(result[index]["source"] == records[index]["source"] for index in range(230))
    actual_input = deepcopy(records)
    assert indicator_series(records) == result
    assert records == actual_input


def test_fixed_decimal_context_handles_huge_values_and_restores_ambient_context():
    records = [
        {"open": "1e600", "high": "1.01e600", "low": "9.9e599", "close": "1e600", "volume": "1e600"}
        for _ in range(205)
    ]
    expected = indicator_series(records)
    before = getcontext().copy()
    with localcontext() as context:
        context.prec = 7
        context.rounding = ROUND_DOWN
        context.Emax = 9
        context.Emin = -9
        context.traps[Inexact] = True
        ambient = context.copy()
        assert indicator_series(records) == expected
        assert context.prec == ambient.prec
        assert context.rounding == ambient.rounding
        assert context.Emax == ambient.Emax and context.Emin == ambient.Emin
        assert context.traps == ambient.traps and context.flags == ambient.flags
    assert getcontext().prec == before.prec
    assert getcontext().traps == before.traps and getcontext().flags == before.flags
    assert D(expected[-1]["sma200"]) == D("1e600")
    assert D(expected[-1]["atr14"]) == D("2e598")
    assert D(expected[-1]["macd"]) == 0


@pytest.mark.parametrize(
    "change",
    [
        {"open": "0"},
        {"high": "-1"},
        {"low": "NaN"},
        {"close": "Infinity"},
        {"close": "not-a-number"},
        {"close": 100.0},
        {"open": True},
        {"volume": "-1"},
        {"volume": "NaN"},
        {"volume": False},
        {"volume": None},
        {"high": "99"},
        {"low": "101"},
        {"segment_break": "true"},
        {"segment_break": None},
    ],
)
def test_invalid_input_is_refused_without_changing_the_source(change: dict[str, Any]):
    records = bars([100])
    records[0].update(change)
    before = deepcopy(records)
    with pytest.raises(ValueError):
        indicator_series(records)
    assert records == before


def test_empty_missing_field_and_wrong_record_types():
    assert indicator_series([]) == []
    with pytest.raises(ValueError, match="list"):
        indicator_series(())  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="record"):
        indicator_series([None])  # type: ignore[list-item]
    record = bars([100])[0]
    del record["volume"]
    with pytest.raises(ValueError, match="volume"):
        indicator_series([record])
