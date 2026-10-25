"""Private immutable investment policy drafts, separate from operator account authority."""

import hashlib
import json
import math
import os
import re
import stat
import threading
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from copy import deepcopy
from pathlib import Path
from typing import Any

from trading_agent.investment_research.policy import POLICY_FIELDS, inspect_draft
from trading_agent.persistence.locking import lock_exclusive

MAX_DRAFTS = 100
MAX_RECORD_BYTES = 32 * 1024
MAX_COMBINED_BYTES = 1024 * 1024
DRAFT_ID = re.compile(r"draft-[a-f0-9]{64}")
_SAVE_LOCK = threading.RLock()
LIMITATIONS = [
    "Saved drafts are research specifications, not active investment policies.",
    "Saving a draft does not alter holdings, cash, proposals, strategies or broker connections.",
    "Draft activation and investment-policy backtesting are not implemented.",
    "A fully specified draft records choices; suitability and profitability remain unverified.",
]


class PolicyStoreError(RuntimeError):
    def __init__(self, code: str, message: str, status: int):
        super().__init__(message)
        self.code, self.message, self.status = code, message, status


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def strict_json(content: bytes) -> Any:
    """Reject ambiguous object keys, nonfinite constants and invalid UTF-8."""

    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate draft JSON field")
            result[key] = value
        return result

    def finite(value: str) -> None:
        raise ValueError("nonfinite draft JSON value")

    def number(value: str) -> float:
        parsed = float(value)
        if not math.isfinite(parsed):
            raise ValueError("nonfinite draft JSON number")
        return parsed

    return json.loads(
        content.decode("utf-8"),
        object_pairs_hook=unique,
        parse_constant=finite,
        parse_float=number,
    )


def preview_draft(payload: Any) -> dict[str, Any]:
    draft = inspect_draft(payload)
    return {
        "schema_version": 1,
        "draft": draft,
        "preview_sha256": hashlib.sha256(_canonical(draft)).hexdigest(),
    }


def _safe_path(path: Path) -> None:
    for item in reversed((path, *path.parents)):
        try:
            metadata = item.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(metadata.st_mode):
            raise ValueError("draft storage path cannot contain symlinks")
        if not stat.S_ISDIR(metadata.st_mode):
            raise ValueError("draft storage path must be a directory")


def _private(metadata: os.stat_result, *, directory: bool) -> None:
    kind = stat.S_ISDIR if directory else stat.S_ISREG
    if not kind(metadata.st_mode) or metadata.st_mode & 0o077 or metadata.st_uid != os.getuid():
        raise ValueError("draft storage requires owner-only regular files and directories")


class InvestmentPolicyStore:
    """GET and preview never create storage; save is the only filesystem mutation."""

    def __init__(self, root: Path):
        self.root = root.absolute()
        _safe_path(self.root)
        if self.root.exists():
            _private(self.root.stat(), directory=True)

    @contextmanager
    def _directory(self, *, create: bool = False) -> Iterator[int | None]:
        _safe_path(self.root)
        if not self.root.exists():
            if not create:
                yield None
                return
            self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        descriptor = os.open(self.root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
        try:
            _private(os.fstat(descriptor), directory=True)
            yield descriptor
        finally:
            os.close(descriptor)

    @staticmethod
    def _names(descriptor: int) -> list[str]:
        names = []
        for name in os.listdir(descriptor):
            if name.startswith("draft-"):
                if not name.endswith(".json") or not DRAFT_ID.fullmatch(name[:-5]):
                    raise ValueError("unexpected draft record name")
                names.append(name)
        if len(names) > MAX_DRAFTS:
            raise ValueError("saved draft count exceeds its storage limit")
        return sorted(names)

    @staticmethod
    def _read(descriptor: int, name: str) -> tuple[dict[str, Any], int]:
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=descriptor)
        with os.fdopen(fd, "rb") as stream:
            before = os.fstat(stream.fileno())
            _private(before, directory=False)
            if before.st_size > MAX_RECORD_BYTES:
                raise ValueError("draft record exceeds its read budget")
            content = stream.read(MAX_RECORD_BYTES + 1)
            after = os.fstat(stream.fileno())
            if len(content) > MAX_RECORD_BYTES or (
                before.st_size,
                before.st_mtime_ns,
                before.st_ctime_ns,
            ) != (after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise ValueError("draft record changed during bounded read")
        record = strict_json(content)
        if not isinstance(record, dict) or set(record) != {"draft_id", "draft"}:
            raise ValueError("invalid immutable draft record")
        draft = record["draft"]
        if not isinstance(draft, dict):
            raise ValueError("invalid immutable draft content")
        checked = preview_draft(
            {"label": draft.get("label"), "parameters": draft.get("parameters")}
        )
        draft_id = "draft-" + checked["preview_sha256"]
        if (
            _canonical(draft) != _canonical(checked["draft"])
            or record["draft_id"] != draft_id
            or name != draft_id + ".json"
        ):
            raise ValueError("immutable draft identity changed")
        return {"draft_id": draft_id, **draft}, len(content)

    @classmethod
    def _records(cls, descriptor: int) -> list[dict[str, Any]]:
        records, total = [], 0
        for name in cls._names(descriptor):
            record, size = cls._read(descriptor, name)
            total += size
            if total > MAX_COMBINED_BYTES:
                raise ValueError("saved drafts exceed their combined read budget")
            records.append(record)
        return records

    def list(self) -> dict[str, Any]:
        with self._directory() as descriptor:
            drafts = [] if descriptor is None else self._records(descriptor)
        return {
            "schema_version": 1,
            "field_definitions": deepcopy(POLICY_FIELDS),
            "drafts": drafts,
            "activation_supported": False,
            "backtest_supported": False,
            "limits": {
                "max_drafts": MAX_DRAFTS,
                "max_record_bytes": MAX_RECORD_BYTES,
                "max_combined_bytes": MAX_COMBINED_BYTES,
            },
            "limitations": list(LIMITATIONS),
        }

    def get(self, draft_id: str) -> dict[str, Any]:
        if not DRAFT_ID.fullmatch(draft_id):
            raise PolicyStoreError("DRAFT_NOT_FOUND", "Saved draft was not found.", 404)
        with self._directory() as descriptor:
            if descriptor is not None:
                try:
                    return self._read(descriptor, draft_id + ".json")[0]
                except FileNotFoundError:
                    pass
        raise PolicyStoreError("DRAFT_NOT_FOUND", "Saved draft was not found.", 404)

    @staticmethod
    def preview(payload: Any) -> dict[str, Any]:
        return preview_draft(payload)

    def save(
        self, payload: Any, preview_sha256: str, acknowledged: bool
    ) -> tuple[dict[str, Any], bool]:
        reviewed = preview_draft(payload)
        if acknowledged is not True:
            raise PolicyStoreError(
                "DRAFT_ACKNOWLEDGEMENT_REQUIRED", "Review and confirm this draft.", 422
            )
        if reviewed["preview_sha256"] != preview_sha256:
            raise PolicyStoreError(
                "DRAFT_PREVIEW_CHANGED",
                "Draft changed after review. Preview it again before saving.",
                409,
            )
        draft_id = "draft-" + reviewed["preview_sha256"]
        record = {"draft_id": draft_id, "draft": reviewed["draft"]}
        content = _canonical(record) + b"\n"
        if len(content) > MAX_RECORD_BYTES:
            raise PolicyStoreError("DRAFT_TOO_LARGE", "Draft exceeds the saved record limit.", 413)
        with _SAVE_LOCK, self._directory(create=True) as descriptor:
            assert descriptor is not None
            lock = os.open(
                ".lock",
                os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK,
                0o600,
                dir_fd=descriptor,
            )
            try:
                _private(os.fstat(lock), directory=False)
                try:
                    lock_exclusive(lock)
                except BlockingIOError:
                    raise PolicyStoreError(
                        "DRAFT_STORAGE_BUSY",
                        "Another process is saving a draft. Review saved drafts before retrying.",
                        409,
                    ) from None
                records = self._records(descriptor)
                for existing in records:
                    if existing["draft_id"] == draft_id:
                        return existing, False
                if len(records) >= MAX_DRAFTS:
                    raise PolicyStoreError("DRAFT_STORAGE_FULL", "Saved draft limit reached.", 429)
                used = sum(
                    os.stat(name, dir_fd=descriptor, follow_symlinks=False).st_size
                    for name in self._names(descriptor)
                )
                if used + len(content) > MAX_COMBINED_BYTES:
                    raise PolicyStoreError(
                        "DRAFT_STORAGE_FULL", "Saved draft storage budget reached.", 429
                    )
                temporary = ".pending-" + uuid.uuid4().hex
                try:
                    fd = os.open(
                        temporary,
                        os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                        0o600,
                        dir_fd=descriptor,
                    )
                    with os.fdopen(fd, "wb") as stream:
                        stream.write(content)
                        stream.flush()
                        os.fsync(stream.fileno())
                    os.link(
                        temporary,
                        draft_id + ".json",
                        src_dir_fd=descriptor,
                        dst_dir_fd=descriptor,
                        follow_symlinks=False,
                    )
                    os.fsync(descriptor)
                finally:
                    os.unlink(temporary, dir_fd=descriptor)
            finally:
                os.close(lock)
        return {"draft_id": draft_id, **reviewed["draft"]}, True
