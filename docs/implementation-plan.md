# Implementation plan, enhancements and status

## Light workspace and real saved-data analysis (0.14.0, 22 October 2026)

Implemented the supplied light/sidebar direction using the existing self-hosted
HTML/JavaScript architecture. Six main areas have distinct entry points; a secondary
purchase/SIP link and contextual onboarding retain existing capabilities. Dashboard
shows server-decimal account estimates, dated daily P&L, position count, valuation
limits, market status, next action, proposal queue and confirmed operating modes.
Strategy preparation and shortlist move to `/strategies` without changing installation,
review or trading authority. Legacy desk fragments migrate through the guarded shell.
Risk Center prioritizes emergency/entry controls and basis reviews; broker and feed
administration remains separate. Broker steps use native keyboard disclosures and
explicit navigation while preserving confirmation and first-unlock default hours.

`api/analysis.py` adds a bounded, authenticated, side-effect-free saved-data view.
Installed reviewed daily data is checked for integrity and availability; saved
completed minute candles exclude gaps, unknown volume and incomplete bars. Return at
most 300 display bars, calculate Decimal SMA 20/50 before display truncation, expose
raw OHLC/source limitations and separate existing quote usability. The SVG is a visual
approximation with exact accessible table data; no broker requests or order controls.
Minute provenance is unknown because it is absent from persisted Candle records.

No framework or external asset dependency was added. The existing same-origin section
frames remain; native scroll fallback is retained for documents over the bounded
height. No graphical backtest, arbitrary strategy builder, notification permission,
financial policy editor or real-order capability was invented. Existing CLI research
and financial actions retain their reviewed workflows. Release version is 0.14.0 in
package metadata/runtime/lockfile so older Python services require explicit restart.

Validation: 660 Python and 117 UI tests, Ruff lint/format and mypy (98 source files)
passed. Coverage includes real served markup labels/structure, route/framing/authorization,
private-state clearing, step navigation without mutation, exact huge/fractional money,
stale valuation/date labels and independent SQLite equality for analysis requests,
including an expired pending proposal that must remain untouched by reading. See the
[test plan](test-plan.md) for final automated counts. A disposable no-broker preview
server was used only for local checks; Firefox capture was unreliable, so desktop/mobile
visual and device acceptance remain unverified. No operator account restart, activation,
setup confirmation or test order was performed.


## Same-second quote handling, cancellation causes and idle-mode explanation (22 October 2026)

Live journal inspection traced six Approval proposals created at 10:52:31 IST to a
safety cancellation at 10:52:36, with repeated data-order failures and no orders.
A later read-only status showed Manual/SESSION_FEED_OR_RISK_PAUSE despite recovered
7/7 quotes. Automatic activations also encountered the already terminal daily signal
identities; existing no-replay behavior is preserved and now explained in the UI.

The model/broker/candle path now recognizes changed Kite whole-second ties ordered by
strictly later receipt time and matching identity/source. Unchanged repeats exclude
receipt time from equality and do not renew clocks, liquidity or clear faults. Tied
changes update actual books/marks/protection/cumulative-volume candles but skip fill
processing for that timestamp. Replay order, backward/ambiguous timestamps, volume,
tick/depth, basis, session, latency and independent financial checks stay in force.

New cancellation records retain concrete pause causes and a durable `desk_pause` event;
hard failures revoke memory authority without first depending on snapshot I/O. Activity
separates proposal/order cancellation and created/updated times. Long-term desks show a
current-day/profile daily signal summary from the existing bounded history, explaining
cancelled/expired/declined/submitted signals without resetting them or forcing retries.

Validation: 650 Python tests, 99 UI tests, Ruff lint/format and mypy passed. New raw-packet
functional callbacks keep Approval active through eight seconds of tied updates and
still cancel on a real backward quote. Unit checks independently reconcile persisted
cash/fills/fees and confirm one depth budget, same-second protective exit latching with
later fills, actual candle deltas, hard-fault authority revocation and no replay.
Distinct external evidence: an eight-second raw probe observed repeated/changed tied
books; an isolated corrected engine then accepted 68 real quotes (20 changed ties),
with zero quality failures, faults or orders. The operator account was not restarted,
rearmed or used for test orders. Sustained/device/execution acceptance remains pending.
Updated main/detailed usage, API, architecture, feed, risk and validation documents.

## Direct daily-review recovery actions (22 October 2026)

Added **Review today’s setup** in the next-step notice, expanded quote details and
quote/basis readiness cards. The existing guided summary opens directly with an
unchecked acknowledgement, reusing an existing installed policy only when the operator
has not selected another. First-time policy selection stays explicit; no ML fallback.
Buttons require a current IST source snapshot, Manual mode and supported guided setup.
Stale/missing data and custom/legacy configurations show recovery guidance instead.
Lock/cancel/late-response guards remain; successful status removes the shortcut.

Validation: 97 JavaScript tests and 17 guided unit/HTTP workflow tests passed, plus
Ruff lint/format checks. Added independent persisted SQLite/exact cash/config checks
showing preview and rejected acknowledgement do not record a basis review or order.
UI cases cover current/stale data, installed versus first/ML policy, cancel/lock,
readiness-card wiring, single explicit confirmation and removal after resolution.
No new Python runtime behavior or dependencies. Updated main, detailed, component and
validation guides; child-page re-entry loads these controls without another restart.

Operational evidence is separate: a 22 October genuine-data download completed 65 × 60
sessions and a preview; those did not approve reviews. Later read-only inspection at
10:51 IST found seven current-day reviews, incoming stored quote timestamps, Manual
mode, zero API blockers, ₹25,000 cash, zero fees and no orders/holdings. No confirmation
request was sent by this assistant. This is a bounded real-feed observation, not
full-session, strategy-profit, phone/Pi or interactive browser acceptance.

## Open-session quote explanations and working shortlist links (22 October 2026)

Read-only inspection of the existing account found incoming quotes rejected for all
eight selected symbols with `LONG_TERM_REVIEW_REQUIRED`, reviews dated 21 October and
no accepted stored quotes. This explains the observed connected/open-session screen;
it is not an independent broker probe or new action approval. The price-basis gate is
preserved. A shared read-only quote diagnostic now distinguishes basis review from
missing/old/rejected/post-reconnect quotes and disconnection in desk and console views.
Readiness shows the current reviewed-session state and blocker-specific next actions.

Workspace links now retain fragments across standalone redirects and section changes,
defer reveal until unlocked/rendered, expand details, focus the review section and
scroll the outer viewport with the applicable sticky-menu offset. Height updates precede
scrolling, and polling does not repeat the jump. Legacy `apply-shortlist` targets the
containing review section instead of a disabled button. Origin/source checks, guarded
section changes and explicit mutations/confirmations remain; viewing cannot apply a list.

Validation: full 637 Python and 90 JavaScript tests passed; Ruff lint/format and mypy
passed. Tests cover next-day blocked incoming quotes across both APIs, independent
persisted SQLite/exact cash equality, post-review new quotes, stale/reconnect/rejection
states, direct/same-section/cross-section links, hidden targets, detail expansion,
desktop/mobile sticky offsets, keyboard focus and spoofed-message rejection. Updated
main/detailed usage, workspace, API and validation guides. These tests simulate workflow;
interactive browser/device acceptance and actual fresh quote execution remain pending.
Reload the workspace for navigation; restart an older Python service for diagnostics.
No operator-owned service, review, feed, shortlist or mode was changed by this work.

## Feed-selection explanation and session-hour defaults (22 October 2026)

Setup step 4 now explains reference catalog versus saved live subscriptions, the app's
ten-symbol limit, token/tick meanings, broader Nifty 100/500 screening and unsaved-input
versus committed-list behavior. Added an accessible saved subscription heading/count
and input help. No actual account selection is changed by these explanatory UI edits.

Step 5 initializes editable 09:15/15:30 IST fields on unlock. Refresh preserves edits,
including intentionally cleared values; lock clears them and a later unlock restores
defaults. Date-specific review, reference, confirmation and server calendar validation
remain mandatory; no session is implicitly saved and existing hours are not rewritten.
Validation: 28 setup/workspace UI and 24 setup unit/API tests pass, covering defaults,
edit preservation, cancel/confirm payloads, unreviewed/blank-time rejection, independent
saved-calendar reads and exact persisted financial-state equality. These are simulated
workflow checks; no broker/market or interactive device acceptance is claimed.

## Saved broker session feedback (22 October 2026)

Implemented visible progress, a pending button label and inline live success/error
feedback in setup step 3. Failed rechecks clear stale local profile verification,
give connectivity/login recovery and permit explicit retry; locking/auth failure
clears feedback and late results cannot restore it. Existing authenticated read-only
profile routes and private token persistence are unchanged. Login/exchange requests
also report their progress/results beside the controls. UI assets load on section
re-entry without restarting the account service.

Validation: 25 setup/workspace UI tests and 23 setup unit/API tests exercise delayed
success, duplicate prevention, failure/retry, timeout, lock/auth clearing, secret
redaction and independent persisted SQLite/credential/config equality. Broker responses
are simulated. Firefox initially showed an unverified session and later displayed
“Profile verified this run” on 22 October. This is an observed UI status, not an
independent broker probe or streaming acceptance. Automated coordinate clicks returned
`noWindowsAvailable`; desktop/mobile interactive acceptance of the updated UI is pending.

## Simplified combined preparation review (0.13.1)

Implemented the requested shorter setup: download → choose policy → review one summary
and acknowledgement → confirm. Existing same-day completed downloads are reused.
The authenticated summary binds exact at-most-ten ranked stocks, held symbols, source
coverage, all calendar dates/hours, unused-account corrections, eligible current-day
basis reviews and entry hours. Confirmation coordinates existing disconnect, immutable
install, shortlist, listed reviews and connection controls. No freeform reference or
separate feed/shortlist click is required on this path. Advanced CSV/individual controls
remain available. Every mode activation stays a separate explicit choice after readiness.

The two-minute preview expires on time, source/account/shortlist changes or newly
completed missing history. Pending orders, used calendar conflicts, faults and no
candidates refuse action. Held positions, quarantines and uncovered earlier quote basis
are excluded from combined current-day attestations. Setup persists phase/outcome before
side effects, reports partial completion, never automatically retries after failure or
restart, and returns identical completed confirmations without repeating connection/reviews.
Model/data/ranking work remains outside the engine lock; the streaming worker is joined
without that lock. The installation gate covers the whole coordinated operation.

UI: one primary finish button, source/calendar/stock review dialog, unchecked consolidated
acknowledgement, clear Manual/closed-hour outcome, hidden advanced forms, and an embedded
workspace dialog sized/positioned to the visible parent viewport. Locks discard private
summaries and late responses; pending reviews block menu navigation and periodic refresh.
Detailed usage and recovery: [strategy-preparation.md](strategy-preparation.md).

Validation is recorded in [test-plan.md](test-plan.md). All new provider/execution tests
use invented data, including independent Decimal cash/fee reconciliation. The user's
running server, saved account, actual review assertions and mode were not changed.
External market/ML/device gates below remain open; this work does not establish profit.


Validation completed locally: **630 Python tests**, **77 JavaScript tests**, **92%**
overall Python coverage; Ruff lint/format (152 files), mypy (96 source files), frozen
offline lock/sync, sdist/wheel build and project secret checks passed. Isolated Chrome
checks at 1440 × 1100 and 390 × 844 verified no horizontal overflow, visible bounded
review dialog, initially unchecked acknowledgement, consolidated confirmation, Manual
outcome, current-day review persistence and shared unlock into activity, with no browser
exceptions. The embedded-parent resize/scroll listeners are removed on close/lock/unload.
No actual account reviews, strategy or mode were applied during validation.

## Genuine strategy preparation and actionable readiness (0.13.0)

Implemented operator-requested genuine-data acquisition in Trading desk: fixed official
Nifty 100/500 constituent CSV, NSE capital-market holidays and equity-action snapshots,
catalog/INE equity matching and up to 60 completed daily Kite sessions. All returned
action kinds in the interval and incomplete history are excluded. Downloads are
background, cancellable, quota-paced and separate from quote/risk authority; progress,
sources, period, coverage and exclusion reasons are visible. No per-stock history read
is made for known action exclusions. Failures are bounded/sanitized, with no data or ML
fallback. A read-only real-source probe returned 100 constituents, 60 proposed completed
sessions, 65 action-free catalog matches and exact 60-session Kite history for one share.
This verifies source/read plumbing, not all-stock coverage or current-market profitability.

Subsequently completed the actual Nifty 100 acquisition: 35 action exclusions, 65
catalog-matched eligible shares, each with all 60 expected daily candles (3,900 rows).
Stored only genuine source snapshots and an unreviewed draft through a strictly read-only
catalog adapter. No actual account/configuration, reviews, strategy/mode or orders were
changed. The new UI will load this pending review after the operator restarts the older
owning server. Validation: 614 Python / 71 JS tests, 92% coverage, static/type checks,
frozen offline environment and build/secret checks; synthetic headless desktop/mobile
layout and installation/navigation checks passed independently of the real data download.

Added an editable calendar and explicit class/basis/policy review, optional server-selected
compatible ML, an explicitly chosen experimental rules policy and private immutable profile
installation. It preserves existing used session definitions, holds Manual, requires a
disconnected feed/no pending orders and rechecks generation/state after out-of-lock
validation. Saved profile/data hashes restore in Manual on restart. Current constituents
are `prospective_snapshot`, available no earlier than observation/review; historical
execution/ML rejects them. Existing point-in-time contracts remain the default.

The desk now shows actionable strategy, transport, per-symbol freshness/basis, market and
entry-window, shortlist, analysis/model and risk cards beside mode explanations. Browser
refresh preserves unsaved preparation reviews. Detailed guide: [strategy-preparation.md](strategy-preparation.md).
Independent current-market model/expectancy validation, point-in-time universe acquisition,
unattended daily refresh, automatic action accounting and early-year/cross-year source
automation remain open; the supported explicit custom-bundle workflow remains available.

Found the actual account's saved 15:15 close conflicting with the normal 15:30 proposal.
Added visible hour differences and a separate strict acknowledgement for correcting an
unused account only; quotes/candles, pinned reviews, trades, actions and portfolio/SIP/
desk-instruction usage prevent correction, rechecked after validation. No actual calendar
was changed automatically. Installation blocks arming; midnight invalidates source runs.
Verified the actual Nifty 500 source contains 501 rows with six unsupported series/dummy
entries; exclude those individually and retain 495 supported shares within the 500-symbol
analysis limit. This is current-source parsing evidence, not their daily history acceptance.

## Trading desk and decision modes (0.12.0)

Delivered a default Trading desk and separate Buy / sell activity section. Explicit
manual/approval/automatic paper modes control strategy proposals for both horizons.
Reviewed daily bundles can screen up to 500 symbols, with separate equity-share
classification, current matching calendar, strict real/synthetic/model provenance and
bounded held-preserving shortlist review. Intraday uses causal completed five-minute
rules; long-term uses prior completed daily rules and optional matching validated ML.
A missing real profile/model is visible and blocks activation; the old five stocks
are not replaced or called profit picks. Rules-only is an explicit experimental policy.

Durable proposals have preview/expiry/mode-generation/price-gap bounds, quantity/cash/
risk revalidation and explicit authorization before the independent paper broker.
The broker journals exact authorization identity with its order transaction; restart
links a matching committed order or cancels unsubmitted authority without replay.
Discretionary sells follow the selected mode; protective exits do not wait. Mode/data/
risk pauses revoke authority before I/O, cancel unfilled desk buys and retain holdings.
Activity uses indexed cursors and exact Decimal cash-flow/fee/fill evidence. Daily
ranking/history I/O stay outside risk locks; only the execution daily timeline is held.

This completes the workflow implementation, not the original profit-evidence/data
acquisition milestones. No genuine daily bundle/model was installed, no actual user
account or mode was changed and no real/paper order was placed in that account.
See [trading-desk.md](trading-desk.md) for commands, configuration, recovery and limits.
Broader automatic data acquisition, qualified net-expectancy ranking and prospective
real-market acceptance remain the next priority; LT3c2/LT3c3 also remain open.

Prepared 20 October 2026; updated 21 October 2026. This is the execution record for the original
[project specification](../zerodha_ai_trading_agent_project_spec.md).

## Implemented scope

### Verified after-hours feed repair (0.11.1)

Diagnosed the actual 8004 feed failure with a valid broker profile and successful
read-only WebSocket: all five selected full packets had empty bid/ask sides after
hours. Skip zero-depth/price observations without manufacturing executable Quotes
or disconnecting; retain strict framing/identity and other validation. Immediately
invalidate prior fresh depth per symbol, reset manual partial candles and apply existing
intraday stale-data safeguards without silently rearming. Added safe stream state,
consecutive retry budget/failure category, receipt time and ignored-book
count to authenticated Setup and explanatory UI. Added meaningful unit, HTTP lifecycle,
pending-order/accounting and UI checks. Updated usage/restart and component documents.
The corrected worker stayed connected in an isolated 15-second actual broker check;
five unusable observations, zero usable quotes, no account callbacks or orders.
No operator-owned process was stopped or restarted by this work. Port 8004 was no
longer listening at the final local check; the operator can start the corrected version
with `./scripts/start_ui.sh` and explicitly reconnect in Setup.
This does not complete fresh-market execution, full-session or strategy acceptance.

### Shared workspace and explicit operating guidance (0.11.0)

Added the requested clear menu and a shared in-memory local unlock across its Start
here, Trading console, Broker & feed setup and Purchases & SIP sections. Direct page
URLs route to the workspace; root goes to the guide. Reload/new workspace tabs still
require unlock. Pending requests/confirmations/login windows block navigation, and
lock/authorization failure clears shared access. Scoped same-origin framing and
origin/window/view checks preserve the bearer-only boundary without browser storage.
Workspace metadata explains actual account mode, configured hours, feed-not-requested
versus disconnected and the difference between trade/strategy/monitoring frequencies.
The [new workspace guide](workspace.md) gives restart and next-session instructions.
This changes navigation, not financial policy, order submission or automatic discovery.

### New priority: broader profit-oriented discovery for both horizons

The operator clarified that “best” means potential profit, after being asked to
choose five manual feed symbols. The next priority is now the staged
[stock-selection implementation plan](stock-selection-plan.md): real data coverage,
reviewed broad equity membership, separate intraday/long-term net-of-cost evaluation,
explainable candidate/selection UI and prospective paper acceptance. Profile-driven
screening, strategy modes and activity UI are now implemented (0.12.0); real-data
acquisition/qualified profit validation and prospective acceptance remain pending. Current account data has no accepted quotes or
stored candles; available research inputs inspected were synthetic. Do not substitute
stock names, demo ranks, index membership or unvalidated gross returns for evidence.
LT3c2 rebalancing and other outstanding work remain open after this new priority.

### Browser setup and repeat startup (0.10.0)

Implemented in response to actual operator-token/request-token confusion and manual
setup friction. `/setup` now separates local authorization from Kite credentials,
opens the official login with state-bound popup handoff, explicitly exchanges and
verifies the session, imports a catalog, validates/persists selected symbols, adds
operator-reviewed immutable session definitions and controls the manual feed.
`scripts/start_ui.sh` opens a matching running account or starts its UI/browser;
`serve --open` remains the lower-level option. No secret is returned in status or
stored in browser persistence, and the independent broker/risk boundary is retained.

The real app registration/payment/login/2FA remain external. First local runtime,
operator credential and economic-policy setup, bound automation, complex corporate
actions and research/model acceptance retain their documented workflows. This does
not complete LT3c2 rebalancing, ETF-specific accounting or real-market acceptance.
The [new detailed usage guide](ui-setup.md) covers commands, private persistence,
failure/recovery and limits. Test evidence is recorded in the change log.

The [live-data first paper-session guide](first-paper-session.md) records developer
registration, officially checked plan requirements, private daily token handling,
isolated manual intraday/long-term setup and acceptance/recovery steps. This is
operator documentation, not evidence of an actual broker login/feed session or a
sandbox integration. External data entitlement and sustained market-feed acceptance
remain pending.
The first-session recovery instructions also distinguish copied-config port
selection, a diagnostic-only preflight, offline UI startup and the nonempty catalog
selection required by streaming. Local UI availability does not establish live-data
or session readiness.
The first actual profile/WebSocket observation is now recorded in
[acceptance.md](acceptance.md#first-connected-session-observation-21-october-2026),
with calendar/price-basis and full-quote acceptance still pending. Catalog `EQ`
membership can include ETFs; instrument-class-aware charges and corresponding
unit/functional accounting checks are required before claiming ETF execution support.

The repository delivers Phases 1–3 infrastructure/research and Phase 4 supervised
intraday paper-feed engineering, LT1–LT2 long-term paper mechanics and LT3a daily
research foundations plus LT3b offline quote-executed daily strategy/ML validation
and LT3c1 reviewed contributions/SIP.
The paper horizons share transactional risk/execution mechanics. Rules/models
run offline or on explicitly configured dedicated paper accounts. No live adapter, profitability
or compliance readiness is implied. External account creation, entitlement checks
and OS service installation require real credentials/hardware and are not fabricated.

| Original work item | Implementation / evidence |
|---|---|
| Git and environment | `main` initialized; Python 3.13.16 `.venv`; hashed `uv.lock`; ignored secrets/runtime/data |
| Typed config and paper guard | Frozen validated TOML settings; alternate mode/public host rejected |
| Structured diagnostics | Rotating JSON with secret redaction, intent correlation in durable journal |
| Local app and health | FastAPI console, liveness, entry readiness, authenticated private API |
| Read-only broker contract | Restricted transport implementing official profile/catalog/history protocol |
| Manual authentication | Supported browser URL + hidden request-token exchange + private output file |
| Streaming and candles | Strict full-mode NSE decoder, disconnect/reconnect gating, 1m/5m builders, history storage |
| Database and account | Schema v1, WAL FULL, file ownership, atomic journal/materialized state, exactly ₹25k initial cash |
| Risk and execution | Fee/slippage-aware sizing, reservations, fill state machine, loss gates, stop/target/session exits |
| Kill and recovery | Durable switch, explicit operator reset, restart reconciliation/cancellation/requeued exits |
| Tests and quality | Unit, integration, functional CLI/API, replay, security, dependency audit, Ruff, mypy, CI |
| Deployment and recovery | macOS/Pi scripts, launchd/systemd templates, verified backup/restore tests |
| Research foundations | O(1) EMA/VWAP/Wilder ATR; service still rejects unconfigured ML |

## Enhancements and justified changes

1. **Atomic reservations and fills.** Sizing and cash/risk reservation share a writer
   transaction; cash, cost basis, fees, orders, fills and audit events commit together.
   One process owns an account, preventing a second startup from changing active work.
2. **Explicit calendar and time.** There is no baked-in possibly stale holiday list.
   Unknown dates are closed. Session time is IST; storage and epoch decoding are UTC.
   Reviewed early closes take precedence. The empty shipped calendar is intentional.
3. **Conservative research accounting.** Decimal money, tick-aware adverse prices,
   order-cumulative fees, estimated liquidation P&L, residual basis allocation,
   and cost-aware daily capacity extend the illustrative sizing formula.
4. **No false closes.** A stop, kill or watchdog request queues an exit; fresh data
   and actual simulated depth are required for fills. Remaining positions persist.
5. **Restart semantics.** Reconcile durable state first, cancel pre-crash pending
   orders, and request required exits again. This avoids reviving old entry intent.
6. **Configuration and schema safety.** Required metadata cannot silently reseed
   when missing; unknown schema and changed risk policies fail closed. New policy
   experiments use a new account. SQLite defaults remain durable rather than tuned
   to unsafe write modes for benchmark scores.
7. **Dependency exception.** The official SDK installed a vulnerable pinned Autobahn
   stack and a flagged Twisted dependency. It was removed, with no ignored advisory.
   A smaller allowlisted HTTPX/WebSocket implementation follows official broker
   protocols and has a clean re-scan. This also removes order-capable SDK methods
   from runtime. See [threat-model.md](threat-model.md).
8. **Lightweight research path.** Incremental Decimal indicators avoid pandas/NumPy
   startup/memory costs in the hot path. Heavy training dependencies are deferred
   until there is a chronological strategy dataset. TOML uses Python's standard
   parser instead of YAML, reducing dependencies. Public types and artifacts remain
   suitable for adding offline ML in later phases.
9. **Normalized schema.** Candidates, decisions, state transitions and system
   notifications live in the append-only journal; snapshots are transactionally
   derived. A few duplicate tables in the illustrative layout were unnecessary.
10. **Reviewable operations.** No host-wide services, users, firewall rules or broker
    plans were silently provisioned. Templates and instructions make these concrete
    for the operator while preserving this workspace's permissions and credentials.

## Phase 2 delivered — version 0.2.0

| Work item | Implementation / evidence |
|---|---|
| Predeclared rules | ORB and VWAP-continuation, completed 5m data, prior-volume reference, independent symbol/session state |
| Causal features | No active/future candles; missing opening/history disables that session; future-quote prefix-invariance test |
| Execution boundary | Existing fee/slippage/latency/depth risk broker; no candle-close fills or invented OHLC paths |
| Isolated research | New output account; backtests never open the service account; export never runs restart cancellation |
| Provenance | Raw-price manifest, reviewed sessions/sources, chronological typed JSONL, source/config/code hashes and unchanged-input checks |
| Reports | Net metrics, observed drawdown, partial-trade accounting, decisions, equity CSV, journal and incomplete-exposure gates |
| Commands | `research-demo`, `backtest`, `export-research`, and configurable strategy TOML |
| Performance | Constant per-candle work; measured p99 below 0.018 ms on this Mac, excluding input parsing/execution/network |
| Verification | Unit, integration, functional CLI, deterministic/leakage/failure tests; detailed research guide |

Enhancements to the Phase 2 plan:

- Require completed candles and observed quotes; OHLCV alone cannot reconstruct
  executable depth or stop/target ordering, so candle-only runs are refused.
- Even zero-latency experiments require a strictly later exchange quote to fill.
- Preserve positions at dataset exhaustion; disclose pending orders, stale valuations,
  held-position quote gaps and incomplete results instead of fabricating liquidation.
- Label synthetic/mixed/replay provenance explicitly, with one positive and one
  negative synthetic session rather than a profitability demonstration.
- Bound manifest/line reads, reject external/symlinked bundle paths and manual
  candidate events, and leave no loadable manifest after failed exports.
- Preserve source orders during export; disclose historical candle availability,
  fee matching and unavailable connection history as research assumptions.

See [backtesting.md](backtesting.md) for input construction, rules, reports and sample gates.

## Phase 3 delivered — version 0.3.0

| Work item | Implementation / evidence |
|---|---|
| Causal training schema | Twelve finite ordered features, completed-time checks, economic candidate fingerprint, no outcomes in features |
| Execution labels | Independent fee/risk/latency/depth-aware paper trials, time barriers and actual fill interval ends; exclusions retained |
| Provenance | Source manifest/hashes, full strategy/economic settings, label policy, code hash, sample/audit hashes and completion manifest |
| Chronological validation | Whole-session expanding walk-forward blocks, interval purge/embargo, independent later calibration and frozen final holdout |
| Baseline model | Train-only StandardScaler + fixed logistic regression + separate regularized sigmoid calibration; no hyperparameter search |
| Diagnostics/gates | ROC-AUC, Brier/log loss, training-only baseline, reliability/ECE, selected count/net label P&L and strict validation consistency |
| Safe artifacts | Bounded local JSON coefficients/reports, exact dimensions/schema, hash checks, no executable persistence, failed-gate refusal |
| Scored research | Same-availability-time ranking, deterministic ties, later portfolio replay and independent risk/model gate |
| Account continuity | Durable model version/schema marker, missing/changed gate refusal before recovery, idempotency includes vector |
| Lightweight inference | Pure Python twelve-feature math; optional training packages never imported for scoring; Pi setup uses runtime/broker extras |
| Commands/docs | `ml-build`, `ml-train`, `ml-demo`, `backtest --model`, full [ML guide](ml-research.md) and corresponding component updates |
| Verification | Unit/functional/causality/censoring/risk/integrity/determinism tests plus a separate inference/ranking benchmark |

Enhancements to the Phase 3 plan:

1. Label **all standalone feasible candidates**, rather than only trades selected
   by a competing portfolio. Preserve censored/rejected/unfilled/interrupted paths
   separately so missing outcomes never silently become negative labels.
2. Use actual quote-driven paper execution for labels. OHLC paths and forced horizon
   closes are not reconstructed. Label end includes the final liquidation fill,
   allowing delayed outcomes to be purged correctly across split boundaries.
3. Reserve separate calibration blocks in every fold; fitting scalers, base models
   or calibration on evaluation/holdout observations is prohibited.
4. Make model availability follow **final validation plus embargo**, not merely
   coefficient fitting. A historical replay cannot use future approval evidence.
5. Freeze fixed baseline coefficients before final holdout diagnostics, retain
   unsuccessful reports, and check diagnostic consistency again during loading.
6. Export inspectable JSON math rather than pickle/joblib. Keep training optional
   and outside the connected feed process; add measured inference/ranking latency.
7. Keep synthetic test settings separate from real research defaults. An explicit
   offline synthetic override relaxes only provenance and only on synthetic data.
8. Bind vectors to economic candidates and accounts to model identity. Model gates
   add rejection conditions without changing the original risk hash or any limit.

Synthetic end-to-end verification uses sixty training/validation sessions followed
by ten unseen invented sessions. It establishes software behavior only. There is no
empirically accepted market model or live readiness.

## Phase 4 engineering delivered — version 0.4.0

| Work item | Implementation / evidence |
|---|---|
| Supervised feed | Explicit `serve --stream --automate`, authenticated arm/disarm, universe-wide readiness and disarmed startup/restart/session |
| Safe account setup | `paper-init` checks profile/catalog and exclusively creates/binds a new account without conflicting manual model initialization |
| Causal history | Separate paced worker loads full completed current-session 5m data; incomplete/revised/obsolete responses fail and missed signals are not replayed |
| Independent execution | Same fee/depth/latency/sizing/kill broker, controller-bound submissions, durable proposal caps, model age/availability |
| Recovery | Disconnect/staleness cancels buys and disarms; stale holdings queue durable exits, without fake closes or automatic rearming |
| Policy continuity | Runtime/catalog/model/strategy/feed identities and used calendar definitions pinned; changed/removed automation fails before recovery |
| Observability | Recent timing windows, cumulative counts/maxima/exceedances, periodic status and observed per-run drawdown |
| Evidence | Source-preserving `paper-report`, net trades, incidents, clean-run/sample/model/latency gates; external/live flags always false |
| Drills | Synthetic partial fills, disconnect with holdings, silence and unclean pending-entry restart with separate ledgers/reports |
| Performance | Additive event-kind/time index, populated benchmark and test proving history network waits release the execution lock |
| Captured research data | Exports preserve first observed candle/connection clocks; missing clocks and unclocked supervised overrides fail |
| Verification/docs | Unit/concurrency/functional API/CLI tests, CI drills and complete [paper-feed guide](paper-feed.md) |

Enhancements to the Phase 4 plan:

1. Supervised arming replaces resumption of old entry authority after restart or
   reconnect. Protective handling continues independently while entries are disarmed.
2. Authoritative completed historical candles avoid unknown first-bar volume and
   partial-bar/history mixing. Backfill warms features without replaying missed trades.
3. History HTTP/rate pacing stays outside the quote/risk lock. Responses from obsolete
   connections are discarded, the whole universe is required and late signals are skipped.
4. Accounts bind their controller/model before recovery. Durable proposal counts
   survive rewarm/restart; model/rule changes use a new account.
5. Engineering evidence remains separate from empirical acceptance. Reports disclose
   recent-window quantiles, lost crash samples and unresolved exposure. No report can
   authorize live execution.

Actual feed duration, fill calibration, entitlement and Pi reboot/storage/power-loss
drills remain external acceptance work. Synthetic tests deliver the code milestone only.

## Phase 4 acceptance tooling and responsive console — version 0.4.1

The next locally implementable milestone extends acceptance support while actual
broker/device/model evidence remains pending. It does not advance into live execution.

| Work item | Implementation / evidence |
|---|---|
| Responsive operator UI | Packaged HTML/CSS/JS, account cards, readiness reasons, positions, recent orders, details and mobile CSS stacking |
| Consistent bounded view | Authenticated `/api/console`, engine-serialized snapshot, latest 200 orders and at most ten quote rows |
| Operator safety | Lock clears values/token and rejects late requests; stale indicators, serialized actions, explicit arm/reset confirmation, no automatic action retry |
| Local acceptance diagnostic | `preflight [--strict] [--output NEW_PATH]`, read-only WAL-aware accounting/integrity, identity/permission/calendar/disk/runtime checks |
| Evidence integrity | New private JSON/Markdown reports and last-written hash manifest; external/live acceptance always false |
| Deployment patch check | Explicit official SQLite WAL-reset fix branches; actual local runtime SQLite 3.53.1 |
| Validation | 284 Python tests, 13 JavaScript cases, 92% Python coverage; wheel includes and loads all UI assets |
| Usage and external work | Dedicated [console](operator-console.md) and [acceptance](acceptance.md) guides and corresponding component documentation |

Enhancements: diagnose accounts without acquiring write ownership/recovering orders;
keep heavy integrity work out of the feed/UI polling path; bound recent UI history;
retain exact decimal display; distinguish local checks, current session and external
acceptance. CSS supports mobile browsers but small-screen visual/physical-phone
acceptance remains pending because browser tooling did not yield reliable evidence.
Desktop Safari and the isolated virtual kill/reset/lock flow were verified locally.

## Long-term scope extension — LT1 delivered, version 0.5.0

The user extended the project to include long-term investing. This introduces a
separate paper horizon; it does not convert intraday accounts or implement the
original live infrastructure Phase 5. Full usage and explicit limits are in
[long-term.md](long-term.md).

| Work item | Implementation / evidence |
|---|---|
| Separate horizon | `investment_horizon`, dedicated config/database/8001 listener, durable binding and unchanged legacy intraday hash |
| Overnight lifecycle | Holdings survive close/weekend/restart; pending buys expire, requested exits remain latched until closure |
| Independent risk | Existing sizing, cash/depth/tick/latency limits plus durable observed peak/drawdown and gap-preserving daily reference |
| Price-basis integrity | Current-session operator review, previous accepted quote clock, pinned used calendar definitions and persistent corporate-action quarantine |
| Delivery costs | Observed retail NSE delivery schedule, exact partial-order fees, atomic per-symbol/day DP allocation and entry cash buffer |
| Reconstruction | Delivery fees/day markers, fills, review authority, quarantines and requested exits checked against journal/ledger on startup |
| Operator/API | Horizon badge, long-term risk/review panel and confirmed individual full-holding exit, authenticated typed endpoints |
| Evidence/drills | Source-preserving `long-term-report`; invented overnight partial/restart, opening-gap and unadjusted-action scenarios |
| Performance/validation | 328 Python + 17 JavaScript tests, 92% Python coverage; populated long-term p99 0.3288 ms on this Mac, excluding network/Pi |
| Documentation | New detailed long-term guide plus updated original specification, usage, API, risk, architecture, threat, operations, acceptance and tests |

Enhancements to the scope: require a separate account instead of changing intraday
semantics; preserve opening gaps rather than marking the new day's baseline at its
first new price; retain explicit exits across cancelled/restarted residual orders;
charge DP only on actual fills; block unaffordable exit fees without inventing cash;
reject a restarted selected feed that omits a held symbol; quarantine known corporate
actions instead of treating an unadjusted price jump as ordinary market P&L.

## LT2 delivered — reviewed corporate actions, version 0.6.0

| Work item | Implementation / evidence |
|---|---|
| Reviewed inputs | Bounded strict JSON, stable action/batch/receipt IDs, sourced ex-date sessions, explicit chronology and quarantine hash/complete-coverage assertion |
| Share ledger | Increasing splits and bonuses, conservative tick-adjusted protections, original holding identity/cost conservation and affected-order cancellation |
| Fractional handling | Exact rational claim, pro-rata basis rounded down to paise with exact holding residual, unknown valuation retained after whole-share exit, explicit cash-in-lieu receipt |
| Dividend ledger | Frozen gross/deduction/net receivable, nonspendable before payment, exact once-only net cash receipt and separately reported investment income |
| Integrity/recovery | Additive tables, atomic journal/materialized accounting, independent ordered fill/action/receipt reconstruction, cache/basis/protection verification and backup/restart tests |
| Operator workflow | Exclusive offline CLI, current-session review and post-application quote required on resume; existing protective exits retain their latch |
| Reports/console | Schema-2 evidence with claims/batches/quarantine hashes/income, adjusted whole-share metrics and separate console claim summary |
| Demonstration/performance | Invented split→dividend→bonus/fraction→exit→receipt lifecycle and a 2,000-quote populated unpaid-dividend benchmark, p99 0.2564 ms on this Mac |
| Standing requirement | [AGENTS.md](../AGENTS.md) records the user's instruction to update usage and component guides with every feature/workflow change |

Enhancements: apply actions only before the account crosses the first affected
ex-date price/trade basis; never infer a payment, fraction value or settled eligibility;
freeze explicit same-date action order; reject unsupported fraction chains and
reverse/complex issuer events rather than silently losing claims. Full schemas,
commands, retry/failure behavior and exclusions are in [corporate-actions.md](corporate-actions.md).

### Extended long-term roadmap

LT3 is implemented in dependency order: **LT3a delivered in 0.7.0** reviewed completed daily data,
point-in-time membership and total-return-aware causal screening with an accessible
offline research dashboard; **LT3b delivered in 0.8.0** quote-executed daily strategy
research and separate chronological ML validation; **LT3c1 delivered in 0.9.0**
reviewed cash-budget additions/acquisition history/SIP; **LT3c2 next** reviewed
rebalance proposals; **LT3c3** aggregate capital coordination. A daily bar cannot establish an
executable fill, and screening statistics cannot approve a model or portfolio.

LT3a delivers bounded streaming daily bundles, explicit period-benefit/availability
evidence, historical inclusion/exclusion/re-entry, consecutive rolling gross-return/
trend/volatility/turnover screening and deterministic candidate ranks. The private
offline dashboard explains statuses/metrics, filters/sorts, missing-data/empty states
and provenance without account/control access. Source/code hashes, mutation checks,
strict validation, invented adverse/gap/exclusion fixtures and unit/functional/UI
tests support review. **420 Python + 23 JavaScript tests, 92% coverage**; 538-bar Mac
analysis p50 **8.0033 ms** including input/validation/hashes. See
[daily-research.md](daily-research.md) for schemas, assumptions and exclusions.

| Milestone | Required implementation / acceptance | Status |
|---|---|---|
| LT1: overnight paper foundations | Lifecycle, delivery costs, reviews, risk, console, evidence and tests | Engineering delivered |
| LT2: corporate actions and cash/share ledger | Reviewed split/bonus/dividend entitlements and effective/payment dates, integral/fractional handling, atomic idempotency, independent reconstruction and recovery | Supported paper engineering delivered; complex actions/tax lots/custody remain excluded |
| LT3: daily research and portfolio management | Completed daily price/total-return data, point-in-time universe, causal strategy/ML validation, SIP/lot additions, rebalancing and cross-account allocation | LT3a/LT3b/LT3c1 delivered; LT3c2 reviewed rebalance proposals next; LT3c3 capital coordination pending |
| LT4: actual read-only holdings and supervised acceptance | Reviewed custody/sellable holdings/settlement reconciliation, calibrated costs/fills and sustained actual device/feed evidence | Pending external access and engineering |
| Live infrastructure / pilot | Existing separate empirical, compliance, adapter/reconciliation and explicit approval gates | Pending; execution unavailable |

Reviews and LT2 inputs are operator assertions, not verified corporate-action feeds.
Real settlement/custody, income tax/AMC, automatic long-term signals, complex actions,
lot/tax management and combined capital coordination are not implemented. Preserved
overnight state alone is not full investment-platform or production readiness.

## LT3b delivered — quote-executed daily strategy and separate ML, version 0.8.0

| Work item | Implementation / evidence |
|---|---|
| Reviewed executions | Separate strict bounded quote/control/action bundle; matching catalog, exact sourced daily calendars, availability clocks and structural raw price/benefit checks |
| Causal strategy | Prior completed available daily windows, current PIT universe, applied-action reference basis, deterministic simultaneous rank, one proposal/session and bounded session-horizon/screen exits |
| Exact delivery replay | Isolated account, existing durable Decimal broker/risk/fees/DP/action/cash ledger, later quote/depth fills, retained unresolved exposure and independent reconstruction |
| Independent labels | Separate account per standalone candidate; full net outcomes and actual final fill intervals; explicit partial/unfilled/interrupted/gap/cash-action/capacity exclusions |
| Separate daily ML | Own twelve-feature/model namespaces, expanding whole-session interval purge/embargo, train-only scaling, separate calibration, frozen holdout and retained failed diagnostics |
| Later scoring | Bounded JSON math, hash/audit/context/gate checks, after-validation availability, probability rank/threshold and independent risk; pure Python inference |
| Explanatory UI | Responsive offline portfolio/label/validation/scored dashboards, exact money, searchable evidence, incomplete states, chronology and plain-language next steps |
| Validation/docs | 479 Python + 29 JavaScript tests, 92% coverage; complete [daily execution guide](daily-execution.md), main usage/component updates, CI/demo/benchmark |

Enhancements: keep independent cash-specific dividend/payment intervals censored
instead of guessing a counterfactual deduction; keep quiet declared sessions in
training chronology; use actual market-open elapsed coverage rather than counting
overnight time as missing ticks; require model availability after the last declared
source session close plus embargo; preserve actual incomplete trial accounts and
explicitly separate label sums/observer state from portfolio returns. Source hashes
and final manifests support consistency, not authenticated broker provenance.

Measured Mac fixture: durable three-session/nine-trade replay p50 **35.4865 ms**,
p99 **47.7677 ms**; warmed single-symbol screen p99 **0.0074 ms**. No unsafe SQLite
tuning or new runtime dependency. These timings exclude network/Pi and do not claim
large-universe performance. Actual daily data acquisition, empirical acceptance,
historical fee matching and custody remain pending. Daily models do not enable the
connected long-term service. **Next locally implementable item: LT3c lot additions/SIP,
reviewed rebalancing and aggregate capital coordination**, before LT4 actual holdings.

## LT3c1 delivered — reviewed contribution foundation, version 0.9.0

LT3c is deliberately split by financial dependency: stable contribution identity/
cash accounting first; reviewed rebalance proposals second; aggregate account capital
coordination third. This preserves independent reconstruction and review at each step.
It does not mark all portfolio management or tax-lot accounting complete.

| Work item | Implementation / evidence |
|---|---|
| Reviewed contributions | Read-only exact preview, fresh quote/holding/capacity hash, explicit authenticated confirmation, atomic budget/order/proof reservation |
| Safe holding additions | Existing-plus-added position room, shared daily/per-trade/aggregate risk and cash/fee checks, retained protection/opening identity, exit-latch refusal |
| Acquisition history | Original filled BUY orders, actual cash/fees and partial entries; distinct current aggregate pooled holdings; no FIFO/tax-lot attribution |
| SIP occurrences | Immutable reviewed source-session dates, fixed cash caps/new-holding percentages, one confirmed attempt/date, explicit missed/due/cancelled states and no automatic catch-up/funding |
| Atomic cancellation/recovery | Pending plan buys cancelled with plan; restart cancels residue, retains fills and consumed occurrence; identical approval retries return original state |
| Independent integrity | Additive tables/schema/journal, reconstructed plan/approval/hash/order authority, first-fill basis and later price-cap/time checks, existing Decimal fills/fees/actions/claims reconciliation |
| Responsive UI | `/portfolio` with exact previews, clear confirmations, due-plan buttons, reserved/spent cash, pending orders, current holdings, original lot history, stale/locked states |
| Evidence/performance | Deterministic invented restart/SIP lifecycle, 511 Python + 36 UI tests, 92% coverage; populated preview p99 0.1784 ms, durable confirmation/fill p99 1.5532 ms |
| Usage | [Detailed contribution/SIP guide](portfolio-contributions.md), main usage and component/specification updates; no new dependency or broker capability |

Enhancements: spend only already available virtual cash rather than infer future
deposits; require an explicitly reviewed session list rather than guess holiday
roll-forward; separate original acquisition history from current pooled ownership;
leave the original intent route's duplicate-holding guard intact; atomically cancel
plan remainder without selling filled shares. The demo's mutable UI copy is separate
from frozen financial evidence. Network/device/market acceptance remains external.

**Next: LT3c2 reviewed rebalance proposals**, followed by LT3c3 shared capital
coordination. Partial discretionary trims/execution, per-lot ownership/FIFO/taxes,
deposits/withdrawals and connected daily automatic signals remain outside this release.

## Remaining external milestones and acceptance gates

| Milestone | Required next evidence |
|---|---|
| Real read-only session | 21 October 2026: actual saved-session profile authentication and five-symbol WebSocket connection observed; accepted full quotes, history entitlement and sustained checks pending; unit transports remain mocked |
| Target-device operations | ARM64 Pi dependency installation, reboot/launchd/systemd/power-loss drill, disk monitoring |
| Empirical strategy validation | Actual matching raw candle/quote data, point-in-time universe/corporate-action review, calibrated fees/depth and retained unfavorable experiments |
| Empirical ML acceptance | Implemented Phase 3 workflow must pass on reviewed real data, with exclusion/selection/cost assumptions retained and later portfolio validation |
| Phase 4 external acceptance | Sustained actual supervised feed, calibrated fills/costs, full-session coverage review and target-device recovery/latency |
| Future live (Phases 5–6) | Separate explicit approval, current compliance and broker rules, separate reviewed adapter/reconciliation |

The code is portable by design, but local tests on this Mac are not a Raspberry Pi
deployment certificate. Backup tests and SQLite fault injection do not replace a real
power-loss rehearsal. A clean advisory scan is time-specific, not a future guarantee.
No live account action or order was attempted. See [test-plan.md](test-plan.md) for
the final measured validation record.
