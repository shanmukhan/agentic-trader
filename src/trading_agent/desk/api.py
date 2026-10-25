"""Authenticated decision controls; all proposals originate in the server strategy pipeline."""

import json
from typing import Any

from fastapi import Depends, HTTPException, Query
from fastapi.responses import HTMLResponse

from trading_agent.desk.activity import activity, fill_page
from trading_agent.desk.contracts import DecisionAction, ModeRequest
from trading_agent.desk.service import DeskError


def mount_desk(
    app: Any, desk: Any, setup: Any, authorized: Any, assets: Any, clock: Any, preparation: Any
) -> None:
    from trading_agent.desk.guided import GuidedConfirm, GuidedPreview, GuidedSetup

    guided = GuidedSetup(preparation)
    app.state.guided_setup = guided

    @app.get("/desk", response_class=HTMLResponse)
    def page() -> str:
        return assets.joinpath("desk.html").read_text()

    @app.get("/activity", response_class=HTMLResponse)
    def activity_page() -> str:
        return assets.joinpath("activity.html").read_text()

    @app.get("/desk.js")
    def script() -> HTMLResponse:
        return HTMLResponse(
            assets.joinpath("desk.js").read_text(), media_type="application/javascript"
        )

    @app.get("/api/desk", dependencies=[Depends(authorized)])
    def status() -> dict:
        return {
            **desk.view(clock()),
            "preparation": preparation.view(),
            "guided_setup": guided.view(),
        }

    @app.get("/api/desk/alerts", dependencies=[Depends(authorized)])
    def alerts() -> dict:
        """Bounded persisted proposal metadata; reading never expires or approves a trade."""
        from trading_agent.models import stamp

        with desk.engine.db.read_snapshot() as tx:
            records = [
                json.loads(row[0])
                for row in tx.execute(
                    "SELECT payload FROM desk_decisions "
                    "ORDER BY (state='awaiting_approval') DESC,rowid DESC LIMIT 100"
                )
            ]
        return {
            "observed_at": stamp(clock()),
            "decisions": [
                {key: record[key] for key in ("id", "state", "expires_at")} for record in records
            ],
            "limit": 100,
        }

    @app.get("/preparation.js")
    def preparation_script() -> HTMLResponse:
        return HTMLResponse(
            assets.joinpath("preparation.js").read_text(), media_type="application/javascript"
        )

    from trading_agent.desk.preparation import DownloadRequest, InstallRequest

    def prepare_action(action: Any) -> dict:
        from trading_agent.api.setup import SetupError

        try:
            return action()
        except SetupError:
            raise
        except Exception:
            raise SetupError(
                "Preparation could not be saved or validated. Refresh status and "
                "inspect local preparation files before retrying. No mode was activated."
            ) from None

    @app.post("/api/desk/preparation/download", dependencies=[Depends(authorized)])
    def download(body: DownloadRequest) -> dict:
        return prepare_action(lambda: preparation.start(body))

    @app.post("/api/desk/preparation/cancel", dependencies=[Depends(authorized)])
    def cancel_download() -> dict:
        return prepare_action(preparation.cancel)

    @app.post("/api/desk/preparation/install", dependencies=[Depends(authorized)])
    def install(body: InstallRequest) -> dict:
        return prepare_action(lambda: preparation.install(body))

    @app.post("/api/desk/preparation/guided/preview", dependencies=[Depends(authorized)])
    def guided_preview(body: GuidedPreview) -> dict:
        return prepare_action(lambda: guided.preview(body))

    @app.post("/api/desk/preparation/guided/confirm", dependencies=[Depends(authorized)])
    def guided_confirm(body: GuidedConfirm) -> dict:
        return prepare_action(lambda: guided.confirm(body))

    @app.post("/api/desk/mode", dependencies=[Depends(authorized)])
    def mode(body: ModeRequest) -> dict:
        try:
            return desk.set_mode(body.mode, clock(), body.revision)
        except DeskError as error:
            raise HTTPException(409, str(error)) from None

    @app.post("/api/desk/decisions/{identity}/preview", dependencies=[Depends(authorized)])
    def preview(identity: str) -> dict:
        try:
            return desk.preview(identity, clock())
        except DeskError as error:
            raise HTTPException(409, str(error)) from None

    @app.post("/api/desk/decisions/{identity}/approve", dependencies=[Depends(authorized)])
    def approve(identity: str, body: DecisionAction) -> dict:
        try:
            return desk.approve(identity, body.preview_sha256, clock())
        except DeskError as error:
            raise HTTPException(409, str(error)) from None

    @app.post("/api/desk/decisions/{identity}/reject", dependencies=[Depends(authorized)])
    def reject(identity: str) -> dict:
        try:
            return desk.reject(identity, clock())
        except DeskError as error:
            raise HTTPException(409, str(error)) from None

    @app.get("/api/activity", dependencies=[Depends(authorized)])
    def history(
        before: int = Query(default=0, ge=0), limit: int = Query(default=50, ge=1, le=100)
    ) -> dict:
        return activity(desk.engine, clock(), before, limit)

    @app.get("/api/activity/orders/{identity}/fills", dependencies=[Depends(authorized)])
    def fills(identity: str, before: int = Query(default=0, ge=0)) -> dict:
        try:
            return fill_page(desk.engine, identity, before)
        except KeyError:
            raise HTTPException(404, "Unknown paper order.") from None

    @app.post("/api/desk/shortlist", dependencies=[Depends(authorized)])
    def shortlist(body: DecisionAction) -> dict:
        if not setup or not desk.research:
            raise HTTPException(
                409, "A reviewed broad-market profile and manual feed setup are required."
            )
        # Preserve the existing setup -> engine lock order.
        with setup.lock:
            with desk.engine.lock, desk.engine.db.transaction() as tx:
                if desk.mode != "manual":
                    raise HTTPException(
                        409, "Switch to manual mode before replacing the shortlist."
                    )
                plan = desk.shortlist(tx)
                if not plan or not plan["catalog_candidates"] or not plan["symbols"]:
                    raise HTTPException(
                        409, "No qualified reviewed shortlist; nothing was replaced."
                    )
                if plan["preview_sha256"] != body.preview_sha256:
                    raise HTTPException(409, "Shortlist changed. Refresh and review again.")
            try:
                setup.select_symbols({"symbols": plan["symbols"]})
            except ValueError:
                raise HTTPException(
                    409,
                    "Disconnect market data and resolve pending orders before applying "
                    "the shortlist. Held symbols are always retained.",
                ) from None
        return desk.view(clock())
