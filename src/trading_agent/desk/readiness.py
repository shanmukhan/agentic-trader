"""Plain-language state and actionable next steps. Never grants trading authority."""

from datetime import datetime
from typing import Any

from trading_agent.execution.quote_status import quote_status
from trading_agent.market_data.calendar import IST


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
            quotes.append(quote_status(e, tx, row["symbol"], now))
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
            "or zero-depth observations cannot fill an order."
            + (
                f" {basis} symbols await today's price-basis review; incoming quotes "
                "are blocked before storage until review is resolved."
                if basis
                else ""
            ),
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
                "href": "#execution-shortlist",
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
    if not blockers:
        next_action = (
            "Choose Approval or Automatic and confirm. "
            "Each proposal still needs independent risk approval."
        )
    elif not profile_ok:
        next_action = (
            "Prepare and review a strategy below first. Reconnecting alone will not enable modes."
        )
    elif any(r in blockers for r in ("EXECUTION_SHORTLIST_NOT_REVIEWED", "NO_EXECUTION_SHORTLIST")):
        next_action = (
            "Review the execution shortlist and apply it while disconnected in Manual. "
            "Then resolve today's price-basis reviews and wait for new valid quotes."
        )
    elif basis:
        next_action = (
            f"Resolve today's price-basis reviews for {basis} selected symbols in Advanced "
            "controls, then wait for new valid quotes. An open market does not clear this review."
        )
    elif not e.connected:
        next_action = "Check the broker session and connect market data in Broker & data."
    elif not e.calendar.is_open(now) or "OUTSIDE_ENTRY_WINDOW" in blockers:
        next_action = (
            "Wait for a reviewed open entry session; inspect the session and entry-window checks."
        )
    elif not fresh:
        next_action = (
            "The reviewed session is open. Inspect quote details and feed diagnostics "
            "for the remaining quote blocker."
        )
    else:
        next_action = "Resolve the outstanding readiness checks before choosing a trading mode."
    return {
        "checks": checks,
        "quotes": quotes,
        "now_ist": local.isoformat(),
        "session_open": e.calendar.is_open(now),
        "next_reviewed_open": next_open,
        "blocking_count": len(blockers),
        "can_start": not blockers,
        "next_action": next_action,
    }
