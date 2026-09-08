"""Render completed RV15/RV5 releases against immutable v3; never fit models."""
# Long literals are generated Markdown/SVG, including complete links and attributes.
# ruff: noqa: E501

from __future__ import annotations

import argparse
import html
import statistics
import subprocess
import sys
from datetime import date
from itertools import accumulate
from pathlib import Path
from typing import Any

from artifacts.rp4_code.evaluate import sha256, write_bytes_once, write_json_once
from artifacts.rp4_v3_code import inference as inf
from artifacts.rp4_v3_code.report_v3 import (
    _close,
    csv_bytes,
    differences,
    number,
    read_csv,
    read_json,
    table,
)

ROOT = Path(__file__).resolve().parents[2]
WINDOWS = ("primary", "confirmation")
LABELS = {30: "v3 RV30", 15: "v4 RV15 primario", 5: "v4 RV5 secundario"}
SPEC_SHA = "0a45b0a608110e2ca0dcf38accc2a0c2521ebbe9d223eb002e36ec51f78afd04"
V3_PINS = {
    "artifacts/rp4_v3_b2/summary.json": "645d319f4b5b283a2b1bc6ecda1a185650b8436cdbf3b319e9debfc41210ef1d",
    "artifacts/rp4_v3_b3/summary.json": "64af964691d1127df7b3e2e0f05395c810719f2fe4e5ba3fa0207fcc8e15591b",
    "artifacts/rp4_v3_b2/session_losses.csv": "8eb70bfe30c60a9cc1dd6802dd711e506cb4582ae172fdfbe9fee9f9ddc5064f",
    "artifacts/rp4_v3_b3/session_losses.csv": "1798a86cde522b2e7e44bbd69dc758da40ff15ba62c951eea2032100d2782725",
    "docs/rp4/results_v3.md": "86703434ae2d1d8e2ef3a9c59ae9737f3a4e4c8460234076b794e04ac2deee1f",
}
type Rows = list[dict[str, Any]]
type Results = dict[tuple[int, str], tuple[dict[str, Any], Rows]]


def verify_receipt_identity(receipt: dict[str, Any], horizon: int, window: str) -> None:
    """Require the exact completed launcher step before reading any result payload."""
    stage = "B2" if window == "primary" else "B3"
    fields = ("status", "exit_code", "stage", "window", "horizon_minutes", "target_key")
    if tuple(receipt.get(key) for key in fields) != (
        "COMPLETE",
        0,
        stage,
        window,
        horizon,
        f"rv_{horizon}",
    ):
        raise ValueError("RP4_V4_REPORT_RECEIPT_IDENTITY")
    common = [
        sys.executable,
        "-B",
        "-m",
        "artifacts.rp4_v4_code.evaluate_v4",
        "--spec",
        str(ROOT / "artifacts/rp4_v4_a1/specification.json"),
        "--spec-sha256",
        SPEC_SHA,
        "--release",
        str(ROOT / "artifacts/rp4_v4_a2" / f"evaluation_release_rv{horizon}.json"),
        "--horizon",
        str(horizon),
        "--window",
        window,
        "--threads",
        "4",
        "--shard-count",
        "8",
    ]
    expected = [
        subprocess.list2cmdline(common + ["--shard-index", str(index)]) for index in range(8)
    ]
    expected.append(subprocess.list2cmdline(common + ["--aggregate-only"]))
    commands = receipt.get("commands", [])
    if [command.get("command") for command in commands] != expected or any(
        command.get("exit_code") != 0 for command in commands
    ):
        raise ValueError("RP4_V4_REPORT_COMMAND_IDENTITY")


def timing_row(receipt: dict[str, Any], horizon: int, window: str) -> dict[str, Any]:
    """Export observed host resources literally; absent measurements remain unavailable."""
    resources = receipt.get("resources", {})
    return {
        "horizon_minutes": horizon,
        "window": window,
        "started_at_utc": receipt.get("started_at_utc"),
        "completed_at_utc": receipt.get("completed_at_utc"),
        "elapsed_seconds": receipt.get("elapsed_seconds"),
        **{
            key: resources.get(key)
            for key in (
                "logical_cpu_count",
                "physical_memory_bytes",
                "memory_status",
                "os",
                "session_shards",
                "threads_per_model",
                "maximum_model_threads",
                "blas_threads_per_child",
            )
        },
    }


def verify_results(summary: dict[str, Any], rows: Rows, horizon: int, window: str) -> None:
    if summary.get("status") != "COMPUTED" or summary["window"] != window or not rows:
        raise ValueError("RP4_V4_REPORT_INCOMPLETE_WINDOW")
    dates = [row["session_date"] for row in rows]
    if dates != sorted(set(dates)) or len(dates) != summary["N_sessions"]:
        raise ValueError("RP4_V4_REPORT_SESSION_ORDER_OR_COUNT")
    if horizon != 30 and (
        summary["binding"]["specification_sha256"] != SPEC_SHA
        or summary["horizon_minutes"] != horizon
        or summary["target_key"] != f"rv_{horizon}"
    ):
        raise ValueError("RP4_V4_REPORT_WRONG_TARGET")
    if set(summary["completed_session_sha256"]) != {day + ".json" for day in dates}:
        raise ValueError("RP4_V4_REPORT_SESSION_RECEIPT_SET")
    expected = {(f, c) for f in inf.FAMILIES for c, _, _ in inf.CONTRASTS}
    if {(r["family"], r["contrast"]) for r in summary["contrasts"]} != expected:
        raise ValueError("RP4_V4_REPORT_CONTRAST_SET")
    for item in summary["contrasts"]:
        _, base, richer = next(c for c in inf.CONTRASTS if c[0] == item["contrast"])
        delta = differences(rows, item["family"], base, richer)
        _close(item["estimate"], statistics.mean(delta), "V4_ESTIMATE")
        baseline = statistics.mean(float(r[f"loss__{item['family']}__{base}"]) for r in rows)
        _close(
            item["qlike_reduction_percent"], 100 * statistics.mean(delta) / baseline, "V4_PERCENT"
        )
        if item["N_sessions"] != len(rows) or item["N_origins"] != summary["N_origins"]:
            raise ValueError("RP4_V4_REPORT_CONTRAST_N")
    recomputed = inf.family_fixed_sequence(summary["contrasts"], primary=horizon != 5)
    for left, right in zip(recomputed["contrasts"], summary["contrasts"], strict=True):
        for key in ("rejected", "p_for_decision", "hypothesis_status"):
            if left[key] != right[key]:
                raise ValueError("RP4_V4_REPORT_FIXED_SEQUENCE")


def main_table(results: Results, window: str) -> str:
    headers = ["Familia / contraste"]
    for h in LABELS:
        headers += [
            f"{LABELS[h]} Δ [IC95%]",
            "p unilateral / formal",
            "% QLIKE",
            "N sesiones/orígenes",
        ]
    output = []
    for family in inf.FAMILIES:
        for contrast, _, _ in inf.CONTRASTS:
            row = [("Ridge" if family == inf.FAMILIES[0] else "LightGBM") + " / " + contrast]
            for h in LABELS:
                summary, _ = results[h, window]
                item = next(
                    x
                    for x in summary["contrasts"]
                    if (x["family"], x["contrast"]) == (family, contrast)
                )
                formal = (
                    number(item["p_for_decision"])
                    if item["p_for_decision"] is not None
                    else "NO ABIERTA"
                    if item["hypothesis_status"] == "NOT_TESTED"
                    else "NO VERIFICABLE"
                )
                row += [
                    f"{number(item['estimate'], signed=True)} [{number(item['ci_low'])}, {number(item['ci_high'])}]",
                    number(item["p_raw"]) + " / " + formal,
                    number(item["qlike_reduction_percent"], signed=True),
                    f"{item['N_sessions']}/{item['N_origins']}",
                ]
            output.append(row)
    return table(headers, output)


def figure(results: Results, contrast: str, base: str, richer: str) -> str:
    out = [
        '<svg xmlns="http://www.w3.org/2000/svg" width="1680" height="1320" viewBox="0 0 1680 1320" role="img">',
        f"<title>RP4 v3 y v4: {html.escape(contrast)}</title>",
        "<desc>Doce paneles con fechas reales y escalas independientes; todas las sesiones, sin recortes.</desc>",
        '<rect width="100%" height="100%" fill="white"/><g font-family="Segoe UI,Arial,sans-serif" fill="#182333">',
        f'<text x="65" y="38" font-size="23">{html.escape(contrast)} · QLIKE acumulado base − ampliado</text>',
        '<text x="65" y="65" font-size="13">Horizontes distintos; escalas independientes. Valores positivos favorecen al conjunto rico.</text>',
    ]
    for col, horizon in enumerate(LABELS):
        for wi, window in enumerate(WINDOWS):
            for fi, family in enumerate(inf.FAMILIES):
                rows = results[horizon, window][1]
                values = [0.0, *accumulate(differences(rows, family, base, richer))]
                left, right = 85 + col * 550, 500 + col * 550
                top, bottom = 137 + (wi * 2 + fi) * 294, 342 + (wi * 2 + fi) * 294
                low, high = min(values), max(values)
                pad = 0.08 * (high - low) if high > low else 1.0
                low, high = low - pad, high + pad

                def y(
                    value: float,
                    low: float = low,
                    high: float = high,
                    top: int = top,
                    bottom: int = bottom,
                ) -> float:
                    return bottom - (value - low) * (bottom - top) / (high - low)

                title = f"{LABELS[horizon]} · {window} · {'Ridge' if fi == 0 else 'LightGBM'}"
                out += [
                    f'<text x="{left}" y="{top - 30}" font-size="14">{html.escape(title)}</text>',
                    f'<text x="{left}" y="{top - 10}" font-size="12">N={len(rows)} · final {values[-1]:+.8g}</text>',
                ]
                for tick in range(5):
                    value = low + (high - low) * tick / 4
                    out += [
                        f'<line x1="{left}" x2="{right}" y1="{y(value):.2f}" y2="{y(value):.2f}" stroke="#e2e6ec"/>',
                        f'<text x="{left - 8}" y="{y(value) + 4:.2f}" text-anchor="end" font-size="10">{value:.4g}</text>',
                    ]
                out.append(
                    f'<line x1="{left}" x2="{right}" y1="{y(0):.2f}" y2="{y(0):.2f}" stroke="#6a7685" stroke-dasharray="4 3"/>'
                )
                days = [date.fromisoformat(row["session_date"]).toordinal() for row in rows]
                times = [days[0] - 1, *days]
                path = " ".join(
                    f"{'M' if i == 0 else 'L'} {left + (right - left) * (day - times[0]) / (times[-1] - times[0]):.2f} {y(value):.2f}"
                    for i, (day, value) in enumerate(zip(times, values, strict=True))
                )
                color = {30: "#657388", 15: "#146a94", 5: "#aa652b"}[horizon]
                out += [
                    f'<path d="{path}" fill="none" stroke="{color}" stroke-width="2" data-horizon="{horizon}" data-window="{window}" data-family="{family}" data-endpoint="{values[-1]:.17g}" data-sessions="{len(rows)}"/>',
                    f'<text x="{left}" y="{bottom + 20}" font-size="11">{rows[0]["session_date"]}</text>',
                    f'<text x="{right}" y="{bottom + 20}" text-anchor="end" font-size="11">{rows[-1]["session_date"]}</text>',
                ]
    return "\n".join(out + ["</g></svg>", ""])


def fit_rows(records: Rows, horizon: int, window: str) -> Rows:
    output = []
    for r in records:
        endpoint, family, name = r["model"].split("__")
        if endpoint != "mean" or r["target_key"] != f"rv_{horizon}":
            raise ValueError("RP4_V4_REPORT_FIT_ENDPOINT")
        selected = r["selected"]
        if len(r["inner_valid_sessions"]) != 10 or max(r["inner_valid_sessions"]) >= r["session"]:
            raise ValueError("RP4_V4_REPORT_NONCAUSAL_TUNING")
        bounds = r.get("bounds", {}).get("refit", {})
        output.append(
            {
                "horizon_minutes": horizon,
                "window": window,
                "session": r["session"],
                "family": family,
                "information_set": name,
                "selected_lambda": selected.get("lambda"),
                "selected_leaves": selected.get("num_leaves"),
                "selected_rounds": selected.get("rounds"),
                "train_rows": r["train_rows"],
                "inner_fit_rows": r["inner_fit_rows"],
                "inner_valid_rows": r["inner_valid_rows"],
                "validation_qlike": selected["validation_qlike"],
                "prediction_rows": r.get("prediction_rows"),
                "count_low": r.get("count_low"),
                "count_high": r.get("count_high"),
                "validation_rows": selected.get("prediction_rows"),
                "validation_count_low": selected.get("count_low"),
                "validation_count_high": selected.get("count_high"),
                "lower": bounds.get("lower"),
                "upper": bounds.get("upper"),
                "percentile_1": bounds.get("percentile_1"),
                "percentile_99": bounds.get("percentile_99"),
            }
        )
    return output


def bound_rows(records: Rows) -> Rows:
    """Count phase-specific ridge hits; missing counters never become zeros."""
    output = []
    groups = sorted(
        {
            (r["horizon_minutes"], r["window"], r["information_set"])
            for r in records
            if r["family"] == "log_ridge_harq"
        }
    )
    for horizon, window, name in groups:
        rows = [
            r
            for r in records
            if (r["horizon_minutes"], r["window"], r["information_set"], r["family"])
            == (horizon, window, name, "log_ridge_harq")
        ]
        for phase, keys in (
            ("evaluation", ("prediction_rows", "count_low", "count_high")),
            ("validation", ("validation_rows", "validation_count_low", "validation_count_high")),
        ):
            known = all(r.get(k) is not None for r in rows for k in keys)
            totals = [sum(int(r[k]) for r in rows) for k in keys] if known else [None] * 3
            if known and any(
                int(r[keys[0]]) < int(r[keys[1]]) + int(r[keys[2]])
                or any(float(r[k]) < 0 or float(r[k]) != int(r[k]) for k in keys)
                for r in rows
            ):
                raise ValueError("RP4_V4_REPORT_BOUND_COUNTS_INVALID")
            output.append(
                {
                    "horizon_minutes": horizon,
                    "window": window,
                    "information_set": name,
                    "phase": phase,
                    "N_predictions": totals[0],
                    "count_low": totals[1],
                    "count_high": totals[2],
                    "status": "COMPUTED" if known else "NO VERIFICABLE",
                }
            )
    return output


def run() -> dict[str, Any]:
    spec_path = ROOT / "artifacts/rp4_v4_a1/specification.json"
    if sha256(spec_path) != SPEC_SHA:
        raise ValueError("RP4_V4_REPORT_SPEC_HASH")
    spec = read_json(spec_path)
    private = Path(spec["data_root"])
    out = ROOT / "artifacts/rp4_v4_b4"
    input_pins = dict(V3_PINS)
    input_pins[str(spec_path)] = SPEC_SHA
    results: Results = {}
    receipt_times: Rows = []
    for legacy_path, digest in V3_PINS.items():
        if sha256(ROOT / legacy_path) != digest:
            raise ValueError("RP4_V4_REPORT_LEGACY_HASH:" + legacy_path)
    artifacts: dict[str, bytes] = {}
    fits: Rows = []
    all_stats: Rows = []
    secondary: dict[str, Rows] = {
        key: []
        for key in (
            "distribution_secondary",
            "posterior_mean",
            "regime_secondary",
            "high_gamma_vs_rest",
            "top_loss_sessions",
            "robustness",
        )
    }
    coverage: Rows = []
    census: Rows = []
    for horizon in LABELS:
        for window in WINDOWS:
            stage = "b2" if window == "primary" else "b3"
            folder = (
                ROOT
                / "artifacts"
                / (f"rp4_v3_{stage}" if horizon == 30 else f"rp4_v4_{stage}_rv{horizon}")
            )
            if horizon != 30:
                receipt = read_json(folder / "receipt.json")
                verify_receipt_identity(receipt, horizon, window)
                diag_path = (
                    private / "evaluation" / f"rv{horizon}" / window / "fit_diagnostics.json"
                )
                required = {
                    (folder / "summary.json").resolve(),
                    (folder / "session_losses.csv").resolve(),
                    diag_path.resolve(),
                }
                received = {Path(k).resolve(): v for k, v in receipt["artifacts_sha256"].items()}
                if set(received) != required or any(sha256(p) != received[p] for p in required):
                    raise ValueError("RP4_V4_REPORT_REQUIRED_ARTIFACT_PINS")
            summary, losses = (
                read_json(folder / "summary.json"),
                read_csv(folder / "session_losses.csv"),
            )
            if horizon != 30:
                if receipt.get("status") != "COMPLETE" or receipt.get("exit_code") != 0:
                    raise ValueError("RP4_V4_REPORT_UNCLOSED_STAGE")
                release_path = ROOT / "artifacts/rp4_v4_a2" / f"evaluation_release_rv{horizon}.json"
                release = read_json(release_path)
                if (
                    sha256(release_path) != receipt["release_sha256"]
                    or summary["binding"]["release_sha256"] != receipt["release_sha256"]
                    or receipt["evaluation_code_sha256"] != release["evaluation_code_sha256"]
                ):
                    raise ValueError("RP4_V4_REPORT_RELEASE_BINDING")
                for source, digest in release["evaluation_code_sha256"].items():
                    if sha256(ROOT / source) != digest:
                        raise ValueError("RP4_V4_REPORT_EVALUATOR_CHANGED")
                    input_pins[source] = digest
                commands = receipt["commands"]
                if len(commands) != 9 or any(r["exit_code"] != 0 for r in commands):
                    raise ValueError("RP4_V4_REPORT_COMMAND_SET")
                for command in commands:
                    if sha256(Path(command["log"])) != command["log_sha256"]:
                        raise ValueError("RP4_V4_REPORT_EXECUTION_LOG_CHANGED")
                input_pins[str(release_path)] = sha256(release_path)
                pins = receipt["artifacts_sha256"]
                for source, digest in pins.items():
                    path = Path(source)
                    path = path if path.is_absolute() else ROOT / path
                    if not path.resolve().is_relative_to(
                        ROOT
                    ) and not path.resolve().is_relative_to(private):
                        raise ValueError("RP4_V4_REPORT_PATH_OUTSIDE_SCOPE")
                    if sha256(path) != digest:
                        raise ValueError("RP4_V4_REPORT_RECEIPT_DRIFT:" + str(path))
                    input_pins[str(path)] = digest
                input_pins[str(folder / "receipt.json")] = sha256(folder / "receipt.json")
                receipt_times.append(timing_row(receipt, horizon, window))
                diag_path = (
                    private / "evaluation" / f"rv{horizon}" / window / "fit_diagnostics.json"
                )
                input_pins[str(diag_path)] = sha256(diag_path)
                fits.extend(fit_rows(read_json(diag_path), horizon, window))
                for key in secondary:
                    secondary[key].extend(
                        {"horizon_minutes": horizon, "window": window, **r} for r in summary[key]
                    )
                census.extend(
                    {"horizon_minutes": horizon, "window": window, **r}
                    for r in summary["empty_window_secondary"]["census"]
                )
            verify_results(summary, losses, horizon, window)
            results[horizon, window] = summary, losses
            bilateral = {
                (r["family"], r["contrast"]): r for r in summary["comparability_bilateral"]
            }
            for r in summary["contrasts"]:
                legacy = bilateral[r["family"], r["contrast"]]
                all_stats.append(
                    {
                        "horizon_minutes": horizon,
                        "window": window,
                        **r,
                        "p_bilateral": legacy["p_raw"],
                        "p_holm_bilateral": legacy["p_holm"],
                    }
                )
            coverage.extend(
                {"horizon_minutes": horizon, "window": window, **r}
                for r in summary["evaluation_quality_by_asset"]
            )
    bounds = bound_rows(fits)
    for name, rows in {
        "primary_statistics": all_stats,
        "coverage": coverage,
        "empty_census": census,
        "fit_selection_bounds": fits,
        "bound_counts": bounds,
        "timing": receipt_times,
        **secondary,
    }.items():
        artifacts[name + ".csv"] = csv_bytes(rows)
    for contrast, base, richer in inf.CONTRASTS:
        artifacts[contrast + ".svg"] = figure(results, contrast, base, richer).encode("utf-8")
    winning = [
        f
        for f in inf.FAMILIES
        if all(r["rejected"] for r in results[15, "primary"][0]["contrasts"] if r["family"] == f)
    ]
    text = [
        "# RP4 v4 — cierre final del horizonte del flujo",
        "",
        spec["label"] + ".",
        "RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.",
        "## Resultado y regla de cierre",
        "",
        (
            "RV15 satisface H1 → H2 en: "
            + ", ".join(winning)
            + ". Se reporta el alcance por familia; RV5 no decide el resultado."
            if winning
            else "RV15 no satisface H1 → H2 en ninguna familia. Se cierra este intento: B1>B0 observado en la primaria de 30 minutos sigue siendo el resultado principal; la evidencia de B2 se informa por horizonte sin afirmar equivalencia a cero."
        ),
        "No hay v5. La regla de al menos una familia es operativa; no implica control global 5% entre familias ni versiones.",
        "## Comparación primaria",
        "",
        main_table(results, "primary"),
        "## Comparación de confirmación",
        "",
        main_table(results, "confirmation"),
        "Delta positivo favorece al conjunto rico. IC95% percentil bilateral; p unilateral de nula centrada. H2 NO ABIERTA significa que H1 no rechazó; su p nominal no es una prueba formal. Las dos ventanas se informan separadas, no se suman como replicaciones independientes.",
        "En las decisiones, rechazo significa rechazo de la nula delta≤0, es decir evidencia a favor del incremento; no rechazo de la ventaja como hipótesis sustantiva.",
        "[Estadísticas completas, p bilateral y Holm, DM/GW y decisiones](../../artifacts/rp4_v4_b4/primary_statistics.csv). Reducción % = 100 × media de diferencias por sesión / media de QLIKE base. Los horizontes tienen objetivos distintos.",
        "## Cobertura de la muestra",
        "",
        table(
            ["Horizonte", "Ventana", "Activo", "Programados", "Elegibles", "%"],
            [
                [
                    str(r["horizon_minutes"]),
                    r["window"],
                    r["asset"],
                    str(r["scheduled_rows"]),
                    str(r["eligible_rows"]),
                    number(100 * r["eligible_rows"] / r["scheduled_rows"]),
                ]
                for r in coverage
            ],
        ),
        "[Conteos y causas](../../artifacts/rp4_v4_b4/coverage.csv). Máscara y entrenamiento de v3 conservados; RV15/RV5 no incorporan nuevos orígenes por ser más cortos.",
        "## Secundarios registrados, no promovibles",
        "",
    ]
    for horizon in (15, 5):
        for window in WINDOWS:
            summary = results[horizon, window][0]
            text += [
                f"### RV{horizon} · {window}",
                "",
                table(
                    [
                        "Familia",
                        "Contraste",
                        "Estadístico",
                        "Delta",
                        "IC95%",
                        "p bilateral",
                        "Holm",
                        "N",
                    ],
                    [
                        [
                            r["family"],
                            r["contrast"],
                            r["statistic"],
                            number(r["estimate"], signed=True),
                            f"[{number(r['ci_low'])}, {number(r['ci_high'])}]",
                            number(r["p_raw"]),
                            number(r["p_holm"]),
                            str(r["N_sessions"]),
                        ]
                        for r in summary["distribution_secondary"]
                    ],
                ),
                table(
                    ["Familia", "Contraste", "P(delta>0) condicional", "HAC SE", "N"],
                    [
                        [
                            r["family"],
                            r["contrast"],
                            number(r.get("probability_positive")),
                            number(r.get("HAC_SE")),
                            str(r["N_sessions"]),
                        ]
                        for r in summary["posterior_mean"]
                    ],
                ),
            ]
    text += [
        "La posterior es una aproximación gaussiana con varianza HAC plug-in: no integra la incertidumbre de esa varianza. Mediana pareada no equivale a diferencia de medianas; recorte 5% por cada cola sólo en el secundario.",
        "[Todos los regímenes con N, desconocidos, intervalos y p](../../artifacts/rp4_v4_b4/regime_secondary.csv) · [Activos, bloques, retiradas y últimas 30 sesiones](../../artifacts/rp4_v4_b4/robustness.csv) · [Interacción alto gamma frente al resto](../../artifacts/rp4_v4_b4/high_gamma_vs_rest.csv). Se conservan primera/última hora, viernes calendario, tercer viernes, alto flujo, eventos y ventanas vacías/no vacías; no se promueve un estrato favorable.",
        "## Ventanas vacías y cotas",
        "",
        table(
            [
                "RV",
                "Ventana",
                "Ventana flujo",
                "Activo",
                "N",
                "Vacías",
                "No vacías",
                "Desconocidas",
            ],
            [
                [
                    str(r["horizon_minutes"]),
                    r["window"],
                    r["horizon"],
                    r["asset"],
                    str(r["N_origins"]),
                    str(r["N_empty_origins"]),
                    str(r["N_nonempty_origins"]),
                    str(r["N_unknown_origins"]),
                ]
                for r in census
            ],
        ),
        "El contraste B2/B1 dentro y fuera de los vacíos está en el CSV de regímenes, con intervalos y N; ningún origen sale por estar vacío.",
        "[Rondas/hojas/lambda, cotas y contactos de cada sesión](../../artifacts/rp4_v4_b4/fit_selection_bounds.csv). Cotas calculadas únicamente con P1/P99 del objetivo de entrenamiento del horizonte correspondiente.",
        table(
            ["RV", "Ventana", "Ridge", "Fase", "N pronósticos", "Cota inferior", "Cota superior"],
            [
                [
                    str(r["horizon_minutes"]),
                    r["window"],
                    r["information_set"],
                    r["phase"],
                    number(r["N_predictions"]),
                    number(r["count_low"]),
                    number(r["count_high"]),
                ]
                for r in bounds
            ],
        ),
        "Los denominadores de validación suman aplicaciones en ajustes sucesivos, no orígenes únicos. [Conteos de cotas](../../artifacts/rp4_v4_b4/bound_counts.csv).",
        "## Días extremos",
        "",
    ]
    for horizon in (15, 5):
        for window in WINDOWS:
            rows = [
                r
                for r in secondary["top_loss_sessions"]
                if r["horizon_minutes"] == horizon
                and r["window"] == window
                and r["ranked_information_set"] == "B2"
            ]
            text += [
                f"### RV{horizon} · {window}: diez mayores pérdidas B2 por familia",
                "",
                table(
                    [
                        "Familia",
                        "Día",
                        "Rango",
                        "QLIKE B0",
                        "QLIKE B1",
                        "QLIKE B2",
                        "Delta B1/B0",
                        "Delta B2/B1",
                    ],
                    [
                        [
                            r["family"],
                            r["session_date"],
                            str(r["rank"]),
                            number(r["qlike_B0"]),
                            number(r["qlike_B1"]),
                            number(r["qlike_B2"]),
                            number(r["B1_over_B0"], signed=True),
                            number(r["B2_over_B1"], signed=True),
                        ]
                        for r in rows
                    ],
                ),
            ]
    text += [
        "[Diez extremos por cada familia y cada conjunto, incluidos B0 y B1](../../artifacts/rp4_v4_b4/top_loss_sessions.csv). Todos los signos se conservan.",
        "## Evolución acumulada",
        "",
        "![B1 sobre B0](../../artifacts/rp4_v4_b4/B1_over_B0.svg)",
        "![B2 sobre B1](../../artifacts/rp4_v4_b4/B2_over_B1.svg)",
        "## Datos, ejecución y trazabilidad",
        "",
        "[Validación de RV15/RV5](../../artifacts/rp4_v4_a2/REPORT.md) · [Especificación congelada](specification_v4.md) · [Decisión 133](decision_133_v4.md). La confirmación no tiene referencia previa de RV15/RV5; no se afirma paridad con un archivo inexistente.",
        "Ocho shards disjuntos × cuatro hilos, entrenamiento completo pasado por shard. Sin ensayo adicional sobre evaluación, descargas o publicación. [Tiempos reales y recursos observados: CPU lógica, RAM y límites de hilos](../../artifacts/rp4_v4_b4/timing.csv). Los releases y recibos de las cuatro ejecuciones están vinculados en el manifiesto del informe.",
        "## Divulgación y cierre",
        "",
        "Esta es la cuarta evaluación de las mismas ventanas: v1 diseño inicial; v2 cobertura/capacidad/regularización; v3 mecanismo y ventanas vacías; v4 horizonte condicional predeclarado. RV5 es un endpoint secundario de v4, no una quinta versión ni réplica independiente. Los p dentro de una versión no corrigen toda la búsqueda anterior.",
        "La ventana 20 de julio a 28 de agosto fue leída una vez por el puente de Fase 8 con otra especificación. El PIT es proxy de tiempo fuente a 120 s, como en la literatura.",
        "Hueco UW aceptado: 2025-01-25 a 2025-02-24, sin relleno. El inventario de dealers y la disponibilidad histórica al cliente no están observados directamente. Un resultado no rechazado no demuestra ausencia o absorción; los intervalos delimitan lo medido.",
        "[v3 intacto](results_v3.md) · [Cierre de secundarios v3](results_v3_revision1.md) · [Manifiesto y hashes](../../artifacts/rp4_v4_b4/report_manifest.json). La primaria v3 no depende de reparar sus secundarios.",
    ]
    report = "\n\n".join(text) + "\n"
    for name, content in artifacts.items():
        write_bytes_once(out / name, content)
    write_bytes_once(ROOT / "docs/rp4/results_v4.md", report.encode("utf-8"))
    output_hashes = {str((out / name).relative_to(ROOT)): sha256(out / name) for name in artifacts}
    output_hashes["docs/rp4/results_v4.md"] = sha256(ROOT / "docs/rp4/results_v4.md")
    manifest = {
        "status": "RP4_V4_REPORT_COMPLETE",
        "input_sha256": input_pins,
        "output_sha256": output_hashes,
        "report_code_sha256": sha256(Path(__file__)),
        "rv15_primary_winning_families": winning,
        "model_fits": 0,
        "downloads": 0,
        "publication": False,
    }
    write_json_once(out / "report_manifest.json", manifest)
    return manifest


if __name__ == "__main__":
    argparse.ArgumentParser(description=__doc__).parse_args()
    import json

    print(json.dumps(run(), sort_keys=True))
