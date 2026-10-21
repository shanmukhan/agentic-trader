import sqlite3
from datetime import timedelta
from decimal import Decimal as D

import pytest
from conftest import NOW, candidate, quote

from trading_agent.execution.costs import Charges, delivery_charges
from trading_agent.execution.delivery import HoldingReview
from trading_agent.execution.paper_broker import PaperBroker
from trading_agent.persistence.database import Database
from trading_agent.risk.policy import policy_fingerprint
from trading_agent.settings import Settings


def review(
    engine, now=NOW, *, symbol="NSE:DEMO", clear=True, reference="synthetic price-basis review"
):
    return engine.review_holding(
        HoldingReview(
            symbol=symbol, session_date=now.date(), no_corporate_action=clear, reference=reference
        ),
        now,
    )


def buy(engine, *, stop="490", target="600", depth=100):
    review(engine)
    engine.ingest(quote(), NOW)
    order = engine.submit(candidate(stop=stop, target=target), NOW)
    assert order["state"] == "ACCEPTED", order
    engine.ingest(quote(1, ask_size=depth), NOW + timedelta(seconds=1))
    return order


def reconcile(engine):
    with engine.db.transaction() as tx:
        engine.db.reconcile(tx)


def test_legacy_intraday_policy_identity_and_separate_delivery_policy():
    assert (
        policy_fingerprint(Settings())
        == "642c1e1c9fabdd41278868d4e66108e201e7c1b15ddb888ed5ad9704afd1cbaa"
    )
    assert policy_fingerprint(Settings(investment_horizon="long_term")) != policy_fingerprint(
        Settings()
    )
    assert Charges().fee("BUY", D(10000)) == D("4.22")
    # Delivery ₹10k: STT 10 both sides; buy stamp 1.50; taxable turnover fees .31701 + 18% GST.
    assert delivery_charges().fee("BUY", D(10000)) == D("11.88")
    assert delivery_charges().fee("SELL", D(10000)) == D("25.72")
    assert delivery_charges().fee("SELL", D(0)) == 0


def test_overnight_and_weekend_holdings_are_preserved_without_session_exit(long_term_factory):
    engine = long_term_factory()
    order = buy(engine)
    close = NOW.replace(hour=9, minute=45)
    engine.poll(close)
    engine.poll(NOW + timedelta(days=4))  # deliberately unlisted Saturday
    state = engine.snapshot(NOW + timedelta(days=4))
    assert state["positions"][0]["quantity"] == order["quantity"]
    assert not state["kill"] and not state["valuation_fresh"]
    assert [item["side"] for item in engine.orders()] == ["BUY"]
    assert state["investment_horizon"] == "long_term"
    assert state["long_term"]["settlement_verified"] is False
    reconcile(engine)


def test_no_unreviewed_price_can_change_valuation_or_fill(long_term_factory):
    engine = long_term_factory()
    assert not engine.ingest(quote(), NOW)
    order = engine.submit(candidate(), NOW)
    assert order["state"] == "REJECTED" and "LONG_TERM_REVIEW_REQUIRED" in order["reason"]
    with engine.db.transaction() as tx:
        assert tx.execute("SELECT COUNT(*) FROM quotes").fetchone()[0] == 0
    review(engine)
    engine.ingest(quote(1), NOW + timedelta(seconds=1))
    assert (
        engine.submit(
            candidate("reviewed", now=NOW + timedelta(seconds=1), stop="490", target="600"),
            NOW + timedelta(seconds=1),
        )["state"]
        == "ACCEPTED"
    )
    reconcile(engine)


def test_review_is_idempotent_strict_current_date_and_registered_symbol(long_term_factory):
    engine = long_term_factory()
    review(engine)
    with engine.db.transaction() as tx:
        count = tx.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    review(engine)
    with engine.db.transaction() as tx:
        assert tx.execute("SELECT COUNT(*) FROM events").fetchone()[0] == count
    with pytest.raises(ValueError, match="current IST"):
        engine.review_holding(
            HoldingReview(
                symbol="NSE:DEMO",
                session_date=(NOW + timedelta(days=1)).date(),
                no_corporate_action=True,
                reference="future",
            ),
            NOW,
        )
    with pytest.raises(ValueError, match="registered"):
        review(engine, symbol="NSE:MISSING")
    with pytest.raises(ValueError):
        HoldingReview(
            symbol="NSE:DEMO", session_date=NOW.date(), no_corporate_action=1, reference="test"
        )
    reconcile(engine)


def test_blocked_action_cancels_entries_and_remains_quarantined_next_day(long_term_factory):
    engine = long_term_factory()
    review(engine)
    engine.ingest(quote(), NOW)
    engine.submit(candidate(stop="490", target="600"), NOW)
    review(engine, clear=False, reference="known split: unsupported adjustment")
    assert engine.orders()[0]["state"] == "CANCELLED"
    assert not engine.ingest(quote(1, bid="250", ask="250.05"), NOW + timedelta(seconds=1))
    tomorrow = NOW + timedelta(days=1)
    with pytest.raises(ValueError, match="unresolved corporate action"):
        review(engine, tomorrow)
    assert engine.snapshot(tomorrow)["long_term"]["quarantined_symbols"] == ["NSE:DEMO"]
    reconcile(engine)


def test_first_next_session_quote_keeps_opening_gap_in_daily_loss(long_term_factory):
    engine = long_term_factory(daily_loss_limit=D(100), max_trade_risk=D(100))
    buy(engine)
    prior = engine.snapshot(NOW + timedelta(seconds=1))
    tomorrow = NOW + timedelta(days=1)
    review(engine, tomorrow)
    engine.ingest(quote(base=tomorrow, bid="450", ask="450.05"), tomorrow)
    state = engine.snapshot(tomorrow)
    assert D(state["day_pnl"]) < -100
    assert state["kill"] and state["kill_reason"] == "DAILY_LOSS_LIMIT"
    assert state["long_term"]["daily_reference"] == prior["long_term"]["last_trusted_equity"]
    assert state["positions"]  # trigger quote never liquidates immediately
    engine.ingest(quote(1, base=tomorrow, bid="450", ask="450.05"), tomorrow + timedelta(seconds=1))
    assert not engine.snapshot(tomorrow + timedelta(seconds=1))["positions"]
    reconcile(engine)


def test_portfolio_drawdown_uses_persistent_peak_across_days(long_term_factory):
    engine = long_term_factory(long_term_drawdown_limit=D(500), daily_loss_limit=D(500))
    buy(engine, stop="350", target="1000")
    engine.ingest(quote(2, bid="900", ask="900.05"), NOW + timedelta(seconds=2))
    peak = engine.snapshot(NOW + timedelta(seconds=2))["long_term"]["peak_equity"]
    for days, bid in [(1, "700"), (2, "500"), (3, "350")]:
        now = NOW + timedelta(days=days)
        review(engine, now)
        engine.ingest(quote(base=now, bid=bid, ask=str(D(bid) + D(".05"))), now)
    state = engine.snapshot(now)
    assert state["long_term"]["peak_equity"] == peak
    assert state["kill"] and state["kill_reason"] == "LONG_TERM_DRAWDOWN_LIMIT"
    reconcile(engine)


def test_partial_exit_dp_once_per_stock_day_across_cancelled_orders(long_term_factory):
    engine = long_term_factory()
    buy(engine)
    tomorrow = NOW + timedelta(days=1)
    review(engine, tomorrow)
    engine.ingest(quote(base=tomorrow), tomorrow)
    first = engine.exit_holding("NSE:DEMO", tomorrow)["order"]
    engine.ingest(quote(1, base=tomorrow, bid_size=2), tomorrow + timedelta(seconds=1))
    engine.cancel(first["id"], tomorrow + timedelta(seconds=1))
    engine.poll(tomorrow + timedelta(seconds=1))
    engine.ingest(quote(2, base=tomorrow, bid_size=2), tomorrow + timedelta(seconds=2))
    with engine.db.transaction() as tx:
        assert (
            tx.execute("SELECT COUNT(*) FROM events WHERE kind='delivery_dp_charge'").fetchone()[0]
            == 1
        )
        assert sum(
            D(row[0]) for row in tx.execute("SELECT value FROM meta WHERE key GLOB 'lt_order_dp:*'")
        ) == D("15.34")
    day_three = NOW + timedelta(days=2)
    review(engine, day_three)
    engine.ingest(quote(base=day_three, bid_size=2), day_three)
    with engine.db.transaction() as tx:
        assert (
            tx.execute("SELECT COUNT(*) FROM events WHERE kind='delivery_dp_charge'").fetchone()[0]
            == 2
        )
    reconcile(engine)


def test_restart_keeps_position_and_requeues_latched_exit(long_term_factory):
    engine = long_term_factory()
    buy(engine)
    when = NOW + timedelta(seconds=2)
    old = engine.exit_holding("NSE:DEMO", when)["order"]
    settings, calendar = engine.settings, engine.calendar
    engine.db.close()
    db = Database(settings.database, settings.starting_cash)
    try:
        recovered = PaperBroker(db, settings, calendar, recovery_time=when)
        assert recovered.orders()[-1]["state"] == "CANCELLED"
        assert recovered.snapshot(when)["positions"] and not recovered.connected
        recovered.poll(when)
        assert recovered.orders()[-1]["side"] == "SELL"
        assert recovered.orders()[-1]["id"] != old["id"]
        recovered.set_connected(True)
        recovered.ingest(quote(3), NOW + timedelta(seconds=3))
        assert not recovered.snapshot(NOW + timedelta(seconds=3))["positions"]
        reconcile(recovered)
    finally:
        db.close()


def test_horizon_and_policy_change_fail_before_pending_recovery(long_term_factory):
    engine = long_term_factory()
    review(engine)
    engine.ingest(quote(), NOW)
    engine.submit(candidate(stop="490", target="600"), NOW)
    before = engine.orders()
    changed = engine.settings.model_copy(update={"investment_horizon": "intraday"})
    with pytest.raises(ValueError, match="horizon changed"):
        PaperBroker(engine.db, changed, engine.calendar, recovery_time=NOW)
    changed = engine.settings.model_copy(update={"long_term_drawdown_limit": D(2000)})
    with pytest.raises(ValueError, match="policy changed"):
        PaperBroker(engine.db, changed, engine.calendar, recovery_time=NOW)
    assert engine.orders() == before


@pytest.mark.parametrize(
    "key", ["investment_horizon", "long_term_schema", "lt_peak_equity", "lt_last_clock"]
)
def test_missing_durable_markers_are_never_reseeded(long_term_factory, key):
    engine = long_term_factory()
    buy(engine)
    with engine.db.transaction() as tx:
        tx.execute("DELETE FROM meta WHERE key=?", (key,))
    with pytest.raises(RuntimeError):
        reconcile(engine)


def test_clock_regression_and_changed_used_calendar_refused(long_term_factory):
    engine = long_term_factory()
    buy(engine)
    with pytest.raises(ValueError, match="backward"):
        engine.poll(NOW)
    engine.calendar.sources[NOW.date()] = "changed definition"
    with pytest.raises(ValueError, match="definition changed"):
        review(engine, NOW + timedelta(seconds=1))


def test_delivery_fee_and_review_corruption_detected(long_term_factory):
    engine = long_term_factory()
    buy(engine)
    engine.exit_holding("NSE:DEMO", NOW + timedelta(seconds=2))
    engine.ingest(quote(3), NOW + timedelta(seconds=3))
    reconcile(engine)
    with engine.db.transaction() as tx:
        tx.execute("UPDATE meta SET value='0' WHERE key GLOB 'lt_order_dp:*'")
    with pytest.raises(RuntimeError, match="DP charge metadata"):
        reconcile(engine)


def test_fee_allocation_rolls_back_with_failed_fill(long_term_factory, monkeypatch):
    engine = long_term_factory()
    buy(engine)
    engine.exit_holding("NSE:DEMO", NOW + timedelta(seconds=2))
    original = engine._fill
    before = engine.snapshot(NOW + timedelta(seconds=2))

    def failed(*args):
        original(*args)
        raise sqlite3.OperationalError("simulated disk fault")

    monkeypatch.setattr(engine, "_fill", failed)
    with pytest.raises(sqlite3.OperationalError):
        engine.ingest(quote(3), NOW + timedelta(seconds=3))
    assert engine.snapshot(NOW + timedelta(seconds=3))["cash"] == before["cash"]
    with engine.db.transaction() as tx:
        assert not tx.execute("SELECT 1 FROM meta WHERE key GLOB 'lt_dp:*'").fetchone()
        engine.db.reconcile(tx)


def test_exit_fee_cash_shortfall_preserves_holding_and_never_charges_unfilled_dp(long_term_factory):
    engine = long_term_factory(
        starting_cash=D(100),
        max_trade_risk=D(30),
        daily_loss_limit=D(40),
        long_term_drawdown_limit=D(50),
        max_position_notional=D(90),
        max_total_notional=D(90),
        max_positions=1,
    )
    review(engine)
    engine.ingest(quote(bid="40", ask="40.05"), NOW)
    order = engine.submit(candidate(stop="35", target="80"), NOW)
    assert order["quantity"] == 2
    engine.ingest(quote(1, bid="40", ask="40.05"), NOW + timedelta(seconds=1))
    engine.exit_holding("NSE:DEMO", NOW + timedelta(seconds=2))
    engine.ingest(quote(3, bid=".10", ask=".15", bid_size=1), NOW + timedelta(seconds=3))
    before = engine.snapshot(NOW + timedelta(seconds=3))
    assert before["positions"][0]["quantity"] == 1
    tomorrow = NOW + timedelta(days=1)
    review(engine, tomorrow)
    engine.ingest(quote(base=tomorrow, bid=".10", ask=".15"), tomorrow)
    state = engine.snapshot(tomorrow)
    assert state["cash"] == before["cash"] and D(state["cash"]) >= 0
    assert state["positions"][0]["quantity"] == 1 and not state["faulted"]
    with engine.db.transaction() as tx:
        assert (
            tx.execute("SELECT COUNT(*) FROM events WHERE kind='delivery_dp_charge'").fetchone()[0]
            == 1
        )
        assert tx.execute("SELECT 1 FROM events WHERE kind='long_term_exit_blocked'").fetchone()
    reconcile(engine)


def test_reported_action_preserves_original_price_and_cost_basis(long_term_factory):
    engine = long_term_factory()
    buy(engine)
    before = engine.snapshot(NOW + timedelta(seconds=1))
    tomorrow = NOW + timedelta(days=1)
    review(engine, tomorrow, clear=False, reference="known corporate action, not applied")
    assert not engine.ingest(quote(base=tomorrow, bid="250", ask="250.05"), tomorrow)
    after = engine.snapshot(tomorrow)
    assert after["positions"] == before["positions"]
    assert after["cash"] == before["cash"] and not after["valuation_fresh"]
    assert not after["kill"]
    reconcile(engine)


def test_same_day_two_stocks_have_independent_dp_charges(long_term_factory):
    engine = long_term_factory()
    buy(engine)
    now = NOW + timedelta(seconds=1)
    review(engine, now, symbol="NSE:SECOND")
    engine.ingest(quote(base=now, symbol="NSE:SECOND", token=2), now)
    entry = engine.submit(
        candidate("second", now=now, symbol="NSE:SECOND", stop="490", target="600"), now
    )
    assert entry["state"] == "ACCEPTED"
    engine.ingest(quote(1, base=now, symbol="NSE:SECOND", token=2), now + timedelta(seconds=1))
    for symbol in ["NSE:DEMO", "NSE:SECOND"]:
        engine.exit_holding(symbol, now + timedelta(seconds=1))
    engine.ingest(quote(3), NOW + timedelta(seconds=3))
    engine.ingest(quote(3, symbol="NSE:SECOND", token=2), NOW + timedelta(seconds=3))
    with engine.db.transaction() as tx:
        assert (
            tx.execute("SELECT COUNT(*) FROM events WHERE kind='delivery_dp_charge'").fetchone()[0]
            == 2
        )
    reconcile(engine)


def test_delivery_rejects_intraday_automation_and_ml_before_mutating_account(long_term_factory):
    engine = long_term_factory()
    before = engine.orders()
    with pytest.raises(ValueError, match="intraday model/automation"):
        PaperBroker(engine.db, engine.settings, engine.calendar, automation="intraday-controller")
    with pytest.raises(ValueError, match="intraday model/automation"):
        PaperBroker(engine.db, engine.settings, engine.calendar, model=object())
    assert engine.orders() == before


@pytest.mark.parametrize(
    "mutation",
    [
        "UPDATE meta SET value='NaN' WHERE key='lt_peak_equity'",
        "UPDATE meta SET value='1' WHERE key='lt_peak_equity'",
        "UPDATE meta SET value='2026-10-20T10:00:00' WHERE key='lt_last_clock'",
        "UPDATE meta SET value='2' WHERE key='long_term_schema'",
        "DELETE FROM events WHERE kind='long_term_review'",
        "DELETE FROM events WHERE kind='fill'",
        "UPDATE events SET payload='{}' WHERE kind='fill'",
        "UPDATE meta SET value='{}' WHERE key GLOB 'lt_review:*'",
        "DELETE FROM meta WHERE key GLOB 'lt_exit:*'",
        "DELETE FROM meta WHERE key GLOB 'lt_order_dp:*'",
    ],
)
def test_delivery_account_corruption_fails_closed(long_term_factory, mutation):
    engine = long_term_factory()
    buy(engine)
    engine.exit_holding("NSE:DEMO", NOW + timedelta(seconds=2))
    engine.ingest(quote(3), NOW + timedelta(seconds=3))
    with engine.db.transaction() as tx:
        tx.execute(mutation)
    with pytest.raises((RuntimeError, ValueError, KeyError)):
        reconcile(engine)


def test_held_symbols_cannot_be_omitted_from_restarted_feed_before_cancellation(long_term_factory):
    engine = long_term_factory()
    buy(engine)
    engine.exit_holding("NSE:DEMO", NOW + timedelta(seconds=2))
    before = engine.orders()
    changed = engine.settings.model_copy(update={"stream_tokens": (2,)})
    with pytest.raises(ValueError, match="every held symbol"):
        PaperBroker(engine.db, changed, engine.calendar, recovery_time=NOW + timedelta(seconds=2))
    assert engine.orders() == before


def test_long_term_drawdown_cannot_be_reset_by_waiting_for_a_new_day(long_term_factory):
    engine = long_term_factory(long_term_drawdown_limit=D(500), daily_loss_limit=D(500))
    buy(engine, stop="350", target="1000")
    engine.ingest(quote(2, bid="900", ask="900.05"), NOW + timedelta(seconds=2))
    tomorrow = NOW + timedelta(days=1)
    review(engine, tomorrow)
    engine.ingest(quote(base=tomorrow, bid="350", ask="350.05"), tomorrow)
    engine.ingest(quote(1, base=tomorrow, bid="350", ask="350.05"), tomorrow + timedelta(seconds=1))
    assert not engine.snapshot(tomorrow + timedelta(seconds=1))["positions"]
    with pytest.raises(ValueError, match="drawdown remains breached"):
        engine.reset_kill(NOW + timedelta(days=2))


def test_direct_delivery_drills_reconcile_and_preserve_quarantined_exposure(tmp_path):
    from trading_agent.paper.long_term_demo import long_term_demo

    result = long_term_demo(tmp_path / "drills")
    assert result["scenarios"]["overnight_restart"]["positions"] == 0
    assert result["scenarios"]["opening_gap"]["kill"]
    assert result["scenarios"]["corporate_action"]["quarantines"] == ["NSE:DEMO"]
    assert (tmp_path / "drills" / "corporate_action" / "evidence" / "manifest.json").is_file()
