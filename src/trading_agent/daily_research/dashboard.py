"""Self-contained accessible report; no network or HTML injection sink."""

import base64
import hashlib
import json
from importlib.resources import files
from typing import Any


def render(result: dict[str, Any]) -> str:
    resources = files("trading_agent.daily_research").joinpath("static")
    style = resources.joinpath("style.css").read_text(encoding="utf-8")
    script = resources.joinpath("dashboard.js").read_text(encoding="utf-8")
    template = resources.joinpath("template.html").read_text(encoding="utf-8")
    data = (
        json.dumps(result, sort_keys=True)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )

    def csp(content: str) -> str:
        return base64.b64encode(hashlib.sha256(content.encode()).digest()).decode()

    for key, value in (
        ("STYLE_HASH", csp(style)),
        ("SCRIPT_HASH", csp(script)),
        ("STYLE", style),
        ("SCRIPT", script),
        ("DATA", data),
    ):
        template = template.replace("{{" + key + "}}", value)
    return template
