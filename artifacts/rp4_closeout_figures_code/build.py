"""New comparison figures from completed, hash-pinned summaries only."""
# Long lines are literal SVG, display labels, provenance pins, and generated prose.
# ruff: noqa: E501

from __future__ import annotations

import argparse
import hashlib
import html
import json
import math
import os
import statistics
import struct
import subprocess
import time
from datetime import UTC, date, datetime
from itertools import accumulate
from pathlib import Path
from typing import Any

from artifacts.rp4_v3_code.report_v3 import (
    _close,
    csv_bytes,
    differences,
    read_csv,
    read_json,
    validate_window,
)
from artifacts.rp4_v4_code import report_v4_checked as checked
from scripts.figure_style import INK, MUTED, PAPER_2, RULE, SANS, Canvas

ROOT = Path(__file__).resolve().parents[2]
OUT = Path("artifacts/rp4_closeout_figures")
FIGURES = Path("docs/figures/rp4")
CODE = Path("artifacts/rp4_closeout_figures_code")
COMMAND = (
    "uv run --offline --frozen --no-sync python -B -m artifacts.rp4_closeout_figures_code.build"
)
MANIFEST_PINS = {
    "artifacts/rp4_v2_b4/report_manifest.json": "2ba6b2611be4a4dd1e0cfd031a5f50680c96d665f603386522a9af0c21610083",
    "artifacts/rp4_v4_b4/report_manifest.json": "a387b789158b78232b29911ae63638a0367ae3acb5a21e5672dbcfaec4cba56f",
}
HELPER_PINS = {
    "artifacts/rp4_v3_code/report_v3.py": "bb5b7d574207e8307a1b31800e689166583851161365fd94b689f94fce7be356",
    "artifacts/rp4_v4_code/report_v4_checked.py": "17c0c0fc67336aa945db9c156bf6f0e1043206391e3d3f0bb5873382c0424c7c",
    "scripts/figure_style.py": "139d363fbafb9f85b130114504f9d4036a2b5080dc6e1d2741014b84151042a6",
}
SERIES = (("v1", 30), ("v2", 30), ("v3", 30), ("v4", 15), ("v4", 5))
WINDOWS = ("primary", "confirmation")
WINDOW_LABEL = {"primary": "Primaria", "confirmation": "Confirmación"}
FAMILIES = ("log_ridge_harq", "lightgbm_qlike")
FAMILY_LABEL = {"log_ridge_harq": "Ridge", "lightgbm_qlike": "LightGBM"}
COLORS = {"log_ridge_harq": "#0072B2", "lightgbm_qlike": "#D55E00"}
CONTRASTS = (("B1_over_B0", "B0", "B1"), ("B2_over_B1", "B1", "B2"))
EVENTS = (
    ("2025-04-07", "A", "semana arancelaria; contexto, no causalidad"),
    ("2025-04-09", "A", "semana arancelaria; contexto, no causalidad"),
    ("2025-05-15", "B", "indisponibilidad del proveedor"),
    ("2025-09-17", "C", "FOMC"),
    ("2025-09-18", "D", "indisponibilidad del proveedor"),
    ("2026-06-17", "E", "FOMC"),
    ("2026-08-31", "F", "AMZN: choque observado; noticia/earnings no demostrados"),
)
# Public identifiers excluded by the publication contract, encoded for the guard itself.
EXCLUDED_WORDS = tuple(
    bytes.fromhex(value).decode("ascii")
    for value in (
        "636f646578",
        "636c61756465",
        "63686174677074",
        "6167656e7465",
        "6d6473363530",
        "63617073746f6e65",
    )
)
type Rows = list[dict[str, Any]]
type Results = dict[tuple[str, int, str], tuple[dict[str, Any], Rows]]


def digest(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def public_guard(data: bytes) -> None:
    text = data.decode("utf-8").lower()
    if any(word in text for word in EXCLUDED_WORDS):
        raise ValueError("PUBLIC_IDENTITY_TOKEN")
    if ":\\" in text or ":/users/" in text or ":/artifacts/" in text:
        raise ValueError("PUBLIC_ABSOLUTE_PATH")


def write_new(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != content:
            raise FileExistsError("OUTPUT_ALREADY_EXISTS:" + path.name)
        return
    with path.open("xb") as stream:
        stream.write(content)


def json_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def finite(value: Any) -> float:
    if value is None or isinstance(value, bool):
        raise ValueError("FINITE_NUMBER_REQUIRED")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("FINITE_NUMBER_REQUIRED")
    return result


def percent_interval(delta: Any, low: Any, high: Any, baseline: Any) -> tuple[float, ...]:
    """Rescale the saved difference interval; do not estimate a ratio interval."""
    d, lo, hi, base = map(finite, (delta, low, high, baseline))
    if base <= 0 or lo > hi:
        raise ValueError("INVALID_DENOMINATOR_OR_INTERVAL")
    return 100 * d / base, 100 * lo / base, 100 * hi / base


def pinned_input(path: Path, manifest: dict[str, Any]) -> str:
    """Locate a path in either frozen report schema without exporting private paths."""
    pins = manifest.get("input_sha256", manifest.get("inputs_sha256", {}))
    selected = []
    for name, expected in pins.items():
        candidate = Path(name)
        candidate = candidate if candidate.is_absolute() else ROOT / candidate
        if candidate.resolve() == path.resolve():
            selected.append(expected)
    if len(selected) != 1 or digest(path) != selected[0]:
        raise ValueError("FROZEN_INPUT_HASH:" + path.name)
    return str(selected[0])


def source_folder(version: str, horizon: int, window: str) -> Path:
    stage = "b2" if window == "primary" else "b3"
    prefix = "rp4" if version == "v1" else f"rp4_{version}"
    suffix = f"_rv{horizon}" if version == "v4" else ""
    return Path("artifacts") / f"{prefix}_{stage}{suffix}"


def load_sources() -> tuple[Results, dict[str, str]]:
    """Read only saved summaries/session aggregates; reuse the checked report gates."""
    sources = dict(MANIFEST_PINS) | dict(HELPER_PINS)
    for name, expected in sources.items():
        if digest(ROOT / name) != expected:
            raise ValueError("FROZEN_HELPER_OR_MANIFEST_HASH:" + name)
    old = read_json(ROOT / "artifacts/rp4_v2_b4/report_manifest.json")
    recent = read_json(ROOT / "artifacts/rp4_v4_b4/report_manifest.json")
    results: Results = {}
    for version, horizon in SERIES:
        for window in WINDOWS:
            folder = source_folder(version, horizon, window)
            authority = old if version in ("v1", "v2") else recent
            for name in ("summary.json", "session_losses.csv"):
                path = folder / name
                sources[path.as_posix()] = pinned_input(ROOT / path, authority)
            summary = read_json(ROOT / folder / "summary.json")
            rows = read_csv(ROOT / folder / "session_losses.csv")
            if version in ("v1", "v2"):
                spec_key = (
                    "parent_specification_sha256" if version == "v1" else "specification_sha256"
                )
                validate_window(summary, rows, version, window, old[spec_key])
            else:
                checked.verify_results(summary, rows, horizon, window)
            if version == "v4":
                receipt_path = folder / "receipt.json"
                sources[receipt_path.as_posix()] = pinned_input(ROOT / receipt_path, recent)
                receipt = read_json(ROOT / receipt_path)
                checked.verify_receipt_identity(receipt, horizon, window)
                release_path = Path("artifacts/rp4_v4_a2") / f"evaluation_release_rv{horizon}.json"
                release_hash = pinned_input(ROOT / release_path, recent)
                sources[release_path.as_posix()] = release_hash
                if (
                    receipt["release_sha256"] != release_hash
                    or summary["binding"]["release_sha256"] != release_hash
                ):
                    raise ValueError("RELEASE_BINDING")
                saved = {Path(k).resolve(): v for k, v in receipt["artifacts_sha256"].items()}
                for name in ("summary.json", "session_losses.csv"):
                    path = (ROOT / folder / name).resolve()
                    if saved.get(path) != digest(path):
                        raise ValueError("RECEIPT_ARTIFACT_HASH")
            results[version, horizon, window] = (summary, rows)
    return results, sources


def comparison_rows(results: Results, sources: dict[str, str]) -> Rows:
    output = []
    for version, horizon in SERIES:
        for window in WINDOWS:
            summary, sessions = results[version, horizon, window]
            folder = source_folder(version, horizon, window)
            for item in summary["contrasts"]:
                name, base, richer = next(c for c in CONTRASTS if c[0] == item["contrast"])
                family = item["family"]
                baseline = statistics.mean(finite(r[f"loss__{family}__{base}"]) for r in sessions)
                delta = statistics.mean(differences(sessions, family, base, richer))
                _close(item["estimate"], delta, "CLOSEOUT_DELTA")
                point, low, high = percent_interval(
                    item["estimate"], item["ci_low"], item["ci_high"], baseline
                )
                _close(item["qlike_reduction_percent"], point, "CLOSEOUT_PERCENT")
                bilateral = next(
                    (
                        row
                        for row in summary.get("comparability_bilateral", [])
                        if (row["family"], row["contrast"]) == (family, name)
                    ),
                    item if version in ("v1", "v2") else {},
                )
                output.append(
                    {
                        "version": version,
                        "target": f"RV{horizon}",
                        "horizon_minutes": horizon,
                        "window": window,
                        "family": family,
                        "family_group": "linear" if family != "lightgbm_qlike" else "tree",
                        "contrast": name,
                        "N_sessions": item["N_sessions"],
                        "N_origins": item["N_origins"],
                        "N_asset_sessions": item["N_asset_sessions"],
                        "delta_qlike": item["estimate"],
                        "ci_low_qlike": item["ci_low"],
                        "ci_high_qlike": item["ci_high"],
                        "baseline_qlike_observed": baseline,
                        "percent_reduction": point,
                        "ci_low_rescaled_percent": low,
                        "ci_high_rescaled_percent": high,
                        "interval_definition": "saved_difference_CI95_scaled_by_100_over_observed_baseline;not_bootstrap_ratio_CI",
                        "p_raw": item.get("p_raw"),
                        "p_raw_sidedness": "two_sided" if version in ("v1", "v2") else "one_sided",
                        "p_for_decision": item.get("p_for_decision"),
                        "hypothesis_status": item.get("hypothesis_status"),
                        "p_bilateral": bilateral.get("p_raw"),
                        "p_holm_bilateral": bilateral.get("p_holm"),
                        "source_summary": (folder / "summary.json").as_posix(),
                        "source_summary_sha256": sources[(folder / "summary.json").as_posix()],
                        "source_session_losses": (folder / "session_losses.csv").as_posix(),
                        "source_session_losses_sha256": sources[
                            (folder / "session_losses.csv").as_posix()
                        ],
                    }
                )
    if len(output) != 40:
        raise ValueError("COMPARISON_EXPECTS_40_ROWS")
    return output


def text(
    x: float, y: float, content: str, *, size: int = 18, color: str = INK, **attrs: Any
) -> str:
    attributes = " ".join(
        f'{key.replace("_", "-")}="{html.escape(str(value))}"' for key, value in attrs.items()
    )
    return (
        f'<text x="{x:.2f}" y="{y:.2f}" font-family="{SANS}" font-size="{size}" '
        f'fill="{color}" {attributes}>{html.escape(content)}</text>'
    )


def line(
    x1: float, y1: float, x2: float, y2: float, color: str = RULE, width: float = 1, dash: str = ""
) -> str:
    return (
        f'<line x1="{x1:.3f}" y1="{y1:.3f}" x2="{x2:.3f}" y2="{y2:.3f}" '
        f'stroke="{color}" stroke-width="{width}" stroke-dasharray="{dash}"/>'
    )


def compact(value: float, *, signed: bool = False) -> str:
    if value == 0:
        return "0"
    sign = "+" if signed else ""
    return format(value, f"{sign}.5g").replace("-", "−")


def extent(values: list[float], padding: float = 0.08) -> tuple[float, float]:
    if not values or not all(math.isfinite(value) for value in values):
        raise ValueError("AXIS_REQUIRES_FINITE_VALUES")
    lo, hi = min(0.0, *values), max(0.0, *values)
    span = hi - lo or 1.0
    return lo - padding * span, hi + padding * span


def cumulative_data(
    rows: Rows, family: str, base: str, richer: str
) -> tuple[list[date], list[float]]:
    dates = [date.fromisoformat(row["session_date"]) for row in rows]
    if not dates or dates != sorted(set(dates)):
        raise ValueError("CURVE_DATE_ORDER")
    values = list(accumulate(differences(rows, family, base, richer)))
    if not all(math.isfinite(value) for value in values):
        raise ValueError("CURVE_FINITE")
    return dates, values


def cumulative_svg(results: Results, contrast: str, base: str, richer: str) -> tuple[bytes, Rows]:
    title = f"{richer} frente a {base} · diferencias acumuladas de QLIKE"
    canvas = Canvas(
        1840,
        1360,
        title,
        "Cuatro paneles con escalas independientes; dos familias, dos horizontes y dos ventanas.",
        contrast,
    )
    canvas.front(text(40, 45, title, size=30, font_weight=600))
    canvas.front(
        text(
            40,
            78,
            f"Σ sesión [QLIKE({base}) − QLIKE({richer})]. Positivo favorece a {richer}; negativo favorece a {base}.",
            size=21,
        )
    )
    canvas.front(
        text(
            40,
            108,
            "Ejes Y independientes por panel: compare valores, no alturas entre paneles. Curvas completas, sin quitar días.",
            size=18,
            color=MUTED,
        )
    )
    for i, family in enumerate(FAMILIES):
        x: float = 40 + 275 * i
        canvas.front(line(x, 138, x + 52, 138, COLORS[family], 3, "" if i == 0 else "10,5"))
        canvas.front(text(x + 62, 144, FAMILY_LABEL[family], size=20))
    metadata = []
    for row_index, horizon in enumerate((15, 5)):
        for col_index, window in enumerate(WINDOWS):
            left, top, width, height = 122 + 895 * col_index, 252 + row_index * 465, 735, 326
            summary, rows = results["v4", horizon, window]
            curves = {family: cumulative_data(rows, family, base, richer) for family in FAMILIES}
            dates = curves[FAMILIES[0]][0]
            xmin, xmax = dates[0].toordinal(), dates[-1].toordinal()
            lo, hi = extent([v for _, values in curves.values() for v in values])

            def x_position(
                day: date,
                xmin: int = xmin,
                xmax: int = xmax,
                left: int = left,
                width: int = width,
            ) -> float:
                return left + width * (day.toordinal() - xmin) / max(1, xmax - xmin)

            def y_position(
                value: float, lo: float = lo, hi: float = hi, top: int = top, height: int = height
            ) -> float:
                return top + height * (hi - value) / (hi - lo)

            canvas.front(
                text(
                    left - 78,
                    top - 58,
                    f"RV{horizon} · {WINDOW_LABEL[window]}",
                    size=25,
                    font_weight=600,
                )
            )
            canvas.front(
                text(
                    left - 78,
                    top - 29,
                    f"{dates[0]} — {dates[-1]} · N = {summary['N_sessions']} sesiones · escala propia",
                    size=17,
                    color=MUTED,
                )
            )
            canvas.back(
                f'<rect x="{left}" y="{top}" width="{width}" height="{height}" fill="{PAPER_2}"/>'
            )
            for fraction in (0, 0.25, 0.5, 0.75, 1):
                value = lo + fraction * (hi - lo)
                y = y_position(value)
                canvas.back(line(left, y, left + width, y))
                canvas.front(text(left - 12, y + 6, compact(value), size=16, text_anchor="end"))
            canvas.front(line(left, y_position(0), left + width, y_position(0), MUTED, 1.5))
            for index in range(5):
                ordinal = round(xmin + index * (xmax - xmin) / 4)
                day = date.fromordinal(ordinal)
                x = x_position(day)
                canvas.front(line(x, top + height, x, top + height + 7, MUTED))
                canvas.front(text(x, top + height + 29, str(day), size=15, text_anchor="middle"))
            event_rows = []
            for event_day, marker, label in EVENTS:
                day = date.fromisoformat(event_day)
                if dates[0] <= day <= dates[-1]:
                    x = x_position(day)
                    canvas.back(line(x, top, x, top + height, "#9BA5AE", 1.2, "5,5"))
                    label_y = top + (39 if event_day in ("2025-04-09", "2025-09-18") else 19)
                    canvas.front(
                        text(
                            x,
                            label_y,
                            marker,
                            size=16,
                            color=MUTED,
                            font_weight=700,
                            text_anchor="middle",
                        )
                    )
                    event_rows.append(
                        {
                            "date": event_day,
                            "marker": marker,
                            "in_session_csv": day in dates,
                            "label": label,
                        }
                    )
            finals = []
            for index, family in enumerate(FAMILIES):
                _, values = curves[family]
                points = " ".join(
                    f"{x_position(day):.3f},{y_position(value):.3f}"
                    for day, value in zip(dates, values, strict=True)
                )
                canvas.front(
                    f'<polyline fill="none" stroke="{COLORS[family]}" stroke-width="2.8" stroke-dasharray="{"" if index == 0 else "10,5"}" points="{points}"/>'
                )
                finals.append(f"{FAMILY_LABEL[family]} {compact(values[-1], signed=True)}")
                metadata.append(
                    {
                        "horizon_minutes": horizon,
                        "window": window,
                        "family": family,
                        "contrast": contrast,
                        "N_sessions": len(values),
                        "final_cumulative_delta": values[-1],
                        "axis_low": lo,
                        "axis_high": hi,
                        "events": event_rows,
                    }
                )
            canvas.front(
                text(left, top + height + 58, "Final: " + " · ".join(finals) + " QLIKE", size=17)
            )
    foot = (
        "Contexto temporal — las marcas no identifican causalidad ni ajustan el cálculo:",
        "A · 2025-04-07 y 2025-04-09: semana arancelaria (contexto, no causalidad).",
        "B · 2025-05-15: indisponibilidad del proveedor.   C · 2025-09-17: FOMC.   D · 2025-09-18: indisponibilidad del proveedor.",
        "E · 2026-06-17: FOMC.   F · 2026-08-31: AMZN, choque observado; noticia o earnings NO demostrados.",
        "Fuentes: pérdidas por sesión y resúmenes congelados. RV15 es el horizonte primario de v4; RV5 es secundario.",
    )
    for index, label in enumerate(foot):
        canvas.front(
            text(
                40,
                1173 + 34 * index,
                label,
                size=18,
                color=INK if index == 0 else MUTED,
                font_weight=600 if index == 0 else 400,
            )
        )
    return canvas.render().encode(), metadata


def comparison_svg(rows: Rows) -> bytes:
    canvas = Canvas(
        2100,
        1700,
        "Comparación completa: reducción de QLIKE por versión",
        "Cuarenta facetas independientes, con todos los intervalos guardados y sin truncar resultados adversos.",
        "comparison",
    )
    canvas.front(
        text(
            35,
            46,
            "Versiones y horizontes · reducción de QLIKE con incertidumbre guardada",
            size=29,
            font_weight=600,
        )
    )
    canvas.front(
        text(
            35,
            80,
            "Cada mini-panel tiene un eje X independiente. Las longitudes NO son comparables entre paneles: lea los valores y sus ejes.",
            size=20,
        )
    )
    canvas.front(
        text(
            35,
            112,
            "Barra: 100 × diferencia media / QLIKE base observado. Bigote: IC95% de la diferencia reescalado; NO es un IC bootstrap del cociente.",
            size=18,
            color=MUTED,
        )
    )
    labels = (
        ("primary", "linear", "B1_over_B0"),
        ("primary", "linear", "B2_over_B1"),
        ("primary", "tree", "B1_over_B0"),
        ("primary", "tree", "B2_over_B1"),
        ("confirmation", "linear", "B1_over_B0"),
        ("confirmation", "linear", "B2_over_B1"),
        ("confirmation", "tree", "B1_over_B0"),
        ("confirmation", "tree", "B2_over_B1"),
    )
    for col, (version, horizon) in enumerate(SERIES):
        x = 310 + col * 355
        canvas.front(
            text(
                x + 165,
                157,
                f"{version} · RV{horizon}",
                size=23,
                font_weight=600,
                text_anchor="middle",
            )
        )
        canvas.front(
            text(
                x + 165,
                182,
                "lineal: log-OLS" if version == "v1" else "lineal: ridge",
                size=16,
                color=MUTED,
                text_anchor="middle",
            )
        )
        for row_index, (window, family_group, contrast) in enumerate(labels):
            y = 210 + row_index * 168
            selected = [
                r
                for r in rows
                if (
                    r["version"],
                    r["horizon_minutes"],
                    r["window"],
                    r["family_group"],
                    r["contrast"],
                )
                == (version, horizon, window, family_group, contrast)
            ]
            if len(selected) != 1:
                raise ValueError("COMPARISON_FACET_IDENTITY")
            row = selected[0]
            point, low, high = [
                finite(row[key])
                for key in (
                    "percent_reduction",
                    "ci_low_rescaled_percent",
                    "ci_high_rescaled_percent",
                )
            ]
            xmin, xmax = extent([point, low, high], padding=0.09)
            plot_left, plot_width = x + 24, 283

            def xp(
                value: float,
                xmin: float = xmin,
                xmax: float = xmax,
                plot_left: int = plot_left,
                plot_width: int = plot_width,
            ) -> float:
                return plot_left + plot_width * (value - xmin) / (xmax - xmin)

            color = COLORS[FAMILIES[0] if family_group == "linear" else FAMILIES[1]]
            canvas.back(
                f'<rect x="{x}" y="{y - 10}" width="331" height="156" fill="{PAPER_2}" stroke="{RULE}"/>'
            )
            if col == 0:
                canvas.front(text(35, y + 20, WINDOW_LABEL[window], size=21, font_weight=600))
                canvas.front(
                    text(
                        35,
                        y + 49,
                        "Lineal" if family_group == "linear" else "LightGBM",
                        size=20,
                        color=color,
                    )
                )
                canvas.front(text(35, y + 78, contrast.replace("_over_", " / "), size=20))
                canvas.front(text(35, y + 105, "Positivo = mejora", size=16, color=MUTED))
            canvas.front(
                text(
                    x + 15,
                    y + 14,
                    compact(point, signed=True) + " %",
                    size=21,
                    color=color,
                    font_weight=600,
                )
            )
            canvas.front(
                text(
                    x + 15,
                    y + 38,
                    f"IC reescalado [{compact(low)}, {compact(high)}] %",
                    size=14,
                    color=MUTED,
                )
            )
            bar_y = y + 74
            canvas.front(line(xp(0), y + 48, xp(0), y + 98, "#707A84", 1.2))
            canvas.front(
                f'<rect x="{min(xp(0), xp(point)):.3f}" y="{bar_y - 9}" width="{abs(xp(point) - xp(0)):.3f}" height="18" fill="{color}" fill-opacity="0.55"/>'
            )
            canvas.front(line(xp(low), bar_y, xp(high), bar_y, INK, 2))
            for endpoint in (low, high):
                canvas.front(line(xp(endpoint), bar_y - 6, xp(endpoint), bar_y + 6, INK, 2))
            canvas.front(
                f'<circle cx="{xp(point):.3f}" cy="{bar_y}" r="4.5" fill="{color}" stroke="white" stroke-width="1"/>'
            )
            canvas.front(line(plot_left, y + 103, plot_left + plot_width, y + 103, MUTED))
            for value, anchor in ((xmin, "start"), (xmax, "end")):
                canvas.front(
                    text(
                        xp(value),
                        y + 122,
                        compact(value) + "%",
                        size=14,
                        color=MUTED,
                        text_anchor=anchor,
                    )
                )
            canvas.front(
                text(
                    x + 15,
                    y + 140,
                    f"N = {row['N_sessions']} sesiones / {row['N_origins']} orígenes",
                    size=13,
                    color=MUTED,
                )
            )
    for index, label in enumerate(
        (
            "No se omiten resultados adversos: los extremos de v1 se representan completos en su propia escala, sin corte en −100 %.",
            "Muestras, familias lineales e inferencia cambian entre versiones; RV30, RV15 y RV5 son objetivos distintos. No son réplicas independientes.",
            "Datos, intervalos, p, tamaños muestrales y hashes exactos: comparison_v1_v4.csv. No se entrenó ni se ejecutó bootstrap nuevo.",
        )
    ):
        canvas.front(text(35, 1584 + 35 * index, label, size=18, color=MUTED))
    return canvas.render().encode()


def rasterize(
    svg: bytes, node: Path, modules: Path, renderer: Path
) -> tuple[bytes, dict[str, Any]]:
    run = subprocess.run(
        [str(node), str(renderer), str(modules / "sharp")],
        input=svg,
        capture_output=True,
        check=False,
        timeout=60,
    )
    if run.returncode != 0:
        raise RuntimeError("SVG_RASTERIZATION_FAILED:" + str(run.returncode))
    result = run.stdout
    if result[:8] != b"\x89PNG\r\n\x1a\n" or result[12:16] != b"IHDR":
        raise ValueError("PNG_SIGNATURE")
    width, height = struct.unpack(">II", result[16:24])
    metadata = json.loads(run.stderr.decode("utf-8"))
    if (metadata["width"], metadata["height"]) != (width, height):
        raise ValueError("PNG_DIMENSION_IDENTITY")
    return result, metadata


def build() -> dict[str, Any]:
    started = datetime.now(UTC).isoformat()
    tick = time.perf_counter()
    node, modules = Path(os.environ["RP4_FIGURE_NODE"]), Path(os.environ["RP4_FIGURE_NODE_MODULES"])
    results, sources = load_sources()
    rows = comparison_rows(results, sources)
    outputs: dict[Path, bytes] = {OUT / "comparison_v1_v4.csv": csv_bytes(rows)}
    panel_metadata = []
    for contrast, base, richer in CONTRASTS:
        svg, panels = cumulative_svg(results, contrast, base, richer)
        outputs[FIGURES / f"v4_{contrast}_cumulative.svg"] = svg
        panel_metadata.extend(panels)
    outputs[FIGURES / "comparison_v1_v4.svg"] = comparison_svg(rows)
    render_metadata = []
    for path, content in list(outputs.items()):
        public_guard(content)
        if path.suffix == ".svg":
            png, metadata = rasterize(content, node, modules, ROOT / CODE / "rasterize.cjs")
            outputs[path.with_suffix(".png")] = png
            render_metadata.append({"path": path.with_suffix(".png").as_posix(), **metadata})
    code_sha256 = {
        path.relative_to(ROOT).as_posix(): digest(path)
        for path in sorted((ROOT / CODE).glob("*"))
        if path.is_file() and path.suffix in (".py", ".cjs")
    }
    source_receipt = {
        "schema": "frozen-figure-source-receipt-v1",
        "input_sha256": sources,
        "model_fits": 0,
        "new_bootstrap_repetitions": 0,
        "private_origin_data_read": False,
        "source_validation": "frozen_report_hashes_and_checked_report_window_arithmetic",
    }
    outputs[OUT / "sources.json"] = json_bytes(source_receipt)
    outputs[OUT / "panel_metadata.json"] = json_bytes(panel_metadata)
    readme = """# Figuras de cierre

Tres figuras nuevas (SVG y PNG) se derivan sólo de resúmenes y pérdidas por sesión congelados. No hay entrenamiento, descargas ni bootstrap nuevo.

- `v4_B1_over_B0_cumulative`: RV15 y RV5, dos familias y ambas ventanas en cuatro paneles separados. Suma por sesión de QLIKE base menos QLIKE ampliado, sin exclusiones nuevas.
- `v4_B2_over_B1_cumulative`: la misma definición para el segundo contraste.
- `comparison_v1_v4`: cuarenta facetas con las cinco combinaciones versión/objetivo, ambas ventanas, familias y contrastes. Cada faceta usa un eje independiente; los extremos adversos no se recortan.

El intervalo porcentual es el IC95% guardado para la diferencia, multiplicado por 100 y dividido por la pérdida base media observada. No es un intervalo bootstrap del cociente: no incluye de nuevo la incertidumbre del denominador. Las comparaciones no son réplicas independientes, y las versiones difieren en muestra, familia lineal y procedimiento de inferencia.

`comparison_v1_v4.csv` conserva estimación, IC, p, N, denominador observado y fuentes con hashes. Los p de v1/v2 son bilaterales; v3/v4 conserva p unilateral y su estado secuencial, además del p bilateral y Holm guardados. Un p formal no abierto permanece vacío, no se transforma en cero.

Las marcas de fechas son contexto, no explicaciones causales ni criterios de exclusión. La marca AMZN identifica un choque observado: no demuestra una noticia ni earnings. `panel_metadata.json` indica si cada fecha anotada está presente en el CSV de sesiones.

Ejecutar con el entorno existente y las variables `RP4_FIGURE_NODE` y `RP4_FIGURE_NODE_MODULES` apuntando a la dependencia de rasterización ya instalada:

```text
uv run --offline --frozen --no-sync python -B -m artifacts.rp4_closeout_figures_code.build
```

Los archivos previos no se sustituyen. Los hashes de las fuentes se verifican antes de calcular las coordenadas de las figuras.
"""
    outputs[OUT / "README.md"] = readme.encode()
    for path, content in outputs.items():
        if path.suffix != ".png":
            public_guard(content)
        write_new(ROOT / path, content)
    manifest = {
        "schema": "closeout-figures-v1",
        "status": "COMPLETE",
        "exit_code": 0,
        "command": COMMAND,
        "started_at_utc": started,
        "completed_at_utc": datetime.now(UTC).isoformat(),
        "elapsed_seconds": time.perf_counter() - tick,
        "code_sha256": code_sha256,
        "source_receipt_sha256": digest(ROOT / OUT / "sources.json"),
        "artifacts_sha256": {path.as_posix(): digest(ROOT / path) for path in outputs},
        "comparison_rows": len(rows),
        "curve_panels": len(panel_metadata) // 2,
        "renderers": render_metadata,
        "axes": "independent_per_panel_explicitly_labeled",
        "interval": "saved_delta_CI_scaled_by_observed_denominator_not_ratio_CI",
        "event_annotations": [
            {"date": day, "marker": marker, "description": label} for day, marker, label in EVENTS
        ],
        "new_bootstrap_repetitions": 0,
        "model_fits": 0,
        "downloads": 0,
        "private_origin_data_read": False,
        "prior_artifacts_modified": False,
        "public_identity_guard": "PASS",
        "research_only": True,
        "capital_go": False,
        "publication": False,
    }
    content = json_bytes(manifest)
    public_guard(content)
    write_new(ROOT / OUT / "manifest.json", content)
    return {
        "status": "COMPLETE",
        "exit_code": 0,
        "manifest": (OUT / "manifest.json").as_posix(),
        "manifest_sha256": digest(ROOT / OUT / "manifest.json"),
        "comparison_rows": len(rows),
    }


def main() -> int:
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(build(), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
