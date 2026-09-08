"""Append a common-axis thesis summary and calendar-tick curve revisions."""
# Long literals are generated SVG labels and frozen provenance pins.
# ruff: noqa: E501

from __future__ import annotations

import json
import os
import time
import xml.etree.ElementTree as ET
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

from artifacts.rp4_closeout_figures_code import build as b
from artifacts.rp4_v3_code.report_v3 import csv_bytes, read_csv, read_json
from scripts import figure_style as style

OUT = Path("artifacts/rp4_closeout_figures_revision2")
OLD_MANIFEST = "15bae2d6eeda608cecc6d24cbc34a9c0174eb2ae6a3a319d9e22519930b88c04"
OLD_BUILD = "47500aae9b906ab3b0f1e6aa8806853ba8ed02650bf8379e7ba51a97e5cbe03b"
PINS = {
    "artifacts/rp4_closeout_figures/manifest.json": OLD_MANIFEST,
    "artifacts/rp4_closeout_figures/comparison_v1_v4.csv": "0d9554e1fc5151b4eb7b149b7bc529bbdfee1d12e92883163087aedc6942a9ba",
    "artifacts/rp4_closeout_figures_code/build.py": OLD_BUILD,
    "artifacts/rp4_market_audit/REPORT.md": "74c6d6e5aaa43c51e73b0cacc8bde6a569aa1093686bafd5c10973d1abe3dcab",
    "artifacts/rp4_market_audit/summary.json": "f59a01f7819b36c7ee726b0f47541a0f0a4c17868b8d3d6035cc083d72fc3fdb",
    "artifacts/rp4_market_audit/manifest.json": "f52c37e95f9ebe9961d2d42e1e6719ffbf823a0a7a0128fb5d029407d507219f",
    "artifacts/rp4_market_audit/receipt.json": "956d17a5887644ffe61a3bbf1208638f116f8a700e2a44fb36f95f73d504a105",
}
OFFICIAL_LISTING_URL = "https://www.nasdaqtrader.com/MicroNews.aspx?id=OTA2026-2"
G_DATE = "2026-01-26"
G_LABEL = "Inicio del listado de vencimientos lunes/miércoles (aviso OTA2026-2)"
COMMAND = (
    "uv run --offline --frozen --no-sync python -B -m artifacts.rp4_closeout_figures_code.additions"
)
NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)


def real_session_ticks(dates: list[date], period: str) -> list[date]:
    """First observed session in each month/quarter, never a fabricated calendar day."""
    if period not in ("month", "quarter") or dates != sorted(set(dates)) or not dates:
        raise ValueError("TICK_PERIOD_OR_SESSION_ORDER")
    chosen: dict[tuple[int, int], date] = {}
    for day in dates:
        key = (day.year, day.month if period == "month" else (day.month - 1) // 3)
        chosen.setdefault(key, day)
    return list(chosen.values())


def clipping(point: Any, low: Any, high: Any, limit: float = 3) -> dict[str, Any]:
    point, low, high = map(b.finite, (point, low, high))
    if low > high or limit <= 0:
        raise ValueError("INVALID_CLIPPING_INTERVAL")
    return {
        "point": point,
        "ci_low": low,
        "ci_high": high,
        "point_clipped_low": point < -limit,
        "point_clipped_high": point > limit,
        "ci_low_clipped": abs(low) > limit,
        "ci_high_clipped": abs(high) > limit,
        "visible_point": max(-limit, min(limit, point)),
        "visible_ci_low": max(-limit, min(limit, low)),
        "visible_ci_high": max(-limit, min(limit, high)),
    }


def arrow(
    x: float, y: float, direction: str, color: str, *, size: float = 7, filled: bool = True
) -> str:
    sign = -1 if direction == "up" else 1
    points = f"{x:.2f},{y + sign * size:.2f} {x - size:.2f},{y - sign * size:.2f} {x + size:.2f},{y - sign * size:.2f}"
    return f'<polygon data-out-of-scale="{direction}" points="{points}" fill="{color if filled else "white"}" stroke="{color}" stroke-width="1.8"/>'


def outside_number(value: float) -> str:
    return (format(value, "+.2f") if abs(value) >= 100 else format(value, "+.5g")).replace("-", "−")


def thesis_svg(rows: b.Rows) -> tuple[bytes, b.Rows]:
    title = "Síntesis de tesis · reducción de QLIKE en la evaluación primaria"
    canvas = style.Canvas(
        1840,
        1030,
        title,
        "Dos contrastes, cinco versiones/objetivos, dos familias; eje común de menos tres a más tres por ciento con todos los recortes marcados.",
        "thesis-summary",
    )
    canvas.front(b.text(40, 45, title, size=29, font_weight=600))
    canvas.front(
        b.text(
            40,
            80,
            "Misma escala Y: −3 % a +3 %. Positivo = menor pérdida al añadir información. Sólo la ventana primaria.",
            size=20,
        )
    )
    canvas.front(
        b.text(
            40,
            112,
            "Flechas = punto o límite del IC fuera de escala; se imprime su valor real. No se presenta el recorte como un resultado de ±3 %.",
            size=18,
            color=style.MUTED,
        )
    )
    for index, family in enumerate(b.FAMILIES):
        x: float = 42 + 380 * index
        canvas.front(b.line(x, 147, x + 48, 147, b.COLORS[family], 3))
        canvas.front(f'<circle cx="{x + 24}" cy="147" r="5" fill="{b.COLORS[family]}"/>')
        label = "Lineal: log-OLS v1; ridge v2–v4" if index == 0 else "LightGBM"
        canvas.front(b.text(x + 60, 154, label, size=19))
    clipping_rows = []
    for panel, (contrast, base, richer) in enumerate(b.CONTRASTS):
        left, top, width, height = 105 + 905 * panel, 278, 758, 460

        def yp(value: float, top: int = top, height: int = height) -> float:
            return top + height * (3 - value) / 6

        canvas.front(b.text(left, 206, f"{richer} / {base}", size=27, font_weight=600))
        canvas.front(
            b.text(
                left,
                234,
                f"100 × [QLIKE({base}) − QLIKE({richer})] / QLIKE({base}) observado",
                size=18,
                color=style.MUTED,
            )
        )
        canvas.back(
            f'<rect x="{left}" y="{top}" width="{width}" height="{height}" fill="{style.PAPER_2}"/>'
        )
        for tick in range(-3, 4):
            y = yp(tick)
            canvas.back(
                b.line(
                    left,
                    y,
                    left + width,
                    y,
                    style.MUTED if tick == 0 else style.RULE,
                    1.6 if tick == 0 else 1,
                )
            )
            canvas.front(
                b.text(
                    left - 12, y + 6, f"{tick:+d}%" if tick else "0%", size=17, text_anchor="end"
                )
            )
        for col, (version, horizon) in enumerate(b.SERIES):
            center = left + width * (col + 0.5) / len(b.SERIES)
            canvas.front(
                b.text(
                    center,
                    top + height + 50,
                    f"{version} · RV{horizon}",
                    size=18,
                    font_weight=600,
                    text_anchor="middle",
                )
            )
            for index, group in enumerate(("linear", "tree")):
                selected = [
                    r
                    for r in rows
                    if (
                        r["version"],
                        int(r["horizon_minutes"]),
                        r["window"],
                        r["family_group"],
                        r["contrast"],
                    )
                    == (version, horizon, "primary", group, contrast)
                ]
                if len(selected) != 1:
                    raise ValueError("THESIS_POINT_IDENTITY")
                item = selected[0]
                clip = clipping(
                    item["percent_reduction"],
                    item["ci_low_rescaled_percent"],
                    item["ci_high_rescaled_percent"],
                )
                x = center + (-24 if index == 0 else 24)
                color = b.COLORS[b.FAMILIES[index]]
                canvas.front(
                    b.line(
                        x, yp(clip["visible_ci_low"]), x, yp(clip["visible_ci_high"]), color, 2.4
                    )
                )
                for end, flag in (("ci_low", "ci_low_clipped"), ("ci_high", "ci_high_clipped")):
                    if clip[flag]:
                        side = "down" if clip[end] < -3 else "up"
                        boundary = -3 if side == "down" else 3
                        canvas.front(arrow(x, yp(boundary), side, color, size=5, filled=False))
                        label_y = (
                            top - 14 - 19 * index
                            if side == "up"
                            else top + height + 18 + 16 * index
                        )
                        canvas.front(
                            b.text(
                                x,
                                label_y,
                                "IC " + outside_number(clip[end]),
                                size=12,
                                color=color,
                                text_anchor="middle",
                            )
                        )
                    else:
                        canvas.front(b.line(x - 6, yp(clip[end]), x + 6, yp(clip[end]), color, 2.2))
                if clip["point_clipped_low"] or clip["point_clipped_high"]:
                    side = "down" if clip["point_clipped_low"] else "up"
                    canvas.front(arrow(x, yp(clip["visible_point"]), side, color, size=8))
                    label_y = (
                        top + height + 91 + 17 * index if side == "down" else top - 37 - 19 * index
                    )
                    canvas.front(
                        b.text(
                            center,
                            label_y,
                            "▼ " + outside_number(clip["point"]) + " %"
                            if side == "down"
                            else "▲ " + outside_number(clip["point"]) + " %",
                            size=15,
                            color=color,
                            font_weight=600,
                            text_anchor="middle",
                        )
                    )
                else:
                    canvas.front(
                        f'<circle cx="{x:.3f}" cy="{yp(clip["point"]):.3f}" r="5.6" fill="{color}" stroke="white" stroke-width="1.1"/>'
                    )
                clipping_rows.append(
                    {
                        "version": version,
                        "horizon_minutes": horizon,
                        "window": "primary",
                        "family_group": group,
                        "family": item["family"],
                        "contrast": contrast,
                        "N_sessions": item["N_sessions"],
                        "N_origins": item["N_origins"],
                        **clip,
                    }
                )
            canvas.front(
                b.text(
                    center,
                    top + height + 72,
                    f"N = {item['N_sessions']}",
                    size=14,
                    color=style.MUTED,
                    text_anchor="middle",
                )
            )
    foot = (
        "Bigotes = IC95% guardado de la diferencia × 100 / pérdida base observada; NO son intervalos bootstrap del cociente.",
        "v1 usa 92 261 orígenes; las demás versiones, 160 832. Los horizontes son objetivos distintos y no son réplicas independientes.",
        "La figura completa sin recortes y las cifras exactas permanecen en comparison_v1_v4.svg y comparison_v1_v4.csv.",
        "Escala resumida solicitada para lectura comparativa; los puntos adversos y todos los límites fuera de escala se conservan con flechas.",
    )
    for index, label in enumerate(foot):
        canvas.front(b.text(40, 902 + 31 * index, label, size=18, color=style.MUTED))
    return canvas.render().encode(), clipping_rows


def _append(root: ET.Element, markup: str) -> None:
    root.append(ET.fromstring(markup))


def revised_curve(
    results: b.Results, contrast: str, base: str, richer: str
) -> tuple[bytes, b.Rows]:
    """Only replace tick/annotation display nodes of the pinned cumulative renderer."""
    original, metadata = b.cumulative_svg(results, contrast, base, richer)
    root = ET.fromstring(original)
    root.set("height", "1480")
    root.set("viewBox", "0 0 1840 1480")
    prior_curves = [
        element.attrib["points"] for element in root if element.tag.endswith("polyline")
    ]
    removed_text = removed_lines = 0
    bottoms = (578.0, 1043.0)
    for element in list(root):
        if element.tag.endswith("text"):
            y = float(element.attrib["y"])
            if y >= 1173:
                root.remove(element)
            elif any(y == bottom + 29 for bottom in bottoms):
                root.remove(element)
                removed_text += 1
        elif element.tag.rsplit("}", 1)[-1] == "line":
            y1, y2 = float(element.attrib["y1"]), float(element.attrib["y2"])
            if any(y1 == bottom and y2 == bottom + 7 for bottom in bottoms):
                root.remove(element)
                removed_lines += 1
    if (removed_text, removed_lines) != (20, 20):
        raise ValueError("PINNED_RENDERER_TICK_LAYOUT_DRIFT")
    for row_index, horizon in enumerate((15, 5)):
        for col_index, window in enumerate(b.WINDOWS):
            left, top, width, height = 122 + 895 * col_index, 252 + row_index * 465, 735, 326
            _, rows = results["v4", horizon, window]
            dates = [date.fromisoformat(row["session_date"]) for row in rows]
            period = "quarter" if window == "primary" else "month"
            ticks = real_session_ticks(dates, period)
            xmin, xmax = dates[0].toordinal(), dates[-1].toordinal()
            for day in ticks:
                x = left + width * (day.toordinal() - xmin) / max(1, xmax - xmin)
                _append(root, b.line(x, top + height, x, top + height + 7, style.MUTED))
                _append(
                    root,
                    b.text(
                        x,
                        top + height + 29,
                        str(day),
                        size=15,
                        text_anchor="end" if day == dates[0] else "middle",
                    ),
                )
            g_day = date.fromisoformat(G_DATE)
            if dates[0] <= g_day <= dates[-1]:
                x = left + width * (g_day.toordinal() - xmin) / max(1, xmax - xmin)
                _append(root, b.line(x, top, x, top + height, "#9BA5AE", 1.2, "5,5"))
                _append(
                    root,
                    b.text(
                        x,
                        top + 19,
                        "G",
                        size=16,
                        color=style.MUTED,
                        font_weight=700,
                        text_anchor="middle",
                    ),
                )
            for item in metadata:
                if (item["horizon_minutes"], item["window"]) == (horizon, window):
                    item["tick_rule"] = f"first_observed_session_of_{period}"
                    item["ticks"] = [str(day) for day in ticks]
                    if dates[0] <= g_day <= dates[-1]:
                        item["events"] = [
                            *item["events"],
                            {
                                "date": G_DATE,
                                "marker": "G",
                                "label": G_LABEL,
                                "in_session_csv": g_day in dates,
                            },
                        ]
    foot = (
        "Contexto temporal — las marcas no identifican causalidad ni ajustan el cálculo:",
        "A · 2025-04-07 y 2025-04-09: semana arancelaria (contexto, no causalidad).",
        "B · 2025-05-15: indisponibilidad del proveedor.   C · 2025-09-17: FOMC.   D · 2025-09-18: indisponibilidad del proveedor.",
        "E · 2026-06-17: FOMC.   G · 2026-01-26: inicio del listado de vencimientos lunes/miércoles (Nasdaq OTA2026-2).",
        "F · 2026-08-31, AMZN: barras de 1 min, retorno log −152 pb a las 14:00 ET y +71 pb en el minuto siguiente.",
        "Volumen del minuto siguiente ≈11× la mediana de la sesión. Causa no identificada; noticia o earnings NO demostrados.",
        "Eje X: primera sesión observada de cada trimestre (primaria) o mes (confirmación); todas las marcas son sesiones del CSV.",
        "Fuentes: pérdidas congeladas, auditoría agregada de barras y Nasdaq OTA2026-2. RV15 primario; RV5 secundario.",
    )
    for index, label in enumerate(foot):
        _append(
            root,
            b.text(
                40,
                1173 + 36 * index,
                label,
                size=18,
                color=style.INK if index == 0 else style.MUTED,
                font_weight=600 if index == 0 else 400,
            ),
        )
    current_curves = [
        element.attrib["points"] for element in root if element.tag.endswith("polyline")
    ]
    if current_curves != prior_curves or len(current_curves) != 8:
        raise ValueError("CUMULATIVE_COORDINATES_CHANGED")
    return ET.tostring(root, encoding="utf-8"), metadata


def run() -> dict[str, Any]:
    tick = time.perf_counter()
    start = datetime.now(UTC).isoformat()
    for name, expected in PINS.items():
        if b.digest(b.ROOT / name) != expected:
            raise ValueError("ADDITION_SOURCE_PIN:" + name)
    old_manifest = read_json(b.ROOT / "artifacts/rp4_closeout_figures/manifest.json")
    for name, expected in old_manifest["artifacts_sha256"].items():
        if b.digest(b.ROOT / name) != expected:
            raise ValueError("ORIGINAL_FIGURE_CHANGED")
    market = read_json(b.ROOT / "artifacts/rp4_market_audit/summary.json")
    amzn = next(row for row in market["bars"] if row["asset"] == "AMZN")
    if (
        amzn["session_date"],
        round(amzn["event_close_to_close_log_return_bp"]),
        round(amzn["next_close_to_close_log_return_bp"]),
        round(amzn["next_volume_over_session_median"]),
    ) != ("2026-08-31", -152, 71, 11):
        raise ValueError("ANNOTATION_SOURCE_IDENTITY")
    results, sources = b.load_sources()
    rows = read_csv(b.ROOT / "artifacts/rp4_closeout_figures/comparison_v1_v4.csv")
    summary_svg, clipped = thesis_svg(rows)
    outputs: dict[Path, bytes] = {b.FIGURES / "thesis_summary.svg": summary_svg}
    panels = []
    for contrast, base, richer in b.CONTRASTS:
        svg, current_panels = revised_curve(results, contrast, base, richer)
        outputs[b.FIGURES / f"v4_{contrast}_cumulative_v2.svg"] = svg
        panels.extend(current_panels)
    node, modules = Path(os.environ["RP4_FIGURE_NODE"]), Path(os.environ["RP4_FIGURE_NODE_MODULES"])
    renderers = []
    for path, content in list(outputs.items()):
        b.public_guard(content)
        png, metadata = b.rasterize(content, node, modules, b.ROOT / b.CODE / "rasterize.cjs")
        outputs[path.with_suffix(".png")] = png
        renderers.append({"path": path.with_suffix(".png").as_posix(), **metadata})
    outputs[OUT / "clipping_census.csv"] = csv_bytes(clipped)
    outputs[OUT / "panel_metadata.json"] = b.json_bytes(panels)
    outputs[OUT / "annotation_sources.json"] = b.json_bytes(
        {
            "source_sha256": PINS,
            "official_listing_url": OFFICIAL_LISTING_URL,
            "listing_date": G_DATE,
            "amzn_aggregate": amzn,
            "context_is_not_causality": True,
        }
    )
    for path, content in outputs.items():
        if path.suffix != ".png":
            b.public_guard(content)
        b.write_new(b.ROOT / path, content)
    for name, expected in old_manifest["artifacts_sha256"].items():
        if b.digest(b.ROOT / name) != expected:
            raise ValueError("ORIGINAL_FIGURE_CHANGED_AFTER_GENERATION")
    manifest = {
        "schema": "closeout-figures-revision2",
        "status": "COMPLETE",
        "exit_code": 0,
        "command": COMMAND,
        "started_at_utc": start,
        "completed_at_utc": datetime.now(UTC).isoformat(),
        "elapsed_seconds": time.perf_counter() - tick,
        "source_sha256": sources | PINS,
        "code_sha256": {
            path.relative_to(b.ROOT).as_posix(): b.digest(path)
            for path in (
                Path(__file__),
                b.ROOT / b.CODE / "test_additions.py",
                b.ROOT / b.CODE / "rasterize.cjs",
            )
        },
        "artifacts_sha256": {path.as_posix(): b.digest(b.ROOT / path) for path in outputs},
        "renderers": renderers,
        "summary_points": len(clipped),
        "points_outside_scale": sum(
            row["point_clipped_low"] or row["point_clipped_high"] for row in clipped
        ),
        "interval_limits_outside_scale": sum(
            row["ci_low_clipped"] + row["ci_high_clipped"] for row in clipped
        ),
        "scale_percent": [-3, 3],
        "curve_coordinates_preserved_exact": True,
        "old_output_hashes_unchanged": True,
        "calendar_ticks_are_observed_sessions": True,
        "model_fits": 0,
        "new_bootstrap_repetitions": 0,
        "downloads": 0,
        "new_raw_or_target_reads": 0,
        "public_identity_guard": "PASS",
        "publication": False,
    }
    content = b.json_bytes(manifest)
    b.public_guard(content)
    b.write_new(b.ROOT / OUT / "manifest.json", content)
    return {
        "status": "COMPLETE",
        "exit_code": 0,
        "manifest": (OUT / "manifest.json").as_posix(),
        "manifest_sha256": b.digest(b.ROOT / OUT / "manifest.json"),
        "points_outside_scale": manifest["points_outside_scale"],
        "interval_limits_outside_scale": manifest["interval_limits_outside_scale"],
    }


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
