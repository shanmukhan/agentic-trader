"""Stable economic-policy identity shared by accounts and research artifacts."""

import hashlib
import json
from typing import Any

from trading_agent.settings import Settings


def policy_values(settings: Settings) -> dict[str, Any]:
    values = settings.model_dump(
        mode="json",
        exclude={
            "operator_token",
            "host",
            "port",
            "public_origin",
            "public_path",
            "database",
            "calendar",
            "stream_tokens",
            "stream_limit",
        },
    )
    # Preserve every existing intraday account/model identity byte for byte.
    if settings.investment_horizon == "intraday":
        values.pop("investment_horizon")
        values.pop("long_term_drawdown_limit")
    return values


def policy_fingerprint(settings: Settings) -> str:
    return hashlib.sha256(json.dumps(policy_values(settings), sort_keys=True).encode()).hexdigest()
