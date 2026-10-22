"""Synthetic replay evidence; these checks do not establish host sandbox or market acceptance."""

import csv
import hashlib
import io
import json
import sqlite3
from contextlib import closing
from decimal import Decimal
from pathlib import Path

import pytest

from trading_agent.daily_execution.dataset import ExecutionDataset
from trading_agent.daily_execution.runner import run_daily
from trading_agent.daily_research.dataset import DailyDataset
from trading_agent.research_jobs.registry import register_bundle
from trading_agent.research_jobs.reports import verify_report

D = Decimal
JOB = "11223344556677889900aabbccddeeff"


@pytest.fixture
def evidence(execution_inputs, daily_strategy, daily_policy, tmp_path):
    daily, execution, _ = execution_inputs
    registered = register_bundle(
        tmp_path / "registry",
        daily,
        execution,
        Path("config/daily-strategy.toml"),
        Path("config/long-term.toml"),
        "Invented verification fixture",
    )
    record = json.loads(
        (tmp_path / "registry/resources" / registered["resource_id"] / "resource.json").read_text()
    )
    output = tmp_path / "result"
    run_daily(
        ExecutionDataset(execution, DailyDataset(daily)),
        strategy=daily_strategy,
        policy=daily_policy,
        output=output,
    )
    return output, record, daily_policy


def rehash(output, name):
    manifest_path = output / "manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["sha256"][name] = hashlib.sha256((output / name).read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))


def mutate_report(output, change):
    path = output / "report.json"
    report = json.loads(path.read_text())
    change(report)
    path.write_text(json.dumps(report))
    rehash(output, "report.json")


def test_reopened_exact_financial_evidence_and_readonly_verification(evidence):
    output, record, policy = evidence
    before = {path.name: path.read_bytes() for path in output.iterdir()}
    result = verify_report(output, record, JOB)
    snapshot = result["final_snapshot"]
    # Independent sums from persisted fills, rather than the producer's episode helper.
    with closing(sqlite3.connect(output / "paper.sqlite3")) as db:
        fills = db.execute(
            "SELECT o.side,f.quantity,f.price,f.fees FROM fills f JOIN orders o ON o.id=f.order_id"
        ).fetchall()
        assert fills and {row[0] for row in fills} == {"BUY", "SELL"}
        cash = policy.starting_cash
        fees = D(0)
        for side, quantity, price, fee in fills:
            fees += D(fee)
            cash += (1 if side == "SELL" else -1) * quantity * D(price) - D(fee)
        assert db.execute("SELECT COUNT(*) FROM positions").fetchone()[0] == 0
        assert cash == D(snapshot["cash"]) == D(snapshot["equity"])
        assert fees == D(snapshot["fees"])
        assert D(snapshot["realized_pnl"]) == cash - policy.starting_cash
    assert result["synthetic"] is True
    assert result["performance"]["state"] == "unavailable"
    assert result["summary"]["completed_trades"] == 9
    assert sum(D(row["net_pnl"]) for row in result["trades"]) == cash - policy.starting_cash
    assert before == {path.name: path.read_bytes() for path in output.iterdir()}


@pytest.mark.parametrize("field", ["cash", "fees", "realized_pnl", "equity"])
def test_rehashed_financial_summary_tampering_is_rejected(evidence, field):
    output, record, _ = evidence
    mutate_report(output, lambda report: report["final_snapshot"].__setitem__(field, "1.00"))
    with pytest.raises(ValueError, match="ledger"):
        verify_report(output, record, JOB)


@pytest.mark.parametrize(
    "field,value",
    [
        ("net_observed_pnl", "999999"),
        ("initial_cash", "1.00"),
        ("income_received", "100"),
        ("completed_trades", 100),
        ("unpaid_claims", 10),
        ("observed_drawdown", "1.00"),
        ("stale_valuation_observations", 100),
    ],
)
def test_rehashed_metric_tampering_is_rejected(evidence, field, value):
    output, record, _ = evidence
    mutate_report(output, lambda report: report["metrics"].__setitem__(field, value))
    with pytest.raises(ValueError, match="metrics|drawdown"):
        verify_report(output, record, JOB)


def test_rehashed_trade_profit_tampering_is_rejected(evidence):
    output, record, _ = evidence
    mutate_report(output, lambda report: report["trades"][0].__setitem__("net_pnl", "1000000"))
    with pytest.raises(ValueError, match="trade episodes"):
        verify_report(output, record, JOB)


@pytest.mark.parametrize("field", ["code_sha256", "charges_version"])
def test_rehashed_runtime_identity_changes_are_rejected(evidence, field):
    output, record, _ = evidence
    mutate_report(output, lambda report: report.__setitem__(field, "different-runtime"))
    with pytest.raises(ValueError, match="immutable request"):
        verify_report(output, record, JOB)


def test_rehashed_corrupt_persisted_cash_is_rejected(evidence):
    output, record, _ = evidence
    with closing(sqlite3.connect(output / "paper.sqlite3")) as db:
        db.execute("UPDATE meta SET value='1000000' WHERE key='cash'")
        db.commit()
    rehash(output, "paper.sqlite3")
    with pytest.raises(ValueError, match="reconciliation"):
        verify_report(output, record, JOB)


@pytest.mark.parametrize("artifact", ["report.json", "paper.sqlite3", "equity.csv"])
def test_unrehashed_artifact_changes_are_rejected(evidence, artifact):
    output, record, _ = evidence
    with (output / artifact).open("ab") as file:
        file.write(b" ")
    with pytest.raises(ValueError, match="integrity"):
        verify_report(output, record, JOB)


@pytest.mark.parametrize("kind", ["directory", "artifact", "ancestor", "extra"])
def test_output_symlinks_and_unlisted_artifacts_are_rejected(evidence, tmp_path, kind):
    output, record, _ = evidence
    if kind == "directory":
        link = tmp_path / "linked-output"
        link.symlink_to(output, target_is_directory=True)
        output = link
    elif kind == "ancestor":
        link = tmp_path / "linked-parent"
        link.symlink_to(tmp_path, target_is_directory=True)
        output = link / "result"
    elif kind == "artifact":
        original = output / "report.json"
        original.rename(tmp_path / "actual-report.json")
        original.symlink_to(tmp_path / "actual-report.json")
    else:
        (output / "unexpected.txt").write_text("unlisted")
    with pytest.raises(ValueError, match="regular"):
        verify_report(output, record, JOB)


@pytest.mark.parametrize("kind", ["report_duplicate", "manifest_duplicate", "nonfinite"])
def test_ambiguous_json_is_rejected_even_with_rehashed_artifact(evidence, kind):
    output, record, _ = evidence
    name = "manifest.json" if kind == "manifest_duplicate" else "report.json"
    path = output / name
    text = path.read_text()
    if kind == "nonfinite":
        path.write_text(text[:-1] + ',"bad":NaN}')
    else:
        key = "state" if name == "manifest.json" else "mode"
        value = '"finished"' if name == "manifest.json" else '"paper"'
        path.write_text(text[:-1].rstrip().removesuffix("}") + f',"{key}":{value}}}')
    if name != "manifest.json":
        rehash(output, name)
    with pytest.raises(ValueError):
        verify_report(output, record, JOB)


def test_stale_curve_does_not_create_drawdown_or_high_water_mark(evidence):
    output, record, policy = evidence
    path = output / "equity.csv"
    reader = csv.DictReader(io.StringIO(path.read_text()))
    fields = reader.fieldnames
    rows = list(reader)
    report = json.loads((output / "report.json").read_text())
    # A stale mark can be displayed as an observation but cannot establish a performance peak.
    rows[1]["equity"] = "999999"
    rows[1]["valuation_fresh"] = "False"
    peak, drawdown, stale = policy.starting_cash, D(0), 0
    for row in rows:
        if row["valuation_fresh"] == "True":
            peak = max(peak, D(row["equity"]))
            drawdown = max(drawdown, peak - D(row["equity"]))
        else:
            stale += 1
    content = io.StringIO(newline="")
    writer = csv.DictWriter(content, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    path.write_text(content.getvalue())
    rehash(output, "equity.csv")
    report["metrics"].update(observed_drawdown=str(drawdown), stale_valuation_observations=stale)
    (output / "report.json").write_text(json.dumps(report))
    rehash(output, "report.json")
    result = verify_report(output, record, JOB)
    assert result["equity_curve"][1]["equity"] == "999999"
    assert result["drawdown_curve"][1]["drawdown"] is None
    assert result["drawdown_curve"][1]["drawdown_pct"] is None
    assert D(result["drawdown_curve"][-1]["drawdown"]) < 999999 - D(rows[-1]["equity"])
    assert "Stale observations" in result["limitations"][-1]


def test_open_holdings_are_valued_from_persisted_quotes_without_fabricated_close(
    execution_inputs,
    daily_strategy,
    daily_policy,
    tmp_path,
):
    daily, execution, _ = execution_inputs
    source = execution / "events.jsonl"
    source.write_text("\n".join(source.read_text().splitlines()[:10]) + "\n")
    public = register_bundle(
        tmp_path / "registry",
        daily,
        execution,
        Path("config/daily-strategy.toml"),
        Path("config/long-term.toml"),
        "Invented open exposure",
    )
    record = json.loads(
        (tmp_path / "registry/resources" / public["resource_id"] / "resource.json").read_text()
    )
    output = tmp_path / "held-result"
    run_daily(
        ExecutionDataset(execution, DailyDataset(daily)),
        strategy=daily_strategy,
        policy=daily_policy,
        output=output,
    )
    result = verify_report(output, record, JOB)
    assert result["status"] == "incomplete" and result["trades"] == []
    snapshot = result["final_snapshot"]
    assert len(snapshot["positions"]) == 3
    with closing(sqlite3.connect(output / "paper.sqlite3")) as db:
        paid = sum(
            D(price) * quantity + D(fee)
            for price, quantity, fee in db.execute("SELECT price,quantity,fees FROM fills")
        )
        assert D(snapshot["cash"]) == daily_policy.starting_cash - paid
        assert sum(D(cost) for (cost,) in db.execute("SELECT cost FROM positions")) == paid
        for position in snapshot["positions"]:
            payload = json.loads(
                db.execute(
                    "SELECT payload FROM quotes WHERE symbol=?", (position["symbol"],)
                ).fetchone()[0]
            )
            quantity = position["quantity"]
            tick = D(
                db.execute(
                    "SELECT tick FROM instruments WHERE symbol=?", (position["symbol"],)
                ).fetchone()[0]
            )
            # Hand-calculate the conservative bid, levies and DP estimate from persisted data.
            mark = (
                D(payload["bid"]) * (1 - daily_policy.slippage_bps / 10000) / tick
            ).to_integral_value(rounding="ROUND_FLOOR") * tick
            turnover = mark * quantity
            taxable = turnover * (D("0.0000307") + D("0.000001") + D("0.000000001"))
            fee = ((taxable * D("1.18") + turnover * D("0.001")) * 100).to_integral_value(
                rounding="ROUND_CEILING"
            ) / 100 + D("15.34")
            assert D(position["liquidation_value"]) == turnover - fee
    assert D(snapshot["equity"]) == D(snapshot["cash"]) + sum(
        D(p["liquidation_value"]) for p in snapshot["positions"]
    )
    mutate_report(
        output,
        lambda report: report["final_snapshot"]["positions"][0].__setitem__(
            "liquidation_value", "1000000"
        ),
    )
    with pytest.raises(ValueError, match="holding valuation"):
        verify_report(output, record, JOB)


@pytest.mark.parametrize("fault", ["status", "gate", "unknown_metric", "bad_money", "extra_lock"])
def test_other_rehashed_inconsistent_evidence_fails_closed(evidence, fault):
    output, record, _ = evidence

    def change(report):
        if fault == "status":
            report["status"] = "incomplete"
        elif fault == "gate":
            report["gates"]["flat_no_pending_orders"] = False
            report["status"] = "incomplete"
        elif fault == "unknown_metric":
            report["metrics"]["unverified_profit"] = "100000"
        elif fault == "bad_money":
            report["final_snapshot"]["cash"] = "not-money"

    if fault == "extra_lock":
        (output / "paper.sqlite3.lock").write_text("untrusted lock payload")
    else:
        mutate_report(output, change)
    with pytest.raises(ValueError):
        verify_report(output, record, JOB)
