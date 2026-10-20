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
