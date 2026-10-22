# Phase 2 API and job contracts

Date: 22 October 2026 IST. Status: **design only; all proposed routes, envelopes and
limits below are unimplemented** unless explicitly marked Current. This document does
not change [current API contracts](../api-contracts.md). Read with
[architecture](architecture.md), [financial definitions](financial-metrics.md) and
[data/strategy semantics](strategy-and-data-contracts.md).

## Compatibility and authority

Keep current `/api/*` routes, response fields, exact money semantics and browser guards.
Add new resource namespaces where a distinct research/job/read-model capability needs
them; no wholesale `/api/v2` migration. New responses carry `schema_version`; adding
optional fields is compatible, removing fields/changing meaning is not. An incompatible
contract needs a separately versioned resource and a documented compatibility period.
No feature silently relabels current `equity` as complete portfolio value or treats
current mixed desk view methods as side-effect-free queries without characterization.

Every private endpoint retains bearer/Host checks, mutation Origin enforcement, no-store
and sanitized errors. The operator token remains memory-only in the browser; requests
do not accept it in URL/query/cookies. Setup credential input is the only approved secret
entry and never echoes submitted values in validation, response or logs. No request
accepts a local path, upstream URL, SQL, Python expression, arbitrary model object or
live-execution mode. Resource IDs resolve inside a verified server-owned registry.

Viewing, filtering, previewing and running a backtest do not authorize paper orders.
GET/HEAD on new queries are nonmutating: no strategy refresh, expiry, `tick`/`poll`, broker
download, recovery constructor, subscription, install or financial journal append. A
preview POST may persist review evidence and audit identity, but reserves no money and
grants no order authority. Paper confirmation goes through existing authority/risk and
must distinguish confirmed decision, accepted order and executed fill.

## Endpoint matrix

`Current` means present in the audited 0.14.0 baseline, not fully meeting every target
requirement. `Proposed` means absent or a future extension; do not call it from UI until
implemented and advertised in capabilities.

| Destination/capability | Current endpoint(s) to preserve | Proposed additive contract and boundary |
|---|---|---|
| Workspace/status | `GET /api/workspace` | Add a versioned capability manifest with implemented destinations/actions/limits; no private state until authenticated. |
| Dashboard/account | `GET /api/desk`, `/api/status`, `/api/console` | `GET /api/portfolio/summary`: coherent snapshot, versioned metric definitions, completeness and provenance. Never sum independent account seeds. |
| Discovery | Reviewed discovery/shortlist inside `GET /api/desk` | `GET /api/research/candidates`: immutable bundle/policy ID, deterministic rank/filter, missing/excluded evidence. Watchlist save is a separate non-execution resource. |
| Saved analysis | `GET /api/analysis` (`1d`, `1m`, `5m`) | `GET /api/research/series`: registered symbol/bundle, daily/weekly/monthly coverage-aware bars and defined indicators. Preserve existing analysis response; new intraday features excluded. |
| Strategy definitions | Preparation/profile evidence inside `GET /api/desk` | `GET /api/research/strategies` and `GET /api/research/strategies/{id}`: versioned immutable research definitions and compatibility flags; `POST /api/research/strategies/validate`: bounded draft validation only. |
| Preparation | `POST /api/desk/preparation/{download,cancel,install}`, guided preview/confirm | Existing workflow stays; richer source-year/error/progress evidence is additive. New generic jobs do not automatically replace or retry guided state. |
| Backtesting | Existing CLI only | `POST /api/backtests/jobs`, `GET /api/backtests/jobs[/{id}]`, `POST /api/backtests/jobs/{id}/cancel`, `GET /api/backtests/reports/{id}`: isolated request-bound jobs/results, no installed-policy mutation. |
| Paper review | `/api/desk/mode`, `/api/desk/decisions/{id}/{preview,approve,reject}`, `/api/desk/shortlist` | Preserve current guarded mutations. New proposal-list queries may be added without changing daily identity or terminal replay behavior. |
| Paper execution | `/api/paper/orders`, `/api/paper/intents`, order cancel | Preserve server sizing, independent risk, idempotency and no broker order transport. No browser-supplied quantity shortcut. |
| Portfolio/purchases | `/api/paper/portfolio`, preview, contributions, plans, plan cancel | Proposed `/api/portfolio/holdings`, `/api/portfolio/allocation` are reads. Future allocation preview/confirm creates reviewed proposals through the decision service; never directly writes orders/holdings. |
| History | `/api/activity`, `/api/activity/orders/{id}/fills` | New symbol/date/entity/state filters and snapshot pagination require explicit capability/schema version. Keep existing cursor/limit behavior for old clients. |
| Risk | `/api/control/{kill,flatten,reset}`, long-term reviews/exit, automation arm/disarm | `GET /api/risk/policy` and `/api/risk/exposure` describe current frozen limits, pending risk and unknown classifications. Policy change is a separate preview/new-account design, not an edit of bound financial meaning. |
| Broker/data | `GET /api/setup`, `POST /api/setup/{operation}` | Add sanitized verification/error/recovery/evidence fields; proposed connect preview/outcome resources require an explicit implementation design. Current route dispatch does not imply these operations exist. |
| Settings/system | Current typed TOML plus CLI verification/backup | `GET /api/system/configuration`, `/api/system/incidents`: redacted read-only state, restart requirements and incident references. No secret download or implicit engine recovery. |
| Learning | Existing static guide/help | Versioned static articles/glossary; optional local display preferences have no execution or notification authority. |

A future capability manifest lists only implemented resource schemas, intervals,
symbols, actions and actual configured limits. Unsupported planned features return an
honest unavailable state; do not fabricate success/sample portfolio values.

## New read-response envelope

The proposed envelope is `meta`, `data`, `provenance`. Existing endpoints are not wrapped
in it automatically. `meta` contains `schema_version`, server `observed_at`, opaque
`snapshot_id`, account ID or null for independent research, `mode: "paper"` for account
responses, relevant policy/artifact/ledger identities, and warnings. A snapshot ID binds
one read instant; it is not an authorization token or substitute for a mutable revision.

Each metric has the following conceptual shape. This is a synthetic schema example,
not an actual account result:

```json
{
  "id": "complete_liquidation_equity",
  "value": null,
  "unit": "INR",
  "method_id": "liquidation-equity",
  "method_version": "proposed-1",
  "state": "unavailable",
  "freshness": "unknown",
  "reason_codes": ["UNVALUED_FRACTION"],
  "as_of": null,
  "observed_at": "2026-10-22T06:00:00Z",
  "provenance_ref": "synthetic-example-only"
}
```

- `state`: `available`, `partial`, `unavailable`, `not_configured`, `not_applicable`.
  `partial` may expose a clearly named known component; a requested full total is null
  when unknown, with a separate partial estimate if useful. `null` never means zero.
- `freshness`: `current`, `stale`, `unknown`, independent of availability. A last-known
  value may be stale and dated; stale input cannot be presented as current performance
  or execution readiness. Input quality/validation is separate evidence, not freshness.
- `reason_codes`: stable machine codes with a centrally mapped plain-language message
  and scoped safe action. Empty means no known limitation, not source certification.
- `as_of`: latest instant/session actually represented; `observed_at`: server response
  observation. For metrics on one snapshot, observation may be inherited from `meta`.
- `method_id`/`method_version`, `unit` and `provenance_ref` are required whenever a value
  could otherwise be interpreted under a different return, price or cost methodology.

Full definitions, minimum history and independent synthetic exact calculations are in
[financial metrics](financial-metrics.md). Unsupported benchmark/fundamental values stay
null with `not_configured` or `unavailable`, not an invented zero or guessed proxy.

## Provenance, dates and exact values

Provenance entries identify `id`, source kind/provider, declared synthetic status
(`true`, `false` or `null` when unknown), acquired-at, source period and coverage,
event/available-at semantics, raw/share-adjusted/total-return basis, immutable content
hashes, schema/method versions and licensing/entitlement reference where relevant.
Do not expose private paths, credentials or authenticated source URLs. A provider label
or dataset `synthetic:false` is a declared claim, not independent market certification.
Old minute candles lacking per-record provenance remain unknown.

Financial amounts, prices, fractional claims, percentages and ratios serialize as
finite base-10 strings, without exponent, NaN or Infinity. Decimal precision/rounding is
defined by the method/charge policy; never round accounting through a JSON float. Money
display may use paise, while exact input/basis can require more scale. Integer share
quantities remain strict JSON integers within validated bounds; fractional entitlements
are decimal strings. A zero amount is `"0.00"` under a two-decimal money method; unavailable
is null. IDs/hashes are opaque strings. Chart pixel coordinates may use display floats;
exact accessible tables/tooltips retain source strings. Unit `INR`, `percent`, `ratio`,
`count`, `shares` or `seconds` must be explicit; 0.10 ratio and 10 percent are different.

Instants are RFC 3339 timezone-aware UTC (`Z`/`+00:00`); reject naive timestamps. Session
dates are `YYYY-MM-DD` in `Asia/Kolkata`. Local display uses IST and preserves the date.
Clock filtering for new history queries uses `[from, to)` instants; a UI date-range
selector converts whole IST dates into those bounds and explains them. Research date
ranges use inclusive session-date bounds named `start_session`/`end_session`, not the
same parameters as instant history filters. `event_at`, `available_at`, `observed_at`
and valuation `as_of` cannot be substituted for each other. Server clocks govern expiry;
caller timestamps cannot renew authority or pretend that data was available earlier.

## Bounded reads and pagination

New tables default to 50 rows and cap at 100. Stable order is newest immutable sequence
first with ID tie-break; research ranking uses its declared score then symbol tie-break.
A cursor binds resource/filter/order/account, first-page high-water sequence and snapshot
identity. Subsequent pages exclude later inserts and do not duplicate/skip rows.
Return `next_cursor`, `has_more`, `snapshot_at` and result scope; no unbounded total scan.
Cursor is opaque, validated and expires after a proposed ten-minute snapshot window;
expiry returns `CURSOR_EXPIRED` and refresh restarts page one. This does not replace the
current integer `before` history cursor until a compatible extension is implemented.

Proposed chart response defaults 300/caps 3,000 completed bars. Warmup computation uses
the immutable bundle within an independent declared budget before display truncation;
insufficient history produces null indicators. Actual supported caps are capability
values and require measured acceptance before shipping. Pagination never fills missing
bars; response identifies coverage gaps, partial periods, excluded rows and truncation.
Comparisons use an aligned declared date/basis and disclose missing values. Query/parser
limits and deadlines apply before large file/JSON materialization; allowlisted IDs and
bounded filters prevent arbitrary path/data reads. Existing analysis keeps its current
300 displayed bars/600 inspected minute-row contract.

Initial proposed budgets for new resources are 64 KiB streamed JSON request bodies,
512 KiB table/summary responses and 4 MiB chart responses, with a two-second account-read
deadline and five-second immutable research-read deadline. Larger artifacts use explicit
bounded export streams, not inline report JSON. These are design limits to benchmark and
enforce, not measured latency promises; capacity changes require a capability revision.
The existing 8 KiB secret-entry request limit stays in place. Admission rejects an
oversized request before JSON parsing; exceeding a query budget returns a scoped timeout
or unavailable result without partial financial state. No caller can raise a server cap.

## Errors and recovery

New endpoints use `{error: {code, message, incident_id, retryable, recovery_action,
field_errors}}`. Field errors contain approved field names/reasons, never submitted
secret values. Optional incident IDs reference sanitized local diagnostics; clients
must not parse exception text. Current legacy `detail` errors remain compatible until
adapted explicitly. A source outage/unavailable optional metric may be HTTP 200 with
an unavailable panel; HTTP success is not trade acceptance.

| Status/class | Stable examples | Recovery rule |
|---|---|---|
| 400/422 input | `INVALID_FILTER`, `INVALID_INTERVAL`, `INVALID_SCHEMA` | Correct input; reject extra fields, nonfinite values and caller paths. |
| 401 authentication | `OPERATOR_AUTH_REQUIRED` | Clear tab-private state; unlock explicitly. |
| 403 boundary | `ORIGIN_FORBIDDEN`, `ACTION_NOT_PERMITTED` | No retry; preserve protections and sanitized context. |
| 404 | `RESOURCE_NOT_FOUND` | No private existence leak beyond authenticated scope. |
| 409 state/integrity | `REVISION_CHANGED`, `PREVIEW_EXPIRED`, `IDEMPOTENCY_CONFLICT`, `DEPENDENCY_CHANGED`, `CURSOR_EXPIRED`, `INPUT_INTEGRITY_FAILED` | Refresh/review or inspect evidence; never blind financial retry. |
| 429 capacity/throttle | `JOB_QUEUE_FULL`, `BROKER_RATE_LIMITED` | Retry-After for a bounded safe read or explicit later job start; no auto new mutation. |
| 503 dependency/integrity | `BROKER_UNAVAILABLE`, `STORAGE_UNAVAILABLE`, `ACCOUNT_INTEGRITY_FAILED` | Distinguish local availability from financial fault; integrity faults revoke authority and require verified recovery. |

Broker categories are credential-free `AUTHENTICATION_REQUIRED`, `SESSION_EXPIRED`,
`PERMISSION_DENIED`, `RATE_LIMITED`, `NETWORK_TIMEOUT`, `NETWORK_UNAVAILABLE`,
`PROVIDER_UNAVAILABLE`, `INVALID_RESPONSE`, `MAPPING_CONFLICT`, `UNKNOWN_FAILURE`.
Specific expiry requires recognized broker evidence, not every 403. Unknown permission
evidence stays generic rather than asserting a missing entitlement. Read retries are
bounded, respect capped Retry-After plus jitter/backoff, support cancellation and consume
one process-wide acquisition budget. Token exchange and uncertain confirmations do not
auto-retry. WebSocket bounded reconnect does not renew credentials or automatically
resume revoked paper authority.

## Mutation preview, confirmation and idempotency

Existing guarded operations retain their current schemas. The following is the target
for new consequential workflows; it does not retrofit extra requests onto the emergency
kill path or claim existing endpoints already implement every field.

1. Client submits a strict typed preview request with opaque operation ID and expected
   account/revision plus selected registered policy/artifact IDs. Server validates input,
   coupled constraints and capability, computes exact effects and persists review evidence.
2. Preview returns server-generated `preview_id`, canonical SHA-256 binding, exact proposed
   financial effects/limits, warnings/required unchecked acknowledgements, current revision,
   server `created_at`/`expires_at` (at most 120 seconds) and scoped operation outcome URL.
   It reserves no financial capacity and cannot certify missing calendar/basis data.
3. Binding includes account and operation identity, canonical request, ledger/decision revision,
   policy/charge/model/source/calendar/basis hashes, subscription/connection generation and
   relevant quote IDs/clocks/limits. Select only dependencies material to the operation;
   document them so unrelated polling does not unpredictably expire a preview. Baseline
   quote IDs/clocks identify the reviewed observation for audit; they do not require every
   later market tick to match that observation. A newer usable quote may confirm within
   the original reviewed limits/expiry and valid policy/connection/basis dependencies,
   unless a particular operation explicitly declares same-observation binding.
4. Confirm sends only preview ID/hash, durable operation/idempotency key and explicit strict
   acknowledgement of listed consequences. Reacquire the account lock; check expiry,
   identity/revision/material dependencies and independent risk against current state.
   The current usable quote must satisfy the original maximum quantity/price/cash/risk
   and permitted movement bounds; neither caps nor expiry may be increased by this check.
   An old quote or preview is never a promise of fill/price. Conflicts create no partial financial write.
5. Persist authorization and idempotency outcome atomically with the relevant financial
   command; orchestrated file/network operations record durable phases instead. Same key
   and canonical request returns the durable current result; changed request with same key
   returns 409. Keys are scoped by account/operation, survive restart and are retained with
   financial audit evidence. Never clear one to replay a terminal daily signal.
6. On timeout/lost response, controls show outcome unknown and GET the operation resource.
   A GET cannot restart the command. Completed outcome is displayed; interrupted partial
   outcomes require explicit new review/recovery, not automatic retry. UI cancel closes the
   review without POST confirmation; cancelling a running command is a separate capability.

Modes remain Manual/Approval/Automatic **paper** authorities. A mode label does not
establish quote usability, session/basis readiness or a new eligible signal. An allocation
plan, strategy validation or completed backtest cannot activate a mode. Reports do not
copy research holdings into the operator account. Financial rejection remains explicit
and distinct from transport failure and later execution; current paper-intent rejection
continues its documented HTTP 200 `REJECTED` behavior.

## Bounded jobs and artifact integrity

These proposed initial limits are admission/acceptance targets, not measured capacity:
one running research worker, one queued job; default 15-minute wall budget with a reviewed
configuration ceiling of 60 minutes, 512 MiB worker memory target, 2 GiB output cap and
10 MiB combined sanitized log cap. Reject inputs before starting when estimated workload
cannot fit; inability to enforce a limit on a platform disables the affected capability
until an equivalent bounded runner is verified. Do not advertise these limits as current
behavior. Different workloads may require a reviewed capability revision after benchmarks.

`POST /api/backtests/jobs` accepts immutable dataset/strategy/model/calendar/cost IDs and
their expected hashes, declared session range, method versions and a durable request key.
Never accept paths, secrets, current-account IDs as scratch targets, arbitrary executable
code or unbounded parameter sweeps. Duplicate key/request returns the existing job;
conflict returns 409; full queue returns 429. Submission returns 202 with job/outcome URL.

State transitions: `queued → running → completed|failed`; `queued → cancelled`;
`running → cancel_requested → cancelled|failed`; any nonterminal state on service restart
→ `interrupted`. Completion and cancel race is serialized: a verified published completed
manifest remains completed; a committed cancel request prevents later successful publish.
No automatic restart/resume/new job. Operator can explicitly clone a failed/interrupted
request under a new identity; original outcome and partial evidence remain visible.

Progress carries stage, monotonic completed units/known total, start/update times and
sanitized failure/recovery code; unknown ETA stays null. Cancel POST is idempotent, stops
new work, requests cooperative exit, then terminates the isolated process after a proposed
five-second grace. It never cancels a paper account order. Polling is read-only, backs off
when hidden and cannot revive locked private state.

Each job starts in a new private scratch directory. Registry publication requires matching
request/input hashes, completed-state manifest, schema/strategy/method/cost identities,
reconciliation status for any simulated ledger, output sizes and hashes. Use atomic manifest
publication with directory durability requirements; never interpret a partial CSV as a
successful report. Download/export resolves allowlisted artifact IDs, validates regular-file
identity, hashes/size and byte budget, and sets safe filenames. Unknown/changed output is
unavailable/quarantined; no repair or prior successful status reuse. Retention may remove
explicitly selected research outputs with a reviewable effect, not financial journals or
operator-account evidence. Storage exhaustion yields a failed job without account mutation.

## Implementation acceptance references

- **API-01:** round-trip finite decimal strings, timezone/session boundaries, every null/
  freshness state and independent synthetic financial examples; no loss through browser floats.
- **API-02:** coherent snapshots and stable pagination with concurrent inserts, expired/tampered
  cursors, bounded scans/files, filter changes and lock/late-response clearing.
- **API-03:** preview expiry/revision/dependency conflicts; duplicate/conflicting/concurrent keys;
  response loss and restart; exact independent persisted cash/orders/fills/fees/claims unchanged
  for preview/cancel/rejection, and reconciled for accepted financial operations.
- **API-04:** jobs queue/full/cancel-publish races, process kill/restart/interruption, CPU/memory/
  disk/response bounds, partial manifests, changed inputs, traversal/symlink and no credentials.
- **API-05:** no broker order route or financial command from GET/report/job; incompatible schema
  rejection; harmless optional-report failure isolated while ledger faults still fail closed.
- **API-06:** typed broker 401/recognized expiry/ambiguous 403/429/5xx/timeout/bad JSON/oversized
  streamed body, bounded cancellation/backoff, no secret echo and no token-exchange retry.

These IDs specify future unit, functional, security and independent persisted-state checks.
They are not executed test results. Real broker, rendered browser, target-device resilience
and investment out-of-sample acceptance remain distinct evidence categories.
