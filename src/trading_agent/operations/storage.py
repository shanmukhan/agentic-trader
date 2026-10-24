"""Private atomic operation checkpoints, flushed before potentially ambiguous I/O."""

import os
from pathlib import Path

from trading_agent.api.setup import private_write


def durable_write(path: Path, content: str) -> None:
    private_write(path, content)
    for directory in (path.parent, path.parent.parent):
        descriptor = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
