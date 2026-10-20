from decimal import Decimal as D

import pytest

from trading_agent.execution.costs import Charges, down, up
from trading_agent.risk.limits import size


def test_independently_calculated_charges():
    charges = Charges()
    # ₹10k: brokerage=3, exchange=.307, SEBI=.01, IPFT=.00001,
    # GST=.5970618, buy stamp=.3 / sell STT=2.5; conservative paisa ceiling.
    assert charges.fee("BUY", D(10000)) == D("4.22")
    assert charges.fee("SELL", D(10000)) == D("6.42")
    assert charges.fee("BUY", D(0)) == 0
    assert charges.fee("BUY", D(1000000)) < D(500)


def test_tick_rounding():
    assert up(D("500.251"), D(".05")) == D("500.30")
    assert down(D("500.251"), D(".05")) == D("500.25")


@pytest.mark.parametrize("side,amount", [("SHORT", "10"), ("BUY", "-1"), ("BUY", "NaN")])
def test_invalid_fees(side, amount):
    with pytest.raises(ValueError):
        Charges().fee(side, D(amount))


def test_fee_inclusive_sizing_and_maximality():
    charges = Charges()
    result = size(
        price=D("500.25"),
        stop_fill=D("494.75"),
        cash=D(25000),
        exposure_room=D(20000),
        position_cap=D(10000),
        risk_budget=D("62.5"),
        target_fill=D("509.7"),
        charges=charges,
    )
    assert result.allowed and result.quantity == 10
    assert result.risk_reservation <= D("62.5")
    assert D("5.5") * 11 + charges.round_trip(D("500.25"), D("494.75"), 11) > D("62.5")


@pytest.mark.parametrize(
    "cash,room,budget,stop,target,reason",
    [
        ("0", "20000", "62.5", "495", "510", "ZERO_QUANTITY"),
        ("25000", "0", "62.5", "495", "510", "ZERO_QUANTITY"),
        ("25000", "20000", "0", "495", "510", "ZERO_QUANTITY"),
        ("25000", "20000", "62.5", "501", "510", "INVALID_STOP_OR_TARGET"),
        ("25000", "20000", "62.5", "495", "500.26", "COSTS_EXCEED_REWARD"),
    ],
)
def test_sizing_rejection(cash, room, budget, stop, target, reason):
    result = size(
        price=D("500.25"),
        stop_fill=D(stop),
        cash=D(cash),
        exposure_room=D(room),
        position_cap=D(10000),
        risk_budget=D(budget),
        target_fill=D(target),
        charges=Charges(),
    )
    assert not result.allowed and reason in result.reasons
