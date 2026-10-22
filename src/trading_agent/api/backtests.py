"""Authenticated bounded jobs; errors never fault or mutate an operator account."""

from collections.abc import Callable
from typing import Any, Literal

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from trading_agent.daily_research.dataset import read_json
from trading_agent.research_jobs import BacktestJobs, JobError


class Start(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    resource_id: str = Field(pattern=r"^bundle-[a-f0-9]{24}$")
    resource_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    request_key: str = Field(pattern=r"^[a-zA-Z0-9_-]{32,64}$")
    acknowledged: Literal[True]

    @field_validator("acknowledged", mode="before")
    @classmethod
    def explicit_acknowledgement(cls, value: object) -> object:
        if value is not True:
            raise ValueError("explicit acknowledgement required")
        return value


class Cancel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
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
                "recovery_action": "Review current job and resource state.",
                "field_errors": [],
            }
        },
        status_code=status,
        headers={"Retry-After": "5"} if status == 429 else None,
    )


async def _body(request: Request, schema: type[Start] | type[Cancel]) -> Any:
    content = bytearray()
    async for part in request.stream():
        content.extend(part)
        if len(content) > 4096:
            raise HTTPException(413, "research request exceeds 4 KiB")
    try:
        return schema.model_validate(read_json(content.decode("utf-8")))
    except (ValueError, ValidationError, UnicodeError):
        raise HTTPException(422, "invalid research request; review approved fields") from None


def mount_backtests(app: FastAPI, manager: BacktestJobs, authorized: Callable[..., None]) -> None:
    def guarded(function: Callable[..., Any], *args: Any) -> Any:
        try:
            return function(*args)
        except JobError as error:
            return _error(error.code, error.message, error.status)
        except Exception:
            return _error(
                "RESEARCH_STORAGE_UNAVAILABLE", "Research evidence could not be read safely.", 503
            )

    @app.get("/api/backtests/resources", dependencies=[Depends(authorized)])
    def resources() -> Any:
        return guarded(manager.resources)

    @app.get("/api/backtests/jobs", dependencies=[Depends(authorized)])
    def jobs() -> Any:
        return guarded(lambda: {"schema_version": 1, "jobs": manager.jobs()})

    @app.post("/api/backtests/jobs", dependencies=[Depends(authorized)])
    async def start(request: Request) -> Any:
        body = await _body(request, Start)

        def submit() -> JSONResponse:
            job, created = manager.submit(**body.model_dump())
            return JSONResponse(
                {"schema_version": 1, "job": job}, status_code=202 if created else 200
            )

        return guarded(submit)

    @app.get("/api/backtests/jobs/{job_id}", dependencies=[Depends(authorized)])
    def job(job_id: str) -> Any:
        return guarded(lambda: {"schema_version": 1, "job": manager.job(job_id)})

    @app.post("/api/backtests/jobs/{job_id}/cancel", dependencies=[Depends(authorized)])
    async def cancel(job_id: str, request: Request) -> Any:
        await _body(request, Cancel)
        return guarded(lambda: {"schema_version": 1, "job": manager.cancel(job_id)})

    @app.get("/api/backtests/reports/{report_id}", dependencies=[Depends(authorized)])
    def report(report_id: str) -> Any:
        return guarded(manager.report, report_id)
