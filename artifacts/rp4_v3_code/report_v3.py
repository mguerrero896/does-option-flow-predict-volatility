"""Render completed RP4 v3 aggregates with immutable v1/v2 comparisons; never fit models."""

from __future__ import annotations

import argparse
import csv
import html
import io
import json
import math
import statistics
from collections import Counter
from datetime import date
from itertools import accumulate
from pathlib import Path
from typing import Any

from artifacts.rp4_code.evaluate import sha256, write_bytes_once, write_json_once
from artifacts.rp4_v3_code import inference as inf

ROOT = Path(__file__).resolve().parents[2]
LEGACY_MANIFEST_SHA = "2ba6b2611be4a4dd1e0cfd031a5f50680c96d665f603386522a9af0c21610083"
WINDOWS = {"primary": "Primaria", "confirmation": "Confirmación"}
VERSIONS = ("v1", "v2", "v3")
FAMILIES = {"v1": ("log_ols_harq", "lightgbm_qlike"), "v2": inf.FAMILIES, "v3": inf.FAMILIES}
type Rows = list[dict[str, Any]]
type Comparison = dict[str, dict[str, tuple[dict[str, Any], Rows]]]


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv(path: Path) -> Rows:
    return list(csv.DictReader(io.StringIO(path.read_text(encoding="utf-8"))))


def csv_bytes(rows: Rows) -> bytes:
    stream = io.StringIO(newline="")
    if rows:
        columns = list(dict.fromkeys(key for row in rows for key in row))
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    return stream.getvalue().encode("utf-8")


def number(value: Any, *, signed: bool = False) -> str:
    return (
        format(float(value), "+.8g" if signed else ".8g")
        if value is not None and math.isfinite(float(value))
        else "NO VERIFICABLE"
    )


def family_label(family: str, endpoint: str = "qlike_mean") -> str:
    if endpoint in ("quantile", "quantile_pinball_log_rv"):
        return "Lineal (cuantil)" if family == "log_ridge_harq" else "LightGBM (quantile)"
    if endpoint in ("jump", "jump_auc"):
        return "Lineal (logit)" if family == "log_ridge_harq" else "LightGBM (binary)"
    return family


def table(headers: list[str], rows: list[list[str]]) -> str:
    def line(values: list[str]) -> str:
        return (
            "| " + " | ".join(str(v).replace("|", "\\|").replace("\n", " ") for v in values) + " |"
        )

    return "\n".join([line(headers), line(["---"] * len(headers)), *map(line, rows)])


def _close(actual: Any, expected: float, reason: str) -> None:
    if actual is None or not math.isclose(float(actual), expected, rel_tol=1e-10, abs_tol=1e-12):
        raise ValueError("RP4_V3_REPORT_" + reason)


def differences(rows: Rows, family: str, base: str, richer: str) -> list[float]:
    return [
        float(r[f"loss__{family}__{base}"]) - float(r[f"loss__{family}__{richer}"]) for r in rows
    ]


def validate_receipt(
    path: Path,
    *,
    root: Path,
    private_root: Path,
    stage: str,
    window: str,
    required: list[Path],
) -> dict[str, Any]:
    """Check completed commands and every bound artifact/log before reading result payloads."""
    receipt: dict[str, Any] = read_json(path)
    if (
        receipt.get("status"),
        receipt.get("exit_code"),
        receipt.get("stage"),
        receipt.get("window"),
    ) != (
        "COMPLETE",
        0,
        stage,
        window,
    ):
        raise ValueError("RP4_V3_REPORT_INCOMPLETE_RECEIPT")
    if receipt.get("execution_failure") is not None:
        raise ValueError("RP4_V3_REPORT_EXECUTION_FAILURE")
    allowed = (root.resolve(), private_root.resolve())

    def allowed_path(value: str) -> Path:
        candidate = Path(value)
        candidate = (candidate if candidate.is_absolute() else root / candidate).resolve()
        if not any(candidate.is_relative_to(parent) for parent in allowed):
            raise ValueError("RP4_V3_REPORT_RECEIPT_PATH_OUTSIDE_SCOPE")
        return candidate

    pins = {
        allowed_path(name): digest for name, digest in receipt.get("artifacts_sha256", {}).items()
    }
    if not {p.resolve() for p in required} <= set(pins):
        raise ValueError("RP4_V3_REPORT_REQUIRED_ARTIFACT_NOT_PINNED")
    for source, digest in pins.items():
        if sha256(source) != digest:
            raise ValueError("RP4_V3_REPORT_RECEIPT_ARTIFACT_HASH_DRIFT")
    commands = receipt.get("commands", [])
    if not commands or any(not c.get("command") or c.get("exit_code") != 0 for c in commands):
        raise ValueError("RP4_V3_REPORT_COMMAND_EXIT_NOT_ZERO")
    for command in commands:
        if sha256(allowed_path(command["log"])) != command.get("log_sha256"):
            raise ValueError("RP4_V3_REPORT_COMMAND_LOG_HASH_DRIFT")
    for name, digest in receipt.get("evaluation_code_sha256", {}).items():
        if sha256(allowed_path(name)) != digest:
            raise ValueError("RP4_V3_REPORT_EVALUATION_CODE_DRIFT")
    return receipt


def validate_window(
    summary: dict[str, Any], rows: Rows, version: str, window: str, digest: str
) -> None:
    if summary.get("status") != "COMPUTED" or not rows:
        raise ValueError("RP4_V3_REPORT_COMPLETED_AGGREGATES_REQUIRED")
    if summary["window"] != window or summary["binding"]["specification_sha256"] != digest:
        raise ValueError("RP4_V3_REPORT_WINDOW_OR_SPECIFICATION_DRIFT")
    dates = [r["session_date"] for r in rows]
    if dates != sorted(set(dates)) or len(rows) != summary["N_sessions"]:
        raise ValueError("RP4_V3_REPORT_SESSION_ORDER_OR_COUNT")
    if set(summary["completed_session_sha256"]) != {d + ".json" for d in dates}:
        raise ValueError("RP4_V3_REPORT_COMPLETED_SESSION_SET")
    if summary["scheduled_sessions"] != len(rows) + len(summary["skipped_sessions"]):
        raise ValueError("RP4_V3_REPORT_UNACCOUNTED_SCHEDULE")
    expected = {(f, c) for f in FAMILIES[version] for c, _, _ in inf.CONTRASTS}
    if (
        len(summary["contrasts"]) != 4
        or {(r["family"], r["contrast"]) for r in summary["contrasts"]} != expected
    ):
        raise ValueError("RP4_V3_REPORT_CONTRAST_SET")
    for result in summary["contrasts"]:
        _, base, richer = next(c for c in inf.CONTRASTS if c[0] == result["contrast"])
        values = differences(rows, result["family"], base, richer)
        if not all(math.isfinite(value) for value in values):
            raise ValueError("RP4_V3_REPORT_NONFINITE_SESSION_LOSS")
        _close(result["estimate"], statistics.mean(values), "ESTIMATE_MISMATCH")
        baseline = statistics.mean(float(r[f"loss__{result['family']}__{base}"]) for r in rows)
        if baseline > 0:
            _close(
                result["qlike_reduction_percent"],
                100 * statistics.mean(values) / baseline,
                "PERCENT_MISMATCH",
            )
        if result["N_sessions"] != len(rows) or result["N_origins"] != summary["N_origins"]:
            raise ValueError("RP4_V3_REPORT_CONTRAST_N_MISMATCH")
    if version == "v3":
        required = (
            "comparability_bilateral",
            "distribution_secondary",
            "posterior_mean",
            "regime_secondary",
            "high_gamma_vs_rest",
            "quantile_secondary",
            "jump_secondary",
            "mz_secondary",
            "empty_window_secondary",
        )
        if any(name not in summary for name in required):
            raise ValueError("RP4_V3_REPORT_REGISTERED_SECONDARY_MISSING")
        recomputed = inf.family_fixed_sequence(summary["contrasts"])
        if (
            recomputed != summary["primary_sequence"]
            or recomputed["global_joint_reject"] != summary["global_joint_reject"]
        ):
            raise ValueError("RP4_V3_REPORT_SEQUENCE_DRIFT")
        for item in summary["distribution_secondary"]:
            _, base, richer = next(c for c in inf.CONTRASTS if c[0] == item["contrast"])
            delta = differences(rows, item["family"], base, richer)
            trim = math.floor(0.05 * len(delta))
            ordered = sorted(delta)
            estimate = (
                statistics.median(delta)
                if item["statistic"] == "median"
                else statistics.mean(
                    ordered[trim : len(ordered) - trim] if trim else ordered,
                )
            )
            _close(item["estimate"], estimate, "PAIRED_DISTRIBUTION_MISMATCH")
        for row in summary["empty_window_secondary"]["census"]:
            if row["N_origins"] != sum(
                row[k] for k in ("N_empty_origins", "N_nonempty_origins", "N_unknown_origins")
            ):
                raise ValueError("RP4_V3_REPORT_EMPTY_CENSUS_ACCOUNTING")


def fit_diagnostics(records: Rows, dates: list[str], window: str) -> tuple[Rows, Rows]:
    """Export selected metadata only: never model coefficients or origin forecasts."""
    normalized, calibrations = [], []
    seen = set()
    required = {
        (day, f"mean__{family}__{name}")
        for day in dates
        for family in inf.FAMILIES
        for name in inf.SETS
    }
    for row in records:
        key = (row["session"], row["model"])
        parts = row["model"].split("__")
        if key in seen or len(parts) != 3 or row["session"] not in dates:
            raise ValueError("RP4_V3_REPORT_FIT_KEY_INVALID")
        seen.add(key)
        endpoint, family, name = parts
        if (
            endpoint not in ("mean", "quantile", "jump")
            or family not in inf.FAMILIES
            or name not in inf.SETS
        ):
            raise ValueError("RP4_V3_REPORT_FIT_MODEL_INVALID")
        if row.get("endpoint", endpoint) != endpoint:
            raise ValueError("RP4_V3_REPORT_FIT_ENDPOINT_DRIFT")
        selected = row.get("selected", {})
        valid_days = row.get("inner_valid_sessions", [])
        if selected and (len(valid_days) != 10 or max(valid_days) >= row["session"]):
            raise ValueError("RP4_V3_REPORT_FIT_NONCAUSAL_TUNING")
        ridge = family == "log_ridge_harq"
        bounds = row.get("bounds", {}).get("refit", {})
        inner_bounds = row.get("bounds", {}).get("inner_fit", {})
        if bounds and not (0 < bounds["lower"] < bounds["upper"]):
            raise ValueError("RP4_V3_REPORT_FIT_INVALID_BOUNDS")
        if selected and not ridge and not 1 <= selected["rounds"] <= 2000:
            raise ValueError("RP4_V3_REPORT_FIT_ROUNDS_OUTSIDE_REGISTRY")
        preprocessing = row.get("preprocessing", {}).get("refit", {})
        winsor = preprocessing.get("winsorization", {})
        item = {
            "window": window,
            "session": row["session"],
            "endpoint": endpoint,
            "family": family,
            "information_set": name,
            "model": row["model"],
            "status": row.get("status", "COMPUTED" if selected else "NO VERIFICABLE"),
            "reason": row.get("reason"),
            "selected_lambda": selected.get("lambda"),
            "selected_rounds": selected.get("rounds"),
            "refit_rounds": row.get("refit_rounds"),
            "selected_leaves": selected.get("num_leaves"),
            "validation_score": selected.get(
                "validation_qlike",
                selected.get(
                    "validation_pinball",
                    selected.get("validation_logloss", selected.get("validation_score")),
                ),
            ),
            "train_rows": row.get("train_rows"),
            "inner_fit_rows": row.get("inner_fit_rows"),
            "inner_valid_rows": row.get("inner_valid_rows"),
            "prediction_rows": row.get(
                "prediction_rows",
                row.get("mz_secondary", {}).get("calibration", {}).get("prediction_rows"),
            ),
            "percentile_1": bounds.get("percentile_1"),
            "percentile_99": bounds.get("percentile_99"),
            "inner_percentile_1": inner_bounds.get("percentile_1"),
            "inner_percentile_99": inner_bounds.get("percentile_99"),
            "inner_lower_bound": inner_bounds.get("lower"),
            "inner_upper_bound": inner_bounds.get("upper"),
            "lower_bound": bounds.get("lower"),
            "upper_bound": bounds.get("upper"),
            "validation_prediction_rows": selected.get("prediction_rows"),
            "validation_count_low": selected.get("count_low"),
            "validation_count_high": selected.get("count_high"),
            "count_low": row.get("count_low"),
            "count_high": row.get("count_high"),
            "count_log_low": row.get("count_log_low"),
            "count_log_high": row.get("count_log_high"),
            "count_variance_floor": row.get("count_variance_floor"),
            "count_probability_low": row.get("count_probability_low"),
            "count_probability_high": row.get("count_probability_high"),
            "columns_kept": len(preprocessing["active_columns"])
            if "active_columns" in preprocessing
            else None,
            "columns_removed": len(preprocessing["removed_columns"])
            if "removed_columns" in preprocessing
            else None,
            "removed_columns_detail": json.dumps(preprocessing.get("removed_columns")),
            "inner_removed_columns_detail": json.dumps(
                row.get("preprocessing", {}).get("inner_fit", {}).get("removed_columns")
            ),
            "winsor_metadata_available": bool(winsor),
            "single_class_inner_fit": row.get("single_class_inner_fit"),
            "single_class_refit": row.get(
                "single_class_refit", row.get("solver_refit", {}).get("single_class_training")
            ),
            "solver_refit_iterations": row.get("solver_refit", {}).get("iterations"),
            "solver_refit_converged": row.get("solver_refit", {}).get("converged"),
            "winsor_train_low_entries": sum(r["count_low"] for r in winsor.get("training", []))
            if winsor
            else None,
            "winsor_train_high_entries": sum(r["count_high"] for r in winsor.get("training", []))
            if winsor
            else None,
            "winsor_prediction_low_entries": sum(
                r["count_low"] for r in winsor.get("predicting", [])
            )
            if winsor
            else None,
            "winsor_prediction_high_entries": sum(
                r["count_high"] for r in winsor.get("predicting", [])
            )
            if winsor
            else None,
        }
        normalized.append(item)
        if endpoint == "mean" and family == "lightgbm_qlike":
            calibration = row.get("mz_secondary", {}).get("calibration")
            if calibration is None:
                raise ValueError("RP4_V3_REPORT_MZ_DIAGNOSTICS_MISSING")
            days = calibration["calibration_sessions"]
            if days and (
                max(days) >= row["session"] or calibration["inner_fit_last_session"] >= min(days)
            ):
                raise ValueError("RP4_V3_REPORT_MZ_CALIBRATION_NOT_TRAIN_ONLY")
            calibrations.append(
                {
                    "window": window,
                    "session": row["session"],
                    "information_set": name,
                    "intercept": calibration["applied_coefficients"]["intercept"],
                    "slope": calibration["applied_coefficients"]["slope"],
                    "attempted_intercept": calibration.get("attempted_coefficients", {}).get(
                        "intercept"
                    ),
                    "attempted_slope": calibration.get("attempted_coefficients", {}).get("slope"),
                    "rank": calibration.get("rank"),
                    "calibration_sessions": json.dumps(days),
                    "inner_fit_last_session": calibration["inner_fit_last_session"],
                    "selected_num_leaves": calibration.get("selected_num_leaves"),
                    "selected_rounds": calibration.get("selected_rounds"),
                    "N_calibration_sessions": calibration["N_sessions"],
                    "training_identity_fallback": calibration["training_identity_fallback"],
                    "training_fallback_reason": calibration["training_fallback_reason"],
                    "origin_identity_fallback_count": calibration["origin_identity_fallback_count"],
                    "count_floor": calibration["count_floor"],
                    "prediction_rows": calibration["prediction_rows"],
                }
            )
    if not required <= seen:
        raise ValueError("RP4_V3_REPORT_PRIMARY_FITS_INCOMPLETE")
    return normalized, calibrations


def winsor_diagnostics(records: Rows, window: str) -> Rows:
    totals: dict[tuple[str, str, str, str], dict[str, Any]] = {}
    for fit in records:
        for phase in ("inner_fit", "refit"):
            preprocessing = fit.get("preprocessing", {}).get(phase, {})
            for partition, entries in preprocessing.get("winsorization", {}).items():
                if partition not in ("training", "predicting"):
                    continue
                for entry in entries:
                    key = (fit["model"], phase, partition, entry["column"])
                    aggregate = totals.setdefault(
                        key,
                        {
                            "window": window,
                            "model": fit["model"],
                            "fit_phase": phase,
                            "partition": partition,
                            "column": entry["column"],
                            "count_low": 0,
                            "count_high": 0,
                            "N_fit_records": 0,
                        },
                    )
                    aggregate["count_low"] += entry["count_low"]
                    aggregate["count_high"] += entry["count_high"]
                    aggregate["N_fit_records"] += 1
    return [totals[key] for key in sorted(totals)]


def bound_summary(fits: Rows) -> Rows:
    """Do not turn absent hit counters into zeros; preserve phase-specific denominators."""
    output = []
    for window in WINDOWS:
        for endpoint in ("mean", "quantile", "jump"):
            for family in inf.FAMILIES:
                for name in inf.SETS:
                    rows = [
                        r
                        for r in fits
                        if (r["window"], r["endpoint"], r["family"], r["information_set"])
                        == (window, endpoint, family, name)
                    ]
                    bounded_ridge = family == "log_ridge_harq" and endpoint != "jump"
                    phases = ("validation", "evaluation") if bounded_ridge else ("evaluation",)
                    for phase in phases:
                        if phase == "validation":
                            low, high, denominator, kind = (
                                "validation_count_low",
                                "validation_count_high",
                                "validation_prediction_rows",
                                "percentile_bounds",
                            )
                        else:
                            low, high = (
                                ("count_low", "count_high")
                                if bounded_ridge
                                else (
                                    ("count_probability_low", "count_probability_high")
                                    if endpoint == "jump"
                                    else ("count_log_low", "count_log_high")
                                )
                            )
                            denominator = "prediction_rows"
                            kind = (
                                "percentile_bounds"
                                if bounded_ridge
                                else "probability_clip"
                                if endpoint == "jump"
                                else "log_clip"
                            )
                        known = bool(rows) and all(
                            r.get(key) is not None for r in rows for key in (low, high, denominator)
                        )
                        n = sum(int(r[denominator]) for r in rows) if known else None
                        low_total = sum(int(r[low]) for r in rows) if known else None
                        high_total = sum(int(r[high]) for r in rows) if known else None
                        if known and any(
                            any(
                                float(r[key]) < 0 or float(r[key]) != int(r[key])
                                for key in (low, high, denominator)
                            )
                            or int(r[low]) + int(r[high]) > int(r[denominator])
                            for r in rows
                        ):
                            raise ValueError("RP4_V3_REPORT_BOUND_HITS_EXCEED_PREDICTIONS")
                        output.append(
                            {
                                "window": window,
                                "endpoint": endpoint,
                                "family": family,
                                "information_set": name,
                                "phase": phase,
                                "kind": kind,
                                "N_fit_records": len(rows),
                                "N_predictions": n,
                                "count_low": low_total,
                                "count_high": high_total,
                                "percent_low": 100 * low_total / n
                                if n and low_total is not None
                                else None,
                                "percent_high": 100 * high_total / n
                                if n and high_total is not None
                                else None,
                                "status": "COMPUTED" if known else "NO VERIFICABLE",
                            }
                        )
    return output


def empty_census_comparison(raw: Rows, windows: Comparison) -> Rows:
    """Compare all scheduled panel rows with scored rows, matching asset/session/horizon."""
    output = []
    keys = [(r["asset"], r["session_date"]) for r in raw]
    if len(keys) != len(set(keys)):
        raise ValueError("RP4_V3_REPORT_RAW_CENSUS_DUPLICATE")
    for window in WINDOWS:
        summary = windows["v3"][window][0]
        dates = {name.removesuffix(".json") for name in summary["completed_session_sha256"]}
        dates.update(r["session"] for r in summary["skipped_sessions"])
        evaluated = {
            (r["asset"], r["session_date"], r["horizon"]): r
            for r in summary["empty_window_secondary"]["census_by_session"]
        }
        seen = set()
        for row in raw:
            if row["session_date"] not in dates:
                continue
            for horizon in ("5m", "30m"):
                key = (row["asset"], row["session_date"], horizon)
                seen.add(key)
                actual = evaluated.get(key, {})
                available = int(row["N_origins"])
                empty = int(row[f"b2_{horizon}_window_empty_count"])
                unknown = int(row[f"b2_{horizon}_window_empty_unknown"])
                nonempty = available - empty - unknown
                values = {
                    name: int(actual.get(name, 0))
                    for name in (
                        "N_origins",
                        "N_empty_origins",
                        "N_nonempty_origins",
                        "N_unknown_origins",
                    )
                }
                if (
                    min(available, empty, unknown, nonempty, *values.values()) < 0
                    or any(
                        values[name] > total
                        for name, total in (
                            ("N_origins", available),
                            ("N_empty_origins", empty),
                            ("N_nonempty_origins", nonempty),
                            ("N_unknown_origins", unknown),
                        )
                    )
                    or values["N_origins"]
                    != sum(
                        values[name]
                        for name in ("N_empty_origins", "N_nonempty_origins", "N_unknown_origins")
                    )
                ):
                    raise ValueError("RP4_V3_REPORT_RAW_VS_EXECUTED_CENSUS_ACCOUNTING")
                output.append(
                    {
                        "window": window,
                        "asset": row["asset"],
                        "session_date": row["session_date"],
                        "horizon": horizon,
                        "available_origins": available,
                        "available_empty": empty,
                        "available_nonempty": nonempty,
                        "available_unknown": unknown,
                        **{"executed_" + k: v for k, v in values.items()},
                    }
                )
        if not set(evaluated) <= seen:
            raise ValueError("RP4_V3_REPORT_EXECUTED_CENSUS_WITHOUT_RAW_SOURCE")
    return output


def unchanged_lgb_parity(windows: Comparison) -> Rows:
    """Verify unchanged B0/B1 series by session, without recomputing a forecast."""
    output = []
    for window in WINDOWS:
        old = {r["session_date"]: r for r in windows["v2"][window][1]}
        new = {r["session_date"]: r for r in windows["v3"][window][1]}
        if set(old) != set(new):
            raise ValueError("RP4_V3_REPORT_UNCHANGED_LGB_SESSION_SET_DRIFT")
        for name in ("B0", "B1"):
            for value in ("loss", "forecast"):
                column = f"{value}__lightgbm_qlike__{name}"
                differences = [
                    abs(float(old[day][column]) - float(new[day][column])) for day in sorted(old)
                ]
                if not differences or not all(math.isfinite(x) for x in differences):
                    raise ValueError("RP4_V3_REPORT_UNCHANGED_LGB_NONFINITE")
                maximum = max(differences)
                row = {
                    "window": window,
                    "column": column,
                    "N_sessions": len(differences),
                    "maximum_absolute_difference": maximum,
                    "exact": maximum == 0,
                }
                if maximum != 0:
                    raise ValueError("RP4_V3_REPORT_UNCHANGED_LGB_PARITY_DRIFT:" + json.dumps(row))
                output.append(row)
    return output


def raw_census_table(comparison: Rows | None, spec: dict[str, Any], window: str) -> str:
    if comparison is None:
        return ""
    rows = []
    for horizon in ("5m", "30m"):
        for asset in spec["assets"]:
            selected = [
                r
                for r in comparison
                if (r["window"], r["asset"], r["horizon"]) == (window, asset, horizon)
            ]
            rows.append(
                [
                    horizon,
                    asset,
                    *[
                        str(sum(r[k] for r in selected))
                        for k in (
                            "available_origins",
                            "available_empty",
                            "available_unknown",
                            "executed_N_origins",
                            "executed_N_empty_origins",
                            "executed_N_unknown_origins",
                        )
                    ],
                ]
            )
    return "\n\n".join(
        [
            "Censo fuente frente a la muestra evaluada, mismas sesiones programadas:",
            table(
                [
                    "Horizonte",
                    "Activo",
                    "Fuente orígenes",
                    "Fuente vacíos",
                    "Fuente desconocidos",
                    "Evaluados",
                    "Evaluados vacíos",
                    "Evaluados desconocidos",
                ],
                rows,
            ),
            "[Censo por activo, sesión y horizonte]"
            "(../../artifacts/rp4_v3_b4/empty_window_census.csv). "
            "Las primeras 60 sesiones de entrenamiento no cuentan como evaluación primaria. "
            "[Conversiones a NaN por columna](../../artifacts/rp4_v3_b4/empty_window_recode.csv).",
        ]
    )


def cumulative_figure(windows: Comparison, contrast: str, base: str, richer: str) -> str:
    """Twelve exact cumulative series, independently labelled scales; no tail clipping."""
    width, height = 1670, 1510
    content = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 '
        f'{width} {height}" role="img">',
        f"<title>RP4 v1/v2/v3: {html.escape(contrast)}</title>",
        "<desc>Doce paneles, escalas independientes. Suma de QLIKE base menos ampliado; positivo "
        "favorece al conjunto rico.</desc>",
        '<rect width="100%" height="100%" fill="white"/>',
        '<g font-family="Segoe UI,Arial,sans-serif" fill="#1a2332">',
        f'<text x="52" y="43" font-size="25">RP4 v1 / v2 / v3 · {richer} sobre {base}</text>',
        '<text x="52" y="72" font-size="14">Suma de [QLIKE base − ampliado]. Escala '
        "independiente por panel; todas las sesiones y extremos.</text>",
    ]
    for column, version in enumerate(VERSIONS):
        for wi, window in enumerate(WINDOWS):
            for fi, family in enumerate(FAMILIES[version]):
                rows = windows[version][window][1]
                curve = [0.0, *accumulate(differences(rows, family, base, richer))]
                left, right = 92 + column * 548, 518 + column * 548
                top, bottom = 167 + 334 * (2 * wi + fi), 398 + 334 * (2 * wi + fi)
                low, high = min(curve), max(curve)
                padding = 0.08 * (high - low) if high > low else 1.0
                low, high = low - padding, high + padding

                def y(
                    value: float,
                    low: float = low,
                    high: float = high,
                    top: int = top,
                    bottom: int = bottom,
                ) -> float:
                    return bottom - (value - low) * (bottom - top) / (high - low)

                label = f"{version} · {WINDOWS[window]} · {'Lineal' if fi == 0 else 'LightGBM'}"
                content += [
                    f'<text x="{left}" y="{top - 37}" font-size="16">{html.escape(label)}</text>',
                    f'<text x="{left}" y="{top - 16}" font-size="12">{len(rows)} sesiones · '
                    f"final {curve[-1]:+.8g}</text>",
                ]
                for index in range(5):
                    value = low + (high - low) * index / 4
                    content += [
                        f'<line x1="{left}" x2="{right}" y1="{y(value):.2f}" y2="{y(value):.2f}" '
                        f'stroke="#e1e6ea"/>',
                        f'<text x="{left - 8}" y="{y(value) + 4:.2f}" text-anchor="end" '
                        f'font-size="11">{value:.4g}</text>',
                    ]
                content.append(
                    f'<line x1="{left}" x2="{right}" y1="{y(0):.2f}" y2="{y(0):.2f}" '
                    f'stroke="#5a6570" stroke-dasharray="4 4"/>'
                )
                days = [date.fromisoformat(r["session_date"]).toordinal() for r in rows]
                times = [days[0] - 1, *days]
                path = " ".join(
                    f"{'M' if i == 0 else 'L'} "
                    f"{left + (right - left) * (day - times[0]) / (times[-1] - times[0]):.2f} "
                    f"{y(value):.2f}"
                    for i, (day, value) in enumerate(zip(times, curve, strict=True))
                )
                color = {"v1": "#5a6570", "v2": "#1a2332", "v3": "#d58718"}[version]
                content.append(
                    f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2" '
                    f'data-version="{version}" data-window="{window}" data-family="{family}" '
                    f'data-endpoint="{curve[-1]:.17g}" data-sessions="{len(rows)}"/>'
                )
                content += [
                    f'<text x="{left}" y="{bottom + 23}" '
                    f'font-size="12">{rows[0]["session_date"]}</text>',
                    f'<text x="{right}" y="{bottom + 23}" text-anchor="end" '
                    f'font-size="12">{rows[-1]["session_date"]}</text>',
                ]
    return "\n".join(content + ["</g></svg>", ""])


def _inference_table(records: Rows, *, p_label: str = "p nominal") -> str:
    return table(
        ["Familia", "Contraste", "Delta", "IC95%", p_label, "p Holm", "N sesiones", "Estado"],
        [
            [
                family_label(r.get("family", "lightgbm_qlike"), r.get("endpoint", "qlike_mean")),
                r.get("contrast", ""),
                number(r.get("estimate"), signed=True),
                f"[{number(r.get('ci_low'))}, {number(r.get('ci_high'))}]",
                number(r.get("p_raw")),
                number(r.get("p_holm")) if "p_holm" in r else "no aplica",
                str(r.get("N_sessions", "NO VERIFICABLE")),
                str(r.get("hypothesis_status", r.get("status", "NO VERIFICABLE"))),
            ]
            for r in records
        ],
    )


def comparison_table(windows: Comparison, window: str) -> str:
    columns = ["Delta", "IC95%", "p bilateral", "Holm", "Reducción %", "N sesiones", "N orígenes"]
    output = []
    for index in range(2):
        for contrast, _, _ in inf.CONTRASTS:
            row = ["Lineal OLS v1 / ridge v2–v3" if index == 0 else "LightGBM QLIKE", contrast]
            for version in VERSIONS:
                summary = windows[version][window][0]
                records = (
                    summary["comparability_bilateral"] if version == "v3" else summary["contrasts"]
                )
                r = next(
                    r
                    for r in records
                    if (r["family"], r["contrast"]) == (FAMILIES[version][index], contrast)
                )
                row += [
                    number(r["estimate"], signed=True),
                    f"[{number(r.get('ci_low'))}, {number(r.get('ci_high'))}]",
                    number(r.get("p_raw")),
                    number(r.get("p_holm")),
                    number(r.get("qlike_reduction_percent"), signed=True),
                    str(r["N_sessions"]),
                    str(r["N_origins"]),
                ]
            output.append(row)
    return table(["Familia", "Contraste"] + [f"{v} {c}" for v in VERSIONS for c in columns], output)


def render_report(
    windows: Comparison,
    spec: dict[str, Any],
    fits: Rows,
    mz_fits: Rows,
    materialization: dict[str, Any],
    empty_comparison: Rows | None = None,
    baseline_parity: Rows | None = None,
) -> str:
    parts = [
        "# RP4 — resultados v3 y comparación v1/v2",
        "",
        spec["label"] + ".",
        "",
        "RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.",
        "",
        "Delta QLIKE = pérdida base menos ampliada: positivo favorece B1 sobre B0 o B2 sobre B1. "
        "Cada activo pesa igual dentro de su sesión y cada sesión pesa igual. Reducción % = 100 "
        "× media(delta) / media(pérdida base).",
        "",
        "La decisión primaria v3 es unilateral: H1 y luego H2, alfa 0,05 por familia y ventana; "
        "la conjunción exige ambas hipótesis en ambas familias. Un H2 no abierto conserva su p "
        "nominal "
        "sólo como diagnóstico no promovible. El IC95% es percentil bilateral, no la inversión "
        "de esa prueba unilateral.",
        "",
        "La tabla comparable mantiene p bilaterales y Holm de cuatro contrastes; no es la regla "
        "decisoria v3. "
        "Los secundarios, la recalibración MZ y una familia favorable no rescatan una conjunción "
        "primaria fallida. "
        "El bootstrap circular usa bloques de cinco sesiones, 9.999 réplicas y semilla 20260907.",
    ]
    for window, label in WINDOWS.items():
        summary, _ = windows["v3"][window]
        outcome = (
            "SATISFECHA EN ESTA VENTANA"
            if summary["primary_sequence"]["global_joint_reject"]
            else "NO SATISFECHA EN ESTA VENTANA"
        )
        parts += [
            "",
            f"## {label}",
            "",
            f"Conjunción primaria registrada: **{outcome}**. "
            "Esto describe el criterio de esta especificación, no una garantía de edge "
            "financiero ni estabilidad universal.",
            "",
            comparison_table(windows, window),
            "",
            "### Decisión unilateral v3",
            "",
            _inference_table(summary["contrasts"], p_label="p unilateral nominal"),
            "",
            table(
                ["Familia", "Contraste", "p formal", "Uso del p nominal", "Rechazo"],
                [
                    [
                        r["family"],
                        r["contrast"],
                        number(r["p_for_decision"]),
                        r["nominal_p_role"],
                        str(r["rejected"]),
                    ]
                    for r in summary["contrasts"]
                ],
            ),
            "",
            "### Cobertura de orígenes por activo",
            "",
        ]
        coverage = []
        for asset in spec["assets"]:
            row = [asset]
            for version in VERSIONS:
                current = windows[version][window][0]
                r = next(r for r in current["evaluation_quality_by_asset"] if r["asset"] == asset)
                row += [
                    str(r["scheduled_rows"]),
                    str(r["eligible_rows"]),
                    number(100 * r["eligible_rows"] / r["scheduled_rows"])
                    if r["scheduled_rows"]
                    else "NO VERIFICABLE",
                ]
            row.append(
                str(summary.get("executed_origins_by_asset", {}).get(asset, "NO VERIFICABLE"))
            )
            coverage.append(row)
        parts += [
            table(
                ["Activo"]
                + [f"{v} {c}" for v in VERSIONS for c in ("programados", "elegibles", "%")]
                + ["v3 ejecutados"],
                coverage,
            ),
            "",
        ]
        for version in VERSIONS:
            current = windows[version][window][0]
            skipped = (
                "; ".join(f"{r['session']}: {r['reason']}" for r in current["skipped_sessions"])
                or "ninguna"
            )
            parts += [
                f"{version}: {current['N_sessions']} sesiones ejecutadas / "
                f"{current['scheduled_sessions']} programadas; "
                f"{current['first_session']}–{current['last_session']}. Omitidas: {skipped}.",
                "",
            ]
        parts += [
            "La columna de compuerta opcional rp4_eligible "
            + (
                "está ausente: se conserva el fallback heredado; no se afirma haber aplicado una "
                "compuerta nueva."
                if summary.get("quality_gate_column_present") is False
                else "está presente."
                if summary.get("quality_gate_column_present") is True
                else "es NO VERIFICABLE."
            ),
            "",
            "### Mediana, recortada y probabilidad condicional",
            "",
            "Mediana de diferencias no equivale a diferencia de medianas. El recorte elimina "
            "floor(0,05 N) "
            "sesiones por cada cola sólo para ese secundario; ningún día sale de la media "
            "primaria.",
        ]
        for statistic, title in (
            ("median", "Mediana pareada"),
            ("trimmed_mean_5pct", "Media recortada 5% por cola"),
        ):
            parts += [
                "",
                f"{title}:",
                "",
                _inference_table(
                    [r for r in summary["distribution_secondary"] if r["statistic"] == statistic],
                    p_label="p bilateral",
                ),
            ]
        parts += [
            "",
            table(
                ["Familia", "Contraste", "P(delta>0)", "HAC SE", "N", "Estado"],
                [
                    [
                        r["family"],
                        r["contrast"],
                        number(r.get("probability_positive")),
                        number(r.get("HAC_SE")),
                        str(r["N_sessions"]),
                        r["status"],
                    ]
                    for r in summary["posterior_mean"]
                ],
            ),
            "",
            "P(delta>0) es una aproximación gaussiana condicional: verosimilitud de la media con "
            "varianza HAC5/N "
            "plug-in y prior plano. Requiere CLT de la media, dependencia de memoria corta y "
            "varianza finita; "
            "no integra incertidumbre de la varianza ni es frecuencia de signos del bootstrap.",
            "",
            "### Cuantil 0,90 de log(RV30)",
            "",
            _inference_table(
                summary["quantile_secondary"]["contrasts"], p_label="p unilateral secundario"
            ),
            "",
            table(
                ["Familia", "Conjunto", "Pérdida pinball media"],
                [
                    [
                        family_label(r["family"], "quantile"),
                        r["information_set"],
                        number(r["mean_pinball"]),
                    ]
                    for r in summary["quantile_secondary"]["model_losses"]
                ],
            ),
            "",
            "### Salto: AUC fuera de muestra",
            "",
            "AUC agrupada por origen, peso uno, empates 0,5; mejora = AUC rica − AUC base. El "
            "remuestreo "
            "duplica sesiones enteras y conserva comparaciones entre ellas. Una réplica "
            "monoclase hace "
            "NO VERIFICABLES todos sus IC/p; no se redibuja ni se descarta silenciosamente.",
            "",
            table(
                [
                    "Familia",
                    "Conjunto",
                    "AUC",
                    "IC95%",
                    "Réplicas monoclase",
                    "N sesiones",
                    "N orígenes",
                    "Estado",
                ],
                [
                    [
                        family_label(family["family"], "jump"),
                        name,
                        number(r.get("estimate")),
                        f"[{number(r.get('ci_low'))}, {number(r.get('ci_high'))}]",
                        str(family["invalid_class_resamples"]),
                        str(family["N_sessions"]),
                        str(family["N_origins"]),
                        r["status"],
                    ]
                    for family in summary["jump_secondary"]["families"]
                    for name, r in family["auc"].items()
                ],
            ),
            "",
            _inference_table(
                summary["jump_secondary"]["contrasts"], p_label="p unilateral secundario"
            ),
        ]
        for section in ("quantile_secondary", "jump_secondary"):
            r = summary[section]
            excluded = (
                "; ".join(f"{e['session']}: {e['reason']}" for e in r["excluded_sessions"])
                or "ninguna"
            )
            parts += [
                "",
                f"{section}: N={r['N_sessions']} sesiones, {r['N_origins']} orígenes. "
                f"Sesiones excluidas únicamente de este endpoint: {excluded}.",
            ]
        parts += [
            "",
            "### MZ: recalibración secundaria sólo LightGBM",
            "",
            table(
                [
                    "Conjunto",
                    "QLIKE original",
                    "QLIKE recalibrado",
                    "Mejora por recalibración",
                    "Reducción %",
                    "N sesiones",
                    "N orígenes",
                ],
                [
                    [
                        r["information_set"],
                        number(r["raw_qlike"]),
                        number(r["recalibrated_qlike"]),
                        number(r["calibration_improvement"], signed=True),
                        number(r["calibration_reduction_percent"], signed=True),
                        str(r["N_sessions"]),
                        str(r["N_origins"]),
                    ]
                    for r in summary["mz_secondary"]["model_losses"]
                ],
            ),
            "",
            _inference_table(
                summary["mz_secondary"]["contrasts"], p_label="p bilateral nominal secundario"
            ),
            "",
            "La calibración usa diez medias de validación predichas por el candidato entrenado "
            "antes de ellas, "
            "no valores ajustados del refit. No reemplaza los pronósticos primarios. "
            "[Coeficientes y fallbacks por sesión](../../artifacts/rp4_v3_b4/mz_calibration.csv).",
            "",
            "### Ventanas de flujo vacías",
            "",
            table(
                ["Horizonte", "Activo", "Orígenes", "Vacíos", "No vacíos", "Desconocidos"],
                [
                    [
                        r["horizon"],
                        r["asset"],
                        *[
                            str(r[k])
                            for k in (
                                "N_origins",
                                "N_empty_origins",
                                "N_nonempty_origins",
                                "N_unknown_origins",
                            )
                        ],
                    ]
                    for r in summary["empty_window_secondary"]["census"]
                ],
            ),
            "",
            table(
                [
                    "Grupo",
                    "Familia",
                    "Delta B2/B1",
                    "IC95%",
                    "p bilateral",
                    "Holm4",
                    "N sesiones",
                    "N orígenes",
                ],
                [
                    [
                        r["subset"],
                        r["family"],
                        number(r["estimate"], signed=True),
                        f"[{number(r.get('ci_low'))}, {number(r.get('ci_high'))}]",
                        number(r.get("p_raw")),
                        number(r.get("p_holm")),
                        str(r["N_sessions"]),
                        str(r["N_origins"]),
                    ]
                    for r in summary["empty_window_secondary"]["contrasts"]
                    if r["statistic"] == "mean"
                ],
            ),
            "",
            "Membresía desconocida no equivale a ventana no vacía. Medianas, recortadas, IC y "
            "estados completos "
            "se conservan en el CSV de regímenes; ceros de actividad no se confunden con formas "
            "observadas.",
            "",
            raw_census_table(empty_comparison, spec, window),
            "",
            "### Regímenes, interacción gamma y días extremos",
            "",
            table(
                [
                    "Grupo",
                    "Familia",
                    "Contraste",
                    "Media Δ",
                    "Mediana Δ",
                    "Recortada Δ",
                    "N sesiones",
                    "N desconocidos",
                ],
                [
                    [
                        r["subset"],
                        r["family"],
                        r["contrast"],
                        number(r["estimate"], signed=True),
                        *[
                            number(
                                next(
                                    x["estimate"]
                                    for x in summary["regime_secondary"]
                                    if (x["subset"], x["family"], x["contrast"], x["statistic"])
                                    == (r["subset"], r["family"], r["contrast"], statistic)
                                ),
                                signed=True,
                            )
                            for statistic in ("median", "trimmed_mean_5pct")
                        ],
                        str(r["N_sessions"]),
                        str(r["N_unknown_membership_origins"]),
                    ]
                    for r in summary["regime_secondary"]
                    if r["statistic"] == "mean"
                    and r["subset"]
                    in (
                        "first_hour",
                        "last_hour",
                        "high_flow",
                        "event",
                        "weekly_expiration",
                        "third_friday",
                        "high_gamma",
                    )
                ],
            ),
            "",
            "Alto flujo hereda el umbral aprendido con la máscara original v1, como v2. Alto "
            "gamma usa "
            "sólo el umbral del entrenamiento previo del mismo activo. Alto gamma menos resto "
            "compara "
            "incrementos en activo-sesiones con ambos grupos conocidos, luego promedia por sesión; "
            "no compara muestras temporales distintas ni rellena un grupo ausente.",
            "",
            _inference_table(
                [r for r in summary["high_gamma_vs_rest"] if r["statistic"] == "mean"],
                p_label="p bilateral interacción",
            ),
            "",
            f"[Todos los regímenes, activos, bloques, leave-one-block-out y últimas 30 sesiones: "
            f"medias, medianas, recortadas e IC]"
            f"(../../artifacts/rp4_v3_b4/regimes_{window}.csv). "
            f"[Interacción gamma "
            f"completa](../../artifacts/rp4_v3_b4/high_gamma_vs_rest_{window}.csv). "
            f"[Diez días de mayor pérdida de cada modelo, con signos de ambos "
            f"contrastes](../../artifacts/rp4_v3_b4/top_loss_{window}.csv).",
            "",
            "### Diagnósticos DM, GW y MZ",
            "",
            table(
                ["Familia", "Contraste", "DM", "p DM", "GW", "p GW"],
                [
                    [
                        r["family"],
                        r["contrast"],
                        *[
                            number(r.get(k))
                            for k in (
                                "dm_hac_statistic",
                                "dm_hac_p_two_sided",
                                "gw_hac_diagnostic_statistic",
                                "gw_hac_diagnostic_p",
                            )
                        ],
                    ]
                    for r in summary["comparability_bilateral"]
                ],
            ),
            "",
            table(
                ["Modelo", "Intercepto", "Pendiente", "p a=0,b=1", "Estado"],
                [
                    [
                        name,
                        number(r.get("intercept")),
                        number(r.get("slope")),
                        number(r.get("joint_a0_b1_hac_p")),
                        r["status"],
                    ]
                    for name, r in summary["mincer_zarnowitz"].items()
                ],
            ),
            "",
            "DM y GW conservan exactamente el diagnóstico asintótico HAC de v2; GW no adquiere "
            "la garantía del diseño original con memoria fija. MZ evalúa medias de sesión en "
            "niveles.",
        ]
    parts += [
        "",
        "## Selección y estabilidad numérica",
        "",
        "Ridge estandariza con entrenamiento, winsoriza a ±5 SD y usa cotas RV30 [0,5 × p1; 2 × "
        "p99] "
        "del entrenamiento correspondiente. No se winsoriza RV30 ni la pérdida observada. "
        "[Rondas, lambda y cotas por "
        "sesión/endpoint](../../artifacts/rp4_v3_b4/fit_selection.csv).",
        "",
    ]
    selection = []
    for window in WINDOWS:
        for endpoint in ("mean", "quantile", "jump"):
            for family in inf.FAMILIES:
                for name in inf.SETS:
                    rows = [
                        r
                        for r in fits
                        if (r["window"], r["endpoint"], r["family"], r["information_set"])
                        == (window, endpoint, family, name)
                    ]
                    choice = "selected_lambda" if family == "log_ridge_harq" else "selected_rounds"
                    values = [r[choice] for r in rows if r[choice] is not None]
                    counts = Counter(values)
                    text = (
                        "; ".join(f"{k:g}:{v}" for k, v in sorted(counts.items()))
                        if choice == "selected_lambda"
                        else (
                            f"mín {min(values)}; mediana {statistics.median(values):g}; máx "
                            f"{max(values)}; tope 2000: {counts[2000]}"
                            if values
                            else "NO VERIFICABLE"
                        )
                    )
                    selection.append(
                        [
                            window,
                            endpoint,
                            family,
                            name,
                            str(len(rows)),
                            text or "NO VERIFICABLE",
                        ]
                    )
    parts += [
        table(
            [
                "Ventana",
                "Endpoint",
                "Familia",
                "Conjunto",
                "Registros",
                "Lambda/rondas",
            ],
            selection,
        ),
        "",
        table(
            [
                "Ventana",
                "Endpoint",
                "Familia",
                "Conjunto",
                "Fase",
                "Acotamiento",
                "N predicciones",
                "Cota baja",
                "% baja",
                "Cota alta",
                "% alta",
            ],
            [
                [
                    r["window"],
                    r["endpoint"],
                    r["family"],
                    r["information_set"],
                    r["phase"],
                    r["kind"],
                    number(r["N_predictions"]),
                    number(r["count_low"]),
                    number(r["percent_low"]),
                    number(r["count_high"]),
                    number(r["percent_high"]),
                ]
                for r in bound_summary(fits)
            ],
        ),
        "",
        "Los porcentajes usan las predicciones de su propia fase: validación del candidato "
        "seleccionado o evaluación del refit. No se imputan contadores ausentes como cero. "
        "P1/P99, L/U de inner_fit y refit, N y columnas eliminadas se conservan por sesión en "
        "el CSV de selección. [Resumen de cotas](../../artifacts/rp4_v3_b4/bound_counts.csv). "
        "[Winsorización por columna, fase y partición]"
        "(../../artifacts/rp4_v3_b4/winsor_counts.csv): "
        "suma de aplicaciones a través de ajustes; un dato histórico puede aparecer varias veces. "
        "El detalle por sesión sigue vinculado en los diagnósticos de ajuste originales.",
        "",
        table(
            ["Ventana", "Conjunto", "Fallback entrenamiento", "Fallback orígenes", "Piso MZ"],
            [
                [
                    window,
                    name,
                    str(
                        sum(
                            bool(r["training_identity_fallback"])
                            for r in mz_fits
                            if r["window"] == window and r["information_set"] == name
                        )
                    ),
                    str(
                        sum(
                            r["origin_identity_fallback_count"]
                            for r in mz_fits
                            if r["window"] == window and r["information_set"] == name
                        )
                    ),
                    str(
                        sum(
                            r["count_floor"]
                            for r in mz_fits
                            if r["window"] == window and r["information_set"] == name
                        )
                    ),
                ]
                for window in WINDOWS
                for name in inf.SETS
            ],
        ),
        "",
        "## Derivación y custodia de los datos",
        "",
        table(
            ["Ventana", "Serie LightGBM B0/B1 sin cambiar", "N", "Máx. diferencia v2/v3"],
            [
                [
                    r["window"],
                    r["column"],
                    str(r["N_sessions"]),
                    number(r["maximum_absolute_difference"]),
                ]
                for r in (baseline_parity or [])
            ],
        ),
        "",
        "La paridad anterior se verifica por fecha sobre pérdidas y pronósticos de sesión; "
        "no se presupone a partir del nombre del modelo ni requiere reajustarlo.",
        "",
        "[Comparación por columna: candidato, derivación independiente y puentes de IV/causalidad]"
        "(../../artifacts/rp4_v3_b4/gamma_comparison.csv). "
        "[Cobertura de gamma/jump](../../artifacts/rp4_v3_b4/gamma_coverage.csv). "
        "[Conteos de IV, duplicados y "
        "disponibilidad](../../artifacts/rp4_v3_b4/materialization_counts.csv). "
        "Estas son auditorías de construcción, no modelos elegidos por su resultado.",
        "",
        "[Cierre A2: atribución de las discrepancias del candidato y regla de ventanas vacías]"
        "(../../artifacts/rp4_v3_a2/REPORT.md).",
        "",
        "Alineación RV30 reconstruida frente al panel conservado: "
        + json.dumps(
            materialization.get("rv30_alignment", {"status": "NO VERIFICABLE"}),
            sort_keys=True,
            ensure_ascii=False,
        )
        + ".",
        "",
        "## Evolución acumulada",
        "",
        "Cada figura conserva doce series (tres versiones × dos ventanas × dos familias), con "
        "escalas "
        "independientes y todos los valores adversos. El eje temporal usa fechas reales.",
        "",
        "![B1 sobre B0](../../artifacts/rp4_v3_b4/B1_over_B0.svg)",
        "",
        "![B2 sobre B1](../../artifacts/rp4_v3_b4/B2_over_B1.svg)",
        "",
        "## Fe de erratas heredada y divulgación",
        "",
        "En v1 sí entraban b2_5m_observed_span_s y b2_30m_observed_span_s; los otros siete "
        "diagnósticos "
        "señalados ya estaban excluidos, incluido b1_median_quote_age_s, al igual que "
        "b1_pcp_residual. "
        "Los dos observed_span salen en v2 y siguen fuera; los nuevos indicadores de ventana vacía "
        "están explícitamente autorizados por el addendum v3, no se presentan como existentes en "
        "v1.",
        "",
        "La ventana 20 de julio a 28 de agosto fue leída una vez por el puente de Fase 8 con "
        "otra especificación. "
        "El PIT es proxy de tiempo fuente a 120 s, como en la literatura.",
        "",
        "Hueco aceptado UW: 2025-01-25 a 2025-02-24, sin relleno. El desbalance gamma firmado es "
        "proxy "
        "de actividad de opciones, no inventario observado de dealers ni prueba causal sobre RV30.",
        "",
        "Limitación: v3 responde a resultados anteriores conocidos; fijar el código y ejecutar "
        "una vez "
        "no elimina selección adaptativa entre versiones, y ni Holm ni la secuencia dentro de "
        "una versión "
        "corrigen esa búsqueda ni convierten el tiempo fuente en disponibilidad histórica "
        "demostrada.",
        "",
        "Un contraste no rechazado no demuestra absorción de la información ni equivalencia a "
        "cero. "
        "No se repitieron v1/v2, no se ocultaron signos negativos y no se declara edge "
        "financiero garantizado.",
        "",
        "## Trazabilidad",
        "",
        "[Especificación original v3](specification_v3.md) · [Decisión 131](decision_131_v3.md) · "
        "[Informe v1 intacto](results_v1.md) · [Informe v2 intacto](results_v2.md) · "
        "[Manifiesto del informe y especificación "
        "efectiva](../../artifacts/rp4_v3_b4/report_manifest.json).",
        "",
        "Recibos con comandos, salidas y hashes: [A1](../../artifacts/rp4_v3_a1/receipt.json) · "
        "[A2](../../artifacts/rp4_v3_a2/receipt.json) · "
        "[B2](../../artifacts/rp4_v3_b2/receipt.json) · "
        "[B3](../../artifacts/rp4_v3_b3/receipt.json) · "
        "[B4](../../artifacts/rp4_v3_b4/receipt.json). "
        "El recibo B4 se emite después de salida 0 del generador para evitar un hash "
        "autorreferente.",
        "",
        "[Adición A1B: ventanas vacías](v3_window_empty_addendum.md) · "
        "[Decisión 132](decision_132_v3_empty_windows.md) · "
        "[Registro efectivo](../../artifacts/rp4_v3_a1_empty_window/specification.json) · "
        "[Recibo A1B](../../artifacts/rp4_v3_a1_empty_window/receipt.json).",
        "",
        "El generador valida recibos y hashes de agregados terminados; no ajusta modelos, no abre "
        "paneles por origen, no descarga datos, no activa colectores y no publica resultados.",
        "",
    ]
    return "\n".join(parts)


def run(args: argparse.Namespace) -> dict[str, Any]:
    if sha256(args.spec) != args.spec_sha256:
        raise ValueError("RP4_V3_REPORT_SPEC_HASH_MISMATCH")
    spec = read_json(args.spec)
    private_root = Path(spec["data_root"]).resolve()
    if spec.get("evaluation_panel_relative_path") != "materialized_empty_windows/panel.parquet":
        raise ValueError("RP4_V3_REPORT_EFFECTIVE_EMPTY_WINDOW_SPEC_REQUIRED")
    rule = spec["empty_window_addendum"]
    frozen_path = args.spec.parent / "freeze.json"
    frozen = read_json(frozen_path)
    document_pins = {
        ROOT / spec["specification_md_path"]: spec["specification_md_sha256"],
        ROOT / "docs/rp4/decision_131_v3.md": spec["decision_sha256"],
        ROOT / "docs/rp4/v3_addendum_stability_calibration.md": spec["addendum_sha256"],
        ROOT / rule["md_path"]: rule["md_sha256"],
        ROOT / rule["decision_path"]: rule["decision_sha256"],
        ROOT / "artifacts/rp4_v3_a1/specification.json": spec["original_v3_specification_sha256"],
        ROOT / "artifacts/rp4_v3_a1/freeze.json": frozen["original_v3_freeze_sha256"],
    }
    if frozen["specification_sha256"] != args.spec_sha256 or frozen["addendum"] != rule:
        raise ValueError("RP4_V3_REPORT_EFFECTIVE_FREEZE_DRIFT")
    for path, expected in document_pins.items():
        if not path.resolve().is_relative_to(ROOT.resolve()) or sha256(path) != expected:
            raise ValueError("RP4_V3_REPORT_REGISTERED_DOCUMENT_DRIFT")
    planned = [
        args.spec,
        frozen_path,
        *document_pins,
        Path(__file__),
        ROOT / "artifacts/rp4_v3_code/inference.py",
        ROOT / "artifacts/rp4_v2_b4/report_manifest.json",
        ROOT / "docs/rp4/results_v1.md",
        ROOT / "docs/rp4/results_v2.md",
        ROOT / "artifacts/rp4_v3_a2/evaluation_release.json",
        *[
            private_root / "materialized" / name
            for name in ("manifest.json", "comparison.csv", "coverage.csv", "counts.csv")
        ],
        *[
            private_root / "materialized_empty_windows" / name
            for name in ("manifest.json", "census.csv", "recode_audit.json")
        ],
    ]
    for version in VERSIONS:
        prefix = "rp4" if version == "v1" else f"rp4_{version}"
        for window, stage in (("primary", "b2"), ("confirmation", "b3")):
            directory = ROOT / "artifacts" / f"{prefix}_{stage}"
            planned.extend(directory / name for name in ("summary.json", "session_losses.csv"))
            if version == "v3":
                planned.extend(
                    [
                        directory / "receipt.json",
                        private_root / "evaluation" / window / "fit_diagnostics.json",
                    ]
                )
    # Capture all bytes BEFORE presenting any aggregates; changes during rendering fail closed.
    initial_sha = {p.resolve(): sha256(p) for p in planned}
    if initial_sha[args.spec.resolve()] != args.spec_sha256:
        raise ValueError("RP4_V3_REPORT_SPEC_CHANGED_BEFORE_READ")
    legacy_path = ROOT / "artifacts/rp4_v2_b4/report_manifest.json"
    if sha256(legacy_path) != LEGACY_MANIFEST_SHA:
        raise ValueError("RP4_V3_REPORT_LEGACY_CLOSURE_DRIFT")
    legacy = read_json(legacy_path)
    paths = [
        args.spec,
        frozen_path,
        *document_pins,
        legacy_path,
        Path(__file__),
        ROOT / "artifacts/rp4_v3_code/inference.py",
    ]
    for name in ("docs/rp4/results_v1.md", "docs/rp4/results_v2.md"):
        expected = legacy["inputs_sha256"].get(name, legacy["outputs_sha256"].get(name))
        if sha256(ROOT / name) != expected:
            raise ValueError("RP4_V3_REPORT_PREVIOUS_REPORT_CHANGED")
        paths.append(ROOT / name)
    windows: Comparison = {v: {} for v in VERSIONS}
    fits, mz_fits, winsor_rows = [], [], []
    release = ROOT / "artifacts/rp4_v3_a2/evaluation_release.json"
    paths.append(release)
    release_sha = sha256(release)
    release_data = read_json(release)
    for version in VERSIONS:
        prefix = "rp4" if version == "v1" else f"rp4_{version}"
        for window, stage in (("primary", "b2"), ("confirmation", "b3")):
            directory = ROOT / "artifacts" / f"{prefix}_{stage}"
            sources = [directory / "summary.json", directory / "session_losses.csv"]
            if version == "v3":
                fit_path = private_root / "evaluation" / window / "fit_diagnostics.json"
                receipt_path = directory / "receipt.json"
                receipt = validate_receipt(
                    receipt_path,
                    root=ROOT,
                    private_root=private_root,
                    stage=stage.upper(),
                    window=window,
                    required=[*sources, fit_path],
                )
                if receipt["release_sha256"] != release_sha:
                    raise ValueError("RP4_V3_REPORT_RELEASE_RECEIPT_DRIFT")
                paths.extend([receipt_path, fit_path])
                digest = args.spec_sha256
            else:
                for path in sources:
                    if sha256(path) != legacy["inputs_sha256"][path.relative_to(ROOT).as_posix()]:
                        raise ValueError("RP4_V3_REPORT_CLOSED_LEGACY_RESULT_DRIFT")
                digest = (
                    legacy["parent_specification_sha256"]
                    if version == "v1"
                    else legacy["specification_sha256"]
                )
            summary, rows = read_json(sources[0]), read_csv(sources[1])
            validate_window(summary, rows, version, window, digest)
            if summary["result_label"] != spec["label"]:
                raise ValueError("RP4_V3_REPORT_LABEL_DRIFT")
            windows[version][window] = summary, rows
            paths.extend(sources)
            if version == "v3":
                if summary["binding"]["release_sha256"] != release_sha:
                    raise ValueError("RP4_V3_REPORT_RESULT_RELEASE_DRIFT")
                if receipt["evaluation_code_sha256"] != summary["binding"]["code_sha256"]:
                    raise ValueError("RP4_V3_REPORT_RESULT_RECEIPT_CODE_DRIFT")
                fit_records = read_json(fit_path)
                selected, calibration = fit_diagnostics(
                    fit_records, [r["session_date"] for r in rows], window
                )
                fit_keys = {(r["session"], r["model"]) for r in fit_records}
                for endpoint in ("quantile", "jump"):
                    excluded = {
                        r["session"] for r in summary[endpoint + "_secondary"]["excluded_sessions"]
                    }
                    expected_keys = {
                        (r["session_date"], f"{endpoint}__{family}__{name}")
                        for r in rows
                        if r["session_date"] not in excluded
                        for family in inf.FAMILIES
                        for name in inf.SETS
                    }
                    if not expected_keys <= fit_keys:
                        raise ValueError("RP4_V3_REPORT_COMPLETED_TAIL_FITS_INCOMPLETE")
                fits.extend(selected)
                mz_fits.extend(calibration)
                winsor_rows.extend(winsor_diagnostics(fit_records, window))
    bindings = [windows["v3"][w][0]["binding"] for w in WINDOWS]
    baseline_parity = unchanged_lgb_parity(windows)
    if any(
        bindings[0][key] != bindings[1][key]
        for key in ("panel_sha256", "specification_sha256", "release_sha256", "code_sha256")
    ):
        raise ValueError("RP4_V3_REPORT_WINDOWS_DIFFERENT_CONTRACT")
    manifest_path = private_root / "materialized/manifest.json"
    effective_manifest_path = private_root / "materialized_empty_windows/manifest.json"
    materialized = read_json(manifest_path)
    recoded = read_json(effective_manifest_path)
    if any(
        windows["v3"][w][0]["materialization_manifest_sha256"] != sha256(effective_manifest_path)
        for w in WINDOWS
    ):
        raise ValueError("RP4_V3_REPORT_MATERIALIZATION_MANIFEST_DRIFT")
    gamma_pins = {Path(p).resolve(): digest for p, digest in materialized["artifacts"].items()}
    recode_pins = {Path(p).resolve(): digest for p, digest in recoded["artifacts"].items()}
    if (
        materialized["spec_sha256"] != spec["original_v3_specification_sha256"]
        or materialized["preserved_values_exact_by_keys"] is not True
        or recoded["spec_sha256"] != args.spec_sha256
        or recoded["source_gamma_manifest_sha256"] != sha256(manifest_path)
        or recoded["source_gamma_panel_sha256"]
        != gamma_pins.get((manifest_path.parent / "panel.parquet").resolve())
        or recoded["preserved_unaffected_values_exact_by_keys"] is not True
        or recoded["preserved_values_exact_by_keys"] is not False
        or recoded["changed_columns_only"] != rule["columns_to_nan"]
        or recoded["excluded_origins"] != 0
        or recoded["excluded_sessions"] != 0
        or recode_pins.get((effective_manifest_path.parent / "panel.parquet").resolve())
        != bindings[0]["panel_sha256"]
        or release_data["materialization_manifest_sha256"] != sha256(effective_manifest_path)
        or release_data["panel_sha256"] != bindings[0]["panel_sha256"]
        or release_data["specification_sha256"] != args.spec_sha256
    ):
        raise ValueError("RP4_V3_REPORT_GAMMA_RECODE_CHAIN_DRIFT")
    paths.extend([manifest_path, effective_manifest_path])
    public = ROOT / "artifacts/rp4_v3_b4"
    materialization_exports = {
        "comparison.csv": "gamma_comparison.csv",
        "coverage.csv": "gamma_coverage.csv",
        "counts.csv": "materialization_counts.csv",
    }
    payloads = {}
    for source_name, output_name in materialization_exports.items():
        source = manifest_path.parent / source_name
        pins = {Path(name).resolve(): digest for name, digest in materialized["artifacts"].items()}
        if pins.get(source.resolve()) != sha256(source):
            raise ValueError("RP4_V3_REPORT_MATERIALIZATION_EXPORT_PIN")
        payloads[public / output_name] = csv_bytes(read_csv(source))
        paths.append(source)
    raw_census_path = effective_manifest_path.parent / "census.csv"
    recode_audit_path = effective_manifest_path.parent / "recode_audit.json"
    for path in (raw_census_path, recode_audit_path):
        if recode_pins.get(path.resolve()) != sha256(path):
            raise ValueError("RP4_V3_REPORT_RECODE_EXPORT_HASH_DRIFT")
        paths.append(path)
    empty_comparison = empty_census_comparison(read_csv(raw_census_path), windows)
    payloads[public / "empty_window_census.csv"] = csv_bytes(empty_comparison)
    payloads[public / "empty_window_recode.csv"] = csv_bytes(read_json(recode_audit_path))
    payloads[ROOT / "docs/rp4/results_v3.md"] = render_report(
        windows, spec, fits, mz_fits, materialized, empty_comparison, baseline_parity
    ).encode("utf-8")
    payloads[public / "fit_selection.csv"] = csv_bytes(fits)
    payloads[public / "mz_calibration.csv"] = csv_bytes(mz_fits)
    payloads[public / "bound_counts.csv"] = csv_bytes(bound_summary(fits))
    payloads[public / "winsor_counts.csv"] = csv_bytes(winsor_rows)
    payloads[public / "unchanged_lgb_parity.csv"] = csv_bytes(baseline_parity)
    for window in WINDOWS:
        summary = windows["v3"][window][0]
        for section, name in (
            ("regime_secondary", "regimes"),
            ("top_loss_sessions", "top_loss"),
            ("high_gamma_vs_rest", "high_gamma_vs_rest"),
        ):
            payloads[public / f"{name}_{window}.csv"] = csv_bytes(summary[section])
    for contrast, base, richer in inf.CONTRASTS:
        payloads[public / f"{contrast}.svg"] = cumulative_figure(
            windows, contrast, base, richer
        ).encode("utf-8")

    def label(path: Path) -> str:
        resolved = path.resolve()
        return (
            "private/" + resolved.relative_to(private_root).as_posix()
            if resolved.is_relative_to(private_root)
            else resolved.relative_to(ROOT).as_posix()
        )

    inputs = {label(p): initial_sha[p.resolve()] for p in paths}
    if any(p.exists() and p.read_bytes() != data for p, data in payloads.items()):
        raise ValueError("RP4_V3_REPORT_IMMUTABLE_OUTPUT_MISMATCH")
    if any(sha256(p) != inputs[label(p)] for p in paths):
        raise ValueError("RP4_V3_REPORT_INPUT_CHANGED_DURING_RENDER")
    for path, data in payloads.items():
        write_bytes_once(path, data)
    result = {
        "schema_version": "rp4-v3-report-v1",
        "specification_sha256": args.spec_sha256,
        "effective_specification_path": label(args.spec),
        "unchanged_lgb_parity": baseline_parity,
        "legacy_report_manifest_sha256": LEGACY_MANIFEST_SHA,
        "inputs_sha256": inputs,
        "outputs_sha256": {label(p): sha256(p) for p in payloads},
        "models_fitted": 0,
        "raw_or_origin_panels_read": False,
        "published": False,
        "RESEARCH_ONLY": True,
        "capital_go": False,
        "command": "uv run --offline --frozen --no-sync python -B -m "
        "artifacts.rp4_v3_code.report_v3 --spec "
        + label(args.spec)
        + " --spec-sha256 "
        + args.spec_sha256,
    }
    write_json_once(public / "report_manifest.json", result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--spec-sha256", required=True)
    result = run(parser.parse_args())
    print(
        json.dumps(
            {"status": "RP4_V3_REPORT_COMPLETE", "outputs_sha256": result["outputs_sha256"]},
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
