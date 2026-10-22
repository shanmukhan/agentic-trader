# Current allocation and daily-performance contracts — 0.17.0

**Portfolio** now shows a separate current allocation based on actual cash and held
whole shares at current accepted bids. This is a read-only calculation from the same
saved account/quote cut. It does not set targets, rank purchases, rebalance, change risk
limits, approve a review or submit an order. The existing net liquidation estimate,
remaining cost basis, realized/unrealized P&L and daily accounting change keep their
existing distinct definitions.

## Read current allocation

Start/restart the owning UI with `./scripts/start_ui.sh`, unlock and open
`/workspace#portfolio`. Select **Refresh saved status** for a new read. No extra input or
confirmation is needed because viewing allocation changes no account state.

The method is `cash-and-held-share-accepted-bid-allocation-v1`:

```text
share value = held whole quantity × current accepted usable bid
allocation base = actual cash + sum(share values)
cash weight % = 100 × actual cash / allocation base
share weight % = 100 × share value / allocation base
```

The server uses a private 34-significant-digit Decimal context with HALF_EVEN ratio
rounding. Monetary sums/products must remain exact; precision loss is rejected. Exact
money/percentage strings are returned, with no browser floating-point money conversion.
Displayed rounded ratios can sum slightly differently from 100%; holdings are not altered.

Example for arithmetic explanation only: ₹1,000 actual cash and two held shares at
₹500 accepted bid gives ₹2,000 allocation base, 50% cash and 50% held shares. A ₹200
pending reservation remains inside the ₹1,000 cash; subtracting it would count the
commitment twice. This example is not an account result or a purchase recommendation.

Reserved purchase cash, delivery-fee buffer and pending order count appear separately.
They restrict new purchases and can overlap. Unfilled buy quantities are not holdings;
pending sell proceeds are not cash. Dividend receivables and all fractional claims are
excluded consistently from every weight and shown as exclusions. An unvalued fractional
claim stays unknown; it is never assigned zero value merely to produce a complete portfolio.

This excluding-claims **gross allocation** differs deliberately from net liquidation
equity, which uses the existing exit-cost/claim assumptions, and from conservative risk
exposure. Compare values only after reading their bases. There is no sector allocation,
target weight, suggested rebalance or authority to increase capital.

## Missing or stale evidence

All current weights are unavailable when any held-share quote is missing/stale/unusable,
a supplied price-basis review is explicitly false, positions are truncated/incomplete,
the ledger is faulted/unreconciled, or the allocation denominator is nonpositive.
The calculation uses no cost-basis fallback. Zero cash with no holdings does not become
100% cash; a positive cash-only account does. Missing commitment evidence stays null.

The UI states the reason and withholds current weights. Refresh cannot repair an
unreviewed basis or obtain a broker quote. Resolve the relevant readiness/basis/feed
workflow, await a new accepted usable quote, then refresh. After hours an unavailable
current allocation is expected even if an older net estimate remains visible. A saved
screen becomes stale as described in [workspace.md](workspace.md); locking clears it.

## Implemented daily-performance calculator, not an invented history

`investment_research.performance.performance_summary` is a pure library contract.
There is no new browser/HTTP endpoint that accepts arbitrary equity points or activates
an investment policy. Current account reads expose `daily_metrics` as unavailable with
`ACCEPTED_DAILY_VALUATION_HISTORY_UNAVAILABLE`; browser backtest reports use
`EVENT_TIME_NOT_DAILY_CUTS`. The application does not yet persist the complete accepted
daily valuation/flow history needed to publish this suite for accounts or legacy jobs.

The calculator requires a caller-reviewed, ordered expected session calendar, an explicit
opening point before those sessions and comparable daily net-equity cuts. Each point has
canonical `session` (`YYYY-MM-DD`), aware `time` belonging to that IST day, exact decimal
`equity` or null and strict `complete` boolean; only the opening has `opening: true`.
A complete opening value must equal explicit `initial_equity`. Inputs are bounded to
25,000 reviewed daily sessions and reject duplicates, out-of-order/naive clocks and
non-finite/ambiguous values. No calendar, positive price, opening value or flow is inferred.

| Output | Required evidence and definition |
|---|---|
| Total return | Eligible opening/final endpoints, positive base and explicit no-external-flow declaration; `100 × (final / opening − 1)` |
| CAGR | Valid endpoint return and at least 365 elapsed calendar days (or a larger configured minimum); `(final / opening)^(365.25 / elapsed days) − 1` |
| Daily maximum drawdown | Complete positive daily path and known zero flows; largest peak-to-trough percent with dates/amount/duration |
| Annualized volatility | Sample standard deviation of consecutive daily returns × square root of declared annualization (default 252) |
| Sharpe | Explicit constant daily risk-free assumption, sample excess-return deviation and nonzero denominator |
| Sortino | Explicit constant daily target, downside deviation over all daily samples and nonzero denominator |
| Monthly returns | Explicit coverage start/end and reviewed session calendar; only complete months and eligible prior/current endpoints |

Primary annualized volatility/Sharpe/Sortino require at least 252 consecutive daily
returns and at least 365 elapsed calendar days. Shorter mathematically calculable
estimates are separately labelled provisional research estimates; they never fill the
primary metric. CAGR cannot annualize a short sample. Missing risk-free/target assumptions
or zero deviation remain unavailable, not zero. Declared conventions are part of the method.

Missing/incomplete intermediate daily cuts disable path-dependent statistics; valid
endpoints can still support total return and sufficiently long CAGR, with incomplete
path coverage explicit. Unknown or nonzero external flows block these return formulas.
This slice supplies no money-weighted/TWR flow treatment, benchmark-relative portfolio
series or accepted account return history. Partial months, absent sessions and unsupported
flow history keep monthly cells null with reasons; weekdays/holidays are never guessed.

Results carry method identifiers, precision/rounding, exact string/null values, units,
reason codes, primary/provisional separation, coverage and explicit gaps. The calculator
never mutates inputs or the global Decimal context. Event-time `equity.csv`, old stored
baselines and price-only stock returns cannot be relabelled as accepted daily portfolio cuts.

## Policy and acceptance boundary

The user's preference covers **both months-based and multi-year horizons**, and **both
monthly and quarterly review cadences**. Those are requirements for future configurable
policy contracts. No concrete duration, active cadence, target allocation, reserve,
rebalance threshold or new execution policy has been selected or installed. The existing
legacy offline strategy remains labelled by its actual holding-session cap.

Automated arithmetic tests use independent exact references and cover missing/stale
quotes, reservations, exclusions, flow gates, month boundaries and daily paths. Functional
read tests must independently compare persisted ledger values and prove account/mode
invariance. Those are synthetic/local evidence; rendered device acceptance, real-source
coverage, long-running daily-cut capture and profitable strategy acceptance remain open.
