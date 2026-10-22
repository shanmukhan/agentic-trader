"""Pure, authenticated workspace read models over existing account and research facts.

No desk view, expiry, strategy refresh, feed poll or recovery constructor runs here.
The independent SQLite connection is opened read-only, so accidental writes from a
future snapshot decorator fail without changing the account or in-memory authority.
"""

import json
import sqlite3
from contextlib import closing
from datetime import datetime
from decimal import Decimal
from typing import Any

from fastapi import Depends, HTTPException

from trading_agent.execution.quote_status import quote_status
from trading_agent.market_data.calendar import IST
from trading_agent.models import stamp, utc

RESEARCH_LIMIT = 500
POSITION_LIMIT = 10
DECISION_LIMIT = 10
SCREEN_FIELDS = (
    "symbol",
    "rank",
    "status",
    "reasons",
    "observations",
    "gross_total_return_pct",
    "index_level",
    "trend_index_average",
    "daily_volatility_pct",
    "average_turnover",
    "last_session",
    "last_close",
    "available_at",
    "membership_effective_session",
)
LIMIT_FIELDS = (
    "starting_cash",
    "max_trade_risk",
    "daily_loss_limit",
    "long_term_drawdown_limit",
    "max_position_notional",
    "max_total_notional",
    "max_positions",
    "max_consecutive_losses",
    "max_quote_age_seconds",
    "max_spread_bps",
    "slippage_bps",
    "latency_ms",
    "order_ttl_seconds",
)
DECISION_FIELDS = (
    "id",
    "symbol",
    "side",
    "state",
    "mode",
    "created_at",
    "updated_at",
    "outcome",
    "order_id",
)


def _discovery(research: Any, selected: set[str]) -> dict[str, Any]:
    result = research.result if research else None
    rows = result.get("rows", []) if result else []
    from trading_agent.investment_research.ranking import explain_ranking

    reviewed = (
        {
            s.symbol
            for s in research.profile.shares
            if result and s.reviewed_at <= datetime.fromisoformat(result["as_of"])
        }
        if research
        else set()
    )
    published_rows = [
        {
            **{key: row[key] for key in SCREEN_FIELDS if key in row},
            "subscribed": row["symbol"] in selected,
            "equity_share_class_reviewed": row["symbol"] in reviewed,
        }
        for row in rows[:RESEARCH_LIMIT]
    ]
    ranking = explain_ranking(published_rows, result.get("policy", {}) if result else {})
    return {
        "state": "available" if result else "missing",
        "as_of": result.get("as_of") if result else None,
        "latest_reviewed_completed_session": result.get("latest_reviewed_completed_session")
        if result
        else None,
        "rows": ranking.pop("rows"),
        "ranking": ranking,
        "candidate_count": result.get("candidate_count") if result else None,
        "policy": result.get("policy") if result else None,
        "quality": result.get("quality") if result else None,
        "source": {
            "description": research.dataset.manifest.source if research else None,
            "synthetic": research.dataset.manifest.synthetic if research else None,
            "universe_kind": research.dataset.manifest.universe_kind if research else None,
        },
        "row_limit": RESEARCH_LIMIT,
        "truncated": len(rows) > RESEARCH_LIMIT,
        "limitations": [
            "This is the last installed research screen, not a refresh or a live price list.",
            "A research candidate is not an order, forecast, backtest or investment approval.",
            "Gross research total returns are before execution costs and tax.",
            "Source and synthetic labels are dataset declarations, not external acceptance.",
            *(result.get("limitations", []) if result else []),
        ],
    }


def _portfolio(desk: Any, tx: sqlite3.Connection, now: datetime) -> dict[str, Any]:
    engine = desk.engine
    # These existing valuation methods only SELECT. The mode=ro connection also
    # enforces that contract if their implementation changes later.
    snapshot = engine._snapshot(tx, now)
    positions = snapshot["positions"]
    unvalued = snapshot.get("long_term", {}).get("unvalued_fractional_claims", 0)
    cash_only = not positions and not Decimal(snapshot.get("long_term", {}).get("receivable", "0"))
    state = (
        "incomplete"
        if unvalued
        else "empty"
        if cash_only
        else "fresh"
        if snapshot["valuation_fresh"]
        else "stale"
    )
    detail = {
        "incomplete": (
            "Unvalued fractional claims are excluded from the existing equity estimate. "
            "It is not a complete portfolio value. Review claims in Purchases & SIP."
        ),
        "empty": "No held shares or outstanding valued claims; equity is the ledger cash balance.",
        "fresh": (
            "Existing net-liquidation estimate uses accepted current bid prices, assumed "
            "slippage and hypothetical remaining exit fees; it is not a guaranteed sale value."
        ),
        "stale": (
            "Some held-share prices are stale, missing or unaccepted after connection. "
            "Existing estimates retain saved bids or cost-based fallback; they are not current."
        ),
    }[state]
    decorated = []
    for position in positions[:POSITION_LIMIT]:
        symbol = position["symbol"]
        quote = engine._quote(tx, symbol)
        decorated.append(
            {
                **position,
                "quote": {
                    **quote_status(engine, tx, symbol, now),
                    "bid": str(quote.bid) if quote else None,
                    "last": str(quote.last) if quote else None,
                    "source": quote.source if quote else None,
                },
            }
        )
    from trading_agent.investment_research.performance import unavailable_performance
    from trading_agent.investment_research.portfolio_metrics import allocation_snapshot

    allocation_input = {
        **snapshot,
        "positions": decorated,
        "positions_truncated": len(positions) > POSITION_LIMIT,
        "faulted": engine.faulted,
        "pending_order_count": tx.execute(
            "SELECT count(*) FROM orders WHERE state IN ('ACCEPTED','PARTIAL')"
        ).fetchone()[0],
    }
    allocation = allocation_snapshot(allocation_input)
    return {
        **snapshot,
        "positions": decorated,
        "position_count": len(positions),
        "position_limit": POSITION_LIMIT,
        "positions_truncated": len(positions) > POSITION_LIMIT,
        "remaining_cost_basis": str(sum((Decimal(p["cost"]) for p in positions), Decimal(0))),
        "net_unrealized_pnl": str(
            sum((Decimal(p["unrealized_pnl"]) for p in positions), Decimal(0))
        ),
        "allocation": allocation,
        "currency": "INR",
        "day_equity": engine.db.get(tx, "day_equity"),
        "accounting_day_current": snapshot["day"] == now.astimezone(IST).date().isoformat(),
        "valuation_state": state,
        "valuation_detail": detail,
        "provenance": {
            "kind": "paper_ledger",
            "synthetic": True if desk.synthetic else None,
            "detail": (
                "Synthetic/replay desk context; account values are simulated ledger values."
                if desk.synthetic
                else "Paper ledger; broker/replay origin of every historical fill is not certified."
            ),
        },
        "performance": {
            "daily_metrics": unavailable_performance(
                "ACCEPTED_DAILY_VALUATION_HISTORY_UNAVAILABLE",
                "The current ledger has no complete reviewed daily valuation/flow series.",
            ),
            "state": "unavailable",
            "total_return_pct": None,
            "cagr_pct": None,
            "sharpe": None,
            "benchmark_return_pct": None,
            "detail": (
                "This summary does not establish a complete valuation/flow history or benchmark. "
                "No portfolio return or risk-adjusted performance is inferred."
            ),
        },
        "limitations": [
            "Paper values are simulated; no real broker orders or settlement are represented.",
            "Day P&L uses the stored accounting-day equity baseline; no midnight close is assumed.",
            "Fees are already included in cash/basis and net liquidation; do not subtract again.",
            "Reserved cash and delivery buffers restrict spending; they are not spent cash.",
            "Exposure is the existing conservative risk measure, not market-value allocation.",
            "Viewing does not roll the accounting day, process fills or reconcile the account.",
        ],
    }


def _settings(desk: Any, now: datetime) -> dict[str, Any]:
    engine, research = desk.engine, desk.research
    settings = engine.settings
    local = now.astimezone(IST)
    values = settings.model_dump(mode="json", include=set(LIMIT_FIELDS))
    return {
        "mode": "paper",
        "investment_horizon": settings.investment_horizon,
        "decision_mode": desk.mode,
        "mode_reason": desk.reason,
        "feed_connected": engine.connected,
        "automation_configured": desk.automation is not None,
        "automation_armed": bool(desk.automation and desk.automation.armed),
        "session_open": engine.calendar.is_open(now),
        "calendar_today": local.date() in engine.calendar.sessions,
        "local_day": local.date().isoformat(),
        "entry_start": settings.entry_start.isoformat(timespec="minutes"),
        "entry_end": settings.entry_end.isoformat(timespec="minutes"),
        "entry_window_open": settings.entry_start <= local.time() < settings.entry_end,
        "flatten_at": settings.flatten_at.isoformat(timespec="minutes"),
        "limits": values,
        "strategy": {
            "configured": research is not None or desk.automation is not None,
            "mode": research.profile.strategy_mode if research else None,
            "holding_sessions": research.profile.long_term.max_hold_sessions
            if research and engine.long_term
            else None,
        },
        "limitations": [
            "These are the current bound account limits; this screen cannot change them.",
            "Long-term is the account horizon label; the current daily strategy has a finite "
            "holding-session cap and is not a validated months-to-years investment policy.",
            "A connected feed or open session does not prove execution readiness.",
        ],
    }


def _backtests() -> dict[str, Any]:
    return {
        "state": "registered_jobs",
        "commands": [
            {
                "label": "Check daily delivery backtest inputs",
                "command": ".venv/bin/trading-agent daily-backtest --help",
                "detail": "Needs reviewed daily and recorded execution/depth bundles and a "
                "long-term policy. Daily OHLC alone cannot reconstruct fills.",
            },
            {
                "label": "Check existing intraday replay backtest inputs",
                "command": ".venv/bin/trading-agent backtest --help",
                "detail": "Existing isolated intraday research engine is preserved; no new "
                "intraday feature is introduced by this workspace.",
            },
            {
                "label": "Inspect an invented offline demonstration",
                "command": ".venv/bin/trading-agent research-demo --help",
                "detail": "The optional demo creates synthetic evidence in a new output "
                "directory; its results do not establish market performance.",
            },
        ],
        "limitations": [
            "Registered browser jobs are separate from this read; "
            "launch depends on verified isolation.",
            "These help commands do not start jobs or change the connected paper account.",
            "CLI backtests use independent virtual accounts and new output directories.",
            "No run, return, benchmark or profitability claim is fabricated by this page.",
        ],
    }


def workspace_views_snapshot(desk: Any, now: datetime) -> dict[str, Any]:
    """Return one bounded read cut without changing SQLite or operator authority."""
    now = utc(now)
    engine = desk.engine
    with (
        engine.lock,
        closing(
            sqlite3.connect(engine.settings.database.resolve().as_uri() + "?mode=ro", uri=True)
        ) as tx,
    ):
        tx.row_factory = sqlite3.Row
        tx.execute("BEGIN")
        tokens = desk.execution_tokens[:10]
        selected = (
            {
                row[0]
                for row in tx.execute(
                    "SELECT symbol FROM instruments WHERE token IN ("
                    + ",".join("?" for _ in tokens)
                    + ")",
                    tokens,
                )
            }
            if tokens
            else set()
        )
        discovery = _discovery(desk.research, selected)
        rows = tx.execute(
            "SELECT payload FROM desk_decisions ORDER BY time DESC,id DESC LIMIT ?",
            (DECISION_LIMIT + 1,),
        ).fetchall()
        decisions = []
        for row in rows[:DECISION_LIMIT]:
            record = json.loads(row[0])
            decisions.append({key: record.get(key) for key in DECISION_FIELDS})
        return {
            "schema_version": 1,
            "observed_at": stamp(now),
            "capabilities": {
                "discovery": {
                    "state": discovery["state"],
                    "detail": "Installed prior-daily screen; filtering grants no authority.",
                },
                "portfolio": {
                    "state": "available",
                    "detail": "Current existing ledger valuation, with explicit freshness limits.",
                },
                "settings": {
                    "state": "read_only",
                    "detail": "Current bound limits; credentials and local paths are omitted.",
                },
                "backtests": {
                    "state": "registered_jobs",
                    "detail": "Registered isolated jobs; launch requires verified runtime "
                    "limits and inputs.",
                },
                "fundamentals": {
                    "state": "unsupported",
                    "detail": "No sourced fundamental statements or quality scores are installed.",
                },
                "allocation_snapshot": {
                    "state": "available",
                    "detail": "Current accepted-bid cash/held weights; quote coverage gates apply.",
                },
                "allocation": {
                    "state": "unsupported",
                    "detail": "No target-weight, issuer/sector taxonomy or rebalance workflow.",
                },
                "benchmark": {
                    "state": "unsupported",
                    "detail": "No configured comparable benchmark or certified return history.",
                },
            },
            "discovery": discovery,
            "portfolio": _portfolio(desk, tx, now),
            "settings": _settings(desk, now),
            "backtests": _backtests(),
            "dashboard": {
                "recent_decisions": decisions,
                "decision_limit": DECISION_LIMIT,
                "decisions_truncated": len(rows) > DECISION_LIMIT,
                "limitations": [
                    "Proposal states are the last materialized records; this read does not "
                    "expire, cancel, approve or execute them.",
                    "Full proposal, order and fill outcomes are reviewed in Paper Trading.",
                ],
            },
        }


def mount_workspace_views(
    app: Any, desk: Any, authorized: Any, assets: Any, clock: Any, setup: Any = None
) -> None:
    @app.get("/api/workspace/views", dependencies=[Depends(authorized)])
    def status() -> dict[str, Any]:
        try:
            return workspace_views_snapshot(desk, clock())
        except Exception:
            # A failed read must not enter the generic mutation failure handler,
            # which deliberately revokes authority for failed operator actions.
            raise HTTPException(
                503, "Workspace data could not be read. Refresh or inspect the local journal."
            ) from None
