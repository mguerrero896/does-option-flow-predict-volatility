"""Synthetic-only contracts; no licensed inputs, stored targets or real fits."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import lightgbm as lgb
import numpy as np
import pandas as pd  # type: ignore[import-untyped]
import pytest
from artifacts.rp4_code.evaluate import equal_session_asset_mean
from artifacts.rp4_v2_code import models as v2
from artifacts.rp4_v3_code import models as v3
from scipy import optimize, sparse
from scipy.special import expit


def _sample(*, per_day: int = 30) -> dict[str, Any]:
    generator = np.random.default_rng(20260907)
    day = np.repeat(np.arange(22), per_day)
    # Match pandas string-column .to_numpy() used by the actual runner.
    dates = np.asarray([f"2024-01-{value + 1:02d}" for value in day], dtype=object)
    assets = np.tile(np.where(np.arange(per_day) % 4 == 0, "B", "A"), 22)
    design = generator.normal(size=(len(day), 4))
    design[::5, 2] = np.nan
    design[:, 3] = 0.1
    target = np.exp(-8.0 + 0.4 * design[:, 0] + generator.normal(0, 0.3, len(day)))
    return {
        "design": design,
        "target": target,
        "train": day < 21,
        "inner_fit": day < 11,
        "inner_valid": (day >= 11) & (day < 21),
        "test": day == 21,
        "dates": dates,
        "assets": assets,
    }


def _tree_options() -> dict[str, Any]:
    # Small deterministic fixture cap, never the settings of a real evaluation.
    return {
        "num_leaves": [3, 7],
        "num_boost_round": 40,
        "early_stopping_rounds": 5,
        "min_data_in_leaf": 10,
        "num_threads": 1,
    }


def _jump_sample() -> dict[str, Any]:
    sample = _sample()
    generator = np.random.default_rng(604)
    sample["target"] = (
        generator.random(len(sample["target"])) < expit(sample["design"][:, 0])
    ).astype(float)
    return sample


def _mz_inputs() -> dict[str, Any]:
    dates, assets, forecast = [], [], []
    for day in range(10):
        # Unequal row counts and intentionally absent B on alternating days.
        for asset, rows in (("A", day + 1), ("B", 2 * (day % 2))):
            dates.extend([f"2024-02-{day + 1:02d}"] * rows)
            assets.extend([asset] * rows)
            forecast.extend([float(day + 1 + (asset == "B"))] * rows)
    return {
        "validation_forecast": np.asarray(forecast),
        "validation_target": 2.0 + 3.0 * np.asarray(forecast),
        "dates": np.asarray(dates),
        "assets": np.asarray(assets),
        "forecast": np.array([0.5, 2.0, 7.0]),
        "inner_fit_last_session": "2024-01-31",
        "selected_num_leaves": 15,
        "selected_rounds": 4,
    }


def test_train_only_medians_scaling_and_missing_columns() -> None:
    train = np.array(
        [[1, np.nan, 7, 2], [2, np.nan, 7, 4], [np.nan, np.nan, 7, np.nan], [4, np.nan, 7, 8]],
        dtype=float,
    )
    original = train.copy()
    first = v3._ridge_design(train, np.array([[999, 55, 7, 1998]]), [0, 1, 3])
    second = v3._ridge_design(train, np.full((1, 4), -1e50), [0, 1, 3])
    np.testing.assert_array_equal(train, original)
    np.testing.assert_array_equal(first.fitted, second.fitted)
    for key in ("medians", "centers", "scales_population_sd", "active_columns", "removed_columns"):
        assert first.record[key] == second.record[key]
    assert first.record["medians"] == [2.0, None, 7.0, 4.0]
    dropped = {row["column"]: row["reason"] for row in first.record["removed_columns"]}
    assert dropped["feature:1"] == "all_missing_training"
    assert dropped["presence:1"] == "zero_variance_training"
    assert dropped["feature:2"] == "zero_variance_training"
    assert first.record["presence_indices"] == [0, 1, 3]
    json.dumps(first.record, allow_nan=False)


def test_all_missing_columns_do_not_invent_medians() -> None:
    fitted = v3._ridge_design(np.full((20, 2), np.nan), np.array([[1.0, -9.0]]), [0, 1])
    assert fitted.record["medians"] == [None, None]
    assert fitted.record["active_columns"] == ["intercept"]
    np.testing.assert_array_equal(fitted.fitted, np.ones((20, 1)))
    np.testing.assert_array_equal(fitted.predicting, np.ones((1, 1)))


def test_winsorization_uses_preclip_stats_without_recentering() -> None:
    train = np.zeros((400, 1))
    train[-1, 0] = 100.0
    predicted = np.array([[-1e20], [1e20], [0.0]])
    encoded = v3._ridge_design(train, predicted, [])
    raw_z = (train[:, 0] - train[:, 0].mean()) / train[:, 0].std(ddof=0)
    np.testing.assert_array_equal(encoded.fitted[:, 1], np.clip(raw_z, -5, 5))
    np.testing.assert_array_equal(encoded.predicting[:2, 1], [-5, 5])
    assert abs(encoded.fitted[:, 1].mean()) > 0.01
    assert encoded.record["restandardized_after_winsorization"] is False
    assert encoded.record["winsorization"]["training"] == [
        {"column": "feature:0", "count_low": 0, "count_high": 1}
    ]
    assert encoded.record["winsorization"]["predicting"] == [
        {"column": "feature:0", "count_low": 1, "count_high": 1}
    ]
    np.testing.assert_array_equal(encoded.fitted[:, 0], 1)


def test_rank_after_winsorization_includes_intercept() -> None:
    # Clipping destroys zero-mean slopes. QR(slopes) alone would retain three
    # slopes here although the intercept plus one-hot design has rank only 3.
    categories = np.r_[0, 1, np.full(398, 2)]
    train = np.eye(3)[categories]
    encoded = v3._ridge_design(train, train[:3], [])
    assert encoded.record["design_rank_including_intercept"] == 3
    assert encoded.record["slope_rank"] == 2
    assert encoded.fitted.shape == (400, 3)
    assert np.linalg.matrix_rank(encoded.fitted) == 3
    assert encoded.record["qr_intercept_projection_for_rank_only"] is True
    assert any(row["reason"] == "collinear_qr" for row in encoded.record["removed_columns"])


def test_percentiles_linear_interpolation_and_inclusive_bound_counts() -> None:
    target = np.array([1.0, 2.0, 3.0, 100.0])
    bounds = v3._training_bounds(target)
    assert bounds["percentile_1"] == pytest.approx(1.03)
    assert bounds["percentile_99"] == pytest.approx(97.09)
    assert bounds["lower"] == 0.5 * bounds["percentile_1"]
    assert bounds["upper"] == 2 * bounds["percentile_99"]
    values = np.array([-1e300, bounds["log_lower"], 0.0, bounds["log_upper"], 1e300])
    prediction, record = v3._quantile_predict(values[:, None], np.ones(1), bounds)
    assert record["count_low"] == record["count_high"] == 2
    assert np.isfinite(prediction).all()
    np.testing.assert_array_equal(prediction[:2], bounds["lower"])
    np.testing.assert_allclose(prediction[-2:], bounds["upper"], rtol=4e-16)
    assert np.all((prediction >= bounds["lower"]) & (prediction <= bounds["upper"]))
    assert record["smearing"] is False


def test_ridge_future_targets_and_distribution_do_not_fit_parameters() -> None:
    sample = _sample()
    _, first = v3.fit_ridge(**sample, nullable_indices=[2], options={})
    altered = copy.deepcopy(sample)
    altered["target"][altered["test"]] = np.nan
    altered["design"][altered["test"]] = 1e100
    _, second = v3.fit_ridge(**altered, nullable_indices=[2], options={})
    assert first["coefficients"] == second["coefficients"]
    assert first["selected"] == second["selected"]
    assert first["bounds"] == second["bounds"]
    assert first["preprocessing"]["inner_fit"] == second["preprocessing"]["inner_fit"]
    for key in ("medians", "centers", "scales_population_sd", "active_columns"):
        assert first["preprocessing"]["refit"][key] == second["preprocessing"]["refit"][key]
    changed_validation = copy.deepcopy(sample)
    changed_validation["target"][sample["inner_valid"]] *= 20
    changed_validation["design"][sample["inner_valid"]] *= 100
    _, third = v3.fit_ridge(**changed_validation, nullable_indices=[2], options={})
    assert first["bounds"]["inner_fit"] == third["bounds"]["inner_fit"]
    for key in ("medians", "centers", "scales_population_sd", "active_columns"):
        assert first["preprocessing"]["inner_fit"][key] == third["preprocessing"]["inner_fit"][key]


def test_mz_uses_equal_assets_and_ten_causal_session_means() -> None:
    inputs = _mz_inputs()
    result = v3.mz_secondary(**inputs)
    calibration = result["calibration"]
    np.testing.assert_allclose(result["forecast"], 2 + 3 * inputs["forecast"], atol=1e-13)
    assert calibration["applied_coefficients"]["intercept"] == pytest.approx(2)
    assert calibration["applied_coefficients"]["slope"] == pytest.approx(3)
    assert calibration["N_sessions"] == 10
    assert calibration["rank"] == 2
    for day, mean in zip(
        calibration["calibration_sessions"], calibration["session_target_means"], strict=True
    ):
        mask = inputs["dates"] == day
        expected = equal_session_asset_mean(
            inputs["validation_target"][mask],
            inputs["dates"][mask].tolist(),
            inputs["assets"][mask].tolist(),
        )
        assert mean == pytest.approx(expected)
    assert (
        calibration["forecast_provenance"]
        == "selected_inner_fit_candidate_before_last_ten_sessions"
    )
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("defect", ["nine_sessions", "rank_one", "invalid_pair"])
def test_mz_training_degenerate_identity_is_separate_from_origin_fallback(defect: str) -> None:
    inputs = _mz_inputs()
    if defect == "nine_sessions":
        keep = inputs["dates"] != "2024-02-10"
        for key in ("validation_forecast", "validation_target", "dates", "assets"):
            inputs[key] = inputs[key][keep]
    elif defect == "rank_one":
        inputs["validation_forecast"][:] = 2.0
    else:
        inputs["validation_target"][0] = np.nan
    result = v3.mz_secondary(**inputs)
    np.testing.assert_array_equal(result["forecast"], inputs["forecast"])
    assert result["calibration"]["training_identity_fallback"] is True
    assert result["calibration"]["origin_identity_fallback_count"] == 0
    json.dumps(result, allow_nan=False)


def test_mz_finite_adverse_slope_is_not_discarded() -> None:
    inputs = _mz_inputs()
    inputs["validation_target"] = 20.0 - inputs["validation_forecast"]
    inputs["forecast"] = np.array([2.0, 30.0])
    result = v3.mz_secondary(**inputs)
    np.testing.assert_allclose(result["forecast"], [18.0, 1e-12])
    assert result["calibration"]["training_identity_fallback"] is False
    assert result["calibration"]["origin_identity_fallback_count"] == 0
    assert result["calibration"]["count_floor"] == 1


def test_mz_later_numeric_failure_is_local_and_does_not_change_previous_origins() -> None:
    inputs = _mz_inputs()
    inputs["validation_target"] = 1e5 * inputs["validation_forecast"]
    inputs["forecast"] = np.array([1.0, 2.0])
    first = v3.mz_secondary(**inputs)
    inputs["forecast"] = np.array([1.0, 2.0, 1e307])
    second = v3.mz_secondary(**inputs)
    np.testing.assert_array_equal(second["forecast"][:2], first["forecast"])
    assert second["forecast"][-1] == 1e307
    assert second["calibration"]["training_identity_fallback"] is False
    assert second["calibration"]["origin_identity_fallback_count"] == 1
    json.dumps(second, allow_nan=False)


def test_mz_rejects_noncausal_validation() -> None:
    inputs = _mz_inputs()
    inputs["inner_fit_last_session"] = "2024-02-01"
    with pytest.raises(ValueError, match="NONCAUSAL"):
        v3.mz_secondary(**inputs)


@pytest.mark.parametrize("failure", ["scale_overflow", "lstsq_failure"])
def test_mz_training_numeric_degeneracy_preserves_serializable_identity(
    failure: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    inputs = _mz_inputs()
    if failure == "scale_overflow":
        # One row in each session: finite pairs, overflowing sum in mean scale.
        inputs["dates"] = np.asarray([f"2024-02-{day + 1:02d}" for day in range(10)])
        inputs["assets"] = np.full(10, "A")
        inputs["validation_target"] = np.full(10, 1e308)
        inputs["validation_forecast"] = np.arange(1.0, 11.0)
    else:

        def broken_svd(*args: Any, **kwargs: Any) -> None:
            raise np.linalg.LinAlgError("synthetic training SVD failure")

        monkeypatch.setattr(np.linalg, "lstsq", broken_svd)
    result = v3.mz_secondary(**inputs)
    np.testing.assert_array_equal(result["forecast"], inputs["forecast"])
    assert result["calibration"]["training_identity_fallback"] is True
    assert result["calibration"]["origin_identity_fallback_count"] == 0
    json.dumps(result, allow_nan=False)


def test_primary_lightgbm_is_bitwise_v2_and_mz_uses_selected_inner_candidate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sample = _sample()
    options = _tree_options()
    expected, expected_record = v2.fit_lightgbm(**sample, options=options, threads=1)
    original_train = lgb.train
    trained = []

    def capture(*args: Any, **kwargs: Any) -> Any:
        result = original_train(*args, **kwargs)
        trained.append(result)
        return result

    monkeypatch.setattr(lgb, "train", capture)
    actual, record = v3.fit_lightgbm(**sample, options=options, threads=1)
    np.testing.assert_array_equal(actual, expected)
    assert {key: value for key, value in record.items() if key != "mz_secondary"} == expected_record
    selected = record["selected"]
    selected_index = options["num_leaves"].index(selected["num_leaves"])
    inner_prediction = record["inner_fit_init_score"] + trained[selected_index].predict(
        sample["design"][sample["inner_valid"]],
        raw_score=True,
        num_iteration=selected["rounds"],
        num_threads=1,
    )
    recalibration = v3.mz_secondary(
        v2._lgb_forecast(inner_prediction),
        sample["target"][sample["inner_valid"]],
        sample["dates"][sample["inner_valid"]],
        sample["assets"][sample["inner_valid"]],
        actual,
        inner_fit_last_session=str(np.max(sample["dates"][sample["inner_fit"]])),
        selected_num_leaves=selected["num_leaves"],
        selected_rounds=selected["rounds"],
    )
    assert recalibration == record["mz_secondary"]
    # The final refit includes validation labels and must not feed MZ.
    refit_prediction = record["init_score"] + trained[-1].predict(
        sample["design"][sample["inner_valid"]],
        raw_score=True,
        num_threads=1,
    )
    assert not np.array_equal(inner_prediction, refit_prediction)
    json.dumps(record, allow_nan=False)


def test_admm_true_pinball_agrees_with_independent_linear_program_when_penalty_irrelevant() -> None:
    response = np.linspace(-4.0, 2.0, 39) ** 3
    fitted = np.ones((len(response), 1))
    coefficient, diagnostics, _ = v3._quantile_admm(fitted, response, 10000.0, {})
    # Independent LP: unpenalized intercept, nonnegative positive/negative residual.
    rows = len(response)
    matrix = sparse.hstack([fitted, sparse.eye(rows), -sparse.eye(rows)]).tocsr()
    result = optimize.linprog(
        np.r_[0.0, np.full(rows, 0.9), np.full(rows, 0.1)],
        A_eq=matrix,
        b_eq=response,
        bounds=[(None, None)] + [(0.0, None)] * (2 * rows),
        method="highs",
    )
    assert result.success
    assert diagnostics["objective_total_sum_scale"] == pytest.approx(result.fun, abs=0.002)
    assert abs(coefficient[0] - result.x[0]) < 0.03
    assert diagnostics["converged"] is True
    assert diagnostics["primal_residual_norm"] <= diagnostics["primal_tolerance"]
    assert diagnostics["dual_residual_norm_objective_over_n"] <= diagnostics["dual_tolerance"]


def test_admm_exact_l2_objective_matches_independent_convex_qp() -> None:
    generator = np.random.default_rng(1234)
    fitted = np.column_stack([np.ones(25), generator.normal(size=(25, 2))])
    response = generator.normal(size=25) + fitted[:, 1]
    penalty = 0.75
    coefficient, diagnostics, _ = v3._quantile_admm(fitted, response, penalty, {})
    # SLSQP's smooth slack QP independently verifies the SUM, penalty and sign.
    rows, width = fitted.shape
    start = np.r_[np.zeros(width), np.maximum(response, 0), np.maximum(-response, 0)]
    matrix = np.column_stack([fitted, np.eye(rows), -np.eye(rows)])

    def objective(values: np.ndarray[Any, Any]) -> tuple[float, np.ndarray[Any, Any]]:
        loss = 0.9 * values[width : width + rows].sum() + 0.1 * values[width + rows :].sum()
        total = loss + penalty * np.square(values[1:width]).sum()
        gradient = np.r_[0.0, 2 * penalty * values[1:width], np.full(rows, 0.9), np.full(rows, 0.1)]
        return float(total), gradient

    result = optimize.minimize(
        objective,
        start,
        jac=True,
        method="SLSQP",
        bounds=[(None, None)] * width + [(0.0, None)] * (2 * rows),
        constraints=[optimize.LinearConstraint(matrix, response, response)],
        options={"maxiter": 500, "ftol": 1e-10},
    )
    assert result.success
    assert diagnostics["objective_total_sum_scale"] == pytest.approx(result.fun, abs=0.005)
    assert diagnostics["objective_l2_penalty"] == penalty * np.square(coefficient[1:]).sum()
    assert diagnostics["intercept_penalized"] is False


def test_admm_nonconvergence_has_diagnostics_and_no_forecast() -> None:
    generator = np.random.default_rng(707)
    fitted = np.column_stack([np.ones(100), generator.normal(size=(100, 4))])
    with pytest.raises(v3.ModelConvergenceError, match="QUANTILE_ADMM_NOT_CONVERGED") as caught:
        v3._quantile_admm(fitted, generator.normal(size=100), 1.0, {"maxiter": 1})
    assert caught.value.diagnostics["converged"] is False
    assert caught.value.diagnostics["iterations"] == 1
    json.dumps(caught.value.diagnostics, allow_nan=False)


def test_quantile_is_not_a_mean_relabel_and_refit_is_cold() -> None:
    sample = _sample()
    sample["design"][:] = 1.0
    generator = np.random.default_rng(912)
    sample["target"] = np.exp(-6.0 + generator.exponential(size=len(sample["target"])))
    prediction, record = v3.fit_quantile(**sample, nullable_indices=[], options={})
    expected_log = np.quantile(np.log(sample["target"][sample["train"]]), 0.9, method="linear")
    np.testing.assert_allclose(np.log(prediction), expected_log, atol=0.03)
    assert abs(np.log(prediction[0]) - np.log(sample["target"][sample["train"]]).mean()) > 0.8
    assert record["smearing"] is False
    assert record["solver_refit"]["warm_started_same_training_design"] is False
    assert record["lambda_solve_order"] == [10000.0, 100.0, 1.0, 0.01, 0.0001]
    by_lambda = {row["lambda"]: row for row in record["candidates"]}
    assert by_lambda[10000.0]["solver"]["warm_started_same_training_design"] is False
    assert all(
        by_lambda[value]["solver"]["warm_started_same_training_design"]
        for value in [100, 1, 0.01, 0.0001]
    )
    json.dumps(record, allow_nan=False)


@pytest.mark.parametrize("endpoint", ["quantile", "jump"])
def test_linear_tail_future_target_is_unread(endpoint: str) -> None:
    sample = _sample() if endpoint == "quantile" else _jump_sample()
    fit = v3.fit_quantile if endpoint == "quantile" else v3.fit_jump
    first, first_record = fit(**sample, nullable_indices=[2], options={"lambda_grid": [1, 100]})
    altered = copy.deepcopy(sample)
    altered["target"][altered["test"]] = np.nan
    second, second_record = fit(**altered, nullable_indices=[2], options={"lambda_grid": [1, 100]})
    np.testing.assert_array_equal(first, second)
    assert first_record == second_record
    json.dumps(first_record, allow_nan=False)


def test_logistic_objective_gradient_intercept_and_nonconvergence() -> None:
    generator = np.random.default_rng(610)
    fitted = np.column_stack([np.ones(300), generator.normal(size=(300, 3))])
    target = (generator.random(300) < expit(-0.8 + fitted[:, 1])).astype(float)
    coefficient, record = v3._logistic_coefficient(fitted, target, 2.0, {})
    probability = expit(fitted @ coefficient)
    expected = v3._binary_loss(target, probability).sum() + 2 * np.square(coefficient[1:]).sum()
    assert record["objective_total_sum_scale"] == pytest.approx(expected, abs=1e-10)
    gradient = fitted.T @ (probability - target) + 4 * np.r_[0.0, coefficient[1:]]
    assert np.max(np.abs(gradient / 300)) < 1e-6
    with pytest.raises(v3.ModelConvergenceError, match="LOGISTIC_NOT_CONVERGED"):
        v3._logistic_coefficient(fitted, target, 2.0, {"maxiter": 1})


@pytest.mark.parametrize("family", ["linear", "lightgbm"])
@pytest.mark.parametrize("value", [0.0, 1.0])
def test_jump_single_class_uses_empirical_frequency_without_fabricated_class(
    family: str, value: float, monkeypatch: pytest.MonkeyPatch
) -> None:
    sample = _jump_sample()
    sample["target"][:] = value
    sample["target"][sample["test"]] = np.nan

    def forbidden(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("A single-class fit must not invent a second class for LightGBM")

    monkeypatch.setattr(lgb, "train", forbidden)
    options = _tree_options() if family == "lightgbm" else {}
    prediction, record = v3.fit_jump(
        **sample, nullable_indices=[2], options=options, family=family, threads=1
    )
    expected = np.clip(value, 1e-12, 1 - 1e-12)
    np.testing.assert_allclose(prediction, expected, atol=1e-25)
    if family == "linear":
        assert record["solver_refit"]["single_class_training"] is True
        assert record["selected"]["lambda"] == 10000
    else:
        assert record["single_class_refit"] is True
        assert record["refit_rounds"] == 0
    assert record["class_weights"] is None
    json.dumps(record, allow_nan=False)


@pytest.mark.parametrize("endpoint", ["quantile", "jump"])
def test_native_tail_objectives_early_stopping_and_init_score_parity(endpoint: str) -> None:
    sample = _sample() if endpoint == "quantile" else _jump_sample()
    fit = v3.fit_quantile if endpoint == "quantile" else v3.fit_jump
    options = _tree_options()
    prediction, record = fit(
        **sample, nullable_indices=[2], options=options, family="lightgbm", threads=1
    )
    assert prediction.shape == (sample["test"].sum(),)
    assert np.isfinite(prediction).all()
    assert record["objective"] == ("quantile" if endpoint == "quantile" else "binary")
    assert record["refit_rounds"] == record["selected"]["rounds"]
    for candidate in record["candidates"]:
        assert candidate["init_score_prediction_parity_abs_difference"] < 1e-12
        assert candidate["rounds"] == np.argmin(candidate["validation_score_by_round"]) + 1
        assert candidate["rounds_evaluated"] <= 40
        assert candidate["rounds_evaluated"] <= candidate["rounds"] + 5
    if endpoint == "quantile":
        assert record["forecast_log_clip"] == [-30, 30]
        assert "bounds" not in record
        assert record["smearing"] is False
    else:
        assert np.all((prediction >= 1e-12) & (prediction <= 1 - 1e-12))
    altered = copy.deepcopy(sample)
    altered["target"][altered["test"]] = np.nan
    second, second_record = fit(
        **altered, nullable_indices=[2], options=options, family="lightgbm", threads=1
    )
    np.testing.assert_array_equal(prediction, second)
    assert record == second_record
    json.dumps(record, allow_nan=False)


@pytest.mark.parametrize("endpoint", ["mean", "quantile", "jump"])
def test_native_constant_inputs_are_not_an_artificial_round_count_failure(endpoint: str) -> None:
    sample = _jump_sample() if endpoint == "jump" else _sample()
    sample["design"][:] = 1.0
    if endpoint == "mean":
        prediction, record = v3.fit_lightgbm(**sample, options=_tree_options(), threads=1)
    else:
        fit = v3.fit_quantile if endpoint == "quantile" else v3.fit_jump
        prediction, record = fit(
            **sample, nullable_indices=[], options=_tree_options(), family="lightgbm", threads=1
        )
    assert np.isfinite(prediction).all()
    assert record["refit_rounds"] == record["selected"]["rounds"] == 1


def test_lightgbm_quantile_log_clip_has_no_primary_variance_floor() -> None:
    sample = _sample()
    sample["design"][:] = 1.0
    sample["target"][:] = np.exp(-29.0)
    prediction, record = v3.fit_quantile(
        **sample, nullable_indices=[], options=_tree_options(), family="lightgbm", threads=1
    )
    np.testing.assert_array_equal(prediction, np.exp(-29.0))
    assert np.all(prediction < 1e-12)
    assert record["forecast_log_clip"] == [-30, 30]
    assert record["variance_floor"] is None
    assert all(row["validation_score"] == 0.0 for row in record["candidates"])


@pytest.mark.parametrize("invalid", [-1.0, 0.5, np.nan, np.inf])
def test_jump_training_target_is_strictly_binary(invalid: float) -> None:
    sample = _jump_sample()
    sample["target"][0] = invalid
    with pytest.raises(ValueError, match="TRAINING_JUMP_TARGET_NOT_BINARY"):
        v3.fit_jump(**sample, nullable_indices=[2], options={})


@pytest.mark.parametrize("failure", ["convergence", "programming"])
def test_runner_convergence_is_endpoint_local_and_completed_fits_are_not_repeated(
    failure: str, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # The runner is integration-tested only through deterministic test doubles.
    # No model call, licensed input, or stored evaluation is made here.
    from artifacts.rp4_v3_code import evaluate_v3 as runner
    from artifacts.rp4_v3_code.freeze import FEATURES

    sample = _sample(per_day=2)
    origin_minute = np.tile([60, 65], 22)
    panel = pd.DataFrame(
        {
            "asset": sample["assets"],
            "session_date": sample["dates"],
            "origin_minute": origin_minute,
            "rv30": sample["target"],
            "jump30": np.zeros(len(origin_minute)),
            FEATURES[1]: np.ones(len(origin_minute)),
        }
    )
    origins_ns = (
        pd.to_datetime(sample["dates"], utc=True).as_unit("ns").asi8
        + origin_minute * 60 * 1_000_000_000
    )
    end_ns = origins_ns + 30 * 60 * 1_000_000_000
    spec = {
        "embargo_minutes": 60,
        "missing_allowed": [],
        "feature_sets": dict.fromkeys(["B0", "B1", "B2"], ["f0", "f1", "f2", "f3"]),
        "model": {"tuning_sessions": 10, "ridge": {}, "lightgbm": {}},
    }
    calls = {"mean": 0, "quantile": 0, "jump": 0}

    def mean(*args: Any, **kwargs: Any) -> tuple[Any, dict[str, Any]]:
        calls["mean"] += 1
        prediction = np.full(int(args[5].sum()), 0.01)
        return prediction, {"mz_secondary": {"forecast": prediction.tolist(), "calibration": {}}}

    def quantile(*args: Any, **kwargs: Any) -> tuple[Any, dict[str, Any]]:
        calls["quantile"] += 1
        if failure == "programming":
            raise ValueError("SYNTHETIC_UNEXPECTED_PROGRAMMING_DEFECT")
        raise v3.ModelConvergenceError("QUANTILE_ADMM", {"converged": False, "iterations": 1})

    def jump(*args: Any, **kwargs: Any) -> tuple[Any, dict[str, Any]]:
        calls["jump"] += 1
        return np.full(int(args[5].sum()), 0.5), {"synthetic_test_double": True}

    monkeypatch.setattr(runner, "fit_ridge", mean)
    monkeypatch.setattr(runner, "fit_lightgbm", mean)
    monkeypatch.setattr(runner, "fit_quantile", quantile)
    monkeypatch.setattr(runner, "fit_jump", jump)
    monkeypatch.setattr(runner, "tail_options", lambda *_args: {})
    matrices = dict.fromkeys(["B0", "B1", "B2"], sample["design"])
    arguments = (
        tmp_path,
        "2024-01-22",
        {"synthetic_pin": 1},
        panel,
        spec,
        matrices,
        matrices,
        sample["dates"],
        sample["assets"],
        origins_ns,
        end_ns,
        np.ones(len(panel), dtype=bool),
        np.ones(len(panel), dtype=bool),
        1,
    )
    if failure == "programming":
        with pytest.raises(ValueError, match="SYNTHETIC_UNEXPECTED_PROGRAMMING_DEFECT"):
            runner.fit_session(*arguments)
        assert calls == {"mean": 6, "quantile": 1, "jump": 0}
        return
    first = runner.fit_session(*arguments)
    assert first["tail_status"]["quantile"]["status"] == "NO VERIFICABLE"
    assert first["tail_forecasts"]["quantile"] == {}
    assert first["tail_status"]["jump"]["status"] == "COMPUTED"
    assert all(len(value) == 3 for value in first["forecasts"].values())
    assert calls == {"mean": 6, "quantile": 1, "jump": 6}
    second = runner.fit_session(*arguments)
    assert second == first
    assert calls["mean"] == calls["jump"] == 6
    json.dumps(first, allow_nan=False)
