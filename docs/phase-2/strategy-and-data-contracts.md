# Strategy, evidence and market-data contracts

Date: 22 October 2026 IST. Status: **Phase 2 design proposal only**. These contracts
do not change a running profile, acquire broker data, approve a review, migrate a
database, arm paper trading or establish investment performance. Implementation and
acceptance belong to later approved phases. Existing runtime behavior below is
descriptive; clauses marked **V2** are proposed requirements, not current features.

Read with [architecture](architecture.md), [API contracts](api-contracts.md), the
[Phase 1 gap analysis](../GAP_ANALYSIS.md) and
[existing daily execution guide](../daily-execution.md). The executable scenario
inventory is specified in [strategy-scenarios.json](examples/strategy-scenarios.json);
the JSON is design evidence, not a test runner or a successful test result.

## 1. Preserve the existing policy and name its limitations

The current `daily-delivery-momentum-v1` is an experimental delivery-trading
hypothesis, not a validated months-to-years investment policy. Its default screen
uses 20-session momentum, a 50-session trend average, ₹10,000,000 average daily
turnover and a 5% daily-volatility ceiling. The default execution hypothesis has a
2% stop, 4% target, 100-basis-point absolute entry gap and a 20-reviewed-session
holding limit. Configured values may differ. The holding-limit schema currently
accepts at most 252 sessions. These are descriptions of existing defaults, not
recommendations to change the operator's configuration.

References: [daily policy](../../src/trading_agent/daily_research/analysis.py),
[daily strategy identity](../../src/trading_agent/daily_execution/contracts.py),
[connected decisions](../../src/trading_agent/desk/signals.py),
[replay decisions](../../src/trading_agent/daily_execution/strategy.py).

Preserve existing strategy/configuration hashes, intent IDs, fee versions, model
artifacts, decision history and broker-independent financial records. Display the
legacy hypothesis and actual configured hold limit when selecting it. Do not call
its existing backtest a reproduction of connected behavior until a declared
runtime-specific semantics identity is attached and parity is demonstrated.

The audit found these existing differences; Phase 2 does **not** resolve them by
silently changing either runtime:

| Case | Connected desk today | Offline daily replay today | Consequence |
|---|---|---|---|
| First quote fails entry gap; a later quote passes | Reconsiders until an eligible proposal is offered; durable proposal key then prevents replay | Consumes its per-symbol/session `used` slot before checking the screen or gap | Different entry timing and sometimes different participation |
| A held stock has `needs_data` / absent latest history | No screen exit solely for that status; holding-limit check can still apply | Any noncandidate screen can cause `DAILY_SCREEN_EXIT` | Missing evidence can become a sale in replay |
| A held stock is outside the universe | No screen exit specifically for this status; independent support/risk guards still apply | Noncandidate screen can cause screen exit | Universe changes have different exit semantics |
| Current-day action changes yesterday's reference | Daily gap/vector uses `last_close` directly | Replay applies the reviewed current-day share/cash effect to yesterday's raw close | Model gap feature and entry selection can differ on an action date |
| Exit timing and authority | Fresh quote and current Approval/Automatic authority produce a proposal; operator approval may be delayed | `exits_due` runs before each grouped event; requests a direct paper exit | Same strategy name does not imply equal authorization or fill timing |
| Holding age | Uses reviewed-session indices only if opening date is present; otherwise avoids a holding-limit exit | Directly indexes opening/session dates | Incomplete calendars require explicit migration/recovery, not guessed age |

For reproducibility, future legacy result metadata should identify semantics as
`legacy-connected-v1` or `legacy-replay-v1` without changing the existing economic
hash algorithm. Existing artifacts lacking the field remain `legacy_unspecified`,
not retroactively certified. Fixing a legacy behavior requires a separately named
compatibility decision, adverse tests and explicit migration notes.

## 2. Proposed months-to-years policy identity

**V2:** introduce a new draft family, provisionally
`nse-investment-policy-v2`, with `decision_semantics = investment-decisions-v2.1`.
This is a proposed contract name, not an installed implementation. A descriptive
label such as “Long-horizon trend and momentum research” is appropriate until
parameters and evidence exist. It must not inherit legacy stops, targets or hold
limits as hidden defaults. A rules-only strategy is a distinct explicit choice;
required ML or fundamental inputs may not silently fall back to rules-only data.

Separate identities:

| Identity | Required content | Does not grant |
|---|---|---|
| `policy_version_id` | Family, semantics version, fully specified parameters, schedule and exit rules; immutable canonical configuration hash | Account authority or profitable validation |
| `data_bundle_id` | Immutable manifest plus content hashes, source/basis/availability/calendar/universe identities | Permission to assume future or unavailable data |
| `experiment_id` | Policy/data/model/calendars/cost versions, code identity, evaluation split, capital/cash-flow assumptions and execution evidence/model | Permission to install or trade |
| `installation_id` | Explicit account/policy/evidence binding, revision and effective future cycle, separate from the experiment | Permission to arm after restart |
| `authority_epoch_id` | Acknowledged mode, account/revision, activation clock, permitted bounds and expiry | Permission to bypass per-order risk |
| `signal_slot_id` | Account, installed policy lineage, symbol/issuer, side, declared cycle ID and signal rule | A fill; mode revision is excluded from slot identity |
| `proposal_id`, `intent_id`, `order_id`, `fill_id` | Durable causal links; original identities never rewritten | Equivalence between a proposal and shares bought |

New V2 hashes use an explicitly versioned canonicalization contract, not an
unannounced replacement for existing digests: UTF-8 JSON, sorted object keys,
deterministic declared sequence order, UTC aware timestamps, fixed documented
decimal-string scales, no NaN/Infinity/duplicate keys, schema version and domain tag
included. Currency and quantity units are explicit. Human labels, local paths and
secret values are excluded; source/license references and semantic configuration
are included. The same financial meaning must have one canonical representation.

Changing a threshold, horizon, formula, seed, availability rule, model feature,
ranking tie rule, fee schedule or execution convention creates a new identity.
Correcting a source creates a new data bundle. Prior decisions and experiments keep
their exact original bindings. Pending authority expires on installation changes.
No new lineage may be installed to replay a completed signal in the same cycle;
the first activation cycle is shown in an explicit migration preview, with
account-level duplicate, pending-order and current-holding checks across lineages.

### Investment decisions that must be explicit before V2 activation

These are unresolved product/investment inputs, not permission questions answered
by approval to write Phase 2 documents. A draft can be saved and researched, but
cannot be activated with unresolved required fields. No “recommended” aggressive
allocation is preselected.

| Decision | Required explicit definition | Conservative design recommendation |
|---|---|---|
| Intended holding horizon | Months/years description, review schedule, any maximum age and action at that age | Do not import the 20-session limit or promise a minimum holding period during risk exits |
| Trend/momentum configuration | Price basis, lookbacks, thresholds, rank factors/weights and deterministic ties | Start a transparent rules-only research family; evaluate out of sample before claiming validation |
| Review/rebalance cadence | Exchange-session schedule, holiday/month-end rule, entry window, missed-cycle rule | No catch-up execution after missed/restarted cycles; propose at next declared cycle |
| Exit policy | Trend/screen failure, universe exclusion, maximum age, stop/target/portfolio drawdown treatment and precedence | Missing evidence is an explicit wait/block, not a negative investment signal; emergency protection remains independent |
| Allocation | Target/max per stock, total exposure, reserve, sector/issuer caps, integer rounding and rebalance tolerance | Require explicit reviewed limits; ₹25,000 pilot capital is context, not a mandate to deploy it all |
| Quote/gap/liquidity tolerances | Current quote ages, spread/gap limits, slippage/cost assumptions and turnover participation | Reject infeasible allocations rather than borrowing, fractional shares or estimated liquidity |
| Fundamental factors | Licensed source, eligible metrics, lag/staleness, valuation and missing-data rule | Disable quality/value family until licensed causal evidence exists; show unavailable metrics |
| Benchmark and evaluation | Named comparable total-return benchmark, currency, dates, risk-free/hurdle input and out-of-sample protocol | No fabricated comparison; a price-index substitute is a different disclosed benchmark |
| ML | Explicit disabled/required mode, feature/schema/model bindings, calibration/threshold, validity/embargo | No model from the legacy family can authorize V2 without retraining and matched validation |

Portfolio construction emits target/Delta **proposals**, then independent risk may
reduce or reject them. It cannot override held-instrument retention, action
quarantine, cash reservations, fee buffers, stop protections, kill state or durable
idempotency. If existing risk cannot express the selected long-horizon exit/target
policy, activation remains blocked until that independent risk contract is reviewed
and tested; the UI must not invent targets simply to satisfy an existing schema.

## 3. V2 canonical decision semantics and connected/replay parity

One pure decision contract should consume an immutable `DecisionContext` and return
`WAIT`, `NO_SIGNAL`, `BLOCKED`, `BUY_PROPOSAL` or `SELL_PROPOSAL`, with reason codes,
input identities, `as_of`, next eligible evaluation and whether its signal slot was
consumed. Transport, authority, order submission and fills remain separate owners.
“Blocked” is a terminal slot only once the first complete opportunity was evaluated;
unavailable prerequisite states use `WAIT` with `slot_consumed=false`.

Context must include account/installation, aware decision clock, reviewed sessions,
calendar coverage, cycle ID, full data snapshot identity and input availability,
reviewed membership/instrument support, current accepted quote identity, action/basis
state, holdings/pending reservations, authority epoch and risk/model identity. All
required dependencies must be available at the decision clock. Pure results have
no network or ledger side effects. Order risk revalidates current values and bounds
under the single financial transaction owner even after a successful pure decision.

**First complete opportunity:** within an explicitly active policy schedule and
current acknowledged Approval/Automatic authority epoch, use the first accepted
fresh quote received at or after epoch activation for which required prior-period
data, full calendar coverage and current basis are valid. Receipt order must be
known; a stale, conflicting, basis-blocked, zero-depth or pre-activation quote is
not an opportunity. A known `screened_out` or membership exclusion is complete
negative evidence, unlike `needs_data`. The first complete evaluation consumes
one durable symbol/side/rule/cycle slot even if a gap, model threshold or order-risk
check fails. Later quotes cannot shop for a favorable same-cycle entry.

Manual research may calculate candidates but grants no executable opportunity or
authority. To compare modes, replay must receive the same authority events and
delays. A pure strategy parity claim compares identical declared contexts. An
execution parity claim additionally requires equal quote/control sequences,
activation/approval delays, fees, risk inputs and later fill opportunities; neither
claim is currently established for legacy connected/replay paths.

| Case / acceptance ID | V2 connected expectation | V2 replay expectation under identical context | Durable/financial invariant |
|---|---|---|---|
| P01 — first usable opportunity exceeds entry gap; later quote recovers | Record `NO_SIGNAL: ENTRY_GAP`; consume slot; no automatic retry | Same decision at same first quote; later quote cannot enter | No order, reservation or fill; new cycle may evaluate anew |
| P02 — multiple quotes or same-second Kite updates | Preserve first consumed slot; identical observation is a no-op; ordered tied updates may update marks/protection | Same with recorded quote-source/receipt ordering; conflicting replay ties remain invalid | No renewed freshness for repeats, repeated liquidity or duplicate intent |
| P03 — required prior session or indicator window missing | `WAIT: REQUIRED_DATA_UNAVAILABLE`; do not enter or consume slot | Same; no invented bar or backward-filled value | Existing holdings remain, valuations report uncertainty; independent protection still operates |
| P04 — complete screen explicitly rejects a new candidate | `NO_SIGNAL: SCREEN_FILTERED`; consume slot and explain each failed factor | Same negative evidence and rank | No buy merely because a quote exists |
| P05 — held stock's screen is missing versus explicitly filtered | Missing: `WAIT`, never discretionary sell solely for missing data. Filtered: evaluate configured exit at the declared cycle | Same distinction; do not coerce all noncandidate states into one exit | Prior stops/queued exits survive; a requested sell is not a completed fill |
| P06 — late daily row or corrected snapshot arrives | Before an unconsumed opportunity/cutoff: new version may make data usable. After consumption: preserve result, effective next cycle | Advance only by recorded availability; same binding rules | No retroactive revision of signal/model score, authority or historical return |
| P07 — current-day reviewed split/bonus/dividend | Apply verified action and basis before quote admission; convert prior raw reference with the same reviewed effect | Same effects/event order, never read a future close as a feature | For factor `f` new shares/old share and cash `c` per old share, current reference `(prior_raw_close-c)/f`; require positive result and supported action |
| P08 — action notice/review is late, unsupported or contradictory | Quarantine; `WAIT: BASIS_REVIEW_REQUIRED`; block automatic purchases/rebalance and mark uncertainty | Same; no earlier use of later review or generic factor one | No guessed cash/quantity adjustment, no forced invented liquidation; preserve claims/protection requests |
| P09 — held stock leaves selection or becomes unsupported | Feed selection retains all held symbols. Definitive membership removal follows configured exit rule; unsupported instrument/basis pauses entries pending review | Same supported-asset/action rules and declared exit policy | Cannot delete holding, drop feed subscription or bypass basis to “fix” readiness |
| P10 — hold age, cross-year/holiday gap, unknown opening date | Count declared reviewed trading sessions after opening session, not calendar days; invalid coverage `WAIT/BLOCKED: HOLD_AGE_UNKNOWN` | Same explicit index convention; no missing-date index crash or guessed age | Configured holding limit triggers only when proven; stop/kill path remains independent |
| P11 — simultaneous candidates, scarce cash, integer lot and costs | Deterministic shared batch ordering then independent exact-fee sizing and reservation | Same batch clocks, rank/tie rule, marks, charges and reservation sequence | No input iteration/arrival-order windfall; total reserved cash/exposure/risk cannot exceed limits |
| P12 — ML required but unavailable, stale or mismatched | `WAIT: MODEL_CONTEXT_INVALID` before first opportunity; threshold rejection at complete opportunity consumes slot | Same model/data/code/feature/policy/cost bindings and availability/embargo | No legacy model use, missing-to-zero feature or rules fallback |
| P13 — pending approval, expiry, rejection or risk pause | Revalidate fresh quote, expiry, mode/revision and reviewed caps at preview/approve; terminal slot remains terminal | Replay explicit approval/control events and same delays | No approved bound increase; no order after cancelled/expired authority |
| P14 — mode switch, reconnect, lost response, process restart | Reconcile existing order/fills by durable ID; expire unsubmitted authority; resume Manual; keep terminal slots | Replay same restart/control semantics in a disposable account | No automatic rearm or replay of cancelled daily signals; idempotent response may return existing order |
| P15 — missing final quote, no depth, data exhaustion | Keep pending order/holding, label stale/incomplete valuation | Same; do not synthesize a last-close liquidation | Exact ledger remains reconstructible; incomplete results cannot pass a complete-execution gate |

At a shared event timestamp, implementation must define deterministic causal
phases: validate recorded ordering; apply known calendar/control/review/action
changes; admit quotes on that basis; run risk/protection and current pending-order
processing; take a consistent batch snapshot; compute strategy/portfolio proposals;
revalidate authority/risk and reserve. New orders require a strictly later eligible
execution quote under the existing fill boundary. If source ordering is ambiguous,
fail closed rather than retrospectively apply an action to an already used quote.
Kill/disconnect revocation has priority over new authority. Proposal iteration
order must be a versioned batch rule, for example declared rank then stable symbol,
not worker scheduling. Reusing future rank/model score to sort the earlier batch is
forbidden. The exact rule must be fixed before V2 activation.

Holding-age convention for a supported calendar is
`index(current_session)-index(first_fill_session)`; opening session is age zero.
Later pooled additions do not silently reset the existing account holding clock.
If V2 requires per-lot ages, it needs a new explicit lot/accounting contract; the
current pooled position cannot be presented as statutory FIFO or independently
owned historical purchase lots. Session review is explicit across all needed years,
including early closes; weekdays are not a substitute for a reviewed calendar.

## 4. Immutable acquisition and evidence manifests

**V2 proposed `market-evidence-v2` manifest:** preparation is a bounded read-only
acquire/validate/build operation. It may create a new immutable bundle and status;
it cannot install policy, set mode, approve today's price basis, change selected
symbols, write to an operator ledger or connect a second execution owner. A separate
reviewed installation action shows effects and binds exact immutable identities.

| Manifest field group | Required meaning |
|---|---|
| Schema/content identity | Schema/version/domain, bundle UUID/content hash, each regular bounded file name/hash/size/row count, created/finished clocks; manifest published last only after validation |
| Source/acquisition | Provider and official endpoint/product identifier, request interval/symbol/interval parameters without credentials, observed retrieval clocks, license/entitlement reference, coverage limits, safe action/job ID; no secret or profile PII |
| Instrument/entity identity | Exchange, durable source security/entity IDs, effective symbol/token/tick/asset-class mapping and availability; symbol reuse, renames, delistings and mapping changes never rewrite old fills |
| Calendar | Reviewed sourced sessions covering requested history, warmup and intended analysis; historical year sources/holiday/early-close version and coverage diagnostics |
| Price data | Raw OHLCV, units/currency, session, source publication/first-availability/retrieval clocks, source revision, completeness/integrity/basis status; daily bar cannot be available before session close |
| Actions | Supported action identity/type/ex/record/payment/effective dates, terms/share units, announcement/known/reviewed clocks, source/hash, unsupported/conflict state; distinguish analytical benefit from credited ledger cash |
| Universe | Explicit `point_in_time` or `prospective_snapshot`, effective intervals and known-at clocks, source references, exclusion/delisting coverage and selection date |
| Fundamentals/sector | Provider metric definitions, fiscal period, publication/revision/availability, currency/scale/entity basis and sector taxonomy version; explicit unavailable reasons |
| Benchmark | Identified provider series/return type/currency/tax convention, constituent/availability basis where relevant, levels/dates/source revision and license |
| Derived data | Formula/aggregation/seed/basis versions, upstream hashes, warmup ranges, missing/partial/gap diagnostics and generation code identity |
| Use limitations | Synthetic or real-source assertion; historical selection eligibility, survivorship/action coverage, unverified source assertions; no `ready_for_live=true` claim |

An artifact is usable only if its entire dependency closure was available by
`as_of`, content matches hashes and declared coverage is complete for that operation.
Store `effective_at`, provider `published_at`/first known clock, local `observed_at`
and `reviewed_at` separately. An unknown historical first-availability clock is not
the same as an old fiscal period; flag unknown and reject causal backtest use.
Local download time cannot prove historical knowability. Corrections preserve the
old observation plus new revision/known clock; a current restatement cannot replace
the earlier version in an as-of experiment.

No calendar generation may start on 1 January and then silently omit required
previous-year warmup. Plan backward from the requested number of **reviewed
sessions**, acquire explicitly reviewed year sources across the boundary, validate
coverage, then request bars. If a year source is absent, return a precise missing
coverage error and preserve the last valid bundle. Do not manufacture sessions from
weekdays, copy holidays across years or mark missing vendor bars as market holidays.

Acquisition stays within source and local resource budgets defined in
[architecture](architecture.md). Work in a new private staging directory; bounded
regular-file reads, symlink/path refusal, duplicate-key/nonfinite checks and hash
verification apply before publication. Cancel/failure leaves no finished manifest
or active-pointer change; restart marks interrupted jobs and never silently resumes
installation. A duplicate request may refer to an existing immutable completed
artifact if every semantic input matches; it cannot reuse the result of a different
source revision or incomplete job.

### Raw, share-adjusted and total-return data remain distinct

| Series | Definition / appropriate use | Prohibited inference |
|---|---|---|
| Raw tradable OHLCV | Source price/share units at that session. Execution and ledger use raw observed quotes plus reviewed action transformations | A split price gap is automatically an economic loss; a raw high/low establishes an executable intraday path |
| Causally share-adjusted OHLCV | Derived at a stated as-of from supported share actions known by then; adjust all OHLC consistently, volume inversely to price factor, retain raw source and factor chain | Future actions can adjust earlier strategy inputs without an as-of revision; cash dividends are share factors |
| Gross analytical total-return index | For supported period factor `f_t` and cash `c_t` per previous share: `I_t=I_(t-1)*(f_t*C_t+c_t)/C_(t-1)`, seeded at 100. Formula uses only available chronological benefits | Index units are a tradable security; gross benefits equal spendable account cash or net investor return |
| Account equity/return | Exact ledger cash + supported marked holdings + separately disclosed eligible claims under the metric contract; external contributions handled explicitly | A broker/custody holding, guaranteed exit value or raw index return after fees/taxes |

The gross index convention assumes same-close reinvestment, ignores payment delays,
investor taxes and fees, and remains separate from the corporate-action cash/claim
ledger. Dividends must not be counted twice in index returns and account cash.
Rights, mergers, consolidations and identity changes remain unsupported until an
explicit transformation contract is implemented; never choose a zero action or
factor one to conceal an unknown event. Price-adjusted charts must visibly label
basis and as-of; volume cannot be mixed with another share basis. A total-return
index alone has no valid ATR/high/low without a separately declared adjusted OHLC
convention, so initial ATR/support/resistance use raw or share-adjusted OHLC only.

### Universe, fundamentals and benchmark eligibility

Historical selection requires membership known by the selection date and inclusion
of delisted/excluded securities within declared source coverage. Existing current
Nifty snapshots remain useful **prospective** research with a prominent
survivorship limitation; they cannot become point-in-time execution/ML evidence by
changing a label. Missing delisted prices are missing evidence, not zero returns.

Fundamental availability requires a licensed product and a provider contract for
local storage, caching, historical/revised versions, derivative displays and any
redistribution. No provider is selected or purchased by this design. Each metric
must carry entity/standalone-or-consolidated basis, accounting standard, fiscal
period, units/currency/scale, publication and first-availability clocks, revision,
and provenance. Define trailing-period windows from available reports; do not sum
cumulative quarters twice or mix consolidated numerator with standalone denominator.
P/E is unavailable or separately “not meaningful” for nonpositive earnings, not zero.
Market capitalization needs available share counts and same-basis price; split
changes must be matched. Growth with missing/zero/negative base needs a metric-specific
rule and disclosure. No zero-filled revenue, debt, sector or unlicensed estimates.

The benchmark must identify price versus gross/net total return. Align only actual
common complete sessions; report missing/nonmatching dates and coverage. Do not
forward-fill a missing benchmark into a fabricated daily return. Relative strength
over `n` matched intervals is `(stock_total_return_growth / benchmark_growth)-1`,
requiring positive base/index levels and the same return/currency convention.
Account-vs-index comparison must disclose fee/tax differences and contribution
treatment. If no admissible benchmark exists, hide dependent metrics with an
unavailable reason; a blank comparison is preferable to a synthetic Nifty series.

## 5. Long-horizon aggregation and indicator definitions

**Proposed `investment-indicators-v2.1`:** all calculations use complete, eligible,
consecutive reviewed observations on the declared basis and only dependencies
available by `as_of`. Each output carries formula version, interval, lookback,
seed/warmup, basis, upstream identity, dependency `available_at`, state and reason.
Missing means `null` plus reason, never zero. Display rounding cannot feed decisions;
financial sizing/costs remain Decimal with the existing specified tick/fee rounding.
Finite analytics may use a separately documented numeric precision/tolerance, and
independent fixtures must check it. These indicators describe evidence, not profit
probabilities or automatic orders.

### Daily to weekly/monthly

Aggregate exchange-local daily sessions into Monday–Sunday ISO weeks and calendar
months. OHLC = first open, max high, min low, last close; volume = sum, all on a
consistent share basis. A completed period requires every expected reviewed session
in that period and every input available. Week/month completion is after its last
reviewed session close **and** verified calendar coverage through the period end;
Friday/month-end weekday guesses are insufficient. Holidays/early closes follow
the reviewed calendar. An in-progress period is visibly `partial=true`, excluded
from completed-period strategy features by default. A listing/delisting or missing
bar makes a period incomplete rather than shrinking its denominator silently.
Dependency availability is the maximum constituent input/basis/calendar-availability
clock. The label/date is the last actual included session, not an invented bar.

Perform supported share adjustment before aggregating OHLC; do not aggregate raw
prices across a split and then apply one mixed-period factor. A weekly/monthly
feature's warmup counts complete weekly/monthly bars, not daily observations.

### Causal formulas and minimum warmup

Here `x_t` is the declared close/index basis, `H/L/C` share-consistent OHLC,
`n` a configured positive integer, and all recursive sequences reset at a genuine
missing required session, basis break or invalid membership/data segment. They do
not bridge a gap by carrying forward the previous value.

| Indicator | Versioned formula and first valid output | Causality / limits |
|---|---|---|
| SMA 50 / SMA 200 | `SMA_n(t)=sum(x_(t-n+1)..x_t)/n`; first output at `n` consecutive complete bars | No shortened average while warming up; require 200 completed bars for SMA200, not 200 calendar days |
| EMA n | Seed at bar `n` with SMA of first `n`; thereafter `EMA_t=alpha*x_t+(1-alpha)*EMA_(t-1)`, `alpha=2/(n+1)` | First value at `n`; seed/warmup origin included in identity. Never silently change EMA convention across display/backtest |
| RSI 14 (Wilder) | First 14 close differences require 15 bars; seed average gain/loss by arithmetic means; update `avg_t=(13*avg_(t-1)+new)/14`; `100-100/(1+avgGain/avgLoss)` | Both zero gives 50; zero loss with positive gain gives 100; zero gain with positive loss gives 0. Values before seed unavailable |
| MACD 12/26/9 | SMA-seeded EMA12 minus EMA26; line first valid at bar26. Signal EMA9 seeded from first nine valid line values; histogram=line-signal | Signal/histogram first valid at bar34. No plotting zero signal/histogram during warmup |
| ATR 14 (Wilder) | `TR_t=max(H_t-L_t,abs(H_t-C_(t-1)),abs(L_t-C_(t-1)))`; seed mean of 14 TRs then Wilder update | This contract requires previous close for each TR, so first ATR uses 15 consecutive bars. Gap/basis action without coherent adjusted OHLC blocks output |
| Rolling support/resistance n | At session `t`, support=min of prior `n` complete lows; resistance=max of prior `n` complete highs; explicitly excludes bar `t` | Requires `n` prior bars. No centered pivots or future-confirmation label presented as known in the past; levels are descriptive, not guaranteed barriers |
| Drawdown | `peak_t=max(x_start..x_t)`, `dd_t=x_t/peak_t-1`; maximum drawdown is most negative eligible `dd` within stated coverage | Label basis/window. Missing period yields incomplete sequence, not an assumed new high/recovery. Account drawdown and stock total-return drawdown are different |
| Realized daily volatility n | Population standard deviation of `n` simple consecutive returns on the selected basis; first at `n+1` closes; annualized only with explicit factor | Preserve legacy screen's population convention separately; annualization factor and sampling frequency must be disclosed, not mixed with sample variance |
| Relative strength n | Ratio of matched stock/benchmark growth factors minus one over `n` aligned intervals | Requires `n+1` matched levels; no computation across a silently omitted market date, unmatched basis or missing benchmark |

The EMA seed convention defines a reproducible value; a longer history can change
recursive values, so requested display range is not permission to truncate warmup.
Keep the manifest's fixed seed origin and calculate before slicing the visible
window. With a limited-history bundle, label the seed/warmup limitation. Require
indicator-ready states separately: enough bars for SMA50 does not imply MACD signal,
ATR, weekly SMA200 or any ranking's full dependency set is ready.

### Ranking and explanations

Filters and scores are different. Publish each configured threshold and observed
value, eligibility status, missing dependencies, component rank/weight/normalization
and deterministic tie rule. Use complete eligible peer groups as of the same clock;
a universe change creates a different experiment. Do not compare raw unscaled debt
with momentum or convert a rank score into a percentage chance of profit. A
candidate explanation must reference actual inputs and formula versions, list
contradictory factors, concentration/data risks and the next safe action. A failing
fundamentals filter cannot be described as passed because fundamentals are absent.

## 6. Implementation acceptance specification

These tests are **required future work**, not new tests executed in Phase 2. The
scenario JSON lists minimum differential cases and expected economics. A future
harness should run a shared event tape through pure decisions, connected control
adapters and isolated replay with identical authority/clock inputs. Compare signal
slots, reason codes, feature/snapshot hashes, quantities, reservations, orders and
fills. Intentional differences such as operator approval latency must be declared
inputs and must explain every resulting deviation.

1. **Legacy preservation and identity:** golden existing v1 artifacts/intent IDs
   retain their hashes and semantics; current profiles are not rewritten. V2 drafts
   with unresolved fields cannot activate. Parameter/formula/basis changes alter
   V2 identity; presentation labels/local path changes do not.
2. **Causality:** perturb future bars, future membership/actions/fundamental
   restatements/benchmark revisions and provider data unavailable at `as_of`;
   all earlier eligible results are byte-identical. Test equal clock boundaries,
   late availability, cross-year source coverage and cancellation before publication.
3. **Pure/parity:** implement P01–P15 and both orderings of same-clock action/quote
   admission, failing closed for ambiguity. Test gaps that recover, missing versus
   filtered screens, membership re-entry, holding opening outside available calendar,
   later pooled additions, ML mismatches and already-terminal cycle reactivation.
4. **Arithmetic reference fixtures:** hand-calculated constant/increasing/decreasing
   and split/dividend sequences; independent Decimal/reference calculations for
   aggregate OHLCV, every indicator's first valid index/seed, zero-gain/loss RSI,
   MACD bar34, ATR bar15, causal prior-window support/resistance and drawdown recovery.
   Recalculate from a full bundle versus a sliced view; warmup and outputs must agree.
5. **Financial invariants:** use ₹25,000 synthetic pilot cash and invented prices,
   independent fee calculations, simultaneous candidates and insufficient cash;
   verify no leverage/fractional shares, exact fee-inclusive reservations, integer
   rounding, no same-quote fills, one liquidity budget per eligible timestamp,
   partial fills and stop-triggered queued exits. Independently reconstruct cash,
   fees, quantities, pooled basis and claims from persisted SQL/fills/events; call
   reconciliation as an additional check, not the sole oracle.
6. **Authority/crash:** lost approve response, expiry, stale preview/revision,
   disconnect, kill, source mutation, process death before/after authorization and
   committed submission. No new order or resumed mode without authority; original
   pending orders/claims reconcile and terminal slots are not retried. Assert no
   broker order endpoint/call/import is reachable from any job or UI action.
7. **Data honesty/UI:** missing fundamentals are unavailable; unsupported actions
   are quarantined; partial periods/stale marks/benchmark gaps are labelled; rank is
   not probability. Show legacy versus V2 horizon, first-opportunity/no-replay reason,
   proposal versus order versus fill, and exact reviewed financial bounds. Tests must
   assert keyboard and screen-reader access to these explanations as well as text.
8. **External acceptance:** source licensing, historical first-availability claims,
   delisted/PIT coverage, current broker entitlement, sustained real data and target
   device/browser rendering require separate evidence. Synthetic parity and historical
   backtests establish neither future profit nor real-market/device acceptance.

The retained intraday strategy is outside this contract's feature scope. The
confirmed duplicate-observation false pause in its wrapper belongs to the narrow
correctness specification in the [intraday roadmap](../INTRADAY_FUTURE_ROADMAP.md).
Any later shared quote-status change must preserve benign repeat no-op semantics,
no freshness/liquidity renewal, true conflict rejection and protective exits. This
document neither changes intraday behavior nor authorizes strategy expansion.
