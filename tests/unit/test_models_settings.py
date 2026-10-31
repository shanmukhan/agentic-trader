from datetime import datetime
from decimal import Decimal

import pytest
from conftest import candidate, quote
from pydantic import ValidationError

from trading_agent.models import Quote
from trading_agent.settings import Settings


@pytest.mark.parametrize(
    "changes",
    [
        {"mode": "live"},
        {"host": "0.0.0.0"},
        {"max_trade_risk": "NaN"},
        {"max_total_notional": "25001"},
        {"entry_end": "16:00"},
        {"operator_token": "short"},
        {"latency_ms": 30000},
        {"starting_cash": "-1"},
        {"stream_tokens": [-1]},
        {"stream_limit": 0},
        {"stream_limit": 3001},
        {"stream_limit": True},
        {"stream_tokens": list(range(1, 52))},
        {"stream_limit": 10, "stream_tokens": list(range(1, 12))},
        {"stream_limit": 50, "stream_tokens": [1, 1]},
        {"unexpected": True},
    ],
)
def test_invalid_settings(changes):
    with pytest.raises(ValidationError):
        Settings(**changes)


def test_environment_live_mode_rejected(tmp_path, monkeypatch):
    path = tmp_path / "paper.toml"
    path.write_text('mode="paper"\n')
    monkeypatch.setenv("TRADING_MODE", "live")
    with pytest.raises(ValidationError):
        Settings.load(path)


@pytest.mark.parametrize(
    "changes",
    [
        {"last": "NaN"},
        {"bid": "501"},
        {"volume": -1},
        {"ask_size": True},
        {"symbol": "NFO:DEMO"},
        {"received_time": datetime(2026, 10, 20)},
        {"last": "0"},
        {"token": -2},
    ],
)
def test_invalid_quote(changes):
    values = quote().model_dump()
    values.update(changes)
    with pytest.raises(ValidationError):
        Quote.model_validate(values)


def test_naive_decision_rejected():
    with pytest.raises(ValidationError):
        candidate(now=datetime(2026, 10, 20))


def test_decimal_exactness():
    assert quote().bid == Decimal("499.95")
    assert Settings().starting_cash == Decimal("25000")


def test_configured_stream_capacity_preserves_economic_identity(tmp_path, monkeypatch):
    from trading_agent.risk.policy import policy_fingerprint

    monkeypatch.delenv("TRADING_MODE", raising=False)
    path = tmp_path / "paper.toml"
    tokens = tuple(256 * index + 1 for index in range(50))
    path.write_text(f"stream_limit=50\nstream_tokens={list(tokens)}\n")
    settings = Settings.load(path)
    assert settings.stream_limit == 50 and settings.stream_tokens == tokens
    assert policy_fingerprint(settings) == policy_fingerprint(Settings())
    assert (
        len(Settings(stream_limit=3000, stream_tokens=tuple(range(1, 3001))).stream_tokens) == 3000
    )
