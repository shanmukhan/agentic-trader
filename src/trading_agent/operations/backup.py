"""Stopped-owner, source-preserving backups and isolated verification. Never recover orders."""

import fcntl
import hashlib
import json
import os
import re
import sqlite3
import time
import tomllib
from contextlib import closing
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from trading_agent.desk.contracts import AnalysisProfile
from trading_agent.desk.preparation import saved_profile
from trading_agent.models import stamp
from trading_agent.observability.preflight import _account
from trading_agent.operations.report import account_id
from trading_agent.settings import Settings

MAX_FILE = 128 * 1024**2
MAX_TOTAL = 512 * 1024**2
MAX_FILES = 256


def write_new(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with os.fdopen(os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "wb") as file:
        file.write(data)
        file.flush()
        os.fsync(file.fileno())
    for directory in (path.parent, path.parent.parent):
        descriptor = os.open(directory, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def read_file(path: Path, limit: int = MAX_FILE) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > limit:
        raise ValueError("backup reference missing, unsafe or exceeds budget")
    with path.open("rb") as file:
        data = file.read(limit + 1)
    if len(data) > limit:
        raise ValueError("backup file exceeds budget")
    return data


def create_package(settings: Settings, config: Path, output: Path, now: datetime) -> dict[str, Any]:
    if "operator_token" in tomllib.loads(read_file(config).decode()):
        raise ValueError("keep operator credentials in the private environment, outside backups")
    loaded = Settings.load(config)
    if loaded.model_dump(exclude={"operator_token"}) != settings.model_dump(
        exclude={"operator_token"}
    ):
        raise ValueError("backup config differs from owning account")
    if settings.database.is_symlink() or not settings.database.is_file():
        raise ValueError("existing regular ledger required")
    # Same advisory owner lock, without constructing Database or PaperBroker.
    fd = os.open(str(settings.database) + ".lock", os.O_RDWR | os.O_NOFOLLOW)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        original = _account(settings)
        identity_keys = (
            "horizon_matches",
            "initial_cash_matches",
            "risk_policy_matches",
            "charges_match",
        )
        if not all(original[key] for key in identity_keys):
            raise ValueError("backup account identity mismatch")
        refs = {config.resolve(): "config", settings.calendar.resolve(): "calendar"}

        def include(path: Path, role: str) -> None:
            if path.is_symlink():
                raise ValueError("symbolic link in backup references")
            if path.is_dir():
                for child in sorted(path.rglob("*")):
                    if child.is_symlink():
                        raise ValueError("symbolic link in backup references")
                    if child.is_file():
                        refs[child.resolve()] = role
                        if len(refs) > MAX_FILES:
                            raise ValueError("too many backup artifacts")
            else:
                read_file(path)
                refs[path.resolve()] = role

        profile = (
            Path(os.environ["TRADING_ANALYSIS_PROFILE"])
            if os.environ.get("TRADING_ANALYSIS_PROFILE")
            else saved_profile(SimpleNamespace(settings=settings))
        )
        if profile:
            from trading_agent.daily_research.dataset import DailyDataset

            spec = AnalysisProfile.load(profile)
            DailyDataset(spec.daily_dataset)  # Validate declared data hashes before copying.
            include(profile, "profile")
            include(spec.daily_dataset, "daily_data")
            if spec.model_directory:
                include(spec.model_directory, "model")
            root = settings.database.with_suffix(".analysis")
            if profile.parent.parent.resolve() == root.resolve():
                include(profile.parent, "preparation_sources")
                include(root / "active.json", "active_pointer")
        # Explicit preparation model may be used for the next reviewed installation.
        if os.environ.get("TRADING_PREPARATION_MODEL"):
            include(Path(os.environ["TRADING_PREPARATION_MODEL"]), "preparation_model")
        if config.is_symlink() or settings.calendar.is_symlink():
            raise ValueError("unsafe config/calendar reference")
        output.mkdir(parents=True, exist_ok=False, mode=0o700)
        manifest: dict[str, Any] = {
            "schema_version": 1,
            "state": "finished",
            "observed_at": stamp(now),
            "account_id": account_id(settings.database),
            "files": {},
            "references": [],
            "ready_for_live": False,
            "credentials_included": False,
            "automatic_service_restore": False,
        }
        total = 0

        def record(name: str, data: bytes) -> None:
            nonlocal total
            total += len(data)
            if total > MAX_TOTAL:
                raise ValueError("backup package exceeds budget")
            write_new(output / name, data)
            manifest["files"][name] = hashlib.sha256(data).hexdigest()

        for index, (source, role) in enumerate(sorted(refs.items())):
            name = f"artifacts/{index:04d}"
            record(name, read_file(source))
            manifest["references"].append({"original": str(source), "stored": name, "role": role})
        destination = output / "ledger.sqlite3"
        write_new(destination, b"")
        with (
            closing(
                sqlite3.connect(settings.database.resolve().as_uri() + "?mode=ro", uri=True)
            ) as source_db,
            closing(sqlite3.connect(destination)) as target_db,
        ):
            deadline = time.monotonic() + 30

            def progress(status: int, remaining: int, total: int) -> None:
                if time.monotonic() > deadline:
                    raise TimeoutError("backup exceeded time budget")

            source_db.backup(target_db, pages=256, progress=progress)
        data = read_file(destination)
        total += len(data)
        if total > MAX_TOTAL:
            raise ValueError("backup package exceeds budget")
        manifest["files"]["ledger.sqlite3"] = hashlib.sha256(data).hexdigest()
        verified = _account(settings.model_copy(update={"database": destination}))
        if verified != original:
            raise ValueError("backup ledger differs from stopped source")
        for ref in manifest["references"]:
            if (
                hashlib.sha256(read_file(Path(ref["original"]))).hexdigest()
                != manifest["files"][ref["stored"]]
            ):
                raise ValueError("referenced artifact changed during backup")
        record("evidence.json", (json.dumps(original, sort_keys=True) + "\n").encode())
        # A crash/disk-full leaves no completion manifest; never delete the failing evidence.
        write_new(
            output / "manifest.json",
            (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode(),
        )
        return {
            "output": str(output),
            "verified": True,
            "files": len(manifest["files"]),
            "cash": verified["cash"],
            "fees": verified["fees"],
            "pending_orders": verified["pending_orders"],
            "ready_for_live": False,
        }
    finally:
        os.close(fd)


def restore_drill(settings: Settings, package: Path, output: Path) -> dict[str, Any]:
    if package.is_symlink() or (package / "artifacts").is_symlink():
        raise ValueError("unsafe backup directory")
    manifest = json.loads(read_file(package / "manifest.json", 1_000_000))
    if (
        manifest.get("schema_version") != 1
        or manifest.get("state") != "finished"
        or manifest.get("account_id") != account_id(settings.database)
        or not 2 <= len(manifest["files"]) <= MAX_FILES + 2
        or not {"ledger.sqlite3", "evidence.json"} <= set(manifest["files"])
    ):
        raise ValueError("backup identity/manifest invalid")
    total = 0
    # Validate before creating a destination; never interpret original paths as write targets.
    for name, expected in manifest["files"].items():
        if not re.fullmatch(r"(?:artifacts/\d{4}|ledger\.sqlite3|evidence\.json)", name):
            raise ValueError("unsafe backup member")
        data = read_file(package / name)
        total += len(data)
        if total > MAX_TOTAL or hashlib.sha256(data).hexdigest() != expected:
            raise ValueError("backup hash/budget verification failed")
    if output.resolve() == settings.database.parent.resolve() or output.resolve().is_relative_to(
        package.resolve()
    ):
        raise ValueError("drill destination must be separate")
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    for name, expected in manifest["files"].items():
        data = read_file(package / name)
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError("backup changed during restore")
        write_new(output / name, data)
    verified = _account(settings.model_copy(update={"database": output / "ledger.sqlite3"}))
    if verified != json.loads(read_file(output / "evidence.json")):
        raise ValueError("restored ledger differs from backup evidence")
    if not all(
        verified[key]
        for key in (
            "horizon_matches",
            "initial_cash_matches",
            "risk_policy_matches",
            "charges_match",
        )
    ):
        raise ValueError("restored account policy mismatch")
    result = {
        "state": "verified",
        "cash": verified["cash"],
        "fees": verified["fees"],
        "pending_orders": verified["pending_orders"],
        "positions": verified["positions"],
        "service_started": False,
        "paths_rebound": False,
        "ready_for_live": False,
    }
    write_new(
        output / "references.json", (json.dumps(manifest["references"], indent=2) + "\n").encode()
    )
    write_new(output / "restore-result.json", (json.dumps(result, indent=2) + "\n").encode())
    return result
