"""Render RP4 tables and cumulative-loss figures from completed public aggregates."""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
from itertools import accumulate
from pathlib import Path
from typing import Any

from evaluate import CONTRASTS, FAMILIES, load_spec, sha256, write_bytes_once, write_json_once
from figure_style import ACCENT, INK, MUTED, RULE, SANS, Canvas, esc, header, legend

ROOT = Path(__file__).resolve().parents[2]
LABELS = {"primary": "Primaria", "confirmation": "Confirmación"}
FAMILY_LABELS = {"log_ols_harq": "log-OLS HARQ", "lightgbm_qlike": "LightGBM QLIKE"}


def number(value: Any, *, signed: bool = False) -> str:
    if value is None or not math.isfinite(float(value)):
        return "NO VERIFICABLE"
    return format(float(value), "+.8g" if signed else ".8g")


def table(headers: list[str], rows: list[list[str]]) -> str:
    def line(values: list[str]) -> str:
        return "| " + " | ".join(value.replace("|", "\\|") for value in values) + " |"

    return "\n".join([line(headers), line(["---"] * len(headers)), *map(line, rows)])


def load_window(directory: Path, specification_sha256: str) -> tuple[dict[str, Any], list[Any]]:
    summary = json.loads((directory / "summary.json").read_text(encoding="utf-8"))
    if summary["binding"]["specification_sha256"] != specification_sha256:
        raise ValueError("RP4_REPORT_SPECIFICATION_MISMATCH")
    csv_text = (directory / "session_losses.csv").read_text(encoding="utf-8")
    rows = list(csv.DictReader(io.StringIO(csv_text)))
    if len(rows) != summary.get("N_sessions", 0):
        raise ValueError("RP4_REPORT_SESSION_COUNT_MISMATCH")
    dates = [row["session_date"] for row in rows]
    if dates != sorted(set(dates)):
        raise ValueError("RP4_REPORT_SESSION_ORDER_INVALID")
    expected = {(family, contrast) for family in FAMILIES for contrast, _, _ in CONTRASTS}
    actual = {(row["family"], row["contrast"]) for row in summary["contrasts"]}
    if rows and expected != actual:
        raise ValueError("RP4_REPORT_CONTRASTS_INCOMPLETE")
    for result in summary["contrasts"]:
        _, base, expanded = next(item for item in CONTRASTS if item[0] == result["contrast"])
        family = result["family"]
        delta = [
            float(row[f"loss__{family}__{base}"]) - float(row[f"loss__{family}__{expanded}"])
            for row in rows
        ]
        if not all(math.isfinite(value) for value in delta):
            raise ValueError("RP4_REPORT_NONFINITE_SESSION_LOSS")
        if not math.isclose(
            math.fsum(delta) / len(delta), result["estimate"], rel_tol=1e-10, abs_tol=1e-12
        ):
            raise ValueError("RP4_REPORT_ESTIMATE_DOES_NOT_MATCH_SESSION_LOSS")
    return summary, rows


def cumulative_figure(
    windows: dict[str, tuple[dict[str, Any], list[Any]]], contrast: str, base: str, expanded: str
) -> str:
    title = f"RP4 · {expanded} sobre {base}"
    canvas = Canvas(
        1180,
        930,
        title,
        "Diferencia acumulada de QLIKE por sesión; "
        "positiva favorece al conjunto ampliado. Ambas familias y ventanas.",
        contrast,
    )
    header(
        canvas,
        "Resultados fuera de muestra walk-forward",
        title,
        "Suma de [QLIKE base − QLIKE ampliado]. Escalas independientes por familia y ventana.",
    )
    panels = [
        (column, row_index, window, rows, family, color)
        for column, (window, (_, rows)) in enumerate(windows.items())
        for row_index, (family, color) in enumerate(zip(FAMILIES, (INK, ACCENT), strict=True))
    ]
    for column, row_index, window, rows, family, color in panels:
        left, right = 90 + column * 565, 550 + column * 565
        top, bottom = 180 + row_index * 350, 440 + row_index * 350
        curve = [
            0.0,
            *accumulate(
                float(row[f"loss__{family}__{base}"]) - float(row[f"loss__{family}__{expanded}"])
                for row in rows
            ),
        ]
        low, high = min(curve), max(curve)
        padding = (high - low) * 0.08 if high > low else 1.0
        low, high = low - padding, high + padding

        def y(
            value: float, low: float = low, high: float = high, bottom: int = bottom, top: int = top
        ) -> float:
            return bottom - (value - low) / (high - low) * (bottom - top)

        canvas.front(
            f'<text x="{left}" y="{top - 43}" font-family="{SANS}" font-size="16" '
            f'fill="{INK}">{esc(LABELS[window])} · {esc(FAMILY_LABELS[family])}</text>'
            f'<text x="{left}" y="{top - 21}" font-family="{SANS}" font-size="12" '
            f'fill="{MUTED}">{len(rows)} sesiones · acumulado final {curve[-1]:+.7g}</text>'
        )
        for index in range(5):
            value = low + (high - low) * index / 4
            canvas.back(
                f'<line x1="{left}" y1="{y(value):.2f}" x2="{right}" '
                f'y2="{y(value):.2f}" stroke="{RULE}"/>'
            )
            canvas.front(
                f'<text x="{left - 9}" y="{y(value) + 4:.2f}" '
                f'text-anchor="end" font-family="{SANS}" font-size="11" '
                f'fill="{MUTED}">{value:.4g}</text>'
            )
        canvas.back(
            f'<line x1="{left}" y1="{y(0):.2f}" x2="{right}" '
            f'y2="{y(0):.2f}" stroke="{INK}" stroke-dasharray="4 4"/>'
        )
        path = " ".join(
            f"{'M' if index == 0 else 'L'} "
            f"{left + (right - left) * index / max(len(rows), 1):.2f} {y(value):.2f}"
            for index, value in enumerate(curve)
        )
        canvas.front(
            f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2" '
            f'data-family="{family}" data-window="{window}" '
            f'data-endpoint="{curve[-1]:.17g}"/>'
        )
        for position, label, anchor in (
            (left, rows[0]["session_date"] if rows else "Sin datos", "start"),
            (right, rows[-1]["session_date"] if rows else "", "end"),
        ):
            canvas.front(
                f'<text x="{position}" y="{bottom + 25}" text-anchor="{anchor}" '
                f'font-family="{SANS}" font-size="12" fill="{MUTED}">{esc(label)}</text>'
            )
    legend(canvas, 865, [(INK, FAMILY_LABELS[FAMILIES[0]]), (ACCENT, FAMILY_LABELS[FAMILIES[1]])])
    return canvas.render() + "\n"


def render_report(
    windows: dict[str, tuple[dict[str, Any], list[Any]]], label: str, audit: str
) -> str:
    parts = [
        "# RP4 — resultados v1",
        "",
        label + ".",
        "",
        "RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.",
        "",
        "Delta = QLIKE del conjunto base menos QLIKE del ampliado: positivo favorece "
        "al ampliado; negativo lo perjudica. Reducción (%) = 100 × delta / QLIKE base. "
        "Las medias dan igual peso a activos dentro de cada sesión y después a sesiones. "
        "Los intervalos son percentiles del bootstrap de bloques de 5 sesiones "
        "(9.999 réplicas); p bilateral centrado y Holm de cuatro contrastes por ventana.",
    ]
    for window, (summary, _) in windows.items():
        parts += [
            "",
            f"## {LABELS[window]}",
            "",
            f"Sesiones evaluadas: {summary.get('N_sessions', 0)}; "
            f"orígenes: {summary.get('N_origins', 0)}; "
            f"fechas: {summary.get('first_session', 'NO VERIFICABLE')} a "
            f"{summary.get('last_session', 'NO VERIFICABLE')}.",
            "",
        ]
        rows = [
            [
                FAMILY_LABELS[row["family"]],
                row["contrast"],
                number(row["estimate"], signed=True),
                f"[{number(row.get('ci_low'))}, {number(row.get('ci_high'))}]",
                number(row.get("p_raw")),
                number(row.get("p_holm")),
                number(row.get("qlike_reduction_percent"), signed=True),
                str(row["N_sessions"]),
                str(row["N_origins"]),
                str(row.get("N_asset_sessions", "NO VERIFICABLE")),
            ]
            for row in summary["contrasts"]
        ]
        parts.append(
            table(
                [
                    "Familia",
                    "Contraste",
                    "Estimación",
                    "IC 95 %",
                    "p crudo",
                    "p Holm",
                    "Reducción %",
                    "N sesiones",
                    "N orígenes",
                    "N activo-sesión",
                ],
                rows,
            )
        )
        if not rows:
            parts += ["", "NO VERIFICABLE: " + summary.get("reason", "sin contraste calculable")]
        for row in summary["contrasts"]:
            if row.get("status") != "COMPUTED":
                parts += [
                    "",
                    f"{row['family']} / {row['contrast']}: NO VERIFICABLE; "
                    + row.get("reason", "incertidumbre no calculable")
                    + ".",
                ]
        parts += [
            "",
            "### DM y GW por sesión",
            "",
            "GW se informa como diagnóstico HAC asintótico, sin atribuirle la garantía "
            "del test original de memoria fija.",
            "",
            table(
                ["Familia", "Contraste", "DM", "p DM", "GW", "p GW"],
                [
                    [
                        FAMILY_LABELS[row["family"]],
                        row["contrast"],
                        number(row.get("dm_hac_statistic")),
                        number(row.get("dm_hac_p_two_sided")),
                        number(row.get("gw_hac_diagnostic_statistic")),
                        number(row.get("gw_hac_diagnostic_p")),
                    ]
                    for row in summary["contrasts"]
                ],
            ),
            "",
            "### Mincer–Zarnowitz",
            "",
            table(
                [
                    "Modelo / conjunto",
                    "Intercepto",
                    "Pendiente",
                    "p conjunto a=0, b=1",
                    "N sesiones",
                ],
                [
                    [
                        name,
                        number(row.get("intercept")),
                        number(row.get("slope")),
                        number(row.get("joint_a0_b1_hac_p")),
                        str(row.get("N_sessions", "NO VERIFICABLE")),
                    ]
                    for name, row in summary.get("mincer_zarnowitz", {}).items()
                ],
            ),
            "",
            "### Secundarios predefinidos",
            "",
        ]
        secondary = summary.get("secondary", [])
        parts.append(
            table(
                [
                    "Subconjunto",
                    "Familia",
                    "Contraste",
                    "Delta",
                    "Reducción %",
                    "N sesiones",
                    "N orígenes",
                ],
                [
                    [
                        row["subset"],
                        FAMILY_LABELS[row["family"]],
                        row["contrast"],
                        number(row["estimate"], signed=True),
                        number(row.get("qlike_reduction_percent"), signed=True),
                        str(row["N_sessions"]),
                        str(row["N_origins"]),
                    ]
                    for row in secondary
                    if "estimate" in row
                ],
            )
        )
        memberships = {row["subset"]: row for row in secondary}
        if memberships:
            parts += [
                "",
                table(
                    ["Subconjunto", "Cobertura", "Membresía verificada", "Membresía desconocida"],
                    [
                        [
                            name,
                            row.get("coverage_status", row.get("status", "NO VERIFICABLE")),
                            str(row.get("N_verified_membership_origins", "NO VERIFICABLE")),
                            str(row.get("N_unknown_membership_origins", "NO VERIFICABLE")),
                        ]
                        for name, row in memberships.items()
                    ],
                ),
            ]
        for name, row in memberships.items():
            if row.get("status") == "NO VERIFICABLE":
                parts += [
                    "",
                    f"{name}: NO VERIFICABLE; {row.get('reason', 'sin membresía verificable')}.",
                ]
        parts += [
            "",
            "### Estabilidad: todos los signos",
            "",
            table(
                ["Subconjunto", "Familia", "B1 sobre B0", "B2 sobre B1"],
                [
                    [
                        subset,
                        FAMILY_LABELS[family],
                        *[
                            number(
                                next(
                                    (
                                        row["estimate"]
                                        for row in summary.get("robustness", [])
                                        if row.get("subset") == subset
                                        and row.get("family") == family
                                        and row.get("contrast") == contrast
                                    ),
                                    None,
                                ),
                                signed=True,
                            )
                            for contrast, _, _ in CONTRASTS
                        ],
                    ]
                    for subset in dict.fromkeys(
                        row["subset"] for row in summary.get("robustness", [])
                    )
                    for family in FAMILIES
                ],
            ),
            "",
            "### Exclusiones de calidad",
            "",
            "Los conteos de motivos se solapan; no deben sumarse como exclusiones disjuntas.",
            "",
            table(
                [
                    "Activo",
                    "Programados",
                    "Elegibles",
                    "Objetivo inválido",
                    "Predictor obligatorio incompleto",
                    "Gate fallido",
                ],
                [
                    [
                        row["asset"],
                        *[
                            str(row[key])
                            for key in (
                                "scheduled_rows",
                                "eligible_rows",
                                "invalid_target",
                                "incomplete_mandatory_predictors",
                                "failed_quality_gate",
                            )
                        ],
                    ]
                    for row in summary.get("evaluation_quality_by_asset", [])
                ],
            ),
            "",
            "Sesiones omitidas: "
            + (
                "; ".join(
                    f"{row['session']}: {row['reason']}"
                    for row in summary.get("skipped_sessions", [])
                )
                or "ninguna"
            )
            + ".",
        ]
    parts += [
        "",
        "## Evolución de pérdidas",
        "",
        "Cada figura muestra ambas familias y ambas ventanas, sin eliminar sesiones adversas.",
        "",
        "![B1 sobre B0, diferencia acumulada de QLIKE](../../artifacts/rp4_b4/B1_over_B0.svg)",
        "",
        "![B2 sobre B1, diferencia acumulada de QLIKE](../../artifacts/rp4_b4/B2_over_B1.svg)",
        "",
        "## Divulgación",
        "",
        "La ventana 20 de julio a 28 de agosto fue leída una vez por el puente de Fase 8 "
        "con otra especificación. "
        "El PIT es proxy de tiempo fuente a 120 s, como en la literatura.",
        "",
        "La lectura previa se atribuye al propietario y al protocolo del puente; no se presenta "
        "created_at como prueba de recepción por el cliente. Hueco aceptado de UW: "
        "2025-01-25 a 2025-02-24, sin relleno. La convención call largo / put corto y el OI "
        "del cierre previo no identifican posiciones observadas de dealers.",
        "",
        "Limitación: la exposición previa no desaparece al fijar la partición, el tiempo fuente "
        "y el posicionamiento son proxies, y la inferencia depende de supuestos de dependencia "
        "y aproximaciones asintóticas/bootstrap.",
        "",
        audit.strip(),
        "",
    ]
    return "\n".join(parts)


def run(args: argparse.Namespace) -> None:
    spec = load_spec(args.spec, args.spec_sha256)
    windows = {
        window: load_window(directory, args.spec_sha256)
        for window, directory in (("primary", args.primary), ("confirmation", args.confirmation))
    }
    bindings = [summary["binding"] for summary, _ in windows.values()]
    for field in ("evaluator_sha256", "imports_sha256"):
        if bindings[0][field] != bindings[1][field]:
            raise ValueError(f"RP4_REPORT_WINDOWS_BIND_DIFFERENT_{field.upper()}")
    if bindings[0]["panel_sha256"] != bindings[1]["panel_sha256"]:
        if args.panel_lineage is None:
            raise ValueError("RP4_REPORT_PANEL_PREFIX_PROOF_MISSING")
        lineage = json.loads(args.panel_lineage.read_text(encoding="utf-8"))
        if (
            lineage.get("development_panel_sha256") != bindings[0]["panel_sha256"]
            or lineage.get("combined_panel_sha256") != bindings[1]["panel_sha256"]
            or lineage.get("spec_sha256") != args.spec_sha256
            or lineage.get("development_prefix_equal_by_keys") is not True
        ):
            raise ValueError("RP4_REPORT_PANEL_PREFIX_PROOF_MISMATCH")
    for window, (summary, _) in windows.items():
        if summary["window"] != window or summary["result_label"] != spec["label"]:
            raise ValueError("RP4_REPORT_WINDOW_OR_LABEL_MISMATCH")
    paths = [
        args.spec,
        ROOT / "docs/rp4/specification_v1.md",
        args.audit,
        Path(__file__),
        ROOT / "scripts/figure_style.py",
    ]
    paths += [
        directory / name
        for directory in (args.primary, args.confirmation)
        for name in ("summary.json", "session_losses.csv")
    ]
    if args.panel_lineage is not None:
        paths.append(args.panel_lineage)
    for contrast, base, expanded in CONTRASTS:
        write_bytes_once(
            args.figures / f"{contrast}.svg",
            cumulative_figure(windows, contrast, base, expanded).encode(),
        )
    report = render_report(windows, spec["label"], args.audit.read_text(encoding="utf-8"))
    write_bytes_once(args.output, report.encode())
    outputs = [args.output, *(args.figures / f"{contrast}.svg" for contrast, _, _ in CONTRASTS)]
    write_json_once(
        args.figures / "report_manifest.json",
        {
            "specification_sha256": args.spec_sha256,
            "inputs_sha256": {str(path): sha256(path) for path in paths},
            "outputs_sha256": {str(path): sha256(path) for path in outputs},
            "raw_or_origin_data_read": False,
            "models_fitted": 0,
        },
    )
    print("RP4_B4_REPORT_RENDERED:" + sha256(args.output), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--spec-sha256", required=True)
    parser.add_argument("--primary", type=Path, required=True)
    parser.add_argument("--confirmation", type=Path, required=True)
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--panel-lineage", type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "docs/rp4/results_v1.md")
    parser.add_argument("--figures", type=Path, default=ROOT / "artifacts/rp4_b4")
    run(parser.parse_args())
