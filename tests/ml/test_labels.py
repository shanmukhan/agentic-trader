import json
from datetime import datetime, timedelta
from decimal import Decimal as D

import pytest
from conftest import changed_dataset

from trading_agent.backtesting.dataset import CandleEvent, ConnectionEvent, QuoteEvent
from trading_agent.ml.labeling import build_samples
from trading_agent.ml.samples import Samples
from trading_agent.ml.schema import LabelPolicy
from trading_agent.settings import Settings
from trading_agent.strategy.rules import StrategySettings


def build(dataset, output, **changes):
    return build_samples(
        dataset, strategy=StrategySettings(), policy=Settings(**changes), output=output
    )


def test_labels_use_actual_costs_exits_and_strictly_later_quotes(research_dataset, tmp_path):
    original = research_dataset.events_path.read_bytes()
    report = build(research_dataset, tmp_path / "labels")
    rows = Samples(tmp_path / "labels").read()
    assert report["counts"] == {"candidates": 2, "labeled": 2, "target_1": 1, "target_0": 1}
    assert [row.exit_reason for row in rows] == ["TARGET", "STOP"]
    assert sum(row.net_pnl for row in rows) == D("-25.97")
    audit = [
        json.loads(line)
        for line in (tmp_path / "labels/label_audit.jsonl").read_text().splitlines()
    ]
    for row, evidence in zip(rows, audit, strict=True):
        assert all(
            datetime.fromisoformat(fill["time"]) > row.features.time for fill in evidence["fills"]
        )
        assert evidence["fills"][0]["time"] != row.features.time.isoformat()
        assert row.label_end == row.features.time + timedelta(seconds=3)
        assert not evidence["snapshot"]["positions"] and D(evidence["snapshot"]["fees"]) > 0
    assert not list((tmp_path / "labels").glob("label-*"))
    assert research_dataset.events_path.read_bytes() == original


@pytest.mark.parametrize(
    "mode,reason",
    [
        ("disconnect", "INTERRUPTED"),
        ("gap", "QUOTE_GAP"),
        ("truncated", "DATASET_END"),
        ("unfilled", "UNRESOLVED_OR_UNFILLED"),
        ("bad_quote", "QUOTE_QUALITY"),
        ("quality", "CANDLE_QUALITY"),
    ],
)
def test_unresolved_interrupted_or_bad_data_are_censored_not_losses(
    research_dataset, tmp_path, mode, reason
):
    signal = [event for event in research_dataset.events() if isinstance(event, CandleEvent)][13]
    end = signal.time

    def edit(events):
        prefix = [event for event in events if event.time <= end + timedelta(seconds=1)]
        later = next(
            event
            for event in events
            if isinstance(event, QuoteEvent) and event.time == end + timedelta(seconds=2)
        )
        if mode == "disconnect":
            return prefix + [ConnectionEvent(time=end + timedelta(seconds=2), connected=False)]
        if mode == "gap":
            later = QuoteEvent(
                time=end + timedelta(seconds=7),
                quote=later.quote.model_copy(
                    update={
                        "exchange_time": end + timedelta(seconds=7),
                        "received_time": end + timedelta(seconds=7),
                    }
                ),
            )
            return prefix + [later]
        if mode == "unfilled":
            return [event for event in events if event.time <= end] + [later]
        if mode == "bad_quote":
            return prefix + [
                QuoteEvent(
                    time=end + timedelta(seconds=2),
                    quote=later.quote.model_copy(update={"volume": 1}),
                )
            ]
        if mode == "quality":
            return prefix + [
                CandleEvent(
                    time=end + timedelta(minutes=5),
                    candle=signal.candle.model_copy(update={"start": end, "quality": "gap"}),
                )
            ]
        return prefix

    data = changed_dataset(research_dataset, tmp_path / "changed", edit)
    result = build(data, tmp_path / "labels")
    assert result["counts"][f"censored:{reason}"] == 1
    assert not Samples(tmp_path / "labels").read()
    evidence = json.loads((tmp_path / "labels/label_audit.jsonl").read_text())
    assert evidence["censor_reason"] == reason


def test_horizon_requests_exit_before_observing_later_price_and_does_not_fabricate_fill(
    research_dataset, tmp_path
):
    signal = [event for event in research_dataset.events() if isinstance(event, CandleEvent)][13]
    end = signal.time

    def edit(events):
        prefix = [event for event in events if event.time <= end + timedelta(seconds=1)]
        quote = prefix[-1].quote
        for second in range(2, 62):
            now = end + timedelta(seconds=second)
            prefix.append(
                QuoteEvent(
                    time=now,
                    quote=quote.model_copy(
                        update={
                            "exchange_time": now,
                            "received_time": now,
                            "volume": quote.volume + 100 * second,
                        }
                    ),
                )
            )
        return prefix

    data = changed_dataset(research_dataset, tmp_path / "horizon", edit)
    build_samples(
        data,
        strategy=StrategySettings(),
        policy=Settings(),
        output=tmp_path / "labels",
        labels=LabelPolicy(horizon_minutes=1),
    )
    row = Samples(tmp_path / "labels").read()[0]
    assert row.target == 0 and row.exit_reason == "LABEL_TIME_LIMIT"
    assert row.label_end == end + timedelta(seconds=61) and row.net_pnl < 0


def test_partial_fill_labels_use_completed_quantity_and_actual_fees(research_dataset, tmp_path):
    def edit(events):
        return [
            QuoteEvent(time=event.time, quote=event.quote.model_copy(update={"ask_size": 1}))
            if isinstance(event, QuoteEvent)
            else event
            for event in events
        ]

    data = changed_dataset(research_dataset, tmp_path / "partial", edit)
    build(data, tmp_path / "labels")
    rows = Samples(tmp_path / "labels").read()
    evidence = [
        json.loads(line)
        for line in (tmp_path / "labels/label_audit.jsonl").read_text().splitlines()
    ]
    assert len(rows) == 2
    assert all(record["fills"][0]["quantity"] == 1 for record in evidence)
    assert sum(row.net_pnl for row in rows) != D("-25.97")


def test_risk_rejections_are_exclusions_and_bundle_corruption_is_rejected(
    research_dataset, tmp_path
):
    result = build(research_dataset, tmp_path / "labels", max_trade_risk=D(".10"))
    assert result["counts"]["censored:RISK_REJECTED"] == 2
    assert not Samples(tmp_path / "labels").read()
    with (tmp_path / "labels/samples.jsonl").open("a") as file:
        file.write("{}\n")
    with pytest.raises(ValueError, match="hashes"):
        Samples(tmp_path / "labels")


def test_failed_export_never_leaves_completion_manifest(research_dataset, tmp_path):
    with pytest.raises(ValueError, match="outside"):
        build(research_dataset, research_dataset.directory / "labels")
    with research_dataset.events_path.open("a") as file:
        file.write('{"type":"invalid"}\n')
    with pytest.raises(ValueError):
        build(research_dataset, tmp_path / "failed")
    assert not (tmp_path / "failed/manifest.json").exists()
