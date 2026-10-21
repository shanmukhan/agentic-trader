# Agentic Trader — paper only

Version **0.12.0** adds a **Trading desk** with manual, per-trade approval and automatic
paper modes, plus a separate **Buy / sell activity** tab explaining decisions, orders,
fills and fees. Intraday and long-term profiles use separate account/risk contexts.
The existing five-symbol account is still a manual watchlist until genuine reviewed
broad-market data and an appropriate policy/model are configured. The upgrade does
not install profitable-stock evidence or activate trading. See the
[detailed desk guide](docs/trading-desk.md) for setup, prerequisites and limits.

Read-only Zerodha Kite data, deterministic risk checks, durable simulated execution,
and a local authenticated dashboard for intraday and long-term paper accounts.
Starting virtual cash per isolated account: **₹25,000**.
There is no live execution adapter, live order route, or funds transfer functionality.

Python **3.13.16** is recommended. The application targets Python 3.13 on macOS and
64-bit Raspberry Pi OS. Install a patched interpreter; do not use the original 3.13.0.

```sh
uv sync --frozen --all-extras
uv run trading-agent environment
uv run trading-agent init-db
uv run trading-agent demo --directory data/demo-first
uv run trading-agent research-demo --directory data/research-first
uv run trading-agent ml-demo --directory data/ml-first
uv run trading-agent paper-demo --directory data/paper-first
uv run trading-agent long-term-demo --directory data/long-term-first
uv run trading-agent serve
```

Open <http://127.0.0.1:8000>. `/health` works without credentials; paper controls
require `TRADING_OPERATOR_TOKEN`. The responsive web console supports desktop and
mobile browser layouts; there is no native mobile app. `/ready` returns 503 until entry prerequisites
are met. The demo uses synthetic data and its own isolated database, with no network.

Read the [complete usage guide](docs/how-to-use.md) before connecting market data.
After initial local configuration, `./scripts/start_ui.sh` starts/opens your account
and browser. The new [browser setup guide](docs/ui-setup.md) covers Kite login,
session exchange, catalog/symbols, reviewed dates and feed controls. Unlock with the
local `TRADING_OPERATOR_TOKEN`, not a Zerodha redirect token.
The [shared workspace guide](docs/workspace.md) explains its clear menu, one unlock
across sections, feed startup steps and the difference between trade and monitoring
frequency. The current long-term account remains manual.
See [implementation status](docs/implementation-plan.md), [risk policy](docs/risk-policy.md),
[architecture](docs/architecture.md), [API contracts](docs/api-contracts.md),
[operator runbook](docs/runbook.md), [threat model](docs/threat-model.md),
[test plan](docs/test-plan.md), and [change log](docs/CHANGELOG.md).

See the [strategy/backtesting guide](docs/backtesting.md) for Phase 2 hypotheses,
data exports, research runs and report interpretation.
The [ML research guide](docs/ml-research.md) covers Phase 3 labels, chronological
training/calibration, validation, JSON artifacts and later scored portfolio replays.
The [supervised paper-feed guide](docs/paper-feed.md) covers dedicated accounts,
authenticated arming, outages/restarts, history loading and operational evidence.

The [console guide](docs/operator-console.md) covers desktop/mobile access and safe
controls. The [acceptance guide](docs/acceptance.md) covers `preflight --strict`,
private diagnostic evidence and remaining broker/device work. Node 24 is used only
for JavaScript tests; serving the console needs no Node or frontend build.

Local validation: **582 Python tests and 62 JavaScript tests passed; 92% Python coverage**, with lint/type checks, dependency
audit and builds passing. Details are in the change log. Sustained real-market strategy/fill acceptance and Raspberry Pi deployment remain
unverified.

```sh
uv run pytest --cov=trading_agent
node --test tests/ui/*.test.cjs
uv run ruff check .
uv run mypy src/trading_agent
uv run python scripts/benchmark.py
uv run python scripts/benchmark_strategy.py
uv run python scripts/benchmark_ml.py --model data/ml-first/model --allow-synthetic-model
uv run python scripts/benchmark_paper.py
uv run pip-audit
```

Phase 1 provides infrastructure and paper execution. Phase 2 adds predeclared rule
hypotheses and quote-driven historical research in isolated accounts. Phase 3 adds
offline calibrated ML and probability-ranked research with independent risk gates.
Phase 4 adds opt-in supervised intraday paper-feed automation and operations reports.
Version 0.5.0 adds LT1 overnight paper holdings, delivery-cost/DP accounting, persistent
protective exits, price-basis review/quarantine and portfolio drawdown. Read the
[long-term usage guide](docs/long-term.md) for the separate config, localhost:8001 UI,
commands, limits and remaining milestones. Version 0.6.0 adds LT2 reviewed split/bonus
adjustments, dividend/fraction claims and idempotent cash receipts. Follow the
[corporate-action usage guide](docs/corporate-actions.md) and try
`trading-agent corporate-actions-demo --directory data/corporate-actions-first`.
Version 0.7.0 adds LT3a completed daily data, point-in-time membership and causal
screening with a self-contained interactive research dashboard. Read the
[daily research guide](docs/daily-research.md) and run
`trading-agent daily-research-demo --directory data/daily-research-first`.
Version 0.8.0 adds LT3b quote-executed daily delivery research, independent outcome
labels, chronological daily ML validation and later scored replays with explanatory
dashboards. Read [daily execution and ML usage](docs/daily-execution.md) and try
`trading-agent daily-execution-demo --directory data/daily-execution-first --with-ml`.
Version 0.9.0 adds LT3c1 reviewed cash-budget holding additions, original acquisition
history and explicit-session SIP plans. Open `/portfolio` on a manual long-term
service or try `trading-agent portfolio-demo --directory data/portfolio-first`.
Follow the [contribution/SIP guide](docs/portfolio-contributions.md) for previews,
confirmation, recovery and the separate demo UI working copy. Rebalance proposals,
cross-account capital coordination and actual custody/settlement remain pending.
Each account has its own virtual capital; combined allocation is not implemented.
Real-feed/target-device acceptance and live execution remain later milestones in
the [original specification](zerodha_ai_trading_agent_project_spec.md).
Engineering tests and synthetic demonstrations provide no evidence of trading profitability.
