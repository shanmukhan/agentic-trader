# Test and validation plan

All automated tests use virtual capital and synthetic or mocked market data.
No broker credentials, real orders or funds are used. Run from the repository root:

Phase 1 local result (20 October 2026): **108 passed; 90% reported coverage**.
The latest combined validation is recorded in [CHANGELOG.md](CHANGELOG.md).

```sh
.venv/bin/pytest --cov=trading_agent --cov-report=term-missing
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy src/trading_agent
.venv/bin/python scripts/check_secrets.py
.venv/bin/pip-audit --skip-editable
.venv/bin/python scripts/benchmark.py
.venv/bin/python scripts/benchmark_strategy.py
.venv/bin/python scripts/benchmark_ml.py --model data/ml-first/model --allow-synthetic-model
```

## Coverage matrix

| Suite | Evidence required |
|---|---|
| Unit models/config | Non-paper modes, public listener, invalid times/prices/size, NaN, unknown fields, naive timestamps |
| Unit costs/sizing | Independently calculated fees, adverse tick rounding, fee-inclusive maximum size, zero capacity, unattractive targets |
| Unit candles/features | Cumulative-volume deltas, incomplete/initial/gapped candles, monotonic data, VWAP/EMA/ATR hand calculations, session reset |
| Unit broker | Sanitized profiles, cash catalog filtering, completed history/gaps, auth checksum and route allowlist, binary depth/UTC decoding |
| Integration execution | Cash/risk reservations, partial fills, cumulative fees, cancel/stop/target/gap behavior, liquidity consumption, duplicate intents/quotes |
| Integration risk | Session/early-close boundaries, spread/stale/feed/model rejection, notional/position limits, daily mark-to-market loss and streak gates |
| Integration persistence | Exclusive account owner, rollback after fill on disk-full, policy mismatch, startup reconciliation, missing/corrupt state, private backup/restore |
| Functional API/CLI | Credential-free startup, authenticated entry→fill→kill→exit→reset, CSRF/Host boundaries, no live route, demo artifacts and mode guard |
| Replay | Identical events/config produce identical fills, balances and journal digest; invalid clocks/types fail |
| Security | Forbidden broker operations never reach transport, secret redaction, limited working-tree secret patterns, audited locked dependencies |
| Performance | Reproducible indicator and quote/journal/risk timings, preserving FULL durability |

`.github/workflows/ci.yml` repeats checks on Ubuntu with patched Python and the frozen
lock. CI is configured but has not been run on a remote service in this workspace.
Ruff and mypy cover application code. Tests exercise financial outcomes rather than
only checking implementation-shaped return values. Coverage reports expose untested
deployment/broker branches; no external acceptance is inferred from coverage alone.

The persistence suite includes actual child-process death before commit, not only
an exception mock. A seeded thirty-round-trip sequence combines partial buys,
residual cancellations, partial sells, same-time exit reissues and reconciliation
after each completed position to exercise monetary conservation across operations.

## Phase 2 automated acceptance

The added suite tests ORB/VWAP triggers and their distinct pullback requirements;
completed-candle warmup; prior-only volume/range features; session resets and missing
opening data; stale/missing/wide/empty quotes; independent risk rejection; future
quote prefix invariance; strict later-tick execution with zero latency; and absence
of fabricated OHLC fills or end-of-data closes.

Dataset tests cover chronological and availability clocks, restricted raw basis and
paths, input mutation, bounded reads, schema/field errors and rejected symlinks.
Export tests verify original orders/journal are unchanged, calendar provenance and
synthetic classification survive, overrides work and failed exports lack manifests.
Metric tests verify observed peak drawdown, net fees, null no-trade/no-loss ratios
and one completed trade across partial fills. Functional CLI tests generate/re-run
reports deterministically and preserve source orders during export. The strategy
benchmark records analysis-only latency separately from the existing ingestion path.

No real-market profitability or walk-forward ML acceptance is inferred from these
tests. Reports retain incomplete exposure and research evidence gaps.

## Phase 3 automated acceptance

The ML unit/integration suite covers finite fixed-schema feature construction,
candidate identity, future/incomplete/missing input rejection, actual fee-inclusive
labels, later-tick fills, stops/targets, partial quantities, horizon exits and
separate censor outcomes for interruptions, quote gaps/quality, flagged candles,
unfilled entries and unresolved exposure. Failed builds lack completion manifests.

Split tests exercise whole-session grouping across simultaneous symbols, expanding
windows, final holdout exclusion from all fits, crossing label intervals and strict
embargo equality. Model tests prove scaling/base coefficients use training only,
calibration labels affect only the calibrator, holdout changes cannot affect fitting,
and final coefficients exist before holdout metrics are computed. Insufficient or
single-class samples fail, and reliability/gate diagnostics remain inspectable.

Artifact tests reject corruption, missing manifests, NaN, wrong dimensions/scales,
feature schema changes, inconsistent reports, oversized files, symlinks, failed
metrics, wrong config/fees and future validation cutoffs. A fresh-process check
proves model loading imports no NumPy, SciPy, sklearn, joblib or pickle.

Scored research tests verify deterministic results and same-time ranking before
independent position gates; later prices cannot change earlier scores. Risk tests
exercise missing/unscored/wrong-model/changed-candidate vectors, idempotency conflicts,
unchanged sizing, kill/position gates, durable model binding and missing metadata
failure before pending-order recovery. Functional CLI tests run label→train→score,
check artifacts and confirm the service database is never opened. Wrong mode and
invalid command/override failures remain sanitized.

CI includes the synthetic workflow and inference/ranking benchmark. All performance
timers state their excluded work. Real-market model performance and full Pi/feed
acceptance remain unverified; a synthetic diagnostic pass cannot establish either.

Final combined local result on 20 October 2026: **215 passed; 93% overall coverage**.
There are 56 added Phase 3 cases. Feature/schema modules reached 100%, training and
sample validation 99%, inference 97%, labeling 94% and report validation 91% statement
coverage. Ruff, formatting, mypy, secret-pattern/Markdown-link checks, frozen lock,
offline builds and dependency audit passed. See [CHANGELOG.md](CHANGELOG.md).
Availability tests also cover the complete validation session and delayed source
observations after the last labeled trade.

## Manual external acceptance

Before claiming deployed Phase 1 readiness, complete a real manual login and read-only
profile/history/stream check, inspect the current NSE calendar and broker entitlement,
install the service under a dedicated user, reboot, exercise network interruption,
measure target-device latency with positions, and rehearse backup/power recovery.
Record dates, OS/architecture, policy/code revision, fee version and artifacts.
These checks need real hardware/account access and remain explicitly unverified.

The final local command results and any limitations are recorded in
[CHANGELOG.md](CHANGELOG.md). A dependency scan is checked at implementation time;
repeat it before deployment and every dependency update.
