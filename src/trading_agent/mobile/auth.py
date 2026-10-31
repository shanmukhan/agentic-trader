"""Opaque device credentials; the financial ledger is never opened or modified here."""

import hashlib
import hmac
import json
import re
import secrets
import threading
from collections.abc import Callable
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from trading_agent.api.setup import private_write
from trading_agent.models import stamp


class MobileAuthError(ValueError):
    pass


def fingerprint(secret: str) -> str:
    return hashlib.sha256(secret.encode()).hexdigest()


class DeviceAccess:
    SESSION_SECONDS = 900

    def __init__(self, path: Path, owner: Callable[[], str], clock: Callable[[], datetime]):
        self.path, self.owner, self.clock = path, owner, clock
        self.lock = threading.RLock()
        self.devices: dict[str, dict[str, Any]] = {}
        self.sessions: dict[str, dict[str, Any]] = {}
        self.failures: dict[str, tuple[datetime, int]] = {}
        if path.exists() or path.is_symlink():
            if path.is_symlink() or path.stat().st_mode & 0o077 or path.stat().st_size > 100_000:
                raise MobileAuthError("Mobile pairing storage must be a private regular file.")
            try:
                value = json.loads(path.read_text())
                if (
                    value["schema_version"] != 1
                    or not isinstance(value["devices"], list)
                    or len(value["devices"]) > 20
                ):
                    raise ValueError
                for device in value["devices"]:
                    if not (
                        re.fullmatch(r"[a-f0-9]{32}", device["id"])
                        and re.fullmatch(r"[a-f0-9]{64}", device["secret_sha256"])
                        and re.fullmatch(r"[a-f0-9]{64}", device["owner_sha256"])
                        and isinstance(device["label"], str)
                        and 1 <= len(device["label"]) <= 60
                        and isinstance(device["revoked"], bool)
                    ):
                        raise ValueError
                    datetime.fromisoformat(device["created_at"])
                    self.devices[device["id"]] = device
                if len(self.devices) != len(value["devices"]):
                    raise ValueError
            except Exception:
                raise MobileAuthError(
                    "Saved mobile pairings are invalid; review them locally."
                ) from None

    def _save(self) -> None:
        private_write(
            self.path,
            json.dumps({"schema_version": 1, "devices": list(self.devices.values())}) + "\n",
        )

    def _current(self, device: dict[str, Any]) -> bool:
        return not device["revoked"] and hmac.compare_digest(
            device["owner_sha256"], fingerprint(self.owner())
        )

    def enroll(self, label: str) -> dict[str, str]:
        with self.lock:
            if sum(self._current(d) for d in self.devices.values()) >= 8:
                raise MobileAuthError(
                    "Eight phones are already paired. Revoke an old pairing first."
                )
            # Keep bounded revoked history. Removing it never makes a credential valid again.
            if len(self.devices) >= 20:
                oldest = next(
                    (key for key, d in self.devices.items() if not self._current(d)), None
                )
                if oldest:
                    self.devices.pop(oldest)
            identity, secret = secrets.token_hex(16), secrets.token_hex(32)
            device = {
                "id": identity,
                "label": label,
                "secret_sha256": fingerprint(secret),
                "owner_sha256": fingerprint(self.owner()),
                "created_at": stamp(self.clock()),
                "revoked": False,
            }
            self.devices[identity] = device
            try:
                self._save()
            except Exception:
                self.devices.pop(identity)
                raise
            return {"device_id": identity, "device_secret": secret}

    def session(self, identity: str, secret: str) -> dict[str, Any]:
        with self.lock:
            now = self.clock()
            bucket = identity if identity in self.devices else "unknown"
            since, attempts = self.failures.get(bucket, (now, 0))
            if now - since >= timedelta(minutes=1):
                since, attempts = now, 0
            if attempts >= 5:
                raise MobileAuthError("Too many unlock attempts. Wait one minute and try again.")
            device = self.devices.get(identity)
            expected = device["secret_sha256"] if device else "0" * 64
            valid = hmac.compare_digest(fingerprint(secret), expected)
            if not device or not valid or not self._current(device):
                self.failures[bucket] = (since, attempts + 1)
                raise MobileAuthError("Phone authorization failed. Pair this phone again.")
            self.failures.pop(bucket, None)
            self.sessions = {
                key: s
                for key, s in self.sessions.items()
                if s["expires_at"] > now and s["device_id"] != identity
            }
            token = secrets.token_hex(32)
            expires = now + timedelta(seconds=self.SESSION_SECONDS)
            self.sessions[fingerprint(token)] = {
                "device_id": identity,
                "issued_at": now,
                "expires_at": expires,
            }
            return {"access_token": token, "expires_at": stamp(expires), "device_id": identity}

    def identity(self, token: str) -> str | None:
        if not re.fullmatch(r"[a-f0-9]{64}", token):
            return None
        with self.lock:
            session = self.sessions.get(fingerprint(token))
            if not session or not session["issued_at"] <= self.clock() < session["expires_at"]:
                return None
            device = self.devices.get(session["device_id"])
            return session["device_id"] if device and self._current(device) else None

    @staticmethod
    def permits(method: str, path: str) -> bool:
        # The native app has the browser's paper-account controls, never raw broker orders.
        if method == "GET":
            roots = (
                "/api/desk",
                "/api/activity",
                "/api/workspace",
                "/api/analysis",
                "/api/research",
                "/api/paper",
                "/api/console",
                "/api/feed",
                "/api/setup",
                "/api/investment-policies",
                "/api/backtests",
                "/api/operations",
                "/api/trading-environment",
                "/api/mobile",
            )
            return any(path == root or path.startswith(root + "/") for root in roots)
        if method == "DELETE":
            return path == "/api/mobile/session" or path.startswith("/api/mobile/devices/")
        post_roots = (
            "/api/desk",
            "/api/paper",
            "/api/control",
            "/api/setup",
            "/api/investment-policies",
            "/api/backtests",
            "/api/operations/download",
            "/api/mobile/broker",
        )
        return method == "POST" and any(
            path == root or path.startswith(root + "/") for root in post_roots
        )

    def logout(self, token: str) -> None:
        with self.lock:
            self.sessions.pop(fingerprint(token), None)

    def list(self, identity: str | None = None) -> list[dict[str, Any]]:
        with self.lock:
            return [
                {k: d[k] for k in ("id", "label", "created_at", "revoked")}
                | {"active": self._current(d)}
                for d in self.devices.values()
                if identity is None or d["id"] == identity
            ]

    def revoke(self, identity: str) -> None:
        with self.lock:
            if identity not in self.devices:
                raise MobileAuthError("Phone pairing not found.")
            self.devices[identity]["revoked"] = True
            try:
                self._save()
            finally:
                # Revocation stays fail-closed in this process even if persistence is uncertain.
                self.sessions = {
                    key: s for key, s in self.sessions.items() if s["device_id"] != identity
                }
