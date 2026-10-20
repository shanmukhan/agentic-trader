import hashlib
import json
import shutil

import pytest

from trading_agent.ml.samples import Samples


def copied(ml_demo, tmp_path):
    directory = tmp_path / "samples"
    shutil.copytree(ml_demo[0] / "samples", directory)
    return directory


def update(directory, edit):
    rows = [json.loads(line) for line in (directory / "samples.jsonl").read_text().splitlines()]
    changed = edit(rows)
    (directory / "samples.jsonl").write_text("".join(json.dumps(row) + "\n" for row in changed))
    manifest = json.loads((directory / "manifest.json").read_text())
    manifest["samples_sha256"] = hashlib.sha256(
        (directory / "samples.jsonl").read_bytes()
    ).hexdigest()
    (directory / "manifest.json").write_text(json.dumps(manifest))


@pytest.mark.parametrize(
    "kind", ["duplicate", "undeclared_symbol", "undeclared_session", "missing_row"]
)
def test_samples_refuse_duplicate_outside_context_and_wrong_count(ml_demo, tmp_path, kind):
    directory = copied(ml_demo, tmp_path)

    def edit(rows):
        if kind == "duplicate":
            rows[1] = rows[0]
        elif kind == "undeclared_symbol":
            rows[0]["features"]["symbol"] = "NSE:UNKNOWN"
        elif kind == "undeclared_session":
            rows[0]["features"]["time"] = "2027-01-01T04:55:00Z"
        else:
            rows.pop()
        return rows

    update(directory, edit)
    with pytest.raises(ValueError):
        Samples(directory).read()


@pytest.mark.parametrize("kind", ["counts", "policy", "strategy", "synthetic", "sessions"])
def test_manifest_rejects_inconsistent_provenance_and_statistics(ml_demo, tmp_path, kind):
    directory = copied(ml_demo, tmp_path)
    manifest = json.loads((directory / "manifest.json").read_text())
    if kind == "counts":
        manifest["counts"]["candidates"] += 1
    elif kind == "policy":
        manifest["risk_policy"]["latency_ms"] += 1
    elif kind == "strategy":
        manifest["strategy_settings"]["min_bar_volume"] += 1
    elif kind == "synthetic":
        manifest["synthetic"] = False
    else:
        manifest["sessions"].reverse()
    (directory / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError):
        Samples(directory)


def test_sample_paths_and_manifest_size_are_bounded(ml_demo, tmp_path):
    directory = copied(ml_demo, tmp_path)
    (directory / "samples.jsonl").unlink()
    (directory / "samples.jsonl").symlink_to(ml_demo[0] / "samples/samples.jsonl")
    with pytest.raises(ValueError, match="local"):
        Samples(directory)
    (directory / "samples.jsonl").unlink()
    (directory / "manifest.json").write_bytes(b" " * 1_000_001)
    with pytest.raises(ValueError, match="oversized"):
        Samples(directory)
