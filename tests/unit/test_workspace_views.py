"""Pure workspace query checks; all data and economic scenarios are invented."""

import copy
import json
import sqlite3
from contextlib import closing
from datetime import timedelta
from decimal import Decimal as D

import pytest
from conftest import NOW, candidate, quote

from trading_agent.api.workspace_views import workspace_views_snapshot
from trading_agent.corporate_actions.contracts import ActionBatch, digest
from trading_agent.corporate_actions.service import apply_batch
from trading_agent.desk.service import TradingDesk
from trading_agent.persistence.database import Database


def dump(engine):
    with closing(sqlite3.connect(engine.settings.database)) as db:
        return list(db.iterdump())


def authority(desk):
    engine = desk.engine
    return (
        desk.mode,
        desk.mode_day,
        desk.reason,
        desk.revision,
        desk.last_analysis,
        desk.analysis_error,
        engine.connected,
        engine.faulted,
        set(engine.bad_symbols),
        set(engine.seen_symbols),
    )


def test_current_research_is_copied_with_declared_source_and_no_invented_metrics(desk_factory):
    desk, _, _ = desk_factory()
    original = copy.deepcopy(desk.research.result)
    before = dump(desk.engine)
    view = workspace_views_snapshot(desk, NOW)
    discovery = view["discovery"]
    assert discovery["state"] == "available"
    assert discovery["source"]["synthetic"] is True
    assert discovery["source"]["description"] == "INVENTED test data"
    assert discovery["as_of"] == original["as_of"]
    assert discovery["latest_reviewed_completed_session"] == "2026-10-19"
    assert discovery["policy"] == original["policy"]
    assert len(discovery["rows"]) == len(original["rows"]) == 3
    for row in discovery["rows"]:
        saved = next(item for item in original["rows"] if item["symbol"] == row["symbol"])
        assert len(row["evidence"]) == 5
        assert all(item["state"] in {"passed", "failed", "unavailable"} for item in row["evidence"])
        assert {
            k: v
            for k, v in row.items()
            if k not in {"subscribed", "evidence", "equity_share_class_reviewed"}
        } == saved
        assert row["subscribed"] == (row["symbol"] == "NSE:DEMO")
    assert view["portfolio"]["provenance"]["synthetic"] is True
    assert view["capabilities"]["fundamentals"]["state"] == "unsupported"
    assert desk.research.result == original
    assert dump(desk.engine) == before


def test_unconfigured_sources_are_missing_and_performance_is_unknown_not_zero(engine):
    desk = TradingDesk(engine, NOW)
    before = dump(engine)
    view = workspace_views_snapshot(desk, NOW)
    assert view["discovery"]["state"] == "missing"
    assert view["discovery"]["as_of"] is None
    assert view["discovery"]["candidate_count"] is None
    assert view["discovery"]["source"]["synthetic"] is None
    assert view["discovery"]["rows"] == []
    portfolio = view["portfolio"]
    assert portfolio["positions"] == [] and portfolio["valuation_state"] == "empty"
    assert D(portfolio["cash"]) == D(portfolio["equity"]) == D("25000")
    assert portfolio["performance"]["state"] == "unavailable"
    assert portfolio["performance"]["total_return_pct"] is None
    assert portfolio["performance"]["cagr_pct"] is None
    assert portfolio["performance"]["sharpe"] is None
    assert portfolio["performance"]["benchmark_return_pct"] is None
    assert portfolio["provenance"]["synthetic"] is None
    assert view["backtests"]["state"] == "registered_jobs"
    assert all(item["command"].endswith(" --help") for item in view["backtests"]["commands"])
    assert dump(engine) == before


def test_read_past_expiry_and_session_rollover_preserves_authority_and_entire_database(
    desk_factory,
):
    desk, _, _ = desk_factory()
    desk.set_mode("approval", NOW, desk.revision)
    decision = desk.offer(candidate(), NOW, {"kind": "intraday", "signal_key": "fixture"})
    assert decision["state"] == "awaiting_approval"
    engine = desk.engine
    before, memory = dump(engine), authority(desk)
    view = workspace_views_snapshot(desk, NOW + timedelta(days=1))
    assert not view["portfolio"]["accounting_day_current"]
    assert view["portfolio"]["day"] == "2026-10-20"
    assert view["settings"]["local_day"] == "2026-10-21"
    assert view["settings"]["decision_mode"] == "approval"
    assert view["dashboard"]["recent_decisions"][0]["state"] == "awaiting_approval"
    assert view["dashboard"]["recent_decisions"][0]["id"] == decision["id"]
    assert authority(desk) == memory
    assert dump(engine) == before


def test_partial_fill_summary_agrees_with_independent_persisted_cash_basis_and_reservations(
    engine,
):
    desk = TradingDesk(engine, NOW)
    order = engine.submit(candidate(), NOW)
    now = NOW + timedelta(seconds=1)
    engine.ingest(quote(1, ask_size=3), now)
    with closing(sqlite3.connect(engine.settings.database)) as db:
        db.row_factory = sqlite3.Row
        fills = db.execute("SELECT quantity,price,fees FROM fills").fetchall()
        assert sum(row["quantity"] for row in fills) == 3 < order["quantity"]
        fees = sum((D(row["fees"]) for row in fills), D(0))
        cost = sum((D(row["price"]) * row["quantity"] for row in fills), D(0)) + fees
        expected_cash = D("25000") - cost
        remaining = db.execute("SELECT reserved_cash,state FROM orders").fetchone()
        assert remaining["state"] == "PARTIAL"
        assert D(db.execute("SELECT cost FROM positions").fetchone()[0]) == cost
        assert D(db.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0]) == (
            expected_cash
        )
    before, memory = dump(engine), authority(desk)
    portfolio = workspace_views_snapshot(desk, now)["portfolio"]
    assert D(portfolio["cash"]) == expected_cash
    assert D(portfolio["fees"]) == fees
    assert D(portfolio["reserved_cash"]) == D(remaining["reserved_cash"])
    assert D(portfolio["available_cash"]) == expected_cash - D(remaining["reserved_cash"])
    assert D(portfolio["remaining_cost_basis"]) == cost
    position = portfolio["positions"][0]
    assert position["quantity"] == 3 and D(position["cost"]) == cost
    assert position["quote"]["status"] == "USABLE"
    assert D(portfolio["net_unrealized_pnl"]) == D(position["unrealized_pnl"])
    assert D(portfolio["equity"]) == expected_cash + D(position["liquidation_value"])
    assert D(portfolio["day_pnl"]) == D(portfolio["equity"]) - D(portfolio["day_equity"])
    allocation = portfolio["allocation"]
    assert allocation["state"] == "available"
    assert D(allocation["gross_market_value"]) == D("1499.85")
    assert D(allocation["allocation_base"]) == expected_cash + D("1499.85")
    assert D(allocation["cash_balance"]) == expected_cash
    assert D(allocation["commitments"]["reserved_cash"]) == D(remaining["reserved_cash"])
    assert allocation["commitments"]["pending_order_count"] == 1
    assert allocation["positions"][0]["quantity"] == 3
    assert portfolio["valuation_state"] == "fresh"
    stale = workspace_views_snapshot(desk, now + timedelta(seconds=10))["portfolio"]
    assert stale["valuation_state"] == "stale" and not stale["valuation_fresh"]
    assert stale["equity"] == portfolio["equity"]
    assert stale["positions"][0]["quote"]["status"] == "STALE_QUOTE"
    assert stale["allocation"]["state"] == "unavailable"
    assert stale["allocation"]["cash_weight_pct"] is None
    assert stale["allocation"]["positions"][0]["weight_pct"] is None
    assert authority(desk) == memory and dump(engine) == before
    with engine.db.transaction() as tx:
        Database.reconcile(tx)


def test_unknown_fraction_claim_stays_explicitly_incomplete_not_complete_equity(corporate_account):
    engine = corporate_account
    now = NOW + timedelta(days=1)
    with engine.db.transaction() as tx:
        quarantine = json.loads(engine.db.get(tx, "lt_quarantine:NSE:DEMO"))
    batch = ActionBatch.model_validate(
        {
            "batch_id": "workspace-fraction",
            "symbol": "NSE:DEMO",
            "quarantine_sha256": digest(quarantine),
            "reviewed_at": now.isoformat(),
            "reference": "INVENTED action review",
            "covers_all_actions": True,
            "actions": [
                {
                    "action_id": "workspace-bonus",
                    "kind": "bonus",
                    "ex_date": "2026-10-21",
                    "record_date": "2026-10-21",
                    "credit_date": "2026-10-21",
                    "announced_at": NOW.isoformat(),
                    "reference": "INVENTED bonus notice",
                    "numerator": 1,
                    "denominator": 3,
                }
            ],
        }
    )
    applied = apply_batch(engine.db, engine.settings, engine.calendar, batch, now)
    assert applied["result"]["claims"][0]["amount"] is None
    desk = TradingDesk(engine, now)
    before = dump(engine)
    portfolio = workspace_views_snapshot(desk, now)["portfolio"]
    assert portfolio["valuation_state"] == "incomplete"
    assert not portfolio["valuation_fresh"]
    assert "not a complete portfolio value" in portfolio["valuation_detail"]
    assert portfolio["long_term"]["unvalued_fractional_claims"] == 1
    assert portfolio["performance"]["total_return_pct"] is None
    with closing(sqlite3.connect(engine.settings.database)) as db:
        basis = D(db.execute("SELECT cost FROM positions").fetchone()[0])
        assert D(portfolio["remaining_cost_basis"]) == basis
        assert D(portfolio["cash"]) == D(
            db.execute("SELECT value FROM meta WHERE key='cash'").fetchone()[0]
        )
    assert dump(engine) == before
    with engine.db.transaction() as tx:
        Database.reconcile(tx)


def test_query_connection_itself_rejects_accidental_financial_write(engine, monkeypatch):
    desk = TradingDesk(engine, NOW)
    before, memory = dump(engine), authority(desk)

    def incorrect_snapshot(tx, now):
        tx.execute("UPDATE meta SET value='1' WHERE key='cash'")
        raise AssertionError("read-only connection should have refused the write")

    monkeypatch.setattr(engine, "_snapshot", incorrect_snapshot)
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        workspace_views_snapshot(desk, NOW)
    assert dump(engine) == before and authority(desk) == memory


def test_output_is_bounded_to_current_research_and_recent_decisions(desk_factory):
    desk, _, _ = desk_factory()
    desk.set_mode("approval", NOW, desk.revision)
    for number in range(12):
        desk.offer(candidate(str(number)), NOW, {"kind": "intraday", "signal_key": str(number)})
    before = dump(desk.engine)
    view = workspace_views_snapshot(desk, NOW)
    assert len(view["dashboard"]["recent_decisions"]) == 10
    assert view["dashboard"]["decisions_truncated"]
    assert view["dashboard"]["decision_limit"] == 10
    assert view["discovery"]["row_limit"] == 500
    assert not view["discovery"]["truncated"]
    assert dump(desk.engine) == before
