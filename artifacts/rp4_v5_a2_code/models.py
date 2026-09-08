"""Amendment 1: fit only the requested family on its supplied bounded window."""

from __future__ import annotations

import math
import warnings
from time import perf_counter

import numpy as np
import pandas as pd
from artifacts.rp4_v2_code import models as v2
from artifacts.rp4_v3_code import models as v3
from artifacts.rp4_v5_code import models as a1
from sklearn.exceptions import ConvergenceWarning
from sklearn.linear_model import ElasticNet
from threadpoolctl import threadpool_limits

from mds650.metrics import qlike_losses

FAMILIES = a1.FAMILIES
CONFIG = {
    "elastic_net_max_iter": 500000,
    "mlp_configs": [
        {"hidden_layer_sizes": [64, 32], "alpha": 0.0001},
        {"hidden_layer_sizes": [32], "alpha": 0.01},
    ],
    "mlp_max_iter": 200,
    "mlp_batch_size": 1024,
    "early_stop_fraction": 0.1,
    "early_stop_patience": 20,
    "early_stop_tol": 1e-4,
    "purge_minutes": 60,
    "seed": 20260908,
}


def _elastic_candidate(split, parameters):
    fitted, predicting = split.design.fitted, split.design.predicting
    slopes, prediction_slopes = fitted[:, 1:], predicting[:, 1:]
    zero_column = slopes.shape[1] == 0
    if zero_column:
        slopes, prediction_slopes = np.zeros((len(fitted), 1)), np.zeros((len(predicting), 1))
    model = ElasticNet(
        **parameters,
        selection="cyclic",
        precompute=True,
        max_iter=CONFIG["elastic_net_max_iter"],
        tol=1e-6,
        fit_intercept=True,
        copy_X=True,
    )
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        model.fit(slopes, split.response)
    coefficient = np.r_[model.intercept_, model.coef_]
    gap = float(model.dual_gap_)
    converged = (
        not any(issubclass(item.category, ConvergenceWarning) for item in caught)
        and np.isfinite(coefficient).all()
        and math.isfinite(gap)
    )
    record = {
        "n_iter": int(model.n_iter_),
        "dual_gap": gap if math.isfinite(gap) else None,
        "converged": bool(converged),
        "max_iter": CONFIG["elastic_net_max_iter"],
        "tol": 1e-6,
        "precompute": True,
        "selection": "cyclic",
        "intercept_penalized": False,
        "zero_column_for_no_active_slopes": zero_column,
        "warnings": [{"category": x.category.__name__, "message": str(x.message)} for x in caught],
        "coefficients": [float(x) if math.isfinite(x) else None for x in coefficient],
    }
    if not converged:
        raise v3.ModelConvergenceError("A2_ELASTIC_NET", record)
    fitted_log = np.asarray(model.predict(slopes), dtype=float)
    predicting_log = np.asarray(model.predict(prediction_slopes), dtype=float)
    if not np.isfinite(fitted_log).all() or not np.isfinite(predicting_log).all():
        raise ValueError("A2_ELASTIC_LOG_PREDICTION_NONFINITE")
    forecast, calibration = v2._ridge_predict(
        fitted_log[:, None], predicting_log[:, None], split.response, np.ones(1), split.bounds
    )
    return forecast, {**record, **calibration}


def _fit_elastic(inner, refit, validation_target, groups):
    candidates, exclusions = [], []

    def fit(split, parameters, stage):
        try:
            return _elastic_candidate(split, parameters)
        except v3.ModelConvergenceError as error:
            if parameters["alpha"] != 0.0001:
                raise
            exclusions.append(
                {
                    "stage": stage,
                    **parameters,
                    "reason": "numerical_nonconvergence",
                    "diagnostics": error.diagnostics,
                }
            )
            return None

    for alpha in a1.ELASTIC_ALPHA_GRID:
        for ratio in a1.ELASTIC_L1_GRID:
            parameters = {"alpha": alpha, "l1_ratio": ratio}
            result = fit(inner, parameters, "inner_fit")
            if result is None:
                candidates.append({**parameters, "status": "excluded", "validation_qlike": None})
                continue
            forecast, diagnostics = result
            a1._positive_forecast(forecast, len(validation_target))
            score = groups.mean(qlike_losses(validation_target, forecast))
            if not math.isfinite(score):
                raise ValueError("A2_ELASTIC_VALIDATION_SCORE_NONFINITE")
            candidates.append(
                {
                    **parameters,
                    "status": "converged",
                    "validation_qlike": score,
                    **diagnostics,
                }
            )
    ranked = sorted(
        (i for i, row in enumerate(candidates) if row["status"] == "converged"),
        key=lambda i: (candidates[i]["validation_qlike"], i),
    )
    for rank, index in enumerate(ranked, 1):
        selected = candidates[index]
        parameters = {key: selected[key] for key in ("alpha", "l1_ratio")}
        result = fit(refit, parameters, "refit")
        if result is None:
            continue
        forecast, diagnostics = result
        return forecast, {
            "method": "elastic_net_log_Duan_v3_preprocessing_A2_budget",
            "selected": {**selected, "selection_rank_after_refit_exclusions": rank},
            "candidates": candidates,
            "candidate_exclusions": exclusions,
            "candidate_exclusion_policy": "only_alpha_0.0001_numerical_nonconvergence",
            "preprocessing": {"inner_fit": inner.design.record, "refit": refit.design.record},
            "bounds": {"inner_fit": inner.bounds, "refit": refit.bounds},
            "refit": diagnostics,
            "tie_break": "grid_order",
        }
    raise v3.ModelConvergenceError(
        "A2_ELASTIC_NO_REFIT", {"candidates": candidates, "candidate_exclusions": exclusions}
    )


def temporal_core(panel, fitting):
    """Reserve the last 10% of fitting sessions and purge before their first origin."""
    dates = panel["session_date"].to_numpy()
    days = np.unique(dates[fitting])
    count = max(1, math.ceil(len(days) * CONFIG["early_stop_fraction"]))
    if len(days) <= count:
        raise ValueError("A2_MLP_TOO_FEW_SESSIONS_FOR_CHRONOLOGICAL_STOP")
    stop = fitting & np.isin(dates, days[-count:])
    times = {}
    for column in ("forecast_origin_utc", "target_end_utc"):
        if column not in panel:
            raise ValueError("A2_MLP_TEMPORAL_TIMES_MISSING")
        value = pd.to_datetime(panel[column], utc=True, errors="raise")
        if value[fitting].isna().any():
            raise ValueError("A2_MLP_TEMPORAL_TIMES_NULL")
        times[column] = value.to_numpy(dtype="datetime64[ns]").astype(np.int64)
    cutoff = int(times["forecast_origin_utc"][stop].min()) - 60 * 60 * 1_000_000_000
    before_purge = fitting & ~stop
    core = before_purge & (times["target_end_utc"] <= cutoff)
    if not core.any() or dates[core].max() >= dates[stop].min():
        raise ValueError("A2_MLP_EMPTY_OR_NONCAUSAL_CORE")
    return (
        core,
        stop,
        {
            "fitting_rows": int(fitting.sum()),
            "core_rows": int(core.sum()),
            "stop_rows": int(stop.sum()),
            "fitting_sessions": len(days),
            "stop_sessions": np.unique(dates[stop]).tolist(),
            "core_last_session": str(dates[core].max()),
            "purged_rows": int(np.count_nonzero(before_purge & ~core)),
            "purge_minutes": 60,
            "stop_fraction": 0.1,
            "preprocessing_target_scale_and_bounds_fit": "core_only",
            "selected_checkpoint_fit": "core_only_stop_labels_used_only_for_early_stopping",
        },
    )


def _mlp_split(panel, design, target, fitting, predicting, nullable):
    core, stop, provenance = temporal_core(panel, fitting)
    encoded = v3._ridge_design(
        design[core],
        np.concatenate([design[stop], design[predicting]]),
        nullable,
        qr_relative_tolerance=1e-10,
    )
    return {
        "design": encoded,
        "response": np.log(target[core]),
        "stop_response": np.log(target[stop]),
        "stop_rows": int(stop.sum()),
        "bounds": v3._training_bounds(target[core]),
        "temporal_split": provenance,
    }


def _mlp_candidate(split, parameters, backend, device, threads):
    from artifacts.rp4_v5_a2_code import torch_mlp

    encoded, count = split["design"], split["stop_rows"]
    fitted, stopping = encoded.fitted[:, 1:], encoded.predicting[:count, 1:]
    predicting = encoded.predicting[count:, 1:]
    zero_column = fitted.shape[1] == 0
    if zero_column:
        fitted = np.zeros((len(fitted), 1))
        stopping = np.zeros((len(stopping), 1))
        predicting = np.zeros((len(predicting), 1))
    training_log, predicting_log, diagnostics = torch_mlp.fit_predict(
        fitted,
        stopping,
        predicting,
        split["response"],
        split["stop_response"],
        parameters,
        backend=backend,
        device=device,
        threads=threads,
    )
    forecast, calibration = v2._ridge_predict(
        training_log[:, None],
        predicting_log[:, None],
        split["response"],
        np.ones(1),
        split["bounds"],
    )
    return forecast, {
        **diagnostics,
        **calibration,
        "zero_column_for_no_active_slopes": zero_column,
    }


def _fit_mlp(panel, design, target, masks, nullable, groups, backend, device, threads):
    train, inner_fit, inner_valid, test = masks
    inner = _mlp_split(panel, design, target, inner_fit, inner_valid, nullable)
    candidates = []
    for parameters in CONFIG["mlp_configs"]:
        forecast, record = _mlp_candidate(inner, parameters, backend, device, threads)
        a1._positive_forecast(forecast, int(inner_valid.sum()))
        score = groups.mean(qlike_losses(target[inner_valid], forecast))
        if not math.isfinite(score):
            raise ValueError("A2_MLP_VALIDATION_SCORE_NONFINITE")
        candidates.append({**parameters, "validation_qlike": score, **record})
    selected_index = min(range(len(candidates)), key=lambda i: candidates[i]["validation_qlike"])
    inner_record = {
        "preprocessing": inner["design"].record,
        "bounds": inner["bounds"],
        "temporal_split": inner["temporal_split"],
    }
    del inner
    refit = _mlp_split(panel, design, target, train, test, nullable)
    forecast, record = _mlp_candidate(
        refit, CONFIG["mlp_configs"][selected_index], backend, device, threads
    )
    return forecast, {
        "method": "A2_temporal_early_stopping_MLP_log_Duan_core_only_bounds",
        "selected": candidates[selected_index],
        "candidates": candidates,
        "parameter_grid": CONFIG["mlp_configs"],
        "tie_break": "grid_order",
        "inner_fit": inner_record,
        "refit": {
            **record,
            "preprocessing": refit["design"].record,
            "bounds": refit["bounds"],
            "temporal_split": refit["temporal_split"],
        },
        "backend": backend,
        "device": device,
    }


def fit_family(
    family,
    panel,
    target,
    masks,
    name,
    spec,
    tree_design=None,
    linear_design=None,
    device=None,
    threads=1,
):
    """One family, one set, train-only labels; lazy Torch import is MLP-only."""
    start = perf_counter()
    if family not in FAMILIES or name not in ("B0", "B1", "B2") or threads < 1:
        raise ValueError("A2_FAMILY_SET_OR_THREADS_INVALID")
    amendment = spec.get("amendment", {})
    for key, value in CONFIG.items():
        if amendment.get(key) != value:
            raise ValueError(f"A2_REGISTERED_CONFIG_DRIFT:{key}")
    for key, permitted in (
        ("lightgbm_device", ("cpu", "gpu", "cuda")),
        ("mlp_backend", ("torch", "sklearn")),
        ("mlp_device", ("cpu", "cuda")),
    ):
        if amendment.get(key) not in permitted:
            raise ValueError(f"A2_BACKEND_CONFIG_INVALID:{key}")
    for key in ("lightgbm_gpu_platform_id", "lightgbm_gpu_device_id"):
        value = amendment.get(key)
        if value is not None and (type(value) is not int or value < 0):
            raise ValueError(f"A2_GPU_ID_INVALID:{key}")
    if spec["model"]["tuning_sessions"] != 10:
        raise ValueError("A2_EXTERNAL_VALIDATION_SESSIONS_DRIFT")
    keys = panel[list(a1.KEYS)]
    if keys.isna().any().any() or keys.duplicated().any():
        raise ValueError("A2_INVALID_OR_DUPLICATE_KEYS")
    if not pd.MultiIndex.from_frame(keys).is_monotonic_increasing:
        raise ValueError("A2_UNSORTED_KEYS")
    dates, assets = panel["session_date"].to_numpy(), panel["asset"].to_numpy()
    train, inner_fit, inner_valid, test = masks
    design = tree_design if family == "lightgbm_qlike" else linear_design
    if family == "seasonal_persistence":
        design = np.empty((len(panel), 0))
    if design is None:
        raise ValueError("A2_REQUESTED_FAMILY_DESIGN_MISSING")
    v2._validate_inputs(design, target, *masks, dates, assets)
    names = spec["feature_sets"][name]
    nullable = [i for i, column in enumerate(names) if column in spec["missing_allowed"]]
    if family != "seasonal_persistence":
        width = len(names) + len(spec["assets"]) - 1
        if design.shape != (len(panel), width):
            raise ValueError("A2_REGISTERED_DESIGN_WIDTH_MISMATCH")
        for i in range(width):
            if i not in nullable and not np.isfinite(design[train | test, i]).all():
                raise ValueError("A2_MANDATORY_DESIGN_NONFINITE")
    groups = v2._SessionAssetGroups.from_labels(dates[inner_valid], assets[inner_valid])
    with threadpool_limits(limits=threads):
        if family == "seasonal_persistence":
            forecast, record = a1._fit_seasonal(panel, target, masks)
        elif family == "log_ridge_harq":
            forecast, record = v3.fit_ridge(
                design, target, *masks, nullable, dates, assets, spec["model"]["ridge"]
            )
        elif family == "lightgbm_qlike":
            from artifacts.rp4_v5_a2_code.lightgbm_device import fit_lightgbm

            actual_device = device or amendment.get("lightgbm_device", "cpu")
            options = {**spec["model"]["lightgbm"], "num_threads": threads}
            expected = {**a1.LIGHTGBM_OPTIONS, "num_threads": threads}
            if any(options.get(key) != value for key, value in expected.items()):
                raise ValueError("A2_LIGHTGBM_GRID_DRIFT")
            if actual_device == "cpu":
                forecast, record = v2.fit_lightgbm(
                    design, target, *masks, dates, assets, options, threads=threads
                )
                record = {**record, "device_type": "cpu", "producer": "frozen_v2_original"}
            else:
                forecast, record = fit_lightgbm(
                    design,
                    target,
                    *masks,
                    dates,
                    assets,
                    options,
                    threads=threads,
                    device=actual_device,
                    gpu_platform_id=amendment.get("lightgbm_gpu_platform_id"),
                    gpu_device_id=amendment.get("lightgbm_gpu_device_id"),
                )
        elif family == "mlp_log":
            backend = amendment.get("mlp_backend", "sklearn")
            actual_device = device or amendment.get("mlp_device", "cpu")
            forecast, record = _fit_mlp(
                panel, design, target, masks, nullable, groups, backend, actual_device, threads
            )
        else:
            inner, refit = a1._prepare_log_splits(
                design, target, masks, nullable, spec["model"]["ridge"]
            )
            if family == "log_har":
                forecast, record = a1._fit_log_family(
                    family, inner, refit, target[inner_valid], groups
                )
            else:
                forecast, record = _fit_elastic(inner, refit, target[inner_valid], groups)
    a1._positive_forecast(forecast, int(test.sum()))
    if not math.isfinite(record["selected"]["validation_qlike"]):
        raise ValueError("A2_SELECTED_VALIDATION_SCORE_NONFINITE")
    return forecast, {
        **record,
        "family": family,
        "information_set": name,
        "num_threads": threads,
        "elapsed_seconds": perf_counter() - start,
        "train_rows": int(train.sum()),
        "inner_fit_rows": int(inner_fit.sum()),
        "inner_valid_rows": int(inner_valid.sum()),
        "test_rows": int(test.sum()),
        "inner_valid_sessions": np.unique(dates[inner_valid]).tolist(),
        "validation_metric": v2.METRIC_NAME,
    }
