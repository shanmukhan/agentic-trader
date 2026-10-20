# Paper risk and accounting policy

All balances are virtual. These engineering defaults are not evidence that a strategy
will make money. Limits are planned constraints; gaps, unavailable quotes and outages
can produce larger simulated losses than a stop budget.

| Control | Default and behavior |
|---|---|
| Mode | Only `paper`; alternate modes fail validation |
| Capital | ₹25,000 exact Decimal cash, no borrowing |
| Per-trade risk | ₹62.50 including estimated round-trip fees and stop slippage |
| Daily loss | ₹250 against opening liquidation equity, realized + unrealized + fees |
| Position notional | ₹10,000 excluding fees; fees additionally reserved in cash |
| Total notional | ₹20,000 including pending buys; rising marks can block subsequent fills |
| Position count | Two distinct held/pending-entry symbols |
| Losing trades | Three completed losing round trips pause entries |
| Sessions | Explicit reviewed dates; 09:30 inclusive–14:30 exclusive IST entries |
| Flatten | Request at 15:15 or fifteen minutes before an earlier close |
| Freshness | Quote exchange and receipt age ≤5 seconds; no future decision times |
| Spread | At most 30 bps; positive bid and ask depth for entries |
| Slippage | Five bps adverse, rounded adversely to instrument tick |
| Latency / TTL | 100 ms simulated minimum / 30 s unfilled entry expiry |
| Model | ML-dependent intents always rejected in Phase 1 |

## Sizing and reservations

The gate computes an adverse entry cap from ask plus slippage, and a stop liquidation
price from stop minus slippage. It binary-searches the maximum integer quantity fitting
cash including buy fees, position/portfolio notional, per-trade risk and remaining
daily loss capacity after existing open/pending risk. A target whose estimated profit
does not cover estimated round-trip fees is rejected. Missing/invalid stops and target
ordering, off-grid prices, duplicate position entries, missing data and closed sessions
are rejected. Sizing and reservation commit in the same transaction.

At the default ₹500 ask and ₹495 stop, realistic cost/slippage assumptions approve
10 shares in the fixture, compared with the specification's 12 before costs. A client
cannot provide its own quantity or override the gate. Fill quotes recheck session,
feed, quote quality, kill/loss state, exposure and entry cap. A worse price cancels
the residual entry. Partial fills release only the corresponding cash/risk reservation;
cumulative fee accounting preserves the brokerage cap for each order.

## Accounting and exits

Buy cash debit = quantity × fill price + incremental order fees. The same amount
forms position cost basis. Sell credit = quantity × fill price − incremental fees.
Realized P&L deducts proportional entry cost basis. The last sale consumes the exact
remaining basis. A completed position counts once for the loss streak even when
exits were partial or cancelled/reissued after restart. Equity uses adverse bid-side
liquidation value minus estimated exit fees. Stale estimates are labelled and block
new entries; missing marks never make a position disappear.

Bid crossing a stop or target queues an exit; a later quote supplies the actual
simulated fill, which can be worse than the trigger. Bid liquidity bounds each
partial sell. The total available side depth is consumed at most once per accepted
quote event. Even configured zero latency requires a strictly later exchange quote
than creation, preventing same-time or same-candle-close executions.
Kill and session exits never manufacture cash from stale prices. With
no fresh data or reviewed open session the exit remains pending; overnight exposure
blocks entries persistently. The one-second watchdog can request exits without ticks
but cannot fill them. Shutdown preserves open positions for reconciliation.

## Charge schedule and limits of the simulator

`nse-intraday-observed-2026-10-20-v1` is an observed schedule snapshot, not a claim
about the exchange's original effective date. Rates were checked on 20 October 2026
against [Zerodha charges](https://zerodha.com/charges/): brokerage min(0.03%, ₹20)
per order, sell STT 0.025%, NSE transaction 0.00307%, SEBI ₹10/crore, buy stamp 0.003%,
and GST 18% on taxable charges. The estimate includes NSE IPFT ₹0.01/crore plus GST.
Each order's accumulated fees round up to a paisa; partial fills charge only the
increment from the cumulative total. This deliberately differs from broker
contract-note netting, statutory rounding, and later fee changes.

Stops, spread/slippage estimates, and displayed returns are simulation assumptions.
There is no exchange queue-position model, hidden liquidity, price impact calibration,
corporate-action adjustment, live order rejection model or profitability gate.
Unfillable/cancelled/rejected paper instructions exercise engineering behavior.
Calibrate against actual data before using the simulator for research conclusions.
Schedule upgrades require a reviewed version and a new research account/replay.

## Phase 2 research boundary

Rule hypotheses generate entry proposals only in isolated backtest accounts. The
same cash, risk, exposure, freshness, kill and session gates apply; there is no
strategy bypass or client-supplied quantity. Missing/flagged candle history disables
the symbol for the session. A historical candle's high/low cannot trigger a fill;
only supplied quote events can establish observed stop/target order and liquidity.

Dataset exhaustion never closes a holding at a convenient last price. Reports retain
unresolved orders/positions, label stale/gapped results incomplete, and distinguish
completed-trade P&L from estimated liquidation equity. Historical fee matching is
not verified: the current observed charge snapshot is an explicit approximation
across dataset dates. Synthetic provenance and minimum sample gates cannot authorize
live trading. See [backtesting.md](backtesting.md) for research assumptions.
