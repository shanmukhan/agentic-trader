# Daily delivery execution and model research: LT3b usage

Version 0.12.0 adds a separate connected paper decision workflow in
[Trading desk](trading-desk.md). It reuses reviewed prior-daily screening and the
strict daily model loader, then sends approved/automatic proposals through the same
paper risk broker. The existing offline replay/model evidence remains separate.
Source/class/calendar/basis/model reviews are required, and code installation does
not supply current-market qualified profit evidence or enable real orders.

Version 0.8.0 adds offline quote-executed daily strategy research, independent
delivery outcome labels, separate chronological daily ML and a later scored replay.
Use Python 3.13.16 and the existing `.venv`; `uv sync --frozen --all-extras` includes
the optional training and test packages. Pure Python model loading/scoring does not
import NumPy or scikit-learn. No broker credentials or operator token are needed.

These commands remain paper research and cannot arm an account, submit broker orders
or allocate real money. Version 0.12.0 can consume a matching validated real daily
artifact through its separate Trading desk profile and paper authority/risk gates. A completed result
means the documented internal checks passed, not that a strategy is profitable or
accepted for deployment. Intraday research and its model namespace remain separate.

## 1. Run the complete invented example

From the repository root, choose a new output directory:

```sh
.venv/bin/trading-agent daily-execution-demo \
  --directory data/daily-execution-first --with-ml
open data/daily-execution-first/portfolio/index.html
open data/daily-execution-first/labels/index.html
open data/daily-execution-first/model/index.html
open data/daily-execution-first/scored/index.html
```

On Linux, open those files with the desktop browser/file manager. Each HTML file is
self-contained and uses no network. The demo creates its own inputs and accounts;
it does not open `data/paper.sqlite3` or `data/long-term.sqlite3`. Omitting `--with-ml`
runs portfolio replay and labels only. Reusing an output directory fails rather
than overwriting an experiment. Do not delete unfavorable experiments to improve
reported results.

The fixture has 55 daily warmup sessions, 50 execution sessions, three invented
symbols, explicit daily reviews and four quote observations per symbol/session.
One path hits an adverse stop; two hit favorable targets. Expected software checks:
150 standalone completed labels (100 target positives, 50 adverse negatives),
passing demonstration walk-forward/holdout checks, a failed `non_synthetic` gate,
and a separate ten-session scored replay. The invented path deliberately makes
these checks deterministic; its P&L, accuracy and sample size are not market evidence.
`summary.json` summarizes the run. Every `ready_for_live` flag remains false.

## 2. Understand the four dashboards

Open the neighboring `index.html` from each output directory. This is responsive
desktop/mobile **browser UI**, not a native app or a live account screen. It has no
operator token, trading buttons or automatic refresh. Physical-phone/pixel acceptance
is pending; automated DOM behavior and packaged assets are tested.

| Report | Main information | How to act on it |
|---|---|---|
| Portfolio / scored | Observed net liquidation P&L, fees, completed trades, open positions, pending orders, unpaid claims and freshness | Inspect all failed checks and decisions before interpreting returns |
| Labels | Completed and excluded/censored trials; portfolio return explicitly not measured | Read `label_audit.jsonl`, including missing outcomes and capacity exclusions |
| Model | Final holdout pass/fail, ROC-AUC and selected independent-label P&L | Inspect each chronological split; failed checks block model loading |

The evidence view switches between completed trades and all decisions. Search by
symbol or reason; **Clear search** restores the full view and keyboard focus.
Validation shows split windows, counts, AUC/Brier, calibration error and selected
label P&L. Tables show at most 200 matching rows and disclose the full count; all
records remain in JSON/JSONL. Scroll wide tables on small screens or with keyboard
focus. Expand policy/model details and limitations for context.

Money is formatted from exact decimal strings, including values beyond JavaScript's
safe integer range. Statistical feature/probability values use floating point.
Times display in IST. Untrusted values render as text under a hash-bound CSP.
If scripts are disabled, read the adjacent Markdown and JSON evidence.

## 3. Prepare two matching reviewed input bundles

First prepare the `manifest.json` and `daily.jsonl` described in
[daily-research.md](daily-research.md). Raw completed bars, period share factors and
cash benefits, first-available price/basis clocks and point-in-time membership are
required. Include warmup and every relevant reviewed exchange session, including
sessions with no candidate. Do not construct a universe from today's survivors.
Premarket control clocks cannot consume a membership change before its `known_at`.

The second directory contains **execution** `manifest.json` and `events.jsonl`.
Its kind must be explicitly `daily-delivery-execution-v1`. Example manifest:

```json
{
  "schema_version": 1,
  "kind": "daily-delivery-execution-v1",
  "source": "reviewed capture/source version",
  "price_basis": "unadjusted",
  "data_notes": "Document completeness, clocks, gaps, depth and historical cost assumptions",
  "synthetic": false,
  "instruments": [{"symbol":"NSE:EXAMPLE","token":123,"tick_size":"0.05"}],
  "sessions": [{"day":"2026-10-20","open":"09:15","close":"15:30","source":"reviewed session reference"}],
  "events_file": "events.jsonl"
}
```

This is a schema example, not an actual catalog/calendar assertion. At most ten
unique instruments are accepted. Symbols must occur in the daily historical
universe. Session dates must be unique and chronological, with open/close/source
**exactly matching** the daily manifest. Keep no-signal/quiet sessions in the
execution calendar: validation splits use all declared days, not just successful
trade days. Missing events are not evidence of uninterrupted coverage.

Every JSONL line contains an aware `time` and one of these event shapes:

| Type | Additional fields | Meaning |
|---|---|---|
| `connection` | `connected`: strict Boolean | Observed connection state; start connected only with evidence |
| `review` | `review`: `HoldingReview` | Current-session clear basis, or quarantine followed by complete LT2 action batch and new clear review |
| `quote` | `quote`: strict `Quote` | Symbol/token, exchange/received clocks, raw last/bid/ask, depth, volume and source |
| `clock` | none | Observed watchdog/expiry clock; never creates an executable price |
| `kill` | none | Interrupts entries and requests protective exits |
| `action` | `batch`: complete `ActionBatch` | Same reviewed/quarantine-hash LT2 share/dividend contract |
| `receipt` | `receipt`: `CashReceipt` | Reviewed exact net payment for an existing account claim |

Example clear review and quote lines:

```jsonl
{"type":"connection","time":"2026-10-20T09:59:58+05:30","connected":true}
{"type":"review","time":"2026-10-20T09:59:59+05:30","review":{"symbol":"NSE:EXAMPLE","session_date":"2026-10-20","no_corporate_action":true,"reference":"reviewed complete raw price basis"}}
{"type":"quote","time":"2026-10-20T10:00:00+05:30","quote":{"symbol":"NSE:EXAMPLE","token":123,"exchange_time":"2026-10-20T10:00:00+05:30","received_time":"2026-10-20T10:00:00+05:30","last":"500.00","bid":"500.00","ask":"500.05","bid_size":100,"ask_size":100,"volume":100000,"source":"kite"}}
```

These example lines alone cannot complete an order. Later exchange observations
are required even with zero configured latency. Event clocks are nondecreasing;
equal-clock order is preserved. Quotes must match the catalog and a reviewed open
session on the current event date. Manual candidate/candle events, ambiguous JSON
keys, naïve clocks, empty files and backward time are rejected. Manifest reads are
bounded to 1 MB, events to 256 MB, each line to 64 KiB; inputs must be regular local
nonsymlink files. Inputs are hashed before and after processing.

For actions, follow [corporate-actions.md](corporate-actions.md): include the
actual quarantine review, its exact canonical hash, complete ordered intervening
actions, source/availability clocks and a post-application clear review before a
new quote. Cash deductions/receipts must match **this portfolio's entitlement**.
They cannot be copied blindly between accounts. Daily share/cash period benefits
must agree with the applied action basis. Observed last trades must lie in the
declared matching daily raw OHLC range when a daily row exists. Future daily rows
are used only to reject contradictory input, never as decision features or fills.
Correcting a contradiction requires a reviewed new experiment; no finished manifest
is written for the failed run.

There is no automatic daily bundle export, issuer feed or historical quote fetch in
this milestone. Supply independently reviewed matching evidence; historical OHLC
without recorded quotes/depth cannot reconstruct these executions.

## 4. Run an unscored daily portfolio experiment

```sh
.venv/bin/trading-agent --config config/long-term.toml daily-backtest \
  /absolute/path/reviewed-daily /absolute/path/reviewed-execution \
  --strategy config/daily-strategy.toml --output data/daily-portfolio-first
```

Global `--config` precedes the subcommand. A long-term policy is mandatory. The
configured service DB/path, operator secret and calendar file are not opened;
economic limits and costs are copied into a new private output account, using the
reviewed execution calendar/catalog. Output must be new and outside both inputs.
Each account starts with its own configured virtual cash; there is no shared pool.

The default fixed hypothesis is a prior completed 20-session positive gross return,
index at/above its 50-session trend, average turnover at least ₹10 million and daily
volatility no greater than 5%. See LT3a for gross-index assumptions. Fresh current
asks must be within 100 bps of the prior raw close adjusted only by **already applied**
current-session share/cash effects. Entry stop/target are 2%/4%, conservatively tick
rounded. These engineering defaults are not an investment recommendation.

One eligible observation per symbol/session is considered inside the account's
entry window: the first fresh accepted quote consumes that day's decision even if
the daily screen/data, entry-gap check, model or independent risk rejects it. Later
same-day quotes do not retry that proposal or replay a missed signal. Simultaneous
candidates rank by momentum, then symbol; candidates
observed at different times are never retroactively reordered. Rejections remain
visible. A held symbol is not added to or re-entered on its exit session. Existing
risk, cash reservations, depth, latency, slippage, delivery fees, DP allocation,
daily loss, drawdown and persistent exit latches remain independent gates.

At/after the next session's entry-start clock, holdings request an exit when the
prior-daily screen is unavailable/ineligible/outside the current universe or age
reaches 20 reviewed daily sessions. Stop/target and account protection can request
exits earlier. Sparse clocks delay observing this condition. A request never
guarantees price or a fill; only a later acceptable quote/depth can close it.
Long-term holdings are not automatically sold at the daily close or end of input.

Coverage defaults permit at most 30 **open-market seconds** between held-symbol
quotes; overnight/weekend/closed time is excluded. Raising this limit changes the
experiment's assumptions and model identity; it cannot recover missed price paths.
Disconnects while held, rejected/stale quotes, unresolved orders/claims and stale
final marks are disclosed as incomplete evidence. Internally complete sparse
fixtures still do not verify full-session feed continuity or intratick extremes.

## 5. Build independent outcomes before training

```sh
.venv/bin/trading-agent --config config/long-term.toml daily-labels \
  /absolute/path/reviewed-daily /absolute/path/reviewed-execution \
  --strategy config/daily-strategy.toml --output data/daily-labels-first
```

All standalone eligible candidates are evaluated, including unfavorable ones, in
separate `trials/<id>/paper.sqlite3` accounts. Portfolio competition never determines
which observations become labels. The observer itself places no orders and its
cash/flat state is not a portfolio return. Label creation cannot use a model filter.
Defaults allow 32 concurrent trials and 2,000 attempted samples; excess attempts
are explicit `CAPACITY_EXCLUDED` audits. Caps are bounded to 64/10,000.

Labels use fixed entry stop/target, a 20-session time barrier and current universe
exit. They deliberately do not use the portfolio's intermediate daily-screen exit.
The barrier requests an exit/cancels residual entry; the label interval ends only
on the actual final quote-driven liquidation fill. End-of-input never supplies a
guessed price or negative outcome.

`target=1` means a fully filled entry completed a net-positive `TARGET` exit after
all charges; other fully completed exits are `0`. Exact net capital P&L is retained.
Only `LABELED` rows enter `samples.jsonl`. `label_audit.jsonl` also retains risk/capacity
exclusions, unfilled and partial entries, interruption, stale/invalid/gap quotes,
unsettled claims and source exhaustion. Relevant account-specific dividends or
receipts censor a trial: its quantity may differ from the portfolio's reviewed total
deduction/payment. Pure supported share actions can continue; fractional/unpaid
claims prevent a completed label. The observer normalizes zero-entitlement dividend
deductions to zero and ignores payments; it is an information context, not accounting
for a held portfolio. Preserve censored trial DBs for inspection.
Even ignored observer payments require a preceding source action and observed
review/payment clocks; unavailable or unreferenced receipts refuse completion.

## 6. Train and inspect a separate daily model

```sh
.venv/bin/trading-agent daily-train data/daily-labels-first \
  --training config/daily-ml.toml --output data/daily-model-first
```

The loader verifies the completion manifest, every listed artifact hash, chronological
session context, strategy/risk/delivery identity, matching audit/candidate fingerprint,
full entry fill, no residual position and net cash reconciliation. The twelve daily
features have namespace `daily-delivery-features-v1`: momentum, trend distance,
daily volatility, log turnover, spread, entry gap, stop distance, target distance,
minutes since open, log price, history count and gross reward/risk. They contain
neither exit prices nor outcomes. Intraday artifacts/features are refused.

`config/daily-ml.toml` declares fixed expanding whole-session blocks: at least 30
training sessions, ten calibration sessions, three ten-session evaluation folds,
then a frozen twenty-session final holdout (at least 90 declared execution sessions).
Insufficient samples/classes after purge stop training. Entire label intervals
that overlap the next block are removed, with a strict additional 1,440 elapsed
minute embargo. Overnight holding intervals therefore require enough preceding
data; day counts alone cannot guarantee a fit. Keep the small `daily-ml-demo.toml`
policy for invented software fixtures only.

The scaler fits training data only. Fixed logistic regression is followed by
disjoint sigmoid calibration. No parameter search or holdout tuning is performed.
Final coefficients are written before computing holdout diagnostics. Reports retain
AUC, Brier/log loss, training-only baseline, reliability bins/ECE, class/sample counts,
selected count/net label P&L, purge counts, interval boundaries and per-split gates.
Selected-label sums are independent counterfactual results, not portfolio P&L.

Failed statistical checks retain the report/model for review but block loading.
The synthetic override never relaxes statistical, chronology, identity or risk
checks. Real empirical acceptance and economic feasibility require a subsequent
independent portfolio run; repeated experiments/selection bias need separate review.

## 7. Score only a later independent replay

```sh
.venv/bin/trading-agent --config config/long-term.toml daily-backtest \
  /absolute/path/later-daily /absolute/path/later-execution \
  --strategy config/daily-strategy.toml --model data/daily-model-first \
  --output data/daily-scored-first
```

The model is `daily-delivery-model-v1`, persisted as bounded JSON coefficients,
not pickle/joblib. `available_after` is the latest final holdout label end, source
event clock or declared source session close, **plus embargo**. The first event of
the scored replay must be strictly later. Earlier replay, altered strategy/risk/fees,
failed diagnostics or artifact mutation fail closed before an output account is
created. Supply the same strategy/account economics used for labels/training.

For invented evidence only, add `--allow-synthetic-model`. A synthetic model can
score only an execution bundle explicitly declared synthetic. Any non-Kite source
quote also marks a result synthetic; source declarations alone do not authenticate
actual provenance. Scores below the frozen threshold do not submit candidates.
Simultaneous passing candidates rank by probability then symbol, with the usual
independent portfolio risk checks. The daily model is an upstream offline selector;
it does not change `PaperBroker` model bindings or enable connected automation.

## 8. Artifacts, recovery, accounting and performance

Replay/labels output includes `paper.sqlite3`, `report.json`, `report.md`, `index.html`,
`context.json`, `decisions.jsonl`, `equity.csv`, `samples.jsonl`, `label_audit.jsonl`
and a last-written hash `manifest.json`. Label outputs also retain individual trial
DBs, with journal digests in audits; those trial DB files are not individually listed
in the top-level manifest. Model output contains `model.json`, `validation.json`,
`validation.md`, `index.html` and its completion manifest. Keep whole bundles private.
Output directories are mode 0700 and research files mode 0600. SQLite keeps WAL/FULL
durability. Accounts reconcile independently from financial events before completion.

Observed net liquidation P&L includes estimated exit charges and known receivables;
it can be stale/incomplete. Actual fill capital P&L and received dividend income
are separate. Unknown fraction valuation and unpaid claims are never fabricated.
Paper sale cash/credit and custody remain simulation simplifications: no real
T+1 settlement, tax lots, AMC/income-tax calculation or custody reconciliation exists.
Historical cost applicability must be reviewed independently; the shared configured
delivery schedule is an estimate, not a historical fee database.

On failure, preserve the partial output and logs; absence of a finished manifest
means it is not a loadable sample/model bundle. Fix/review inputs or policy and
rerun into a new directory. There is no append/resume/rewrite experiment workflow.
Incomplete completed reports remain inspectable, but censored intervals never train.
Hash checks detect inconsistency, not a malicious owner who rewrites all evidence.

Daily input is parsed/validated once; selected symbol state advances by availability,
membership uses binary search and rolling windows stay bounded. Rare late old rows
rebuild only that symbol. Coverage uses prefix sums/binary search. Financial writes
retain the existing durable transaction behavior. Reproduce timing with:

```sh
.venv/bin/python scripts/benchmark_daily_execution.py --samples 20
```

[Captured Mac evidence](benchmark-daily-execution-macos.json): 219 daily bars,
36 quotes, nine completed trades, full parse/hash/durable replay/report p50
**35.4865 ms**, p95 **38.7704 ms**, p99/max **47.7677 ms** across twenty runs.
One thousand warmed single-symbol screens: p50 **0.0058 ms**, p99 **0.0074 ms**.
Fixture creation, network, label trials, training and actual Pi are excluded.
These small local timings are not exchange latency or a large-universe guarantee.

Next in the plan is LT3c: reviewed lot additions/SIP, rebalance proposals and
aggregate capital coordination. Actual read-only custody/settlement reconciliation,
real data/model acceptance, physical device/feed drills and all live phases remain
open. See [implementation-plan.md](implementation-plan.md).

## 9. LT3c1 now supplies reviewed contribution foundations (0.9.0)

[Contribution/SIP usage](portfolio-contributions.md) adds explicit manual purchases/
holding additions, original acquisition history and recurring reviewed-session
occurrences. It reuses exact delivery accounting while keeping normal daily strategy
research unchanged: the daily model does not arm this service or schedule SIPs.
LT3c2 reviewed rebalance proposals and LT3c3 cross-account capital coordination remain
next. No current per-lot/FIFO/tax attribution or external funding is supplied.
