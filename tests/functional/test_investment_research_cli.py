"""Isolated subprocess research with invented data, denied network and no account."""

import hashlib
import json
import os
import stat
import subprocess
import sys
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path

import pytest

from trading_agent.daily_research.demo import create_daily_demo


@pytest.fixture
def isolated_cli(tmp_path):
    absent = tmp_path / "operator-account-must-not-be-created.sqlite3"
    config = tmp_path / "paper.toml"
    config.write_text("database=" + json.dumps(str(absent)) + "\n")
    guard = tmp_path / "network-guard"
    guard.mkdir()
    (guard / "sitecustomize.py").write_text(
        "import socket\n"
        "def prohibited(*args, **kwargs):\n"
        "    raise AssertionError('Research subprocess attempted network access')\n"
        "socket.create_connection = prohibited\n"
        "socket.socket.connect = prohibited\n"
        "socket.socket.connect_ex = prohibited\n"
    )
    environment = {
        key: value for key, value in os.environ.items() if not key.startswith("TRADING_")
    }
    source = Path(__file__).resolve().parents[2] / "src"
    environment["PYTHONPATH"] = os.pathsep.join((str(guard), str(source)))
    environment["TRADING_MODE"] = "paper"
    dataset = tmp_path / "invented-daily"
    as_of = create_daily_demo(dataset)

    def run(output, *extra, as_of_value=None):
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "trading_agent.main",
                "--config",
                str(config),
                "investment-analyze",
                str(dataset),
                "--symbol",
                "NSE:TREND",
                "--as-of",
                as_of.isoformat() if as_of_value is None else as_of_value,
                "--output",
                str(output),
                *extra,
            ],
            capture_output=True,
            text=True,
            env=environment,
            timeout=30,
        )

    return run, dataset, absent


def assert_no_account(path):
    assert not path.exists()
    assert not Path(str(path) + ".lock").exists()
    assert not Path(str(path) + "-wal").exists()
    assert not Path(str(path) + "-shm").exists()


def test_subprocess_writes_private_hashed_finished_report_without_account_or_network(
    isolated_cli,
    tmp_path,
):
    run, dataset, absent = isolated_cli
    original = {path.name: path.read_bytes() for path in dataset.iterdir()}
    output = tmp_path / "isolated-price-report"
    response = run(output, "--timeframe", "1d")
    assert response.returncode == 0, response.stderr
    report = json.loads(response.stdout)
    stored = json.loads((output / "report.json").read_text())
    manifest = json.loads((output / "manifest.json").read_text())
    assert report == stored
    assert stored["source"]["synthetic"] is True
    assert stored["timeframe"] == "1d" and len(stored["bars"]) == 90
    assert stored["bars"][-1]["rsi14"] is not None
    assert stored["research"]["benchmark"]["state"] == "unavailable"
    assert stored["research"]["fundamentals"]["state"] == "unavailable"
    assert manifest["state"] == "finished" and manifest["schema_version"] == 1
    assert manifest["snapshot_id"] == stored["research"]["snapshot_id"]
    assert manifest["execution_simulated"] is False and manifest["ready_for_live"] is False
    assert set(manifest["sha256"]) == {"report.json", "report.md"}
    for name, expected in manifest["sha256"].items():
        assert hashlib.sha256((output / name).read_bytes()).hexdigest() == expected
    assert stat.S_IMODE(output.stat().st_mode) == 0o700
    assert all(stat.S_IMODE(path.stat().st_mode) == 0o600 for path in output.iterdir())
    assert {path.name: path.read_bytes() for path in dataset.iterdir()} == original
    assert_no_account(absent)
    # A second command cannot overwrite evidence or claim another successful run.
    saved = {path.name: path.read_bytes() for path in output.iterdir()}
    repeated = run(output)
    assert repeated.returncode == 1 and "Traceback" not in repeated.stderr
    assert not repeated.stdout
    assert {path.name: path.read_bytes() for path in output.iterdir()} == saved
    assert_no_account(absent)


@pytest.mark.parametrize("interval", ["1w", "1mo"])
def test_subprocess_without_calendar_review_reports_no_invented_completed_periods(
    isolated_cli,
    tmp_path,
    interval,
):
    run, _, absent = isolated_cli
    output = tmp_path / ("incomplete-" + interval)
    response = run(output, "--timeframe", interval)
    assert response.returncode == 0, response.stderr
    result = json.loads(response.stdout)
    assert result["timeframe"] == interval and not result["bars"]
    assert not result["research"]["coverage"]["calendar_verified"]
    assert result["research"]["partial_periods"]
    assert all(
        row["reason"] == "CALENDAR_COVERAGE_UNVERIFIED"
        for row in result["research"]["partial_periods"]
    )
    assert json.loads((output / "manifest.json").read_text())["state"] == "finished"
    assert_no_account(absent)


@pytest.mark.parametrize("as_of", ["2026-09-04T10:30:00", "not-a-date"])
def test_subprocess_rejects_ambiguous_asof_without_finished_report_or_account(
    isolated_cli,
    tmp_path,
    as_of,
):
    run, _, absent = isolated_cli
    output = tmp_path / "invalid-clock"
    response = run(output, as_of_value=as_of)
    assert response.returncode != 0 and "Traceback" not in response.stderr
    assert not response.stdout and not (output / "manifest.json").exists()
    assert not output.exists()
    assert_no_account(absent)


def test_subprocess_rejects_bad_hash_bound_context_without_finished_report_or_account(
    isolated_cli,
    tmp_path,
):
    run, _, absent = isolated_cli
    context = tmp_path / "untrusted-context.json"
    context.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "dataset_sha256": {"manifest.json": "0" * 64, "daily.jsonl": "0" * 64},
                "calendar": {
                    "start": "2026-05-01",
                    "end": "2026-10-31",
                    "available_at": "2026-05-01T00:00:00Z",
                    "reference": "INVENTED review with deliberately incorrect source hashes",
                    "completeness_reviewed": True,
                },
            }
        )
    )
    output = tmp_path / "wrong-context"
    response = run(output, "--context", str(context))
    assert response.returncode == 1 and "Traceback" not in response.stderr
    assert not response.stdout and not output.exists()
    assert_no_account(absent)


def test_subprocess_cannot_put_report_inside_daily_source(isolated_cli):
    run, dataset, absent = isolated_cli
    output = dataset / "report"
    response = run(output)
    assert response.returncode == 1 and "Traceback" not in response.stderr
    assert not output.exists()
    assert_no_account(absent)


@pytest.mark.parametrize("synthetic", [True, False])
def test_subprocess_compares_declared_daily_benchmark_only_with_matching_source_labels(
    isolated_cli,
    tmp_path,
    synthetic,
):
    run, dataset, absent = isolated_cli
    manifest = json.loads((dataset / "manifest.json").read_text())
    sessions = manifest["sessions"]
    benchmark = {
        "schema_version": 1,
        "series_id": "invented-index",
        "title": "Invented index fixture",
        "provider": "Local test declaration",
        "source_url": "https://example.invalid/index",
        "license_reference": "Invented test fixture; no licensed market evidence",
        "currency": "INR",
        "return_type": "gross_total_return",
        "synthetic": synthetic,
        "published_at": "2026-05-01T00:00:00Z",
        "available_at": "2026-05-01T00:01:00Z",
        "rows": [
            {
                "session": session["day"],
                "level": str(1000 + index),
                "close_at": session["day"] + "T15:30:00+05:30",
                "available_at": session["day"] + "T15:40:00+05:30",
            }
            for index, session in enumerate(sessions)
        ],
    }
    path = tmp_path / "declared-benchmark.json"
    path.write_text(json.dumps(benchmark))
    output = tmp_path / "benchmark-report"
    response = run(output, "--benchmark", str(path))
    assert response.returncode == 0, response.stderr
    comparison = json.loads(response.stdout)["research"]["benchmark"]
    assert comparison["metadata"]["synthetic"] is synthetic
    if not synthetic:
        assert comparison["state"] == "unavailable"
        assert comparison["reason"] == "SOURCE_PROVENANCE_MISMATCH"
        assert comparison["relative_strength_pct"] is None
    else:
        assert comparison["state"] == "available" and comparison["interval"] == "1d"
        raw = [json.loads(line) for line in (dataset / "daily.jsonl").read_text().splitlines()]
        rows = [row for row in raw if row["symbol"] == "NSE:TREND"]
        # The final twenty invented intervals contain no cash/share actions, so
        # their exact wealth factor reduces to the ratio of their raw closes.
        assert all(row["share_numerator"] == 1 for row in rows[-20:])
        assert all(Decimal(row["cash_per_previous_share"]) == 0 for row in rows[-20:])
        stock_factor = Fraction(Decimal(rows[-1]["close"])) / Fraction(Decimal(rows[-21]["close"]))
        index_factor = Fraction(1089, 1069)
        relative = 100 * (stock_factor / index_factor - 1)
        with localcontext() as context:
            context.prec = 60
            expected = (Decimal(relative.numerator) / Decimal(relative.denominator)).quantize(
                Decimal("0.000000000001")
            )
        assert comparison["relative_strength_pct"] == str(expected)
    assert_no_account(absent)
