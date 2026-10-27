"""Token-only synchronization: secret transport, private persistence and auth reload."""

import importlib.util
import json
import shlex
import sqlite3
import subprocess
import sys
from contextlib import closing
from decimal import Decimal
from pathlib import Path
from unittest.mock import Mock

import pytest
from conftest import NOW, TOKEN
from fastapi.testclient import TestClient
from pydantic import SecretStr

from trading_agent.api.app import create_app

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "token_sync", ROOT / "deployment/rpi/sync_operator_token.py"
)
sync = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sync)
NEW = "synced-test-operator-" + "b" * 32


@pytest.mark.parametrize(
    "assignment",
    [
        f"TRADING_OPERATOR_TOKEN={NEW}\n",
        f"export TRADING_OPERATOR_TOKEN='{NEW}' # private\n",
        f' TRADING_OPERATOR_TOKEN = "{NEW}"\n',
    ],
)
def test_only_literal_token_value_is_read(assignment):
    assert sync.read_token(assignment) == NEW


@pytest.mark.parametrize(
    "text",
    [
        "",
        "TRADING_OPERATOR_TOKEN=short\n",
        "TRADING_OPERATOR_TOKEN=${OTHER}\n",
        f"TRADING_OPERATOR_TOKEN={NEW}\nTRADING_OPERATOR_TOKEN={NEW}\n",
        'TRADING_OPERATOR_TOKEN="unterminated\n',
    ],
)
def test_invalid_input_fails_without_echoing_secret(text):
    with pytest.raises(ValueError) as error:
        sync.read_token(text)
    assert NEW not in str(error.value)


def test_only_token_changes_and_private_backup_preserves_previous_configuration(tmp_path):
    env = tmp_path / "service.env"
    previous = (
        f"TRADING_OPERATOR_TOKEN={TOKEN}\nTRADING_MODE=paper\n"
        "TRADING_PUBLIC_ORIGIN=https://shanmukhan.com\nKITE_API_KEY=synthetic-broker-key\n"
    )
    env.write_text(previous)
    backup = tmp_path / "backup"
    assert sync.replace_token(env, NEW, backup)
    assert env.read_text() == previous.replace(TOKEN, NEW)
    assert (backup / "agentic-trader.env").read_text() == previous
    assert env.stat().st_mode & 0o777 == 0o600
    assert backup.stat().st_mode & 0o777 == 0o700
    assert (backup / "agentic-trader.env").stat().st_mode & 0o777 == 0o600
    assert not sync.replace_token(env, NEW, tmp_path / "unused")
    assert not (tmp_path / "unused").exists()
    link = tmp_path / "link"
    link.symlink_to(env)
    with pytest.raises(ValueError, match="symlink"):
        sync.replace_token(link, TOKEN, tmp_path / "bad-backup")


def test_ssh_sends_secret_only_over_stdin_and_remote_program_compiles(tmp_path, monkeypatch):
    env = tmp_path / ".env"
    env.write_text(f"TRADING_OPERATOR_TOKEN={NEW}\nKITE_API_SECRET=private-broker-value\n")
    run = Mock()
    monkeypatch.setattr(sync.subprocess, "run", run)
    sync.sync("operator@pi.local", env)
    argv = run.call_args.args[0]
    assert NEW not in " ".join(argv)
    assert "private-broker-value" not in " ".join(argv)
    assert json.loads(run.call_args.kwargs["input"]) == {"token": NEW}
    assert "private-broker-value" not in run.call_args.kwargs["input"]
    assert 'systemctl","restart","agentic-trader' in argv[-1]
    with pytest.raises(ValueError, match="SSH"):
        sync.sync("-oProxyCommand=unexpected", env)


@pytest.mark.parametrize(
    "previous,changed,active",
    [
        (NEW, False, True),
        (NEW, False, False),
        ("short", True, False),
        ("bad+token/!" * 4, True, True),
        ("", True, True),
        ('"unterminated', True, False),
    ],
)
def test_generated_remote_program_repairs_existing_value_in_an_independent_process(
    tmp_path, monkeypatch, previous, changed, active
):
    env = tmp_path / "service.env"
    original = f"TRADING_OPERATOR_TOKEN={previous}\nTRADING_MODE=paper\n"
    env.write_text(original)
    local = tmp_path / ".env"
    local.write_text(f"TRADING_OPERATOR_TOKEN={NEW}\n")
    run = Mock()
    monkeypatch.setattr(sync.subprocess, "run", run)
    sync.sync("operator@pi.local", local)
    program = shlex.split(run.call_args.args[0][-1])[-1]
    program = program.replace("/etc/agentic-trader.env", str(env)).replace(
        "/var/backups/trading-operator-token-", str(tmp_path / "private-backup-")
    )
    # Isolate only external HTTP/systemd effects. Execute the exact generated Python
    # program to catch runtime import/name errors that compilation cannot detect.
    calls = tmp_path / "systemctl-calls.json"
    stub = """import io,json,subprocess,urllib.request
from pathlib import Path
class Response(io.BytesIO):
    status=200
urllib.request.urlopen=lambda *args,**kwargs:Response(b'{"mode":"paper"}')
"""
    stub += f"""
commands=[]
def systemctl(args,**kwargs):
    commands.append(args)
    Path({str(calls)!r}).write_text(json.dumps(commands))
    return subprocess.CompletedProcess(args, {0 if active else 3} if "is-active" in args else 0)
subprocess.run=systemctl
"""
    monkeypatch.undo()
    result = subprocess.run(
        [sys.executable, "-c", stub + program],
        input=json.dumps({"token": NEW}),
        text=True,
        check=True,
        capture_output=True,
    )
    outcome = json.loads(result.stdout)
    assert outcome["token_changed"] is changed
    assert outcome["service_restarted"] is (changed or not active)
    assert outcome["public_authenticated_read"] == 200
    if changed:
        backup = Path(outcome["private_backup"])
        assert backup.is_relative_to(tmp_path)
        assert (backup / "agentic-trader.env").read_text() == original
        assert (backup / "agentic-trader.env").stat().st_mode & 0o777 == 0o600
    else:
        assert outcome["private_backup"] is None
    assert NEW not in result.stdout + result.stderr
    assert env.read_text() == f"TRADING_OPERATOR_TOKEN={NEW}\nTRADING_MODE=paper\n"
    mutations = [command for command in json.loads(calls.read_text()) if "is-active" not in command]
    assert mutations == (
        [
            ["systemctl", "reset-failed", "agentic-trader"],
            ["systemctl", "restart", "agentic-trader"],
        ]
        if changed or not active
        else []
    )


def test_generate_token_repairs_weak_local_value_and_preserves_private_backup(
    tmp_path, monkeypatch
):
    env = tmp_path / ".env"
    previous = "TRADING_OPERATOR_TOKEN=short!\nKITE_API_SECRET=synthetic-local-only\n"
    env.write_text(previous)
    generate = Mock(return_value=NEW)
    monkeypatch.setattr(sync.secrets, "token_urlsafe", generate)
    backup = sync.generate_local_token(env)
    generate.assert_called_once_with(32)
    assert sync.read_token(env.read_text()) == NEW
    assert env.read_text() == previous.replace("short!", NEW)
    assert (backup / "agentic-trader.env").read_text() == previous
    assert env.stat().st_mode & 0o777 == 0o600
    assert backup.stat().st_mode & 0o777 == 0o700


def test_generate_cli_saves_strong_token_without_printing_or_sending_broker_secrets(tmp_path):
    fixture_script = tmp_path / "deployment/rpi/sync_operator_token.py"
    fixture_script.parent.mkdir(parents=True)
    fixture_script.write_text((ROOT / "deployment/rpi/sync_operator_token.py").read_text())
    env = tmp_path / ".env"
    env.write_text("TRADING_OPERATOR_TOKEN=short!\nKITE_API_SECRET=synthetic-local-only\n")
    code = """import json,re,runpy,subprocess,sys
def ssh(args,**kwargs):
    value=json.loads(kwargs['input'])
    assert set(value)=={'token'} and re.fullmatch(r'[A-Za-z0-9_-]{43}',value['token'])
    assert value['token'] not in ' '.join(args)
    assert 'synthetic-local-only' not in kwargs['input']
    return subprocess.CompletedProcess(args,0)
subprocess.run=ssh
sys.argv=['sync_operator_token.py','operator@pi.local','--generate']
runpy.run_path(SCRIPT,run_name='__main__')
"""
    result = subprocess.run(
        [sys.executable, "-c", "SCRIPT=" + repr(str(fixture_script)) + "\n" + code],
        check=True,
        capture_output=True,
        text=True,
    )
    token = sync.read_token(env.read_text())
    assert len(token) == 43 and token not in result.stdout + result.stderr
    assert "synthetic-local-only" not in result.stdout + result.stderr
    assert json.loads(result.stdout)["local_token_generated"] is True


def test_invalid_target_cannot_rotate_local_token_with_generate(tmp_path):
    fixture_script = tmp_path / "deployment/rpi/sync_operator_token.py"
    fixture_script.parent.mkdir(parents=True)
    fixture_script.write_text((ROOT / "deployment/rpi/sync_operator_token.py").read_text())
    env = tmp_path / ".env"
    original = f"TRADING_OPERATOR_TOKEN={NEW}\n"
    env.write_text(original)
    result = subprocess.run(
        [sys.executable, str(fixture_script), "bad host", "--generate"],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert env.read_text() == original
    assert not (tmp_path / "backups").exists()
    assert NEW not in result.stdout + result.stderr


def test_duplicate_existing_assignments_fail_without_change_or_backup(tmp_path):
    env = tmp_path / "service.env"
    original = "TRADING_OPERATOR_TOKEN=short\nTRADING_OPERATOR_TOKEN=another\n"
    env.write_text(original)
    with pytest.raises(ValueError, match="exactly one"):
        sync.replace_token(env, NEW, tmp_path / "backup")
    assert env.read_text() == original
    assert not (tmp_path / "backup").exists()


def test_cli_ssh_failure_is_concise_without_embedded_remote_source(tmp_path):
    fixture_script = tmp_path / "deployment/rpi/sync_operator_token.py"
    fixture_script.parent.mkdir(parents=True)
    fixture_script.write_text((ROOT / "deployment/rpi/sync_operator_token.py").read_text())
    (tmp_path / ".env").write_text(f"TRADING_OPERATOR_TOKEN={NEW}\n")
    # Execute the real CLI entry point with a stubbed SSH failure; no network.
    code = """import runpy,subprocess,sys
def fail(*args,**kwargs):
    raise subprocess.CalledProcessError(1,args[0])
subprocess.run=fail
sys.argv=["sync_operator_token.py", "not-used@pi.invalid"]
runpy.run_path(SCRIPT,run_name="__main__")
"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "SCRIPT=" + repr(str(fixture_script)) + "\n" + code,
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert "Token sync failed" in result.stderr
    assert "Traceback" not in result.stderr
    assert "sudo -n /usr/bin/python3 -c" not in result.stderr


def test_reloaded_operator_token_rejects_old_token_without_changing_finances(engine):
    def finances():
        with closing(sqlite3.connect(engine.settings.database)) as db:
            assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            assert Decimal(
                db.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0]
            ) == Decimal("25000.00")
            return {
                table: db.execute(f"SELECT * FROM {table}").fetchall()
                for table in ["meta", "orders", "fills", "positions"]
            }

    before = finances()
    for expected, rejected in [(TOKEN, NEW), (NEW, TOKEN)]:
        engine.settings = engine.settings.model_copy(
            update={
                "operator_token": SecretStr(expected),
                "public_origin": "https://shanmukhan.com",
                "public_path": "/agentic-trader",
            }
        )
        with TestClient(
            create_app(engine, clock=lambda: NOW, background=False),
            base_url="https://shanmukhan.com",
        ) as client:
            assert (
                client.get(
                    "/agentic-trader/api/workspace", headers={"Authorization": "Bearer " + rejected}
                ).status_code
                == 401
            )
            assert (
                client.get(
                    "/agentic-trader/api/workspace", headers={"Authorization": "Bearer " + expected}
                ).status_code
                == 200
            )
    assert finances() == before
