# Paper risk and accounting policy

The table below describes the default intraday profile. The LT1 section specifies
the separate long-term policy. All balances are virtual. These engineering defaults are not evidence that a strategy
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
| Model | Unconfigured ML is rejected; verified models only add gates, including supervised age/availability |

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

## Phase 3 independent model boundary

An offline model cannot supply quantity or alter account limits. The broker checks
its stored version, policy/fee identity, feature/candidate fingerprint, decision
time, completed-feature time, validation availability and probability threshold.
Unscored candidates on a model-bound account receive `MODEL_REQUIRED`; missing or
inconsistent vectors receive `MODEL_FEATURE_CONTEXT`; mismatched artifacts receive
`MODEL_CONTEXT_MISMATCH`. Low scores receive `MODEL_BELOW_THRESHOLD`. A model that
is not available at that time receives `MODEL_NOT_YET_AVAILABLE`. Without a model,
ML-dependent candidates still receive `MODEL_UNAVAILABLE`.

Model checks precede sizing but do not replace any independent gate. The model
identity is durable; removing or replacing it requires a separate research account.
Idempotent intent fingerprints include the supplied feature vector. Changing a
vector under an existing intent raises a conflict instead of rescoring its order.

Training labels use separate feasible-trade accounts and actual simulated costs;
they exclude bad/incomplete paths. Selected label P&L does not account for concurrent
portfolio competition. Walk-forward/holdout gates and later scored replays provide
research diagnostics only. No live readiness or financial authorization follows.
Supervised paper deployment requires the separate Phase 4 controls. See
[ml-research.md](ml-research.md) for label semantics and limits.

## Phase 4 supervised controls

Dedicated accounts bind the exact automation/rule/catalog/model/feed policy and
cannot restart as manual accounts. `AUTOMATION_CONTROLLER_REQUIRED` rejects
controller-free submissions. Used calendar dates are pinned; proposal caps survive
history reload/restart through durable journal counts. Existing economic limits,
fees, sizing, reservations, stops and targets remain independent.

Startup and every new session require explicit arming after all universe quotes
and current completed history are ready. Backfill cannot replay missed trades.
Disconnects, stale quotes, bad history and quality failures disarm and cancel pending
buys. Stale holdings or disconnects queue durable kill exits; absent data never
fabricates liquidation. Kill/reset/reconnect do not rearm. Models must pass loader
gates, be non-synthetic, available by decision time and within the default thirty-day
validation age. Manual entries are disabled on supervised services.

Disarm preserves protective handling of filled positions; flatten/kill separately
request exits. Operational reports expose incidents and preliminary evidence gates,
and always retain false live readiness/external acceptance. See [paper-feed.md](paper-feed.md).

## Long-term paper horizon (LT1, 0.5.0)

The intraday defaults above are unchanged. Long-term uses a separate explicitly bound
account with `config/long-term.toml`: virtual ₹25,000, planned trade risk ₹250, daily
loss ₹500, persistent peak-to-equity drawdown ₹2,500, position ₹7,500, portfolio ₹20,000
and five positions. These engineering defaults are not recommended capital allocations.
The two virtual seeds are independent; a shared capital/aggregate risk cap is not supplied.

Long-term closes/weekends/restarts do not force liquidation or trigger an overnight
kill. Pending entries retain TTL/session expiry. Stop/target, operator exit, kill,
daily loss and portfolio drawdown can queue protective exits. Requests are latched
per holding until flat; restart/cancellation of residual orders cannot discard them.
A selected restarted feed must include all held symbols before pending recovery runs.
Fresh reviewed quotes, session liquidity and affordability still govern actual fills.

A new reviewed session uses the last fully trusted observed portfolio equity as its
daily reference before replacing old quotes, retaining opening gaps. Full-portfolio
freshness is required to update trusted equity/peak and evaluate portfolio loss gates;
stale/quarantined holdings delay those marks and block entries. Individual reviewed
holding stops/exits remain protective. Peak/drawdown persist across dates/restarts;
waiting for another session cannot reset breached portfolio drawdown. Reference marks
are observations, not guaranteed closing valuations or maximum-loss guarantees.

Current-session raw-price reviews must cover intervening corporate actions since
the previous accepted quote. Missing review blocks quote replacement/fills. A reported
action cancels buys and persistently quarantines the symbol. A clear review cannot
remove it; a complete supported offline action batch is required, as described in
[corporate-actions.md](corporate-actions.md). No share quantity/payment is inferred.

Delivery fee estimates have a separate pinned version, cumulative variable order
charges and one actual-fill DP charge per symbol/IST day. An entry buffer of
`max_positions × DP` reduces available entry cash. It is not a booked fee. Actual
exit cash shortfall blocks a fill without creating negative cash or losing the holding.
Startup rederives delivery fee and review/exit/quarantine evidence independently.
See [long-term.md](long-term.md) for observed official sources, cost assumptions,
excluded account/personal taxes/settlement cases and all operational boundaries.

### LT2 claims and adjusted price basis (0.6.0)

Split/bonus changes retain total capital cost and holding identity; whole shares and
fractional claims partition basis without discarding residuals. Claim basis rounds
down to paise, leaving the holding's exact residual. Stops round down and targets
up on the registered tick after dividing by the share factor. Dividends leave these
protective levels unchanged. Old symbol quotes/candles are invalidated; a clear
current-session review and strictly post-application quote are required to resume.

Known net unpaid dividends contribute to estimated equity, never spendable cash.
Receipt transfers receivable to cash without resetting the daily reference/peak.
Unknown fractional claims make portfolio valuation stale and block entries/portfolio
loss updates; whole-share stops and latched exits remain active on usable quotes.
Dividend income is separate from capital realized P&L. Fraction proceeds less its
basis join capital P&L; payment does not incur another trade/DP fee. Entitlements
persist after whole-share sale. Receipt processing time books cash; no historical
daily marks are rewritten. Unreviewed/unsupported actions remain quarantined.
