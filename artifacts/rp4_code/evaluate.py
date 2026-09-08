"""RP4 fixed-spec expanding-session evaluation; all row-level outputs remain on D:."""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import math
import os
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
import pandas as pd  # type: ignore[import-untyped]
from scipy import stats
from scipy.special import logsumexp

from mds650.metrics import holm_adjust, qlike_losses
from mds650.rp2.inference import newey_west_variance, session_block_draws
from mds650.rp2.qlike_objective import lightgbm_objective

type Array = npt.NDArray[np.float64]
type Mask = npt.NDArray[np.bool_]

ROOT = Path(__file__).resolve().parents[2]
KEYS = ["asset", "session_date", "origin_minute"]
FAMILIES = ("log_ols_harq", "lightgbm_qlike")
SETS = ("B0", "B1", "B2")
CONTRASTS = (("B1_over_B0", "B0", "B1"), ("B2_over_B1", "B1", "B2"))


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_bytes_once(path: Path, encoded: bytes) -> None:
    """Publish a complete checkpoint atomically; never replace a completed result."""
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != encoded:
            raise ValueError(f"RP4_IMMUTABLE_OUTPUT_MISMATCH:{path}")
        return
    handle, temporary_name = tempfile.mkstemp(prefix=".rp4-", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        # Both files are on the same volume: hard-link creation is atomic and exclusive.
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_json_once(path: Path, payload: object) -> None:
    encoded = (json.dumps(payload, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    write_bytes_once(path, encoded)


def load_spec(path: Path, expected_sha256: str) -> dict[str, Any]:
    if sha256(path) != expected_sha256:
        raise ValueError("RP4_SPECIFICATION_HASH_MISMATCH")
    specification: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    markdown = ROOT / "docs/rp4/specification_v1.md"
    if sha256(markdown) != specification["specification_md_sha256"]:
        raise ValueError("RP4_SPECIFICATION_MARKDOWN_HASH_MISMATCH")
    feature_sets = specification["feature_sets"]
    for name in SETS:
        columns = feature_sets[name]
        if not columns or len(columns) != len(set(columns)):
            raise ValueError(f"RP4_FEATURE_ALLOWLIST_INVALID:{name}")
        excluded = {
            value
            for values in specification["excluded_registered_predictors"].values()
            for value in values
        }
        forbidden = set(columns) & {
            "rv30",
            "jump30",
            "minute_bucket",
            "role",
            "source",
            *KEYS,
            *excluded,
        }
        if forbidden:
            raise ValueError(f"RP4_FORBIDDEN_PREDICTORS:{sorted(forbidden)}")
    if feature_sets["B1"][: len(feature_sets["B0"])] != feature_sets["B0"]:
        raise ValueError("RP4_B0_NOT_NESTED_IN_B1")
    if feature_sets["B2"][: len(feature_sets["B1"])] != feature_sets["B1"]:
        raise ValueError("RP4_B1_NOT_NESTED_IN_B2")
    return specification


def transform_ols(values: Array, names: Sequence[str], transforms: Mapping[str, str]) -> Array:
    result = values.copy()
    for index, name in enumerate(names):
        transform = transforms.get(name, "raw")
        if transform == "log":
            result[:, index] = np.log(np.maximum(values[:, index], 1e-12))
        elif transform == "signed":
            result[:, index] = np.sign(values[:, index]) * np.log1p(np.abs(values[:, index]))
        elif transform != "raw":
            raise ValueError(f"RP4_UNKNOWN_TRANSFORM:{name}:{transform}")
    return result


def equal_session_asset_mean(
    values: Array, sessions: Sequence[Any], assets: Sequence[Any]
) -> float:
    frame = pd.DataFrame({"value": values, "session": sessions, "asset": assets})
    return float(
        frame.groupby(["session", "asset"])["value"].mean().groupby("session").mean().mean()
    )


def causal_masks(
    dates: npt.NDArray[Any],
    origins_ns: npt.NDArray[np.int64],
    target_end_ns: npt.NDArray[np.int64],
    eligible: Mask,
    session: str,
    *,
    embargo_minutes: int = 60,
    validation_sessions: int = 10,
) -> tuple[Mask, Mask, Mask, Mask]:
    test = eligible & (dates == session)
    if not test.any():
        raise ValueError("RP4_SESSION_NO_ELIGIBLE_ORIGINS")
    gap = embargo_minutes * 60 * 1_000_000_000
    train = eligible & (dates < session) & (target_end_ns <= origins_ns[test].min() - gap)
    days = np.unique(dates[train])
    if days.size <= validation_sessions:
        raise ValueError("RP4_INSUFFICIENT_TRAINING_SESSIONS")
    inner_valid = train & np.isin(dates, days[-validation_sessions:])
    inner_fit = train & ~inner_valid
    inner_fit &= target_end_ns <= origins_ns[inner_valid].min() - gap
    if not inner_fit.any():
        raise ValueError("RP4_INNER_TRAINING_EMPTY_AFTER_EMBARGO")
    return train, inner_fit, inner_valid, test


def ols_design(
    training: Array, predicting: Array, nullable_indices: Sequence[int]
) -> tuple[Array, Array]:
    """Observed centered feature × presence plus presence, not an invented raw IV."""
    finite = np.isfinite(training)
    counts = finite.sum(axis=0)
    total = np.where(finite, training, 0.0).sum(axis=0)
    center = np.divide(total, counts, out=np.zeros(training.shape[1]), where=counts > 0)
    centered = np.where(finite, training - center, 0.0)
    variance = np.divide(
        np.square(centered).sum(axis=0),
        counts,
        out=np.zeros(training.shape[1]),
        where=counts > 0,
    )
    scale = np.where(variance > 1e-24, np.sqrt(variance), 1.0)

    def encode(values: Array) -> Array:
        present = np.isfinite(values)
        contributions = np.where(present, (values - center) / scale, 0.0)
        components = [np.ones((len(values), 1)), contributions]
        if nullable_indices:
            components.append(present[:, nullable_indices].astype(np.float64))
        return np.column_stack(components)

    fitted_design, prediction_design = encode(training), encode(predicting)
    # Columns with no training variation have no estimable slope; retain the intercept.
    active = np.ptp(fitted_design, axis=0) > 1e-12
    active[0] = True
    return fitted_design[:, active], prediction_design[:, active]


def fit_ols(
    design: Array,
    target: Array,
    train: Mask,
    test: Mask,
    nullable_indices: Sequence[int],
) -> tuple[Array, dict[str, Any]]:
    fitted, predicting = ols_design(design[train], design[test], nullable_indices)
    response = np.log(target[train])
    coefficient, _, rank, singular = np.linalg.lstsq(fitted, response, rcond=1e-10)
    log_smear = float(logsumexp(response - fitted @ coefficient) - math.log(response.size))
    forecast = np.maximum(np.exp(np.clip(predicting @ coefficient + log_smear, -30, 30)), 1e-12)
    return forecast, {
        "method": "ordinary_least_squares_log_target_Duan_smearing",
        "train_rows": int(train.sum()),
        "rank": int(rank),
        "design_columns": fitted.shape[1],
        "rcond": 1e-10,
        "smallest_singular_value": float(singular[-1]) if singular.size else None,
        "log_smearing": log_smear,
        "hyperparameters": "none",
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
    threads: int,
) -> tuple[Array, dict[str, Any]]:
    import lightgbm as lgb

    rounds_grid = tuple(int(value) for value in options.get("num_boost_round", [25, 50, 100]))
    leaves_grid = tuple(int(value) for value in options.get("num_leaves", [7, 15]))
    seed = int(options.get("seed", 20260907))

    def fit(mask: Mask, leaves: int, rounds: int) -> tuple[Any, float]:
        start = float(np.log(target[mask].mean()))
        dataset = lgb.Dataset(
            design[mask],
            label=np.log(target[mask]),
            init_score=np.full(int(mask.sum()), start),
            free_raw_data=True,
        )
        parameters = {
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
        return lgb.train(parameters, dataset, num_boost_round=rounds), start

    choices: list[dict[str, Any]] = []
    for leaves in leaves_grid:
        booster, start = fit(inner_fit, leaves, max(rounds_grid))
        for rounds in rounds_grid:
            raw = start + np.asarray(
                booster.predict(design[inner_valid], num_iteration=rounds, num_threads=threads),
                dtype=np.float64,
            )
            forecast = np.maximum(np.exp(np.clip(raw, -30, 30)), 1e-12)
            loss = qlike_losses(target[inner_valid], forecast)
            score = equal_session_asset_mean(loss, dates[inner_valid], assets[inner_valid])
            if not np.isfinite(score):
                raise ValueError("RP4_TUNING_SCORE_NONFINITE")
            choices.append({"num_leaves": leaves, "rounds": rounds, "validation_qlike": score})
    selected = min(
        choices, key=lambda row: (row["validation_qlike"], row["num_leaves"], row["rounds"])
    )
    booster, start = fit(train, selected["num_leaves"], selected["rounds"])
    raw = start + np.asarray(booster.predict(design[test], num_threads=threads), dtype=np.float64)
    forecast = np.maximum(np.exp(np.clip(raw, -30, 30)), 1e-12)
    return forecast, {
        "selected": selected,
        "candidates": choices,
        "train_rows": int(train.sum()),
        "inner_fit_rows": int(inner_fit.sum()),
        "inner_valid_rows": int(inner_valid.sum()),
        "inner_valid_sessions": sorted(np.unique(dates[inner_valid]).tolist()),
        "seed": seed,
        "init_score": start,
        "objective": "QLIKE_log_variance",
    }


def hac_matrix(values: Array, lags: int) -> Array:
    centered = values - values.mean(axis=0)
    size = len(centered)
    covariance = centered.T @ centered / size
    for lag in range(1, min(lags, size - 1) + 1):
        weight = 1.0 - lag / (lags + 1)
        term = centered[lag:].T @ centered[:-lag] / size
        covariance += weight * (term + term.T)
    return (covariance + covariance.T) / 2


def mean_inference(
    values: Array,
    *,
    repetitions: int,
    block_length: int,
    seed: int,
    minimum_sessions: int = 10,
) -> dict[str, Any]:
    size = len(values)
    result: dict[str, Any] = {
        "estimate": float(values.mean()) if size else None,
        "N_sessions": size,
    }
    if size < minimum_sessions or not np.isfinite(values).all():
        return {**result, "status": "NO VERIFICABLE", "reason": "insufficient finite sessions"}
    if np.ptp(values) == 0:
        return {**result, "status": "NO VERIFICABLE", "reason": "degenerate session variance"}
    estimate = float(values.mean())
    draws = session_block_draws(
        values, repetitions=repetitions, block_length=block_length, seed=seed
    )
    means = draws.mean(axis=1)
    interval = np.quantile(means, [0.025, 0.975])
    # Impose the null by centering each resampled session series, not by counting signs.
    exceedances = np.count_nonzero(np.abs(means - estimate) >= abs(estimate))
    raw_p = float((exceedances + 1) / (repetitions + 1))
    lags = min(5, size - 2)
    long_run = newey_west_variance(values, lags=lags)
    standard_error = math.sqrt(long_run / size)
    dm = estimate / standard_error if standard_error > 0 else None
    gw_values = np.column_stack([np.ones(size - 1), values[:-1]]) * values[1:, None]
    gw_covariance = hac_matrix(gw_values, min(5, size - 3))
    rank = int(np.linalg.matrix_rank(gw_covariance))
    gw_stat = (
        float(
            (size - 1)
            * gw_values.mean(axis=0)
            @ np.linalg.pinv(gw_covariance)
            @ gw_values.mean(axis=0)
        )
        if rank == 2
        else None
    )
    return {
        **result,
        "status": "COMPUTED",
        "ci_low": float(interval[0]),
        "ci_high": float(interval[1]),
        "p_raw": raw_p,
        "bootstrap_repetitions": repetitions,
        "bootstrap_block_length": block_length,
        "dm_hac_statistic": dm,
        "dm_hac_p_two_sided": float(2 * stats.norm.sf(abs(dm))) if dm is not None else None,
        "dm_hac_lags": lags,
        "gw_hac_diagnostic_statistic": gw_stat,
        "gw_hac_diagnostic_p": float(stats.chi2.sf(gw_stat, rank)) if gw_stat is not None else None,
        "gw_hac_diagnostic_df": rank,
        "gw_status": "ASYMPTOTIC_DIAGNOSTIC" if gw_stat is not None else "NO VERIFICABLE",
    }


def mincer_zarnowitz(actual: Array, forecast: Array) -> dict[str, Any]:
    if len(actual) < 10:
        return {"status": "NO VERIFICABLE", "reason": "fewer than 10 session means"}
    scale = float(np.mean(actual))
    design = np.column_stack([np.ones(len(actual)), forecast / scale])
    response = actual / scale
    coefficient, _, rank, _ = np.linalg.lstsq(design, response, rcond=1e-10)
    if rank < 2:
        return {"status": "NO VERIFICABLE", "reason": "rank deficient MZ design"}
    residual = response - design @ coefficient
    bread = np.linalg.pinv(design.T @ design / len(actual))
    meat = hac_matrix(design * residual[:, None], min(5, len(actual) - 2))
    covariance = bread @ meat @ bread / len(actual)
    difference = coefficient - np.array([0.0, 1.0])
    rank_covariance = int(np.linalg.matrix_rank(covariance))
    statistic = float(difference @ np.linalg.pinv(covariance) @ difference)
    return {
        "status": "COMPUTED" if rank_covariance == 2 else "NO VERIFICABLE",
        "scale": "levels_session_means",
        "intercept": float(coefficient[0] * scale),
        "slope": float(coefficient[1]),
        "joint_a0_b1_hac_statistic": statistic,
        "joint_a0_b1_hac_p": float(stats.chi2.sf(statistic, rank_covariance))
        if rank_covariance == 2
        else None,
        "N_sessions": len(actual),
    }


def aggregate_records(
    records: Sequence[dict[str, Any]], options: Mapping[str, Any]
) -> tuple[dict[str, Any], pd.DataFrame]:
    all_rows: list[pd.DataFrame] = []
    for record in records:
        frame = pd.DataFrame(record["keys"])
        frame["actual"] = record["target"]
        for secondary, values in record["secondary"].items():
            frame[secondary] = values
        for family in FAMILIES:
            for information_set in SETS:
                name = f"{family}__{information_set}"
                frame[f"forecast__{name}"] = record["forecasts"][family][information_set]
                frame[f"loss__{name}"] = qlike_losses(
                    frame["actual"].to_numpy(), frame[f"forecast__{name}"].to_numpy()
                )
        all_rows.append(frame)
    if not all_rows:
        return {
            "status": "NO VERIFICABLE",
            "reason": "no evaluated session",
            "contrasts": [],
        }, pd.DataFrame()
    rows = pd.concat(all_rows, ignore_index=True)
    numeric = [column for column in rows if column.startswith(("loss__", "forecast__"))] + [
        "actual"
    ]

    def means(frame: pd.DataFrame) -> pd.DataFrame:
        return (
            frame.groupby(["session_date", "asset"])[numeric].mean().groupby("session_date").mean()
        )

    session = means(rows)
    bootstrap = options.get("bootstrap", {})
    contrasts: list[dict[str, Any]] = []
    for family in FAMILIES:
        for label, base, expanded in CONTRASTS:
            baseline = session[f"loss__{family}__{base}"].to_numpy()
            losses = session[f"loss__{family}__{expanded}"].to_numpy()
            result = mean_inference(
                baseline - losses,
                repetitions=int(bootstrap.get("replications", 9999)),
                block_length=int(bootstrap.get("block_length", 5)),
                seed=int(bootstrap.get("seed", 20260907)),
                minimum_sessions=int(options.get("minimum_sessions_inference", 10)),
            )
            result.update(
                {
                    "family": family,
                    "contrast": label,
                    "baseline_qlike": float(baseline.mean()),
                    "expanded_qlike": float(losses.mean()),
                    "N_origins": len(rows),
                    "N_asset_sessions": len(rows[["asset", "session_date"]].drop_duplicates()),
                    "qlike_reduction_percent": float(
                        100 * (baseline.mean() - losses.mean()) / baseline.mean()
                    )
                    if baseline.mean() > 0
                    else None,
                }
            )
            contrasts.append(result)
    adjusted = holm_adjust(
        {f"{row['family']}__{row['contrast']}": row.get("p_raw", 1.0) for row in contrasts}
    )
    for row in contrasts:
        row["p_holm"] = adjusted[f"{row['family']}__{row['contrast']}"] if "p_raw" in row else None
    secondary_results: list[dict[str, Any]] = []
    for secondary in ("first_hour", "high_flow", "event"):
        membership = rows[secondary] if secondary in rows else pd.Series(None, index=rows.index)
        known = membership.notna()
        member = membership.eq(True).fillna(False)
        subset = rows.loc[known & member]
        unknown_count = int((~known).sum())
        coverage = {
            "N_available_origins": len(rows),
            "N_verified_membership_origins": int(known.sum()),
            "N_unknown_membership_origins": unknown_count,
            "N_verified_nonmember_origins": int((known & ~member).sum()),
            "N_excluded_from_subset_origins": len(rows) - len(subset),
            "N_unknown_membership_sessions": int(rows.loc[~known, "session_date"].nunique()),
            "coverage_status": "PARTIAL_COVERAGE" if unknown_count else "COMPLETE_COVERAGE",
        }
        if subset.empty:
            secondary_results.append(
                {
                    "subset": secondary,
                    "status": "NO VERIFICABLE",
                    "reason": "no verified member origins",
                    **coverage,
                }
            )
            continue
        subset_means = means(subset)
        for family in FAMILIES:
            for label, base, expanded in CONTRASTS:
                baseline = subset_means[f"loss__{family}__{base}"].to_numpy()
                expanded_loss = subset_means[f"loss__{family}__{expanded}"].to_numpy()
                secondary_results.append(
                    {
                        "subset": secondary,
                        "status": "PARTIAL_COVERAGE" if unknown_count else "COMPUTED",
                        **coverage,
                        "family": family,
                        "contrast": label,
                        "estimate": float((baseline - expanded_loss).mean()),
                        "qlike_reduction_percent": float(
                            100 * (baseline - expanded_loss).mean() / baseline.mean()
                        )
                        if baseline.mean() > 0
                        else None,
                        "N_sessions": len(subset_means),
                        "N_origins": len(subset),
                    }
                )
    robustness: list[dict[str, Any]] = []
    block_size = len(session) // 3
    blocks = [
        session.index[:block_size],
        session.index[block_size : 2 * block_size],
        session.index[2 * block_size :],
    ]
    subsets = {
        f"asset_{asset}": rows[rows["asset"] == asset] for asset in sorted(rows["asset"].unique())
    }
    subsets["last30sessions"] = rows[rows["session_date"].isin(session.index[-30:])]
    for index, block in enumerate(blocks):
        subsets[f"chronological_block_{index + 1}"] = rows[rows["session_date"].isin(block)]
        subsets[f"leave_block_{index + 1}_out"] = rows[~rows["session_date"].isin(block)]
    for subset_name, subset in subsets.items():
        if subset.empty:
            robustness.append(
                {"subset": subset_name, "status": "NO VERIFICABLE", "reason": "empty subset"}
            )
            continue
        subset_means = means(subset)
        for family in FAMILIES:
            for label, base, expanded in CONTRASTS:
                base_loss = subset_means[f"loss__{family}__{base}"].to_numpy()
                extra_loss = subset_means[f"loss__{family}__{expanded}"].to_numpy()
                robustness.append(
                    {
                        "subset": subset_name,
                        "family": family,
                        "contrast": label,
                        "estimate": float((base_loss - extra_loss).mean()),
                        "N_origins": len(subset),
                        "N_sessions": len(subset_means),
                        "N_asset_sessions": len(
                            subset[["asset", "session_date"]].drop_duplicates()
                        ),
                        "qlike_reduction_percent": float(
                            100 * (base_loss - extra_loss).mean() / base_loss.mean()
                        )
                        if base_loss.mean() > 0
                        else None,
                    }
                )
    calibration = {
        f"{family}__{information_set}": mincer_zarnowitz(
            session["actual"].to_numpy(),
            session[f"forecast__{family}__{information_set}"].to_numpy(),
        )
        for family in FAMILIES
        for information_set in SETS
    }
    return {
        "status": "COMPUTED",
        "N_origins": len(rows),
        "N_sessions": len(session),
        "first_session": str(session.index.min()),
        "last_session": str(session.index.max()),
        "contrasts": contrasts,
        "mincer_zarnowitz": calibration,
        "secondary": secondary_results,
        "robustness": robustness,
        "RESEARCH_ONLY": True,
        "capital_go": False,
        "disclaimer": "NOT INVESTMENT ADVICE",
    }, session.reset_index()


def run(args: argparse.Namespace) -> dict[str, Any]:
    specification = load_spec(args.spec, args.spec_sha256)
    if args.threads != specification["model"]["lightgbm"]["num_threads"]:
        raise ValueError("RP4_THREAD_COUNT_DIFFERS_FROM_SPECIFICATION")
    if Path(inspect.getfile(qlike_losses)).resolve() != ROOT / "src/mds650/metrics.py":
        raise ValueError("RP4_IMPORT_RESOLVED_OUTSIDE_CURRENT_CHECKOUT")
    output = args.output.resolve()
    public_output = args.public_output.resolve()
    if os.name == "nt" and output.drive.lower() != "d:":
        raise ValueError("RP4_GRANULAR_OUTPUT_MUST_REMAIN_ON_D")
    data_root = Path(specification["data_root"]).resolve()
    if output == data_root or not output.is_relative_to(data_root):
        raise ValueError("RP4_GRANULAR_OUTPUT_OUTSIDE_REGISTERED_NEW_ROOT")
    output.mkdir(parents=True, exist_ok=True)
    window = specification["windows"][args.window]
    binding = {
        "panel_sha256": sha256(args.panel),
        "specification_sha256": args.spec_sha256,
        "evaluator_sha256": sha256(Path(__file__)),
        "window": args.window,
        "imports_sha256": {
            str(path.relative_to(ROOT)): sha256(path)
            for path in (
                ROOT / "src/mds650/metrics.py",
                ROOT / "src/mds650/rp2/inference.py",
                ROOT / "src/mds650/rp2/qlike_objective.py",
            )
        },
    }
    write_json_once(output / "binding.json", binding)
    panel = pd.read_parquet(args.panel)
    required = set(
        KEYS
        + ["rv30", "forecast_origin_utc", "target_end_utc"]
        + specification["feature_sets"]["B2"]
    )
    if missing := required - set(panel.columns):
        raise ValueError(f"RP4_PANEL_COLUMNS_MISSING:{sorted(missing)}")
    if panel.duplicated(KEYS).any():
        raise ValueError("RP4_DUPLICATE_ORIGIN_KEYS")
    panel["session_date"] = panel["session_date"].astype(str)
    panel = panel.sort_values(["session_date", "asset", "origin_minute"]).reset_index(drop=True)
    origins = pd.to_datetime(panel["forecast_origin_utc"], utc=True)
    end = pd.to_datetime(panel["target_end_utc"], utc=True)
    if (
        origins.isna().any()
        or end.isna().any()
        or not ((end - origins) == pd.Timedelta(minutes=30)).all()
    ):
        raise ValueError("RP4_TARGET_INTERVAL_INVALID")
    # Pandas 3 may retain microseconds; explicit ns conversion is necessary for embargo arithmetic.
    origins_ns = origins.dt.as_unit("ns").astype("int64").to_numpy()
    end_ns = end.dt.as_unit("ns").astype("int64").to_numpy()
    dates, assets = panel["session_date"].to_numpy(), panel["asset"].to_numpy()
    expected_assets = specification["assets"]
    if set(assets) - set(expected_assets):
        raise ValueError("RP4_UNREGISTERED_ASSET")
    target = panel["rv30"].to_numpy(dtype=np.float64)
    nullable = set(specification["missing_allowed"])
    complete_columns = [
        name for name in specification["feature_sets"]["B2"] if name not in nullable
    ]
    finite_target = np.isfinite(target) & (target > 0)
    complete = np.isfinite(panel[complete_columns].to_numpy(dtype=np.float64)).all(axis=1)
    quality = (
        panel["rp4_eligible"].fillna(False).to_numpy(dtype=bool)
        if "rp4_eligible" in panel
        else np.ones(len(panel), dtype=bool)
    )
    eligible = finite_target & complete & quality
    asset_design = np.column_stack(
        [(assets == asset).astype(float) for asset in expected_assets[1:]]
    )
    designs = {
        name: np.column_stack(
            [panel[specification["feature_sets"][name]].to_numpy(dtype=np.float64), asset_design]
        )
        for name in SETS
    }
    ols_designs = {
        name: np.column_stack(
            [
                transform_ols(
                    panel[specification["feature_sets"][name]].to_numpy(dtype=np.float64),
                    specification["feature_sets"][name],
                    specification["feature_transforms"],
                ),
                asset_design,
            ]
        )
        for name in SETS
    }
    scheduled = sorted(set(dates[(dates >= window["start"]) & (dates <= window["end"])]))
    scheduled = scheduled[int(window.get("warmup_sessions", 0)) :]
    records, skipped = [], []
    for session in scheduled:
        checkpoint = output / "sessions" / f"{session}.json"
        if checkpoint.exists():
            record = json.loads(checkpoint.read_text(encoding="utf-8"))
            if record["binding"] != binding:
                raise ValueError("RP4_COMPLETED_SESSION_BINDING_MISMATCH")
            records.append(record)
            print(f"RP4_RESUMED_SESSION:{session}", flush=True)
            continue
        if not (eligible & (dates == session)).any():
            skipped.append({"session": session, "reason": "no eligible origins"})
            continue
        try:
            train, inner_fit, inner_valid, test = causal_masks(
                dates,
                origins_ns,
                end_ns,
                eligible,
                session,
                embargo_minutes=int(specification["embargo_minutes"]),
                validation_sessions=int(specification["model"]["tuning_sessions"]),
            )
        except ValueError as error:
            if str(error) not in {
                "RP4_INSUFFICIENT_TRAINING_SESSIONS",
                "RP4_INNER_TRAINING_EMPTY_AFTER_EMBARGO",
            }:
                raise
            skipped.append({"session": session, "reason": str(error)})
            print(f"RP4_SKIPPED_SESSION:{session}:{error}", flush=True)
            continue
        forecasts: dict[str, dict[str, list[float]]] = {family: {} for family in FAMILIES}
        fits: dict[str, Any] = {}
        for information_set in SETS:
            nullable_indices = [
                index
                for index, name in enumerate(specification["feature_sets"][information_set])
                if name in nullable
            ]
            for family in FAMILIES:
                if family == "log_ols_harq":
                    prediction, fit_record = fit_ols(
                        ols_designs[information_set], target, train, test, nullable_indices
                    )
                else:
                    prediction, fit_record = fit_lightgbm(
                        designs[information_set],
                        target,
                        train,
                        inner_fit,
                        inner_valid,
                        test,
                        dates,
                        assets,
                        specification["model"]["lightgbm"],
                        threads=args.threads,
                    )
                if not np.isfinite(prediction).all() or (prediction <= 0).any():
                    raise ValueError("RP4_FORECAST_INVALID")
                forecasts[family][information_set] = prediction.tolist()
                fits[f"{family}__{information_set}"] = fit_record
        local = origins.dt.tz_convert("America/New_York")
        first_hour = (
            (local.dt.hour * 60 + local.dt.minute >= 570)
            & (local.dt.hour * 60 + local.dt.minute < 630)
        ).to_numpy()
        high_flow: list[bool | None] = [None] * int(test.sum())
        high_flow_thresholds: dict[str, float] = {}
        if "previous_day_b2_30m_premium" in panel:
            training_flows = (
                panel.loc[train]
                .groupby(["asset", "session_date"])["previous_day_b2_30m_premium"]
                .mean()
                .dropna()
            )
            high_flow_thresholds = {
                str(asset): float(group.quantile(2 / 3))
                for asset, group in training_flows.groupby("asset")
            }
            high_flow = [
                bool(value > high_flow_thresholds[asset])
                if asset in high_flow_thresholds and np.isfinite(value)
                else None
                for asset, value in panel.loc[
                    test, ["asset", "previous_day_b2_30m_premium"]
                ].itertuples(index=False, name=None)
            ]
        events = (
            [None if pd.isna(value) else bool(value) for value in panel.loc[test, "is_event"]]
            if "is_event" in panel
            else [None] * int(test.sum())
        )
        record = {
            "binding": binding,
            "session": session,
            "keys": panel.loc[test, KEYS].to_dict("records"),
            "target": target[test].tolist(),
            "forecasts": forecasts,
            "fits": fits,
            "secondary": {
                "first_hour": first_hour[test].tolist(),
                "high_flow": high_flow,
                "event": events,
            },
            "train_last_session": str(np.max(dates[train])),
            "train_sessions": len(set(dates[train])),
            "high_flow_training_thresholds_by_asset": high_flow_thresholds,
            "max_training_target_end_utc": str(end[train].max()),
            "first_evaluation_origin_utc": str(origins[test].min()),
        }
        write_json_once(checkpoint, record)
        records.append(record)
        print(f"RP4_COMPLETED_SESSION:{session}:origins={int(test.sum())}", flush=True)
    summary, session_losses = aggregate_records(records, specification.get("inference", {}))
    summary.update(
        {
            "binding": binding,
            "result_label": specification["label"],
            "window": args.window,
            "scheduled_sessions": len(scheduled),
            "skipped_sessions": skipped,
            "panel_quality": {
                "rows": len(panel),
                "invalid_target": int((~finite_target).sum()),
                "incomplete_mandatory_predictors": int((~complete).sum()),
                "failed_quality_gate": int((~quality).sum()),
                "eligible": int(eligible.sum()),
            },
            "evaluation_quality_by_asset": [
                {
                    "asset": asset,
                    "scheduled_rows": int(mask.sum()),
                    "eligible_rows": int((mask & eligible).sum()),
                    "invalid_target": int((mask & ~finite_target).sum()),
                    "incomplete_mandatory_predictors": int((mask & ~complete).sum()),
                    "failed_quality_gate": int((mask & ~quality).sum()),
                }
                for asset in expected_assets
                for mask in [(assets == asset) & np.isin(dates, scheduled)]
            ],
            "completed_session_sha256": {
                path.name: sha256(path) for path in sorted((output / "sessions").glob("*.json"))
            },
        }
    )
    write_json_once(public_output / "summary.json", summary)
    csv_path = public_output / "session_losses.csv"
    csv = session_losses.to_csv(index=False).encode()
    write_bytes_once(csv_path, csv)
    print(f"RP4_WINDOW_COMPLETE:{args.window}:sessions={len(records)}", flush=True)
    print(f"summary_sha256={sha256(public_output / 'summary.json')}", flush=True)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--spec-sha256", required=True)
    parser.add_argument("--window", choices=("primary", "confirmation"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--public-output", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()
    if args.threads < 1:
        parser.error("--threads must be positive")
    run(args)


if __name__ == "__main__":
    main()
