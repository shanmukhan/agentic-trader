import json
import os
from datetime import timedelta
from decimal import Decimal
from unittest.mock import Mock

import pytest
from conftest import NOW, candidate, quote

from trading_agent.api.setup import SetupError, SetupService, private_write
from trading_agent.risk.policy import policy_fingerprint
from trading_agent.settings import Settings


@pytest.fixture
def setup_service(engine, tmp_path):
    engine.set_connected(False)
    engine.calendar.sources = {day: "invented test session" for day in engine.calendar.sessions}
    calendar = tmp_path / "sessions.csv"
    calendar.write_text(
        "date,open,close,source\n"
        + "".join(f"{day},09:15,15:30,invented test session\n" for day in engine.calendar.sessions)
    )
    engine.settings = engine.settings.model_copy(update={"calendar": calendar})
    config = tmp_path / "manual.toml"
    values = engine.settings.model_dump(mode="json", exclude={"operator_token"})
    config.write_text("".join(f"{key} = {json.dumps(value)}\n" for key, value in values.items()))
    return SetupService(engine, config, lambda: NOW)


def accounting(service):
    with service.engine.db.transaction() as tx:
        return (
            dict(
                tx.execute("SELECT key,value FROM meta WHERE key IN ('cash','fees','policy_hash')")
            ),
            [
                tx.execute(f"SELECT count(*) FROM {table}").fetchone()[0]
                for table in ("fills", "positions", "orders")
            ],
        )


def test_private_credentials_saved_without_exposing_values_and_survive_restart(setup_service):
    s = setup_service
    before = accounting(s)
    s.save_credentials({"api_key": "unitkey", "api_secret": "unitsecret"})
    assert s.path.stat().st_mode & 0o777 == 0o600
    assert s.status()["credentials_configured"]
    assert "unitsecret" not in json.dumps(s.status())
    assert "unitkey" not in json.dumps(s.status())
    restored = SetupService(s.engine, s.config, lambda: NOW)
    assert restored.values == s.values
    assert accounting(s) == before


def test_unsafe_credential_files_and_atomic_write_failure(setup_service, monkeypatch):
    s = setup_service
    s.path.write_text("{}")
    s.path.chmod(0o644)
    with pytest.raises(SetupError, match="private"):
        SetupService(s.engine, s.config)
    s.path.unlink()
    target = s.path.with_name("target")
    target.write_text("unchanged")
    s.path.symlink_to(target)
    with pytest.raises(SetupError):
        private_write(s.path, "secret")
    s.path.unlink()
    monkeypatch.setattr(os, "replace", Mock(side_effect=OSError("disk failure")))
    with pytest.raises(OSError):
        private_write(target, "new secret")
    assert target.read_text() == "unchanged"
    assert not list(target.parent.glob(".setup-*"))


def test_login_nonce_consumed_even_on_uncertain_exchange_and_secrets_redacted(
    setup_service, monkeypatch
):
    s = setup_service
    s.save_credentials({"api_key": "unitkey", "api_secret": "unitsecret"})
    login = s.begin_login()
    assert login["login_url"].startswith("https://kite.zerodha.com/")
    assert "redirect_params=" in login["login_url"]
    exchange = Mock(side_effect=RuntimeError("private upstream token details"))
    monkeypatch.setattr("trading_agent.api.setup.exchange_token", exchange)
    with pytest.raises(SetupError, match="Start a new manual login") as failure:
        s.exchange({"request_token": "onetimerequest", "state": login["state"]})
    assert "private" not in str(failure.value)
    with pytest.raises(SetupError, match="already used"):
        s.exchange({"request_token": "onetimerequest", "state": login["state"]})
    assert exchange.call_count == 1
    assert s.values["access_token"] == ""


def test_login_expiry_and_successful_exchange_are_private(setup_service, monkeypatch):
    s = setup_service
    s.save_credentials({"api_key": "unitkey", "api_secret": "unitsecret"})
    login = s.begin_login()
    s.nonce = (login["state"], 0)
    with pytest.raises(SetupError, match="expired"):
        s.exchange({"request_token": "req", "state": login["state"]})
    login = s.begin_login()
    monkeypatch.setattr("trading_agent.api.setup.exchange_token", lambda *a: "newsession")
    monkeypatch.setattr("trading_agent.api.setup.ReadOnlyKite", lambda *a: Mock())
    s.exchange({"request_token": "req", "state": login["state"]})
    assert s.verified and s.status()["access_token_available"]
    assert json.loads(s.path.read_text())["access_token"] == "newsession"
    assert "newsession" not in json.dumps(s.status())


def test_selection_is_catalog_validated_and_financial_identity_preserved(setup_service):
    s = setup_service
    before = accounting(s)
    old_hash = policy_fingerprint(s.engine.settings)
    for symbols in ([], ["DEMO", "NSE:DEMO"], ["MISSING"], [3]):
        with pytest.raises(SetupError):
            s.select_symbols({"symbols": symbols})
    s.select_symbols({"symbols": ["DEMO", "SECOND"]})
    assert Settings.load(s.config).stream_tokens == (1, 2)
    assert policy_fingerprint(s.engine.settings) == old_hash
    assert accounting(s) == before
    assert {r["symbol"] for r in s.status()["selected"]} == {"NSE:DEMO", "NSE:SECOND"}


def test_selection_cannot_omit_a_holding_or_change_with_pending_orders(setup_service):
    s = setup_service
    s.engine.set_connected(True)
    current = NOW + timedelta(seconds=1)
    s.engine.ingest(quote(1), current)
    assert s.engine.submit(candidate(now=current), current)["state"] == "ACCEPTED"
    with pytest.raises(SetupError, match="pending"):
        s.select_symbols({"symbols": ["SECOND"]})
    s.engine.ingest(quote(2), NOW + timedelta(seconds=2))
    with pytest.raises(SetupError, match="held"):
        s.select_symbols({"symbols": ["SECOND"]})
    s.select_symbols({"symbols": ["DEMO", "SECOND"]})


def test_calendar_requires_review_cannot_rewrite_and_persists_new_session(setup_service):
    s = setup_service
    before = accounting(s)
    body = {
        "date": "2026-10-22",
        "open": "09:15",
        "close": "15:30",
        "source": "invented reviewed session",
        "reviewed": True,
    }
    for patch in (
        {"reviewed": 1},
        {"date": "2026-10-19"},
        {"open": "18:00"},
        {"source": "bad\nsource"},
        {"close": "10:00+05:30"},
    ):
        with pytest.raises(SetupError):
            s.add_session({**body, **patch})
    s.add_session(body)
    loaded = Settings.load(s.config)
    assert loaded.calendar != s.config.parent / "sessions.csv"
    from trading_agent.market_data.calendar import SessionCalendar

    assert len(SessionCalendar.load(loaded.calendar).sessions) == 3
    assert loaded.calendar.stat().st_mode & 0o777 == 0o600
    assert accounting(s) == before
    with pytest.raises(SetupError, match="Existing session"):
        s.add_session({**body, "close": "15:00"})


def test_calendar_config_failure_does_not_replace_live_or_old_calendar(setup_service, monkeypatch):
    s = setup_service
    old_path, old_text = s.engine.settings.calendar, s.config.read_text()
    old_sessions = dict(s.engine.calendar.sessions)
    monkeypatch.setattr(s, "_persist_config", Mock(side_effect=OSError("cannot write")))
    with pytest.raises(SetupError, match="remain unchanged"):
        s.add_session(
            {
                "date": "2026-10-22",
                "open": "09:15",
                "close": "15:30",
                "source": "invented source",
                "reviewed": True,
            }
        )
    assert s.engine.settings.calendar == old_path
    assert s.engine.calendar.sessions == old_sessions
    assert s.config.read_text() == old_text


def test_connect_disconnect_does_not_submit_orders_and_uses_explicit_credentials(
    setup_service, monkeypatch
):
    s = setup_service
    before = accounting(s)
    with pytest.raises(SetupError, match="at least one"):
        s.connect()
    s.select_symbols({"symbols": ["DEMO"]})
    s.values = {"api_key": "key", "api_secret": "secret", "access_token": "session"}
    monkeypatch.setattr("trading_agent.api.setup.ReadOnlyKite", lambda *a: Mock())
    stream = Mock()
    factory = Mock(return_value=stream)
    monkeypatch.setattr("trading_agent.api.setup.QuoteStream", factory)
    s.start()
    s.connect()
    assert factory.call_args.kwargs["credentials"] == ("key", "session")
    stream.start.assert_called_once()
    with pytest.raises(SetupError, match="already requested"):
        s.connect()
    with pytest.raises(SetupError, match="Disconnect"):
        s.save_credentials({"api_key": "other", "api_secret": "othersecret"})
    with pytest.raises(SetupError, match="Disconnect"):
        s.select_symbols({"symbols": ["SECOND"]})
    s.disconnect()
    stream.close.assert_called_once()
    assert not s.engine.connected and s.stream is None
    assert accounting(s) == before
    assert Decimal(s.engine.snapshot(NOW)["cash"]) == Decimal("25000")


def test_automation_bound_account_setup_is_refused(setup_service):
    s = setup_service
    s.engine.automation = "bound"
    with pytest.raises(SetupError, match="manual account"):
        s.save_credentials({"api_key": "key", "api_secret": "secret"})


def test_manual_feed_callbacks_preserve_risk_and_latch_candle_failures(setup_service, monkeypatch):
    s = setup_service
    before = accounting(s)
    s.select_symbols({"symbols": ["DEMO"]})
    s.clock = lambda: NOW + timedelta(seconds=1)
    monkeypatch.setattr("trading_agent.api.setup.ReadOnlyKite", lambda *a: Mock())
    factory = Mock()
    monkeypatch.setattr("trading_agent.api.setup.QuoteStream", factory)
    s.prepare_stream()
    ingest, connected = factory.call_args.args[1:3]
    connected(True)
    ingest(quote(1))
    assert s.engine.snapshot(s.clock())["feed_connected"]
    assert accounting(s) == before  # Receiving data submits/reserves no order.
    connected(False)
    assert not s.engine.connected
    connected(True)
    s.clock = lambda: NOW + timedelta(seconds=2)
    monkeypatch.setattr(
        "trading_agent.api.setup.store_candles", Mock(side_effect=RuntimeError("storage fault"))
    )
    with pytest.raises(RuntimeError, match="storage fault"):
        ingest(quote(2))
    assert s.engine.faulted and not s.engine.connected
    assert accounting(s) == before


def test_setup_refuses_to_overwrite_external_economic_policy_changes(setup_service):
    s = setup_service
    changed = s.config.read_text().replace('starting_cash = "25000"', 'starting_cash = "30000"')
    assert changed != s.config.read_text()
    s.config.write_text(changed)
    with pytest.raises(SetupError, match="Financial policy"):
        s.select_symbols({"symbols": ["DEMO"]})
    assert s.config.read_text() == changed
    assert s.engine.settings.stream_tokens == ()


def test_manual_callback_counts_lock_wait_in_freshness_before_any_fill(setup_service, monkeypatch):
    import threading

    s = setup_service
    e = s.engine
    s.select_symbols({"symbols": ["DEMO"]})
    monkeypatch.setattr("trading_agent.api.setup.ReadOnlyKite", lambda *a: Mock())
    factory = Mock()
    monkeypatch.setattr("trading_agent.api.setup.QuoteStream", factory)
    s.prepare_stream()
    ingest = factory.call_args.args[1]
    e.set_connected(True)
    e.ingest(quote(1), NOW + timedelta(seconds=1))
    order = e.submit(
        candidate("waiting", now=NOW + timedelta(seconds=1)), NOW + timedelta(seconds=1)
    )
    assert order["state"] == "ACCEPTED"
    current = [NOW + timedelta(seconds=2)]
    started = threading.Event()
    clock_called = threading.Event()
    errors = []

    def clock():
        clock_called.set()
        return current[0]

    s.clock = clock

    def callback():
        started.set()
        try:
            ingest(quote(2))
        except Exception as error:
            errors.append(error)

    worker = threading.Thread(target=callback)
    with e.lock:
        worker.start()
        assert started.wait(1)
        read_clock_while_blocked = clock_called.wait(0.02)
        current[0] = NOW + timedelta(seconds=8)
    worker.join(2)
    assert not worker.is_alive() and not errors and not read_clock_while_blocked
    assert e.orders()[0]["state"] == "ACCEPTED" and e.orders()[0]["filled"] == 0
    assert Decimal(e.snapshot(current[0])["cash"]) == Decimal("25000")
    assert Decimal(e.snapshot(current[0])["fees"]) == 0
