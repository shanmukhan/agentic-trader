"""Offline fitting only. Holdout is inspected after final coefficients are frozen."""

import json
import platform
import warnings
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

from trading_agent.backtesting.dataset import digest_file
from trading_agent.backtesting.report import code_digest
from trading_agent.market_data.calendar import IST
from trading_agent.ml.inference import Artifact, ArtifactManifest, Coefficients
from trading_agent.ml.samples import Samples
from trading_agent.ml.schema import Sample, TrainingSettings
from trading_agent.ml.splits import Split, chronological_splits


def fit(split: Split, settings: TrainingSettings) -> Coefficients:
    import numpy as np
    from sklearn.exceptions import ConvergenceWarning
    from sklearn.linear_model import LogisticRegression
    from sklearn.preprocessing import StandardScaler

    for name, rows, minimum in (
        ("train", split.train, settings.min_train_samples),
        ("calibration", split.calibration, settings.min_calibration_samples),
    ):
        if (
            len(rows) < minimum
            or min(sum(row.target == cls for row in rows) for cls in (0, 1))
            < settings.min_class_samples
        ):
            raise ValueError(f"insufficient {name} samples/classes after interval purge")
    x = np.asarray([row.features.values for row in split.train], dtype=np.float64)
    y = np.asarray([row.target for row in split.train])
    scaler = StandardScaler().fit(x)
    estimator = LogisticRegression(
        C=settings.regularization_c,
        solver="lbfgs",
        tol=1e-9,
        max_iter=settings.max_iterations,
        random_state=0,
    )
    calibrator = LogisticRegression(
        C=settings.regularization_c,
        solver="lbfgs",
        tol=1e-9,
        max_iter=settings.max_iterations,
        random_state=0,
    )
    with warnings.catch_warnings():
        warnings.simplefilter("error", ConvergenceWarning)
        estimator.fit(scaler.transform(x), y)
        cal_x = np.asarray([row.features.values for row in split.calibration], dtype=np.float64)
        cal_scores = estimator.decision_function(scaler.transform(cal_x)).reshape(-1, 1)
        calibrator.fit(cal_scores, [row.target for row in split.calibration])
    return Coefficients(
        means=tuple(float(v) for v in scaler.mean_),
        scales=tuple(float(v) for v in scaler.scale_),
        weights=tuple(float(v) for v in estimator.coef_[0]),
        intercept=float(estimator.intercept_[0]),
        calibration_slope=float(calibrator.coef_[0][0]),
        calibration_intercept=float(calibrator.intercept_[0]),
    )


def evaluate(
    rows: tuple[Sample, ...], model: Coefficients, baseline: float, settings: TrainingSettings
) -> dict[str, Any]:
    from sklearn.metrics import brier_score_loss, log_loss, roc_auc_score

    y: list[int] = [row.target for row in rows]
    p = [model.probability(row.features) for row in rows]
    bins: list[dict[str, Any]] = []
    for index in range(10):
        selected = [
            j
            for j, prob in enumerate(p)
            if index / 10 <= prob < (index + 1) / 10 or index == 9 and prob == 1
        ]
        bins.append(
            {
                "lower": index / 10,
                "upper": (index + 1) / 10,
                "count": len(selected),
                "mean_probability": sum(p[j] for j in selected) / len(selected)
                if selected
                else None,
                "fraction_positive": sum(y[j] for j in selected) / len(selected)
                if selected
                else None,
            }
        )
    ece = sum(
        item["count"] / len(rows) * abs(item["mean_probability"] - item["fraction_positive"])
        for item in bins
        if item["count"]
    )
    selected_rows = [
        row for row, prob in zip(rows, p, strict=True) if prob >= settings.probability_threshold
    ]
    auc = float(roc_auc_score(y, p)) if len(set(y)) == 2 else None
    brier = float(brier_score_loss(y, p))
    baseline_brier = float(brier_score_loss(y, [baseline] * len(y)))
    pnl = sum((row.net_pnl for row in selected_rows), Decimal(0))
    gates = {
        "sample_count": len(rows) >= settings.min_evaluation_samples,
        "both_classes": min(y.count(cls) for cls in (0, 1)) >= settings.min_class_samples,
        "auc": auc is not None and auc >= settings.min_auc,
        "brier_over_train_baseline": brier < baseline_brier,
        "calibration": ece <= settings.max_calibration_error,
        "selected_count": len(selected_rows) >= settings.min_selected_samples,
        "selected_counterfactual_pnl": pnl > 0,
    }
    return {
        "count": len(rows),
        "positive_count": sum(y),
        "roc_auc": auc,
        "brier": brier,
        "baseline_probability_from_training_only": baseline,
        "baseline_brier": baseline_brier,
        "log_loss": float(log_loss(y, p, labels=[0, 1])),
        "expected_calibration_error": ece,
        "reliability_bins": bins,
        "selected_count": len(selected_rows),
        "selected_net_pnl": str(pnl),
        "gates": gates,
        "passed": all(gates.values()),
    }


def train_model(samples: Samples, *, settings: TrainingSettings, output: Path) -> dict[str, Any]:
    import numpy
    import sklearn

    output = output.resolve()
    if output.is_relative_to(samples.directory):
        raise ValueError("model output must be outside the sample bundle")
    rows = samples.read()
    splits = chronological_splits(rows, samples.manifest.sessions, settings)
    output.mkdir(parents=True, exist_ok=False, mode=0o700)
    diagnostics: list[dict[str, Any]] = []
    last_session = max(samples.manifest.source_manifest.sessions, key=lambda session: session.day)
    validation_session_end = datetime.combine(last_session.day, last_session.close, IST)
    validation_label_end = max(row.label_end for row in splits[-1].evaluation)
    validated_through = max(
        validation_label_end, validation_session_end, samples.manifest.source_available_through
    )
    for split in splits:
        coefficients = fit(split, settings)
        if split.name == "holdout":
            artifact = Artifact(
                coefficients=coefficients,
                label_policy=samples.manifest.label_policy,
                synthetic=samples.manifest.synthetic,
                strategy_sha256=samples.manifest.strategy_sha256,
                policy_sha256=samples.manifest.policy_sha256,
                charges_version=samples.manifest.charges_version,
                samples_manifest_sha256=samples.digest,
                training_sha256=settings.digest(),
                code_sha256=code_digest(),
                fit_label_end=max(row.label_end for row in (*split.train, *split.calibration)),
                validation_label_end=validation_label_end,
                validated_through=validated_through,
                available_after=validated_through + timedelta(minutes=settings.embargo_minutes),
                embargo_minutes=settings.embargo_minutes,
                threshold=settings.probability_threshold,
            )
            # Freeze the exported model before computing holdout outcome diagnostics.
            (output / "model.json").write_text(artifact.model_dump_json(indent=2) + "\n")
        metrics = evaluate(
            split.evaluation,
            coefficients,
            sum(row.target for row in split.train) / len(split.train),
            settings,
        )
        diagnostics.append(
            {
                "name": split.name,
                "train_count": len(split.train),
                "calibration_count": len(split.calibration),
                "train_first": min(row.features.time for row in split.train).isoformat(),
                "train_last": max(row.features.time for row in split.train).isoformat(),
                "train_label_end": max(row.label_end for row in split.train).isoformat(),
                "calibration_first": min(
                    row.features.time for row in split.calibration
                ).isoformat(),
                "calibration_last": max(row.features.time for row in split.calibration).isoformat(),
                "calibration_label_end": max(
                    row.label_end for row in split.calibration
                ).isoformat(),
                "evaluation_first": min(row.features.time for row in split.evaluation).isoformat(),
                "evaluation_last": max(row.features.time for row in split.evaluation).isoformat(),
                "evaluation_label_end": max(row.label_end for row in split.evaluation).isoformat(),
                "purged_train": split.purged_train,
                "purged_calibration": split.purged_calibration,
                "metrics": metrics,
            }
        )
    samples.assert_unchanged()
    gates = {
        "walk_forward": all(d["metrics"]["passed"] for d in diagnostics[:-1]),
        "holdout": diagnostics[-1]["metrics"]["passed"],
        "non_synthetic": not samples.manifest.synthetic,
    }
    report: dict[str, Any] = {
        "schema_version": 1,
        "ready_for_live": False,
        "research_approved": all(gates.values()),
        "model_sha256": digest_file(output / "model.json"),
        "training_sha256": settings.digest(),
        "settings": settings.model_dump(),
        "samples_manifest_sha256": samples.digest,
        "samples_counts": samples.manifest.counts,
        "source_available_through": samples.manifest.source_available_through.isoformat(),
        "validation_session_end": validation_session_end.isoformat(),
        "synthetic": samples.manifest.synthetic,
        "runtime": {
            "python": platform.python_version(),
            "numpy": numpy.__version__,
            "sklearn": sklearn.__version__,
        },
        "gates": gates,
        "splits": diagnostics,
    }
    (output / "validation.json").write_text(
        json.dumps(report, sort_keys=True, indent=2, allow_nan=False) + "\n"
    )
    (output / "validation.md").write_text(
        "# Offline model validation\n\nPAPER RESEARCH ONLY. Ready for live: false.\n\n"
        + "Synthetic: "
        + str(samples.manifest.synthetic)
        + ". Research gates: `"
        + json.dumps(gates, sort_keys=True)
        + "`.\n\n"
        + "| Split | Count | ROC-AUC | Brier | ECE | Selected | Net counterfactual P&L | Passed |\n"
        + "|---|---:|---:|---:|---:|---:|---:|---|\n"
        + "".join(
            f"| {d['name']} | {d['metrics']['count']} | {d['metrics']['roc_auc']} "
            f"| {d['metrics']['brier']:.6f} | {d['metrics']['expected_calibration_error']:.6f} "
            f"| {d['metrics']['selected_count']} | {d['metrics']['selected_net_pnl']} "
            f"| {d['metrics']['passed']} |\n"
            for d in diagnostics
        )
        + "\nFinal coefficients were frozen before holdout metrics were computed. "
        "No threshold or parameter search runs. Selected trade P&L sums isolated labels, "
        "not portfolio performance. Hashes, split windows, purges and reliability bins "
        "are in validation.json.\n"
    )
    manifest = ArtifactManifest(
        model_sha256=report["model_sha256"],
        validation_sha256=digest_file(output / "validation.json"),
    )
    (output / "manifest.json").write_text(manifest.model_dump_json(indent=2) + "\n")
    return report
