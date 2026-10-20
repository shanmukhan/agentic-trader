"""Exercise real request construction and response decoding with a mock HTTP transport."""

import hashlib
from datetime import timedelta
from decimal import Decimal as D
from urllib.parse import parse_qs

import httpx
import pytest
from conftest import NOW

from trading_agent.broker.readonly_kite import BrokerUnavailable, ReadOnlyKite, RestrictedKiteHTTP
from trading_agent.models import Instrument


def install_transport(monkeypatch, handler):
    original = httpx.Client
    monkeypatch.setattr(
        httpx, "Client", lambda **kwargs: original(**kwargs, transport=httpx.MockTransport(handler))
    )


def test_auth_checksum_endpoint_and_profile_signing(monkeypatch):
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path == "/session/token":
            return httpx.Response(
                200, json={"status": "success", "data": {"access_token": "test-session"}}
            )
        return httpx.Response(200, json={"status": "success", "data": {"broker": "ZERODHA"}})

    install_transport(monkeypatch, handler)
    client = RestrictedKiteHTTP("test-key")
    assert client.generate_session("request", api_secret="secret")["access_token"] == "test-session"
    form = parse_qs(requests[0].content.decode())
    assert form["checksum"] == [hashlib.sha256(b"test-keyrequestsecret").hexdigest()]
    assert requests[0].method == "POST" and requests[0].url.host == "api.kite.trade"
    assert "secret" not in requests[0].content.decode()
    assert ReadOnlyKite("test-key", "test-session").get_profile()["authenticated"]
    assert requests[1].headers["Authorization"] == "token test-key:test-session"
    assert requests[1].headers["X-Kite-Version"] == "3"


def test_csv_and_history_decode_with_real_response_shapes(monkeypatch):
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path == "/instruments/NSE":
            return httpx.Response(
                200,
                text="instrument_token,tradingsymbol,tick_size,lot_size,"
                "instrument_type,segment,exchange\n1,DEMO,0.05,1,EQ,NSE,NSE\n",
            )
        return httpx.Response(
            200,
            json={
                "status": "success",
                "data": {"candles": [["2026-10-20T10:00:00+05:30", 100, 102, 99, 101, 200]]},
            },
        )

    install_transport(monkeypatch, handler)
    broker = ReadOnlyKite("test-key", "test-session")
    item = broker.get_instruments()[0]
    assert item == Instrument(symbol="NSE:DEMO", token=1, tick_size=D(".05"))
    candles = broker.get_historical_candles(
        item, NOW, NOW + timedelta(minutes=10), 5, NOW + timedelta(minutes=10)
    )
    assert candles[0].start == NOW and candles[0].close == 101
    assert requests[1].url.path == "/instruments/historical/1/5minute"
    assert requests[1].url.params["from"] == "2026-10-20 10:00:00"


@pytest.mark.parametrize(
    "status,payload",
    [
        (403, {"status": "error", "message": "secret-token-value"}),
        (200, {"status": "error", "message": "secret-token-value"}),
        (302, {"status": "success", "data": {}}),
    ],
)
def test_auth_expiry_error_and_redirect_do_not_leak(monkeypatch, status, payload):
    install_transport(
        monkeypatch,
        lambda request: httpx.Response(
            status, json=payload, headers={"Location": "https://unexpected.example/"}
        ),
    )
    with pytest.raises(BrokerUnavailable) as failure:
        ReadOnlyKite("key", "session").get_profile()
    assert "secret-token-value" not in str(failure.value)


def test_read_request_requires_auth_before_network(monkeypatch):
    def unexpected(request):
        pytest.fail("network was reached without a session")

    install_transport(monkeypatch, unexpected)
    with pytest.raises(BrokerUnavailable):
        RestrictedKiteHTTP("key").profile()
