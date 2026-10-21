import struct
from datetime import timedelta
from decimal import Decimal as D
from unittest.mock import Mock

import pytest
from conftest import NOW, candidate, quote

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
    assert stream.diagnostics()["last_failure"] == (
        "broker_rejected" if isinstance(message, str) else "invalid_data"
    )


def test_stream_accepts_server_owned_credentials_without_global_environment(monkeypatch):
    monkeypatch.delenv("KITE_API_KEY", raising=False)
    monkeypatch.delenv("KITE_ACCESS_TOKEN", raising=False)
    stream = QuoteStream(
        [Instrument(symbol="NSE:DEMO", token=1, tick_size=D(".05"))],
        lambda q: None,
        lambda connected: None,
        lambda: NOW,
        credentials=("serverkey", "serversession"),
    )
    assert "api_key=serverkey" in stream._url
    assert "access_token=serversession" in stream._url
    stream.close()


@pytest.mark.parametrize("offset", [64, 68, 124, 128])
def test_empty_book_is_not_an_executable_quote(offset):
    message = bytearray(packet())
    struct.pack_into(">I", message, 4 + offset, 0)
    instruments = {1: Instrument(symbol="NSE:DEMO", token=1, tick_size=D(".05"))}
    assert parse_binary(bytes(message), instruments, NOW) == []
    # One empty book must not discard another instrument's usable quote.
    mixed = struct.pack(">H", 2) + message[2:] + packet(257)[2:]
    instruments[257] = Instrument(symbol="NSE:OTHER", token=257, tick_size=D(".05"))
    assert [q.symbol for q in parse_binary(mixed, instruments, NOW)] == ["NSE:OTHER"]
    conflicting = struct.pack(">H", 2) + packet()[2:] + message[2:]
    assert parse_binary(conflicting, instruments, NOW) == []
    with pytest.raises(ValueError):
        parse_binary(bytes(message) + b"bad", instruments, NOW)
    struct.pack_into(">I", message, 4, 513)
    with pytest.raises(ValueError, match="unknown"):
        parse_binary(bytes(message), instruments, NOW)


def test_retry_budget_exposes_only_safe_failure_codes(monkeypatch):
    import websockets.sync.client

    def failure(*args, **kwargs):
        raise TimeoutError("https://private.invalid/?access_token=DO_NOT_EXPOSE")

    monkeypatch.setattr(websockets.sync.client, "connect", failure)
    stream = QuoteStream(
        [Instrument(symbol="NSE:DEMO", token=1, tick_size=D(".05"))],
        Mock(),
        Mock(),
        lambda: NOW,
        credentials=("key", "session"),
    )
    waits = []
    monkeypatch.setattr(stream._stop, "wait", waits.append)
    stream._run()
    assert stream.diagnostics() == {
        "state": "failed",
        "failures": 10,
        "last_failure": "timeout",
        "last_message_at": None,
        "unusable_quotes": 0,
    }
    assert len(waits) == 9 and max(waits) == 30
    snapshot = stream.diagnostics()
    snapshot["state"] = "modified"
    assert stream.diagnostics()["state"] == "failed"
    stream.close()
    assert stream.diagnostics()["state"] == "stopped"


def test_observed_empty_book_invalidates_recent_depth_until_next_accepted_quote(engine):
    assert engine._fresh(quote(), NOW)
    engine.invalidate_quote("NSE:DEMO")
    assert engine.connected and not engine._fresh(quote(), NOW)
    rejected = engine.submit(candidate("empty-book"), NOW)
    assert rejected["state"] == "REJECTED"
    assert "STALE_OR_MISSING_QUOTE" in rejected["reason"]
    assert not engine.snapshot(NOW)["positions"]
    assert D(engine.snapshot(NOW)["cash"]) == D("25000.00")
    assert engine.ingest(quote(1), NOW + timedelta(seconds=1))
    assert engine._fresh(quote(1), NOW + timedelta(seconds=1))
    accepted = engine.submit(
        candidate("restored", now=NOW + timedelta(seconds=1)), NOW + timedelta(seconds=1)
    )
    assert accepted["state"] == "ACCEPTED"
