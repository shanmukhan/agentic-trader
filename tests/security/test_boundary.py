import logging
from pathlib import Path

import pytest

from trading_agent.broker.readonly_kite import BrokerUnavailable, ReadOnlyKite, make_client
from trading_agent.ml.inference import ModelUnavailable, PhaseOneScorer
from trading_agent.observability.logging import RedactedJSON


def test_sdk_blocks_forbidden_routes_before_network(monkeypatch):
    import httpx

    client = make_client("test-key", "test-token")
    calls = []
    monkeypatch.setattr(httpx, "Client", lambda *a, **k: calls.append((a, k)))
    for route, method in (
        ("order.place", "POST"),
        ("gtt.place", "POST"),
        ("user.profile", "POST"),
        ("market.instruments", "DELETE"),
    ):
        with pytest.raises(BrokerUnavailable):
            client._request(route, method)
    assert not calls


def test_readonly_adapter_surface_and_missing_credentials():
    assert not any(
        name in ReadOnlyKite.__dict__
        for name in ("place_order", "modify_order", "cancel_order", "transfer_funds")
    )
    with pytest.raises(BrokerUnavailable):
        ReadOnlyKite("", "")
    with pytest.raises(ModelUnavailable):
        PhaseOneScorer().score({})


def test_secret_redaction(monkeypatch):
    monkeypatch.setenv("KITE_ACCESS_TOKEN", "sensitive-test-credential")
    record = logging.LogRecord(
        "test",
        logging.ERROR,
        "",
        1,
        "failure sensitive-test-credential request_token=unknown api_secret=hidden",
        (),
        None,
    )
    output = RedactedJSON().format(record)
    assert "sensitive-test-credential" not in output
    assert "unknown" not in output and "hidden" not in output
    assert "[REDACTED]" in output


@pytest.mark.parametrize(
    "message",
    [
        "Authorization: token unknown-key:unknown-session",
        "Authorization=Bearer unknown-session",
        '{"api_secret": "unknown-session"}',
        "{'access_token': 'unknown-session'}",
    ],
)
def test_unknown_secret_header_and_json_redaction(message):
    record = logging.LogRecord("test", logging.ERROR, "", 1, message, (), None)
    output = RedactedJSON().format(record)
    assert "unknown-session" not in output and "unknown-key" not in output


def test_execution_does_not_import_broker_sdk():
    source = Path("src/trading_agent/execution/paper_broker.py").read_text()
    assert "kiteconnect" not in source and "requests" not in source
