"""Stable economic-policy identity shared by accounts and research artifacts."""

import hashlib
import json
from typing import Any

from trading_agent.settings import Settings


def policy_values(settings: Settings) -> dict[str, Any]:
    return settings.model_dump(
        mode="json",
        exclude={"operator_token", "host", "port", "database", "calendar", "stream_tokens"},
    )


def policy_fingerprint(settings: Settings) -> str:
    return hashlib.sha256(json.dumps(policy_values(settings), sort_keys=True).encode()).hexdigest()
