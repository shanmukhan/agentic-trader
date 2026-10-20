import hmac
import logging
import threading
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from importlib.resources import files
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from trading_agent.api.console import console_snapshot
from trading_agent.execution.delivery import HoldingExit, HoldingReview
from trading_agent.execution.paper_broker import IntentConflict, PaperBroker
from trading_agent.models import Candidate

if TYPE_CHECKING:
    from trading_agent.paper.runtime import PaperFeed

ASSETS = files("trading_agent.api").joinpath("static")


def create_app(
    engine: PaperBroker,
    clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    stream: Any = None,
    background: bool = True,
    automation: "PaperFeed | None" = None,
) -> FastAPI:
    stopped = threading.Event()

    def watchdog() -> None:
        while not stopped.wait(1):
            try:
                with engine.lock:
                    if not engine.faulted:
                        if automation:
                            automation.tick(clock())
                        else:
                            engine.poll(clock())
            except Exception:
                engine.faulted = True
                engine.set_connected(False)
                logging.getLogger(__name__).error("watchdog failed; entries blocked")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        worker = threading.Thread(target=watchdog, name="risk-watchdog", daemon=True)
        if background:
            worker.start()
        try:
            if stream:
                stream.start()
            yield
        finally:
            stopped.set()
            if stream:
                stream.close()
            if automation and not automation.closed:
                with engine.lock:
                    automation.close(clock())
            if background:
                worker.join(timeout=5)
            engine.set_connected(False)

    app = FastAPI(
        title="Paper operator API",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]"])

    @app.middleware("http")
    async def security_headers(request: Request, call_next: Any) -> Any:
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; "
            "style-src 'self'; form-action 'none'; object-src 'none'; "
            "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'"
        )
        return response

    def authorized(request: Request, authorization: Annotated[str | None, Header()] = None) -> None:
        secret = engine.settings.operator_token.get_secret_value()
        if not secret:
            raise HTTPException(503, "operator controls disabled: configure operator token")
        if not authorization or not hmac.compare_digest(
            authorization.encode(), ("Bearer " + secret).encode()
        ):
            raise HTTPException(401, "operator authentication required")
        if request.method not in ("GET", "HEAD"):
            # Bearer authentication and Origin validation protect browser controls.
            origin = request.headers.get("origin")
            permitted = {
                f"http://127.0.0.1:{engine.settings.port}",
                f"http://localhost:{engine.settings.port}",
                f"http://[::1]:{engine.settings.port}",
            }
            if origin is not None and origin not in permitted:
                raise HTTPException(403, "cross-origin controls prohibited")

    @app.exception_handler(Exception)
    async def safe_error(request: Request, exc: Exception) -> JSONResponse:
        engine.faulted = True
        engine.set_connected(False)
        if automation:
            automation.fail(clock())
        logging.getLogger(__name__).error("operator request failed; entries blocked")
        return JSONResponse(
            {"detail": "internal failure; entries blocked; inspect local journal"}, 503
        )

    @app.get("/", response_class=HTMLResponse)
    def dashboard() -> str:
        return ASSETS.joinpath("index.html").read_text(encoding="utf-8")

    @app.get("/dashboard.js")
    def javascript() -> HTMLResponse:
        return HTMLResponse(
            ASSETS.joinpath("dashboard.js").read_text(encoding="utf-8"),
            media_type="application/javascript",
        )

    @app.get("/dashboard.css")
    def stylesheet() -> HTMLResponse:
        return HTMLResponse(
            ASSETS.joinpath("dashboard.css").read_text(encoding="utf-8"), media_type="text/css"
        )

    @app.get("/portfolio", response_class=HTMLResponse)
    def portfolio_page() -> str:
        return ASSETS.joinpath("portfolio.html").read_text(encoding="utf-8")

    @app.get("/portfolio.js")
    def portfolio_script() -> HTMLResponse:
        return HTMLResponse(
            ASSETS.joinpath("portfolio.js").read_text(), media_type="application/javascript"
        )

    @app.get("/money.js")
    def money_script() -> HTMLResponse:
        return HTMLResponse(
            ASSETS.joinpath("money.js").read_text(), media_type="application/javascript"
        )

    from trading_agent.portfolio import service as portfolio
    from trading_agent.portfolio.contracts import Approval, CancelPlan, Contribution, SIPPlan

    @app.get("/api/paper/portfolio", dependencies=[Depends(authorized)])
    def portfolio_view() -> dict[str, Any]:
        try:
            return portfolio.view(engine, clock())
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from None

    @app.post("/api/paper/portfolio/preview", dependencies=[Depends(authorized)])
    def contribution_preview(request: Contribution) -> dict[str, Any]:
        try:
            return portfolio.preview(engine, request, clock())
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from None

    @app.post("/api/paper/portfolio/contributions", dependencies=[Depends(authorized)])
    def contribution_confirm(request: Approval) -> dict[str, Any]:
        try:
            return portfolio.confirm(engine, request, clock())
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from None

    @app.post("/api/paper/portfolio/plans", dependencies=[Depends(authorized)])
    def sip_create(request: SIPPlan) -> dict[str, Any]:
        try:
            return portfolio.create_plan(engine, request, clock())
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from None

    @app.post("/api/paper/portfolio/plans/cancel", dependencies=[Depends(authorized)])
    def sip_cancel(request: CancelPlan) -> dict[str, Any]:
        try:
            return portfolio.cancel_plan(engine, request, clock())
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from None

    @app.get("/api/console", dependencies=[Depends(authorized)])
    def console() -> dict[str, Any]:
        return console_snapshot(engine, clock(), automation)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "alive", "mode": "paper"}

    @app.get("/ready")
    def ready() -> JSONResponse:
        now = clock()
        with engine.lock:
            with engine.db.transaction() as tx:
                snapshot = engine._snapshot(tx, now)
                quotes = [
                    engine._quote(tx, row[0]) for row in tx.execute("SELECT symbol FROM quotes")
                ]
                can_enter = bool(quotes) and any(
                    not engine._entry_reasons(tx, q, now) for q in quotes
                )
            if automation:
                can_enter = can_enter and automation.armed and not automation.readiness(now)
        return JSONResponse(
            {
                "ready": can_enter,
                "mode": "paper",
                "feed": snapshot["feed_connected"],
                "kill": snapshot["kill"],
                "calendar_open": engine.calendar.is_open(now),
            },
            200 if can_enter else 503,
        )

    @app.get("/api/status", dependencies=[Depends(authorized)])
    def status() -> dict[str, Any]:
        return engine.snapshot(clock())

    @app.get("/api/paper/orders", dependencies=[Depends(authorized)])
    def orders() -> list[dict[str, Any]]:
        return engine.orders()

    @app.post("/api/paper/intents", dependencies=[Depends(authorized)])
    def submit(candidate: Candidate) -> dict[str, Any]:
        if automation:
            raise HTTPException(409, "manual entry intents disabled on automated paper accounts")
        try:
            return engine.submit(candidate, clock())
        except IntentConflict as exc:
            raise HTTPException(409, str(exc)) from None

    @app.post("/api/paper/orders/{intent}/cancel", dependencies=[Depends(authorized)])
    def cancel(intent: str) -> dict[str, Any]:
        try:
            return engine.cancel(intent, clock())
        except KeyError:
            raise HTTPException(404, "unknown paper intent") from None

    @app.post("/api/control/kill", dependencies=[Depends(authorized)])
    def kill() -> dict[str, bool]:
        with engine.lock:
            if automation:
                automation.disarm(clock(), "OPERATOR_KILL")
            engine.kill(clock())
        return {"kill": True}

    @app.post("/api/control/flatten", dependencies=[Depends(authorized)])
    def flatten() -> dict[str, bool]:
        with engine.lock:
            if automation:
                automation.disarm(clock(), "OPERATOR_FLATTEN")
            engine.flatten(clock())
        return {"kill": True, "exits_queued": True}

    @app.post("/api/control/reset", dependencies=[Depends(authorized)])
    def reset() -> dict[str, bool]:
        try:
            engine.reset_kill(clock())
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from None
        return {"kill": False}

    @app.post("/api/paper/long-term/reviews", dependencies=[Depends(authorized)])
    def review_holding(review: HoldingReview) -> dict[str, Any]:
        try:
            return engine.review_holding(review, clock())
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from None

    @app.post("/api/paper/long-term/exit", dependencies=[Depends(authorized)])
    def exit_holding(request: HoldingExit) -> dict[str, Any]:
        try:
            return engine.exit_holding(request.symbol, clock())
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from None
        except KeyError:
            raise HTTPException(404, "no open holding for this symbol") from None

    @app.get("/api/paper/automation", dependencies=[Depends(authorized)])
    def automation_status() -> dict[str, Any]:
        with engine.lock:
            return automation.status(clock()) if automation else {"enabled": False, "armed": False}

    @app.post("/api/paper/automation/arm", dependencies=[Depends(authorized)])
    def arm() -> dict[str, Any]:
        if not automation:
            raise HTTPException(409, "paper automation is not configured")
        try:
            with engine.lock:
                return automation.arm(clock())
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from None

    @app.post("/api/paper/automation/disarm", dependencies=[Depends(authorized)])
    def disarm() -> dict[str, Any]:
        if not automation:
            raise HTTPException(409, "paper automation is not configured")
        with engine.lock:
            automation.disarm(clock())
            return automation.status(clock())

    return app
