import hashlib
import json
import subprocess
import sys


def test_portfolio_demo_preserves_configured_account_and_finished_artifacts(tmp_path):
    config = tmp_path / "paper.toml"
    absent = tmp_path / "untouched.sqlite3"
    config.write_text("database=" + json.dumps(str(absent)) + "\n")
    output = tmp_path / "demo"
    command = [
        sys.executable,
        "-m",
        "trading_agent.main",
        "--config",
        str(config),
        "portfolio-demo",
        "--directory",
        str(output),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    summary = json.loads(result.stdout)
    assert summary["final_cash"] == "25273.45"
    assert summary["acquisition_lots"] == 4 and summary["restart_order_state"] == "CANCELLED"
    assert summary["held_before_sale"] == 6 and not summary["ready_for_live"]
    assert not absent.exists()
    manifest = json.loads((output / "manifest.json").read_text())
    for name, expected in manifest["sha256"].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == expected
        assert (output / name).stat().st_mode & 0o777 == 0o600
    repeated = subprocess.run(command, capture_output=True, text=True)
    assert repeated.returncode == 1 and "Traceback" not in repeated.stderr
