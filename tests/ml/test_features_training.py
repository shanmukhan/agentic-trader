from datetime import timedelta
from pathlib import Path

import pytest

from trading_agent.backtesting.dataset import CandleEvent, QuoteEvent
from trading_agent.ml.features import FEATURE_NAMES, FeatureVector, make_features
from trading_agent.ml.samples import Samples
from trading_agent.ml.schema import Sample, TrainingSettings
from trading_agent.ml.splits import chronological_splits
from trading_agent.ml.training import evaluate, fit, train_model
from trading_agent.settings import Settings
from trading_agent.strategy.rules import RuleStrategy, StrategySettings


def context(dataset):
    rules = RuleStrategy(StrategySettings(), dataset.manifest.calendar())
    latest = None
    for event in dataset.events():
        if isinstance(event, QuoteEvent):
            latest = event.quote
        if isinstance(event, CandleEvent):
            result = rules.evaluate(
                event.candle,
                now=event.time,
                quote=latest,
                instrument=dataset.manifest.instruments[0],
                connected=True,
            )
            if result.candidate:
                return dict(
                    candidate=result.candidate,
                    candle=event.candle,
                    candle_end=result.candle_end,
                    features=result.features,
                    quote=latest,
                    instrument=dataset.manifest.instruments[0],
                    opened=dataset.manifest.calendar().bounds(event.time)[0],
                    policy=Settings(),
                )
    raise AssertionError("fixture needs a candidate")


def test_fixed_features_are_causal_finite_and_exclude_future_label(research_dataset):
    kwargs = context(research_dataset)
    vector = make_features(**kwargs)
    assert len(vector.values) == len(FEATURE_NAMES) == 12
    assert vector.values[3] == 2.5 and vector.values[10] == 70
    assert set(vector.model_dump()) == {
        "version",
        "symbol",
        "time",
        "candle_end",
        "values",
        "candidate_sha256",
    }
    with pytest.raises(ValueError, match="complete"):
        FeatureVector(**(vector.model_dump() | {"candle_end": vector.time + timedelta(seconds=1)}))
    for bad in (float("nan"), float("inf"), "1", None):
        with pytest.raises(ValueError):
            FeatureVector(**(vector.model_dump() | {"values": (bad, *vector.values[1:])}))
    for values in (vector.values[:-1], (*vector.values, 1.0)):
        with pytest.raises(ValueError):
            FeatureVector(**(vector.model_dump() | {"values": values}))


@pytest.mark.parametrize(
    "mutation", ["future_quote", "missing", "nan", "incomplete", "wrong_token", "wrong_end"]
)
def test_feature_construction_rejects_invalid_context(research_dataset, mutation):
    kwargs = context(research_dataset)
    if mutation == "future_quote":
        kwargs["quote"] = kwargs["quote"].model_copy(
            update={"received_time": kwargs["candidate"].decision_time + timedelta(seconds=1)}
        )
    elif mutation in {"missing", "nan"}:
        kwargs["features"] = kwargs["features"] | {"ema": None if mutation == "missing" else "NaN"}
    elif mutation == "incomplete":
        kwargs["candle"] = kwargs["candle"].model_copy(update={"completed": False})
    elif mutation == "wrong_token":
        kwargs["instrument"] = kwargs["instrument"].model_copy(update={"token": 999})
    else:
        kwargs["candle_end"] -= timedelta(seconds=1)
    with pytest.raises(ValueError):
        make_features(**kwargs)


def test_purges_overlapping_label_intervals_and_embargo_equality(ml_demo):
    samples = Samples(ml_demo[0] / "samples")
    rows = samples.read()
    cfg = TrainingSettings.load(Path("config/ml-demo.toml"))
    rows[19] = rows[19].model_copy(
        update={"label_end": rows[20].features.time - timedelta(minutes=cfg.embargo_minutes)}
    )
    rows[29] = rows[29].model_copy(
        update={"label_end": rows[30].features.time - timedelta(minutes=cfg.embargo_minutes)}
    )
    splits = chronological_splits(rows, samples.manifest.sessions, cfg)
    first = splits[0]
    assert first.purged_train == first.purged_calibration == 1
    assert len(first.train) == 19 and len(first.calibration) == 9
    assert rows[19].id not in {row.id for row in first.train}
    assert rows[29].id not in {row.id for row in first.calibration}
    for split in splits:
        assert max(row.label_end for row in split.train) + timedelta(
            minutes=cfg.embargo_minutes
        ) < min(row.features.time for row in split.calibration)
        assert max(row.label_end for row in split.calibration) + timedelta(
            minutes=cfg.embargo_minutes
        ) < min(row.features.time for row in split.evaluation)
        assert not {row.id for row in split.train} & {row.id for row in split.calibration}


def test_same_session_symbols_stay_together_and_holdout_is_never_a_fit_block(ml_demo):
    samples = Samples(ml_demo[0] / "samples")
    rows = samples.read()
    second = [
        row.model_copy(
            update={
                "id": row.id + ":second",
                "features": row.features.model_copy(update={"symbol": "NSE:SECOND"}),
            }
        )
        for row in rows
    ]
    cfg = TrainingSettings.load(Path("config/ml-demo.toml"))
    splits = chronological_splits(rows + second, samples.manifest.sessions, cfg)
    final_ids = {row.id for row in splits[-1].evaluation}
    for split in splits:
        for block in (split.train, split.calibration, split.evaluation):
            assert len(block) % 2 == 0
            times = [row.features.time for row in block]
            assert all(times.count(t) == 2 for t in set(times))
        assert not final_ids & {row.id for row in (*split.train, *split.calibration)}
    assert [len(split.train) for split in splits] == [40, 60, 80]


def test_scaling_and_base_estimator_fit_only_training_and_calibrator_uses_separate_labels(ml_demo):
    samples = Samples(ml_demo[0] / "samples")
    cfg = TrainingSettings.load(Path("config/ml-demo.toml"))
    split = chronological_splits(samples.read(), samples.manifest.sessions, cfg)[-1]
    original = fit(split, cfg)
    from dataclasses import replace

    changed_eval = tuple(
        row.model_copy(
            update={
                "features": row.features.model_copy(
                    update={"values": tuple(value + 1000 for value in row.features.values)}
                )
            }
        )
        for row in split.evaluation
    )
    assert fit(replace(split, evaluation=changed_eval), cfg) == original
    flipped_cal = tuple(
        row.model_copy(update={"target": 1 - row.target}) for row in split.calibration
    )
    changed = fit(replace(split, calibration=flipped_cal), cfg)
    assert changed.means == original.means and changed.scales == original.scales
    assert changed.weights == original.weights and changed.intercept == original.intercept
    assert changed.calibration_slope < 0 < original.calibration_slope
    assert original.means[3] == pytest.approx(2.25)


def test_frozen_export_precedes_holdout_evaluation_and_training_is_deterministic(
    ml_demo, tmp_path, monkeypatch
):
    import trading_agent.ml.training as training

    original = training.evaluate
    output = tmp_path / "trained"
    checked = []

    def verify_frozen(rows, coefficients, baseline, settings):
        if rows[0].id == Samples(ml_demo[0] / "samples").read()[50].id:
            assert (output / "model.json").is_file()
            checked.append(True)
        return original(rows, coefficients, baseline, settings)

    monkeypatch.setattr(training, "evaluate", verify_frozen)
    report = train_model(
        Samples(ml_demo[0] / "samples"),
        settings=TrainingSettings.load(Path("config/ml-demo.toml")),
        output=output,
    )
    assert checked and report["gates"] == {
        "walk_forward": True,
        "holdout": True,
        "non_synthetic": False,
    }
    assert (output / "model.json").read_bytes() == (ml_demo[0] / "model/model.json").read_bytes()
    with pytest.raises(ValueError, match="sessions"):
        chronological_splits(
            Samples(ml_demo[0] / "samples").read(),
            Samples(ml_demo[0] / "samples").manifest.sessions,
            TrainingSettings(),
        )


def test_small_single_class_and_bad_models_do_not_pass_acceptance(ml_demo):
    from dataclasses import replace

    samples = Samples(ml_demo[0] / "samples")
    cfg = TrainingSettings.load(Path("config/ml-demo.toml"))
    split = chronological_splits(samples.read(), samples.manifest.sessions, cfg)[0]
    with pytest.raises(ValueError, match="train"):
        fit(replace(split, train=split.train[:5]), cfg)
    with pytest.raises(ValueError, match="calibration"):
        fit(replace(split, calibration=tuple(row for row in split.calibration if row.target)), cfg)
    model = fit(split, cfg)
    rows = tuple(row for row in split.evaluation if row.target)
    result = evaluate(rows, model, 0.5, cfg)
    assert result["roc_auc"] is None and not result["passed"]
    assert not result["gates"]["both_classes"]
    row = samples.read()[0]
    with pytest.raises(ValueError):
        Sample(**(row.model_dump() | {"target": True}))
    with pytest.raises(ValueError):
        Sample(**(row.model_dump() | {"label_end": row.features.time}))
    with pytest.raises(ValueError):
        Sample(**(row.model_dump() | {"target": 0}))


def test_model_availability_covers_entire_validation_session_and_later_source(
    ml_demo, research_model, tmp_path
):
    import json
    import shutil
    from datetime import datetime

    artifact = research_model.artifact
    assert artifact.validated_through > artifact.validation_label_end
    source = Samples(ml_demo[0] / "samples")
    final = source.manifest.source_manifest.sessions[-1]
    from trading_agent.market_data.calendar import IST

    closing = datetime.combine(final.day, final.close, IST)
    assert artifact.available_after == closing + timedelta(minutes=30)
    directory = tmp_path / "samples"
    shutil.copytree(ml_demo[0] / "samples", directory)
    manifest = json.loads((directory / "manifest.json").read_text())
    later = closing + timedelta(hours=2)
    manifest["source_available_through"] = later.isoformat()
    (directory / "manifest.json").write_text(json.dumps(manifest))
    train_model(
        Samples(directory),
        settings=TrainingSettings.load(Path("config/ml-demo.toml")),
        output=tmp_path / "model",
    )
    trained = json.loads((tmp_path / "model/model.json").read_text())
    assert datetime.fromisoformat(trained["available_after"]) == later + timedelta(minutes=30)
    assert trained["coefficients"] == artifact.coefficients.model_dump(mode="json")
