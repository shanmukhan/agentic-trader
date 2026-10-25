"""Bounded, serialized operator views; polling never runs recovery or submits work."""

from datetime import datetime
from typing import TYPE_CHECKING, Any

from trading_agent.execution.paper_broker import PaperBroker
from trading_agent.execution.quote_status import quote_status
from trading_agent.models import stamp, utc

if TYPE_CHECKING:
    from trading_agent.paper.runtime import PaperFeed

ORDER_LIMIT = 200


def console_snapshot(
    engine: PaperBroker, now: datetime, automation: "PaperFeed | None" = None
) -> dict[str, Any]:
    now = utc(now)
    with engine.lock:
        with engine.db.read_snapshot() as tx:
            account = engine._snapshot(tx, now)
            rows = tx.execute(
                "SELECT * FROM orders ORDER BY rowid DESC LIMIT ?", (ORDER_LIMIT + 1,)
            ).fetchall()
            orders = [dict(row) for row in rows[:ORDER_LIMIT]]
            # Selected feeds honor the configured transport capacity. Manual services
            # show the ten most recently observed symbols, rather than the whole catalog.
            if engine.settings.stream_tokens:
                placeholders = ",".join("?" for _ in engine.settings.stream_tokens)
                symbols = [
                    row[0]
                    for row in tx.execute(
                        f"SELECT symbol FROM instruments WHERE token IN ({placeholders}) "
                        "ORDER BY symbol",
                        engine.settings.stream_tokens,
                    )
                ]
            else:
                symbols = [
                    row[0]
                    for row in tx.execute("SELECT symbol FROM quotes ORDER BY time DESC LIMIT 10")
                ]
            quotes = []
            for symbol in symbols:
                quote = engine._quote(tx, symbol)
                quotes.append(
                    {
                        **quote_status(engine, tx, symbol, now),
                        "reasons": engine._entry_reasons(tx, quote, now),
                    }
                )
            reasons = (
                []
                if any(not item["reasons"] for item in quotes)
                else sorted(
                    {reason for item in quotes for reason in item["reasons"]}
                    or set(engine._entry_reasons(tx, None, now))
                )
            )
        # PaperFeed.status opens its own transactions; never nest them inside the view above.
        controller: dict[str, Any] = (
            automation.status(now) if automation else {"enabled": False, "armed": False}
        )
        if automation:
            reasons = sorted(set(reasons + controller["readiness_reasons"]))
            if not controller["armed"]:
                reasons.append("AUTOMATION_DISARMED")
        return {
            "schema_version": 1,
            "observed_at": stamp(now),
            "account": account,
            "orders": orders,
            "orders_truncated": len(rows) > ORDER_LIMIT,
            "order_limit": ORDER_LIMIT,
            "quotes": quotes,
            "automation": controller,
            "entry_readiness": {"ready": not reasons, "reasons": reasons},
        }
