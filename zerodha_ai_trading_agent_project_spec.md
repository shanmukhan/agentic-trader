# Zerodha AI Intraday Equity Trading Agent

**Project specification:** v1.1

**Prepared:** 20 October 2026

**Status:** Phase 1 implementation delivered; external broker/device acceptance pending

**Safety:** No live trading, no real orders, no transfer of funds in Phase 1.

### Implementation record — 20 October 2026

The implemented scope, enhancements, deviations and remaining milestones are in
[docs/implementation-plan.md](docs/implementation-plan.md). All changes are recorded
in [docs/CHANGELOG.md](docs/CHANGELOG.md), with component details in architecture,
risk, security, API and testing documents. Start with the detailed
[how-to-use guide](docs/how-to-use.md).

Python 3.13.16 and a hashed `uv.lock` replace the open-ended Python/package choices.
Configuration uses standard-library TOML. Incremental indicators avoid heavyweight
dataframes on the execution path. Reviewed session dates are explicitly allowlisted;
the supplied calendar is empty and unknown dates are closed. Pending orders are
cancelled after restart reconciliation, with required paper exits requeued.

**Security-driven SDK deviation:** the official SDK's pinned WebSocket dependency
failed the vulnerability audit. It was removed and replaced with restricted clients
for the official read-only HTTP and quote protocols; see
[the dependency decision](docs/threat-model.md). There is still no live order path.
The roadmap below remains the future strategy/ML/live plan; Phase 1 completion does
not imply those later stages or real-world broker/hardware acceptance are complete.

## 1. Project charter

Build a secure, testable, eventually fully automated **intraday NSE cash-equity trading agent** integrated with a personal Zerodha account. Use a **hybrid strategy**: deterministic candidate generation, ML ranking, and an independent deterministic risk engine. Begin with **read-only market data and paper execution**. Live trading is a separate future milestone subject to successful testing and current broker/exchange requirements.

| Parameter | Decision |
|---|---|
| Broker | Zerodha Kite Connect |
| Market | NSE cash equities; long-only initially |
| Trading style | Intraday; positions exited same day |
| Virtual pilot capital | ₹25,000 |
| Strategy | Rule-based signals + ML scoring |
| Deployment | Raspberry Pi 4 or Mac mini; portable Python application |
| Backend | Python 3.13.16; pinned and tested environment |
| API / dashboard | FastAPI + lightweight local web UI |
| Storage | SQLite with WAL; upgrade to PostgreSQL if needed |
| Execution mode | PAPER_ONLY, fail closed |
| Leverage | None initially |
| Live orders | Prohibited in Phase 1 |

### Non-goals for Phase 1

- No live order-placement integration, live order endpoints, or live broker adapter.
- No unattended bypass of Zerodha login, 2FA, or session expiry.
- No guaranteed return, automated strategy optimization on live capital, or LLM-authorized orders.
- No options, futures, short selling, leverage, or high-frequency trading.

## 2. Architecture

```text
Zerodha read-only Kite API / WebSocket
                  |
        Broker read-only adapter
                  |
      Market data ingestion/validation
                  |
          Candle + feature engine
                  |
     Rule candidate generation (Phase 2)
                  |
      ML score/rank (Phase 2)
                  |
      Deterministic risk gate
                  |
        Paper execution engine
                  |
     Paper portfolio + event journal
                  |
      SQLite + FastAPI dashboard
                  |
         Alerts / kill switch
```

**Hard trust boundary:** the strategy and ML modules cannot invoke a live broker order API. Phase 1 has no code path to send live orders. Use an allowlisted, read-only Kite adapter and mock all broker interactions in tests. Future live execution must be separately implemented, reviewed, enabled, and validated.

### Module interfaces

- `BrokerReadOnly`: `get_profile()`, `get_instruments()`, `get_historical_candles()`, `subscribe_quotes()`; no order methods.
- `MarketEvent`: exchange timestamp, receipt timestamp, instrument token, price, volume, source, data-quality status.
- `Candle`: instrument, timeframe, start/end time, OHLCV, completed flag, quality flags.
- `FeatureVector`: timestamp, instrument, features, feature-version; computed using only past completed data.
- `TradeCandidate`: instrument, side, entry hypothesis, stop, exit rule, signal reason, model version, decision timestamp.
- `RiskDecision`: allow/reject, reason codes, approved quantity, exposure and risk reservation.
- `PaperOrder`: unique client intent ID, state, quantity, simulated price, costs, timestamps.
- `PortfolioSnapshot`: virtual cash, reserved cash, positions, realized/unrealized P&L, costs, equity.

### Invariants

1. All timestamps stored in UTC with explicit conversion to `Asia/Kolkata` for market rules.
2. Never use incomplete candles for a completed-candle strategy.
3. No strategy decision can override risk limits.
4. Missing market data, missing configuration, invalid stop, database write failure, or unknown session status blocks new entries.
5. Every simulated order intent and state transition is durable and idempotent.
6. Kill-switch state survives restart and is reset only through an authenticated operator action.
7. On restart, recover journal, positions, pending paper orders, and risk reservations before processing signals.

## 3. Recommended repository layout

```text
zerodha-ai-agent/
├── README.md
├── pyproject.toml
├── .env.example
├── .gitignore
├── config/
│   ├── default.yaml
│   ├── macos.yaml
│   ├── raspberry_pi.yaml
│   └── paper.yaml
├── src/trading_agent/
│   ├── __init__.py
│   ├── main.py
│   ├── settings.py
│   ├── broker/
│   │   ├── models.py
│   │   └── readonly_kite.py
│   ├── market_data/
│   │   ├── historical.py
│   │   ├── stream.py
│   │   ├── candles.py
│   │   └── quality.py
│   ├── features/
│   │   ├── vwap.py
│   │   ├── ema.py
│   │   └── atr.py
│   ├── strategy/
│   │   ├── rules.py
│   │   └── signals.py
│   ├── ml/
│   │   ├── features.py
│   │   ├── training.py
│   │   └── inference.py
│   ├── risk/
│   │   ├── limits.py
│   │   ├── sizing.py
│   │   └── circuit_breaker.py
│   ├── execution/
│   │   ├── paper_broker.py
│   │   └── order_state.py
│   ├── portfolio/
│   │   └── accounting.py
│   ├── persistence/
│   │   ├── database.py
│   │   └── migrations/
│   ├── api/
│   │   ├── app.py
│   │   └── routes.py
│   └── observability/
│       ├── logging.py
│       └── alerts.py
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── replay/
│   └── security/
├── scripts/
│   ├── setup_macos.sh
│   ├── setup_pi.sh
│   └── check_environment.sh
├── deployment/
│   ├── systemd/trading-agent.service
│   └── launchd/com.example.trading-agent.plist
└── docs/
    ├── architecture.md
    ├── threat-model.md
    ├── risk-policy.md
    ├── api-contracts.md
    ├── test-plan.md
    └── runbook.md
```

## 4. Technology decisions

| Area | Recommended implementation |
|---|---|
| Language | Python 3.13.16; exact dependency versions/hashes in `uv.lock` |
| API | FastAPI, Pydantic |
| Zerodha transport | Restricted official HTTP/WebSocket protocol; SDK omitted after vulnerability audit |
| Features | Incremental Decimal indicators; pandas/NumPy deferred to offline research |
| ML baseline | scikit-learn; XGBoost only after ARM compatibility is verified |
| Persistence | SQLite with WAL and schema migrations |
| Tests | pytest, pytest-asyncio if async is used, mocked HTTP/WebSocket |
| Quality | Ruff, mypy or pyright, dependency vulnerability scan, secret scanner |
| Logging | Structured JSON, rotating logs, secret redaction |
| Deployment | Python virtual environment; systemd on Pi, launchd on macOS |
| Remote access | Tailscale or equivalent private VPN; no public dashboard exposure |

Start as a modular monolith; avoid Redis, Kubernetes, and microservices until a concrete need emerges. Train larger ML models on Mac mini or another capable machine, export versioned models, and perform lightweight inference on Raspberry Pi.

## 5. Strategy design (Phase 2+)

### Universe and session

- Start with 5–10 liquid NSE stocks; selection based on measurable spread, turnover, price, and data availability.
- Use completed 5-minute candles for initial signals; 1-minute data may be used for execution simulation.
- Example entry window: 09:30–14:30 IST; target simulated flat by 15:15 IST; respect trading holidays and early closures.
- Long-only, unleveraged; no overnight positions.

### Rule-based candidate generator

Research VWAP trend continuation and opening-range breakout as **hypotheses**, not proven strategies. Example requirements: price above VWAP, rising trend EMA, sufficient volume, acceptable spread, volatility-based stop, and sufficient estimated net reward after costs. Reject signals with missing or stale inputs.

### ML scorer

- Initial model: calibrated gradient-boosted classifier or logistic-regression baseline.
- Inputs: distance from VWAP/EMA, ATR%, recent returns, relative volume, time of day, broad-market trend, spread/liquidity estimates.
- Target: probability that a predeclared favorable barrier is reached before stop/time exit **after estimated costs**.
- Use chronological walk-forward splits, purging/embargo for overlapping labels, untouched out-of-sample test windows, and realistic fees/slippage.
- Save feature schema, training window, model hash, validation report, and calibration diagnostics.
- LLMs may explain trades and logs, but may not directly place orders or bypass the risk gate.

## 6. Risk policy for virtual ₹25,000 account

**Illustrative engineering defaults, not personalized investment advice.** These thresholds are intentionally conservative and must be evaluated against fees, lot/share sizing, and strategy viability.

| Control | Phase 1/2 paper default |
|---|---|
| Virtual starting cash | ₹25,000 |
| Max planned risk per trade | 0.25% = ₹62.50 |
| Daily loss cutoff | 1% = ₹250 |
| Maximum single position notional | ₹10,000 |
| Maximum total notional | ₹20,000 |
| Max simultaneous positions | 2 |
| Max consecutive losing trades | 3, then pause |
| Leverage | 0 |
| New entries | 09:30–14:30 IST (configurable) |
| Target end-of-day flatten | By 15:15 IST |
| Stale/missing quotes | Block new entries |
| Disconnected broker feed | Block new entries |
| Database failure | Stop new entries |
| Model unavailable | Reject ML-dependent trades |
| Stop missing/invalid | Reject |
| Kill switch | Persistently disable entries; cancel/flatten simulated exposure |

**Sizing:** `floor(min(risk_budget / stop_distance, position_notional_cap / entry_price, available_cash / entry_price))`, then reduce for expected fees/slippage and remaining portfolio exposure. Reject quantity zero or if expected costs make the trade unattractive. For example, a ₹500 entry and ₹495 stop implies 12 shares at ₹62.50 planned risk (before fees and slippage), not 50 shares.

Daily loss checks include realized and unrealized P&L and estimated costs; reserve risk for pending orders. Simulate gaps, spreads, partial fills, order rejects, and market-data interruptions. Stops and daily cutoffs are **not guaranteed maximum realized losses**.

## 7. Paper broker specification

- Only virtual orders; no calls to broker order-placement endpoints.
- Simulated order states: `CREATED → ACCEPTED → PARTIAL/FILLED/CANCELLED/REJECTED`; transitions logged.
- Use unique order-intent IDs to prevent duplicates.
- Marketable fills modeled with available bid/ask or conservative spread/slippage assumptions; never assume fills at the last traded price without justification.
- Include realistic latency, partial fills, rejected orders, brokerage, STT, exchange fees, GST, stamp duty, SEBI fees, and slippage; version charge schedule by effective date.
- Reconcile cash, positions, fees, and realized/unrealized P&L after each simulated fill and after restart.
- Replay the same events/config/model to obtain identical decisions and simulated results.

## 8. Security and threat model

### Assets

Zerodha API key/secret, session token, market data, configuration, paper journal, host SSH access, dashboard credentials, future order permissions.

### Threats and mitigations

| Threat | Mitigation |
|---|---|
| Secret leakage | Environment/secret store; strict file permissions; never commit or log credentials |
| Unauthorized dashboard access | Bind to loopback, VPN-only remote access, authentication and CSRF protection for state-changing controls |
| Compromised dependencies | Lock versions, scan vulnerabilities, review upgrades |
| Malicious/untrusted data | Validate schemas, timestamps, price ranges, instrument mapping |
| Duplicate simulated orders | Persistent idempotency key and order-state machine |
| Stale data | Freshness checks and fail-closed policy |
| Power loss | Durable journal, startup reconciliation, backup/restore tests |
| Session expiry | Stop dependent operations; supported manual reauthentication |
| AI overriding limits | Strict one-way interfaces and independent risk gate |
| Unauthorized live execution | No live adapter, no live endpoint, no order-placement code in Phase 1 |

On Pi: create an unprivileged service user, use SSH keys, firewall inbound ports, prefer SSD over SD card for heavy writes, and consider UPS. On Mac: use a dedicated non-admin user/service context, FileVault, firewall, OS updates, and launchd. Both: disable public port forwarding, redact logs, back up databases, and rehearse recovery.

### Zerodha-specific notes

Verify current Kite Connect pricing, API permissions, authentication, token lifetime, static-IP requirements, order-rate rules, and exchange/SEBI obligations against official sources **before** purchasing a plan or enabling future live execution. Do not bypass 2FA or automate prohibited login methods. A static public IP requirement, if applicable to future order placement, concerns the network egress IP—not whether the machine is a Pi or Mac mini. Official docs: https://kite.trade/docs/connect/v3/ and https://developers.kite.trade/ .

## 9. Mac mini vs Raspberry Pi 4

| Dimension | Mac mini | Raspberry Pi 4 |
|---|---|---|
| CPU / memory | Generally more headroom; Apple Silicon strong for training | Adequate for streaming and small-model inference |
| Historical backtesting | Faster on large datasets | Slower; avoid large in-memory jobs |
| ML training | Preferred | Only small experiments |
| Live/paper signal latency | Adequate for 1m/5m systems | Adequate for 1m/5m systems |
| Disk | Usually faster internal SSD | Prefer USB SSD over microSD |
| Continuous operation | Good; configure sleep/power recovery | Good; configure UPS/power/network recovery |
| Service manager | launchd | systemd |
| OS / dependencies | macOS ARM64 (Apple Silicon) or x86_64 | Linux ARM64; verify native wheels |
| Static public IP | Depends on network | Depends on network |
| Power use | Typically higher | Very low |

**Recommendation:** use Mac mini for development, research, training, and extensive backtesting; use Pi for paper trading/monitoring if desired. Maintain one codebase, separate platform deployment files, pinned dependencies, and architecture-neutral interfaces. If you have only the Pi, it can handle Phase 1. For future live trading, reliability and static-IP compliance matter more than CPU; evaluate a VPS/static egress solution separately.

## 10. Development roadmap

| Phase | Approximate engineering window | Deliverable | Live orders? |
|---|---|---|---|
| 1. Foundation and read-only Kite | Days 1–7 | Pi/Mac service, authentication, candles, SQLite, risk skeleton, dashboard, tests | No |
| 2. Strategy and backtester | Weeks 2–3 | Rule candidates, realistic backtests, research reports | No |
| 3. ML + full risk engine | Weeks 4–5 | Walk-forward model, calibrated score, enforced risk policy | No |
| 4. Live-feed paper trading | Weeks 6–7+ | Paper execution, fill simulation, reliability and performance evidence | No |
| 5. Future live infrastructure | Weeks 8–9+ | Compliance review, static IP, separately reviewed live adapter, reconciliation | Disabled until explicitly approved |
| 6. Controlled live pilot | Only after validated readiness | Small-capital monitored rollout | Separate decision |

These are planning estimates, not promised dates. Prolong paper validation if performance or reliability criteria are not met.

## 11. Phase 1 detailed plan

### Day 1 — Environment, scaffolding, security

- Detect OS, CPU architecture, memory, Python and disk capacity.
- Set up Python virtual environment and pinned dependencies.
- Create modular repository, `.env.example`, `.gitignore`, typed settings, logging, pytest, linter.
- Set `TRADING_MODE=paper` and reject any other mode at startup.
- Add unprivileged service account and local-only health endpoint.
- **Done when:** app starts with no broker credentials and tests pass.

### Day 2 — Read-only Kite authentication

- Create Kite developer app and configure callback URL.
- Implement official request-token → access-token login flow.
- Store secrets outside Git, redact logs, handle token expiry.
- Read profile and optional read-only account details; mock responses in CI.
- **Done when:** authenticated read-only request succeeds; missing/expired token fails safely.

### Day 3 — Historical and streaming market data

- Fetch instrument master and stable token-to-symbol mapping.
- Retrieve historical 1m/5m candles subject to plan entitlements.
- Connect quote WebSocket, record exchange and receipt timestamps.
- Detect duplicates, missing intervals, stale quotes, reconnects, holidays.
- **Done when:** validated candles are stored and replayable.

### Day 4 — Persistence and virtual portfolio

- SQLite schema and migrations: instruments, candles, events, candidates, risk decisions, paper orders, fills, positions, account snapshots, model metadata, system state.
- Seed paper cash with ₹25,000.
- Add idempotent event journal and restart recovery.
- **Done when:** paper portfolio survives restart without double-counting.

### Day 5 — Risk gate and dashboard

- Implement exposure, per-trade risk, daily loss, position count, stale-data and session checks.
- Add persistent kill switch and simulated flatten action.
- Build localhost dashboard: connectivity, data freshness, virtual cash, positions, P&L, risk state.
- **Done when:** all invalid simulated trade candidates are rejected.

### Days 6–7 — Integration, resilience, deployment

- Test malformed data, token expiry, disconnect, disk full, database failure, restart, kill-switch persistence.
- Add systemd unit (Pi) and launchd plist (Mac); no public listener.
- Add logs, alerts, database backup/restore and operator runbook.
- **Done when:** acceptance criteria pass and deployment is reproducible.

## 12. Acceptance checklist

Checked items have local automated evidence. Real account access, actual service
installation/reboot and target-device checks remain unchecked until performed.

- [ ] Runs on Raspberry Pi OS 64-bit or macOS without modifying core trading modules.
- [ ] Service starts automatically and recovers after restart.
- [ ] Kite authentication follows supported flow and handles expiry.
- [x] No live order-placement code or reachable order endpoint exists.
- [ ] Instrument and historical candle ingestion works where API entitlement permits.
- [x] Market feed disconnects and stale quotes are detected (mocked feed).
- [x] 1m/5m candles are timestamp-correct, de-duplicated and validated.
- [x] Paper portfolio starts with exactly ₹25,000.
- [x] Risk limits reject invalid candidates.
- [x] Kill switch is durable and effective.
- [x] Simulated order state changes are idempotent.
- [x] Redaction and secret-pattern checks pass; only synthetic test credentials used.
- [x] Unit, integration, functional, replay and security tests pass.
- [x] Backup and restore are verified in local tests.
- [x] Dashboard is private and authenticated for account and control actions.
- [x] Setup instructions and operator runbook are complete.

## 13. Test matrix

| Suite | Cases | Expected behavior |
|---|---|---|
| Unit | VWAP, EMA, ATR, sizing, fees, daily P&L | Deterministic correct values |
| Data quality | Duplicate/out-of-order ticks, missing candles | Reject/flag and block affected decisions |
| Authentication | Missing, invalid, expired session | No dependent broker operations |
| Risk | Excess size/exposure, daily loss, bad stop | Reject with reason |
| Paper execution | Partial fill, cancel, reject, duplicate intent | Correct state and accounting |
| Persistence | Crash mid-order, restart, disk full | No duplicate fills; fail closed |
| Replay | Same input/config/model | Identical results |
| Security | Secret scan, forbidden live route, dashboard auth | No secret leaks or live execution path |
| Operational | Disconnect, reconnect, reboot, backup/restore | Safe recovery with alerting |

For Phase 1, the ML scorer is a deterministic stub. Training, validation, and performance gating come later.

## 14. Initial developer tasks (implementation order)

1. Initialize repository and `pyproject.toml` with pinned dependencies.
2. Implement typed configuration and reject `TRADING_MODE != paper`.
3. Add JSON logs with secret redaction and correlation IDs.
4. Implement FastAPI `/health` and `/ready` (local only).
5. Define read-only broker protocol and mock adapter.
6. Implement official Kite authentication and profile retrieval.
7. Implement instrument catalog and historical candle ingestion.
8. Add SQLite migrations and market-data repository.
9. Implement paper account and event journal.
10. Implement risk policy, sizing and kill switch.
11. Add tests and CI checks.
12. Package systemd and launchd deployment examples.
13. Produce setup, recovery and troubleshooting documentation.

## 15. Definition of ready for later live execution

**Do not treat Phase 1 completion as permission to trade real money.** A separate decision requires: documented exchange/broker compliance; stable supported authentication; verified static-IP/egress arrangement if required; reviewed live adapter; robust broker order reconciliation; broker-side protective orders where available; independently tested failure modes; realistic out-of-sample net profitability; extended paper trading across varying conditions; operator monitoring and kill switch; and explicit user approval.

## 16. Official references

- Kite Connect API documentation: https://kite.trade/docs/connect/v3/
- Zerodha developer portal: https://developers.kite.trade/
- Kite Connect Python client: https://github.com/zerodha/pykiteconnect

Check official documentation for current pricing, product availability, API limits, authentication and retail algo trading rules before acting. This document is a technical design, not a guarantee of financial returns or a legal/compliance determination.
