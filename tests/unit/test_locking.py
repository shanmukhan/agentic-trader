import errno
import os
import subprocess
import sys
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from trading_agent.persistence.locking import lock_exclusive


def test_process_ownership_denied_until_descriptor_closes(tmp_path):
    path = tmp_path / "owner"
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    probe = (
        "import os, sys; from trading_agent.persistence.locking import lock_exclusive; "
        "fd = os.open(sys.argv[1], os.O_RDWR); lock_exclusive(fd)"
    )
    try:
        lock_exclusive(descriptor)
        blocked = subprocess.run([sys.executable, "-c", probe, str(path)], capture_output=True)
        assert blocked.returncode != 0
        assert b"BlockingIOError" in blocked.stderr
    finally:
        os.close(descriptor)
    available = subprocess.run([sys.executable, "-c", probe, str(path)], capture_output=True)
    assert available.returncode == 0, available.stderr.decode()
    assert path.read_bytes() == b""


@pytest.mark.parametrize("contents", [b"", b"existing owner metadata"])
def test_windows_adapter_locks_first_byte_without_mutation(tmp_path, monkeypatch, contents):
    path = tmp_path / "owner"
    path.write_bytes(contents)
    descriptor = os.open(path, os.O_RDWR)
    observed = []
    fake = SimpleNamespace(LK_NBLCK=123)
    fake.locking = Mock(side_effect=lambda fd, mode, count: observed.append(os.lseek(fd, 0, 1)))
    monkeypatch.setitem(sys.modules, "msvcrt", fake)
    monkeypatch.setattr(sys, "platform", "win32")
    try:
        os.lseek(descriptor, 5, os.SEEK_SET)
        lock_exclusive(descriptor)
        fake.locking.assert_called_once_with(descriptor, 123, 1)
        assert observed == [0]
        assert os.lseek(descriptor, 0, os.SEEK_CUR) == 5
    finally:
        os.close(descriptor)
    assert path.read_bytes() == contents


@pytest.mark.parametrize("error", [errno.EACCES, errno.EAGAIN, errno.EDEADLK, errno.EBADF])
def test_windows_busy_is_nonblocking_and_errors_preserve_offset(tmp_path, monkeypatch, error):
    descriptor = os.open(tmp_path / "owner", os.O_CREAT | os.O_RDWR, 0o600)
    fake = SimpleNamespace(LK_NBLCK=123, locking=Mock(side_effect=OSError(error, "failure")))
    monkeypatch.setitem(sys.modules, "msvcrt", fake)
    monkeypatch.setattr(sys, "platform", "win32")
    try:
        os.lseek(descriptor, 3, os.SEEK_SET)
        expected = OSError if error == errno.EBADF else BlockingIOError
        with pytest.raises(expected) as failure:
            lock_exclusive(descriptor)
        assert failure.value.errno == (errno.EBADF if error == errno.EBADF else errno.EAGAIN)
        assert os.lseek(descriptor, 0, os.SEEK_CUR) == 3
    finally:
        os.close(descriptor)
