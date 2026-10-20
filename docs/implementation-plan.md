# Implementation plan, enhancements and status

Prepared 20 October 2026. This is the execution record for the original
[project specification](../zerodha_ai_trading_agent_project_spec.md).

## Implemented scope

The repository delivers Phase 1 infrastructure plus the virtual broker/risk mechanics
needed to test it meaningfully. This is deliberately paper only. No live adapter,
automatic strategy, trained model, profitability claim or compliance readiness is
implied. External account creation, entitlement verification and installation of OS
services require the actual environment and credentials and are not fabricated.

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
| Research foundations | O(1) EMA/VWAP/Wilder ATR; deterministic unavailable-model stub |

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

## Remaining milestones and acceptance gates

| Milestone | Required next evidence |
|---|---|
| Real read-only session | Actual manual login, profile, history entitlement, full quote feed; tests currently mock Kite |
| Target-device operations | ARM64 Pi dependency installation, reboot/launchd/systemd/power-loss drill, disk monitoring |
| Strategy/backtest (Phase 2) | Predeclared rule hypotheses, contiguous adjusted research data, realistic event replay, leakage review |
| ML (Phase 3) | Chronological purged walk-forward data, calibration, untouched OOS, versioned schema/model/report |
| Extended paper validation (Phase 4) | Sustained actual feed, calibrated fill/cost assumptions, outage drills and latency distribution with positions |
| Future live (Phases 5–6) | Separate explicit approval, current compliance and broker rules, separate reviewed adapter/reconciliation |

The code is portable by design, but local tests on this Mac are not a Raspberry Pi
deployment certificate. Backup tests and SQLite fault injection do not replace a real
power-loss rehearsal. A clean advisory scan is time-specific, not a future guarantee.
No live account action or order was attempted. See [test-plan.md](test-plan.md) for
the final measured validation record.
