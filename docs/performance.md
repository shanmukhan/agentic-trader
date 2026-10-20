# Performance design and measured baseline

Run `.venv/bin/python scripts/benchmark.py --samples 2000 --output benchmark.json`.
The committed [Mac baseline](benchmark-macos.json) was generated locally on
20 October 2026 with Python 3.13.16 and SQLite 3.53.1 on ARM64 macOS.

| Path | p50 | p95 | p99 |
|---|---:|---:|---:|
| Incremental indicator update | 0.0022 ms | 0.0024 ms | 0.0028 ms |
| Quote validation + journal + risk + durable commit | 0.097 ms | 0.119 ms | 0.153 ms |

The fixture has 2,000 sequential quotes, one instrument and an empty portfolio.
These are isolated local CPU/storage measurements and exclude network transport,
market depth competition, ML, populated-account execution and Pi hardware. Results
vary with filesystem, thermal state and load. They are not a service-level promise.
Typed Quote/Candle objects are constructed before timing. The ingestion timer covers
catalog, tick, ordering/freshness checks and durable processing, and excludes Pydantic
object construction and binary socket parsing. Measure those boundaries separately
when validating an actual feed deployment.

## Why the analysis path stays small

EMA/VWAP/Wilder ATR update with constant per-candle work and bounded warmup state.
Candle builders retain only active buckets and previous cumulative volume. SQLite
indexes pending orders and uses direct symbol lookup; the gate processes a bounded
number of holdings. Model training, batch dataframe processing and research jobs do
not run in the feed process. A watchdog checks time exits independently of ticks.

The journal grows with accepted quote events and must be monitored. Reconciliation
is linear in fills at startup. Order/history views currently return all records and
are suitable for the initial pilot, not unlimited multi-year dashboards. Add cursor
pagination and an explicitly reviewed archival policy before sustained large-volume
operation. Do not silently discard audit events or downgrade `synchronous=FULL`.

## Performance gate for the next phase

Benchmark the intended device under representative symbol count, active positions,
partial fills, orders, logging, and actual broker bursts. Capture p50/p95/p99 receipt-
to-decision latency separately from broker/network time. A provisional pilot target
is local risk/commit p99 below 50 ms; measure it on Pi before adopting that target.
Alert on stale exchange timestamps rather than relying on CPU timing alone. Introduce
batching or PostgreSQL only after profiling identifies a measurable bottleneck and
atomic durability remains tested.

## Phase 2 completed-candle analysis

Run `.venv/bin/python scripts/benchmark_strategy.py --samples 2000 --output benchmark.json`.
The committed [strategy baseline](benchmark-strategy-macos.json) uses the same Mac
and patched Python, with 2,000 evaluations per hypothesis:

| Hypothesis | p50 | p95 | p99 |
|---|---:|---:|---:|
| Opening-range breakout | 0.0109 ms | 0.0118 ms | 0.0177 ms |
| VWAP continuation | 0.0105 ms | 0.0111 ms | 0.0168 ms |

It includes indicator updates, prior-volume mean, opening-range/filter checks,
candidate caps and candidate creation when triggered. Quotes/candles are prebuilt;
input decoding, disk, network, risk/accounting transactions and report writing are
excluded. It is synthetic single-symbol analysis, not end-to-end feed latency.

Rolling volume uses a bounded deque plus running sum rather than rescanning a
window. Strategy state is per symbol and resets on the next session. Event input,
decisions and equity outputs stream; final trade summaries scale with trade count.
Offline source export may scan/sort the journal and requires exclusive ownership.
Neither export nor report generation runs in the connected feed process.

## Phase 3 JSON inference and ranking

After creating `data/ml-first` with `ml-demo`, run:

```sh
.venv/bin/python scripts/benchmark_ml.py --model data/ml-first/model \
  --allow-synthetic-model --samples 10000 --output benchmark.json
```

The [ML Mac baseline](benchmark-ml-macos.json) records 10,000 observations per path
on the same ARM64 Mac with Python 3.13.16:

| Path | p50 | p95 | p99 |
|---|---:|---:|---:|
| Loaded twelve-feature score | 0.000916 ms | 0.000959 ms | 0.001167 ms |
| Score and rank ten candidates | 0.009375 ms | 0.009584 ms | 0.014375 ms |

The timer includes coefficient standardization, logistic/sigmoid math, availability
checks and sorting where applicable. It excludes feature construction, artifact
loading/verification, parsing, I/O, risk/sizing/commit, training and network. These
measurements use invented model inputs and provide no strategy-performance or Pi
latency evidence. The durable gate verifies context and recomputes probability;
that full transaction is outside the score timer.

Scoring imports no NumPy/sklearn/SciPy/joblib/pickle. Training installs optional
locked dependencies and runs separately. Label generation uses isolated durable
paper accounts and can be storage intensive; it is intentionally outside the feed
path. Sample loading is bounded at one million rows and fitting remains in memory;
partition larger research datasets explicitly rather than exhausting the device.

## Phase 4 populated paper pipeline

Run `.venv/bin/python scripts/benchmark_paper.py --samples 2000 --output benchmark.json`.
The [populated Mac baseline](benchmark-paper-macos.json) uses Python 3.13.16 and
SQLite WAL/FULL with one synthetic instrument, nineteen partial entry fills and
a nineteen-share holding during most of the timed workload:

| Path | p50 | p95 | p99 |
|---|---:|---:|---:|
| Quote/risk/accounting/performance with periodic telemetry | 0.1990 ms | 0.2279 ms | 0.4791 ms |

The timer includes supervision, valuation, durable risk/fill writes, observed
performance and periodic telemetry. It excludes object construction, socket parsing,
callback contention, history HTTP, network and actual Pi behavior. This is not
empirical fill or target-device evidence. Measure the intended universe/device
against the provisional 50 ms local processing budget.

History waits/pacing run outside the quote lock. Local signal batches still serialize
with execution; incomplete/late responses cannot generate usable entries. A concurrency
test holds HTTP open while a quote processes. The additive event-kind/time index
prevents proposal caps from scanning the quote journal. Durability is unchanged.

Runtime percentiles use the latest 512 observations per stage plus cumulative counts,
maxima and exceedances. Reports check retained local p99 and cumulative fraction
above budget; these are not global quantiles. Telemetry can miss crash observations,
and per-run observed drawdown is not a complete cross-restart equity path.
See [paper-feed.md](paper-feed.md).

## Version 0.4.1 operator/acceptance workload

The console polls one combined view every three seconds only while visible. It
reads at most 201 recent orders by reverse rowid traversal, returns 200, and caps
quote rows at ten. This avoids loading/serializing the growing full order history
at each refresh. State capture still holds the engine lock: UI polling can contend
with quote processing, so measure it with the actual target-device workload. Existing
analysis/execution algorithms and FULL/WAL settings are unchanged; no new p99 claim
is inferred from the earlier benchmark.

Preflight integrity/reconciliation can scan the fill ledger. It runs only on explicit
CLI invocation, outside quote processing and UI polls, with a one-second SQLite busy
wait and a five-second cooperative query budget. Read transactions can delay WAL
recycling and consume I/O even without SQL writes. Run outside busy entry periods;
OS/storage stalls are not hard-bounded by the SQL progress callback. A low-disk floor
is not a retention plan. See [acceptance.md](acceptance.md).

## LT1 long-term quote path (0.5.0)

The [captured Mac benchmark](benchmark-long-term-macos.json) processes 2,000 accepted
quotes while holding fourteen shares, with SQLite WAL/FULL durability:

| Path | p50 | p95 | p99 |
|---|---:|---:|---:|
| Long-term quote, review/calendar, held valuation, risk and durable checkpoints/journal | 0.1843 ms | 0.2147 ms | 0.3288 ms |

The timer excludes quote construction/parsing, callback contention, network/history
and actual Pi behavior. No durability setting was weakened. Hot-path lookups use
indexed metadata keys and bounded holdings; startup/report delivery reconstruction
scans history separately. Source/report scans can still consume I/O and are not part
of this latency claim. Reproduce with `python scripts/benchmark_long_term.py --samples
2000`; CI runs 1,000 observations and the separate synthetic long-term drills.

## LT2 quote path with unpaid dividend (0.6.0)

The [captured measurement](benchmark-corporate-actions-macos.json) uses 2,000 invented
observations, fourteen held shares and a ₹14 unpaid net dividend. Mac ARM64/Python
3.13.16, SQLite WAL/FULL: p50 **0.2003 ms**, p95 **0.2297 ms**, p99 **0.2564 ms**,
maximum **0.6823 ms**. This is a separate local sample, not proof of improvement or
an external service-level guarantee. It excludes object construction, parsing,
callback contention, network/history, action application/reconstruction and Pi.

```sh
.venv/bin/python scripts/benchmark_long_term.py --samples 2000 --corporate-actions
```

Offline action/receipt review and startup reconciliation may scan history; they do
not run inside quote callbacks. Snapshots read two atomic primary-key caches for
known receivable/unknown-fraction count. A SQL-trace test verifies that snapshot
polling does not scan financial/event/action history. Durability was not relaxed.

## LT3a end-to-end daily screen (0.7.0)

[Captured Mac measurement](benchmark-daily-research-macos.json): thirty runs of
538 bars, six symbols and ninety declared sessions; p50 **8.0033 ms**, p95
**15.2105 ms**, maximum/p99 **20.4069 ms**. Includes loading, strict validation,
universe/basis checks, rolling calculations/ranking and input/Python hashes. Excludes
fixture creation, HTML writing, network/history, execution and actual Pi. The small
fixture is not a large-universe or connected-feed latency guarantee.

```sh
.venv/bin/python scripts/benchmark_daily.py --samples 30
```

The engine streams bars with bounded per-symbol rolling state and binary-search
membership checks. It runs outside the connected quote process. Its gross analytical
returns are descriptive and have no execution authority.
