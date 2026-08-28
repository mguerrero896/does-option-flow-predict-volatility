"""One-shot Phase 8A bridge evaluator bound to the frozen v2 contract.

Without a separate owner token this module may inspect only sanitized store metadata.
After validation it atomically claims the sole read, advances the store read counter
from zero to one, verifies every captured payload, reuses the existing RP3 panel adapter,
and scores the registered 20-session primary and 30-session sensitivity windows.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import shutil
import sys
import tempfile
from collections import Counter
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Final

import numpy as np
import numpy.typing as npt
import polars as pl

from mds650.b1v3_confirmation import enumerate_xnys_sessions
from mds650.executable_closure import build_executable_closure
from mds650.metrics import holm_adjust, qlike_losses
from mds650.providers.fmp import parse_minute_payload
from mds650.rp2.inference import aggregate_by_session, newey_west_p_value
from mds650.rp2.ladder import canonical_float_array_sha256, fit_ladder_model
from mds650.rp2.panel import (
    B0_FEATURES,
    B1_FEATURES,
    B2_FEATURES,
    TARGET_ASSETS,
    common_evaluation_mask,
    load_merged_panel,
    panel_paths,
    session_rank,
)
from mds650.rp2.preprocessing import fold_design

ROOT: Final = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT: Final = ROOT / "artifacts" / "phase8_bridge" / "bridge_contract_v2.json"
DEFAULT_EVALUATOR_FREEZE: Final = (
    ROOT / "artifacts" / "phase8_bridge" / "evaluator_freeze_v4.json"
)
EXECUTABLE_SCRIPTS: Final = (
    "scripts/evaluate_phase8_bridge_v2.py",
    "scripts/download_calibration_20d.py",
    "scripts/rp3_acquire_batch.py",
    "scripts/rp3_build_eval_panels.py",
    "scripts/rp2_block3_target_panel.py",
    "scripts/rp2_block4_b0_panel.py",
    "scripts/rp2_block5_surface_panel.py",
    "scripts/rp2_block6_flow_panel.py",
)
MODELS: Final = ("gamma_glm", "lightgbm")
BAR_ASSETS: Final = tuple(sorted((*TARGET_ASSETS, "SPY", "QQQ")))
INFORMATION_SETS: Final = {
    "B0": [*B0_FEATURES],
    "B0+B1": [*B0_FEATURES, *B1_FEATURES],
    "B0+B2": [*B0_FEATURES, *B2_FEATURES],
    "B0+B1+B2": [*B0_FEATURES, *B1_FEATURES, *B2_FEATURES],
}
PAIRS: Final = {
    "delta_b1": ("B0", "B0+B1"),
    "delta_b2_given_b1": ("B0+B1", "B0+B1+B2"),
    "delta_b2_given_b0": ("B0", "B0+B2"),
    "delta_total": ("B0", "B0+B1+B2"),
}
GIB: Final = 1024**3
type FloatArray = npt.NDArray[np.float64]
type IntArray = npt.NDArray[np.int64]


def _canonical_sha256(payload: Mapping[str, Any], *, omit: str) -> str:
    body = {key: value for key, value in payload.items() if key != omit}
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    try:
        with temporary.open("w", encoding="utf-8", newline="\n") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _load_script(name: str) -> Any:
    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"PHASE8_BRIDGE_SCRIPT_UNAVAILABLE:{name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_contract(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("PHASE8_BRIDGE_CONTRACT_INVALID")
    contract: dict[str, Any] = value
    if contract.get("contract_sha256") != _canonical_sha256(contract, omit="contract_sha256"):
        raise RuntimeError("PHASE8_BRIDGE_CONTRACT_HASH_INVALID")
    if contract.get("status") != "TARGET_BLIND_METHOD_FROZEN_READ_NOT_AUTHORIZED":
        raise RuntimeError("PHASE8_BRIDGE_CONTRACT_STATUS_INVALID")
    if tuple(contract.get("models", {}).get("families", ())) != MODELS:
        raise RuntimeError("PHASE8_BRIDGE_MODEL_FAMILY_DRIFT")
    return contract


def validate_evaluator_freeze(path: Path, contract: Mapping[str, Any]) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise RuntimeError("PHASE8_BRIDGE_EVALUATOR_FREEZE_INVALID")
    freeze: dict[str, Any] = value
    if freeze.get("freeze_sha256") != _canonical_sha256(freeze, omit="freeze_sha256"):
        raise RuntimeError("PHASE8_BRIDGE_EVALUATOR_FREEZE_HASH_INVALID")
    closure = build_executable_closure(ROOT, scripts=EXECUTABLE_SCRIPTS)
    evaluator_hash = next(
        row["sha256"]
        for row in closure["files"]
        if row["path"] == "scripts/evaluate_phase8_bridge_v2.py"
    )
    if (
        freeze.get("status")
        != "TARGET_BLIND_EXECUTABLE_CLOSURE_FROZEN_READ_NOT_AUTHORIZED"
        or freeze.get("protocol_id") != contract["protocol_id"]
        or freeze.get("contract_sha256") != contract["contract_sha256"]
        or freeze.get("evaluator_sha256") != evaluator_hash
        or freeze.get("executable_closure") != closure
    ):
        raise RuntimeError("PHASE8_BRIDGE_EVALUATOR_FREEZE_DRIFT")
    return freeze


def validate_authorization(path: Path | None, contract: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the future owner token without touching a Phase 8 store path."""

    if path is None or not path.is_file():
        raise PermissionError("PHASE8_BRIDGE_ONE_SHOT_AUTHORIZATION_REQUIRED")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PermissionError("PHASE8_BRIDGE_ONE_SHOT_AUTHORIZATION_INVALID")
    token: dict[str, Any] = value
    required = {
        "authorization_type": "PHASE8_BRIDGE_ONE_SHOT_READ",
        "protocol_id": contract["protocol_id"],
        "contract_sha256": contract["contract_sha256"],
        "authorize_read_and_evaluation": True,
        "sealed_cohorts_read_before": 0,
    }
    if any(token.get(key) != expected for key, expected in required.items()):
        raise PermissionError("PHASE8_BRIDGE_ONE_SHOT_AUTHORIZATION_INVALID")
    for field in ("authorization_id", "authorized_by", "authorized_at_utc"):
        if not isinstance(token.get(field), str) or not token[field].strip():
            raise PermissionError(f"PHASE8_BRIDGE_ONE_SHOT_{field.upper()}_MISSING")
    return token


def _window_sessions(contract: Mapping[str, Any], role: str) -> tuple[str, ...]:
    spec = contract["cohort"][role]
    start, end = str(spec["window"]).split("..", maxsplit=1)
    sessions = enumerate_xnys_sessions(date.fromisoformat(start), date.fromisoformat(end))
    if len(sessions) != int(spec["sessions"]):
        raise RuntimeError(f"PHASE8_BRIDGE_FROZEN_WINDOW_INVALID:{role}")
    return sessions


def _raw_path(holdout_root: Path, record: Mapping[str, Any]) -> Path:
    relative = Path(str(record.get("relative_path", "")))
    path = (holdout_root / relative).resolve()
    raw = (holdout_root / "raw").resolve()
    try:
        path.relative_to(raw)
    except ValueError as error:
        raise RuntimeError("PHASE8_BRIDGE_RAW_PATH_ESCAPE") from error
    return path


def preflight_holdout(
    holdout_root: Path, contract: Mapping[str, Any]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Validate calendar, checkpoints, records and file metadata without reading payloads."""

    requested_root = holdout_root
    root = requested_root.resolve()
    required = {
        "manifest": root / "manifest.json",
        "counter": root / "access_counter.json",
        "checkpoints": root / "checkpoints.json",
        "records": root / "records.jsonl",
        # The operational store is a Windows junction; its frozen calendar lives
        # beside the junction in the recovery checkout, not beside its resolved target.
        "calendar": requested_root.parent / "holdout_manifest.json",
    }
    missing = sorted(name for name, path in required.items() if not path.is_file())
    if missing:
        raise RuntimeError(f"PHASE8_BRIDGE_STORE_METADATA_MISSING:{','.join(missing)}")

    calendar = json.loads(required["calendar"].read_text(encoding="utf-8"))
    expected_sessions = _window_sessions(contract, "sensitivity")
    if (
        int(calendar.get("session_count", -1)) != len(expected_sessions)
        or tuple(str(value) for value in calendar.get("sessions", ())) != expected_sessions
        or int(calendar.get("holdout_reads", -1)) != 0
    ):
        raise RuntimeError("PHASE8_BRIDGE_CALENDAR_IDENTITY_MISMATCH")

    manifest = json.loads(required["manifest"].read_text(encoding="utf-8"))
    if (
        manifest.get("namespace") != "holdout"
        or manifest.get("manifest_sha256")
        != _canonical_sha256(manifest, omit="manifest_sha256")
    ):
        raise RuntimeError("PHASE8_BRIDGE_STORE_MANIFEST_INVALID")

    counter = json.loads(required["counter"].read_text(encoding="utf-8"))
    if int(counter.get("read_count", -1)) != 0:
        raise RuntimeError("PHASE8_BRIDGE_STORE_ALREADY_READ")

    checkpoints = json.loads(required["checkpoints"].read_text(encoding="utf-8"))
    if int(checkpoints.get("completed_count", -1)) != len(expected_sessions):
        raise RuntimeError("PHASE8_BRIDGE_ACQUISITION_INCOMPLETE")
    checkpoint_sessions = checkpoints.get("sessions", {})
    for session in expected_sessions:
        providers = checkpoint_sessions.get(session, {})
        if any(
            providers.get(provider, {}).get("status") != "PASS"
            for provider in ("fmp", "unusual_whales", "massive")
        ):
            raise RuntimeError(f"PHASE8_BRIDGE_PROVIDER_CHECKPOINT_INCOMPLETE:{session}")

    records: list[dict[str, Any]] = []
    fingerprints: set[str] = set()
    counts: Counter[tuple[str, str]] = Counter()
    with required["records"].open(encoding="utf-8") as stream:
        for line in stream:
            value = json.loads(line)
            if not isinstance(value, dict):
                raise RuntimeError("PHASE8_BRIDGE_RECORD_INVALID")
            record: dict[str, Any] = value
            session = str(record.get("requested_session"))
            provider = str(record.get("provider"))
            fingerprint = str(record.get("request_fingerprint"))
            if (
                session not in expected_sessions
                or provider not in {"fmp", "unusual_whales", "massive"}
                or fingerprint in fingerprints
                or record.get("http_status") != 200
                or record.get("schema_valid") is not True
                or record.get("checkpoint_status") != "PASS"
            ):
                raise RuntimeError("PHASE8_BRIDGE_RECORD_SET_INVALID")
            path = _raw_path(root, record)
            if not path.is_file() or path.stat().st_size != int(record.get("byte_count", -1)):
                raise RuntimeError("PHASE8_BRIDGE_RAW_FILE_METADATA_MISMATCH")
            fingerprints.add(fingerprint)
            counts[(session, provider)] += 1
            records.append(record)
    for session in expected_sessions:
        if (
            counts[(session, "fmp")] != len(BAR_ASSETS)
            or counts[(session, "unusual_whales")] != 1
            or counts[(session, "massive")] < len(BAR_ASSETS)
        ):
            raise RuntimeError(f"PHASE8_BRIDGE_RECORD_COVERAGE_INVALID:{session}")
    return records, {
        "sessions": len(expected_sessions),
        "records": len(records),
        "completed_count": int(checkpoints["completed_count"]),
        "sealed_cohorts_read": 0,
    }


def _preflight_output(output_dir: Path) -> None:
    resolved = output_dir.resolve()
    if resolved == ROOT.resolve() or ROOT.resolve() in resolved.parents:
        raise RuntimeError("PHASE8_BRIDGE_OUTPUT_INSIDE_REPOSITORY")
    if resolved.exists():
        raise RuntimeError("PHASE8_BRIDGE_ONE_SHOT_ALREADY_ATTEMPTED")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    usage = shutil.disk_usage(resolved.parent)
    if usage.free - 60 * GIB < 80 * GIB:
        raise RuntimeError("PHASE8_BRIDGE_PROJECTED_MINIMUM_FREE_SPACE_BELOW_FLOOR")
    try:
        with tempfile.NamedTemporaryFile(dir=resolved.parent, delete=True) as stream:
            stream.write(b"MDS650_PHASE8_WRITE_PROBE")
            stream.flush()
    except OSError as error:
        raise RuntimeError("PHASE8_BRIDGE_OUTPUT_WRITE_PROBE_FAILED") from error


def claim_one_shot(
    holdout_root: Path,
    token: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    """Consume the only store read before the first raw byte is opened."""

    root = holdout_root.resolve()
    counter_path = root / "access_counter.json"
    claim_path = root / "evaluation_claim_v2.json"
    counter = json.loads(counter_path.read_text(encoding="utf-8"))
    if int(counter.get("read_count", -1)) != 0:
        raise RuntimeError("PHASE8_BRIDGE_STORE_ALREADY_READ")
    claim = {
        "schema_version": "phase8-bridge-one-shot-claim-v2.0",
        "status": "CLAIMED_BEFORE_RAW_READ",
        "authorization_id": token["authorization_id"],
        "authorization_sha256": _canonical_sha256(token, omit="__never__"),
        "protocol_id": contract["protocol_id"],
        "contract_sha256": contract["contract_sha256"],
        "claimed_at_utc": datetime.now(UTC).isoformat(),
        "sealed_cohorts_read_before": 0,
    }
    try:
        descriptor = os.open(claim_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as error:
        raise RuntimeError("PHASE8_BRIDGE_ONE_SHOT_ALREADY_CLAIMED") from error
    with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
        json.dump(claim, stream, indent=2, sort_keys=True)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())

    counter["read_count"] = 1
    counter["phase8_bridge_authorization_id"] = token["authorization_id"]
    _atomic_json(counter_path, counter)
    with (root / "access.log").open("a", encoding="utf-8", newline="\n") as stream:
        stream.write(
            json.dumps(
                {
                    "action": "authorized_one_shot_read",
                    "authorization_id": token["authorization_id"],
                    "contract_sha256": contract["contract_sha256"],
                    "at_utc": datetime.now(UTC).isoformat(),
                },
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        )
        stream.flush()
        os.fsync(stream.fileno())
    return claim


def _fingerprint(path: str, params: Mapping[str, str]) -> str:
    body = json.dumps(
        {"path": path, "params": dict(params)},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(body).hexdigest()


def materialize_panels(
    holdout_root: Path,
    records: Sequence[Mapping[str, Any]],
    contract: Mapping[str, Any],
    output_dir: Path,
    *,
    workers: int,
) -> Path:
    """Verify raw custody, normalize it once, and run the existing 3-to-6 adapter."""

    root = holdout_root.resolve()
    for record in records:
        path = _raw_path(root, record)
        if _sha256(path) != record["payload_sha256"]:
            raise RuntimeError("PHASE8_BRIDGE_RAW_SHA256_MISMATCH")

    lookup = {
        (str(record["requested_session"]), str(record["request_fingerprint"])): record
        for record in records
    }
    by_provider: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for record in records:
        by_provider.setdefault(
            (str(record["requested_session"]), str(record["provider"])), []
        ).append(record)

    calibration = _load_script("download_calibration_20d")
    acquirer = _load_script("rp3_acquire_batch")
    builder = _load_script("rp3_build_eval_panels")
    sessions = _window_sessions(contract, "sensitivity")
    days = [date.fromisoformat(value) for value in sessions]
    materialized = output_dir / "materialized"
    rp3_root = materialized / "rp3"
    config = acquirer.RP3StorageConfig(
        sessions=tuple(days),
        excluded_dates=frozenset(),
        data_root=rp3_root,
        minimum_free_bytes=80 * GIB,
        projected_peak_additional_bytes=60 * GIB,
    )
    for path in (config.event_root, config.temporary_root):
        path.mkdir(parents=True, exist_ok=True)

    expected_fields: set[str] | None = None
    bar_frames: list[pl.DataFrame] = []
    for day in days:
        session = day.isoformat()
        tape_records = by_provider.get((session, "unusual_whales"), [])
        if len(tape_records) != 1:
            raise RuntimeError(f"PHASE8_BRIDGE_TAPE_IDENTITY_MISMATCH:{session}")
        counters = calibration.filter_session(
            day,
            _raw_path(root, tape_records[0]),
            expected_fields,
            config,
        )
        if expected_fields is None:
            expected_fields = set(counters["schema_fields"])

        for asset in BAR_ASSETS:
            fingerprint = _fingerprint(
                "/stable/historical-chart/1min",
                {
                    "symbol": asset,
                    "from": session,
                    "to": (day + timedelta(days=1)).isoformat(),
                },
            )
            fmp_record = lookup.get((session, fingerprint))
            if fmp_record is None or fmp_record.get("provider") != "fmp":
                raise RuntimeError(f"PHASE8_BRIDGE_FMP_IDENTITY_MISMATCH:{session}:{asset}")
            payload = json.loads(_raw_path(root, fmp_record).read_bytes())
            bars = parse_minute_payload(
                payload,
                asset=asset,
                run_id="phase8-bridge-v2",
                source_response_id=str(fmp_record["payload_sha256"]),
                source_timezone="America/New_York",
            )
            if not bars:
                raise RuntimeError(f"PHASE8_BRIDGE_FMP_EMPTY:{session}:{asset}")
            bar_frames.append(
                pl.DataFrame(
                    [
                        {
                            "asset": bar.asset,
                            "bar_start_utc": bar.bar_start_utc,
                            "open": bar.open,
                            "high": bar.high,
                            "low": bar.low,
                            "close": bar.close,
                            "volume": bar.volume,
                        }
                        for bar in bars
                    ]
                )
            )

    bar_store = rp3_root / "data" / "fmp" / "underlying_1min_eval.parquet"
    bar_store.parent.mkdir(parents=True, exist_ok=True)
    pl.concat(bar_frames, how="vertical").unique(
        subset=["asset", "bar_start_utc"], keep="first"
    ).sort(["asset", "bar_start_utc"]).write_parquet(bar_store)

    panel_root = output_dir / "panels"
    summary = builder.build_batch(materialized, panel_root, workers=workers)
    if tuple(str(value) for value in summary["sessions"]) != sessions:
        raise RuntimeError("PHASE8_BRIDGE_BUILT_SESSION_IDENTITY_MISMATCH")
    return panel_root


def _studentized_session_stats(
    differences: FloatArray, sessions: IntArray, *, repetitions: int, seed: int
) -> dict[str, float | int]:
    values, labels = aggregate_by_session(differences, sessions)
    if values.size < 3 or repetitions < 1:
        raise ValueError("PHASE8_BRIDGE_INFERENCE_TOO_SMALL")
    estimate = float(values.mean())
    standard_error = float(values.std(ddof=1) / np.sqrt(values.size))
    if standard_error <= 0.0:
        return {
            "estimate": estimate,
            "ci_low": estimate,
            "ci_high": estimate,
            "p_value_raw": 1.0,
            "newey_west_p_value": 1.0,
            "sessions": int(labels.size),
        }
    generator = np.random.default_rng(seed)
    centred = values - estimate
    samples = generator.choice(np.array([-1.0, 1.0]), size=(repetitions, values.size)) * centred
    sample_se = samples.std(axis=1, ddof=1) / np.sqrt(values.size)
    with np.errstate(divide="ignore", invalid="ignore"):
        statistics = samples.mean(axis=1) / sample_se
    statistics = statistics[np.isfinite(statistics)]
    if statistics.size < repetitions // 2:
        raise ValueError("PHASE8_BRIDGE_STUDENTIZATION_DEGENERATE")
    low_t, high_t = np.quantile(statistics, [0.025, 0.975])
    observed = abs(estimate / standard_error)
    p_value = (float(np.count_nonzero(np.abs(statistics) >= observed)) + 1.0) / (
        statistics.size + 1.0
    )
    return {
        "estimate": estimate,
        "ci_low": float(estimate - high_t * standard_error),
        "ci_high": float(estimate - low_t * standard_error),
        "p_value_raw": p_value,
        "newey_west_p_value": newey_west_p_value(values),
        "sessions": int(labels.size),
    }


def analyse_losses(
    losses: Mapping[str, FloatArray],
    sessions: IntArray,
    *,
    repetitions: int,
    seed: int,
) -> dict[str, Any]:
    """Compute all five registered estimands from one common forecast/loss cube."""

    differences = {
        label: losses[base] - losses[expanded] for label, (base, expanded) in PAIRS.items()
    }
    differences["delta_interaction"] = (
        differences["delta_total"]
        - differences["delta_b1"]
        - differences["delta_b2_given_b0"]
    )
    rows = {
        label: _studentized_session_stats(
            values, sessions, repetitions=repetitions, seed=seed
        )
        for label, values in differences.items()
    }
    adjusted = holm_adjust({label: float(row["p_value_raw"]) for label, row in rows.items()})
    for label, row in rows.items():
        row["p_value_holm_descriptive"] = adjusted[label]
    return rows


def score_panels(
    development: pl.DataFrame,
    phase8: pl.DataFrame,
    contract: Mapping[str, Any],
) -> tuple[dict[str, Any], pl.DataFrame]:
    """Fit on D/V only and score both declared Phase 8 windows."""

    sensitivity_sessions = _window_sessions(contract, "sensitivity")
    primary_sessions = set(_window_sessions(contract, "primary"))
    observed_sessions = tuple(sorted(str(value) for value in phase8["session_date"].unique()))
    if observed_sessions != sensitivity_sessions:
        raise RuntimeError("PHASE8_BRIDGE_SESSION_IDENTITY_MISMATCH")
    observed_assets = {str(value) for value in phase8["asset"].unique()}
    if observed_assets != set(TARGET_ASSETS):
        raise RuntimeError("PHASE8_BRIDGE_ASSET_IDENTITY_MISMATCH")

    repetitions = int(contract["inference"]["primary_window"]["wild_cluster_bootstrap_repetitions"])
    seed = int(contract["inference"]["primary_window"]["seed"])
    result: dict[str, Any] = {}
    forecast_rows: list[pl.DataFrame] = []
    for training_role in ("D", "V"):
        train = development.filter(pl.col("role") == training_role).sort(
            ["session_date", "asset", "origin_minute"]
        )
        evaluation = phase8.sort(["session_date", "asset", "origin_minute"])
        combined = pl.concat(
            [
                train.with_columns(pl.lit(False).alias("_phase8")),
                evaluation.with_columns(pl.lit(True).alias("_phase8")),
            ],
            how="diagonal_relaxed",
        )
        target = np.asarray(combined["rv30"].to_numpy(), dtype=np.float64)
        usable = common_evaluation_mask(combined, target)
        train_mask = (~combined["_phase8"].to_numpy()) & usable
        evaluation_mask = combined["_phase8"].to_numpy() & usable
        labels = np.asarray(combined["session_date"].to_numpy()).astype(str)
        if set(labels[evaluation_mask]) != set(sensitivity_sessions):
            raise RuntimeError(f"PHASE8_BRIDGE_USABLE_SESSION_MISSING:{training_role}")
        ranks = session_rank(labels)
        designs = {
            name: fold_design(combined, features, train_mask)[0]
            for name, features in INFORMATION_SETS.items()
        }
        role_result: dict[str, Any] = {}
        for model in MODELS:
            losses: dict[str, FloatArray] = {}
            fit_records: dict[str, Any] = {}
            for information_set, design in designs.items():
                fit_record: dict[str, object] | None = {} if model == "lightgbm" else None
                forecast = fit_ladder_model(
                    model,
                    design,
                    target,
                    train_mask,
                    sessions=ranks,
                    record=fit_record,
                )
                scored = forecast[evaluation_mask]
                actual = target[evaluation_mask]
                losses[information_set] = qlike_losses(actual, scored)
                if fit_record is not None:
                    fit_records[information_set] = fit_record
                forecast_rows.append(
                    pl.DataFrame(
                        {
                            "training_role": training_role,
                            "model_family": model,
                            "information_set": information_set,
                            "session_date": labels[evaluation_mask],
                            "asset": combined["asset"].to_numpy()[evaluation_mask],
                            "origin_minute": combined["origin_minute"].to_numpy()[evaluation_mask],
                            "rv30": actual,
                            "forecast": scored,
                        }
                    )
                )
            evaluation_labels = labels[evaluation_mask]
            evaluation_ranks = session_rank(evaluation_labels)
            primary_mask = np.isin(evaluation_labels, list(primary_sessions))
            windows = {
                "primary_20": analyse_losses(
                    {name: values[primary_mask] for name, values in losses.items()},
                    evaluation_ranks[primary_mask],
                    repetitions=repetitions,
                    seed=seed,
                ),
                "sensitivity_30": analyse_losses(
                    losses, evaluation_ranks, repetitions=repetitions, seed=seed
                ),
            }
            delta = windows["primary_20"]["delta_total"]
            label = (
                "DIRECTIONALLY_SUPPORTIVE_EXPLORATORY"
                if float(delta["ci_low"]) > 0.0
                else "DIRECTIONALLY_ADVERSE_EXPLORATORY"
                if float(delta["ci_high"]) < 0.0
                else "IMPRECISE_EXPLORATORY"
            )
            role_result[model] = {
                "classification": label,
                "windows": windows,
                "fit_records": fit_records,
                "loss_sha256": {
                    name: canonical_float_array_sha256(values) for name, values in losses.items()
                },
            }
        result[training_role] = role_result
    classifications = {
        cell["classification"] for role in result.values() for cell in role.values()
    }
    result["overall_classification"] = (
        classifications.pop() if len(classifications) == 1 else "MIXED_EXPLORATORY"
    )
    return result, pl.concat(forecast_rows, how="vertical")


def run(
    *,
    contract_path: Path,
    evaluator_freeze_path: Path,
    authorization_path: Path | None,
    development_panel_root: Path,
    holdout_root: Path,
    output_dir: Path,
    workers: int,
) -> dict[str, Any]:
    contract = load_contract(contract_path)
    validate_evaluator_freeze(evaluator_freeze_path, contract)
    token = validate_authorization(authorization_path, contract)
    records, store_preflight = preflight_holdout(holdout_root, contract)
    _preflight_output(output_dir)
    resolved_output = output_dir.resolve()
    resolved_output.mkdir(parents=False, exist_ok=False)
    assert authorization_path is not None
    _atomic_json(
        resolved_output / "authorization_consumed.json",
        {
            **token,
            "status": "CONSUMED_BEFORE_PHASE8_READ",
            "authorization_sha256": _sha256(authorization_path),
        },
    )
    claim_one_shot(holdout_root, token, contract)

    phase8_panel_root = materialize_panels(
        holdout_root,
        records,
        contract,
        resolved_output,
        workers=workers,
    )
    development_paths = panel_paths(development_panel_root)
    development = load_merged_panel(
        development_paths["b0"], development_paths["b1"], development_paths["b2"]
    )
    phase8_paths = panel_paths(phase8_panel_root)
    phase8 = load_merged_panel(phase8_paths["b0"], phase8_paths["b1"], phase8_paths["b2"])
    evaluation, forecasts = score_panels(development, phase8, contract)
    forecast_path = resolved_output / "forecast_cube.parquet"
    forecasts.write_parquet(forecast_path, compression="zstd")
    document = {
        "schema_version": "phase8-exploratory-bridge-result-v2.0",
        "status": "EXPLORATORY_BRIDGE_EVALUATION_COMPLETE",
        "claim_classification": "EXPLORATORY_DESCRIPTIVE_NOT_CONFIRMATORY",
        "protocol_id": contract["protocol_id"],
        "contract_sha256": contract["contract_sha256"],
        "sealed_cohorts_read": 1,
        "confirmatory_promotion_allowed": False,
        "store_preflight": store_preflight,
        "evaluation": evaluation,
        "forecast_cube_sha256": _sha256(forecast_path),
        "personal_paths_emitted": False,
        "secret_values_emitted": False,
    }
    document["result_sha256"] = _canonical_sha256(document, omit="result_sha256")
    _atomic_json(resolved_output / "result.json", document)
    return document


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument("--evaluator-freeze", type=Path, default=DEFAULT_EVALUATOR_FREEZE)
    parser.add_argument("--authorization", type=Path)
    parser.add_argument("--development-panel-root", type=Path, required=True)
    parser.add_argument("--holdout-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args(argv)
    result = run(
        contract_path=args.contract,
        evaluator_freeze_path=args.evaluator_freeze,
        authorization_path=args.authorization,
        development_panel_root=args.development_panel_root,
        holdout_root=args.holdout_root,
        output_dir=args.output_dir,
        workers=args.workers,
    )
    print(json.dumps({"status": result["status"], "sealed_cohorts_read": 1}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
