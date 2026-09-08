"""One frozen RP4 v2 walk-forward run; reuse v1 inference without modifying v1."""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd  # type: ignore[import-untyped]
from artifacts.rp4_code import evaluate as v1
from artifacts.rp4_v2_code.freeze import REMOVED, V1_SHA
from artifacts.rp4_v2_code.models import fit_lightgbm, fit_ridge

from mds650.metrics import qlike_losses

ROOT = Path(__file__).resolve().parents[2]
FAMILIES = ("log_ridge_harq", "lightgbm_qlike")
LINEAR = FAMILIES[0]
KEYS = v1.KEYS
EVALUATION_SOURCE_PATHS = (
    "artifacts/rp4_v2_code/evaluate_v2.py",
    "artifacts/rp4_v2_code/models.py",
    "artifacts/rp4_v2_code/freeze.py",
    "artifacts/rp4_code/evaluate.py",
    "src/mds650/metrics.py",
    "src/mds650/rp2/inference.py",
    "src/mds650/rp2/qlike_objective.py",
)


def evaluation_code_hashes() -> dict[str, str]:
    return {name: v1.sha256(ROOT / name) for name in EVALUATION_SOURCE_PATHS}


def write_checkpoint(output: Path, session: str, record: dict[str, Any]) -> None:
    encoded = (json.dumps(record, indent=2, sort_keys=True, allow_nan=False) + "\n").encode()
    # Receipt first: an interruption can leave an incomplete computation, never an
    # unpinned completed checkpoint that resume silently blesses after the fact.
    v1.write_json_once(
        output / "session_receipts" / f"{session}.json",
        {
            "session": session,
            "binding": record["binding"],
            "sha256": hashlib.sha256(encoded).hexdigest(),
        },
    )
    v1.write_bytes_once(output / "sessions" / f"{session}.json", encoded)


def read_checkpoint(
    output: Path, session: str, binding: dict[str, Any], expected: pd.DataFrame
) -> dict[str, Any]:
    checkpoint = output / "sessions" / f"{session}.json"
    receipt_path = output / "session_receipts" / f"{session}.json"
    if not receipt_path.exists():
        raise ValueError("RP4_V2_COMPLETED_SESSION_WITHOUT_RECEIPT")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    encoded = checkpoint.read_bytes()
    if receipt != {
        "session": session,
        "binding": binding,
        "sha256": hashlib.sha256(encoded).hexdigest(),
    }:
        raise ValueError("RP4_V2_COMPLETED_SESSION_HASH_OR_BINDING_DRIFT")
    record: dict[str, Any] = json.loads(encoded)
    if record["binding"] != binding or record["session"] != session:
        raise ValueError("RP4_V2_SESSION_BINDING_DRIFT")
    if record["keys"] != expected[KEYS].to_dict("records") or not np.array_equal(
        record["target"], expected["rv30"].to_numpy()
    ):
        raise ValueError("RP4_V2_COMPLETED_SESSION_PANEL_PARITY_DRIFT")
    return record


def v1_secondary_eligibility(panel: pd.DataFrame, spec: dict[str, Any]) -> np.ndarray:
    """Keep the v1 high-flow definition even when v2 recovers more training rows."""
    source = spec["input_panels"]["combined"]
    if v1.sha256(Path(source["path"])) != source["sha256"]:
        raise ValueError("RP4_V2_SECONDARY_REFERENCE_HASH_DRIFT")
    original = pd.read_parquet(source["path"])
    old_spec = json.loads(
        (ROOT / "artifacts/rp4_a1/specification.json").read_text(encoding="utf-8")
    )
    mandatory = [c for c in old_spec["feature_sets"]["B2"] if c not in old_spec["missing_allowed"]]
    old_target = original["rv30"].to_numpy(dtype=float)
    quality = (
        original["rp4_eligible"].fillna(False).to_numpy(dtype=bool)
        if "rp4_eligible" in original
        else np.ones(len(original), dtype=bool)
    )
    original["v1_secondary_eligible"] = (
        np.isfinite(old_target)
        & (old_target > 0)
        & np.isfinite(original[mandatory].to_numpy(dtype=float)).all(axis=1)
        & quality
    )
    joined = panel[KEYS].merge(
        original[KEYS + ["v1_secondary_eligible"]],
        on=KEYS,
        how="left",
        validate="one_to_one",
        sort=False,
    )
    if joined["v1_secondary_eligible"].isna().any() or joined[KEYS].to_dict("records") != panel[
        KEYS
    ].to_dict("records"):
        raise ValueError("RP4_V2_SECONDARY_REFERENCE_KEY_DRIFT")
    result: np.ndarray = np.asarray(joined["v1_secondary_eligible"], dtype=bool)
    return result


def high_flow_membership(
    panel: pd.DataFrame,
    reference_eligible: np.ndarray,
    dates: np.ndarray,
    origins_ns: np.ndarray,
    end_ns: np.ndarray,
    session: str,
    test: np.ndarray,
    embargo_minutes: int,
) -> tuple[list[bool | None], dict[str, float]]:
    old_test = reference_eligible & (dates == session)
    anchor = origins_ns[old_test].min() if old_test.any() else origins_ns[test].min()
    reference_train = (
        reference_eligible
        & (dates < session)
        & (end_ns <= anchor - embargo_minutes * 60 * 1_000_000_000)
    )
    flows = (
        panel.loc[reference_train]
        .groupby(["asset", "session_date"])["previous_day_b2_30m_premium"]
        .mean()
        .dropna()
    )
    thresholds = {
        str(asset): float(group.quantile(2 / 3)) for asset, group in flows.groupby("asset")
    }
    membership = [
        bool(value > thresholds[asset]) if asset in thresholds and np.isfinite(value) else None
        for asset, value in panel.loc[test, ["asset", "previous_day_b2_30m_premium"]].itertuples(
            index=False, name=None
        )
    ]
    return membership, thresholds


def load_spec(path: Path, expected_sha256: str) -> dict[str, Any]:
    if v1.sha256(path) != expected_sha256:
        raise ValueError("RP4_V2_SPECIFICATION_HASH_MISMATCH")
    spec: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    if spec["schema_version"] != "rp4-walkforward-v2":
        raise ValueError("RP4_V2_SCHEMA_REQUIRED")
    checks = {
        ROOT / "docs/rp4/specification_v2.md": spec["specification_md_sha256"],
        ROOT / "docs/rp4/decision_130_v2.md": spec["decision_sha256"],
        ROOT / "artifacts/rp4_a1/specification.json": V1_SHA,
    }
    if any(v1.sha256(p) != digest for p, digest in checks.items()):
        raise ValueError("RP4_V2_FROZEN_DOCUMENT_DRIFT")
    frozen = json.loads((path.parent / "freeze.json").read_text(encoding="utf-8"))
    if frozen["specification_sha256"] != expected_sha256:
        raise ValueError("RP4_V2_FREEZE_MISMATCH")
    old = json.loads((ROOT / "artifacts/rp4_a1/specification.json").read_text(encoding="utf-8"))
    for key in (
        "windows",
        "assets",
        "inference",
        "purge_minutes",
        "embargo_minutes",
        "source_cutoff_seconds",
    ):
        if spec[key] != old[key]:
            raise ValueError(f"RP4_V2_OUT_OF_SCOPE_CHANGE:{key}")
    for name in v1.SETS:
        expected = [c for c in old["feature_sets"][name] if c not in REMOVED]
        if spec["feature_sets"][name] != expected:
            raise ValueError(f"RP4_V2_FEATURE_ALLOWLIST_DRIFT:{name}")
    if spec["mandatory_predictors"] != spec["feature_sets"]["B0"]:
        raise ValueError("RP4_V2_MANDATORY_DRIFT")
    if set(spec["missing_allowed"]) != set(spec["feature_sets"]["B2"]) - set(
        spec["feature_sets"]["B0"]
    ):
        raise ValueError("RP4_V2_OPTIONAL_DRIFT")
    return spec


def aggregate_records(
    records: list[dict[str, Any]], options: dict[str, Any]
) -> tuple[dict[str, Any], pd.DataFrame]:
    """Adapt the family name only; v1 bootstrap/Holm/MZ/DM/GW code is unchanged."""
    adapted = []
    for record in records:
        adapted.append(
            {
                **record,
                "forecasts": {
                    "log_ols_harq": record["forecasts"][LINEAR],
                    "lightgbm_qlike": record["forecasts"]["lightgbm_qlike"],
                },
            }
        )
    summary, losses = v1.aggregate_records(adapted, options)

    def rename(value: Any) -> Any:
        if isinstance(value, dict):
            return {k.replace("log_ols_harq", LINEAR): rename(v) for k, v in value.items()}
        if isinstance(value, list):
            return [rename(v) for v in value]
        if isinstance(value, str):
            return value.replace("log_ols_harq", LINEAR)
        return value

    summary = rename(summary)
    losses = losses.rename(columns=lambda x: x.replace("log_ols_harq", LINEAR))
    summary["inference_adapter"] = "v1_exact_arithmetic_with_explicit_new_linear_family_name"
    if losses.empty:
        summary.update({"tail_secondary": [], "top_loss_sessions": []})
        return summary, losses
    tails = []
    top = []
    for family in FAMILIES:
        for label, base, expanded in v1.CONTRASTS:
            delta = (
                losses[f"loss__{family}__{base}"] - losses[f"loss__{family}__{expanded}"]
            ).to_numpy()
            trim = int(np.floor(0.05 * len(delta)))
            ordered = np.sort(delta)
            kept = ordered[trim : len(ordered) - trim] if trim else ordered
            tails.append(
                {
                    "family": family,
                    "contrast": label,
                    "N_sessions": len(delta),
                    "median_paired_contrast": float(np.median(delta)),
                    "trimmed_mean_5pct_each_tail": float(kept.mean()),
                    "removed_each_tail": trim,
                }
            )
        for ranking_set in v1.SETS:
            worst = losses.sort_values(
                [f"loss__{family}__{ranking_set}", "session_date"], ascending=[False, True]
            ).head(10)
            for rank, row in enumerate(worst.to_dict("records"), 1):
                result = {
                    "family": family,
                    "ranked_information_set": ranking_set,
                    "rank": rank,
                    "session_date": row["session_date"],
                }
                for information_set in v1.SETS:
                    result[f"qlike_{information_set}"] = row[f"loss__{family}__{information_set}"]
                for label, base, expanded in v1.CONTRASTS:
                    delta = result[f"qlike_{base}"] - result[f"qlike_{expanded}"]
                    result[label] = delta
                    result[label + "_sign"] = int(np.sign(delta))
                top.append(result)
    summary["tail_secondary"] = tails
    summary["top_loss_sessions"] = top
    return summary, losses


def panel_masks(
    panel: pd.DataFrame, specification: dict[str, Any]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    target = panel["rv30"].to_numpy(dtype=float)
    valid_target = np.isfinite(target) & (target > 0)
    complete = np.isfinite(panel[specification["mandatory_predictors"]].to_numpy(dtype=float)).all(
        axis=1
    )
    quality = (
        panel["rp4_eligible"].fillna(False).to_numpy(dtype=bool)
        if "rp4_eligible" in panel
        else np.ones(len(panel), dtype=bool)
    )
    return valid_target & complete & quality, valid_target, complete, quality


def run(args: argparse.Namespace) -> dict[str, Any]:
    spec = load_spec(args.spec, args.spec_sha256)
    if (
        v1.ROOT != ROOT
        or Path(inspect.getfile(qlike_losses)).resolve() != ROOT / "src/mds650/metrics.py"
    ):
        raise ValueError("RP4_V2_IMPORT_OUTSIDE_BOUND_CHECKOUT")
    if args.threads != spec["model"]["lightgbm"]["num_threads"]:
        raise ValueError("RP4_V2_THREAD_COUNT_DRIFT")
    if (
        args.shard_count < 1
        or (args.shard_index is not None and not 0 <= args.shard_index < args.shard_count)
        or (args.shard_index is not None and args.aggregate_only)
        or (args.shard_count > 1 and args.shard_index is None and not args.aggregate_only)
    ):
        raise ValueError("RP4_V2_INVALID_SESSION_SHARD")
    root = Path(spec["data_root"]).resolve()
    output = args.output.resolve()
    if (
        output == root
        or not output.is_relative_to(root)
        or (os.name == "nt" and output.drive.lower() != "d:")
    ):
        raise ValueError("RP4_V2_OUTPUT_OUTSIDE_PRIVATE_NEW_ROOT")
    public_output = args.public_output.resolve()
    public_artifacts = ROOT / "artifacts"
    in_public_v2 = (
        public_output != public_artifacts
        and public_output.is_relative_to(public_artifacts)
        and public_output.relative_to(public_artifacts).parts[0].startswith("rp4_v2_")
    )
    if not (public_output.is_relative_to(root) or in_public_v2):
        raise ValueError("RP4_V2_PUBLIC_OUTPUT_OUTSIDE_NEW_SCOPE")
    if args.panel.resolve() != root / "materialized/panel.parquet":
        raise ValueError("RP4_V2_FILTERED_PANEL_REQUIRED")
    manifest_path = args.panel.parent / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    panel_sha = v1.sha256(args.panel)
    # The materializer's manifest is separately pinned by the release, not trusted by filename.
    release = json.loads(args.release.read_text(encoding="utf-8"))
    if release["panel_sha256"] != panel_sha or release[
        "materialization_manifest_sha256"
    ] != v1.sha256(manifest_path):
        raise ValueError("RP4_V2_PANEL_RELEASE_MISMATCH")
    if release["specification_sha256"] != args.spec_sha256:
        raise ValueError("RP4_V2_RELEASE_SPEC_MISMATCH")
    execution = {"session_shards": args.shard_count, "threads_per_model": args.threads}
    if release["execution"] != execution:
        raise ValueError("RP4_V2_RELEASE_EXECUTION_DRIFT")
    code_hashes = evaluation_code_hashes()
    if release["evaluation_code_sha256"] != code_hashes:
        raise ValueError("RP4_V2_RELEASE_CODE_DRIFT")
    binding = {
        "panel_sha256": panel_sha,
        "specification_sha256": args.spec_sha256,
        "release_sha256": v1.sha256(args.release),
        "window": args.window,
        "code_sha256": code_hashes,
        "execution": execution,
    }
    try:
        v1.write_json_once(output / "binding.json", binding)
    except FileExistsError:
        # Another session shard may publish the same binding concurrently.
        v1.write_json_once(output / "binding.json", binding)
    panel = pd.read_parquet(args.panel)
    required = set(
        KEYS + ["rv30", "forecast_origin_utc", "target_end_utc"] + spec["feature_sets"]["B2"]
    )
    if missing := required - set(panel.columns):
        raise ValueError(f"RP4_V2_PANEL_COLUMNS_MISSING:{sorted(missing)}")
    if panel.duplicated(KEYS).any():
        raise ValueError("RP4_V2_DUPLICATE_KEYS")
    panel["session_date"] = panel["session_date"].astype(str)
    window = spec["windows"][args.window]
    panel = (
        panel[
            (panel["session_date"] >= spec["windows"]["primary"]["start"])
            & (panel["session_date"] <= window["end"])
        ]
        .sort_values(["session_date", "asset", "origin_minute"])
        .reset_index(drop=True)
    )
    origins = pd.to_datetime(panel["forecast_origin_utc"], utc=True)
    end = pd.to_datetime(panel["target_end_utc"], utc=True)
    if (
        origins.isna().any()
        or end.isna().any()
        or not ((end - origins) == pd.Timedelta(minutes=30)).all()
    ):
        raise ValueError("RP4_V2_TARGET_INTERVAL_INVALID")
    origins_ns, end_ns = (x.dt.as_unit("ns").astype("int64").to_numpy() for x in (origins, end))
    dates, assets = panel["session_date"].to_numpy(), panel["asset"].to_numpy()
    if set(assets) - set(spec["assets"]):
        raise ValueError("RP4_V2_UNKNOWN_ASSET")
    target = panel["rv30"].to_numpy(dtype=float)
    eligible, valid_target, complete, quality = panel_masks(panel, spec)
    secondary_eligible = (
        v1_secondary_eligibility(panel, spec)
        if "previous_day_b2_30m_premium" in panel
        else eligible
    )
    optional = set(spec["missing_allowed"])
    asset_design = np.column_stack(
        [(assets == asset).astype(float) for asset in spec["assets"][1:]]
    )
    designs, linear_designs = {}, {}
    for name in v1.SETS:
        names = spec["feature_sets"][name]
        values = panel[names].to_numpy(dtype=float).copy()
        values[~np.isfinite(values)] = np.nan
        designs[name] = np.column_stack([values, asset_design])
        linear_designs[name] = np.column_stack(
            [v1.transform_ols(values, names, spec["feature_transforms"]), asset_design]
        )
    scheduled = sorted(set(dates[(dates >= window["start"]) & (dates <= window["end"])]))[
        window["warmup_sessions"] :
    ]
    records, skipped, fit_rows = [], [], []
    local = origins.dt.tz_convert("America/New_York")
    first_hour = (
        (local.dt.hour * 60 + local.dt.minute >= 570) & (local.dt.hour * 60 + local.dt.minute < 630)
    ).to_numpy()
    assigned = (
        scheduled if args.shard_index is None else scheduled[args.shard_index :: args.shard_count]
    )
    for session in assigned:
        checkpoint = output / "sessions" / f"{session}.json"
        if checkpoint.exists():
            record = read_checkpoint(
                output, session, binding, panel.loc[eligible & (dates == session)]
            )
            records.append(record)
            print(f"RP4_V2_REUSED_COMPLETE_SESSION:{session}", flush=True)
            continue
        if not (eligible & (dates == session)).any():
            skipped.append({"session": session, "reason": "no eligible origins"})
            continue
        try:
            train, inner_fit, inner_valid, test = v1.causal_masks(
                dates,
                origins_ns,
                end_ns,
                eligible,
                session,
                embargo_minutes=spec["embargo_minutes"],
                validation_sessions=spec["model"]["tuning_sessions"],
            )
        except ValueError as error:
            if str(error) not in {
                "RP4_INSUFFICIENT_TRAINING_SESSIONS",
                "RP4_INNER_TRAINING_EMPTY_AFTER_EMBARGO",
            }:
                raise
            skipped.append({"session": session, "reason": str(error)})
            continue
        if args.aggregate_only:
            raise ValueError(f"RP4_V2_AGGREGATION_MISSING_COMPLETED_SESSION:{session}")
        forecasts: dict[str, Any] = {family: {} for family in FAMILIES}
        fits = {}
        for information_set in v1.SETS:
            nullable_indices = [
                i
                for i, name in enumerate(spec["feature_sets"][information_set])
                if name in optional
            ]
            for family in FAMILIES:
                if family == LINEAR:
                    prediction, fitted = fit_ridge(
                        linear_designs[information_set],
                        target,
                        train,
                        inner_fit,
                        inner_valid,
                        test,
                        nullable_indices,
                        dates,
                        assets,
                        spec["model"]["ridge"],
                    )
                else:
                    prediction, fitted = fit_lightgbm(
                        designs[information_set],
                        target,
                        train,
                        inner_fit,
                        inner_valid,
                        test,
                        dates,
                        assets,
                        spec["model"]["lightgbm"],
                        threads=args.threads,
                    )
                if prediction.shape != (int(test.sum()),):
                    raise ValueError("RP4_V2_FORECAST_SHAPE_MISMATCH")
                if not np.isfinite(prediction).all() or (prediction <= 0).any():
                    raise ValueError("RP4_V2_NONPOSITIVE_NONFINITE_FORECAST")
                forecasts[family][information_set] = prediction.tolist()
                fits[f"{family}__{information_set}"] = fitted
        high_flow: list[bool | None] = [None] * int(test.sum())
        thresholds: dict[str, float] = {}
        if "previous_day_b2_30m_premium" in panel:
            high_flow, thresholds = high_flow_membership(
                panel,
                secondary_eligible,
                dates,
                origins_ns,
                end_ns,
                session,
                test,
                spec["embargo_minutes"],
            )
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
            "high_flow_training_thresholds_by_asset": thresholds,
            "max_training_target_end_utc": str(end[train].max()),
            "first_evaluation_origin_utc": str(origins[test].min()),
        }
        write_checkpoint(output, session, record)
        records.append(record)
        print(f"RP4_V2_COMPLETED_SESSION:{session}:origins={int(test.sum())}", flush=True)
    if args.shard_index is not None:
        result = {
            "status": "RP4_V2_SESSION_SHARD_COMPLETE",
            "window": args.window,
            "shard_index": args.shard_index,
            "shard_count": args.shard_count,
            "assigned_sessions": len(assigned),
            "completed_sessions": len(records),
            "skipped_sessions": skipped,
            "binding": binding,
        }
        v1.write_json_once(output / "shards" / f"{args.shard_index}.json", result)
        print(json.dumps(result), flush=True)
        return result
    summary, session_losses = aggregate_records(records, spec["inference"])
    summary.update(
        {
            "binding": binding,
            "result_label": spec["label"],
            "window": args.window,
            "scheduled_sessions": len(scheduled),
            "skipped_sessions": skipped,
            "materialization_manifest_sha256": v1.sha256(manifest_path),
            "materialization_status": manifest.get("status", "RECORDED_IN_MANIFEST"),
            "quality_gate_column_present": "rp4_eligible" in panel,
            "evaluation_quality_by_asset": [
                {
                    "asset": asset,
                    "scheduled_rows": int(mask.sum()),
                    "eligible_rows": int((mask & eligible).sum()),
                    "invalid_target": int((mask & ~valid_target).sum()),
                    "incomplete_mandatory_predictors": int((mask & ~complete).sum()),
                    "failed_quality_gate": int((mask & ~quality).sum()),
                }
                for asset in spec["assets"]
                for mask in [(assets == asset) & np.isin(dates, scheduled)]
            ],
            "completed_session_sha256": {
                p.name: v1.sha256(p) for p in sorted((output / "sessions").glob("*.json"))
            },
        }
    )
    for record in records:
        for name, fit in sorted(record["fits"].items()):
            fit_rows.append({"session": record["session"], "model": name, **fit})
    v1.write_json_once(args.public_output / "summary.json", summary)
    v1.write_bytes_once(
        args.public_output / "session_losses.csv", session_losses.to_csv(index=False).encode()
    )
    v1.write_json_once(output / "fit_diagnostics.json", fit_rows)
    print(
        json.dumps(
            {
                "status": "RP4_V2_WINDOW_COMPLETE",
                "window": args.window,
                "N_sessions": len(records),
                "summary_sha256": v1.sha256(args.public_output / "summary.json"),
            }
        ),
        flush=True,
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--spec-sha256", required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--window", choices=("primary", "confirmation"), required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--public-output", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--shard-count", type=int, default=1)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--shard-index", type=int)
    mode.add_argument("--aggregate-only", action="store_true")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
