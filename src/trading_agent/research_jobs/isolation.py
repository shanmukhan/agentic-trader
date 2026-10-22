"""Fail-closed process sandbox and hard per-worker resource budgets."""

import json
import platform
import resource
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

LIMITS = {
    "worker_slots": 1,
    "queue_slots": 1,
    "wall_seconds": 60,
    "cpu_seconds": 30,
    "memory_bytes": 2 * 1024**3,
    "max_input_bytes": 32 * 1024**2,
    "max_output_bytes": 128 * 1024**2,
    "max_file_bytes": 32 * 1024**2,
    "max_log_bytes": 64 * 1024,
    "max_rows": 100_000,
}


def environment(work: Path) -> dict[str, str]:
    """Allowlist only; no operator token, broker credentials, proxy or config environment."""
    return {
        "PATH": "/usr/bin:/bin",
        "HOME": str(work),
        "TMPDIR": str(work / "tmp"),
        "LANG": "C.UTF-8",
        "OPENBLAS_NUM_THREADS": "1",
        "OMP_NUM_THREADS": "1",
    }


def sandbox_profile(work: Path, registered: Path) -> str:
    def subpath(path: Path | str) -> str:
        return "(subpath " + json.dumps(str(Path(path).resolve())) + ")"

    reads = {
        Path(sys.prefix).resolve(),
        Path(sys.base_prefix).resolve(),
        Path(__file__).resolve().parents[1],
        registered.resolve(),
        work.resolve(),
        Path("/usr/lib"),
        Path("/System/Library"),
        Path("/Library/Apple"),
        Path("/private/var/db/dyld"),
    }
    # Python is the sole executable. Imported package files cannot spawn another program.
    return "\n".join(
        [
            "(version 1)",
            "(deny default)",
            "(deny network*)",
            "(allow process-exec (literal "
            + json.dumps(str(Path(sys.executable).resolve()))
            + "))",
            "(allow file-read* "
            + " ".join(subpath(p) for p in sorted(reads))
            + ' (literal "/dev/null") (literal "/dev/urandom") (literal "/dev/random"))',
            "(allow file-write* " + subpath(work) + ' (literal "/dev/null"))',
            "(allow sysctl-read)",
            "(allow mach-lookup)",
        ]
    )


def apply_limits() -> None:
    for kind, maximum in (
        (resource.RLIMIT_AS, LIMITS["memory_bytes"]),
        (resource.RLIMIT_CPU, LIMITS["cpu_seconds"]),
        (resource.RLIMIT_FSIZE, LIMITS["max_file_bytes"]),
        (resource.RLIMIT_NOFILE, 64),
        (resource.RLIMIT_CORE, 0),
    ):
        resource.setrlimit(kind, (maximum, maximum))
        if resource.getrlimit(kind) != (maximum, maximum):
            raise RuntimeError("worker resource limit could not be enforced")


def capability(root: Path) -> dict[str, Any]:
    """Probe in a separate Python; never change limits on the operator process."""
    if platform.system() != "Darwin" or not Path("/usr/bin/sandbox-exec").is_file():
        return {
            "available": False,
            "reason": "No verified OS network/write sandbox on this platform.",
        }
    try:
        with tempfile.TemporaryDirectory(prefix=".probe-", dir=root) as temporary:
            parent = Path(temporary)
            probe_dir = parent / "work"
            probe_dir.mkdir(mode=0o700)
            (probe_dir / "tmp").mkdir(mode=0o700)
            sentinel = parent / "outside"
            sentinel.write_bytes(b"harmless-isolation-sentinel")
            sentinel.chmod(0o600)
            result = subprocess.run(
                [
                    "/usr/bin/sandbox-exec",
                    "-p",
                    sandbox_profile(probe_dir, root / "resources"),
                    sys.executable,
                    "-I",
                    str(Path(__file__).with_name("worker.py")),
                    "--probe",
                    str(sentinel),
                ],
                cwd=probe_dir,
                env=environment(probe_dir),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=5,
                check=False,
            )
            available = (
                result.returncode == 0
                and result.stdout == b"isolated-limits-ok\n"
                and sentinel.read_bytes() == b"harmless-isolation-sentinel"
            )
    except (OSError, subprocess.SubprocessError):
        available = False
    return {
        "available": available,
        "reason": (
            "OS network/read/write sandbox and worker hard-limit probe passed."
            if available
            else "OS isolation or hard memory/CPU/file limits could not be verified; jobs disabled."
        ),
    }


def command(work: Path, registered: Path, resource_id: str) -> list[str]:
    return [
        "/usr/bin/sandbox-exec",
        "-p",
        sandbox_profile(work, registered),
        sys.executable,
        "-I",
        str(Path(__file__).with_name("worker.py")),
        str(work),
        str(registered.parent.parent),
        resource_id,
    ]
