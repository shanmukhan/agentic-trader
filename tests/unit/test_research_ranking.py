"""Invented screen evidence, not broker or real-market acceptance."""

from copy import deepcopy
from decimal import Decimal

import pytest

from trading_agent.daily_research.analysis import DailyPolicy, analyze
from trading_agent.daily_research.dataset import DailyDataset
from trading_agent.daily_research.demo import create_daily_demo
from trading_agent.investment_research.ranking import explain_ranking

POLICY = {
    "momentum_sessions": 20,
    "trend_sessions": 50,
    "min_average_turnover": "10000000.00",
    "max_daily_volatility_pct": "5.0000",
}


def row(**changes):
    return {
        "symbol": "NSE:INVENTED",
        "status": "research_candidate",
        "rank": 3,
        "reasons": [],
        "gross_total_return_pct": "1.0000000000000000000000001",
        "index_level": "101.0000000000000000000000001",
        "trend_index_average": "100.0000000000000000000000001",
        "average_turnover": "10000000.00",
        "daily_volatility_pct": "5.0000",
        **changes,
    }


def evidence(result):
    return {item["metric"]: item for item in result["rows"][0]["evidence"]}


def test_method_explains_actual_policy_and_preserves_rank_status_order_and_input():
    rows = [
        row(symbol="NSE:Z", rank=8),
        row(symbol="NSE:A", rank=2),
        row(symbol="NSE:OUTSIDE", status="outside_universe", rank=None),
    ]
    original_rows, original_policy = deepcopy(rows), deepcopy(POLICY)
    result = explain_ranking(rows, POLICY)
    assert result["method_id"] == "legacy-prior-daily-momentum-v1"
    assert "descending, then symbol ascending" in result["tie_rule"]
    assert "after excluding unreviewed equity share classes" in result["tie_rule"]
    assert "no new score or eligibility decision" in result["detail"]
    assert result["thresholds"] == {
        "momentum_sessions": "20",
        "trend_sessions": "50",
        "momentum_min_exclusive_pct": "0",
        "min_average_turnover": "10000000.00",
        "max_daily_volatility_pct": "5.0000",
    }
    assert [item["rank"] for item in result["rows"]] == [8, 2, None]
    assert [item["symbol"] for item in result["rows"]] == ["NSE:Z", "NSE:A", "NSE:OUTSIDE"]
    assert rows == original_rows and original_policy == POLICY
    for explained, original in zip(result["rows"], rows, strict=True):
        assert {key: value for key, value in explained.items() if key != "evidence"} == original
        assert all("score" not in item for item in explained["evidence"])
    result["rows"][0]["reasons"].append("COPY_ONLY")
    assert rows == original_rows
    assert "20 sessions" in evidence(result)["gross_total_return_pct"]["detail"]
    assert "50-session average" in evidence(result)["index_level"]["detail"]


@pytest.mark.parametrize(
    ("metric", "value", "state"),
    [
        ("gross_total_return_pct", "-0.0000000000000000000000001", "failed"),
        ("gross_total_return_pct", "0.0000", "failed"),
        ("gross_total_return_pct", "0.0000000000000000000000001", "passed"),
        ("index_level", "100.0000000000000000000000000", "failed"),
        ("index_level", "100.0000000000000000000000001", "passed"),
        ("average_turnover", "9999999.9999999999999999999", "failed"),
        ("average_turnover", "10000000.00", "passed"),
        ("daily_volatility_pct", "5.0000000000000000000000001", "failed"),
        ("daily_volatility_pct", "5.0000", "passed"),
    ],
)
def test_exact_predicates_and_equality_boundaries_match_legacy_rules(metric, value, state):
    original = row(**{metric: value})
    result = explain_ranking([original], POLICY)
    item = evidence(result)[metric]
    assert item["state"] == state
    assert item["observed"] == value
    assert result["rows"][0]["status"] == original["status"]
    assert result["rows"][0]["rank"] == 3


def test_big_exact_numbers_do_not_collapse_to_float_equality():
    result = explain_ranking(
        [
            row(
                index_level="9007199254740993.12340001",
                trend_index_average="9007199254740993.12340002",
                average_turnover="9007199254740993.12340001",
            )
        ],
        {**POLICY, "min_average_turnover": "9007199254740993.12340002"},
    )
    items = evidence(result)
    assert items["index_level"]["state"] == items["average_turnover"]["state"] == "failed"
    assert items["index_level"]["observed"] == "9007199254740993.12340001"
    assert items["index_level"]["threshold"] == "9007199254740993.12340002"


@pytest.mark.parametrize("value", [None, True, 0.0, float("inf"), "NaN", "Infinity", "invalid"])
def test_missing_invalid_and_binary_float_values_remain_unavailable(value):
    result = explain_ranking([row(gross_total_return_pct=value)], POLICY)
    item = evidence(result)["gross_total_return_pct"]
    assert item["state"] == "unavailable" and item["observed"] is None
    assert item["threshold"] == "0"
    assert "Comparison unavailable" in item["detail"]


def test_missing_rows_and_thresholds_are_unknown_without_default_or_zero_invention():
    result = explain_ranking(
        [{"symbol": "NSE:MISSING", "status": "needs_data", "rank": None, "reasons": []}],
        {},
    )
    assert all(item["state"] == "unavailable" for item in result["rows"][0]["evidence"])
    assert all(item["observed"] is None for item in result["rows"][0]["evidence"])
    assert result["thresholds"]["momentum_sessions"] is None
    assert result["thresholds"]["min_average_turnover"] is None
    assert evidence(result)["average_turnover"]["threshold"] is None
    assert evidence(result)["index_level"]["threshold"] is None
    assert explain_ranking([], {})["rows"] == []


def test_decimal_and_integer_inputs_remain_exact_text_without_changing_original_types():
    original = row(gross_total_return_pct=Decimal("1.230000000000000001"), index_level=101)
    result = explain_ranking([original], POLICY)
    assert evidence(result)["gross_total_return_pct"]["observed"] == "1.230000000000000001"
    assert evidence(result)["index_level"]["observed"] == "101"
    assert isinstance(result["rows"][0]["gross_total_return_pct"], Decimal)


def test_share_class_rejection_cannot_be_hidden_by_numeric_pass_or_existing_rank():
    original = row(reasons=["EQUITY_SHARE_CLASS_NOT_REVIEWED"], equity_share_class_reviewed=True)
    result = explain_ranking([original], POLICY)
    items = evidence(result)
    assert all(items[key]["state"] == "passed" for key in POLICY_METRICS)
    assert items["equity_share_class_reviewed"]["state"] == "failed"
    assert result["rows"][0]["rank"] == original["rank"]
    assert (
        evidence(explain_ranking([row()], POLICY))["equity_share_class_reviewed"]["state"]
        == "unavailable"
    )
    assert (
        evidence(explain_ranking([row(equity_share_class_reviewed=False)], POLICY))[
            "equity_share_class_reviewed"
        ]["state"]
        == "failed"
    )
    assert (
        evidence(explain_ranking([row(equity_share_class_reviewed=True)], POLICY))[
            "equity_share_class_reviewed"
        ]["state"]
        == "passed"
    )


POLICY_METRICS = {
    "gross_total_return_pct": "NONPOSITIVE_MOMENTUM",
    "index_level": "BELOW_TREND_AVERAGE",
    "average_turnover": "LOW_AVERAGE_TURNOVER",
    "daily_volatility_pct": "HIGH_DAILY_VOLATILITY",
}


def test_real_screen_implementation_agrees_for_synthetic_candidates_and_exclusions(tmp_path):
    directory = tmp_path / "invented-daily-input"
    as_of = create_daily_demo(directory)
    result = analyze(DailyDataset(directory), DailyPolicy(), as_of)
    before = deepcopy(result)
    explained = explain_ranking(result["rows"], result["policy"])
    for original, item in zip(result["rows"], explained["rows"], strict=True):
        assert item["status"] == original["status"] and item["rank"] == original["rank"]
        items = {entry["metric"]: entry for entry in item["evidence"]}
        for metric, reason in POLICY_METRICS.items():
            assert (items[metric]["state"] == "failed") == (reason in original["reasons"])
            if metric not in original:
                assert items[metric]["state"] == "unavailable"
    assert {item["status"] for item in explained["rows"]} == {
        "research_candidate",
        "screened_out",
        "needs_data",
        "outside_universe",
    }
    assert result == before


def test_actual_desk_share_class_filter_and_candidate_ranks_are_retained(desk_factory):
    desk, _, _ = desk_factory()
    original = deepcopy(desk.research.result)
    result = explain_ranking(original["rows"], original["policy"])
    for original_row, explained_row in zip(original["rows"], result["rows"], strict=True):
        assert explained_row["rank"] == original_row["rank"]
        if "EQUITY_SHARE_CLASS_NOT_REVIEWED" in original_row["reasons"]:
            items = {item["metric"]: item for item in explained_row["evidence"]}
            assert items["equity_share_class_reviewed"]["state"] == "failed"
    assert desk.research.result == original
