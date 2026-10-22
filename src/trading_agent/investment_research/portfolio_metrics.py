"""Pure cash/held-share allocation; this is not liquidation equity or risk exposure.

Inputs are a read-only snapshot at one ledger/quote cut. ``quote.usable`` must be
the caller's already established acceptance/freshness decision, never merely the
presence of a saved bid. Known receivables and unknown fractional claims are
excluded consistently. Monetary arithmetic rejects precision loss; ratios use
34-digit Decimal precision, ROUND_HALF_EVEN, in an independent private context.
"""

import re
from decimal import ROUND_HALF_EVEN, Context, Decimal, Inexact, localcontext
from typing import Any

METHOD = "cash-and-held-share-accepted-bid-allocation-v1"
_CONTEXT = Context(prec=34, rounding=ROUND_HALF_EVEN)
_DECIMAL = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[Ee][+-]?[0-9]{1,3})?\Z")


def _money(value: object, label: str) -> Decimal:
    if not isinstance(value, str) or len(value) > 128 or not _DECIMAL.fullmatch(value):
        raise ValueError(f"{label} must be a bounded finite Decimal string")
    try:
        result = Decimal(value)
    except ArithmeticError as exc:
        raise ValueError(f"{label} must be a bounded finite Decimal string") from exc
    if not result.is_finite() or not -64 <= result.adjusted() <= 64:
        raise ValueError(f"{label} must be a bounded finite Decimal string")
    return result


def allocation_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    """Return current allocation without mutating or repairing the input snapshot.

    Required: ``cash`` and ``positions``; each held position requires a unique
    symbol, positive integer quantity and ``quote`` with a positive decimal bid
    and ``usable is True``. An explicit false ``basis_reviewed`` rejects a mark.
    A truncated position list, account fault or unusable held quote disables all
    current weights. Missing reservation/buffer/count evidence stays null rather
    than being invented as zero. Claims do not disable this *excluding-claims*
    allocation, and reservations are never subtracted from its denominator.
    """
    if not isinstance(snapshot, dict):
        raise ValueError("allocation requires a snapshot object")
    cash = _money(snapshot.get("cash"), "cash")
    positions = snapshot.get("positions")
    if not isinstance(positions, list) or len(positions) > 10_000:
        raise ValueError("positions must be a bounded list")
    long_term = snapshot.get("long_term", {})
    if not isinstance(long_term, dict):
        raise ValueError("long_term must be an object")
    receivable = _money(long_term.get("receivable", "0"), "dividend receivable")
    if receivable < 0:
        raise ValueError("dividend receivable cannot be negative")
    fractions = long_term.get("unvalued_fractional_claims", 0)
    if type(fractions) is not int or fractions < 0:
        raise ValueError("fractional claim count must be a nonnegative integer")
    commitments: dict[str, Any] = {}
    for name in ("reserved_cash", "delivery_fee_buffer"):
        amount = snapshot.get(name)
        if amount is not None:
            parsed = _money(amount, name)
            if parsed < 0:
                raise ValueError(f"{name} cannot be negative")
        commitments[name] = amount
    count = snapshot.get("pending_order_count")
    if count is not None and (type(count) is not int or count < 0):
        raise ValueError("pending_order_count must be a nonnegative integer")
    commitments["pending_order_count"] = count
    commitments["detail"] = (
        "Pending commitments constrain new purchases; they are not owned shares. "
        "Reserved cash and delivery buffers remain within actual cash and can overlap."
    )
    rows: list[dict[str, Any]] = []
    reasons: list[str] = []
    if snapshot.get("faulted") is True or snapshot.get("reconciled") is False:
        reasons.append("UNRECONCILED_LEDGER")
    if cash < 0 and "UNRECONCILED_LEDGER" not in reasons:
        reasons.append("UNRECONCILED_LEDGER")
    if snapshot.get("positions_truncated") is True or (
        "position_count" in snapshot and snapshot["position_count"] != len(positions)
    ):
        reasons.append("INCOMPLETE_POSITIONS")
    symbols: set[str] = set()
    total = Decimal(0)
    with localcontext(_CONTEXT) as ctx:
        for position in positions:
            if not isinstance(position, dict):
                raise ValueError("each held position must be an object")
            symbol = position.get("symbol")
            quantity = position.get("quantity")
            if not isinstance(symbol, str) or not symbol or len(symbol) > 100 or symbol in symbols:
                raise ValueError("held symbols must be bounded, unique strings")
            if type(quantity) is not int or not 0 < quantity <= 10**12:
                raise ValueError("held quantity must be a positive bounded integer")
            symbols.add(symbol)
            supplied_quote = position.get("quote")
            quote = supplied_quote if isinstance(supplied_quote, dict) else {}
            bid = quote.get("bid")
            value: Decimal | None = None
            reason: str | None = None
            if bid is None:
                reason = "MISSING_PRICE"
            else:
                mark = _money(bid, "accepted bid")
                if mark <= 0:
                    reason = "MISSING_PRICE"
                elif quote.get("basis_reviewed") is False:
                    reason = "PRICE_BASIS_UNREVIEWED"
                elif quote.get("usable") is not True:
                    reason = "STALE_PRICE"
                else:
                    # Money must remain exact. Only division for ratios may round.
                    ctx.traps[Inexact] = True
                    try:
                        value = mark * quantity
                        total += value
                    except Inexact as exc:
                        raise ValueError(
                            "allocation money exceeds 34-digit exact precision"
                        ) from exc
                    finally:
                        ctx.traps[Inexact] = False
            if reason and reason not in reasons:
                reasons.append(reason)
            rows.append(
                {
                    "symbol": symbol,
                    "quantity": quantity,
                    "gross_value": str(value) if value is not None else None,
                    "weight_pct": None,
                    "reason": reason,
                }
            )
        base: Decimal | None = None
        cash_weight: str | None = None
        if not reasons:
            ctx.traps[Inexact] = True
            try:
                base = cash + total
            except Inexact as exc:
                raise ValueError("allocation money exceeds 34-digit exact precision") from exc
            finally:
                ctx.traps[Inexact] = False
            if base <= 0:
                reasons.append("NONPOSITIVE_BASE")
            else:
                cash_weight = str(cash / base * 100)
                for row in rows:
                    row["weight_pct"] = str(Decimal(row["gross_value"]) / base * 100)
    return {
        "state": "unavailable" if reasons else "available",
        "reason": reasons[0] if reasons else None,
        "reason_codes": reasons,
        "method_id": METHOD,
        "decimal_precision": 34,
        "rounding": ROUND_HALF_EVEN,
        "basis": "Actual cash plus held whole shares at current accepted bid; claims excluded.",
        "cash_balance": snapshot["cash"],
        "gross_market_value": str(total)
        if not reasons or reasons == ["NONPOSITIVE_BASE"]
        else None,
        "allocation_base": str(base) if base is not None else None,
        "cash_weight_pct": cash_weight,
        "positions": rows,
        "excluded_claims": {
            "dividend_receivable": str(receivable),
            "unvalued_fractional_claims": fractions,
            "fractional_realizable_value": None if fractions else "0",
            "detail": (
                "Receivables and fractional claims are excluded from every allocation weight."
            ),
        },
        "commitments": commitments,
        "limitations": [
            "This allocation is not complete liquidation equity or executor risk exposure.",
            "No cost-basis fallback, pending sell proceeds or unfilled buy quantities are used.",
            "An available allocation does not authorize a purchase or change account policy.",
        ],
    }
