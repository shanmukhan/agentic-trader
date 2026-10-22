# Phase 2 — architecture and UX design

Date: **22 October 2026 IST**. The user approved Phase 2 after the
[Phase 1 audit](../ARCHITECTURE_AUDIT.md). Runtime baseline is **0.14.0 / 2d5c208**.
This package specifies the target product; it is not a claim that Phase 3 screens,
new APIs, calculations, strategies or background jobs have been implemented.

## Deliverables

| Artifact | What it makes reviewable |
|---|---|
| [Architecture](architecture.md) | Component boundaries, retained stack/frames, one financial writer, read models, isolated jobs, compatibility and migration rules |
| [Navigation manifest](navigation.json) | Twelve grouped destinations and canonical/legacy aliases |
| [UX specification](ux-specification.md) | Every screen's inputs, states, actions, authority and accessibility behavior; shared modal/async/metric/table contracts |
| [Light design system](design-system.md) | Color/contrast, typography, spacing, responsive layout and reusable components |
| [Offline prototype](prototype.html) | Local navigation, missing/stale example states, timeframe controls and design-only connection confirmation; no account connection or results |
| [API/job contracts](api-contracts.md) | Current/proposed endpoint matrix, exact values/null/provenance/clocks, stable pagination, preview/confirm/idempotency, bounded job lifecycle and recovery |
| [Financial metrics](financial-metrics.md) | Cash/basis/equity/P&L/claim identities, returns/benchmarks, allocation/risk and completeness rules |
| [Synthetic financial examples](examples/financial-examples.json) | Seven independently checked arithmetic cases and two return paths, clearly not account evidence |
| [Strategy/data contracts](strategy-and-data-contracts.md) | Legacy versus proposed long-horizon identity, causal data/indicators and connected/replay semantics |
| [Strategy scenarios](examples/strategy-scenarios.json) | Fifteen proposed acceptance vectors; specified, not executed financial workflows |
| [Acceptance plan](acceptance-plan.md) | Fix-first specifications, per-screen test matrix, financial/security/browser gates and Phase 3 handoff |

Open `prototype.html` locally in a browser to review it. The persistent design-preview
banner distinguishes it from the actual workspace. Choose a destination or example
state; all monetary results remain unavailable. “Confirm · preview only” merely closes
the local preview; it cannot connect a feed or submit an order. It does not contain
credentials, fetch APIs, WebSockets or browser storage. The real application is still
started through the existing `./scripts/start_ui.sh` workflow and has not been changed.

## Decisions made

Retain FastAPI/Pydantic, SQLite/Decimal and self-hosted HTML/JavaScript; no framework
rewrite, real execution adapter or database replacement. Keep the guarded same-origin
frames initially and consolidate shared presentation components. Group the twelve
requested destinations by task, preserving legacy routes and pending-action guards.
Research, coherent reads and isolated jobs cannot acquire financial authority.

Use exact values with versioned definitions, explicit null/partial/freshness/provenance
and separate income/claims/fees. Preserve the existing legacy policy; new months-to-years
policy drafts cannot activate until their parameters, evidence and compatibility are
complete. A new profile or mode switch cannot replay a terminal investment cycle.
No licensed fundamentals or benchmark source is guessed. No new aggressive limits or
account changes are activated by the design.

The first implementation priority is confirmation visibility and shared lifecycle
coverage, followed by grouped navigation and coherent read views. Calendar cross-year,
strategy parity and recovery/provenance specifications must be implemented before
expansion depends on them. Existing intraday features remain preserved/deferred;
the documented narrow repeat-handling issue is not an invitation to add intraday work.

## Open implementation inputs

- Select and verify source rights/availability for historical membership, fundamentals,
  sector classification and a compatible benchmark. Until then, use unavailable states.
- Supply and review a new investment policy's holding/rebalance/entry/exit/target/risk
  parameters. Phase 2 defines the required fields; it does not make them active defaults.
- Characterize real data volumes, process/resource budgets, target device and browser
  behavior before advertising proposed capacity or latency limits.
- Evaluate any interactive chart library's maintained version, license, local bundling,
  CSP and accessible alternatives during implementation; no dependency is added here.

## Validation record

Executed successfully:

- `.venv/bin/python docs/phase-2/validate_design.py`: twelve destinations/aliases,
  fifteen proposed scenario definitions, linked documents, HTML labels/structure,
  offline boundary and eleven required contrast pairs.
- `.venv/bin/python docs/phase-2/validate_financial_examples.py`: **129 independent
  arithmetic/contract comparisons**, seven synthetic ledger cases and two return paths.
- `node --test docs/phase-2/validate-prototype.cjs`: **6 passed**, covering all twelve
  screens × four example states, local dialog outcomes, interval text and mobile-menu state.
- Ruff lint/helper formatting and `git diff --check`: passed.

These validate design artifacts and synthetic examples only. The runtime suite was not
rerun because application code, configuration and financial workflows did not change.
Phase 1's 660 Python/117 UI baseline remains dated evidence, not Phase 2 feature proof.
Real browser/layout, broker, target-device, profitability and persisted-account acceptance
remain separate. See [acceptance-plan.md](acceptance-plan.md).

## Implementation handoff

The user subsequently requested Phase 3 and Phase 4. Version 0.15.0 delivered the
[shared frontend/saved-state slice](../frontend-modernization.md); 0.16.0 delivers
[causal price research](../investment-research.md), explicit period coverage, indicators,
legacy-ranking explanations and an optional sourced benchmark adapter. Fundamentals,
browser jobs, new investment policies and portfolio returns/allocation remain future
work. Runtime tests pass; full rendered browser/device and source acceptance remain
open. This package stays a design reference, not proof that every proposed contract
is installed. See the [V2 plan](../IMPLEMENTATION_PLAN.md) and
[implementation record](../implementation-plan.md) for actual status.
