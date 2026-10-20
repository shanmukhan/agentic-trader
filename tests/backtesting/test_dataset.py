import json
from datetime import timedelta

import pytest
from pydantic import ValidationError

from trading_agent.backtesting.dataset import CandleEvent, Dataset, Manifest, QuoteEvent


@pytest.mark.parametrize(
    "mutation",
    [
        {"type": "candidate"},
        {"time": "2026-10-20T09:20:00"},
        {"connected": "true", "type": "connection"},
        {"extra": "ignored?"},
    ],
)
def test_invalid_events_are_rejected(research_dataset, mutation):
    event = next(research_dataset.events()).model_dump(mode="json")
    event.update(mutation)
    research_dataset.events_path.write_text(json.dumps(event) + "\n")
    with pytest.raises(ValueError, match="schema"):
        list(research_dataset.events())


def test_event_order_and_input_hash_integrity(research_dataset):
    events = list(research_dataset.events())
    with research_dataset.events_path.open("w") as file:
        for event in (events[1], events[0]):
            file.write(event.model_dump_json() + "\n")
    with pytest.raises(ValueError, match="backward"):
        list(research_dataset.events())
    with pytest.raises(ValueError, match="changed"):
        research_dataset.assert_unchanged()


def test_future_candles_and_quote_receipts_not_usable_early(research_dataset):
    events = list(research_dataset.events())
    quote = next(e for e in events if isinstance(e, QuoteEvent))
    candle = next(e for e in events if isinstance(e, CandleEvent))
    with pytest.raises(ValidationError):
        QuoteEvent(time=quote.time - timedelta(seconds=1), quote=quote.quote)
    with pytest.raises(ValidationError):
        CandleEvent(time=candle.time - timedelta(seconds=1), candle=candle.candle)


@pytest.mark.parametrize(
    "field,value",
    [
        ("price_basis", "split_adjusted"),
        ("events_file", "../private.jsonl"),
        ("instruments", []),
        ("sessions", []),
    ],
)
def test_manifest_basis_paths_and_universe_are_explicit(research_dataset, field, value):
    values = research_dataset.manifest.model_dump(mode="json")
    values[field] = value
    with pytest.raises(ValidationError):
        Manifest.model_validate(values)


def test_oversized_and_blank_event_lines_fail_before_json_parsing(research_dataset):
    for content in (b"x" * 65537, b"\n"):
        research_dataset.events_path.write_bytes(content)
        with pytest.raises(ValueError, match="line"):
            list(research_dataset.events())


def test_symlinked_files_and_oversized_manifest_rejected(research_dataset, tmp_path):
    original = research_dataset.manifest_path.read_bytes()
    target = tmp_path / "other-manifest.json"
    target.write_bytes(original)
    research_dataset.manifest_path.unlink()
    research_dataset.manifest_path.symlink_to(target)
    with pytest.raises(ValueError, match="local"):
        Dataset(research_dataset.directory)
    research_dataset.manifest_path.unlink()
    research_dataset.manifest_path.write_bytes(b" " * 1_000_001)
    with pytest.raises(ValueError, match="oversized"):
        Dataset(research_dataset.directory)
