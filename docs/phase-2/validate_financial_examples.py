"""Independently check design examples; no application imports, DB, network or writes.

Run from any directory with Python 3.13:
    python /path/to/repository/docs/phase-2/validate_financial_examples.py

The only read dependency is examples/financial-examples.json beside this script.
The invented fees and prices are fixture inputs, not the runtime fee policy.
This is reproducible design arithmetic, not persisted-account acceptance.
"""

import json
from datetime import datetime
from decimal import ROUND_FLOOR, ROUND_HALF_EVEN, Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from typing import Any

D = Decimal
FIXTURE_PATH = Path(__file__).resolve().parent / "examples" / "financial-examples.json"


class Checks:
    """Count actual comparisons rather than reporting a manually estimated total."""

    def __init__(self) -> None:
        self.count = 0

    def equal(self, label: str, actual: Any, expected: Any) -> None:
        self.count += 1
        if actual != expected:
            raise AssertionError(f"{label}: calculated {actual!r}; expected {expected!r}")

    def money(self, label: str, actual: Decimal, expected: str) -> None:
        self.equal(label, actual, D(expected))


def filled_ledger(case: dict[str, Any]) -> tuple[Decimal, Decimal, int, Decimal, Decimal]:
    """Derive cash/basis from invented fills without reading expected output fields."""
    cash, basis, qty, realized, fees = D(case["seed"]), D(0), 0, D(0), D(0)
    for fill in case["fills"]:
        amount, price, fee = fill["quantity"], D(fill["price"]), D(fill["fee"])
        fees += fee
        if fill["side"] == "BUY":
            cash -= amount * price + fee
            basis += amount * price + fee
            qty += amount
        elif fill["side"] == "SELL":
            if not 0 < amount <= qty:
                raise ValueError("Synthetic sell exceeds its prior filled holding")
            released = basis if amount == qty else basis * amount / qty
            basis -= released
            qty -= amount
            cash += amount * price - fee
            realized += amount * price - fee - released
        else:
            raise ValueError("Unknown synthetic side")
    return cash, basis, qty, realized, fees


def validate_case(case: dict[str, Any], check: Checks) -> None:
    name = case["id"]
    seed = D(case["seed"])
    cash, basis, qty, realized, fees = filled_ledger(case)
    check.equal(f"{name}: cash+basis identity", cash + basis, seed + realized)

    if "action" in case:
        action = case["action"]
        exact_qty = qty * Fraction(action["new_share_numerator"], action["old_share_denominator"])
        whole, remainder = divmod(exact_qty.numerator, exact_qty.denominator)
        fraction = Fraction(remainder, exact_qty.denominator)
        # Independently allocate the cost fraction; floor whole paise to the claim.
        fraction_cost_ratio = fraction / exact_qty
        transferred = (
            basis * D(fraction_cost_ratio.numerator) / D(fraction_cost_ratio.denominator)
        ).quantize(D("0.01"), rounding=ROUND_FLOOR)
        basis -= transferred
        before = case["expected_before_fraction_receipt"]
        liquidation = whole * D(case["valuation"]["estimated_exit_price"]) - D(
            case["valuation"]["estimated_exit_fee"]
        )
        check.equal(f"{name}: whole shares", whole, action["result_whole_quantity"])
        check.equal(
            f"{name}: fraction",
            fraction,
            Fraction(action["fraction_numerator"], action["fraction_denominator"]),
        )
        for key, calculated in {
            "cash": cash,
            "whole_held_basis": basis,
            "fraction_basis_pending": transferred,
            "whole_liquidation_value": liquidation,
            "whole_unrealized_liquidation_pnl": liquidation - basis,
            "known_component_equity": cash + liquidation,
            "ledger_identity_cash_plus_whole_and_fraction_basis": cash + basis + transferred,
        }.items():
            check.money(f"{name}: before {key}", calculated, before[key])
        check.equal(f"{name}: full equity unavailable", before["complete_equity"], None)
        check.equal(f"{name}: gain unavailable", before["net_gain"], None)
        check.equal(f"{name}: partial component", before["known_component_state"], "partial")
        check.equal(
            f"{name}: unknown-value reason", before["complete_equity_reason"], "UNVALUED_FRACTION"
        )
        check.equal(f"{name}: transferred basis conserved", cash + basis + transferred, seed)
        receipt = D(case["fraction_cash_receipt"])
        cash += receipt
        fraction_pnl = receipt - transferred
        realized += fraction_pnl
        after = case["expected_after_fraction_receipt"]
        for key, calculated in {
            "cash": cash,
            "whole_held_basis": basis,
            "fraction_basis_pending": D(0),
            "fraction_realized_capital_pnl": fraction_pnl,
            "realized_capital_pnl": realized,
            "whole_unrealized_liquidation_pnl": liquidation - basis,
            "complete_equity": cash + liquidation,
            "net_gain": cash + liquidation - seed,
            "ledger_identity_cash_plus_basis": cash + basis,
            "ledger_identity_seed_plus_realized": seed + realized,
        }.items():
            check.money(f"{name}: after {key}", calculated, after[key])
        check.equal(f"{name}: settled identity", cash + basis, seed + realized)
        return

    if "dividend" in case:
        dividend = case["dividend"]
        receivable = D(dividend["gross_per_share"]) * dividend["entitled_quantity"] - D(
            dividend["reviewed_withholding"]
        )
        liquidation = qty * D(case["valuation"]["estimated_exit_price"]) - D(
            case["valuation"]["estimated_exit_fee"]
        )
        check.money(f"{name}: net dividend", receivable, dividend["net_receipt"])
        for stage, received in (("before", False), ("after", True)):
            expected = case[f"expected_{stage}_receipt"]
            stage_cash = cash + (receivable if received else D(0))
            unpaid = D(0) if received else receivable
            for key, calculated in {
                "cash": stage_cash,
                "held_basis": basis,
                "liquidation_value": liquidation,
                "unrealized_liquidation_pnl": liquidation - basis,
                "dividend_receivable": unpaid,
                "dividend_income_received": receivable if received else D(0),
                "realized_capital_pnl": realized,
                "complete_equity": stage_cash + liquidation + unpaid,
                "net_gain": stage_cash + liquidation + unpaid - seed,
            }.items():
                check.money(f"{name}: {stage} {key}", calculated, expected[key])
        check.money(
            f"{name}: receipt does not add equity twice",
            (cash + receivable + liquidation) - (cash + liquidation + receivable),
            case["expected_after_receipt"]["equity_change_on_receipt"],
        )
        return

    expected = case["expected"]
    for key, calculated in {
        "cash": cash,
        "held_basis": basis,
        "realized_capital_pnl": realized,
        "charged_fees": fees,
    }.items():
        if key in expected:
            check.money(f"{name}: {key}", calculated, expected[key])

    if "valuation" in case:
        valuation = case["valuation"]
        gross = qty * D(valuation["accepted_bid"])
        liquidation = qty * D(valuation["estimated_exit_price"]) - D(
            valuation["estimated_exit_fee"]
        )
        constraints = case["constraints"]
        available = max(
            D(0),
            cash
            - D(constraints["pending_buy_cash_reservation"])
            - D(constraints["invented_delivery_buffer"]),
        )
        for key, calculated in {
            "released_basis": sum(
                (
                    D(f["price"]) * f["quantity"] + D(f["fee"])
                    for f in case["fills"]
                    if f["side"] == "BUY"
                ),
                D(0),
            )
            - basis,
            "gross_market_value": gross,
            "liquidation_value": liquidation,
            "unrealized_liquidation_pnl": liquidation - basis,
            "complete_equity": cash + liquidation,
            "available_cash": available,
            "net_gain": cash + liquidation - seed,
            "simple_return_ratio": (cash + liquidation) / seed - 1,
            "ledger_identity_cash_plus_basis": cash + basis,
            "ledger_identity_seed_plus_realized": seed + realized,
        }.items():
            check.money(f"{name}: {key}", calculated, expected[key])
        check.equal(f"{name}: held quantity", qty, expected["held_quantity"])
        check.equal(f"{name}: no completed episode", expected["completed_episodes"], 0)
        check.equal(f"{name}: open episode", expected["open_episodes"], 1)
        check.equal(f"{name}: win rate unavailable", expected["win_rate_percent"], None)
        check.equal(f"{name}: win reason", expected["win_rate_reason"], "NO_COMPLETED_TRADES")
        return

    if "last_trusted_valuation" in case:
        prior = case["last_trusted_valuation"]
        prior_at = datetime.fromisoformat(prior["as_of"])
        current_cut = datetime.fromisoformat(case["current_valuation_cut"])
        check.equal(f"{name}: prior dated cut", prior_at < current_cut, True)
        check.equal(f"{name}: prior accepted bid positive", D(prior["accepted_bid"]) > 0, True)
        prior_liquidation = qty * D(prior["estimated_exit_price"]) - D(prior["estimated_exit_fee"])
        check.money(
            f"{name}: independently dated last estimate",
            cash + prior_liquidation,
            expected["last_trusted_equity"],
        )
        check.equal(f"{name}: current cash", expected["cash_freshness"], "current")
        for key in (
            "current_gross_market_value",
            "current_complete_equity",
            "current_unrealized_liquidation_pnl",
        ):
            check.equal(f"{name}: {key}", expected[key], None)
        check.equal(f"{name}: stale reason", expected["current_equity_reason"], "STALE_PRICE")
        check.equal(
            f"{name}: old estimate remains old", expected["last_trusted_equity_is_current"], False
        )
        return

    check.equal(f"{name}: no remaining shares", qty, 0)
    for key, calculated in {
        "complete_equity": cash,
        "net_gain": cash - seed,
        "simple_return_ratio": cash / seed - 1,
    }.items():
        check.money(f"{name}: {key}", calculated, expected[key])
    if case["fills"]:
        check.equal(f"{name}: completed episode", expected["completed_episodes"], 1)
        check.money(
            f"{name}: win rate", D(100) if realized > 0 else D(0), expected["win_rate_percent"]
        )
    else:
        check.money(
            f"{name}: all cash allocation", cash / cash * 100, expected["cash_allocation_percent"]
        )
        check.money(f"{name}: no stocks allocation", D(0), expected["held_allocation_percent"])
        check.equal(f"{name}: no-trade win rate", expected["win_rate_percent"], None)
        check.equal(f"{name}: no-trade reason", expected["win_rate_reason"], "NO_COMPLETED_TRADES")


def validate_return_path(case: dict[str, Any], check: Checks) -> None:
    name = case["id"]
    levels, expected = case["valuation_levels"], case["expected"]
    endpoint = D(levels[-1]) / D(levels[0]) - 1
    if "daily_returns" not in case:
        check.money(f"{name}: endpoint still defined", endpoint, expected["endpoint_return_ratio"])
        check.equal(f"{name}: declared interior gap", None in levels[1:-1], True)
        check.equal(f"{name}: no daily drawdown", expected["daily_maximum_drawdown"], None)
        check.equal(f"{name}: no annualized volatility", expected["annualized_volatility"], None)
        check.equal(f"{name}: gap reason", expected["path_metric_reason"], "INCOMPLETE_SERIES")
        return
    linked, peak, worst_pct, worst_amount = D(1), D(levels[0]), D(0), D(0)
    for before, after, rate in zip(levels[:-1], levels[1:], case["daily_returns"], strict=True):
        calculated_rate = D(after) / D(before) - 1
        check.money(f"{name}: individual daily return", calculated_rate, rate)
        linked *= 1 + calculated_rate
        peak = max(peak, D(after))
        worst_pct = max(worst_pct, 1 - D(after) / peak)
        worst_amount = max(worst_amount, peak - D(after))
    check.equal(f"{name}: endpoint and compound agree", endpoint, linked - 1)
    check.money(f"{name}: total return", endpoint, expected["total_return_ratio"])
    check.money(f"{name}: drawdown ratio", worst_pct, expected["maximum_drawdown_ratio"])
    check.money(f"{name}: drawdown amount", worst_amount, expected["maximum_drawdown_amount"])
    arithmetic_sum = sum((D(rate) for rate in case["daily_returns"]), D(0))
    check.money(
        f"{name}: misleading arithmetic sum",
        arithmetic_sum,
        expected["arithmetic_sum_not_total_return"],
    )
    check.equal(f"{name}: sum differs from portfolio return", arithmetic_sum != endpoint, True)
    check.equal(f"{name}: short-sample CAGR unavailable", expected["cagr"], None)
    check.equal(
        f"{name}: short-sample reason", expected["cagr_reason"], "INSUFFICIENT_OBSERVATIONS"
    )


def main() -> None:
    fixture = json.loads(FIXTURE_PATH.read_text())
    checks = Checks()
    checks.equal("design fixture only", fixture["runtime_contract"], False)
    checks.equal(
        "synthetic evidence", fixture["fixture_kind"], "synthetic_exact_arithmetic_design_examples"
    )
    # All fixture monetary operations terminate at this precision. This validation
    # context does not alter runtime/persisted proportional-basis arithmetic.
    with localcontext() as context:
        context.prec = 50
        context.rounding = ROUND_HALF_EVEN
        for case in fixture["cases"]:
            validate_case(case, checks)
        for case in fixture["return_path_examples"]:
            validate_return_path(case, checks)
    print(
        f"PASS: {len(fixture['cases'])} synthetic ledger examples and "
        f"{len(fixture['return_path_examples'])} return paths; "
        f"{checks.count} independent arithmetic/contract comparisons. "
        "No application imports, account access, network or writes."
    )


if __name__ == "__main__":
    main()
