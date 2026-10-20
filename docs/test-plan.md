# Test and validation plan

All automated tests use virtual capital and synthetic or mocked market data.
No broker credentials, real orders or funds are used. Run from the repository root:

Latest local result (20 October 2026): **108 passed; 90% reported coverage**. Financial
cost/sizing modules have 100% coverage and the paper broker has 93%. Full quality,
audit and packaging results appear in [CHANGELOG.md](CHANGELOG.md).

```sh
.venv/bin/pytest --cov=trading_agent --cov-report=term-missing
.venv/bin/ruff check .
.venv/bin/ruff format --check .
.venv/bin/mypy src/trading_agent
.venv/bin/python scripts/check_secrets.py
.venv/bin/pip-audit --skip-editable
.venv/bin/python scripts/benchmark.py
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
