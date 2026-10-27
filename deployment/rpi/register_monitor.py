"""Extend the deployed RPi Monitor allowlist, preserving unrelated private settings.

Run with the deployed monitor Python (python-dotenv), as root, after app health checks.
Backups are made by install.sh before this program is invoked.
"""

import importlib.util
import json
import os
import re
import stat
import sys
import tempfile
from pathlib import Path

SERVICES = {
    "agentic-trader": "agentic-trader.service",
    "portfolio-advisor": "portfolio-advisor.service",
}


def merge(text: str, settings: dict[str, str | None]) -> str:
    allowed = json.loads(settings.get("ALLOWED_SERVICES_JSON") or "{}")
    if not isinstance(allowed, dict):
        raise ValueError("Monitor allowlist must be an object")
    for name, unit in SERVICES.items():
        if name in allowed and allowed[name] != unit:
            raise ValueError(f"Conflicting monitor entry: {name}")
    allowed.update(SERVICES)
    line = "ALLOWED_SERVICES_JSON='" + json.dumps(allowed, separators=(",", ":")) + "'"
    pattern = r"(?m)^(?:export\s+)?ALLOWED_SERVICES_JSON\s*=.*$"
    if len(re.findall(pattern, text)) > 1:
        raise ValueError("Duplicate monitor allowlist declarations; review manually")
    if re.search(pattern, text):
        return re.sub(pattern, lambda _: line, text)
    return text.rstrip("\n") + "\n" + line + "\n"


def private_replace(path: Path, content: str) -> None:
    original = path.stat()
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w") as file:
            os.fchmod(file.fileno(), stat.S_IMODE(original.st_mode))
            os.fchown(file.fileno(), original.st_uid, original.st_gid)
            file.write(content)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)


def register(root: Path, rule_path: Path) -> None:
    from dotenv import dotenv_values

    env_path = root / ".env"
    text = merge(env_path.read_text(), dict(dotenv_values(env_path)))
    # Parse and validate the proposed env with the actual deployed renderer BEFORE
    # either live file changes; never deploy unrelated local monitor modifications.
    import io

    env = dict(dotenv_values(stream=io.StringIO(text)))
    spec = importlib.util.spec_from_file_location("render", root / "deploy/render_polkit_rule.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Missing deployed monitor renderer")
    renderer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(renderer)
    rule = renderer.render((root / "deploy/10-rpi-monitor-systemctl.rules").read_text(), env)
    old_env, old_rule = env_path.read_text(), rule_path.read_text()
    try:
        private_replace(rule_path, rule)
        private_replace(env_path, text)
    except BaseException:
        private_replace(rule_path, old_rule)
        private_replace(env_path, old_env)
        raise
    print(json.dumps(SERVICES))


if __name__ == "__main__":
    register(Path(sys.argv[1]), Path(sys.argv[2]))
