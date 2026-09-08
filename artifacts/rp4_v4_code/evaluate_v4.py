"""Target-explicit RP4 v4 mean-only runner; immutable v3 masks and model inputs."""

from __future__ import annotations

import argparse
import copy
import hashlib
import inspect
import json
from functools import partial
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd  # type: ignore[import-untyped]
from artifacts.rp4_code import evaluate as v1
from artifacts.rp4_v2_code import evaluate_v2 as v2
from artifacts.rp4_v2_code.models import fit_lightgbm
from artifacts.rp4_v3_code import evaluate_v3 as v3
from artifacts.rp4_v3_code.models import fit_ridge

ROOT = Path(__file__).resolve().parents[2]
KEYS, FAMILIES, SETS = v1.KEYS, v2.FAMILIES, v1.SETS
SHARDS, THREADS = 8, 4
PARENT_SHA = "930f3ddb6ef6284f1129dda26ed705699a666ade005c6ad363cb67864794e6f5"
FREEZE_SHA = "830a87bd9c091d897739cbab2160d49ab32ae08550d5d4e4dd0bc8e8fc32468a"
SOURCE_PATHS = tuple(
    dict.fromkeys(
        (
            *v3.SOURCE_PATHS,
            "artifacts/rp4_v4_code/evaluate_v4.py",
            "artifacts/rp4_v4_code/execute.py",
            "artifacts/rp4_v4_code/aggregate_v4.py",
            "artifacts/rp4_v2_code/execute.py",
            "artifacts/rp4_v4_code/freeze.py",
            "artifacts/rp4_v4_code/materialize_targets.py",
        )
    )
)


def evaluation_code_hashes() -> dict[str, str]:
    return {name: v1.sha256(ROOT / name) for name in SOURCE_PATHS}


def horizon_contract(spec: dict[str, Any], horizon: int) -> tuple[str, str]:
    if horizon not in (5, 15):
        raise ValueError("RP4_V4_UNREGISTERED_HORIZON")
    rule = spec["horizons"][str(horizon)]
    expected = (f"rv_{horizon}", f"target_end_{horizon}_utc")
    if (rule["target_key"], rule["target_end_key"]) != expected:
        raise ValueError("RP4_V4_TARGET_COLUMN_DRIFT")
    return expected


def load_spec(path: Path, expected_sha256: str) -> dict[str, Any]:
    if v1.sha256(path) != expected_sha256:
        raise ValueError("RP4_V4_SPECIFICATION_HASH_MISMATCH")
    spec: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    if spec.get("schema_version") != "rp4-walkforward-v4":
        raise ValueError("RP4_V4_SCHEMA_REQUIRED")
    parent_path = ROOT / "artifacts/rp4_v3_a1_empty_window/specification.json"
    parent = v3.load_spec(parent_path, PARENT_SHA)
    if (
        Path(spec["parent_specification"]["path"]).resolve() != parent_path
        or spec["parent_specification"]["sha256"] != PARENT_SHA
    ):
        raise ValueError("RP4_V4_PARENT_SPECIFICATION_DRIFT")
    freeze_path = path.parent / "freeze_manifest.json"
    frozen = json.loads(freeze_path.read_text(encoding="utf-8"))
    if frozen["specification_sha256"] != expected_sha256 or v1.sha256(freeze_path) != FREEZE_SHA:
        raise ValueError("RP4_V4_FREEZE_MISMATCH")
    documents = {
        spec["specification_md_path"]: spec["specification_md_sha256"],
        "docs/rp4/decision_133_v4.md": spec["decision_sha256"],
    }
    if any(v1.sha256(ROOT / name) != digest for name, digest in documents.items()):
        raise ValueError("RP4_V4_DOCUMENT_DRIFT")
    inherited_model = copy.deepcopy(parent["model"])
    inherited_model.pop("mz_secondary")
    inherited_model["lightgbm"]["initial_score"] = "log_training_mean_selected_target"
    inherited_model["ridge"]["forecast_bounds_reference"] = (
        "positive_training_selected_target_linear_quantiles"
    )
    if spec["model"] != inherited_model or spec["endpoint_scope"] != ["mean"]:
        raise ValueError("RP4_V4_MODEL_OR_ENDPOINT_DRIFT")
    for name in (
        "feature_sets",
        "feature_transforms",
        "mandatory_predictors",
        "missing_allowed",
        "assets",
        "windows",
        "purge_minutes",
        "embargo_minutes",
        "source_cutoff_seconds",
        "secondary",
    ):
        if spec[name] != parent[name]:
            raise ValueError(f"RP4_V4_INHERITED_CONTRACT_DRIFT:{name}")
    if [len(spec["feature_sets"][name]) for name in SETS] != [29, 69, 138]:
        raise ValueError("RP4_V4_FEATURE_WIDTH_DRIFT")
    if Path(spec["base_panel"]["path"]).resolve() != v3.evaluation_panel_path(parent):
        raise ValueError("RP4_V4_BASE_PANEL_PATH_DRIFT")
    if spec["execution"] != {
        "session_shards": SHARDS,
        "threads_per_model": THREADS,
        "order": ["15/primary", "15/confirmation", "5/primary", "5/confirmation"],
    }:
        raise ValueError("RP4_V4_EXECUTION_CONTRACT_DRIFT")
    if (
        spec["mask_policy"]
        != "exact_v3_eligibility_and_30min_causal_end_require_selected_target_finite_positive"
    ):
        raise ValueError("RP4_V4_MASK_POLICY_DRIFT")
    if set(spec["horizons"]) != {"5", "15"}:
        raise ValueError("RP4_V4_HORIZON_SET_DRIFT")
    for horizon in (5, 15):
        horizon_contract(spec, horizon)
    if spec["target_panel_relative_path"] != "targets/panel.parquet":
        raise ValueError("RP4_V4_TARGET_PANEL_PATH_DRIFT")
    return spec


def target_panel_path(spec: dict[str, Any]) -> Path:
    return Path(spec["data_root"]).resolve() / str(spec["target_panel_relative_path"])


def prepare_panel(
    base: pd.DataFrame, targets: pd.DataFrame, spec: dict[str, Any], horizon: int
) -> tuple[Any, ...]:
    """Join only by keys; new targets never influence the inherited row mask."""
    target_key, end_key = horizon_contract(spec, horizon)
    required = set(
        KEYS + ["rv30", "forecast_origin_utc", "target_end_utc"] + spec["feature_sets"]["B2"]
    )
    if missing := required - set(base):
        raise ValueError(f"RP4_V4_BASE_MISSING_COLUMNS:{sorted(missing)}")
    if missing := set(KEYS + [target_key, end_key]) - set(targets):
        raise ValueError(f"RP4_V4_TARGET_MISSING_COLUMNS:{sorted(missing)}")
    base, targets = base.copy(), targets.copy()
    base["session_date"] = base["session_date"].astype(str)
    targets["session_date"] = targets["session_date"].astype(str)
    if base.duplicated(KEYS).any() or targets.duplicated(KEYS).any():
        raise ValueError("RP4_V4_DUPLICATE_KEYS")
    base = base.sort_values(["session_date", "asset", "origin_minute"]).reset_index(drop=True)
    joined = base[KEYS].merge(
        targets[KEYS + [target_key, end_key]],
        on=KEYS,
        how="left",
        validate="one_to_one",
        sort=False,
        indicator=True,
    )
    if (
        len(base) != len(targets)
        or not joined["_merge"].eq("both").all()
        or not joined[KEYS].equals(base[KEYS])
    ):
        raise ValueError("RP4_V4_TARGET_KEY_SET_OR_ORDER_DRIFT")
    eligible, valid_original, complete, quality = v2.panel_masks(base, spec)
    target = joined[target_key].to_numpy(dtype=float)
    invalid = eligible & ~(np.isfinite(target) & (target > 0))
    if invalid.any():
        census = {
            "horizon_minutes": horizon,
            "invalid_eligible_origins": int(invalid.sum()),
            "invalid_eligible_sessions": int(base.loc[invalid, "session_date"].nunique()),
            "by_asset": {
                str(a): int(n) for a, n in base.loc[invalid].groupby("asset").size().items()
            },
        }
        raise ValueError(
            "RP4_V4_TARGET_INVALID_ON_INHERITED_MASK:" + json.dumps(census, sort_keys=True)
        )
    origins = pd.to_datetime(base["forecast_origin_utc"], utc=True)
    original_ends = pd.to_datetime(base["target_end_utc"], utc=True)
    selected_ends = pd.to_datetime(joined[end_key], utc=True)
    if (
        origins.isna().any()
        or original_ends.isna().any()
        or selected_ends.isna().any()
        or not (original_ends - origins).eq(pd.Timedelta(minutes=30)).all()
        or not (selected_ends - origins).eq(pd.Timedelta(minutes=horizon)).all()
        or not (selected_ends <= original_ends).all()
    ):
        raise ValueError("RP4_V4_TARGET_INTERVAL_INVALID")
    vectors = tuple(
        x.dt.as_unit("ns").astype("int64").to_numpy()
        for x in (origins, original_ends, selected_ends)
    )
    return base, target, eligible, valid_original, complete, quality, *vectors


def read_checkpoint(
    output: Path, session: str, binding: dict[str, Any], expected: pd.DataFrame, target: np.ndarray
) -> dict[str, Any]:
    receipt_path = output / "session_receipts" / f"{session}.json"
    if not receipt_path.exists():
        raise ValueError("RP4_V4_COMPLETED_SESSION_WITHOUT_RECEIPT")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    encoded = (output / "sessions" / f"{session}.json").read_bytes()
    if receipt != {
        "session": session,
        "binding": binding,
        "sha256": hashlib.sha256(encoded).hexdigest(),
    }:
        raise ValueError("RP4_V4_COMPLETED_SESSION_HASH_OR_BINDING_DRIFT")
    record: dict[str, Any] = json.loads(encoded)
    if record["binding"] != binding or record["session"] != session:
        raise ValueError("RP4_V4_SESSION_BINDING_DRIFT")
    if (
        record["target_key"] != binding["target_key"]
        or record["horizon_minutes"] != binding["horizon_minutes"]
        or record["keys"] != expected[KEYS].to_dict("records")
        or not np.array_equal(record["target"], target)
    ):
        raise ValueError("RP4_V4_COMPLETED_SESSION_TARGET_OR_KEY_DRIFT")
    return record


def component(
    output: Path,
    session: str,
    name: str,
    binding: dict[str, Any],
    expected: pd.DataFrame,
    target: np.ndarray,
    fitting: v3.FitCall,
) -> dict[str, Any]:
    location = output / "components" / session
    if (location / "sessions" / f"{name}.json").exists():
        return read_checkpoint(location, name, binding, expected, target)
    prediction, fit = fitting()
    prediction = np.asarray(prediction, dtype=float)
    if (
        prediction.shape != (len(expected),)
        or not np.isfinite(prediction).all()
        or np.any(prediction <= 0)
    ):
        raise ValueError("RP4_V4_INVALID_COMPONENT_FORECAST")
    record: dict[str, Any] = v3.jsonable(
        {
            "binding": binding,
            "session": name,
            "evaluation_session": session,
            "horizon_minutes": binding["horizon_minutes"],
            "target_key": binding["target_key"],
            "forecast_scale": f"RV{binding['horizon_minutes']}_level",
            "keys": expected[KEYS].to_dict("records"),
            "target": target.tolist(),
            "forecast": prediction,
            "fit": fit,
        }
    )
    v2.write_checkpoint(location, name, record)
    print(f"RP4_V4_COMPONENT_COMPLETE:{binding['horizon_minutes']}:{session}:{name}", flush=True)
    return record


def fit_session(
    output: Path,
    session: str,
    binding: dict[str, Any],
    panel: pd.DataFrame,
    target: np.ndarray,
    spec: dict[str, Any],
    trees: dict[str, Any],
    linear: dict[str, Any],
    origins_ns: np.ndarray,
    original_end_ns: np.ndarray,
    selected_end_ns: np.ndarray,
    eligible: np.ndarray,
    reference: np.ndarray,
) -> dict[str, Any]:
    dates, assets = panel["session_date"].to_numpy(), panel["asset"].to_numpy()
    masks = v1.causal_masks(
        dates,
        origins_ns,
        original_end_ns,
        eligible,
        session,
        embargo_minutes=spec["embargo_minutes"],
        validation_sessions=spec["model"]["tuning_sessions"],
    )
    train, inner_fit, inner_valid, test = masks
    expected = panel.loc[test]
    forecasts: dict[str, dict[str, Any]] = {family: {} for family in FAMILIES}
    fits = {}
    for name in SETS:
        nullable = [
            i for i, col in enumerate(spec["feature_sets"][name]) if col in spec["missing_allowed"]
        ]
        for family in FAMILIES:
            call = (
                partial(
                    fit_ridge,
                    linear[name],
                    target,
                    *masks,
                    nullable,
                    dates,
                    assets,
                    spec["model"]["ridge"],
                )
                if family == FAMILIES[0]
                else partial(
                    fit_lightgbm,
                    trees[name],
                    target,
                    *masks,
                    dates,
                    assets,
                    spec["model"]["lightgbm"],
                    threads=THREADS,
                )
            )
            name_key = f"mean__{family}__{name}"
            saved = component(output, session, name_key, binding, expected, target[test], call)
            forecasts[family][name], fits[name_key] = saved["forecast"], saved["fit"]
    secondary, thresholds = v3.secondary_membership(
        panel, spec, session, train, test, reference, dates, origins_ns, original_end_ns
    )
    return {
        "binding": binding,
        "session": session,
        "horizon_minutes": binding["horizon_minutes"],
        "target_key": binding["target_key"],
        "keys": expected[KEYS].to_dict("records"),
        "target": target[test].tolist(),
        "forecasts": forecasts,
        "fits": fits,
        "secondary": secondary,
        "training_thresholds": thresholds,
        "train_last_session": str(np.max(dates[train])),
        "train_sessions": len(set(dates[train])),
        "max_training_target_end_utc": str(pd.Timestamp(original_end_ns[train].max(), tz="UTC")),
        "max_training_selected_target_end_utc": str(
            pd.Timestamp(selected_end_ns[train].max(), tz="UTC")
        ),
        "first_evaluation_origin_utc": str(pd.Timestamp(origins_ns[test].min(), tz="UTC")),
        "mask_counts": dict(
            zip(
                ("train", "inner_fit", "inner_valid", "test"),
                (int(m.sum()) for m in masks),
                strict=True,
            )
        ),
        "mask_sha256": {
            key: hashlib.sha256(
                str(len(mask)).encode() + b":" + np.packbits(mask).tobytes()
            ).hexdigest()
            for key, mask in zip(("train", "inner_fit", "inner_valid", "test"), masks, strict=True)
        },
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    spec = load_spec(args.spec, args.spec_sha256)
    target_key, end_key = horizon_contract(spec, args.horizon)
    if (
        args.shard_count != SHARDS
        or args.threads != THREADS
        or (args.shard_index is not None and not 0 <= args.shard_index < SHARDS)
        or (args.shard_index is not None and args.aggregate_only)
        or (args.shard_index is None and not args.aggregate_only)
    ):
        raise ValueError("RP4_V4_INVALID_SHARD_OR_THREAD_CONFIGURATION")
    if (
        v1.ROOT != ROOT
        or Path(inspect.getfile(fit_ridge)).resolve() != ROOT / "artifacts/rp4_v3_code/models.py"
        or Path(inspect.getfile(fit_lightgbm)).resolve() != ROOT / "artifacts/rp4_v2_code/models.py"
    ):
        raise ValueError("RP4_V4_IMPORT_OUTSIDE_BOUND_CHECKOUT")
    root = Path(spec["data_root"]).resolve()
    output = root / "evaluation" / f"rv{args.horizon}" / args.window
    public = (
        ROOT
        / "artifacts"
        / (f"rp4_v4_{'b2' if args.window == 'primary' else 'b3'}_rv{args.horizon}")
    )
    release = json.loads(args.release.read_text(encoding="utf-8"))
    code = evaluation_code_hashes()
    base_path, target_path = Path(spec["base_panel"]["path"]), target_panel_path(spec)
    expected_pins = {
        "specification_sha256": args.spec_sha256,
        "freeze_sha256": v1.sha256(args.spec.parent / "freeze_manifest.json"),
        "base_panel_sha256": v1.sha256(base_path),
        "target_panel_sha256": v1.sha256(target_path),
        "target_manifest_sha256": v1.sha256(target_path.parent / "manifest.json"),
        "target_resolution_sha256": v1.sha256(target_path.parent / "resolution.json"),
        "evaluation_code_sha256": code,
        "horizon_minutes": args.horizon,
        "target_key": target_key,
        "execution": spec["execution"],
    }
    if (
        any(release.get(key) != value for key, value in expected_pins.items())
        or expected_pins["base_panel_sha256"] != spec["base_panel"]["sha256"]
    ):
        raise ValueError("RP4_V4_RELEASE_DRIFT")
    binding = {**expected_pins, "release_sha256": v1.sha256(args.release), "window": args.window}
    try:
        v1.write_json_once(output / "binding.json", binding)
    except FileExistsError:
        v1.write_json_once(output / "binding.json", binding)
    window = spec["windows"][args.window]
    start, end = spec["windows"]["primary"]["start"], window["end"]
    base = pd.read_parquet(base_path)
    base = base[base["session_date"].astype(str).between(start, end)]
    targets = pd.read_parquet(
        target_path,
        columns=KEYS + [target_key, end_key],
        filters=[("session_date", ">=", start), ("session_date", "<=", end)],
    )
    (
        panel,
        target,
        eligible,
        valid_original,
        complete,
        quality,
        origins_ns,
        original_end_ns,
        selected_end_ns,
    ) = prepare_panel(base, targets, spec, args.horizon)
    dates, assets = panel["session_date"].to_numpy(), panel["asset"].to_numpy()
    if set(assets) - set(spec["assets"]):
        raise ValueError("RP4_V4_UNKNOWN_ASSET")
    reference = v2.v1_secondary_eligibility(panel, spec)
    trees, linear = v3.designs(panel, spec)
    scheduled = sorted(set(dates[(dates >= window["start"]) & (dates <= window["end"])]))[
        window["warmup_sessions"] :
    ]
    assigned = scheduled if args.shard_index is None else scheduled[args.shard_index :: SHARDS]
    records, skipped = [], []
    for session in assigned:
        test = eligible & (dates == session)
        expected = panel.loc[test]
        if (output / "sessions" / f"{session}.json").exists():
            records.append(read_checkpoint(output, session, binding, expected, target[test]))
            continue
        if expected.empty:
            skipped.append({"session": session, "reason": "no eligible origins"})
            continue
        try:
            v1.causal_masks(
                dates,
                origins_ns,
                original_end_ns,
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
            raise ValueError(f"RP4_V4_AGGREGATION_MISSING_SESSION:{session}")
        if evaluation_code_hashes() != code:
            raise ValueError("RP4_V4_CODE_CHANGED_BEFORE_FIT")
        record = fit_session(
            output,
            session,
            binding,
            panel,
            target,
            spec,
            trees,
            linear,
            origins_ns,
            original_end_ns,
            selected_end_ns,
            eligible,
            reference,
        )
        v2.write_checkpoint(output, session, v3.jsonable(record))
        records.append(record)
        print(
            f"RP4_V4_COMPLETED_SESSION:rv{args.horizon}:{session}:origins={len(expected)}",
            flush=True,
        )
    if args.shard_index is not None:
        result = {
            "status": "RP4_V4_SESSION_SHARD_COMPLETE",
            "binding": binding,
            "shard_index": args.shard_index,
            "assigned_sessions": len(assigned),
            "completed_sessions": len(records),
            "skipped_sessions": skipped,
        }
        v1.write_json_once(output / "shards" / f"{args.shard_index}.json", result)
        return result
    from artifacts.rp4_v4_code.aggregate_v4 import aggregate_records

    summary, losses = aggregate_records(records, spec["inference"])
    summary.update(
        {
            "binding": binding,
            "result_label": spec["label"],
            "window": args.window,
            "horizon_minutes": args.horizon,
            "target_key": target_key,
            "scheduled_sessions": len(scheduled),
            "skipped_sessions": skipped,
            "quality_gate_column_present": "rp4_eligible" in panel,
            "inherited_eligibility_unchanged": True,
            "evaluation_quality_by_asset": [
                {
                    "asset": asset,
                    "scheduled_rows": int(mask.sum()),
                    "eligible_rows": int((mask & eligible).sum()),
                    "invalid_target": int((mask & ~valid_original).sum()),
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
    v1.write_json_once(public / "summary.json", v3.jsonable(summary))
    v1.write_bytes_once(
        public / "session_losses.csv", losses.to_csv(index=False, lineterminator="\n").encode()
    )
    v1.write_json_once(
        output / "fit_diagnostics.json",
        [
            {
                "session": r["session"],
                "model": name,
                "endpoint": "mean",
                "horizon_minutes": args.horizon,
                "target_key": target_key,
                **fit,
            }
            for r in records
            for name, fit in sorted(r["fits"].items())
        ],
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--spec-sha256", required=True)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--horizon", type=int, choices=(5, 15), required=True)
    parser.add_argument("--window", choices=("primary", "confirmation"), required=True)
    parser.add_argument("--threads", type=int, default=THREADS)
    parser.add_argument("--shard-count", type=int, default=SHARDS)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--shard-index", type=int)
    mode.add_argument("--aggregate-only", action="store_true")
    print(json.dumps(v3.jsonable(run(parser.parse_args())), sort_keys=True))


if __name__ == "__main__":
    main()
