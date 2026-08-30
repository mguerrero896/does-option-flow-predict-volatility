"""Versioned, preregistered reanalysis of Ext1's directional B2 mechanism."""

from __future__ import annotations

import argparse
import json
import math
import subprocess
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
import polars as pl
import rp2_ext1_mechanism_utility as ext1
from scipy import stats

from mds650.b1v3_confirmation import canonical_sha256, sha256_file
from mds650.metrics import holm_adjust
from mds650.rp2.bars import BAR_SOURCES
from mds650.rp2.dml import cross_fitted_residuals, dml_partial_out, time_block_folds
from mds650.rp2.feature_registry import feature_map, registry_sha256
from mds650.rp2.inference import (
    clustered_mean_test,
    inference_config_digest,
    minimum_detectable_effect_from_long_run_variance,
    newey_west_p_value,
    newey_west_variance,
    wild_cluster_bootstrap,
)
from mds650.rp2.panel import (
    B0_FEATURES,
    B1_FEATURES,
    B2_FEATURES,
    chronological_split,
    common_evaluation_mask,
    lift_mask,
    load_merged_panel,
    mask_sha256,
    session_rank,
)
from mds650.rp2.preprocessing import (
    FittedPreprocessor,
    describe_preprocessor,
    fit_preprocessor,
    fold_design,
    transform_features,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs" / "rp2_ext1_directional_v2.json"
OUTPUT = ROOT / "artifacts" / "rp2_ext1_directional_v2"
FACTORIAL_CONTRACT = ROOT / "configs" / "rp2_ext1_directional_factorial_v1.json"
FACTORIAL_OUTPUT = ROOT / "artifacts" / "rp2_ext1_directional_factorial_v1"
FROZEN_ARTIFACT = ROOT / "artifacts" / "rp2_ext1_mechanism_utility" / "mechanism_utility.json"
PANEL_PATHS = {
    "B0": ROOT / "artifacts" / "rp2_block4_b0" / "b0_panel.parquet",
    "B1": ROOT / "artifacts" / "rp2_block5_surface" / "b1_surface_panel.parquet",
    "B2": ROOT / "artifacts" / "rp2_block6_flow" / "b2_flow_panel.parquet",
}
TIME_OF_DAY = ("minutes_since_open", "minutes_to_close")

type FloatArray = npt.NDArray[np.float64]
type BoolArray = npt.NDArray[np.bool_]
type IntArray = npt.NDArray[np.int64]


def _number(value: object) -> float:
    if not isinstance(value, (int, float)):
        raise TypeError("RP2_EXT1_DIRECTIONAL_EXPECTED_NUMBER")
    return float(value)


def load_contract(path: Path = CONTRACT) -> dict[str, Any]:
    """Load and verify the result-blind analysis contract."""

    document: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    stored = document.get("contract_sha256")
    unsigned = dict(document)
    unsigned.pop("contract_sha256", None)
    if stored != canonical_sha256(unsigned):
        raise ValueError("RP2_EXT1_DIRECTIONAL_CONTRACT_HASH_MISMATCH")
    family = document["family"]
    expected = (
        len(document["modes"])
        * len(document["cells"])
        * len(document["outcome"]["horizons_minutes"])
    )
    if family["dml_effect_tests"] != expected or family["size"] != (
        family["dml_effect_tests"] + family["directional_metric_tests"]
    ):
        raise ValueError("RP2_EXT1_DIRECTIONAL_FAMILY_MISMATCH")
    return document


def load_factorial_contract(path: Path = FACTORIAL_CONTRACT) -> dict[str, Any]:
    """Load the result-blind treatment-by-coverage contract and fail on drift."""

    document: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    stored = document.get("contract_sha256")
    unsigned = dict(document)
    unsigned.pop("contract_sha256", None)
    if stored != canonical_sha256(unsigned):
        raise ValueError("RP2_EXT1_FACTORIAL_CONTRACT_HASH_MISMATCH")

    frozen = json.loads(FROZEN_ARTIFACT.read_text(encoding="utf-8"))
    if sha256_file(FROZEN_ARTIFACT) != document["frozen_ext1"]["artifact_file_sha256"]:
        raise ValueError("RP2_EXT1_FACTORIAL_FROZEN_ARTIFACT_DRIFT")
    if frozen.get("core_treatments") != document["treatment_sets"]["ext1_exact"]["features"]:
        raise ValueError("RP2_EXT1_FACTORIAL_FROZEN_TREATMENTS_DRIFT")

    b2 = document["treatment_sets"]["b2_panel_12"]
    if b2["features"] != list(B2_FEATURES) or len(b2["features"]) != 12:
        raise ValueError("RP2_EXT1_FACTORIAL_B2_FEATURES_DRIFT")
    if b2["feature_registry_sha256"] != registry_sha256():
        raise ValueError("RP2_EXT1_FACTORIAL_FEATURE_REGISTRY_DRIFT")

    source_names = [name for name, _, _ in BAR_SOURCES]
    coverage = document["coverage_cells"]
    if coverage["complete"]["source_names"] != source_names:
        raise ValueError("RP2_EXT1_FACTORIAL_COMPLETE_COVERAGE_DRIFT")
    august = coverage["august"]["source_names"]
    if not august or not set(august) < set(source_names):
        raise ValueError("RP2_EXT1_FACTORIAL_AUGUST_COVERAGE_INVALID")

    expected = (
        len(document["treatment_sets"])
        * len(coverage)
        * len(document["roles"])
        * len(document["outcome"]["horizons_minutes"])
    )
    if document["family"]["size"] != expected:
        raise ValueError("RP2_EXT1_FACTORIAL_FAMILY_MISMATCH")
    return document


def factorial_cells(contract: Mapping[str, Any]) -> tuple[tuple[str, str], ...]:
    """The four treatment-by-coverage cells in their frozen declaration order."""

    return tuple(
        (treatment, coverage)
        for treatment in contract["treatment_sets"]
        for coverage in contract["coverage_cells"]
    )


def resolve_treatment_design(
    panel: pl.DataFrame,
    requested: Sequence[str],
    aliases: Mapping[str, Mapping[str, str]],
) -> tuple[list[str], tuple[str, ...], list[dict[str, str]]]:
    """Resolve historical labels to current columns without changing their values."""

    available = feature_map("B2_CORE", "B2_RICH")
    resolved: list[str] = []
    provenance: list[dict[str, str]] = []
    for name in requested:
        alias = aliases.get(name)
        source = name if alias is None else alias["panel_column"]
        if source not in available:
            raise ValueError(f"RP2_EXT1_FACTORIAL_UNKNOWN_TREATMENT:{name}:{source}")
        if source not in panel.columns:
            raise ValueError(f"RP2_EXT1_FACTORIAL_PANEL_COLUMN_MISSING:{name}:{source}")
        if source in resolved:
            raise ValueError(f"RP2_EXT1_FACTORIAL_DUPLICATE_RESOLUTION:{source}")
        resolved.append(source)
        if alias is not None:
            provenance.append(
                {
                    "requested_feature": name,
                    "panel_column": source,
                    "resolution": alias["status"],
                    "value_operation": "IN_MEMORY_DESIGN_ALIAS_NO_RECOMPUTATION",
                }
            )
    return resolved, tuple(requested), provenance


def exact_factorial_treatment_design(
    frame: pl.DataFrame, features: Sequence[str], train: BoolArray
) -> tuple[FloatArray, FittedPreprocessor]:
    """Impute and scale fold-locally while retaining only the requested treatment columns."""

    design, _, fitted = fold_design(
        frame,
        features,
        train,
        intercept=False,
        include_missing_indicators=False,
    )
    return design, fitted


def factorial_attribution(
    tests: Mapping[str, Mapping[str, object]], contract: Mapping[str, Any]
) -> dict[str, object]:
    """Describe the two main shifts on log(Wald/df), with the frozen classification rule."""

    treatment_effects: list[float] = []
    coverage_effects: list[float] = []
    interactions: list[dict[str, object]] = []

    def evidence(key: str) -> float:
        record = tests[key]
        value = _number(record["joint_wald"]) / _number(record["treatment_df"])
        if value <= 0.0:
            raise ValueError(f"RP2_EXT1_FACTORIAL_WALD_NONPOSITIVE:{key}")
        return math.log(value)

    for role in contract["roles"]:
        for horizon in contract["attribution"]["primary_horizons_minutes"]:
            core_august = evidence(f"ext1_exact/august/{role}/h{horizon}")
            core_complete = evidence(f"ext1_exact/complete/{role}/h{horizon}")
            b2_august = evidence(f"b2_panel_12/august/{role}/h{horizon}")
            b2_complete = evidence(f"b2_panel_12/complete/{role}/h{horizon}")
            treatment = ((b2_august - core_august) + (b2_complete - core_complete)) / 2.0
            coverage = ((core_complete - core_august) + (b2_complete - b2_august)) / 2.0
            interaction = (b2_complete - b2_august) - (core_complete - core_august)
            treatment_effects.append(treatment)
            coverage_effects.append(coverage)
            interactions.append(
                {
                    "role": role,
                    "horizon": horizon,
                    "treatment_main_effect": treatment,
                    "coverage_main_effect": coverage,
                    "interaction": interaction,
                }
            )

    treatment_shift = float(np.median(np.abs(treatment_effects)))
    coverage_shift = float(np.median(np.abs(coverage_effects)))
    if treatment_shift > 0.0 and treatment_shift >= 2.0 * coverage_shift:
        classification = "TREATMENT_SET"
    elif coverage_shift > 0.0 and coverage_shift >= 2.0 * treatment_shift:
        classification = "COVERAGE"
    else:
        classification = "MIXED_OR_INTERACTION"
    return {
        "classification": classification,
        "evidence_scale": contract["attribution"]["evidence_scale"],
        "median_abs_treatment_main_effect": treatment_shift,
        "median_abs_coverage_main_effect": coverage_shift,
        "primary_contrasts": interactions,
        "interpretation": contract["attribution"]["interpretation"],
    }


def analysis_mask(frame: pl.DataFrame, cell: BoolArray, horizon: int, mode: str) -> BoolArray:
    """Return the preregistered native or horizon-matched analysis rows."""

    response = np.asarray(frame[f"y_signed_return_{horizon}"].to_numpy(), dtype=np.float64)
    if mode == "native_tod":
        return cell & np.isfinite(response)
    if mode in {"matched120_no_tod", "matched120_tod"}:
        matched = np.asarray(frame["y_signed_return_120"].to_numpy(), dtype=np.float64)
        return cell & np.isfinite(matched) & np.isfinite(response)
    raise ValueError(f"RP2_EXT1_DIRECTIONAL_MODE_UNKNOWN:{mode}")


def effect_record(
    *,
    theta: float,
    standard_error: float,
    p_value: float,
    rows: int,
    clusters: int,
    evaluation_mask_sha256: str,
    family_size: int,
) -> dict[str, object]:
    """Serialize one effect without discarding its magnitude or design power."""

    degrees = max(clusters - 1, 1)
    critical = float(stats.t.ppf(0.975, df=degrees))
    family_alpha = 0.05 / family_size
    detectable = minimum_detectable_effect_from_long_run_variance(
        standard_error**2 * clusters,
        clusters,
        alpha=family_alpha,
        power=0.8,
    )
    return {
        "theta": theta,
        "standard_error": standard_error,
        "ci_95_low": theta - critical * standard_error,
        "ci_95_high": theta + critical * standard_error,
        "p_value": p_value,
        "familywise_mde": detectable,
        "below_familywise_mde": abs(theta) < detectable,
        "rows": rows,
        "clusters": clusters,
        "evaluation_mask_sha256": evaluation_mask_sha256,
    }


def directional_metric(
    score: FloatArray,
    response: FloatArray,
    sessions: IntArray,
    *,
    family_size: int,
    evaluation_mask_sha256: str,
) -> dict[str, object]:
    """Session-balanced sign accuracy; descriptive hit rate is retained separately."""

    finite = np.isfinite(score) & np.isfinite(response) & (response != 0.0)
    score, response, sessions = score[finite], response[finite], sessions[finite]
    predicted, positive = score > 0.0, response > 0.0
    balanced: list[float] = []
    hit_rate: list[float] = []
    labels: list[int] = []
    for label in np.unique(sessions):
        keep = sessions == label
        actual = positive[keep]
        if not actual.any() or actual.all():
            continue
        guess = predicted[keep]
        sensitivity = float(guess[actual].mean())
        specificity = float((~guess[~actual]).mean())
        balanced.append((sensitivity + specificity) / 2.0)
        hit_rate.append(float((guess == actual).mean()))
        labels.append(int(label))
    session_balanced = np.asarray(balanced, dtype=np.float64)
    session_labels = np.asarray(labels, dtype=np.int64)
    if session_balanced.size < 3:
        raise ValueError("RP2_EXT1_DIRECTIONAL_TOO_FEW_BALANCED_SESSIONS")
    centered = session_balanced - 0.5
    measured = clustered_mean_test(centered, session_labels)
    long_run = newey_west_variance(centered, lags=5)
    if long_run <= 0.0 and centered.size >= 2:
        long_run = float(np.var(centered, ddof=1))
    record = effect_record(
        theta=measured.mean,
        standard_error=measured.standard_error,
        p_value=measured.p_value_two_sided,
        rows=int(score.size),
        clusters=measured.clusters,
        evaluation_mask_sha256=evaluation_mask_sha256,
        family_size=family_size,
    )
    record.update(
        {
            "balanced_accuracy": float(session_balanced.mean()),
            "sign_accuracy": float(np.mean(hit_rate)),
            "positive_return_share": float(positive.mean()),
            "wild_cluster_p_value": wild_cluster_bootstrap(session_balanced - 0.5),
            "newey_west_p_value": newey_west_p_value(session_balanced - 0.5),
            "long_run_variance": long_run,
            "sessions": int(session_balanced.size),
            "excluded_single_class_sessions": int(np.unique(sessions).size - session_balanced.size),
        }
    )
    return record


def _cell_mask(frame: pl.DataFrame, specification: Mapping[str, str]) -> BoolArray:
    dates = frame["session_date"].cast(pl.Utf8)
    return np.asarray(
        (
            (frame["role"] == specification["role"])
            & (dates >= specification["start"])
            & (dates <= specification["end"])
        ).to_numpy(),
        dtype=bool,
    )


def _dml_effect(
    frame: pl.DataFrame,
    score: FloatArray,
    response: FloatArray,
    keep: BoolArray,
    nuisance_features: Sequence[str],
    *,
    folds: int,
    family_size: int,
) -> dict[str, object]:
    subset = frame.filter(pl.Series(keep))
    y = response[keep]
    d = score[keep]
    sessions = subset["session_date"].rank("dense").cast(pl.Int64).to_numpy() - 1
    sessions = np.asarray(sessions, dtype=np.int64)
    if y.size < 2000 or np.unique(sessions).size < 20:
        raise ValueError("RP2_EXT1_DIRECTIONAL_INSUFFICIENT_ROWS")
    blocks = time_block_folds(sessions, folds=folds, purge_sessions=1)
    placeholder = np.empty((y.size, len(nuisance_features) + 1), dtype=np.float64)
    designs: dict[int, FloatArray] = {}

    def nuisance_for(train: BoolArray) -> FloatArray:
        key = id(train)
        if key not in designs:
            designs[key] = fold_design(subset, nuisance_features, train)[0]
        return designs[key]

    y_residual = cross_fitted_residuals(placeholder, y, blocks, design_builder=nuisance_for)
    d_residual = cross_fitted_residuals(placeholder, d, blocks, design_builder=nuisance_for)
    estimate = dml_partial_out(y_residual, d_residual[:, None], sessions, ("directional_score",))
    record = effect_record(
        theta=float(estimate.theta[0]),
        standard_error=float(estimate.standard_error[0]),
        p_value=float(estimate.p_value[0]),
        rows=estimate.rows,
        clusters=estimate.clusters,
        evaluation_mask_sha256=mask_sha256(keep),
        family_size=family_size,
    )
    record.update(
        {
            "t_statistic": float(estimate.t_statistic[0]),
            "nuisance_features": list(nuisance_features),
            "time_of_day_controls": [name for name in TIME_OF_DAY if name in nuisance_features],
        }
    )
    return record


def _git_head() -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return completed.stdout.strip()


def _origins(panel: pl.DataFrame) -> dict[tuple[str, str], FloatArray]:
    out: dict[tuple[str, str], FloatArray] = {}
    for (asset, session_date), group in panel.group_by(
        ["asset", "session_date"], maintain_order=True
    ):
        out[(str(asset), str(session_date))] = np.asarray(
            group["origin_minute"].to_numpy(), dtype=np.float64
        )
    return out


def _source_hashes(data_root: Path) -> dict[str, object]:
    out: dict[str, object] = {}
    for name, role, relative in BAR_SOURCES:
        path = data_root / relative
        if not path.is_file():
            raise FileNotFoundError(f"RP2_EXT1_DIRECTIONAL_BAR_SOURCE_MISSING:{name}:{relative}")
        out[name] = {"role": role, "path": relative, "sha256": sha256_file(path)}
    return out


def _coverage_sources(names: Sequence[str]) -> tuple[tuple[str, str, str], ...]:
    selected = tuple(source for source in BAR_SOURCES if source[0] in names)
    if [name for name, _, _ in selected] != list(names):
        raise ValueError("RP2_EXT1_FACTORIAL_COVERAGE_SOURCE_DRIFT")
    return selected


def _factorial_role_results(
    panel: pl.DataFrame,
    targets: pl.DataFrame,
    *,
    role: str,
    requested: Sequence[str],
    aliases: Mapping[str, Mapping[str, str]],
    horizons: Sequence[int],
    train_share: float,
    folds: int,
) -> tuple[dict[int, dict[str, object]], dict[int, BoolArray], dict[str, object]]:
    actual, labels, alias_provenance = resolve_treatment_design(panel, requested, aliases)
    frame = (
        panel.filter(pl.col("role") == role)
        .join(targets, on=["asset", "session_date", "origin_minute"], how="left")
        .sort(["session_date", "asset", "origin_minute"])
    )
    rv30 = np.asarray(frame["rv30"].to_numpy(), dtype=np.float64)
    keep = common_evaluation_mask(frame, rv30)
    if int(keep.sum()) < 2000:
        raise ValueError(f"RP2_EXT1_FACTORIAL_INSUFFICIENT_BASE_ROWS:{role}")
    available = frame.filter(pl.Series(keep))
    sessions = session_rank(
        np.asarray(available["session_date"].cast(pl.Utf8).to_numpy(), dtype=np.str_)
    )
    train, _ = chronological_split(sessions, train_share=train_share)
    nuisance_features = [*B0_FEATURES, *B1_FEATURES]
    nuisance, _, nuisance_fitted = fold_design(available, nuisance_features, train)
    treatment, treatment_fitted = exact_factorial_treatment_design(available, actual, train)

    results: dict[int, dict[str, object]] = {}
    masks: dict[int, BoolArray] = {}
    for horizon in horizons:
        response = np.asarray(
            available[f"y_signed_return_{horizon}"].to_numpy(), dtype=np.float64
        )
        measured = ext1._dml_on_target(
            nuisance,
            treatment,
            response,
            sessions,
            labels,
            folds=folds,
            evaluation_base=keep,
            frame=available,
            nuisance_features=nuisance_features,
        )
        if measured is None:
            raise ValueError(f"RP2_EXT1_FACTORIAL_UNMEASURED:{role}:h{horizon}")
        mask = lift_mask(keep, np.isfinite(response))
        if measured["evaluation_mask_sha256"] != mask_sha256(mask):
            raise ValueError("RP2_EXT1_FACTORIAL_MASK_HASH_MISMATCH")
        measured.update(
            {
                "treatment_df": len(labels),
                "wald_per_df": _number(measured["joint_wald"]) / len(labels),
                "requested_treatments": list(labels),
                "resolved_panel_columns": actual,
            }
        )
        results[horizon] = measured
        masks[horizon] = mask
    design = {
        "requested_treatments": list(labels),
        "resolved_panel_columns": actual,
        "alias_resolution": alias_provenance,
        "treatment_design_policy": "EXACT_REQUESTED_FEATURES_NO_MISSING_INDICATORS",
        "excluded_missing_indicator_features": list(
            treatment_fitted.missing_indicator_features
        ),
        "nuisance_preprocessing": describe_preprocessor(nuisance_fitted),
        "treatment_preprocessing": describe_preprocessor(treatment_fitted),
    }
    return results, masks, design


def _factorial_mask_invariants(
    masks: Mapping[str, Mapping[int, BoolArray]], contract: Mapping[str, Any]
) -> dict[str, object]:
    same_treatment_masks: list[dict[str, object]] = []
    coverage_subsets: list[dict[str, object]] = []
    for role in contract["roles"]:
        for horizon in contract["outcome"]["horizons_minutes"]:
            for coverage in contract["coverage_cells"]:
                core = masks[f"ext1_exact/{coverage}/{role}"][horizon]
                b2 = masks[f"b2_panel_12/{coverage}/{role}"][horizon]
                if not np.array_equal(core, b2):
                    raise ValueError(
                        f"RP2_EXT1_FACTORIAL_TREATMENT_MASK_DRIFT:{coverage}:{role}:h{horizon}"
                    )
                same_treatment_masks.append(
                    {
                        "coverage": coverage,
                        "role": role,
                        "horizon": horizon,
                        "rows": int(core.sum()),
                        "evaluation_mask_sha256": mask_sha256(core),
                    }
                )
            for treatment in contract["treatment_sets"]:
                august = masks[f"{treatment}/august/{role}"][horizon]
                complete = masks[f"{treatment}/complete/{role}"][horizon]
                if not np.all(~august | complete):
                    raise ValueError(
                        f"RP2_EXT1_FACTORIAL_COVERAGE_NOT_NESTED:{treatment}:{role}:h{horizon}"
                    )
                coverage_subsets.append(
                    {
                        "treatment_set": treatment,
                        "role": role,
                        "horizon": horizon,
                        "august_rows": int(august.sum()),
                        "complete_rows": int(complete.sum()),
                        "added_rows": int((complete & ~august).sum()),
                    }
                )
    return {
        "same_coverage_role_horizon_same_mask_across_treatment_sets": True,
        "august_mask_subset_of_complete_mask": True,
        "treatment_mask_checks": same_treatment_masks,
        "coverage_subset_checks": coverage_subsets,
    }


def run_factorial(
    data_root: Path,
    output_dir: Path,
    *,
    contract_path: Path = FACTORIAL_CONTRACT,
) -> Path:
    """Execute the frozen 2x2 treatment-by-coverage directional comparison."""

    contract = load_factorial_contract(contract_path)
    source_hashes = _source_hashes(data_root)
    panel = load_merged_panel(PANEL_PATHS["B0"], PANEL_PATHS["B1"], PANEL_PATHS["B2"])
    origins = _origins(panel)
    targets: dict[str, pl.DataFrame] = {}
    coverage_records: dict[str, dict[str, object]] = {}
    for coverage_name, coverage_spec in contract["coverage_cells"].items():
        coverage_record: dict[str, object] = {}
        sources = _coverage_sources(coverage_spec["source_names"])
        targets[coverage_name] = ext1.build_target_battery(
            data_root,
            origins,
            sources=sources,
            coverage=coverage_record,
        )
        coverage_records[coverage_name] = coverage_record

    tests: dict[str, dict[str, object]] = {}
    masks: dict[str, dict[int, BoolArray]] = {}
    designs: dict[str, object] = {}
    raw_p: dict[str, float] = {}
    for treatment_name, coverage_name in factorial_cells(contract):
        treatment = contract["treatment_sets"][treatment_name]
        for role in contract["roles"]:
            records, cell_masks, design = _factorial_role_results(
                panel,
                targets[coverage_name],
                role=role,
                requested=treatment["features"],
                aliases=contract["aliases"],
                horizons=contract["outcome"]["horizons_minutes"],
                train_share=contract["estimator"]["train_share_for_feature_preprocessing"],
                folds=contract["estimator"]["folds"],
            )
            cell = f"{treatment_name}/{coverage_name}/{role}"
            masks[cell] = cell_masks
            designs[cell] = design
            for horizon, record in records.items():
                key = f"{cell}/h{horizon}"
                tests[key] = record
                raw_p[key] = _number(record["joint_p_value"])

    if len(tests) != contract["family"]["size"]:
        raise ValueError(f"RP2_EXT1_FACTORIAL_FAMILY_REALIZED:{len(tests)}")
    for key, adjusted in holm_adjust(raw_p).items():
        tests[key]["holm_p"] = adjusted
    invariants = _factorial_mask_invariants(masks, contract)
    attribution = factorial_attribution(tests, contract)

    document: dict[str, object] = {
        "schema_version": "rp2-ext1-directional-factorial-results-v1.0",
        "label": contract["label"],
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "code_commit": _git_head(),
        "sealed_cohorts_read": 0,
        "contract": {
            "path": contract_path.relative_to(ROOT).as_posix(),
            "contract_sha256": contract["contract_sha256"],
            "file_sha256": sha256_file(contract_path),
        },
        "inference_config_digest": inference_config_digest(),
        "inputs": {
            "panels": {
                name: {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path)}
                for name, path in PANEL_PATHS.items()
            },
            "bar_sources": source_hashes,
            "frozen_ext1": {
                "path": FROZEN_ARTIFACT.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(FROZEN_ARTIFACT),
            },
            "feature_registry_sha256": registry_sha256(),
        },
        "coverage": coverage_records,
        "designs": designs,
        "tests": tests,
        "mask_invariants": invariants,
        "attribution": attribution,
        "limits": [
            "The two treatment sets are not nested, so attribution is descriptive.",
            "D and V are already-observed exploratory partitions, not confirmation cohorts.",
            (
                "No trading profit, costs, slippage, capacity, calibration, or causal "
                "effect is measured."
            ),
        ],
    }
    document["self_sha256"] = canonical_sha256(document)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "results.json"
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(document, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
    return path


def _survivors(battery: Mapping[str, object]) -> list[str]:
    return sorted(
        name
        for name, value in battery.items()
        if isinstance(value, dict) and float(value.get("holm_p", 1.0)) <= 0.05
    )


def _legacy_reproduction(
    panel: pl.DataFrame,
    targets: pl.DataFrame,
    frozen: Mapping[str, object],
    *,
    train_share: float,
    folds: int,
) -> dict[str, object]:
    roles: dict[str, object] = {}
    for role in ("D", "V"):
        measured = ext1.run_role(panel, targets, role=role, train_share=train_share, folds=folds)
        current = measured["a_other_targets"]
        assert isinstance(current, dict)
        frozen_role = frozen[role]
        assert isinstance(frozen_role, dict)
        historical = frozen_role["a_other_targets"]
        assert isinstance(historical, dict)
        comparisons: dict[str, object] = {}
        for outcome in ("y_signed_return_60", "y_signed_return_120"):
            old = historical[outcome]
            new = current[outcome]
            assert isinstance(old, dict) and isinstance(new, dict)
            comparisons[outcome] = {
                "frozen": {
                    key: old[key]
                    for key in ("joint_wald", "joint_p_value", "holm_p", "rows", "clusters")
                },
                "current_same_source_universe": {
                    key: new[key]
                    for key in ("joint_wald", "joint_p_value", "holm_p", "rows", "clusters")
                },
            }
        roles[role] = {
            "current_battery": current,
            "frozen_holm_survivors": _survivors(historical),
            "current_holm_survivors": _survivors(current),
            "key_comparisons": comparisons,
        }
    frozen_treatments = frozen.get("core_treatments")
    exact = frozen_treatments == list(ext1.CORE_TREATMENTS)
    return {
        "status": "NUMERICALLY_COMPARABLE_NOT_EXACT" if not exact else "EXACT_DESIGN",
        "exact_reproduction": False,
        "reason": (
            "The frozen artifact has no panel, bar, registry, or code hashes and its treatment "
            "registry differs from the current corrected registry; current code is run on the "
            "same three bar-source names and every difference is retained."
        ),
        "frozen_core_treatments": frozen_treatments,
        "current_core_treatments": list(ext1.CORE_TREATMENTS),
        "roles": roles,
    }


def _directional_results(
    panel: pl.DataFrame,
    targets: pl.DataFrame,
    contract: Mapping[str, Any],
    *,
    folds: int,
) -> tuple[dict[str, object], dict[str, object]]:
    frame = panel.join(targets, on=["asset", "session_date", "origin_minute"], how="left").sort(
        ["session_date", "asset", "origin_minute"]
    )
    features = list(contract["instrument"]["features"])
    weights = np.asarray(contract["instrument"]["weights"], dtype=np.float64)
    discovery = np.asarray((frame["role"] == "D").to_numpy(), dtype=bool)
    fitted = fit_preprocessor(frame, features, discovery)
    transformed = transform_features(frame, features, fitted, intercept=False)
    score = np.asarray(transformed[:, : len(features)] @ weights, dtype=np.float64)
    family_size = int(contract["family"]["size"])
    tests: dict[str, dict[str, object]] = {}
    raw_p: dict[str, float] = {}
    horizons = [int(value) for value in contract["outcome"]["horizons_minutes"]]
    for cell_name, cell_specification in contract["cells"].items():
        cell = _cell_mask(frame, cell_specification)
        for mode in contract["modes"]:
            nuisance = [*B0_FEATURES, *B1_FEATURES]
            if mode == "matched120_no_tod":
                nuisance = [name for name in nuisance if name not in TIME_OF_DAY]
            for horizon in horizons:
                keep = analysis_mask(frame, cell, horizon, mode)
                response = np.asarray(
                    frame[f"y_signed_return_{horizon}"].to_numpy(), dtype=np.float64
                )
                key = f"dml/{cell_name}/{mode}/h{horizon}"
                record = _dml_effect(
                    frame,
                    score,
                    response,
                    keep,
                    nuisance,
                    folds=folds,
                    family_size=family_size,
                )
                record.update(
                    {"test_type": "dml_effect", "cell": cell_name, "mode": mode, "horizon": horizon}
                )
                tests[key] = record
                raw_p[key] = _number(record["p_value"])
        for horizon in (60, 120):
            keep = analysis_mask(frame, cell, horizon, "matched120_tod")
            response = np.asarray(frame[f"y_signed_return_{horizon}"].to_numpy(), dtype=np.float64)
            metric_keep = keep & np.isfinite(score) & np.isfinite(response) & (response != 0.0)
            dates = np.asarray(frame["session_date"].cast(pl.Utf8).to_numpy(), dtype=np.str_)
            candidate_dates = np.unique(dates[metric_keep])
            eligible_dates = [
                session
                for session in candidate_dates
                if np.unique(response[metric_keep & (dates == session)] > 0.0).size == 2
            ]
            excluded_sessions = len(candidate_dates) - len(eligible_dates)
            metric_keep &= np.isin(dates, eligible_dates)
            kept_frame = frame.filter(pl.Series(metric_keep))
            sessions = kept_frame["session_date"].rank("dense").cast(pl.Int64).to_numpy() - 1
            key = f"metric/{cell_name}/matched120_tod/h{horizon}"
            record = directional_metric(
                score[metric_keep],
                response[metric_keep],
                np.asarray(sessions, dtype=np.int64),
                family_size=family_size,
                evaluation_mask_sha256=mask_sha256(metric_keep),
            )
            record["excluded_single_class_sessions"] = excluded_sessions
            record.update(
                {
                    "test_type": "balanced_sign_accuracy",
                    "cell": cell_name,
                    "mode": "matched120_tod",
                    "horizon": horizon,
                }
            )
            tests[key] = record
            raw_p[key] = _number(record["p_value"])
    if len(raw_p) != family_size:
        raise ValueError(f"RP2_EXT1_DIRECTIONAL_FAMILY_REALIZED:{len(raw_p)}:{family_size}")
    for key, adjusted in holm_adjust(raw_p).items():
        tests[key]["holm_p"] = adjusted
    primary = [tests[f"dml/V_all/matched120_tod/h{horizon}"] for horizon in (60, 120)]
    native = [tests[f"dml/V_all/native_tod/h{horizon}"] for horizon in (60, 120)]
    pursue = all(
        _number(record["theta"]) > 0.0
        and _number(record["ci_95_low"]) > 0.0
        and _number(record["holm_p"]) <= 0.05
        and not bool(record["below_familywise_mde"])
        for record in primary
    ) and all(_number(record["theta"]) > 0.0 for record in native)
    strict = _number(primary[1]["ci_95_high"]) <= 0.0
    decision = {
        "status": "FALSIFIED_DIRECTION" if strict else ("PURSUE" if pursue else "DO_NOT_PURSUE"),
        "pursue_rule_passed": pursue,
        "strict_directional_falsifier_triggered": strict,
        "primary_test_keys": [
            "dml/V_all/matched120_tod/h60",
            "dml/V_all/matched120_tod/h120",
        ],
        "native_sign_check_keys": ["dml/V_all/native_tod/h60", "dml/V_all/native_tod/h120"],
    }
    instrument = {
        "features": features,
        "weights": weights.tolist(),
        "preprocessing": describe_preprocessor(fitted),
        "score_mean": float(score.mean()),
        "score_standard_deviation": float(score.std()),
        "does_not_measure": [
            "causal effect",
            "trading profit or implementability",
            "transaction costs, slippage, capacity, or risk-adjusted return",
            "probability calibration",
        ],
    }
    return {"tests": tests, "decision": decision}, instrument


def run(data_root: Path, output_dir: Path, *, train_share: float, folds: int) -> Path:
    contract = load_contract()
    source_hashes = _source_hashes(data_root)
    frozen_hash = sha256_file(FROZEN_ARTIFACT)
    expected_frozen = contract["legacy_reproduction"]["artifact_file_sha256"]
    if frozen_hash != expected_frozen:
        raise ValueError("RP2_EXT1_DIRECTIONAL_FROZEN_ARTIFACT_DRIFT")
    panel = load_merged_panel(PANEL_PATHS["B0"], PANEL_PATHS["B1"], PANEL_PATHS["B2"])
    origins = _origins(panel)
    legacy_coverage: dict[str, object] = {}
    current_coverage: dict[str, object] = {}
    legacy_names = contract["legacy_reproduction"]["source_names"]
    legacy_sources = tuple(source for source in BAR_SOURCES if source[0] in legacy_names)
    legacy_targets = ext1.build_target_battery(
        data_root, origins, sources=legacy_sources, coverage=legacy_coverage
    )
    current_targets = ext1.build_target_battery(
        data_root, origins, sources=BAR_SOURCES, coverage=current_coverage
    )
    frozen: dict[str, object] = json.loads(FROZEN_ARTIFACT.read_text(encoding="utf-8"))
    reproduction = _legacy_reproduction(
        panel, legacy_targets, frozen, train_share=train_share, folds=folds
    )
    directional, instrument = _directional_results(panel, current_targets, contract, folds=folds)
    document: dict[str, object] = {
        "schema_version": "rp2-ext1-directional-v2-results-v1.0",
        "label": "EXPLORATORY_DIRECTIONAL_REANALYSIS",
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "code_commit": _git_head(),
        "contract": {
            "path": "configs/rp2_ext1_directional_v2.json",
            "sha256": contract["contract_sha256"],
        },
        "inference_config_digest": inference_config_digest(),
        "sealed_cohorts_read": 0,
        "inputs": {
            "panels": {
                name: {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256_file(path)}
                for name, path in PANEL_PATHS.items()
            },
            "bar_sources": source_hashes,
            "frozen_artifact": {
                "path": FROZEN_ARTIFACT.relative_to(ROOT).as_posix(),
                "sha256": frozen_hash,
            },
        },
        "coverage": {"legacy_source_universe": legacy_coverage, "current": current_coverage},
        "reproduction": reproduction,
        "instrument": instrument,
        "directional": directional,
        "historical_decay_comparator": contract["historical_decay_comparator"],
    }
    document["self_sha256"] = canonical_sha256(document)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "results.json"
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(
        json.dumps(document, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)
    return path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("D:/MDS650"))
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    parser.add_argument("--factorial-only", action="store_true")
    parser.add_argument("--factorial-contract", type=Path, default=FACTORIAL_CONTRACT)
    parser.add_argument("--factorial-output-dir", type=Path, default=FACTORIAL_OUTPUT)
    parser.add_argument("--train-share", type=float, default=0.6)
    parser.add_argument("--folds", type=int, default=5)
    args = parser.parse_args(argv)
    if args.factorial_only:
        path = run_factorial(
            args.data_root,
            args.factorial_output_dir,
            contract_path=args.factorial_contract,
        )
    else:
        path = run(args.data_root, args.output_dir, train_share=args.train_share, folds=args.folds)
    print(path)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
