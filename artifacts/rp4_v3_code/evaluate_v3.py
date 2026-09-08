"""Frozen RP4 v3 session runner with immutable per-model checkpoints."""

from __future__ import annotations

import argparse
import copy
import inspect
import json
import os
from collections.abc import Callable
from functools import partial
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
import pandas as pd  # type: ignore[import-untyped]
from artifacts.rp4_code import evaluate as v1
from artifacts.rp4_v2_code import evaluate_v2 as v2
from artifacts.rp4_v3_code.empty_windows import INDICATORS, ORIGINAL_SHA, affected_columns
from artifacts.rp4_v3_code.freeze import ADDENDUM_SHA, BASE_SHA, FEATURES, V2_SHA
from artifacts.rp4_v3_code.models import (
    ModelConvergenceError,
    fit_jump,
    fit_lightgbm,
    fit_quantile,
    fit_ridge,
)

from mds650.metrics import qlike_losses

ROOT = Path(__file__).resolve().parents[2]
FAMILIES = v2.FAMILIES
KEYS = v1.KEYS
EFFECTIVE_FREEZE_SHA = "97e84fccde837b6cf2a45d11920282fb6067db64d4882295adb028547281aad6"
EVALUATION_PANEL_RELATIVE_PATH = "materialized_empty_windows/panel.parquet"
Array = npt.NDArray[np.float64]
Mask = npt.NDArray[np.bool_]
Labels = npt.NDArray[Any]
FitCall = Callable[[], tuple[Array, dict[str, Any]]]
SOURCE_PATHS = (
    "artifacts/rp4_v3_code/evaluate_v3.py",
    "artifacts/rp4_v3_code/models.py",
    "artifacts/rp4_v3_code/inference.py",
    "artifacts/rp4_v3_code/aggregate_v3.py",
    "artifacts/rp4_v3_code/freeze.py",
    "artifacts/rp4_v3_code/empty_windows.py",
    "artifacts/rp4_v2_code/evaluate_v2.py",
    "artifacts/rp4_v2_code/models.py",
    "artifacts/rp4_v2_code/freeze.py",
    "artifacts/rp4_code/evaluate.py",
    "src/mds650/metrics.py",
    "src/mds650/rp2/inference.py",
    "src/mds650/rp2/qlike_objective.py",
)


def evaluation_code_hashes() -> dict[str, str]:
    return {name: v1.sha256(ROOT / name) for name in SOURCE_PATHS}


def load_spec(path: Path, expected_sha256: str) -> dict[str, Any]:
    if v1.sha256(path) != expected_sha256:
        raise ValueError("RP4_V3_SPECIFICATION_HASH_MISMATCH")
    spec: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    if spec.get("schema_version") != "rp4-walkforward-v3":
        raise ValueError("RP4_V3_SCHEMA_REQUIRED")
    original_path = ROOT / "artifacts/rp4_v3_a1/specification.json"
    original_freeze_path = original_path.parent / "freeze.json"
    effective_freeze_path = path.parent / "freeze.json"
    if (
        spec.get("original_v3_specification_sha256") != ORIGINAL_SHA
        or v1.sha256(original_path) != ORIGINAL_SHA
        or v1.sha256(effective_freeze_path) != EFFECTIVE_FREEZE_SHA
    ):
        raise ValueError("RP4_V3_EMPTY_WINDOW_REGISTRATION_CHAIN_DRIFT")
    original: dict[str, Any] = json.loads(original_path.read_text(encoding="utf-8"))
    original_freeze = json.loads(original_freeze_path.read_text(encoding="utf-8"))
    frozen = json.loads(effective_freeze_path.read_text(encoding="utf-8"))
    if (
        original_freeze["specification_sha256"] != ORIGINAL_SHA
        or frozen["specification_sha256"] != expected_sha256
        or frozen["schema_version"] != "rp4-v3-effective-empty-window-freeze-v1"
        or frozen["original_v3_specification_sha256"] != ORIGINAL_SHA
        or frozen["original_v3_freeze_sha256"] != v1.sha256(original_freeze_path)
        or frozen["addendum"] != spec.get("empty_window_addendum")
        or frozen["producer_sha256"] != v1.sha256(ROOT / "artifacts/rp4_v3_code/empty_windows.py")
    ):
        raise ValueError("RP4_V3_FREEZE_MISMATCH")
    rule = spec["empty_window_addendum"]
    if (
        rule["md_path"] != "docs/rp4/v3_window_empty_addendum.md"
        or rule["decision_path"] != "docs/rp4/decision_132_v3_empty_windows.md"
        or rule["indicators"] != INDICATORS
        or rule["counts"] != ["b2_5m_trades", "b2_30m_trades"]
        or rule["columns_to_nan"]
        != {
            str(minutes): affected_columns(original["feature_sets"]["B2"], minutes)
            for minutes in (5, 30)
        }
        or rule["unknown_count"] != "unknown_indicator_no_recode"
        or rule["no_origin_or_session_exclusion"] is not True
        or rule["activity_values_unchanged"] is not True
        or rule["diagnostics"] != "census_and_B2_over_B1_inside_outside"
    ):
        raise ValueError("RP4_V3_EMPTY_WINDOW_RULE_DRIFT")
    checks = {
        ROOT / "docs/rp4/specification_v3.md": spec["specification_md_sha256"],
        ROOT / "docs/rp4/decision_131_v3.md": spec["decision_sha256"],
        ROOT / "artifacts/rp4_v2_a1/specification.json": V2_SHA,
        ROOT / "docs/rp4/v3_addendum_stability_calibration.md": ADDENDUM_SHA,
        ROOT / rule["md_path"]: rule["md_sha256"],
        ROOT / rule["decision_path"]: rule["decision_sha256"],
    }
    if any(v1.sha256(p) != digest for p, digest in checks.items()):
        raise ValueError("RP4_V3_FROZEN_DOCUMENT_DRIFT")
    if any(
        original_freeze[name] != original[name]
        for name in (
            "specification_md_sha256",
            "decision_sha256",
            "addendum_sha256",
            "parent_specification_sha256",
        )
    ):
        raise ValueError("RP4_V3_ORIGINAL_FREEZE_METADATA_DRIFT")
    inherited = copy.deepcopy(original)
    inherited["original_v3_specification_sha256"] = ORIGINAL_SHA
    inherited["authority_decisions"].append(132)
    inherited["empty_window_addendum"] = rule
    inherited["feature_sets"]["B2"] += INDICATORS
    inherited["missing_allowed"] += INDICATORS
    inherited["feature_transforms"].update(dict.fromkeys(INDICATORS, "raw"))
    inherited["evaluation_panel_relative_path"] = EVALUATION_PANEL_RELATIVE_PATH
    if spec != inherited:
        raise ValueError("RP4_V3_EMPTY_WINDOW_UNAUTHORIZED_SPECIFICATION_CHANGE")
    parent = json.loads((ROOT / "artifacts/rp4_v2_a1/specification.json").read_text())
    for key in (
        "windows",
        "assets",
        "purge_minutes",
        "embargo_minutes",
        "source_cutoff_seconds",
        "mandatory_predictors",
    ):
        if spec[key] != parent[key]:
            raise ValueError(f"RP4_V3_OUT_OF_SCOPE_CHANGE:{key}")
    for name in v1.SETS:
        expected = parent["feature_sets"][name] + (FEATURES + INDICATORS if name == "B2" else [])
        if spec["feature_sets"][name] != expected:
            raise ValueError(f"RP4_V3_FEATURE_ALLOWLIST_DRIFT:{name}")
    if spec["base_panel"]["sha256"] != BASE_SHA:
        raise ValueError("RP4_V3_BASE_PANEL_PIN_DRIFT")
    return spec


def evaluation_panel_path(spec: dict[str, Any]) -> Path:
    """The effective freeze names the recoded panel, never the pre-addendum panel."""
    if spec.get("evaluation_panel_relative_path") != EVALUATION_PANEL_RELATIVE_PATH:
        raise ValueError("RP4_V3_EFFECTIVE_PANEL_PATH_DRIFT")
    return Path(spec["data_root"]).resolve() / EVALUATION_PANEL_RELATIVE_PATH


def designs(panel: pd.DataFrame, spec: dict[str, Any]) -> tuple[dict[str, Array], dict[str, Array]]:
    """Preserve every old transform; transform four new features once in each route."""
    asset_effects = np.column_stack(
        [(panel["asset"].to_numpy() == asset).astype(float) for asset in spec["assets"][1:]]
    )
    trees: dict[str, Array] = {}
    linear: dict[str, Array] = {}
    old_transforms = {k: v for k, v in spec["feature_transforms"].items() if k not in FEATURES}
    for name in v1.SETS:
        names = spec["feature_sets"][name]
        raw = panel[names].to_numpy(dtype=float).copy()
        raw[~np.isfinite(raw)] = np.nan
        for indicator in INDICATORS:
            if indicator in names:
                values = raw[:, names.index(indicator)]
                if not np.isin(values[np.isfinite(values)], [0.0, 1.0]).all():
                    raise ValueError("RP4_V3_EMPTY_WINDOW_INDICATOR_NOT_BINARY")
        transformed = v1.transform_ols(raw, names, old_transforms)
        for column in FEATURES:
            if column not in names:
                continue
            index = names.index(column)
            value = raw[:, index]
            if column == FEATURES[-1]:
                if np.any(value[np.isfinite(value)] < 0):
                    raise ValueError("RP4_V3_SIGNED_TRADE_COUNT_NEGATIVE")
                changed = np.log1p(value)
            else:
                changed = np.sign(value) * np.log1p(np.abs(value))
            raw[:, index] = changed
            transformed[:, index] = changed
        trees[name] = np.column_stack([raw, asset_effects])
        linear[name] = np.column_stack([transformed, asset_effects])
    return trees, linear


def jsonable(value: Any) -> Any:
    """Serialize diagnostics explicitly; forecast/target finiteness is checked first."""
    if isinstance(value, dict):
        return {str(k): jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [jsonable(v) for v in value]
    if isinstance(value, (float, np.floating)):
        return float(value) if np.isfinite(value) else None
    if isinstance(value, (np.integer, np.bool_)):
        return value.item()
    return value


def component(
    output: Path,
    session: str,
    name: str,
    binding: dict[str, Any],
    expected: pd.DataFrame,
    fitting: FitCall,
) -> dict[str, Any]:
    """A later failed component cannot cause a completed fit to run twice."""
    location = output / "components" / session
    if (location / "sessions" / f"{name}.json").exists():
        return v2.read_checkpoint(location, name, binding, expected)
    prediction, fitted = fitting()
    prediction = np.asarray(prediction, dtype=float)
    if prediction.shape != (len(expected),) or not np.isfinite(prediction).all():
        raise ValueError(f"RP4_V3_INVALID_COMPONENT_FORECAST:{name}")
    if name.startswith(("mean__", "quantile__")) and np.any(prediction <= 0):
        raise ValueError("RP4_V3_VARIANCE_FORECAST_NONPOSITIVE")
    if name.startswith("jump__") and np.any((prediction <= 0) | (prediction >= 1)):
        raise ValueError("RP4_V3_CLASSIFIER_PROBABILITY_INVALID")
    record: dict[str, Any] = jsonable(
        {
            "binding": binding,
            "session": name,
            "evaluation_session": session,
            "keys": expected[KEYS].to_dict("records"),
            "target": expected["rv30"].tolist(),
            "forecast": prediction,
            "forecast_scale": "probability" if name.startswith("jump__") else "RV30_level",
            "fit": fitted,
        }
    )
    v2.write_checkpoint(location, name, record)
    print(f"RP4_V3_COMPONENT_COMPLETE:{session}:{name}", flush=True)
    return record


def secondary_membership(
    panel: pd.DataFrame,
    spec: dict[str, Any],
    session: str,
    train: Mask,
    test: Mask,
    reference: Mask,
    dates: Labels,
    origins_ns: npt.NDArray[np.int64],
    end_ns: npt.NDArray[np.int64],
) -> tuple[dict[str, list[bool | None]], dict[str, Any]]:
    selected = panel.loc[test]
    minute = selected["origin_minute"].to_numpy()
    date = pd.Timestamp(session)
    membership: dict[str, list[bool | None]] = {
        "first_hour": (minute < 60).tolist(),
        "last_hour": (minute >= 300).tolist(),
        "weekly_expiration": [date.dayofweek == 4] * len(selected),
        "third_friday": [date.dayofweek == 4 and 15 <= date.day <= 21] * len(selected),
        "event": [None if pd.isna(x) else bool(x) for x in selected["is_event"]]
        if "is_event" in selected
        else [None] * len(selected),
    }
    for minutes, indicator in zip((5, 30), INDICATORS, strict=True):
        values = (
            selected[indicator].to_numpy(dtype=float)
            if indicator in selected
            else np.full(len(selected), np.nan)
        )
        if not np.isin(values[np.isfinite(values)], [0.0, 1.0]).all():
            raise ValueError("RP4_V3_EMPTY_WINDOW_SECONDARY_NOT_BINARY")
        membership[f"window_empty_{minutes}m"] = [
            None if not np.isfinite(value) else bool(value) for value in values
        ]
    high_flow: list[bool | None] = [None] * len(selected)
    flow_thresholds: dict[str, float] = {}
    if "previous_day_b2_30m_premium" in panel:
        high_flow, flow_thresholds = v2.high_flow_membership(
            panel, reference, dates, origins_ns, end_ns, session, test, spec["embargo_minutes"]
        )
    membership["high_flow"] = high_flow
    historical = panel.loc[train, ["asset", FEATURES[1]]].copy()
    historical[FEATURES[1]] = historical[FEATURES[1]].abs()
    historical = historical[np.isfinite(historical[FEATURES[1]])]
    thresholds = {
        str(asset): float(group[FEATURES[1]].quantile(2 / 3, interpolation="linear"))
        for asset, group in historical.groupby("asset")
    }
    membership["high_gamma"] = [
        bool(abs(value) > thresholds[asset]) if asset in thresholds and np.isfinite(value) else None
        for asset, value in selected[["asset", FEATURES[1]]].itertuples(index=False, name=None)
    ]
    return membership, {"high_flow": flow_thresholds, "high_gamma": thresholds}


def tail_options(spec: dict[str, Any], family: str) -> dict[str, Any]:
    if family == FAMILIES[1]:
        return dict(spec["model"]["lightgbm"])
    quantile = spec["tail_models"]["linear_quantile"]
    logistic = spec["tail_models"]["linear_jump"]
    return {
        **spec["model"]["ridge"],
        "admm": {
            "initial_rho": quantile["rho_initial"],
            "maxiter": quantile["maxiter"],
            "absolute_tolerance": quantile["absolute_tolerance"],
            "relative_tolerance": quantile["relative_tolerance"],
            "balance_interval": quantile["balance_every"],
            "balance_ratio": quantile["balance_ratio"],
            "balance_factor": quantile["balance_factor"],
        },
        "logistic": {k: logistic[k] for k in ("maxiter", "gtol", "ftol")},
    }


def fit_session(
    output: Path,
    session: str,
    binding: dict[str, Any],
    panel: pd.DataFrame,
    spec: dict[str, Any],
    trees: dict[str, Array],
    linear: dict[str, Array],
    dates: Labels,
    assets: Labels,
    origins_ns: npt.NDArray[np.int64],
    end_ns: npt.NDArray[np.int64],
    eligible: Mask,
    reference: Mask,
    threads: int,
) -> dict[str, Any]:
    target = panel["rv30"].to_numpy(dtype=float)
    train, inner_fit, inner_valid, test = v1.causal_masks(
        dates,
        origins_ns,
        end_ns,
        eligible,
        session,
        embargo_minutes=spec["embargo_minutes"],
        validation_sessions=spec["model"]["tuning_sessions"],
    )
    masks = (train, inner_fit, inner_valid, test)
    expected = panel.loc[test]
    forecasts: dict[str, dict[str, list[float]]] = {family: {} for family in FAMILIES}
    mz: dict[str, list[float]] = {}
    fits: dict[str, dict[str, Any]] = {}
    optional = set(spec["missing_allowed"])
    for name in v1.SETS:
        nullable = [i for i, c in enumerate(spec["feature_sets"][name]) if c in optional]
        for family in FAMILIES:
            tag = f"mean__{family}__{name}"
            fitting: FitCall
            if family == FAMILIES[0]:
                fitting = partial(
                    fit_ridge,
                    linear[name],
                    target,
                    *masks,
                    nullable,
                    dates,
                    assets,
                    spec["model"]["ridge"],
                )
            else:
                fitting = partial(
                    fit_lightgbm,
                    trees[name],
                    target,
                    *masks,
                    dates,
                    assets,
                    spec["model"]["lightgbm"],
                    threads=threads,
                )
            saved = component(output, session, tag, binding, expected, fitting)
            forecasts[family][name] = saved["forecast"]
            fitted = dict(saved["fit"])
            if family == FAMILIES[1]:
                calibration = dict(fitted.pop("mz_secondary"))
                prediction = np.asarray(calibration.pop("forecast"), dtype=float)
                if prediction.shape != (len(expected),) or not np.isfinite(prediction).all():
                    raise ValueError("RP4_V3_MZ_SECONDARY_INVALID")
                if np.any(prediction <= 0):
                    raise ValueError("RP4_V3_MZ_SECONDARY_NONPOSITIVE")
                mz[name] = prediction.tolist()
                fitted["mz_secondary"] = calibration
            fits[tag] = fitted

    raw_jump = panel["jump30"].to_numpy(dtype=float)
    jump_eligible = eligible & np.isfinite(raw_jump) & (raw_jump >= 0)
    jump_positions = np.flatnonzero(jump_eligible[test])
    labels = np.where(np.isfinite(raw_jump), (raw_jump > 0).astype(float), np.nan)
    tails: dict[str, dict[str, dict[str, list[float]]]] = {}
    tail_status: dict[str, dict[str, Any]] = {}
    for endpoint in ("quantile", "jump"):
        tail_forecasts: dict[str, dict[str, list[float]]] = {family: {} for family in FAMILIES}
        try:
            endpoint_masks = (
                masks
                if endpoint == "quantile"
                else v1.causal_masks(
                    dates,
                    origins_ns,
                    end_ns,
                    jump_eligible,
                    session,
                    embargo_minutes=spec["embargo_minutes"],
                    validation_sessions=spec["model"]["tuning_sessions"],
                )
            )
            endpoint_target = target if endpoint == "quantile" else labels
            endpoint_expected = panel.loc[endpoint_masks[-1], KEYS].copy()
            endpoint_expected["rv30"] = endpoint_target[endpoint_masks[-1]]
            for name in v1.SETS:
                nullable = [i for i, c in enumerate(spec["feature_sets"][name]) if c in optional]
                for family in FAMILIES:
                    method = fit_quantile if endpoint == "quantile" else fit_jump
                    matrix = linear[name] if family == FAMILIES[0] else trees[name]
                    options = tail_options(spec, family)
                    family_kind = "linear" if family == FAMILIES[0] else "lightgbm"
                    tag = f"{endpoint}__{family}__{name}"
                    saved = component(
                        output,
                        session,
                        tag,
                        binding,
                        endpoint_expected,
                        partial(
                            method,
                            matrix,
                            endpoint_target,
                            *endpoint_masks,
                            nullable,
                            dates,
                            assets,
                            options,
                            family=family_kind,
                            threads=threads,
                        ),
                    )
                    natural_forecast = np.asarray(saved["forecast"], dtype=float)
                    # Models/checkpoints export a positive RV30 quantile in levels;
                    # pinball's registered estimand is log(RV30), exactly one log here.
                    tail_forecasts[family][name] = (
                        np.log(natural_forecast).tolist()
                        if endpoint == "quantile"
                        else natural_forecast.tolist()
                    )
                    fits[tag] = saved["fit"]
            tails[endpoint] = tail_forecasts
            tail_status[endpoint] = {"status": "COMPUTED"}
        except ModelConvergenceError as error:
            tails[endpoint] = {}
            tail_status[endpoint] = {
                "status": "NO VERIFICABLE",
                "reason": str(error),
                "diagnostics": jsonable(error.diagnostics),
            }
        except ValueError as error:
            # Only predetermined numerical/availability failures are missing endpoints.
            # Programming/configuration errors stop execution for a tested repair.
            message = str(error)
            allowed = (
                "RP4_SESSION_NO_ELIGIBLE_ORIGINS",
                "RP4_INSUFFICIENT_TRAINING_SESSIONS",
                "RP4_INNER_TRAINING_EMPTY_AFTER_EMBARGO",
            )
            if not message.startswith(allowed):
                raise
            tails[endpoint] = {}
            tail_status[endpoint] = {"status": "NO VERIFICABLE", "reason": message}
    secondary, thresholds = secondary_membership(
        panel, spec, session, train, test, reference, dates, origins_ns, end_ns
    )
    return {
        "binding": binding,
        "session": session,
        "keys": expected[KEYS].to_dict("records"),
        "target": target[test].tolist(),
        "forecasts": forecasts,
        "fits": fits,
        "mz_forecasts": mz,
        "tail_forecasts": tails,
        "tail_status": tail_status,
        "jump_positions": jump_positions.tolist(),
        "jump_target": labels[test][jump_positions].tolist(),
        "secondary": secondary,
        "training_thresholds": thresholds,
        "train_last_session": str(np.max(dates[train])),
        "train_sessions": len(set(dates[train])),
        "max_training_target_end_utc": str(pd.Timestamp(end_ns[train].max(), tz="UTC")),
        "first_evaluation_origin_utc": str(pd.Timestamp(origins_ns[test].min(), tz="UTC")),
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    spec = load_spec(args.spec, args.spec_sha256)
    if (
        v1.ROOT != ROOT
        or Path(inspect.getfile(qlike_losses)).resolve() != ROOT / "src/mds650/metrics.py"
    ):
        raise ValueError("RP4_V3_IMPORT_OUTSIDE_BOUND_CHECKOUT")
    if args.threads != spec["model"]["lightgbm"]["num_threads"]:
        raise ValueError("RP4_V3_THREAD_DRIFT")
    if (
        args.shard_count < 1
        or (args.shard_index is not None and not 0 <= args.shard_index < args.shard_count)
        or (args.shard_index is not None and args.aggregate_only)
        or (args.shard_count > 1 and args.shard_index is None and not args.aggregate_only)
    ):
        raise ValueError("RP4_V3_INVALID_SHARD")
    root, output = Path(spec["data_root"]).resolve(), args.output.resolve()
    if (
        output == root
        or not output.is_relative_to(root)
        or (os.name == "nt" and output.drive.lower() != "d:")
    ):
        raise ValueError("RP4_V3_OUTPUT_OUTSIDE_PRIVATE_ROOT")
    public = args.public_output.resolve()
    public_base = ROOT / "artifacts"
    if not (
        public.is_relative_to(root)
        or (
            public.is_relative_to(public_base)
            and public != public_base
            and public.relative_to(public_base).parts[0].startswith("rp4_v3_")
        )
    ):
        raise ValueError("RP4_V3_PUBLIC_OUTPUT_OUTSIDE_NEW_SCOPE")
    if args.panel.resolve() != evaluation_panel_path(spec):
        raise ValueError("RP4_V3_MATERIALIZED_PANEL_REQUIRED")
    manifest_path = args.panel.parent / "manifest.json"
    release = json.loads(args.release.read_text(encoding="utf-8"))
    execution = {"session_shards": args.shard_count, "threads_per_model": args.threads}
    code = evaluation_code_hashes()
    if (
        release["panel_sha256"] != v1.sha256(args.panel)
        or release["materialization_manifest_sha256"] != v1.sha256(manifest_path)
        or release["specification_sha256"] != args.spec_sha256
        or release["effective_freeze_sha256"] != v1.sha256(args.spec.parent / "freeze.json")
        or release["evaluation_panel_relative_path"] != spec["evaluation_panel_relative_path"]
        or release["execution"] != execution
        or release["evaluation_code_sha256"] != code
    ):
        raise ValueError("RP4_V3_RELEASE_DRIFT")
    binding = {
        "panel_sha256": release["panel_sha256"],
        "specification_sha256": args.spec_sha256,
        "release_sha256": v1.sha256(args.release),
        "window": args.window,
        "code_sha256": code,
        "execution": execution,
    }
    try:
        v1.write_json_once(output / "binding.json", binding)
    except FileExistsError:
        # Session shards publish the same immutable binding concurrently.
        v1.write_json_once(output / "binding.json", binding)
    panel = pd.read_parquet(args.panel)
    required = set(
        KEYS
        + ["rv30", "jump30", "forecast_origin_utc", "target_end_utc"]
        + spec["feature_sets"]["B2"]
    )
    if missing := required - set(panel):
        raise ValueError(f"RP4_V3_PANEL_MISSING_COLUMNS:{sorted(missing)}")
    if panel.duplicated(KEYS).any():
        raise ValueError("RP4_V3_DUPLICATE_KEYS")
    panel["session_date"] = panel["session_date"].astype(str)
    window = spec["windows"][args.window]
    panel = panel[panel["session_date"].between(spec["windows"]["primary"]["start"], window["end"])]
    panel = panel.sort_values(["session_date", "asset", "origin_minute"]).reset_index(drop=True)
    origins, ends = (
        pd.to_datetime(panel[c], utc=True) for c in ("forecast_origin_utc", "target_end_utc")
    )
    if (
        origins.isna().any()
        or ends.isna().any()
        or not ((ends - origins) == pd.Timedelta(minutes=30)).all()
    ):
        raise ValueError("RP4_V3_TARGET_INTERVAL_INVALID")
    origins_ns, end_ns = (x.dt.as_unit("ns").astype("int64").to_numpy() for x in (origins, ends))
    dates, assets = panel["session_date"].to_numpy(), panel["asset"].to_numpy()
    if set(assets) - set(spec["assets"]):
        raise ValueError("RP4_V3_UNKNOWN_ASSET")
    eligible, valid_target, complete, quality = v2.panel_masks(panel, spec)
    reference = v2.v1_secondary_eligibility(panel, spec)
    trees, linear = designs(panel, spec)
    scheduled = sorted(set(dates[(dates >= window["start"]) & (dates <= window["end"])]))[
        window["warmup_sessions"] :
    ]
    assigned = (
        scheduled if args.shard_index is None else scheduled[args.shard_index :: args.shard_count]
    )
    records, skipped = [], []
    for session in assigned:
        expected = panel.loc[eligible & (dates == session)]
        if (output / "sessions" / f"{session}.json").exists():
            records.append(v2.read_checkpoint(output, session, binding, expected))
            print(f"RP4_V3_REUSED_COMPLETE_SESSION:{session}", flush=True)
            continue
        if expected.empty:
            skipped.append({"session": session, "reason": "no eligible origins"})
            continue
        try:
            # Same eligibility-only exclusion as v2; no fit and no new rule.
            # An empty-window indicator is optional and never enters this mask.
            v1.causal_masks(
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
            raise ValueError(f"RP4_V3_AGGREGATION_MISSING_SESSION:{session}")
        record = fit_session(
            output,
            session,
            binding,
            panel,
            spec,
            trees,
            linear,
            dates,
            assets,
            origins_ns,
            end_ns,
            eligible,
            reference,
            args.threads,
        )
        v2.write_checkpoint(output, session, record)
        records.append(record)
        print(f"RP4_V3_COMPLETED_SESSION:{session}:origins={len(expected)}", flush=True)
    if args.shard_index is not None:
        result = {
            "status": "RP4_V3_SESSION_SHARD_COMPLETE",
            "window": args.window,
            "shard_index": args.shard_index,
            "shard_count": args.shard_count,
            "assigned_sessions": len(assigned),
            "completed_sessions": len(records),
            "skipped_sessions": skipped,
            "binding": binding,
        }
        v1.write_json_once(output / "shards" / f"{args.shard_index}.json", result)
        return result
    from artifacts.rp4_v3_code.aggregate_v3 import aggregate_records

    summary, losses = aggregate_records(records, spec["inference"])
    summary.update(
        {
            "binding": binding,
            "result_label": spec["label"],
            "window": args.window,
            "scheduled_sessions": len(scheduled),
            "skipped_sessions": skipped,
            "materialization_manifest_sha256": v1.sha256(manifest_path),
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
    v1.write_json_once(public / "summary.json", jsonable(summary))
    v1.write_bytes_once(
        public / "session_losses.csv", losses.to_csv(index=False, lineterminator="\n").encode()
    )
    v1.write_json_once(
        output / "fit_diagnostics.json",
        [
            {"session": record["session"], "model": name, "endpoint": name.split("__")[0], **fit}
            for record in records
            for name, fit in sorted(record["fits"].items())
        ],
    )
    print(
        json.dumps(
            {
                "status": "RP4_V3_WINDOW_COMPLETE",
                "window": args.window,
                "N_sessions": len(records),
                "summary_sha256": v1.sha256(public / "summary.json"),
            }
        ),
        flush=True,
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("spec", "panel", "release", "output", "public-output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--spec-sha256", required=True)
    parser.add_argument("--window", choices=("primary", "confirmation"), required=True)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--shard-count", type=int, default=1)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--shard-index", type=int)
    mode.add_argument("--aggregate-only", action="store_true")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
