# Investment policy drafts and review-date previews — 0.19.0

**Strategies → Create or inspect investment policy drafts** opens
`/workspace#strategies/investment-policy`. This is a separate planning workspace for
months-based or multi-year horizons and monthly or quarterly reviews. Each draft
chooses one horizon unit and one cadence; you can save separate alternatives to
compare your intended configurations. Every parameter starts unresolved. Values in
this guide describe accepted inputs, not recommended financial limits.

A saved draft cannot install a strategy, activate Approval/Automatic, submit an order,
connect a broker or run a backtest. The existing installed strategy and legacy replay
keep their current holding-session semantics. A fully specified draft records choices;
it establishes neither strategy implementation nor suitability, profitability or
complete source coverage. Full Phase 5 execution, parity, OOS/walk-forward, target
allocation/rebalancing and platform acceptance remain open.

## Create, review and save a draft

1. Load the current UI with `./scripts/start_ui.sh` and unlock the workspace with its
   local operator token. Restart an older owning process explicitly if it has not loaded
   these routes. Open **Strategies**, then **Create or inspect investment policy drafts**.
   Existing strategy preparation, shortlist links and legacy routes remain available.
2. Optionally name the draft, then use the four step buttons: **Horizon**,
   **Screening**, **Allocation**, and **Exits**. Only the selected group is shown.
   **Previous group** and **Next group** move focus to its fieldset. Progress counts
   entered choices; it does not certify validity. Navigation never sends a preview
   or save, and your unsaved entries persist across groups. Empty fields stay null;
   no strategy, duration, return target or reserve is silently selected. You may save
   an incomplete draft while researching the remaining decisions.
3. Select **Review all choices**. Local checks flag invalid ranges, precision and
   allocation relationships and focus the first affected input, including hidden
   groups. Clear an invalid field to keep it unresolved. The server still validates
   every entered choice, normalizes exact decimal strings and returns a preview. It writes no draft record. Read the exact
   values, unresolved fields and reproducibility identities in the confirmation.
4. Check **I reviewed this draft snapshot and its limitations**, then select **Save
   draft snapshot**. Cancel/Escape saves nothing and leaves your unsaved form available.
   A successful save lists an immutable private snapshot and its `draft-…` identifier.
   The account's installed strategy, mode, cash, holdings and connection are unchanged.
5. Select **Edit a copy** to use a saved snapshot as an unsaved starting point.
   A changed value or name produces another snapshot when reviewed and saved. Saving
   the same canonical content returns the existing snapshot instead of duplicating it.

Menu navigation blocks while the form has unsaved choices, a review is open, a request
is pending or a save outcome is uncertain. Save or **Discard changes / start fresh**
before leaving through the workspace menu. **Lock**, authorization failure and
page exit clear private form/preview state; they do not undo an already received save.
The form is memory-only until explicitly saved. The browser's standard unload warning
is requested while edits, review, requests or uncertain outcomes remain; choosing to
leave still discards that local state. Reload does not recover unsaved edits.

## Inputs and exact values

The schema is `1`, family `nse-investment-policy-v2`, with proposed decision semantics
`investment-decisions-v2.1`. All 25 parameters are nullable. A non-null invalid value
is an error, never reclassified as an unresolved choice. Unknown fields and unsupported
options are rejected. Integer inputs must be actual integers. Decimal API/file inputs
must be strings: JSON floats, integers, booleans, NaN and Infinity are not accepted as
decimal values. The browser uses text inputs for decimal fields and BigInt for exact local checks.
Changing the horizon unit changes the displayed bounds (1–100 years or 1–1200 months)
without converting or resetting your count. Inspect the number before review.
Saved snapshots show a labelled exact-value table; expand their details for all
choices and the complete snapshot identifier.

Percentages and basis points use up to four decimal places; turnover uses up to two.
Redundant trailing zeros normalize, while extra nonzero precision is rejected instead
of rounded. Equivalent exact
spellings normalize to fixed scale: `"2.5"` becomes `"2.5000"`, turnover `"100"`
becomes `"100.00"`, and negative zero becomes positive zero. No commas or embedded
whitespace are accepted. Decimal strings are limited to 80 characters and any exponent
to −18 through 18; ordinary fixed-point strings are easier to review.

| Group | Parameter | Accepted non-null input |
|---|---|---|
| Horizon and reviews | `horizon_unit` | `months` or `years` |
| Horizon and reviews | `horizon_count` | Integer 1–1200 months or 1–100 years, according to the chosen unit |
| Horizon and reviews | `review_cadence` | `monthly` or `quarterly` |
| Horizon and reviews | `review_session_rule` | `first_reviewed_session` or `last_reviewed_session` |
| Horizon and reviews | `missed_cycle_policy` | `skip`; no catch-up review is invented |
| Screening | `price_basis` | `share_adjusted_close` |
| Screening | `strategy_mode` | `rules_only` |
| Screening | `momentum_sessions`, `trend_sessions` | Each an integer 2–1000 completed sessions |
| Screening | `min_momentum_pct` | Decimal string −100 through 10000 percent |
| Screening | `min_average_turnover` | Decimal string 0 through 1000000000000 INR, scale 2 |
| Screening | `max_daily_volatility_pct` | Decimal string greater than 0 through 100 percent |
| Allocation | `cash_reserve_pct` | Decimal string 0 through 100 percent |
| Allocation | `max_invested_pct`, `max_stock_weight_pct`, `max_sector_weight_pct` | Each a decimal string greater than 0 through 100 percent |
| Allocation | `max_positions` | Integer 1–10 |
| Allocation | `unknown_sector_policy` | `block_new_entries` |
| Execution and exits | `max_entry_gap_bps` | Decimal string greater than 0 through 5000 basis points |
| Execution and exits | `stop_pct` | Decimal string greater than 0 and less than 100 percent |
| Execution and exits | `target_pct` | Decimal string greater than 0 through 1000 percent |
| Execution and exits | `max_drawdown_pct` | Decimal string greater than 0 through 100 percent |
| Execution and exits | `screen_exit` | `request_exit` or `hold` |
| Execution and exits | `universe_exit` | `request_exit` or `block_for_review` |
| Execution and exits | `horizon_action` | `request_exit` or `review_only` |

Entered limits must agree even in an incomplete draft: maximum invested allocation
plus cash reserve cannot exceed 100%; stock and sector caps cannot exceed the invested
cap; stock cap cannot exceed sector cap. These are proposed ceilings, not instructions
to fill each cap. This form supplies no sector classifications or financial source data.
An optional label is at most 120 characters, trimmed, with control characters rejected.

## Identity and private persistence

`draft_sha256` binds the canonical parameters, schema, family and decision semantics in
the `agentic-trader.investment-policy` hash domain. It excludes the display label,
paths, time and storage metadata. It exists for incomplete drafts too. Only a draft
with no missing fields receives `policy_version_id`, equal to that semantic hash.
The state then becomes `specified`; activation/backtest support remains false.

`preview_sha256` binds the entire normalized reviewed draft, including its name and
limitations. Save requires that exact hash and `acknowledged: true`. A changed preview
returns conflict rather than saving different choices under an old confirmation.
`draft_id` is `draft-` followed by the preview hash. Renaming a copy changes its saved
snapshot identity while retaining its parameter identity.

Saved JSON records live in a separate owner-private directory derived from the configured
account database by replacing its suffix with `.investment-policies`. The store validates
record content and identity again on reads, rejects symlinked/unsafe storage, serializes
saves and publishes records without overwriting existing snapshots. Limits are 100 saved
drafts, 32 KiB per record and 1 MiB combined record content. There is no UI deletion,
retention migration or active-policy write. Opening, listing and previewing drafts do
not create that storage; saving is the persistence action.

## Inspect a local draft or preview review dates

Create your own UTF-8 JSON file containing only optional `label` and `parameters`.
For example, this deliberately incomplete file selects scheduling choices while leaving
all financial inputs unresolved:

```json
{
  "label": "Scheduling example; not an active policy",
  "parameters": {
    "horizon_unit": "years",
    "horizon_count": 2,
    "review_cadence": "quarterly",
    "review_session_rule": "last_reviewed_session",
    "missed_cycle_policy": "skip"
  }
}
```

Inspect it without saving or opening an account:

```sh
.venv/bin/trading-agent investment-policy /absolute/path/to/draft.json
```

The command prints the canonical inspection and identities under `draft`, original-file
hashes under `input_sha256`, and `schedule: null` when no calendar is supplied. It also
reports `account_changed: false` and `execution_authorized: false`. Input reads are bounded
to 32 KiB for the draft and 128 KiB for the optional calendar; ambiguous/duplicate JSON
keys and nonfinite constants are rejected. To add a pure calendar preview, supply
**all three** explicit scheduling arguments:

```sh
.venv/bin/trading-agent investment-policy /absolute/path/to/draft.json \
  --calendar /absolute/path/to/reviewed-calendar.json \
  --start 2026-11-01 --as-of '2026-10-22T12:00:00+05:30'
```

The calendar object accepts exactly these fields:

```json
{
  "coverage_start": "2026-11-01",
  "coverage_end": "2028-12-31",
  "sessions": [],
  "known_at": "2026-10-22T09:00:00+05:30",
  "reference": "Illustrative empty declaration; replace with reviewed complete evidence"
}
```

This empty illustration declares **no sessions**; it is not an NSE trading calendar.
For useful planning, supply the actual reviewed sorted, unique session dates within
the inclusive coverage bounds, at most 5,000 dates. The dates must use canonical
`YYYY-MM-DD`; `known_at` and `--as-of` must be offset-aware ISO timestamps. `reference`
must be nonblank, at most 500 characters. The coverage bounds are your assertion of
continuous complete coverage, explicitly labelled unverified by the software. A source
reference does not independently certify exchange openings, holidays or future sessions.
This declaration is separate from, and never installs, the account's exchange calendar.

The schedule uses calendar months/years and preserves the original day where possible:
31 January + 1 month clamps to February's last day; + 2 months is 31 March. A leap-day
year anniversary clamps only in its destination year. `start` is inclusive; the
anniversary `horizon_end` is exclusive. This is a planning boundary, not a minimum
holding guarantee, mandatory liquidation time or forecast of profitable returns.

Reviews align to full calendar months or calendar quarters. Selecting the first/last
reviewed exchange session requires coverage of the **entire period**, including dates
before the start or after the horizon boundary. A first candidate before start or a
last candidate at/after end is skipped. There is no later catch-up date. A fully
covered period with no declared sessions is `no_session`, never a weekday guess.

The stdout schedule reports required coverage, exact period/candidate/review dates,
availability/reason codes, the source declaration and `execution_authorized: false` /
`policy_activated: false`. `available` means every cycle is resolved, including explicit
skips and no-session periods; it grants no financial authority. `partial` preserves
unresolved periods. Missing five scheduling choices, future-known calendar evidence,
coverage gaps and horizons exceeding the 400-cycle limit remain explicit unavailable
states rather than truncated or inferred schedules. The command writes no report,
draft, account, calendar installation or scheduled task, and performs no download.

## Failure and recovery

- **Invalid draft (422):** correct the entered type, bounds or conflicting allocation
  limits, then preview again. Valid entered values do not supply missing choices.
- **Preview changed (409):** review the current complete snapshot again. Do not reuse
  a confirmation hash after changing its label or parameters.
- **Save outcome unknown:** the request may have reached the server. Select **Refresh
  saved drafts** first. A matching snapshot resolves the uncertainty. If absent, use
  **Review retry of the same draft** to confirm that same content/hash explicitly.
  There is no automatic POST retry or silent new identity.
- **Saved read unavailable (503):** retain the error/stale label, inspect trusted local
  storage permissions/integrity and refresh after resolving it. Do not edit hash-bound
  records to bypass validation; there is no account fault recovery on this path.
- **Storage full (429) or record/request too large (413):** inspect the supplied limits.
  No automatic deletion or quota expansion is performed; retention tooling is future work.
- **Missing schedule fields:** fill the five scheduling choices before expecting dates.
  Other financial choices may remain null for a date-only preview.
- **Calendar not known at `as_of` or incomplete period:** review the actual evidence and
  supply appropriate coverage/clock values. Do not shift availability times or fabricate
  sessions merely to clear the warning. A malformed calendar or naive timestamp fails
  validation; a valid-but-insufficient calendar returns explicit unavailable periods.
- **Cycle limit/range exceeded:** choose an explicitly reviewed shorter preview or retain
  the unavailable result. The draft's permitted holding horizon can exceed this bounded
  schedule-preview capacity; no hidden truncation occurs.

## Validation boundary

The pure policy contract has 132 unit cases covering independent semantic hashes,
both horizons/cadences, no financial defaults, canonical decimal arithmetic under a
hostile host context, input immutability, schema/type/bound failures and coupled limits.
Schedule checks use synthetic calendar declarations, including end-of-month/leap-day,
coverage, knowledge clock, skipped/no-session periods and cycle bounds. Store/API/UI
checks cover persisted identity, save conflicts/idempotency, safe failures, navigation,
confirmation and private-content clearing. The integrated v0.18 validation record belongs
in [test-plan.md](test-plan.md); prior v0.17 counts are historical.
Final checks: **1,213 Python / 186 UI tests**, **92.13% statement coverage**,
Ruff/format/mypy passed. A disposable desktop Firefox check covered blank/explicit
choices, deep-scroll review, Escape, confirmed saving, reload/lock privacy, persisted
snapshot recovery and returning to the existing strategy setup. Independent private
JSON/SQL checks verified the draft and unchanged virtual accounting; the preview server
and tab were closed. Mobile/touch, broad keyboard/zoom and second-engine checks remain open.

These are local/synthetic software checks, not real-market, broker/device, future-calendar
or investment-policy execution acceptance. The v0.17 isolated-job capability still fails
closed on the implementation Mac; this feature does not enable it or adapt this new
policy family to legacy replay.

## Usability validation (0.19.0)

The four-step flow adds controller checks for blank defaults, focus/progress, value
retention without requests, unit bounds, exact precision and coupled limits, saved
value labels, correction feedback and lock clearing. Existing acknowledged save,
unknown-outcome reconciliation, navigation guards and immutable persistence tests pass.
Desktop Firefox on a disposable empty account verified the group transition, a
100.0001% combined allocation error, corrected exact preview, deep-scroll native
dialog and Escape without save. This run saved no policy and made no account changes.
See [the current combined validation record](test-plan.md).
