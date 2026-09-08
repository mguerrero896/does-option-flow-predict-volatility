"""Mean-QLIKE-only RP4 v4 aggregation; no fits, target construction, MZ, or tail endpoints."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import numpy as np
import pandas as pd  # type: ignore[import-untyped]
from artifacts.rp4_code import evaluate as v1
from artifacts.rp4_v3_code import aggregate_v3 as v3
from artifacts.rp4_v3_code import inference as inf

from mds650.metrics import holm_adjust

FAMILIES, SETS, CONTRASTS = inf.FAMILIES, inf.SETS, inf.CONTRASTS


def _contract(records: list[dict[str, Any]]) -> tuple[int, str, str]:
    first = records[0]
    horizon, target_key = first.get("horizon_minutes"), first.get("target_key")
    window = first.get("binding", {}).get("window")
    if type(horizon) is not int or horizon not in (5, 15) or target_key != f"rv_{horizon}":
        raise ValueError("RP4_V4_AGGREGATE_TARGET_HORIZON_CONTRACT")
    if window not in ("primary", "confirmation"):
        raise ValueError("RP4_V4_AGGREGATE_WINDOW_REQUIRED")
    for record in records:
        if (
            type(record.get("horizon_minutes")) is not int
            or record.get("horizon_minutes") != horizon
            or record.get("target_key") != target_key
            or record.get("binding") != first["binding"]
        ):
            raise ValueError("RP4_V4_AGGREGATE_MIXED_TARGET_OR_BINDING")
        for key, expected in (("horizon_minutes", horizon), ("target_key", target_key)):
            if key in record["binding"] and record["binding"][key] != expected:
                raise ValueError("RP4_V4_AGGREGATE_TARGET_BINDING_DRIFT")
        if any(not name.startswith("mean__") for name in record.get("fits", {})):
            raise ValueError("RP4_V4_AGGREGATE_MEAN_ONLY_FITS")
    return horizon, target_key, window


def _comparability(
    frame: pd.DataFrame, session: pd.DataFrame, parameters: v3.InferenceOptions
) -> list[dict[str, Any]]:
    """Literal legacy mean-inference arithmetic, without its full MZ aggregator."""
    results = []
    for family in FAMILIES:
        for contrast, base, rich in CONTRASTS:
            baseline = session[f"loss__{family}__{base}"].to_numpy()
            expanded = session[f"loss__{family}__{rich}"].to_numpy()
            result = v1.mean_inference(baseline - expanded, **parameters)
            result.update(
                family=family,
                contrast=contrast,
                baseline_qlike=float(baseline.mean()),
                expanded_qlike=float(expanded.mean()),
                N_origins=len(frame),
                N_asset_sessions=len(frame[["asset", "session_date"]].drop_duplicates()),
                qlike_reduction_percent=float(
                    100 * (baseline.mean() - expanded.mean()) / baseline.mean()
                )
                if baseline.mean() > 0
                else None,
            )
            results.append(result)
    adjusted = holm_adjust(
        {f"{r['family']}__{r['contrast']}": r.get("p_raw", 1.0) for r in results}
    )
    for result in results:
        result["p_holm"] = (
            adjusted[f"{result['family']}__{result['contrast']}"] if "p_raw" in result else None
        )
    return results


def _descriptives(
    frame: pd.DataFrame, session: pd.DataFrame, numeric: list[str]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Preserve the v1/v2 descriptive fields, including unknown-group accounting."""
    secondary_results: list[dict[str, Any]] = []
    for name in ("first_hour", "high_flow", "event"):
        membership = frame[name]
        known = membership.notna()
        member = membership.eq(True).fillna(False)
        subset = frame.loc[known & member]
        unknown = int((~known).sum())
        coverage = {
            "N_available_origins": len(frame),
            "N_verified_membership_origins": int(known.sum()),
            "N_unknown_membership_origins": unknown,
            "N_verified_nonmember_origins": int((known & ~member).sum()),
            "N_excluded_from_subset_origins": len(frame) - len(subset),
            "N_unknown_membership_sessions": int(frame.loc[~known, "session_date"].nunique()),
            "coverage_status": "PARTIAL_COVERAGE" if unknown else "COMPLETE_COVERAGE",
        }
        if subset.empty:
            secondary_results.append(
                {
                    "subset": name,
                    "status": "NO VERIFICABLE",
                    "reason": "no verified member origins",
                    **coverage,
                }
            )
            continue
        means = v3._means(subset, numeric)
        for family in FAMILIES:
            for contrast, base, rich in CONTRASTS:
                baseline = means[f"loss__{family}__{base}"].to_numpy()
                expanded = means[f"loss__{family}__{rich}"].to_numpy()
                secondary_results.append(
                    {
                        "subset": name,
                        "status": "PARTIAL_COVERAGE" if unknown else "COMPUTED",
                        **coverage,
                        "family": family,
                        "contrast": contrast,
                        "estimate": float((baseline - expanded).mean()),
                        "qlike_reduction_percent": float(
                            100 * (baseline - expanded).mean() / baseline.mean()
                        )
                        if baseline.mean() > 0
                        else None,
                        "N_sessions": len(means),
                        "N_origins": len(subset),
                    }
                )
    size = len(session) // 3
    blocks = [session.index[:size], session.index[size : 2 * size], session.index[2 * size :]]
    subsets = {
        f"asset_{asset}": frame[frame["asset"] == asset]
        for asset in sorted(frame["asset"].unique())
    }
    subsets["last30sessions"] = frame[frame["session_date"].isin(session.index[-30:])]
    for index, block in enumerate(blocks, 1):
        subsets[f"chronological_block_{index}"] = frame[frame["session_date"].isin(block)]
        subsets[f"leave_block_{index}_out"] = frame[~frame["session_date"].isin(block)]
    robustness: list[dict[str, Any]] = []
    for name, subset in subsets.items():
        if subset.empty:
            robustness.append(
                {"subset": name, "status": "NO VERIFICABLE", "reason": "empty subset"}
            )
            continue
        means = v3._means(subset, numeric)
        for family in FAMILIES:
            for contrast, base, rich in CONTRASTS:
                baseline = means[f"loss__{family}__{base}"].to_numpy()
                expanded = means[f"loss__{family}__{rich}"].to_numpy()
                robustness.append(
                    {
                        "subset": name,
                        "family": family,
                        "contrast": contrast,
                        "estimate": float((baseline - expanded).mean()),
                        "N_origins": len(subset),
                        "N_sessions": len(means),
                        "N_asset_sessions": len(
                            subset[["asset", "session_date"]].drop_duplicates()
                        ),
                        "qlike_reduction_percent": float(
                            100 * (baseline - expanded).mean() / baseline.mean()
                        )
                        if baseline.mean() > 0
                        else None,
                    }
                )
    return secondary_results, robustness


def _tail_descriptives(losses: pd.DataFrame) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Distribution of primary QLIKE, not a quantile or jump-model endpoint."""
    tails, top = [], []
    for family in FAMILIES:
        for contrast, base, rich in CONTRASTS:
            delta = (
                losses[f"loss__{family}__{base}"] - losses[f"loss__{family}__{rich}"]
            ).to_numpy()
            trim = int(np.floor(0.05 * len(delta)))
            ordered = np.sort(delta)
            kept = ordered[trim : len(ordered) - trim] if trim else ordered
            tails.append(
                {
                    "family": family,
                    "contrast": contrast,
                    "N_sessions": len(delta),
                    "median_paired_contrast": float(np.median(delta)),
                    "trimmed_mean_5pct_each_tail": float(kept.mean()),
                    "removed_each_tail": trim,
                }
            )
        for information_set in SETS:
            worst = losses.sort_values(
                [f"loss__{family}__{information_set}", "session_date"], ascending=[False, True]
            ).head(10)
            for rank, row in enumerate(worst.to_dict("records"), 1):
                item = {
                    "family": family,
                    "ranked_information_set": information_set,
                    "rank": rank,
                    "session_date": row["session_date"],
                }
                for name in SETS:
                    item[f"qlike_{name}"] = row[f"loss__{family}__{name}"]
                for contrast, base, rich in CONTRASTS:
                    delta_value = item[f"qlike_{base}"] - item[f"qlike_{rich}"]
                    item[contrast] = delta_value
                    item[contrast + "_sign"] = int(np.sign(delta_value))
                top.append(item)
    return tails, top


def aggregate_records(
    records: list[dict[str, Any]], options: Mapping[str, Any]
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Aggregate one registered horizon/window without invoking excluded endpoints."""
    if not records:
        return {
            "status": "NO VERIFICABLE",
            "reason": "no evaluated session",
            "contrasts": [],
            "endpoint_scope": ["mean"],
            "global_joint_reject": False,
            "predeclared_closure": {
                "status": "NO VERIFICABLE",
                "applies": False,
                "satisfied": None,
            },
            "RESEARCH_ONLY": True,
            "capital_go": False,
        }, pd.DataFrame()
    horizon, target_key, window = _contract(records)
    parameters = v3._options(options)
    frame = v3._frame(records)
    numeric = [column for column in frame if column.startswith(("loss__", "forecast__"))] + [
        "actual"
    ]
    session = v3._means(frame, numeric)
    losses = session.reset_index()
    comparable = _comparability(frame, session, parameters)
    primary = v3._loss_records(frame, parameters, endpoint="qlike_mean", primary=horizon == 15)
    for row, old in zip(primary, comparable, strict=True):
        row.update({key: value for key, value in old.items() if key.startswith(("dm_", "gw_"))})
        row.update(
            baseline_qlike=old["baseline_qlike"],
            expanded_qlike=old["expanded_qlike"],
            qlike_reduction_percent=row["percent_reduction_mean"],
        )
    sequence = inf.family_fixed_sequence(primary, primary=horizon == 15)
    successful = [family for family in FAMILIES if sequence["families"][family]["both_rejected"]]
    applies = horizon == 15 and window == "primary"
    posterior = []
    for family in FAMILIES:
        for contrast, base, rich in CONTRASTS:
            delta = (
                losses[f"loss__{family}__{base}"] - losses[f"loss__{family}__{rich}"]
            ).to_numpy()
            posterior.append(
                {
                    **inf.posterior_probability_mean(
                        delta, minimum_sessions=parameters["minimum_sessions"]
                    ),
                    "family": family,
                    "contrast": contrast,
                    "inference_role": "SECONDARY",
                }
            )
    secondary, robustness = _descriptives(frame, session, numeric)
    tails, top = _tail_descriptives(losses)
    regimes = v3._regimes(frame, parameters)
    summary = {
        "status": "COMPUTED",
        **v3._counts(frame),
        "first_session": str(session.index.min()),
        "last_session": str(session.index.max()),
        "target_key": target_key,
        "horizon_minutes": horizon,
        "window": window,
        "target_horizon_role": "PRIMARY" if horizon == 15 else "SECONDARY",
        "endpoint_scope": ["mean"],
        "inference_adapter": (
            "v1_exact_bilateral_mean_and_v3_pure_QLIKE_helpers_no_MZ_or_tail_models"
        ),
        "contrasts": sequence["contrasts"],
        "primary_sequence": sequence,
        "global_joint_reject": sequence["global_joint_reject"],
        "global_joint_role": "ALL_FAMILIES_DIAGNOSTIC_NOT_V4_CLOSURE",
        "predeclared_closure": {
            "rule": "both_contrasts_reject_in_at_least_one_family_at_15min_primary",
            "applies": applies,
            "status": ("SATISFIED" if successful else "NOT_SATISFIED")
            if applies
            else "NOT_APPLICABLE",
            "satisfied": bool(successful) if applies else None,
            "at_least_one_family_rejects": bool(successful),
            "successful_families": successful,
            "global_alpha_0_05_control_claimed": False,
        },
        "comparability_bilateral": comparable,
        "distribution_secondary": v3._distribution(
            frame, parameters, endpoint="qlike_distribution_secondary", statistics=v3.STATISTICS[1:]
        ),
        "posterior_mean": posterior,
        "regime_secondary": regimes,
        "empty_window_secondary": v3._empty_windows(frame, regimes),
        "high_gamma_vs_rest": v3._high_vs_rest(frame, parameters),
        "secondary": secondary,
        "robustness": robustness,
        "tail_secondary": tails,
        "top_loss_sessions": top,
        "secondary_can_rescue_primary": False,
        "executed_origins_by_asset": {
            str(asset): int(len(group)) for asset, group in frame.groupby("asset")
        },
        "excluded_endpoint_diagnostics": [
            "mincer_zarnowitz",
            "mz_secondary",
            "quantile_secondary",
            "jump_secondary",
        ],
        "RESEARCH_ONLY": True,
        "capital_go": False,
        "disclaimer": "NOT INVESTMENT ADVICE",
    }
    return summary, losses
