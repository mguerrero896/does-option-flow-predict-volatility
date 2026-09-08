"""Synthetic-only RP4 v2 model contracts: never load a licensed panel or target."""

from __future__ import annotations

import json
from typing import Any

import lightgbm as lgb
import numpy as np
import pytest
from artifacts.rp4_code.evaluate import equal_session_asset_mean, qlike_losses
from artifacts.rp4_v2_code.models import (
    LEAVES_GRID,
    METRIC_NAME,
    RIDGE_GRID,
    _lgb_forecast,
    _ridge_coefficient,
    _ridge_design,
    _ridge_predict,
    _SessionAssetGroups,
    _training_bounds,
    fit_lightgbm,
    fit_ridge,
)


def _sample(*, per_day: int = 30) -> dict[str, Any]:
    generator = np.random.default_rng(20260907)
    dates = np.repeat(np.arange(22), per_day)
    assets = np.tile(np.where(np.arange(per_day) % 4 == 0, "B", "A"), 22)
    design = generator.normal(size=(dates.size, 4))
    design[::5, 2] = np.nan
    design[:, 3] = 0.1
    target = np.exp(-8.0 + 0.4 * design[:, 0] + generator.normal(0, 0.05, dates.size))
    return {
        "design": design,
        "target": target,
        "train": dates < 21,
        "inner_fit": dates < 11,
        "inner_valid": (dates >= 11) & (dates < 21),
        "test": dates == 21,
        "dates": dates,
        "assets": assets,
    }


def test_grouped_mean_matches_v1_with_unequal_rows_and_missing_assets() -> None:
    generator = np.random.default_rng(91)
    sessions, assets = [], []
    for day, available_assets in enumerate(("ABCDEF", "AB", "C", "BDEF", "ACE")):
        for asset in available_assets:
            rows = int(generator.integers(1, 400))
            sessions.extend([day] * rows)
            assets.extend([asset] * rows)
    sessions_array, assets_array = np.asarray(sessions), np.asarray(assets)
    groups = _SessionAssetGroups.from_labels(sessions, assets)
    shuffled = generator.permutation(len(sessions))
    shuffled_groups = _SessionAssetGroups.from_labels(
        sessions_array[shuffled].tolist(), assets_array[shuffled].tolist()
    )
    np.testing.assert_array_equal(groups.session_asset_counts, [6, 2, 1, 4, 3])
    for _ in range(100):
        loss = generator.lognormal(0, 1, len(sessions))
        expected = equal_session_asset_mean(loss, sessions, assets)
        assert abs(groups.mean(loss) - expected) <= 1e-14
        assert abs(shuffled_groups.mean(loss[shuffled]) - expected) <= 1e-14


def test_grouped_mean_does_not_weight_by_row_count_or_fabricate_absent_assets() -> None:
    dates, assets = [1, 1, 1, 1, 2], ["A", "A", "A", "B", "A"]
    values = np.array([0.0, 0.0, 0.0, 4.0, 10.0])
    groups = _SessionAssetGroups.from_labels(dates, assets)
    # Session 1: (0 + 4)/2 = 2; session 2 has only A: 10. Final mean=6.
    assert groups.mean(values) == equal_session_asset_mean(values, dates, assets) == 6.0
    assert groups.mean(values) != values.mean()


def test_medians_scaling_and_rank_depend_only_on_training() -> None:
    train = np.array(
        [[1, np.nan, 7, 2], [2, np.nan, 7, 4], [np.nan, np.nan, 7, np.nan], [4, np.nan, 7, 8]],
        dtype=float,
    )
    predicted = np.array([[999, 55, 7, 1998], [np.nan, 88, 7, np.nan]])
    first = _ridge_design(train, predicted, [0, 1, 3])
    second = _ridge_design(train, np.full_like(predicted, 1e50), [0, 1, 3])
    assert first.record == second.record
    np.testing.assert_array_equal(first.fitted, second.fitted)
    assert first.record["medians"] == [2.0, None, 7.0, 4.0]
    assert first.record["finite_training_counts"] == [3, 0, 4, 3]
    assert first.record["presence_indices"] == [0, 1, 3]
    dropped = {entry["column"]: entry["reason"] for entry in first.record["removed_columns"]}
    assert dropped["feature:1"] == "all_missing_training"
    assert dropped["presence:1"] == "zero_variance_training"
    assert dropped["feature:2"] == "zero_variance_training"
    assert sum(value == "collinear_qr" for value in dropped.values()) == 2
    assert first.record["slope_rank"] == 2
    np.testing.assert_allclose(first.fitted[:, 1:].mean(axis=0), 0, atol=1e-15)
    np.testing.assert_allclose(first.fitted[:, 1:].std(axis=0, ddof=0), 1, atol=1e-15)
    np.testing.assert_array_equal(first.fitted[:, 0], 1)
    json.dumps(first.record, allow_nan=False)


def test_all_nonfinite_column_has_no_invented_median_or_prediction_effect() -> None:
    train = np.array([[np.nan, np.inf], [np.nan, -np.inf], [np.nan, np.nan]])
    encoded = _ridge_design(train, np.array([[9.0, 8.0], [np.nan, -1.0]]), [0, 1])
    assert encoded.record["medians"] == [None, None]
    assert encoded.record["active_columns"] == ["intercept"]
    np.testing.assert_array_equal(encoded.fitted, np.ones((3, 1)))
    np.testing.assert_array_equal(encoded.predicting, np.ones((2, 1)))
    assert len(encoded.record["removed_columns"]) == 4


def test_constant_decimal_is_zero_variance_despite_mean_roundoff() -> None:
    train = np.full((330, 2), 0.1)
    encoded = _ridge_design(train, np.array([[999.0, 0.1]]), [])
    assert encoded.record["active_columns"] == ["intercept"]
    assert all(
        row["reason"] == "zero_variance_training" for row in encoded.record["removed_columns"]
    )


def test_qr_collinearity_uses_relative_tolerance_after_scaling() -> None:
    generator = np.random.default_rng(28)
    x = generator.normal(size=120)
    tiny = generator.normal(size=120) * 1e-12
    material = generator.normal(size=120) * 1e-5
    near = _ridge_design(np.column_stack([x, x + tiny]), np.zeros((1, 2)), [])
    different_scale = _ridge_design(
        np.column_stack([x * 1e12, (x + tiny) * 1e-5]), np.zeros((1, 2)), []
    )
    independent = _ridge_design(np.column_stack([x, x + material]), np.zeros((1, 2)), [])
    assert near.record["slope_rank"] == different_scale.record["slope_rank"] == 1
    assert independent.record["slope_rank"] == 2
    assert near.record["qr_relative_tolerance"] == 1e-10


def test_ridge_uses_sum_of_squares_and_never_penalizes_intercept() -> None:
    design = np.column_stack([np.ones(4), [-1.5, -0.5, 0.5, 1.5]])
    response = np.array([-9.0, -8.0, -7.0, -6.0])
    penalty = 100.0
    coefficient = _ridge_coefficient(design.T @ design, design.T @ response, penalty)
    assert coefficient[0] == pytest.approx(response.mean())
    expected_slope = float(design[:, 1] @ response / (design[:, 1] @ design[:, 1] + penalty))
    assert coefficient[1] == pytest.approx(expected_slope)
    mean_loss_slope = float(design[:, 1] @ response / (design[:, 1] @ design[:, 1] + 4 * penalty))
    assert coefficient[1] != pytest.approx(mean_loss_slope)


def test_ridge_bounds_clip_before_exponentiating_and_count_both_limits() -> None:
    fitted = np.column_stack([np.ones(4), [-1.0, -0.5, 0.5, 1.0]])
    log_target = -8 + fitted[:, 1]
    bounds = _training_bounds(np.exp(log_target), [0.1, 10.0])
    with np.errstate(over="raise"):
        forecast, record = _ridge_predict(
            fitted, np.array([[1.0, -1e6], [1.0, 1e6]]), log_target, np.array([-8.0, 1.0]), bounds
        )
    assert forecast[0] == pytest.approx(0.1 * np.min(np.exp(log_target)))
    assert forecast[1] == pytest.approx(10 * np.max(np.exp(log_target)))
    assert record["count_low"] == record["count_high"] == 1
    assert record["log_smearing"] == pytest.approx(0, abs=1e-14)
    assert np.isfinite(forecast).all()


def test_ridge_test_targets_never_affect_fit_or_tuning() -> None:
    sample = _sample()
    original, record = fit_ridge(**sample, nullable_indices=[2], options={})
    sample["target"][sample["test"]] = np.nan
    changed, changed_record = fit_ridge(**sample, nullable_indices=[2], options={})
    np.testing.assert_array_equal(original, changed)
    assert record == changed_record
    assert record["lambda_grid"] == list(RIDGE_GRID)
    assert len(record["candidates"]) == 5
    assert record["inner_valid_sessions"] == list(range(11, 21))
    assert record["bounds"]["inner_fit"]["minimum_positive_training_target"] == pytest.approx(
        sample["target"][sample["inner_fit"]].min()
    )
    assert record["bounds"]["refit"]["maximum_positive_training_target"] == pytest.approx(
        sample["target"][sample["train"]].max()
    )
    json.dumps(record, allow_nan=False)


def test_inner_preprocessing_does_not_use_validation_rows() -> None:
    sample = _sample()
    _, original = fit_ridge(**sample, nullable_indices=[2], options={})
    sample["design"][sample["inner_valid"], 2] = 1000.0
    _, changed = fit_ridge(**sample, nullable_indices=[2], options={})
    assert original["preprocessing"]["inner_fit"] == changed["preprocessing"]["inner_fit"]
    assert original["preprocessing"]["refit"] != changed["preprocessing"]["refit"]
    assert changed["preprocessing"]["refit"]["medians"][2] > 0.5


def test_ridge_intercept_only_smearing_is_training_arithmetic_mean_and_tie_is_larger_lambda() -> (
    None
):
    sample = _sample()
    sample["design"][:] = np.nan
    forecast, record = fit_ridge(**sample, nullable_indices=[0, 1, 2, 3], options={})
    np.testing.assert_allclose(forecast, sample["target"][sample["train"]].mean(), rtol=1e-13)
    assert record["selected"]["lambda"] == 1e4
    assert record["preprocessing"]["refit"]["active_columns"] == ["intercept"]
    assert len({row["validation_qlike"] for row in record["candidates"]}) == 1


def test_ridge_selection_uses_equal_asset_and_session_qlike(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sample = _sample()
    calls: list[tuple[np.ndarray[Any, Any], np.ndarray[Any, Any], np.ndarray[Any, Any]]] = []

    def spy(values: Any, dates: Any, assets: Any) -> float:
        calls.append((values.copy(), dates.copy(), assets.copy()))
        return equal_session_asset_mean(values, dates, assets)

    monkeypatch.setattr("artifacts.rp4_v2_code.models.equal_session_asset_mean", spy)
    _, record = fit_ridge(**sample, nullable_indices=[2], options={})
    assert len(calls) == 5
    for candidate, (loss, dates, assets) in zip(record["candidates"], calls, strict=True):
        assert candidate["validation_qlike"] == equal_session_asset_mean(loss, dates, assets)
        np.testing.assert_array_equal(dates, sample["dates"][sample["inner_valid"]])
        np.testing.assert_array_equal(assets, sample["assets"][sample["inner_valid"]])


@pytest.mark.parametrize("kind", ["overlap", "future_inner", "eleven_valid_days", "invalid_target"])
def test_invalid_temporal_masks_and_training_targets_fail_before_fitting(kind: str) -> None:
    sample = _sample()
    if kind == "overlap":
        sample["inner_fit"] |= sample["inner_valid"]
    elif kind == "future_inner":
        sample["inner_fit"] |= sample["test"]
    elif kind == "eleven_valid_days":
        sample["inner_valid"] |= sample["dates"] == 10
        sample["inner_fit"] &= sample["dates"] < 10
    else:
        sample["target"][0] = 0
    with pytest.raises(ValueError, match="RP4_V2_"):
        fit_ridge(**sample, nullable_indices=[2], options={})


def test_lightgbm_actual_early_stopping_and_refit_exact_best_round() -> None:
    sample = _sample(per_day=60)
    sample["target"][:] = 0.025
    forecast, record = fit_lightgbm(**sample, options={})
    assert record["num_leaves_grid"] == list(LEAVES_GRID)
    assert record["selected"]["num_leaves"] == 15
    assert record["selected"]["rounds"] == record["refit_rounds"] == 1
    assert record["maximum_rounds"] == 2000
    assert record["early_stopping_rounds"] == 50
    assert record["num_threads"] == 4
    for candidate in record["candidates"]:
        assert candidate["rounds_evaluated"] == 51
        assert candidate["stopped_before_cap"] is True
        assert candidate["rounds"] == 1
        assert candidate["init_score_prediction_parity_abs_difference"] < 1e-12
    np.testing.assert_allclose(forecast, 0.025, rtol=1e-12)
    json.dumps(record, allow_nan=False)


def test_constant_lightgbm_inputs_exhaust_splits_without_spurious_refit_failure() -> None:
    sample = _sample(per_day=60)
    sample["design"][:] = 0.1
    sample["design"][:, 2] = np.nan
    forecast, record = fit_lightgbm(**sample, options={})
    assert record["selected"]["rounds"] == record["refit_rounds"] == 1
    for candidate in record["candidates"]:
        assert candidate["rounds"] == 1
        assert candidate["rounds_evaluated"] == 51
    np.testing.assert_allclose(forecast, sample["target"][sample["train"]].mean(), rtol=1e-12)


def test_lightgbm_grouping_is_precomputed_once_and_v1_helper_checks_candidates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sample = _sample(per_day=45)
    calls = 0

    def checked_helper(values: Any, sessions: Any, assets: Any) -> float:
        nonlocal calls
        calls += 1
        return equal_session_asset_mean(values, sessions, assets)

    monkeypatch.setattr("artifacts.rp4_v2_code.models.equal_session_asset_mean", checked_helper)
    _, record = fit_lightgbm(**sample, options={"num_boost_round": 30, "early_stopping_rounds": 10})
    assert calls == len(LEAVES_GRID)
    assert sum(row["rounds_evaluated"] for row in record["candidates"]) > calls
    for candidate in record["candidates"]:
        assert candidate["init_score_prediction_parity_abs_difference"] <= 1e-14


def test_lightgbm_callback_init_score_is_not_added_twice(monkeypatch: pytest.MonkeyPatch) -> None:
    sample = _sample(per_day=45)
    calls: list[dict[str, Any]] = []
    original_train = lgb.train

    def recording_train(params: Any, train_set: Any, **kwargs: Any) -> Any:
        seen: dict[str, Any] = {
            "params": params,
            "rows": len(train_set.label),
            "rounds_requested": kwargs["num_boost_round"],
            "has_valid": "valid_sets" in kwargs,
        }
        callbacks_seen: list[tuple[np.ndarray[Any, Any], float]] = []
        if seen["has_valid"]:
            original_metric = kwargs["feval"]

            def checked_metric(raw: Any, dataset: Any) -> tuple[str, float, bool]:
                result = original_metric(raw, dataset)
                callbacks_seen.append((raw.copy(), result[1]))
                return result

            kwargs["feval"] = checked_metric
        model = original_train(params, train_set, **kwargs)
        seen["callback_values"] = callbacks_seen
        seen["current_iteration"] = model.current_iteration()
        calls.append(seen)
        return model

    monkeypatch.setattr(lgb, "train", recording_train)
    options = {"num_boost_round": 100, "early_stopping_rounds": 10}
    _, record = fit_lightgbm(**sample, options=options)
    assert len(calls) == 4
    valid_target = sample["target"][sample["inner_valid"]]
    valid_dates = sample["dates"][sample["inner_valid"]]
    valid_assets = sample["assets"][sample["inner_valid"]]
    for call in calls[:3]:
        raw, observed_score = call["callback_values"][0]
        expected_score = equal_session_asset_mean(
            qlike_losses(valid_target, _lgb_forecast(raw)), valid_dates, valid_assets
        )
        double_init_score = equal_session_asset_mean(
            qlike_losses(valid_target, _lgb_forecast(raw + record["inner_fit_init_score"])),
            valid_dates,
            valid_assets,
        )
        assert observed_score == pytest.approx(expected_score, abs=1e-12)
        assert abs(observed_score - double_init_score) > 1.0
        assert call["rows"] == sample["inner_fit"].sum()
        assert call["rounds_requested"] == 100
        assert call["params"]["feature_pre_filter"] is False
        assert call["params"]["zero_as_missing"] is False
    assert calls[-1]["has_valid"] is False
    assert calls[-1]["rows"] == sample["train"].sum()
    assert calls[-1]["rounds_requested"] == record["selected"]["rounds"]
    assert calls[-1]["current_iteration"] == record["selected"]["rounds"]
    assert record["validation_metric"] == METRIC_NAME


def test_lightgbm_test_targets_do_not_change_tuning_and_missing_stays_native() -> None:
    sample = _sample(per_day=45)
    sample["design"][::11, 2] = np.inf
    sample["design"][:, 3] = np.nan
    options = {"num_boost_round": 60, "early_stopping_rounds": 8}
    original, record = fit_lightgbm(**sample, options=options)
    sample["target"][sample["test"]] = np.nan
    sample["design"][np.isinf(sample["design"])] = np.nan
    repeated, repeated_record = fit_lightgbm(**sample, options=options)
    np.testing.assert_array_equal(original, repeated)
    assert record == repeated_record
    assert np.isfinite(original).all() and np.all(original > 0)


def test_lgb_numeric_guards_preserve_v1_clip_and_floor() -> None:
    forecast = _lgb_forecast(np.array([-1e300, -30, 0, 30, 1e300]))
    np.testing.assert_array_equal(forecast[:2], [1e-12, 1e-12])
    assert forecast[2] == 1.0
    np.testing.assert_array_equal(forecast[3:], [np.exp(30), np.exp(30)])
