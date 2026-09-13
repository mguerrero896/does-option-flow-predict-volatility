"""Synthetic checks; no historical panels or model fits."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import activity_without_iv as variant
import materialize_iv as baseline
import numpy as np
import polars as pl
import pytest
from polars.testing import assert_frame_equal
from test_materialize_iv import tape_fixture


def inputs():
    base = pl.DataFrame(
        {
            "asset": ["AAPL"],
            "session_date": ["2026-07-01"],
            "origin_minute": [35],
            "rv_back_30": [0.001],
            "rate": [0.04],
            "dividend_cash_prior365": [1.0],
        }
    )
    grid = SimpleNamespace(close=np.full(390, 100.0), open=np.full(390, 100.0))
    return tape_fixture(), base, grid


def test_default_and_all_valid_match_original_exactly():
    raw, base, grid = inputs()
    names = list(variant.ACTIVITY_COLUMNS) + ["b2_30m_vega_flow", "b2_30m_d_iv"]
    expected = baseline.option_features(raw, base, grid, names, filtered=True)
    for opt_in in (False, True):
        actual = variant.option_features(
            raw, base, grid, names, filtered=True, independent_activity=opt_in
        )
        assert_frame_equal(expected, actual, check_exact=True)


@pytest.mark.parametrize("iv", [None, float("nan"), float("inf"), -1.0, 0.02, 4.0])
def test_invalid_iv_counts_activity_without_changing_iv_components(iv):
    raw, base, grid = inputs()
    raw = raw.with_columns(
        pl.when(pl.col("id") == "110")
        .then(pl.lit(iv, pl.Float64))
        .otherwise(pl.col("implied_volatility"))
        .alias("implied_volatility")
    )
    names = list(variant.ACTIVITY_COLUMNS) + [
        "b2_30m_vega_flow",
        "b2_30m_d_iv",
        "b2_30m_decay_intensity_last",
        "rp4_surface_populated_cells",
        "rp4_dealer_gamma_net",
    ]
    original = baseline.option_features(raw, base, grid, names, filtered=True)
    result = variant.option_features(
        raw, base, grid, names, filtered=True, independent_activity=True
    )
    assert result["b2_30m_trades"][0] == original["b2_30m_trades"][0] + 1
    assert result["b2_30m_premium"][0] == original["b2_30m_premium"][0] + 1000
    unchanged = [n for n in result.columns if n not in variant.ACTIVITY_COLUMNS]
    assert_frame_equal(original.select(unchanged), result.select(unchanged), check_exact=True)


@pytest.mark.parametrize(
    "field,value",
    [
        ("size", 0.0),
        ("size", float("inf")),
        ("premium", None),
        ("premium", -1.0),
        ("premium", float("nan")),
        ("strike", None),
        ("option_type", "unknown"),
        ("executed_at", None),
        ("created_at", None),
    ],
)
def test_invalid_activity_excluded(field, value):
    raw, base, grid = inputs()
    expected = variant.activity_features(raw, base, grid)
    changed = raw.with_columns(
        pl.when(pl.col("id") == "110")
        .then(pl.lit(value, raw.schema[field]))
        .otherwise(pl.col(field))
        .alias(field)
    )
    result = variant.activity_features(changed, base, grid)
    assert result["b2_30m_trades"][0] == expected["b2_30m_trades"][0] - 1
    assert result["b2_30m_premium"][0] == expected["b2_30m_premium"][0] - 1000


def test_two_clocks_boundaries_stale_and_negative_latency():
    raw, base, grid = inputs()
    cutoff = datetime(2026, 7, 1, 14, 3, tzinfo=UTC)
    lower = cutoff - timedelta(minutes=5)
    cases = [
        (lower, lower),
        (cutoff, cutoff),
        (lower - timedelta(microseconds=1), lower),
        (cutoff, cutoff + timedelta(microseconds=1)),
        (cutoff + timedelta(microseconds=1), cutoff),
    ]
    expected = variant.activity_features(raw, base, grid)
    for index, (executed, created) in enumerate(cases):
        extra = raw.head(1).with_columns(
            id=pl.lit(f"extra{index}"),
            implied_volatility=pl.lit(None, pl.Float64),
            executed_at=pl.lit(executed),
            created_at=pl.lit(created),
        )
        actual = variant.activity_features(pl.concat([raw, extra]), base, grid)
        assert actual["b2_5m_trades"][0] == expected["b2_5m_trades"][0] + (index < 2)


def test_sparse_is_null_empty_window_is_zero_and_clocks_require_utc():
    raw, base, grid = inputs()
    assert variant.activity_features(raw.head(49), base, grid)["b2_5m_trades"][0] is None
    late = base.with_columns(origin_minute=pl.lit(150))
    assert variant.activity_features(raw, late, grid)["b2_5m_trades"][0] == 0
    with pytest.raises(ValueError, match="REQUIRES_UTC"):
        variant.activity_features(
            raw.with_columns(pl.col("created_at").dt.replace_time_zone(None)), base, grid
        )


def test_timestamp_units_do_not_change_activity():
    raw, base, grid = inputs()
    expected = variant.activity_features(raw, base, grid)
    changed = raw.with_columns(pl.col("created_at", "executed_at").dt.cast_time_unit("ns"))
    assert_frame_equal(expected, variant.activity_features(changed, base, grid), check_exact=True)


def test_session_identity_and_keys_are_required():
    raw, base, grid = inputs()
    with pytest.raises(ValueError, match="REQUIRES_ONE_SESSION"):
        variant.activity_features(raw, base.head(0), grid)
    with pytest.raises(ValueError, match="REQUIRES_ONE_SESSION"):
        variant.activity_features(
            raw, pl.concat([base, base.with_columns(asset=pl.lit("MSFT"))]), grid
        )
    with pytest.raises(ValueError):
        variant.activity_features(raw, pl.concat([base, base]), grid)


def test_all_iv_missing_activity_survives_without_imputing_iv():
    raw, base, grid = inputs()
    raw = raw.with_columns(implied_volatility=pl.lit(None, pl.Float64))
    names = ["b2_30m_trades", "b2_30m_premium", "b2_30m_vega_flow"]
    before = raw.clone()
    actual = variant.option_features(
        raw, base, grid, names, filtered=True, independent_activity=True
    )
    assert actual["b2_30m_trades"][0] == 120
    assert actual["b2_30m_premium"][0] == 120000
    assert actual["b2_30m_vega_flow"][0] is None
    assert_frame_equal(raw, before, check_exact=True)
