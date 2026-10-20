# Local preflight and external paper acceptance

Version 0.4.1 implements the next locally verifiable part of Phase 4 acceptance:
read-only deployment/account diagnostics and clearer operator supervision. It does
not complete empirical broker, model, fill-calibration or physical-device acceptance.
Those require actual observations. No local report can approve live execution.

## Run a local preflight

Use the same config, Python environment and private environment variables as the
service, from the repository root:

```sh
.venv/bin/trading-agent --config config/paper.toml preflight
.venv/bin/trading-agent --config config/paper.toml preflight --strict
.venv/bin/trading-agent --config config/paper.toml preflight --output data/preflight-first
```

Choose a new output directory every time. `report.json` is the machine-readable
result; `report.md` is its review table. Both are created mode 0600 in a mode-0700
directory. `manifest.json` is written last with SHA-256 hashes of both reports.
An interrupted/failed output is not accepted merely because its directory exists;
require the finished manifest, matching hashes and the original successful command.
Hashes detect accidental changes; they do not authenticate a malicious local editor.
Keep evidence private because it contains account balances and platform information.

Without `--strict`, exit 0 means diagnostics were produced, including blocked checks.
With `--strict`, exit **2** means one or more required local checks were blocked;
the JSON/report remains available. Command/config/output failures exit **1** with a
sanitized error. `local_checks_passed` considers only rows with `required: true`.
Optional checks can remain blocked/unverified even when local checks pass.

## Checks and interpretation

| Check | Meaning |
|---|---|
| Python | Supported Python 3.13.x; the locked local environment uses 3.13.16 |
| SQLite WAL fix | Recognizes official 3.51.3+, 3.50.7+ on branch 3.50, or 3.44.6+ on branch 3.44 |
| Operator token | Validated configuration contains a private token; no token value is emitted |
| Paper/loopback | Existing typed settings require paper mode and loopback binding |
| Reviewed calendar | CSV parses without unknown/duplicate dates or missing source references |
| Today's session | Informational: reviewed current IST date exists; `calendar_open_now` is separate |
| Disk | At least 1 GiB free on the account volume, a floor rather than retention capacity planning |
| Existing/private account | Regular non-symlink account; database and immediate directory deny group/other permissions |
| Integrity/accounting | Schema v1, SQLite integrity and exact fill-ledger/cash/cost/fee/reservation reconciliation |
| Durable identity | Starting cash, economic-policy hash, charge version and model/automation marker structure match |
| Stream catalog | Distinct selected tokens exist in stored catalog; required for controller-bound accounts |
| Flat account | Informational: remaining holdings/pending orders need review and are preserved |

The SQLite version rule follows the [official WAL-reset advisory](https://www.sqlite.org/wal.html#walresetbug).
Unknown distribution backports are not assumed fixed. Obtain a supported patched
runtime or independently review vendor evidence; do not edit version strings to
bypass the diagnostic. This project's Python lock does not pin an OS SQLite library.
The local interpreter reports SQLite **3.53.1**; the target Pi must be inspected itself.
The check does not establish the absence of all future SQLite advisories.

The report does not import a broker client or send a network request. Credentials
being present would not establish validity, expiry, account entitlement or full feed
quality. It does not load/approve a model, replay history, check current stream
freshness, match the complete intended controller configuration, arm/reset anything,
or change account records. Actual service startup still enforces the full bound
strategy/feed/model/calendar identity; paper arming adds runtime readiness checks.

## Safe inspection of a running account

Unlike `status`/`verify-db`, preflight does not construct `Database` or `PaperBroker`,
initialize tables, take process ownership or cancel pre-existing pending orders.
It opens an existing SQLite URI with `mode=ro`, enables `query_only`, disables trusted
schema expressions and reads a single transaction including committed WAL contents.
Paths are URI escaped. Missing accounts are reported and never created.

Normal SQLite locking and WAL coordination remain enabled: `immutable=1` and
`nolock=1` would be inappropriate for a changing service account. SQLite can coordinate
or create WAL shared-memory sidecars; the claim is no SQL/account mutation, not zero
filesystem activity. Do not remove sidecars or copy only the main database file.
See SQLite's [read-only URI](https://www.sqlite.org/uri.html) and
[WAL read-only/concurrency guidance](https://www.sqlite.org/wal.html).

Database queries have a one-second lock wait and a five-second processing deadline
checked by SQLite's progress handler and after reconciliation. Deadline expiry,
busy/corrupt/unsupported state or I/O failure blocks the check without repairing it.
The deadline is cooperative and is not a hard limit on a stalled OS/filesystem call.
Read-only integrity checks still consume I/O and can delay WAL recycling; run them
outside busy entry periods. This is an on-demand diagnostic, not a hot-path poll.
For a large account that exceeds the budget, preserve it and follow the reviewed
maintenance/backup process rather than relaxing financial integrity checks.

## External acceptance record to complete

Keep a private acceptance folder for the actual account/device. Record operator,
UTC/IST observation interval, code revision, Python/OS/CPU/SQLite versions, reviewed
calendar/universe, fee version, risk/controller/model identities, commands, expected
outcomes, observed outcomes and paths/hashes of supporting artifacts. Retain failed
and unfavorable observations as well as successful ones.

1. **Actual read-only session:** manually authenticate, verify the intended profile
   without publishing personal details, fetch completed history, and observe full
   quotes with catalog/timestamp/depth checks. Test missing/expired credentials and
   entitlement failures. The existing fixtures do not establish broker acceptance.
2. **Target device and recovery:** install the frozen broker/runtime environment on
   the actual ARM64 Pi or service Mac. Capture preflight output and dependency audit,
   run existing paper drills/benchmarks, install the reviewed service template, test
   reboot/network interruption and verify account/kill/pending-entry behavior. Rehearse
   backup restore to a new account path. Physical power/storage tests need disposable
   paper accounts, preserved evidence and verified recovery, not the only copy.
3. **Empirical strategy/model/fill evidence:** follow the [research](backtesting.md)
   and [ML](ml-research.md) workflows on reviewed raw data. Retain chronological
   selection/exclusion, corporate-action/universe decisions, actual fee review and
   depth/adverse-fill calibration. Synthetic profitable examples are not evidence.
4. **Sustained supervised feed:** follow [paper-feed.md](paper-feed.md), explicitly
   arm only after readiness, record actual full-session coverage and interruptions,
   then stop and generate `paper-report`. Review its preliminary gates and measurement
   limits. Counts of dates alone do not establish full coverage or empirical approval.
5. **Operator devices:** use [operator-console.md](operator-console.md) to check actual
   desktop/mobile layouts, lock/unlock, stale/network-loss handling and confirmation
   behavior in an isolated virtual account. Verify the private access path separately.

These are operator-run acceptance procedures, not automatically certified assertions.
`external_acceptance_verified` and `ready_for_live` remain false in every preflight
and paper report. Future live infrastructure/pilot phases remain separate work under
the explicit scope gates in [implementation-plan.md](implementation-plan.md).

## Long-term extension acceptance (LT1 / 0.5.0)

Preflight now checks stored horizon and the appropriate charge version. Legacy absent
horizon is intraday only; it cannot approve a long-term configuration. Full startup
still enforces pending-order protection, selected coverage of held symbols, pinned
used calendar definitions and long-term marker/ledger reconstruction.

LT1 delivers overnight paper mechanics, not actual delivery-product acceptance.
`long-term-report` preserves source orders and records observed marks, DP days and
quarantine/unresolved holdings. Require separate evidence for corporate-action cash/
share adjustments, actual custody/sellable quantities and settlement, daily strategy/
ML/portfolio validation, account-specific costs and combined capital allocation.
Operator no-action reviews and synthetic drills cannot satisfy those gates.
The [extended roadmap](implementation-plan.md) identifies LT2–LT4 and retains the
original future live approval/validation boundary. See [long-term.md](long-term.md).

## LT2 paper corporate-action acceptance (0.6.0)

Engineering tests cover reviewed split/bonus quantities, fractional basis/claims,
dividend withholding/receivables, later sale/payment, exact once-only receipts,
failed-write rollback, corruption, restart/exit quantity, used-calendar checks,
read-only preflight reconstruction, CLI ownership and backup/restore. The invented
full lifecycle ends at ₹25,029.42 with no open holding or claim. This is software
behavior evidence, not verified broker/registrar/bank or tax/settlement evidence.

For real read-only acceptance, retain actual issuer notices, correct ex/record/
credit/payment dates, reviewed net deductions and custody/receipt reconciliation.
Test unsupported/fractional combinations by leaving quarantine unresolved. LT2
supports only the documented paper action subset and does not satisfy LT3 strategy
or LT4 custody/device/feed gates. See [corporate-actions.md](corporate-actions.md).

## LT3a daily data/screen acceptance (0.7.0)

Local software acceptance covers future-prefix feature invariance, late basis/price
exclusion, historical universe removal/re-entry, missing-session reset, neutral
split/dividend wealth math, malformed/ambiguous input and unchanged-source evidence.
The six-symbol ninety-session demo includes qualifying, unfavorable, thin, missing,
re-entry and excluded examples. It does not establish empirical strategy/model
performance. Actual source/calendar completeness, point-in-time notices, benefit
units and receipt clocks require external review; future quote-executed daily
strategies/ML and actual device/browser checks remain pending.

## LT3b daily execution/model engineering acceptance (0.8.0)

Software evidence covers later quote/depth fills, exact cash/fees/reconstruction,
overnight/session-horizon exits, sourced split integration, original dividend/payment
routing, source contradictions, censored independent intervals, audit/model tampering,
chronology/purge, train-only fitting, failed gates, after-validation model availability,
CLI isolation and clear responsive report states. An invented fifty-session experiment
provides 150 standalone outcomes and a distinct later ten-session scored replay.
Synthetic statistical checks do not establish a market edge.

Actual reviewed daily/quote coverage, PIT universe/action notices, matching historical
costs, empirical sample/model performance, custody/settlement and target-device/browser
pixel/handset acceptance remain pending. Daily models stay offline. The next code
milestone is LT3c lot/SIP/rebalance/aggregate capital. Workflow and explicit limitations:
[daily-execution.md](daily-execution.md).
