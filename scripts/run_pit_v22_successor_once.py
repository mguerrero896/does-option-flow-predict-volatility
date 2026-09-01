"""Run the signed PIT v2.2 successor evaluation exactly once."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

from mds650.phase6 import (
    B0V2_FEATURES,
    B1V2A_FEATURES,
    B1V2B_FEATURES,
    B1V2C_FEATURES,
    B2V2_FEATURES,
    OUTCOME_ASSETS,
    build_b0v2_features,
    build_phase6_common_panel,
    build_phase6_origins,
)
from mds650.phase6_evaluation import (
    add_training_volatility_regime,
    authorize_phase6_oos,
    evaluate_phase6,
    forecast_phase6_fold,
    phase6_contrast,
    phase6_fold_definitions,
    phase6_information_sets,
    select_phase6_parameters,
    training_mde_from_forecasts,
    training_only_oof_forecasts,
    validate_phase6_evaluation_panel,
)
from mds650.rp2.panel import DEFAULT_TRAIN_SHARE, chronological_split, session_rank
from mds650.storage import assert_outside_frozen, write_content_addressed
from mds650.study_design import canonical_sha256
from mds650.temporal_validation import split_expanding_fold

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts" / "target_blind_v22"
METHOD_TEMPLATE = ROOT / "artifacts" / "phase6" / "method_freeze.json"
TARGET_LINKAGE_POLICY: dict[str, Any] = {
    "eligible_origin_set": "PREDICTOR_COMPLETE_INTERSECT_TARGET_COMPLETE",
    "required_target_price_count": 31,
    "required_target_return_count": 30,
    "require_finite_rv30": True,
    "require_positive_rv30": True,
    "missing_target_action": "EXCLUDE_ORIGIN",
    "imputation": "FORBIDDEN",
    "cross_provider_bar_substitution": "FORBIDDEN",
}
PROTOCOL_CONFIGS = {
    "v1": {
        "source_preregistration": "next_confirmation_preregistration_v2.json",
        "signed_freeze": "successor_method_freeze_v1.json",
        "owner_authorization": "successor_owner_authorization_v1.json",
        "run_id": "pit-v22-successor-evaluation-v1-20260901",
        "base_commit": "b8657bfa7e280b75fddd7ee818cbaa5987c495d2",
        "signed_freeze_sha256": (
            "0b3d26ac08e06ff9e862dbc40ce17f42102067f126bfe3f1ba1e55e880639faf"
        ),
        "owner_authorization_sha256": (
            "db2f243bd8201a3363624be7120b49affd30a13b21ad6ed4f481e69e7487eea2"
        ),
        "gated_root_path_sha256": (
            "0348aa63962b19714303dccd0a8f8d273f1dc0152e9e2dc15353fad1956fea94"
        ),
        "data_defect_resolution": "",
        "data_defect_resolution_sha256": "",
    },
    "v2": {
        "source_preregistration": "next_confirmation_preregistration_v3.json",
        "signed_freeze": "successor_method_freeze_v2.json",
        "owner_authorization": "successor_owner_authorization_v2.json",
        "run_id": "pit-v22-successor-evaluation-v2-20260902",
        "base_commit": "b9ec78d6b368aa7ecc5d1e8dcc0c2a0c62a2cbcf",
        "signed_freeze_sha256": (
            "d803083ccbbaa23889db8ecae7fa5ed8323dc42cb8ae4613edcad5faa404dc40"
        ),
        "owner_authorization_sha256": (
            "b9176f7a0745ea7ba3bb0e1f7fbf796f4a6e01d5071cab6a65a15974193c81a1"
        ),
        "gated_root_path_sha256": (
            "b0f7f75c38470bb9a6965c6187cf4814cfe8cf93109e18ca2c058e3b6a1bafb9"
        ),
        "data_defect_resolution": "target_source_discrepancy_resolution_v1.json",
        "data_defect_resolution_sha256": (
            "794a2ef5594cdb77c4ad72b63639eaac8cccaf3a8b7447338e5e7c097d93a5c1"
        ),
    },
}

PROTOCOL_VERSION: str
SOURCE_PREREGISTRATION: Path
SIGNED_FREEZE: Path
OWNER_AUTHORIZATION: Path
RUN_ID: str
SOURCE_PANEL: Path
SOURCE_BARS: Path
GATED_ROOT: Path
TRACKED_RESULT: Path
TRACKED_LOG: Path
BASE_COMMIT: str
EXPECTED_SIGNED_FREEZE_SHA256: str
EXPECTED_OWNER_AUTHORIZATION_SHA256: str
EXPECTED_GATED_ROOT_PATH_SHA256: str
DATA_DEFECT_RESOLUTION: Path | None
EXPECTED_DATA_DEFECT_RESOLUTION_SHA256: str | None
EXPECTED_SOURCE_PANEL_SHA256 = "d9f6c7690c5952a1c0e69087f9c8643c9b0496927fe863456d23648f268cd236"
MODEL_ROLES = ("gamma_glm_confirmatory", "lightgbm_robustness")
KEYS = ("origin_id", "asset", "session_date", "forecast_origin_utc")


def configure_protocol(version: str) -> None:
    """Select one closed protocol configuration without weakening either contract."""
    global BASE_COMMIT
    global DATA_DEFECT_RESOLUTION
    global EXPECTED_DATA_DEFECT_RESOLUTION_SHA256
    global EXPECTED_GATED_ROOT_PATH_SHA256
    global EXPECTED_OWNER_AUTHORIZATION_SHA256
    global EXPECTED_SIGNED_FREEZE_SHA256
    global OWNER_AUTHORIZATION
    global PROTOCOL_VERSION
    global RUN_ID
    global SIGNED_FREEZE
    global SOURCE_PREREGISTRATION
    global TRACKED_LOG
    global TRACKED_RESULT

    try:
        config = PROTOCOL_CONFIGS[version]
    except KeyError as error:
        raise ValueError("PIT_V22_SUCCESSOR_PROTOCOL_VERSION_INVALID") from error
    PROTOCOL_VERSION = version
    SOURCE_PREREGISTRATION = ARTIFACTS / config["source_preregistration"]
    SIGNED_FREEZE = ARTIFACTS / config["signed_freeze"]
    OWNER_AUTHORIZATION = ARTIFACTS / config["owner_authorization"]
    RUN_ID = config["run_id"]
    TRACKED_RESULT = ARTIFACTS / f"successor_evaluation_result_{version}.json"
    TRACKED_LOG = ARTIFACTS / f"successor_evaluation_run_{version}.json"
    BASE_COMMIT = config["base_commit"]
    EXPECTED_SIGNED_FREEZE_SHA256 = config["signed_freeze_sha256"]
    EXPECTED_OWNER_AUTHORIZATION_SHA256 = config["owner_authorization_sha256"]
    EXPECTED_GATED_ROOT_PATH_SHA256 = config["gated_root_path_sha256"]
    resolution = config["data_defect_resolution"]
    DATA_DEFECT_RESOLUTION = ARTIFACTS / resolution if resolution else None
    EXPECTED_DATA_DEFECT_RESOLUTION_SHA256 = config["data_defect_resolution_sha256"] or None


configure_protocol("v1")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json_with_sha256(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    payload = json.loads(raw.decode("utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"PIT_V22_JSON_OBJECT_REQUIRED:{path.name}")
    return payload, hashlib.sha256(raw).hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    return _read_json_with_sha256(path)[0]


def _json_bytes(payload: Mapping[str, Any]) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode()


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    assert_outside_frozen(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".part")
    with temporary.open("wb") as target:
        target.write(_json_bytes(payload))
        target.flush()
        os.fsync(target.fileno())
    os.replace(temporary, path)


def _write_parquet(path: Path, frame: pl.DataFrame) -> None:
    assert_outside_frozen(path)
    temporary = path.with_suffix(path.suffix + ".part")
    frame.write_parquet(temporary, compression="zstd")
    with temporary.open("r+b") as persisted:
        os.fsync(persisted.fileno())
    os.replace(temporary, path)


def _log_payload(events: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "pit-v22-successor-evaluation-log-1.0",
        "run_id": RUN_ID,
        "events": list(events),
    }


def _write_log(path: Path, events: Sequence[Mapping[str, Any]]) -> None:
    _write_json(path, _log_payload(events))


def _write_new_json(path: Path, payload: Mapping[str, Any]) -> str:
    assert_outside_frozen(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload_bytes = _json_bytes(payload)
    digest = hashlib.sha256(payload_bytes).hexdigest()
    with tempfile.NamedTemporaryFile(
        mode="wb", dir=path.parent, prefix=f".{path.name}.", suffix=".part", delete=False
    ) as target:
        temporary = Path(target.name)
        target.write(payload_bytes)
        target.flush()
        os.fsync(target.fileno())
    try:
        os.link(temporary, path)
    except FileExistsError as error:
        raise FileExistsError("PIT_V22_SUCCESSOR_TRACKED_OUTPUT_ALREADY_EXISTS") from error
    finally:
        with suppress(OSError):
            temporary.unlink(missing_ok=True)
    return digest


def _assert_public_payload(payload: Mapping[str, Any]) -> None:
    rendered = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    if re.search(r"(?i)(?:[a-z]:[\\/]|/users/|/home/)", rendered):
        raise RuntimeError("PIT_V22_SUCCESSOR_PERSONAL_PATH_IN_PUBLIC_PAYLOAD")


def _event(events: list[dict[str, Any]], gated_log: Path, name: str, **details: Any) -> None:
    event = {
        "event": name,
        "recorded_at_utc": datetime.now(UTC).isoformat(),
        **details,
    }
    events.append(event)
    _write_log(gated_log, events)
    print(json.dumps(event, sort_keys=True), flush=True)


def claim_one_shot(path: Path, payload: Mapping[str, Any]) -> None:
    """Create the irreversible process claim; an existing claim forbids a rerun."""
    try:
        _write_new_json(path, payload)
    except FileExistsError as error:
        raise FileExistsError("PIT_V22_SUCCESSOR_ALREADY_CLAIMED") from error


def successor_session_split(
    session_dates: Sequence[str], *, train_share: float = DEFAULT_TRAIN_SHARE
) -> dict[str, list[str]]:
    """Apply the registered session split, then halve its chronological remainder."""
    dates = [str(day) for day in session_dates]
    if len(dates) < 3 or dates != sorted(set(dates)):
        raise ValueError("PIT_V22_SUCCESSOR_SESSION_DATES_INVALID")
    ranks = session_rank(np.asarray(dates, dtype=np.str_))
    development_mask, remainder_mask = chronological_split(ranks, train_share=train_share)
    development = np.asarray(dates)[development_mask].tolist()
    remainder = np.asarray(dates)[remainder_mask].tolist()
    midpoint = len(remainder) // 2
    validation, holdout = remainder[:midpoint], remainder[midpoint:]
    if not development or not validation or not holdout:
        raise ValueError("PIT_V22_SUCCESSOR_SPLIT_EMPTY")
    return {
        "development": development,
        "validation": validation,
        "holdout": holdout,
    }


def _runtime_preregistration(
    split: Mapping[str, Sequence[str]],
    source_preregistration: Mapping[str, Any],
    method_template: Mapping[str, Any],
) -> dict[str, Any]:
    development = list(split["development"])
    validation = list(split["validation"])
    holdout = list(split["holdout"])
    payload: dict[str, Any] = {
        "schema_version": "pit-v22-successor-runtime-preregistration-1.0",
        "status": "FROZEN_BEFORE_OOS",
        "oos_read_count": 0,
        "bound_panel_sha256": source_preregistration["bound_panel"]["panel_sha256"],
        "source_preregistration_sha256": source_preregistration["preregistration_sha256"],
        "source_bars_sha256": source_preregistration["bound_panel"]["source_hashes"][
            "fmp_bars_sha256"
        ],
        "outcome_assets": list(OUTCOME_ASSETS),
        "train_share": DEFAULT_TRAIN_SHARE,
        "session_universe": (
            "PREDICTOR_COMPLETE_INTERSECT_TARGET_COMPLETE"
            if PROTOCOL_VERSION == "v2"
            else "COMMON_PREDICTOR_COMPLETE_SESSIONS"
        ),
        "session_universe_count": len([*development, *validation, *holdout]),
        "remainder_rule": "EQUAL_CHRONOLOGICAL_VALIDATION_AND_HOLDOUT",
        "remainder_boundary_fixed_target_free": True,
        "information_sets": {
            name: list(features)
            for name, features in phase6_information_sets(include_b1_robustness=True).items()
        },
        "models": method_template["models"],
        "inference": method_template["inference"],
        "folds": [
            {"fold": 1, "train_dates": development, "test_dates": validation},
            {
                "fold": 2,
                "train_dates": [*development, *validation],
                "test_dates": holdout,
            },
        ],
    }
    if PROTOCOL_VERSION == "v2":
        payload["target_linkage_eligibility_policy"] = dict(TARGET_LINKAGE_POLICY)
        payload["linked_common_complete_rows_at_freeze"] = "NOT_READ_OUTCOME_DEPENDENT"
    payload["manifest_sha256"] = canonical_sha256(payload)
    phase6_fold_definitions(payload)
    return payload


def _git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def _preflight(*, require_clean: bool) -> tuple[dict[str, Any], dict[str, Any]]:
    gated_root_path_sha256 = hashlib.sha256(
        GATED_ROOT.resolve().as_posix().casefold().encode()
    ).hexdigest()
    if GATED_ROOT.name != RUN_ID or gated_root_path_sha256 != EXPECTED_GATED_ROOT_PATH_SHA256:
        raise RuntimeError("PIT_V22_SUCCESSOR_GATED_ROOT_INVALID")
    source_preregistration, source_preregistration_raw_sha256 = _read_json_with_sha256(
        SOURCE_PREREGISTRATION
    )
    freeze, freeze_sha256 = _read_json_with_sha256(SIGNED_FREEZE)
    authorization, authorization_sha256 = _read_json_with_sha256(OWNER_AUTHORIZATION)
    method_template, method_template_sha256 = _read_json_with_sha256(METHOD_TEMPLATE)
    resolution_sha256: str | None = None
    protocol_specific_valid = True
    if DATA_DEFECT_RESOLUTION is not None:
        resolution, resolution_sha256 = _read_json_with_sha256(DATA_DEFECT_RESOLUTION)
        resolution_unsigned = {
            key: value for key, value in resolution.items() if key != "manifest_sha256"
        }
        protocol_specific_valid = (
            resolution_sha256 == EXPECTED_DATA_DEFECT_RESOLUTION_SHA256
            and resolution.get("manifest_sha256") == canonical_sha256(resolution_unsigned)
            and resolution.get("status") == "FROZEN_BEFORE_OOS"
            and resolution.get("oos_read_count") == 0
            and resolution.get("eligibility_policy") == TARGET_LINKAGE_POLICY
            and source_preregistration.get("target_linkage_eligibility_policy")
            == TARGET_LINKAGE_POLICY
            and freeze.get("target_linkage_eligibility_policy") == TARGET_LINKAGE_POLICY
            and freeze.get("data_defect_resolution_sha256") == resolution_sha256
            and authorization.get("protocol_id") == "pit-v22-successor-method-freeze-v2"
            and authorization.get("run_id") == RUN_ID
            and authorization.get("data_defect_decision") == resolution.get("decision")
        )
    prereg_unsigned = {
        key: value
        for key, value in source_preregistration.items()
        if key != "preregistration_sha256"
    }
    method_unsigned = {
        key: value for key, value in method_template.items() if key != "manifest_sha256"
    }
    panel_sha256 = _sha256(SOURCE_PANEL)
    bars_sha256 = _sha256(SOURCE_BARS)
    if (
        source_preregistration["preregistration_sha256"] != canonical_sha256(prereg_unsigned)
        or source_preregistration["preregistration_sha256"]
        != freeze["provenance"]["preregistration_sha256"]
        or method_template.get("manifest_sha256") != canonical_sha256(method_unsigned)
        or freeze_sha256 != EXPECTED_SIGNED_FREEZE_SHA256
        or authorization_sha256 != EXPECTED_OWNER_AUTHORIZATION_SHA256
        or panel_sha256 != EXPECTED_SOURCE_PANEL_SHA256
        or freeze_sha256 != authorization.get("contract_sha256")
        or authorization.get("authorize_read_and_evaluation") is not True
        or authorization.get("sealed_cohorts_read_before") != 0
        or freeze.get("zero_oos_reads_at_freeze") is not True
        or freeze.get("model_fit_performed_at_freeze") is not False
        or freeze.get("bound_panel_sha256") != panel_sha256
        or source_preregistration["bound_panel"]["panel_sha256"] != panel_sha256
        or source_preregistration["bound_panel"]["source_hashes"]["fmp_bars_sha256"] != bars_sha256
        or not protocol_specific_valid
    ):
        raise RuntimeError("PIT_V22_SUCCESSOR_SIGNED_INPUT_INVALID")
    schema = pl.read_parquet_schema(SOURCE_PANEL)
    forbidden = {"rv30", "target", "forecast", "qlike", "mae", "rmse", "loss"}
    if forbidden & {name.lower() for name in schema}:
        raise RuntimeError("PIT_V22_SOURCE_PANEL_NOT_TARGET_FREE")
    required_features = {
        *KEYS,
        *B0V2_FEATURES,
        *B1V2A_FEATURES,
        *B1V2B_FEATURES,
        *B1V2C_FEATURES,
        *B2V2_FEATURES,
        "common_predictor_complete",
    }
    if not required_features <= set(schema):
        raise RuntimeError("PIT_V22_SOURCE_PANEL_SCHEMA_INVALID")
    source_keys = pl.read_parquet(
        SOURCE_PANEL, columns=["origin_id", "session_date", "common_predictor_complete"]
    )
    common = source_keys.filter(pl.col("common_predictor_complete"))
    sessions = sorted(common["session_date"].unique().to_list())
    if (
        source_keys.height != int(freeze["bound_panel_rows"])
        or common.height != int(freeze["bound_panel_common_complete_rows"])
        or source_keys["origin_id"].n_unique() != source_keys.height
        or len(sessions) != 159
    ):
        raise RuntimeError("PIT_V22_SOURCE_PANEL_COUNTS_INVALID")
    split = successor_session_split(sessions)
    preregistration = _runtime_preregistration(split, source_preregistration, method_template)
    expected_counts = {"development": 95, "validation": 32, "holdout": 32}
    if {name: len(values) for name, values in split.items()} != expected_counts:
        raise RuntimeError("PIT_V22_SUCCESSOR_SPLIT_INVALID")
    outputs = (GATED_ROOT, TRACKED_RESULT, TRACKED_LOG)
    if any(path.exists() for path in outputs):
        raise RuntimeError("PIT_V22_SUCCESSOR_OUTPUT_ALREADY_EXISTS")
    if _git("merge-base", "--is-ancestor", BASE_COMMIT, "HEAD").returncode != 0:
        raise RuntimeError("PIT_V22_SUCCESSOR_BASE_NOT_ANCESTOR")
    if require_clean and _git("status", "--porcelain").stdout.strip():
        raise RuntimeError("PIT_V22_SUCCESSOR_WORKTREE_DIRTY")
    return preregistration, {
        "status": "PASS_TARGET_FREE_PREFLIGHT",
        "source_panel_sha256": panel_sha256,
        "source_bars_sha256": bars_sha256,
        "signed_freeze_sha256": freeze_sha256,
        "owner_authorization_sha256": authorization_sha256,
        "source_preregistration_raw_sha256": source_preregistration_raw_sha256,
        "method_template_sha256": method_template_sha256,
        "source_rows": source_keys.height,
        "source_common_complete_rows": common.height,
        "split_session_counts": expected_counts,
        "runtime_preregistration_sha256": preregistration["manifest_sha256"],
        "data_defect_resolution_sha256": resolution_sha256,
    }


def _validate_target_linkage(
    source: pl.DataFrame, targets: pl.DataFrame, common: pl.DataFrame
) -> None:
    source_common_ids = source.filter(pl.col("common_predictor_complete")).select("origin_id")
    target_complete_ids = targets.filter(
        pl.col("rv30").is_finite()
        & (pl.col("rv30") > 0)
        & (pl.col("target_price_count") == 31)
        & (pl.col("target_return_count") == 30)
    ).select("origin_id")
    expected_ids = source_common_ids.join(
        target_complete_ids, on="origin_id", how="inner", validate="1:1"
    ).sort("origin_id")
    if not common.select("origin_id").sort("origin_id").equals(expected_ids):
        raise RuntimeError("PIT_V22_TARGET_LINKAGE_INVALID")


def _linked_panel(source: pl.DataFrame, bars: pl.DataFrame) -> tuple[pl.DataFrame, pl.DataFrame]:
    sessions = sorted(source["session_date"].unique().to_list())
    origins = build_phase6_origins(sessions)
    if not origins.select(KEYS).sort("origin_id").equals(source.select(KEYS).sort("origin_id")):
        raise RuntimeError("PIT_V22_ORIGIN_KEY_DRIFT")
    targets = build_b0v2_features(bars, origins, delay_minutes=1, include_target=True)
    b0 = (
        source.select(
            *KEYS,
            pl.col("b0v2_max_predictor_available_at_utc").alias("max_predictor_available_at_utc"),
            pl.col("b0v2_predictor_missing_reason").alias("predictor_drop_reason"),
            *B0V2_FEATURES,
        )
        .join(
            targets.select(
                "origin_id",
                "target_price_count",
                "target_return_count",
                "rv30",
                pl.col("drop_reason").alias("target_drop_reason"),
            ),
            on="origin_id",
            how="left",
            validate="1:1",
        )
        .with_columns(
            pl.coalesce("target_drop_reason", "predictor_drop_reason").alias("drop_reason")
        )
        .drop("target_drop_reason", "predictor_drop_reason")
    )
    b1 = source.select(
        *KEYS,
        "forecast_origin_ns",
        "max_sip_timestamp_ns",
        *B1V2A_FEATURES,
        *B1V2B_FEATURES,
        *B1V2C_FEATURES,
        "b1v2a_complete",
        "b1v2b_complete",
        "b1v2c_complete",
    )
    b2 = source.select(
        *KEYS,
        *B2V2_FEATURES,
        "b2v2_complete",
        "b2v2_cutoff_utc",
        "b2v2_max_created_at_utc",
    )
    all_rows, common = build_phase6_common_panel(origins, b0, b1, b2)
    _validate_target_linkage(source, targets, common)
    return all_rows, common


def _complete_feature_rows(panel: pl.DataFrame, features: Sequence[str]) -> pl.DataFrame:
    numeric = [name for name in features if name != "b0v2_asset_identity"]
    return panel.filter(
        pl.all_horizontal(pl.col(name).is_finite() for name in numeric)
        & pl.col("b0v2_asset_identity").is_not_null()
    )


def _forecast_primary(
    panel: pl.DataFrame, preregistration: Mapping[str, Any]
) -> tuple[pl.DataFrame, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    guard = int(preregistration["models"]["purge_embargo_minutes"])
    parts: list[pl.DataFrame] = []
    variants: list[dict[str, Any]] = []
    selections: list[dict[str, Any]] = []
    cutpoints: list[dict[str, Any]] = []
    for fold in phase6_fold_definitions(preregistration):
        training, testing = split_expanding_fold(
            panel, fold, purge_minutes=guard, embargo_minutes=guard
        )
        testing, thresholds = add_training_volatility_regime(training, testing)
        cutpoints.append({"fold": fold.fold, **thresholds})
        for information_set, features in phase6_information_sets().items():
            for role in MODEL_ROLES:
                selected, records = select_phase6_parameters(
                    training,
                    fold=fold,
                    information_set=information_set,
                    features=features,
                    role=role,
                    preregistration=preregistration,
                )
                variants.extend(records)
                selections.append(
                    {
                        "fold": fold.fold,
                        "information_set": information_set,
                        "model_role": role,
                        "parameters": selected,
                    }
                )
                parts.append(
                    forecast_phase6_fold(
                        training,
                        testing,
                        fold=fold,
                        information_set=information_set,
                        features=features,
                        role=role,
                        parameters=selected,
                        preregistration=preregistration,
                    )
                )
    forecasts = pl.concat(parts).sort(["fold", "model_role", "information_set", "origin_id"])
    expected = forecasts["origin_id"].n_unique()
    if expected == 0 or forecasts.height != expected * 3 * len(MODEL_ROLES):
        raise RuntimeError("PIT_V22_PRIMARY_FORECAST_PAIRING_FAILURE")
    return forecasts, variants, selections, cutpoints


def _forecast_b1_robustness(
    panel: pl.DataFrame, preregistration: Mapping[str, Any]
) -> tuple[pl.DataFrame, list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    guard = int(preregistration["models"]["purge_embargo_minutes"])
    information_sets = phase6_information_sets(include_b1_robustness=True)
    parts: list[pl.DataFrame] = []
    variants: list[dict[str, Any]] = []
    selections: list[dict[str, Any]] = []
    sample_counts: list[dict[str, Any]] = []
    for expanded in ("B1v2b", "B1v2c"):
        sample = _complete_feature_rows(panel, information_sets[expanded])
        sample_counts.append(
            {
                "information_set": expanded,
                "rows": sample.height,
                "sessions": sample["session_date"].n_unique(),
            }
        )
        baseline = f"B0v2_on_{expanded}_sample"
        for fold in phase6_fold_definitions(preregistration):
            training, testing = split_expanding_fold(
                sample, fold, purge_minutes=guard, embargo_minutes=guard
            )
            testing, _ = add_training_volatility_regime(training, testing)
            for information_set, features in (
                (baseline, information_sets["B0v2"]),
                (expanded, information_sets[expanded]),
            ):
                for role in MODEL_ROLES:
                    selected, records = select_phase6_parameters(
                        training,
                        fold=fold,
                        information_set=information_set,
                        features=features,
                        role=role,
                        preregistration=preregistration,
                    )
                    variants.extend(records)
                    selections.append(
                        {
                            "fold": fold.fold,
                            "sample": expanded,
                            "information_set": information_set,
                            "model_role": role,
                            "parameters": selected,
                        }
                    )
                    parts.append(
                        forecast_phase6_fold(
                            training,
                            testing,
                            fold=fold,
                            information_set=information_set,
                            features=features,
                            role=role,
                            parameters=selected,
                            preregistration=preregistration,
                        ).with_columns(pl.lit(expanded).alias("robustness_sample"))
                    )
    forecasts = pl.concat(parts).sort(
        ["robustness_sample", "fold", "model_role", "information_set", "origin_id"]
    )
    contrasts = [
        {
            **phase6_contrast(
                forecasts.filter((pl.col("robustness_sample") == expanded) & (pl.col("fold") == 2)),
                role=role,
                name=f"{expanded.lower()}_over_b0",
                baseline=f"B0v2_on_{expanded}_sample",
                expanded=expanded,
                preregistration=preregistration,
            ),
            "robustness_sample": expanded,
            "evaluation_scope": "HOLDOUT_ONLY",
        }
        for expanded in ("B1v2b", "B1v2c")
        for role in MODEL_ROLES
    ]
    return forecasts, variants, selections, [*sample_counts, *contrasts]


def _runtime_method(
    preregistration: Mapping[str, Any],
    method_template: Mapping[str, Any],
    *,
    development_panel_sha256: str,
    method_template_sha256: str,
    training_mde: Mapping[str, float],
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "pit-v22-successor-runtime-method-freeze-1.0",
        "status": "FROZEN_AFTER_DEVELOPMENT_BEFORE_OOS",
        "oos_read_count": 0,
        "signed_freeze_sha256": EXPECTED_SIGNED_FREEZE_SHA256,
        "owner_authorization_sha256": EXPECTED_OWNER_AUTHORIZATION_SHA256,
        "source_preregistration_sha256": preregistration["source_preregistration_sha256"],
        "runtime_preregistration_sha256": preregistration["manifest_sha256"],
        "bound_target_free_panel_sha256": preregistration["bound_panel_sha256"],
        "development_linked_common_panel_sha256": development_panel_sha256,
        "source_bars_sha256": preregistration["source_bars_sha256"],
        "method_template_sha256": method_template_sha256,
        "uv_lock_sha256": _sha256(ROOT / "uv.lock"),
        "execution_commit": _git("rev-parse", "HEAD").stdout.strip(),
        "execution_tree": _git("rev-parse", "HEAD^{tree}").stdout.strip(),
        "models": method_template["models"],
        "inference": method_template["inference"],
        "edge_promotion_rule": "NOT_PREDECLARED_IN_SIGNED_SUCCESSOR_FREEZE",
        "training_mde": dict(training_mde),
        "mde_method": {
            **method_template["mde_method"],
            "scope": "DEVELOPMENT_95_SESSIONS_LAST_30_OOF_ONLY",
        },
        "timing_sensitivities_in_this_run": "NOT_EVALUATED",
        "information_sets": preregistration["information_sets"],
        "source_code_hashes": {
            path.relative_to(ROOT).as_posix(): _sha256(path)
            for path in (
                ROOT / "scripts" / "run_pit_v22_successor_once.py",
                ROOT / "src" / "mds650" / "phase6.py",
                ROOT / "src" / "mds650" / "phase6_evaluation.py",
                ROOT / "src" / "mds650" / "metrics.py",
                ROOT / "src" / "mds650" / "modeling.py",
                ROOT / "src" / "mds650" / "temporal_validation.py",
            )
        },
    }
    if PROTOCOL_VERSION == "v2":
        payload["target_linkage_eligibility_policy"] = dict(TARGET_LINKAGE_POLICY)
        payload["data_defect_resolution_sha256"] = EXPECTED_DATA_DEFECT_RESOLUTION_SHA256
    payload["manifest_sha256"] = canonical_sha256(payload)
    return payload


def _mde_annotations(
    evaluation: Mapping[str, Any], training_mde: Mapping[str, float]
) -> dict[str, Any]:
    return {
        role: {
            contrast: {
                "estimate": evaluation["global"][role][contrast]["estimate"],
                "training_mde": training_mde[contrast],
                "estimate_at_least_mde": evaluation["global"][role][contrast]["estimate"]
                >= training_mde[contrast],
                "mde_role": (
                    "CONFIRMATORY_THRESHOLD"
                    if role == "gamma_glm_confirmatory"
                    else "DESCRIPTIVE_REFERENCE_ONLY"
                ),
            }
            for contrast in ("delta_b1v2", "delta_b2v2")
        }
        for role in MODEL_ROLES
    }


def _execute() -> dict[str, Any]:
    preregistration, preflight = _preflight(require_clean=True)
    GATED_ROOT.mkdir(parents=True, exist_ok=False)
    paths = {
        "claim": GATED_ROOT / "one_shot_claim.json",
        "log": GATED_ROOT / TRACKED_LOG.name,
        "preregistration": GATED_ROOT / "runtime_preregistration.json",
        "development_panel": GATED_ROOT / "development_linked_common_panel.parquet",
        "panel": GATED_ROOT / "linked_common_panel.parquet",
        "mde_forecasts": GATED_ROOT / "development_mde_oof_forecasts.parquet",
        "method": GATED_ROOT / "runtime_method_freeze.json",
        "ledger": GATED_ROOT / "oos_access_ledger.json",
        "predictions": GATED_ROOT / "oos_primary_predictions.parquet",
        "robustness_predictions": GATED_ROOT / "oos_b1_robustness_predictions.parquet",
        "variants": GATED_ROOT / "variant_ledger.json",
        "result": GATED_ROOT / TRACKED_RESULT.name,
    }
    claim = {
        "schema_version": "pit-v22-successor-one-shot-claim-1.0",
        "status": "TARGET_BUILD_IN_PROGRESS",
        "run_id": RUN_ID,
        "contract_sha256": _sha256(SIGNED_FREEZE),
        "claimed_at_utc": datetime.now(UTC).isoformat(),
    }
    claim_one_shot(paths["claim"], claim)
    events: list[dict[str, Any]] = []
    try:
        attempt_ledger: dict[str, Any] = {
            "schema_version": "pit-v22-successor-oos-access-ledger-1.0",
            "status": "ONE_SHOT_CLAIMED_DEVELOPMENT_ONLY",
            "run_id": RUN_ID,
            "evaluation_attempt_count": 1,
            "oos_read_count": 0,
            "results_inspected": False,
            "rerun_allowed": False,
            "contract_sha256": claim["contract_sha256"],
            "bound_panel_sha256": preflight["source_panel_sha256"],
            "runtime_preregistration_sha256": preregistration["manifest_sha256"],
        }
        attempt_ledger["manifest_sha256"] = canonical_sha256(attempt_ledger)
        _write_json(paths["ledger"], attempt_ledger)
        _event(events, paths["log"], "ONE_SHOT_CLAIMED", run_id=RUN_ID)
        _write_json(paths["preregistration"], preregistration)
        _event(
            events,
            paths["log"],
            "RUNTIME_PREREGISTRATION_FROZEN",
            sha256=_sha256(paths["preregistration"]),
        )

        panel_sha256 = _sha256(SOURCE_PANEL)
        bars_sha256 = _sha256(SOURCE_BARS)
        if (
            panel_sha256 != preflight["source_panel_sha256"]
            or bars_sha256 != preflight["source_bars_sha256"]
        ):
            raise RuntimeError("PIT_V22_SOURCE_CHANGED_BEFORE_TARGET_BUILD")
        development_dates = preregistration["folds"][0]["train_dates"]
        development_source = (
            pl.scan_parquet(SOURCE_PANEL)
            .filter(pl.col("session_date").is_in(development_dates))
            .collect()
        )
        development_bars = (
            pl.scan_parquet(SOURCE_BARS)
            .filter(pl.col("session_date").is_in(development_dates))
            .collect()
        )
        development_all, development = _linked_panel(development_source, development_bars)
        development_predictor_complete_rows = development_source.filter(
            pl.col("common_predictor_complete")
        ).height
        development_target_exclusions = development_predictor_complete_rows - development.height
        if PROTOCOL_VERSION == "v2" and development_target_exclusions != 6:
            raise RuntimeError("PIT_V22_DEVELOPMENT_TARGET_EXCLUSION_COUNT_INVALID")
        _write_parquet(paths["development_panel"], development)
        _event(
            events,
            paths["log"],
            "DEVELOPMENT_RV30_LINKED",
            rows=development.height,
            target_linkage_excluded_origins=development_target_exclusions,
            development_panel_sha256=_sha256(paths["development_panel"]),
        )

        mde_forecasts, mde_variants = training_only_oof_forecasts(development, preregistration)
        _write_parquet(paths["mde_forecasts"], mde_forecasts)
        method_template, method_template_sha256 = _read_json_with_sha256(METHOD_TEMPLATE)
        if (
            method_template_sha256 != preflight["method_template_sha256"]
            or _git("status", "--porcelain").stdout.strip()
        ):
            raise RuntimeError("PIT_V22_METHOD_OR_CODE_CHANGED_BEFORE_FREEZE")
        training_mde = training_mde_from_forecasts(
            mde_forecasts,
            draws=int(preregistration["inference"]["bootstrap_repetitions"]),
            seed=int(preregistration["inference"]["seed"]),
        )
        method = _runtime_method(
            preregistration,
            method_template,
            development_panel_sha256=_sha256(paths["development_panel"]),
            method_template_sha256=preflight["method_template_sha256"],
            training_mde=training_mde,
        )
        _write_json(paths["method"], method)
        runtime_method_sha256 = _sha256(paths["method"])
        _event(
            events,
            paths["log"],
            "DEVELOPMENT_MDE_FROZEN",
            training_mde=training_mde,
            method_sha256=runtime_method_sha256,
        )

        result_paths = (
            TRACKED_RESULT,
            TRACKED_LOG,
            paths["predictions"],
            paths["robustness_predictions"],
            paths["variants"],
            paths["result"],
        )
        authorization_document, authorization_sha256 = _read_json_with_sha256(OWNER_AUTHORIZATION)
        if (
            _sha256(SIGNED_FREEZE) != preflight["signed_freeze_sha256"]
            or authorization_sha256 != preflight["owner_authorization_sha256"]
            or _sha256(SOURCE_PANEL) != preflight["source_panel_sha256"]
            or _sha256(SOURCE_BARS) != preflight["source_bars_sha256"]
            or _sha256(paths["method"]) != runtime_method_sha256
            or _git("status", "--porcelain").stdout.strip()
        ):
            raise RuntimeError("PIT_V22_SIGNED_INPUT_CHANGED_BEFORE_AUTHORIZATION")
        authorization = authorize_phase6_oos(
            authorization_document,
            common_panel_sha256=panel_sha256,
            preregistration_manifest_sha256=preregistration["manifest_sha256"],
            results_exist=any(path.exists() for path in result_paths),
            contract_sha256=preflight["signed_freeze_sha256"],
        )
        _write_json(paths["ledger"], authorization)
        _event(
            events,
            paths["log"],
            "OOS_AUTHORIZATION_CONSUMED",
            oos_read_count=1,
            evaluation_attempt_count=1,
        )

        all_session_dates = pl.read_parquet(SOURCE_PANEL, columns=["session_date"])[
            "session_date"
        ].unique()
        remaining_dates = sorted(set(all_session_dates) - set(development_dates))
        remaining_source = (
            pl.scan_parquet(SOURCE_PANEL)
            .filter(pl.col("session_date").is_in(remaining_dates))
            .collect()
        )
        remaining_bars = (
            pl.scan_parquet(SOURCE_BARS)
            .filter(pl.col("session_date").is_in(remaining_dates))
            .collect()
        )
        if (
            _sha256(SOURCE_PANEL) != preflight["source_panel_sha256"]
            or _sha256(SOURCE_BARS) != preflight["source_bars_sha256"]
            or _sha256(paths["method"]) != runtime_method_sha256
        ):
            raise RuntimeError("PIT_V22_SOURCE_CHANGED_DURING_OOS_MATERIALIZATION")
        remaining_all, remaining_common = _linked_panel(remaining_source, remaining_bars)
        all_rows = pl.concat([development_all, remaining_all]).sort(
            ["session_date", "forecast_origin_utc", "asset"]
        )
        common = pl.concat([development, remaining_common]).sort(
            ["session_date", "forecast_origin_utc", "asset"]
        )
        target_linkage_excluded_origins = preflight["source_common_complete_rows"] - common.height
        if (
            all_rows.height != preflight["source_rows"]
            or common.height <= 0
            or target_linkage_excluded_origins < 0
        ):
            raise RuntimeError("PIT_V22_TARGET_LINKAGE_COUNTS_INVALID")
        _write_parquet(paths["panel"], common)
        linked_panel_sha256 = _sha256(paths["panel"])
        common = validate_phase6_evaluation_panel(common, preregistration)
        _event(
            events,
            paths["log"],
            "OOS_RV30_LINKED_AND_VALIDATED",
            rows=common.height,
            target_linkage_excluded_origins=target_linkage_excluded_origins,
            linked_panel_sha256=linked_panel_sha256,
        )

        predictions, variants, selections, cutpoints = _forecast_primary(common, preregistration)
        _write_parquet(paths["predictions"], predictions)
        robustness_predictions, robustness_variants, robustness_selections, robustness = (
            _forecast_b1_robustness(common, preregistration)
        )
        _write_parquet(paths["robustness_predictions"], robustness_predictions)
        variant_ledger = {
            "schema_version": "pit-v22-successor-variant-ledger-1.0",
            "status": "COMPLETE",
            "oos_read_count": 1,
            "mde_variants": mde_variants,
            "oos_variants": [*variants, *robustness_variants],
            "selected_variants": [*selections, *robustness_selections],
            "volatility_regime_cutpoints": cutpoints,
            "all_variants_retained": True,
        }
        variant_ledger["manifest_sha256"] = canonical_sha256(variant_ledger)
        _write_json(paths["variants"], variant_ledger)
        _event(
            events,
            paths["log"],
            "TWO_EXPANDING_FOLDS_FORECAST",
            evaluated_origins=predictions["origin_id"].n_unique(),
            prediction_rows=predictions.height,
        )

        holdout_predictions = predictions.filter(pl.col("fold") == 2)
        evaluation = evaluate_phase6(holdout_predictions, method)
        annotations = _mde_annotations(evaluation, training_mde)
        edge_claim_eligible = False
        _event(
            events,
            paths["log"],
            "EVALUATION_COMPLETE",
            decision=evaluation["decision"],
            edge_claim_eligible=edge_claim_eligible,
        )
        content_addressed_payloads: dict[str, str] = {}
        for protocol_id, path in {
            "runtime-preregistration": paths["preregistration"],
            "development-linked-panel": paths["development_panel"],
            "linked-common-panel": paths["panel"],
            "development-mde-forecasts": paths["mde_forecasts"],
            "runtime-method-freeze": paths["method"],
            "primary-predictions": paths["predictions"],
            "b1-robustness-predictions": paths["robustness_predictions"],
            "variant-ledger": paths["variants"],
        }.items():
            payload = path.read_bytes()
            digest = hashlib.sha256(payload).hexdigest()
            addressed = write_content_addressed(
                payload,
                root=GATED_ROOT / "content_addressed",
                protocol_id=protocol_id,
            )
            if addressed.stem != digest:
                raise RuntimeError("PIT_V22_CONTENT_ADDRESS_MISMATCH")
            content_addressed_payloads[protocol_id] = digest
        if content_addressed_payloads["linked-common-panel"] != linked_panel_sha256:
            raise RuntimeError("PIT_V22_LINKED_PANEL_SNAPSHOT_MISMATCH")
        if content_addressed_payloads["runtime-method-freeze"] != runtime_method_sha256:
            raise RuntimeError("PIT_V22_RUNTIME_METHOD_SNAPSHOT_MISMATCH")
        _event(
            events,
            paths["log"],
            "PRIMARY_PAYLOADS_CONTENT_ADDRESSED",
            payload_count=len(content_addressed_payloads),
        )
        result: dict[str, Any] = {
            "schema_version": "pit-v22-successor-evaluation-result-1.0",
            "status": "SCIENTIFIC_EVALUATION_COMPLETE_PENDING_CUSTODY_VALIDATION",
            "run_id": RUN_ID,
            "evaluation_attempt_count": 1,
            "oos_read_count": 1,
            "all_signs_retained": True,
            "split_session_counts": preflight["split_session_counts"],
            "evaluation_scope": "HOLDOUT_ONLY",
            "validation_forecasts_retained_without_confirmatory_inference": True,
            "source_rows": preflight["source_rows"],
            "linked_common_complete_rows": common.height,
            "target_linkage_excluded_origins": target_linkage_excluded_origins,
            "holdout_evaluated_origins": holdout_predictions["origin_id"].n_unique(),
            "evaluation": evaluation,
            "mde_annotations": annotations,
            "b1_information_set_robustness": robustness,
            "eligibility": {
                "scientific_result_eligible": False,
                "edge_claim_eligible": edge_claim_eligible,
                "capital_eligible": False,
                "capital_go": False,
                "research_only": True,
                "scientific_result_reason": "PENDING_CANONICAL_CUSTODY_VALIDATION",
                "edge_claim_reason": "NO_BINARY_EDGE_PROMOTION_RULE_IN_SIGNED_SUCCESSOR_FREEZE",
                "evaluator_diagnostic_decision": evaluation["decision"],
            },
            "content_addressed_primary_payloads": content_addressed_payloads,
            "limitations": [
                "UNUSUAL_WHALES_CREATED_AT_IS_AN_OPERATIONAL_AVAILABILITY_PROXY",
                "TIMING_SENSITIVITY_FORECASTS_NOT_EVALUATED_IN_THIS_SUCCESSOR_RUN",
                "NO_CAUSAL_OR_TRADING_PROFITABILITY_CLAIM",
                "RESEARCH_ONLY_NOT_INVESTMENT_ADVICE",
            ],
            "hashes": {
                "signed_freeze_sha256": preflight["signed_freeze_sha256"],
                "owner_authorization_sha256": preflight["owner_authorization_sha256"],
                "source_preregistration_sha256": preregistration["source_preregistration_sha256"],
                "runtime_preregistration_sha256": preregistration["manifest_sha256"],
                "source_target_free_panel_sha256": preflight["source_panel_sha256"],
                "source_bars_sha256": bars_sha256,
                "development_linked_common_panel_sha256": content_addressed_payloads[
                    "development-linked-panel"
                ],
                "linked_common_panel_sha256": content_addressed_payloads["linked-common-panel"],
                "development_mde_forecasts_sha256": content_addressed_payloads[
                    "development-mde-forecasts"
                ],
                "runtime_method_freeze_sha256": content_addressed_payloads["runtime-method-freeze"],
                "primary_predictions_sha256": content_addressed_payloads["primary-predictions"],
                "b1_robustness_predictions_sha256": content_addressed_payloads[
                    "b1-robustness-predictions"
                ],
                "variant_ledger_sha256": content_addressed_payloads["variant-ledger"],
            },
            "personal_paths_emitted": False,
            "secret_values_emitted": False,
        }
        if PROTOCOL_VERSION == "v2":
            result["target_linkage_eligibility_policy"] = dict(TARGET_LINKAGE_POLICY)
            result["hashes"]["data_defect_resolution_sha256"] = preflight[
                "data_defect_resolution_sha256"
            ]
        result["manifest_sha256"] = canonical_sha256(result)
        _assert_public_payload(result)
        result_payload = _json_bytes(result)
        result_address = write_content_addressed(
            result_payload,
            root=GATED_ROOT / "content_addressed",
            protocol_id="successor-result",
        )
        if result_address.stem != hashlib.sha256(result_payload).hexdigest():
            raise RuntimeError("PIT_V22_RESULT_CONTENT_ADDRESS_MISMATCH")
        _write_json(paths["result"], result)
        result_sha256 = _write_new_json(TRACKED_RESULT, result)
        _event(
            events,
            paths["log"],
            "RESULT_WRITTEN",
            result_sha256=result_sha256,
        )
        completed_ledger = {
            **{key: value for key, value in authorization.items() if key != "manifest_sha256"},
            "status": "OOS_CONSUMED_RESULTS_REPORTED",
            "results_inspected": True,
            "result_sha256": result_sha256,
            "decision": evaluation["decision"],
        }
        completed_ledger["manifest_sha256"] = canonical_sha256(completed_ledger)
        _write_json(paths["ledger"], completed_ledger)
        _event(
            events,
            paths["log"],
            "LEDGER_CLOSED",
            status=completed_ledger["status"],
        )
        _write_json(
            paths["claim"],
            {
                **claim,
                "status": "COMPLETE_REPORTED",
                "result_sha256": result_sha256,
                "completed_at_utc": datetime.now(UTC).isoformat(),
            },
        )
        _event(
            events,
            paths["log"],
            "CLAIM_CLOSED",
            status="COMPLETE_REPORTED",
        )
        public_log = _log_payload(events)
        _assert_public_payload(public_log)
        log_payload = _json_bytes(public_log)
        log_address = write_content_addressed(
            log_payload,
            root=GATED_ROOT / "content_addressed",
            protocol_id="successor-log",
        )
        if log_address.stem != hashlib.sha256(log_payload).hexdigest():
            raise RuntimeError("PIT_V22_LOG_CONTENT_ADDRESS_MISMATCH")
        log_sha256 = _write_new_json(TRACKED_LOG, public_log)
        return {
            "status": "PASS_ONE_SHOT_EVALUATION_COMPLETE",
            "decision": evaluation["decision"],
            "result_sha256": result_sha256,
            "full_log_sha256": log_sha256,
        }
    except BaseException as error:
        message = str(error)
        safe_message = message if re.fullmatch(r"[A-Z0-9_:.-]+", message) else "DETAIL_REDACTED"
        failure_code = f"{type(error).__name__}:{safe_message or 'NO_MESSAGE'}"
        current_ledger = (
            _read_json(paths["ledger"])
            if paths["ledger"].exists()
            else {
                "schema_version": "pit-v22-successor-oos-access-ledger-1.0",
                "run_id": RUN_ID,
                "evaluation_attempt_count": 1,
                "oos_read_count": 0,
            }
        )
        failed_ledger = {
            **{key: value for key, value in current_ledger.items() if key != "manifest_sha256"},
            "status": "FAIL_CLOSED",
            "failure_code": failure_code,
            "rerun_allowed": False,
        }
        failed_ledger["manifest_sha256"] = canonical_sha256(failed_ledger)
        _write_json(paths["ledger"], failed_ledger)
        _write_json(
            paths["claim"],
            {
                **claim,
                "status": "FAIL_CLOSED",
                "failure_code": failure_code,
                "rerun_allowed": False,
                "failed_at_utc": datetime.now(UTC).isoformat(),
            },
        )
        _event(
            events,
            paths["log"],
            "FAIL_CLOSED",
            error_type=type(error).__name__,
            error=failure_code,
            rerun_allowed=False,
        )
        public_failure_log = _log_payload(events)
        _assert_public_payload(public_failure_log)
        if not TRACKED_LOG.exists():
            _write_new_json(TRACKED_LOG, public_failure_log)
        raise


def main() -> None:
    global GATED_ROOT, SOURCE_BARS, SOURCE_PANEL
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--execute", action="store_true")
    parser.add_argument("--protocol-version", choices=tuple(PROTOCOL_CONFIGS), default="v1")
    parser.add_argument("--source-panel", type=Path, required=True)
    parser.add_argument("--source-bars", type=Path, required=True)
    parser.add_argument("--gated-root", type=Path, required=True)
    args = parser.parse_args()
    configure_protocol(args.protocol_version)
    SOURCE_PANEL = args.source_panel
    SOURCE_BARS = args.source_bars
    GATED_ROOT = args.gated_root
    if args.preflight_only:
        _, summary = _preflight(require_clean=True)
    else:
        summary = _execute()
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
