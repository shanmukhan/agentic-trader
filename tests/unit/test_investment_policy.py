"""Draft contracts only; no broker, execution or investment-suitability acceptance."""

import hashlib
import json
from copy import deepcopy
from decimal import ROUND_DOWN, Context, Decimal, Inexact, Rounded, localcontext

import pytest
from pydantic import ValidationError

from trading_agent.investment_research.policy import (
    POLICY_FIELDS,
    InvestmentPolicyDraft,
    PolicyParameters,
    inspect_draft,
)


def specified_parameters():
    return {
        "horizon_unit": "months",
        "horizon_count": 18,
        "review_cadence": "monthly",
        "review_session_rule": "first_reviewed_session",
        "missed_cycle_policy": "skip",
        "price_basis": "share_adjusted_close",
        "strategy_mode": "rules_only",
        "momentum_sessions": 60,
        "trend_sessions": 200,
        "min_momentum_pct": "2.5",
        "min_average_turnover": "10000000.75",
        "max_daily_volatility_pct": "4",
        "cash_reserve_pct": "10",
        "max_invested_pct": "90",
        "max_stock_weight_pct": "15",
        "max_sector_weight_pct": "30",
        "max_positions": 8,
        "unknown_sector_policy": "block_new_entries",
        "max_entry_gap_bps": "25",
        "stop_pct": "12",
        "target_pct": "30",
        "max_drawdown_pct": "20",
        "screen_exit": "request_exit",
        "universe_exit": "block_for_review",
        "horizon_action": "review_only",
    }


def inspect(parameters=None, **values):
    return inspect_draft({"parameters": {**(parameters or {}), **values}})


def test_empty_draft_has_no_schedule_or_financial_defaults_and_no_authority():
    actual = inspect_draft({})
    names = [field["name"] for field in POLICY_FIELDS]
    assert names == list(PolicyParameters.model_fields)
    assert len(names) == len(set(names)) == 25
    assert actual["parameters"] == dict.fromkeys(names)
    assert actual["missing_fields"] == names
    assert actual["state"] == "incomplete"
    assert actual["label"] is None
    assert actual["policy_version_id"] is None
    assert actual["activation_supported"] is False
    assert actual["backtest_supported"] is False
    assert len(actual["draft_sha256"]) == 64


def test_complete_draft_identity_is_independently_reproducible_and_has_no_authority():
    parameters = specified_parameters()
    actual = inspect_draft({"label": "  Proposed monthly policy  ", "parameters": parameters})
    canonical = {
        **parameters,
        "min_momentum_pct": "2.5000",
        "min_average_turnover": "10000000.75",
        "max_daily_volatility_pct": "4.0000",
        "cash_reserve_pct": "10.0000",
        "max_invested_pct": "90.0000",
        "max_stock_weight_pct": "15.0000",
        "max_sector_weight_pct": "30.0000",
        "max_entry_gap_bps": "25.0000",
        "stop_pct": "12.0000",
        "target_pct": "30.0000",
        "max_drawdown_pct": "20.0000",
    }
    identity = {
        "domain": "agentic-trader.investment-policy",
        "schema_version": 1,
        "family": "nse-investment-policy-v2",
        "decision_semantics": "investment-decisions-v2.1",
        "parameters": canonical,
    }
    expected = hashlib.sha256(
        json.dumps(identity, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()
    assert actual["parameters"] == canonical
    assert actual["draft_sha256"] == expected == actual["policy_version_id"]
    assert actual["label"] == "Proposed monthly policy"
    assert actual["state"] == "specified"
    assert actual["missing_fields"] == []
    assert actual["activation_supported"] is actual["backtest_supported"] is False
    assert "not implemented" in " ".join(actual["limitations"])


@pytest.mark.parametrize(
    "unit,count", [("months", 1), ("months", 1200), ("years", 1), ("years", 100)]
)
@pytest.mark.parametrize("cadence", ["monthly", "quarterly"])
def test_both_horizon_units_and_review_cadences_are_explicit_options(unit, count, cadence):
    actual = inspect(
        specified_parameters(), horizon_unit=unit, horizon_count=count, review_cadence=cadence
    )
    assert actual["state"] == "specified"
    assert actual["parameters"]["horizon_unit"] == unit
    assert actual["parameters"]["horizon_count"] == count
    assert actual["parameters"]["review_cadence"] == cadence


def test_semantic_identity_ignores_labels_input_order_and_equivalent_decimal_spelling():
    initial = specified_parameters()
    original = deepcopy(initial)
    equivalent = dict(reversed(list(initial.items())))
    equivalent["min_momentum_pct"] = "+2.50000"
    equivalent["min_average_turnover"] = "1000000075e-2"
    first = inspect_draft({"parameters": initial, "label": "First idea"})
    second = inspect_draft({"label": "Renamed", "parameters": equivalent})
    assert first["parameters"] == second["parameters"]
    assert first["draft_sha256"] == second["draft_sha256"]
    assert first["policy_version_id"] == second["policy_version_id"]
    assert initial == original
    changed = inspect(initial, horizon_count=19)
    assert changed["policy_version_id"] != first["policy_version_id"]


def test_null_and_omitted_values_have_the_same_identity_and_do_not_fill_defaults():
    assert inspect_draft({}) == inspect_draft({"label": None, "parameters": {}})
    explicit = {name: None for name in PolicyParameters.model_fields}
    assert inspect_draft({"parameters": explicit}) == inspect_draft({})
    partial = inspect(horizon_unit="years", review_cadence="quarterly")
    assert partial["state"] == "incomplete"
    assert partial["parameters"]["horizon_count"] is None
    assert partial["policy_version_id"] is None
    assert "horizon_count" in partial["missing_fields"]
    assert partial["draft_sha256"] != inspect_draft({})["draft_sha256"]


@pytest.mark.parametrize(
    "payload",
    [
        {"schema_version": 2},
        {"activation_supported": True},
        {"account_id": "operator"},
        {"parameters": {"enable": True}},
        {"parameters": None},
        {"parameters": []},
        {"label": 4},
        {"label": True},
        {"label": "x" * 121},
        {"label": "a\x00b"},
        {"parameters": {"horizon_unit": "both"}},
        {"parameters": {"review_cadence": "both"}},
        {"parameters": {"review_session_rule": "first_weekday"}},
        {"parameters": {"missed_cycle_policy": "catch_up"}},
        {"parameters": {"price_basis": "raw"}},
        {"parameters": {"strategy_mode": "ml"}},
        {"parameters": {"unknown_sector_policy": "ignore"}},
        {"parameters": {"screen_exit": "sell_now"}},
        {"parameters": {"universe_exit": "hold"}},
        {"parameters": {"horizon_action": "continue_forever"}},
    ],
)
def test_schema_rejects_unreviewed_fields_and_unsupported_choices(payload):
    with pytest.raises(ValidationError):
        inspect_draft(payload)


@pytest.mark.parametrize(
    "field", ["horizon_count", "momentum_sessions", "trend_sessions", "max_positions"]
)
@pytest.mark.parametrize("value", [True, False, "2", 2.0, -1, 0, 1201])
def test_integer_fields_reject_coercion_and_out_of_bound_values(field, value):
    with pytest.raises(ValidationError):
        inspect(**{field: value})


@pytest.mark.parametrize(
    "value",
    [
        1,
        1.5,
        True,
        False,
        Decimal("1"),
        "NaN",
        "sNaN",
        "Infinity",
        "-Infinity",
        "1_000",
        "1,000",
        " 1",
        "1 ",
        "",
        ".",
        "+",
        "1e19",
        "1e-19",
        "1e999",
        "1e1000",
        "0" * 81,
        "0.00001",
        "1.23456",
        "100.00001",
        "１",
        "\x001",
    ],
)
def test_decimal_fields_require_bounded_exact_decimal_strings(value):
    with pytest.raises(ValidationError):
        inspect(min_momentum_pct=value)


@pytest.mark.parametrize(
    "name,value,expected",
    [
        ("min_momentum_pct", "-100", "-100.0000"),
        ("min_momentum_pct", "10000", "10000.0000"),
        ("min_momentum_pct", "-0", "0.0000"),
        ("min_momentum_pct", "+.1250", "0.1250"),
        ("min_momentum_pct", "1e-4", "0.0001"),
        ("min_momentum_pct", "1e2", "100.0000"),
        ("min_average_turnover", "1000000000000.00", "1000000000000.00"),
        ("min_average_turnover", "0", "0.00"),
        ("cash_reserve_pct", "100", "100.0000"),
        ("max_invested_pct", "100", "100.0000"),
        ("max_stock_weight_pct", "100", "100.0000"),
        ("max_sector_weight_pct", "100", "100.0000"),
        ("max_daily_volatility_pct", "100", "100.0000"),
        ("max_entry_gap_bps", "5000", "5000.0000"),
        ("stop_pct", "99.9999", "99.9999"),
        ("target_pct", "1000", "1000.0000"),
        ("max_drawdown_pct", "100", "100.0000"),
    ],
)
def test_decimal_boundaries_and_canonical_scales_are_exact(name, value, expected):
    assert inspect(**{name: value})["parameters"][name] == expected


@pytest.mark.parametrize(
    "name,value",
    [
        ("min_momentum_pct", "-100.0001"),
        ("min_momentum_pct", "10000.0001"),
        ("min_average_turnover", "-0.01"),
        ("min_average_turnover", "1000000000000.01"),
        ("min_average_turnover", "1.001"),
        ("cash_reserve_pct", "-0.0001"),
        ("cash_reserve_pct", "100.0001"),
        ("max_invested_pct", "0"),
        ("max_stock_weight_pct", "0"),
        ("max_sector_weight_pct", "0"),
        ("max_daily_volatility_pct", "0"),
        ("max_entry_gap_bps", "0"),
        ("max_entry_gap_bps", "5000.0001"),
        ("stop_pct", "0"),
        ("stop_pct", "100"),
        ("target_pct", "0"),
        ("target_pct", "1000.0001"),
        ("max_drawdown_pct", "0"),
        ("max_drawdown_pct", "100.0001"),
    ],
)
def test_decimal_range_and_precision_failures_are_invalid_instead_of_missing(name, value):
    with pytest.raises(ValidationError):
        inspect(**{name: value})


@pytest.mark.parametrize(
    "parameters,match",
    [
        ({"horizon_unit": "years", "horizon_count": 101}, "100 years"),
        ({"cash_reserve_pct": "100", "max_invested_pct": "0.0001"}, "cash reserve"),
        ({"cash_reserve_pct": "10.0001", "max_invested_pct": "90"}, "cash reserve"),
        ({"max_stock_weight_pct": "60", "max_invested_pct": "50"}, "stock weight"),
        ({"max_sector_weight_pct": "60", "max_invested_pct": "50"}, "sector weight"),
        ({"max_stock_weight_pct": "30.0001", "max_sector_weight_pct": "30"}, "stock weight"),
    ],
)
def test_inconsistent_partial_financial_limits_are_rejected(parameters, match):
    with pytest.raises(ValidationError, match=match):
        inspect(parameters)


def test_exact_allocation_boundary_is_valid_without_float_rounding():
    actual = inspect(
        cash_reserve_pct="33.3333",
        max_invested_pct="66.6667",
        max_stock_weight_pct="66.6667",
        max_sector_weight_pct="66.6667",
    )
    assert actual["parameters"]["cash_reserve_pct"] == "33.3333"
    assert actual["parameters"]["max_invested_pct"] == "66.6667"


def test_identity_and_validation_do_not_depend_on_host_decimal_context():
    expected = inspect(specified_parameters())
    hostile = Context(prec=2, rounding=ROUND_DOWN)
    hostile.traps[Inexact] = True
    hostile.traps[Rounded] = True
    with localcontext(hostile) as host:
        flags = dict(host.flags)
        assert inspect(specified_parameters()) == expected
        assert (
            inspect(cash_reserve_pct="33.3333", max_invested_pct="66.6667")["state"] == "incomplete"
        )
        with pytest.raises(ValidationError, match="cash reserve"):
            inspect(cash_reserve_pct="33.3334", max_invested_pct="66.6667")
        assert dict(host.flags) == flags


def test_models_are_frozen_and_do_not_mutate_or_share_draft_inputs():
    payload = {"label": "Proposal", "parameters": {"horizon_unit": "years"}}
    original = deepcopy(payload)
    draft = InvestmentPolicyDraft.model_validate(payload)
    with pytest.raises(ValidationError, match="frozen"):
        draft.label = "Changed"
    with pytest.raises(ValidationError, match="frozen"):
        draft.parameters.horizon_count = 5
    first = inspect_draft(payload)
    first["parameters"]["horizon_unit"] = "months"
    assert payload == original
    assert inspect_draft(payload)["parameters"]["horizon_unit"] == "years"


def test_metadata_offers_no_implicit_selection_and_describes_bounds_used_by_validation():
    for field in POLICY_FIELDS:
        assert field["label"] and field["group"]
        assert "default" not in field
        if field["kind"] == "choice":
            assert all(set(choice) == {"value", "label"} for choice in field["choices"])
            for choice in field["choices"]:
                assert (
                    inspect(**{field["name"]: choice["value"]})["parameters"][field["name"]]
                    == choice["value"]
                )
        elif field["kind"] == "integer":
            assert (
                inspect(**{field["name"]: field["minimum"]})["parameters"][field["name"]]
                == field["minimum"]
            )
            assert (
                inspect(**{field["name"]: field["maximum"]})["parameters"][field["name"]]
                == field["maximum"]
            )
        else:
            assert field["step"] == (
                "0.01" if field["name"] == "min_average_turnover" else "0.0001"
            )
            assert isinstance(field["minimum"], str)
            assert isinstance(field["maximum"], str)
            assert field["scale"] == (2 if field["name"] == "min_average_turnover" else 4)
