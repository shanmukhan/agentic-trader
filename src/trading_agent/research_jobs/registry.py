"""Private immutable, copied inputs for isolated offline delivery research."""

import hashlib
import json
import os
import shutil
import stat
import tempfile
import tomllib
from dataclasses import asdict
from pathlib import Path
from typing import Any

from trading_agent.backtesting.report import code_digest
from trading_agent.daily_execution.contracts import DailyStrategy
from trading_agent.daily_execution.dataset import ExecutionDataset, QuoteEvent, ReviewEvent
from trading_agent.daily_research.dataset import DailyDataset
from trading_agent.execution.costs import charges_for
from trading_agent.risk.policy import policy_values
from trading_agent.settings import Settings

MAX_INPUT_BYTES = 32 * 1024 * 1024
MAX_ROWS = 100_000
LIMITATIONS = [
    "Offline paper research; no operator account, broker connection or orders are used.",
    "Only later observed bid/ask quotes fill; daily OHLC bars never fill orders.",
    "Legacy offline v1 semantics; connected strategy parity is not established.",
    "Out-of-sample evaluation is not declared; profitability is not validated.",
    "Historical source review, costs, custody and real-market acceptance remain unverified.",
]


def digest(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def runtime_definition(policy: Settings) -> dict[str, Any]:
    """Bind the implementation and exact observed paper fee assumptions before review."""
    return {
        "code_sha256": code_digest(),
        "charges": {key: str(value) for key, value in asdict(charges_for(policy)).items()},
    }


def private_json(path: Path, value: Any) -> None:
    """Replace one private JSON state atomically and durably."""
    content = json.dumps(value, sort_keys=True, indent=2).encode() + b"\n"
    fd, name = tempfile.mkstemp(prefix=".state-", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as file:
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        os.replace(name, path)
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        Path(name).unlink(missing_ok=True)


def private_directory(path: Path) -> None:
    if path.is_symlink():
        raise ValueError("private research directory cannot be a symlink")
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if not path.is_dir() or path.stat().st_mode & 0o077:
        raise ValueError("private research directory requires owner-only permissions")


def read_bytes(path: Path, limit: int = MAX_INPUT_BYTES) -> bytes:
    """Read a bounded regular file without following its final symlink or growth race."""
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, "rb") as file:
        before = os.fstat(file.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size > limit:
            raise ValueError("input must be a bounded regular file")
        content = file.read(limit + 1)
        after = os.fstat(file.fileno())
        if len(content) > limit or (before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
            after.st_size,
            after.st_mtime_ns,
            after.st_ctime_ns,
        ):
            raise ValueError("input changed during bounded read")
        return content


def read_private_json(path: Path, limit: int) -> Any:
    def unique(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError("duplicate research JSON field")
            result[key] = value
        return result

    def finite(value: str) -> None:
        raise ValueError("nonfinite research JSON value")

    return json.loads(read_bytes(path, limit), object_pairs_hook=unique, parse_constant=finite)


def file_hash(path: Path, limit: int = MAX_INPUT_BYTES) -> str:
    return hashlib.sha256(read_bytes(path, limit)).hexdigest()


def _validate(root: Path) -> tuple[DailyDataset, ExecutionDataset]:
    daily = DailyDataset(root / "daily")
    execution = ExecutionDataset(root / "execution", daily)
    if len(execution.manifest.instruments) > 10 or len(execution.sessions) > 252:
        raise ValueError("browser research supports at most ten symbols and 252 execution sessions")
    for number, _ in enumerate(daily.bars(), 1):
        if number > MAX_ROWS:
            raise ValueError("daily row limit exceeded")
    quotes, reviews = set(), set()
    for number, event in enumerate(execution.events(), 1):
        if number > MAX_ROWS:
            raise ValueError("execution row limit exceeded")
        if isinstance(event, QuoteEvent):
            quotes.add(event.quote.symbol)
        elif isinstance(event, ReviewEvent):
            reviews.add(event.review.symbol)
    symbols = {item.symbol for item in execution.manifest.instruments}
    if quotes != symbols or not symbols <= reviews:
        raise ValueError("each execution instrument requires observed quotes and explicit reviews")
    return daily, execution


def register_bundle(
    root: Path, daily: Path, execution: Path, strategy: Path, policy: Path, label: str
) -> dict[str, Any]:
    """CLI-only registration: copy bounded inputs; retain hashes, never operator paths/secrets."""
    if not isinstance(label, str) or not label.strip() or len(label) > 120:
        raise ValueError("resource label must contain one to 120 characters")
    for source in (daily, execution):
        if source.is_symlink() or not source.is_dir():
            raise ValueError("bundle must be a regular directory")
    paths = {
        "daily/manifest.json": daily / "manifest.json",
        "daily/daily.jsonl": daily / "daily.jsonl",
        "execution/manifest.json": execution / "manifest.json",
        "execution/events.jsonl": execution / "events.jsonl",
        "strategy.toml": strategy,
        "policy.toml": policy,
    }
    hashes = {name: file_hash(path) for name, path in paths.items()}
    if sum(path.stat().st_size for path in paths.values()) > MAX_INPUT_BYTES:
        raise ValueError("combined source input exceeds 32 MiB")
    definition = DailyStrategy.model_validate(tomllib.loads(read_bytes(strategy).decode("utf-8")))
    settings = Settings.model_validate(tomllib.loads(read_bytes(policy).decode("utf-8")))
    if settings.investment_horizon != "long_term":
        raise ValueError("browser backtests require a long-term economic policy")
    values = policy_values(settings)
    identity = {
        "source_hashes": hashes,
        "strategy": definition.model_dump(mode="json"),
        "policy": values,
        "runtime": runtime_definition(settings),
        "schema_version": 1,
    }
    private_directory(root)
    registry = root.resolve() / "resources"
    private_directory(registry)
    staging = Path(tempfile.mkdtemp(prefix=".register-", dir=registry))
    try:
        for section in ("daily", "execution"):
            (staging / section).mkdir(mode=0o700)
        for name, source in paths.items():
            if "/" not in name:
                continue  # Raw policy may contain operator paths or credentials; never copy it.
            shutil.copyfile(source, staging / name)
            (staging / name).chmod(0o600)
            if file_hash(staging / name) != hashes[name]:
                raise ValueError("input changed while copying")
        if any(file_hash(path) != hashes[name] for name, path in paths.items()):
            raise ValueError("input changed while registering")
        daily_set, execution_set = _validate(staging)
        public = {
            "label": label.strip(),
            "synthetic": bool(daily_set.manifest.synthetic or execution_set.manifest.synthetic),
            "strategy": identity["strategy"],
            "policy": values,
            "runtime": identity["runtime"],
            "coverage": {
                "daily_sessions": len(daily_set.manifest.sessions),
                "execution_sessions": len(execution_set.sessions),
                "symbols": [item.symbol for item in execution_set.manifest.instruments],
                "first_session": str(execution_set.sessions[0]),
                "last_session": str(execution_set.sessions[-1]),
            },
            "provenance": {
                "universe_kind": "point_in_time",
                "fill_model": "later-observed-bid-ask-v1",
                "semantics": "legacy-offline-v1",
                "connected_parity": "not_established",
                "out_of_sample": "not_declared",
                "source_hashes": hashes,
            },
            "limitations": LIMITATIONS,
        }
        identity["public_metadata"] = public
        sha = digest(identity)
        resource_id = "bundle-" + sha[:24]
        public = {**public, "resource_id": resource_id, "resource_sha256": sha}
        destination = registry / resource_id
        if destination.exists():
            return load_resource(root, resource_id)["public"]
        if len(list(registry.glob("bundle-*"))) >= 32:
            raise ValueError("registered resource limit reached")
        private_json(staging / "resource.json", {**identity, "public": public})
        os.rename(staging, destination)
        return public
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def load_resource(root: Path, resource_id: str) -> dict[str, Any]:
    import re

    if not re.fullmatch(r"bundle-[a-f0-9]{24}", resource_id):
        raise KeyError("resource not found")
    path = root / "resources" / resource_id
    if not path.exists() and not path.is_symlink():
        raise KeyError("resource not found")
    if path.is_symlink() or not path.is_dir():
        raise ValueError("resource directory changed")
    for section in ("daily", "execution"):
        if (path / section).is_symlink() or not (path / section).is_dir():
            raise ValueError("resource section changed")
    record = path / "resource.json"
    data = read_private_json(record, 128 * 1024)
    identity = {
        key: data[key]
        for key in (
            "source_hashes",
            "strategy",
            "policy",
            "runtime",
            "schema_version",
            "public_metadata",
        )
    }
    sha = digest(identity)
    if sha != data["public"]["resource_sha256"] or resource_id != "bundle-" + sha[:24]:
        raise ValueError("resource identity changed")
    if data["public"] != {
        **identity["public_metadata"],
        "resource_id": resource_id,
        "resource_sha256": sha,
    }:
        raise ValueError("public resource metadata changed")
    if (
        data["public"]["strategy"] != data["strategy"]
        or data["public"]["policy"] != data["policy"]
        or data["public"]["runtime"] != data["runtime"]
        or data["public"]["provenance"]["source_hashes"] != data["source_hashes"]
    ):
        raise ValueError("public resource definitions differ")
    for name in (
        "daily/manifest.json",
        "daily/daily.jsonl",
        "execution/manifest.json",
        "execution/events.jsonl",
    ):
        if file_hash(path / name) != data["source_hashes"][name]:
            raise ValueError("resource input changed")
    return data
