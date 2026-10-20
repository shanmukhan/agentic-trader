import json
import subprocess
import sys

from trading_agent.daily_execution.demo import create_execution_demo


def test_daily_replay_label_train_commands_use_isolated_outputs(tmp_path):
    daily, execution, _ = create_execution_demo(tmp_path / "inputs", sessions=50)
    absent = tmp_path / "untouched.sqlite3"
    config = tmp_path / "long-term.toml"
    config.write_text('investment_horizon="long_term"\ndatabase=' + json.dumps(str(absent)) + "\n")
    cmd = [sys.executable, "-m", "trading_agent.main", "--config", str(config)]
    for command in ("daily-backtest", "daily-labels"):
        result = subprocess.run(
            cmd + [command, str(daily), str(execution), "--output", str(tmp_path / command)],
            capture_output=True,
            text=True,
            check=True,
        )
        payload = json.loads(result.stdout)
        assert payload["kind"].startswith("daily-delivery-") and not payload["ready_for_live"]
        assert (tmp_path / command / "index.html").exists()
    result = subprocess.run(
        cmd
        + [
            "daily-train",
            str(tmp_path / "daily-labels"),
            "--training",
            "config/daily-ml-demo.toml",
            "--output",
            str(tmp_path / "model"),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(result.stdout)["gates"]["holdout"]
    assert not absent.exists()
    failed = subprocess.run(
        cmd
        + [
            "daily-backtest",
            str(daily),
            str(execution),
            "--output",
            str(tmp_path / "daily-backtest"),
        ],
        capture_output=True,
        text=True,
    )
    assert failed.returncode == 1 and "Traceback" not in failed.stderr


def test_daily_execution_refuses_intraday_configuration_before_output(tmp_path):
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "trading_agent.main",
            "daily-backtest",
            "absent",
            "absent",
            "--output",
            str(tmp_path / "bad"),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1 and not (tmp_path / "bad").exists()
    assert "Traceback" not in result.stderr
