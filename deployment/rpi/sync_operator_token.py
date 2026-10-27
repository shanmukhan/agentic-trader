"""Explicitly synchronize ONLY the workstation operator token to the Pi service.

Usage: .venv/bin/python deployment/rpi/sync_operator_token.py USER@PI
Use --generate to create and privately save a strong replacement automatically.
Otherwise requires a literal URL-safe TRADING_OPERATOR_TOKEN in the local project .env,
key-based SSH and a current noninteractive sudo session. No broker credentials
or account data are copied. Credentials travel only over SSH stdin, never argv.
"""

import argparse
import hmac
import json
import os
import re
import secrets
import shlex
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path

KEY = "TRADING_OPERATOR_TOKEN"
ASSIGNMENT = re.compile(r"(?m)^\s*(?:export\s+)?TRADING_OPERATOR_TOKEN\s*=([^\n]*)$")


def read_token(text: str) -> str:
    matches = ASSIGNMENT.findall(text)
    if len(matches) != 1:
        raise ValueError("Provide exactly one TRADING_OPERATOR_TOKEN assignment")
    try:
        parts = shlex.split(matches[0], comments=True)
    except ValueError:
        raise ValueError("Operator token assignment has invalid quoting") from None
    if len(parts) != 1 or not re.fullmatch(r"[A-Za-z0-9_-]{32,1024}", parts[0]):
        raise ValueError(
            "Local .env requires a literal URL-safe operator token of 32–1024 characters. "
            "Use --generate to create and privately save a strong replacement."
        )
    return parts[0]


def replace_token(path: Path, token: str, backup_directory: Path) -> bool:
    read_token(KEY + "=" + token)  # Validate before changing or backing up anything.
    if path.is_symlink():
        raise ValueError("Refusing a symlink environment file")
    previous = path.read_text()
    if len(ASSIGNMENT.findall(previous)) != 1:
        raise ValueError(
            "Pi environment must contain exactly one TRADING_OPERATOR_TOKEN assignment"
        )
    try:
        old_token = read_token(previous)
    except ValueError:
        # The existing credential may be empty, short, punctuation-bearing or
        # incorrectly quoted. A valid replacement repairs it; preserve the old
        # bytes in the private backup rather than requiring them to be valid.
        old_token = None
    if old_token is not None and hmac.compare_digest(token, old_token):
        return False
    updated = ASSIGNMENT.sub(lambda _: KEY + "=" + token, previous)
    metadata = path.stat()
    backup_directory.mkdir(mode=0o700, parents=True, exist_ok=False)
    backup = backup_directory / "agentic-trader.env"
    with backup.open("x") as file:
        os.fchmod(file.fileno(), 0o600)
        file.write(previous)
        file.flush()
        os.fsync(file.fileno())
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=".operator-token-")
    try:
        with os.fdopen(fd, "w") as file:
            os.fchmod(file.fileno(), 0o600)
            os.fchown(file.fileno(), metadata.st_uid, metadata.st_gid)
            file.write(updated)
            file.flush()
            os.fsync(file.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return True


def generate_local_token(env_path: Path) -> Path:
    backup = (
        env_path.parent
        / "backups"
        / ("operator-token-" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ"))
    )
    replace_token(env_path, secrets.token_urlsafe(32), backup)
    return backup


def validate_target(target: str) -> str:
    if target.startswith("-") or not re.fullmatch(r"[A-Za-z0-9_.@:-]+", target):
        raise ValueError("Use a plain SSH USER@HOST target")
    return target


def sync(target: str, env_path: Path) -> None:
    validate_target(target)
    token = read_token(env_path.read_text())
    remote = Path(__file__).read_text().split("\ndef sync(")[0]
    remote += """
import sys,time,urllib.request,urllib.error
from datetime import UTC,datetime
incoming=json.load(sys.stdin)["token"]
path=Path("/etc/agentic-trader.env")
backup=Path("/var/backups/trading-operator-token-"+datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ"))
try:
    changed=replace_token(path,incoming,backup)
except (OSError,ValueError) as error:
    raise SystemExit("Pi token update stopped before restart: "+str(error))
restart_needed=changed or subprocess.run(
    ["systemctl","is-active","--quiet","agentic-trader"],check=False).returncode != 0
if restart_needed:
    subprocess.run(["systemctl","reset-failed","agentic-trader"],check=True)
    subprocess.run(["systemctl","restart","agentic-trader"],check=True)
for attempt in range(30):
    try:
        request=urllib.request.Request(
            "https://shanmukhan.com/agentic-trader/api/workspace",
            headers={"Authorization":"Bearer "+incoming})
        with urllib.request.urlopen(request,timeout=5) as response:
            assert response.status==200 and json.load(response)["mode"]=="paper"
        break
    except (OSError,AssertionError):
        if attempt==29:
            raise SystemExit(
                "Token sync verification failed; review private backup and service logs")
        time.sleep(1)
print(json.dumps({"token_changed":changed,"service_restarted":restart_needed,
                  "public_authenticated_read":200,
                  "private_backup":str(backup) if changed else None}))
"""
    compile(remote, "remote-token-sync", "exec")
    subprocess.run(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            target,
            "sudo -n /usr/bin/python3 -c " + shlex.quote(remote),
        ],
        input=json.dumps({"token": token}),
        text=True,
        check=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("target", type=validate_target)
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate and privately save a strong token before syncing",
    )
    args = parser.parse_args()
    try:
        local_env = Path(__file__).resolve().parents[2] / ".env"
        if args.generate:
            local_backup = generate_local_token(local_env)
            print(
                json.dumps(
                    {
                        "local_token_generated": True,
                        "local_env": str(local_env),
                        "private_local_backup": str(local_backup),
                    }
                ),
                flush=True,
            )
        sync(args.target, local_env)
    except (OSError, ValueError) as error:
        parser.exit(1, str(error) + "\n")
    except subprocess.CalledProcessError:
        parser.exit(1, "Token sync failed. Resolve the Pi/SSH error above, then retry.\n")
