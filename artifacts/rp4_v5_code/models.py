"""RP4 v5 fixed-grid estimators; no data access and no evaluation-label reads.

The frozen v3 linear preprocessing is shared by HAR-X, elastic net and MLP.
Ridge and LightGBM call their frozen producers without modification.
"""

from __future__ import annotations

import math
import warnings
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from time import perf_counter
from typing import Any

import numpy as np
import pandas as pd
from artifacts.rp4_code.evaluate import Array, Mask
from artifacts.rp4_v2_code import models as v2
from artifacts.rp4_v3_code import models as v3
from scipy import linalg
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import ElasticNet
from sklearn.neural_network import MLPRegressor
from threadpoolctl import threadpool_limits

from mds650.metrics import qlike_losses

FAMILIES = (
    "seasonal_persistence",
    "log_har",
    "log_ridge_harq",
    "log_elastic_net",
    "lightgbm_qlike",
    "mlp_log",
)
SEASONAL_GRID = (1, 5, 20)
ELASTIC_ALPHA_GRID = (0.0001, 0.01, 1.0)
ELASTIC_L1_GRID = (0.1, 0.5, 0.9)
MLP_ARCHITECTURES = ((32,), (64, 32))
MLP_ALPHA_GRID = (0.0001, 0.01)
SEED = 20260908
THREADS = 4
KEYS = ("session_date", "asset", "origin_minute")
LIGHTGBM_OPTIONS = {
    "num_leaves": [7, 15, 31, 63, 127],
    "num_boost_round": 2000,
    "early_stopping_rounds": 50,
    "learning_rate": 0.05,
    "min_data_in_leaf": 100,
    "max_bin": 63,
    "seed": SEED,
    "num_threads": THREADS,
}


def _positive_forecast(forecast: Array, size: int) -> None:
    if forecast.shape != (size,) or not np.isfinite(forecast).all() or np.any(forecast <= 0):
        raise ValueError("RP4_V5_FORECAST_NOT_POSITIVE_FINITE_OR_WRONG_SHAPE")


@dataclass(frozen=True)
class _LogSplit:
    design: v2._RidgeDesign
    response: Array
    bounds: dict[str, float]


def _prepare_log_splits(
    design: Array,
    target: Array,
    masks: tuple[Mask, Mask, Mask, Mask],
    nullable: Sequence[int],
    options: Mapping[str, Any],
) -> tuple[_LogSplit, _LogSplit]:
    train, inner_fit, inner_valid, test = masks
    tolerance = float(options.get("qr_relative_tolerance", 1e-10))
    factors = options.get("forecast_bounds", [0.5, 2.0])
    if tolerance != 1e-10:
        raise ValueError("RP4_V5_QR_TOLERANCE_DRIFT")

    def prepare(fitting: Mask, predicting: Mask) -> _LogSplit:
        observed = target[fitting]
        return _LogSplit(
            v3._ridge_design(
                design[fitting], design[predicting], nullable, qr_relative_tolerance=tolerance
            ),
            np.log(observed),
            v3._training_bounds(observed, factors),
        )

    return prepare(inner_fit, inner_valid), prepare(train, test)


def _seasonal_predict(
    fitted: pd.DataFrame, predicting: pd.DataFrame, lookback: int
) -> tuple[Array, dict[str, Any]]:
    """The fitted frame alone contains labels; each asset/minute has one row/session."""
    recent = fitted.groupby(["asset", "origin_minute"], sort=False).tail(lookback)
    seasonal = recent.groupby(["asset", "origin_minute"], sort=False)["target"].mean()
    asset_means = fitted.groupby("asset", sort=False)["target"].mean()
    global_mean = float(fitted["target"].mean())
    keys = pd.MultiIndex.from_frame(predicting[["asset", "origin_minute"]])
    forecast = seasonal.reindex(keys).to_numpy(dtype=float)
    missing_group = np.isnan(forecast)
    fallback = predicting["asset"].map(asset_means).to_numpy(dtype=float)
    missing_asset = missing_group & np.isnan(fallback)
    forecast = np.where(missing_group, fallback, forecast)
    forecast = np.where(missing_asset, global_mean, forecast)
    floor_count = int(np.count_nonzero(forecast < 1e-12))
    forecast = np.maximum(forecast, 1e-12)
    _positive_forecast(forecast, len(predicting))
    return forecast, {
        "training_rows": len(fitted),
        "training_sessions": int(fitted["session_date"].nunique()),
        "asset_fallback_rows": int(np.count_nonzero(missing_group & ~missing_asset)),
        "global_fallback_rows": int(missing_asset.sum()),
        "seasonal_rows": int((~missing_group).sum()),
        "prediction_rows": len(predicting),
        "floor": 1e-12,
        "count_floor": floor_count,
    }


def _fit_seasonal(
    panel: pd.DataFrame, target: Array, masks: tuple[Mask, Mask, Mask, Mask]
) -> tuple[Array, dict[str, Any]]:
    train, inner_fit, inner_valid, test = masks

    def fitting_frame(mask: Mask) -> pd.DataFrame:
        frame = panel.loc[mask, list(KEYS)].copy()
        frame["target"] = target[mask]
        return frame

    groups = v2._SessionAssetGroups.from_labels(
        panel.loc[inner_valid, "session_date"].tolist(),
        panel.loc[inner_valid, "asset"].tolist(),
    )
    inner = fitting_frame(inner_fit)
    validation_keys = panel.loc[inner_valid, list(KEYS)]
    choices = []
    for lookback in SEASONAL_GRID:
        forecast, record = _seasonal_predict(inner, validation_keys, lookback)
        score = groups.mean(qlike_losses(target[inner_valid], forecast))
        if not math.isfinite(score):
            raise ValueError("RP4_V5_SEASONAL_VALIDATION_SCORE_NONFINITE")
        choices.append({"K": lookback, "validation_qlike": score, **record})
    selected = min(choices, key=lambda row: (row["validation_qlike"], row["K"]))
    forecast, record = _seasonal_predict(
        fitting_frame(train), panel.loc[test, list(KEYS)], selected["K"]
    )
    return forecast, {
        "method": "same_asset_origin_minute_last_K_available_training_sessions_mean",
        "selected": selected,
        "candidates": choices,
        "K_grid": list(SEASONAL_GRID),
        "tie_break": "smaller_K",
        "information_set_invariant": True,
        **record,
    }


def _log_candidate(
    family: str, split: _LogSplit, parameters: Mapping[str, Any]
) -> tuple[Array, dict[str, Any]]:
    fitted, predicting = split.design.fitted, split.design.predicting
    if family == "log_har":
        coefficient, _, rank, singular = linalg.lstsq(
            fitted, split.response, cond=1e-10, check_finite=True, lapack_driver="gelsd"
        )
        if not np.isfinite(coefficient).all():
            raise ValueError("RP4_V5_HAR_COEFFICIENT_NONFINITE")
        forecast, calibration = v2._ridge_predict(
            fitted, predicting, split.response, coefficient, split.bounds
        )
        return forecast, {
            "coefficients": coefficient.tolist(),
            "rank": int(rank),
            "design_columns": fitted.shape[1],
            "rcond": 1e-10,
            "smallest_singular_value": float(singular[-1]) if singular.size else None,
            "intercept_penalized": False,
            **calibration,
        }

    slopes, prediction_slopes = fitted[:, 1:], predicting[:, 1:]
    zero_column = slopes.shape[1] == 0
    if zero_column:
        # sklearn needs >=1 column; this zero carries no information or penalty.
        slopes = np.zeros((len(fitted), 1))
        prediction_slopes = np.zeros((len(predicting), 1))
    model: Any
    response = split.response
    center, scale = 0.0, 1.0
    if family == "log_elastic_net":
        model = ElasticNet(
            alpha=parameters["alpha"],
            l1_ratio=parameters["l1_ratio"],
            selection="cyclic",
            precompute=True,
            max_iter=10000,
            tol=1e-6,
            fit_intercept=True,
            copy_X=True,
        )
    elif family == "mlp_log":
        center = float(response.mean())
        raw_scale = float(response.std(ddof=0))
        if np.ptp(response) == 0:
            center, raw_scale = float(response[0]), 0.0
        scale = raw_scale if raw_scale > 0 else 1.0
        response = (response - center) / scale
        model = MLPRegressor(
            hidden_layer_sizes=parameters["hidden_layer_sizes"],
            alpha=parameters["alpha"],
            activation="relu",
            solver="adam",
            batch_size=1024,
            learning_rate_init=0.001,
            max_iter=100,
            shuffle=False,
            random_state=SEED,
            early_stopping=False,
            n_iter_no_change=20,
            tol=1e-4,
        )
    else:
        raise ValueError("RP4_V5_UNKNOWN_LOG_FAMILY")

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        model.fit(slopes, response)
    if any("Training interrupted by user" in str(item.message) for item in caught):
        raise RuntimeError("RP4_V5_MODEL_TRAINING_INTERRUPTED")
    convergence_warnings = [
        str(item.message) for item in caught if issubclass(item.category, ConvergenceWarning)
    ]
    record: dict[str, Any] = {
        "n_iter": int(model.n_iter_),
        "zero_column_for_no_active_slopes": zero_column,
        "warnings": [
            {"category": item.category.__name__, "message": str(item.message)} for item in caught
        ],
    }
    if family == "log_elastic_net":
        dual_gap = float(model.dual_gap_)
        coefficient = np.r_[float(model.intercept_), model.coef_]
        record.update(
            {
                "dual_gap": dual_gap if math.isfinite(dual_gap) else None,
                "converged": not convergence_warnings
                and math.isfinite(dual_gap)
                and bool(np.isfinite(coefficient).all()),
                "max_iter": 10000,
                "tol": 1e-6,
                "selection": "cyclic",
                "precompute": True,
                "intercept_penalized": False,
                "coefficients": [float(x) if math.isfinite(x) else None for x in coefficient],
            }
        )
        if not record["converged"]:
            raise v3.ModelConvergenceError("V5_ELASTIC_NET", {**parameters, **record})
    else:
        cap_reached = int(model.n_iter_) >= 100
        loss = float(model.loss_)
        curve = np.asarray(model.loss_curve_, dtype=float)
        if not math.isfinite(loss) or not np.isfinite(curve).all():
            raise ValueError("RP4_V5_MLP_TRAINING_LOSS_NONFINITE")
        record.update(
            {
                "max_iter": 100,
                "cap_reached": cap_reached,
                "stopping_reason": "cap_reached" if cap_reached else "training_loss_tolerance",
                "loss": loss,
                "loss_curve": curve.tolist(),
                "target_log_center": center,
                "target_log_population_sd": raw_scale,
                "target_log_scale": scale,
                "target_log_zero_sd_divisor_one": raw_scale == 0.0,
                "batch_size": 1024,
                "effective_batch_size": min(1024, len(fitted)),
                "shuffle": False,
                "early_stopping": False,
                "random_state": SEED,
                "parameter_count": sum(x.size for x in (*model.coefs_, *model.intercepts_)),
            }
        )
        if convergence_warnings and not cap_reached:
            raise v3.ModelConvergenceError("V5_MLP_UNEXPECTED", {**parameters, **record})
    fitted_log = np.asarray(model.predict(slopes), dtype=float) * scale + center
    predicting_log = np.asarray(model.predict(prediction_slopes), dtype=float) * scale + center
    if not np.isfinite(fitted_log).all() or not np.isfinite(predicting_log).all():
        raise ValueError("RP4_V5_FITTED_LOG_PREDICTION_NONFINITE")
    # A one-column adapter reuses the frozen Duan and clipping implementation.
    forecast, calibration = v2._ridge_predict(
        fitted_log[:, None],
        predicting_log[:, None],
        split.response,
        np.ones(1),
        split.bounds,
    )
    return forecast, {**record, **calibration}


def _fit_log_family(
    family: str,
    inner: _LogSplit,
    refit: _LogSplit,
    validation_target: Array,
    validation_groups: v2._SessionAssetGroups,
) -> tuple[Array, dict[str, Any]]:
    if family == "log_har":
        grid = [{}]
    elif family == "log_elastic_net":
        grid = [
            {"alpha": alpha, "l1_ratio": ratio}
            for alpha in ELASTIC_ALPHA_GRID
            for ratio in ELASTIC_L1_GRID
        ]
    elif family == "mlp_log":
        grid = [
            {"hidden_layer_sizes": layers, "alpha": alpha}
            for layers in MLP_ARCHITECTURES
            for alpha in MLP_ALPHA_GRID
        ]
    else:
        raise ValueError("RP4_V5_UNKNOWN_LOG_FAMILY")
    choices = []
    for parameters in grid:
        forecast, record = _log_candidate(family, inner, parameters)
        _positive_forecast(forecast, len(validation_target))
        score = validation_groups.mean(qlike_losses(validation_target, forecast))
        if not math.isfinite(score):
            raise ValueError("RP4_V5_LOG_VALIDATION_SCORE_NONFINITE")
        choices.append({**parameters, "validation_qlike": score, **record})
    selected_index = min(range(len(choices)), key=lambda i: choices[i]["validation_qlike"])
    forecast, record = _log_candidate(family, refit, grid[selected_index])
    _positive_forecast(forecast, len(refit.design.predicting))
    return forecast, {
        "method": f"{family}_Duan_smearing_v3_preprocessing_percentile_bounds",
        "selected": choices[selected_index],
        "candidates": choices,
        "parameter_grid": grid,
        "hyperparameters": "none" if family == "log_har" else "fixed_grid",
        "tie_break": "singleton" if family == "log_har" else "grid_order",
        "preprocessing": {"inner_fit": inner.design.record, "refit": refit.design.record},
        "bounds": {"inner_fit": inner.bounds, "refit": refit.bounds},
        "refit": record,
        "num_threads": THREADS,
        "validation_metric": v2.METRIC_NAME,
    }


def fit_families(
    panel: pd.DataFrame,
    target: Array,
    masks: tuple[Mask, Mask, Mask, Mask],
    name: str,
    spec: Mapping[str, Any],
    trees: Mapping[str, Array],
    linear: Mapping[str, Array],
) -> tuple[dict[str, Array], dict[str, dict[str, Any]]]:
    """Fit all six fixed families for one information set and selected target.

    ``target[test]`` is deliberately not inspected, including in validation.
    Row order and original asset/session labels are retained for equal-group QLIKE.
    """
    if name not in ("B0", "B1", "B2") or len(masks) != 4:
        raise ValueError("RP4_V5_INFORMATION_SET_OR_MASK_COUNT_INVALID")
    if not set(KEYS).issubset(panel.columns):
        raise ValueError("RP4_V5_PANEL_KEYS_MISSING")
    keys = panel[list(KEYS)]
    if keys.isna().any().any() or keys.duplicated().any():
        raise ValueError("RP4_V5_PANEL_KEYS_MISSING_OR_DUPLICATED")
    if not pd.MultiIndex.from_frame(keys).is_monotonic_increasing:
        raise ValueError("RP4_V5_PANEL_NOT_SORTED_BY_ORIGINAL_KEYS")
    if spec["model"]["tuning_sessions"] != 10:
        raise ValueError("RP4_V5_TUNING_SESSIONS_DRIFT")
    tree_options = spec["model"]["lightgbm"]
    if any(tree_options.get(key) != value for key, value in LIGHTGBM_OPTIONS.items()):
        raise ValueError("RP4_V5_LIGHTGBM_REGISTERED_OPTIONS_DRIFT")
    feature_names = spec["feature_sets"][name]
    width = len(feature_names) + len(spec["assets"]) - 1
    optional = set(spec["missing_allowed"])
    nullable = [i for i, column in enumerate(feature_names) if column in optional]
    dates, assets = panel["session_date"].to_numpy(), panel["asset"].to_numpy()
    train, inner_fit, inner_valid, test = masks
    for design in (linear[name], trees[name]):
        v2._validate_inputs(design, target, *masks, dates, assets)
        if design.shape != (len(panel), width):
            raise ValueError("RP4_V5_REGISTERED_DESIGN_WIDTH_MISMATCH")
        mandatory = [i for i in range(width) if i not in nullable]
        if not np.isfinite(design[train | test][:, mandatory]).all():
            raise ValueError("RP4_V5_MANDATORY_DESIGN_NONFINITE")
    groups = v2._SessionAssetGroups.from_labels(dates[inner_valid], assets[inner_valid])
    forecasts: dict[str, Array] = {}
    fits: dict[str, dict[str, Any]] = {}
    with threadpool_limits(limits=THREADS):
        prepare_start = perf_counter()
        inner, refit = _prepare_log_splits(
            linear[name], target, masks, nullable, spec["model"]["ridge"]
        )
        preparation_seconds = perf_counter() - prepare_start
        for family in FAMILIES:
            start = perf_counter()
            if family == "seasonal_persistence":
                forecast, record = _fit_seasonal(panel, target, masks)
            elif family == "log_ridge_harq":
                forecast, record = v3.fit_ridge(
                    linear[name], target, *masks, nullable, dates, assets, spec["model"]["ridge"]
                )
            elif family == "lightgbm_qlike":
                forecast, record = v2.fit_lightgbm(
                    trees[name], target, *masks, dates, assets, tree_options, threads=THREADS
                )
            else:
                forecast, record = _fit_log_family(
                    family, inner, refit, target[inner_valid], groups
                )
            elapsed = perf_counter() - start
            _positive_forecast(forecast, int(test.sum()))
            if not math.isfinite(record["selected"]["validation_qlike"]):
                raise ValueError("RP4_V5_SELECTED_VALIDATION_SCORE_NONFINITE")
            forecasts[family] = forecast
            fits[family] = {
                **record,
                "elapsed_seconds": elapsed,
                "train_rows": int(train.sum()),
                "inner_fit_rows": int(inner_fit.sum()),
                "inner_valid_rows": int(inner_valid.sum()),
                "test_rows": int(test.sum()),
                "inner_fit_last_session": str(dates[inner_fit].max()),
                "inner_valid_sessions": np.unique(dates[inner_valid]).tolist(),
                "validation_metric": v2.METRIC_NAME,
            }
        fits["log_har"]["shared_preprocessing_elapsed_seconds"] = preparation_seconds
        fits["log_har"]["shared_preprocessing_families"] = ["log_har", "log_elastic_net", "mlp_log"]
    return forecasts, fits
