# Profit-oriented stock discovery: both horizons

**0.13.0 acquisition update:** [Strategy preparation](strategy-preparation.md) now downloads
genuine current Nifty 100/500 constituents, official holiday/action sources and up to 60
completed Kite daily sessions. It exposes progress, source hashes, catalog/action/history
exclusions, explicit reviews and profile/calendar installation. Current constituents are
prospective snapshots, never substituted for historical membership/ML evidence. A real
read-only source and one-stock history probe succeeded; broader installed-run acceptance,
qualified net expectancy and matching real-market ML validation remain uncompleted.
The subsequent real Nifty 100 download retrieved all 60 expected candles for 65 shares
(3,900 rows), with 35 action exclusions. It is saved as an unreviewed private draft;
no strategy or review was installed in the actual account.

Requested 21 October 2026: the operator wants the platform to find candidates with
potential profit after costs for **both intraday and long-term paper trading**,
instead of requiring a hand-picked five-symbol list. Version 0.12.0 delivers the reviewed-profile screening, approval/automatic paper
workflow and activity UI described below. Version 0.13 adds the acquisition path above;
independent
current-market profitability acceptance remain unfinished; this is not a stock tip.

## Current capability and evidence

The five configured symbols are a manual market-data subscription, not ranked
investment recommendations. The app's one-to-ten-symbol execution/feed bound is a
local policy, not a claim about Kite's maximum market-data capacity. Broader discovery
must be separate from that bounded execution universe, and must preserve held symbols
when a reviewed shortlist is applied.

The repository already supplies causal five-minute intraday rule hypotheses,
quote-executed replays, daily momentum/trend/turnover/volatility research over up to
500 symbols, chronological ML tools and exact paper risk/accounting. The daily
screen's deterministic research rank is not calibrated expected profit. The Trading desk now connects reviewed daily bundles, broader screening, current
rule signals and optional validated ML to bounded paper proposals/execution. It does
now downloads a supported current-constituent daily subset through explicit UI preparation;
fundamentals, historical membership sourcing and automatic action accounting remain open.

Read-only inspection on 21 October 2026 found 5,184 catalog instruments, **zero
accepted account quotes and zero stored candles**. Six daily and sixteen intraday
input manifests declared synthetic data; none declared a real reviewed research
bundle. Counts describe this workspace at that observation, not every possible data
directory or future session. Catalog access and a connected socket alone do not
establish usable history or demonstrated profitability.

## Delivered workflow (0.12.0)

The [Trading desk](trading-desk.md) reads an explicitly installed real-data profile,
screens up to 500 declared symbols, excludes unreviewed equity-share classes, shows
candidate/exclusion evidence and previews a catalog-matched execution shortlist of at
most ten while preserving every held symbol. Daily screen rank is not net expectancy.
Model filtering is applied to causal trade-time features, with no silent fallback
when rules-plus-ML validation is missing or incompatible. Both horizons can queue
per-trade approvals or submit eligible paper orders automatically after explicit mode
activation. Discretionary daily sells follow the selected mode; protective exits stay
independent. Actual buy/sell activity retains reasons, authorization, fills and fees.

The original account still has its configured watchlist and no installed reviewed
real discovery profile/model from this implementation. Code/tests do not fill that
evidence gap. Synthetic fixtures are rejected by connected profile loading. The
next acceptance work is installed real-input coverage and prospective net-of-cost
acceptance, including strict class/basis sourcing; no automatic profit claim is made.

## Define “best” precisely

Use an estimated positive net expectancy supported by independent chronological
evaluation, sufficient observations and acceptable losses/drawdown. A high win rate,
recent price gain, liquid index membership or attractive gross target alone is
insufficient. No stock or selector can guarantee profit.

Net expectancy must use net completed-trade P&L from the actual fill ledger with
fees included once. Spread/slippage assumptions already embedded in execution
prices must not be subtracted again as if absent. Unclosed holdings, stale values,
missing quote paths and unresolved cash/benefit claims must remain visible; they
cannot be silently dropped or assumed liquidated to improve a ranking.

Keep separate intraday and long-term rankings, accounts and risk policies. Existing
per-account virtual cash is not a shared capital pool. A final candidate still needs
current execution checks and does not automatically authorize an order.

## Implementation sequence and remaining evidence

1. **Real data and acquisition status — reviewed UI acquisition delivered in 0.13; full-run acceptance pending.** Expose catalog, historical bars, quote/depth,
   calendar, corporate-action and freshness coverage in the UI. Record source,
   retrieval/availability clocks and missing inputs. Complete real feed/history
   validation; never relabel a synthetic fixture or infer missing prices/reviews.
   Analysis/data acquisition must remain separate from account execution authority.
2. **Reviewed broad equity universe — current constituent ingestion delivered; historical membership sourcing pending.** Start with an explicitly sourced Nifty 500
   universe as a proposed discovery baseline. NSE Indices describes this universe
   using market capitalisation and average daily turnover; that does not imply its
   members will be profitable. Fetch/version membership, match actual NSE catalog
   tokens/ticks, identify instrument class, and exclude unsupported or untradable
   instruments with explicit reasons. Do not treat every catalog `EQ` row as an
   equity share. Backtests need historical point-in-time membership including removals;
   today's constituents are not a historical universe.
3. **Intraday screen and validation — connected profile signals delivered; empirical acceptance pending.** Predeclare liquidity, usable depth/spread,
   volatility, completed-bar trend/VWAP/relative-volume and entry rules. Use contiguous
   session data, exact cost-aware sizing, later observed quote fills and current
   tradability. Rank only with adequate independent out-of-sample evidence and show
   data clock, net expectancy, sample size, loss/drawdown and exclusion reasons.
4. **Long-term screen and validation — connected profile signals delivered; empirical acceptance pending.** Acquire reviewed completed daily history and
   action-aware price/return basis, then evaluate momentum/trend/liquidity/volatility
   and delivery costs. Genuine business-quality/valuation claims additionally need
   point-in-time fundamental/filing data; price-only features cannot stand in for
   those inputs. Validate holding/exit rules and later quote-executed results across
   chronological regimes, avoiding selection/tuning on the final holdout.
5. **Stock-selection UI — profile/evidence, approval modes and activity delivered.** Show two separate lists with as-of time, universe/coverage,
   rank basis, evidence, estimated costs and risk. “No qualified candidate” and
   “insufficient data” are valid outcomes. Explain why individual symbols were
   excluded. Preview a bounded proposed feed selection, preserve all held symbols,
   require confirmation and never replace a running selection silently. Recommendations
   are hypotheses, not executed trades. Do not display unsupported confidence,
   probability, target profit or fabricated model approval.
6. **Paper acceptance.** Record prospectively selected candidates, subsequent observed
   execution, net results, coverage/outages and loss/drawdown over a predeclared
   evaluation period. Keep rejected/no-signal sessions. Reassess only through versioned
   policies. No real-order adapter or automatic live approval is part of this work.

History downloads must run outside quote/risk locks and respect provider quotas.
Incremental metrics and bounded cached state should support broad analysis without
slowing protective controls. Network acquisition and local analysis need separate
timing/coverage measures; an analysis benchmark must not conceal data-fetch latency.

## Required tests and documentation

Unit/functional checks must cover point-in-time membership, corporate-action basis,
stale/missing/unavailable data, strict instrument classes, chronological splits and
holdout isolation, exact net costs without double counting, unfinished exposure,
deterministic ties/ranks, no-positive-candidate outcomes and held-symbol preservation.
UI checks must distinguish research, selection preview and actual execution, with
explicit confirmation and safe unknown-outcome recovery. Each stage updates main
usage, the detailed guide, relevant components, implementation status and change log.

## Disabled Zerodha login button

In the current Setup page, broker login/session replacement is intentionally disabled
while a feed is requested. A verified working session does not need another login.
To replace it, use **step 6 → Disconnect market data → confirm**, refresh Setup, then
open login in step 3. Disconnecting does not close positions; pending fills/exits
wait for new quotes after reconnection. Do not disconnect merely to make the button
clickable when the current broker session already works.

Official references checked on 21 October 2026:

- [Nifty 500 universe description](https://www.niftyindices.com/indices/equity/broad-based-indices/nifty-500).
- [NSE impact cost and liquidity](https://www.nseindia.com/static/products-services/indices-impact-cost).

These sources support universe/liquidity concepts, not a claim of future returns.
