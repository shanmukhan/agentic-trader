from datetime import timedelta

import pytest

from trading_agent.backtesting.dataset import CandleEvent, ConnectionEvent, Dataset
from trading_agent.backtesting.export import export_dataset
from trading_agent.paper.demo import OPEN, SIGNAL, WARM, prepare_signal


def export(feed, output, **options):
    return export_dataset(
        feed.engine.db,
        feed.engine.calendar,
        start=OPEN,
        end=SIGNAL + timedelta(seconds=3),
        symbols=("NSE:DEMO",),
        output=output,
        source="invented supervised capture",
        **options,
    )


def test_supervised_exports_preserve_backfill_receipts_and_real_connection_events(
    paper_factory, tmp_path
):
    feed = paper_factory()
    prepare_signal(feed)
    feed.connection(False, SIGNAL + timedelta(seconds=1))
    orders = feed.engine.orders()
    export(feed, tmp_path / "export")
    data = Dataset(tmp_path / "export")
    candles = [event for event in data.events() if isinstance(event, CandleEvent)]
    assert len(candles) == 15
    assert all(event.time == WARM for event in candles[:14])
    assert candles[0].candle.start == OPEN and candles[-1].time == SIGNAL
    connections = [event for event in data.events() if isinstance(event, ConnectionEvent)]
    assert [(event.time, event.connected) for event in connections] == [
        (OPEN, False),
        (WARM, True),
        (SIGNAL + timedelta(seconds=1), False),
    ]
    assert data.manifest.synthetic and "first observed" in data.manifest.data_notes
    assert feed.engine.orders() == orders


@pytest.mark.parametrize("mode", ["missing_observation", "override"])
def test_supervised_export_refuses_missing_observation_or_external_clock_override(
    paper_factory, tmp_path, mode
):
    feed = paper_factory()
    prepare_signal(feed)
    options = {}
    if mode == "missing_observation":
        with feed.engine.db.transaction() as tx:
            tx.execute("DELETE FROM events WHERE kind='feed_evaluation'")
    else:
        options["candle_file"] = tmp_path / "unclocked.jsonl"
    with pytest.raises(ValueError):
        export(feed, tmp_path / "incomplete", **options)
    assert not (tmp_path / "incomplete/manifest.json").exists()
