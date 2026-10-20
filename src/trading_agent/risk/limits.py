"""Pure sizing. Caller must hold the account transaction while reserving resources."""

from decimal import Decimal

from trading_agent.execution.costs import Charges
from trading_agent.models import RiskDecision


def size(
    *,
    price: Decimal,
    stop_fill: Decimal,
    cash: Decimal,
    exposure_room: Decimal,
    position_cap: Decimal,
    risk_budget: Decimal,
    target_fill: Decimal,
    charges: Charges,
) -> RiskDecision:
    if not 0 < stop_fill < price < target_fill:
        return RiskDecision(allowed=False, reasons=("INVALID_STOP_OR_TARGET",))
    upper = int(
        min(
            cash / price,
            exposure_room / price,
            position_cap / price,
            risk_budget / (price - stop_fill),
        )
    )
    # Binary search is bounded by log2(quantity), including fees and stop slippage.
    lo, hi = 0, max(0, upper)
    while lo < hi:
        qty = (lo + hi + 1) // 2
        cost = price * qty + charges.fee("BUY", price * qty)
        risk = (price - stop_fill) * qty + charges.round_trip(price, stop_fill, qty)
        if cost <= cash and risk <= risk_budget:
            lo = qty
        else:
            hi = qty - 1
    if lo == 0:
        return RiskDecision(allowed=False, reasons=("ZERO_QUANTITY",))
    fees = charges.round_trip(price, target_fill, lo)
    if (target_fill - price) * lo <= fees:
        return RiskDecision(allowed=False, reasons=("COSTS_EXCEED_REWARD",))
    return RiskDecision(
        allowed=True,
        reasons=(),
        quantity=lo,
        price_cap=price,
        cash_reservation=price * lo + charges.fee("BUY", price * lo),
        risk_reservation=(price - stop_fill) * lo + charges.round_trip(price, stop_fill, lo),
    )
