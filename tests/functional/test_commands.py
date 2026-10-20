import json
from datetime import timedelta
from decimal import Decimal as D
from unittest.mock import Mock

import pytest
from conftest import NOW

from trading_agent.main import execute, parser
from trading_agent.models import Instrument


@pytest.fixture
def configuration(tmp_path, monkeypatch):
    calendar = tmp_path / "sessions.csv"
    calendar.write_text("date,open,close,source\n2026-10-20,09:15,15:30,synthetic-test\n")
    config = tmp_path / "settings.toml"
    config.write_text(f'database="{tmp_path / "account.db"}"\ncalendar="{calendar}"\n')
    monkeypatch.setattr("trading_agent.main.clock", lambda: NOW)
    return config


def command(configuration, *parts):
    return parser().parse_args(["--config", str(configuration), *parts])


def test_initialization_status_backup_and_verification(configuration, tmp_path):
    assert execute(command(configuration, "init-db"))["cash"] == "25000"
    assert execute(command(configuration, "status"))["positions"] == []
    assert execute(command(configuration, "verify-db"))["accounting"] == "reconciled"
    backup = tmp_path / "backup.db"
    assert execute(command(configuration, "backup", str(backup)))["backup"] == str(backup)
    assert backup.stat().st_mode & 0o777 == 0o600


def test_manual_token_file_is_private_and_exclusive(configuration, tmp_path, monkeypatch):
    monkeypatch.setattr("trading_agent.main.getpass.getpass", lambda message: "one-time-token")
    monkeypatch.setattr("trading_agent.main.exchange_token", lambda *args: "temporarysession123")
    output = tmp_path / ".env.session"
    args = command(configuration, "exchange-token", "--output", str(output))
    execute(args)
    assert output.read_text() == "export KITE_ACCESS_TOKEN='temporarysession123'\n"
    assert output.stat().st_mode & 0o777 == 0o600
    with pytest.raises(FileExistsError):
        execute(args)


def test_serve_startup_is_local_and_single_worker(configuration, monkeypatch):
    calls = []
    monkeypatch.setattr("trading_agent.main.configure_logging", lambda: None)
    monkeypatch.setattr("uvicorn.run", lambda app, **kwargs: calls.append(kwargs))
    assert execute(command(configuration, "serve")) is None
    assert calls[0]["host"] == "127.0.0.1" and calls[0]["workers"] == 1
    assert calls[0]["access_log"] is False and calls[0]["proxy_headers"] is False


def test_readonly_import_commands(configuration, monkeypatch):
    broker = Mock()
    broker.get_instruments.return_value = [
        Instrument(symbol="NSE:DEMO", token=1, tick_size=D(".05"))
    ]
    broker.get_historical_candles.return_value = []
    monkeypatch.setattr("trading_agent.main.ReadOnlyKite.from_environment", lambda: broker)
    assert execute(command(configuration, "instruments"))["stored"] == 1
    result = execute(
        command(
            configuration,
            "historical",
            "NSE:DEMO",
            "--start",
            NOW.isoformat(),
            "--end",
            (NOW + timedelta(minutes=5)).isoformat(),
        )
    )
    assert result["stored"] == 0


def test_environment_and_replay_entrypoint(configuration, tmp_path):
    from trading_agent.replay import demo

    assert execute(command(configuration, "environment"))["mode"] == "paper"
    demo_dir = tmp_path / "demo"
    expected = demo(demo_dir)
    instruments = tmp_path / "instruments.json"
    instruments.write_text(json.dumps([{"symbol": "NSE:DEMO", "token": 1, "tick_size": "0.05"}]))
    actual = execute(
        command(
            configuration,
            "replay",
            str(demo_dir / "events.jsonl"),
            "--instruments",
            str(instruments),
        )
    )
    assert actual == expected
    with pytest.raises(ValueError, match="unused"):
        execute(
            command(
                configuration,
                "replay",
                str(demo_dir / "events.jsonl"),
                "--instruments",
                str(instruments),
            )
        )
