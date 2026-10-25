"""Exit invariants deliberately permit gap-through stop prices."""

from decimal import Decimal as D

import pytest

from trading_agent.risk.limits import validate_exit


@pytest.mark.parametrize(
    "quantity,held", [(0, 3), (-1, 3), (4, 3), (1, 0), (True, 3), (1, True), (1.0, 3)]
)
def test_exit_rejects_invalid_or_unowned_quantity(quantity, held):
    with pytest.raises(RuntimeError, match="quantity"):
        validate_exit(quantity=quantity, held_quantity=held, price=D("1"))


@pytest.mark.parametrize("price", ["0", "-1", "NaN", "Infinity", "-Infinity"])
def test_exit_requires_finite_positive_execution_price(price):
    with pytest.raises(RuntimeError, match="positive price"):
        validate_exit(quantity=1, held_quantity=1, price=D(price))


def test_exit_has_no_stop_or_entry_price_gate():
    assert validate_exit(quantity=1, held_quantity=1, price=D("0.05")) is None
