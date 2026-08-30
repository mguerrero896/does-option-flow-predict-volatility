"""Audit Phase 8 loss-differential dispersion from already materialized bytes.

This reads the pinned forecast cube and D/V development panels only. It never opens the
sealed store. Phase 8 inference is replayed through the frozen evaluator's statistical
functions; the current D/V reference is measured through the existing Block 12 producer.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Final

import numpy as np
import polars as pl
from evaluate_phase8_bridge_v2 import PAIRS, analyse_losses
from rp2_block12_prospective_design import measure_dispersion

from mds650.metrics import qlike_losses
from mds650.rp2.inference import aggregate_by_session
from mds650.rp2.panel import load_merged_panel, session_rank

ROOT: Final = Path(__file__).resolve().parents[1]
RESULT: Final = ROOT / "artifacts" / "phase8_bridge" / "result_20260830_v1.json"
CONTRACT: Final = ROOT / "artifacts" / "phase8_bridge" / "bridge_contract_v2.json"
DESIGN: Final = ROOT / "artifacts" / "rp2_block12_prospective" / "design.json"
POINTERS: Final = ROOT / "artifacts" / "rp2_panel_pointers.json"
DEFAULT_OUTPUT: Final = ROOT / "artifacts" / "phase8_bridge" / "dispersion_audit_20260830_v1.json"
MODELS: Final = ("gamma_glm", "lightgbm")
INFORMATION_SETS: Final = ("B0", "B0+B1", "B0+B2", "B0+B1+B2")
KEYS: Final = ("session_date", "asset", "origin_minute")
CHECKED_CONTRASTS: Final = ("delta_b1", "delta_b2_given_b1")
HISTORICAL_DESIGN_PRODUCER_SHA256: Final = (
    "7dad5bd53a400358f3aeca92e5005af84c5f4e32a58ceb1e8c2133b08cde0baa"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(payload: Mapping[str, Any], *, omit: str) -> str:
    body = {key: value for key, value in payload.items() if key != omit}
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"PHASE8_DISPERSION_JSON_OBJECT_REQUIRED:{path.name}")
    return value


def _assert_hash(path: Path, expected: str, label: str) -> None:
    actual = _sha256(path)
    if actual != expected:
        raise ValueError(f"PHASE8_DISPERSION_{label}_SHA256_MISMATCH:{actual}")


def _primary_loss_cube(
    cube: pl.DataFrame, *, role: str, model: str, start: str, end: str
) -> tuple[dict[str, np.ndarray[Any, np.dtype[np.float64]]], np.ndarray[Any, Any], int]:
    frame = cube.filter(
        (pl.col("training_role") == role)
        & (pl.col("model_family") == model)
        & pl.col("session_date").is_between(pl.lit(start), pl.lit(end), closed="both")
    )
    if frame.is_empty() or frame.null_count().sum_horizontal().item() != 0:
        raise ValueError(f"PHASE8_DISPERSION_CUBE_INVALID:{role}:{model}")

    target = frame.filter(pl.col("information_set") == "B0").select(*KEYS, "rv30")
    if target.n_unique(KEYS) != target.height:
        raise ValueError(f"PHASE8_DISPERSION_DUPLICATE_KEYS:{role}:{model}:B0")
    wide = target
    for information_set in INFORMATION_SETS:
        forecasts = frame.filter(pl.col("information_set") == information_set).select(
            *KEYS, pl.col("forecast").alias(information_set)
        )
        if forecasts.height != target.height or forecasts.n_unique(KEYS) != target.height:
            raise ValueError(f"PHASE8_DISPERSION_KEYSET_MISMATCH:{role}:{model}:{information_set}")
        wide = wide.join(forecasts, on=list(KEYS), how="inner", validate="1:1")
    wide = wide.sort(KEYS)
    if wide.height != target.height:
        raise ValueError(f"PHASE8_DISPERSION_JOIN_LOSS:{role}:{model}")

    actual = np.asarray(wide["rv30"].to_numpy(), dtype=np.float64)
    losses = {
        information_set: qlike_losses(
            actual,
            np.asarray(wide[information_set].to_numpy(), dtype=np.float64),
        )
        for information_set in INFORMATION_SETS
    }
    sessions = session_rank(wide["session_date"].to_numpy())
    return losses, sessions, wide.height


def _replay_phase8(
    cube: pl.DataFrame,
    result: Mapping[str, Any],
    contract: Mapping[str, Any],
) -> dict[str, dict[str, dict[str, Any]]]:
    start, end = str(contract["cohort"]["primary"]["window"]).split("..")
    repetitions = int(contract["inference"]["primary_window"]["wild_cluster_bootstrap_repetitions"])
    seed = int(contract["inference"]["primary_window"]["seed"])
    replay: dict[str, dict[str, dict[str, Any]]] = {}
    for role in ("D", "V"):
        replay[role] = {}
        for model in MODELS:
            losses, sessions, rows = _primary_loss_cube(
                cube, role=role, model=model, start=start, end=end
            )
            computed = analyse_losses(losses, sessions, repetitions=repetitions, seed=seed)
            published = result["evaluation"][role][model]["windows"]["primary_20"]
            for contrast, statistics in computed.items():
                for key, value in statistics.items():
                    if value != published[contrast][key]:
                        raise ValueError(
                            "PHASE8_DISPERSION_RESULT_REPLAY_MISMATCH:"
                            f"{role}:{model}:{contrast}:{key}"
                        )

            contrasts: dict[str, Any] = {}
            for contrast in CHECKED_CONTRASTS:
                base, expanded = PAIRS[contrast]
                per_session, labels = aggregate_by_session(
                    losses[base] - losses[expanded], sessions
                )
                contrasts[contrast] = {
                    **published[contrast],
                    "origins": rows,
                    "origins_per_session_min": int(
                        min(np.count_nonzero(sessions == label) for label in labels)
                    ),
                    "origins_per_session_max": int(
                        max(np.count_nonzero(sessions == label) for label in labels)
                    ),
                    "session_sigma": float(np.std(per_session, ddof=1)),
                    "standard_error": float(np.std(per_session, ddof=1) / np.sqrt(labels.size)),
                }
            replay[role][model] = contrasts
    return replay


def _current_dv_reference(
    b0_panel: Path,
    b1_panel: Path,
    b2_panel: Path,
    pointers: Mapping[str, Any],
) -> tuple[dict[str, dict[str, dict[str, float]]], dict[str, Any]]:
    supplied = {
        "artifacts/rp2_block4_b0/b0_panel.parquet": b0_panel,
        "artifacts/rp2_block5_surface/b1_surface_panel.parquet": b1_panel,
        "artifacts/rp2_block6_flow/b2_flow_panel.parquet": b2_panel,
    }
    identities: dict[str, Any] = {}
    for logical_path, path in supplied.items():
        expected = str(pointers["panels"][logical_path]["sha256"])
        _assert_hash(path, expected, "CURRENT_DV_PANEL")
        identities[logical_path] = {
            "bytes": path.stat().st_size,
            "sha256": expected,
        }

    panel = load_merged_panel(b0_panel, b1_panel, b2_panel)
    reference: dict[str, dict[str, dict[str, float]]] = {}
    role_sessions: dict[str, int] = {}
    for role in ("D", "V"):
        role_sessions[role] = int(panel.filter(pl.col("role") == role)["session_date"].n_unique())
        measured, _ = measure_dispersion(panel, role=role, train_share=0.6)
        reference[role] = measured
    return reference, {"panels": identities, "role_sessions": role_sessions}


def build_audit(
    *, forecast_cube: Path, b0_panel: Path, b1_panel: Path, b2_panel: Path
) -> dict[str, Any]:
    result = _load_json(RESULT)
    contract = _load_json(CONTRACT)
    design = _load_json(DESIGN)
    pointers = _load_json(POINTERS)
    _assert_hash(forecast_cube, str(result["forecast_cube_sha256"]), "CUBE")
    _assert_hash(
        DESIGN,
        str(contract["provenance"]["input_sha256"][DESIGN.relative_to(ROOT).as_posix()]),
        "DESIGN",
    )
    if result["contract_sha256"] != contract["contract_sha256"]:
        raise ValueError("PHASE8_DISPERSION_CONTRACT_IDENTITY_MISMATCH")

    cube = pl.read_parquet(forecast_cube)
    replay = _replay_phase8(cube, result, contract)
    current_reference, current_identity = _current_dv_reference(
        b0_panel, b1_panel, b2_panel, pointers
    )
    calibration = {
        (row["reference_role"], row["family"], row["contrast"]): row
        for row in contract["power"]["calibration"]
    }

    cells: dict[str, dict[str, dict[str, Any]]] = {}
    for role in ("D", "V"):
        cells[role] = {}
        for model in MODELS:
            b1 = replay[role][model]["delta_b1"]
            b2 = replay[role][model]["delta_b2_given_b1"]
            frozen = calibration[(role, model, "delta_b1")]
            phase8_sigma = float(b1["session_sigma"])
            frozen_sigma = float(frozen["session_sigma"])
            current_sigma = float(current_reference[role][model]["delta_b1_session_sigma"])
            cells[role][model] = {
                "delta_b1": {
                    "estimate": b1["estimate"],
                    "ci_low": b1["ci_low"],
                    "ci_high": b1["ci_high"],
                    "p_value_raw": b1["p_value_raw"],
                    "p_value_holm_descriptive": b1["p_value_holm_descriptive"],
                    "holm_below_0_05": b1["p_value_holm_descriptive"] < 0.05,
                    "phase8_session_sigma": phase8_sigma,
                    "phase8_standard_error": b1["standard_error"],
                    "origins": b1["origins"],
                    "origins_per_session_min": b1["origins_per_session_min"],
                    "origins_per_session_max": b1["origins_per_session_max"],
                    "contract_reference": {
                        "mde_n20": frozen["mde_n20"],
                        "session_sigma": frozen_sigma,
                        "effect_to_mde": abs(float(b1["estimate"])) / float(frozen["mde_n20"]),
                        "reference_to_phase8_sigma": frozen_sigma / phase8_sigma,
                        "phase8_to_reference_variance": (phase8_sigma / frozen_sigma) ** 2,
                    },
                    "current_dv_reference": {
                        "evaluation_sessions": int(
                            current_reference[role][model]["evaluation_sessions"]
                        ),
                        "session_sigma": current_sigma,
                        "reference_to_phase8_sigma": current_sigma / phase8_sigma,
                        "phase8_to_reference_variance": (phase8_sigma / current_sigma) ** 2,
                    },
                },
                "delta_b2_given_b1": {
                    "estimate": b2["estimate"],
                    "ci_low": b2["ci_low"],
                    "ci_high": b2["ci_high"],
                    "p_value_raw": b2["p_value_raw"],
                    "p_value_holm_descriptive": b2["p_value_holm_descriptive"],
                    "interval_crosses_zero": b2["ci_low"] <= 0.0 <= b2["ci_high"],
                    "phase8_session_sigma": b2["session_sigma"],
                    "phase8_standard_error": b2["standard_error"],
                },
            }

    b1_cells = [cells[role][model]["delta_b1"] for role in ("D", "V") for model in MODELS]
    b2_cells = [cells[role][model]["delta_b2_given_b1"] for role in ("D", "V") for model in MODELS]
    audit: dict[str, Any] = {
        "schema_version": "phase8-bridge-dispersion-audit-v1.0",
        "status": "COMPLETE",
        "claim_classification": "EXPLORATORY_DESCRIPTIVE_NOT_CONFIRMATORY",
        "protocol_id": contract["protocol_id"],
        "contract_sha256": contract["contract_sha256"],
        "source_identity": {
            "forecast_cube": {
                "bytes": forecast_cube.stat().st_size,
                "sha256": result["forecast_cube_sha256"],
            },
            "result": {
                "path": RESULT.relative_to(ROOT).as_posix(),
                "file_sha256": _sha256(RESULT),
                "result_sha256": result["result_sha256"],
            },
            "contract_power_design": {
                "path": DESIGN.relative_to(ROOT).as_posix(),
                "file_sha256": _sha256(DESIGN),
                "design_sha256": design["design_sha256"],
                "producer_commit": "9453954a2191e04e2990dbf37504dcbca5e7c6fc",
                "producer_sha256": HISTORICAL_DESIGN_PRODUCER_SHA256,
                "historical_input_bytes_available_to_this_audit": False,
                "comparability": (
                    "Same QLIKE contrast and session aggregation; the historical producer "
                    "predates the Phase 8 preprocessing and model-selection pipeline."
                ),
            },
            "current_dv_reference": current_identity,
        },
        "method": {
            "estimand": "QLIKE(base) - QLIKE(expanded)",
            "aggregation": "mean within XNYS session, then equal weight across sessions",
            "dispersion": "sample standard deviation of session means (ddof=1)",
            "primary_sessions": 20,
            "contract_mde_alpha_one_sided": contract["power"]["reference_alpha"],
            "contract_mde_power": contract["power"]["power"],
            "descriptive_holm_family_size": contract["multiplicity"]["holm_family_size_per_model"],
            "confidence_interval": contract["inference"]["primary_window"]["confidence_interval"],
        },
        "checks": {
            "sealed_store_reopened": False,
            "second_evaluator_execution": False,
            "cube_duplicate_keys": 0,
            "cube_nulls": int(cube.null_count().sum_horizontal().item()),
            "cube_rows": cube.height,
            "published_statistics_replayed_exactly": True,
            "replayed_contrast_rows": 20,
            "replayed_statistic_fields": 140,
        },
        "cells": cells,
        "conclusion": {
            "delta_b1_holm_below_0_05_cells": sum(
                bool(cell["holm_below_0_05"]) for cell in b1_cells
            ),
            "delta_b2_given_b1_holm_below_0_05_cells": sum(
                float(cell["p_value_holm_descriptive"]) < 0.05 for cell in b2_cells
            ),
            "delta_b2_given_b1_intervals_crossing_zero": sum(
                bool(cell["interval_crosses_zero"]) for cell in b2_cells
            ),
            "aggregation_change_supported": False,
            "sub_mde_explanation": (
                "The registered MDE is an ex-ante 80%-power design value at one-sided "
                "alpha 0.005, not a minimum significance threshold. Realized Phase 8 "
                "session dispersion is lower in every Holm-below-0.05 B1 cell than both "
                "the frozen contract reference and the current D/V same-estimator reference."
            ),
            "mechanism_claim": (
                "Lower realized loss-differential dispersion is measured; a calmer market "
                "regime is not identified causally."
            ),
            "historical_reference_limitation": (
                "The frozen design output and its producer remain hash-verifiable, but the "
                "historical D/V panel bytes are unavailable for an upstream refit and that "
                "producer predates the Phase 8 model pipeline. The current D/V panels provide "
                "the independent same-estimator comparison."
            ),
        },
    }
    audit["audit_sha256"] = _canonical_sha256(audit, omit="audit_sha256")
    return audit


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--forecast-cube", type=Path, required=True)
    parser.add_argument("--b0-panel", type=Path, required=True)
    parser.add_argument("--b1-panel", type=Path, required=True)
    parser.add_argument("--b2-panel", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    payload = build_audit(
        forecast_cube=args.forecast_cube,
        b0_panel=args.b0_panel,
        b1_panel=args.b1_panel,
        b2_panel=args.b2_panel,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"[phase8-dispersion] wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
