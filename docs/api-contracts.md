# Operator API and command contracts

## Investment policy drafts and schedule inspection (0.18.0)

All `/api/investment-policies*` routes use existing local Bearer/Host/Origin access
controls and no-store responses. They operate on separate research storage, without
calling account mutation recovery or opening financial authority. Request bodies are
bounded to 16 KiB and reject extra fields, duplicate JSON keys, invalid UTF-8 and
nonfinite JSON constants. Paths, URLs, imports and execution/activation inputs are
unsupported. GET/list/preview do not create draft storage.

| Endpoint | Input/output |
|---|---|
| `GET /api/investment-policies` | Schema 1, ordered `field_definitions`, canonical saved `drafts`, actual storage limits, limitations, activation/backtest support false |
| `POST /api/investment-policies/preview` | Only `draft: {label?, parameters?}`; returns schema 1, normalized `draft`, full-record `preview_sha256`; no persistence |
| `POST /api/investment-policies` | Only `draft`, exact lowercase 64-hex `preview_sha256`, literal `acknowledged: true`; returns schema 1 and saved `draft`, 201 new or 200 same snapshot |
| `GET /api/investment-policies/{draft_id}` | Schema 1 and verified canonical draft for `draft-` + 64 lowercase hex; 404 missing/invalid identity |

Canonical inspection includes `schema_version: 1`, `family: nse-investment-policy-v2`,
`decision_semantics: investment-decisions-v2.1`, all 25 nullable parameters, optional
normalized label, `draft_sha256`, `policy_version_id`, `state`, ordered `missing_fields`,
limitations and `activation_supported: false` / `backtest_supported: false`. State is
`incomplete` until every field is non-null, then `specified`. Specified does not mean
validated, installed, active or executable. Saved records additionally carry `draft_id`.

Decimal values are exact strings, fixed scale 4 except turnover scale 2; integer fields
reject floats, booleans and numeric strings. Bounds, choices and the four field groups
come from `POLICY_FIELDS`; no defaults are supplied. Relationships are enforced for
entered values: invested cap plus reserve ≤100%, stock/sector caps ≤ invested cap, and
stock cap ≤ sector cap. See [all input bounds and examples](investment-policy-drafts.md#inputs-and-exact-values).

The semantic SHA-256 binds sorted compact UTF-8 JSON over domain
`agentic-trader.investment-policy`, schema/family/decision semantics and canonical
parameters, including nulls. Label/path/time are excluded. `policy_version_id` equals
that hash only for a specified draft. The preview hash binds the whole inspection,
including the name/limitations; `draft_id` prefixes it with `draft-`. Repeating that
exact reviewed save is idempotent. Different name/content creates another immutable
snapshot. No automatic retry or update/delete/activate endpoint exists.

Changed preview is 409 `DRAFT_PREVIEW_CHANGED`; invalid parameter/type/relationship
is 422 `DRAFT_INVALID`; missing acknowledgement is rejected. Full storage is 429
`DRAFT_STORAGE_FULL`, oversized record/request 413, and unreadable/unsafe/tampered stored
evidence 503 `DRAFT_STORAGE_UNAVAILABLE`. Body validation may use FastAPI's `detail`
response; domain failures use sanitized `error.code/message`, null incident ID,
`retryable: false`, recovery action and field-errors array. Refresh saved drafts after an
unknown save outcome before explicitly reviewing a same-content/hash retry.

Storage defaults to the configured database path with suffix `.investment-policies`,
with 100 immutable records maximum, 32 KiB each and 1 MiB combined. Ownership/private
permissions, symlinks, bounded reads and canonical record identities are checked.
There is no account schema migration or financial history update.

`investment-policy DRAFT_JSON` is a separate offline stdout-only inspection command.
Optional `--calendar CALENDAR_JSON --start YYYY-MM-DD --as-of AWARE_ISO_TIMESTAMP` must
be supplied together for `reviewed-calendar-policy-schedule-v1`. It validates explicit
whole-period calendar coverage and knowledge time without installing that calendar or
scheduling execution. Reads are bounded to 32 KiB draft / 128 KiB calendar and hashes of
the original bytes are returned in `input_sha256`; `draft` contains canonical inspection
and `schedule` is null when not requested. The pure preview returns `available`, `partial` or `unavailable`,
exact cycles/reasons, source-declaration labels, `execution_authorized: false` and
`policy_activated: false`. See [calendar schema and failure/recovery](investment-policy-drafts.md#inspect-a-local-draft-or-preview-review-dates).
No HTTP schedule or policy-backtest endpoint is introduced.

## Registered backtest jobs and allocation (0.17.0)

All `/api/backtests/*` routes use existing local Bearer/Host/Origin controls and no-store
responses. GETs only inspect research storage; they do not start/retry jobs or touch
account authority. JSON body is bounded to 4 KiB, parsed strictly and rejects extra
fields; paths, URLs, config overrides, executable models and uploads are unsupported.

| Endpoint | Input/output |
|---|---|
| `GET /api/backtests/resources` | Schema 1, registered public resource identities/coverage/strategy/economic policy/provenance, bound runtime code hash and complete observed fee schedule, actual budgets, `capability.available/reason`, limitations |
| `GET /api/backtests/jobs` | Schema 1, retained bounded saved jobs; no inferred ETA |
| `POST /api/backtests/jobs` | Only `resource_id` (`bundle-` + 24 lowercase hex), exact 64-hex `resource_sha256`, 32–64 character alphanumeric/underscore/hyphen `request_key`, `acknowledged: true`; new 202, same request 200 |
| `GET /api/backtests/jobs/{job_id}` | Schema 1, saved state/stage/timestamps/resource/request key/report link or 404 |
| `POST /api/backtests/jobs/{job_id}/cancel` | Only `acknowledged: true`; retained cancelled/terminal outcome, never a financial-order action |
| `GET /api/backtests/reports/{report_id}` | Only succeeded/verified report: exact summary/snapshot, event curves, orders/fills/trades, provenance/hash/limitations and truncation |

States are `queued`, `running`, `succeeded`, `failed`, `cancelled`, `interrupted`.
A duplicate key conflicts (409) if resource/hash differs. Admission is unavailable
(503) unless OS/hard-budget detection passed, full (429 with `Retry-After: 5`) with
one active and one queued admission or 100 retained jobs. Resource identity/integrity
failure returns a sanitized error; read failures never call account mutation recovery.
Resource/report JSON never exposes raw policy credentials or operator paths. Body
validation uses HTTP 413/422; domain errors carry sanitized `error.code/message`,
null incident ID, `retryable: false`, recovery action and field-errors array.

Private registration uses `register-backtest` with explicit local paths; defaults to
the configured account path's `.research-jobs` sibling. Resource identities bind copied
inputs plus validated strategy, sanitized economic policy and public metadata. Report
publication independently checks exact hashes and read-only persisted accounting.
Only Darwin sandbox backend exists, with launch unavailable on the implementation Mac.
See [exact runtime budgets and failure/recovery](browser-backtesting.md).

`GET /api/workspace/views` additionally exposes `portfolio.allocation` with method,
state/reasons, exact actual cash/accepted-bid whole-share values/percentages, excluded
claims and separately labelled commitments. It is not liquidation equity, risk exposure,
target allocation or a mutation. Missing/stale/unreviewed held evidence disables weights.
`capabilities.allocation_snapshot` describes the read-only view; the target-allocation
capability remains unsupported. `backtests.state` is `registered_jobs`, whose actual
launch is still capability-gated. `portfolio.performance.daily_metrics` stays typed
unavailable until accepted daily/flow history exists; no client-supplied performance API
is exposed. [Definitions and null/recovery behavior](portfolio-analytics.md).

## Installed investment price series (0.16.0)

`GET /api/research/series` is an authenticated, no-store, nonmutating query. It accepts
only a saved symbol matching `NSE:[A-Z0-9&_.-]{1,30}` and timeframe `1d`, `1w` or `1mo`.
Unknown supported-format symbols return 404; invalid symbols/intervals 422. Extra
query names are ignored and cannot select paths, datasets, context, URLs or benchmarks.
The browser still uses legacy `/api/analysis` for minute charts; its raw daily resource
keeps its original meanings.

Schema 1 retains analysis quote/symbol/screen context and adds `research` with
`series_version`, `formula_version`, `snapshot_id`, exact input/source-code hashes,
`basis`, 15 `indicator_status` entries, coverage/seed/daily quality, excluded period
states, benchmark availability and explicit unavailable fundamentals. A status carries
its exact decimal string/null, formula, warmup/lookback, reason, basis and dependency
availability time. OHLC/volume are share-adjusted per contiguous segment; the separate
gross index includes known share/cash benefits. Drawdown/volatility are price measures,
not portfolio results. Research labels never change legacy ranking or financial state.

Calculate full eligible history before returning at most 300 display bars. The excluded
period list is bounded to 24 with explicit truncation. Dataset files and optional
fixed-name `investment-context.json`/`investment-benchmark.json` are bounded and
hash-checked. Context binds both original data hashes, explicit reviewed calendar
coverage and any benchmark hash; neither file can be selected through an HTTP path.
Partial periods/unknown coverage are excluded rather than inferred. Benchmark relative
wealth uses 20 matched **daily** intervals even on weekly/monthly charts. Source/license
fields remain unverified declarations; synthetic stock/benchmark labels must agree.

New read failures return sanitized 503 without invoking the account mutation-fault
handler or revoking authority. Nothing polls fills, refreshes strategy, expires
proposals, downloads, opens an account or submits an order. CLI `investment-analyze`
accepts explicit local paths for isolated research artifacts, creates a new private
output directory and publishes its hashed finished manifest last. See
[the research data schemas](investment-research.md).


## Installed V2 workspace read model (0.15.0)

`GET /api/workspace/views` requires the existing local Bearer operator token and is
`no-store`; unauthorized reads return 401. Schema version 1 returns `observed_at`,
`capabilities`, `discovery`, `portfolio`, `settings`, `backtests`, and `dashboard`.
Research is bounded to 500 rows, positions to 10, recent materialized decisions to
10; bounds/truncation are explicit. Exact account/metric decimals remain strings.
Missing performance fields are null with an unavailable capability, never zero.
The read returns dataset-declared synthetic labels and unknown historic fill origin
honestly. No credential fields or config paths are included in Settings.

One engine-lock/SQLite `BEGIN` cut uses a separately closed `mode=ro` connection.
No desk tick/view/expiry, research refresh, broker call, download, fill poll,
reconciliation or recovering engine construction runs. `observed_at` is response
observation time; stored accounting `day`, research `as_of` and quote timestamps keep
their separate meanings. Proposal state is last materialized state, possibly awaiting
the normal expiry workflow. Read failures return sanitized 503 without routing through
the mutation-fault handler. POST is unsupported (405). This is a narrow current read
contract; named-watchlist and target-allocation mutations remain unimplemented; the additive
0.17 job/current-allocation contracts above supersede the older CLI-only limitation.

Page routes `/dashboard`, `/discovery`, `/holdings`, `/settings` and `/learn` use this
model. Since 0.17, `/backtesting` uses its separate research-job API above. `/paper` reuses the existing desk API/controller. Public page
shells carry no private values. The workspace handoff checks exact origin/source,
canonical destination and reported child path. See [frontend behavior and recovery](frontend-modernization.md).


## V2 Phase 2 proposed contracts

[phase-2/api-contracts.md](phase-2/api-contracts.md) defines the current/proposed endpoint
matrix, future exact-value/provenance/null/read/error/cursor schemas and reviewed
mutation/job contracts. Existing routes and fields below are unchanged. Do not call
proposed resources or interpret prototype states as actual API/account results.


## Saved market analysis (0.14.0)

`GET /api/analysis?symbol=NSE:SYMBOL&timeframe=1d|1m|5m` uses the existing bearer/Host
and no-store contracts. Omit symbol to choose the first saved subscription/research
stock; an empty setup returns no symbol/bars. Unknown saved-universe symbols return
404; malformed symbols/unsupported intervals return 422. POST is unsupported. No
browser paths or data-source overrides are accepted. `/analysis` and `/strategies`
are same-origin framed shells; scripts remain non-frameable. Strategy mutation routes
remain unchanged.

Response schema version 1 includes observed_at, selected symbol/timeframe, bounded
symbol choices (subscription and daily-history flags), existing quote usability plus
exact last/bid/ask strings, market_session_open, bars and screening context. Each bar
has time/session, exact decimal-string open/high/low/close, integer volume, quality,
nullable decimal-string sma20/sma50 and daily available_at. `bar_limit=300`, truncated,
excluded_candles, data_state (available/missing/unavailable), message and limitations
explain omissions. Minute reads inspect at most 600 persisted rows; insufficient
history produces null averages. Daily averages are computed before display truncation.

Daily source.kind is installed_reviewed_daily; its synthetic flag is a declared dataset
flag, not independent certification. Minute source.kind is stored_completed_candles
and synthetic is null: individual persisted candles do not record broker/replay
provenance. Source text also declares raw prices without inferred corporate-action
adjustment. Daily data must pass fingerprints and completed/available-time checks;
minute candles must pass validation, completion and quality checks. Bad chart inputs
return unavailable chart data without repairing the file or faulting the account.

This GET never refreshes strategy decisions, expires proposals, polls the risk engine,
downloads broker history, changes subscriptions/reviews or submits an order. Exact
accounting and full persisted-state equality are verified in synthetic API tests.
The chart uses display-only numeric coordinates while the table retains exact values.
See [market-analysis.md](market-analysis.md) for inputs, recovery and material limits.


## Pause causes and handled daily signals (22 October 2026)

New cancelled proposal records include `pause_reasons`; existing `outcome` codes remain
compatible. A `desk_pause` journal event records the previous mode, Manual result,
generic reason and concrete causes. Hard fault/disconnect/date/controller conditions
revoke memory authority before attempting a snapshot. This changes diagnostic evidence,
not pause thresholds or trade authorization. Old records are not backfilled with guesses.

`GET /api/desk` additionally returns nullable `daily_signal_summary` for a long-term
research profile: `handled`, `selected`, state counts and a plain-language message from
matching current-day/profile daily-entry proposals in the existing latest-100 window.
This explains terminal signals/idle modes; it cannot reset an identity, rearm authority,
retry a cancelled signal or create an order. Activity distinguishes unapproved proposal
cancellation from order cancellation and displays created/updated times separately.

## Quote diagnostics and readiness navigation (22 October 2026)

`GET /api/desk` readiness quote rows and `GET /api/console` quote rows now share additive
`status`, `detail`, `usable`, `basis_reviewed` and exchange/receipt timestamp fields.
Existing freshness, age and entry-reason fields remain available. Statuses distinguish
`PRICE_BASIS_REVIEW_REQUIRED`, `FEED_DISCONNECTED`, `NO_ACCEPTED_QUOTE`, `QUOTE_REJECTED`,
`AWAITING_NEW_QUOTE`, `STALE_QUOTE` and `USABLE`. Basis review takes explanatory priority
over quote absence: long-term review rejection occurs before storage. `fresh` retains
the existing quote-clock/connection-generation meaning; `usable` additionally excludes
the missing basis-review case. Neither grants execution authority or bypasses other gates.
No price, quote or financial journal row is created by reading these diagnostics.

Readiness additionally returns `session_open` for the reviewed account calendar, and
blocker-specific next actions. The supported-shortlist link is `#execution-shortlist`.
Workspace section fragments use `#view/element-id`, with strictly bounded IDs and
matching-origin/frame messages for reveal/scroll. Legacy `apply-shortlist` resolves
to the containing review section so a disabled button cannot swallow keyboard focus.
All mutations and confirmations retain their original API requirements.

## Combined preparation setup (0.13.1)

All routes below retain the same bearer, Host and mutation-Origin checks. Extra fields
are forbidden; expected conflicts return credential-free 409 reasons and invalid typed
requests return 422. There is no browser-supplied path, model, arbitrary symbol list or
financial policy override.

| Endpoint | Contract |
|---|---|
| `POST /api/desk/preparation/guided/preview` | Current 32-hex `revision`, explicit `strategy_mode` rules/rules_ml; validates same-day downloaded evidence and returns exact setup summary, 64-hex preview hash and two-minute expiry; persists only a private review record |
| `POST /api/desk/preparation/guided/confirm` | Exactly `preview_sha256` and strict `acknowledged: true`; validates complete binding again, then coordinates disconnect/install/shortlist/listed current-day reviews/connect while staying Manual |
| `GET /api/desk` | Additionally returns bounded `guided_setup` state/phase/message/summary, excluding the private binding |

The private guided record persists before side effects. Confirmed repeats after completion
return the saved outcome; stopped/interrupted attempts require a new preview. Restart
never replays unfinished steps. Errors can leave earlier saved steps in place; inspect
phase/readiness/activity. Reconnection can resume protective exits; no strategy mode is
activated. Read [strategy-preparation.md](strategy-preparation.md) for review eligibility.


## Trading desk and activity (0.12.0)

New `/desk`, `/activity` and `/desk.js` are public shells/assets. The two pages join
`/console`, `/setup`, `/portfolio` in the fixed same-origin frame allowlist; no other
route gains framing access. All private endpoints retain bearer, Host and mutation
Origin enforcement. JSON mode/approval models forbid extra fields and require strict
explicit acknowledgement. No HTTP request can supply an analysis/model filesystem path.

| Endpoint | Contract |
|---|---|
| `GET /api/desk` | Actual mode/revision, blockers, selected symbols, reviewed discovery/provenance/exclusions, proposed shortlist/hash, latest 100 decisions and virtual account |
| `POST /api/desk/mode` | `mode` manual/approval/automatic, current 32-hex `revision`, strict `acknowledged: true`; confirmed authority change, cancels previous pending desk buys/proposals |
| `POST /api/desk/decisions/{id}/preview` | Current bounded preview; no order/cash reservation; persists reviewed proposal and preview hash |
| `POST /api/desk/decisions/{id}/approve` | Exactly `preview_sha256`; fresh full revalidation; terminal retries return the existing result; no replay |
| `POST /api/desk/decisions/{id}/reject` | Decline an awaiting proposal, no financial order |
| `POST /api/desk/shortlist` | Exactly reviewed `preview_sha256`; manual mode, disconnected/no-pending Setup flow; preserves held symbols and updates only feed tokens |
| `GET /api/activity?before=0&limit=50` | Newest-first order-row cursor; limit 1–100; exact orders, original reason/origin, decision, latest 100 fills, cash debit and next cursor |
| `GET /api/activity/orders/{id}/fills?before=0` | Up to 100 fills with stable earlier-sequence cursor; 404 unknown order |

Expected workflow conflicts return credential-free 409 reasons. Invalid typed
requests return 422. An interrupted authorization is not automatically retried.
Polling GETs do not authorize trades or mutate financial state. Preview is an explicit
POST that persists review evidence; it does not buy shares. Read-only workspace metadata
additionally exposes `decision_mode` and `analysis_configured`. A selected mode is not
proof of activation or qualified market data. See [trading-desk.md](trading-desk.md).

Listener: `http://127.0.0.1:8000`, one process/worker. There is no live trading route.
OpenAPI and interactive API docs are disabled. Public health responses contain no
account details. Every `/api/` route requires `Authorization: Bearer <operator token>`.
The token must contain at least 32 characters. Missing configuration returns 503;
missing/wrong authorization returns 401. Send no token in query strings or cookies.
State changes from browsers require either the configured local Origin or no Origin
for non-browser clients. Untrusted Origins return 403; untrusted Hosts return 400.

| Method and path | Result |
|---|---|
| `GET /` | Public entry shell; ordinary browser navigation opens the workspace guide, legacy token callbacks retain capture |
| `GET /workspace` | Shared menu/guide; no private account data before local unlock |
| `GET /console` | Same-origin console section inside the workspace |
| `GET /dashboard.js` | Static console script |
| `GET /dashboard.css` | Static responsive console stylesheet |
| `GET /api/console` | Serialized account/readiness/automation and bounded recent orders |
| `GET /health` | Liveness, 200 and `mode: paper` |
| `GET /ready` | Entry prerequisites; 200 ready / 503 blocked |
| `GET /api/status` | Transactionally derived account/risk snapshot |
| `GET /api/paper/orders` | Persisted paper orders and rejection/cancellation reasons |
| `POST /api/paper/intents` | Risk-gated paper entry; quantity is engine assigned |
| `POST /api/paper/orders/{intent}/cancel` | Idempotent cancellation of pending residual |
| `POST /api/control/kill` | Durable entry kill, cancels buys, queues exits |
| `POST /api/control/flatten` | Same behavior, operator-flatten audit reason |
| `POST /api/control/reset` | Reset kill if flat with no pending orders/budget breach/fault |

Example request schema, with a **current** aware timestamp and real catalog symbol
required for actual paper use:

```json
{
  "intent_id": "research-unique-id-001",
  "symbol": "NSE:DEMO",
  "stop": "495.00",
  "target": "510.00",
  "decision_time": "2026-10-20T04:30:00+00:00",
  "reason": "explicitly evaluated research hypothesis",
  "requires_ml": false,
  "model_version": "phase1-stub"
}
```

Unknown fields and naive timestamps return 422. Financial rejection is a successful
HTTP 200 response containing `state: REJECTED` and reason codes; transport success
does not mean the trade was approved. An accepted order begins `ACCEPTED`, with
`CREATED` and the risk decision also present in the durable journal. Identical intent
retry returns its current persisted state. Conflicting reuse returns 409. An unknown
cancel ID returns 404. A reset that cannot safely proceed returns 409. Unexpected
internal errors return a generic 503 and latch a fault without exposing raw payloads.
Money formatting and timezone offsets are normalized for retry fingerprints: `495`
and `495.00`, or two timestamps representing the same instant, remain the same intent.

The status snapshot exposes Decimal values as strings. `equity` and `day_pnl` include
adverse bid-side exit assumptions and estimated exit fees. `realized_pnl` includes
actual simulated fees and cost allocation. `fees` counts charged fees only, while
unrealized/equity includes estimated remaining sell fees. `reserved_risk` is planned
remaining loss-to-stop for open holdings plus pending entries, not a guaranteed
loss bound. `valuation_fresh` must be inspected along with connectivity and kill.

Representative rejection codes include `FEED_DISCONNECTED`, `KILL_SWITCH`,
`STALE_OR_MISSING_QUOTE`, `UNKNOWN_OR_CLOSED_SESSION`, `OUTSIDE_ENTRY_WINDOW`,
`EARLY_CLOSE_CUTOFF`, `STALE_PORTFOLIO_VALUATION`, `DAILY_LOSS_LIMIT`, `LOSS_STREAK`,
`TOTAL_EXPOSURE_LIMIT`, `STALE_OR_FUTURE_DECISION`, `MODEL_UNAVAILABLE`,
`POSITION_ALREADY_EXISTS`, `POSITION_LIMIT`, `ENTRY_ALREADY_PENDING`,
`INVALID_TICK_SIZE`, `STOP_ALREADY_TRIGGERED`, `INVALID_STOP_OR_TARGET`,
`ZERO_QUANTITY`, and `COSTS_EXCEED_REWARD`. Multiple independent reasons may be joined.

`/ready` checks entry prerequisites only, not approval for an arbitrary candidate.
It can be ready with one usable instrument while another is blocked. No readiness
response bypasses the per-intent gate.

## CLI and database ownership

### Shared workspace navigation (0.11.0)

`GET /workspace` serves the public menu/guide shell; `/workspace.js` and
`/workspace-bridge.js` serve its same-origin scripts. `GET /console` is the explicit
console section. Ordinary root/Setup/Portfolio page navigation routes to the matching
workspace section; legacy manual broker callback URLs are preserved. No private
workspace request is sent before local unlock.

Authenticated `GET /api/workspace` returns actual horizon, configured entry/flatten
times, quote-age limit, current calendar/feed flags and supervised automation state/
proposal cap. It performs no recovery, arming, order submission or financial write.
It is metadata for guidance, not candidate approval. `/api/setup` additionally reports
`ui_version` so the launcher can refuse an older running service.

The workspace retains the operator token only in memory and hands it to the current
section using exact origin, frame-window and view checks. The section verifies its
parent origin/window. Lock/authorization failure clears the whole workspace; no cookie,
URL credential or browser storage was added. Only `/console`, `/setup`, `/portfolio`, `/desk` and `/activity`
permit same-origin framing (`SAMEORIGIN`, `frame-ancestors 'self'`). Workspace/root,
API and other assets retain framing denial; cross-origin framing remains blocked.
See [workspace.md](workspace.md) for navigation, active-action guards and limitations.

### Broker setup actions

`GET /setup`, `/setup.js` and `/kite-callback.js` serve public shells/assets without
private account values. `/api/setup` and all its actions require the existing local
operator bearer/Host/Origin checks. This is the separate operator credential, never
a broker request/access token. The Setup manager is attached by the manual CLI
service; automation-bound/custom apps without one return a safe 409.

| Route | Contract |
|---|---|
| `GET /api/setup` | Credential-presence/profile-run flags, stream requested/connected, catalog count, selected symbol/token/tick rows, today/session definitions, private account-path hash for launcher identity |
| `POST /api/setup/credentials` | Exactly `api_key`, `api_secret`; private save, clears saved access token; active feed must be disconnected |
| `POST /api/setup/login` | Empty object; official HTTPS login URL and random five-minute state; no account password/2FA bypass |
| `POST /api/setup/exchange` | Exactly `request_token`, `state`; single-attempt exchange/profile verification, private token persistence; raw secrets are never returned |
| `POST /api/setup/profile` | Empty object; explicit external read-only profile check; status only, no personal fields |
| `POST /api/setup/catalog` | Empty object; read-only catalog download, atomic existing mapping validation/import; disconnect first |
| `POST /api/setup/symbols` | Exactly `symbols`, 1–10 distinct current catalog names; accepts `NSE:` or bare uppercase; no pending orders, preserves every held symbol; persists tokens/config |
| `POST /api/setup/session` | Exactly `date`, `open`, `close`, `source`, strict `reviewed: true`; current/future sourced supported IST session; existing definitions cannot change |
| `POST /api/setup/connect` | Empty object; verifies profile/selection and requests full stream; no intent or arming; fresh quotes may resume existing pending fills/exits |
| `POST /api/setup/disconnect` | Empty object; stops stream, blocks quote-dependent entries/fills; no liquidation |

Since 0.11.1, `GET /api/setup` and successful action responses also include
`feed_diagnostics`: null when no stream is requested, otherwise a credential-free
snapshot containing `state` (`connecting`, `connected`, `retrying`, `failed`,
`stopped`), `failures` (current consecutive failures, at most ten), `last_failure`
(null or fixed `handshake_rejected`, `timeout`, `broker_rejected`, `invalid_data`,
`processing_error`, `connection_lost`), `last_message_at` (UTC receipt timestamp,
including text/heartbeat; not quote freshness) and `unusable_quotes` (cumulative
full packets skipped for zero bid/ask prices/quantities in this requested stream).
Last failure is retained as history after recovery; connected state takes precedence.
These fields describe transport, not quote acceptance, market opening or permission
to trade. No raw broker error or authenticated URL is returned. Diagnostics are
read under a short stream lock with no external I/O.

Setup bodies are bounded to 8192 bytes and parsed without framework validation that
could echo credential input. Known/third-party setup failures return credential-free
409 messages; independent financial controls are not faulted merely because a login
fails. Successful actions return refreshed status, except `login`, which returns
its URL/state. An API key appears in that official URL; API secret/access token do
not. No auto retry exists; inspect status after an uncertain response, and begin a
fresh login after an uncertain exchange. The single active login state is consumed
before the external exchange attempt.

The popup callback strips its URL query and posts the request token only to its own
origin; Setup additionally verifies popup identity and matching state. A legacy
CLI redirect without a matching Setup popup stays available for manual capture.
No callback GET writes a token or changes account authority. Private credential
files, config selection, calendar snapshot boundaries and remaining CLI-only work
are documented in [ui-setup.md](ui-setup.md).

`trading-agent --config PATH COMMAND` selects an explicit TOML file. Commands:
`environment`, `init-db`, `status`, `verify-db`, `login-url`, `exchange-token`,
`profile`, `instruments`, `historical`, `serve`, `backup`, `demo`, `replay`.
Use `--help` on each subcommand for arguments. All except environment validate paper
configuration. Broker-only commands need credentials; offline commands do not.

The running service owns the account database. Stop it before database-owning CLI
commands, including `status`, `backup`, and `verify-db`; use the authenticated API
for running status. Opening the engine cancels pre-existing pending orders as part
of restart recovery. This behavior applies to database-owning commands as well as
service startup. Inspect the journal before restarting experiments.

Phase 2 adds `research-demo`, `backtest`, and `export-research`; see
[backtesting.md](backtesting.md) for arguments and dataset contracts. Backtest/demo
accounts are isolated from the service database. Unlike engine-owning commands,
`export-research` does not run recovery or cancel pending source orders, though the
service must be stopped to release its account lock. No new HTTP control or live
route is added. The strategy commands have no network or credential requirement.

Journal categories include quote, candidate, risk_decision, order_state, fill,
data_quality and kill_switch. Intent IDs are correlation keys for order/decision
events. `seq` supplies durable journal ordering. Secrets and full user profiles are
not journal payloads. Quote events contain market data and both timestamps.
Research journals also include `strategy_evaluation` with completed-candle features,
filter reasons and the generated candidate. Only subsequent risk decisions can
authorize a simulated order. Zero simulated latency still requires a strictly later
exchange timestamp than the order's decision/creation time.

## Phase 3 offline commands and artifacts

- `ml-build DATASET --strategy PATH --horizon-minutes 30 --output NEW_PATH` builds
  isolated execution labels and a hashed provenance/audit bundle.
- `ml-train SAMPLES --training config/ml.toml --output NEW_PATH` fits chronological
  train/calibration blocks and emits versioned JSON coefficients and diagnostics.
- `ml-demo --directory NEW_PATH` exercises the full synthetic workflow using
  `config/ml-demo.toml`; optional `--strategy`/`--training` select explicit fixtures.
- `backtest DATASET --model MODEL_PATH --output NEW_PATH` requires a verified model
  matching strategy/policy/fees and data starting after validation plus embargo.
  `--allow-synthetic-model` is offline-only, requires `--model`, and relaxes only
  provenance. Synthetic models cannot score non-synthetic data.

Phase 3 added no HTTP route, quantity field, model upload or live operation.
Model-bound research journals add `model_decision` (artifact ID, features,
reasons). `decisions.jsonl` adds probability, same-time rank, vector and model hash.
The broker recomputes the gate rather than trusting a reported probability.
Strict feature/sample/artifact/report contracts and new reason codes are detailed
in [ml-research.md](ml-research.md) and [risk-policy.md](risk-policy.md).

## Phase 4 supervised paper contracts

`paper-init (--rule-only | --model PATH)` creates a new private dedicated account,
checks the read-only catalog/profile and binds automation. It requires configured
reviewed tokens and an operator token; existing paths are refused. `serve --stream
--automate (--rule-only | --model PATH)` starts that account disarmed. Both commands
accept `--strategy` and `--feed-policy`; context changes require a new account.
Connected models must pass validation and be non-synthetic; no override exists.

Authenticated routes use the same Host/Origin/Bearer protections:

| Method/path | Behavior |
|---|---|
| `GET /api/paper/automation` | Enabled/armed state, reasons, counters, bounded timing windows, last candles and snapshot; disabled object for manual services |
| `POST /api/paper/automation/arm` | Arm after all current data/session/model/kill/fault prerequisites pass; 409 with reasons otherwise |
| `POST /api/paper/automation/disarm` | Cancel pending entries; preserve protective handling of holdings |

Manual entry intents return 409 on automated services. The broker independently
rejects controller-free submissions with `AUTOMATION_CONTROLLER_REQUIRED`.
Kill/flatten disarm; reset does not rearm. `/ready` requires armed automation and
all universe data when configured. `/health` remains liveness; no live route exists.

`paper-demo --directory NEW_PATH` runs synthetic drills. `paper-report --output
NEW_PATH` reconciles source storage without broker recovery and writes JSON/Markdown,
trades and a completion marker. Stop the source service first for its ownership lock.
Journal additions: `automation_start/stop/state/candidate/fault`, `feed_connection`,
`feed_evaluation`, `history_failure`, `paper_telemetry`. Reports disclose percentile
windows and missing crash measurements; see [paper-feed.md](paper-feed.md).

## Version 0.4.1 console and preflight contracts

`GET /api/console` uses the existing Bearer/Host/security-header boundary. Schema v1
returns `observed_at`, `account`, `orders`, `order_limit` (200), `orders_truncated`,
`quotes`, `automation` and `entry_readiness: {ready, reasons}`. Orders are newest
insertion first; the existing full orders endpoint remains unchanged. Quotes cover
the configured catalog tokens or at most ten most recent observed symbols for a
manual service. Monetary values remain decimal strings. An empty positions list is
flat, while entry readiness additionally needs data/session/risk prerequisites.
Automation requires explicit arming and whole-universe readiness. A ready response
never approves an arbitrary intent. Polling captures state under the engine lock,
without polling/recovery/submission/arming side effects; nested DB transactions are
avoided when obtaining automation status.

The responsive page polls this endpoint once per refresh. CSS/script are packaged
same-origin resources, with CSP `style-src 'self'`, no inline styles/scripts and no
third-party assets. Arm/reset dialogs add an operator step without changing the
server's authorization or risk contracts. [operator-console.md](operator-console.md)
details browser freshness, request races and private mobile access.

`preflight [--strict] [--output NEW_PATH]` runs before the CLI's engine-opening path.
It uses an existing read-only SQLite snapshot including WAL rather than constructing
an owning Database/PaperBroker. It neither creates accounts nor runs recovery.
Exit 0 means a diagnostic was produced; strict mode exits 2 for blocked required
local checks. Invalid config/output/command failures exit 1. Structured checks and
private artifact/measurement limits are in [acceptance.md](acceptance.md).

## Long-term paper contracts (0.5.0 / LT1)

`investment_horizon` defaults to `intraday`; `long_term` requires a separate bound
account. `config/long-term.toml` supplies the dedicated 8001 listener and engineering
risk defaults. Status/console snapshots add `investment_horizon`. Long-term snapshots
also expose `delivery_fee_buffer` and `long_term` observed peak/drawdown/reference,
quarantine names (at most eleven in the console) and adjustment/settlement flags.
The adjustment flag records applied paper batches; settlement always remains false.
Full quarantine history is available in the account report. Available cash excludes
the delivery entry buffer; cash/fees remain actual simulated ledger values.

| Method/path | Schema and behavior |
|---|---|
| `POST /api/paper/long-term/reviews` | `{symbol, session_date, no_corporate_action, reference}`; strict boolean, current IST reviewed date, registered selected symbol, reference 3–300 characters |
| `POST /api/paper/long-term/exit` | `{symbol}` only; durable full remaining holding exit, no client quantity, repeated pending request returns current order |

Both routes retain Bearer/Host/Origin checks and are refused with 409 on intraday
accounts. Wrong review context or clearing quarantine returns 409; malformed/unknown
fields return 422. A nonexistent/closed holding exit returns 404. A successful exit
response has `exit_queued: true` and `order`; it is not a fill. A successful review
returns its record and paper/adjustment flags, not proof of external verification.
Clear reviews are idempotent by unchanged payload; changes append audit evidence.
A false review quarantines that symbol and cancels pending buys. A clear review
cannot remove it; the reviewed offline LT2 workflow can resolve a supported action.

Manual long-term entries use the existing Candidate/intents schema and independent
fee-aware sizing. Intraday automatic rules/models cannot be attached to this horizon.
New entry codes include `LONG_TERM_REVIEW_REQUIRED` and `LONG_TERM_DRAWDOWN_LIMIT`.
An exit lacking fee cash remains pending with journal reason `INSUFFICIENT_EXIT_FEE_CASH`.
Legacy intraday policy hashes remain byte-identical, including existing model artifacts.

`long-term-demo --directory NEW_PATH` creates only separate invented accounts.
`--config LONG_CONFIG long-term-report --output NEW_PATH` requires a stopped existing
long-term account, reconciles without engine recovery/cancellation and emits private
JSON/Markdown/trades plus a final hash manifest. All live/external/settlement acceptance
flags remain false. Read [long-term.md](long-term.md) for full command and simulation limits.

## LT2 offline corporate-action contracts (0.6.0)

`apply-corporate-actions --file FILE` accepts `ActionBatch`: stable `batch_id`, symbol,
current `quarantine_sha256`, aware `reviewed_at`, reference, literal true
`covers_all_actions` and 1–20 ordered split/bonus/dividend actions. Shares require
strict integer ratios/credit date; dividends require exact per-share amount, total
withholding and payment date. Every action has its own ID, ex/record dates, aware
announcement and evidence reference. `record-corporate-cash --file FILE` accepts
`CashReceipt`: stable payment/claim IDs, paid date, exact net amount, aware review
and reference. See [corporate-actions.md](corporate-actions.md) for full schemas.

Both commands require `--config LONG_CONFIG`, an existing long-term account, matching
policy and exclusive ownership. Input is UTF-8, nonsymlinked, bounded to 64 KiB, with
duplicate keys/extra fields rejected. They return `paper_only` and `idempotent` plus
their durable result. Matching canonical retries append no events; conflicting IDs,
double payment, future/unsupported/context-invalid requests fail with CLI exit 1.
Failure output remains generic/redacted; review input/evidence and the runbook.
No browser upload form or financial-action HTTP endpoint was added.

Snapshots' `long_term` adds `receivable`, `unvalued_fractional_claims` and
`income_received`; equity includes known unpaid net dividends while available cash
excludes them. Unknown fractional claims make `valuation_fresh` false. Account
`realized_pnl` includes settled fraction capital P&L and excludes dividend income.
`long-term-report` schema 2 adds complete batches/claims, quarantine hashes, received
income and fractional realized P&L. The hash-manifest format remains schema 1.
`corporate-actions-demo --directory NEW` produces only invented isolated evidence.

## LT3a offline daily research (0.7.0)

`daily-research-demo --directory NEW` creates an invented dataset and report.
`daily-analyze DATASET --as-of AWARE_TIMESTAMP --policy TOML --output NEW` validates
and screens reviewed completed raw daily bars. Neither opens the configured account
or calls a broker. Input manifest/JSONL schema 1, fixed policy and all availability/
universe/benefit units are specified in [daily-research.md](daily-research.md).
Strict bounded input and new output outside the source are required. Invalid input
or naive clocks fail without a finished manifest. Report schema 1 includes rows,
statuses/reasons, candidate ranks, policy, source/code hashes and coverage. Live,
execution and model-validation flags are always false. Its interactive `index.html`
is an offline file; no route/auth/trading contract changed.

## LT3b offline command contracts (0.8.0)

- `--config LONG_TERM daily-backtest DAILY EXECUTION --strategy TOML --output NEW`
  replays into an isolated delivery account; optional `--model DIRECTORY` selects
  upstream daily candidates only after validation plus embargo. Synthetic scoring
  requires `--allow-synthetic-model` and explicitly synthetic execution input.
- `--config LONG_TERM daily-labels DAILY EXECUTION --strategy TOML --output NEW`
  creates standalone candidate trials and auditable exclusions; no model filtering.
- `daily-train LABELS --training TOML --output NEW` validates finished evidence,
  performs chronological fitting and retains failed diagnostics without allowing scoring.
- `daily-execution-demo --directory NEW [--with-ml]` creates invented isolated evidence.

Global config precedes the subcommand. No service API/authorization, long-term
model attachment or broker capability was added. Strict event schemas, matching
calendars, files, return meanings and recovery are in [daily-execution.md](daily-execution.md).
Reports support desktop/mobile browsers; model loading uses bounded JSON and hashes.

## LT3c1 reviewed contribution and SIP API (0.9.0)

Static `/portfolio`, `/portfolio.js` and shared `/money.js` contain no private values.
All `/api/paper/portfolio` routes retain bearer/origin/no-cache checks and require a
manual long-term account. GET returns bounded account/orders/holdings/original lots
and explicit plan-date states. POST `/preview` accepts a cash-budget `Contribution`
and reserves nothing; POST `/contributions` accepts `Approval` with exact request
and preview hash. Changed/expired/blocked context returns 409 without an order;
invalid typed input returns 422. Exact duplicate approvals return original order state.

POST `/plans` saves immutable ID/symbol/budget/dates/protection percentages/reference;
POST `/plans/cancel` atomically cancels future occurrences and pending plan buys.
No automatic execution or cash deposit occurs. Original `/api/paper/intents` still
rejects adding to an open holding. `portfolio-demo --directory NEW` creates separate
invented evidence and a UI working copy. Full schemas/examples and limits:
[portfolio-contributions.md](portfolio-contributions.md).
