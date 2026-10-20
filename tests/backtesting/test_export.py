from datetime import timedelta
from decimal import Decimal as D

import pytest
from conftest import NOW, candidate, quote

from trading_agent.backtesting.dataset import CandleEvent, Dataset
from trading_agent.backtesting.export import export_dataset
from trading_agent.market_data.repository import store_candles
from trading_agent.models import Candle


def test_export_preserves_source_account_and_labels_replay_data(engine, research_dataset, tmp_path):
    candles = [e.candle for e in research_dataset.events() if isinstance(e, CandleEvent)]
    store_candles(engine.db, candles, NOW + timedelta(days=2))
    engine.submit(candidate(), NOW)
    before = engine.orders()
    with engine.db.transaction() as tx:
        count = tx.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    output = tmp_path / "export"
    result = export_dataset(
        engine.db,
        engine.calendar,
        start=NOW - timedelta(hours=1),
        end=NOW + timedelta(days=2),
        symbols=("NSE:DEMO",),
        output=output,
        source="test export",
    )
    assert result == {"quote": 1, "candle": 28}
    assert engine.orders() == before and before[0]["state"] == "ACCEPTED"
    with engine.db.transaction() as tx:
        assert count == tx.execute("SELECT COUNT(*) FROM events").fetchone()[0]
    exported = Dataset(output)
    assert exported.manifest.synthetic
    times = [e.time for e in exported.events()]
    assert times == sorted(times)


def test_candle_override_and_kite_provenance(engine, tmp_path):
    now = NOW + timedelta(seconds=1)
    engine.ingest(quote(1).model_copy(update={"source": "kite"}), now)
    candle = Candle(
        symbol="NSE:DEMO",
        start=NOW + timedelta(minutes=5),
        minutes=5,
        open=D(500),
        high=D(501),
        low=D(499),
        close=D(500),
        volume=1000,
    )
    override = tmp_path / "verified.jsonl"
    override.write_text(candle.model_dump_json() + "\n")
    output = tmp_path / "export"
    export_dataset(
        engine.db,
        engine.calendar,
        start=now,
        end=NOW + timedelta(hours=1),
        symbols=("NSE:DEMO",),
        output=output,
        source="declared source",
        candle_file=override,
    )
    exported = Dataset(output)
    assert not exported.manifest.synthetic  # provenance label only, not proof of authenticity
    assert any(isinstance(e, CandleEvent) for e in exported.events())


def test_failed_export_has_no_loadable_manifest(engine, tmp_path):
    output = tmp_path / "incomplete"
    with pytest.raises(ValueError, match="both"):
        export_dataset(
            engine.db,
            engine.calendar,
            start=NOW,
            end=NOW + timedelta(hours=1),
            symbols=("NSE:DEMO",),
            output=output,
            source="missing candles",
        )
    assert not (output / "manifest.json").exists()
    with pytest.raises(FileNotFoundError):
        Dataset(output)


@pytest.mark.parametrize("symbols", [(), ("NSE:MISSING",), ("NSE:DEMO", "NSE:DEMO")])
def test_export_rejects_invalid_universe(engine, tmp_path, symbols):
    with pytest.raises(ValueError):
        export_dataset(
            engine.db,
            engine.calendar,
            start=NOW,
            end=NOW + timedelta(hours=1),
            symbols=symbols,
            output=tmp_path / "export",
            source="test",
        )
