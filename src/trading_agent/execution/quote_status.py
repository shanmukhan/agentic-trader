"""Read-only quote explanations; none of these diagnostics grant execution authority."""

import sqlite3
from datetime import datetime
from typing import Any

from trading_agent.execution.paper_broker import PaperBroker
from trading_agent.models import stamp


def quote_status(
    engine: PaperBroker, tx: sqlite3.Connection, symbol: str, now: datetime
) -> dict[str, Any]:
    quote = engine._quote(tx, symbol)
    reviewed = engine.long_term.reviewed(tx, symbol, now) if engine.long_term else None
    fresh = engine._fresh(quote, now)
    if reviewed is False:
        status = "PRICE_BASIS_REVIEW_REQUIRED"
        detail = (
            "Today's price-basis review is missing or blocked. Incoming quotes cannot be "
            "accepted until that review is resolved and a new valid quote arrives. "
            "This does not mean the broker has stopped sending data."
        )
    elif not engine.connected:
        status, detail = "FEED_DISCONNECTED", "Feed disconnected. Saved quotes cannot be used."
    elif quote is None:
        status, detail = (
            "NO_ACCEPTED_QUOTE",
            ("No accepted quote is stored. Inspect the feed diagnostics in Broker & data."),
        )
    elif symbol in engine.bad_symbols:
        status, detail = (
            "QUOTE_REJECTED",
            (
                "A newer observation failed quote quality, depth or price-basis checks. "
                "Wait for a new valid quote; the saved quote cannot be used."
            ),
        )
    elif symbol not in engine.seen_symbols:
        status, detail = (
            "AWAITING_NEW_QUOTE",
            (
                "No quote has been accepted since the latest feed connection. "
                "Wait for a new valid quote."
            ),
        )
    elif not fresh:
        status, detail = (
            "STALE_QUOTE",
            (
                "The last accepted quote is outside the allowed exchange/receipt time window. "
                "Check the feed and system clock."
            ),
        )
    else:
        status, detail = "USABLE", "Fresh accepted quote; other execution checks still apply."
    return {
        "symbol": symbol,
        "status": status,
        "detail": detail,
        "usable": status == "USABLE",
        "fresh": fresh,
        "basis_reviewed": reviewed,
        "exchange_time": stamp(quote.exchange_time) if quote else None,
        "received_time": stamp(quote.received_time) if quote else None,
        "age_seconds": (now - quote.exchange_time).total_seconds() if quote else None,
    }
