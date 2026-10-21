# Test and validation plan

## After-hours transport regression coverage (0.11.1)

Unit cases independently zero best bid/ask prices and quantities, preserve a second
usable instrument in a mixed batch, and retain rejection of unknown tokens/trailing
corruption. Bounded retry tests verify ten failures/nine waits, final failed/stopped
states, snapshot isolation and fixed timeout codes without exception details. Existing
invalid-packet/broker-error tests verify safe failure classification. Functional HTTP
coverage runs the actual worker against a mocked full packet while an order is pending:
connection stays online, ignored-book count advances, no symbol becomes fresh, and
persisted order/cash/fee/reservation/position state remains unchanged. UI tests distinguish
connected transport from usable depth and give retry-exhaustion recovery without exposing
unknown error text. Prior-depth invalidation/recovery tests prove a new entry is rejected
immediately despite the earlier quote's age, then permitted only after accepted valid
data. Service tests prove immediate intraday disarm while remaining connected and no
automatic rearm after recovery. Full validation: **547 Python / 56 JS tests**, **93% coverage**.

Separately, an actual diagnostic-only broker check after market hours verified HTTP 200
profile, successful WebSocket handshake and the original zero-sided packet failure.
The corrected worker stayed connected for 15 seconds with five ignored books and zero
usable quotes. No callback entered the user's account; no order, review or arming occurred.
This brief observation does not establish fresh-market/fill or full-session acceptance.

## Shared menu coverage (0.11.0)

Functional checks cover authenticated read-only workspace metadata, actual manual
versus bound intraday cadence, public shell privacy, explicit framing allowlist and
unchanged account state. Launcher tests refuse older UI versions as well as mismatched
accounts. UI tests verify no private fetch before unlock, one unlock across menu
changes, exact origin/window/active-view token handoff, hostile hash rejection,
mutation/dialog navigation guards, global lock/authorization-failure propagation,
late-response suppression and preserved broker callback behavior. An integration
test uses the real Setup controller with the workspace bridge to prove shared unlock
does not falsely lock the parent. Physical-browser layout/phone acceptance remains
distinct from these DOM and HTTP checks.

## Browser setup coverage (0.10.0)

Unit and functional tests cover operator/Origin authorization, bounded secret bodies
without validation echoes, redacted upstream failures, private atomic credential
files and symlink/permission refusal, login state expiry/replay, persisted catalog
selection, pending-order/held-symbol guards, unchanged economic identity and exact
cash/fees/orders/positions. Calendar tests require strict review, preserve existing
definitions, verify idempotence and keep live/configured calendars unchanged on a
save failure. Feed callback tests receive synthetic quotes without creating orders
and latch candle-storage faults. The launcher probes only the correct account,
rejects redirects/mismatches and starts another process only after connection refusal.

JavaScript tests exercise locked/private state, credential clearing before awaits,
late-response suppression, callback origin/window/state binding, one-time explicit
exchange, safe text rendering and confirmation/cancellation for symbols, calendar
and feed changes. Legacy manual callback capture remains covered. Real broker login
and 2FA are not automated, and no phone/pixel acceptance is inferred from DOM tests.

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

## Phase 4 automated acceptance

Added supervised startup/arming/history readiness, disabled-entry backfill, causal
later-quote fills, history deduplication, independent risk rejection, manual-controller
bypass refusal and ranked multi-symbol position admission tests. Interruption cases
cover disconnect, watchdog silence, first resumed quote without an intervening tick,
conflicting/volume-regressed data and stale exchanges. Holdings stay open until valid
liquidation data returns; kills persist.

History tests cover missing/flagged/future/revised/foreign-symbol candles, model age,
synthetic connected-model rejection, calendar/cutoff changes, clock regression and
storage failure. Restart tests preserve pending entries during identity rejection,
then verify cancellation and disarmed rewarm under the correct controller. Concurrency,
connection generations, retry cadence, first-bar request ranges, monotonic rate pacing
and worker shutdown are tested.

Functional API cases verify authenticated arm/disarm, Origin protections, readiness
without nested transactions, manual-intent rejection, kill/reset independence and
background stale-feed disarming. CLI cases exercise model-bound initialization,
option requirements, source-preserving reports and all four synthetic fault drills.
Metrics tests verify bounded windows and cumulative budget counts. Reports reconcile
money and retain unfinished exposure and crash limitations.

Combined local result: **259 tests passed; 92% coverage**. Paper runtime reached 91%,
service 90%, reports/demo 93%, metrics 100%, independent execution 93%. These use
invented data or mocked read-only broker responses and do not establish feed access,
empirical fills, full-session coverage, hardware recovery or live readiness. CI runs
the drills and populated-account benchmark.
Additional cases preserve observed candle receipt/connection clocks on export,
reject missing clocks/overrides, and cancel pending buys at model-age expiry.

## Version 0.4.1 console and acceptance tooling

Combined local result: **284 Python cases and 13 JavaScript cases passed**. Python
statement coverage is **92% overall**, preflight **97%**, combined console view **93%**,
API **90%** and independent execution **93%**. There are 25 new Python cases covering
running WAL account inspection without cancellation/events, missing source paths,
unknown sessions, official SQLite fix branches, policy/permission/low-disk failures,
corrupt/missing state, schema refusal, query budgets, symlinks, private/exclusive
hashed artifacts and failed output without a finished manifest. Functional API/CLI
cases exercise authentication, bounded history, feed/kill/stale diagnostics, disarmed
polling, security headers/assets, missing-account diagnostics and strict exit codes.

Run the dependency-free browser logic suite with Node 24:

```sh
node --test tests/ui/console.test.cjs
```

It tests exact decimal/rupee display, locked shell and text-only injection handling,
late responses after lock, six-second display staleness, arm/reset confirmations,
post-action/poll ordering, auth failures, visible-tab polling, overlap suppression,
immediate kill messaging, unknown timeout outcomes and server reset rejection.
These tests execute application JavaScript using a minimal DOM harness; they are
not browser rendering, accessibility certification or physical touch acceptance.
Node is for tests only and is not a runtime frontend dependency. CI includes the
same Node suite alongside Python checks; remote CI was not run here.

Desktop Safari was visually checked with an isolated virtual account: account/readiness
cards, lock/unlock and kill/reset dialog behavior. The preview returned flat at
₹25,000 with kill inactive. Small-screen visual/real handset verification remains
pending: browser automation did not yield reliable mobile evidence. The source/wheel
build contains all three UI assets and loads them outside the repository. Original
account read-only preflight reconciled cash ₹25,000.00 with no holdings/pending orders;
operator-token configuration is correctly blocked in the unconfigured shell.

## Long-term LT1 automated and local acceptance (0.5.0)

Combined local result: **328 Python tests and 17 JavaScript tests passed**; **92% Python
coverage**. The 44 added Python cases cover overnight/weekend retention, required and
strict/idempotent reviews, persistent quarantine, changed price rejection, opening-gap
loss accounting, cross-day high-water/drawdown, same-day and cross-day partial DP,
exit cancellation/restart latches, horizon/config/model refusal before recovery,
fee cash shortfall, rollback, corruption/missing metadata/journal, held feed coverage,
current API/Origin/auth behavior, source-preserving private hashed reports, horizon/
cost preflight and isolated CLI drills/refusals. Intraday and ML regressions pass.

Long-term policy coverage: **96%**; delivery reconstruction **93%**; charges **100%**;
independent paper broker **93%**; long-term demo **90%**, report **92%**; API **91%**.
The JavaScript suite adds four cases for horizon/review fields and clearing, explicit
quarantine confirmation, typed symbol-only holding exits and stale-review blocking.
A populated 2,000-quote Mac benchmark measured long-term p99 **0.3288 ms**, excluding
network/parsing/contention/history/Pi, with WAL/FULL preserved.

Desktop Safari displayed the long-term horizon, virtual account/buffer, blocked
readiness and review form in an isolated flat/no-feed account. No market-data session,
real order or custody action was attempted. Mobile/actual-device acceptance remains
pending. Original-account read-only checks and final quality/build/audit results are
recorded in [CHANGELOG.md](CHANGELOG.md). See [long-term.md](long-term.md) for exact
supported behavior and the still-missing adjustment/research/settlement milestones.

## LT2 corporate-action validation (0.6.0)

Current combined result: **387 Python tests, 19 JavaScript tests, 92% Python coverage**.
New tests cover integral split/bonus and conservative tick levels, unchanged basis,
ordered split/bonus/dividend quantities, nonspendable net entitlements, exact and
zero receipts, whole-share sale before payment, retained rational fractional claims,
separate income/capital P&L and idempotent retries. Failure cases include ambiguous/
oversized/symlink input, strict flags/ratios, future dates, conflicting IDs, duplicate
payment, accepted ex-date quotes, fractional chains and changed used calendar.

Fault tests roll back action and receipt mutations after journal write; corruption
checks cover tables/events/claims/caches/receipts/cash/holding protections. Restart
requeues latched exits for adjusted shares; backup reopens with claims intact.
Functional CLI tests exercise isolated lifecycle, offline ownership, adjustment/
receipt/report flow and source preservation. JavaScript adds separate claim display
and updated quarantine confirmation. The direct and CLI invented lifecycle verifies
₹25,029.42 final cash = seed + capital realized P&L + received dividend income.

The populated unpaid-dividend benchmark records p99 **0.2564 ms** on this Mac;
network, callback contention and actual Pi/mobile/custody acceptance remain excluded.
See [corporate-actions.md](corporate-actions.md) and the change log for final checks.

## LT3a daily research validation (0.7.0)

Current combined result: **420 Python tests and 23 JavaScript tests**, **92% Python
coverage**. Daily analysis **97%**, input validation **93%**, report renderer/demo
**100%**. Thirty-three new Python cases include strict clocks/OHLC/ratios/volume/input
bounds, future-prefix invariance, split/dividend gross wealth, late price/basis,
universe removal/re-entry, gaps, missing/latest/empty states, source mutation,
private hashed artifacts, symlink rejection and isolated CLI behavior. Four new
JavaScript cases cover explanatory rendering, safe text, filter/sort/clear/focus,
empty states and large-value display. CI executes all UI tests, daily demo and benchmark.

Actual browser pixel/handset acceptance is pending computer-use permissions. The
synthetic screen is not a daily fill/backtest/model validation or real-market result.

## LT3b quote execution and daily ML validation (0.8.0)

Current combined evidence: **479 Python tests, 29 JavaScript tests, 92% Python
coverage**. Fifty-nine new Python cases include exact fees/cash/reconstruction,
later fills/private artifacts, adverse independent labels, source exhaustion,
partial/unfilled/interruption/stale/gap exclusions, input identity/paths/clocks,
closed-hour coverage, unavailable/late daily review and rebuild invariance,
premarket membership availability, overnight session-limit exits,
capacity/rank, contradictory basis/OHLC, sourced split-before-entry, dividend/payment
routing and counterfactual cash censoring. Model cases check separate namespace,
whole-session interval purge/embargo, disjoint training/scaling, after-validation
availability, matching audit/candidate/cash evidence, corrupt/rehashed artifacts,
failed holdout refusal, synthetic/context gates and no heavy training imports in scoring.
Functional CLI exercises isolated replay/labels/train and fail-closed intraday config.

Six new JavaScript cases cover exact large money, incomplete exposure, explicit
label/portfolio meaning, view/search/clear/focus, failed validation, 200-row disclosure,
empty states and exponents. CI runs daily end-to-end ML demo and separate benchmark.
Ruff/mypy/frozen lock/build/resource/dependency/secret checks supplement behavioral
validation. Browser pixel/physical-phone and actual broker/Pi evidence remain pending.
See [daily-execution.md](daily-execution.md) and [implementation-plan.md](implementation-plan.md).

Final local checks: Ruff lint/format, mypy, frozen offline `uv` lock/sync and installed
dependency consistency pass. Sdist/wheel builds pass; wheel-loaded console/daily/
execution resources and escaped CSP rendering work outside the repository. Secret
patterns and all local links in 22 Markdown files pass. Online advisory scan reports
no known vulnerabilities. Read-only preflight leaves the original account at exactly
₹25,000, zero fees, flat/no orders and its legacy risk hash; operator/calendar/broker/
device readiness remains explicitly incomplete. No new dependency or broker action.

## LT3c1 contribution/SIP verification (0.9.0)

Current combined evidence: **511 Python and 36 JavaScript tests**, **92% coverage**.
Thirty-two new Python cases cover budget/protection/position capacity, concrete
approval and stale contexts, partial/restart/idempotency, damaged/missing proof,
concurrent confirmations and transactional fault rollback, explicit SIP schedules/
missed/cancelled occurrences and pinned calendar changes. Split→addition→partial/
final sale checks exact pooled cost/P&L and one DP charge. A deterministic two-run
lifecycle compares financial journal digests; functional CLI preserves its configured
account and verifies private finished artifacts. API tests cover bearer/origin,
manual-long-term guards, typed payloads and preview→confirmation→actual later fills.

Seven new UI cases exercise exact money/text safety, locks/late responses, preview/
explicit single confirmation, blocked reasons, stale/cancelled dialogs, due-plan IDs/
save/cancel and unknown outcomes without retries. Full existing intraday/long-term/
ML/security tests remain. AST import checks cover execution/portfolio/risk/actions.
CI adds `portfolio-demo` and populated benchmark; full [usage](portfolio-contributions.md)
distinguishes original acquisitions from current/FIFO ownership. Actual broker/Pi/
phone/pixel and portfolio rebalance/cross-account acceptance remain pending.

Ruff lint/format, mypy, frozen lock/sync, installed package consistency, sdist/wheel,
outside-repository shared/new UI resources, secret scan and links in 23 Markdown
files pass. Online `pip-audit --skip-editable` reports no known vulnerabilities.
Actual localhost:8003 asset/CSP/bearer/four-lot checks pass on the separate preview
copy; the original demo artifact hashes remain unchanged. Original account read-only
preflight retains ₹25,000, zero fees/events/orders/holdings and the legacy risk hash.
Missing operator/calendar/broker/device readiness is still disclosed.
