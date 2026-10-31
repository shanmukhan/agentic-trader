"""Authenticated NSE catalog selection and explicit operator safety recovery."""

from typing import Any

from fastapi import Depends, HTTPException, Query
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, ConfigDict, Field

from trading_agent.models import Symbol, stamp


class WatchlistChange(BaseModel):
    model_config = ConfigDict(extra="forbid")
    symbols: list[Symbol] = Field(max_length=3000)
    revision: int = Field(ge=1, strict=True)
    acknowledged: bool = Field(strict=True)


class SafetyResume(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=1, strict=True)
    acknowledged: bool = Field(strict=True)


def mount_watchlist(app: Any, desk: Any, authorized: Any, assets: Any, clock: Any) -> None:
    e = desk.engine

    @app.get("/watchlist", response_class=HTMLResponse)
    def page() -> str:
        return assets.joinpath("watchlist.html").read_text()

    @app.get("/watchlist.js")
    def script() -> HTMLResponse:
        return HTMLResponse(
            assets.joinpath("watchlist.js").read_text(), media_type="application/javascript"
        )

    def view() -> dict[str, Any]:
        now = clock()
        with e.lock, e.db.read_snapshot() as tx:
            snapshot = e._snapshot(tx, now)
            state = e.safety.view(tx, now, snapshot)
            assert state is not None
            held = {r[0] for r in tx.execute("SELECT symbol FROM positions")}
            catalog = {r[0]: r[1] for r in tx.execute("SELECT symbol,token FROM instruments")}
            imported = tx.execute(
                "SELECT value FROM meta WHERE key='nse_catalog_imported_at'"
            ).fetchone()
            return {
                "schema_version": 1,
                "observed_at": stamp(now),
                "safety": state,
                "catalog_count": sum(token & 255 == 1 for token in catalog.values()),
                "catalog_imported_at": imported[0] if imported else None,
                "mode": desk.mode,
                "selected": [
                    {
                        "symbol": s,
                        "held": s in held,
                        "feed_selected": catalog.get(s) in e.settings.stream_tokens,
                        "catalog_available": s in catalog,
                    }
                    for s in state["symbols"]
                ],
                "held_outside_watchlist": sorted(held - set(state["symbols"])),
            }

    @app.get("/api/desk/watchlist", dependencies=[Depends(authorized)])
    def status() -> dict[str, Any]:
        return view()

    @app.get("/api/desk/watchlist/catalog", dependencies=[Depends(authorized)])
    def catalog(
        q: str = Query(default="", max_length=34), limit: int = Query(default=100, ge=1, le=100)
    ) -> dict[str, Any]:
        # Literal substring search: %, _ and quotes cannot alter the match or SQL.
        search = q.strip().upper().removeprefix("NSE:")
        with e.lock, e.db.read_snapshot() as tx:
            rows = [
                dict(r)
                for r in tx.execute(
                    "SELECT symbol,token FROM instruments WHERE (token & 255)=1 "
                    "AND instr(symbol,?)>0 ORDER BY symbol",
                    (search,),
                )
            ]
        return {
            "schema_version": 1,
            "matches": len(rows),
            "limit": limit,
            "items": rows[:limit],
            "observed_at": stamp(clock()),
        }

    @app.post("/api/desk/watchlist", dependencies=[Depends(authorized)])
    def replace(body: WatchlistChange) -> dict[str, Any]:
        if not body.acknowledged:
            raise HTTPException(409, "Review and acknowledge the watchlist change.")
        try:
            with e.lock:
                with e.db.transaction() as tx:
                    e.safety.replace(tx, body.symbols, body.revision, clock())
                desk.pause(clock(), "WATCHLIST_CHANGED_REVIEW_REQUIRED")
            return view()
        except ValueError as error:
            raise HTTPException(409, str(error)) from None

    @app.post("/api/desk/safety/resume", dependencies=[Depends(authorized)])
    def resume(body: SafetyResume) -> dict[str, Any]:
        if not body.acknowledged:
            raise HTTPException(409, "Acknowledge the new drawdown reference before resuming.")
        try:
            with e.lock:
                if desk.mode != "manual":
                    raise ValueError("Switch to manual mode before resuming the safety pause.")
                with e.db.transaction() as tx:
                    e.safety.resume(tx, body.revision, clock())
            return view()
        except ValueError as error:
            raise HTTPException(409, str(error)) from None
