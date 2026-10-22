"""Simulated denial/limit protocols; these tests do not certify a native sandbox."""

import errno
import os
import subprocess
import sys
from pathlib import Path

import pytest

from trading_agent.research_jobs import isolation, worker
from trading_agent.research_jobs.registry import read_bytes, read_private_json


@pytest.mark.parametrize("missing", [None, "read", "write", "network"])
def test_probe_requires_all_denials_and_can_write_own_work(tmp_path, monkeypatch, capsys, missing):
    outside = tmp_path / "outside"
    outside.write_bytes(b"harmless sentinel")
    work = tmp_path / "work"
    (work / "tmp").mkdir(parents=True)
    monkeypatch.chdir(work)
    monkeypatch.setattr(sys, "argv", [str(worker.__file__), "--probe", str(outside)])
    calls = []
    monkeypatch.setattr(isolation, "apply_limits", lambda: calls.append("limits"))
    original_read = Path.read_bytes
    original_open = os.open

    def read(path):
        if path == outside and missing != "read":
            raise PermissionError(errno.EPERM, "simulated sandbox denial")
        return original_read(path)

    def opening(path, flags, *args, **kwargs):
        if path == outside and missing != "write":
            raise PermissionError(errno.EACCES, "simulated sandbox denial")
        return original_open(path, flags, *args, **kwargs)

    class Connection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def settimeout(self, timeout):
            pass

        def connect(self, address):
            # A refused connection is not evidence of an OS network prohibition.
            raise OSError(errno.ECONNREFUSED if missing == "network" else errno.EPERM, "test")

    monkeypatch.setattr(Path, "read_bytes", read)
    monkeypatch.setattr("os.open", opening)
    monkeypatch.setattr("socket.socket", lambda: Connection())
    assert worker.main() == (0 if missing is None else 2)
    assert calls == ["limits"]
    assert capsys.readouterr().out == ("isolated-limits-ok\n" if missing is None else "")
    assert not (work / "tmp" / "inside").exists()


def test_hard_limit_set_failure_is_not_ignored(monkeypatch):
    calls = []

    def failed(kind, maximum):
        calls.append((kind, maximum))
        raise ValueError("simulated unsupported hard limit")

    monkeypatch.setattr(isolation.resource, "setrlimit", failed)
    with pytest.raises(ValueError):
        isolation.apply_limits()
    assert calls == [(isolation.resource.RLIMIT_AS, (2 * 1024**3, 2 * 1024**3))]


def test_hard_limit_values_are_verified_after_setting(monkeypatch):
    monkeypatch.setattr(isolation.resource, "setrlimit", lambda *_: None)
    monkeypatch.setattr(isolation.resource, "getrlimit", lambda _: (-1, -1))
    with pytest.raises(RuntimeError, match="could not be enforced"):
        isolation.apply_limits()


def test_capability_probe_failure_is_sanitized_and_never_changes_parent_limits(
    tmp_path, monkeypatch
):
    monkeypatch.setattr(isolation.platform, "system", lambda: "Darwin")
    original = Path.is_file
    monkeypatch.setattr(
        Path,
        "is_file",
        lambda path: True if str(path) == "/usr/bin/sandbox-exec" else original(path),
    )

    def prohibited(*args):
        pytest.fail("operator process limits must never change")

    monkeypatch.setattr(isolation.resource, "setrlimit", prohibited)

    def failed(command, **kwargs):
        assert command[:2] == ["/usr/bin/sandbox-exec", "-p"]
        assert "(deny network*)" in command[2]
        assert kwargs["timeout"] == 5
        assert "PYTHONPATH" not in kwargs["env"]
        raise subprocess.TimeoutExpired(command, 5, stderr="private diagnostic")

    monkeypatch.setattr(isolation.subprocess, "run", failed)
    result = isolation.capability(tmp_path)
    assert result["available"] is False
    assert "private" not in result["reason"]
    assert list(tmp_path.iterdir()) == []


def test_bounded_read_refuses_symlinks_fifos_and_oversized_files(tmp_path):
    regular = tmp_path / "large"
    regular.write_bytes(b"12345")
    with pytest.raises(ValueError):
        read_bytes(regular, 4)
    alias = tmp_path / "alias"
    alias.symlink_to(regular)
    with pytest.raises(OSError):
        read_bytes(alias, 10)
    fifo = tmp_path / "pipe"
    os.mkfifo(fifo)
    with pytest.raises(ValueError):
        read_bytes(fifo, 10)


@pytest.mark.parametrize("text", ['{"a":1,"a":2}', '{"a":NaN}', '{"a":Infinity}'])
def test_private_json_refuses_ambiguous_or_nonfinite_evidence(tmp_path, text):
    path = tmp_path / "state.json"
    path.write_text(text)
    with pytest.raises(ValueError):
        read_private_json(path, 1024)
