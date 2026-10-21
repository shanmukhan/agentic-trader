"""Plain-language state and actionable next steps. Never grants trading authority."""

from datetime import datetime
from typing import Any

from trading_agent.market_data.calendar import IST
from trading_agent.models import stamp


def readiness(desk: Any, now: datetime, blockers: list[str]) -> dict[str, Any]:
    e = desk.engine
    with e.lock, e.db.transaction() as tx:
        tokens = desk.execution_tokens
        selected = (
            [
                dict(r)
                for r in tx.execute(
                    "SELECT symbol,token FROM instruments WHERE token IN ("
                    + ",".join("?" for _ in tokens)
                    + ") ORDER BY symbol",
                    tokens,
                )
            ]
            if tokens
            else []
        )
        quotes = []
        for row in selected:
            q = e._quote(tx, row["symbol"])
            quotes.append(
                {
                    "symbol": row["symbol"],
                    "usable": bool(q and e._fresh(q, now)),
                    "exchange_time": stamp(q.exchange_time) if q else None,
                    "received_time": stamp(q.received_time) if q else None,
                    "age_seconds": max(0, (now - q.exchange_time).total_seconds()) if q else None,
                    "basis_reviewed": e.long_term.reviewed(tx, row["symbol"], now)
                    if e.long_term
                    else None,
                }
            )
    local = now.astimezone(IST)
    bounds = e.calendar.bounds(now)
    future = [
        (day, times)
        for day, times in sorted(e.calendar.sessions.items())
        if datetime.combine(day, times[0], IST) > now
    ]
    next_open = datetime.combine(future[0][0], future[0][1][0], IST).isoformat() if future else None
    fresh = sum(q["usable"] for q in quotes)
    basis = sum(q["basis_reviewed"] is False for q in quotes)
    profile_ok = not any(
        r in blockers for r in ("NO_ANALYSIS_PROFILE", "ANALYSIS_PROFILE_INVALID_OR_UNAVAILABLE")
    )
    checks = [
        {
            "key": "strategy",
            "title": "Strategy and historical data",
            "ready": profile_ok,
            "detail": (
                desk.research.profile.name + " · " + desk.research.profile.strategy_mode
                if desk.research
                else "Existing bound intraday strategy"
                if desk.automation
                else "No strategy installed. A connected feed supplies quotes; "
                "it cannot create the strategy or historical data."
            ),
            "action": "Prepare strategy data",
            "href": "#strategy-setup",
        },
        {
            "key": "feed",
            "title": "Market-data connection",
            "ready": e.connected,
            "detail": "Socket connected. Quote usability is checked separately below."
            if e.connected
            else "Market-data socket is offline. Check the saved broker session "
            "and connect in Broker & data.",
            "action": "Open Broker & data",
            "href": "/setup",
        },
        {
            "key": "quotes",
            "title": "Usable execution quotes",
            "ready": fresh > 0,
            "detail": f"{fresh} of {len(quotes)} selected symbols have quotes within "
            f"the {e.settings.max_quote_age_seconds}-second limit. Empty bid/ask "
            "or zero-depth observations cannot fill an order.",
            "action": "Inspect quote details",
            "href": "#quote-details",
        },
        {
            "key": "session",
            "title": "Reviewed exchange session",
            "ready": e.calendar.is_open(now),
            "detail": f"Today’s reviewed session is {bounds[0].strftime('%H:%M')}–"
            f"{bounds[1].strftime('%H:%M')} IST; it is "
            f"{'open' if e.calendar.is_open(now) else 'closed'} now."
            if bounds
            else "Today has no reviewed session. Review exchange notices; "
            "a connected socket does not establish market hours.",
            "action": "Review calendar",
            "href": "/setup",
        },
        {
            "key": "entry_window",
            "title": "Strategy entry window",
            "ready": "OUTSIDE_ENTRY_WINDOW" not in blockers,
            "detail": f"New entries are allowed {e.settings.entry_start.strftime('%H:%M')}–"
            f"{e.settings.entry_end.strftime('%H:%M')} IST within a reviewed open session. "
            "Protective exits use their own rules.",
            "action": None,
            "href": None,
        },
    ]
    if e.long_term:
        checks.append(
            {
                "key": "basis",
                "title": "Today’s long-term price-basis reviews",
                "ready": basis == 0 and bool(quotes),
                "detail": f"{basis} selected symbols still need today’s corporate-action/"
                "price-basis review. Historical-data installation does not approve "
                "the current execution basis. New quotes are required after review.",
                "action": "Review in Advanced controls",
                "href": "/console",
            }
        )
    if desk.research:
        checks.append(
            {
                "key": "selection",
                "title": "Supported execution shortlist",
                "ready": not any(
                    r in blockers
                    for r in (
                        "NO_EXECUTION_SHORTLIST",
                        "EXECUTION_SHORTLIST_NOT_REVIEWED",
                        "UNSUPPORTED_HELD_ASSET_CLASS",
                    )
                ),
                "detail": "The execution list must use reviewed equity shares. Apply the ranked "
                "shortlist explicitly while disconnected; held symbols are always retained.",
                "action": "Review the ranked shortlist",
                "href": "#apply-shortlist",
            }
        )
        checks.append(
            {
                "key": "analysis",
                "title": "Analysis and model availability",
                "ready": not desk.analysis_error
                and not any(
                    r in blockers
                    for r in (
                        "ML_MODEL_NOT_CURRENT",
                        "RESEARCH_DAILY_HISTORY_UNAVAILABLE",
                        "RESEARCH_CALENDAR_NOT_CURRENT",
                    )
                ),
                "detail": "Rules only: experimental paper hypothesis; no ML filter is running."
                if desk.research.profile.strategy_mode == "rules"
                else "Rules + ML: matching model integrity, validation chronology "
                "and age are required.",
                "action": "Review strategy data",
                "href": "#strategy-setup",
            }
        )
    checks.append(
        {
            "key": "risk",
            "title": "Account controls",
            "ready": not any(r in blockers for r in ("KILL_SWITCH", "ACCOUNT_FAULTED")),
            "detail": "Kill/account faults must be resolved. Every individual proposal still "
            "passes independent cash, fees, spread, exposure and loss-limit checks.",
            "action": "Inspect safeguards",
            "href": "/console",
        }
    )
    return {
        "checks": checks,
        "quotes": quotes,
        "now_ist": local.isoformat(),
        "next_reviewed_open": next_open,
        "blocking_count": len(blockers),
        "can_start": not blockers,
        "next_action": "Choose Approval or Automatic and confirm. "
        "Each proposal still needs independent risk approval."
        if not blockers
        else "Prepare and review a strategy below first. Reconnecting alone will not enable modes."
        if not profile_ok
        else "Review the execution shortlist, then resolve the outstanding checks. "
        "Wait for an open entry session and fresh quotes.",
    }
