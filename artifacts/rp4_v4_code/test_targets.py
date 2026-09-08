"""Synthetic RP4 v4 target reconstruction and byte-alignment contracts; no real labels."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
import polars as pl
import pytest
from artifacts.rp4_v4_code import materialize_targets as target
from polars.testing import assert_frame_equal

from mds650.rp2.bars import build_session_grid
from mds650.rp2.realized import forward_measures, log_returns

SESSION = "2026-06-09"


def bars(*, minutes: int = 390, session: str = SESSION) -> pl.DataFrame:
    index: npt.NDArray[np.int64] = np.arange(minutes, dtype=np.int64)
    close = np.exp(np.log(100.0) + np.cumsum(np.sin(index * 0.73) * 0.002 + 0.00001))
    return pl.DataFrame({"asset": "AAPL", "session_date": session, "minute": index, "close": close})


def keys(origins: list[int], *, session: str = SESSION) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "asset": ["AAPL"] * len(origins),
            "session_date": [session] * len(origins),
            "origin_minute": origins,
        },
        schema={"asset": pl.String, "session_date": pl.String, "origin_minute": pl.Int64},
    )


def derive(frame: pl.DataFrame, origins: list[int], *, session: str = SESSION) -> pl.DataFrame:
    return target.session_targets(
        keys(origins, session=session),
        build_session_grid(frame, session=date.fromisoformat(session)),
        frame,
    )


def test_exact_inherited_estimator_float_bits_and_rv30_control() -> None:
    frame = bars()
    origins = [0, 3, 120, 359]
    actual = derive(frame, origins)
    returns = log_returns(frame["close"].to_numpy())
    for h in (*target.HORIZONS, 30):
        name = f"rv_{h}" if h != 30 else "rv30_reconstructed"
        expected = forward_measures(returns, np.array(origins, dtype=np.int64), h).rv
        np.testing.assert_array_equal(
            actual[name].to_numpy().view(np.uint64), expected.view(np.uint64)
        )


def test_future_return_index_and_no_predictor_latency_shift() -> None:
    frame = bars()
    result = derive(frame, [30])
    closes = frame["close"].to_numpy()
    for h in target.HORIZONS:
        expected = np.sum(np.diff(np.log(closes[30 : 30 + h + 1])) ** 2)
        assert result[f"rv_{h}"][0] == pytest.approx(expected, rel=1e-12)
        shifted = np.sum(np.diff(np.log(closes[28 : 28 + h + 1])) ** 2)
        assert not np.isclose(result[f"rv_{h}"][0], shifted, rtol=1e-8, atol=0)


def test_beyond_horizon_mutation_does_not_change_target_prefix_bits() -> None:
    frame = bars()
    changed = frame.with_columns(
        pl.when(pl.col("minute") > 45)
        .then(pl.col("close") * 2)
        .otherwise(pl.col("close"))
        .alias("close")
    )
    before, after = derive(frame, [30]), derive(changed, [30])
    for h in target.HORIZONS:
        np.testing.assert_array_equal(
            before[f"rv_{h}"].to_numpy().view(np.uint64),
            after[f"rv_{h}"].to_numpy().view(np.uint64),
        )
    within = frame.with_columns(
        pl.when(pl.col("minute") == 35)
        .then(pl.col("close") * 2)
        .otherwise(pl.col("close"))
        .alias("close")
    )
    assert derive(within, [30])["rv_5"][0] != before["rv_5"][0]


def test_h_plus_one_observed_anchors_not_forward_filled_valid_mask() -> None:
    frame = bars().filter(pl.col("minute") != 40)
    result = derive(frame, [30])
    assert np.isfinite(result["rv_5"][0])
    assert np.isnan(result["rv_15"][0])
    assert result["target_status_15"][0] == "unobserved_target_close"
    assert build_session_grid(frame, session=date.fromisoformat(SESSION)).valid[40]


def test_missing_either_endpoint_invalidates_five_minute_target() -> None:
    for missing in (30, 35):
        result = derive(bars().filter(pl.col("minute") != missing), [30])
        assert np.isnan(result["rv_5"][0])


def test_missing_outside_window_still_obeys_inherited_session_fill_gate() -> None:
    frame = bars()
    accepted = derive(frame.filter(pl.col("minute") < 371), [30])
    rejected = derive(frame.filter(pl.col("minute") < 370), [30])
    assert np.isfinite(accepted["rv_5"][0])
    assert np.isnan(rejected["rv_5"][0])
    assert rejected["target_status_5"][0] == "session_quality"


def test_leading_missing_never_backfilled_and_origin_grid_is_not_reselected() -> None:
    frame = bars().filter(pl.col("minute") >= 2)
    result = derive(frame, [0, 1, 2, 3])
    assert result["origin_minute"].to_list() == [0, 1, 2, 3]
    assert np.isnan(result["rv_5"].to_numpy()[:2]).all()
    assert np.isfinite(result["rv_5"].to_numpy()[2:]).all()


def test_early_close_and_out_of_session_origins() -> None:
    session = "2025-11-28"
    result = derive(bars(minutes=210, session=session), [194, 204, 205, -1], session=session)
    assert np.isfinite(result["rv_15"][0])
    assert np.isfinite(result["rv_5"][1])
    assert np.isnan(result["rv_5"][2])
    assert np.isnan(result["rv_5"][3])


def test_holiday_and_missing_grid_remain_nan_with_reason() -> None:
    holiday = "2026-07-03"
    result = derive(bars(session=holiday), [30], session=holiday)
    assert result["target_status_5"][0] == "session_quality"
    assert np.isnan(result["rv_5"][0])
    result = target.session_targets(keys([30]), None, None)
    assert result["target_status_5"][0] == "missing_bar_grid"


def test_zero_variance_is_not_floored_or_silently_removed() -> None:
    result = derive(bars().with_columns(close=pl.lit(100.0)), [30])
    assert result["rv_5"][0] == 0.0
    assert result.height == 1


def test_key_duplicates_and_nulls_rejected() -> None:
    with pytest.raises(ValueError, match="KEY_NOT_UNIQUE"):
        target.session_targets(keys([30, 30]), None, None)
    with pytest.raises(ValueError, match="KEY_NOT_UNIQUE"):
        target.session_targets(keys([30]).with_columns(asset=pl.lit(None, pl.String)), None, None)


def synthetic_base(origins: list[int]) -> pl.DataFrame:
    frame = keys(origins)
    times = [datetime(2026, 6, 9, 13, 30, tzinfo=UTC) + timedelta(minutes=i) for i in origins]
    return frame.with_columns(
        pl.Series("forecast_origin_utc", times, dtype=pl.Datetime("us", "UTC")),
        pl.Series(
            "target_end_utc",
            [t + timedelta(minutes=30) for t in times],
            dtype=pl.Datetime("us", "UTC"),
        ),
        rv30=pl.lit(0.1),
        predictor=pl.lit(1.0),
        rp4_eligible=pl.lit(True),
    )


def test_sidecar_alignment_uses_keys_and_keeps_thirty_minute_clock() -> None:
    base = synthetic_base([30, 60])
    original = base.clone()
    rebuilt = derive(bars(), [60, 30])
    sidecar = target.attach_target_ends(base, rebuilt)
    assert sidecar.columns == target.KEYS + [
        "rv_15",
        "rv_5",
        "target_end_15_utc",
        "target_end_5_utc",
    ]
    assert sidecar["rv_5"][0] == rebuilt.filter(pl.col("origin_minute") == 30)["rv_5"][0]
    assert (sidecar["target_end_5_utc"][0] - base["forecast_origin_utc"][0]).total_seconds() == 300
    assert_frame_equal(base, original, check_exact=True)
    with pytest.raises(ValueError, match="THIRTY_MINUTE_END"):
        target.attach_target_ends(
            base.with_columns(
                target_end_utc=pl.col("forecast_origin_utc") + pl.duration(minutes=15)
            ),
            rebuilt,
        )


def test_byte_comparison_does_not_mistake_tolerance_for_identity() -> None:
    frame = keys([30, 60]).with_columns(
        pl.Series("a", [0.1, 0.2]),
        pl.Series("b", [np.nextafter(0.1, 1.0), 0.2]),
    )
    summary, different = target.compare_float_columns(frame, "a", "b", label="synthetic")
    assert summary["finite_bit_mismatches"] == 1
    assert summary["tolerance_mismatches"] == 0
    assert different["origin_minute"].to_list() == [30]


def test_null_nan_and_signed_zero_are_audited_separately() -> None:
    frame = keys([1, 2, 3, 4]).with_columns(
        pl.Series("a", [None, np.nan, 0.0, np.nan], dtype=pl.Float64),
        pl.Series("b", [np.nan, np.nan, -0.0, 1.0], dtype=pl.Float64),
    )
    summary, mismatch = target.compare_float_columns(frame, "a", "b", label="synthetic")
    assert summary["null_mask_mismatches"] == 1
    assert summary["finite_bit_mismatches"] == 1
    assert summary["finite_mask_mismatches"] == 1
    assert mismatch.height == 3


def test_registered_reference_comparison_is_keyed_not_positional() -> None:
    reconstructed = keys([30, 60]).with_columns(
        pl.Series("rv_15", [0.1, 0.2]), pl.Series("rv_5", [0.3, 0.4])
    )
    registered = reconstructed.reverse()
    summary, differences = target.reference_comparison(reconstructed, registered)
    assert summary["intersecting_keys"] == 2
    assert differences.is_empty()
    assert target.keyed_float_digest(reconstructed, "rv_5") == target.keyed_float_digest(
        registered, "rv_5"
    )


def test_missing_short_target_on_inherited_mask_fails_census_not_excludes() -> None:
    base = synthetic_base([30, 60])
    reconstructed = derive(bars(), [60, 30]).with_columns(
        pl.when(pl.col("origin_minute") == 30)
        .then(float("nan"))
        .otherwise(pl.col("rv_5"))
        .alias("rv_5")
    )
    specification: dict[str, Any] = {"mandatory_predictors": ["predictor"]}
    counts, failures, coverage = target.inherited_census(base, reconstructed, specification)
    assert counts == {"rv_15": 0, "rv_5": 1}
    assert failures["origin_minute"].to_list() == [30]
    assert coverage.filter(pl.col("target") == "rv_5")["eligible_v3"][0] == 2
    assert base.height == reconstructed.height == 2


def test_new_targets_cannot_restore_rows_excluded_by_original_rv30_or_quality() -> None:
    base = synthetic_base([30, 60]).with_columns(
        pl.Series("rv30", [np.nan, 0.1]), pl.Series("rp4_eligible", [True, False])
    )
    reconstructed = derive(bars(), [30, 60]).with_columns(rv_5=pl.lit(float("nan")))
    counts, failures, coverage = target.inherited_census(
        base, reconstructed, {"mandatory_predictors": ["predictor"]}
    )
    assert counts["rv_5"] == 0
    assert failures.is_empty()
    assert coverage["eligible_v3"].sum() == 0


def test_hash_gate_rejects_before_reading_real_inputs(tmp_path: Path) -> None:
    specification = tmp_path / "specification.json"
    specification.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="SOURCE_DRIFT"):
        target.input_contract(specification, "0" * 64, "0" * 64)


def test_bar_asset_session_and_minute_identity_are_not_positional() -> None:
    frame = bars()
    grid = build_session_grid(frame, session=date.fromisoformat(SESSION))
    with pytest.raises(ValueError, match="OBSERVED_BAR_IDENTITY"):
        target.session_targets(keys([30]), grid, frame.with_columns(asset=pl.lit("TSLA")))
    with pytest.raises(ValueError, match="OBSERVED_BAR_IDENTITY"):
        target.session_targets(keys([30]), grid, pl.concat([frame, frame.head(1)]))
    typed_date = frame.with_columns(pl.col("session_date").str.to_date())
    assert_frame_equal(
        target.session_targets(keys([30]), grid, typed_date),
        target.session_targets(keys([30]), grid, frame),
        check_exact=True,
    )


def test_missing_reconstructed_key_does_not_silently_shrink_census() -> None:
    with pytest.raises(AssertionError):
        target.inherited_census(
            synthetic_base([30, 60]), derive(bars(), [30]), {"mandatory_predictors": ["predictor"]}
        )


def test_zero_target_is_explicit_failure_on_an_eligible_v3_row() -> None:
    reconstructed = derive(bars().with_columns(close=pl.lit(100.0)), [30])
    counts, failures, _ = target.inherited_census(
        synthetic_base([30]), reconstructed, {"mandatory_predictors": ["predictor"]}
    )
    assert counts == {"rv_15": 1, "rv_5": 1}
    assert failures["value"].to_list() == [0.0, 0.0]


def test_missing_optional_quality_flag_matches_inherited_all_true_fallback() -> None:
    base = synthetic_base([30, 60]).drop("rp4_eligible")
    spec: dict[str, Any] = {"mandatory_predictors": ["predictor"]}
    columns = target.selected_base_columns(base.schema, spec)
    assert "rp4_eligible" not in columns
    counts, _, coverage = target.inherited_census(
        base.select(columns), derive(bars(), [30, 60]), spec
    )
    assert counts == {"rv_15": 0, "rv_5": 0}
    assert coverage["eligible_v3"].to_list() == [2, 2]
