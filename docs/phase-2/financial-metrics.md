# Financial values, performance and allocation contracts

Design date: **22 October 2026 IST**. Contract: `investment-metrics-v1-draft`.
This deliverable is within the user-approved **Phase 2 design scope**; its proposed
contracts are not implemented runtime behavior or acceptance of future financial features. It preserves the existing paper ledger;
it does not change capital, risk settings, positions, orders, fees or authority.
These are measurement and software constraints, not investment recommendations.

Read with [architecture](architecture.md), [API contracts](api-contracts.md),
[the architecture audit](../ARCHITECTURE_AUDIT.md),
[the risk policy](../risk-policy.md) and
[synthetic arithmetic examples](examples/financial-examples.json).

## Existing semantics that must survive implementation

Source inspection, rather than a proposed label, establishes the current definitions:

| Existing component | Actual definition / boundary |
|---|---|
| `execution/paper_broker.py::_snapshot` | Cash plus conservative held-position liquidation estimates. Held bid is adjusted for configured slippage and rounded down to the instrument tick, with a minimum of one tick. Estimated sell charges reduce the position estimate. Without a quote, the legacy calculation uses pooled cost per share as a fallback and marks valuation untrusted; it is not a market price. |
| `execution/long_term.py::decorate` | Adds known unpaid net corporate receivables to equity. Unvalued fractional claims make `valuation_fresh` false. Entry-sizing available cash additionally retains a delivery-fee buffer, currently `dp_sell × max_positions`, floored at zero. |
| `corporate_actions/accounting.py::Ledger` | Buy fees join pooled basis. A sale releases proportional basis, with the exact final residual on full closure. Net sale proceeds less released basis form realized capital P&L. Fractional cash-in-lieu settlement also enters realized capital P&L. Net dividend receipts enter a separate income accumulator. |
| `persistence/database.py::reconcile` | Independently rebuilds cash, positions, claims, accumulated fees and order reservations from financial evidence. Read models must not silently repair discrepancies. |
| `portfolio/service.py` | A contribution or SIP budget spends this account's existing virtual cash. It is not a new deposit. Original acquisitions are purchase history, not current FIFO tax lots or custody records. |
| `backtesting/report.py::Performance` | Maximum **observed event-snapshot** drawdown, counting stale observations separately. It is not yet the proposed complete daily performance series. Completed pooled holding episodes drive completed-trade statistics; unfinished episodes are separately counted. |

Current Decimal strings and legacy fields retain their meaning. An additive read model
may expose better-labelled values, but must not silently convert existing `equity`
into a gross market value, erase incomplete claims, change proportional basis rounding,
or treat old report event samples as daily valuations. This design does not introduce
statutory capital-gains taxation, FIFO lots, broker custody reconciliation, settlement
cash, corporate-action tax estimation or real-money execution.

## Common value and evidence envelope

Use the [shared API envelope](api-contracts.md) with each financial measure carrying
`id`, `value`, `unit`, `state`, `freshness`, `reason_codes`, `method_id`,
`method_version`, `provenance_ref`, `as_of` and `observed_at`. The parent response
binds account, policy, source manifests, valuation snapshot and paper environment.

- Money uses finite Decimal strings, `unit: "INR"`; percentages, ratios and counts
  have explicit units. Money, return values and fee rates never use JSON binary floats
  as authoritative values. Integer quantities/counts may remain schema-typed integers
  outside the scalar-metric envelope. A string `"0"` is valid known zero; `null` is not.
- States are `available`, `partial`, `unavailable`, `not_configured` or
  `not_applicable`. `partial` is allowed only for a clearly named component or bounded
  subtotal, never a supposedly complete account total. `unavailable` has `value: null`.
  `freshness` is independently `current`, `stale` or `unknown`; current receipt does
  not make an old event price current. Known ledger cash can remain current when
  quotes are stale. Source acceptance/completeness is recorded in provenance, not
  inferred from freshness.
- `as_of` is the economic/valuation time; `observed_at` is when this response observed
  the evidence. Both are explicit offset-aware timestamps; exchange session labels
  use Asia/Kolkata. Aggregates identify the valuation cut and maximum constituent
  age. A claim's review or payment date is not a stock-price time.
- Preserve persisted monetary/basis strings exactly. Display INR to two decimals with
  a declared presentation-rounding rule and provide exact values in detail/export.
  Do not round each basis component for convenience, then sum rounded displays. The
  existing proportional-basis Decimal arithmetic is not silently migrated to a new
  precision context; any arithmetic-policy change needs a version and reconciliation
  gate. New metric calculations declare their Decimal precision and rounding in the
  method manifest; nonterminating ratios may be rounded once at that declared precision.
- Presentation may use ordinary numeric chart coordinates only after the authoritative
  exact values and missing points are retained. Never draw a smooth line across a
  missing valuation or imply executable precision beyond the applicable instrument tick.
  Exact historical/adjusted source values remain available in the table with their
  declared basis; do not round historical evidence using a later instrument tick.

Minimum stable reasons include `NO_POSITIONS`, `NO_COMPLETED_TRADES`,
`MISSING_PRICE`, `STALE_PRICE`, `PRICE_BASIS_UNREVIEWED`, `UNVALUED_FRACTION`,
`UNRECONCILED_LEDGER`, `INCOMPLETE_SERIES`, `INSUFFICIENT_OBSERVATIONS`,
`NONPOSITIVE_BASE`, `ZERO_VARIANCE`, `NO_DOWNSIDE_OBSERVATIONS`,
`UNSUPPORTED_EXTERNAL_FLOW`, `BENCHMARK_NOT_CONFIGURED`, `BENCHMARK_BASIS_MISMATCH`,
`LICENSE_NOT_APPROVED` and `SECTOR_UNKNOWN`. Codes explain data/eligibility; they
must not imply that a valid measurement authorizes a paper purchase.

## Account values and reconciliation identities

Symbols below describe one account at one reconciled ledger cut:

- `C`: actual virtual cash; `C0`: initial virtual cash.
- `B`: remaining pooled held-share basis, including paid acquisition fees.
- `H`: basis transferred to still-unpaid fractional claims.
- `R`: realized capital P&L, including settled fractional-claim capital P&L.
- `I`: received net dividend income; `A`: known unpaid net dividend receivables.
- `G`: gross marked held-share value using declared accepted bid marks before
  hypothetical slippage/exit fees; `L`: estimated net liquidation value of those shares.
- `F`: realizable value of unpaid fractional claims, unknown until supported evidence
  exists; the present system does not value those claims before payment.
- `Q`: active buy-order cash reservations; `D`: entry-sizing delivery-fee buffer.

| ID / user label | Definition | Display and eligibility |
|---|---|---|
| `cash_balance` · Virtual cash balance | `C` | Ledger money, includes proceeds/income already received. Not a bank balance or proof of settlement. |
| `cash_reserved` · Cash committed to pending buys | `Q`, summed once from active accepted/partial orders | Pending reservations are part of cash, not money already spent. Cancel releases only remaining reservation; a partial fill remains spent. |
| `delivery_fee_buffer` · Cash held back for possible delivery charges | `D` under existing bound policy | Not a charged fee, liability already paid, or investment reserve policy. |
| `available_cash` · Available for a new paper purchase | Long-term `max(0, C − Q − D)`; existing independent sizing/risk can reduce it further | Do not promise that the entire amount can be used for a particular stock. Never subtract this buffer again from equity. |
| `held_cost_basis` · Current holding cost | `B` | Different from seed capital, cumulative purchases and present market value. Sold basis is excluded. |
| `purchase_cash_debits` · Cumulative purchase spending | Sum filled buy notionals plus their actual charged fees | Historical turnover may exceed initial cash through reinvestment. Not current invested basis or new external contributions. |
| `gross_market_value` · Gross value of held shares | `G = Σ quantity × accepted bid` | Bid-mark convention is explicit. A close-mark valuation is a different method. No fallback-to-cost price qualifies. |
| `estimated_liquidation_value` · Estimated net proceeds from holdings | `L = Σ(executable-price estimate × quantity − remaining applicable estimated sell charges)` | Hypothetical, not an executable quote or guaranteed sale. Preserve possible small/negative net proceeds rather than clamping away fees. Charges respect the existing same-day DP allocation state. |
| `estimated_liquidation_equity` · Estimated virtual portfolio value | `C + L + A + F` when every term is supportably valued | Headline complete value is null if a held mark/basis/claim is unknown or stale. Last trusted estimate may be shown separately with its original time; it must not become current by reload. |
| `known_component_equity` · Known value, excluding unvalued claims | `C + known L + known A`, with coverage/excluded count | May be `partial`. It is not a guaranteed lower bound: unresolved claims, fees and incomplete action economics prevent that claim. A legacy fallback-to-basis amount is separately labelled legacy estimate, not known market value. |
| `realized_capital_pnl` · Realized capital P&L | `R` | Net acquisition/exit fees already accounted for; includes settled fractions. Show fraction component separately as a subset, never add it twice. |
| `unrealized_liquidation_pnl` · Estimated P&L on held shares | `U = L − B` | Includes estimated future exit charges. Requires complete current held valuation. Does not include income or unpaid fractional claim P&L. |
| `dividend_income_received` / `dividend_receivable` | `I` / `A` | Net of explicitly reviewed withholding. Gross dividend/withholding are supporting fields; neither is invented. Receipt transfers receivable to cash with no second gain. |
| `fraction_basis_pending` / `fraction_proceeds_received` | `H` / cumulative actual fraction receipts | Pending claim basis is known historical cost, not the claim's market value. Claim numerator/denominator remain exact integers. |
| `fees_charged` / `exit_fees_estimated` | Actual fill-fee sum / current hypothetical remaining exit charge | Costs are already embedded in the corresponding net cash/P&L. Never subtract charged fees again from a net P&L or net return. Their sum is not fees already charged. |
| `net_investment_gain` · Net gain including income | Complete equity minus `C0`, presently with no external cash flows | Null if valuation incomplete. Does not equal realized capital P&L while holdings or receivables remain. |
| `daily_pnl` · Change from daily reference | Complete current equity minus the persisted, explicitly identified daily reference | Preserve current opening-gap reference semantics. It is not necessarily close-to-close daily return. Null if either relevant valuation is incomplete/stale. |

With no external cash movement, independently verify these exact identities using
ordered fills/actions/receipts, not just displayed read-model totals:

```text
C = C0 − Σ(buy notional + buy fee) + Σ(sell notional − sell fee)
       + received net dividends + received fraction proceeds
C + B + H = C0 + R + I
complete equity = C + L + A + F
complete equity − C0 = R + I + (L − B) + A + (F − H)
cash reserved ≤ C; available cash = max(0, C − Q − D) for long-term accounts
```

If no unpaid fraction exists, `F = H = 0` and the gain bridge becomes
`R + I + U + A`. For an unvalued fraction, the full equity/gain identity remains
symbolic; replacing `F` with zero or `H` fabricates a valuation. Splits/bonuses
redistribute shares and basis without creating cash or profit by themselves. A
fraction receipt releases that claim's remaining basis and creates only the
corresponding net capital result. A dividend payment transfers `A` to `C`; it is
not an additional total-equity gain on payment.

Reservations and buffers never reduce account equity; they constrain entry sizing.
Unrealized P&L is not sale cash, held cost is not an extra equity asset, known receivables
are not spendable cash, and one independently seeded account cannot fund another.
Any reconciliation failure makes derived financial totals unavailable and blocks
mutation under existing safety rules; a chart cannot mask it.

## Performance series and return methods

### Eligible valuations

The future `portfolio-daily-net-liquidation-v1` series uses one declared valuation
cut per sourced, reviewed exchange session, plus an explicit opening baseline.
It records price/basis/action availability clocks, held coverage, claims, estimated
cost method, cash and ledger hash at each cut. A complete daily point must have
supportable same-cut valuations for all assets/claims. A close quote/bar is a
valuation input, not authority for a fill at that close. The existing event-time
`equity.csv` is evidence to retain, not an already accepted daily return series.

Non-session days are not missing observations and add no zero-return daily sample.
A missing reviewed session, stale mark, unresolved action, unvalued claim or unknown
flow creates a gap. Do not forward-fill it, interpolate it, drop it silently, or
turn the subsequent multi-session change into a one-session return. Contiguous
valid subperiods may have their own explicitly dated statistics. Required range
coverage and excluded sessions accompany every metric. An all-cash complete account
has zero investment return; it is different from an account with no valuations.

### Cash flows and returns

Current seed is initial capital, not an in-period return. Existing contributions/SIP
are security purchases funded from that seed and are internal portfolio cash changes.
Buys, sells, dividends, fees, fractional receipts and reinvestment are internal events.
For present accounts, no external deposit/withdrawal/transfer workflow is implemented.

For complete compatible endpoints with no external flows:

```text
simple total return = Vend / Vstart − 1
daily return rt = Vt / V(t−1) − 1
linked time-weighted return = Π(1 + rt) − 1
```

Both endpoint and linked methods must agree when the daily path is complete. An
endpoint return can be available when internal observations are missing, but the
path-dependent metrics cannot; its method/coverage must disclose that difference.
Never average security returns or independent training labels into portfolio return.

If external flows are added in a future approved ledger version, require explicit
signed amounts, timestamps and valuations immediately before/after each flow.
Time-weighted return chains flow-free subperiod factors. Money-weighted return solves
dated investor cash flows with contributions negative and terminal value positive,
using a declared day-count/solver and uniqueness/residual checks; it is null for
unsupported flows, no root, multiple admissible roots or insufficient valuation.
Modified Dietz is a separate approximation, never silently substituted for TWR/IRR.
With only initial and terminal cash flows, annualized money-weighted return reduces
to the same endpoint annualization; a separate IRR badge adds no independent evidence.
Unknown flows disable both adjusted methods rather than being assumed zero.

### Metric definitions and publication gates

All ratios below are computed on returns as fractions; display percentages multiply
by 100. Specify method/version and sample dates with each value. Proposed `A = 252`
is a **versioned annualization convention**, not a guarantee that a calendar year
contains 252 sessions. Use actual sourced sessions for coverage and actual elapsed
time for CAGR. Ratios may be computed for research on shorter samples only with an
explicit provisional label; the primary investment summary requires at least 252
valid consecutive daily returns and at least 365 elapsed calendar days for annualized
risk measures. These conservative UI gates are not evidence of statistical validity.

| Measure | Proposed formula / eligibility |
|---|---|
| Total return | Endpoint formula above; positive start equity, complete comparable endpoints and known flows. A zero return is valid. Nonpositive base is null. |
| CAGR | `(Vend/Vstart)^(365.25/elapsed_calendar_days) − 1`, positive endpoints, elapsed days > 0, and at least 365 elapsed days for primary display. Explicitly label shorter-period total return instead; never annualize a few profitable days by default. Complete endpoints and an uninterrupted known-flow ledger are required; missing interior valuation points are disclosed but do not alone invalidate this endpoint-derived measure. They still invalidate path-dependent risk measures. |
| Maximum daily drawdown | For each complete daily point, `peak_t = max(Vstart,…,Vt)`, `dd_t = 1 − Vt/peak_t`; maximum nonnegative `dd_t`, also show peak-to-trough INR amount and dates/duration. Daily value is unavailable with interior gaps; existing observed-event drawdown remains a separately labelled statistic. Nonpositive peaks invalidate percentage drawdown. |
| Annualized volatility | Sample standard deviation `s = sqrt(Σ(rt−mean(r))²/(n−1))`; `s × sqrt(A)`. Need n≥2 mathematically and complete regular daily path. Zero variance yields known volatility zero, not a valid Sharpe denominator. |
| Sharpe | `mean(rt−rf_t) / sample_std(rt−rf_t) × sqrt(A)`. Risk-free series must specify source/currency/tenor, publication clock and conversion convention. An explicitly selected constant zero research baseline is labelled zero-rate assumption, not a fetched yield. Missing configuration/source or zero variance gives null. |
| Sortino | `mean(rt−target_t) / sqrt(mean(min(0,rt−target_t)²)) × sqrt(A)`, with downside squared average over **all n daily samples**, not just negative observations. Target series/annual-to-daily convention are explicit. No downside observations or zero downside deviation gives null, not infinity. |
| Monthly return | Compound valid daily returns between consecutive reviewed month-end cuts. A first/last partial month is explicitly labelled partial with dates and is excluded from full-month comparisons. A missing interior session makes the full-month metric unavailable. Do not sum daily percentage returns. |
| Portfolio turnover | Both gross traded value `buy_notional + sell_notional` and a separately named two-sided turnover ratio `(buy_notional + sell_notional)/(2 × mean_daily_gross_asset_value)` over the stated period. Gross asset value is `cash + gross held market value`, excludes unvalued claims, and requires complete aligned daily coverage. No annualization by default. Also expose one-way `min(buys,sells)/mean_daily_gross_asset_value` only under a different method ID; never silently mix conventions. Fees/dividends/splits/claim receipts are not traded notional. |
| Win rate | Completed profitable pooled holding episodes / all completed pooled holding episodes. Zero-P&L completions stay in the denominator; show wins/losses/breakeven counts. No completed episode means null, not 0%. Open episodes and partial exits are censored/excluded and counted. Existing capital-P&L episode definition excludes separate dividends/fraction receipts; preserve that label until an explicitly versioned economic-episode method exists. |
| Profit factor / expectancy | Existing completed capital episodes only: positive P&L sum / absolute negative sum; mean completed net capital P&L. No negative completions makes profit factor null with `NO_COMPLETED_LOSSES`, even if every trade won. No completed episodes makes expectancy null. |
| Costs | Charged actual simulated fees, hypothetical remaining exit fees and execution slippage assumptions are separate. Net-equity returns already include the appropriate cash/basis charges and liquidation estimates. Do not subtract total fees again. |

Every report carries independent states for job completion (`completed`, `failed`,
`cancelled`, `interrupted`), valuation coverage (`complete`, `incomplete`), position
censoring (open episode/order/claim counts), and evaluation (`in_sample`,
`out_of_sample`, `walk_forward`, `not_declared`). A completed job can have incomplete
valuation; out-of-sample is only valid with immutable predeclared split, tuning and
availability evidence. It is never inferred from file age. Open holdings are not
artificially sold to improve the win rate or make a report appear complete.

## Benchmark and relative-comparison contract

Benchmark is initially `not_configured`; no series is fabricated from portfolio
prices, constituent averages, current membership or an unrelated downloaded example.
Before enabling comparison, register the exact source/index identifier, price-index
or total-return-index basis, currency, timezone, license/entitlement and permitted
display/export/cache retention, acquisition/hash and historical availability.
Source access is not itself permission to redistribute its data.

The default comparable comparison would use an appropriate INR **total-return**
benchmark alongside net-of-cost portfolio total return, explicitly explaining that
an index has no portfolio execution costs. A price-only index may be shown under its
own price-return label, with incompatibility disclosed; it cannot silently stand in
for total return. Net-versus-gross dividend and reinvestment conventions must match
or be clearly incompatible. No claim of outperformance is published from mismatched
dates/basis/currency or insufficient eligible coverage.

Both series normalize to the same starting valid observation and share sourced
reviewed session endpoints. Session-close availability must be respected: a value
published after a decision cannot explain that earlier decision. No forward-fill over
an internal missing benchmark session, guessed holiday, late constituent history or
future corporate action is allowed. A common-range view requires explicit shorter
dates/coverage and a new comparison identity; it does not silently replace the
operator's selected date range. Cumulative return difference in percentage points and
relative wealth `(1+Rp)/(1+Rb)−1` are distinct named measures. Relative-strength
features retain their source/availability/window and are not a probability of profit.
Tracking error/information ratio, if later offered, need complete paired daily samples
and separately versioned zero-denominator rules.

## Allocation, exposure and risk policy presentation

Actual allocation uses one explicit, complete gross-value denominator:

```text
allocation_base = actual cash + Σ(current accepted bid × held quantity)
stock_weight = gross held stock value / allocation_base
cash_weight = actual cash / allocation_base
```

Thus actual cash plus stock weights sum to 100% within declared Decimal precision.
Receivables and fractional claims are shown separately as excluded claims with values
or unknown state; this chart is explicitly **cash and held-share allocation**, not a
complete-liquidation-equity allocation. It must not silently include claims for one
stock and exclude them for another. Empty all-cash holdings show cash 100%; a zero or
nonpositive denominator yields unavailable percentages. Stale/unknown marks disable
current weights, with a dated last-trusted chart available separately. Pending orders
are a distinct commitment overlay, never counted as owned shares or counted twice
with cash. A cash breakdown can show `reserved`, `buffer`, and `available` only if
the segments form a nonoverlapping partition; if buffers overlap scarce cash, show
amounts and constraint text instead of an invalid pie chart.

Risk **exposure** remains the existing conservative `max(marked held value, held basis)`
per position plus pending buy cap notional. It is not the chart denominator or net
liquidation equity. Current planned stop risk and pending reserved risk remain
independent constraints; a stop level is not a maximum realized-loss guarantee.

Future per-stock/issuer/sector/cash-reserve rules are additive to all current executor
limits. A proposal must use the same ledger/quote/policy cut as its review, include all
remaining accepted/partial buy commitments once, assume no unfilled sell proceeds,
deduct fees, round to whole shares/ticks, and pass the independent existing risk gate.
For a percentage allocation limit, the policy must name the projected gross-value
denominator and valuation convention in the approval. Projected cash is reduced by
all pending/proposed worst-case cash reservations; projected holdings include their
whole-share quantities marked on the same current bid convention. Evaluate the
limit against the smaller positive pre/post projected allocation base, so fees or
new cash cannot hide a concentration breach. A missing price or nonpositive base
blocks percentage-limit evaluation. Do not replace the executor's current exposure
formula with these new presentation percentages.

Sector/issuer taxonomy requires registered source, effective date and version. Unknown
classification stays in an **Unknown** bucket and still counts toward total stock
exposure. When a configured sector cap cannot be proven because an affected holding or
new purchase has unknown classification, that new buy is blocked for review; it is
not assigned a zero sector weight or silently placed in a permissive invented sector.
Existing holdings are not automatically liquidated on classification changes. Sell
protection remains governed by existing independent rules.

There is no newly active percentage default in Phase 2. New reserve/sector/target
policies start `not_configured`, and current bound limits remain effective. A later
configuration screen may propose values only through an explicit policy preview,
coupled validation, fingerprint/migration and operator confirmation; it must not
increase capital, change limits, reuse independent seeds as shared capital or make
an automatic rebalance solely because the UI opened. Cash reserve is separate from
the existing DP buffer; validation must prevent counting the same withheld amount
twice. Target weights sum to at most 100% including an explicit target cash share,
while actual execution can differ due to whole shares, fees, liquidity and blocked
assets. An allocation suggestion is not an order or approval.

## Implementation acceptance specification

The companion JSON is **synthetic arithmetic**, not a market sample, account snapshot,
broker contract note, strategy performance claim or proof of persisted reconciliation.
Its fixed invented fees are inputs, not the current fee calculator. Verify it with an
independent Decimal calculation before building API presentation tests. Then Phase 3/5
implementation must add meaningful unit/HTTP/UI and isolated persisted-ledger tests:

1. Positive, losing, zero-result, partial-fill, cancel-after-partial and exact final
   basis residual; independent SQL/fill/action reconstruction agrees with cash and
   ledger identities. Reservations/buffers never reduce equity or get double-counted.
2. Dividend declaration/payment has no duplicate income; split/bonus conserves basis;
   fractional claim preserves exact ratio/basis, makes full equity null while unknown,
   and settles exactly once. Unsupported/late actions remain unavailable/quarantined.
3. Same money under changed display rounding, stale/missing quote, zero holdings,
   unknown sector and unresolved claims; no click/lock/reload invents data or orders.
4. Independently computed return paths, volatility, downside convention, month
   compounding, drawdown, turnover and zero denominators; missing sessions, leap-year
   elapsed time, irregular observation frequency and unsupported flows fail correctly.
5. Complete endpoints with an internal gap permit endpoint-derived total return and
   eligible CAGR; daily path metrics stay unavailable. Benchmark mismatch/license/PIT/calendar tests block comparison.
6. Complete jobs with open positions, failure/cancel/interruption and genuinely
   separate out-of-sample slices keep their distinct statuses. Identical run manifests
   reproduce exact inputs; no test is described as profitable-market acceptance.

No application tests are added by this document-only phase. Real broker, browser/device,
licensing and sustained market acceptance remain separately dated external evidence.
