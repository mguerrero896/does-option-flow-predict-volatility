"""Aggregate completed RP4 v3 forecasts; no fitting, panel reads, or file writes."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypedDict

import numpy as np
import pandas as pd  # type: ignore[import-untyped]
from artifacts.rp4_code import evaluate as v1
from artifacts.rp4_v2_code import evaluate_v2 as v2
from artifacts.rp4_v3_code import inference as inf

from mds650.metrics import qlike_losses

FAMILIES = inf.FAMILIES
SETS = inf.SETS
CONTRASTS = inf.CONTRASTS
REGIMES = (
    "first_hour",
    "high_flow",
    "event",
    "last_hour",
    "weekly_expiration",
    "third_friday",
    "high_gamma",
    "window_empty_5m",
    "window_empty_30m",
)
STATISTICS: tuple[inf.Statistic, ...] = ("mean", "median", "trimmed_mean_5pct")


class InferenceOptions(TypedDict):
    repetitions: int
    block_length: int
    seed: int
    minimum_sessions: int


def _options(options: Mapping[str, Any]) -> InferenceOptions:
    bootstrap = options.get("bootstrap", {})
    return {
        "repetitions": int(bootstrap.get("replications", 9999)),
        "block_length": int(bootstrap.get("block_length", 5)),
        "seed": int(bootstrap.get("seed", 20260907)),
        "minimum_sessions": int(options.get("minimum_sessions_inference", 10)),
    }


def _vector(value: Any, size: int, *, positive: bool = False) -> np.ndarray:
    vector: np.ndarray = np.asarray(value, dtype=float)
    if vector.shape != (size,) or not np.isfinite(vector).all():
        raise ValueError("RP4_V3_AGGREGATE_NONFINITE_OR_MISALIGNED_VECTOR")
    if positive and (vector <= 0).any():
        raise ValueError("RP4_V3_AGGREGATE_NONPOSITIVE_VARIANCE")
    return vector


def _frame(records: list[dict[str, Any]]) -> pd.DataFrame:
    frames = []
    dates = [r["session"] for r in records]
    if dates != sorted(set(dates)):
        raise ValueError("RP4_V3_AGGREGATE_SESSION_ORDER_OR_DUPLICATE")
    for record in records:
        frame = pd.DataFrame(record["keys"])
        if frame.empty or not set(v1.KEYS) <= set(frame):
            raise ValueError("RP4_V3_AGGREGATE_KEYS_REQUIRED")
        if frame.duplicated(v1.KEYS).any() or not frame["session_date"].eq(record["session"]).all():
            raise ValueError("RP4_V3_AGGREGATE_KEY_DATE_OR_DUPLICATE")
        actual = _vector(record["target"], len(frame), positive=True)
        frame["actual"] = actual
        for subset in REGIMES:
            membership = record.get("secondary", {}).get(subset, [None] * len(frame))
            if len(membership) != len(frame) or any(
                value is not None and not isinstance(value, (bool, np.bool_))
                for value in membership
            ):
                raise ValueError("RP4_V3_AGGREGATE_MEMBERSHIP_CONTRACT")
            frame[subset] = membership
        if set(record["forecasts"]) != set(FAMILIES):
            raise ValueError("RP4_V3_AGGREGATE_COMMON_FAMILIES_REQUIRED")
        for family in FAMILIES:
            if set(record["forecasts"][family]) != set(SETS):
                raise ValueError("RP4_V3_AGGREGATE_COMMON_INFORMATION_SETS_REQUIRED")
            for name in SETS:
                forecast = _vector(record["forecasts"][family][name], len(frame), positive=True)
                frame[f"forecast__{family}__{name}"] = forecast
                frame[f"loss__{family}__{name}"] = qlike_losses(actual, forecast)
        frames.append(frame)
    return pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()


def _means(frame: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    return frame.groupby(["session_date", "asset"])[columns].mean().groupby("session_date").mean()


def _counts(frame: pd.DataFrame) -> dict[str, int]:
    return {
        "N_origins": len(frame),
        "N_sessions": int(frame["session_date"].nunique()) if len(frame) else 0,
        "N_asset_sessions": len(frame[["asset", "session_date"]].drop_duplicates())
        if len(frame)
        else 0,
    }


def _loss_records(
    frame: pd.DataFrame,
    options: InferenceOptions,
    *,
    endpoint: str,
    statistic: inf.Statistic = "mean",
    alternative: inf.Alternative = "greater",
    primary: bool = False,
) -> list[dict[str, Any]]:
    columns = [f"loss__{family}__{name}" for family in FAMILIES for name in SETS]
    session = _means(frame, columns)
    output = []
    for family in FAMILIES:
        for contrast, base, richer in CONTRASTS:
            baseline = session[f"loss__{family}__{base}"].to_numpy()
            expanded = session[f"loss__{family}__{richer}"].to_numpy()
            inference = inf.session_contrast(
                baseline - expanded,
                statistic=statistic,
                alternative=alternative,
                **options,
            )
            output.append(
                {
                    **inference,
                    **_counts(frame),
                    "family": family,
                    "contrast": contrast,
                    "endpoint": endpoint,
                    "inference_role": "PRIMARY" if primary else "SECONDARY",
                    "baseline_loss": float(baseline.mean()) if len(baseline) else None,
                    "expanded_loss": float(expanded.mean()) if len(expanded) else None,
                    "percent_reduction_mean": float(
                        100 * (baseline - expanded).mean() / baseline.mean()
                    )
                    if len(baseline) and baseline.mean() > 0
                    else None,
                }
            )
    return output


def _distribution(
    frame: pd.DataFrame,
    options: InferenceOptions,
    *,
    endpoint: str,
    statistics: tuple[inf.Statistic, ...] = STATISTICS,
) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    for statistic in statistics:
        records = _loss_records(
            frame,
            options,
            endpoint=endpoint,
            statistic=statistic,
            alternative="two-sided",
        )
        output.extend(inf.holm_four(records))
    return output


def _regimes(frame: pd.DataFrame, options: InferenceOptions) -> list[dict[str, Any]]:
    output: list[dict[str, Any]] = []
    dates = sorted(frame["session_date"].unique())
    third = len(dates) // 3
    blocks = [dates[:third], dates[third : 2 * third], dates[2 * third :]]
    subsets: dict[str, tuple[pd.Series, pd.Series]] = {}
    always = pd.Series(True, index=frame.index)
    for name in REGIMES:
        subsets[name] = (frame[name].eq(True), frame[name].notna())
    for horizon in ("5m", "30m"):
        name = f"window_empty_{horizon}"
        subsets[f"window_nonempty_{horizon}"] = (frame[name].eq(False), frame[name].notna())
    for asset in sorted(frame["asset"].unique()):
        subsets[f"asset_{asset}"] = (frame["asset"].eq(asset), always)
    subsets["last30sessions"] = (frame["session_date"].isin(dates[-30:]), always)
    for index, block in enumerate(blocks, 1):
        membership = frame["session_date"].isin(block)
        subsets[f"chronological_block_{index}"] = (membership, always)
        subsets[f"leave_block_{index}_out"] = (~membership, always)
    for name, (member, known) in subsets.items():
        subset = frame.loc[known & member]
        coverage = {
            "subset": name,
            "N_available_origins": len(frame),
            "N_verified_membership_origins": int(known.sum()),
            "N_unknown_membership_origins": int((~known).sum()),
            "N_verified_nonmember_origins": int((known & ~member).sum()),
            "coverage_status": "PARTIAL_COVERAGE" if (~known).any() else "COMPLETE_COVERAGE",
        }
        output.extend(
            {**row, **coverage}
            for row in _distribution(
                subset,
                options,
                endpoint="qlike_regime_secondary",
            )
        )
    return output


def _empty_windows(frame: pd.DataFrame, regimes: list[dict[str, Any]]) -> dict[str, Any]:
    census = []
    by_session = []
    for horizon in ("5m", "30m"):
        for asset, group in frame.groupby("asset"):
            values = group[f"window_empty_{horizon}"]
            census.append(
                {
                    "horizon": horizon,
                    "asset": str(asset),
                    "N_origins": len(group),
                    "N_empty_origins": int(values.eq(True).sum()),
                    "N_nonempty_origins": int(values.eq(False).sum()),
                    "N_unknown_origins": int(values.isna().sum()),
                    "N_sessions": int(group["session_date"].nunique()),
                }
            )
        for (asset, session), group in frame.groupby(["asset", "session_date"]):
            values = group[f"window_empty_{horizon}"]
            by_session.append(
                {
                    "horizon": horizon,
                    "asset": str(asset),
                    "session_date": str(session),
                    "N_origins": len(group),
                    "N_empty_origins": int(values.eq(True).sum()),
                    "N_nonempty_origins": int(values.eq(False).sum()),
                    "N_unknown_origins": int(values.isna().sum()),
                }
            )
    return {
        "inference_role": "SECONDARY",
        "unknown_is_nonempty": False,
        "census": census,
        "census_by_session": by_session,
        "contrasts": [
            row
            for row in regimes
            if row["contrast"] == "B2_over_B1"
            and row["subset"].startswith(("window_empty_", "window_nonempty_"))
        ],
    }


def _high_vs_rest(frame: pd.DataFrame, options: InferenceOptions) -> list[dict[str, Any]]:
    """Paired interaction on asset-sessions containing both known groups, no zero fill."""
    known = frame["high_gamma"].notna()
    groups = frame.loc[known].copy()
    columns = [f"loss__{family}__{name}" for family in FAMILIES for name in SETS]
    high = (
        groups.loc[groups["high_gamma"].eq(True)].groupby(["session_date", "asset"])[columns].mean()
    )
    rest = (
        groups.loc[groups["high_gamma"].eq(False)]
        .groupby(["session_date", "asset"])[columns]
        .mean()
    )
    common = high.index.intersection(rest.index)
    difference = (high.loc[common] - rest.loc[common]).groupby("session_date").mean()
    output = []
    for statistic in STATISTICS:
        rows = []
        for family in FAMILIES:
            for contrast, base, richer in CONTRASTS:
                values = (
                    difference[f"loss__{family}__{base}"] - difference[f"loss__{family}__{richer}"]
                ).to_numpy()
                rows.append(
                    {
                        **inf.session_contrast(
                            values, statistic=statistic, alternative="two-sided", **options
                        ),
                        "family": family,
                        "contrast": contrast,
                        "endpoint": "high_gamma_minus_rest_increment",
                        "inference_role": "SECONDARY",
                        "sign": "increment_high_minus_increment_rest",
                        "N_asset_sessions": len(common),
                        "N_high_asset_sessions": len(high),
                        "N_rest_asset_sessions": len(rest),
                        "N_unknown_membership_origins": int((~known).sum()),
                        "pairing": (
                            "same_asset_session_contains_both_known_groups_then_equal_session"
                        ),
                    }
                )
        output.extend(inf.holm_four(rows))
    return output


def _endpoint_frames(
    records: list[dict[str, Any]],
    endpoint: str,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    frames, excluded = [], []
    for record in records:
        status = record.get("tail_status", {}).get(endpoint, {})
        if status.get("status") != "COMPUTED":
            excluded.append(
                {
                    "session": record["session"],
                    "reason": status.get("reason", "endpoint not complete"),
                }
            )
            continue
        frame = pd.DataFrame(record["keys"])
        if endpoint == "jump":
            raw_positions = np.asarray(record["jump_positions"])
            if raw_positions.ndim != 1 or not np.issubdtype(raw_positions.dtype, np.integer):
                raise ValueError("RP4_V3_AGGREGATE_JUMP_POSITIONS_NOT_INTEGER")
            positions = raw_positions.astype(int)
            if (
                (positions < 0).any()
                or (positions >= len(frame)).any()
                or not np.array_equal(positions, np.unique(positions))
            ):
                raise ValueError("RP4_V3_AGGREGATE_JUMP_POSITION_ALIGNMENT")
            frame = frame.iloc[positions].copy()
            if frame.empty:
                raise ValueError("RP4_V3_AGGREGATE_COMPUTED_JUMP_WITHOUT_ORIGINS")
            target = _vector(record["jump_target"], len(frame))
            if not np.isin(target, [0, 1]).all():
                raise ValueError("RP4_V3_AGGREGATE_JUMP_NONBINARY")
        else:
            target = np.log(_vector(record["target"], len(frame), positive=True))
        frame["actual"] = target
        forecasts = record["tail_forecasts"][endpoint]
        if set(forecasts) != set(FAMILIES) or any(set(forecasts[f]) != set(SETS) for f in FAMILIES):
            raise ValueError("RP4_V3_AGGREGATE_TAIL_COMMON_MASK_REQUIRED")
        for family in FAMILIES:
            for name in SETS:
                prediction = _vector(forecasts[family][name], len(frame))
                if endpoint == "jump" and ((prediction < 0) | (prediction > 1)).any():
                    raise ValueError("RP4_V3_AGGREGATE_JUMP_PROBABILITY_RANGE")
                frame[f"forecast__{family}__{name}"] = prediction
                if endpoint == "quantile":
                    frame[f"loss__{family}__{name}"] = inf.quantile_loss_log_rv(target, prediction)
        frames.append(frame)
    columns = v1.KEYS + ["actual"] + [f"loss__{f}__{s}" for f in FAMILIES for s in SETS]
    return (
        pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=columns)
    ), excluded


def _quantile(records: list[dict[str, Any]], options: InferenceOptions) -> dict[str, Any]:
    frame, excluded = _endpoint_frames(records, "quantile")
    contrasts = _loss_records(frame, options, endpoint="quantile_pinball_log_rv")
    sequence = inf.family_fixed_sequence(
        contrasts, endpoint="quantile_pinball_log_rv", primary=False
    )
    means = _means(frame, [f"loss__{f}__{s}" for f in FAMILIES for s in SETS])
    return {
        "status": "COMPUTED" if len(frame) else "NO VERIFICABLE",
        "endpoint": "quantile_pinball_log_rv",
        "inference_role": "SECONDARY",
        "tau": 0.90,
        **_counts(frame),
        "contrasts": sequence["contrasts"],
        "sequence": sequence,
        "excluded_sessions": excluded,
        "model_losses": [
            {
                "family": f,
                "information_set": s,
                "mean_pinball": float(means[f"loss__{f}__{s}"].mean()) if len(means) else None,
            }
            for f in FAMILIES
            for s in SETS
        ],
    }


def _jump(records: list[dict[str, Any]], options: InferenceOptions) -> dict[str, Any]:
    frame, excluded = _endpoint_frames(records, "jump")
    families = []
    for family in FAMILIES:
        if len(frame):
            families.append(
                inf.pooled_auc_inference(
                    frame["actual"].to_numpy(),
                    {name: frame[f"forecast__{family}__{name}"].to_numpy() for name in SETS},
                    frame["session_date"].to_numpy(),
                    family=family,
                    **options,
                )
            )
        else:
            families.append(
                {
                    "family": family,
                    "status": "NO VERIFICABLE",
                    "N_sessions": 0,
                    "N_origins": 0,
                    "invalid_class_resamples": 0,
                    "reason": "no completed jump sessions",
                    "auc": {
                        s: {
                            "estimate": None,
                            "ci_low": None,
                            "ci_high": None,
                            "status": "NO VERIFICABLE",
                        }
                        for s in SETS
                    },
                    "contrasts": [
                        {
                            "family": family,
                            "contrast": contrast,
                            "status": "NO VERIFICABLE",
                            "estimate": None,
                            "ci_low": None,
                            "ci_high": None,
                            "p_raw": None,
                            "alternative": "greater",
                            "reason": "no completed jump sessions",
                            "endpoint": "jump_auc",
                            "inference_role": "SECONDARY",
                            "N_sessions": 0,
                            "N_origins": 0,
                        }
                        for contrast, _, _ in CONTRASTS
                    ],
                }
            )
    sequence = inf.family_fixed_sequence(
        [row for family in families for row in family["contrasts"]],
        endpoint="jump_auc",
        primary=False,
    )
    return {
        "status": "COMPUTED" if len(frame) else "NO VERIFICABLE",
        "endpoint": "jump_auc",
        "inference_role": "SECONDARY",
        **_counts(frame),
        "families": families,
        "contrasts": sequence["contrasts"],
        "sequence": sequence,
        "excluded_sessions": excluded,
        "positive_labels": int(frame["actual"].sum()) if len(frame) else 0,
        "negative_labels": int((frame["actual"] == 0).sum()) if len(frame) else 0,
    }


def _mz(records: list[dict[str, Any]], options: InferenceOptions) -> dict[str, Any]:
    frames = []
    family = "lightgbm_qlike"
    for record in records:
        frame = pd.DataFrame(record["keys"])
        actual = _vector(record["target"], len(frame), positive=True)
        frame["actual"] = actual
        if set(record.get("mz_forecasts", {})) != set(SETS):
            raise ValueError("RP4_V3_AGGREGATE_MZ_COMMON_INFORMATION_SETS_REQUIRED")
        for name in SETS:
            raw = _vector(record["forecasts"][family][name], len(frame), positive=True)
            prediction = _vector(record["mz_forecasts"][name], len(frame), positive=True)
            frame[f"raw__{name}"] = qlike_losses(actual, raw)
            frame[f"loss__{name}"] = qlike_losses(actual, prediction)
            frame[f"forecast__{name}"] = prediction
        frames.append(frame)
    frame = pd.concat(frames, ignore_index=True)
    columns = ["actual"] + [
        f"{prefix}__{name}" for name in SETS for prefix in ("raw", "loss", "forecast")
    ]
    session = _means(frame, columns)
    contrasts = []
    for contrast, base, richer in CONTRASTS:
        values = (session[f"loss__{base}"] - session[f"loss__{richer}"]).to_numpy()
        contrasts.append(
            {
                **inf.session_contrast(values, alternative="two-sided", **options),
                "family": family,
                "contrast": contrast,
                "endpoint": "mz_recalibrated_qlike",
                "inference_role": "SECONDARY",
                "p_role": "bilateral_nominal_diagnostic_not_primary",
            }
        )
    return {
        "status": "COMPUTED",
        "inference_role": "SECONDARY",
        **_counts(frame),
        "model_losses": [
            {
                "information_set": name,
                "raw_qlike": float(session[f"raw__{name}"].mean()),
                "recalibrated_qlike": float(session[f"loss__{name}"].mean()),
                "calibration_improvement": float(
                    (session[f"raw__{name}"] - session[f"loss__{name}"]).mean()
                ),
                "calibration_reduction_percent": float(
                    100
                    * (session[f"raw__{name}"] - session[f"loss__{name}"]).mean()
                    / session[f"raw__{name}"].mean()
                )
                if session[f"raw__{name}"].mean() > 0
                else None,
                **_counts(frame),
            }
            for name in SETS
        ],
        "contrasts": contrasts,
        "calibration": {
            name: v1.mincer_zarnowitz(
                session["actual"].to_numpy(),
                session[f"forecast__{name}"].to_numpy(),
            )
            for name in SETS
        },
        "primary_predictions_replaced": False,
    }


def aggregate_records(
    records: list[dict[str, Any]],
    options: Mapping[str, Any],
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Keep v2 bilateral arithmetic intact; add separately labelled registered v3 inference."""
    frame = _frame(records)
    summary, losses = v2.aggregate_records(records, dict(options))
    if frame.empty:
        return summary, losses
    parameters = _options(options)
    comparable = summary["contrasts"]
    primary = _loss_records(frame, parameters, endpoint="qlike_mean", primary=True)
    for row, old in zip(primary, comparable, strict=True):
        if (row["family"], row["contrast"]) != (old["family"], old["contrast"]):
            raise ValueError("RP4_V3_AGGREGATE_V2_CONTRAST_ORDER_DRIFT")
        row.update({key: value for key, value in old.items() if key.startswith(("dm_", "gw_"))})
        row.update(
            baseline_qlike=old["baseline_qlike"],
            expanded_qlike=old["expanded_qlike"],
            qlike_reduction_percent=row["percent_reduction_mean"],
        )
    sequence = inf.family_fixed_sequence(primary)
    posterior = []
    for family in FAMILIES:
        for contrast, base, richer in CONTRASTS:
            values = (
                losses[f"loss__{family}__{base}"] - losses[f"loss__{family}__{richer}"]
            ).to_numpy()
            posterior.append(
                {
                    **inf.posterior_probability_mean(
                        values, minimum_sessions=parameters["minimum_sessions"]
                    ),
                    "family": family,
                    "contrast": contrast,
                    "inference_role": "SECONDARY",
                }
            )
    regimes = _regimes(frame, parameters)
    summary.update(
        {
            "inference_adapter": (
                "v2_exact_bilateral_comparability_plus_registered_v3_directional_sequence"
            ),
            "contrasts": sequence["contrasts"],
            "primary_sequence": sequence,
            "comparability_bilateral": comparable,
            "distribution_secondary": _distribution(
                frame,
                parameters,
                endpoint="qlike_distribution_secondary",
                statistics=STATISTICS[1:],
            ),
            "posterior_mean": posterior,
            "regime_secondary": regimes,
            "empty_window_secondary": _empty_windows(frame, regimes),
            "high_gamma_vs_rest": _high_vs_rest(frame, parameters),
            "quantile_secondary": _quantile(records, parameters),
            "jump_secondary": _jump(records, parameters),
            "mz_secondary": _mz(records, parameters),
            "secondary_can_rescue_primary": False,
            "global_joint_reject": sequence["global_joint_reject"],
            "executed_origins_by_asset": {
                str(asset): int(len(group)) for asset, group in frame.groupby("asset")
            },
        }
    )
    return summary, losses
