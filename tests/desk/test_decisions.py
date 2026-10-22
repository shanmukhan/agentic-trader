import json
from datetime import timedelta
from decimal import Decimal as D

import pytest
from conftest import NOW, candidate, quote

from trading_agent.desk.service import DeskError, TradingDesk
from trading_agent.desk.signals import AnalysisWorker
from trading_agent.models import Candle
from trading_agent.persistence.database import Database


def offer(desk, now=NOW, identity="strategy-signal"):
    candle = Candle(
        symbol="NSE:DEMO",
        start=now - timedelta(minutes=5),
        minutes=5,
        open=D(500),
        high=D(500),
        low=D(499),
        close=D(500),
        volume=10000,
    )
    return desk.offer(
        candidate(identity, now=now),
        now,
        {
            "kind": "intraday",
            "signal_key": "one-per-session",
            "candle": candle.model_dump(mode="json"),
            "features": {"ema": "499", "vwap": "499", "atr": "1", "relative_volume": "2"},
        },
    )


def activate(desk, mode="approval", now=NOW):
    return desk.set_mode(mode, now, desk.revision)


def test_manual_watchlist_and_no_profile_never_claim_best_stocks(engine):
    desk = TradingDesk(engine, NOW)
    data = desk.view(NOW)
    assert data["mode"] == "manual" and data["selection_basis"] == "operator_watchlist"
    assert data["discovery"] is None and not data["model_available"]
    with pytest.raises(DeskError, match="NO_ANALYSIS_PROFILE"):
        activate(desk, "automatic")
    assert offer(desk) is None and not engine.orders()


def test_broad_discovery_excludes_unreviewed_etf_and_never_uses_future_close(desk_factory):
    desk, profile, directory = desk_factory()
    assert desk.problem == ""
    data = desk.view(NOW)
    assert len(data["discovery"]["rows"]) == 3
    rows = {r["symbol"]: r for r in data["discovery"]["rows"]}
    assert rows["NSE:ETF"]["rank"] is None
    assert "EQUITY_SHARE_CLASS_NOT_REVIEWED" in rows["NSE:ETF"]["reasons"]
    assert data["shortlist"]["symbols"] == ["NSE:BROAD", "NSE:DEMO"]
    assert data["selected"][0]["symbol"] == "NSE:DEMO"
    assert data["discovery"]["latest_reviewed_completed_session"] == str(
        NOW.date() - timedelta(days=1)
    )
    assert not desk.engine.orders()


def test_semi_autonomous_preview_approval_reprices_with_bounds_and_exact_fills(desk_factory):
    desk, _, _ = desk_factory()
    e = desk.engine
    activate(desk)
    record = offer(desk)
    assert record["state"] == "awaiting_approval" and not e.orders()
    preview = desk.preview(record["id"], NOW)
    assert preview["review"]["allowed"] and not e.orders()
    assert D(e.snapshot(NOW)["reserved_cash"]) == 0
    e.ingest(quote(1, ask="500.05", bid="500.00"), NOW + timedelta(seconds=1))
    result = desk.approve(record["id"], preview["preview_sha256"], NOW + timedelta(seconds=1))
    assert result["state"] == "submitted" and result["authorized_by"] == "operator"
    order = e.orders()[0]
    assert order["state"] == "ACCEPTED" and order["filled"] == 0
    assert order["quantity"] <= preview["review"]["maximum_quantity"]
    e.ingest(quote(2, ask="500.05", bid="500.00"), NOW + timedelta(seconds=2))
    with e.db.transaction() as tx:
        fills = tx.execute("SELECT * FROM fills").fetchall()
        debit = sum((D(r["price"]) * r["quantity"] + D(r["fees"]) for r in fills), D(0))
        assert D(Database.get(tx, "cash")) == D("25000") - debit
        assert D(Database.get(tx, "fees")) == sum((D(r["fees"]) for r in fills), D(0))
        Database.reconcile(tx)
    again = desk.approve(record["id"], preview["preview_sha256"], NOW + timedelta(seconds=2))
    assert again["order_id"] == result["order_id"] and len(e.orders()) == 1


def test_automatic_needs_explicit_mode_and_submits_without_trade_approval(desk_factory):
    desk, _, _ = desk_factory()
    activate(desk, "automatic")
    result = offer(desk)
    assert result["state"] == "submitted" and result["authorized_by"] == "automatic"
    assert desk.engine.orders()[0]["state"] == "ACCEPTED"
    assert offer(desk)["id"] == result["id"] and len(desk.engine.orders()) == 1


def test_ordered_kite_updates_keep_approval_active_but_true_staleness_cancels_and_records_cause(
    desk_factory,
):
    desk, _, _ = desk_factory(horizon="long_term")
    e = desk.engine
    first = quote(1).model_copy(update={"source": "kite"})
    assert e.ingest(first, first.received_time)
    activate(desk, now=first.received_time)
    record = desk.offer(
        candidate("daily", now=first.received_time),
        first.received_time,
        {"kind": "daily", "signal_key": "daily-entry"},
    )
    for second in range(2, 9):
        current = quote(second).model_copy(update={"source": "kite"})
        assert e.ingest(current, current.received_time)
        tied = current.model_copy(
            update={
                "received_time": current.received_time + timedelta(milliseconds=200),
                "ask_size": 101,
            }
        )
        assert e.ingest(tied, tied.received_time)
        desk.tick(tied.received_time)
        assert desk.mode == "approval"
    stopped = NOW + timedelta(seconds=14)
    desk.tick(stopped)
    assert desk.mode == "manual"
    cancelled = desk.view(stopped)["decisions"][0]
    assert cancelled["id"] == record["id"] and cancelled["state"] == "cancelled"
    assert cancelled["pause_reasons"] == ["NO_FRESH_EXECUTION_QUOTES"]
    with e.db.transaction() as tx:
        pause = json.loads(
            tx.execute(
                "SELECT payload FROM events WHERE kind='desk_pause' ORDER BY seq DESC LIMIT 1"
            ).fetchone()[0]
        )
        assert pause["causes"] == ["NO_FRESH_EXECUTION_QUOTES"]
    restored = quote(15).model_copy(update={"source": "kite"})
    e.ingest(restored, restored.received_time)
    activate(desk, "automatic", restored.received_time)
    same = desk.offer(
        candidate("daily", now=restored.received_time),
        restored.received_time,
        {"kind": "daily", "signal_key": "daily-entry"},
    )
    assert same["id"] == record["id"] and same["state"] == "cancelled"
    summary = desk.view(restored.received_time)["daily_signal_summary"]
    assert summary["states"] == {"cancelled": 1}
    assert "does not replay" in summary["message"]
    assert not e.orders()
    assert D(e.snapshot(restored.received_time)["cash"]) == D("25000")
    with e.db.transaction() as tx:
        Database.reconcile(tx)


@pytest.mark.parametrize(
    "failure,cause", [("fault", "ACCOUNT_FAULTED"), ("disconnect", "FEED_DISCONNECTED")]
)
def test_hard_watchdog_failure_revokes_mode_without_reading_a_snapshot(
    desk_factory, monkeypatch, failure, cause
):
    desk, _, _ = desk_factory()
    activate(desk)
    offer(desk)
    if failure == "fault":
        desk.engine.faulted = True
    else:
        desk.engine.set_connected(False)

    def broken_snapshot(now):
        raise AssertionError("Snapshot must not precede hard-failure authority revocation")

    monkeypatch.setattr(desk.engine, "snapshot", broken_snapshot)
    desk.tick(NOW)
    assert desk.mode == "manual"
    with desk.engine.db.transaction() as tx:
        payload = json.loads(tx.execute("SELECT payload FROM desk_decisions").fetchone()[0])
        assert payload["state"] == "cancelled" and payload["pause_reasons"] == [cause]


@pytest.mark.parametrize("change", ["expired", "drift", "stale", "mode", "review_hash", "risk"])
def test_old_or_changed_proposals_cannot_authorize_orders(desk_factory, change):
    desk, _, _ = desk_factory()
    activate(desk)
    record = offer(desk)
    preview = desk.preview(record["id"], NOW)
    now = NOW
    if change == "expired":
        now += timedelta(seconds=121)
    elif change == "drift":
        now += timedelta(seconds=1)
        desk.engine.ingest(quote(1, ask="505", bid="504.95"), now)
    elif change == "stale":
        now += timedelta(seconds=6)
    elif change == "mode":
        desk.set_mode("manual", NOW, desk.revision)
    elif change == "risk":
        desk.engine.kill(NOW)
    if change == "mode":
        assert desk.approve(record["id"], preview["preview_sha256"], now)["state"] == "cancelled"
    else:
        with pytest.raises(DeskError):
            desk.approve(
                record["id"],
                "0" * 64 if change == "review_hash" else preview["preview_sha256"],
                now,
            )
    assert not desk.engine.orders()


def test_mode_switch_and_feed_loss_cancel_pending_buys_without_selling_holding(desk_factory):
    desk, _, _ = desk_factory()
    activate(desk, "automatic")
    offer(desk)
    desk.set_mode("manual", NOW, desk.revision)
    assert desk.engine.orders()[0]["state"] == "CANCELLED"
    assert not desk.engine.snapshot(NOW)["positions"]
    activate(desk, "approval")
    desk.engine.set_connected(False)
    desk.tick(NOW)
    assert desk.mode == "manual"
    desk.engine.set_connected(True)
    desk.engine.ingest(quote(1), NOW + timedelta(seconds=1))
    assert desk.mode == "manual"


def test_declined_expired_and_restart_authority_never_replay(desk_factory, monkeypatch):
    desk, _, _ = desk_factory()
    activate(desk)
    record = offer(desk)
    assert desk.reject(record["id"], NOW)["outcome"] == "OPERATOR_DECLINED"
    assert offer(desk)["state"] == "rejected"
    # Independent proposal, interrupted between durable authorization and broker submit.
    record = desk.offer(
        candidate("second"),
        NOW,
        {"kind": "intraday", "signal_key": "second", "candle": {"close": "500"}},
    )
    preview = desk.preview(record["id"], NOW)
    monkeypatch.setattr(
        desk.engine,
        "submit",
        lambda *a, **k: (_ for _ in ()).throw(RuntimeError("injected interruption")),
    )
    with pytest.raises(RuntimeError):
        desk.approve(record["id"], preview["preview_sha256"], NOW)
    recovered = TradingDesk(desk.engine, NOW, synthetic=True)
    assert recovered.mode == "manual" and not desk.engine.orders()
    assert all(r["state"] != "authorized" for r in recovered.view(NOW)["decisions"])


def test_decision_journal_corruption_is_detected(desk_factory):
    desk, _, _ = desk_factory()
    activate(desk)
    record = offer(desk)
    with desk.engine.db.transaction() as tx:
        changed = dict(record)
        changed["state"] = "submitted"
        tx.execute(
            "UPDATE desk_decisions SET payload=? WHERE id=?", (json.dumps(changed), record["id"])
        )
        with pytest.raises(RuntimeError, match="decision"):
            Database.reconcile(tx)


def test_daily_worker_generates_long_term_proposals_and_auto_orders(desk_factory):
    desk, _, _ = desk_factory(horizon="long_term")
    activate(desk, "approval")
    worker = AnalysisWorker(desk, None, lambda: NOW)
    worker.evaluate(NOW)
    records = desk.view(NOW)["decisions"]
    assert len(records) == 1 and records[0]["context"]["kind"] == "daily"
    assert not desk.engine.orders()
    review = desk.preview(records[0]["id"], NOW)
    assert review["review"]["allowed"]
    result = desk.approve(records[0]["id"], review["preview_sha256"], NOW)
    assert result["state"] == "submitted"
    worker.evaluate(NOW)
    assert len(desk.engine.orders()) == 1


def test_missing_validated_model_and_synthetic_real_connection_fail_closed(desk_factory):
    desk, profile, _ = desk_factory(mode="rules_ml")
    assert desk.problem == "ANALYSIS_PROFILE_INVALID_OR_UNAVAILABLE"
    with pytest.raises(DeskError):
        activate(desk, "automatic")
    desk, profile, _ = desk_factory()
    connected = TradingDesk(desk.engine, NOW, profile=profile)
    assert connected.research is None and connected.problem


def test_intraday_worker_uses_completed_rules_and_auto_submits(desk_factory, monkeypatch):
    from unittest.mock import Mock

    from trading_agent.paper.demo import SIGNAL, demo_quote, signal_candle, warmup

    desk, _, _ = desk_factory()
    desk.engine.ingest(demo_quote(SIGNAL, bid="501", volume=33000), SIGNAL)
    activate(desk, "automatic", SIGNAL)
    setup = Mock()
    setup.broker.return_value.get_historical_candles.return_value = warmup() + [signal_candle()]
    worker = AnalysisWorker(desk, setup, lambda: SIGNAL)
    waits = []
    monkeypatch.setattr(worker.stop, "wait", lambda delay: waits.append(delay) or False)
    worker.evaluate(SIGNAL)
    records = desk.view(SIGNAL)["decisions"]
    assert len(records) == 1 and records[0]["state"] == "submitted"
    assert records[0]["context"]["kind"] == "intraday"
    assert records[0]["candidate"]["reason"].startswith("opening_range_breakout")
    assert desk.engine.orders()[0]["state"] == "ACCEPTED"
    assert waits == [0.4]
    worker.evaluate(SIGNAL)
    assert len(desk.engine.orders()) == 1


def test_sell_approval_and_protective_exit_never_wait_for_discretionary_approval(desk_factory):
    desk, _, _ = desk_factory(horizon="long_term")
    e = desk.engine
    activate(desk, "automatic")
    AnalysisWorker(desk, None, lambda: NOW).evaluate(NOW)
    e.ingest(quote(1), NOW + timedelta(seconds=1))
    assert e.snapshot(NOW + timedelta(seconds=1))["positions"]
    activate(desk, "approval", NOW + timedelta(seconds=1))
    with e.db.transaction() as tx:
        holding = dict(tx.execute("SELECT * FROM positions").fetchone())
    record = desk.offer(
        None,
        NOW + timedelta(seconds=1),
        {"kind": "daily", "holding": holding, "reason": "DAILY_SCREEN_EXIT"},
        symbol="NSE:DEMO",
        side="SELL",
    )
    review = desk.preview(record["id"], NOW + timedelta(seconds=1))
    assert review["review"]["allowed"]
    # A protective stop queues its own exit without approving this discretionary sale.
    e.ingest(quote(2, bid="480", ask="480.05"), NOW + timedelta(seconds=2))
    assert any(o["side"] == "SELL" and o["reason"] == "STOP" for o in e.orders())
    with pytest.raises(DeskError):
        desk.approve(record["id"], review["preview_sha256"], NOW + timedelta(seconds=2))
    e.ingest(quote(3, bid="480", ask="480.05"), NOW + timedelta(seconds=3))
    assert not e.snapshot(NOW + timedelta(seconds=3))["positions"]
    with e.db.transaction() as tx:
        Database.reconcile(tx)


def test_discretionary_sell_requires_approval_and_links_reason_atomically(desk_factory):
    desk, _, _ = desk_factory(horizon="long_term")
    e = desk.engine
    activate(desk, "automatic")
    AnalysisWorker(desk, None, lambda: NOW).evaluate(NOW)
    e.ingest(quote(1), NOW + timedelta(seconds=1))
    activate(desk, "approval", NOW + timedelta(seconds=1))
    with e.db.transaction() as tx:
        holding = dict(tx.execute("SELECT * FROM positions").fetchone())
    record = desk.offer(
        None,
        NOW + timedelta(seconds=1),
        {"kind": "daily", "holding": holding, "reason": "DAILY_SCREEN_EXIT"},
        symbol="NSE:DEMO",
        side="SELL",
    )
    assert not any(o["side"] == "SELL" for o in e.orders())
    review = desk.preview(record["id"], NOW + timedelta(seconds=1))
    result = desk.approve(record["id"], review["preview_sha256"], NOW + timedelta(seconds=1))
    assert result["outcome"] == "EXIT_QUEUED" and result["authorized_by"] == "operator"
    assert e.orders()[-1]["reason"] == "DAILY_SCREEN_EXIT"
    assert e.snapshot(NOW + timedelta(seconds=1))["positions"]
    e.ingest(quote(2), NOW + timedelta(seconds=2))
    assert not e.snapshot(NOW + timedelta(seconds=2))["positions"]
    with e.db.transaction() as tx:
        Database.reconcile(tx)


def test_recovery_links_committed_order_and_never_resubmits(desk_factory, monkeypatch):
    desk, _, _ = desk_factory()
    activate(desk)
    record = offer(desk)
    review = desk.preview(record["id"], NOW)
    original = desk._save

    def fail_final(tx, record, now):
        if record["state"] == "submitted":
            raise RuntimeError("interrupted linkage")
        original(tx, record, now)

    monkeypatch.setattr(desk, "_save", fail_final)
    with pytest.raises(RuntimeError):
        desk.approve(record["id"], review["preview_sha256"], NOW)
    assert len(desk.engine.orders()) == 1
    recovered = TradingDesk(desk.engine, NOW, synthetic=True)
    assert recovered.view(NOW)["decisions"][0]["state"] == "submitted"
    assert len(desk.engine.orders()) == 1
    with desk.engine.db.transaction() as tx:
        Database.reconcile(tx)


def test_broker_authority_survives_missing_decision_journal_detection(desk_factory):
    desk, _, _ = desk_factory()
    activate(desk, "automatic")
    offer(desk)
    with desk.engine.db.transaction() as tx:
        tx.execute("DELETE FROM desk_decisions")
        tx.execute("DELETE FROM events WHERE kind='desk_decision'")
        with pytest.raises(RuntimeError, match="authorization"):
            Database.reconcile(tx)


def test_quantity_cannot_grow_beyond_approval_when_price_falls(desk_factory):
    desk, _, _ = desk_factory()
    activate(desk)
    record = offer(desk)
    review = desk.preview(record["id"], NOW)
    e = desk.engine
    now = NOW + timedelta(seconds=1)
    e.ingest(quote(1, bid="498.95", ask="499.00"), now)
    result = desk.approve(record["id"], review["preview_sha256"], now)
    order = e.orders()[0]
    assert result["state"] == "submitted"
    assert order["quantity"] <= review["review"]["maximum_quantity"]
    assert D(order["reserved_cash"]) <= D(review["review"]["maximum_cash"])
    assert D(order["reserved_risk"]) <= D(review["review"]["maximum_risk"])


def test_slow_history_does_not_hold_risk_lock_or_trade_after_pause(desk_factory, monkeypatch):
    import threading
    from unittest.mock import Mock

    from trading_agent.paper.demo import SIGNAL, demo_quote, signal_candle, warmup

    desk, _, _ = desk_factory()
    e = desk.engine
    e.ingest(demo_quote(SIGNAL, bid="501", volume=33000), SIGNAL)
    activate(desk, "automatic", SIGNAL)
    entered, release, controlled = threading.Event(), threading.Event(), threading.Event()
    setup = Mock()

    def history(*args):
        entered.set()
        if not release.wait(3):
            raise RuntimeError("history test timeout")
        return warmup() + [signal_candle()]

    setup.broker.return_value.get_historical_candles.side_effect = history
    worker = AnalysisWorker(desk, setup, lambda: SIGNAL)
    monkeypatch.setattr(worker.stop, "wait", lambda delay: False)
    thread = threading.Thread(target=worker.evaluate, args=(SIGNAL,))
    thread.start()
    try:
        assert entered.wait(2)

        def pause():
            desk.pause(SIGNAL, "OPERATOR_TEST_PAUSE")
            e.kill(SIGNAL)
            controlled.set()

        control = threading.Thread(target=pause)
        control.start()
        assert controlled.wait(2), "history held the protective control lock"
        control.join(2)
    finally:
        release.set()
        thread.join(3)
    assert not thread.is_alive() and not e.orders() and desk.mode == "manual"


def test_ml_threshold_and_context_are_rechecked_before_paper_submission(desk_factory):
    from types import SimpleNamespace
    from unittest.mock import Mock

    desk, _, _ = desk_factory(horizon="long_term")
    activate(desk, "approval")
    model = Mock()
    model.version = "test-model-hash"
    model.artifact = SimpleNamespace(
        available_after=NOW - timedelta(days=2),
        validated_through=NOW - timedelta(days=1),
        threshold=0.8,
    )
    model.score.return_value = 0.2
    desk.research.model = model
    worker = AnalysisWorker(desk, None, lambda: NOW)
    worker.evaluate(NOW)
    record = desk.view(NOW)["decisions"][0]
    review = desk.preview(record["id"], NOW)
    assert "MODEL_BELOW_THRESHOLD" in review["review"]["reasons"] and not desk.engine.orders()
    model.score.return_value = 0.9
    review = desk.preview(record["id"], NOW)
    assert review["review"]["allowed"] and review["review"]["model_score"] == 0.9
    model.score.return_value = 0.1
    with pytest.raises(DeskError, match="MODEL_BELOW_THRESHOLD"):
        desk.approve(record["id"], review["preview_sha256"], NOW)
    assert not desk.engine.orders()


def test_existing_intraday_controller_can_queue_approvals_and_disarm_invalidates_them(
    paper_factory,
):
    from trading_agent.paper.demo import SIGNAL, WARM, demo_quote, signal_candle, warmup

    feed = paper_factory()
    feed.connection(True, WARM)
    feed.on_quote(demo_quote(WARM), WARM)
    feed.on_candles(warmup(), WARM)
    desk = TradingDesk(feed.engine, WARM, automation=feed)
    activate(desk, "approval", WARM)
    for seconds in range(4, 300, 4):
        feed.on_quote(
            demo_quote(WARM + timedelta(seconds=seconds), volume=28000 + seconds),
            WARM + timedelta(seconds=seconds),
        )
    feed.on_quote(demo_quote(SIGNAL, bid="501", volume=33000), SIGNAL)
    feed.on_candles([signal_candle()], SIGNAL)
    record = desk.view(SIGNAL)["decisions"][0]
    assert record["state"] == "awaiting_approval" and not feed.engine.orders()
    review = desk.preview(record["id"], SIGNAL)
    assert review["review"]["allowed"]
    feed.disarm(SIGNAL, "TEST_DISARM")
    with pytest.raises(DeskError, match="AUTOMATION_NOT_READY"):
        desk.approve(record["id"], review["preview_sha256"], SIGNAL)
    desk.tick(SIGNAL)
    assert desk.mode == "manual" and not feed.engine.orders()


def test_changed_daily_inputs_pause_analysis_without_replacing_evidence(desk_factory):
    desk, _, directory = desk_factory()
    activate(desk, "automatic")
    worker = AnalysisWorker(desk, None, lambda: NOW)
    path = directory / "daily.jsonl"
    lines = path.read_text().splitlines()
    row = json.loads(lines[0])
    row["volume"] += 1
    lines[0] = json.dumps(row)
    path.write_text("\n".join(lines) + "\n")
    with pytest.raises(RuntimeError, match="changed"):
        worker.evaluate(NOW)
    assert not desk.engine.orders()


def test_all_quotes_stale_pauses_without_silent_resume(desk_factory):
    desk, _, _ = desk_factory()
    activate(desk, "automatic")
    offer(desk)
    desk.tick(NOW + timedelta(seconds=6))
    assert desk.mode == "manual" and desk.engine.orders()[0]["state"] == "CANCELLED"
    desk.engine.ingest(quote(7), NOW + timedelta(seconds=7))
    assert desk.mode == "manual"


def test_pause_revokes_memory_authority_even_if_journal_write_fails(desk_factory, monkeypatch):
    desk, _, _ = desk_factory()
    activate(desk)
    record = offer(desk)
    review = desk.preview(record["id"], NOW)
    with monkeypatch.context() as patch:

        def fail(*args, **kwargs):
            raise RuntimeError("injected I/O failure")

        patch.setattr(desk.engine.db, "event", fail)
        with pytest.raises(RuntimeError):
            desk.pause(NOW, "FAULT_TEST")
    assert desk.mode == "manual"
    with pytest.raises(DeskError):
        desk.approve(record["id"], review["preview_sha256"], NOW)
    assert not desk.engine.orders()


def test_slow_durable_authorization_cannot_submit_with_old_quote_time(desk_factory):
    desk, _, _ = desk_factory()
    activate(desk)
    record = offer(desk)
    review = desk.preview(record["id"], NOW)
    desk.clock = lambda: NOW + timedelta(seconds=6)
    result = desk.approve(record["id"], review["preview_sha256"], NOW)
    assert (
        result["state"] == "expired" and result["outcome"] == "AUTHORIZATION_DELAY_OR_CLOCK_CHANGED"
    )
    assert not desk.engine.orders()
    with desk.engine.db.transaction() as tx:
        Database.reconcile(tx)
