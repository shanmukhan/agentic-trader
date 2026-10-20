# Change log

## 2026-10-20 — Initial paper platform

Initialized Git on `main` and implemented the Phase 1 paper-only plan from the supplied
specification. Added Python 3.13.16 environment metadata, exact hashed dependency lock,
package entry point, safe config/secret examples, local private runtime, setup scripts
and Git exclusions for credentials, environments, logs and trading artifacts.

Added validated domain types, Decimal money, UTC/IST separation, reviewed session
calendar, read-only HTTP authentication/profile/catalog/history, strict full-mode
equity WebSocket decoder and bounded reconnection. Removed the initially evaluated
official SDK after its pinned transport failed the vulnerability scan; implemented
the limited official protocol with audited transports and documented the deviation.

Added SQLite schema v1, WAL/FULL durability, exclusive ownership, atomic journal,
idempotent intent fingerprints, accounting reconstruction, paper cash/positions,
cost-aware risk sizing/reservations, latency/depth/partial fills, cumulative fees,
daily/streak/stop/target/session risk gates, persistent kill and conservative restart
recovery. Added credential-free health, entry readiness, authenticated operator API,
Origin/Host/security headers, local dashboard and redacted rotating diagnostics.

Added incremental candle/feature infrastructure, explicit unavailable ML stub,
deterministic replay/demo reports, backup verification, deployment templates, CI,
unit/integration/functional/replay/security checks, secret-pattern check and benchmark.
Updated the specification and corresponding architecture, risk, security, API, test,
performance, usage and operator documentation. Later strategy/ML/live phases remain
gated as described in the implementation plan.

### Local validation record

- **108 tests passed**, including unit, integration, functional CLI/API, replay,
  security, real process-death recovery and seeded partial-execution sequences.
- Coverage reported **90% overall**, **93% paper execution**, and **100% costs/sizing**.
- Ruff lint/format, mypy, project secret-pattern check, shell syntax and launchd plist
  validation passed. All local Markdown links resolve.
- Final dependency scan: **no known vulnerabilities**; the editable local project
  itself is not a PyPI advisory target. No advisories were suppressed.
- Frozen/offline environment sync, source distribution and wheel build succeeded;
  the build backend is pinned to Hatchling 1.32.4.
- The real default paper database was initialized at exactly **₹25,000.00** and
  passed integrity/accounting verification. It is ignored by Git and has no holdings.
- The committed 2,000-event Mac benchmark records p99 indicator update **0.0028 ms**
  and quote ingestion/journal/risk/durable commit **0.153 ms**. Typed model construction,
  network, populated-account execution and ML are outside these timer boundaries.

The final pass also normalized financial/time formatting in idempotency fingerprints,
added durable sequence numbers to same-time exit reissues, strengthened persisted
reservation/fee/policy validation, and checked generic error redaction for headers
and JSON-shaped messages. Corresponding regression tests and component docs were updated.

No actual Kite credentials, broker subscription purchase, live order, host-wide
service installation or Raspberry Pi hardware test was performed. Functional broker
tests use controlled transport responses. Configured remote CI has not executed here.
