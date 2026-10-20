# Architecture and invariants

The application is a Python 3.13 modular monolith. `main.py` owns startup, CLI and
shutdown. HTTP/WebSocket market data flows through `broker/readonly_kite.py`, typed
models, the paper risk/execution boundary and SQLite. Stream candles are persisted
separately after quote processing. Candle-write failure latches a fault and disconnects
the feed. The default service accepts operator intents. Phase 4 additionally binds
a dedicated account to explicitly configured rules/model and supervised entry controls.
Phases 2–3 retain isolated offline research.

```mermaid
flowchart LR
  K[Kite read-only HTTP / quotes] --> V[Validation and instrument catalog]
  V --> P[Paper broker / independent risk checks]
  V --> C[1m / 5m candles]
  C --> F[Incremental features for research]
  A[Authenticated paper intent] --> P
  P --> S[(SQLite WAL and audit journal)]
  C --> S
  S --> D[Loopback dashboard]
  W[One-second watchdog] --> P
```

## Trust and time

Execution has no reference to a network broker client. The HTTP transport maps
explicit route/method pairs to fixed Kite HTTPS URLs. Its sole permitted POST is
manual authentication at `/session/token`. The WebSocket worker sends only subscribe
and full-mode messages. TLS verification is enabled; environment HTTP proxies and
HTTP redirects are disabled. The official order-capable SDK is not installed.

Public timestamps require an explicit timezone, normalize to UTC, and serialize with
microseconds. NSE full-mode epoch timestamps are decoded directly in UTC, independent
of host timezone. Session decisions convert to Asia/Kolkata. No weekday-only holiday
heuristic exists; a reviewed date allowlist is required. Replay injects every clock.

## Ownership, transactions and recovery

A nonblocking `flock` locks the account for its owning process. One Uvicorn worker
is supported. Inside that process an `RLock` serializes feed, watchdog and API access,
and SQLite uses `BEGIN IMMEDIATE`, WAL, foreign keys and `synchronous=FULL`. A paper
fill, position/cash update, fees, order state and audit events share one transaction.
An I/O failure rolls the transaction back and latches an in-memory fault; the process
requires verified restart. A durable kill is stored separately and survives restart.

Schema version 1 creates metadata, instruments, latest quotes, candles, orders,
fills, positions and ordered journal events. Candidate/risk records are journal
events rather than duplicate tables. Orders materialize cash/risk reservations;
positions materialize cost basis. Account snapshots are derived transactionally
from these records. Unknown schema versions and missing required metadata fail closed.
Later migrations must be explicit and preserve the fill ledger; there is no destructive
automatic migration or balance reset.

Startup reconstructs cash, quantity, cost basis, fees and realized P&L from fills and
compares them to the materialized account. It validates order fill totals, turnover,
fees and reservations before accepting work. Pending orders are conservatively
cancelled on startup, then required exits are re-created after reconciliation.
Exit identities include a durable journal sequence, so cancelling and reissuing an
exit at the same timestamp cannot collide or duplicate a fill.
This intentionally strengthens the plan's ambiguous instruction to recover pending
orders: a restarted process never silently continues an old entry decision.
Risk-policy hash mismatches require a separate account. Broker connectivity and
quote trust are never restored from disk.

## Data and performance

Instrument mapping uses `NSE:symbol` identity plus unique token and tick size.
Conflicting remaps are rejected. Quotes validate depth, tick grid, positivity,
timestamp order, cumulative volume and age. Repeated identical quotes have no effect;
conflicting same-time or out-of-order quotes block the symbol until a valid later one.
The packet timestamp has second resolution, so multiple changed packets in the same
second are conservatively rejected. This trades some data completeness for safety;
it is unsuitable for tick-level strategy research.

Builders retain one active candle and prior quote per instrument/timeframe. They do
not emit an active candle until the next interval/watermark. Initial volume is unknown;
missing intervals are flagged. Volume deltas across boundary ticks are assigned to
the new bucket; exact exchange OHLCV should use verified historical candles. A stream
disconnect clears builders, preventing outage-spanning candles from looking complete.
Indicators reject incomplete/flagged/gapped input, use session-local VWAP, EMA and
Wilder ATR, and reset on the next local date. Supervised feed signals use completed
historical bars in Phase 4; optional models add an independent execution gate.

Journal growth is linear in accepted quote events. Current records have indexed
lookups and at most ten streaming instruments and two held positions by default.
Reconciliation scans fills on startup, not on each tick. See [performance.md](performance.md).

## Phase 2 isolated research

`strategy/rules.py` maintains one bounded state per symbol: completed-candle
indicators, a prior-volume deque/sum, fixed opening range and per-session candidate
count. Hypothesis settings are immutable and hashed. Rule code has no broker client
or execution reference; it returns a candidate and explanatory feature/filter record.
All accepted candidates still pass the same independent transactional risk engine.

`backtesting/dataset.py` validates a raw-price manifest and bounded chronological
JSONL stream. Candle availability cannot precede its close; quote availability
cannot precede exchange/receipt time. Source files are hashed before processing and
verified afterward. Candidate injection, unknown symbols/tokens/dates and external
bundle paths are rejected. The input reader does not create an OHLC execution path.

`backtesting/runner.py` injects event time into an isolated paper account, journals
strategy evaluations, submits candidates and writes observations incrementally.
No service-account engine, broker API or wall-clock strategy timing is used. The
report records runtime, rule/config/policy/code/input/journal identities. Net trade
statistics derive from the fill ledger and combine partial exits until a position
is flat. Open positions are preserved and make results incomplete.

`backtesting/export.py` opens source storage without invoking `PaperBroker`, avoiding
restart cancellation. It merges quote journal and completed candles into a new
bundle, retains calendar provenance and labels replay/mixed origins synthetic.
An external verified candle file can replace research candle inputs without changing
the source ledger. Manifests are written last, so failed exports are not loadable.
The offline exporter may sort/scan substantial data; it is not run on the feed path.

`main.py` exposes separate research commands. Default services retain operator
intents; dedicated supervised services are described below. No existing economic
policy-hash encoding changed.

## Phase 3 labels, fitting and inference

`ml/labeling.py` streams causal candidates into bounded independent paper trials.
Each uses real sizing/fill/fee code and later quotes; interrupted, unfilled or
unresolved outcomes are censored. Its deadline is known at entry and queues an exit
before reading later prices. Audit records precede temporary-account cleanup. The
source, settings, code, sample file and audit are preserved in a completion manifest.

`ml/splits.py` groups whole IST sessions in expanding windows and purges label
intervals across calibration/evaluation boundaries with a time embargo. Offline
`ml/training.py` fits train-only scaling/logistic coefficients and a later independent
sigmoid calibrator. Final coefficients freeze before final holdout metrics are
computed. Diagnostics and gates are stored with the model; availability follows the
latest validation label, session close or source observation plus embargo, protecting
later replay from approval leakage.

`ml/inference.py` loads bounded, hash-verified JSON coefficients and performs pure
Python math. `ml/validation.py` checks report identities, windows, calibration bins,
metric gates and availability without importing training dependencies. Candidate
fingerprints bind features to economic intent. Artifacts never execute pickle or
joblib. A failed gate rejects loading; synthetic overrides only relax provenance.

The scored runner buffers candidates at one availability timestamp, scores/sorts
with deterministic tie breaks and submits before the next timestamp. `PaperBroker`
checks model identity, feature context, cutoff and threshold independently, then
applies the existing risk/sizing/reservation boundary. Model IDs persist in metadata
so a restart cannot remove that account's gate. Rule-only runs retain their original
immediate submission behavior. Model decisions, vectors and scores are auditable.

No new database schema or live endpoint is needed. The shared policy fingerprint
preserves the original economic hash encoding. Heavy dependencies are optional
training extras; connected runtime imports no training code. See [ml-research.md](ml-research.md).

## Phase 4 supervised feed pipeline

`paper/runtime.py` serializes quote processing, history evaluation, supervision and
watchdog actions using the existing engine lock. It starts disarmed, warms from
current-session history with `ENTRIES_DISABLED`, requires every reviewed symbol to
be ready, then ranks one observed candle batch before independent risk admission.
Missing/stale/invalid input disarms and cancels pending buys. Stale holdings or
disconnects queue durable kill exits; later valid quotes still supply fills.

`paper/service.py` isolates paced history HTTP from the quote callback and execution
lock. Full current-session five-minute responses are validated before evaluation.
The last-completed boundary and connection generation reject incomplete or obsolete
work. Active stream bars are not mixed into authoritative signal history. Protective
execution continues while history waits. Monotonic request spacing respects the
configured broker budget; late candle signals are skipped instead of backdated.

Dedicated metadata binds runtime/rule version, complete strategy/feed policy, catalog,
model and synthetic mode. Used session definitions are pinned by date. The broker
checks automation identity before restart cancellation and requires the controller
on new submissions. Manual startup or changed policy cannot remove the gate.
`paper-init` binds a new account without assigning a conflicting manual model identity.
Proposal caps derive from durable indexed events, including rejected proposals.

Bounded timing rings retain 512 observations per stage plus cumulative counts/maxima/
budget exceedances. Periodic telemetry journals capture timings and observed per-run
equity/drawdown; missing crash samples are disclosed. `paper/report.py` reads storage
without broker recovery and derives net trades, incidents and preliminary gates.
It cannot attest real hardware or enable live execution.

Schema v1 gains the compatible additive `events_kind_time` index, preventing proposal
lookups from scanning quote history. It changes no ledger or economic-policy hash.
See [paper-feed.md](paper-feed.md) for operations and measurement limits.
Supervised source export also preserves first candle observation clocks and recorded
connection changes. Delayed bars sort by actual availability, missing clocks fail,
and unclocked external overrides are refused; manual-source close assumptions remain
explicitly separate.

## Responsive supervision and local diagnostics (0.4.1)

The UI is plain packaged HTML/CSS/JavaScript under `api/static`, with no Node build,
external asset fetch, browser token persistence or client financial calculations.
`api/console.py` captures a combined account/orders/quote/automation view under the
engine lock; separate transactions for automation status avoid nesting. The orders
query uses reverse rowid traversal with a 201-row bound and returns at most 200;
quotes are bounded at ten. Existing full-history API behavior remains unchanged.
UI polling performs no recovery, arming, journal write or integrity scan. Transport
staleness is visible and blocks entry-enabling UI controls while the independent
server watchdog remains responsible for actual risk handling.

`observability/preflight.py` is a separate on-demand read path. It opens the existing
account with SQLite `mode=ro`, query-only and ordinary WAL locks, takes a coherent
read transaction and reuses the SELECT-only ledger reconciliation routine. It does
not instantiate the owning Database/PaperBroker. A progress deadline bounds normal
SQL work; raw failure details/secrets are not emitted. Local environment/storage/
identity checks and private evidence are distinct from unverified external broker/
device acceptance. See [acceptance.md](acceptance.md) and
[operator-console.md](operator-console.md).
