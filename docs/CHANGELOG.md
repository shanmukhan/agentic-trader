# Change log

## 2026-10-20 — Phase 3 chronological ML research (0.3.0)

Added a versioned twelve-feature causal schema with finite values, completed-time
and instrument checks, and a normalized fingerprint binding economic candidate
identity. Labels use independent standalone paper accounts with existing fee-aware
risk sizing, depth, partial fills, tick rounding and later-quote latency. Predeclared
time barriers queue exits before reading subsequent prices; intervals end at actual
last fills. Unfilled, unresolved, interrupted and bad/gapped paths are censored and
audited rather than converted into negative targets or forced closes.

Added hash-verified sample bundles preserving source manifests, full strategy and
economic settings, label policy, sessions, code identity, counts and execution audit.
Readers validate bounded local paths/records, uniqueness, universe/session context,
outcome-count consistency and immutable inputs. Completion manifests are written
last. Labeling uses temporary independent accounts plus a retained quote observer;
it never opens or changes the configured service account.

Added whole-session expanding walk-forward splits with timestamp-interval purging
and strict embargo, train-only scaling/logistic fitting, disjoint later regularized
sigmoid calibration, and a final holdout inspected after coefficients freeze. Fixed
settings replace parameter search. Diagnostics include ROC-AUC, Brier/log loss,
training-prevalence baseline, reliability/ECE, selected counts and net counterfactual
P&L. Insufficient fitting data fails; failed evaluation models retain diagnostics
and cannot load. Model availability follows the latest final validation label,
declared session close or source observation, plus embargo.

Added bounded JSON-only artifacts and a lightweight pure-Python loader/scorer.
The loader checks hashes, schema/order/dimensions, finite math, report identities,
split windows, reliability consistency, derived acceptance gates and contextual
strategy/policy/fee matching. No pickle or joblib is loaded. Synthetic override
relaxes provenance only, requires all metric gates, and only scores synthetic data.
Integrity hashes do not authenticate a maliciously rewritten local bundle.

Added same-availability-time probability ranking before independent risk admission.
The paper broker rechecks feature/candidate/model context, availability and threshold;
all previous sizing, cash, loss, position, freshness and kill gates remain in force.
Vector changes conflict under an existing intent. Model version/schema metadata
prevents silent gate removal on restart; missing metadata fails before cancelling
pending orders. The original economic-policy hash encoding is preserved. No database
schema migration, live route, network execution adapter or connected automation was added.

Added `ml-build`, `ml-train`, `ml-demo` and `backtest --model`, separate real/synthetic
training policies, optional locked training dependencies, CI steps and a scoring/ranking
benchmark. The Pi setup now installs only broker/runtime extras. Updated the supplied
specification, implementation plan and corresponding architecture, risk, security,
API, runbook, performance, test and usage Markdown; added the detailed ML usage guide.

### Phase 3 validation

- **215 tests passed**, including all 159 previous regressions and 56 added unit,
  integration and functional cases. Reported coverage: **93% overall**, features/schema
  **100%**, training/samples **99%**, inference **97%**, labeling **94%**,
  validation diagnostics **91%** and independent paper execution **93%**.
- Ruff lint/format, mypy, working-tree secret-pattern checks, local Markdown links,
  frozen lock verification and offline wheel/source builds for **0.3.0** passed.
- Current installed dependency audit: **no known vulnerabilities**, no ignored
  advisory. Optional NumPy 2.5.4 / scikit-learn 1.9.1 dependencies are hashed in the
  lock. A fresh-process test confirms loading imports no heavy training/persistence stack.
- The synthetic functional workflow labels sixty candidates (30 per class), passes
  invented walk-forward/holdout diagnostics, and correctly fails `non_synthetic`.
  Ten subsequent sessions remain outside training and validation. Their rule/scored
  portfolio results are reproducible and documented as invented software fixtures.
- The original service account passed integrity/accounting checks and remains flat
  at **₹25,000.00**, with zero fees, zero reservations and no feed connection.
- The 10,000-observation Mac benchmark measured score p99 **0.0012 ms** and ten-candidate
  score/rank p99 **0.0144 ms**. These exclude feature creation, parsing, artifact I/O,
  risk/commit, training and network. Durable quote-path recheck measured p99 **0.156 ms**
  in the existing empty-portfolio fixture; no durability setting was weakened.

No model has been empirically accepted on real market data. Quote density, exclusions,
historical fees, corporate actions, selection bias, actual broker access, Pi operations
and connected paper-feed validation remain external acceptance work. Synthetic passes
and small local latency measurements do not establish profitability or live readiness.

## 2026-10-20 — Phase 2 strategy research (0.2.0)

Added immutable, versioned ORB and VWAP-continuation rule settings and independent
per-symbol/session state. Signals use completed contiguous 5m candles, session VWAP,
rising EMA, Wilder ATR, prior-only relative volume, turnover/price/spread/freshness
filters, ATR stops/targets and a per-session candidate cap. Candidates still pass
the existing cost-aware risk engine; connected-feed strategy automation is deferred.

Added streaming typed raw-price dataset bundles with reviewed sessions, provenance,
availability/chronology checks, restricted paths, bounded reads, synthetic labels,
input hashes and post-run mutation checks. Added a source-preserving exporter that
retains calendar references, accepts verified candle overrides and never runs source
order recovery. Failed exports leave no loadable manifest.

Added isolated quote-driven backtesting and `backtest`, `research-demo`,
`export-research` commands. No OHLC tick path or signal-close fill is invented.
Even zero latency requires a strictly later exchange quote. Research accounts retain
unfinished positions/orders and report gaps/stale valuations as incomplete. Outputs
include decision explanations, equity CSV, completed net-trade statistics, observed
drawdown, fill/accounting journals, reproducibility hashes and runtime versions.

The synthetic two-session fixture contains a winner and loser: final cash ₹24,974.03,
estimated fees ₹20.27 and net P&L −₹25.97 under defaults. It does not establish
profitability. Historical fee matching, queue/impact effects, sparse observations
and incomplete connection history remain disclosed research limitations.

Added leakage, metric, provenance, failed-input/export and source-order isolation
tests, CLI functional checks, a constant-work strategy benchmark, CI coverage of that
benchmark and detailed corresponding architecture/API/risk/security/runbook/usage
documentation. Updated the specification/implementation plan and package to 0.2.0.
No runtime dependency or schema migration was introduced.

### Phase 2 validation

- **159 tests passed**, including the entire Phase 1 regression suite and 51 added
  strategy/data/export/metrics/CLI/causality cases. Reported coverage is **91% overall**,
  **95% rule strategies**, **94% dataset validation**, **95% export**, and **99% metrics/reporting**.
- Ruff lint/format, mypy, working-tree secret-pattern check and local Markdown links
  passed. Wheel and source distribution builds for **0.2.0** succeeded offline.
- Final installed dependency audit found **no known vulnerabilities**; no advisories
  were suppressed and runtime dependencies did not change.
- The functional research demo completed both net-positive and net-negative trades.
  The service paper account remained flat at **₹25,000.00** and passed integrity and
  accounting verification.

The 2,000-evaluation benchmark measured p99 ORB **0.0177 ms**, VWAP **0.0168 ms** on
this Mac. It excludes input construction/decoding, disk, network and execution.
Real-market performance, actual Kite access, Pi deployment and ML remain unverified.

## 2026-10-20 — Initial paper platform

Initialized Git on `main` and implemented the Phase 1 paper-only plan from the supplied
specification. Added Python 3.13.16 environment metadata, exact hashed dependency lock,
package entry point, safe config/secret examples, local private runtime, setup scripts
and Git exclusions for credentials, environments, logs and trading artifacts.

Added validated domain types, Decimal money, UTC/IST separation, reviewed session
calendar, read-only HTTP authentication/profile/catalog/history, strict full-mode
equity WebSocket decoder and bounded reconnection. Removed the initially evaluated
official SDK after its pinned transport failed the vulnerability scan; implemented
the limited official protocol with audited transports and documented the deviation.

Added SQLite schema v1, WAL/FULL durability, exclusive ownership, atomic journal,
idempotent intent fingerprints, accounting reconstruction, paper cash/positions,
cost-aware risk sizing/reservations, latency/depth/partial fills, cumulative fees,
daily/streak/stop/target/session risk gates, persistent kill and conservative restart
recovery. Added credential-free health, entry readiness, authenticated operator API,
Origin/Host/security headers, local dashboard and redacted rotating diagnostics.

Added incremental candle/feature infrastructure, explicit unavailable ML stub,
deterministic replay/demo reports, backup verification, deployment templates, CI,
unit/integration/functional/replay/security checks, secret-pattern check and benchmark.
Updated the specification and corresponding architecture, risk, security, API, test,
performance, usage and operator documentation. Later strategy/ML/live phases remain
gated as described in the implementation plan.

### Local validation record

- **108 tests passed**, including unit, integration, functional CLI/API, replay,
  security, real process-death recovery and seeded partial-execution sequences.
- Coverage reported **90% overall**, **93% paper execution**, and **100% costs/sizing**.
- Ruff lint/format, mypy, project secret-pattern check, shell syntax and launchd plist
  validation passed. All local Markdown links resolve.
- Final dependency scan: **no known vulnerabilities**; the editable local project
  itself is not a PyPI advisory target. No advisories were suppressed.
- Frozen/offline environment sync, source distribution and wheel build succeeded;
  the build backend is pinned to Hatchling 1.32.4.
- The real default paper database was initialized at exactly **₹25,000.00** and
  passed integrity/accounting verification. It is ignored by Git and has no holdings.
- The committed 2,000-event Mac benchmark records p99 indicator update **0.0028 ms**
  and quote ingestion/journal/risk/durable commit **0.153 ms**. Typed model construction,
  network, populated-account execution and ML are outside these timer boundaries.

The final pass also normalized financial/time formatting in idempotency fingerprints,
added durable sequence numbers to same-time exit reissues, strengthened persisted
reservation/fee/policy validation, and checked generic error redaction for headers
and JSON-shaped messages. Corresponding regression tests and component docs were updated.

No actual Kite credentials, broker subscription purchase, live order, host-wide
service installation or Raspberry Pi hardware test was performed. Functional broker
tests use controlled transport responses. Configured remote CI has not executed here.
