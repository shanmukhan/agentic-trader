import json
from datetime import timedelta
from decimal import Decimal as D

import pytest
from conftest import NOW, candidate, quote

from trading_agent.execution.delivery import HoldingReview
from trading_agent.execution.paper_broker import PaperBroker
from trading_agent.persistence.database import Database
from trading_agent.portfolio.contracts import (
    Approval,
    CancelPlan,
    Contribution,
    SIPPlan,
    occurrence_request,
)
from trading_agent.portfolio.service import cancel_plan, confirm, create_plan, preview, view


@pytest.fixture
def account(long_term_factory):
    e = long_term_factory()
    e.review_holding(
        HoldingReview(
            symbol="NSE:DEMO",
            session_date=NOW.date(),
            no_corporate_action=True,
            reference="invented clear basis",
        ),
        NOW,
    )
    e.ingest(quote(), NOW)
    return e


def request(id="contribution-1", **values):
    return Contribution(
        intent_id=id,
        symbol="NSE:DEMO",
        budget="2000",
        reference="invented reviewed purchase",
        **values,
    )


def approve(e, r, now=NOW):
    result = preview(e, r, now)
    assert result["decision"]["allowed"], result
    approval = Approval(request=r, preview_sha256=result["preview_sha256"])
    return confirm(e, approval, now), approval


def fill(e, second=1, **overrides):
    e.ingest(quote(second, **overrides), NOW + timedelta(seconds=second))


def plan(**changes):
    return SIPPlan.model_validate(
        {
            "plan_id": "monthly-test",
            "symbol": "NSE:DEMO",
            "budget": "1000",
            "sessions": [NOW.date(), (NOW + timedelta(days=1)).date()],
            "stop_pct": "2",
            "target_pct": "10",
            "reference": "invented reviewed monthly dates",
            **changes,
        }
    )


def reconcile(e):
    with e.db.transaction() as tx:
        e.db.reconcile(tx)


def test_budget_addition_preserves_protections_basis_identity_and_fees(account):
    e = account
    first, _ = approve(e, request(stop="490", target="600"))
    assert first["quantity"] == 3
    fill(e)
    before = e.snapshot(NOW + timedelta(seconds=1))
    added, approval = approve(e, request("addition"), NOW + timedelta(seconds=1))
    assert added["quantity"] == 3 and D(added["reserved_cash"]) <= D("2000")
    assert confirm(e, approval, NOW + timedelta(seconds=1)) == added
    assert e.snapshot(NOW + timedelta(seconds=1))["positions"][0]["quantity"] == 3
    fill(e, 2)
    after = e.snapshot(NOW + timedelta(seconds=2))
    assert after["positions"][0]["quantity"] == 6
    for key in ("stop", "target", "opened"):
        assert after["positions"][0][key] == before["positions"][0][key]
    assert D(after["positions"][0]["cost"]) == D("25000") - D(after["cash"])
    lots = view(e, NOW + timedelta(seconds=2))["lots"]
    assert len(lots) == 2
    assert sum(D(lot["original_cost"]) for lot in lots) == D(after["positions"][0]["cost"])
    reconcile(e)
    assert confirm(e, approval, NOW + timedelta(days=1))["filled"] == 3


@pytest.mark.parametrize("fault", ["price", "age", "kill", "pending", "holding", "hash"])
def test_stale_approval_never_creates_order_or_partial_metadata(account, fault):
    r = request(stop="490", target="600")
    result = preview(account, r, NOW)
    now = NOW
    if fault == "price":
        fill(account)
        now += timedelta(seconds=1)
    elif fault == "age":
        now += timedelta(seconds=6)
    elif fault == "kill":
        account.kill(now)
    elif fault in {"pending", "holding"}:
        account.submit(candidate(stop="490", target="600"), NOW)
        if fault == "holding":
            fill(account)
            now += timedelta(seconds=1)
    approval = Approval(
        request=r, preview_sha256="0" * 64 if fault == "hash" else result["preview_sha256"]
    )
    with pytest.raises(ValueError, match="preview"):
        confirm(account, approval, now)
    with account.db.transaction() as tx:
        assert not tx.execute("SELECT 1 FROM portfolio_requests").fetchone()
        assert not tx.execute("SELECT 1 FROM orders WHERE id=?", (r.intent_id,)).fetchone()
    reconcile(account)


def test_addition_cannot_change_protections_bypass_exit_or_standard_entry_guard(account):
    approve(account, request(stop="490", target="600"))
    fill(account)
    now = NOW + timedelta(seconds=1)
    blocked = preview(account, request("changed", stop="480", target="700"), now)
    assert "HOLDING_PROTECTIONS_CANNOT_CHANGE" in blocked["decision"]["reasons"]
    assert account.submit(candidate("normal", now=now), now)["state"] == "REJECTED"
    account.exit_holding("NSE:DEMO", now)
    assert (
        "HOLDING_EXIT_ALREADY_REQUESTED"
        in preview(account, request("exit-block"), now)["decision"]["reasons"]
    )


def test_position_room_is_aggregate_and_small_budget_never_creates_a_share(account):
    approve(account, request(stop="490", target="600"))
    fill(account)
    now = NOW + timedelta(seconds=1)
    large = request("large").model_copy(update={"budget": D("20000")})
    result = preview(account, large, now)
    cost = D(account.snapshot(now)["positions"][0]["cost"])
    assert (
        D(result["decision"]["cash_reservation"]) + cost <= account.settings.max_position_notional
    )
    small = preview(account, request("small").model_copy(update={"budget": D("1")}), now)
    assert small["decision"]["reasons"] == ["ZERO_QUANTITY"]


def test_partial_addition_cancel_and_restart_never_rebuys(account):
    approve(account, request(stop="490", target="600"))
    fill(account)
    order, approval = approve(account, request("partial"), NOW + timedelta(seconds=1))
    fill(account, 2, ask_size=1)
    assert account.orders()[-1]["state"] == "PARTIAL"
    db = account.db
    account.db.close()
    reopened = Database(db.path, account.settings.starting_cash)
    try:
        e = PaperBroker(
            reopened, account.settings, account.calendar, recovery_time=NOW + timedelta(seconds=3)
        )
        assert e.orders()[-1]["state"] == "CANCELLED"
        assert confirm(e, approval, NOW + timedelta(seconds=3))["filled"] == 1
        assert e.snapshot(NOW + timedelta(seconds=3))["positions"][0]["quantity"] == 4
        reconcile(e)
    finally:
        reopened.close()


@pytest.mark.parametrize("mutation", ["table", "event", "schema", "order", "missing"])
def test_approval_corruption_is_detected_independently(account, mutation):
    approve(account, request(stop="490", target="600"))
    fill(account)
    approve(account, request("addition"), NOW + timedelta(seconds=1))
    fill(account, 2)
    with account.db.transaction() as tx:
        if mutation == "table":
            row = json.loads(
                tx.execute("SELECT request FROM portfolio_requests WHERE id='addition'").fetchone()[
                    0
                ]
            )
            row["budget"] = "1"
            tx.execute(
                "UPDATE portfolio_requests SET request=? WHERE id='addition'", (json.dumps(row),)
            )
        elif mutation == "event":
            tx.execute(
                "DELETE FROM events WHERE kind='portfolio_contribution' AND entity='addition'"
            )
        elif mutation == "schema":
            tx.execute("DELETE FROM meta WHERE key='portfolio_schema'")
        elif mutation == "order":
            tx.execute("UPDATE orders SET cap='999' WHERE id='addition'")
        else:
            tx.execute("DELETE FROM events WHERE kind='portfolio_contribution'")
            tx.execute("DELETE FROM portfolio_requests")
            tx.execute("DELETE FROM meta WHERE key='portfolio_schema'")
    with pytest.raises(RuntimeError):
        reconcile(account)


def test_sip_dates_are_explicit_once_only_and_cancellation_releases_reservations(account):
    e = account
    p = plan()
    create_plan(e, p, NOW)
    assert create_plan(e, p, NOW)["plan"]["budget"] == "1000"
    due = view(e, NOW)["plans"][0]["occurrences"]
    assert [r["status"] for r in due] == ["DUE", "UPCOMING"]
    r = occurrence_request(p, NOW.date())
    order, approval = approve(e, r)
    assert order["quantity"] == 1
    assert confirm(e, approval, NOW)["id"] == order["id"]
    cancel_plan(e, CancelPlan(plan_id=p.plan_id, reference="operator cancelled"), NOW)
    assert e.orders()[0]["state"] == "CANCELLED"
    assert e.snapshot(NOW)["reserved_cash"] == "0"
    assert not preview(e, occurrence_request(p, (NOW + timedelta(days=1)).date()), NOW)["decision"][
        "allowed"
    ]
    assert confirm(e, approval, NOW)["state"] == "CANCELLED"
    reconcile(e)


def test_sip_missed_sessions_do_not_catch_up_or_mint_cash(account):
    p = plan()
    create_plan(account, p, NOW)
    tomorrow = NOW + timedelta(days=1)
    snapshot = view(account, tomorrow)
    assert snapshot["plans"][0]["occurrences"][0]["status"] == "MISSED"
    assert not preview(account, occurrence_request(p, NOW.date()), tomorrow)["decision"]["allowed"]
    assert D(account.snapshot(tomorrow)["cash"]) == D("25000.00")
    assert not account.orders()


def test_sip_calendar_identity_cannot_change_while_active(account):
    create_plan(account, plan(), NOW)
    from trading_agent.portfolio.service import validate_calendar

    account.calendar.sources[NOW.date()] = "different review"
    with account.db.transaction() as tx, pytest.raises(ValueError, match="session changed"):
        validate_calendar(tx, account)
    cancel_plan(
        account, CancelPlan(plan_id=plan().plan_id, reference="cancel before revision"), NOW
    )
    with account.db.transaction() as tx:
        validate_calendar(tx, account)


@pytest.mark.parametrize(
    "changes",
    [
        {"budget": "0"},
        {"budget": "NaN"},
        {"sessions": []},
        {"sessions": ["2026-10-21", "2026-10-20"]},
        {"sessions": ["2026-10-20", "2026-10-20"]},
        {"stop_pct": "100"},
    ],
)
def test_sip_contracts_fail_closed(changes):
    with pytest.raises(ValueError):
        plan(**changes)


def test_intraday_accounts_reject_all_portfolio_commands(engine):
    with pytest.raises(ValueError, match="long-term"):
        preview(engine, request(stop="490", target="600"), NOW)
    with pytest.raises(ValueError):
        create_plan(engine, plan(), NOW)


def test_contribution_approval_and_order_roll_back_as_one_transaction(account, monkeypatch):
    r = request(stop="490", target="600")
    p = preview(account, r, NOW)
    original = account.db.event

    def fail(tx, time, kind, entity, payload):
        original(tx, time, kind, entity, payload)
        if kind == "order_state":
            raise RuntimeError("injected after financial intent insertion")

    monkeypatch.setattr(account.db, "event", fail)
    with pytest.raises(RuntimeError, match="injected"):
        confirm(account, Approval(request=r, preview_sha256=p["preview_sha256"]), NOW)
    with account.db.transaction() as tx:
        assert not tx.execute("SELECT 1 FROM portfolio_requests").fetchone()
        assert not tx.execute("SELECT 1 FROM orders").fetchone()
        assert not tx.execute("SELECT 1 FROM meta WHERE key='portfolio_schema'").fetchone()
        account.db.reconcile(tx)
    assert account.faulted and not account.connected


def test_concurrent_confirmations_do_not_share_the_same_preview_capacity(account):
    from concurrent.futures import ThreadPoolExecutor

    requests = [request("concurrent-" + str(i), stop="490", target="600") for i in range(2)]
    approvals = [
        Approval(request=r, preview_sha256=preview(account, r, NOW)["preview_sha256"])
        for r in requests
    ]

    def run(approval):
        try:
            return confirm(account, approval, NOW)["state"]
        except ValueError:
            return "STALE_PREVIEW"

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(run, approvals)) == ["ACCEPTED", "STALE_PREVIEW"]
    reconcile(account)


def test_addition_after_split_partial_sale_and_dp_reconcile(corporate_account):
    from trading_agent.backtesting.report import ledger_results
    from trading_agent.corporate_actions.contracts import ActionBatch, digest
    from trading_agent.corporate_actions.service import apply_batch

    e = corporate_account
    now = NOW + timedelta(days=1)
    with e.db.transaction() as tx:
        quarantine = json.loads(e.db.get(tx, "lt_quarantine:NSE:DEMO"))
    batch = ActionBatch.model_validate(
        {
            "batch_id": "addition-split",
            "symbol": "NSE:DEMO",
            "quarantine_sha256": digest(quarantine),
            "reviewed_at": now,
            "reference": "invented complete review",
            "covers_all_actions": True,
            "actions": [
                {
                    "action_id": "split-lots",
                    "kind": "split",
                    "ex_date": now.date(),
                    "record_date": now.date(),
                    "credit_date": now.date(),
                    "announced_at": NOW,
                    "reference": "invented two for one",
                    "numerator": 2,
                    "denominator": 1,
                }
            ],
        }
    )
    apply_batch(e.db, e.settings, e.calendar, batch, now)
    e.review_holding(
        HoldingReview(
            symbol="NSE:DEMO",
            session_date=now.date(),
            no_corporate_action=True,
            reference="invented adjusted basis",
        ),
        now,
    )

    def tick(second, bid="250", depth=100):
        q = quote(second, bid=bid, ask=str(D(bid) + D(".1")), bid_size=depth).model_copy(
            update={
                "exchange_time": now + timedelta(seconds=second),
                "received_time": now + timedelta(seconds=second),
                "last": D(bid),
            }
        )
        e.ingest(q, q.received_time)

    tick(1)
    r = request("post-split").model_copy(update={"budget": D("400")})
    added, _ = approve(e, r, now + timedelta(seconds=1))
    assert added["quantity"] == 1
    tick(2)
    assert e.snapshot(now + timedelta(seconds=2))["positions"][0]["quantity"] == 29
    e.exit_holding("NSE:DEMO", now + timedelta(seconds=2))
    tick(3, bid="275", depth=10)
    tick(4, bid="275")
    final = e.snapshot(now + timedelta(seconds=4))
    trades, _ = ledger_results(e.db)
    assert not final["positions"]
    assert D(final["cash"]) == D(25000) + sum((t["net_pnl"] for t in trades), D(0))
    with e.db.transaction() as tx:
        assert (
            tx.execute("SELECT COUNT(*) FROM events WHERE kind='delivery_dp_charge'").fetchone()[0]
            == 1
        )
        e.db.reconcile(tx)


def test_portfolio_lifecycle_replays_identical_financial_authority(tmp_path):
    from trading_agent.backtesting.report import journal_digest
    from trading_agent.portfolio.demo import portfolio_demo

    results = []
    journals = []
    for name in ("first", "second"):
        directory = tmp_path / name
        results.append(portfolio_demo(directory))
        db = Database(directory / "paper.sqlite3", D(25000))
        try:
            with db.transaction() as tx:
                db.reconcile(tx)
            journals.append(journal_digest(db))
        finally:
            db.close()
    assert results[0] == results[1]
    assert journals[0] == journals[1]
