# Agentic Trader — paper only

Read-only Zerodha Kite data, deterministic risk checks, durable simulated execution,
and a local authenticated dashboard. Starting virtual cash: **₹25,000**.
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
uv run trading-agent serve
```

Open <http://127.0.0.1:8000>. `/health` works without credentials; paper controls
require `TRADING_OPERATOR_TOKEN`. The responsive web console supports desktop and
mobile browser layouts; there is no native mobile app. `/ready` returns 503 until entry prerequisites
are met. The demo uses synthetic data and its own isolated database, with no network.

Read the [complete usage guide](docs/how-to-use.md) before connecting market data.
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

Local validation: **284 Python tests and 13 JavaScript tests passed; 92% Python coverage**, with lint/type checks, dependency
audit and builds passing. Details are in the change log. Real Kite credentials and
Raspberry Pi deployment remain unverified.

```sh
uv run pytest --cov=trading_agent
node --test tests/ui/console.test.cjs
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
Phase 4 adds opt-in supervised paper-feed automation and operations reports.
Real-feed/target-device acceptance and live execution remain later milestones in
the [original specification](zerodha_ai_trading_agent_project_spec.md).
Engineering tests and synthetic demonstrations provide no evidence of trading profitability.
