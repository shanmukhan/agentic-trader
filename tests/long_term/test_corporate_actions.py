import json
import sqlite3
from datetime import timedelta
from decimal import Decimal as D

import pytest
from conftest import NOW, quote

from trading_agent.backtesting.report import journal_digest, ledger_results
from trading_agent.corporate_actions.contracts import ActionBatch, CashReceipt, digest
from trading_agent.corporate_actions.service import apply_batch, record_receipt
from trading_agent.execution.delivery import HoldingReview
from trading_agent.execution.paper_broker import PaperBroker
from trading_agent.paper.long_term_report import long_term_report
from trading_agent.persistence.database import Database

WHEN = NOW + timedelta(days=1)


def batch_for(engine, actions=None, **changes):
    with engine.db.transaction() as tx:
        quarantine = json.loads(engine.db.get(tx, "lt_quarantine:NSE:DEMO"))
    action = {
        "action_id": "split-1",
        "kind": "split",
        "ex_date": "2026-10-21",
        "record_date": "2026-10-21",
        "credit_date": "2026-10-21",
        "announced_at": NOW.isoformat(),
        "reference": "invented exchange notice",
        "numerator": 2,
        "denominator": 1,
    }
    return ActionBatch.model_validate(
        {
            "batch_id": "batch-1",
            "symbol": "NSE:DEMO",
            "quarantine_sha256": digest(quarantine),
            "reviewed_at": WHEN.isoformat(),
            "reference": "all intervening invented actions reviewed",
            "covers_all_actions": True,
            "actions": actions or [action],
            **changes,
        }
    )


def apply(engine, batch=None, now=WHEN):
    return apply_batch(engine.db, engine.settings, engine.calendar, batch or batch_for(engine), now)


def clear_review(engine, now=WHEN):
    engine.review_holding(
        HoldingReview(
            symbol="NSE:DEMO",
            session_date=now.date(),
            no_corporate_action=True,
            reference="invented adjusted basis reviewed after batch",
        ),
        now,
    )


def dividend(action_id="div-1"):
    return {
        "action_id": action_id,
        "kind": "dividend",
        "ex_date": "2026-10-21",
        "record_date": "2026-10-21",
        "payment_date": "2026-10-22",
        "announced_at": NOW.isoformat(),
        "reference": "invented dividend and net deduction",
        "per_share": "10.00",
        "withholding": "14.00",
    }


def receipt(claim_id="div-1", amount="126.00", **changes):
    return CashReceipt.model_validate(
        {
            "payment_id": "receipt-1",
            "claim_id": claim_id,
            "paid_date": "2026-10-22",
            "net_amount": amount,
            "reviewed_at": (WHEN + timedelta(days=1)).isoformat(),
            "reference": "invented bank/registrar net receipt",
            **changes,
        }
    )


@pytest.mark.parametrize("kind,numerator,denominator", [("split", 2, 1), ("bonus", 1, 1)])
def test_share_actions_preserve_basis_adjust_ticks_and_require_new_review_and_quote(
    corporate_account, kind, numerator, denominator
):
    engine = corporate_account
    batch = batch_for(engine)
    action = {
        **batch.actions[0].model_dump(mode="json"),
        "kind": kind,
        "numerator": numerator,
        "denominator": denominator,
    }
    batch = batch_for(engine, [action])
    before = engine.snapshot(WHEN)
    result = apply(engine, batch)
    assert not result["idempotent"] and result["result"]["claims"] == []
    state = engine.snapshot(WHEN)
    assert state["positions"][0]["quantity"] == 28
    assert D(state["positions"][0]["cost"]) == D("7011.82")
    assert D(state["positions"][0]["stop"]) == 245
    assert D(state["positions"][0]["target"]) == 300
    assert state["positions"][0]["opened"] == before["positions"][0]["opened"]
    assert state["cash"] == before["cash"] and state["fees"] == before["fees"]
    assert not state["valuation_fresh"] and not state["long_term"]["quarantined_symbols"]
    assert not engine.ingest(quote(base=WHEN, bid="250", ask="250.05"), WHEN)
    clear_review(engine)
    assert not engine.ingest(quote(base=WHEN, bid="250", ask="250.05"), WHEN)
    assert engine.ingest(quote(1, base=WHEN, bid="250", ask="250.05"), WHEN + timedelta(seconds=1))
    assert engine.snapshot(WHEN + timedelta(seconds=1))["valuation_fresh"]
    with engine.db.transaction() as tx:
        engine.db.reconcile(tx)


def test_dividend_is_nonspendable_receivable_then_credited_once_and_never_a_deposit(
    corporate_account,
):
    engine = corporate_account
    batch = batch_for(engine, [dividend()])
    before = engine.snapshot(WHEN)
    apply(engine, batch)
    state = engine.snapshot(WHEN)
    assert D(state["long_term"]["receivable"]) == 126
    assert D(state["equity"]) > D(
        before["equity"]
    )  # Quote is invalidated, so this is only an estimate.
    assert state["cash"] == before["cash"] and state["available_cash"] == before["available_cash"]
    for key in ("quantity", "cost", "stop", "target", "opened"):
        assert state["positions"][0][key] == before["positions"][0][key]
    paid_at = WHEN + timedelta(days=1)
    result = record_receipt(engine.db, engine.settings, receipt(), paid_at)
    assert result["cash"] == "126" and result["income"] == "126" and result["capital_pnl"] == "0"
    after = engine.snapshot(paid_at)
    assert D(after["cash"]) == D(before["cash"]) + 126
    assert after["long_term"]["income_received"] == "126"
    assert D(after["long_term"]["receivable"]) == 0
    assert after["realized_pnl"] == before["realized_pnl"]
    mark = journal_digest(engine.db)
    assert record_receipt(engine.db, engine.settings, receipt(amount="126"), paid_at)["idempotent"]
    assert apply(engine, batch, now=paid_at)["idempotent"]
    assert journal_digest(engine.db) == mark
    with pytest.raises(ValueError, match="already been paid"):
        record_receipt(engine.db, engine.settings, receipt(payment_id="second-receipt"), paid_at)
    with pytest.raises(ValueError, match="different input"):
        record_receipt(engine.db, engine.settings, receipt(amount="127"), paid_at)
    with engine.db.transaction() as tx:
        engine.db.reconcile(tx)


def test_fraction_is_retained_with_basis_and_unknown_value_through_whole_share_exit(
    corporate_account, tmp_path
):
    engine = corporate_account
    action = batch_for(engine).actions[0].model_dump(mode="json")
    batch = batch_for(engine, [{**action, "kind": "bonus", "numerator": 1, "denominator": 3}])
    result = apply(engine, batch)
    claim = result["result"]["claims"][0]
    assert (claim["numerator"], claim["denominator"]) == (2, 3)
    assert claim["amount"] is None
    position = engine.snapshot(WHEN)["positions"][0]
    assert position["quantity"] == 18
    assert D(position["cost"]) + D(claim["basis"]) == D("7011.82")
    assert D(claim["basis"]) == D("250.42")  # (2/3) / (56/3), rounded down to paise
    clear_review(engine)
    engine.ingest(quote(1, base=WHEN, bid="375", ask="375.05"), WHEN + timedelta(seconds=1))
    state = engine.snapshot(WHEN + timedelta(seconds=1))
    assert not state["valuation_fresh"] and state["long_term"]["unvalued_fractional_claims"] == 1
    engine.exit_holding("NSE:DEMO", WHEN + timedelta(seconds=1))
    engine.ingest(quote(2, base=WHEN, bid="375", ask="375.05"), WHEN + timedelta(seconds=2))
    assert not engine.snapshot(WHEN + timedelta(seconds=2))["positions"]
    report = long_term_report(engine.db, tmp_path / "before-payment")
    assert report["unvalued_fractional_claims"] == 1
    trades, metrics = ledger_results(engine.db)
    assert metrics["completed_trades"] == 1 and trades[0]["corporate_share_delta"] == 4
    assert D(trades[0]["net_pnl"]) == D(report["realized_pnl"])
    paid_at = WHEN + timedelta(days=1)
    payment = receipt("split-1", "240.00")
    record_receipt(engine.db, engine.settings, payment, paid_at)
    after = long_term_report(engine.db, tmp_path / "after-payment")
    assert D(after["fraction_realized_pnl"]) == 240 - D(claim["basis"])
    assert D(after["realized_pnl"]) == D(report["realized_pnl"]) + D(after["fraction_realized_pnl"])
    assert after["unvalued_fractional_claims"] == 0 and D(after["income_received"]) == 0
    assert D(after["cash"]) == 25000 + D(after["realized_pnl"])


def test_same_date_bundle_sequence_freezes_dividend_after_reviewed_share_changes(corporate_account):
    engine = corporate_account
    split = batch_for(engine).actions[0].model_dump(mode="json")
    bonus = {**split, "action_id": "bonus-1", "kind": "bonus", "numerator": 1, "denominator": 2}
    div = {**dividend(), "per_share": "1", "withholding": "0"}
    result = apply(engine, batch_for(engine, [split, bonus, div]))
    assert result["result"]["after"]["quantity"] == 42
    assert result["result"]["claims"][0]["entitled_quantity"] == 42
    assert D(result["result"]["claims"][0]["amount"]) == 42


def test_cancelled_old_exit_retains_latch_and_requeues_adjusted_quantity_on_restart(
    corporate_account,
):
    engine = corporate_account
    old = engine.exit_holding("NSE:DEMO", WHEN)["order"]
    apply(engine)
    assert engine.orders()[-1]["state"] == "CANCELLED"
    assert engine.orders()[-1]["reason"] == "CORPORATE_ACTION_BASIS"
    dbpath, settings, calendar = engine.db.path, engine.settings, engine.calendar
    engine.db.close()
    db = Database(dbpath, settings.starting_cash)
    try:
        recovered = PaperBroker(db, settings, calendar, recovery_time=WHEN)
        recovered.poll(WHEN)
        new = recovered.orders()[-1]
        assert new["id"] != old["id"] and new["quantity"] == 28
        clear_review(recovered)
        recovered.set_connected(True)
        recovered.ingest(quote(1, base=WHEN, bid="250", ask="250.05"), WHEN + timedelta(seconds=1))
        assert not recovered.snapshot(WHEN + timedelta(seconds=1))["positions"]
        with db.transaction() as tx:
            db.reconcile(tx)
    finally:
        db.close()


@pytest.mark.parametrize(
    "mutation",
    [
        {"covers_all_actions": 1},
        {"covers_all_actions": False},
        {"unknown": True},
        {"quarantine_sha256": "invalid"},
        {"reviewed_at": "2026-10-21T10:00:00"},
    ],
)
def test_strict_batch_contract(corporate_account, mutation):
    payload = batch_for(corporate_account).model_dump(mode="json")
    with pytest.raises(ValueError):
        ActionBatch.model_validate({**payload, **mutation})


@pytest.mark.parametrize(
    "mutation",
    [
        {"quarantine_sha256": "0" * 64},
        {"reviewed_at": "2026-10-22T04:30:00Z"},
    ],
)
def test_failed_batch_preserves_quarantine_pending_orders_and_evidence(corporate_account, mutation):
    engine = corporate_account
    engine.exit_holding("NSE:DEMO", WHEN)
    batch = batch_for(engine, **mutation)
    before, orders = journal_digest(engine.db), engine.orders()
    with pytest.raises(ValueError):
        apply(engine, batch)
    assert before == journal_digest(engine.db) and engine.orders() == orders
    assert engine.snapshot(WHEN)["long_term"]["quarantined_symbols"] == ["NSE:DEMO"]


@pytest.mark.parametrize(
    "mutation",
    [
        {"credit_date": "2026-10-22"},
        {"denominator": True},
        {"numerator": 1},
        {"ex_date": "2026-10-22", "record_date": "2026-10-21"},
        {"announced_at": "2026-10-22T00:00:00Z"},
    ],
)
def test_invalid_or_future_share_actions_have_no_effect(corporate_account, mutation):
    engine = corporate_account
    before = journal_digest(engine.db)
    action = batch_for(engine).actions[0].model_dump(mode="json")
    with pytest.raises(ValueError):
        apply(engine, batch_for(engine, [{**action, **mutation}]))
    assert before == journal_digest(engine.db)


def test_atomic_rollback_after_position_and_claim_mutations(corporate_account, monkeypatch):
    engine = corporate_account
    old_event = engine.db.event
    before = journal_digest(engine.db)

    def fail(tx, time, kind, entity, payload):
        old_event(tx, time, kind, entity, payload)
        if kind == "corporate_action_batch":
            raise sqlite3.OperationalError("simulated write failure")

    monkeypatch.setattr(engine.db, "event", fail)
    with pytest.raises(sqlite3.OperationalError):
        apply(engine)
    assert journal_digest(engine.db) == before
    assert engine.snapshot(WHEN)["positions"][0]["quantity"] == 14
    with engine.db.transaction() as tx:
        assert not tx.execute("SELECT 1 FROM corporate_batches").fetchone()
        engine.db.reconcile(tx)


@pytest.mark.parametrize(
    "mutation",
    [
        "DELETE FROM meta WHERE key='corporate_actions_schema'",
        "DELETE FROM meta WHERE key='lt_receivable'",
        "UPDATE meta SET value='1' WHERE key='lt_receivable'",
        "DELETE FROM meta WHERE key GLOB 'lt_basis_after:*'",
        "UPDATE meta SET value='{}' WHERE key GLOB 'lt_claim:*'",
        "DELETE FROM corporate_batches",
        "DELETE FROM events WHERE kind='corporate_action_batch'",
        "UPDATE corporate_batches SET payload='{}'",
        "UPDATE meta SET value='1' WHERE key='lt_income_received'",
    ],
)
def test_action_account_corruption_is_detected(corporate_account, mutation):
    engine = corporate_account
    apply(engine, batch_for(engine, [dividend()]))
    with engine.db.transaction() as tx:
        tx.execute(mutation)
    with pytest.raises((RuntimeError, ValueError, KeyError)), engine.db.transaction() as tx:
        engine.db.reconcile(tx)


@pytest.mark.parametrize(
    "changes",
    [
        {"net_amount": "125"},
        {"paid_date": "2026-10-21"},
        {"paid_date": "2026-10-23"},
        {"reviewed_at": "2026-10-23T04:30:00Z"},
        {"claim_id": "unknown"},
    ],
)
def test_invalid_receipts_do_not_mint_cash(corporate_account, changes):
    engine = corporate_account
    apply(engine, batch_for(engine, [dividend()]))
    before = journal_digest(engine.db)
    with pytest.raises(ValueError):
        record_receipt(engine.db, engine.settings, receipt(**changes), WHEN + timedelta(days=1))
    assert journal_digest(engine.db) == before


def test_accepted_ex_date_price_prevents_retroactive_adjustment(long_term_factory):
    engine = long_term_factory()
    engine.calendar.sources = {day: "invented session" for day in engine.calendar.sessions}
    clear_review(engine)
    engine.ingest(quote(base=WHEN), WHEN)
    engine.review_holding(
        HoldingReview(
            symbol="NSE:DEMO",
            session_date=WHEN.date(),
            no_corporate_action=False,
            reference="action discovered after accepting ex-date raw price",
        ),
        WHEN,
    )
    before = journal_digest(engine.db)
    with pytest.raises(ValueError, match="accepted ex-date quote"):
        apply(engine)
    assert journal_digest(engine.db) == before


def test_changed_action_calendar_refused_before_recovery(corporate_account):
    engine = corporate_account
    apply(engine)
    engine.calendar.sources[WHEN.date()] = "changed source"
    with pytest.raises(ValueError, match="session definition changed"):
        PaperBroker(engine.db, engine.settings, engine.calendar, recovery_time=WHEN)


def test_receipt_failure_rolls_back_cash_claim_and_income(corporate_account, monkeypatch):
    engine = corporate_account
    apply(engine, batch_for(engine, [dividend()]))
    before = journal_digest(engine.db)
    original = engine.db.event

    def failed(tx, time, kind, entity, payload):
        original(tx, time, kind, entity, payload)
        if kind == "corporate_cash_receipt":
            raise sqlite3.OperationalError("simulated receipt disk failure")

    monkeypatch.setattr(engine.db, "event", failed)
    with pytest.raises(sqlite3.OperationalError):
        record_receipt(engine.db, engine.settings, receipt(), WHEN + timedelta(days=1))
    assert journal_digest(engine.db) == before
    with engine.db.transaction() as tx:
        assert not tx.execute("SELECT 1 FROM corporate_payments").fetchone()
        engine.db.reconcile(tx)


@pytest.mark.parametrize(
    "mutation",
    [
        "DELETE FROM corporate_payments",
        "DELETE FROM events WHERE kind='corporate_cash_receipt'",
        "UPDATE corporate_payments SET payload='{}'",
        "UPDATE corporate_payments SET request='{}'",
        "UPDATE meta SET value='0' WHERE key='cash'",
        "UPDATE positions SET stop='1'",
        "UPDATE positions SET opened='2026-10-20T00:00:00+00:00'",
    ],
)
def test_receipt_and_adjusted_protection_corruption_fails_closed(corporate_account, mutation):
    engine = corporate_account
    apply(engine, batch_for(engine, [dividend()]))
    record_receipt(engine.db, engine.settings, receipt(), WHEN + timedelta(days=1))
    with engine.db.transaction() as tx:
        tx.execute(mutation)
    with pytest.raises((RuntimeError, ValueError, KeyError)), engine.db.transaction() as tx:
        engine.db.reconcile(tx)


def test_requarantining_same_review_after_resolution_is_a_new_audited_event(corporate_account):
    engine = corporate_account
    with engine.db.transaction() as tx:
        original_review = HoldingReview.model_validate_json(
            engine.db.get(tx, "lt_quarantine:NSE:DEMO")
        )
    apply(engine)
    engine.review_holding(original_review, WHEN)
    with engine.db.transaction() as tx:
        assert engine.db.get(tx, "lt_quarantine:NSE:DEMO")
        engine.db.reconcile(tx)


def test_fraction_followed_by_another_action_is_refused_atomically(corporate_account):
    engine = corporate_account
    action = batch_for(engine).actions[0].model_dump(mode="json")
    fraction = {**action, "kind": "bonus", "numerator": 1, "denominator": 3}
    before = journal_digest(engine.db)
    with pytest.raises(ValueError, match="final action"):
        apply(engine, batch_for(engine, [fraction, dividend()]))
    assert journal_digest(engine.db) == before


def test_dividend_entitlement_survives_sale_before_cash_receipt(corporate_account):
    engine = corporate_account
    apply(engine, batch_for(engine, [dividend()]))
    clear_review(engine)
    engine.ingest(quote(1, base=WHEN), WHEN + timedelta(seconds=1))
    engine.exit_holding("NSE:DEMO", WHEN + timedelta(seconds=1))
    engine.ingest(quote(2, base=WHEN), WHEN + timedelta(seconds=2))
    before = engine.snapshot(WHEN + timedelta(seconds=2))
    assert not before["positions"] and D(before["long_term"]["receivable"]) == 126
    record_receipt(engine.db, engine.settings, receipt(), WHEN + timedelta(days=1))
    assert D(engine.snapshot(WHEN + timedelta(days=1))["cash"]) == D(before["cash"]) + 126


def test_fully_withheld_dividend_can_be_reconciled_with_explicit_zero_receipt(corporate_account):
    engine = corporate_account
    apply(engine, batch_for(engine, [{**dividend(), "withholding": "140"}]))
    before = engine.snapshot(WHEN)["cash"]
    record_receipt(engine.db, engine.settings, receipt(amount="0"), WHEN + timedelta(days=1))
    assert engine.snapshot(WHEN + timedelta(days=1))["cash"] == before


def test_hot_snapshot_uses_constant_size_claim_caches(corporate_account):
    engine = corporate_account
    apply(engine, batch_for(engine, [dividend()]))
    queries = []
    engine.db.connection.set_trace_callback(queries.append)
    try:
        engine.snapshot(WHEN)
    finally:
        engine.db.connection.set_trace_callback(None)
    assert not any(
        "FROM events" in sql or "FROM fills" in sql or "FROM corporate_" in sql for sql in queries
    )
    assert any("lt_receivable" in sql for sql in queries)


def test_adjusted_account_backup_retains_independent_claim_and_receipt_evidence(
    corporate_account, tmp_path
):
    engine = corporate_account
    apply(engine, batch_for(engine, [dividend()]))
    record_receipt(engine.db, engine.settings, receipt(), WHEN + timedelta(days=1))
    backup = tmp_path / "adjusted-backup.sqlite3"
    engine.db.backup(backup)
    db = Database(backup, engine.settings.starting_cash)
    try:
        with db.transaction() as tx:
            db.reconcile(tx)
            assert db.get(tx, "lt_income_received") == "126"
            assert tx.execute("SELECT COUNT(*) FROM corporate_batches").fetchone()[0] == 1
    finally:
        db.close()


def test_direct_corporate_drill_finishes_cash_identity_and_hashes(tmp_path):
    import hashlib

    from trading_agent.corporate_actions.demo import corporate_actions_demo

    directory = tmp_path / "corporate-drill"
    result = corporate_actions_demo(directory)
    assert result["cash"] == "25029.42" and result["positions"] == 0
    assert D(result["cash"]) == 25000 + D(result["realized_pnl"]) + D(result["income_received"])
    manifest = json.loads((directory / "evidence/manifest.json").read_text())
    for name, expected in manifest["sha256"].items():
        assert hashlib.sha256((directory / "evidence" / name).read_bytes()).hexdigest() == expected
