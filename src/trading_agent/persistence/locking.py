"""Nonblocking process ownership on POSIX and Windows, released by closing the fd."""

import errno
import os
import sys


def lock_exclusive(descriptor: int) -> None:
    """Acquire an exclusive advisory lock without waiting or truncating the file.

    All owners must use this helper. Windows locks the first byte, while POSIX
    locks the whole file. Keep the descriptor open for the full ownership period.
    """
    if sys.platform != "win32":
        import fcntl

        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        return

    import msvcrt

    position = os.lseek(descriptor, 0, os.SEEK_CUR)
    try:
        # Windows permits locking beyond EOF, including empty ownership files.
        # Never write the lock byte: a simultaneous owner may already hold it.
        os.lseek(descriptor, 0, os.SEEK_SET)
        try:
            msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
        except OSError as exc:
            if exc.errno in (errno.EACCES, errno.EAGAIN, errno.EDEADLK):
                raise BlockingIOError(errno.EAGAIN, "ownership lock is already held") from None
            raise
    finally:
        os.lseek(descriptor, position, os.SEEK_SET)
