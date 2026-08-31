"""Rebuild and rescore Phase 8 from the already materialized 30 sessions.

This is an append-only, post-hoc remediation sensitivity. It does not read the sealed
store, collect sessions, replace the historical one-shot result, or create a
confirmatory claim.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final, cast

import numpy as np
import polars as pl
from evaluate_phase8_bridge_v2 import analyse_losses, load_contract, score_panels
from rp3_build_eval_panels import build_batch

from mds650.executable_closure import build_executable_closure
from mds650.metrics import qlike_losses
from mds650.rp2.bars import normalise_bars
from mds650.rp2.panel import (
    B1_FEATURES,
    B2_FEATURES,
    TARGET_ASSETS,
    load_merged_panel,
    panel_paths,
    session_rank,
)
from mds650.rp3.eval_inventory import EVAL_ROLE

ROOT: Final = Path(__file__).resolve().parents[1]
DEFAULT_CONTRACT: Final = (
    ROOT
    / "artifacts"
    / "phase8_bridge"
    / "materialized_remediation_contract_20260831_v1.json"
)
DEFAULT_BRIDGE_CONTRACT: Final = (
    ROOT / "artifacts" / "phase8_bridge" / "bridge_contract_v2.json"
)
DEFAULT_WARMUP_AMENDMENT: Final = (
    ROOT
    / "artifacts"
    / "phase8_bridge"
    / "materialized_remediation_contract_amendment_20260831_v1.json"
)
DEFAULT_GRID_AMENDMENT: Final = (
    ROOT
    / "artifacts"
    / "phase8_bridge"
    / "materialized_remediation_contract_amendment_20260831_v2.json"
)
KEYS: Final = (
    "training_role",
    "model_family",
    "information_set",
    "session_date",
    "asset",
    "origin_minute",
)
PANEL_KEYS: Final = ("session_date", "asset", "origin_minute")
INFORMATION_SETS: Final = ("B0", "B0+B1", "B0+B2", "B0+B1+B2")
B1_INCLUSIVE: Final = ("B0+B1", "B0+B1+B2")
EXECUTABLE_SCRIPTS: Final = (
    "scripts/replay_phase8_materialized_remediation_v1.py",
    "scripts/evaluate_phase8_bridge_v2.py",
    "scripts/rp3_build_eval_panels.py",
    "scripts/rp2_block3_target_panel.py",
    "scripts/rp2_block4_b0_panel.py",
    "scripts/rp2_block5_surface_panel.py",
    "scripts/rp2_block6_flow_panel.py",
    "uv.lock",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(payload: Mapping[str, Any], *, omit: str) -> str:
    body = {key: value for key, value in payload.items() if key != omit}
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"PHASE8_REMEDIATION_JSON_OBJECT_REQUIRED:{path.name}")
    return value


def _atomic_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
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


def _assert_sha256(path: Path, expected: str, label: str) -> None:
    actual = _sha256(path)
    if actual != expected:
        raise ValueError(f"PHASE8_REMEDIATION_{label}_SHA256_MISMATCH:{actual}")


def _validate_contract(path: Path) -> dict[str, Any]:
    contract = _load_json(path)
    expected = str(contract["contract_sha256"])
    if _canonical_sha256(contract, omit="contract_sha256") != expected:
        raise ValueError("PHASE8_REMEDIATION_CONTRACT_SHA256_MISMATCH")
    if contract.get("status") != "PRECOMMITTED_BEFORE_REMEDIATION_MEASUREMENT":
        raise ValueError("PHASE8_REMEDIATION_CONTRACT_NOT_PRECOMMITTED")
    return contract


def _validate_amendment(path: Path, *, expected_status: str) -> dict[str, Any]:
    amendment = _load_json(path)
    expected = str(amendment["amendment_sha256"])
    if _canonical_sha256(amendment, omit="amendment_sha256") != expected:
        raise ValueError(f"PHASE8_REMEDIATION_AMENDMENT_SHA256_MISMATCH:{path.name}")
    if amendment.get("status") != expected_status:
        raise ValueError(f"PHASE8_REMEDIATION_AMENDMENT_STATUS_MISMATCH:{path.name}")
    return amendment


def _load_warmup_bars(path: Path, amendment: Mapping[str, Any]) -> pl.DataFrame:
    warmup = amendment["warmup"]
    _assert_sha256(path, str(warmup["source_sha256"]), "WARMUP_BAR_STORE")
    sessions = {str(value) for value in warmup["sessions"]}
    assets = {str(value) for value in warmup["assets"]}
    if assets != set(TARGET_ASSETS):
        raise ValueError("PHASE8_REMEDIATION_WARMUP_ASSETS_MISMATCH")
    frame = normalise_bars(pl.read_parquet(path)).filter(
        pl.col("session_date").cast(pl.String).is_in(sorted(sessions))
        & pl.col("asset").is_in(sorted(assets))
    )
    observed_sessions = set(frame["session_date"].cast(pl.String).unique().to_list())
    observed_assets = set(frame["asset"].unique().to_list())
    if (
        frame.height != int(warmup["rows"])
        or observed_sessions != sessions
        or observed_assets != assets
        or frame.n_unique(["session_date", "asset", "minute"]) != frame.height
    ):
        raise ValueError("PHASE8_REMEDIATION_WARMUP_CONTENT_MISMATCH")
    return frame.with_columns(
        source=pl.lit("phase8_target_blind_warmup"), role=pl.lit(EVAL_ROLE)
    )


def _validate_materialized_inputs(
    materialized_root: Path,
    historical_root: Path,
    contract: Mapping[str, Any],
) -> dict[str, Any]:
    fixed = contract["fixed_inputs"]
    layout_path = historical_root / "layout_recovery_manifest.json"
    _assert_sha256(
        layout_path,
        str(fixed["materialized_layout_manifest"]["file_sha256"]),
        "LAYOUT_MANIFEST",
    )
    layout = _load_json(layout_path)
    if layout.get("manifest_sha256") != fixed["materialized_layout_manifest"][
        "manifest_sha256"
    ]:
        raise ValueError("PHASE8_REMEDIATION_LAYOUT_MANIFEST_IDENTITY_MISMATCH")

    sessions = tuple(str(value) for value in contract["fixed_inputs"]["sessions"])
    if tuple(sorted(layout["sessions"])) != sessions:
        raise ValueError("PHASE8_REMEDIATION_LAYOUT_SESSIONS_MISMATCH")
    tape_root = materialized_root / "rp3" / "tape" / "full_tape_eval"
    for session in sessions:
        tape = tape_root / f"date={session}" / "full_tape.parquet"
        _assert_sha256(
            tape,
            str(layout["sessions"][session]["output_sha256"]),
            f"TAPE_{session}",
        )

    bars = materialized_root / "rp3" / "data" / "fmp" / "underlying_1min_eval.parquet"
    _assert_sha256(bars, str(fixed["materialized_bar_store_sha256"]), "BAR_STORE")
    return {
        "bar_store_sha256": _sha256(bars),
        "layout_manifest_file_sha256": _sha256(layout_path),
        "layout_manifest_sha256": layout["manifest_sha256"],
        "sessions_verified": len(sessions),
        "tape_files_verified": len(sessions),
    }


def _validate_development_panels(
    development_panel_root: Path, contract: Mapping[str, Any]
) -> dict[str, str]:
    expected = contract["fixed_inputs"]["development_panels"]
    paths = panel_paths(development_panel_root)
    identities: dict[str, str] = {}
    for name in ("b0", "b1", "b2"):
        digest = _sha256(paths[name])
        if digest != expected[f"{name}_sha256"]:
            raise ValueError(f"PHASE8_REMEDIATION_DEVELOPMENT_{name.upper()}_MISMATCH:{digest}")
        identities[name] = digest
    return identities


def _window_mask(window: str, bridge: Mapping[str, Any]) -> pl.Expr:
    cohort = bridge["cohort"]["primary" if window == "primary_20" else "sensitivity"]
    start, end = str(cohort["window"]).split("..")
    return pl.col("session_date").is_between(
        pl.lit(start), pl.lit(end), closed="both"
    )


def compare_forecast_cubes(
    historical: pl.DataFrame,
    remediated: pl.DataFrame,
    bridge: Mapping[str, Any],
    grid_amendment: Mapping[str, Any],
) -> dict[str, Any]:
    """Compare QLIKE on the precommitted paired grid after the B0 cutoff repair."""

    historical = historical.sort(KEYS)
    remediated = remediated.sort(KEYS)
    if (
        historical.n_unique(KEYS) != historical.height
        or remediated.n_unique(KEYS) != remediated.height
    ):
        raise ValueError("PHASE8_REMEDIATION_CUBE_DUPLICATE_KEYS")
    paired = historical.join(
        remediated.select(
            *KEYS,
            pl.col("rv30").alias("rv30_remediated"),
            pl.col("forecast").alias("forecast_remediated"),
        ),
        on=list(KEYS),
        how="inner",
        validate="1:1",
    ).sort(KEYS)
    if paired.height != remediated.height:
        raise ValueError("PHASE8_REMEDIATION_REMEDIATED_ONLY_KEYS")
    if not np.array_equal(paired["rv30"].to_numpy(), paired["rv30_remediated"].to_numpy()):
        raise ValueError("PHASE8_REMEDIATION_RV30_MISMATCH")

    origin_keys = ["session_date", "asset", "origin_minute"]
    historical_origins = historical.select(origin_keys).unique()
    remediated_origins = remediated.select(origin_keys).unique()
    paired_origins = historical_origins.join(
        remediated_origins, on=origin_keys, how="inner", validate="1:1"
    )
    expected_grid = grid_amendment["comparison_grid"]
    observed_grid = {
        "historical_rows": historical_origins.height,
        "remediated_rows": remediated_origins.height,
        "paired_common_origins": paired_origins.height,
        "historical_only_origins": historical_origins.height - paired_origins.height,
        "remediated_only_origins": remediated_origins.height - paired_origins.height,
    }
    for key, value in observed_grid.items():
        if value != int(expected_grid[key]):
            raise ValueError(f"PHASE8_REMEDIATION_GRID_MISMATCH:{key}:{value}")

    rows: list[dict[str, Any]] = []
    for window in ("primary_20", "sensitivity_30"):
        for role in ("D", "V"):
            for model in ("gamma_glm", "lightgbm"):
                for information_set in INFORMATION_SETS:
                    selector = (
                        (pl.col("training_role") == role)
                        & (pl.col("model_family") == model)
                        & (pl.col("information_set") == information_set)
                        & _window_mask(window, bridge)
                    )
                    old_full = historical.filter(selector)
                    common = paired.filter(selector)
                    old_paired_loss = float(
                        qlike_losses(
                            common["rv30"].to_numpy(), common["forecast"].to_numpy()
                        ).mean()
                    )
                    new_paired_loss = float(
                        qlike_losses(
                            common["rv30_remediated"].to_numpy(),
                            common["forecast_remediated"].to_numpy(),
                        ).mean()
                    )
                    improvement = old_paired_loss - new_paired_loss
                    rows.append(
                        {
                            "training_role": role,
                            "model_family": model,
                            "window": window,
                            "information_set": information_set,
                            "historical_full_grid_origins": old_full.height,
                            "paired_common_origins": common.height,
                            "historical_full_grid_mean_qlike": float(
                                qlike_losses(
                                    old_full["rv30"].to_numpy(),
                                    old_full["forecast"].to_numpy(),
                                ).mean()
                            ),
                            "historical_paired_mean_qlike": old_paired_loss,
                            "remediated_paired_mean_qlike": new_paired_loss,
                            "historical_minus_remediated_mean_qlike": improvement,
                            "improved": improvement > 0.0,
                        }
                    )

    primary_b1 = [
        row
        for row in rows
        if row["window"] == "primary_20" and row["information_set"] in B1_INCLUSIVE
    ]
    improved = sum(bool(row["improved"]) for row in primary_b1)
    label = (
        "UNANIMOUS_B1_INCLUSIVE_IMPROVEMENT"
        if improved == len(primary_b1)
        else "NO_B1_INCLUSIVE_IMPROVEMENT"
        if improved == 0
        else "MIXED"
    )
    return {
        "historical_cube_rows": historical.height,
        "remediated_cube_rows": remediated.height,
        "paired_cube_rows": paired.height,
        "historical_only_cube_rows": historical.height - paired.height,
        "grid": observed_grid,
        "rv30_exactly_equal_on_paired_grid": True,
        "mean_qlike_cells": rows,
        "primary_b1_inclusive_cells": len(primary_b1),
        "primary_b1_inclusive_cells_improved": improved,
        "global_label": label,
    }


def _feature_panel_comparison(
    historical_root: Path,
    remediated_panel_root: Path,
    *,
    panel: str,
    features_to_check: Mapping[str, str],
) -> dict[str, Any]:
    old = pl.read_parquet(panel_paths(historical_root)[panel]).sort(PANEL_KEYS)
    new = pl.read_parquet(panel_paths(remediated_panel_root)[panel]).sort(PANEL_KEYS)
    paired = old.join(new, on=list(PANEL_KEYS), how="inner", suffix="_remediated")
    if paired.height != new.height:
        raise ValueError(f"PHASE8_REMEDIATION_{panel.upper()}_REMEDIATED_ONLY_KEYS")

    features: dict[str, Any] = {}
    all_exact = True
    for feature in features_to_check:
        old_values = np.asarray(paired[feature].to_numpy(), dtype=np.float64)
        new_values = np.asarray(
            paired[f"{feature}_remediated"].to_numpy(), dtype=np.float64
        )
        both = np.isfinite(old_values) & np.isfinite(new_values)
        changed = both & (old_values != new_values)
        exact = bool(np.array_equal(old_values, new_values, equal_nan=True))
        all_exact = all_exact and exact
        delta = new_values[changed] - old_values[changed]
        features[feature] = {
            "historical_paired_finite": int(np.isfinite(old_values).sum()),
            "remediated_paired_finite": int(np.isfinite(new_values).sum()),
            "changed_rows": int(changed.sum()),
            "exact_on_paired_grid": exact,
            "mean_change_on_changed_rows": float(delta.mean()) if delta.size else 0.0,
            "max_abs_change": float(np.abs(delta).max()) if delta.size else 0.0,
        }
    return {
        "historical_rows": old.height,
        "remediated_rows": new.height,
        "paired_rows": paired.height,
        "historical_only_rows": old.height - paired.height,
        "remediated_only_rows": new.height - paired.height,
        "all_features_exact_on_paired_grid": all_exact,
        "features": features,
    }


def _evaluate_cube(cube: pl.DataFrame, bridge: Mapping[str, Any]) -> dict[str, Any]:
    repetitions = int(
        bridge["inference"]["primary_window"]["wild_cluster_bootstrap_repetitions"]
    )
    seed = int(bridge["inference"]["primary_window"]["seed"])
    result: dict[str, Any] = {}
    for role in ("D", "V"):
        result[role] = {}
        for model in ("gamma_glm", "lightgbm"):
            cell = cube.filter(
                (pl.col("training_role") == role) & (pl.col("model_family") == model)
            )
            wide = cell.filter(pl.col("information_set") == "B0").select(
                *PANEL_KEYS, "rv30"
            )
            for information_set in INFORMATION_SETS:
                wide = wide.join(
                    cell.filter(pl.col("information_set") == information_set).select(
                        *PANEL_KEYS, pl.col("forecast").alias(information_set)
                    ),
                    on=list(PANEL_KEYS),
                    how="inner",
                    validate="1:1",
                )
            windows: dict[str, Any] = {}
            for window in ("primary_20", "sensitivity_30"):
                frame = wide.filter(_window_mask(window, bridge)).sort(PANEL_KEYS)
                actual = np.asarray(frame["rv30"].to_numpy(), dtype=np.float64)
                losses = {
                    information_set: qlike_losses(
                        actual,
                        np.asarray(frame[information_set].to_numpy(), dtype=np.float64),
                    )
                    for information_set in INFORMATION_SETS
                }
                windows[window] = analyse_losses(
                    losses,
                    session_rank(frame["session_date"].to_numpy()),
                    repetitions=repetitions,
                    seed=seed,
                )
            result[role][model] = {"windows": windows}
    return result


def _contrast_comparison(
    historical: Mapping[str, Any], remediated: Mapping[str, Any]
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for role in ("D", "V"):
        for model in ("gamma_glm", "lightgbm"):
            for window in ("primary_20", "sensitivity_30"):
                old_window = historical[role][model]["windows"][window]
                new_window = remediated[role][model]["windows"][window]
                for contrast in old_window:
                    rows.append(
                        {
                            "training_role": role,
                            "model_family": model,
                            "window": window,
                            "contrast": contrast,
                            "historical": old_window[contrast],
                            "remediated": new_window[contrast],
                            "estimate_change": float(new_window[contrast]["estimate"])
                            - float(old_window[contrast]["estimate"]),
                        }
                    )
    return rows


def run(
    *,
    contract_path: Path,
    warmup_amendment_path: Path,
    grid_amendment_path: Path,
    bridge_contract_path: Path,
    materialized_root: Path,
    warmup_bar_path: Path,
    historical_root: Path,
    development_panel_root: Path,
    output_dir: Path,
    summary_path: Path,
    workers: int,
) -> dict[str, Any]:
    contract = _validate_contract(contract_path)
    amendment_status = "PRECOMMITTED_BEFORE_FIRST_REMEDIATION_MODEL_FIT"
    warmup_amendment = _validate_amendment(
        warmup_amendment_path, expected_status=amendment_status
    )
    grid_amendment = _validate_amendment(
        grid_amendment_path, expected_status=amendment_status
    )
    if (
        warmup_amendment["amends_contract_sha256"] != contract["contract_sha256"]
        or grid_amendment["amends_contract_sha256"] != contract["contract_sha256"]
        or grid_amendment["supersedes_amendment_sha256"]
        != warmup_amendment["amendment_sha256"]
    ):
        raise ValueError("PHASE8_REMEDIATION_AMENDMENT_CHAIN_MISMATCH")
    bridge = load_contract(bridge_contract_path)
    if bridge["contract_sha256"] != contract["fixed_inputs"]["bridge_contract"][
        "contract_sha256"
    ]:
        raise ValueError("PHASE8_REMEDIATION_BRIDGE_CONTRACT_MISMATCH")
    if output_dir.exists():
        raise FileExistsError(f"PHASE8_REMEDIATION_OUTPUT_EXISTS:{output_dir}")
    if historical_root.resolve() == output_dir.resolve():
        raise ValueError("PHASE8_REMEDIATION_HISTORICAL_OUTPUT_REUSE_FORBIDDEN")

    source_identity = _validate_materialized_inputs(
        materialized_root, historical_root, contract
    )
    warmup_bars = _load_warmup_bars(warmup_bar_path, warmup_amendment)
    source_identity["warmup"] = {
        "sha256": _sha256(warmup_bar_path),
        "rows": warmup_bars.height,
        "sessions": warmup_amendment["warmup"]["sessions"],
        "target_or_forecast_read": False,
        "rows_written_or_scored_as_phase8": 0,
    }
    development_identity = _validate_development_panels(development_panel_root, contract)
    historical_result_path = historical_root / "result.json"
    historical_cube_path = historical_root / "forecast_cube.parquet"
    _assert_sha256(
        historical_result_path,
        str(contract["fixed_inputs"]["historical_result"]["file_sha256"]),
        "HISTORICAL_RESULT",
    )
    _assert_sha256(
        historical_cube_path,
        str(contract["fixed_inputs"]["historical_forecast_cube"]["sha256"]),
        "HISTORICAL_CUBE",
    )

    output_dir.mkdir(parents=True, exist_ok=False)
    phase8_panel_root = output_dir / "panels"
    summary = build_batch(
        materialized_root,
        phase8_panel_root,
        workers=workers,
        warmup_bars=warmup_bars,
    )
    built_sessions = tuple(
        str(value) for value in cast(Sequence[object], summary["sessions"])
    )
    if built_sessions != tuple(
        contract["fixed_inputs"]["sessions"]
    ):
        raise ValueError("PHASE8_REMEDIATION_BUILT_SESSIONS_MISMATCH")

    development_paths = panel_paths(development_panel_root)
    development = load_merged_panel(
        development_paths["b0"], development_paths["b1"], development_paths["b2"]
    )
    phase8_paths = panel_paths(phase8_panel_root)
    phase8 = load_merged_panel(
        phase8_paths["b0"], phase8_paths["b1"], phase8_paths["b2"]
    )
    evaluation, forecasts = score_panels(development, phase8, bridge)
    forecast_path = output_dir / "forecast_cube.parquet"
    forecasts.write_parquet(forecast_path, compression="zstd")

    historical_cube = pl.read_parquet(historical_cube_path)
    comparison = compare_forecast_cubes(
        historical_cube, forecasts, bridge, grid_amendment
    )
    historical_paired_cube = historical_cube.join(
        forecasts.select(KEYS), on=list(KEYS), how="semi"
    )
    historical_paired_evaluation = _evaluate_cube(historical_paired_cube, bridge)
    remediated_replay = _evaluate_cube(forecasts, bridge)
    if remediated_replay != {
        role: {
            model: {"windows": evaluation[role][model]["windows"]}
            for model in ("gamma_glm", "lightgbm")
        }
        for role in ("D", "V")
    }:
        raise ValueError("PHASE8_REMEDIATION_RESULT_REPLAY_MISMATCH")
    b1_comparison = _feature_panel_comparison(
        historical_root / "panels",
        phase8_panel_root,
        panel="b1",
        features_to_check=B1_FEATURES,
    )
    b2_comparison = _feature_panel_comparison(
        historical_root / "panels",
        phase8_panel_root,
        panel="b2",
        features_to_check=B2_FEATURES,
    )
    if not b2_comparison["all_features_exact_on_paired_grid"]:
        raise ValueError("PHASE8_REMEDIATION_B2_NEGATIVE_CONTROL_CHANGED")
    document: dict[str, Any] = {
        "schema_version": "phase8-materialized-remediation-result-v1.0",
        "status": "POST_HOC_REMEDIATION_SENSITIVITY_COMPLETE",
        "claim_classification": contract["claim_classification"],
        "protocol_id": contract["protocol_id"],
        "contract_sha256": contract["contract_sha256"],
        "warmup_amendment_sha256": warmup_amendment["amendment_sha256"],
        "grid_amendment_sha256": grid_amendment["amendment_sha256"],
        "bridge_contract_sha256": bridge["contract_sha256"],
        "historical_result_preserved": True,
        "sealed_cohorts_read": 0,
        "sealed_store_reopened": False,
        "new_sessions_collected": 0,
        "session_count": len(built_sessions),
        "code_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip(),
        "scientific_code_commit": contract["execution"]["current_code_commit"],
        "executable_closure": build_executable_closure(ROOT, scripts=EXECUTABLE_SCRIPTS),
        "source_identity": source_identity,
        "development_panel_sha256": development_identity,
        "historical_result_sha256": _sha256(historical_result_path),
        "historical_forecast_cube_sha256": _sha256(historical_cube_path),
        "remediated_panel_sha256": {
            name: _sha256(path) for name, path in phase8_paths.items()
        },
        "remediated_forecast_cube_sha256": _sha256(forecast_path),
        "b1_panel_comparison": b1_comparison,
        "b2_panel_negative_control": b2_comparison,
        "forecast_comparison": comparison,
        "historical_paired_evaluation": historical_paired_evaluation,
        "contrast_comparison": _contrast_comparison(
            historical_paired_evaluation, evaluation
        ),
        "evaluation": evaluation,
        "personal_paths_emitted": False,
        "secret_values_emitted": False,
        "confirmatory_promotion_allowed": False,
    }
    document["result_sha256"] = _canonical_sha256(document, omit="result_sha256")
    _atomic_json(output_dir / "result.json", document)
    _atomic_json(summary_path, document)
    return document


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", type=Path, default=DEFAULT_CONTRACT)
    parser.add_argument(
        "--warmup-amendment", type=Path, default=DEFAULT_WARMUP_AMENDMENT
    )
    parser.add_argument("--grid-amendment", type=Path, default=DEFAULT_GRID_AMENDMENT)
    parser.add_argument("--bridge-contract", type=Path, default=DEFAULT_BRIDGE_CONTRACT)
    parser.add_argument("--materialized-root", type=Path, required=True)
    parser.add_argument("--warmup-bars", type=Path, required=True)
    parser.add_argument("--historical-root", type=Path, required=True)
    parser.add_argument("--development-panel-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--summary-path", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=6)
    arguments = parser.parse_args(argv)
    result = run(
        contract_path=arguments.contract,
        warmup_amendment_path=arguments.warmup_amendment,
        grid_amendment_path=arguments.grid_amendment,
        bridge_contract_path=arguments.bridge_contract,
        materialized_root=arguments.materialized_root,
        warmup_bar_path=arguments.warmup_bars,
        historical_root=arguments.historical_root,
        development_panel_root=arguments.development_panel_root,
        output_dir=arguments.output_dir,
        summary_path=arguments.summary_path,
        workers=arguments.workers,
    )
    print(json.dumps({
        "status": result["status"],
        "global_label": result["forecast_comparison"]["global_label"],
        "result_sha256": result["result_sha256"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
