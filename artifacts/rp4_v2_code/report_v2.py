"""Render the v1/v2 comparison from completed aggregates, never fitting models."""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import statistics
from collections import Counter
from datetime import date
from itertools import accumulate
from pathlib import Path
from typing import Any

from artifacts.rp4_code.evaluate import CONTRASTS, sha256, write_bytes_once, write_json_once
from artifacts.rp4_code.report import number, table
from artifacts.rp4_v2_code.evaluate_v2 import load_spec
from artifacts.rp4_v2_code.freeze import V1_SHA
from figure_style import ACCENT, INK, MUTED, RULE, SANS, Canvas, esc, header

ROOT = Path(__file__).resolve().parents[2]
WINDOWS = {"primary": "Primaria", "confirmation": "Confirmación"}
FAMILIES = {
    "v1": ("log_ols_harq", "lightgbm_qlike"),
    "v2": ("log_ridge_harq", "lightgbm_qlike"),
}
FAMILY_LABELS = {
    "log_ols_harq": "log-OLS HARQ",
    "log_ridge_harq": "log-ridge HARQ",
    "lightgbm_qlike": "LightGBM QLIKE",
}
type Rows = list[dict[str, Any]]
type Window = tuple[dict[str, Any], Rows]
type Comparison = dict[str, dict[str, Window]]


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


def close(actual: Any, expected: Any, reason: str) -> None:
    if not math.isclose(float(actual), float(expected), rel_tol=1e-10, abs_tol=1e-12):
        raise ValueError("RP4_V2_REPORT_" + reason)


def differences(rows: Rows, family: str, base: str, expanded: str) -> list[float]:
    return [
        float(r[f"loss__{family}__{base}"]) - float(r[f"loss__{family}__{expanded}"]) for r in rows
    ]


def validate_iv_counts(rows: Rows, materialized: dict[str, Any]) -> None:
    keys = [(r["asset"], r["session_date"]) for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("RP4_V2_REPORT_IV_DUPLICATE_SESSION_ASSET")
    for key in ("raw_asset_rows", "iv_rejected_total_rows", "newly_rejected_within_old_iv_range"):
        if sum(int(r[key]) for r in rows) != materialized[key]:
            raise ValueError("RP4_V2_REPORT_IV_COUNT_MISMATCH")
    categories = (
        "iv_null_rows",
        "iv_nonfinite_nonnull_rows",
        "iv_below_003_rows",
        "iv_above_3_rows",
    )
    counts = categories + (
        "raw_asset_rows",
        "iv_rejected_total_rows",
        "old_iv_eligible_rows",
        "new_iv_eligible_rows",
        "newly_rejected_within_old_iv_range",
    )
    for row in rows:
        values = {k: int(row[k]) for k in counts}
        raw = values["raw_asset_rows"]
        rejected = values["iv_rejected_total_rows"]
        old = values["old_iv_eligible_rows"]
        new = values["new_iv_eligible_rows"]
        incremental = values["newly_rejected_within_old_iv_range"]
        if (
            any(value < 0 for value in values.values())
            or rejected + new != raw
            or sum(values[k] for k in categories) != rejected
            or not new <= old <= raw
            or old - new != incremental
        ):
            raise ValueError("RP4_V2_REPORT_IV_ROW_ACCOUNTING")
        close(
            row["iv_rejected_percent"],
            100.0 * rejected / raw if raw else 0.0,
            "IV_PERCENT_DENOMINATOR",
        )


def validate_secondaries(summary: dict[str, Any], rows: Rows) -> None:
    expected = {(f, c) for f in FAMILIES["v2"] for c, _, _ in CONTRASTS}
    tails = summary.get("tail_secondary", [])
    if len(tails) != 4 or {(r["family"], r["contrast"]) for r in tails} != expected:
        raise ValueError("RP4_V2_REPORT_SECONDARY_INCOMPLETE")
    for item in tails:
        _, base, expanded = next(c for c in CONTRASTS if c[0] == item["contrast"])
        values = differences(rows, item["family"], base, expanded)
        trim = math.floor(0.05 * len(values))
        ordered = sorted(values)
        kept = ordered[trim : len(ordered) - trim] if trim else ordered
        if item["N_sessions"] != len(rows) or item["removed_each_tail"] != trim:
            raise ValueError("RP4_V2_REPORT_SECONDARY_COUNT_DRIFT")
        close(item["median_paired_contrast"], statistics.median(values), "SECONDARY_MEDIAN_DRIFT")
        close(item["trimmed_mean_5pct_each_tail"], statistics.mean(kept), "SECONDARY_TRIM_DRIFT")
    tops = summary.get("top_loss_sessions", [])
    if len(tops) != 6 * min(10, len(rows)):
        raise ValueError("RP4_V2_REPORT_TOP_LOSS_INCOMPLETE")
    for family in FAMILIES["v2"]:
        for information_set in ("B0", "B1", "B2"):
            actual = sorted(
                (
                    r
                    for r in tops
                    if r["family"] == family and r["ranked_information_set"] == information_set
                ),
                key=lambda r: r["rank"],
            )
            expected_rows = sorted(
                rows,
                key=lambda r: (-float(r[f"loss__{family}__{information_set}"]), r["session_date"]),
            )[:10]
            if len(actual) != len(expected_rows):
                raise ValueError("RP4_V2_REPORT_TOP_LOSS_MODEL_COUNT")
            for rank, (item, source) in enumerate(zip(actual, expected_rows, strict=True), 1):
                if item["rank"] != rank or item["session_date"] != source["session_date"]:
                    raise ValueError("RP4_V2_REPORT_TOP_LOSS_ORDER")
                for name in ("B0", "B1", "B2"):
                    close(
                        item[f"qlike_{name}"], source[f"loss__{family}__{name}"], "TOP_LOSS_VALUE"
                    )
                for contrast, base, expanded in CONTRASTS:
                    delta = float(source[f"loss__{family}__{base}"]) - float(
                        source[f"loss__{family}__{expanded}"]
                    )
                    close(item[contrast], delta, "TOP_LOSS_CONTRAST")
                    if item[contrast + "_sign"] != (1 if delta > 0 else -1 if delta < 0 else 0):
                        raise ValueError("RP4_V2_REPORT_TOP_LOSS_SIGN")


def load_window(directory: Path, version: str, digest: str, window: str, label: str) -> Window:
    summary = read_json(directory / "summary.json")
    rows = read_csv(directory / "session_losses.csv")
    if summary.get("status") != "COMPUTED" or not rows:
        raise ValueError("RP4_V2_REPORT_COMPLETED_SUMMARY_REQUIRED")
    if summary["binding"]["specification_sha256"] != digest:
        raise ValueError("RP4_V2_REPORT_SPECIFICATION_MISMATCH")
    if summary["window"] != window or summary["result_label"] != label:
        raise ValueError("RP4_V2_REPORT_WINDOW_OR_LABEL_MISMATCH")
    dates = [r["session_date"] for r in rows]
    if dates != sorted(set(dates)) or len(rows) != summary["N_sessions"]:
        raise ValueError("RP4_V2_REPORT_SESSION_COUNT_OR_ORDER")
    if set(summary["completed_session_sha256"]) != {d + ".json" for d in dates}:
        raise ValueError("RP4_V2_REPORT_CHECKPOINT_SESSION_MISMATCH")
    if summary["scheduled_sessions"] != len(rows) + len(summary["skipped_sessions"]):
        raise ValueError("RP4_V2_REPORT_INCOMPLETE_SCHEDULE")
    expected = {(f, c) for f in FAMILIES[version] for c, _, _ in CONTRASTS}
    contrasts = summary["contrasts"]
    if len(contrasts) != 4 or {(r["family"], r["contrast"]) for r in contrasts} != expected:
        raise ValueError("RP4_V2_REPORT_CONTRASTS_INCOMPLETE")
    for item in contrasts:
        _, base, expanded = next(c for c in CONTRASTS if c[0] == item["contrast"])
        values = differences(rows, item["family"], base, expanded)
        if not all(math.isfinite(v) for v in values):
            raise ValueError("RP4_V2_REPORT_NONFINITE_LOSS")
        close(item["estimate"], math.fsum(values) / len(values), "ESTIMATE_MISMATCH")
        baseline = statistics.mean(float(r[f"loss__{item['family']}__{base}"]) for r in rows)
        if item.get("qlike_reduction_percent") is not None:
            close(
                item["qlike_reduction_percent"],
                100 * statistics.mean(values) / baseline,
                "PERCENT_REDUCTION_MISMATCH",
            )
    if version == "v2":
        validate_secondaries(summary, rows)
    return summary, rows


def fit_diagnostics(records: Rows, dates: list[str], window: str) -> Rows:
    expected = {
        (d, f + "__" + s) for d in dates for f in FAMILIES["v2"] for s in ("B0", "B1", "B2")
    }
    if len(records) != len(expected) or {(r["session"], r["model"]) for r in records} != expected:
        raise ValueError("RP4_V2_REPORT_FIT_DIAGNOSTICS_INCOMPLETE")
    output = []
    for r in sorted(records, key=lambda r: (r["session"], r["model"])):
        if not r["inner_valid_sessions"] or max(r["inner_valid_sessions"]) >= r["session"]:
            raise ValueError("RP4_V2_REPORT_FIT_CAUSALITY")
        ridge = r["model"].startswith("log_ridge_harq__")
        chosen = r["selected"]
        row = {
            "window": window,
            "session": r["session"],
            "model": r["model"],
            "selected_lambda": chosen["lambda"] if ridge else None,
            "selected_rounds": None if ridge else chosen["rounds"],
            "selected_leaves": None if ridge else chosen["num_leaves"],
            "validation_qlike": chosen["validation_qlike"],
            "train_rows": r["train_rows"],
            "prediction_rows": r.get("prediction_rows"),
            "lower_bound": r["bounds"]["refit"]["lower"] if ridge else None,
            "upper_bound": r["bounds"]["refit"]["upper"] if ridge else None,
            "linear_lower_touches": r["count_low"] if ridge else None,
            "linear_upper_touches": r["count_high"] if ridge else None,
            "lgb_log_low_touches": None if ridge else r["count_log_low"],
            "lgb_log_high_touches": None if ridge else r["count_log_high"],
            "lgb_variance_floor_touches": None if ridge else r["count_variance_floor"],
            "columns_kept": len(r["preprocessing"]["refit"]["active_columns"]) if ridge else None,
            "columns_removed": len(r["preprocessing"]["refit"]["removed_columns"])
            if ridge
            else None,
        }
        if ridge:
            if not (
                0 < row["lower_bound"] < row["upper_bound"]
                and 0 <= r["count_low"] + r["count_high"] <= r["prediction_rows"]
            ):
                raise ValueError("RP4_V2_REPORT_BOUND_COUNTS_INVALID")
        elif not (r["refit_rounds"] == chosen["rounds"] and 1 <= chosen["rounds"] <= 2000):
            raise ValueError("RP4_V2_REPORT_SELECTED_ROUNDS_INVALID")
        output.append(row)
    return output


def cumulative_figure(windows: Comparison, contrast: str, base: str, expanded: str) -> str:
    canvas = Canvas(
        1180,
        1530,
        f"RP4 v1/v2: {expanded} sobre {base}",
        "Ocho paneles con escalas explícitas independientes; todas las sesiones "
        "y sus pérdidas adversas, sin recorte ni cambios de signo.",
        contrast + "-v2",
    )
    header(
        canvas,
        "Fuera de muestra walk-forward",
        f"RP4 v1 / v2 · {expanded} sobre {base}",
        "Suma de [QLIKE base − QLIKE ampliado]. Escala independiente por panel; positivo = mejora.",
    )
    for column, version in enumerate(("v1", "v2")):
        for window_index, window in enumerate(WINDOWS):
            for family_index, family in enumerate(FAMILIES[version]):
                _, rows = windows[version][window]
                curve = [0.0, *accumulate(differences(rows, family, base, expanded))]
                left, right = 92 + 575 * column, 550 + 575 * column
                top = 178 + 334 * (2 * window_index + family_index)
                bottom = top + 236
                low, high = min(curve), max(curve)
                padding = (high - low) * 0.08 if high > low else 1.0
                low, high = low - padding, high + padding

                def y(
                    value: float,
                    low: float = low,
                    high: float = high,
                    top: int = top,
                    bottom: int = bottom,
                ) -> float:
                    return bottom - (value - low) / (high - low) * (bottom - top)

                color = INK if version == "v1" else ACCENT
                canvas.front(
                    f'<text x="{left}" y="{top - 40}" font-family="{SANS}" '
                    f'font-size="16" fill="{INK}">{version} · {WINDOWS[window]} · '
                    f"{esc(FAMILY_LABELS[family])}</text>"
                    f'<text x="{left}" y="{top - 19}" font-family="{SANS}" '
                    f'font-size="12" fill="{MUTED}">{len(rows)} sesiones · final '
                    f"{curve[-1]:+.8g}</text>"
                )
                for index in range(5):
                    value = low + (high - low) * index / 4
                    canvas.back(
                        f'<line x1="{left}" x2="{right}" y1="{y(value):.2f}" '
                        f'y2="{y(value):.2f}" stroke="{RULE}"/>'
                    )
                    canvas.front(
                        f'<text x="{left - 9}" y="{y(value) + 4:.2f}" text-anchor="end" '
                        f'font-family="{SANS}" font-size="11" fill="{MUTED}">{value:.4g}</text>'
                    )
                canvas.back(
                    f'<line x1="{left}" x2="{right}" y1="{y(0):.2f}" '
                    f'y2="{y(0):.2f}" stroke="{INK}" stroke-dasharray="4 4"/>'
                )
                dates = [date.fromisoformat(r["session_date"]).toordinal() for r in rows]
                times = [dates[0] - 1, *dates]
                path = " ".join(
                    f"{'M' if i == 0 else 'L'} "
                    f"{left + (right - left) * (t - times[0]) / (times[-1] - times[0]):.2f} "
                    f"{y(v):.2f}"
                    for i, (t, v) in enumerate(zip(times, curve, strict=True))
                )
                canvas.front(
                    f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2" '
                    f'data-version="{version}" data-window="{window}" data-family="{family}" '
                    f'data-endpoint="{curve[-1]:.17g}" data-sessions="{len(rows)}"/>'
                )
                for x, text, anchor in (
                    (left, rows[0]["session_date"], "start"),
                    (right, rows[-1]["session_date"], "end"),
                ):
                    canvas.front(
                        f'<text x="{x}" y="{bottom + 23}" text-anchor="{anchor}" '
                        f'font-family="{SANS}" font-size="12" fill="{MUTED}">{esc(text)}</text>'
                    )
    return str(canvas.render()) + "\n"


def paired_table(windows: Comparison, window: str) -> str:
    rows = []
    for index in range(2):
        for contrast, _, _ in CONTRASTS:
            row = ["Lineal: OLS v1 → ridge v2" if index == 0 else "LightGBM QLIKE", contrast]
            for version in ("v1", "v2"):
                summary = windows[version][window][0]
                item = next(
                    r
                    for r in summary["contrasts"]
                    if r["family"] == FAMILIES[version][index] and r["contrast"] == contrast
                )
                row += [
                    number(item["estimate"], signed=True),
                    f"[{number(item.get('ci_low'))}, {number(item.get('ci_high'))}]",
                    number(item.get("p_raw")),
                    number(item.get("p_holm")),
                    number(item.get("qlike_reduction_percent"), signed=True),
                    str(item["N_sessions"]),
                    str(item["N_origins"]),
                    str(item.get("N_asset_sessions", "NO VERIFICABLE")),
                ]
            rows.append(row)
    columns = [
        "Delta",
        "IC95%",
        "p crudo",
        "p Holm",
        "Reducción %",
        "N sesiones",
        "N orígenes",
        "N activo-sesión",
    ]
    return str(
        table(["Familia", "Contraste"] + [f"{v} {c}" for v in ("v1", "v2") for c in columns], rows)
    )


def render_report(
    windows: Comparison, spec: dict[str, Any], audit: dict[str, Any], fit_rows: Rows, iv_rows: Rows
) -> str:
    parts = [
        "# RP4 — resultados v2 comparados con v1",
        "",
        spec["label"] + ".",
        "",
        "RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.",
        "",
        "Delta = pérdida QLIKE base menos ampliada; positivo favorece al conjunto rico. "
        "Reducción % = 100 × delta / pérdida base. Se mantienen medias por activo-sesión "
        "y luego por sesión, bootstrap de cinco sesiones (9.999 réplicas), IC percentil 95% "
        "y p bilateral centrado; Holm corrige cuatro contrastes por ventana y versión.",
        "",
        "La familia lineal cambia de log-OLS a log-ridge. Las muestras elegibles cambian "
        "por la nueva obligatoriedad: las diferencias entre versiones no aíslan un único "
        "cambio del modelo. No se reevalúa ni se sobrescribe v1.",
        "",
        "Alto flujo conserva la definición de v1: el tercil superior por activo se calcula "
        "con la prima del día anterior y solo el entrenamiento elegible bajo la máscara v1 "
        "del panel original fijado por SHA-256, con el mismo embargo de 60 minutos. "
        "No se recalcula el umbral con la máscara ampliada de v2; los orígenes recuperados "
        "se clasifican contra ese mismo umbral. Por ello puede cambiar N sin cambiar la regla.",
    ]
    for window, label in WINDOWS.items():
        current = windows["v2"][window][0]
        positives = sum(r["estimate"] > 0 for r in current["contrasts"])
        significant = sum(
            r.get("p_holm") is not None and r["p_holm"] < 0.05 for r in current["contrasts"]
        )
        parts += [
            "",
            "## " + label,
            "",
            f"V2: {positives}/4 contrastes positivos; "
            f"{significant}/4 con p Holm < 0,05. Esto no establece por sí solo una "
            "jerarquía global robusta.",
            "",
            paired_table(windows, window),
            "",
            "### Cobertura efectiva por activo",
            "",
        ]
        coverage = []
        for asset in spec["assets"]:
            row = [asset]
            for version in ("v1", "v2"):
                item = next(
                    r
                    for r in windows[version][window][0]["evaluation_quality_by_asset"]
                    if r["asset"] == asset
                )
                row += [
                    str(item["scheduled_rows"]),
                    str(item["eligible_rows"]),
                    number(100 * item["eligible_rows"] / item["scheduled_rows"]),
                ]
            coverage.append(row)
        parts += [
            table(
                [
                    "Activo",
                    "v1 programados",
                    "v1 elegibles",
                    "v1 %",
                    "v2 programados",
                    "v2 elegibles",
                    "v2 %",
                ],
                coverage,
            ),
            "",
            "Motivos de exclusión —se solapan, no deben sumarse—:",
            "",
            table(
                ["Versión", "Activo", "RV30 inválido", "Obligatorios incompletos", "Gate"],
                [
                    [
                        version,
                        r["asset"],
                        str(r["invalid_target"]),
                        str(r["incomplete_mandatory_predictors"]),
                        str(r["failed_quality_gate"]),
                    ]
                    for version in ("v1", "v2")
                    for r in windows[version][window][0]["evaluation_quality_by_asset"]
                ],
            ),
        ]
        for version in ("v1", "v2"):
            summary, _ = windows[version][window]
            skips = "; ".join(f"{r['session']}: {r['reason']}" for r in summary["skipped_sessions"])
            quality_present = (
                audit["windows"][window]["quality_flag_present"]
                if version == "v1"
                else summary.get("quality_gate_column_present")
            )
            quality_note = (
                "columna rp4_eligible ausente: se conservó el fallback de v1 "
                "(sin exclusión por esa compuerta opcional)"
                if quality_present is False
                else "columna rp4_eligible presente"
                if quality_present is True
                else "presencia de compuerta opcional NO VERIFICABLE"
            )
            parts += [
                "",
                f"{version}: {summary['scheduled_sessions']} sesiones programadas, "
                f"{summary['N_sessions']} ejecutadas; {summary['first_session']} a "
                f"{summary['last_session']}. Omitidas: {skips or 'ninguna'}. {quality_note}.",
            ]
        parts += [
            "",
            "### DM, GW y Mincer–Zarnowitz",
            "",
            "GW es el diagnóstico HAC asintótico de v1, no la garantía del test original "
            "con memoria fija. MZ utiliza medias de sesión en niveles.",
            "",
            table(
                ["Versión", "Familia", "Contraste", "DM", "p DM", "GW", "p GW"],
                [
                    [
                        version,
                        FAMILY_LABELS[r["family"]],
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
                    for version in ("v1", "v2")
                    for r in windows[version][window][0]["contrasts"]
                ],
            ),
            "",
            table(
                ["Versión", "Modelo", "Intercepto", "Pendiente", "p a=0,b=1", "N", "Estado"],
                [
                    [
                        version,
                        model,
                        number(r.get("intercept")),
                        number(r.get("slope")),
                        number(r.get("joint_a0_b1_hac_p")),
                        str(r.get("N_sessions", "NO VERIFICABLE")),
                        r.get("status", "NO VERIFICABLE")
                        + (": " + r["reason"] if "reason" in r else ""),
                    ]
                    for version in ("v1", "v2")
                    for model, r in windows[version][window][0].get("mincer_zarnowitz", {}).items()
                ],
            ),
            "",
            "### Colas: secundarios descriptivos pareados",
            "",
        ]
        tail_rows = []
        for r in current["tail_secondary"]:
            old_family = "log_ols_harq" if r["family"] == "log_ridge_harq" else r["family"]
            old = audit["windows"][window]["paired_contrast_centers"][
                old_family + "__" + r["contrast"]
            ]
            tail_rows.append(
                [
                    FAMILY_LABELS[r["family"]],
                    r["contrast"],
                    number(old["median_of_paired_contrast"], signed=True),
                    number(r["median_paired_contrast"], signed=True),
                    number(old["trimmed_mean_5_percent_each_tail"], signed=True),
                    number(r["trimmed_mean_5pct_each_tail"], signed=True),
                    str(r["removed_each_tail"]),
                    str(r["N_sessions"]),
                ]
            )
        parts += [
            table(
                [
                    "Familia v2",
                    "Contraste",
                    "v1 mediana Δ",
                    "v2 mediana Δ",
                    "v1 recortada",
                    "v2 recortada",
                    "v2 removidas por cola",
                    "N v2",
                ],
                tail_rows,
            ),
            "",
            "Recorte simétrico: floor(0,05 N) por cola; no sustituye la media primaria. "
            "Mediana de diferencias no equivale a diferencia de medianas.",
            "",
            f"[Diez días de mayor pérdida por cada modelo de {label.lower()}, con valores y signos]"
            f"(../../artifacts/rp4_v2_b4/top_loss_{window}.csv). "
            "Se conserva el ranking de cada familia/conjunto, sin quitar los días adversos.",
            "",
            "### Secundarios y estabilidad registrados",
            "",
            table(
                [
                    "Subconjunto",
                    "Familia",
                    "Contraste",
                    "Delta v2",
                    "Reducción %",
                    "N sesiones",
                    "N orígenes",
                    "Estado",
                ],
                [
                    [
                        r["subset"],
                        FAMILY_LABELS[r["family"]],
                        r["contrast"],
                        number(r.get("estimate"), signed=True),
                        number(r.get("qlike_reduction_percent"), signed=True),
                        str(r.get("N_sessions", "NO VERIFICABLE")),
                        str(r.get("N_origins", "NO VERIFICABLE")),
                        r.get("coverage_status", r.get("status", "NO VERIFICABLE")),
                    ]
                    for r in current.get("secondary", [])
                ],
            ),
            "",
            table(
                ["Subconjunto", "Familia", "B1 sobre B0 v2", "B2 sobre B1 v2"],
                [
                    [
                        subset,
                        FAMILY_LABELS[family],
                        *[
                            number(
                                next(
                                    (
                                        r["estimate"]
                                        for r in current.get("robustness", [])
                                        if r["subset"] == subset
                                        and r["family"] == family
                                        and r["contrast"] == contrast
                                    ),
                                    None,
                                ),
                                signed=True,
                            )
                            for contrast, _, _ in CONTRASTS
                        ],
                    ]
                    for subset in dict.fromkeys(r["subset"] for r in current.get("robustness", []))
                    for family in FAMILIES["v2"]
                ],
            ),
        ]
    parts += [
        "",
        "## Rondas, lambda y acotamiento",
        "",
        "[Selección y cotas por sesión/modelo](../../artifacts/rp4_v2_b4/fit_selection.csv). "
        "Los conteos son de pronósticos finales; no de candidatos de validación. "
        "No se publican coeficientes ni series por origen.",
        "",
    ]
    selection_rows = []
    for window in WINDOWS:
        for family in FAMILIES["v2"]:
            for name in ("B0", "B1", "B2"):
                model = family + "__" + name
                selected = [r for r in fit_rows if r["window"] == window and r["model"] == model]
                ridge = family == "log_ridge_harq"
                choices = Counter(
                    r["selected_lambda" if ridge else "selected_rounds"] for r in selected
                )
                values = [r["selected_lambda" if ridge else "selected_rounds"] for r in selected]
                choice_text = (
                    "; ".join(f"{k:g}: {v}" for k, v in sorted(choices.items()))
                    if ridge
                    else f"mín={min(values)}, mediana={statistics.median(values):g}, "
                    f"máx={max(values)}; tope 2000: {choices[2000]}"
                )
                selection_rows.append(
                    [
                        WINDOWS[window],
                        model,
                        str(len(selected)),
                        ("lambda " if ridge else "rondas ") + choice_text,
                        str(
                            sum(
                                r["linear_lower_touches" if ridge else "lgb_log_low_touches"] or 0
                                for r in selected
                            )
                        ),
                        str(
                            sum(
                                r["linear_upper_touches" if ridge else "lgb_log_high_touches"] or 0
                                for r in selected
                            )
                        ),
                        str(sum(r["lgb_variance_floor_touches"] or 0 for r in selected))
                        if not ridge
                        else "no aplica",
                    ]
                )
    parts += [
        table(
            [
                "Ventana",
                "Modelo",
                "Ajustes",
                "Elección: frecuencia",
                "Cota baja / log bajo",
                "Cota alta / log alto",
                "Piso LGB",
            ],
            selection_rows,
        ),
        "",
        "Las cotas ridge son 0,1 × mínimo y 10 × máximo del RV30 de su entrenamiento. "
        "Los umbrales numéricos LightGBM permanecen en [-30,30] log y piso 1e-12; "
        "sus conteos pueden solaparse.",
        "",
        "## Saneamiento IV y preservación",
        "",
        "Filtro por operación, antes de los productores B1/B2/rejilla/dealers: IV finita "
        "en [0,03;3], extremos incluidos. El denominador incluye todas las filas UW originales "
        "del activo, antes de filtrar NBBO, tamaño u horario; no son celdas agregadas ni "
        "orígenes elegibles. Descarte total incluye IV nula, no finita y finita fuera de rango. "
        "Descarte nuevo cuenta únicamente las filas admitidas por [0,01;5] que deja de admitir "
        "[0,03;3]: no es el descarte total ni la pérdida de filas utilizables del panel. "
        "[Conteos por activo y sesión](../../artifacts/rp4_v2_b4/iv_filter_counts.csv).",
        "",
    ]
    iv_counts = []
    for asset in spec["assets"]:
        selected = [r for r in iv_rows if r["asset"] == asset]
        keys = (
            "raw_asset_rows",
            "iv_null_rows",
            "iv_nonfinite_nonnull_rows",
            "iv_below_003_rows",
            "iv_above_3_rows",
            "iv_rejected_total_rows",
            "new_iv_eligible_rows",
            "newly_rejected_within_old_iv_range",
        )
        counts = {k: sum(int(r[k]) for r in selected) for k in keys}
        iv_counts.append(
            [
                asset,
                *[str(counts[k]) for k in keys],
                number(100 * counts["iv_rejected_total_rows"] / counts["raw_asset_rows"])
                if counts["raw_asset_rows"]
                else "NO VERIFICABLE",
            ]
        )
    parts += [
        table(
            [
                "Activo",
                "Filas UW",
                "IV nula",
                "No finita",
                "IV<0,03",
                "IV>3",
                "Descartadas",
                "Aceptadas",
                "Descarte nuevo vs [0,01;5]",
                "% descarte",
            ],
            iv_counts,
        ),
        "",
        "La materialización verifica que B0/HARQ, RV30, claves, relojes y estratos se "
        "conservan por clave; solo cambia el universo de operaciones IV admitidas y las "
        "columnas de opciones derivadas. No hubo nuevas descargas para v2.",
        "",
        "## Fe de erratas adjunta a v1",
        "",
        "El informe v1 permanece inalterado. Su frase absoluta sobre ausencia de diagnósticos "
        "en X no era correcta: sí entraron `b2_5m_observed_span_s` y `b2_30m_observed_span_s`. "
        "Los otros siete diagnósticos señalados, incluido `b1_median_quote_age_s`, ya estaban "
        "excluidos; `b1_pcp_residual` también. No se afirma que se usaron los nueve.",
        "",
        "La auditoría distingue el máximo OLS por origen del promedio de sesión y la mediana "
        "del contraste pareado de la diferencia de medianas marginales. "
        "[Cifras y hashes auditados de v1](../../artifacts/rp4_v2_audit/REPORT.md).",
        "",
        "## Evolución acumulada",
        "",
        "Cada figura conserva ocho series reales: v1/v2 × dos ventanas × dos familias. "
        "Escalas independientes, explícitas por panel; ningún extremo se elimina.",
        "",
        "![B1 sobre B0 v1/v2](../../artifacts/rp4_v2_b4/B1_over_B0.svg)",
        "",
        "![B2 sobre B1 v1/v2](../../artifacts/rp4_v2_b4/B2_over_B1.svg)",
        "",
        "## Divulgación",
        "",
        "La ventana 20 de julio a 28 de agosto fue leída una vez por el puente de Fase 8 "
        "con otra especificación. El PIT es proxy de tiempo fuente a 120 s, como en la literatura.",
        "",
        "Hueco aceptado UW: 2025-01-25 a 2025-02-24, sin relleno. La convención call largo / "
        "put corto y el OI del cierre previo no identifican posiciones observadas de dealers.",
        "",
        "Limitación: v2 responde a resultados ya observados; un hash nuevo y una ejecución "
        "no eliminan la selección adaptativa, Holm por versión no controla la búsqueda entre "
        "v1/v2 y el tiempo fuente sigue siendo un proxy de disponibilidad histórica.",
        "",
        "## Trazabilidad",
        "",
        "[Especificación v2](specification_v2.md) · [Decisión 130](decision_130_v2.md) · "
        "[Informe v1 intacto](results_v1.md) · "
        "[Manifiesto de entradas/salidas del informe]"
        "(../../artifacts/rp4_v2_b4/report_manifest.json).",
        "",
        "Recibos por etapa, con comandos, códigos de salida y hashes: "
        "[A1](../../artifacts/rp4_v2_a1/receipt.json) · "
        "[A2](../../artifacts/rp4_v2_a2/receipt.json) · "
        "[B2 primaria](../../artifacts/rp4_v2_b2/receipt.json) · "
        "[B3 confirmación](../../artifacts/rp4_v2_b3/receipt.json) · "
        "[B4 informe](../../artifacts/rp4_v2_b4/receipt.json). "
        "El recibo B4 se emite externamente después de que el generador termine con "
        "código 0, para evitar la autorreferencia de su hash.",
        "",
        "La evaluación se ejecuta en cuatro particiones disjuntas de sesiones (shards); "
        "cada sesión conserva todo el pasado permitido como entrenamiento, y los "
        "resultados se agregan una sola vez por ventana.",
        "",
        "Se conservan los secundarios y desgloses completos de ambas versiones en "
        "[CSV](../../artifacts/rp4_v2_b4/secondary_and_robustness.csv). "
        "El generador solo verifica y presenta agregados terminados: no ajusta modelos, "
        "no abre paneles por origen y no activa colectores ni publica resultados.",
        "",
    ]
    return "\n".join(parts)


def run(args: argparse.Namespace) -> dict[str, Any]:
    spec = load_spec(args.spec, args.spec_sha256)
    public = ROOT / "artifacts/rp4_v2_b4"
    output = ROOT / "docs/rp4/results_v2.md"
    data_root = Path(spec["data_root"]).resolve()
    audit_path = ROOT / "artifacts/rp4_v2_audit/audit.json"
    audit = read_json(audit_path)
    paths = [
        args.spec,
        args.spec.parent / "freeze.json",
        ROOT / "docs/rp4/specification_v2.md",
        ROOT / "docs/rp4/decision_130_v2.md",
        ROOT / "artifacts/rp4_a1/specification.json",
        ROOT / "docs/rp4/results_v1.md",
        audit_path,
        Path(__file__),
        ROOT / "artifacts/rp4_code/report.py",
        ROOT / "scripts/figure_style.py",
    ]
    if sha256(ROOT / "artifacts/rp4_a1/specification.json") != V1_SHA:
        raise ValueError("RP4_V2_REPORT_PARENT_SPEC_DRIFT")
    windows: Comparison = {"v1": {}, "v2": {}}
    for version, prefix, digest in (("v1", "rp4", V1_SHA), ("v2", "rp4_v2", args.spec_sha256)):
        for window, stage in (("primary", "b2"), ("confirmation", "b3")):
            directory = ROOT / "artifacts" / f"{prefix}_{stage}"
            windows[version][window] = load_window(
                directory, version, digest, window, spec["label"]
            )
            paths.extend([directory / "summary.json", directory / "session_losses.csv"])
    for name, digest in audit["source_sha256"].items():
        if not name.startswith("data/"):
            source = (ROOT / name).resolve()
            if not source.is_relative_to(ROOT.resolve()):
                raise ValueError("RP4_V2_REPORT_AUDIT_PATH_OUTSIDE_ROOT")
            if sha256(source) != digest:
                raise ValueError("RP4_V2_REPORT_V1_AUDIT_INPUT_DRIFT")
    bindings = [windows["v2"][w][0]["binding"] for w in WINDOWS]
    if any(
        bindings[0][k] != bindings[1][k]
        for k in ("panel_sha256", "specification_sha256", "release_sha256", "code_sha256")
    ):
        raise ValueError("RP4_V2_REPORT_WINDOWS_DIFFERENT_BINDING")
    materialization = data_root / "materialized/manifest.json"
    iv_path = data_root / "materialized/iv_filter_counts.csv"
    materialized = read_json(materialization)
    if (
        materialized["spec_sha256"] != args.spec_sha256
        or materialized["preserved_values_exact_by_keys"] is not True
        or materialized["iv_inclusive_bounds"] != [0.03, 3.0]
    ):
        raise ValueError("RP4_V2_REPORT_MATERIALIZATION_CONTRACT")
    for window in WINDOWS:
        if windows["v2"][window][0]["materialization_manifest_sha256"] != sha256(materialization):
            raise ValueError("RP4_V2_REPORT_MATERIALIZATION_HASH")
    pins = materialized["artifacts"]
    for name, expected in (
        ("panel.parquet", bindings[0]["panel_sha256"]),
        ("iv_filter_counts.csv", sha256(iv_path)),
    ):
        found = [
            value
            for key, value in pins.items()
            if Path(key).resolve() == data_root / "materialized" / name
        ]
        if found != [expected]:
            raise ValueError("RP4_V2_REPORT_MATERIALIZATION_PIN")
    iv_fields = (
        "asset",
        "session_date",
        "raw_asset_rows",
        "iv_null_rows",
        "iv_nonfinite_nonnull_rows",
        "iv_below_003_rows",
        "iv_above_3_rows",
        "iv_rejected_total_rows",
        "iv_rejected_percent",
        "old_iv_eligible_rows",
        "new_iv_eligible_rows",
        "newly_rejected_within_old_iv_range",
    )
    iv_rows = [{k: r[k] for k in iv_fields} for r in read_csv(iv_path)]
    validate_iv_counts(iv_rows, materialized)
    paths.extend([materialization, iv_path])
    fits = []
    for window in WINDOWS:
        path = data_root / "evaluation" / window / "fit_diagnostics.json"
        fits.extend(
            fit_diagnostics(
                read_json(path), [r["session_date"] for r in windows["v2"][window][1]], window
            )
        )
        paths.append(path)

    def input_label(path: Path) -> str:
        resolved = path.resolve()
        return (
            "private/" + resolved.relative_to(data_root).as_posix()
            if resolved.is_relative_to(data_root)
            else resolved.relative_to(ROOT.resolve()).as_posix()
        )

    inputs = {input_label(p): sha256(p) for p in paths}
    payloads = {
        output: render_report(windows, spec, audit, fits, iv_rows).encode("utf-8"),
        public / "fit_selection.csv": csv_bytes(fits),
        public / "iv_filter_counts.csv": csv_bytes(iv_rows),
    }
    all_secondary: Rows = []
    for window in WINDOWS:
        payloads[public / f"top_loss_{window}.csv"] = csv_bytes(
            windows["v2"][window][0]["top_loss_sessions"]
        )
        for version in ("v1", "v2"):
            for section in ("secondary", "robustness"):
                all_secondary.extend(
                    {"version": version, "window": window, "section": section, **r}
                    for r in windows[version][window][0].get(section, [])
                )
    payloads[public / "secondary_and_robustness.csv"] = csv_bytes(all_secondary)
    for contrast, base, expanded in CONTRASTS:
        payloads[public / f"{contrast}.svg"] = cumulative_figure(
            windows, contrast, base, expanded
        ).encode("utf-8")
    if any(sha256(p) != inputs[input_label(p)] for p in paths):
        raise ValueError("RP4_V2_REPORT_INPUT_CHANGED_DURING_RENDER")
    # Preflight all outputs before the first write; existing evidence is never replaced.
    if any(p.exists() and p.read_bytes() != content for p, content in payloads.items()):
        raise ValueError("RP4_V2_REPORT_IMMUTABLE_OUTPUT_MISMATCH")
    for path, content in payloads.items():
        write_bytes_once(path, content)
    manifest = {
        "schema_version": "rp4-v2-report-v1",
        "specification_sha256": args.spec_sha256,
        "parent_specification_sha256": V1_SHA,
        "high_flow_reference": {
            "source": "frozen_specification.input_panels.combined.sha256",
            "panel_sha256": spec["input_panels"]["combined"]["sha256"],
            "threshold_eligibility": "original_v1",
            "threshold_recomputed_with_v2_eligibility": False,
            "reference_panel_opened_by_report": False,
        },
        "iv_count_accounting": {
            "denominator": "all_original_UW_asset_rows_before_NBBO_size_session_filters",
            "total_rejected_includes_missing_and_nonfinite": True,
            "incremental_rejected": "old_[0.01,5]_eligible_minus_new_[0.03,3]_eligible",
        },
        "inputs_sha256": inputs,
        "outputs_sha256": {p.relative_to(ROOT).as_posix(): sha256(p) for p in payloads},
        "models_fitted": 0,
        "raw_or_origin_data_read": False,
        "published": False,
        "RESEARCH_ONLY": True,
        "capital_go": False,
        "command": "uv run --offline --frozen --no-sync python -B -m "
        "artifacts.rp4_v2_code.report_v2 --spec-sha256 " + args.spec_sha256,
    }
    write_json_once(public / "report_manifest.json", manifest)
    print("RP4_V2_B4_REPORT_RENDERED:" + sha256(output), flush=True)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--spec", type=Path, default=ROOT / "artifacts/rp4_v2_a1/specification.json"
    )
    parser.add_argument("--spec-sha256", required=True)
    run(parser.parse_args())


if __name__ == "__main__":
    main()
