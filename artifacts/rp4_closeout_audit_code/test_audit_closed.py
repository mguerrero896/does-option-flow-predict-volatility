"""Synthetic-only mapping and weighting regressions for descriptive extraction."""

import pandas as pd
import pytest
from artifacts.rp4_closeout_audit_code.audit_closed import (
    coefficient_rows,
    paired_profile,
    profile_groups,
)
from artifacts.rp4_closeout_audit_code.public_projection import neutral_inputs


def test_removed_coefficients_and_presence_names_are_unambiguous():
    spec = {
        "feature_sets": {"B2": ["x", "y"]},
        "assets": ["A", "B"],
        "feature_transforms": {"x": "log"},
    }
    pre = {
        "input_columns": 3,
        "active_columns": ["intercept", "feature:0", "presence:1"],
        "presence_indices": [1],
        "removed_columns": [
            {"column": "feature:1", "reason": "all_missing_training"},
            {"column": "feature:2", "reason": "zero_variance_training"},
        ],
        "encoded_columns_before_rank_filter": ["feature:0", "feature:2", "presence:1"],
        "centers": [2, 0, 0.5],
        "scales_population_sd": [3, 0, 0.5],
        "medians": [2, None, 0],
        "finite_training_counts": [4, 0, 4],
        "training_rows": 4,
    }
    rows = coefficient_rows({"preprocessing": {"refit": pre}, "coefficients": [1, 2, 3]}, spec)
    indexed = {row["column"]: row for row in rows}
    assert indexed["presence:y"]["coefficient_standardized"] == 3
    assert indexed["y"]["coefficient_standardized"] == 0
    assert indexed["y"]["zero_semantics"] == "dropped_zero_contribution_not_estimated"
    assert indexed["y"]["training_median"] is None
    assert indexed["asset_effect:B"]["removed_reason"] == "zero_variance_training"


def test_weighting_is_not_origin_pooling():
    frame = pd.DataFrame(
        {
            "session_date": ["a", "a", "a", "b"],
            "asset": ["A", "A", "B", "A"],
            "loss__f__B0": [10.0, 10.0, 2.0, 2.0],
            "loss__f__B1": [0.0, 0.0, 0.0, 0.0],
        }
    )
    row = paired_profile(frame, "f", "B0", "B1")
    assert row["delta_pooled"] == 6
    assert row["delta_equal_session_asset"] == 4
    assert row["new_p_value"] is None


def test_intraday_distinguishes_market_and_observed_hour():
    frame = pd.DataFrame(
        {
            "origin_minute": [35, 55, 60, 90, 95, 300, 330],
            "session_date": ["2025-04-07"] * 7,
            "window_empty_5m": [False] * 7,
            "window_empty_30m": [False] * 7,
            "third_friday": [False] * 7,
        }
    )
    meta = pd.DataFrame({"session": ["2025-04-07"], "train_rows": [500]})
    masks = {label: mask for _, label, mask in profile_groups(frame, meta)}
    assert masks["first_market_hour_origin_lt60"].sum() == 2
    assert masks["first_observed_hour_origin35_94"].sum() == 4
    assert masks["last_registered_block_origin_ge300"].sum() == 2
    assert masks["last_market_hour_origin_ge330"].sum() == 1


def test_missing_design_index_is_rejected():
    with pytest.raises(AssertionError):
        coefficient_rows(
            {"preprocessing": {"refit": {"input_columns": 7}}},
            {"feature_sets": {"B2": ["x"]}, "assets": ["A"]},
        )


def test_public_aliases_retain_digests_without_private_paths():
    sources = {
        "private-input/8d0a2131844505b53ed6": "a" * 64,
        "private-input/aac3806c618aa98fef76": "b" * 64,
    }
    result = neutral_inputs(sources)
    assert len(result) == 2 and set(result.values()) == set(sources.values())
    assert all(key.startswith("inputs/source_") for key in result)
    assert not any("private" in key or ":" in key for key in result)
