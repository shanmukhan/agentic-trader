# Phase 2 — acceptance, fix-first specifications and implementation handoff

Date: 22 October 2026 IST. This is a design-validation and future-test contract.
A specified test is not an executed test. Phase 2 does not run the operator account,
change routes/strategies or certify investment results. Runtime baseline remains 0.14.0.

## What completes Phase 2

- Concrete architecture, module/dependency/authority and migration decisions.
- Twelve grouped destinations with canonical/legacy route ownership, all screen states,
  shared component contracts and a light visual system.
- Versioned financial metric/provenance/null/rounding definitions with independently
  checked synthetic arithmetic examples, never substituted for actual account data.
- Legacy versus proposed long-horizon strategy identities, data/indicator semantics,
  and connected/replay acceptance scenarios. Unchosen investment parameters remain
  explicit activation blockers rather than invented operating defaults.
- Typed API/read/preview/confirm/job/cancellation/restart/error design contracts, clearly
  distinguishing existing endpoints from proposed ones.
- A nonconnected offline prototype and reproducible design checks; future browser,
  financial, broker and device release gates remain separately identified.

The user approved architecture/UX design. These artifacts make the next implementation
review concrete; they do not claim approval or completion of Phases 3–6.

## Design checks that can run now

From the repository root:

```sh
.venv/bin/python docs/phase-2/validate_design.py
.venv/bin/python docs/phase-2/validate_financial_examples.py
node --test docs/phase-2/validate-prototype.cjs
git diff --check
```

These checks validate local document/JSON links, route/alias/section consistency,
explicit proposed scenario identities, key palette contrast pairs, exact synthetic
financial identities and simulated prototype interactions. They require no market
network, credentials, operator database or running application. They do not import
application execution services. HTML/DOM checks do not render CSS or prove accessibility.
The [README](README.md#validation-record) records the actual results when executed.

Phase 1's 660 Python/117 UI tests and approximately 92.13% statement coverage are dated
baseline evidence, not tests rerun or new feature acceptance in this documentation phase.
Do not rerun the entire financial suite merely to claim design work is implemented.

## Fix-first specifications for implementation

| ID / audit reference | Required behavior | Concrete acceptance before release | Scope |
|---|---|---|---|
| FIX-01 / UX-01, A-10 | A shared confirmation helper uses the parent visual viewport/visible frame intersection and positions before focus. | Render each Setup/Risk/Purchases/Strategy dialog at top, middle and deep scroll; 320/360/768/1440px and 200% zoom; long content and mobile keyboard. No intersection safely reveals section instead of opening a zero-height modal. Cancel/Escape/lock/pagehide remove pending UI/listeners; no POST on cancel, one on explicit confirm. Preserve immediate emergency-stop semantics. | First Phase 3 component work; existing Setup patch still needs actual Firefox acceptance. |
| FIX-02 / A-01 | Preparation obtains and explicitly reviews every source year needed for the history window, including December→January. | January/February bootstrap, year-end transition, holiday/special-session/source-year mismatch/insufficient coverage cases. Independent immutable source hashes and correct available-at clocks. Missing prior-year evidence blocks honestly; no weekday-inferred calendar. | Data/preparation correctness, before expanding long history. |
| FIX-03 / A-02, B12 | Connected/replay evaluation consumes the same declared authority, data and quote event tape under a new versioned policy contract. | Expand P01–P15 into deterministic fixtures; compare decision/opportunity/slot/reason/model/risk/quote identities and independently reconstructed ledgers. First-gap rejection, missing-versus-filtered data, late revisions, holds/actions, pause/restart and terminal no-replay. Legacy results never silently relabelled. | New long-horizon contract and parity harness; no silent v1/intraday strategy change. |
| FIX-04 / A-08, A-12, A-14, A-15 | Typed credential-free broker recovery, bounded reads and versioned catalog/operational evidence. | Mock expired/permission/429/Retry-After/5xx/malformed/timeout paths; bounded cancellation/retry; token exchange not replayed; changed catalog retains historical/held identities; secrets absent from files/logs/errors/responses. | Reliability foundation; no authenticated broker actions needed for unit tests. |
| FIX-05 / A-07 | Read-only optional-analysis failure is isolated while financial integrity failure still revokes authority. | Corrupt chart/benchmark source does not mutate/fault financial state; ledger corruption/mutation persistence failure still fails closed before diagnostic I/O. Independently compare database dumps and mode/authorization state. | Domain failure classification, not relaxed financial guards. |
| FIX-06 / A-13 | Characterize the retained intraday benign-repeat false-pause separately. | A narrow future fix must preserve unchanged-repeat no-freshness renewal, real quality rejection and strict same-second liquidity budget; no rearm or new intraday features. Existing and new fixtures independently reconcile cash/orders/fills. | Deferred intraday roadmap; no Phase 2 implementation or automatic scope expansion. |

## Screen and component test matrix

| Contract IDs | Unit/contract checks | Functional/rendered checks | Financial/security gate |
|---|---|---|---|
| INV-UI-01 Dashboard | Metric definition/unit/date/null/freshness mapping; no float round trip | Known/empty/stale/incomplete/failed snapshots, long INR values, next action scope | Pure read; same coherent ledger cut; unknown claims do not become zero; no repeated fee subtraction |
| INV-UI-02 Discovery | Deterministic ranking/ties/filters and evidence reasons | Saved research, no licensed fundamentals, comparison date/basis mismatch, named research watchlist | Read/save watchlist cannot subscribe/install/order; historical membership disclosed |
| INV-UI-03 Analysis | Indicator warmup/gaps/actions/weekly-monthly completion and independent reference calculations | Pan/zoom/keyboard/table, no data, partial period, corrupt data, stale current quote | No synthetic prices, inferred provenance or UI trading authority; no network download on viewing |
| INV-UI-04 Strategies | Strict parameters, version/hash/model compatibility, draft readiness | Draft/validated/backtested/installed/blocked; explicit unset long-horizon inputs | Installation stays Manual; preview/confirmation and existing financial policy binding preserved |
| INV-UI-05 Backtesting | Immutable request/cost/method identity, metric null gates | Queue/progress/cancel/restart/failed/partial reports, valid equity/monthly/benchmark views | Isolated account; no future data or OHLC-only invented execution; cancel cannot publish success |
| INV-UI-06 Paper Trading | Proposal identity, expiry and authority epoch, separate decision/order/fill | Review/decline/expire/cancel/pause/idle, cross-route count | Current server preview/risk, one-shot approval, no terminal signal replay or automatic rearm |
| INV-UI-07 Portfolio | Exact basis/fee/claim/income and allocation denominator | Partial fills/additions/actions/unknown sector/fraction, purchase/SIP review | Independent SQL/ledger reconstruction; no external cash creation, tax-lot or custody claim |
| INV-UI-08 History | Stable filter/cursor/high-water scope and entity labels | Large pages, source/reason details, explicit refresh/export | No order from a proposal/read; exact distinct fees, cash flow and capital P&L |
| INV-UI-09 Risk | Coupled limits, pending/current exposure, unknown classification | Kill/disarm/exit/reset/arm distinctions, blocked input explanations | No bypass/increased risk from missing data or UI edits; preserve existing emergency path |
| INV-UI-10 Broker | Error taxonomy, source/catalog/session states | Wizard edits/progress/failure/recovery; fully visible connection modal | No secret echo, automatic attestation or exchange retry; feed connection is not readiness |
| INV-UI-11 Settings | Redacted config and effective/restart/new-account requirements | Invalid/unsaved/pending changes and lock | No alternate policy bypass, remote binding or live toggle |
| INV-UI-12 Learning | Definitions linked to method/state, synthetic examples labelled | Search/contextual help, focus/touch/keyboard/mobile | No form autofill, approval or investment recommendation from a lesson |
| INV-COMP-01/02/03 | Shared dialog/lifecycle/async/metric/status/table contract | All viewport/focus/cancel/late/empty/stale states | No mutation by render/navigation; unknown outcome read before retry |

## Financial and research gates

1. Reconstruct cash, fees, held basis, fractional basis, realized capital, income and
   claims independently from ordered persisted evidence. Use exact Decimal/Fraction
   fixture arithmetic and production accounting policy separately; comparing an engine
   snapshot to itself is not independent validation.
2. Verify every preview, rejected confirmation, cancel, duplicated/conflicting command,
   crash and timeout against full database evidence. Financial writes either commit the
   related authority/ledger effects or leave a documented durable orchestration phase.
3. Show full valuation/return only when all necessary marks/basis/claims are complete
   and current under the method. Retain known components and last trusted values with
   their original times; never call them a current complete total.
4. Use event and availability clocks, point-in-time membership, known action/fundamental
   revisions and compatible model availability. Perturb future data and prove earlier
   results do not change. Current constituent history must not become unbiased evidence.
5. Benchmark matches dates, currency, source/basis and reinvestment conventions. Missing
   license/coverage or incompatible basis yields null plus reason, not a guessed index.
6. Define eligible daily valuations before annualized metrics. No compounding by summing
   daily percentages, no arbitrary zero for undefined ratios, no dividend/fee double count,
   no CAGR/Sharpe/Sortino claim from a handful of observations.
7. Price-only prototypes/strategies are research hypotheses. Quality/value waits for an
   approved licensed point-in-time source. Performance is never a probability of profit.

## Real-browser and external acceptance

When an isolated supported browser is available, inspect the prototype and subsequently
implemented pages at desktop/mobile sizes against the reference. Test actual keyboard,
focus, 200% zoom, scrolling, reduced motion, mobile keyboard and chart/table alternatives.
The current tool inventory exposes no isolated browser surface; native Firefox is in
use, and previous capture behavior was unreliable. No actual desktop/mobile rendering
is certified by Phase 2's simulated DOM tests. Do not change a user's browser/account
settings or connect a real feed to make a visual test appear complete.

Future market-data acceptance is a separately dated, bounded, operator-reviewed run.
Record source, permission, duration, exclusions, clocks, errors and reconciliation.
Synthetic calculations, historical replay, short packet observations and target-device
operation are different evidence classes. No real broker orders, account changes or
profits are an acceptance output of this modernization.

## First Phase 3 implementation slice

Implement the shared dialog helper and regression coverage first, then adopt the grouped
shell/capability-aware navigation while preserving current aliases, in-memory unlock,
known financial workflows and guarded modes. Add coherent read models rather than fake
values for missing screens. Deliver one reviewed vertical slice at a time with usage/API/
component/changelog documentation and actual test results. Phases 4–6 supply the new
research/portfolio/backtesting behavior; a menu label alone does not complete them.
