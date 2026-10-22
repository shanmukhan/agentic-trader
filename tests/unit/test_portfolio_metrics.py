"""Synthetic allocation arithmetic, independent of current operator accounts."""

from copy import deepcopy
from decimal import ROUND_DOWN, Decimal, Inexact, localcontext
from fractions import Fraction

import pytest

from trading_agent.investment_research.portfolio_metrics import allocation_snapshot


def position(symbol="NSE:EXAMPLE", quantity=4, bid="105", **quote):
    return {
        "symbol": symbol,
        "quantity": quantity,
        "cost": "402",
        "liquidation_value": "418",
        "unrealized_pnl": "16",
        "quote": {"bid": bid, "usable": True, "basis_reviewed": True, **quote},
    }


def test_partial_exit_reservation_and_charged_fees_are_not_counted_twice():
    # Independently reconstruct the fixed, invented-fee design example.
    buys, acquisition_fees = Decimal(6) * 100, Decimal(3)
    sale, sale_fees = Decimal(2) * 110, Decimal(2)
    cash = Decimal(1000) - buys - acquisition_fees + sale - sale_fees
    remaining_basis = (buys + acquisition_fees) * Decimal(4) / 6
    released_basis = buys + acquisition_fees - remaining_basis
    realized = sale - sale_fees - released_basis
    assert cash + remaining_basis == Decimal(1000) + realized == Decimal(1017)
    snapshot = {
        "cash": str(cash),
        "positions": [position()],
        "reserved_cash": "50",
        "delivery_fee_buffer": "10",
        "available_cash": "555",
        "fees": "5",
        "equity": "1033",
        "pending_order_count": 1,
    }
    before = deepcopy(snapshot)
    actual = allocation_snapshot(snapshot)
    assert actual["state"] == "available"
    assert actual["allocation_base"] == "1035"  # 615 actual cash + 420 gross bid value.
    assert actual["gross_market_value"] == "420"
    assert actual["cash_balance"] == "615"
    assert actual["commitments"]["reserved_cash"] == "50"
    assert actual["commitments"]["pending_order_count"] == 1
    assert actual["positions"][0]["gross_value"] == "420"
    independent_weight = Fraction(420, 1035) * 100
    expected = Decimal(independent_weight.numerator) / independent_weight.denominator
    assert abs(Decimal(actual["positions"][0]["weight_pct"]) - expected) < Decimal("1e-25")
    assert snapshot == before


def test_cash_and_positions_use_same_denominator_and_sum_to_one_hundred():
    result = allocation_snapshot(
        {"cash": "1", "positions": [position("A", 1, "1"), position("B", 1, "1")]}
    )
    with localcontext() as ctx:
        ctx.prec = 50
        total = Decimal(result["cash_weight_pct"]) + sum(
            (Decimal(row["weight_pct"]) for row in result["positions"]), Decimal(0)
        )
        assert abs(total - 100) <= Decimal("1e-31")


def test_no_holdings_all_cash_known_zero_and_missing_commitments():
    result = allocation_snapshot({"cash": "1000.00", "positions": []})
    assert result["state"] == "available"
    assert result["cash_balance"] == "1000.00"  # Preserve persisted exact string.
    assert result["cash_weight_pct"] == "100"
    assert result["gross_market_value"] == "0"
    assert result["commitments"]["reserved_cash"] is None
    assert result["commitments"]["pending_order_count"] is None


@pytest.mark.parametrize("cash", ["0", "-1"])
def test_nonpositive_base_never_publishes_cash_percentage(cash):
    actual = allocation_snapshot({"cash": cash, "positions": []})
    assert actual["state"] == "unavailable"
    assert actual["cash_weight_pct"] is None
    assert actual["reason"] == ("NONPOSITIVE_BASE" if cash == "0" else "UNRECONCILED_LEDGER")


def test_negative_cash_cannot_be_hidden_by_larger_stock_value():
    actual = allocation_snapshot({"cash": "-1", "positions": [position()]})
    assert actual["state"] == "unavailable"
    assert actual["allocation_base"] is None
    assert actual["positions"][0]["weight_pct"] is None


@pytest.mark.parametrize(
    ("quote", "reason"),
    [
        ({"usable": False}, "STALE_PRICE"),
        ({"usable": 1}, "STALE_PRICE"),
        ({"basis_reviewed": False}, "PRICE_BASIS_UNREVIEWED"),
        ({"bid": None}, "MISSING_PRICE"),
        ({"bid": "0"}, "MISSING_PRICE"),
        ({"bid": "-10"}, "MISSING_PRICE"),
    ],
)
def test_unaccepted_or_unreviewed_marks_disable_all_current_weights(quote, reason):
    actual = allocation_snapshot(
        {"cash": "100", "valuation_fresh": True, "positions": [position(**quote), position("B")]}
    )
    assert actual["state"] == "unavailable"
    assert reason in actual["reason_codes"]
    assert actual["allocation_base"] is None
    assert actual["gross_market_value"] is None
    assert actual["cash_balance"] == "100"
    assert all(row["weight_pct"] is None for row in actual["positions"])


def test_missing_quote_does_not_fall_back_to_cost_or_liquidation_estimate():
    held = position()
    del held["quote"]
    actual = allocation_snapshot({"cash": "598", "positions": [held]})
    assert actual["reason"] == "MISSING_PRICE"
    assert actual["positions"][0]["gross_value"] is None


def test_claims_excluded_consistently_even_when_legacy_equity_incomplete():
    snapshot = {
        "cash": "697",
        "positions": [position(quantity=1, bid="220")],
        "valuation_fresh": False,
        "long_term": {"receivable": "18.20", "unvalued_fractional_claims": 1},
        "equity": "933.20",
    }
    actual = allocation_snapshot(snapshot)
    assert actual["state"] == "available"
    assert actual["allocation_base"] == "917"
    assert actual["excluded_claims"] == {
        "dividend_receivable": "18.20",
        "unvalued_fractional_claims": 1,
        "fractional_realizable_value": None,
        "detail": "Receivables and fractional claims are excluded from every allocation weight.",
    }


@pytest.mark.parametrize(
    "extra",
    [
        {"faulted": True},
        {"reconciled": False},
        {"positions_truncated": True},
        {"position_count": 2},
    ],
)
def test_fault_or_partial_holdings_cannot_publish_complete_allocation(extra):
    actual = allocation_snapshot({"cash": "100", "positions": [position()], **extra})
    assert actual["state"] == "unavailable"
    assert actual["cash_weight_pct"] is None
    assert actual["positions"][0]["weight_pct"] is None


@pytest.mark.parametrize("value", [1.2, True, "NaN", "Infinity", " 10", "1_000", "1e999", ""])
def test_authoritative_cash_must_be_finite_bounded_decimal_string(value):
    with pytest.raises(ValueError):
        allocation_snapshot({"cash": value, "positions": []})


@pytest.mark.parametrize("quantity", [0, -1, True, 1.1, "4", 10**13])
def test_integer_whole_held_quantity_required(quantity):
    with pytest.raises(ValueError):
        allocation_snapshot({"cash": "1", "positions": [position(quantity=quantity)]})


def test_duplicate_symbols_and_negative_claims_or_reservations_rejected():
    invalid = [
        {"positions": [position(), position()]},
        {"long_term": {"receivable": "-1"}},
        {"long_term": {"unvalued_fractional_claims": True}},
        {"reserved_cash": "-1"},
        {"pending_order_count": -1},
    ]
    for changes in invalid:
        with pytest.raises(ValueError):
            allocation_snapshot({"cash": "100", "positions": [], **changes})


def test_ambient_precision_rounding_and_inexact_trap_do_not_change_result():
    snapshot = {"cash": "100", "positions": [position(quantity=7, bid="1.23")]}
    expected = allocation_snapshot(snapshot)
    with localcontext() as ctx:
        ctx.prec = 3
        ctx.rounding = ROUND_DOWN
        ctx.traps[Inexact] = True
        assert allocation_snapshot(snapshot) == expected
        assert ctx.prec == 3 and ctx.rounding == ROUND_DOWN and ctx.traps[Inexact]


def test_money_precision_loss_rejected_instead_of_publishing_rounded_holdings():
    with pytest.raises(ValueError, match="exact precision"):
        allocation_snapshot(
            {
                "cash": "1",
                "positions": [position(quantity=9, bid="1234567890123456789012345678901234.5")],
            }
        )
