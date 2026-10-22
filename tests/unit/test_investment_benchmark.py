"""Invented local benchmark declarations; no provider or real-market acceptance."""

import copy
import hashlib
import json
from datetime import UTC, datetime
from decimal import Decimal, localcontext
from fractions import Fraction

import pytest

from trading_agent.investment_research import benchmark as module
from trading_agent.investment_research.benchmark import compare_benchmark, load_benchmark

AS_OF = datetime(2026, 10, 22, 6, tzinfo=UTC)
SESSIONS = ["2026-10-19", "2026-10-20", "2026-10-21"]


def declaration():
    return {
        "schema_version": 1,
        "series_id": "invented-gross-index",
        "title": "Invented comparison fixture",
        "provider": "Local test fixture",
        "source_url": "https://example.invalid/declared-index-method",
        "license_reference": "Invented fixture; not licensed market data",
        "currency": "INR",
        "return_type": "gross_total_return",
        "synthetic": True,
        "published_at": "2026-10-01T10:00:00+00:00",
        "available_at": "2026-10-01T10:01:00+00:00",
        "rows": [
            {
                "session": day,
                "level": level,
                "close_at": day + "T10:00:00+00:00",
                "available_at": day + "T10:01:00+00:00",
            }
            for day, level in zip(SESSIONS, ["1000", "1100", "1250"], strict=True)
        ],
    }


def stocks():
    return [
        {
            "session": day,
            "total_return_index": level,
            "available_at": day + "T10:02:00+00:00",
            "segment_break": False,
        }
        for day, level in zip(SESSIONS, ["100", "120", "150"], strict=True)
    ]


def write(path, data=None):
    path.write_text(json.dumps(declaration() if data is None else data), encoding="utf-8")
    return path


def test_local_snapshot_has_exact_identity_public_provenance_and_no_paths(tmp_path):
    path = write(tmp_path / "benchmark.json")
    before = path.read_bytes()
    loaded = load_benchmark(path, AS_OF)
    assert loaded["state"] == "available"
    assert loaded["input_identity"] == {
        "sha256": hashlib.sha256(before).hexdigest(),
        "size_bytes": len(before),
    }
    assert loaded["rows"][0]["level"] == "1000"
    assert loaded["series"]["provenance_state"] == "declared_unverified"
    assert loaded["series"]["synthetic"] is True
    assert str(tmp_path) not in json.dumps(loaded)
    assert any("not verified" in text for text in loaded["limitations"])
    assert path.read_bytes() == before


def test_relative_wealth_is_not_percentage_point_excess_and_never_mutates_inputs(tmp_path):
    benchmark = load_benchmark(write(tmp_path / "benchmark.json"), AS_OF)
    stock = stocks()
    before = copy.deepcopy((stock, benchmark))
    result = compare_benchmark(stock, benchmark, lookback=2)
    assert result["state"] == "available"
    assert result["stock_growth"] == "1.5" and result["benchmark_growth"] == "1.25"
    assert result["stock_return_pct"] == "50.000000000000"
    assert result["benchmark_return_pct"] == "25.000000000000"
    assert result["relative_strength_pct"] == "20.000000000000"
    assert result["matched_sessions"] == SESSIONS
    assert result["available_at"] == "2026-10-21T10:02:00.000000+00:00"
    assert result["decimal_precision"] == 34 and result["percent_decimal_places"] == 12
    assert result["interval"] == "1d"
    assert (stock, benchmark) == before


def test_nonterminating_ratio_matches_independent_fraction_calculation(tmp_path):
    data = declaration()
    data["rows"] = data["rows"][:2]
    data["rows"][0]["level"], data["rows"][1]["level"] = "100", "103"
    stock = stocks()[:2]
    stock[1]["total_return_index"] = "101"
    result = compare_benchmark(stock, load_benchmark(write(tmp_path / "b.json", data), AS_OF), 1)
    # Independently cancel the shared 100 base before dividing; do not mirror the adapter.
    fraction = (Fraction(101, 103) - 1) * 100
    with localcontext() as context:
        context.prec = 60
        expected = (Decimal(fraction.numerator) / Decimal(fraction.denominator)).quantize(
            Decimal("0.000000000001")
        )
    assert result["relative_strength_pct"] == str(expected) == "-1.941747572816"


@pytest.mark.parametrize(
    "ending",
    [
        "100.3333333333333333333333333333333",
        "1.003333333333333333333333333333333E+2",
    ],
)
def test_stock_tri_retains_engine_34_digit_analytical_precision(tmp_path, ending):
    data = declaration()
    data["rows"] = data["rows"][:2]
    data["rows"][0]["level"] = data["rows"][1]["level"] = "100"
    stock = stocks()[:2]
    stock[1]["total_return_index"] = ending
    result = compare_benchmark(stock, load_benchmark(write(tmp_path / "b.json", data), AS_OF), 1)
    assert result["state"] == "available"
    assert result["relative_strength_pct"] == "0.333333333333"
    assert result["stock_growth"] == "1.003333333333333333333333333333333"


@pytest.mark.parametrize(
    "ending",
    [
        "100.33333333333333333333333333333333",
        "1E+129",
        "1E-129",
        "NaN",
        "0",
        "+100",
    ],
)
def test_stock_tri_rejects_unbounded_or_invalid_analytical_precision(tmp_path, ending):
    loaded = load_benchmark(write(tmp_path / "b.json"), AS_OF)
    stock = stocks()
    stock[1]["total_return_index"] = ending
    assert compare_benchmark(stock, loaded, 2)["reason_code"] == "invalid_input"


def test_future_row_perturbations_change_identity_but_not_past_numerical_result(tmp_path):
    path = tmp_path / "benchmark.json"
    data = declaration()
    cutoff = datetime(2026, 10, 20, 11, tzinfo=UTC)
    first = load_benchmark(write(path, data), cutoff)
    changed = copy.deepcopy(data)
    changed["rows"][-1]["level"] = "987654321.123456789012"
    changed["rows"][-1]["available_at"] = "2026-10-22T10:05:00+00:00"
    second = load_benchmark(write(path, changed), cutoff)
    assert len(first["rows"]) == len(second["rows"]) == 2
    assert first["input_identity"] != second["input_identity"]
    stock = stocks()
    earlier = compare_benchmark(stock, first, 1)
    stock[-1]["total_return_index"] = "999999999999"
    later = compare_benchmark(stock, second, 1)
    for field in ("relative_strength_pct", "stock_growth", "benchmark_growth", "matched_sessions"):
        assert earlier[field] == later[field]
    assert earlier["state"] == later["state"] == "available"


def test_manifest_availability_gates_all_historical_rows(tmp_path):
    data = declaration()
    data["published_at"] = "2026-10-22T10:00:00+00:00"
    data["available_at"] = "2026-10-22T10:01:00+00:00"
    loaded = load_benchmark(write(tmp_path / "b.json", data), AS_OF)
    assert loaded["state"] == "unavailable" and loaded["rows"] == []
    assert compare_benchmark(stocks(), loaded, 1)["reason_code"] == "benchmark_unavailable"


@pytest.mark.parametrize(
    "field,value",
    [
        ("return_type", "price"),
        ("return_type", "net_total_return"),
    ],
)
def test_declared_nonmatching_return_basis_loads_but_comparison_is_unavailable(
    tmp_path, field, value
):
    data = declaration()
    data[field] = value
    loaded = load_benchmark(write(tmp_path / "b.json", data), AS_OF)
    result = compare_benchmark(stocks(), loaded, 2)
    assert loaded["state"] == "available" and result["reason_code"] == "incompatible_basis"
    assert result["relative_strength_pct"] is None


@pytest.mark.parametrize("change", ["missing_benchmark", "missing_stock", "late_benchmark"])
def test_no_skipping_forward_filling_or_backshifting_missing_sessions(tmp_path, change):
    data, stock, lookback = declaration(), stocks(), 2
    if change == "missing_benchmark":
        del data["rows"][1]
    elif change == "missing_stock":
        del stock[1]
        lookback = 1
    else:
        data["rows"][-1]["available_at"] = "2026-10-22T10:05:00+00:00"
    result = compare_benchmark(
        stock, load_benchmark(write(tmp_path / "b.json", data), AS_OF), lookback
    )
    assert result["reason_code"] == "session_gap"
    assert result["relative_strength_pct"] is None and not result["matched_sessions"]


def test_segment_break_prevents_crossing_but_window_start_can_seed_new_segment(tmp_path):
    benchmark = load_benchmark(write(tmp_path / "b.json"), AS_OF)
    stock = stocks()
    stock[0]["segment_break"] = True
    assert compare_benchmark(stock, benchmark, 2)["state"] == "available"
    stock[1]["segment_break"] = True
    assert compare_benchmark(stock, benchmark, 2)["reason_code"] == "segment_break"
    assert compare_benchmark(stock, benchmark, 1)["state"] == "available"


@pytest.mark.parametrize("lookback", [0, -1, True, 2521, "2", None])
def test_invalid_lookback_returns_explicit_unavailable(tmp_path, lookback):
    loaded = load_benchmark(write(tmp_path / "b.json"), AS_OF)
    assert compare_benchmark(stocks(), loaded, lookback)["reason_code"] == "invalid_lookback"


def test_short_history_and_stock_currency_mismatch_are_not_zero_returns(tmp_path):
    loaded = load_benchmark(write(tmp_path / "b.json"), AS_OF)
    assert compare_benchmark(stocks(), loaded, 20)["reason_code"] == "insufficient_history"
    stock = stocks()
    stock[-1]["currency"] = "USD"
    result = compare_benchmark(stock, loaded, 2)
    assert result["reason_code"] == "incompatible_basis" and result["stock_growth"] is None


@pytest.mark.parametrize(
    "level",
    [
        "0",
        "-1",
        "NaN",
        "Infinity",
        "1e3",
        "01",
        "1.0000000000001",
        "12345678901234567890123456789",
        1000,
        True,
    ],
)
def test_levels_reject_nonplain_nonfinite_nonpositive_and_excess_precision(tmp_path, level):
    data = declaration()
    data["rows"][0]["level"] = level
    with pytest.raises(ValueError, match="level"):
        load_benchmark(write(tmp_path / "b.json", data), AS_OF)


@pytest.mark.parametrize(
    "mutation",
    [
        "duplicate_session",
        "unsorted",
        "naive_clock",
        "availability_before_close",
        "close_on_other_day",
        "extra_path",
        "extra_row_path",
        "numeric_bool_schema",
        "string_synthetic",
        "publication_after_availability",
        "unsupported_currency",
        "unrecognized_basis",
        "empty_license",
        "bad_url",
        "credential_url",
        "ip_url",
    ],
)
def test_invalid_manifest_and_session_declarations_are_rejected(tmp_path, mutation):
    data = declaration()
    if mutation == "duplicate_session":
        data["rows"][1] = copy.deepcopy(data["rows"][0])
    elif mutation == "unsorted":
        data["rows"].reverse()
    elif mutation == "naive_clock":
        data["rows"][0]["available_at"] = "2026-10-19T10:01:00"
    elif mutation == "availability_before_close":
        data["rows"][0]["available_at"] = "2026-10-19T09:59:59+00:00"
    elif mutation == "close_on_other_day":
        data["rows"][0]["close_at"] = "2026-10-18T10:00:00+00:00"
    elif mutation == "extra_path":
        data["path"] = "/private/operator/secrets"
    elif mutation == "extra_row_path":
        data["rows"][0]["file"] = "../secret"
    elif mutation == "numeric_bool_schema":
        data["schema_version"] = True
    elif mutation == "string_synthetic":
        data["synthetic"] = "false"
    elif mutation == "publication_after_availability":
        data["published_at"] = "2026-10-02T10:00:00+00:00"
    elif mutation == "unsupported_currency":
        data["currency"] = "USD"
    elif mutation == "unrecognized_basis":
        data["return_type"] = "adjusted"
    elif mutation == "empty_license":
        data["license_reference"] = "  "
    else:
        data["source_url"] = {
            "bad_url": "http://example.invalid/index",
            "credential_url": "https://user:pass@example.invalid/index",
            "ip_url": "https://127.0.0.1/index",
        }[mutation]
    with pytest.raises(ValueError):
        load_benchmark(write(tmp_path / "b.json", data), AS_OF)


@pytest.mark.parametrize("tail", [',"schema_version":1}', ',"unused":NaN}'])
def test_duplicate_json_keys_and_nonfinite_tokens_are_rejected(tmp_path, tail):
    path = tmp_path / "b.json"
    path.write_text(json.dumps(declaration())[:-1] + tail)
    with pytest.raises(ValueError):
        load_benchmark(path, AS_OF)


def test_regular_nonsymlink_size_and_row_count_bounds(tmp_path):
    target = write(tmp_path / "target.json")
    link = tmp_path / "link.json"
    link.symlink_to(target)
    with pytest.raises(ValueError, match="regular nonsymlink"):
        load_benchmark(link, AS_OF)
    with pytest.raises(ValueError, match="regular nonsymlink"):
        load_benchmark(tmp_path, AS_OF)
    oversized = tmp_path / "oversized.json"
    with oversized.open("wb") as file:
        file.truncate(module.MAX_BYTES + 1)
    with pytest.raises(ValueError, match="bounded"):
        load_benchmark(oversized, AS_OF)
    data = declaration()
    for rows in ([], [data["rows"][0]] * 10001):
        data["rows"] = rows
        with pytest.raises(ValueError, match="10000"):
            load_benchmark(write(target, data), AS_OF)


def test_changed_artifact_during_validation_is_rejected(tmp_path, monkeypatch):
    path = write(tmp_path / "b.json")
    original = module.json.loads

    def loads_then_mutates(*args, **kwargs):
        result = original(*args, **kwargs)
        changed = declaration()
        changed["rows"][0]["level"] = "999"
        write(path, changed)
        return result

    monkeypatch.setattr(module.json, "loads", loads_then_mutates)
    with pytest.raises(RuntimeError, match="changed during validation"):
        load_benchmark(path, AS_OF)


def test_changed_artifact_during_read_is_rejected(tmp_path, monkeypatch):
    path = write(tmp_path / "b.json")
    original, calls = module.os.fstat, 0

    def stat_then_mutates(fd):
        nonlocal calls
        calls += 1
        if calls == 2:
            write(path, {**declaration(), "title": "Mutated during read"})
        return original(fd)

    monkeypatch.setattr(module.os, "fstat", stat_then_mutates)
    with pytest.raises(RuntimeError, match="changed during loading"):
        load_benchmark(path, AS_OF)


def test_valid_extreme_levels_do_not_make_percentage_formatting_overflow(tmp_path):
    data = declaration()
    data["rows"] = data["rows"][:2]
    data["rows"][0]["level"], data["rows"][1]["level"] = "1", "1"
    stock = stocks()[:2]
    stock[0]["total_return_index"] = "0.000000000001"
    stock[1]["total_return_index"] = "9999999999999999999999999999"
    result = compare_benchmark(stock, load_benchmark(write(tmp_path / "b.json", data), AS_OF), 1)
    assert result["state"] == "available"
    assert Decimal(result["relative_strength_pct"]) > Decimal("1e40")


def test_malformed_comparison_rows_return_reason_without_partial_numbers(tmp_path):
    loaded = load_benchmark(write(tmp_path / "b.json"), AS_OF)
    stock = stocks()
    stock[1]["segment_break"] = "false"
    result = compare_benchmark(stock, loaded, 2)
    assert result["reason_code"] == "invalid_input" and result["relative_strength_pct"] is None
    stock = stocks()
    stock.reverse()
    assert compare_benchmark(stock, loaded, 2)["reason_code"] == "invalid_input"
