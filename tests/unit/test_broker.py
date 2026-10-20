import struct
from datetime import timedelta
from decimal import Decimal as D
from unittest.mock import Mock

import pytest
from conftest import NOW

from trading_agent.broker.readonly_kite import (
    BrokerUnavailable,
    QuoteStream,
    ReadOnlyKite,
    exchange_token,
    login_url,
    parse_binary,
)
from trading_agent.models import Instrument


@pytest.fixture
def broker(monkeypatch):
    client = Mock()
    monkeypatch.setattr("trading_agent.broker.readonly_kite.make_client", lambda *a: client)
    return ReadOnlyKite("test-key", "test-session"), client


def test_profile_is_readonly_and_personal_fields_not_exposed(broker):
    adapter, client = broker
    client.profile.return_value = {"broker": "ZERODHA", "email": "private@example.test"}
    assert adapter.get_profile() == {"authenticated": True, "broker": "ZERODHA"}
    client.profile.side_effect = RuntimeError("sensitive-third-party-detail")
    with pytest.raises(BrokerUnavailable) as failure:
        adapter.get_profile()
    assert "sensitive" not in str(failure.value)


def test_catalog_filters_non_equity_instruments(broker):
    adapter, client = broker
    equity = dict(
        exchange="NSE",
        segment="NSE",
        instrument_type="EQ",
        lot_size=1,
        tradingsymbol="DEMO",
        instrument_token=1,
        tick_size=0.05,
    )
    client.instruments.return_value = [
        equity,
        {**equity, "instrument_type": "FUT"},
        {**equity, "exchange": "BSE"},
    ]
    assert adapter.get_instruments() == [Instrument(symbol="NSE:DEMO", token=1, tick_size=D(".05"))]
    client.instruments.assert_called_once_with("NSE")


def test_historical_completed_only_and_gap_flagged(broker):
    adapter, client = broker
    instrument = Instrument(symbol="NSE:DEMO", token=1, tick_size=D(".05"))
    client.historical_data.return_value = [
        dict(
            date=NOW + timedelta(minutes=minute), open=100, high=101, low=99, close=100, volume=100
        )
        for minute in (0, 10, 15)
    ]
    result = adapter.get_historical_candles(
        instrument, NOW, NOW + timedelta(minutes=16), 5, NOW + timedelta(minutes=16)
    )
    assert len(result) == 2 and result[1].quality == "gap"
    with pytest.raises(ValueError):
        adapter.get_historical_candles(
            instrument, NOW, NOW + timedelta(days=31), 5, NOW + timedelta(days=32)
        )


def test_manual_auth_uses_supported_token_flow(broker):
    _, client = broker
    client.generate_session.return_value = {"access_token": "temporary-session"}
    assert exchange_token("key", "secret", "one-time-request") == "temporary-session"
    client.generate_session.assert_called_once_with("one-time-request", api_secret="secret")
    client.login_url.return_value = "https://kite.zerodha.com/connect/login"
    assert login_url("key").startswith("https://kite.zerodha.com/")
    with pytest.raises(BrokerUnavailable):
        exchange_token("", "", "")


def packet(token=1):
    content = bytearray(184)
    for offset, value in (
        (0, token),
        (4, 50000),
        (16, 1000),
        (60, int(NOW.timestamp())),
        (64, 100),
        (68, 49995),
        (124, 100),
        (128, 50000),
    ):
        struct.pack_into(">I", content, offset, value)
    return struct.pack(">HH", 1, 184) + content


def test_full_tick_normalization_and_invalid_depth():
    instrument = Instrument(symbol="NSE:DEMO", token=1, tick_size=D(".05"))
    result = parse_binary(packet(), {1: instrument}, NOW)[0]
    assert result.exchange_time == NOW and result.source == "kite"
    assert result.bid == D("499.95") and result.ask == D(500)
    assert parse_binary(b"\x00", {1: instrument}, NOW) == []
    for message in (b"", b"\x00\x01", packet()[:-1], packet() + b"bad", packet(2)):
        with pytest.raises(ValueError):
            parse_binary(message, {1: instrument}, NOW)


def test_stream_disconnect_and_bad_packet_fail_closed(monkeypatch):
    from contextlib import nullcontext

    import websockets.sync.client

    socket = Mock()
    socket.recv.return_value = packet()
    monkeypatch.setattr(websockets.sync.client, "connect", lambda *a, **k: nullcontext(socket))
    monkeypatch.setenv("KITE_API_KEY", "test-key")
    monkeypatch.setenv("KITE_ACCESS_TOKEN", "test-session")
    states, quotes = [], []

    def received(value):
        quotes.append(value)
        stream._stop.set()

    stream = QuoteStream(
        [Instrument(symbol="NSE:DEMO", token=1, tick_size=D(".05"))],
        received,
        states.append,
        lambda: NOW,
    )
    stream._run()
    assert states == [True, False] and len(quotes) == 1
    assert socket.send.call_count == 2
    stream.close()


@pytest.mark.parametrize("message", [b"broken-packet", '{"type":"error","data":"expired"}'])
def test_malformed_stream_and_expiry_disable_connection(monkeypatch, message):
    from contextlib import nullcontext

    import websockets.sync.client

    socket = Mock()
    socket.recv.return_value = message
    monkeypatch.setattr(websockets.sync.client, "connect", lambda *a, **k: nullcontext(socket))
    monkeypatch.setenv("KITE_API_KEY", "test-key")
    monkeypatch.setenv("KITE_ACCESS_TOKEN", "test-session")
    states, quotes = [], []
    stream = QuoteStream(
        [Instrument(symbol="NSE:DEMO", token=1, tick_size=D(".05"))],
        quotes.append,
        states.append,
        lambda: NOW,
    )
    monkeypatch.setattr(stream._stop, "wait", lambda timeout: stream._stop.set())
    stream._run()
    assert states == [True, False] and not quotes
