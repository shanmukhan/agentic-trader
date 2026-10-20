"""Self-contained execution/validation evidence UI, with exact monetary strings."""

import base64
import hashlib
import json
from importlib.resources import files
from typing import Any


def render(report: dict[str, Any]) -> str:
    root = files("trading_agent.daily_execution").joinpath("static")
    style = files("trading_agent.daily_research").joinpath("static", "style.css").read_text()
    script = root.joinpath("report.js").read_text()
    template = root.joinpath("report.html").read_text()
    data = (
        json.dumps(report, sort_keys=True, default=str)
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    for key, value in (
        ("STYLE_HASH", base64.b64encode(hashlib.sha256(style.encode()).digest()).decode()),
        ("SCRIPT_HASH", base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()),
        ("STYLE", style),
        ("SCRIPT", script),
        ("DATA", data),
    ):
        template = template.replace("{{" + key + "}}", value)
    return template
