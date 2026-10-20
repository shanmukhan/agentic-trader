import hashlib
import json
import shutil
import subprocess
import sys
from datetime import timedelta

import pytest
from conftest import NOW, candidate

from trading_agent.execution.costs import Charges
from trading_agent.execution.paper_broker import IntentConflict, PaperBroker
from trading_agent.ml.features import candidate_fingerprint
from trading_agent.ml.inference import ModelUnavailable, load_model, sigmoid
from trading_agent.ml.samples import Samples
from trading_agent.persistence.database import Database
from trading_agent.risk.policy import policy_fingerprint
from trading_agent.settings import Settings
from trading_agent.strategy.rules import StrategySettings


def load(path, **overrides):
    kwargs = dict(
        strategy_sha256=StrategySettings().digest(),
        policy_sha256=policy_fingerprint(Settings()),
        charges_version=Charges().version,
        allow_synthetic=True,
    )
    return load_model(path, **(kwargs | overrides))


def rehash(directory):
    manifest = {
        "schema_version": 1,
        "model_sha256": hashlib.sha256((directory / "model.json").read_bytes()).hexdigest(),
        "validation_sha256": hashlib.sha256(
            (directory / "validation.json").read_bytes()
        ).hexdigest(),
    }
    (directory / "manifest.json").write_text(json.dumps(manifest))


def high_vector(ml_demo, now=NOW, intent=None):
    vector = Samples(ml_demo[0] / "samples").read()[0].features
    return vector.model_copy(
        update={
            "time": now,
            "candle_end": now,
            "candidate_sha256": candidate_fingerprint(intent or candidate(now=now)),
        }
    )


def test_synthetic_context_and_time_gates_fail_closed(ml_demo, research_model):
    with pytest.raises(ModelUnavailable, match="synthetic"):
        load(ml_demo[0] / "model", allow_synthetic=False)
    for key in ("strategy_sha256", "policy_sha256", "charges_version"):
        with pytest.raises(ModelUnavailable, match="differs"):
            load(ml_demo[0] / "model", **{key: "other"})
    vector = high_vector(ml_demo, research_model.artifact.available_after)
    with pytest.raises(ModelUnavailable, match="embargo"):
        research_model.score(vector)
    assert (
        research_model.score(
            vector.model_copy(update={"time": vector.time + timedelta(microseconds=1)})
        )
        > 0.6
    )
    assert sigmoid(1e6) == 1 and sigmoid(-1e6) == 0
    with pytest.raises(ModelUnavailable):
        sigmoid(float("nan"))


@pytest.mark.parametrize(
    "mode",
    [
        "tamper_model",
        "tamper_report",
        "nan",
        "dimension",
        "scale",
        "schema",
        "inconsistent_report",
        "missing",
        "symlink",
        "oversize",
    ],
)
def test_corrupted_or_unsafe_artifacts_cannot_load(ml_demo, tmp_path, mode):
    directory = tmp_path / "model"
    shutil.copytree(ml_demo[0] / "model", directory)
    raw = json.loads((directory / "model.json").read_text())
    if mode in {"tamper_model", "tamper_report"}:
        name = "model.json" if mode == "tamper_model" else "validation.json"
        with (directory / name).open("a") as file:
            file.write(" ")
    elif mode == "missing":
        (directory / "manifest.json").unlink()
    elif mode == "symlink":
        (directory / "model.json").unlink()
        (directory / "model.json").symlink_to(ml_demo[0] / "model/model.json")
    elif mode == "oversize":
        (directory / "model.json").write_bytes(b" " * 2_000_001)
    elif mode == "inconsistent_report":
        report = json.loads((directory / "validation.json").read_text())
        report["splits"][0]["metrics"]["brier"] = 1.0
        (directory / "validation.json").write_text(json.dumps(report))
        rehash(directory)
    else:
        if mode == "nan":
            raw["coefficients"]["intercept"] = float("nan")
        elif mode == "dimension":
            raw["coefficients"]["weights"].pop()
        elif mode == "scale":
            raw["coefficients"]["scales"][0] = 0
        elif mode == "schema":
            raw["feature_names"][0] = "future_return"
        (directory / "model.json").write_text(json.dumps(raw))
        rehash(directory)
    with pytest.raises((ValueError, FileNotFoundError)):
        load(directory)


def test_synthetic_override_cannot_bypass_failed_metrics(ml_demo, tmp_path):
    directory = tmp_path / "model"
    shutil.copytree(ml_demo[0] / "model", directory)
    report = json.loads((directory / "validation.json").read_text())
    report["splits"][-1]["metrics"]["selected_net_pnl"] = "-1"
    report["splits"][-1]["metrics"]["gates"]["selected_counterfactual_pnl"] = False
    report["splits"][-1]["metrics"]["passed"] = False
    report["gates"]["holdout"] = False
    (directory / "validation.json").write_text(json.dumps(report))
    rehash(directory)
    with pytest.raises(ModelUnavailable, match="failed"):
        load(directory)


def test_model_adds_gate_without_changing_risk_and_cannot_be_bypassed(
    engine_factory, ml_demo, research_model
):
    engine = engine_factory(model=research_model)
    vector = high_vector(ml_demo)
    scored = candidate(requires_ml=True, model_version=research_model.version)
    assert engine.submit(scored, NOW, features=vector)["state"] == "ACCEPTED"
    assert engine.submit(scored, NOW, features=vector)["state"] == "ACCEPTED"
    with pytest.raises(IntentConflict):
        engine.submit(
            scored,
            NOW,
            features=vector.model_copy(update={"values": tuple(0.0 for _ in vector.values)}),
        )
    assert "MODEL_REQUIRED" in engine.submit(candidate("unscored"), NOW)["reason"]
    assert (
        "MODEL_FEATURE_CONTEXT"
        in engine.submit(
            candidate("missing", requires_ml=True, model_version=research_model.version), NOW
        )["reason"]
    )
    wrong = candidate("wrong", requires_ml=True)
    assert (
        "MODEL_CONTEXT_MISMATCH"
        in engine.submit(wrong, NOW, features=high_vector(ml_demo, intent=wrong))["reason"]
    )
    changed_stop = candidate(
        "changed-stop", stop="494", requires_ml=True, model_version=research_model.version
    )
    assert "MODEL_FEATURE_CONTEXT" in engine.submit(changed_stop, NOW, features=vector)["reason"]
    engine.kill(NOW)
    killed_intent = candidate("killed", requires_ml=True, model_version=research_model.version)
    killed = engine.submit(
        killed_intent,
        NOW,
        features=high_vector(ml_demo, intent=killed_intent),
    )
    assert "KILL_SWITCH" in killed["reason"] and killed["state"] == "REJECTED"
    assert engine.snapshot(NOW)["cash"] == "25000"


def test_model_cannot_raise_quantity_or_bypass_position_limits(
    engine_factory, ml_demo, research_model
):
    engine = engine_factory(model=research_model)
    vector = high_vector(ml_demo)
    result = engine.submit(
        candidate(requires_ml=True, model_version=research_model.version), NOW, features=vector
    )
    baseline = engine_factory().submit(candidate(), NOW)
    assert (
        result["quantity"] == baseline["quantity"]
        and result["reserved_risk"] == baseline["reserved_risk"]
    )
    other = candidate("other", requires_ml=True, model_version=research_model.version)
    assert (
        "ENTRY_ALREADY_PENDING"
        in engine.submit(other, NOW, features=high_vector(ml_demo, intent=other))["reason"]
    )
    assert result["quantity"] * float(result["cap"]) <= float(engine.settings.max_position_notional)


def test_account_cannot_restart_with_model_gate_removed(engine_factory, research_model):
    engine = engine_factory(model=research_model)
    engine.db.close()
    db = Database(engine.settings.database, engine.settings.starting_cash)
    try:
        with pytest.raises(ValueError, match="model changed"):
            PaperBroker(db, engine.settings, engine.calendar)
    finally:
        db.close()


def test_missing_model_metadata_fails_closed_and_preserves_pending_orders(
    engine_factory, ml_demo, research_model
):
    engine = engine_factory(model=research_model)
    intent = candidate(requires_ml=True, model_version=research_model.version)
    assert engine.submit(intent, NOW, features=high_vector(ml_demo))["state"] == "ACCEPTED"
    with engine.db.transaction() as tx:
        tx.execute("DELETE FROM meta WHERE key='model_version'")
    engine.db.close()
    db = Database(engine.settings.database, engine.settings.starting_cash)
    try:
        with pytest.raises(RuntimeError, match="model gate metadata"):
            PaperBroker(db, engine.settings, engine.calendar)
        with db.transaction() as tx:
            assert (
                tx.execute("SELECT state FROM orders WHERE id='entry'").fetchone()[0] == "ACCEPTED"
            )
    finally:
        db.close()


def test_inference_never_imports_heavy_training_dependencies(ml_demo):
    program = """
import sys
from pathlib import Path
from trading_agent.ml.inference import load_model
from trading_agent.risk.policy import policy_fingerprint
from trading_agent.settings import Settings
from trading_agent.strategy.rules import StrategySettings
from trading_agent.execution.costs import Charges
load_model(Path(sys.argv[1]), strategy_sha256=StrategySettings().digest(),
    policy_sha256=policy_fingerprint(Settings()), charges_version=Charges().version,
    allow_synthetic=True)
assert not {'numpy', 'sklearn', 'scipy', 'pickle', 'joblib'} & set(sys.modules)
"""
    subprocess.run(
        [sys.executable, "-c", program, str(ml_demo[0] / "model")], check=True, capture_output=True
    )
