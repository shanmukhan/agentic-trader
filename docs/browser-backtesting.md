# Registered browser backtesting — 0.19.0

This is the first Phase 5 implementation slice. **Backtesting** (`/workspace#backtesting`)
now reads a local registry, admits explicitly confirmed isolated daily-replay jobs,
records lifecycle outcomes and exposes verified, bounded JSON reports. It uses the
existing rules-only `daily-delivery-momentum-v1` offline replay. The default strategy
has a **20 reviewed-session holding cap**; this is not a new months-to-years policy.
Connected/replay parity, out-of-sample validation, walk-forward orchestration, browser
ML execution, historical fee accuracy and profitable real-market results are not established.

## Runtime availability comes first

Launch is enabled only after a separate worker proves the required OS sandbox and
hard resource limits. The implemented backend is macOS `sandbox-exec`; other platforms,
including Linux/Raspberry Pi, currently return unavailable for **browser jobs**. Existing
CLI research remains a separate workflow with its existing platform support.

On the implementation Mac, `RLIMIT_AS` setting failed with `ValueError`; the sandbox
probe inside the Codex environment was also denied. Actual isolated-worker execution
on that Mac is **not accepted**. Registration, saved evidence and read-only UI remain
useful while **Job launch unavailable** is shown. Do not loosen limits, bypass the
probe or treat a simulated launcher test as OS isolation evidence. A server restart
reruns capability detection; it never resumes an interrupted job.

The actual configured admission budgets are:

| Budget | Limit |
|---|---|
| Concurrency | One running worker and one admitted queued job |
| Elapsed / CPU time per worker | 60 seconds / 30 seconds |
| Address-space hard limit | 2 GiB |
| Combined registered inputs / individual output file | 32 MiB / 32 MiB |
| Combined worker output / worker log | 128 MiB / 64 KiB |
| Rows per daily/execution input or equity curve | 100,000 |
| Replay universe / execution sessions | Ten symbols / 252 reviewed sessions |
| Retained jobs / registered resources | 100 / 32 |
| Browser request body / public report JSON | 4 KiB / 4 MiB |

Limits fail closed; a large otherwise valid experiment may require the existing direct
CLI instead. No browser upload, filesystem-path selection, URL fetch, arbitrary Python,
serialized executable model or broker login is accepted by this feature.

## Register explicitly reviewed inputs locally

Prepare matching daily and execution bundles as described in [daily-execution.md](daily-execution.md).
The daily universe must declare point-in-time membership. The execution bundle needs
later observed bid/ask quotes and explicit price-basis reviews for each instrument;
daily OHLC bars never supply fills. Review corporate actions, availability clocks,
calendar coverage, excluded observations and source/license declarations first.

From the repository root:

```sh
.venv/bin/trading-agent register-backtest PATH_TO_DAILY PATH_TO_EXECUTION \
  --strategy config/daily-strategy.toml --policy config/long-term.toml \
  --label 'Reviewed delivery research, source version and period'
```

`PATH_TO_DAILY` and `PATH_TO_EXECUTION` are local input directories. `--strategy` and
`--policy` are required TOML paths; policy must have `investment_horizon = "long_term"`.
The label must contain one to 120 characters. The global `--config PATH`, before the
command, selects the application's configured registry default; `--policy` selects
only the experiment's economic policy. With no `--registry`, storage is the configured
account database path with its suffix replaced by `.research-jobs`. To see registration
in a running workspace, use the same configured registry. An explicit `--registry PATH`
can prepare a separate private registry, but the browser cannot switch to it.

For **synthetic software practice only**, create a fresh fixture:

```sh
.venv/bin/trading-agent daily-execution-demo --directory data/browser-practice-first
.venv/bin/trading-agent register-backtest \
  data/browser-practice-first/inputs/daily data/browser-practice-first/inputs/execution \
  --strategy config/daily-strategy.toml --policy config/long-term.toml \
  --label 'SYNTHETIC practice; not market evidence'
```

The demo itself creates isolated research outputs; registration never starts a browser
job. Use a new demo directory. The command prints the resource identifier/hash,
strategy, economic policy, coverage, source hashes and limitations. It copies only the
four dataset files into owner-private storage and retains validated strategy/economic
values, complete observed fee schedule, implementation hash and source hashes.
The fee version, observation date, rates, GST, stamp duty and delivery DP assumption
appear in input/confirmation review. These are conservative paper assumptions, not
historically dated contract-note accounting. Raw policy/config files, operator paths
and credentials are
not copied into the public resource. All relevant metadata is bound to its identity.
Changing inputs or review metadata requires another registration and review.
Changing application Python code or fee assumptions also requires registration/review
again; admission and worker startup reject a resource bound to a different runtime.
Existing saved reports retain their original runtime identity and are verified against it.

Registration never opens the operator account, connects a broker, changes subscriptions,
installs a strategy or alters virtual capital. It rejects oversized/changed/symlinked
inputs, invalid manifests, incompatible sessions and insufficient quote/review coverage.
Inspect the failure, correct the source bundle deliberately, then retry registration;
do not edit an already registered resource to make its checks pass.

## Review, launch, refresh and cancel

1. Start/restart the owning UI normally with `./scripts/start_ui.sh`, unlock with the
   local operator token and open **Backtesting**. An older process must be restarted
   explicitly to load the new routes; no account or service is restarted by registration.
2. Select **Refresh jobs and inputs**, then choose a registered bundle. Inspect its
   exact identity, synthetic declaration, period, symbols, holding cap, policy, costs,
   provenance and runtime limitations. Empty state means no registration, not no trades.
3. When capability is available, select **Review isolated run**, read the confirmation,
   tick its acknowledgement and select **Start isolated run**. Cancel/Escape submits
   nothing. The confirmation creates research work only; it cannot arm paper modes.
4. Saved jobs remain `queued`, `running`, `succeeded`, `failed`, `cancelled` or
   `interrupted`. Stage is evidence, not a forecast: the browser infers no percentage
   or ETA. Visible, unlocked pages refresh job state every 15 seconds, backing off to
   120 seconds on failed reads. Hiding/locking stops polling and clears private content.
5. **Review cancellation** requires its own acknowledgement. A running worker is
   terminated and its durable outcome remains cancelled. Cancellation cannot cancel
   an order, sell holdings or change the connected account. Completed outcomes are retained.

A secure request key binds the reviewed resource hash. A network failure after submit
can mean the request reached the server. Refresh saved jobs first. If the same key is
found, use that recorded job. If not found, the UI permits a separately reviewed retry
with **the same key and hash**; it never automatically resubmits or silently chooses a
new key. The same request returns the existing job even after restart; reusing a key
for another resource conflicts. Locks/navigation may discard an unconfirmed local form;
lock does not cancel already accepted server work.

## Inspect a result without turning it into authority

Only a `succeeded` job exposes **Inspect recorded report**. Publication requires the
finished manifest, exact artifact hashes, request/strategy/policy identity and a read-only
SQLite integrity/accounting reconciliation. Saved report reads verify evidence again.
A successful worker is distinct from the report's complete/incomplete research gates.
Changed or corrupt evidence produces an unavailable/error state rather than a replacement
value. Raw SQLite, executable HTML and arbitrary artifact paths are never served by this API.

The page displays recorded exact summary/final-snapshot strings, synthetic/source labels,
reproducibility hashes, bounded event-time equity/drawdown tables and recorded orders/fills.
Curve history is bounded to the last 3,000 rows; orders/fills/trades to 1,000 each, with
explicit truncation. Retained local artifacts contain the full evidence. Reports retain
unfilled/rejected orders; an order acceptance is not a fill. Decimal amounts are not
converted through JavaScript floating-point money.

Existing `equity.csv` is **event-time evidence**, not accepted daily valuation cuts.
CAGR, Sharpe, Sortino, monthly returns and portfolio benchmark results therefore remain
unavailable in these reports. See [portfolio-analytics.md](portfolio-analytics.md) for
implemented metric gates and the required future source history. Same-resource comparison
requires matching resource hash and `legacy-offline-v1` semantics; incompatible experiments
are blocked, and comparison establishes no strategy or market validation.

## Failure and recovery

- **Isolation unavailable (503):** keep launch disabled; use the direct CLI consciously
  under its documented separate isolation boundary, or complete platform acceptance.
- **Queue/storage full (429):** inspect retained jobs. Wait for work to finish; retained
  evidence is not automatically deleted. No UI deletion/retention migration is supplied.
- **Changed resource/hash (409/503):** inspect source integrity and register corrected
  evidence again. Do not approve changed data using an old request key.
- **Research version changed (409):** re-register the reviewed inputs under the current
  implementation and fee schedule, inspect the new identity, then explicitly start a new job.
- **Failed worker/limits/verification:** the job is failed with no published report.
  Inspect local trusted diagnostics and inputs before explicitly starting another experiment.
  Worker errors are sanitized; no raw credential/path-bearing traceback is returned.
- **Server stop/restart:** queued/running work becomes interrupted; no automatic resume,
  retry, replay or publication occurs. Review evidence and explicitly create new work.
- **Read error or lock:** the page labels stale/unavailable or clears data. Refresh is
  a read, not a retry. Report and resource failures never invoke account mutation recovery.

The browser/API lifecycle and accounting tests use local synthetic fixtures and simulated
launches. A limited desktop Firefox smoke check used a disposable synthetic account to
verify registered-input/unavailable-launch states and the allocation view; its server and
tab were closed. Populated report/mobile/keyboard/zoom acceptance, real OS denial/budget
enforcement,
real broker/data entitlement, target-device performance and long-running operational
acceptance remain separate gates. No user-account activation or real order is part of this slice.

## Reading results in the updated interface (0.19.0)

Saved job cards lead with the registered bundle label and actual lifecycle state.
Expand **Job identity** for the full job ID. Comparison selectors retain full job IDs
alongside bundle names, so two runs of the same inputs remain distinguishable.

A recorded report keeps its summary, valuation limitations and provenance visible.
Expand **Equity history and valuation coverage**, **Drawdown history and valuation
coverage**, **Recorded simulated orders** or **Recorded simulated fills** for the
exact tables. Each table scrolls in a labelled, keyboard-focusable region; expanded
histories have a bounded height and sticky column headings. Closing a disclosure
changes only the display. **Local registration and CLI help** is also expandable.
No launch, cancellation, retry or comparison contract changed; unavailable worker
isolation still blocks launch. Automated checks include safe bundle labels, complete
identity and existing exact report/comparison behavior. See [validation](test-plan.md).
