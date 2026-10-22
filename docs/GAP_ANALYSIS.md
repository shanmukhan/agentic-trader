# V2 requirements and gap analysis

Audit date: **22 October 2026 (IST)**. Baseline: **0.14.0**, Git
`2d5c208`. Scope: Phase 1 of [improvements.txt](../improvements.txt).
This is an inspection and implementation proposal. It adds no execution authority,
does not change strategy parameters and does not approve later implementation.

The application already contains a substantial paper-research and accounting
system. Its missing work is broader than a visual redesign: the current default
daily hypothesis exits after twenty reviewed sessions, whereas the requested
product prioritizes holding periods of months to years. Historical daily replay
and chronological model validation exist in the CLI; a graphical backtesting
workspace does not. Replacing those working engines with a chart-only simulator
would lose important causality and accounting safeguards.

## Status, severity and complexity

- **Implemented:** the specific bounded capability exists in source and has
  relevant automated coverage. This does not mean external acceptance is complete.
- **Partial:** a useful subset exists, but one or more requested behaviors are absent.
- **Missing:** no implementation of the requested capability was found in the
  inspected relevant components. Existing prerequisites may still be reusable.
- **Blocked — licensed data:** do not implement populated results until a reliable
  source, usage rights, historical availability and revision semantics are established.
  A clearly unavailable state can be implemented before acquiring a source.
- **Preserved/deferred:** existing intraday behavior remains supported; new intraday
  work is outside this modernization. See [the intraday roadmap](INTRADAY_FUTURE_ROADMAP.md).

Severity describes the consequence of treating a gap as complete: **High** can
mislead an investment decision or compromise a financial/workflow boundary;
**Medium** materially limits research or usability; **Low** is a contained
presentation/documentation issue. No critical financial exploit is asserted by
this analysis. Security findings belong in [ARCHITECTURE_AUDIT.md](ARCHITECTURE_AUDIT.md).

Complexity is relative engineering scope, not a delivery estimate: **S** is a
bounded presentation/documentation change; **M** spans one component/API and tests;
**L** spans data, calculations, API, UI and financial validation; **XL** requires
new source contracts or cross-component financial workflows. A collection of
individually small indicators is a larger integrated analysis release.

## Product, data and strategy traceability

| ID / requested capability | Status and actual behavior | Evidence | Gap consequence / priority | Dependencies / complexity |
|---|---|---|---|---|
| Q01 · Months-to-years investment horizon | **Partial.** Delivery holdings survive closes, weekends and restarts. The current daily strategy defaults to 20-session momentum, 50-session trend, a 2% stop, a 4% target and a 20-session holding limit; the holding-limit schema permits at most 252 sessions. Overnight accounting is not a multi-year investment policy. | [DailyStrategy](../src/trading_agent/daily_execution/contracts.py), [daily exits](../src/trading_agent/daily_execution/strategy.py), [default config](../config/daily-strategy.toml), [overnight tests](../tests/long_term/test_account.py) | **High / P1.** A beginner may mistake an experimental short holding policy for a validated long-term strategy. | Explicit horizon and exit policy, longer history, corporate-action coverage, benchmark and out-of-sample experiments; **L**. Preserve existing policy/version identity rather than silently changing it. |
| Q02 · NSE discovery and ranking | **Partial.** Current Nifty 100/500 constituent snapshots, genuine broker daily history, share-class reviews and conservative exclusions feed a deterministic daily screen. Not an unrestricted all-NSE investment screener. | [preparation](../src/trading_agent/desk/preparation.py), [official-source adapter](../src/trading_agent/desk/sources.py), [screen](../src/trading_agent/daily_research/analysis.py), [preparation tests](../tests/functional/test_strategy_preparation.py) | **Medium / P1.** Universe and exclusions constrain what can be discovered. | Coverage inventory, explicit universe selection and provenance UI; **M/L**. |
| Q03 · Liquidity, momentum, trend and volatility filters | **Implemented, bounded.** Mean raw close×volume, analytical gross return, total-return-index trend mean and population daily-return volatility; rank descending by return with symbol tie breaks. Fixed descriptive rules, not a probability of profit. | [Window.metrics/analyze](../src/trading_agent/daily_research/analysis.py), [daily analysis tests](../tests/daily_research/test_daily_analysis.py) | **Medium / preserve.** Explain units, periods and rejected/missing states when exposing filters. | Reuse validated calculations and parameter bounds; additional filter UI **M**. |
| Q04 · Market capitalization, revenue/earnings growth, profitability, debt and valuation | **Blocked — licensed data.** No fundamental-data ingestion or point-in-time financial statement schema was found. A broker instrument master and OHLCV are not fundamentals. | [daily bar contract](../src/trading_agent/daily_research/dataset.py), [screen policy](../src/trading_agent/daily_research/analysis.py), [source adapters](../src/trading_agent/desk/sources.py) | **High / P1 source decision.** Filling these with zeros or current values in past periods would mislead research. | Reliable licensed provider, fiscal-period units, currency, publication/first-availability clocks, restatements, entity mapping and historical coverage; **XL**, external dependency. |
| Q05 · Missing fundamental values distinct from zero | **Missing** as a financial-data contract; no populated fundamentals exist. | Same evidence as Q04; [analysis response](../src/trading_agent/api/analysis.py) | **High / before Q04 UI.** Unknown is not zero debt, zero growth or cheap valuation. | Nullable values plus per-field availability/reason/source; **M** after source contract. |
| Q06 · Candidate evidence, contradictions, risk and uncertainty | **Partial.** Screen metrics, rank, exclusion reason codes, coverage and limitations exist. A structured plain-English bullish/bearish/missing-data comparison does not. | [screen output](../src/trading_agent/daily_research/analysis.py), [analysis UI](../src/trading_agent/api/static/analysis.js), [desk research](../src/trading_agent/desk/research.py) | **High / P1.** Rank must not imply expected profit or hide rejected evidence. | Versioned explanation templates tied to actual inputs and policy; **M**. |
| Q07 · Watchlists and candidate comparison | **Partial.** Execution shortlist retains held stocks and permits up to ten subscribed instruments; research universe is broader (up to 500 symbols). No independent named research watchlists or side-by-side candidate comparison. The ten-symbol limit is an application constraint. | [settings](../src/trading_agent/settings.py), [desk service](../src/trading_agent/desk/service.py), [analysis API](../src/trading_agent/api/analysis.py) | **Medium / P2.** Users conflate research selection, subscriptions and investment approval. | Separate research-watchlist persistence from execution subscriptions; preserve held-symbol/duplicate-order constraints; **M/L**. |
| Q08 · Daily, weekly and monthly analysis | **Partial.** Read-only charts expose saved daily, 1-minute and 5-minute candles. Weekly/monthly aggregation and completed-period availability semantics are absent. | [Timeframe/API](../src/trading_agent/api/analysis.py), [chart page](../src/trading_agent/api/static/analysis.html), [analysis tests](../tests/unit/test_analysis.py) | **Medium / P1.** Current minute intervals are not the requested long-term timeframes. | Reviewed-session aggregation, partial-period labels, gaps and corporate-action basis policy; **M/L**. No new intraday strategy behavior. |
| Q09 · Candlesticks, volume, exact data and interaction | **Partial.** Saved raw OHLC candlestick/volume SVG and exact decimal table exist, with stock/interval selection. No chart zoom, crosshair, range selector or richer interactive chart library. | [analysis.js](../src/trading_agent/api/static/analysis.js), [analysis docs](market-analysis.md), [UI tests](../tests/ui/analysis.test.cjs) | **Medium / P2.** The existing chart is useful but does not meet the complete analysis workspace. | Accessible interaction design and browser acceptance; reuse current API where sufficient; **M**. |
| Q10 · SMA 50/200, EMA, RSI, MACD, ATR | **Partial.** Chart SMA 20/50 use exact raw closes and require a full available-bar window. Requested SMA 200 and long-term EMA/RSI/MACD/ATR are absent. Intraday strategy EMA/ATR already exist but do not supply these chart endpoints. | [_averages](../src/trading_agent/api/analysis.py), [intraday rules](../src/trading_agent/strategy/rules.py), [SMA tests](../tests/unit/test_analysis.py) | **Medium / P1/P2.** Do not label these indicators implemented merely because an intraday calculation exists. | Explicit warmup, formulas, missing sessions, raw/adjusted basis, independent reference fixtures; **M** each, **L** integrated. |
| Q11 · Support/resistance, relative strength and stock drawdown | **Missing** from the analysis workspace. Screen volatility is present, but is not drawdown or benchmark-relative strength. | [analysis response](../src/trading_agent/api/analysis.py), [screen metrics](../src/trading_agent/daily_research/analysis.py) | **Medium / P2.** Long-term context remains incomplete. | Predeclared support/resistance method; benchmark-aligned total-return series and source; causal peak/drawdown tests; **L**. |
| Q12 · Transparent research freshness and provenance | **Implemented, bounded.** Daily availability/completion/hash checks; chart/source/quote statuses separated. Current minute candle records do not certify per-candle broker/replay provenance; source labels remain declarations. | [analysis API](../src/trading_agent/api/analysis.py), [quote status](../src/trading_agent/execution/quote_status.py), [read-only API tests](../tests/functional/test_analysis_api.py) | **High / preserve, P1 improvement.** Genuine saved data is not necessarily a fresh executable quote or independently authenticated source. | Preserve null provenance; durable per-observation source/receipt records before stronger claims; **M/L**. |
| Q13 · Configurable trend/momentum investment strategies | **Partial.** A typed fixed daily momentum/trend/liquidity/volatility hypothesis and optional matched daily ML artifact exist; configuration is versioned/hashed. No general visual strategy builder, strategy library or comparison workspace. | [daily contracts](../src/trading_agent/daily_execution/contracts.py), [desk profile](../src/trading_agent/desk/contracts.py), [Strategies page](../src/trading_agent/api/static/desk.html) | **High / P1.** Experimental rules need an explicit policy and horizon; installation is not validation. | Safe configuration schema, immutable versions, preview, validation and experiment identity; **L**. |
| Q14 · Quality/value investment strategy | **Blocked — licensed data** for meaningful research. No such strategy currently implemented. | Q04 plus [current daily strategy](../src/trading_agent/daily_execution/strategy.py) | **High / P2 after data.** Price-only proxies must not be relabeled fundamentals. | Q04/Q05, causal factor definitions and out-of-sample evidence; **XL**. |
| Q15 · Periodic portfolio rebalancing | **Missing.** No target-weight/delta/cost/turnover-constrained rebalance planner or batch execution workflow. | [portfolio service](../src/trading_agent/portfolio/service.py), [portfolio contracts](../src/trading_agent/portfolio/contracts.py) | **High / P2.** Independent ranked buys are not portfolio construction. | Target-allocation policy, sell/buy sequencing, exact cash reservations, minimum lots, idempotency and partial-failure recovery; **XL**. |
| Q16 · SIP-style investment | **Partial.** Explicit reviewed session dates, per-occurrence preview/confirmation, existing cash and once-only attempts are implemented. No unattended periodic orders, automatic deposits or calendar catch-up. This boundary is deliberate. | [SIP contracts/service](../src/trading_agent/portfolio/service.py), [SIP tests](../tests/portfolio/test_contributions.py), [usage](portfolio-contributions.md) | **High / preserve.** A saved plan does not authorize unattended investment or mint capital. | Any future unattended paper scheduler needs separate authority, calendar, cash and failure model; **L**. |
| Q17 · Strategy preparation across the calendar year | **Partial; confirmed defect.** `proposed_sessions` clips its lookback to 1 January of the current year but requires at least 51 earlier sessions. Valid early-year preparation cannot satisfy that requirement; audit fixtures for 15 January and 27 February 2026 fail `CALENDAR_RESPONSE_INVALID_OR_TOO_SHORT`. | [proposed_sessions](../src/trading_agent/desk/sources.py), reproduction described in [architecture audit](ARCHITECTURE_AUDIT.md) | **High / P1.** A working October setup path does not establish reliable year-round onboarding/history preparation. | Reviewed previous/current-year holiday data, cross-year sessions and boundary fixtures; do not substitute unreviewed weekdays; **M/L**. |

## Backtesting and financial validity traceability

| ID / requirement | Status and actual behavior | Evidence | Gap consequence / priority | Dependencies / complexity |
|---|---|---|---|---|
| B01 · Historical daily delivery backtesting | **Implemented, bounded CLI.** `daily-backtest` consumes reviewed daily and observed-quote execution bundles in an isolated delivery account. `daily-labels` creates independent counterfactual trials; `daily-train` and a later scored replay are separate. Intraday `backtest` is also implemented in its own namespace. No graphical run/configuration/compare workflow. | [daily runner](../src/trading_agent/daily_execution/runner.py), [CLI tests](../tests/functional/test_daily_execution_cli.py), [guide](daily-execution.md), [intraday backtesting](backtesting.md) | **High / preserve; P1 UX.** Claiming backtesting is missing overlooks working validation; exposing a run as a profitable strategy would overstate it. | Browser job/result contracts, safe paths, immutable inputs, cancellation/failure status; **L**. |
| B02 · No look-ahead and causal timing | **Implemented, bounded contracts.** Daily completion and first-availability clocks, membership chronology, prior daily screen, strictly later execution quote, matched action-adjusted reference and future-input invariance tests. Source clocks are reviewed assertions. | [timeline](../src/trading_agent/daily_execution/timeline.py), [daily decisions](../src/trading_agent/daily_execution/strategy.py), [future-data tests](../tests/daily_execution/test_execution.py), [daily-analysis tests](../tests/daily_research/test_daily_analysis.py) | **High / preserve.** Passing synthetic future-invariance tests does not verify vendor publication clocks or data revisions. | Any new feature/source must retain availability clocks and independent perturbation tests; **L** for new sources. |
| B03 · Point-in-time membership and survivorship disclosure | **Partial.** Strict historical inclusion/exclusion/re-entry and `known_at` contracts exist. UI acquisition uses today's `prospective_snapshot`; historical execution loader rejects it. No independently acquired historical constituent archive. | [daily dataset](../src/trading_agent/daily_research/dataset.py), [execution loader](../src/trading_agent/daily_execution/dataset.py), [preparation](../src/trading_agent/desk/preparation.py) | **High / P1.** Today's survivors cannot establish unbiased past strategy results. | Licensed/traceable historical membership, delisted securities and identifiers; **XL** external source work. |
| B04 · Corporate actions in research and accounts | **Partial.** Explicit period share/cash benefits support gross analytical daily returns. Delivery ledger supports reviewed split/bonus/dividend/receipts and fractional claims, quarantine, atomic idempotent batches and independent reconciliation. Research is not automatically adjusted from ledger actions. Current downloader excludes stocks with returned actions rather than guessing. | [daily bar/index](../src/trading_agent/daily_research/analysis.py), [corporate service](../src/trading_agent/corporate_actions/service.py), [routing tests](../tests/daily_execution/test_corporate_routing.py), [ledger tests](../tests/long_term/test_corporate_actions.py) | **High / P1.** Wider multi-year coverage requires more than current action exclusions; raw chart gaps can be mistaken for economic losses. | Reviewed chronological source, unsupported-action policy and separate raw/total-return series; **XL**. Reverse splits, rights, mergers and identity changes currently require exclusion/quarantine. |
| B05 · Costs, adverse slippage and liquidity | **Implemented estimates / external calibration partial.** Versioned Decimal charges, buy/sell statutory estimates, delivery DP once per symbol/IST date, adverse tick rounding, latency/TTL and observed depth-bound partial fills. Historical fee schedule, queue position, impact and contract-note netting are not reconstructed. | [costs](../src/trading_agent/execution/costs.py), [risk sizing](../src/trading_agent/risk/limits.py), [broker](../src/trading_agent/execution/paper_broker.py), [delivery tests](../tests/long_term/test_account.py) | **High / P1.** Estimated net returns are sensitive to costs and sparse executable observations. | Version-effective historical cost tables, explicit scenario assumptions and independent calibration; **L** plus external evidence. |
| B06 · Realistic order timing / no OHLC-invented fills | **Implemented.** Only later observed quotes fill; OHLC touches do not establish barrier ordering. Data exhaustion retains unfinished holdings/orders; gaps/stale valuations make reports incomplete. | [runner](../src/trading_agent/daily_execution/runner.py), [intraday runner tests](../tests/backtesting/test_runner.py), [delivery execution tests](../tests/daily_execution/test_execution.py) | **High / preserve.** A daily-candle-only simulator would require a separately disclosed model and must not silently replace this behavior. | Long-horizon observed execution coverage or explicitly approved alternative simulation contract; **XL** if new model. |
| B07 · Out-of-sample and walk-forward validation | **Implemented for optional ML.** Whole-session expanding splits, train/calibration/evaluation separation, label-interval purge/embargo, holdout, model/input identity and later scored replay gates. No general browser experiment registry or predeclared strategy-comparison process. | [splits](../src/trading_agent/ml/splits.py), [daily model](../src/trading_agent/daily_execution/model.py), [model tests](../tests/daily_execution/test_models.py) | **High / preserve, P1 extension.** An internally passing synthetic holdout is not real-market acceptance or proof of profit. | Real eligible data and predeclared evaluation protocol; experiment registry **L**. |
| B08 · Net P&L, win rate, costs and equity observations | **Implemented, bounded.** Ledger-based completed-trade win rate, expectancy and profit factor; observed equity/drawdown, fees and unresolved claims; event-level `equity.csv`. Intraday runner also reports a simple net return percentage. Independent-label sums are explicitly not portfolio return. | [ledger report](../src/trading_agent/backtesting/report.py), [daily report](../src/trading_agent/daily_execution/runner.py), [metric tests](../tests/backtesting/test_metrics.py) | **High / preserve.** Separate completed-trade capital P&L, dividends, fractions and current estimated liquidation equity. | Preserve stale/incomplete and null/no-trade semantics; presentation **M**. |
| B09 · CAGR, annualized volatility, Sharpe, Sortino, monthly returns and turnover | **Missing** as the requested investment-performance suite. Raw fill turnover and event equity exist, but no formal portfolio turnover ratio or standardized return-series methodology. | [report metric construction](../src/trading_agent/backtesting/report.py), [daily metrics](../src/trading_agent/daily_execution/runner.py) | **High / P1/P2.** Annualizing event-time or stale observations can produce misleading comparisons. | Reviewed daily valuations, period frequency, trading-day convention, risk-free source, downside target, cash-flow treatment, null/short-history rules and independent calculations; **L**. |
| B10 · Benchmark comparison / relative strength | **Missing.** No benchmark-series ingestion, synchronized total-return comparison or Nifty 50 benchmark report. Performance microbenchmark scripts are engineering timing evidence, not investment benchmarks. | [current metrics](../src/trading_agent/backtesting/report.py), [daily runner](../src/trading_agent/daily_execution/runner.py), [scripts](../scripts/benchmark_daily.py) | **High / P1 source decision.** Absolute gains cannot establish outperformance. | Traceable licensed index price/total-return data, aligned dates, costs and reinvestment conventions; **L/XL**. |
| B11 · Reproducible experiments | **Implemented, bounded.** New output directories, input/code/policy/model/journal hashes, strict schemas and completion manifests. No browser experiment catalog/compare/export management. | [daily runner](../src/trading_agent/daily_execution/runner.py), [dataset validation](../src/trading_agent/daily_execution/dataset.py), [CLI tests](../tests/functional/test_daily_execution_cli.py) | **Medium / preserve, P2 UI.** Do not discard adverse/failed experiments or reuse changed inputs under a successful identity. | Read-only artifact index and safe validated path mapping; **M/L**. |
| B12 · Research-to-connected strategy parity | **Partial; specification gap.** Connected daily signals revisit quotes until their gap passes; replay consumes its first eligible per-symbol/day attempt before screen/gap checks. Connected holdings request screen exit specifically for `screened_out`, whereas replay also exits for other noncandidate states. Both use independent risk checks, but these choices can produce different investment paths under the same named daily policy. | [connected daily signals](../src/trading_agent/desk/signals.py), [replay decisions](../src/trading_agent/daily_execution/strategy.py) | **High / P1.** Backtest results must not be presented as a validated reproduction of connected behavior until equivalence or intentional differences are specified. This is not a finding that every differing choice is unsafe. | Declare attempt/late-data/missing-screen/action-reference semantics; add shared scenario parity tests before refactoring or changing either version; **L**. |

## Capital, paper execution and monitoring traceability

| ID / requirement | Status and actual behavior | Evidence | Gap consequence / priority | Dependencies / complexity |
|---|---|---|---|---|
| R01 · ₹25,000 pilot and configurable limits | **Implemented.** Typed TOML settings with virtual seed, position/total notional, risk/loss/drawdown, quote/spread/slippage/session controls. Persisted policy identity prevents silently reinterpreting an account under a changed policy. No full settings editor. | [settings](../src/trading_agent/settings.py), [policy identity](../src/trading_agent/risk/policy.py), [account tests](../tests/long_term/test_account.py) | **High / preserve.** These are engineering assumptions, not suitable allocations or maximum realized loss guarantees. | Reviewed policy-change/new-account workflow; settings UI **M/L**. |
| R02 · Position size, cash and aggregate exposure | **Implemented, bounded per account.** Integer sizing includes fees, pending reservations, planned stop risk and current marked exposure. Pooled additions retain protections. | [size](../src/trading_agent/risk/limits.py), [broker](../src/trading_agent/execution/paper_broker.py), [contribution tests](../tests/portfolio/test_contributions.py) | **High / preserve.** Price gaps and exits needing liquidity can exceed planned risk. | Any allocation/rebalance planner must use this gate rather than bypass it; **L** integration. |
| R03 · Cash reserve and sector concentration | **Partial.** A DP exit-fee buffer and configured total-notional cap leave bounded room; no explicit configurable cash-reserve percentage, sector taxonomy or sector-weight constraint. | [long-term snapshot](../src/trading_agent/execution/long_term.py), [settings](../src/trading_agent/settings.py) | **High / P2.** A fee buffer is not a portfolio cash policy; five stocks can share one sector. | Reviewed sector/issuer mapping, policy limits and pending-order treatment; **L**. |
| R04 · Portfolio drawdown and protective controls | **Implemented, bounded.** Persistent trusted peak/daily reference, opening-gap retention, kill, latched exits and stale/quarantined mark blocking. Stops request exits; they do not guarantee price or completion. | [long-term watch](../src/trading_agent/execution/long_term.py), [drawdown/restart tests](../tests/long_term/test_account.py), [risk guide](risk-policy.md) | **High / preserve.** Missing usable quotes delay valuation updates and cannot manufacture liquidation. | UI risk history and explanations **M**; real-world maximum-loss guarantee is unavailable. |
| R05 · Cross-account allocation and shared capital | **Missing.** Each intraday/delivery/research account owns a separate seed; there is no shared ₹25,000 pool or cross-account exposure cap. | [long-term guide](long-term.md), [independent replay](../src/trading_agent/daily_execution/runner.py), [settings](../src/trading_agent/settings.py) | **High / P2 if multiple accounts exposed.** Summing accounts can double-count virtual capital and understate aggregate exposure. | Account registry, capital authority and atomic allocation/reservation semantics; **XL**. |
| R06 · Durable proposals, approvals, orders and fills | **Implemented.** Distinct durable decision/order/fill records, preview-bound approval, idempotent intents, independent risk validation and restart recovery. Cancellation of a proposal need not mean an order or trade existed. Daily signals are not replayed merely by changing mode. | [desk service](../src/trading_agent/desk/service.py), [desk reconciliation](../src/trading_agent/desk/accounting.py), [decision tests](../tests/desk/test_decisions.py) | **High / preserve.** UI must keep these stages separate and explain idle/terminal outcomes. | Clear journey/status presentation; **M**. No automatic retry or new authority implied by this audit. |
| R07 · Exact portfolio accounting and reconciliation | **Implemented, bounded.** Decimal cash/fees/basis, fill-ledger reconstruction, pooled proportional exits, exact final residual, claims and original purchase history. No custody, statutory FIFO tax lots, settlement or personal tax engine. | [database reconciliation](../src/trading_agent/persistence/database.py), [corporate reconstruction](../src/trading_agent/corporate_actions/accounting.py), [accounting sequence tests](../tests/integration/test_accounting_sequences.py), [contribution tests](../tests/portfolio/test_contributions.py) | **High / preserve.** Original purchase history is not current per-lot ownership or real holdings. | New financial workflows need transaction rollback, concurrent/idempotent submission and independent SQL/ledger checks; **L/XL**. |
| R08 · Portfolio value, invested basis and P&L views | **Partial.** Dashboard shows estimated liquidation equity, cash, daily P&L, realized-to-date and positions. Purchases/SIP shows current pooled cost, unrealized P&L and acquisition history. No unified investment-capital/return methodology or allocation visualization. | [Dashboard](../src/trading_agent/api/static/desk.html), [portfolio UI](../src/trading_agent/api/static/portfolio.js), [portfolio service](../src/trading_agent/portfolio/service.py) | **High / P1.** Cash balance, reserved cash, pooled basis, seed and net contribution are different amounts. | Define labels/denominators and stale valuation behavior; allocation chart and performance API **L**. |
| R09 · Broker/feed/session/data warnings | **Implemented, bounded.** Separate connection and usable-quote status, quote ages and basis reviews, explicit reviewed calendar, Manual/Approval/Automatic paper gates, late-response/lock checks. | [readiness](../src/trading_agent/desk/readiness.py), [quote status](../src/trading_agent/execution/quote_status.py), [setup UI](../src/trading_agent/api/static/setup.js) | **High / preserve.** A connected socket or open calendar does not establish usable data. | Better prioritized recovery actions; modal/render acceptance follows UX audit; **M**. |
| R10 · Real execution remains disabled | **Implemented.** Settings accept only `paper`; no broker order transport in the inspected paper pipeline. Broker data retrieval is separate from local simulated execution. | [Settings.mode](../src/trading_agent/settings.py), [PaperBroker](../src/trading_agent/execution/paper_broker.py), [desk service](../src/trading_agent/desk/service.py) | **High / mandatory invariant.** Modernization must never imply enabling or authorizing real orders. | Automated negative boundary checks and review of new adapters; no live implementation in this plan. |
| R11 · Supervised intraday duplicate observation handling | **Partial; confirmed correctness defect.** The engine treats identical market values with a later receipt as a no-op, but the supervised runtime compares full Quote objects and treats the changed receipt as `QUOTE_QUALITY`, clearing its latest quote and disarming. A disposable synthetic reproduction went from armed to disarmed with no engine quality event, cash ₹25,000 and no orders. | [PaperFeed.on_quote](../src/trading_agent/paper/runtime.py), [architecture evidence](ARCHITECTURE_AUDIT.md), [deferred roadmap](INTRADAY_FUTURE_ROADMAP.md) | **Medium / P1 review.** Harmless repeated observations can unnecessarily pause the existing supervised intraday workflow. This is distinct from the ordinary delivery desk. | Narrow engine/runtime outcome contract and regression tests that preserve stale, backward and bad-book rejection; **M**. Audit records the defect only; no fix or rearm in Phase 1. |

## Requested screen coverage at 0.14.0

The requested twelve destinations should be grouped by investment tasks. A menu
label alone is not evidence that its financial workflow exists. The present
[workspace route map](../src/trading_agent/api/static/workspace.js) has seven
embedded sections plus help; it is a working foundation, not twelve completed
screens. Detailed interaction and responsive findings are in
[UX_AUDIT.md](UX_AUDIT.md).

| Requested destination | Current implementation / status | Missing work and relative complexity |
|---|---|---|
| Dashboard | **Partial:** portfolio/cash/P&L/positions first, market/feed status, warnings, next action and proposals. | Total invested capital/return definitions, allocation, benchmark, candidate and recent-decision summaries; **L**. |
| Stock Discovery | **Partial:** daily research table/shortlist under Strategies and installed research. | Dedicated searchable/filterable discovery workflow, independent watchlists, comparisons and source-aware fundamental filters; **L/XL**. |
| Stock Analysis | **Partial:** Market & Analysis read-only saved charts and screening context. | Weekly/monthly, expanded long-term indicators, comparative evidence, benchmark and fundamentals; **L/XL**. |
| Strategies | **Partial:** preparation/review/install workflow and experimental rules/optional validated model. | Explainable configurable long-horizon strategy library, safe versioned editor and comparison; **L**. |
| Backtesting | **Partial overall:** substantial CLI engines and offline reports; no main-navigation run/results workspace. | Jobs, dataset readiness, scenario configuration, equity/monthly/benchmark views, comparison and failure states; **L** reusing engines. |
| Paper Trading | **Partial:** proposals on Dashboard; order/fill/proposal history under Paper Trading. | Coherent proposals/orders/fills/positions journey and explicit idle/terminal states; **M/L**. |
| Portfolio | **Partial:** Purchases & SIP includes holdings/cost basis/acquisition history. | Dedicated allocation, income, return and concentration overview; **L**. |
| Trade History | **Partial:** combined with Paper Trading, pagination/side filter and linked decisions/fills. | Richer date/symbol/status filtering and exact export with clear result scope; **M**. |
| Risk Management | **Partial:** Risk Center contains safety plus technical controls. | Beginner policy/exposure summary, sector/cash-reserve limits and separate administration; **L**. |
| Broker & Data | **Partial:** guided six-step broker/catalog/session/feed workflow. | Prioritized troubleshooting, credential lifecycle states and reliable modal/browser acceptance; **M/L**. |
| Settings | **Partial:** combined Broker & Settings label; typed settings are principally TOML. | Safe read-only current settings first, then explicit policy-change/account identity workflows; **L**. |
| Learning Center | **Partial:** help/onboarding and extensive Markdown guides. | Searchable beginner lessons/glossary, contextual term help and mistakes/uncertainty education; **M**. |

## Existing coverage and missing acceptance evidence

Relevant tests were inspected, rather than inferred from a total test count:

- **Research causality:** [daily analysis tests](../tests/daily_research/test_daily_analysis.py)
  perturb future data, late price/basis clocks, gaps, point-in-time membership,
  split/dividend wealth and invalid input. [Daily execution tests](../tests/daily_execution/test_execution.py)
  check later fills, no fabricated liquidation, incomplete labels, coverage clocks,
  action disagreement and deterministic simultaneous ranking.
- **Validation:** [daily model tests](../tests/daily_execution/test_models.py)
  check separate namespaces, later replay, artifact tampering, independent sample
  evidence and training-only scaling; [split implementation](../src/trading_agent/ml/splits.py)
  implements whole-session purge/embargo. These are internal model diagnostics.
- **Money and recovery:** [delivery account tests](../tests/long_term/test_account.py),
  [corporate-action tests](../tests/long_term/test_corporate_actions.py),
  [contribution tests](../tests/portfolio/test_contributions.py) and
  [sequence tests](../tests/integration/test_accounting_sequences.py) cover exact
  charges/basis, independent reconstructed authority, rollback/corruption,
  partial/restart behavior, idempotency and no cash creation.
- **Analysis/UI:** [unit](../tests/unit/test_analysis.py),
  [functional](../tests/functional/test_analysis_api.py) and
  [UI tests](../tests/ui/analysis.test.cjs) cover exact SMAs, completion/availability,
  bounded/invalid data, GET side-effect absence, authorized symbols, stale/empty
  states and lock/late responses. DOM checks do not establish pixel placement.
- **CLI workflows:** [daily command tests](../tests/functional/test_daily_execution_cli.py)
  and [research command tests](../tests/functional/test_research_commands.py)
  exercise isolated output accounts and reject incompatible configurations.

Fresh Phase 1 baseline validation reported **660 Python tests and 117 UI tests
passed**, **92.1289% Python coverage**, Ruff passed and mypy passed for **98 source
files**. Resource warnings about unclosed SQLite connections occurred in the
coverage run; they require test-fixture/resource investigation and are not by
themselves proof of a production connection leak. Exact commands and execution
results are recorded in
[ARCHITECTURE_AUDIT.md](ARCHITECTURE_AUDIT.md) and
[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md). This document does not claim a
test ran merely because its source was inspected.

Missing acceptance is material: sustained genuine market-source coverage,
independent corporate-action completeness, historical point-in-time constituent
coverage, current/historical broker cost calibration, real-data out-of-sample
investment evidence, and desktop/mobile browser layout/accessibility acceptance.
Synthetic demo P&L, standalone labels and microbenchmark speed are different
evidence categories. A past short read-only broker quote probe is not a sustained
paper strategy or fill-accuracy acceptance test. No profitable strategy, live
readiness, custody correctness or physical-device acceptance follows from this audit.

## Recommended implementation order after approval

1. **P0 · Preserve authority and resolve concrete workflow defects.** Follow the
   architecture/security audit and reproduce the reported clipped connection
   confirmation in the actual scrolled workspace. Keep the confirmation, keyboard
   access and server risk checks. Prioritize the confirmed cross-year preparation
   and supervised intraday duplicate-observation defects for reviewed narrow fixes.
   Audit alone does not modify application code, even for these findings.
2. **P1 · Establish the long-term product contract.** Name the existing 20-session
   hypothesis accurately; specify months/years horizon, return/cash/basis labels,
   benchmark/data entitlements, raw versus total-return charts, and unavailable
   fundamental states. Fix contradictory legacy documentation as part of the
   approved implementation, rather than treating it as current behavior.
3. **P1 · Complete the investment journey using working components.** Group
   discovery/analysis, strategy/backtest and paper/portfolio/history; provide causal
   weekly/monthly views, transparent evidence and safe access to existing offline
   research results. Keep technical administration outside primary investment tasks.
4. **P1/P2 · Add investment analytics with a declared measurement policy.** Build
   reviewed daily valuations, benchmark alignment, CAGR/drawdown/volatility/Sharpe/
   Sortino/monthly returns/turnover only when inputs suffice; use null plus reasons
   for short or missing data. Independently verify representative outputs.
5. **P2 · Extend portfolio construction and data breadth.** Add reviewed target
   allocation/sector/cash policy and cost-aware rebalancing before any unattended
   paper allocation. Fundamentals and historical membership remain gated by their
   reliable licensed sources. No new intraday strategy work is included.

An immediate wholesale framework migration, a new real-order adapter, automatic
approval of daily basis reviews, replaying cancelled daily signals, guessed
fundamentals or invented OHLC execution paths are not necessary to close these gaps.
Existing versioned engines, accounts and safeguards should remain available while
new workflows are built incrementally.
