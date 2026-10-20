import io
import json
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace

import pytest
from conftest import NOW, quote

from trading_agent.corporate_actions.contracts import ActionBatch, CashReceipt, digest
from trading_agent.daily_execution.dataset import ActionEvent, QuoteEvent, ReceiptEvent, ReviewEvent
from trading_agent.daily_execution.labels import Labels
from trading_agent.daily_execution.runtime import ResearchRuntime
from trading_agent.execution.delivery import HoldingReview


def batch(engine, kind):
    now = NOW + timedelta(days=1)
    with engine.db.transaction() as tx:
        quarantine = json.loads(engine.db.get(tx, "lt_quarantine:NSE:DEMO"))
    return ActionBatch.model_validate(
        {
            "batch_id": "daily-action",
            "symbol": "NSE:DEMO",
            "quarantine_sha256": digest(quarantine),
            "reviewed_at": now,
            "reference": "invented full review",
            "covers_all_actions": True,
            "actions": [
                {
                    "action_id": "daily-benefit",
                    "kind": kind,
                    "ex_date": now.date(),
                    "record_date": now.date(),
                    "announced_at": NOW,
                    "reference": "invented source",
                    **(
                        {"numerator": 2, "denominator": 1, "credit_date": now.date()}
                        if kind == "split"
                        else {
                            "per_share": "10",
                            "withholding": "14",
                            "payment_date": (now + timedelta(days=1)).date(),
                        }
                    ),
                }
            ],
        }
    )


def test_replay_uses_original_reviewed_dividend_deduction_and_actual_receipt(
    corporate_account, daily_strategy
):
    e = corporate_account
    runtime = ResearchRuntime(e, SimpleNamespace(bars={}), daily_strategy)
    now = NOW + timedelta(days=1)
    runtime.feed(ActionEvent(time=now, batch=batch(e, "dividend")))
    assert Decimal(e.snapshot(now)["long_term"]["receivable"]) == Decimal("126.00")
    cash = Decimal(e.snapshot(now)["cash"])
    paid = now + timedelta(days=1)
    receipt = CashReceipt(
        payment_id="paid",
        claim_id="daily-benefit",
        paid_date=paid.date(),
        net_amount="126.00",
        reviewed_at=paid,
        reference="invented bank receipt",
    )
    runtime.feed(ReceiptEvent(time=paid, receipt=receipt))
    assert Decimal(e.snapshot(paid)["cash"]) == cash + Decimal(126)
    with e.db.transaction() as tx:
        e.db.reconcile(tx)


def test_replay_split_conserves_basis_and_invalidates_quotes(corporate_account, daily_strategy):
    e = corporate_account
    runtime = ResearchRuntime(e, SimpleNamespace(bars={}), daily_strategy)
    now = NOW + timedelta(days=1)
    basis = e.snapshot(now)["positions"][0]["cost"]
    runtime.feed(ActionEvent(time=now, batch=batch(e, "split")))
    runtime.feed(
        ReviewEvent(
            time=now,
            review=HoldingReview(
                symbol="NSE:DEMO",
                session_date=now.date(),
                no_corporate_action=True,
                reference="invented post-split review",
            ),
        )
    )
    assert not e.snapshot(now)["valuation_fresh"]
    q = quote(1, bid="250", ask="250.05").model_copy(
        update={
            "exchange_time": now + timedelta(seconds=1),
            "received_time": now + timedelta(seconds=1),
            "last": Decimal(250),
        }
    )
    runtime.feed(QuoteEvent(time=q.received_time, quote=q))
    state = e.snapshot(q.received_time)
    assert state["positions"][0]["quantity"] == 28
    assert state["positions"][0]["cost"] == basis
    with e.db.transaction() as tx:
        e.db.reconcile(tx)


def test_account_specific_cash_event_censors_trial_before_transferring_deduction(
    corporate_account, daily_strategy, tmp_path
):
    # A genuine active holding is deliberately used; the action cannot silently apply
    # this account's total withholding to an independent counterfactual quantity.
    from trading_agent.daily_execution.labels import Trial

    e = corporate_account
    runtime = ResearchRuntime(e, SimpleNamespace(bars={}), daily_strategy)
    manager = Labels(runtime, tmp_path, io.StringIO(), io.StringIO())
    trial = Trial("a" * 64, runtime, SimpleNamespace(symbol="NSE:DEMO"), None, None, quote())
    manager.active.append(trial)
    finished = []
    manager.finish = lambda trial, now, reason: finished.append(reason)
    manager.feed(ActionEvent(time=NOW + timedelta(days=1), batch=batch(e, "dividend")))
    assert finished == ["ACCOUNT_SPECIFIC_CASH_ACTION"]
    assert Decimal(e.snapshot(NOW + timedelta(days=1))["long_term"]["receivable"]) == 0
    observer = ResearchRuntime(e, SimpleNamespace(bars={}), daily_strategy, observer=True)
    future = NOW + timedelta(days=2)
    invalid = CashReceipt(
        payment_id="bad",
        claim_id="unknown",
        paid_date=future.date(),
        net_amount="1.00",
        reviewed_at=future,
        reference="invented unavailable receipt",
    )
    with pytest.raises(ValueError, match="source action"):
        observer.feed(ReceiptEvent(time=NOW + timedelta(days=1), receipt=invalid))
