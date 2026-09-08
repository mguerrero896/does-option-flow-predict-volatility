"""Training-only RP4 v2 estimators; no data access, model files, or evaluation runner.

The caller supplies the unchanged v1 causal masks and applies ``transform_ols``
before ``fit_ridge``. Optional non-finite inputs must first become NaN so that a
pointwise log transform cannot turn a missing value into an observed value.
All returned column indices refer to that supplied design, including asset effects.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np
import numpy.typing as npt
from artifacts.rp4_code.evaluate import (
    Array,
    Mask,
    equal_session_asset_mean,
)
from scipy import linalg
from scipy.special import logsumexp

from mds650.metrics import qlike_losses
from mds650.rp2.qlike_objective import lightgbm_objective

RIDGE_GRID = (1e-4, 1e-2, 1.0, 1e2, 1e4)
LEAVES_GRID = (15, 31, 63)
QR_RELATIVE_TOLERANCE = 1e-10
VALIDATION_SESSIONS = 10
METRIC_NAME = "equal_session_asset_qlike"


@dataclass(frozen=True)
class _SessionAssetGroups:
    """Fixed group factors for the v1 two-stage equal-asset/session mean.

    Only observed asset/session pairs are counted. In particular, an absent
    asset is not assigned a zero loss or included in that session's divisor.
    """

    row_groups: npt.NDArray[np.int64]
    group_counts: Array
    group_sessions: npt.NDArray[np.int64]
    session_asset_counts: Array

    @classmethod
    def from_labels(cls, sessions: Sequence[Any], assets: Sequence[Any]) -> _SessionAssetGroups:
        dates_array, assets_array = np.asarray(sessions), np.asarray(assets)
        if (
            dates_array.ndim != 1
            or dates_array.size == 0
            or assets_array.shape != dates_array.shape
        ):
            raise ValueError("RP4_V2_GROUP_LABEL_SHAPE_INVALID")
        _, date_ids = np.unique(dates_array, return_inverse=True)
        asset_values, asset_ids = np.unique(assets_array, return_inverse=True)
        pairs, row_groups = np.unique(date_ids * asset_values.size + asset_ids, return_inverse=True)
        group_sessions = np.asarray(pairs // asset_values.size, dtype=np.int64)
        return cls(
            row_groups=np.asarray(row_groups, dtype=np.int64),
            group_counts=np.asarray(np.bincount(row_groups), dtype=np.float64),
            group_sessions=group_sessions,
            session_asset_counts=np.asarray(np.bincount(group_sessions), dtype=np.float64),
        )

    def mean(self, values: Array) -> float:
        if values.shape != self.row_groups.shape:
            raise ValueError("RP4_V2_GROUP_VALUES_SHAPE_INVALID")
        group_means = np.bincount(self.row_groups, weights=values) / self.group_counts
        session_means = (
            np.bincount(self.group_sessions, weights=group_means) / self.session_asset_counts
        )
        return float(np.mean(session_means))


def _validate_inputs(
    design: Array,
    target: Array,
    train: Mask,
    inner_fit: Mask,
    inner_valid: Mask,
    test: Mask,
    dates: npt.NDArray[Any],
    assets: npt.NDArray[Any],
) -> None:
    """Check mask custody without reading a target outside the training mask."""
    if design.ndim != 2 or design.shape[0] == 0:
        raise ValueError("RP4_V2_DESIGN_SHAPE_INVALID")
    size = design.shape[0]
    if target.shape != (size,) or dates.shape != (size,) or assets.shape != (size,):
        raise ValueError("RP4_V2_INPUT_SHAPE_MISMATCH")
    for mask in (train, inner_fit, inner_valid, test):
        if mask.shape != (size,) or mask.dtype != np.bool_ or not mask.any():
            raise ValueError("RP4_V2_MASK_INVALID_OR_EMPTY")
    if (
        np.any(train & test)
        or np.any(inner_fit & inner_valid)
        or np.any((inner_fit | inner_valid) & ~train)
    ):
        raise ValueError("RP4_V2_TRAIN_VALIDATION_TEST_OVERLAP")
    training_days = np.unique(dates[train])
    if training_days.size <= VALIDATION_SESSIONS:
        raise ValueError("RP4_V2_TOO_FEW_TRAINING_SESSIONS")
    expected_valid = train & np.isin(dates, training_days[-VALIDATION_SESSIONS:])
    if not np.array_equal(expected_valid, inner_valid):
        raise ValueError("RP4_V2_VALIDATION_NOT_LAST_TEN_TRAINING_SESSIONS")
    if np.max(dates[train]) >= np.min(dates[test]) or np.max(dates[inner_fit]) >= np.min(
        dates[inner_valid]
    ):
        raise ValueError("RP4_V2_NONCAUSAL_TRAINING_DATES")
    if not np.isfinite(target[train]).all() or np.any(target[train] <= 0):
        raise ValueError("RP4_V2_TRAINING_TARGET_NOT_POSITIVE_FINITE")


@dataclass(frozen=True)
class _RidgeDesign:
    fitted: Array
    predicting: Array
    record: dict[str, Any]


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
        raise ValueError("RP4_V2_RIDGE_DESIGN_SHAPE_INVALID")
    width = training.shape[1]
    optional = tuple(int(value) for value in nullable_indices)
    if len(set(optional)) != len(optional) or any(
        value < 0 or value >= width for value in optional
    ):
        raise ValueError("RP4_V2_NULLABLE_INDICES_INVALID")
    if not 0 < qr_relative_tolerance < 1:
        raise ValueError("RP4_V2_QR_TOLERANCE_INVALID")
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
        raise ValueError("RP4_V2_RIDGE_SCALING_NONFINITE")
    # A repeated decimal can acquire a tiny non-zero std from mean round-off;
    # its observed range, unlike that computed std, is exactly zero.
    constant = np.ptp(fitted, axis=0) == 0
    scale[constant] = 0.0
    varying = np.flatnonzero((scale > 0) & ~constant)
    zero_variance = np.flatnonzero((scale == 0) | constant)
    standardized = (fitted[:, varying] - center[varying]) / scale[varying]
    standardized_prediction = (predicting_design[:, varying] - center[varying]) / scale[varying]
    if not np.isfinite(standardized).all():
        raise ValueError("RP4_V2_RIDGE_TRAINING_DESIGN_NONFINITE")

    rank = 0
    pivots: npt.NDArray[np.int64] = np.empty(0, dtype=np.int64)
    relative_diagonal: list[float] = []
    if varying.size:
        # mode="r" avoids forming an unused Q on large expanding training panels.
        triangular, pivots = linalg.qr(standardized, mode="r", pivoting=True, check_finite=False)
        diagonal = np.abs(np.diag(triangular))
        if diagonal.size and diagonal[0] > 0:
            relative = diagonal / diagonal[0]
            relative_diagonal = relative.tolist()
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
            "qr_pivot_order": [labels[int(varying[index])] for index in pivots],
            "qr_relative_diagonal": relative_diagonal,
            "qr_relative_tolerance": qr_relative_tolerance,
            "slope_rank": rank,
            "intercept_penalized": False,
        },
    )


def _training_bounds(target: Array, factors: Sequence[float]) -> dict[str, float]:
    if len(factors) != 2 or not 0 < factors[0] <= factors[1]:
        raise ValueError("RP4_V2_RIDGE_BOUND_FACTORS_INVALID")
    minimum, maximum = float(np.min(target)), float(np.max(target))
    lower, upper = float(factors[0] * minimum), float(factors[1] * maximum)
    if not (0 < lower <= upper < math.inf):
        raise ValueError("RP4_V2_RIDGE_BOUNDS_NOT_REPRESENTABLE")
    return {
        "minimum_positive_training_target": minimum,
        "maximum_positive_training_target": maximum,
        "lower": lower,
        "upper": upper,
        "log_lower": math.log(lower),
        "log_upper": math.log(upper),
    }


def _ridge_coefficient(gram: Array, cross: Array, penalty: float) -> Array:
    penalized = gram.copy()
    diagonal = np.diag_indices_from(penalized)
    penalized[diagonal] += np.r_[0.0, np.full(len(gram) - 1, penalty)]
    coefficient = np.asarray(linalg.solve(penalized, cross, assume_a="pos"), dtype=np.float64)
    if not np.isfinite(coefficient).all():
        raise ValueError("RP4_V2_RIDGE_COEFFICIENT_NONFINITE")
    return coefficient


def _ridge_predict(
    fitted: Array,
    predicting: Array,
    log_target: Array,
    coefficient: Array,
    bounds: Mapping[str, float],
) -> tuple[Array, dict[str, Any]]:
    residual = log_target - fitted @ coefficient
    log_smearing = float(logsumexp(residual) - math.log(len(residual)))
    raw = predicting @ coefficient + log_smearing
    if np.isnan(raw).any() or not math.isfinite(log_smearing):
        raise ValueError("RP4_V2_RIDGE_LOG_FORECAST_INVALID")
    bounded = np.clip(raw, bounds["log_lower"], bounds["log_upper"])
    forecast = np.exp(bounded)
    # Match the declared linear endpoints despite exp(log(endpoint)) round-off.
    forecast = np.clip(forecast, bounds["lower"], bounds["upper"])
    return np.asarray(forecast, dtype=np.float64), {
        "log_smearing": log_smearing,
        "count_low": int(np.count_nonzero(raw <= bounds["log_lower"])),
        "count_high": int(np.count_nonzero(raw >= bounds["log_upper"])),
        "prediction_rows": len(raw),
    }


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
        raise ValueError("RP4_V2_RIDGE_PENALTY_GRID_INVALID")
    tolerance = float(options.get("qr_relative_tolerance", QR_RELATIVE_TOLERANCE))
    factors = tuple(float(value) for value in options.get("forecast_bounds", [0.1, 10.0]))
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
            raise ValueError("RP4_V2_RIDGE_TUNING_SCORE_NONFINITE")
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
        "method": "ridge_log_target_Duan_smearing",
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


def _lgb_forecast(raw: Array) -> Array:
    return np.asarray(np.maximum(np.exp(np.clip(raw, -30, 30)), 1e-12), dtype=np.float64)


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
        raise ValueError("RP4_V2_LIGHTGBM_OPTIONS_INVALID")
    if "num_threads" in options and int(options["num_threads"]) != threads:
        raise ValueError("RP4_V2_LIGHTGBM_THREADS_DIFFER_FROM_OPTIONS")
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
            raise ValueError("RP4_V2_LIGHTGBM_TUNING_SCORE_NONFINITE")
        return METRIC_NAME, score, False

    inner_start = float(np.log(target[inner_fit].mean()))
    choices: list[dict[str, Any]] = []
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
            raise ValueError("RP4_V2_LIGHTGBM_BEST_ITERATION_MISMATCH")
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
            raise ValueError("RP4_V2_LIGHTGBM_INIT_SCORE_VALIDATION_PARITY_FAILED")
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
        raise ValueError("RP4_V2_LIGHTGBM_REFIT_ROUND_COUNT_MISMATCH")
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
        raise ValueError("RP4_V2_LIGHTGBM_FORECAST_NONFINITE")
    return forecast, {
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
