import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from trading_agent.daily_execution.contracts import DailyStrategy
from trading_agent.daily_execution.dataset import ExecutionDataset
from trading_agent.daily_execution.model import DailySamples, load_daily_model, train_daily
from trading_agent.daily_execution.runner import run_daily
from trading_agent.daily_research.dataset import DailyDataset
from trading_agent.ml.inference import Artifact, ModelUnavailable
from trading_agent.ml.schema import TrainingSettings
from trading_agent.ml.splits import chronological_splits


def rehash(directory, name):
    manifest = json.loads((directory / "manifest.json").read_text())
    manifest["sha256"][name] = hashlib.sha256((directory / name).read_bytes()).hexdigest()
    (directory / "manifest.json").write_text(json.dumps(manifest))


def test_daily_chronology_separate_namespace_and_later_replay(
    daily_ml_demo, daily_strategy, daily_policy
):
    directory, result = daily_ml_demo
    assert result["label_counts"] == {"LABELED": 150}
    assert result["validation_gates"] == {
        "walk_forward": True,
        "holdout": True,
        "non_synthetic": False,
    }
    assert result["scored_completed_trades"] == 20
    model = load_daily_model(
        directory / "model", strategy=daily_strategy, policy=daily_policy, allow_synthetic=True
    )
    raw = json.loads((directory / "model/model.json").read_text())
    with pytest.raises(ValueError):
        Artifact.model_validate(raw)
    rows = DailySamples(directory / "labels").read()
    assert len(rows) == 150 and sum(row.target for row in rows) == 100
    cfg = TrainingSettings.load(Path("config/daily-ml-demo.toml"))
    samples = DailySamples(directory / "labels")
    splits = chronological_splits(rows, samples.sessions, cfg)
    for split in splits:
        assert max(row.label_end for row in split.train) + timedelta(
            minutes=cfg.embargo_minutes
        ) < min(row.features.time for row in split.calibration)
        assert max(row.label_end for row in split.calibration) + timedelta(
            minutes=cfg.embargo_minutes
        ) < min(row.features.time for row in split.evaluation)
        assert split.purged_train >= 0 and split.purged_calibration >= 0
    crossed = rows[0].model_copy(update={"label_end": splits[0].calibration[0].features.time})
    purged = chronological_splits([crossed, *rows[1:]], samples.sessions, cfg)
    assert crossed.id not in {row.id for row in purged[0].train}
    assert purged[0].purged_train == splits[0].purged_train + 1
    report = json.loads((directory / "model/validation.json").read_text())
    assert model.artifact.available_after > datetime.fromisoformat(report["validation_session_end"])
    vector = rows[0].features.model_copy(update={"time": model.artifact.available_after})
    with pytest.raises(ModelUnavailable, match="embargo"):
        model.score(vector)
    assert (
        0
        <= model.score(vector.model_copy(update={"time": vector.time + timedelta(seconds=1)}))
        <= 1
    )


@pytest.mark.parametrize("kind", ["no_override", "strategy", "policy", "too_early"])
def test_daily_scoring_boundaries(daily_ml_demo, daily_strategy, daily_policy, tmp_path, kind):
    directory, _ = daily_ml_demo
    if kind == "no_override":
        with pytest.raises(ModelUnavailable):
            load_daily_model(directory / "model", strategy=daily_strategy, policy=daily_policy)
    elif kind in {"strategy", "policy"}:
        with pytest.raises(ModelUnavailable):
            load_daily_model(
                directory / "model",
                strategy=DailyStrategy(max_hold_sessions=10)
                if kind == "strategy"
                else daily_strategy,
                policy=daily_policy.model_copy(
                    update={"max_trade_risk": daily_policy.max_trade_risk + 1}
                )
                if kind == "policy"
                else daily_policy,
                allow_synthetic=True,
            )
    else:
        model = load_daily_model(
            directory / "model", strategy=daily_strategy, policy=daily_policy, allow_synthetic=True
        )
        source = ExecutionDataset(
            directory / "inputs/execution", DailyDataset(directory / "inputs/daily")
        )
        with pytest.raises(ValueError, match="embargo"):
            run_daily(
                source,
                strategy=daily_strategy,
                policy=daily_policy,
                output=tmp_path / "early",
                model=model,
            )
        assert not (tmp_path / "early").exists()


@pytest.mark.parametrize(
    "kind", ["hash", "schema", "dimensions", "failed_gates", "provenance", "symlink", "oversized"]
)
def test_daily_model_tampering_and_failed_evidence(
    daily_ml_demo, tmp_path, daily_strategy, daily_policy, kind
):
    directory = tmp_path / "model"
    shutil.copytree(daily_ml_demo[0] / "model", directory)
    name = "model.json"
    raw = json.loads((directory / name).read_text())
    if kind == "hash":
        (directory / name).write_text(json.dumps(raw) + " ")
    elif kind == "symlink":
        (directory / name).unlink()
        (directory / name).symlink_to(daily_ml_demo[0] / "model/model.json")
    elif kind == "oversized":
        (directory / name).write_bytes(b" " * 2_000_001)
    else:
        if kind == "schema":
            raw["feature_version"] = "intraday-features-v1"
        elif kind == "dimensions":
            raw["feature_names"] = list(reversed(raw["feature_names"]))
        elif kind == "provenance":
            raw["synthetic"] = False
        else:
            name = "validation.json"
            raw = json.loads((directory / name).read_text())
            raw["gates"]["holdout"] = False
        (directory / name).write_text(json.dumps(raw))
        rehash(directory, name)
    with pytest.raises((ValueError, ModelUnavailable)):
        load_daily_model(
            directory, strategy=daily_strategy, policy=daily_policy, allow_synthetic=True
        )


@pytest.mark.parametrize(
    "kind", ["hash", "count", "candidate", "cash", "namespace", "sessions", "duplicate"]
)
def test_daily_sample_evidence_is_independently_checked(daily_ml_demo, tmp_path, kind):
    directory = tmp_path / "labels"
    shutil.copytree(daily_ml_demo[0] / "labels", directory, ignore=shutil.ignore_patterns("trials"))
    name = "samples.jsonl"
    if kind in {"candidate", "cash"}:
        name = "label_audit.jsonl"
        rows = [json.loads(s) for s in (directory / name).read_text().splitlines()]
        if kind == "candidate":
            rows[0]["candidate"]["stop"] = "1.00"
        else:
            rows[0]["cash"] = "999999.99"
    elif kind == "sessions":
        name = "context.json"
        raw = json.loads((directory / name).read_text())
        raw["sessions"].reverse()
        (directory / name).write_text(json.dumps(raw))
        rehash(directory, name)
        with pytest.raises(ValueError):
            DailySamples(directory)
        return
    else:
        rows = [json.loads(s) for s in (directory / name).read_text().splitlines()]
        if kind == "count":
            rows.pop()
        elif kind == "duplicate":
            rows[0] = rows[1]
        elif kind == "namespace":
            rows[0]["features"]["version"] = "intraday-features-v1"
    (directory / name).write_text(
        "".join(json.dumps(row) + "\n" for row in rows) + (" " if kind == "hash" else "")
    )
    if kind != "hash":
        rehash(directory, name)
    with pytest.raises(ValueError):
        DailySamples(directory).read()


def test_fitting_scaler_ignores_evaluation_features_and_retains_failed_holdout(
    daily_ml_demo, tmp_path, daily_strategy, daily_policy
):
    from trading_agent.ml.training import fit

    samples = DailySamples(daily_ml_demo[0] / "labels")
    cfg = TrainingSettings.load(Path("config/daily-ml-demo.toml"))
    split = chronological_splits(samples.read(), samples.sessions, cfg)[0]
    first = fit(split, cfg)
    from dataclasses import replace

    changed = replace(
        split,
        evaluation=tuple(
            row.model_copy(
                update={"features": row.features.model_copy(update={"values": (999.0,) * 12})}
            )
            for row in split.evaluation
        ),
    )
    assert first == fit(changed, cfg)
    # Deliberately unattainable acceptance floor retains diagnostics but never loads.
    strict = cfg.model_copy(update={"min_selected_samples": 10000})
    output = tmp_path / "failed"
    report = train_daily(samples, settings=strict, output=output)
    assert not report["gates"]["holdout"] and (output / "manifest.json").exists()
    with pytest.raises(ModelUnavailable):
        load_daily_model(output, strategy=daily_strategy, policy=daily_policy, allow_synthetic=True)


def test_daily_model_loading_and_scoring_imports_no_training_packages(daily_ml_demo):
    script = """
import sys
from pathlib import Path
from trading_agent.daily_execution.contracts import DailyStrategy, DailyVector
from trading_agent.daily_execution.model import load_daily_model
from trading_agent.settings import Settings
import json
from datetime import timedelta
m=load_daily_model(Path(sys.argv[1])/'model', strategy=DailyStrategy(),
    policy=Settings.load('config/long-term.toml'),allow_synthetic=True)
v=DailyVector.model_validate(json.loads((Path(sys.argv[1])/'labels/samples.jsonl').read_text().splitlines()[0])['features'])
m.score(v.model_copy(update={'time':m.artifact.available_after+timedelta(days=1)}))
assert 'numpy' not in sys.modules and 'sklearn' not in sys.modules
"""
    subprocess.run(
        [sys.executable, "-c", script, str(daily_ml_demo[0])],
        check=True,
        capture_output=True,
        text=True,
    )
