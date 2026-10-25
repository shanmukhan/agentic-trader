"""Generated financial invariants, checked by exhaustive quantity enumeration."""

from decimal import ROUND_CEILING, Decimal
from random import Random

import pytest

from trading_agent.execution.costs import Charges, delivery_charges
from trading_agent.risk.limits import size

D = Decimal


def independent_fee(charges, side, turnover):
    if turnover == 0:
        return D(0)
    brokerage = min(charges.brokerage_cap, turnover * charges.brokerage_rate)
    exchange = turnover * (charges.exchange_rate + charges.sebi_rate + charges.ipft_rate)
    taxes = turnover * (charges.stt_sell if side == "SELL" else charges.stt_buy + charges.stamp_buy)
    subtotal = (brokerage + exchange) * (1 + charges.gst) + taxes
    return subtotal.quantize(D(".01"), rounding=ROUND_CEILING) + (
        charges.dp_sell if side == "SELL" else D(0)
    )


@pytest.mark.parametrize("charges", [Charges(), delivery_charges()])
def test_generated_sizing_matches_exhaustive_exact_fee_oracle(charges):
    rng = Random(20261025)
    # Small bounded integer quantities make an independent exhaustive oracle cheap.
    # Include equal constraints, sub-paisa boundaries and fixed delivery exit fees.
    for case in range(400):
        price = D(rng.randrange(10, 1000001)) / 100
        stop = price * D(rng.randrange(50, 100)) / 100
        target = price * D(rng.randrange(101, 151)) / 100
        cap_qty = rng.randrange(1, 31)
        limit = None if case % 3 else rng.randrange(1, 31)
        budgets = [price * rng.randrange(0, 31) + D(rng.randrange(-1, 2)) / 100 for _ in range(3)]
        cash, exposure, cap = [max(D(0), amount) for amount in budgets]
        if case % 10 == 0:
            cash = exposure = cap = price * cap_qty
        risk = (price - stop) * rng.randrange(0, 31) + D(rng.randrange(0, 20))
        kwargs = dict(
            price=price,
            stop_fill=stop,
            target_fill=target,
            cash=cash,
            exposure_room=exposure,
            position_cap=cap,
            risk_budget=risk,
            quantity_limit=limit,
            charges=charges,
        )
        feasible = []
        for qty in range(1, 32):
            cost = price * qty + independent_fee(charges, "BUY", price * qty)
            loss = (price - stop) * qty + independent_fee(charges, "BUY", price * qty)
            loss += independent_fee(charges, "SELL", stop * qty)
            if (
                cost <= cash
                and price * qty <= min(exposure, cap)
                and loss <= risk
                and (limit is None or qty <= limit)
            ):
                feasible.append(qty)
        expected = max(feasible, default=0)
        reward_fees = independent_fee(charges, "BUY", price * expected) + independent_fee(
            charges, "SELL", target * expected
        )
        if expected and (target - price) * expected <= reward_fees:
            expected = 0
        result = size(**kwargs)
        assert result.allowed == bool(expected), (case, kwargs, result)
        assert result.quantity == expected
        if expected:
            assert result.cash_reservation == price * expected + independent_fee(
                charges, "BUY", price * expected
            )
            assert result.risk_reservation == (price - stop) * expected + independent_fee(
                charges, "BUY", price * expected
            ) + independent_fee(charges, "SELL", stop * expected)


@pytest.mark.parametrize("charges", [Charges(), delivery_charges()])
def test_one_share_fee_boundary_is_exact_and_never_rounds_up_authority(charges):
    price, stop, target = D("500"), D("490"), D("550")
    buy = independent_fee(charges, "BUY", price)
    loss = price - stop + buy + independent_fee(charges, "SELL", stop)
    kwargs = dict(
        price=price,
        stop_fill=stop,
        target_fill=target,
        cash=price + buy,
        exposure_room=price,
        position_cap=price,
        risk_budget=loss,
        charges=charges,
    )
    assert size(**kwargs).quantity == 1
    assert not size(**(kwargs | {"cash": price + buy - D(".01")})).allowed
    assert not size(**(kwargs | {"risk_budget": loss - D(".01")})).allowed
