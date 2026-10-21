# Operator API and command contracts

Listener: `http://127.0.0.1:8000`, one process/worker. There is no live trading route.
OpenAPI and interactive API docs are disabled. Public health responses contain no
account details. Every `/api/` route requires `Authorization: Bearer <operator token>`.
The token must contain at least 32 characters. Missing configuration returns 503;
missing/wrong authorization returns 401. Send no token in query strings or cookies.
State changes from browsers require either the configured local Origin or no Origin
for non-browser clients. Untrusted Origins return 403; untrusted Hosts return 400.

| Method and path | Result |
|---|---|
| `GET /` | Operator console shell, no account values until authenticated |
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

### Manual-service setup (0.10.0)

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
