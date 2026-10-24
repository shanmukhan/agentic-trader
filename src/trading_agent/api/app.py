import hmac
import logging
import threading
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from starlette.middleware.trustedhost import TrustedHostMiddleware

from trading_agent.api.console import console_snapshot
from trading_agent.api.setup import SetupService, mount_setup
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
    setup: SetupService | None = None,
    open_browser: bool = False,
    desk_profile: Path | None = None,
    desk: Any = None,
    backtests: Any = None,
    investment_policies: Any = None,
) -> FastAPI:
    from trading_agent.desk.api import mount_desk
    from trading_agent.desk.preparation import Preparation, saved_profile
    from trading_agent.desk.service import TradingDesk
    from trading_agent.desk.signals import AnalysisWorker

    if desk is None and desk_profile is None and setup is not None:
        try:
            desk_profile = saved_profile(engine)
        except Exception:
            # Keep the UI available for recovery; never silently enable an alternative policy.
            desk_profile = engine.settings.database.with_suffix(".invalid-analysis-profile")
    desk = desk or TradingDesk(
        engine, clock(), profile=desk_profile, automation=automation, clock=clock
    )
    desk.clock = clock
    if setup:

        def feed_state(connected: bool) -> None:
            if not connected and desk.mode != "manual":
                desk.pause(clock(), "FEED_DISCONNECTED")

        setup.connection_observer = feed_state
    analysis = AnalysisWorker(desk, setup, clock)
    preparation = Preparation(desk, setup, clock)
    from trading_agent.research_jobs import BacktestJobs

    backtests = backtests or BacktestJobs(engine.settings.database.with_suffix(".research-jobs"))
    from trading_agent.investment_research.policy_store import InvestmentPolicyStore

    investment_policies = investment_policies or InvestmentPolicyStore(
        engine.settings.database.with_suffix(".investment-policies")
    )
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
                        desk.tick(clock())
            except Exception:
                engine.faulted = True
                engine.set_connected(False)
                logging.getLogger(__name__).error("watchdog failed; entries blocked")

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        worker = threading.Thread(target=watchdog, name="risk-watchdog", daemon=True)
        if background:
            worker.start()
            analysis.start()
        try:
            if stream:
                stream.start()
            if open_browser:
                import webbrowser

                # Schedule after lifespan startup so the browser reaches a listening socket.
                host = "[::1]" if engine.settings.host == "::1" else "127.0.0.1"
                threading.Timer(
                    0.5, webbrowser.open, args=[f"http://{host}:{engine.settings.port}/workspace"]
                ).start()
            yield
        finally:
            stopped.set()
            backtests.close()
            preparation.close()
            analysis.close()
            desk.pause(clock(), "SERVER_SHUTDOWN")
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
    app.state.preparation = preparation
    app.state.backtests = backtests
    app.state.investment_policies = investment_policies
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["127.0.0.1", "localhost", "[::1]"])

    @app.middleware("http")
    async def security_headers(request: Request, call_next: Any) -> Any:
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        framed = request.url.path in {
            "/console",
            "/setup",
            "/portfolio",
            "/desk",
            "/activity",
            "/strategies",
            "/investment-policy",
            "/analysis",
            "/dashboard",
            "/discovery",
            "/paper",
            "/holdings",
            "/backtesting",
            "/settings",
            "/learn",
        }
        response.headers["X-Frame-Options"] = "SAMEORIGIN" if framed else "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self'; "
            "style-src 'self'; form-action 'none'; object-src 'none'; "
            "connect-src 'self'; frame-src 'self'; base-uri 'none'; frame-ancestors "
            + ("'self'" if framed else "'none'")
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

    mount_setup(app, setup, authorized)
    mount_desk(app, desk, setup, authorized, ASSETS, clock, preparation)
    from trading_agent.operations.report import operations_report
    from trading_agent.operations.schedule import ScheduledDownload, scheduled_download

    @app.get("/api/operations", dependencies=[Depends(authorized)])
    def operations_status(audit: bool = False) -> dict[str, Any]:
        return operations_report(
            desk, setup, preparation, app.state.guided_setup, clock(), audit=audit
        )

    @app.post("/api/operations/download", dependencies=[Depends(authorized)])
    def operations_download(body: ScheduledDownload) -> dict[str, Any]:
        from trading_agent.api.setup import SetupError

        try:
            return scheduled_download(preparation, body, clock())
        except SetupError:
            raise
        except Exception:
            raise SetupError(
                "Scheduled preparation preflight failed; inspect saved evidence."
            ) from None

    from trading_agent.api.analysis import mount_analysis

    mount_analysis(app, desk, authorized, ASSETS, clock)
    from trading_agent.api.workspace_views import mount_workspace_views

    mount_workspace_views(app, desk, authorized, ASSETS, clock, setup)

    from trading_agent.api.backtests import mount_backtests

    mount_backtests(app, backtests, authorized)
    from trading_agent.api.investment_policies import mount_investment_policies

    mount_investment_policies(app, investment_policies, authorized)

    @app.get("/investment-policy", response_class=HTMLResponse)
    def investment_policy_page() -> str:
        return ASSETS.joinpath("investment-policy.html").read_text(encoding="utf-8")

    @app.get("/investment-policy.js")
    def investment_policy_script() -> HTMLResponse:
        return HTMLResponse(
            ASSETS.joinpath("investment-policy.js").read_text(), media_type="application/javascript"
        )

    @app.get("/backtesting", response_class=HTMLResponse)
    def backtesting_page() -> str:
        return ASSETS.joinpath("backtesting.html").read_text(encoding="utf-8")

    @app.get("/backtesting.js")
    def backtesting_script() -> HTMLResponse:
        return HTMLResponse(
            ASSETS.joinpath("backtesting.js").read_text(), media_type="application/javascript"
        )

    @app.get("/dashboard", response_class=HTMLResponse)
    @app.get("/discovery", response_class=HTMLResponse)
    @app.get("/holdings", response_class=HTMLResponse)
    @app.get("/settings", response_class=HTMLResponse)
    @app.get("/learn", response_class=HTMLResponse)
    def investment_page() -> str:
        return ASSETS.joinpath("investment.html").read_text(encoding="utf-8")

    @app.get("/investment.js")
    def investment_script() -> HTMLResponse:
        return HTMLResponse(
            ASSETS.joinpath("investment.js").read_text(), media_type="application/javascript"
        )

    @app.get("/dialogs.js")
    def dialogs_script() -> HTMLResponse:
        return HTMLResponse(
            ASSETS.joinpath("dialogs.js").read_text(), media_type="application/javascript"
        )

    @app.get("/icons.svg")
    def ui_icons() -> HTMLResponse:
        return HTMLResponse(
            ASSETS.joinpath("icons.svg").read_text(encoding="utf-8"), media_type="image/svg+xml"
        )

    @app.get("/paper", response_class=HTMLResponse)
    def paper_page() -> str:
        return ASSETS.joinpath("desk.html").read_text(encoding="utf-8")

    @app.get("/strategies", response_class=HTMLResponse)
    def strategies_page() -> str:
        return ASSETS.joinpath("desk.html").read_text(encoding="utf-8")

    @app.exception_handler(Exception)
    async def safe_error(request: Request, exc: Exception) -> JSONResponse:
        engine.faulted = True
        engine.set_connected(False)
        desk.mode = "manual"
        if automation:
            automation.fail(clock())
        logging.getLogger(__name__).error("operator request failed; entries blocked")
        return JSONResponse(
            {"detail": "internal failure; entries blocked; inspect local journal"}, 503
        )

    @app.get("/", response_class=HTMLResponse)
    def dashboard() -> str:
        return ASSETS.joinpath("index.html").read_text(encoding="utf-8")

    @app.get("/console", response_class=HTMLResponse)
    def console_page() -> str:
        return ASSETS.joinpath("index.html").read_text(encoding="utf-8")

    @app.get("/workspace", response_class=HTMLResponse)
    def workspace_page() -> str:
        return ASSETS.joinpath("workspace.html").read_text(encoding="utf-8")

    @app.get("/workspace.js")
    def workspace_script() -> HTMLResponse:
        return HTMLResponse(
            ASSETS.joinpath("workspace.js").read_text(), media_type="application/javascript"
        )

    @app.get("/workspace-bridge.js")
    def workspace_bridge() -> HTMLResponse:
        return HTMLResponse(
            ASSETS.joinpath("workspace-bridge.js").read_text(), media_type="application/javascript"
        )

    @app.get("/api/workspace", dependencies=[Depends(authorized)])
    def workspace_status() -> dict[str, Any]:
        from trading_agent.market_data.calendar import IST
        from trading_agent.models import stamp

        now = clock()
        with engine.lock:
            s = engine.settings
            return {
                "mode": "paper",
                "investment_horizon": s.investment_horizon,
                "observed_at": stamp(now),
                "entry_start": s.entry_start.isoformat(timespec="minutes"),
                "entry_end": s.entry_end.isoformat(timespec="minutes"),
                "flatten_at": s.flatten_at.isoformat(timespec="minutes"),
                "max_quote_age_seconds": s.max_quote_age_seconds,
                "calendar_open": engine.calendar.is_open(now),
                "calendar_today": now.astimezone(IST).date() in engine.calendar.sessions,
                "feed_connected": engine.connected,
                "feed_requested": setup.stream is not None if setup else stream is not None,
                "automation_enabled": automation is not None,
                "automation_armed": automation.armed if automation else False,
                "decision_mode": desk.mode,
                "analysis_configured": desk.research is not None,
                "candidate_cap_per_symbol_day": automation.strategy.max_candidates_per_symbol_day
                if automation
                else None,
            }

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
            desk.pause(clock(), "OPERATOR_KILL")
            if automation:
                automation.disarm(clock(), "OPERATOR_KILL")
            engine.kill(clock())
        return {"kill": True}

    @app.post("/api/control/flatten", dependencies=[Depends(authorized)])
    def flatten() -> dict[str, bool]:
        with engine.lock:
            desk.pause(clock(), "OPERATOR_FLATTEN")
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
                desk.set_mode("automatic", clock(), desk.revision)
                return automation.status(clock())
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from None

    @app.post("/api/paper/automation/disarm", dependencies=[Depends(authorized)])
    def disarm() -> dict[str, Any]:
        if not automation:
            raise HTTPException(409, "paper automation is not configured")
        with engine.lock:
            desk.pause(clock(), "OPERATOR_DISARM")
            return automation.status(clock())

    return app
