"""One offline worker; invoked by an OS sandbox, never by HTTP input paths."""

import sys
from collections.abc import Callable
from pathlib import Path

# Isolated Python omits current directory/PYTHONPATH; this is an installed code location.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def main() -> int:
    from trading_agent.research_jobs.isolation import apply_limits

    apply_limits()  # Fail before third-party imports or parsing data when any hard limit fails.
    if len(sys.argv) == 3 and sys.argv[1] == "--probe":
        import errno
        import os
        import socket

        sentinel = Path(sys.argv[2])

        def denied(operation: Callable[[], object]) -> bool:
            try:
                operation()
            except OSError as error:
                return error.errno in {errno.EPERM, errno.EACCES}
            return False

        def outside_write() -> None:
            fd = os.open(sentinel, os.O_WRONLY | os.O_TRUNC)
            os.close(fd)

        def network() -> None:
            with socket.socket() as connection:
                connection.settimeout(0.2)
                connection.connect(("127.0.0.1", 9))

        if not all((denied(sentinel.read_bytes), denied(outside_write), denied(network))):
            return 2
        inside = Path.cwd() / "tmp" / "inside"
        inside.write_bytes(b"allowed")
        if inside.read_bytes() != b"allowed":
            return 2
        inside.unlink()
        print("isolated-limits-ok")
        return 0
    from trading_agent.daily_execution.contracts import DailyStrategy
    from trading_agent.daily_execution.dataset import ExecutionDataset
    from trading_agent.daily_execution.runner import run_daily
    from trading_agent.daily_research.dataset import DailyDataset
    from trading_agent.research_jobs.registry import load_resource, runtime_definition
    from trading_agent.settings import Settings

    work, registry, resource_id = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3]
    record = load_resource(registry, resource_id)
    if record["runtime"] != runtime_definition(Settings.model_validate(record["policy"])):
        raise ValueError("research implementation changed")
    source = registry / "resources" / resource_id
    run_daily(
        ExecutionDataset(source / "execution", DailyDataset(source / "daily")),
        strategy=DailyStrategy.model_validate(record["strategy"]),
        policy=Settings.model_validate(record["policy"]),
        output=work / "result",
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception:
        # Exception text may include private paths or input values; do not emit it.
        print("Offline worker failed; no report published.", file=sys.stderr)
        raise SystemExit(1) from None
