"""RP4 v3 train-only estimators; data access and evaluation belong to the runner.

Linear inputs are already transformed pointwise by the caller. Frozen v2 helpers
are reused without mutation; all changed transforms and new estimators live here.
No target outside the training mask is used by model selection or calibration.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import numpy.typing as npt
from artifacts.rp4_code.evaluate import Array, Mask, equal_session_asset_mean
from artifacts.rp4_v2_code.models import (
    LEAVES_GRID,
    METRIC_NAME,
    QR_RELATIVE_TOLERANCE,
    RIDGE_GRID,
    _lgb_forecast,
    _ridge_coefficient,
    _ridge_predict,
    _RidgeDesign,
    _SessionAssetGroups,
    _validate_inputs,
)
from scipy import linalg
from scipy.optimize import minimize
from scipy.special import expit

from mds650.metrics import qlike_losses
from mds650.rp2.qlike_objective import lightgbm_objective

QUANTILE_LEVEL = 0.90
PROBABILITY_FLOOR = 1e-12


def _training_bounds(target: Array, factors: Sequence[float] = (0.5, 2.0)) -> dict[str, float]:
    if tuple(factors) != (0.5, 2.0):
        raise ValueError("RP4_V3_PERCENTILE_BOUND_FACTORS_DRIFT")
    if target.ndim != 1 or not len(target) or not np.isfinite(target).all() or np.any(target <= 0):
        raise ValueError("RP4_V3_BOUND_TARGET_NOT_POSITIVE_FINITE")
    p1, p99 = np.quantile(target, [0.01, 0.99], method="linear")
    lower, upper = float(0.5 * p1), float(2.0 * p99)
    if not 0 < lower <= upper < math.inf:
        raise ValueError("RP4_V3_PERCENTILE_BOUNDS_NOT_REPRESENTABLE")
    return {
        "training_rows": len(target),
        "percentile_1": float(p1),
        "percentile_99": float(p99),
        "lower": lower,
        "upper": upper,
        "log_lower": math.log(lower),
        "log_upper": math.log(upper),
    }


def _penalties(options: Mapping[str, Any]) -> tuple[float, ...]:
    result = tuple(float(value) for value in options.get("lambda_grid", RIDGE_GRID))
    if (
        not result
        or len(set(result)) != len(result)
        or any(not math.isfinite(x) or x <= 0 for x in result)
    ):
        raise ValueError("RP4_V3_PENALTY_GRID_INVALID")
    return result


def _session_means(values: Array, dates: npt.NDArray[Any], assets: npt.NDArray[Any]) -> Array:
    groups = _SessionAssetGroups.from_labels(dates.tolist(), assets.tolist())
    pair_means = np.bincount(groups.row_groups, weights=values) / groups.group_counts
    return np.asarray(
        np.bincount(groups.group_sessions, weights=pair_means) / groups.session_asset_counts
    )


def mz_secondary(
    validation_forecast: Array,
    validation_target: Array,
    dates: npt.NDArray[Any],
    assets: npt.NDArray[Any],
    forecast: Array,
    *,
    inner_fit_last_session: str,
    selected_num_leaves: int,
    selected_rounds: int,
) -> dict[str, Any]:
    """Fit MZ on previous-validation means, never on final-refit in-sample predictions."""
    if (
        validation_forecast.shape != validation_target.shape
        or dates.shape != validation_target.shape
        or assets.shape != dates.shape
    ):
        raise ValueError("RP4_V3_MZ_VALIDATION_SHAPE_MISMATCH")
    if forecast.ndim != 1 or not np.isfinite(forecast).all() or np.any(forecast <= 0):
        raise ValueError("RP4_V3_MZ_PRIMARY_FORECAST_INVALID")
    days = np.unique(dates).tolist()
    if days and inner_fit_last_session >= str(days[0]):
        raise ValueError("RP4_V3_MZ_NONCAUSAL_VALIDATION_PROVENANCE")
    observed = _session_means(validation_target, dates, assets) if len(dates) else np.empty(0)
    predicted = _session_means(validation_forecast, dates, assets) if len(dates) else np.empty(0)
    valid = np.isfinite(observed) & np.isfinite(predicted) & (observed > 0) & (predicted > 0)
    rank = 0
    reason = None
    attempted: dict[str, float | None] = {"intercept": None, "slope": None}
    scale: float | None = None
    if len(days) != 10 or int(valid.sum()) != 10:
        reason = "not_ten_valid_session_pairs"
    else:
        with np.errstate(over="ignore", invalid="ignore"):
            scale_value = float(observed.mean())
        if not math.isfinite(scale_value) or scale_value <= 0:
            reason = "nonfinite_target_scale"
        else:
            scale = scale_value
            with np.errstate(over="ignore", invalid="ignore"):
                design = np.column_stack([np.ones(10), predicted / scale])
            if not np.isfinite(design).all():
                reason = "nonfinite_scaled_design"
            else:
                try:
                    coefficient, _, rank_value, _ = np.linalg.lstsq(
                        design, observed / scale, rcond=1e-10
                    )
                    rank = int(rank_value)
                    with np.errstate(over="ignore", invalid="ignore"):
                        candidate_intercept = float(coefficient[0] * scale)
                    candidate_slope = float(coefficient[1])
                    attempted = {
                        "intercept": candidate_intercept
                        if math.isfinite(candidate_intercept)
                        else None,
                        "slope": candidate_slope if math.isfinite(candidate_slope) else None,
                    }
                    if rank < 2:
                        reason = "rank_below_two"
                    elif attempted["intercept"] is None or attempted["slope"] is None:
                        reason = "nonfinite_coefficients"
                except np.linalg.LinAlgError:
                    reason = "training_lstsq_numeric_failure"
    intercept, slope = 0.0, 1.0
    if reason is None:
        accepted_intercept, accepted_slope = attempted["intercept"], attempted["slope"]
        if accepted_intercept is None or accepted_slope is None:
            raise ValueError("RP4_V3_MZ_FINITE_COEFFICIENT_STATE_INVALID")
        intercept, slope = accepted_intercept, accepted_slope
    with np.errstate(over="ignore", invalid="ignore"):
        raw = intercept + slope * forecast
    local_fallback = ~np.isfinite(raw)
    applied = np.where(local_fallback, forecast, raw)
    count_floor = int(np.count_nonzero(applied <= PROBABILITY_FLOOR))
    applied = np.maximum(applied, PROBABILITY_FLOOR)
    return {
        "forecast": applied.tolist(),
        "calibration": {
            "method": "OLS_levels_equal_asset_session_means_rcond_1e-10",
            "forecast_provenance": "selected_inner_fit_candidate_before_last_ten_sessions",
            "inner_fit_last_session": inner_fit_last_session,
            "calibration_sessions": days,
            "N_sessions": len(days),
            "N_valid_pairs": int(valid.sum()),
            "selected_num_leaves": selected_num_leaves,
            "selected_rounds": selected_rounds,
            "target_scale": scale,
            "rank": rank,
            "attempted_coefficients": attempted,
            "applied_coefficients": {"intercept": intercept, "slope": slope},
            "training_identity_fallback": reason is not None,
            "training_fallback_reason": reason,
            "origin_identity_fallback_count": int(local_fallback.sum()),
            "origin_fallback_reason": "nonfinite_calibrated_origin"
            if local_fallback.any()
            else None,
            "floor": PROBABILITY_FLOOR,
            "count_floor": count_floor,
            "prediction_rows": len(forecast),
            "session_target_means": [float(x) if math.isfinite(x) else None for x in observed],
            "session_forecast_means": [float(x) if math.isfinite(x) else None for x in predicted],
        },
    }


def _ridge_design(
    training: Array,
    predicting: Array,
    nullable_indices: Sequence[int],
    *,
    qr_relative_tolerance: float = QR_RELATIVE_TOLERANCE,
) -> _RidgeDesign:
    """Median, population scaling and rank decisions use training rows only.

    Presence indicators are generated even for optional columns that are absent
    throughout training; their zero variance then makes them unidentifiable. Such
    a raw column has no median and is never encoded with a fabricated one.
    """
    if (
        training.ndim != 2
        or predicting.ndim != 2
        or training.shape[1] != predicting.shape[1]
        or len(training) == 0
    ):
        raise ValueError("RP4_V3_RIDGE_DESIGN_SHAPE_INVALID")
    width = training.shape[1]
    optional = tuple(int(value) for value in nullable_indices)
    if len(set(optional)) != len(optional) or any(
        value < 0 or value >= width for value in optional
    ):
        raise ValueError("RP4_V3_NULLABLE_INDICES_INVALID")
    if not 0 < qr_relative_tolerance < 1:
        raise ValueError("RP4_V3_QR_TOLERANCE_INVALID")
    present = np.isfinite(training)
    counts = present.sum(axis=0)
    observed = np.flatnonzero(counts > 0)
    all_missing = np.flatnonzero(counts == 0)
    medians: list[float | None] = [None] * width
    for index in observed:
        medians[int(index)] = float(np.median(training[present[:, index], index]))
    observed_medians = np.asarray([medians[int(index)] for index in observed], dtype=np.float64)
    labels = [f"feature:{int(index)}" for index in observed]
    labels.extend(f"presence:{index}" for index in optional)

    def encode(values: Array) -> Array:
        available = np.isfinite(values)
        contributions = np.where(available[:, observed], values[:, observed], observed_medians)
        if optional:
            contributions = np.column_stack(
                [contributions, available[:, optional].astype(np.float64)]
            )
        return np.asarray(contributions, dtype=np.float64)

    fitted = encode(training)
    predicting_design = encode(predicting)
    center = np.mean(fitted, axis=0)
    scale = np.std(fitted, axis=0, ddof=0)
    if not np.isfinite(center).all() or not np.isfinite(scale).all():
        raise ValueError("RP4_V3_RIDGE_SCALING_NONFINITE")
    # A repeated decimal can acquire a tiny non-zero std from mean round-off;
    # its observed range, unlike that computed std, is exactly zero.
    constant = np.ptp(fitted, axis=0) == 0
    scale[constant] = 0.0
    varying = np.flatnonzero((scale > 0) & ~constant)
    zero_variance = np.flatnonzero((scale == 0) | constant)
    with np.errstate(over="ignore", invalid="ignore"):
        standardized = (fitted[:, varying] - center[varying]) / scale[varying]
        standardized_prediction = (predicting_design[:, varying] - center[varying]) / scale[varying]
    training_low, training_high = standardized < -5.0, standardized > 5.0
    predicting_low, predicting_high = standardized_prediction < -5.0, standardized_prediction > 5.0
    standardized = np.clip(standardized, -5.0, 5.0)
    standardized_prediction = np.clip(standardized_prediction, -5.0, 5.0)
    if not np.isfinite(standardized_prediction).all():
        raise ValueError("RP4_V3_RIDGE_PREDICTING_DESIGN_NONFINITE")
    if not np.isfinite(standardized).all():
        raise ValueError("RP4_V3_RIDGE_TRAINING_DESIGN_NONFINITE")

    rank = 0
    pivots: npt.NDArray[np.int64] = np.empty(0, dtype=np.int64)
    relative_diagonal: list[float] = [1.0]
    if varying.size:
        # Project away the retained intercept FOR RANK SELECTION ONLY. The
        # fitted/predicting designs below remain the original clipped z values.
        projected = standardized - standardized.mean(axis=0)
        triangular, pivots = linalg.qr(projected, mode="r", pivoting=True, check_finite=False)
        diagonal = np.abs(np.diag(triangular))
        relative = diagonal / math.sqrt(len(training))
        relative_diagonal.extend(relative.tolist())
        rank = int(np.count_nonzero(relative > qr_relative_tolerance))
    selected = np.sort(pivots[:rank])
    active = varying[selected]
    collinear = varying[pivots[rank:]]
    final_training = np.column_stack([np.ones(len(training)), standardized[:, selected]])
    final_predicting = np.column_stack(
        [np.ones(len(predicting)), standardized_prediction[:, selected]]
    )
    removed = [
        {"column": f"feature:{int(index)}", "reason": "all_missing_training"}
        for index in all_missing
    ]
    removed.extend(
        {"column": labels[int(index)], "reason": "zero_variance_training"}
        for index in zero_variance
    )
    removed.extend({"column": labels[int(index)], "reason": "collinear_qr"} for index in collinear)
    return _RidgeDesign(
        np.asarray(final_training, dtype=np.float64),
        np.asarray(final_predicting, dtype=np.float64),
        {
            "training_rows": len(training),
            "input_columns": width,
            "imputation": "training_median_after_v1_pointwise_transforms",
            "medians": medians,
            "finite_training_counts": counts.tolist(),
            "presence_indices": list(optional),
            "encoded_columns_before_rank_filter": labels,
            "centers": center.tolist(),
            "scales_population_sd": scale.tolist(),
            "active_columns": ["intercept", *[labels[int(index)] for index in active]],
            "removed_columns": removed,
            "qr_pivot_order": ["intercept", *[labels[int(varying[index])] for index in pivots]],
            "qr_relative_diagonal": relative_diagonal,
            "qr_relative_tolerance": qr_relative_tolerance,
            "slope_rank": rank,
            "design_rank_including_intercept": rank + 1,
            "qr_intercept_projection_for_rank_only": True,
            "restandardized_after_winsorization": False,
            "winsorization": {
                "standard_deviation_limit": 5.0,
                "training": [
                    {
                        "column": labels[int(column)],
                        "count_low": int(training_low[:, i].sum()),
                        "count_high": int(training_high[:, i].sum()),
                    }
                    for i, column in enumerate(varying)
                ],
                "predicting": [
                    {
                        "column": labels[int(column)],
                        "count_low": int(predicting_low[:, i].sum()),
                        "count_high": int(predicting_high[:, i].sum()),
                    }
                    for i, column in enumerate(varying)
                ],
            },
            "intercept_penalized": False,
        },
    )


def fit_ridge(
    design: Array,
    target: Array,
    train: Mask,
    inner_fit: Mask,
    inner_valid: Mask,
    test: Mask,
    nullable_indices: Sequence[int],
    dates: npt.NDArray[Any],
    assets: npt.NDArray[Any],
    options: Mapping[str, Any],
) -> tuple[Array, dict[str, Any]]:
    """Select ridge in past validation sessions, then refit using all past rows."""
    _validate_inputs(design, target, train, inner_fit, inner_valid, test, dates, assets)
    penalties = tuple(float(value) for value in options.get("lambda_grid", RIDGE_GRID))
    if (
        not penalties
        or len(set(penalties)) != len(penalties)
        or any(not math.isfinite(value) or value <= 0 for value in penalties)
    ):
        raise ValueError("RP4_V3_RIDGE_PENALTY_GRID_INVALID")
    tolerance = float(options.get("qr_relative_tolerance", QR_RELATIVE_TOLERANCE))
    factors = tuple(float(value) for value in options.get("forecast_bounds", [0.5, 2.0]))
    inner = _ridge_design(
        design[inner_fit], design[inner_valid], nullable_indices, qr_relative_tolerance=tolerance
    )
    inner_response = np.log(target[inner_fit])
    inner_bounds = _training_bounds(target[inner_fit], factors)
    validation_dates = dates[inner_valid].tolist()
    validation_assets = assets[inner_valid].tolist()
    gram, cross = inner.fitted.T @ inner.fitted, inner.fitted.T @ inner_response
    choices: list[dict[str, Any]] = []
    for penalty in penalties:
        coefficient = _ridge_coefficient(gram, cross, penalty)
        forecast, calibration = _ridge_predict(
            inner.fitted, inner.predicting, inner_response, coefficient, inner_bounds
        )
        score = equal_session_asset_mean(
            qlike_losses(target[inner_valid], forecast), validation_dates, validation_assets
        )
        if not math.isfinite(score):
            raise ValueError("RP4_V3_RIDGE_TUNING_SCORE_NONFINITE")
        choices.append({"lambda": penalty, "validation_qlike": score, **calibration})
    selected = min(choices, key=lambda row: (row["validation_qlike"], -row["lambda"]))
    refit = _ridge_design(
        design[train], design[test], nullable_indices, qr_relative_tolerance=tolerance
    )
    response = np.log(target[train])
    bounds = _training_bounds(target[train], factors)
    coefficient = _ridge_coefficient(
        refit.fitted.T @ refit.fitted, refit.fitted.T @ response, selected["lambda"]
    )
    forecast, calibration = _ridge_predict(
        refit.fitted, refit.predicting, response, coefficient, bounds
    )
    return forecast, {
        "method": "ridge_log_target_Duan_smearing_winsorized_z5_percentile_bounds",
        "objective": "sum_squared_log_residuals_plus_lambda_l2_slopes",
        "selected": selected,
        "candidates": choices,
        "lambda_grid": list(penalties),
        "train_rows": int(train.sum()),
        "inner_fit_rows": int(inner_fit.sum()),
        "inner_valid_rows": int(inner_valid.sum()),
        "inner_valid_sessions": np.unique(dates[inner_valid]).tolist(),
        "preprocessing": {"inner_fit": inner.record, "refit": refit.record},
        "bounds": {"inner_fit": inner_bounds, "refit": bounds},
        "coefficients": coefficient.tolist(),
        "intercept_penalized": False,
        "tie_break": "larger_lambda",
        **calibration,
    }


def fit_lightgbm(
    design: Array,
    target: Array,
    train: Mask,
    inner_fit: Mask,
    inner_valid: Mask,
    test: Mask,
    dates: npt.NDArray[Any],
    assets: npt.NDArray[Any],
    options: Mapping[str, Any],
    *,
    threads: int = 4,
) -> tuple[Array, dict[str, Any]]:
    """Native-NaN QLIKE boosting with validation-only early stopping.

    Dataset init scores are already included in ``feval`` raw margins. The
    standalone Booster's prediction excludes them, so add the training start
    exactly once there. A validation parity check verifies this on every fit.
    """
    import lightgbm as lgb

    _validate_inputs(design, target, train, inner_fit, inner_valid, test, dates, assets)
    leaves_grid = tuple(int(value) for value in options.get("num_leaves", LEAVES_GRID))
    maximum_rounds = int(options.get("num_boost_round", 2000))
    patience = int(options.get("early_stopping_rounds", 50))
    seed = int(options.get("seed", 20260907))
    if (
        not leaves_grid
        or len(set(leaves_grid)) != len(leaves_grid)
        or any(value < 2 for value in leaves_grid)
        or maximum_rounds < 1
        or patience < 1
        or threads < 1
    ):
        raise ValueError("RP4_V3_LIGHTGBM_OPTIONS_INVALID")
    if "num_threads" in options and int(options["num_threads"]) != threads:
        raise ValueError("RP4_V3_LIGHTGBM_THREADS_DIFFER_FROM_OPTIONS")
    fitting_design = np.where(np.isfinite(design[inner_fit]), design[inner_fit], np.nan)
    validation_design = np.where(np.isfinite(design[inner_valid]), design[inner_valid], np.nan)
    validation_target = target[inner_valid]
    validation_dates, validation_assets = dates[inner_valid].tolist(), assets[inner_valid].tolist()
    validation_groups = _SessionAssetGroups.from_labels(validation_dates, validation_assets)

    def parameters(mask: Mask, leaves: int) -> dict[str, Any]:
        return {
            "objective": lightgbm_objective(target[mask]),
            "metric": "None",
            "num_leaves": leaves,
            "learning_rate": float(options.get("learning_rate", 0.05)),
            "min_data_in_leaf": int(options.get("min_data_in_leaf", 100)),
            "max_bin": int(options.get("max_bin", 63)),
            "verbosity": -1,
            "seed": seed,
            "deterministic": True,
            "force_col_wise": True,
            "num_threads": threads,
            "feature_pre_filter": False,
            "feature_fraction": 1.0,
            "bagging_fraction": 1.0,
            "boost_from_average": False,
            "zero_as_missing": False,
        }

    def metric(raw: Array, _dataset: Any) -> tuple[str, float, bool]:
        # Do NOT add start here: LightGBM supplied the Dataset's init_score.
        score = validation_groups.mean(
            qlike_losses(validation_target, _lgb_forecast(np.asarray(raw, dtype=np.float64))),
        )
        if not math.isfinite(score):
            raise ValueError("RP4_V3_LIGHTGBM_TUNING_SCORE_NONFINITE")
        return METRIC_NAME, score, False

    inner_start = float(np.log(target[inner_fit].mean()))
    choices: list[dict[str, Any]] = []
    validation_forecasts: dict[int, Array] = {}
    for leaves in leaves_grid:
        fitting_set = lgb.Dataset(
            fitting_design,
            label=np.log(target[inner_fit]),
            init_score=np.full(int(inner_fit.sum()), inner_start),
            free_raw_data=True,
        )
        validation_set = lgb.Dataset(
            validation_design,
            label=np.log(validation_target),
            reference=fitting_set,
            init_score=np.full(len(validation_target), inner_start),
            free_raw_data=True,
        )
        history: dict[str, dict[str, list[float]]] = {}
        booster = lgb.train(
            parameters(inner_fit, leaves),
            fitting_set,
            num_boost_round=maximum_rounds,
            valid_sets=[validation_set],
            valid_names=["inner_valid"],
            feval=metric,
            callbacks=[
                lgb.record_evaluation(history),
                lgb.early_stopping(patience, first_metric_only=True, verbose=False, min_delta=0.0),
            ],
        )
        scores = history["inner_valid"][METRIC_NAME]
        best_round = int(np.argmin(scores)) + 1
        if booster.best_iteration != best_round:
            raise ValueError("RP4_V3_LIGHTGBM_BEST_ITERATION_MISMATCH")
        validation_raw = inner_start + np.asarray(
            booster.predict(
                validation_design, raw_score=True, num_iteration=best_round, num_threads=threads
            ),
            dtype=np.float64,
        )
        verification_score = equal_session_asset_mean(
            qlike_losses(validation_target, _lgb_forecast(validation_raw)),
            validation_dates,
            validation_assets,
        )
        difference = abs(verification_score - scores[best_round - 1])
        if not math.isclose(
            verification_score, scores[best_round - 1], rel_tol=1e-10, abs_tol=1e-12
        ):
            raise ValueError("RP4_V3_LIGHTGBM_INIT_SCORE_VALIDATION_PARITY_FAILED")
        validation_forecasts[leaves] = _lgb_forecast(validation_raw)
        choices.append(
            {
                "num_leaves": leaves,
                "rounds": best_round,
                "validation_qlike": float(scores[best_round - 1]),
                "rounds_evaluated": len(scores),
                "stopped_before_cap": len(scores) < maximum_rounds,
                "validation_qlike_by_round": scores,
                "init_score_prediction_parity_abs_difference": difference,
            }
        )
    selected = min(
        choices, key=lambda row: (row["validation_qlike"], row["num_leaves"], row["rounds"])
    )
    start = float(np.log(target[train].mean()))
    refit_design = np.where(np.isfinite(design[train]), design[train], np.nan)
    dataset = lgb.Dataset(
        refit_design,
        label=np.log(target[train]),
        init_score=np.full(int(train.sum()), start),
        free_raw_data=True,
    )
    booster = lgb.train(
        parameters(train, selected["num_leaves"]), dataset, num_boost_round=selected["rounds"]
    )
    actual_rounds = int(booster.current_iteration())
    if actual_rounds != selected["rounds"]:
        raise ValueError("RP4_V3_LIGHTGBM_REFIT_ROUND_COUNT_MISMATCH")
    prediction_design = np.where(np.isfinite(design[test]), design[test], np.nan)
    raw = start + np.asarray(
        booster.predict(
            prediction_design,
            raw_score=True,
            num_iteration=selected["rounds"],
            num_threads=threads,
        ),
        dtype=np.float64,
    )
    forecast = _lgb_forecast(raw)
    if not np.isfinite(forecast).all():
        raise ValueError("RP4_V3_LIGHTGBM_FORECAST_NONFINITE")
    secondary = mz_secondary(
        validation_forecasts[selected["num_leaves"]],
        validation_target,
        dates[inner_valid],
        assets[inner_valid],
        forecast,
        inner_fit_last_session=str(np.max(dates[inner_fit])),
        selected_num_leaves=int(selected["num_leaves"]),
        selected_rounds=int(selected["rounds"]),
    )
    return forecast, {
        "mz_secondary": secondary,
        "selected": {key: selected[key] for key in ("num_leaves", "rounds", "validation_qlike")},
        "candidates": choices,
        "train_rows": int(train.sum()),
        "inner_fit_rows": int(inner_fit.sum()),
        "inner_valid_rows": int(inner_valid.sum()),
        "inner_valid_sessions": np.unique(validation_dates).tolist(),
        "num_leaves_grid": list(leaves_grid),
        "maximum_rounds": maximum_rounds,
        "early_stopping_rounds": patience,
        "refit_rounds": actual_rounds,
        "seed": seed,
        "num_threads": threads,
        "inner_fit_init_score": inner_start,
        "init_score": start,
        "feval_init_score": "already_included_no_addition",
        "predict_init_score": "added_once_to_standalone_booster_raw_score",
        "objective": "QLIKE_log_variance",
        "validation_metric": METRIC_NAME,
        "tie_break": "fewer_leaves_then_fewer_rounds",
        "forecast_log_clip": [-30, 30],
        "variance_floor": 1e-12,
        "count_log_low": int(np.count_nonzero(raw <= -30)),
        "count_log_high": int(np.count_nonzero(raw >= 30)),
        "count_variance_floor": int(np.count_nonzero(raw <= math.log(1e-12))),
    }


class ModelConvergenceError(RuntimeError):
    """A failed numerical solve has diagnostics but never a valid forecast."""

    def __init__(self, task: str, diagnostics: dict[str, Any]) -> None:
        self.diagnostics = diagnostics
        super().__init__(
            f"RP4_V3_{task}_NOT_CONVERGED:"
            + json.dumps(diagnostics, sort_keys=True, allow_nan=False)
        )


def _pinball(actual: Array, prediction: Array, quantile: float = QUANTILE_LEVEL) -> Array:
    residual = actual - prediction
    return np.maximum(quantile * residual, (quantile - 1.0) * residual)


def _binary_loss(actual: Array, probability: Array) -> Array:
    bounded = np.clip(probability, PROBABILITY_FLOOR, 1.0 - PROBABILITY_FLOOR)
    return -(actual * np.log(bounded) + (1.0 - actual) * np.log1p(-bounded))


def _validate_binary_inputs(
    design: Array,
    target: Array,
    train: Mask,
    inner_fit: Mask,
    inner_valid: Mask,
    test: Mask,
    dates: npt.NDArray[Any],
    assets: npt.NDArray[Any],
) -> None:
    if target.shape != (len(design),) or train.shape != target.shape:
        raise ValueError("RP4_V3_BINARY_TARGET_SHAPE_MISMATCH")
    # The v2 mask/date guard expects positive RV; supply a positive surrogate
    # solely for that guard, then validate actual binary TRAINING labels below.
    surrogate = np.ones(target.shape, dtype=np.float64)
    _validate_inputs(design, surrogate, train, inner_fit, inner_valid, test, dates, assets)
    if not np.isfinite(target[train]).all() or not np.isin(target[train], [0.0, 1.0]).all():
        raise ValueError("RP4_V3_TRAINING_JUMP_TARGET_NOT_BINARY")


@dataclass(frozen=True)
class _ADMMState:
    coefficient: Array
    residual: Array
    scaled_dual: Array
    rho: float


def _quantile_admm(
    fitted: Array,
    response: Array,
    penalty: float,
    options: Mapping[str, Any],
    *,
    gram: Array | None = None,
    cross: Array | None = None,
    warm_start: _ADMMState | None = None,
) -> tuple[Array, dict[str, Any], _ADMMState]:
    """Exact pinball objective, solved to registered ADMM residual tolerances.

    Dividing the entire objective by N preserves SUM(pinball)+lambda*L2.
    The dual stopping residual and tolerance use that normalized objective.
    Residual balancing uses the algebraically equivalent SUM-scale residual.
    The intercept is unpenalized. No smoothing or mean-regression surrogate.
    """
    size, width = fitted.shape
    if response.shape != (size,) or size == 0 or not np.isfinite(response).all():
        raise ValueError("RP4_V3_QUANTILE_SOLVER_SHAPE_OR_TARGET_INVALID")
    maximum = int(options.get("maxiter", 5000))
    absolute = float(options.get("absolute_tolerance", 1e-5))
    relative = float(options.get("relative_tolerance", 1e-4))
    initial_rho = float(options.get("initial_rho", 1.0))
    interval = int(options.get("balance_interval", 25))
    balance_ratio = float(options.get("balance_ratio", 10.0))
    balance_factor = float(options.get("balance_factor", 2.0))
    if (
        maximum < 1
        or interval < 1
        or min(absolute, relative, initial_rho) <= 0
        or not all(
            math.isfinite(value)
            for value in (absolute, relative, initial_rho, balance_ratio, balance_factor)
        )
        or balance_ratio <= 1
        or balance_factor <= 1
        or not math.isfinite(penalty)
        or penalty <= 0
    ):
        raise ValueError("RP4_V3_QUANTILE_ADMM_OPTIONS_INVALID")
    gram_value = fitted.T @ fitted if gram is None else gram
    cross_value = fitted.T @ response if cross is None else cross
    if gram_value.shape != (width, width) or cross_value.shape != (width,):
        raise ValueError("RP4_V3_QUANTILE_GRAM_SHAPE_MISMATCH")
    if warm_start is None:
        coefficient = np.zeros(width)
        coefficient[0] = float(np.quantile(response, QUANTILE_LEVEL, method="linear"))
        residual = response - fitted @ coefficient
        scaled_dual = np.zeros(size)
        rho = initial_rho
    else:
        if (
            warm_start.coefficient.shape != (width,)
            or warm_start.residual.shape != (size,)
            or warm_start.scaled_dual.shape != (size,)
        ):
            raise ValueError("RP4_V3_QUANTILE_WARM_START_SHAPE_MISMATCH")
        coefficient = warm_start.coefficient.copy()
        residual = warm_start.residual.copy()
        scaled_dual = warm_start.scaled_dual.copy()
        rho = float(warm_start.rho)
    start_rho = rho
    cross_residual = fitted.T @ residual
    cross_dual = fitted.T @ scaled_dual

    def factorize(value: float) -> tuple[Array, bool]:
        diagonal = np.r_[0.0, np.full(width - 1, 2.0 * penalty / value)]
        factored, lower = linalg.cho_factor(gram_value + np.diag(diagonal), check_finite=False)
        return np.asarray(factored, dtype=np.float64), bool(lower)

    factor = factorize(rho)
    rho_changes = []
    converged = False
    primal_norm = dual_norm = primal_tolerance = dual_tolerance = math.inf
    for iteration in range(1, maximum + 1):
        coefficient = np.asarray(
            linalg.cho_solve(factor, cross_value - cross_residual - cross_dual, check_finite=False),
            dtype=np.float64,
        )
        fitted_prediction = fitted @ coefficient
        proximal_input = response - fitted_prediction - scaled_dual
        updated = np.maximum(proximal_input - QUANTILE_LEVEL / rho, 0.0) + np.minimum(
            proximal_input + (1.0 - QUANTILE_LEVEL) / rho, 0.0
        )
        previous_cross_residual = cross_residual
        cross_residual = fitted.T @ updated
        primal = fitted_prediction + updated - response
        scaled_dual += primal
        cross_dual += gram_value @ coefficient + cross_residual - cross_value
        dual_sum = rho * (cross_residual - previous_cross_residual)
        primal_norm = float(np.linalg.norm(primal))
        dual_sum_norm = float(np.linalg.norm(dual_sum))
        dual_norm = dual_sum_norm / size
        primal_tolerance = math.sqrt(size) * absolute + relative * max(
            float(np.linalg.norm(fitted_prediction)),
            float(np.linalg.norm(updated)),
            float(np.linalg.norm(response)),
        )
        dual_tolerance = (
            math.sqrt(width) * absolute + relative * float(np.linalg.norm(rho * cross_dual)) / size
        )
        residual = updated
        if not all(
            math.isfinite(value)
            for value in (primal_norm, dual_norm, primal_tolerance, dual_tolerance)
        ):
            raise ValueError("RP4_V3_QUANTILE_ADMM_NONFINITE_ITERATE")
        if primal_norm <= primal_tolerance and dual_norm <= dual_tolerance:
            converged = True
            break
        if iteration % interval == 0:
            old_rho = rho
            if primal_norm > balance_ratio * dual_sum_norm:
                rho *= balance_factor
            elif dual_sum_norm > balance_ratio * primal_norm:
                rho /= balance_factor
            if rho != old_rho:
                scaled_dual *= old_rho / rho
                cross_dual *= old_rho / rho
                factor = factorize(rho)
                rho_changes.append({"iteration": iteration, "from": old_rho, "to": rho})
    loss = float(_pinball(response, fitted @ coefficient).sum())
    penalty_value = float(penalty * np.square(coefficient[1:]).sum())
    diagnostics = {
        "solver": "ADMM_convex_exact_pinball_l2_objective",
        "converged": converged,
        "iterations": iteration,
        "maxiter": maximum,
        "objective_sum_pinball": loss,
        "objective_l2_penalty": penalty_value,
        "objective_total_sum_scale": loss + penalty_value,
        "objective_total_divided_by_n": (loss + penalty_value) / size,
        "training_rows": size,
        "design_columns": width,
        "lambda": penalty,
        "absolute_tolerance": absolute,
        "relative_tolerance": relative,
        "primal_residual_norm": primal_norm,
        "dual_residual_norm_objective_over_n": dual_norm,
        "primal_tolerance": primal_tolerance,
        "dual_tolerance": dual_tolerance,
        "dual_objective_normalization_n": size,
        "initial_rho_sum_scale": start_rho,
        "final_rho_sum_scale": rho,
        "balance_interval": interval,
        "balance_ratio": balance_ratio,
        "balance_factor": balance_factor,
        "rho_changes": rho_changes,
        "warm_started_same_training_design": warm_start is not None,
        "intercept_penalized": False,
        "quantile": QUANTILE_LEVEL,
        "smearing": False,
    }
    if not converged:
        raise ModelConvergenceError("QUANTILE_ADMM", diagnostics)
    state = _ADMMState(coefficient.copy(), residual.copy(), scaled_dual.copy(), rho)
    return coefficient, diagnostics, state


def _quantile_predict(
    predicting: Array,
    coefficient: Array,
    bounds: Mapping[str, float],
) -> tuple[Array, dict[str, Any]]:
    raw = predicting @ coefficient
    if np.isnan(raw).any():
        raise ValueError("RP4_V3_QUANTILE_LOG_FORECAST_INVALID")
    forecast = np.clip(
        np.exp(np.clip(raw, bounds["log_lower"], bounds["log_upper"])),
        bounds["lower"],
        bounds["upper"],
    )
    return np.asarray(forecast), {
        "count_low": int(np.count_nonzero(raw <= bounds["log_lower"])),
        "count_high": int(np.count_nonzero(raw >= bounds["log_upper"])),
        "prediction_rows": len(raw),
        "smearing": False,
    }


def fit_quantile(
    design: Array,
    target: Array,
    train: Mask,
    inner_fit: Mask,
    inner_valid: Mask,
    test: Mask,
    nullable_indices: Sequence[int],
    dates: npt.NDArray[Any],
    assets: npt.NDArray[Any],
    options: Mapping[str, Any],
    *,
    family: str = "linear",
    threads: int = 4,
) -> tuple[Array, dict[str, Any]]:
    """Return a conditional 0.90 quantile of RV30, not its conditional mean."""
    _validate_inputs(design, target, train, inner_fit, inner_valid, test, dates, assets)
    if family == "lightgbm":
        return _fit_lgb_native(
            design,
            target,
            train,
            inner_fit,
            inner_valid,
            test,
            dates,
            assets,
            options,
            task="quantile",
            threads=threads,
        )
    if family != "linear":
        raise ValueError("RP4_V3_UNKNOWN_QUANTILE_FAMILY")
    penalties = _penalties(options)
    tolerance = float(options.get("qr_relative_tolerance", QR_RELATIVE_TOLERANCE))
    admm = options.get("admm", {})
    inner = _ridge_design(
        design[inner_fit], design[inner_valid], nullable_indices, qr_relative_tolerance=tolerance
    )
    inner_response = np.log(target[inner_fit])
    inner_bounds = _training_bounds(target[inner_fit], options.get("forecast_bounds", [0.5, 2.0]))
    gram, cross = inner.fitted.T @ inner.fitted, inner.fitted.T @ inner_response
    state: _ADMMState | None = None
    by_penalty: dict[float, dict[str, Any]] = {}
    for penalty in sorted(penalties, reverse=True):
        coefficient, diagnostics, state = _quantile_admm(
            inner.fitted, inner_response, penalty, admm, gram=gram, cross=cross, warm_start=state
        )
        prediction, hits = _quantile_predict(inner.predicting, coefficient, inner_bounds)
        score = equal_session_asset_mean(
            _pinball(np.log(target[inner_valid]), np.log(prediction)),
            dates[inner_valid].tolist(),
            assets[inner_valid].tolist(),
        )
        if not math.isfinite(score):
            raise ValueError("RP4_V3_QUANTILE_TUNING_SCORE_NONFINITE")
        by_penalty[penalty] = {
            "lambda": penalty,
            "validation_pinball": score,
            "solver": diagnostics,
            **hits,
        }
    choices = [by_penalty[value] for value in penalties]
    selected = min(choices, key=lambda row: (row["validation_pinball"], -row["lambda"]))
    refit = _ridge_design(
        design[train], design[test], nullable_indices, qr_relative_tolerance=tolerance
    )
    response = np.log(target[train])
    bounds = _training_bounds(target[train], options.get("forecast_bounds", [0.5, 2.0]))
    coefficient, diagnostics, _ = _quantile_admm(refit.fitted, response, selected["lambda"], admm)
    forecast, hits = _quantile_predict(refit.predicting, coefficient, bounds)
    return forecast, {
        "method": "linear_log_RV30_quantile_0.90_ridge_pinball_ADMM",
        "objective": "sum_pinball_log_residuals_plus_lambda_l2_slopes",
        "quantile": QUANTILE_LEVEL,
        "smearing": False,
        "selected": selected,
        "candidates": choices,
        "lambda_grid": list(penalties),
        "lambda_solve_order": sorted(penalties, reverse=True),
        "train_rows": int(train.sum()),
        "inner_fit_rows": int(inner_fit.sum()),
        "inner_valid_rows": int(inner_valid.sum()),
        "inner_valid_sessions": np.unique(dates[inner_valid]).tolist(),
        "preprocessing": {"inner_fit": inner.record, "refit": refit.record},
        "bounds": {"inner_fit": inner_bounds, "refit": bounds},
        "solver_refit": diagnostics,
        "coefficients": coefficient.tolist(),
        "intercept_penalized": False,
        "tie_break": "larger_lambda",
        **hits,
    }


def _logistic_coefficient(
    fitted: Array,
    target: Array,
    penalty: float,
    options: Mapping[str, Any],
) -> tuple[Array, dict[str, Any]]:
    frequency = float(target.mean())
    bounded = float(np.clip(frequency, PROBABILITY_FLOOR, 1.0 - PROBABILITY_FLOOR))
    start = np.zeros(fitted.shape[1])
    start[0] = math.log(bounded) - math.log1p(-bounded)
    if np.unique(target).size == 1:
        return start, {
            "solver": "training_empirical_frequency_single_class",
            "converged": True,
            "iterations": 0,
            "single_class_training": True,
            "training_frequency": frequency,
            "clipped_probability": bounded,
            "lambda": penalty,
        }
    maximum = int(options.get("maxiter", 1000))
    gradient_tolerance = float(options.get("gtol", 1e-8))
    function_tolerance = float(options.get("ftol", 1e-12))
    if maximum < 1 or gradient_tolerance <= 0 or function_tolerance <= 0:
        raise ValueError("RP4_V3_LOGISTIC_OPTIONS_INVALID")
    size = len(target)

    def objective(coefficient: Array) -> tuple[float, Array]:
        raw = fitted @ coefficient
        slopes = np.r_[0.0, coefficient[1:]]
        value = float(
            (np.logaddexp(0.0, raw) - target * raw).sum() + penalty * np.dot(slopes, slopes)
        )
        gradient = fitted.T @ (expit(raw) - target) + 2.0 * penalty * slopes
        return value / size, np.asarray(gradient / size)

    result = minimize(
        objective,
        start,
        method="L-BFGS-B",
        jac=True,
        options={"maxiter": maximum, "gtol": gradient_tolerance, "ftol": function_tolerance},
    )
    coefficient = np.asarray(result.x, dtype=np.float64)
    if not np.isfinite(coefficient).all() or not math.isfinite(float(result.fun)):
        raise ValueError("RP4_V3_LOGISTIC_NONFINITE_RESULT")
    diagnostics = {
        "solver": "scipy_minimize_L-BFGS-B",
        "converged": bool(result.success),
        "iterations": int(result.nit),
        "status": int(result.status),
        "message": str(result.message),
        "maxiter": maximum,
        "gtol": gradient_tolerance,
        "ftol": function_tolerance,
        "objective_total_sum_scale": float(result.fun * size),
        "objective_total_divided_by_n": float(result.fun),
        "gradient_inf_norm_objective_over_n": float(np.max(np.abs(result.jac))),
        "lambda": penalty,
        "single_class_training": False,
        "intercept_penalized": False,
        "training_frequency": frequency,
    }
    if not result.success:
        raise ModelConvergenceError("LOGISTIC", diagnostics)
    return coefficient, diagnostics


def fit_jump(
    design: Array,
    target: Array,
    train: Mask,
    inner_fit: Mask,
    inner_valid: Mask,
    test: Mask,
    nullable_indices: Sequence[int],
    dates: npt.NDArray[Any],
    assets: npt.NDArray[Any],
    options: Mapping[str, Any],
    *,
    family: str = "linear",
    threads: int = 4,
) -> tuple[Array, dict[str, Any]]:
    """Return P(jump30 > 0); the caller supplies the registered binary label."""
    _validate_binary_inputs(design, target, train, inner_fit, inner_valid, test, dates, assets)
    if family == "lightgbm":
        return _fit_lgb_native(
            design,
            target,
            train,
            inner_fit,
            inner_valid,
            test,
            dates,
            assets,
            options,
            task="binary",
            threads=threads,
        )
    if family != "linear":
        raise ValueError("RP4_V3_UNKNOWN_JUMP_FAMILY")
    penalties = _penalties(options)
    tolerance = float(options.get("qr_relative_tolerance", QR_RELATIVE_TOLERANCE))
    logistic = options.get("logistic", {})
    inner = _ridge_design(
        design[inner_fit], design[inner_valid], nullable_indices, qr_relative_tolerance=tolerance
    )
    choices: list[dict[str, Any]] = []
    for penalty in penalties:
        coefficient, diagnostics = _logistic_coefficient(
            inner.fitted, target[inner_fit], penalty, logistic
        )
        prediction = np.clip(
            expit(inner.predicting @ coefficient), PROBABILITY_FLOOR, 1.0 - PROBABILITY_FLOOR
        )
        score = equal_session_asset_mean(
            _binary_loss(target[inner_valid], prediction),
            dates[inner_valid].tolist(),
            assets[inner_valid].tolist(),
        )
        if not math.isfinite(score):
            raise ValueError("RP4_V3_JUMP_TUNING_SCORE_NONFINITE")
        choices.append({"lambda": penalty, "validation_logloss": score, "solver": diagnostics})
    selected = min(choices, key=lambda row: (row["validation_logloss"], -row["lambda"]))
    refit = _ridge_design(
        design[train], design[test], nullable_indices, qr_relative_tolerance=tolerance
    )
    coefficient, diagnostics = _logistic_coefficient(
        refit.fitted, target[train], selected["lambda"], logistic
    )
    raw_probability = np.asarray(expit(refit.predicting @ coefficient))
    probability = np.clip(raw_probability, PROBABILITY_FLOOR, 1.0 - PROBABILITY_FLOOR)
    return probability, {
        "method": "L2_logistic_jump30_positive",
        "objective": "sum_binary_logloss_plus_lambda_l2_slopes",
        "selected": selected,
        "candidates": choices,
        "lambda_grid": list(penalties),
        "train_rows": int(train.sum()),
        "inner_fit_rows": int(inner_fit.sum()),
        "inner_valid_rows": int(inner_valid.sum()),
        "inner_valid_sessions": np.unique(dates[inner_valid]).tolist(),
        "preprocessing": {"inner_fit": inner.record, "refit": refit.record},
        "solver_refit": diagnostics,
        "coefficients": coefficient.tolist(),
        "intercept_penalized": False,
        "tie_break": "larger_lambda",
        "class_weights": None,
        "probability_clip": [PROBABILITY_FLOOR, 1.0 - PROBABILITY_FLOOR],
        "count_probability_low": int(np.count_nonzero(raw_probability <= PROBABILITY_FLOOR)),
        "count_probability_high": int(np.count_nonzero(raw_probability >= 1.0 - PROBABILITY_FLOOR)),
        "prediction_rows": int(test.sum()),
    }


def _fit_lgb_native(
    design: Array,
    target: Array,
    train: Mask,
    inner_fit: Mask,
    inner_valid: Mask,
    test: Mask,
    dates: npt.NDArray[Any],
    assets: npt.NDArray[Any],
    options: Mapping[str, Any],
    *,
    task: str,
    threads: int,
) -> tuple[Array, dict[str, Any]]:
    """Native quantile/binary boosting; never relabel the mean model as a tail model."""
    import lightgbm as lgb

    if task not in {"quantile", "binary"}:
        raise ValueError("RP4_V3_UNKNOWN_NATIVE_TASK")
    leaves_grid = tuple(int(value) for value in options.get("num_leaves", LEAVES_GRID))
    maximum = int(options.get("num_boost_round", 2000))
    patience = int(options.get("early_stopping_rounds", 50))
    seed = int(options.get("seed", 20260907))
    if (
        not leaves_grid
        or len(set(leaves_grid)) != len(leaves_grid)
        or any(value < 2 for value in leaves_grid)
        or min(maximum, patience, threads) < 1
    ):
        raise ValueError("RP4_V3_NATIVE_LIGHTGBM_OPTIONS_INVALID")
    if "num_threads" in options and int(options["num_threads"]) != threads:
        raise ValueError("RP4_V3_NATIVE_LIGHTGBM_THREAD_DRIFT")
    validation_target = np.log(target[inner_valid]) if task == "quantile" else target[inner_valid]
    inner_target = np.log(target[inner_fit]) if task == "quantile" else target[inner_fit]
    fitting_design = np.where(np.isfinite(design[inner_fit]), design[inner_fit], np.nan)
    validation_design = np.where(np.isfinite(design[inner_valid]), design[inner_valid], np.nan)
    groups = _SessionAssetGroups.from_labels(
        dates[inner_valid].tolist(), assets[inner_valid].tolist()
    )
    metric_name = (
        "equal_session_asset_pinball_log"
        if task == "quantile"
        else "equal_session_asset_binary_logloss"
    )

    def response_prediction(raw: Array) -> Array:
        if task == "quantile":
            return np.clip(raw, -30.0, 30.0)
        return np.asarray(
            np.clip(expit(raw), PROBABILITY_FLOOR, 1.0 - PROBABILITY_FLOOR), dtype=np.float64
        )

    def losses(actual: Array, prediction: Array) -> Array:
        return (
            _pinball(actual, prediction) if task == "quantile" else _binary_loss(actual, prediction)
        )

    def start_value(response: Array) -> float:
        if task == "quantile":
            return float(np.quantile(response, QUANTILE_LEVEL, method="linear"))
        frequency = float(np.clip(response.mean(), PROBABILITY_FLOOR, 1.0 - PROBABILITY_FLOOR))
        return math.log(frequency) - math.log1p(-frequency)

    def parameters(leaves: int) -> dict[str, Any]:
        result = {
            "objective": task,
            "metric": "None",
            "num_leaves": leaves,
            "learning_rate": float(options.get("learning_rate", 0.05)),
            "min_data_in_leaf": int(options.get("min_data_in_leaf", 100)),
            "max_bin": int(options.get("max_bin", 63)),
            "verbosity": -1,
            "seed": seed,
            "deterministic": True,
            "force_col_wise": True,
            "num_threads": threads,
            "feature_pre_filter": False,
            "feature_fraction": 1.0,
            "bagging_fraction": 1.0,
            "boost_from_average": False,
            "zero_as_missing": False,
        }
        if task == "quantile":
            result["alpha"] = QUANTILE_LEVEL
        return result

    def metric(prediction: Array, _dataset: Any) -> tuple[str, float, bool]:
        # Native binary supplies probabilities; native quantile supplies log-RV.
        values = (
            np.clip(np.asarray(prediction), -30.0, 30.0)
            if task == "quantile"
            else np.clip(np.asarray(prediction), PROBABILITY_FLOOR, 1.0 - PROBABILITY_FLOOR)
        )
        value = groups.mean(losses(validation_target, values))
        if not math.isfinite(value):
            raise ValueError("RP4_V3_NATIVE_TUNING_METRIC_NONFINITE")
        return metric_name, value, False

    inner_start = start_value(inner_target)
    inner_single_class = task == "binary" and np.unique(inner_target).size == 1
    choices: list[dict[str, Any]] = []
    for leaves in leaves_grid:
        if inner_single_class:
            prediction = response_prediction(np.full(len(validation_target), inner_start))
            score = equal_session_asset_mean(
                losses(validation_target, prediction),
                dates[inner_valid].tolist(),
                assets[inner_valid].tolist(),
            )
            choices.append(
                {
                    "num_leaves": leaves,
                    "rounds": 1,
                    "validation_score": score,
                    "rounds_evaluated": 0,
                    "validation_score_by_round": [],
                    "init_score_prediction_parity_abs_difference": 0.0,
                    "single_class_training_frequency_fallback": True,
                }
            )
            continue
        fitting = lgb.Dataset(
            fitting_design,
            label=inner_target,
            init_score=np.full(len(inner_target), inner_start),
            free_raw_data=True,
        )
        validating = lgb.Dataset(
            validation_design,
            label=validation_target,
            reference=fitting,
            init_score=np.full(len(validation_target), inner_start),
            free_raw_data=True,
        )
        history: dict[str, dict[str, list[float]]] = {}
        booster = lgb.train(
            parameters(leaves),
            fitting,
            num_boost_round=maximum,
            valid_sets=[validating],
            valid_names=["inner_valid"],
            feval=metric,
            callbacks=[
                lgb.record_evaluation(history),
                lgb.early_stopping(patience, first_metric_only=True, verbose=False, min_delta=0.0),
            ],
        )
        scores = history["inner_valid"][metric_name]
        best_round = int(np.argmin(scores)) + 1
        if booster.best_iteration != best_round:
            raise ValueError("RP4_V3_NATIVE_BEST_ITERATION_MISMATCH")
        raw = inner_start + np.asarray(
            booster.predict(
                validation_design, raw_score=True, num_iteration=best_round, num_threads=threads
            )
        )
        verification = equal_session_asset_mean(
            losses(validation_target, response_prediction(raw)),
            dates[inner_valid].tolist(),
            assets[inner_valid].tolist(),
        )
        difference = abs(verification - scores[best_round - 1])
        if not math.isclose(verification, scores[best_round - 1], rel_tol=1e-10, abs_tol=1e-12):
            raise ValueError("RP4_V3_NATIVE_INIT_SCORE_VALIDATION_PARITY_FAILED")
        choices.append(
            {
                "num_leaves": leaves,
                "rounds": best_round,
                "validation_score": float(scores[best_round - 1]),
                "rounds_evaluated": len(scores),
                "validation_score_by_round": scores,
                "stopped_before_cap": len(scores) < maximum,
                "init_score_prediction_parity_abs_difference": difference,
                "single_class_training_frequency_fallback": False,
            }
        )
    selected = min(
        choices, key=lambda row: (row["validation_score"], row["num_leaves"], row["rounds"])
    )
    refit_target = np.log(target[train]) if task == "quantile" else target[train]
    start = start_value(refit_target)
    refit_single_class = task == "binary" and np.unique(refit_target).size == 1
    if refit_single_class:
        raw = np.full(int(test.sum()), start)
        actual_rounds = 0
    else:
        fitting = lgb.Dataset(
            np.where(np.isfinite(design[train]), design[train], np.nan),
            label=refit_target,
            init_score=np.full(len(refit_target), start),
            free_raw_data=True,
        )
        booster = lgb.train(
            parameters(selected["num_leaves"]), fitting, num_boost_round=selected["rounds"]
        )
        actual_rounds = int(booster.current_iteration())
        if actual_rounds != selected["rounds"]:
            raise ValueError("RP4_V3_NATIVE_REFIT_ROUND_COUNT_MISMATCH")
        raw = start + np.asarray(
            booster.predict(
                np.where(np.isfinite(design[test]), design[test], np.nan),
                raw_score=True,
                num_iteration=selected["rounds"],
                num_threads=threads,
            )
        )
    predicted_response = response_prediction(raw)
    forecast = np.exp(predicted_response) if task == "quantile" else predicted_response
    if not np.isfinite(forecast).all():
        raise ValueError("RP4_V3_NATIVE_FORECAST_NONFINITE")
    return np.asarray(forecast), {
        "method": "native_lightgbm_log_quantile"
        if task == "quantile"
        else "native_lightgbm_binary_jump",
        "objective": task,
        "quantile": QUANTILE_LEVEL if task == "quantile" else None,
        "selected": {key: selected[key] for key in ["num_leaves", "rounds", "validation_score"]},
        "candidates": choices,
        "num_leaves_grid": list(leaves_grid),
        "maximum_rounds": maximum,
        "early_stopping_rounds": patience,
        "refit_rounds": actual_rounds,
        "seed": seed,
        "num_threads": threads,
        "train_rows": int(train.sum()),
        "inner_fit_rows": int(inner_fit.sum()),
        "inner_valid_rows": int(inner_valid.sum()),
        "inner_valid_sessions": np.unique(dates[inner_valid]).tolist(),
        "inner_fit_init_score": inner_start,
        "init_score": start,
        "single_class_inner_fit": inner_single_class,
        "single_class_refit": refit_single_class,
        "training_frequency": float(target[train].mean()) if task == "binary" else None,
        "validation_metric": metric_name,
        "tie_break": "fewer_leaves_then_fewer_rounds",
        "feval_init_score": "included_native_response_scale_no_addition",
        "predict_init_score": "added_once_to_standalone_booster_raw_score",
        "class_weights": None,
        "smearing": False,
        "forecast_log_clip": [-30, 30] if task == "quantile" else None,
        "variance_floor": None,
        "probability_clip": [PROBABILITY_FLOOR, 1.0 - PROBABILITY_FLOOR]
        if task == "binary"
        else None,
        "count_log_low": int(np.count_nonzero(raw <= -30)) if task == "quantile" else 0,
        "count_log_high": int(np.count_nonzero(raw >= 30)) if task == "quantile" else 0,
        "count_probability_low": int(np.count_nonzero(predicted_response <= PROBABILITY_FLOOR))
        if task == "binary"
        else 0,
        "count_probability_high": int(
            np.count_nonzero(predicted_response >= 1.0 - PROBABILITY_FLOOR)
        )
        if task == "binary"
        else 0,
        "prediction_rows": int(test.sum()),
    }
