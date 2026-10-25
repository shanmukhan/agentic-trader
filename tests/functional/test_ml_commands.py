import json
import subprocess
import sys

from trading_agent.main import execute, parser


def test_complete_ml_cli_and_artifacts_are_isolated_from_service_account(tmp_path):
    config = tmp_path / "paper.toml"
    service = tmp_path / "service.sqlite3"
    config.write_text(f'database="{service}"\n')
    directory = tmp_path / "demo"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "trading_agent.main",
            "--config",
            str(config),
            "ml-demo",
            "--directory",
            str(directory),
        ],
        check=True,
        text=True,
        capture_output=True,
    )
    summary = json.loads(result.stdout)
    assert summary["synthetic"] and not summary["ready_for_live"]
    assert summary["label_counts"]["labeled"] == 60
    assert summary["validation_gates"] == {
        "walk_forward": True,
        "holdout": True,
        "non_synthetic": False,
    }
    assert summary["baseline_metrics"]["completed_trades"] == 10
    assert summary["scored_metrics"]["completed_trades"] == 5
    assert not service.exists()
    built = execute(
        parser().parse_args(
            [
                "--config",
                str(config),
                "ml-build",
                str(directory / "training-data"),
                "--output",
                str(tmp_path / "labels"),
            ]
        )
    )
    assert built["counts"]["labeled"] == 60 and not service.exists()
    trained = execute(
        parser().parse_args(
            [
                "--config",
                str(config),
                "ml-train",
                str(tmp_path / "labels"),
                "--training",
                "config/ml-demo.toml",
                "--output",
                str(tmp_path / "model"),
            ]
        )
    )
    assert not trained["research_approved"] and trained["gates"]["holdout"]
    rerun = execute(
        parser().parse_args(
            [
                "--config",
                str(config),
                "backtest",
                str(directory / "future-data"),
                "--model",
                str(tmp_path / "model"),
                "--allow-synthetic-model",
                "--output",
                str(tmp_path / "scored"),
            ]
        )
    )
    assert rerun["metrics"]["net_pnl"] == "504.70" and not service.exists()
    decisions = [
        json.loads(line) for line in (tmp_path / "scored/decisions.jsonl").read_text().splitlines()
    ]
    probabilities = [row["ml_probability"] for row in decisions if "ml_probability" in row]
    assert len(probabilities) == 10
    assert all(0 <= probability <= 1 for probability in probabilities)
    assert len(set(probabilities)) > 1
    artifact = json.loads((tmp_path / "model/model.json").read_text())
    readable = (tmp_path / "model/validation.md").read_text()
    assert "not causal feature importance" in readable
    for feature, weight in zip(
        artifact["feature_names"], artifact["coefficients"]["weights"], strict=True
    ):
        row = next(line for line in readable.splitlines() if line.startswith(f"| {feature} |"))
        assert float(row.split("|")[4]) == float(f"{weight:.12g}")
    for path in (
        directory / "model/validation.md",
        directory / "model/manifest.json",
        directory / "samples/manifest.json",
        tmp_path / "scored/report.md",
    ):
        assert path.is_file()


def test_ml_commands_refuse_wrong_mode_invalid_override_and_missing_training_data(tmp_path):
    import pytest

    config = tmp_path / "bad.toml"
    config.write_text('mode="live"\n')
    with pytest.raises(ValueError):
        execute(
            parser().parse_args(
                ["--config", str(config), "ml-demo", "--directory", str(tmp_path / "demo")]
            )
        )
    assert not (tmp_path / "demo").exists()
    with pytest.raises(ValueError, match="requires"):
        execute(
            parser().parse_args(
                [
                    "backtest",
                    "missing-data",
                    "--allow-synthetic-model",
                    "--output",
                    str(tmp_path / "out"),
                ]
            )
        )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "trading_agent.main",
            "ml-train",
            str(tmp_path / "absent"),
            "--output",
            str(tmp_path / "model"),
        ],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1 and "FileNotFoundError" in result.stderr
    assert "Traceback" not in result.stderr and not (tmp_path / "model").exists()
