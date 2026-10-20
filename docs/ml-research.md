# Phase 3: chronological ML research

Version 0.3.0 adds an offline logistic model, separate sigmoid calibration,
purged walk-forward evaluation, a final holdout, and scored portfolio replays.
All capital is virtual. This guide covers offline research; the opt-in Phase 4
[supervised paper service](paper-feed.md) can attach approved non-synthetic models
to dedicated accounts. `ready_for_live` is always false.

## Install and run the complete example

Use the existing patched Python 3.13.16 environment from the repository root:

```sh
uv sync --frozen --all-extras
source .venv/bin/activate
trading-agent ml-demo --directory data/ml-first
```

Every output directory must be new. The command requires no broker credentials,
network, account database, or exchange subscription. It creates:

| Directory | Purpose |
|---|---|
| `training-data/` | Sixty invented sessions, including training, calibration, walk-forward validation and final holdout |
| `samples/` | Sixty labeled rule candidates and their execution audit records |
| `model/` | Frozen JSON coefficients, validation JSON/Markdown and completion manifest |
| `future-data/` | Ten additional invented sessions excluded from fitting and validation |
| `baseline/` | Rules with independent risk and no model on those ten later sessions |
| `scored/` | The same later sessions, with probability filtering/ranking and independent risk |

The fixture deliberately makes signal strength predict later prices. It tests the
software, not a market hypothesis. Under shipped settings it produces 30 positive
and 30 negative labels; walk-forward and holdout diagnostic gates pass, while
`non_synthetic` stays false and `research_approved` stays false. The later baseline
completes ten trades with −₹148.80 net P&L; the scored replay completes five with
₹504.70 net P&L and rejects five below threshold. These invented results have no
empirical interpretation. Each account starts independently at ₹25,000.

The demo uses `config/ml-demo.toml`, a deliberately small **synthetic test policy**.
`config/ml.toml` is the separate default for real research. Do not replace real-data
acceptance settings with the demo's sample requirements to obtain a passing report.

## Prepare real research input

Use a reviewed raw candle/quote bundle as described in [backtesting.md](backtesting.md).
Retain full opening warmup, explicit candle-availability timestamps, sufficiently
dense subsequent quotes, catalog/tick information, session sources and connection
events. OHLC bars alone cannot determine executable labels. The provenance
declaration is supplied by the operator; the program cannot authenticate it.

Predeclare the hypothesis, universe, dates, label horizon, simulation policy,
training settings and later evaluation period before looking at results. Retain
unfavorable experiments. This implementation performs no parameter or universe
search and does not correct repeated research for selection bias.

With the default training policy you need at least **90 declared sessions**:
30 initial training + 10 calibration + 3 × 10 validation + 20 final holdout.
You also need at least 100 training samples, 30 calibration samples, 30 samples per
evaluation block, and five examples of each class in every fitted/evaluated block.
These requirements apply after purging and censoring. Ninety sessions of one
candidate per day are insufficient for the first training block; collect more
data or a predeclared broader universe. Empty/insufficient blocks fail.

## Build execution-based labels

```sh
trading-agent --config config/paper.toml ml-build data/reviewed-training \
  --strategy config/strategy.toml --horizon-minutes 30 \
  --output data/labels-experiment-001
```

Rules generate candidates using only completed, contiguous five-minute history and
quotes known at decision time. Each candidate receives a fresh isolated paper account
with the same virtual capital, cost schedule, tick rounding, stop/target, risk sizing,
latency, depth and entry constraints. Portfolio competition does not remove labels.
The entry uses a strictly later exchange quote; no signal-close fill is allowed.

The exit deadline is the earliest of the chosen horizon, policy flatten time and
fifteen minutes before the declared session close. At the deadline the trial queues
a time exit before seeing the next quote price. A later quote still has to fill it.
A previously queued stop/target keeps its exit reason. The label interval ends at
the actual last fill, including any liquidation delay, rather than the nominal horizon.

`target = 1` means a target-triggered completed exit with positive net simulated
P&L. Completed stop/time/session exits are `0`. A target exit with nonpositive net
P&L is also `0`. Prices and money remain Decimal; fees include actual simulated
quantity and partial fills. An absent entry, unresolved position, interrupted feed,
bad quote, held-trial quote gap beyond the policy's five-second default, flagged
candle or other risk exit is **censored**, never converted into a loss or convenient
closing price. Disconnect/kill events exclude active trials; new candidates require
connectivity again. Ordinary source errors abort the bundle.

These are **standalone feasible-trade labels**. They do not represent simultaneous
portfolio capacity, and exclusions can bias the surviving sample. Inspect every
censor count and the source quality; a high exclusion rate is a research failure
even if a model fitted to survivors passes statistical gates.

| File in the sample bundle | Contents |
|---|---|
| `samples.jsonl` | Fixed causal vector, candidate fingerprint, decision/end times, binary target, net P&L and exit reason |
| `label_audit.jsonl` | Every attempted trial, including exclusions, deadline, orders, fills, reconciled ending snapshot and journal digest |
| `manifest.json` | Source manifest/hashes/availability boundary, complete strategy/economic policy, label settings, code hash, sessions, counts and file hashes |
| `observer.sqlite3` | Quote-validation observer journal; it submits no orders |

Temporary trial databases are closed and removed after their evidence is written.
At most 100 trials may overlap; the default strategy/universe normally needs far
fewer. Label construction intentionally uses durable paper accounting and is an
offline operation. It never opens the configured service account. A failed build
leaves no completion manifest; preserve its partial output and rerun to a new path.

## Fixed features and training

The versioned `candidate-features-v1` vector has exactly twelve ordered, finite values:

| Feature | Definition at decision time |
|---|---|
| VWAP distance | `(close − session VWAP) / close`, in bps |
| EMA distance | `(close − completed-bar EMA) / close`, in bps |
| ATR | Completed-bar Wilder ATR / close, in bps |
| Relative volume | Completed bar volume / strictly prior-window mean |
| Candle range | `(high − low) / close`, in bps |
| Candle return | `(close − open) / open`, in bps |
| Spread | `(ask − bid) / bid`, in bps |
| Quote gap | `(ask − close) / close`, in bps |
| Stop distance | Adverse entry cap to adverse stop fill, as entry-price bps |
| Net reward/risk | One-share adverse target gain after fees / one-share adverse stop loss after fees |
| Session time | Minutes since reviewed session open |
| Log turnover | `log1p(close × completed bar volume)` |

The one-share fee ratio is a feature approximation; labels and actual sizing use
their actual quantities. Outcome, subsequent return, label end and realized costs
are excluded from features. Schema/order/dimensions, completion time, source symbol,
token and candidate fingerprint are checked; missing values are not imputed.
The fingerprint binds intent identity, symbol, stop, target, time and reason while
allowing the model-version annotation to be added later.

```sh
trading-agent ml-train data/labels-experiment-001 \
  --training config/ml.toml --output data/model-experiment-001
```

Splits group **whole declared IST sessions**, keeping simultaneous symbols together.
There is no random shuffle. For 90 sessions, the default split schedule is:

| Stage | Train sessions | Calibration sessions | Evaluation sessions |
|---|---|---|---|
| Fold 1 | 1–30 | 31–40 | 41–50 |
| Fold 2 | 1–40 | 41–50 | 51–60 |
| Fold 3 | 1–50 | 51–60 | 61–70 |
| Final frozen model | 1–60 | 61–70 | 71–90, untouched final holdout |

More history expands the initial training window. A training row is kept only if
`label_end + embargo < first calibration decision`. A calibration row is kept only
if `label_end + embargo < first evaluation decision`. The embargo defaults to thirty
minutes and equality is purged. This uses timestamp intervals, not a row-count gap.

Each fold fits a StandardScaler and logistic regression on its training block only.
A separate regularized logistic sigmoid maps the base model's scores using only
the later calibration block. The exported final coefficients are frozen on disk
before final holdout outcome metrics are calculated. C=1, threshold=0.6, solver,
iteration limit and split policy are predeclared; no tuning loop runs. Convergence
warnings fail fitting rather than exporting an uncertain result.

This follows the need for independent calibration data in the official
[calibration guide](https://scikit-learn.org/stable/modules/calibration.html).
The timestamp-interval purge extends the chronological concept described by
[TimeSeriesSplit](https://scikit-learn.org/stable/modules/generated/sklearn.model_selection.TimeSeriesSplit.html).

## Interpret and preserve validation

`model/validation.md` is the readable summary. `validation.json` retains every fold's
windows, actual counts, purges, ROC-AUC, Brier/log loss, training-prevalence constant
baseline, ten reliability bins, expected calibration error (ECE), threshold-selected
count and selected net counterfactual P&L. ECE is a bin-dependent diagnostic, not a
guarantee that probabilities are reliable on future markets.

Every fold and final holdout must meet all predeclared gates: enough samples and
both classes, ROC-AUC ≥0.55, Brier strictly better than the training-only constant
baseline, ECE ≤0.15, at least ten threshold-selected samples and positive selected
net counterfactual P&L under defaults. `research_approved` additionally requires
non-synthetic provenance. Insufficient fitting data fails without a manifest;
a fitted model failing evaluation retains its diagnostics but is refused by the loader.
The synthetic override only relaxes provenance, never metric or integrity gates.

Selected P&L sums isolated trial labels. Use a later portfolio replay to account
for shared cash, reservations, limits and score ordering. Passing these provisional
research gates establishes neither an economic edge nor deployment readiness.
Historical fee matching, corporate actions, universe selection, queue position,
impact, outages and gaps still need empirical review.

## Score a later portfolio replay

```sh
trading-agent --config config/paper.toml backtest data/reviewed-later-period \
  --strategy config/strategy.toml --model data/model-experiment-001 \
  --output data/scored-experiment-001
```

The input stream, including warmup, must start **strictly after** validation is
complete plus embargo (`model.json: available_after`). Completion is the latest of
the holdout's last label fill, its final declared session close, and the source
bundle's final observation. This also covers later observations after the last
trade. It prevents using future validation results to approve a historical decision.
Keep a separate later dataset. Retraining produces a new artifact and account.

For the synthetic example only:

```sh
trading-agent backtest data/ml-first/future-data --model data/ml-first/model \
  --allow-synthetic-model --output data/ml-first-rerun
```

A synthetic model may score only a synthetic dataset. Strategy/economic-policy/fee
hashes must match training; using the same reviewed configuration preserves identity.
The runner scores candidates sharing the exact availability timestamp, sorts by
descending probability with symbol/intent tie breaks, then submits them before the
next timestamp's market data. It never ranks against future candidates. Low scores
produce durable `MODEL_BELOW_THRESHOLD` rejections and no rule-only fallback.

The independent broker verifies features, candidate/model identity, availability and
threshold again. It still controls all quantities, cash, fees, exposure, session,
freshness, daily/streak/kill gates and subsequent fills. A high probability cannot
raise limits or revive a killed account. Model identity persists in account metadata;
removing/replacing it requires a new account. Decisions add probability, rank, vector
and model hash to the normal [backtest artifacts](backtesting.md#read-the-results).

## Artifact safety and performance

`model.json` contains finite scaler, logistic and calibration coefficients plus
feature/label schema, threshold, training/source/code/config identities and
fit/validation/availability windows. `manifest.json`, written last, hashes that model
and its validation report. Loading checks sizes, local paths, hashes, dimensions,
chronology, report/metric consistency and approval gates. No pickle/joblib/ONNX or
executable model is loaded. See the official
[persistence guidance](https://scikit-learn.org/stable/model_persistence.html).

Hashes detect corruption and ordinary mutation; they are not signatures and do not
authenticate a maliciously rewritten local bundle. Review and protect source data,
code, configuration and artifacts. Keep incomplete/failed experiments for diagnosis.

Training requires the optional `ml` extra (NumPy/scikit-learn). Inference imports
neither, uses twelve-feature Python math, and does no disk/network work per score.
The Pi setup installs only broker/runtime dependencies. Train on a separate machine;
use the Phase 4 guide for supervised integration and its remaining empirical checks.

```sh
pytest tests/ml tests/functional/test_ml_commands.py
python scripts/benchmark_ml.py --model data/ml-first/model \
  --allow-synthetic-model --samples 10000 --output benchmark.json
```

The [Mac benchmark](performance.md#phase-3-json-inference-and-ranking) separates score
math and ten-candidate ranking from parsing, feature construction and durable risk
execution. Measure the complete workload on actual target hardware before deployment.
