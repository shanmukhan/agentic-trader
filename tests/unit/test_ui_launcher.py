import errno
import hashlib
import importlib.util
import io
import json
import sys
import urllib.error
from pathlib import Path
from unittest.mock import Mock

import pytest


@pytest.fixture
def launcher(engine, monkeypatch):
    spec = importlib.util.spec_from_file_location("open_existing_ui", "scripts/open_existing_ui.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module.Settings, "load", lambda *a: engine.settings)
    monkeypatch.setattr(sys, "argv", ["open_existing_ui.py", "ignored.toml"])
    monkeypatch.setattr(module.webbrowser, "open", Mock())
    return module, engine


def test_matching_running_account_opens_browser_without_another_owner(launcher, monkeypatch):
    module, engine = launcher
    account = hashlib.sha256(str(engine.settings.database.resolve()).encode()).hexdigest()
    opener = Mock()
    opener.open.return_value = io.BytesIO(
        json.dumps({"account_id": account, "ui_version": module.__version__}).encode()
    )
    build = Mock(return_value=opener)
    monkeypatch.setattr(module.urllib.request, "build_opener", build)
    assert module.main() == 0
    module.webbrowser.open.assert_called_once_with("http://127.0.0.1:8000/workspace")
    assert isinstance(build.call_args.args[1], module.NoRedirect)
    assert (
        module.NoRedirect().redirect_request(None, None, 302, "", {}, "https://evil.test") is None
    )


def test_only_connection_refusal_requests_a_new_process(launcher, monkeypatch):
    module, _ = launcher
    opener = Mock()
    opener.open.side_effect = urllib.error.URLError(
        ConnectionRefusedError(errno.ECONNREFUSED, "no listener")
    )
    monkeypatch.setattr(module.urllib.request, "build_opener", lambda *a: opener)
    assert module.main() == 10
    module.webbrowser.open.assert_not_called()
    opener.open.side_effect = urllib.error.HTTPError(
        "http://127.0.0.1", 401, "Unauthorized", {}, None
    )
    assert module.main() == 1
    module.webbrowser.open.assert_not_called()


def test_mismatched_account_does_not_open_or_restart(launcher, monkeypatch):
    module, _ = launcher
    opener = Mock()
    opener.open.return_value = io.BytesIO(b'{"account_id":"another-account"}')
    monkeypatch.setattr(module.urllib.request, "build_opener", lambda *a: opener)
    assert module.main() == 1
    module.webbrowser.open.assert_not_called()


def test_old_ui_version_is_not_silently_reused(launcher, monkeypatch):
    module, engine = launcher
    account = hashlib.sha256(str(engine.settings.database.resolve()).encode()).hexdigest()
    opener = Mock()
    opener.open.return_value = io.BytesIO(
        json.dumps({"account_id": account, "ui_version": "old"}).encode()
    )
    monkeypatch.setattr(module.urllib.request, "build_opener", lambda *a: opener)
    assert module.main() == 1
    module.webbrowser.open.assert_not_called()


def test_launcher_is_executable_and_shell_syntax_is_valid():
    import subprocess

    assert Path("scripts/start_ui.sh").stat().st_mode & 0o100
    subprocess.run(["sh", "-n", "scripts/start_ui.sh"], check=True)
