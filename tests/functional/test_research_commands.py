import json
import subprocess
import sys
from datetime import timedelta

from conftest import NOW, candidate

from trading_agent.backtesting.dataset import CandleEvent
from trading_agent.main import execute, parser
from trading_agent.market_data.repository import store_candles
from trading_agent.persistence.database import Database


def test_research_demo_and_backtest_cli_generate_reports(tmp_path):
    path = tmp_path / "demo"
    command = [
        sys.executable,
        "-m",
        "trading_agent.main",
        "research-demo",
        "--directory",
        str(path),
    ]
    response = subprocess.run(command, check=True, text=True, capture_output=True)
    summary = json.loads(response.stdout)
    assert summary["metrics"]["completed_trades"] == 2
    assert not summary["ready_for_live"]
    assert (path / "run/report.md").is_file()
    rerun = tmp_path / "another-run"
    args = parser().parse_args(["backtest", str(path / "dataset"), "--output", str(rerun)])
    assert execute(args)["metrics"]["net_pnl"] == "-25.97"
    assert json.loads((rerun / "run.json").read_text())["state"] == "finished"


def test_export_cli_does_not_recover_cancel_source_orders(engine, research_dataset, tmp_path):
    candles = [e.candle for e in research_dataset.events() if isinstance(e, CandleEvent)]
    store_candles(engine.db, candles, NOW + timedelta(days=2))
    engine.submit(candidate(), NOW)
    settings = engine.settings
    engine.db.close()
    calendar = tmp_path / "calendar.csv"
    calendar.write_text(
        "date,open,close,source\n2026-10-20,09:15,15:30,test-source\n"
        "2026-10-21,09:15,15:30,test-source\n"
    )
    config = tmp_path / "paper.toml"
    config.write_text(f'database="{settings.database}"\ncalendar="{calendar}"\n')
    output = tmp_path / "dataset-output"
    args = parser().parse_args(
        [
            "--config",
            str(config),
            "export-research",
            "--start",
            (NOW - timedelta(hours=1)).isoformat(),
            "--end",
            (NOW + timedelta(days=2)).isoformat(),
            "--symbols",
            "NSE:DEMO",
            "--source",
            "operator-reviewed test",
            "--output",
            str(output),
        ]
    )
    assert execute(args)["candle"] == 28
    db = Database(settings.database, settings.starting_cash)
    try:
        with db.transaction() as tx:
            assert (
                tx.execute("SELECT state FROM orders WHERE id='entry'").fetchone()[0] == "ACCEPTED"
            )
        assert (
            json.loads((output / "manifest.json").read_text())["sessions"][0]["source"]
            == "test-source"
        )
    finally:
        db.close()
