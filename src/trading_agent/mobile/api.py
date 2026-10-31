"""Native-phone pairing and browser-mediated broker login, with sanitized failures."""

import hmac
import re
import secrets
import threading
from datetime import timedelta
from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from trading_agent.api.setup import SetupError
from trading_agent.mobile.auth import DeviceAccess, MobileAuthError
from trading_agent.models import stamp


class Pair(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    label: str = Field(min_length=1, max_length=60, pattern=r"^[\w .'-]+$")


class Unlock(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    device_id: str = Field(pattern=r"^[a-f0-9]{32}$")
    device_secret: str = Field(pattern=r"^[a-f0-9]{64}$", repr=False)


class ManualExchange(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    request_token: str = Field(pattern=r"^[A-Za-z0-9_-]{1,256}$", repr=False)


async def body(request: Request, schema: type[Pair] | type[Unlock] | type[ManualExchange]) -> Any:
    content = bytearray()
    async for chunk in request.stream():
        content.extend(chunk)
        if len(content) > 4096:
            raise HTTPException(413, "Mobile authentication request is too large.")
    try:
        return schema.model_validate_json(bytes(content))
    except (ValidationError, ValueError):
        raise HTTPException(422, "Invalid mobile authentication request.") from None


def bearer(request: Request) -> str:
    header = request.headers.get("authorization", "")
    return header[7:] if header.startswith("Bearer ") else ""


class MobileLogin:
    def __init__(self, setup: Any, clock: Any):
        self.setup, self.clock = setup, clock
        self.lock = threading.RLock()
        self.attempts: dict[str, dict[str, Any]] = {}

    def begin(self, identity: str) -> dict[str, Any]:
        if self.setup is None:
            raise HTTPException(409, "Manual broker setup is unavailable for this account.")
        with self.lock:
            now = self.clock()
            self.attempts = {key: a for key, a in self.attempts.items() if a["expires"] > now}
            if len(self.attempts) >= 20:
                raise HTTPException(429, "Too many broker login attempts. Wait five minutes.")
            try:
                value = self.setup.begin_login()
            except SetupError as error:
                raise HTTPException(409, str(error)) from None
            identity_key = secrets.token_hex(16)
            expires = now + timedelta(minutes=5)
            self.attempts[identity_key] = {
                "owner": identity,
                "state": "waiting_for_login",
                "nonce": value["state"],
                "expires": expires,
            }
            url = urlsplit(value["login_url"])
            query = parse_qs(url.query)
            params = parse_qs(query.get("redirect_params", [""])[0])
            params["mobile_attempt"] = [identity_key]
            query["redirect_params"] = [urlencode(params, doseq=True)]
            return {
                "attempt_id": identity_key,
                "expires_at": stamp(expires),
                "login_url": urlunsplit(url._replace(query=urlencode(query, doseq=True))),
            }

    def status(self, identity_key: str, owner: str) -> dict[str, str]:
        with self.lock:
            attempt = self.attempts.get(identity_key)
            if not attempt or attempt["owner"] != owner:
                raise HTTPException(404, "Login attempt not found. Start a fresh login.")
            state = "expired" if attempt["expires"] <= self.clock() else attempt["state"]
            return {
                "state": state,
                "message": {
                    "waiting_for_login": "Complete Zerodha login and return to the app.",
                    "exchanging": "Verifying the broker session.",
                    "verified": "Broker session verified. Continue setup in the app.",
                    "failed": "Login could not be verified. Start a fresh Zerodha login.",
                    "expired": "Login attempt expired. Start a fresh Zerodha login.",
                }[state],
            }

    def finish(self, query: Any) -> str:
        key = query.get("mobile_attempt", "")
        accepted = False
        with self.lock:
            attempt = self.attempts.get(key)
            if attempt and attempt["state"] == "verified":
                accepted = True
            elif (
                attempt
                and attempt["state"] == "waiting_for_login"
                and attempt["expires"] > self.clock()
                and hmac.compare_digest(attempt["nonce"], query.get("setup_state", ""))
                and re.fullmatch(r"[A-Za-z0-9_-]{1,256}", query.get("request_token", ""))
            ):
                attempt["state"] = "exchanging"
                accepted = True
        if accepted and attempt and attempt["state"] == "exchanging":
            try:
                self.setup.exchange(
                    {"state": attempt["nonce"], "request_token": query["request_token"]}
                )
                outcome = "verified"
            except Exception:
                outcome = "failed"
            with self.lock:
                attempt["state"] = outcome
        success = bool(accepted and attempt and attempt["state"] == "verified")
        title = "Zerodha sign-in complete" if success else "Zerodha sign-in needs attention"
        text = (
            "Return to Agentic Trader and unlock to continue. You can close this browser tab."
            if success
            else "Return to Agentic Trader and start a fresh sign-in. No mode was activated."
        )
        return (
            '<!doctype html><html lang="en"><meta name="viewport" '
            'content="width=device-width,initial-scale=1"><title>'
            + title
            + "</title><main><h1>"
            + title
            + "</h1><p>"
            + text
            + "</p></main></html>"
        )


def mount_mobile(
    app: Any, access: DeviceAccess, setup: Any, clock: Any, authorized: Any
) -> MobileLogin:
    login = MobileLogin(setup, clock)

    def owner(request: Request) -> str:
        token = bearer(request)
        if hmac.compare_digest(token, access.owner()):
            return "operator"
        identity = access.identity(token)
        if not identity:
            raise HTTPException(401, "Phone authentication required.")
        return identity

    @app.post("/api/mobile/devices", dependencies=[Depends(authorized)])
    async def pair_phone(request: Request) -> dict[str, str]:
        if owner(request) != "operator":
            raise HTTPException(403, "Use the server operator token to pair a phone.")
        value = await body(request, Pair)
        try:
            return access.enroll(value.label)
        except MobileAuthError as error:
            raise HTTPException(409, str(error)) from None
        except (OSError, SetupError):
            raise HTTPException(
                503, "Pairing could not be saved. Inspect paired phones before retrying."
            ) from None

    @app.get("/api/mobile/devices", dependencies=[Depends(authorized)])
    def phones(request: Request) -> dict[str, Any]:
        identity = owner(request)
        return {"devices": access.list(None if identity == "operator" else identity)}

    @app.delete("/api/mobile/devices/{identity}", dependencies=[Depends(authorized)])
    def revoke(identity: str, request: Request) -> dict[str, bool]:
        current = owner(request)
        if current != "operator" and current != identity:
            raise HTTPException(403, "A phone can revoke only its own pairing.")
        try:
            access.revoke(identity)
        except MobileAuthError as error:
            raise HTTPException(404, str(error)) from None
        except (OSError, SetupError):
            raise HTTPException(
                503, "Revocation persistence is uncertain. Inspect and retry before restarting."
            ) from None
        return {"revoked": True}

    @app.post("/api/mobile/session")
    async def unlock(request: Request) -> dict[str, Any]:
        # This route has no ambient browser credentials; an opaque per-device secret is required.
        origin = request.headers.get("origin")
        if origin is not None:
            raise HTTPException(403, "Use the native Android app for phone unlock.")
        value = await body(request, Unlock)
        try:
            return access.session(value.device_id, value.device_secret)
        except MobileAuthError as error:
            raise HTTPException(429 if "Too many" in str(error) else 401, str(error)) from None

    @app.delete("/api/mobile/session", dependencies=[Depends(authorized)])
    def lock_phone(request: Request) -> dict[str, bool]:
        access.logout(bearer(request))
        return {"locked": True}

    @app.post("/api/mobile/broker/login", dependencies=[Depends(authorized)])
    def broker_login(request: Request) -> dict[str, Any]:
        return login.begin(owner(request))

    @app.get("/api/mobile/broker/login/{identity}", dependencies=[Depends(authorized)])
    def broker_status(identity: str, request: Request) -> dict[str, str]:
        return login.status(identity, owner(request))

    @app.post("/api/mobile/broker/login/{identity}/exchange", dependencies=[Depends(authorized)])
    async def manual_exchange(identity: str, request: Request) -> dict[str, str]:
        current = owner(request)
        login.status(
            identity, current
        )  # Enforce the original phone binding before using its nonce.
        value = await body(request, ManualExchange)
        with login.lock:
            nonce = login.attempts[identity]["nonce"]
        login.finish(
            {"mobile_attempt": identity, "setup_state": nonce, "request_token": value.request_token}
        )
        result = login.status(identity, current)
        if result["state"] != "verified":
            raise HTTPException(409, "Broker exchange failed or expired. Start a fresh login.")
        return result

    return login
