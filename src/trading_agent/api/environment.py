"""Account-environment capabilities; this server cannot execute real orders."""

from typing import Any


def environment_capabilities() -> dict[str, Any]:
    return {
        "schema_version": 1,
        "active": "paper",
        "environments": [
            {
                "id": "paper",
                "label": "Paper",
                "available": True,
                "description": "Virtual money and simulated execution. Market data may be real.",
            },
            {
                "id": "real",
                "label": "Real",
                "available": False,
                "reason_code": "LIVE_EXECUTION_NOT_IMPLEMENTED",
                "description": "Real-order execution and broker-account reconciliation are not "
                "implemented on this server. Real trading cannot be enabled yet.",
            },
        ],
        "switching_available": False,
    }


def mount_environment(app: Any, authorized: Any) -> None:
    from fastapi import Depends

    @app.get("/api/trading-environment", dependencies=[Depends(authorized)])
    def environment() -> dict[str, Any]:
        return environment_capabilities()
