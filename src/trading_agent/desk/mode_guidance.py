"""Read-only explanations of mode gates, using reviewed sessions and server time."""

from datetime import date, datetime, time
from typing import Any

from trading_agent.market_data.calendar import IST


def mode_guidance(
    now: datetime,
    blockers: list[str],
    sessions: dict[date, tuple[time, time]],
    entry_start: time,
    entry_end: time,
) -> dict[str, Any]:
    local = now.astimezone(IST)
    bounds = sessions.get(local.date())
    starts = []
    for day, (opening, closing) in sorted(sessions.items()):
        start = datetime.combine(day, max(opening, entry_start), IST)
        end = datetime.combine(day, min(closing, entry_end), IST)
        if start < end and start > now:
            starts.append(start)
    inside_entry = bool(
        bounds and max(bounds[0], entry_start) <= local.time() < min(bounds[1], entry_end)
    )
    next_entry = min(starts) if starts and not inside_entry else None
    window = f"{entry_start:%H:%M}–{entry_end:%H:%M} IST"
    items: list[dict[str, Any]] = []
    for code in dict.fromkeys(blockers):
        target: str | None = None
        kind = "action"
        if code == "WATCHLIST_EMPTY":
            title = "Choose permitted NSE stocks"
            detail = "The saved watchlist is empty. All new purchases are blocked."
            target = "watchlist"
        elif code == "SAFETY_PAUSED":
            title = "Review the drawdown pause"
            detail = "Entries remain paused until you review the account and reset its reference."
            target = "watchlist"
        elif code == "DATA_QUALITY_DAY_BLOCK":
            title = "Price integrity incident: no new entries today"
            detail = "The entry lockout lasts for this IST day, including after a restart."
            kind = "wait"
            target = "watchlist"
        elif code == "DAILY_TRADE_LIMIT":
            title = "Five entry slots used today"
            detail = "No more entries this IST day. Exits remain available."
            kind = "wait"
            target = "watchlist"
        elif code == "UNKNOWN_OR_CLOSED_SESSION":
            if bounds:
                title = "Wait for the reviewed market session"
                detail = f"Today's reviewed hours are {bounds[0]:%H:%M}–{bounds[1]:%H:%M} IST."
                kind = "wait"
            else:
                title = "Check the exchange calendar"
                detail = "Today has no reviewed session. Do not assume it is a trading day."
                target = "broker"
        elif code == "OUTSIDE_ENTRY_WINDOW":
            title = "Wait for the strategy entry window"
            detail = f"New paper entries are considered only {window} within a reviewed session."
            kind = "wait"
        elif code == "NO_FRESH_EXECUTION_QUOTES":
            title = "Wait for fresh usable prices"
            detail = (
                "A connected feed alone is not enough. New valid quotes must pass "
                "freshness and liquidity checks."
            )
            kind = "wait"
            if bounds and bounds[0] <= local.time() < bounds[1]:
                target = "broker"
        elif code == "FEED_DISCONNECTED":
            title, detail, target = (
                "Connect market data",
                "Check the saved Kite session and review the connection.",
                "broker",
            )
        elif code in ("KILL_SWITCH", "ACCOUNT_FAULTED", "UNSUPPORTED_HELD_ASSET_CLASS"):
            title, detail, target = (
                "Review account safeguards",
                "Resolve the account or holding restriction before starting a mode.",
                "risk",
            )
        elif code == "LONG_TERM_REVIEW_REQUIRED":
            title, detail, target = (
                "Review today's price basis",
                "Review corporate-action evidence for selected stocks, then wait for new quotes.",
                "risk",
            )
        elif code in ("NO_EXECUTION_SHORTLIST", "EXECUTION_SHORTLIST_NOT_REVIEWED"):
            title, detail, target = (
                "Review the execution shortlist",
                "Prepare and confirm the stocks this paper strategy may trade.",
                "strategy",
            )
        elif code == "STRATEGY_INSTALLING":
            title, detail, kind = (
                "Strategy setup is finishing",
                "Wait for the current installation to finish.",
                "wait",
            )
        else:
            title = "Review strategy setup"
            detail = "Resolve this server check: " + code.replace("_", " ").lower() + "."
            target = "strategy"
        items.append(
            {"code": code, "title": title, "detail": detail, "kind": kind, "target": target}
        )
    if (
        not next_entry
        and not inside_entry
        and any(code in blockers for code in ("UNKNOWN_OR_CLOSED_SESSION", "OUTSIDE_ENTRY_WINDOW"))
        and bounds
    ):
        items.append(
            {
                "code": "NEXT_SESSION_REVIEW_REQUIRED",
                "title": "Review the next exchange session",
                "detail": (
                    "No future reviewed entry time is available. "
                    "Review the calendar before the next trading session."
                ),
                "kind": "action",
                "target": "broker",
            }
        )
    state = (
        "ready"
        if not blockers
        else "action_required"
        if any(i["kind"] == "action" for i in items)
        else "waiting"
    )
    if state == "ready":
        title, summary = (
            "Ready to review a paper mode",
            "Choose Approval or Automatic, review its effects and confirm.",
        )
    elif state == "action_required":
        title, summary = (
            "A few setup checks need attention",
            "Complete the steps below. Status updates automatically; your mode stays unchanged.",
        )
    else:
        title = (
            "Waiting for the next entry session" if next_entry else "Waiting for usable market data"
        )
        summary = (
            "Your setup can stay in place. Wait for the time and price checks below. "
            "These checks do not require repeated sign-in or history downloads."
        )
    return {
        "schema_version": 1,
        "state": state,
        "title": title,
        "summary": summary,
        "now_ist": local.isoformat(),
        "entry_window": window,
        "next_entry_at": next_entry.isoformat() if next_entry else None,
        "items": items,
        "automatic_start": False,
    }
