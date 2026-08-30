"""Versioned, preregistered reanalysis of Ext1's directional B2 mechanism."""

from __future__ import annotations

import argparse
import hashlib
import json
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
from mds650.rp2.inference import (
    clustered_mean_test,
    inference_config_digest,
    minimum_detectable_effect_from_long_run_variance,
    newey_west_p_value,
    newey_west_variance,
    wild_cluster_bootstrap,
)
from mds650.rp2.panel import B0_FEATURES, B1_FEATURES, load_merged_panel, mask_sha256
from mds650.rp2.preprocessing import (
    describe_preprocessor,
    fit_preprocessor,
    fold_design,
    transform_features,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs" / "rp2_ext1_directional_v2.json"
OUTPUT = ROOT / "artifacts" / "rp2_ext1_directional_v2"
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
    score: FloatArray, response: FloatArray, sessions: IntArray, *, family_size: int
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
        evaluation_mask_sha256=hashlib.sha256(finite.tobytes()).hexdigest(),
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
            kept_frame = frame.filter(pl.Series(keep))
            sessions = kept_frame["session_date"].rank("dense").cast(pl.Int64).to_numpy() - 1
            key = f"metric/{cell_name}/matched120_tod/h{horizon}"
            record = directional_metric(
                score[keep],
                response[keep],
                np.asarray(sessions, dtype=np.int64),
                family_size=family_size,
            )
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
    path.write_text(
        json.dumps(document, indent=2, sort_keys=True, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    return path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("D:/MDS650"))
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    parser.add_argument("--train-share", type=float, default=0.6)
    parser.add_argument("--folds", type=int, default=5)
    args = parser.parse_args(argv)
    path = run(args.data_root, args.output_dir, train_share=args.train_share, folds=args.folds)
    print(path)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
