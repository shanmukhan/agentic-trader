"""Actual local CLI invocation with invented inputs; no worker or broker is launched."""

import json
import os
import subprocess
import sys
from pathlib import Path


def test_registration_cli_validates_copies_and_repeats_without_opening_account(
    tmp_path, execution_inputs
):
    daily, execution, _ = execution_inputs
    account = tmp_path / "operator.sqlite3"
    config = tmp_path / "operator.toml"
    secret = "invented-operator-token-" + "s" * 40
    config.write_text(
        f"database = {json.dumps(str(account))}\noperator_token = {json.dumps(secret)}\n"
    )
    command = [
        sys.executable,
        "-m",
        "trading_agent.main",
        "--config",
        str(config),
        "register-backtest",
        str(daily),
        str(execution),
        "--strategy",
        "config/daily-strategy.toml",
        "--policy",
        "config/long-term.toml",
        "--label",
        "SYNTHETIC CLI fixture",
    ]
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("TRADING_")
    }
    first = subprocess.run(command, capture_output=True, text=True, env=environment, check=True)
    result = json.loads(first.stdout)
    assert result["synthetic"] is True
    assert result["provenance"]["semantics"] == "legacy-offline-v1"
    assert result["strategy"]["max_hold_sessions"] == 20
    assert secret not in first.stdout
    assert str(account) not in first.stdout
    registry = account.with_suffix(".research-jobs")
    assert (registry / "resources" / result["resource_id"] / "resource.json").is_file()
    assert not account.exists()
    assert not (registry / "jobs").exists()
    second = subprocess.run(command, capture_output=True, text=True, env=environment, check=True)
    assert json.loads(second.stdout) == result
    assert len(list((registry / "resources").iterdir())) == 1
    assert not account.exists()


def test_registration_cli_rejects_intraday_policy_without_account_or_resource(
    tmp_path, execution_inputs
):
    daily, execution, _ = execution_inputs
    root = tmp_path / "rejected"
    policy = tmp_path / "intraday.toml"
    policy.write_text('investment_horizon = "intraday"\n')
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "trading_agent.main",
            "register-backtest",
            str(daily),
            str(execution),
            "--strategy",
            str(Path("config/daily-strategy.toml")),
            "--policy",
            str(policy),
            "--registry",
            str(root),
            "--label",
            "INVENTED reject",
        ],
        capture_output=True,
        text=True,
        env={key: value for key, value in os.environ.items() if not key.startswith("TRADING_")},
    )
    assert result.returncode == 1 and "Traceback" not in result.stderr
    assert "ValueError" in result.stderr and not result.stdout
    assert not root.exists()
