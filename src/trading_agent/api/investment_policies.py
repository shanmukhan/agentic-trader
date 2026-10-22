"""Authenticated previews and immutable specifications with no execution authority."""

from collections.abc import Callable
from typing import Any, Literal

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from trading_agent.investment_research.policy_store import (
    InvestmentPolicyStore,
    PolicyStoreError,
    strict_json,
)

MAX_BODY_BYTES = 16 * 1024


class Preview(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    draft: dict[str, Any]


class Save(Preview):
    preview_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    acknowledged: Literal[True]

    @field_validator("acknowledged", mode="before")
    @classmethod
    def explicit_acknowledgement(cls, value: object) -> object:
        if value is not True:
            raise ValueError("explicit acknowledgement required")
        return value


def _error(code: str, message: str, status: int) -> JSONResponse:
    return JSONResponse(
        {
            "error": {
                "code": code,
                "message": message,
                "incident_id": None,
                "retryable": False,
                "recovery_action": "Review draft choices and preview them again before saving.",
                "field_errors": [],
            }
        },
        status_code=status,
    )


async def _body(request: Request, schema: type[Preview]) -> Any:
    content = bytearray()
    async for part in request.stream():
        content.extend(part)
        if len(content) > MAX_BODY_BYTES:
            raise HTTPException(413, "investment draft request exceeds 16 KiB")
    try:
        return schema.model_validate(strict_json(bytes(content)))
    except (ValueError, ValidationError, UnicodeError, RecursionError):
        raise HTTPException(
            422, "invalid investment draft request; review approved fields"
        ) from None


def mount_investment_policies(
    app: FastAPI, store: InvestmentPolicyStore, authorized: Callable[..., None]
) -> None:
    def guarded(function: Callable[..., Any], *args: Any, invalid: bool = False) -> Any:
        try:
            return function(*args)
        except PolicyStoreError as error:
            return _error(error.code, error.message, error.status)
        except (ValueError, ValidationError):
            return _error(
                "DRAFT_INVALID" if invalid else "DRAFT_STORAGE_UNAVAILABLE",
                "Draft choices are invalid."
                if invalid
                else "Saved draft evidence could not be verified safely.",
                422 if invalid else 503,
            )
        except Exception:
            return _error(
                "DRAFT_STORAGE_UNAVAILABLE", "Saved draft evidence could not be read safely.", 503
            )

    @app.get("/api/investment-policies", dependencies=[Depends(authorized)])
    def drafts() -> Any:
        return guarded(store.list)

    @app.post("/api/investment-policies/preview", dependencies=[Depends(authorized)])
    async def preview(request: Request) -> Any:
        body = await _body(request, Preview)
        return guarded(store.preview, body.draft, invalid=True)

    @app.post("/api/investment-policies", dependencies=[Depends(authorized)])
    async def save(request: Request) -> Any:
        body = await _body(request, Save)
        validation = guarded(store.preview, body.draft, invalid=True)
        if isinstance(validation, JSONResponse):
            return validation

        def submit() -> JSONResponse:
            draft, created = store.save(body.draft, body.preview_sha256, body.acknowledged)
            return JSONResponse(
                {"schema_version": 1, "draft": draft}, status_code=201 if created else 200
            )

        return guarded(submit)

    @app.get("/api/investment-policies/{draft_id}", dependencies=[Depends(authorized)])
    def draft(draft_id: str) -> Any:
        return guarded(lambda: {"schema_version": 1, "draft": store.get(draft_id)})
