import json
import subprocess
import sys

import pytest

from trading_agent.daily_research.demo import create_daily_demo


def test_daily_cli_demo_and_explicit_as_of_report_never_open_service_account(tmp_path):
    config = tmp_path / "paper.toml"
    absent = tmp_path / "untouched.sqlite3"
    config.write_text("database=" + json.dumps(str(absent)) + "\n")
    cmd = [sys.executable, "-m", "trading_agent.main", "--config", str(config)]
    directory = tmp_path / "demo"
    result = subprocess.run(
        cmd + ["daily-research-demo", "--directory", str(directory)],
        capture_output=True,
        text=True,
        check=True,
    )
    report = json.loads(result.stdout)
    assert report["candidate_count"] == 1 and report["synthetic"]
    assert not absent.exists() and (directory / "report/index.html").exists()
    output = tmp_path / "historical"
    result = subprocess.run(
        cmd
        + [
            "daily-analyze",
            str(directory / "dataset"),
            "--as-of",
            "2026-07-01T11:00:00Z",
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    assert json.loads(result.stdout)["latest_reviewed_completed_session"] == "2026-07-01"
    assert not absent.exists()
    failed = subprocess.run(
        cmd + ["daily-research-demo", "--directory", str(directory)], capture_output=True, text=True
    )
    assert failed.returncode == 1 and "Traceback" not in failed.stderr


@pytest.mark.parametrize("as_of", ["2026-09-04T10:30:00", "not-a-date"])
def test_daily_cli_rejects_ambiguous_as_of_and_leaves_no_success_bundle(tmp_path, as_of):
    directory = tmp_path / "daily"
    create_daily_demo(directory)
    output = tmp_path / "invalid"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "trading_agent.main",
            "daily-analyze",
            str(directory),
            "--as-of",
            as_of,
            "--output",
            str(output),
        ],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0 and "Traceback" not in result.stderr
    assert not (output / "manifest.json").exists()
