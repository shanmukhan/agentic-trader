# Remaining product work after the 25 October 2026 audit

The [audit resolution](audit-2026-10-25-resolution.md) separates repaired defects,
existing behavior and future capabilities. Owners below are maintainer roles, not
assigned people or delivery promises. Open items are not accepted or enabled features.

| Priority | Capability | Owner | Blocked by / acceptance needed |
| --- | --- | --- | --- |
| High | Months-to-years policy execution and backtesting | Strategy and accounting maintainers | Separate reviewed execution contract, causal replay, exact accounting, policy migration, connected parity and multi-year tests; a saved draft grants no authority |
| High | Native isolated browser research worker | Runtime maintainer | Actual OS sandbox and memory-budget acceptance on each supported platform; simulated lifecycle tests do not close this gate |
| High | Company fundamentals | Data maintainer | Licensed point-in-time source, publication availability, restatements and reproducible provenance; no invented data or scores |
| High | Portfolio daily return curves, benchmark comparison and per-position trends | Accounting and data maintainers | Reviewed daily cuts, known cash flows, corporate actions, source/basis-compatible benchmark and sufficient history; current snapshots cannot supply these |
| Medium | Allocation targets, sectors and rebalancing | Portfolio maintainer | Reviewed sector classification, target/risk contract and independently tested execution; current allocation weights only describe actual holdings |
| Medium | Named research watchlists | Research maintainer | Versioned private storage, lifecycle/rename/delete contract and separate subscription authority; current temporary comparison selections remain available |
| Medium | ETF execution costs | Accounting maintainer | Reviewed instrument-specific fees and exact accounting evidence; equity-share assumptions do not certify ETFs |
| Medium | Optional local TLS | Runtime and security maintainers | Certificate/trust provisioning and localhost callback/launcher/client compatibility; do not bypass browser certificate warnings or expose a remote bind |
| Low | Opt-in Prometheus/OpenMetrics export | Operations maintainer | Authenticated/bounded metric contract, counters across restart/rollback, dependency and scrape configuration; `/api/feed/status` supplies lightweight local observations now |
| Low | SSE/WebSocket dashboard updates and longer-series rendering | UI and runtime maintainers | Backpressure, auth/Lock cancellation, sequence/reconnect and sustained-load evidence; bounded SVG plots and existing polling remain |
| Low | Backtest fill scatter | Research UI maintainer | A comparable recorded execution-price series and explicit price/time basis; order/fill tables retain exact evidence |
| Low | Automatic hyperparameter search | ML research maintainer | Predeclared chronological nested selection and untouched final holdout; existing expanding-window validation and descriptive coefficient diagnostics remain |
| High | Real broker/feed scale and physical-device acceptance | Operator and QA maintainers | Explicit acceptance using actual supported broker entitlement, sustained symbol load and target OS/device; local synthetic tests do not certify these |

Each implementation must update usage/component guides, the implementation plan,
changelog and tests in the same change. Missing capabilities stay unavailable with
reasons and next actions; they must never appear as zero-valued performance or active
trading authority.
