"""One isolated running job, one queued job, and durable cancellation/publication."""

import copy
import os
import re
import signal
import sqlite3
import stat
import subprocess
import threading
import time
import uuid
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from trading_agent.persistence.locking import lock_exclusive
from trading_agent.research_jobs import isolation
from trading_agent.research_jobs.registry import (
    LIMITATIONS,
    load_resource,
    private_directory,
    private_json,
    read_private_json,
    runtime_definition,
)
from trading_agent.research_jobs.reports import verify_report
from trading_agent.settings import Settings

TERMINAL = {"succeeded", "failed", "cancelled", "interrupted"}


def _load_state(path: Path) -> dict[str, Any]:
    value = read_private_json(path, 16 * 1024)
    fields = {
        "job_id",
        "resource_id",
        "resource_sha256",
        "request_key",
        "state",
        "stage",
        "progress",
        "eta_seconds",
        "created_at",
        "updated_at",
        "report_id",
        "error",
        "semantics",
    }
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError("invalid job schema")
    for key, pattern in (
        ("job_id", r"[a-f0-9]{32}"),
        ("resource_id", r"bundle-[a-f0-9]{24}"),
        ("resource_sha256", r"[a-f0-9]{64}"),
        ("request_key", r"[A-Za-z0-9_-]{32,64}"),
    ):
        if not isinstance(value[key], str) or not re.fullmatch(pattern, value[key]):
            raise ValueError("invalid saved job identity")
    if (
        value["state"] not in TERMINAL | {"queued", "running"}
        or value["stage"] not in {"queued", "validating", "replaying", "verifying", "finished"}
        or value["semantics"] != "legacy-offline-v1"
        or value["eta_seconds"] is not None
        or (
            value["progress"] is not None
            and (type(value["progress"]) is not int or not 0 <= value["progress"] <= 100)
        )
        or value["report_id"] not in (None, value["job_id"])
    ):
        raise ValueError("invalid saved job state")
    for key in ("created_at", "updated_at"):
        if not isinstance(value[key], str) or len(value[key]) > 40:
            raise ValueError("invalid saved job time")
        if datetime.fromisoformat(value[key]).tzinfo is None:
            raise ValueError("saved job time must be aware")
    error = value["error"]
    messages = {
        "JOB_INTERRUPTED": "Server stopped; no automatic resume.",
        "JOB_FAILED": "Offline replay or artifact verification failed; no report published.",
    }
    if error is not None:
        if not isinstance(error, dict) or error.get("code") not in messages:
            raise ValueError("invalid saved error")
        value["error"] = {"code": error["code"], "message": messages[error["code"]]}
    return value


def now() -> str:
    return datetime.now(UTC).isoformat()


class JobError(Exception):
    def __init__(self, code: str, message: str, status: int = 409):
        self.code, self.message, self.status = code, message, status
        super().__init__(message)


class BacktestJobs:
    """Own only a private research directory, never an operator account or configuration."""

    def __init__(self, root: Path):
        private_directory(root)
        self.root = root.resolve()
        private_directory(self.root / "jobs")
        private_directory(self.root / "resources")
        self._owner = os.open(self.root / ".owner", os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
        try:
            owner_stat = os.fstat(self._owner)
            if not stat.S_ISREG(owner_stat.st_mode) or owner_stat.st_mode & 0o077:
                raise ValueError("research ownership file requires private regular permissions")
            lock_exclusive(self._owner)
        except (OSError, ValueError):
            os.close(self._owner)
            raise RuntimeError("research job directory is already owned") from None
        self.lock = threading.RLock()
        self._wake = threading.Event()
        self._closed = False
        self._process: subprocess.Popen[bytes] | None = None
        self._states: dict[str, dict[str, Any]] = {}
        for directory in sorted((self.root / "jobs").iterdir()):
            if not re.fullmatch(r"[a-f0-9]{32}", directory.name) or directory.is_symlink():
                continue
            if len(self._states) >= 100:
                os.close(self._owner)
                raise RuntimeError("research saved-job limit exceeded")
            try:
                private_directory(directory)
                state = _load_state(directory / "job.json")
                if state["job_id"] != directory.name:
                    raise ValueError("job identity differs")
                if state["state"] not in TERMINAL:
                    state.update(
                        state="interrupted",
                        stage="finished",
                        progress=None,
                        report_id=None,
                        updated_at=now(),
                        error={
                            "code": "JOB_INTERRUPTED",
                            "message": "Server stopped; no automatic resume.",
                        },
                    )
                    private_json(directory / "job.json", state)
                self._states[directory.name] = state
            except (OSError, ValueError, KeyError, TypeError):
                os.close(self._owner)
                raise RuntimeError("research job state is unreadable") from None
        try:
            self.capability = isolation.capability(self.root)
        except Exception:
            os.close(self._owner)
            raise
        self._thread = threading.Thread(target=self._loop, name="isolated-research", daemon=True)
        self._thread.start()

    def _save(self, state: dict[str, Any]) -> None:
        state["updated_at"] = now()
        private_json(self.root / "jobs" / state["job_id"] / "job.json", state)

    def resources(self) -> dict[str, Any]:
        directories = sorted((self.root / "resources").glob("bundle-*"))
        if len(directories) > 32:
            raise JobError("RESOURCE_LIMIT_EXCEEDED", "Registered resource limit exceeded.", 503)
        resources = []
        for directory in directories:
            try:
                resources.append(load_resource(self.root, directory.name)["public"])
            except (OSError, ValueError, KeyError):
                raise JobError(
                    "INPUT_INTEGRITY_FAILED", "A registered resource changed.", 503
                ) from None
        return {
            "schema_version": 1,
            "resources": resources,
            "limits": {**isolation.LIMITS, "max_saved_jobs": 100, "max_resources": 32},
            "capability": self.capability,
            "limitations": LIMITATIONS,
        }

    def jobs(self) -> list[dict[str, Any]]:
        with self.lock:
            return [
                copy.deepcopy(row)
                for row in sorted(
                    self._states.values(),
                    key=lambda row: (row["created_at"], row["job_id"]),
                    reverse=True,
                )
            ]

    def job(self, job_id: str) -> dict[str, Any]:
        with self.lock:
            if job_id not in self._states:
                raise JobError("JOB_NOT_FOUND", "Research job not found.", 404)
            return copy.deepcopy(self._states[job_id])

    def submit(
        self, resource_id: str, resource_sha256: str, request_key: str, acknowledged: bool
    ) -> tuple[dict[str, Any], bool]:
        if (
            acknowledged is not True
            or not isinstance(request_key, str)
            or not isinstance(resource_sha256, str)
            or not isinstance(resource_id, str)
            or not re.fullmatch(r"[a-zA-Z0-9_-]{32,64}", request_key)
            or not re.fullmatch(r"[a-f0-9]{64}", resource_sha256)
        ):
            raise JobError("INVALID_SCHEMA", "Review and acknowledge a registered resource.", 422)
        with self.lock:
            for row in self._states.values():
                if row["request_key"] == request_key:
                    if (row["resource_id"], row["resource_sha256"]) != (
                        resource_id,
                        resource_sha256,
                    ):
                        raise JobError(
                            "IDEMPOTENCY_CONFLICT", "Request key belongs to another request."
                        )
                    return copy.deepcopy(row), False
            if self._closed or not self.capability["available"]:
                raise JobError("JOB_ISOLATION_UNAVAILABLE", self.capability["reason"], 503)
            if len(self._states) >= 100:
                raise JobError(
                    "JOB_STORAGE_FULL", "Saved job limit reached; retain audit evidence.", 429
                )
            if sum(row["state"] not in TERMINAL for row in self._states.values()) >= 2:
                raise JobError(
                    "JOB_QUEUE_FULL", "One running and one queued job are already admitted.", 429
                )
            try:
                record = load_resource(self.root, resource_id)
            except KeyError:
                raise JobError(
                    "RESOURCE_NOT_FOUND", "Registered research resource not found.", 404
                ) from None
            except (OSError, ValueError):
                raise JobError(
                    "INPUT_INTEGRITY_FAILED", "Registered research inputs changed."
                ) from None
            if record["public"]["resource_sha256"] != resource_sha256:
                raise JobError("INPUT_INTEGRITY_FAILED", "Resource hash changed; review it again.")
            if record["runtime"] != runtime_definition(Settings.model_validate(record["policy"])):
                raise JobError(
                    "RESEARCH_VERSION_CHANGED",
                    "Research code or fee assumptions changed; register and review a new bundle.",
                )
            job_id = uuid.uuid4().hex
            directory = self.root / "jobs" / job_id
            directory.mkdir(mode=0o700)
            (directory / "tmp").mkdir(mode=0o700)
            created = now()
            state = {
                "job_id": job_id,
                "resource_id": resource_id,
                "resource_sha256": resource_sha256,
                "request_key": request_key,
                "state": "queued",
                "stage": "queued",
                "progress": None,
                "eta_seconds": None,
                "created_at": created,
                "updated_at": created,
                "report_id": None,
                "error": None,
                "semantics": "legacy-offline-v1",
            }
            self._save(state)
            self._states[job_id] = state
            self._wake.set()
            return copy.deepcopy(state), True

    def cancel(self, job_id: str) -> dict[str, Any]:
        with self.lock:
            state = self._states.get(job_id)
            if state is None:
                raise JobError("JOB_NOT_FOUND", "Research job not found.", 404)
            if state["state"] not in TERMINAL:
                state.update(
                    state="cancelled", stage="finished", progress=None, error=None, report_id=None
                )
                self._save(state)  # Durable cancellation wins before any later publication.
                if self._process is not None and getattr(self, "_active_id", None) == job_id:
                    self._terminate(self._process)
            return copy.deepcopy(state)

    @staticmethod
    def _terminate(process: subprocess.Popen[bytes]) -> None:
        if process.poll() is None:
            with suppress(ProcessLookupError):
                os.killpg(process.pid, signal.SIGKILL)

    def _loop(self) -> None:
        while True:
            self._wake.wait()
            self._wake.clear()
            with self.lock:
                if self._closed:
                    return
                queued = next(
                    (row for row in self._states.values() if row["state"] == "queued"), None
                )
                if queued is None:
                    continue
                queued.update(state="running", stage="validating", progress=None)
                self._save(queued)
                self._active_id = queued["job_id"]
            try:
                self._run(queued)
            except Exception:
                with self.lock:
                    if queued["state"] not in TERMINAL:
                        queued.update(
                            state="failed",
                            stage="finished",
                            progress=None,
                            error={
                                "code": "JOB_FAILED",
                                "message": "Offline replay or artifact verification failed; "
                                "no report published.",
                            },
                        )
                        self._save(queued)
            finally:
                with self.lock:
                    if self._process is not None:
                        self._terminate(self._process)
                        with suppress(subprocess.TimeoutExpired, ProcessLookupError):
                            self._process.wait(timeout=5)
                    self._process = None
                    self._active_id = None
                self._wake.set()

    def _run(self, state: dict[str, Any]) -> None:
        record = load_resource(self.root, state["resource_id"])
        if record["public"]["resource_sha256"] != state["resource_sha256"]:
            raise ValueError("request input changed")
        if record["runtime"] != runtime_definition(Settings.model_validate(record["policy"])):
            raise ValueError("research implementation changed")
        work = self.root / "jobs" / state["job_id"]
        source = self.root / "resources" / state["resource_id"]
        with (work / "worker.log").open("xb") as log:
            os.chmod(work / "worker.log", 0o600)
            with self.lock:
                if state["state"] in TERMINAL:
                    return
                self._process = subprocess.Popen(
                    isolation.command(work, source, state["resource_id"]),
                    cwd=work,
                    env=isolation.environment(work),
                    stdin=subprocess.DEVNULL,
                    stdout=log,
                    stderr=log,
                    start_new_session=True,
                )
                process = self._process
                state.update(stage="replaying", progress=None)
                self._save(state)
            deadline = time.monotonic() + isolation.LIMITS["wall_seconds"]
            while process.poll() is None:
                with self.lock:
                    if state["state"] in TERMINAL:
                        self._terminate(process)
                        return
                files = list(work.rglob("*"))
                if (
                    time.monotonic() > deadline
                    or len(files) > 64
                    or any(path.is_symlink() for path in files)
                    or (work / "worker.log").stat().st_size > isolation.LIMITS["max_log_bytes"]
                    or sum(path.stat().st_size for path in files if path.is_file())
                    > isolation.LIMITS["max_output_bytes"]
                ):
                    self._terminate(process)
                    raise RuntimeError("worker budget exceeded")
                self._wake.wait(0.05)
                self._wake.clear()
            if process.returncode != 0:
                raise RuntimeError("worker failed")
        with self.lock:
            if state["state"] in TERMINAL:
                return
            state.update(stage="verifying", progress=None)
            self._save(state)
        current = load_resource(self.root, state["resource_id"])
        public_report = verify_report(work / "result", current, state["job_id"])
        with self.lock:
            if state["state"] in TERMINAL:
                return  # Cancellation and publication serialize on the same durable state lock.
            private_json(work / "published.json", public_report)
            state.update(
                state="succeeded",
                stage="finished",
                progress=100,
                report_id=state["job_id"],
                error=None,
            )
            self._save(state)

    def report(self, report_id: str) -> dict[str, Any]:
        state = self.job(report_id)
        if state["state"] != "succeeded":
            raise JobError(
                "REPORT_NOT_AVAILABLE", "This job has no published verified report.", 404
            )
        try:
            record = load_resource(self.root, state["resource_id"])
            if record["public"]["resource_sha256"] != state["resource_sha256"]:
                raise ValueError("resource differs")
            verified = verify_report(self.root / "jobs" / report_id / "result", record, report_id)
            published = read_private_json(
                self.root / "jobs" / report_id / "published.json", 4 * 1024**2
            )
            if verified != published:
                raise ValueError("published report differs")
            return verified
        except (OSError, ValueError, KeyError, TypeError, sqlite3.Error):
            raise JobError(
                "REPORT_INTEGRITY_FAILED", "Report integrity could not be verified.", 503
            ) from None

    def close(self) -> None:
        with self.lock:
            if self._closed:
                return
            self._closed = True
            for row in self._states.values():
                if row["state"] not in TERMINAL:
                    row.update(
                        state="interrupted",
                        stage="finished",
                        progress=None,
                        error={
                            "code": "JOB_INTERRUPTED",
                            "message": "Server stopped; no automatic resume.",
                        },
                    )
                    self._save(row)
            if self._process:
                self._terminate(self._process)
            self._wake.set()
        self._thread.join(timeout=6)
        os.close(self._owner)
