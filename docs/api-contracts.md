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

There is no new HTTP route, quantity field, model upload, model deployment or live
operation. Model-bound research journals add `model_decision` (artifact ID, features,
reasons). `decisions.jsonl` adds probability, same-time rank, vector and model hash.
The broker recomputes the gate rather than trusting a reported probability.
Strict feature/sample/artifact/report contracts and new reason codes are detailed
in [ml-research.md](ml-research.md) and [risk-policy.md](risk-policy.md).
