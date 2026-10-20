import json
import subprocess
import sys
from datetime import timedelta

import pytest
from conftest import NOW

from trading_agent.backtesting.report import journal_digest
from trading_agent.corporate_actions.contracts import ActionBatch, digest
from trading_agent.corporate_actions.service import load_request
from trading_agent.persistence.database import Database


def cli(args):
    # An explicit invented clock keeps receipt dates causal and the CLI test deterministic.
    code = (
        "from datetime import UTC,datetime; from trading_agent import main; "
        "main.clock=lambda:datetime(2026,10,22,4,30,tzinfo=UTC); main.main()"
    )
    return subprocess.run([sys.executable, "-c", code, *args], capture_output=True, text=True)


def config_for(engine, tmp_path):
    calendar = tmp_path / "sessions.csv"
    calendar.write_text(
        "date,open,close,source\n"
        + "".join(
            f"{day},09:15,15:30,{engine.calendar.sources[day]}\n"
            for day in engine.calendar.sessions
        )
    )
    config = tmp_path / "account.toml"
    values = engine.settings.model_dump(mode="json", exclude={"operator_token"})
    values["calendar"] = str(calendar)
    config.write_text(
        "".join(key + "=" + json.dumps(value) + "\n" for key, value in values.items())
    )
    return config


def request_for(engine, tmp_path):
    with engine.db.transaction() as tx:
        quarantine = json.loads(engine.db.get(tx, "lt_quarantine:NSE:DEMO"))
    payload = {
        "batch_id": "dividend-batch",
        "symbol": "NSE:DEMO",
        "quarantine_sha256": digest(quarantine),
        "reviewed_at": "2026-10-21T04:30:00Z",
        "reference": "INVENTED reviewed notice",
        "covers_all_actions": True,
        "actions": [
            {
                "action_id": "dividend",
                "kind": "dividend",
                "ex_date": "2026-10-21",
                "record_date": "2026-10-21",
                "payment_date": "2026-10-22",
                "announced_at": NOW.isoformat(),
                "reference": "INVENTED dividend entitlement",
                "per_share": "10.00",
                "withholding": "14.00",
            }
        ],
    }
    file = tmp_path / "actions.json"
    file.write_text(json.dumps(payload))
    return file


def test_cli_adjustment_receipt_and_report_preserve_source_and_restart_evidence(
    corporate_account, tmp_path
):
    engine = corporate_account
    engine.exit_holding("NSE:DEMO", NOW + timedelta(days=1))
    config, file = config_for(engine, tmp_path), request_for(engine, tmp_path)
    engine.db.close()
    args = ["--config", str(config)]
    applied = cli([*args, "apply-corporate-actions", "--file", str(file)])
    assert applied.returncode == 0, applied.stderr
    assert not json.loads(applied.stdout)["idempotent"]
    assert json.loads(cli([*args, "apply-corporate-actions", "--file", str(file)]).stdout)[
        "idempotent"
    ]
    receipt = tmp_path / "receipt.json"
    receipt.write_text(
        json.dumps(
            {
                "payment_id": "net-receipt",
                "claim_id": "dividend",
                "paid_date": "2026-10-22",
                "net_amount": "126.00",
                "reviewed_at": "2026-10-22T04:30:00Z",
                "reference": "INVENTED exact net cash receipt",
            }
        )
    )
    paid = cli([*args, "record-corporate-cash", "--file", str(receipt)])
    assert paid.returncode == 0, paid.stderr
    assert json.loads(paid.stdout)["cash"] == "126"
    db = Database(engine.settings.database, engine.settings.starting_cash)
    try:
        before = journal_digest(db)
        with db.transaction() as tx:
            assert db.get(tx, "cash") == "18114.18"
            assert (
                tx.execute("SELECT state FROM orders WHERE side='SELL'").fetchone()[0]
                == "CANCELLED"
            )
            assert tx.execute("SELECT 1 FROM meta WHERE key GLOB 'lt_exit:*'").fetchone()
    finally:
        db.close()
    report = cli([*args, "long-term-report", "--output", str(tmp_path / "report")])
    assert report.returncode == 0, report.stderr
    result = json.loads(report.stdout)
    assert result["schema_version"] == 2 and result["income_received"] == "126"
    assert len(result["corporate_action_batches"]) == 1 and not result["settlement_verified"]
    db = Database(engine.settings.database, engine.settings.starting_cash)
    try:
        assert journal_digest(db) == before
    finally:
        db.close()


def test_cli_corporate_action_demo_is_isolated_and_reconciles_all_benefits(tmp_path):
    directory = tmp_path / "demo"
    result = cli(["corporate-actions-demo", "--directory", str(directory)])
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout)
    assert report == {
        "synthetic": True,
        "ready_for_live": False,
        "cash": "25029.42",
        "realized_pnl": "-20.98",
        "income_received": "50.4",
        "fraction_realized_pnl": "-0.11",
        "positions": 0,
        "receivable": "0",
        "unvalued_fractional_claims": 0,
    }
    assert (directory / "evidence/manifest.json").exists()
    assert cli(["corporate-actions-demo", "--directory", str(directory)]).returncode == 1


def test_cli_cannot_mutate_an_account_owned_by_running_service(corporate_account, tmp_path):
    engine = corporate_account
    config, file = config_for(engine, tmp_path), request_for(engine, tmp_path)
    before = journal_digest(engine.db)
    result = cli(["--config", str(config), "apply-corporate-actions", "--file", str(file)])
    assert result.returncode == 1 and "Traceback" not in result.stderr
    assert journal_digest(engine.db) == before


@pytest.mark.parametrize("command", ["apply-corporate-actions", "record-corporate-cash"])
def test_cli_intraday_rejection_does_not_create_account(tmp_path, command):
    config = tmp_path / "intraday.toml"
    path = tmp_path / "must-not-exist.sqlite3"
    config.write_text("database=" + json.dumps(str(path)) + "\n")
    result = cli(["--config", str(config), command, "--file", "missing.json"])
    assert result.returncode == 1 and not path.exists()


@pytest.mark.parametrize(
    "content",
    [
        '{"batch_id":"one","batch_id":"two"}',
        " " * 65537,
        '{"value":NaN}',
    ],
)
def test_ambiguous_or_oversized_reviewed_input_is_refused(tmp_path, content):
    file = tmp_path / "bad.json"
    file.write_text(content)
    with pytest.raises(ValueError):
        load_request(file, ActionBatch)


def test_symlinked_input_is_refused(tmp_path):
    file = tmp_path / "input.json"
    file.write_text("{}")
    linked = tmp_path / "link.json"
    linked.symlink_to(file)
    with pytest.raises(ValueError, match="regular local file"):
        load_request(linked, ActionBatch)
