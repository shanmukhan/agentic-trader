"""Versioned conservative paper estimates, NOT broker contract-note accounting."""

from dataclasses import dataclass
from datetime import date
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from trading_agent.settings import Settings

D = Decimal
PAISA = D("0.01")


def up(value: Decimal, tick: Decimal = PAISA) -> Decimal:
    return (value / tick).to_integral_value(rounding=ROUND_CEILING) * tick


def down(value: Decimal, tick: Decimal = PAISA) -> Decimal:
    return (value / tick).to_integral_value(rounding=ROUND_FLOOR) * tick


@dataclass(frozen=True)
class Charges:
    version: str = "nse-intraday-observed-2026-10-20-v1"
    observed_on: date = date(2026, 10, 20)
    brokerage_rate: Decimal = D("0.0003")
    brokerage_cap: Decimal = D("20")
    stt_sell: Decimal = D("0.00025")
    stt_buy: Decimal = D("0")
    dp_sell: Decimal = D("0")
    exchange_rate: Decimal = D("0.0000307")
    sebi_rate: Decimal = D("0.000001")
    ipft_rate: Decimal = D("0.000000001")
    stamp_buy: Decimal = D("0.00003")
    gst: Decimal = D("0.18")

    def fee(self, side: str, turnover: Decimal) -> Decimal:
        if side not in ("BUY", "SELL") or not turnover.is_finite() or turnover < 0:
            raise ValueError("invalid fee input")
        if turnover == 0:
            return D(0)
        brokerage = min(self.brokerage_cap, turnover * self.brokerage_rate)
        taxable = brokerage + turnover * (self.exchange_rate + self.sebi_rate + self.ipft_rate)
        tax = turnover * (self.stt_sell if side == "SELL" else self.stamp_buy + self.stt_buy)
        return up(taxable * (1 + self.gst) + tax) + (self.dp_sell if side == "SELL" else D(0))

    def round_trip(self, buy: Decimal, sell: Decimal, quantity: int) -> Decimal:
        return self.fee("BUY", buy * quantity) + self.fee("SELL", sell * quantity)


def delivery_charges() -> Charges:
    """Observed retail-individual NSE estimate, including the higher published DP rate."""
    return Charges(
        version="nse-delivery-observed-2026-10-20-v1",
        brokerage_rate=D(0),
        brokerage_cap=D(0),
        stt_buy=D("0.001"),
        stt_sell=D("0.001"),
        stamp_buy=D("0.00015"),
        dp_sell=D("15.34"),
    )


def charges_for(settings: "Settings") -> Charges:
    return delivery_charges() if settings.investment_horizon == "long_term" else Charges()
