"""Quantify the B2 history repair on local, already-exposed data; never retune."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
from scripts.build_target_blind_common_panel_v22 import (
    B1_ORIGINS,
    B2_AVAILABILITY,
    B2_PRIMARY_ROOT,
    ROOT,
    combined_input_digest,
    sha256_file,
)

from mds650.metrics import regression_metrics
from mds650.phase6 import B2V2_FEATURES, build_b2v2_from_activity
from mds650.phase6_evaluation import (
    add_training_volatility_regime,
    forecast_phase6_fold,
    phase6_fold_definitions,
    phase6_information_sets,
)
from mds650.study_design import canonical_sha256
from mds650.target_blind_panel_v22 import (
    B2_PRIMARY_VARIANT,
    KEY_COLUMNS,
    apply_b2_availability_mask_v22,
)
from mds650.target_blind_sourcebound_v24 import write_if_new_or_identical_v24
from mds650.temporal_validation import split_expanding_fold

SOURCE = Path("D:/MDS650/evidence_root/pit_v22_successor") / (
    "pit-v22-successor-evaluation-v2-20260902"
)
PUBLISHED = Path("D:/MDS650/phase6/derived/target_blind_v22") / (
    "target_blind_common_predictors_v22.parquet"
)
PRIVATE = Path("D:/MDS650/b2_history_repair_v1")
PUBLIC = ROOT / "artifacts/b2_history_repair_v1"


def write_json(path: Path, value: dict[str, Any]) -> None:
    """Reuse the existing no-overwrite writer for an auditable sidecar."""
    value = {**value, "manifest_sha256": canonical_sha256(value)}

    def writer(destination: Path) -> None:
        destination.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    write_if_new_or_identical_v24(path, writer)


def feature_impact(before: pl.DataFrame, after: pl.DataFrame) -> dict[str, Any]:
    """Keep missingness changes separate from numeric changes on identical keys."""
    before, after = before.sort("origin_id"), after.sort("origin_id")
    if not before.select(*KEY_COLUMNS).equals(after.select(*KEY_COLUMNS)):
        raise ValueError("B2_REPAIR_ORIGIN_MISMATCH")
    x = before.select(B2V2_FEATURES).to_numpy().astype(float)
    y = after.select(B2V2_FEATURES).to_numpy().astype(float)
    bx, by = np.isfinite(x).all(axis=1), np.isfinite(y).all(axis=1)
    common = bx & by
    changed = x[common] != y[common]
    delta = np.abs(x[common] - y[common])
    return {
        "rows": before.height,
        "sessions": before["session_date"].n_unique(),
        "before_complete": int(bx.sum()),
        "after_complete": int(by.sum()),
        "lost_complete": int((bx & ~by).sum()),
        "gained_complete": int((~bx & by).sum()),
        "common_complete": int(common.sum()),
        "changed_common_rows": int(changed.any(axis=1).sum()),
        "changed_common_cells": int(changed.sum()),
        "features": {
            f: {
                "changed_rows": int(changed[:, i].sum()),
                "max_abs_delta": float(delta[:, i].max()) if common.any() else None,
            }
            for i, f in enumerate(B2V2_FEATURES)
        },
    }


def build_features() -> None:
    """Measure numeric contamination before any read of archived outcomes."""
    paths = sorted(B2_PRIMARY_ROOT.glob("date=*.parquet"))
    manifest = json.loads(
        (
            ROOT
            / "artifacts/target_blind_v22"
            / ("target_blind_common_predictor_manifest_v22.json")
        ).read_text()
    )
    hashes = {
        "origins_sha256": sha256_file(B1_ORIGINS),
        "b2_availability_sidecar_sha256": sha256_file(B2_AVAILABILITY),
        "b2_primary_inputs_sha256": combined_input_digest(paths),
    }
    if any(manifest["source_hashes"][k] != v for k, v in hashes.items()):
        raise ValueError("B2_REPAIR_SOURCE_DRIFT")
    if sha256_file(PUBLISHED) != manifest["output"]["panel_sha256"]:
        raise ValueError("B2_REPAIR_PUBLISHED_PANEL_DRIFT")
    origins = pl.read_parquet(B1_ORIGINS)
    availability = pl.read_parquet(B2_AVAILABILITY)
    selected = availability.filter(pl.col("canonical_variant") == B2_PRIMARY_VARIANT)
    activity = pl.read_parquet(paths)
    before = apply_b2_availability_mask_v22(
        build_b2v2_from_activity(activity, origins), availability
    )
    after = apply_b2_availability_mask_v22(
        build_b2v2_from_activity(
            activity,
            origins,
            history_eligibility=selected.select(*KEY_COLUMNS, "eligible_for_corrected_pit_panel"),
        ),
        availability,
    )
    published = pl.read_parquet(PUBLISHED)
    reproduction = feature_impact(published, before)
    if (
        reproduction["changed_common_cells"]
        or reproduction["lost_complete"]
        or (reproduction["gained_complete"])
    ):
        raise ValueError("B2_REPAIR_BASELINE_NOT_REPRODUCED")
    if hashes != {
        "origins_sha256": sha256_file(B1_ORIGINS),
        "b2_availability_sidecar_sha256": sha256_file(B2_AVAILABILITY),
        "b2_primary_inputs_sha256": combined_input_digest(paths),
    }:
        raise ValueError("B2_REPAIR_INPUT_CHANGED_DURING_BUILD")
    write_if_new_or_identical_v24(
        PRIVATE / "b2_corrected.parquet", lambda p: after.write_parquet(p)
    )
    result = {
        "schema_version": "b2-history-repair-impact-1.0",
        "status": "FEATURE_IMPACT_MEASURED",
        "historical_masked_features_reproduced_exactly": True,
        "excluded_activity_origins": selected.filter(
            ~pl.col("eligible_for_corrected_pit_panel")
        ).height,
        "impact": feature_impact(before, after),
        "impact_on_published_common_predictor_rows": feature_impact(
            before.join(
                published.filter(pl.col("common_predictor_complete")).select("origin_id"),
                on="origin_id",
                how="semi",
            ),
            after.join(
                published.filter(pl.col("common_predictor_complete")).select("origin_id"),
                on="origin_id",
                how="semi",
            ),
        ),
        "source_hashes": hashes,
        "runtime_hashes": {
            f: sha256_file(ROOT / f)
            for f in (
                "src/mds650/phase6.py",
                "src/mds650/target_blind_panel_v22.py",
                "scripts/build_target_blind_common_panel_v22.py",
                "scripts/audit_b2_history_repair_v1.py",
            )
        },
        "corrected_features_sha256": sha256_file(PRIVATE / "b2_corrected.parquet"),
        "target_reads": 0,
        "provider_requests": 0,
        "alpha_spent": 0,
        "capital_go": False,
    }
    write_json(PUBLIC / "feature_impact.json", result)
    print(json.dumps(result["impact"]), flush=True)


def forecast(panel: pl.DataFrame, prereg: dict[str, Any], ledger: dict[str, Any]) -> pl.DataFrame:
    """Refit the archived choices on unchanged chronological folds; no search."""
    selections = ledger["selected_variants"][:12]
    parts = []
    for fold in phase6_fold_definitions(prereg):
        guard = int(prereg["models"]["purge_embargo_minutes"])
        training, testing = split_expanding_fold(
            panel,
            fold,
            purge_minutes=guard,
            embargo_minutes=guard,
        )
        testing, _ = add_training_volatility_regime(training, testing)
        for setting in (s for s in selections if s["fold"] == fold.fold):
            info, role = setting["information_set"], setting["model_role"]
            parts.append(
                forecast_phase6_fold(
                    training,
                    testing,
                    fold=fold,
                    information_set=info,
                    features=phase6_information_sets()[info],
                    role=role,
                    parameters=setting["parameters"],
                    preregistration=prereg,
                )
            )
    return pl.concat(parts).sort("fold", "model_role", "information_set", "origin_id")


def summarize(predictions: pl.DataFrame) -> dict[str, Any]:
    metrics = []
    gains = []
    for (fold, role), frame in predictions.group_by("fold", "model_role"):
        for (info,), model in frame.group_by("information_set"):
            metrics.append(
                {
                    "fold": fold,
                    "model_role": role,
                    "information_set": info,
                    "historical_role": "VALIDATION" if fold == 1 else "HOLDOUT",
                    "start": frame["session_date"].min(),
                    "end": frame["session_date"].max(),
                    **regression_metrics(model["rv30"].to_numpy(), model["forecast"].to_numpy()),
                }
            )
        wide = frame.pivot(
            on="information_set",
            index=[
                "origin_id",
                "asset",
                "session_date",
                "volatility_regime",
            ],
            values="qlike_loss",
        )
        for baseline, expanded in (("B0v2", "B1v2a"), ("B1v2a", "B2v2")):
            difference = wide.with_columns((pl.col(baseline) - pl.col(expanded)).alias("gain"))
            daily = (
                difference.group_by("session_date").agg(pl.col("gain").mean()).sort("session_date")
            )
            blocks = [float(b.mean()) for b in np.array_split(daily["gain"].to_numpy(), 4)]
            gains.append(
                {
                    "fold": fold,
                    "model_role": role,
                    "contrast": f"{expanded}_over_{baseline}",
                    "historical_role": "VALIDATION" if fold == 1 else "HOLDOUT",
                    "mean_by_origin": float(difference["gain"].to_numpy().mean()),
                    "mean_by_session": float(daily["gain"].to_numpy().mean()),
                    "sessions": daily.height,
                    "by_asset": difference.group_by("asset")
                    .agg(pl.col("gain").mean())
                    .sort("asset")
                    .to_dicts(),
                    "by_training_defined_regime": difference.group_by("volatility_regime")
                    .agg(pl.col("gain").mean())
                    .sort("volatility_regime")
                    .to_dicts(),
                    "four_chronological_block_means": blocks,
                }
            )
    return {
        "metrics": sorted(
            metrics, key=lambda r: (r["fold"], r["model_role"], r["information_set"])
        ),
        "gains": sorted(gains, key=lambda r: (r["fold"], r["model_role"], r["contrast"])),
    }


def evaluate() -> None:
    """Attribute differences using identical rows, folds, targets and parameters."""
    result_path = ROOT / "artifacts/target_blind_v22/successor_evaluation_result_v2.json"
    original = json.loads(result_path.read_text())
    names = {
        "linked_common_panel.parquet": "linked_common_panel_sha256",
        "oos_primary_predictions.parquet": "primary_predictions_sha256",
        "variant_ledger.json": "variant_ledger_sha256",
        "runtime_preregistration.json": "runtime_preregistration_sha256",
    }
    hashes = {name: sha256_file(SOURCE / name) for name in names}
    if any(hashes[name] != original["hashes"][key] for name, key in names.items()):
        raise ValueError("B2_REPAIR_ARCHIVE_DRIFT")
    feature_audit = json.loads((PUBLIC / "feature_impact.json").read_text())
    if sha256_file(PRIVATE / "b2_corrected.parquet") != feature_audit["corrected_features_sha256"]:
        raise ValueError("B2_REPAIR_FEATURE_DRIFT")
    protocol: dict[str, Any] = {
        "scope": "RETROSPECTIVE_REPAIR_SENSITIVITY_NOT_INDEPENDENT_CONFIRMATION",
        "source_hashes": hashes,
        "feature_audit_sha256": sha256_file(PUBLIC / "feature_impact.json"),
        "selection": "ARCHIVED_HYPERPARAMETERS_NO_RETUNING_SAME_ROWS_BOTH_ARMS",
        "alpha_spent": 0,
        "capital_go": False,
        "runtime_sha256": {
            f: sha256_file(ROOT / f)
            for f in (
                "src/mds650/phase6_evaluation.py",
                "src/mds650/modeling.py",
                "src/mds650/phase6.py",
                "src/mds650/temporal_validation.py",
                "src/mds650/metrics.py",
                "scripts/audit_b2_history_repair_v1.py",
                "uv.lock",
            )
        },
    }
    write_json(PUBLIC / "evaluation_protocol.json", protocol)
    panel = pl.read_parquet(SOURCE / "linked_common_panel.parquet")
    archived = pl.read_parquet(SOURCE / "oos_primary_predictions.parquet")
    prereg = json.loads((SOURCE / "runtime_preregistration.json").read_text())
    ledger = json.loads((SOURCE / "variant_ledger.json").read_text())
    replay = forecast(panel, prereg, ledger)
    keys = ["fold", "model_role", "information_set", "origin_id"]
    archived = archived.sort(keys)
    if not replay.select(*keys, "rv30").equals(archived.select(*keys, "rv30")):
        raise ValueError("B2_REPAIR_REPLAY_PAIRING_FAILURE")
    reproduction_error = float(
        np.max(np.abs(replay["forecast"].to_numpy() - archived["forecast"].to_numpy()))
    )
    if reproduction_error > 1e-12:
        raise ValueError(f"B2_REPAIR_FORECAST_REPLAY_MISMATCH:{reproduction_error}")
    metric_reproduction = {
        column: float(np.max(np.abs(replay[column].to_numpy() - archived[column].to_numpy())))
        for column in ("qlike_loss", "absolute_error", "squared_error")
    }
    if any(error > 1e-12 for error in metric_reproduction.values()):
        raise ValueError("B2_REPAIR_HISTORICAL_METRIC_MISMATCH")
    fixed = (
        panel.drop(*B2V2_FEATURES)
        .join(
            pl.read_parquet(PRIVATE / "b2_corrected.parquet").select("origin_id", *B2V2_FEATURES),
            on="origin_id",
            how="left",
            validate="1:1",
            maintain_order="left",
        )
        .filter(pl.all_horizontal(pl.col(f).is_finite() for f in B2V2_FEATURES))
    )
    matched_before = panel.join(fixed.select("origin_id"), on="origin_id", how="semi")
    if matched_before.height != panel.height:
        replay = forecast(matched_before, prereg, ledger)
    corrected = forecast(fixed, prereg, ledger)
    if not replay.select(*keys, "rv30").equals(corrected.select(*keys, "rv30")):
        raise ValueError("B2_REPAIR_ARMS_NOT_PAIRED")
    control = pl.col("information_set") != "B2v2"
    control_error = float(
        np.max(
            np.abs(
                replay.filter(control)["forecast"].to_numpy()
                - corrected.filter(control)["forecast"].to_numpy()
            )
        )
    )
    if control_error > 1e-12:
        raise ValueError(f"B2_REPAIR_B0_B1_CONTROL_DRIFT:{control_error}")
    for name, frame in (("before", replay), ("after", corrected)):
        write_if_new_or_identical_v24(PRIVATE / f"{name}_forecasts.parquet", frame.write_parquet)
    result = {
        **protocol,
        "status": "COMPLETED_RETROSPECTIVE_REPAIR_SENSITIVITY",
        "historical_forecast_reproduction_max_abs_error": reproduction_error,
        "historical_metric_reproduction_max_abs_error": metric_reproduction,
        "b0_b1_control_forecast_max_abs_error": control_error,
        "original_panel_rows": panel.height,
        "same_mask_rows": fixed.height,
        "rows_lost_to_corrected_history": panel.height - fixed.height,
        "forecast_rows_per_arm": corrected.height,
        "before": summarize(replay),
        "after": summarize(corrected),
        "forecast_hashes": {
            name: sha256_file(PRIVATE / f"{name}_forecasts.parquet") for name in ("before", "after")
        },
    }
    if any(sha256_file(SOURCE / name) != h for name, h in hashes.items()):
        raise ValueError("B2_REPAIR_ARCHIVE_CHANGED_DURING_RUN")
    if any(sha256_file(ROOT / f) != h for f, h in protocol["runtime_sha256"].items()):
        raise ValueError("B2_REPAIR_RUNTIME_CHANGED_DURING_RUN")
    if sha256_file(PRIVATE / "b2_corrected.parquet") != feature_audit["corrected_features_sha256"]:
        raise ValueError("B2_REPAIR_FEATURE_CHANGED_DURING_RUN")
    write_json(PUBLIC / "evaluation_result.json", result)
    print(
        json.dumps(
            {
                k: result[k]
                for k in (
                    "status",
                    "same_mask_rows",
                    "historical_forecast_reproduction_max_abs_error",
                )
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("features", "evaluate"))
    args = parser.parse_args()
    build_features() if args.stage == "features" else evaluate()
