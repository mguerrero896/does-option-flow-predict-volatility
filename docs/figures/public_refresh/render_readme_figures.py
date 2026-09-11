"""Render public-facing figures from saved statistics and cumulative loss aggregates."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from scripts import figure_style as style  # noqa: E402
from scripts.verify_public_projection import INTERNAL_LABEL  # noqa: E402

ET.register_namespace("", "http://www.w3.org/2000/svg")
ASSETS = ("AAPL", "AMZN", "META", "MSFT", "NVDA", "TSLA")
FAMILIES = ("log_ridge_harq", "lightgbm_qlike")
STATISTICS = "artifacts/rp4_v4_b4/primary_statistics.csv"
ROBUSTNESS = "artifacts/rp4_v4_b4/robustness.csv"
CURVES = "artifacts/rp4_readme_figures_v1/cumulative_by_asset_rv15.csv"
CONTROL = "artifacts/rp4_universe_public_v1/control_six_rv15_losses.csv"
SPECIFICATION = "docs/rp4/specification_v4.md"
RASTERIZER = "artifacts/rp4_closeout_figures_code/rasterize.cjs"
WORKFLOW = "docs/figures/public_refresh/proposal_to_replication.workflow.svg"
READABLE_WORKFLOW = "docs/figures/public_refresh/proposal_to_replication_readme.workflow.svg"
TIMELINE = "docs/figures/public_refresh/programme_timeline.architecture.svg"
GLOBAL = "docs/figures/rp4/v4_B2_over_B1_cumulative_v2.svg"
MANIFEST = HERE / "readme_figures_manifest.json"
SOURCE_HASH_MODE = {
    "default": "raw-bytes",
    "by_suffix": {
        ".py": "utf8-text-crlf-to-lf",
        ".cjs": "utf8-text-crlf-to-lf",
        ".mjs": "utf8-text-crlf-to-lf",
    },
}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_digest(relative: str) -> str:
    """Preserve raw evidence; make code-text hashes portable across Git checkouts."""
    data = (ROOT / relative).read_bytes()
    if Path(relative).suffix in SOURCE_HASH_MODE["by_suffix"]:
        data.decode("utf-8")
        data = data.replace(b"\r\n", b"\n")
    return digest(data)


def read_csv(relative: str) -> list[dict[str, str]]:
    with (ROOT / relative).open(newline="", encoding="utf-8") as stream:
        return list(csv.DictReader(stream))


def label(canvas, x, y, value, size=17, color=style.INK, weight="400", anchor="start"):
    canvas.front(
        f'<text x="{x}" y="{y}" font-family="{style.SANS}" font-size="{size}" '
        f'fill="{color}" font-weight="{weight}" text-anchor="{anchor}">{style.esc(value)}</text>'
    )


def box(canvas, x, y, width, height, fill=style.PAPER, stroke=style.RULE_STRONG, radius=10):
    canvas.front(
        f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{radius}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="1.4"/>'
    )


def line(canvas, x1, y1, x2, y2, color=style.RULE, width=1):
    canvas.front(
        f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}"/>'
    )


def matrix() -> bytes:
    rows = [
        r for r in read_csv(STATISTICS) if r["horizon_minutes"] == "15" and r["window"] == "primary"
    ]
    assert len(rows) == 4 and all(r["N_sessions"] == "419" for r in rows)
    c = style.Canvas(
        1200,
        730,
        "Do options improve volatility forecasts?",
        "Four saved comparisons for six stocks and 419 reused historical sessions. Linear option "
        "state and flow improve forecast loss; tree option flow does not show a clear improvement.",
        "result-matrix",
    )
    label(c, 40, 54, "Do options improve volatility forecasts?", 32, weight="600")
    label(
        c, 40, 87, "Percentage reduction in forecast loss for the next 15 minutes", 20, style.MUTED
    )
    columns = [
        (240, "B1_over_B0", "Option state", "Added to price history"),
        (706, "B2_over_B1", "Option flow", "Added to price history and option state"),
    ]
    for x, _, title, subtitle in columns:
        label(c, x + 214, 143, title, 23, weight="600", anchor="middle")
        label(c, x + 214, 169, subtitle, 15, style.MUTED, anchor="middle")
    for row_index, family in enumerate(FAMILIES):
        y = 192 + row_index * 200
        label(c, 40, y + 86, ("Linear", "Tree")[row_index], 28, weight="600")
        label(c, 40, y + 115, "model family", 17, style.MUTED)
        for x, contrast, _, _ in columns:
            r = next(r for r in rows if r["family"] == family and r["contrast"] == contrast)
            focal = family == FAMILIES[0] and contrast == "B2_over_B1"
            box(
                c,
                x,
                y,
                428,
                176,
                style.ACCENT_TINT if focal else style.PAPER_2,
                style.ACCENT if focal else style.RULE_STRONG,
            )
            label(
                c,
                x + 214,
                y + 72,
                f"{float(r['percent_reduction_mean']):+.3f}%",
                50,
                weight="600",
                anchor="middle",
            )
            label(
                c,
                x + 214,
                y + 110,
                f"p = {float(r['p_raw']):.4f}",
                23,
                style.MUTED,
                anchor="middle",
            )
            words = (
                "Lower forecast loss"
                if r["hypothesis_status"] == "REJECTED"
                else "No clear improvement"
            )
            label(c, x + 214, y + 146, words, 17, style.MUTED, anchor="middle")
    line(c, 40, 612, 1160, 612)
    label(
        c, 40, 646, "Six stocks · 419 historical sessions · 15-minute forecasts", 20, weight="600"
    )
    label(
        c,
        40,
        677,
        "One-sided tests in sequence within each family. "
        "These sessions were reused across designs.",
        17,
        style.MUTED,
    )
    label(
        c,
        40,
        705,
        "The final 25-session window does not confirm the full sequence. "
        "Forecast skill is not trading profit.",
        17,
        style.MUTED,
    )
    return c.render().encode()


def information_sets() -> bytes:
    assert "29/69/138" in (ROOT / SPECIFICATION).read_text("utf-8")
    c = style.Canvas(
        1200,
        712,
        "Three nested information sets",
        "B0 has 29 price-history predictors. B1 contains B0 and adds option state for 69 total. "
        "B2 contains B1 and adds a mixed 69-column option-information block for 138 total, "
        "before family-specific indicators and asset effects.",
        "information-sets-current",
    )
    label(c, 40, 54, "Three nested information sets", 32, weight="600")
    label(
        c,
        40,
        87,
        "Each step retains prior predictors; added blocks do not isolate a causal mechanism.",
        20,
        style.MUTED,
    )
    box(c, 40, 130, 1120, 468, style.ACCENT_TINT, style.ACCENT)
    label(c, 68, 174, "B2 · Price history + option state + mixed flow block", 24, weight="600")
    label(c, 1130, 174, "138 total", 25, weight="600", anchor="end")
    label(c, 68, 207, "Adds activity, IV / price / spread changes, exposure proxies and empty-window fields", 19, style.MUTED)
    box(c, 76, 240, 1048, 320, style.LINK_TINT, style.LINK)
    label(c, 104, 284, "B1 · Price history + option state", 24, weight="600")
    label(c, 1094, 284, "69 total", 25, weight="600", anchor="end")
    label(
        c,
        104,
        317,
        "Adds the implied-volatility surface and option-state measures",
        19,
        style.MUTED,
    )
    box(c, 112, 350, 976, 172, style.PAPER, style.RULE_STRONG)
    label(c, 140, 400, "B0 · Price and volatility history", 24, weight="600")
    label(c, 1058, 400, "29 total", 25, weight="600", anchor="end")
    label(
        c,
        140,
        440,
        "The same price-history baseline is present in all three sets.",
        20,
        style.MUTED,
    )
    label(
        c,
        140,
        475,
        "Chronological training and the same eligible forecast origins",
        19,
        style.MUTED,
    )
    label(
        c,
        40,
        639,
        "Counts are total predictors, before family-specific indicators and asset effects.",
        19,
        style.MUTED,
    )
    label(
        c,
        40,
        674,
        "Boxes show inclusion, not a scale of predictor counts. "
        "The information cutoff is 120 seconds.",
        18,
        style.MUTED,
    )
    return c.render().encode()


def curve_data():
    rows, controls, robust = read_csv(CURVES), read_csv(CONTROL), read_csv(ROBUSTNESS)
    assert len(rows) == len(controls) == 419
    assert [r["session_date"] for r in rows] == [r["session_date"] for r in controls]
    assert len({r["session_date"] for r in rows}) == 419
    assert list(rows[0]) == ["session_date"] + [f"{f}__{a}" for f in FAMILIES for a in ASSETS]
    values = {(f, a): [float(r[f"{f}__{a}"]) for r in rows] for f in FAMILIES for a in ASSETS}
    assert all(math.isfinite(v) for curve in values.values() for v in curve)
    errors, endpoints = [], []
    for family in FAMILIES:
        total = 0.0
        for i, control in enumerate(controls):
            total += float(control[f"loss__{family}__B1"]) - float(control[f"loss__{family}__B2"])
            errors.append(abs(sum(values[family, a][i] for a in ASSETS) / 6 - total))
        for asset in ASSETS:
            row = next(
                r
                for r in robust
                if r["horizon_minutes"] == "15"
                and r["window"] == "primary"
                and r["family"] == family
                and r["contrast"] == "B2_over_B1"
                and r["subset"] == f"asset_{asset}"
            )
            endpoints.append(
                abs(values[family, asset][-1] - float(row["estimate"]) * int(row["N_sessions"]))
            )
    assert max(errors) <= 5.001e-7 and max(endpoints) <= 5.001e-7
    return (
        rows,
        values,
        {
            "global_points": len(errors),
            "endpoints": len(endpoints),
            "maximum_global_difference": max(errors),
            "maximum_endpoint_difference": max(endpoints),
            "absolute_tolerance": 5.001e-7,
        },
    )


def asset_curves() -> tuple[bytes, dict]:
    rows, values, controls = curve_data()
    c = style.Canvas(
        1200,
        956,
        "How option-flow gains accumulated for each stock",
        "Six stock panels compare saved cumulative daily forecast-loss differences "
        "for linear and tree models. All panels use the same scale and 419 historical sessions. "
        "Positive favors adding option flow. "
        "Curves are descriptive and are not trading returns.",
        "asset-cumulative-flow",
    )
    label(c, 40, 54, "How option-flow gains accumulated for each stock", 30, weight="600")
    label(
        c,
        40,
        89,
        "Cumulative QLIKE difference: option state − (option state + flow) · 15-minute forecasts",
        19,
        style.MUTED,
    )
    line(c, 40, 128, 83, 128, style.LINK, 3)
    label(c, 95, 135, "Linear", 19)
    line(c, 215, 128, 258, 128, style.ACCENT, 3)
    label(c, 270, 135, "Tree", 19)
    label(c, 450, 135, "Above zero: adding flow lowered forecast loss", 18, style.MUTED)
    all_values = [0.0] + [v for curve in values.values() for v in curve]
    low, high = math.floor(min(all_values) * 2) / 2, math.ceil(max(all_values) * 2) / 2
    ticks = [low + (high - low) * i / 4 for i in range(5)]
    for index, asset in enumerate(ASSETS):
        left, top = 40 + (index % 3) * 392, 182 + (index // 3) * 330
        x, y, w, h = left + 48, top + 39, 290, 215
        label(c, left + 48, top + 9, asset, 24, weight="600")

        def sy(value, origin=y, height=h):
            return origin + height * (high - value) / (high - low)

        for tick in ticks:
            yy = sy(tick)
            line(
                c,
                x,
                yy,
                x + w,
                yy,
                style.RULE_STRONG if tick == 0 else style.RULE,
                1.5 if tick == 0 else 1,
            )
            label(c, x - 9, yy + 5, f"{tick:+.2f}" if tick else "0", 13, style.MUTED, anchor="end")
        for family, color in zip(FAMILIES, (style.LINK, style.ACCENT), strict=True):
            curve = values[family, asset]
            points = [f"M {x:.3f} {sy(curve[0]):.3f}"]
            for i in range(1, len(curve)):
                points.append(f"H {x + w * i / (len(curve) - 1):.3f} V {sy(curve[i]):.3f}")
            c.front(
                f'<path d="{" ".join(points)}" fill="none" stroke="{color}" stroke-width="2.2"/>'
            )
        label(c, x, y + h + 24, rows[0]["session_date"], 13, style.MUTED)
        label(c, x + w, y + h + 24, rows[-1]["session_date"], 13, style.MUTED, anchor="end")
        label(c, x, y + h + 52, f"Linear {values[FAMILIES[0], asset][-1]:+.3f}", 16, style.LINK)
        label(
            c,
            x + w,
            y + h + 52,
            f"Tree {values[FAMILIES[1], asset][-1]:+.3f}",
            16,
            style.MUTED,
            anchor="end",
        )
    line(c, 40, 841, 1160, 841)
    label(
        c,
        40,
        877,
        "Same vertical scale in every panel · 419 sessions · six stocks · all saved dates retained",
        19,
        weight="600",
    )
    label(
        c,
        40,
        910,
        "Existing aggregates rounded to six decimals. "
        "A stock curve is not an independent replication.",
        17,
        style.MUTED,
    )
    label(
        c,
        40,
        938,
        "These are cumulative forecast-loss differences, not returns, profits or an equity curve.",
        17,
        style.MUTED,
    )
    return c.render().encode(), controls


def readme_readability(data: bytes) -> dict:
    """Check every visible label at GitHub's observed 831-pixel image width."""
    root = ET.fromstring(data)
    width = float(root.attrib["viewBox"].split()[2])
    intrinsic_width = float(root.attrib["width"].removesuffix("px"))
    display_width = min(831, intrinsic_width)
    labels = []
    for node in root.iter():
        transform = node.get("transform", "")
        contains_text = any(child.tag.rsplit("}", 1)[-1] == "text" for child in node.iter())
        if contains_text:
            assert not re.search(r"\b(?:scale|matrix)\s*\(", transform), "Unmeasured text scaling"
        if node.tag.rsplit("}", 1)[-1] != "text" or not "".join(node.itertext()).strip():
            continue
        size = float(node.attrib["font-size"])
        effective = size * display_width / width
        assert effective >= 18, f"README text too small: {''.join(node.itertext())}"
        labels.append({"text": "".join(node.itertext()), "effective_px": effective})
    assert labels, "No measured diagram labels"
    return {
        "available_width_px": 831,
        "intrinsic_width_px": intrinsic_width,
        "display_width_px": display_width,
        "minimum_required_px": 18,
        "minimum_effective_px": min(item["effective_px"] for item in labels),
        "labels": labels,
    }


def static_svg(data: bytes) -> None:
    root = ET.fromstring(data)
    assert root.tag.endswith("}svg")
    for node in root.iter():
        assert node.tag.rsplit("}", 1)[-1] not in {"script", "foreignObject"}
        for key, value in node.attrib.items():
            assert not key.lower().startswith("on")
            if key.rsplit("}", 1)[-1] in {"href", "src"}:
                assert value.startswith("#"), "External SVG resource"
        if node.tag.endswith("}style") and node.text:
            assert "@import" not in node.text
            for url in re.findall(r"url\(([^)]+)\)", node.text):
                url = url.strip("'\" ")
                if url.startswith("data:image/svg+xml,"):
                    static_svg(unquote(url.split(",", 1)[1]).encode())
                else:
                    assert url.startswith("#"), "External stylesheet resource"


def rasterization_svg(data: bytes, readme_compact: bool = False) -> bytes:
    """Resolve the archived Archify light palette for Sharp's SVG engine.

    The original browser export uses CSS variables, which the installed librsvg
    does not render. Geometry, text and font declarations remain unchanged;
    only the light palette and CSS variable fallbacks become explicit values.
    """
    root = ET.fromstring(data)
    if readme_compact:
        _, _, width, height = map(float, root.attrib["viewBox"].split())
        # The unchanged 96-dpi rasterizer yields a 1662-pixel (2x README) PNG.
        root.set("width", "1246.5")
        root.set("height", str(1246.5 * height / width))
    if root.get("data-preset") is None:
        return data
    root.set("data-theme", "light")
    styles = [n for n in root if n.tag.endswith("}style")]
    assert len(styles) == 1 and styles[0].text
    css = styles[0].text
    palette = re.search(r'\[data-theme="light"\]\s*\{([^}]+)\}', css)
    assert palette, "The archived Archify export lacks its light palette"
    variables = dict(re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", palette[1]))

    def replace(match):
        name, _, fallback = match[1].partition(",")
        if name.strip() in variables:
            return variables[name.strip()]
        assert fallback.strip(), f"Unresolved SVG variable: {name}"
        return fallback.strip()

    for node in root.iter():
        for key, value in list(node.attrib.items()):
            node.set(key, re.sub(r"var\(([^)]+)\)", replace, value))
        if node.text:
            node.text = re.sub(r"var\(([^)]+)\)", replace, node.text)
    result = ET.tostring(root, encoding="utf-8") + b"\n"
    assert b"var(" not in result
    return result


def rasterize(data: bytes, readme_compact: bool = False) -> tuple[bytes, dict]:
    node, modules = os.environ["RP4_FIGURE_NODE"], Path(os.environ["RP4_FIGURE_NODE_MODULES"])
    result = subprocess.run(
        [node, str(ROOT / RASTERIZER), str(modules / "sharp")],
        input=rasterization_svg(data, readme_compact),
        capture_output=True,
        check=True,
    )
    metadata = json.loads(result.stderr)
    pixels = subprocess.run(
        [
            node,
            "-e",
            "const sharp = require(process.argv[1]); "
            "sharp(require('fs').readFileSync(0)).stats().then(s => "
            "process.stdout.write(JSON.stringify(s.channels.slice(0, 3)"
            ".map(c => c.max - c.min))));",
            str(modules / "sharp"),
        ],
        input=result.stdout,
        capture_output=True,
        check=True,
    )
    rgb_ranges = json.loads(pixels.stdout)
    assert max(rgb_ranges) >= 128, "PNG is blank or lacks readable contrast"
    metadata["nonblank_rgb_ranges"] = rgb_ranges
    return result.stdout, metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--render", action="store_true")
    mode.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    sources = [
        STATISTICS,
        ROBUSTNESS,
        CURVES,
        CONTROL,
        SPECIFICATION,
        WORKFLOW,
        READABLE_WORKFLOW,
        TIMELINE,
        GLOBAL,
        "scripts/figure_style.py",
        "scripts/verify_public_projection.py",
        RASTERIZER,
        Path(__file__).relative_to(ROOT).as_posix(),
        "artifacts/rp4_readme_figures_v1/import_receipt.json",
        "docs/figures/public_refresh/manifest.json",
        "docs/figures/public_refresh/reproduce.mjs",
    ]
    source_hashes = {p: source_digest(p) for p in sources}
    curves, controls = asset_curves()
    outputs = {
        HERE / "result_matrix.svg": matrix(),
        HERE / "information_sets.svg": information_sets(),
        HERE / "cumulative_by_asset_rv15.svg": curves,
    }
    svg_sources = outputs | {
        ROOT / p: (ROOT / p).read_bytes() for p in (WORKFLOW, READABLE_WORKFLOW, TIMELINE, GLOBAL)
    }
    readability = {
        p: readme_readability(svg_sources[ROOT / p]) for p in (READABLE_WORKFLOW, TIMELINE)
    }
    for data in svg_sources.values():
        static_svg(data)
    first_text = " ".join(ET.fromstring(outputs[HERE / "result_matrix.svg"]).itertext())
    assert not INTERNAL_LABEL.search(first_text)
    assert not re.search(r"\b(?:RP[234]|v[1-9]|H[12])\b", first_text)
    assert all(value in first_text for value in ("+0.880%", "+0.623%", "+1.170%", "-0.115%"))
    for path in (*outputs, ROOT / READABLE_WORKFLOW, ROOT / GLOBAL):
        visible_text = " ".join(
            (node.text or "")
            for node in ET.fromstring(svg_sources[path]).iter()
            if node.tag.rsplit("}", 1)[-1] in {"text", "tspan", "title", "desc"}
        )
        assert not INTERNAL_LABEL.search(visible_text)
        assert not re.search(r"\b(?:RP[234]|v[1-9])\b", visible_text)
    png_metadata = {}
    if args.render:
        for path, data in svg_sources.items():
            png, metadata = rasterize(data, path in (ROOT / READABLE_WORKFLOW, ROOT / TIMELINE))
            outputs[path.with_suffix(".png")] = png
            png_metadata[path.with_suffix(".png").relative_to(ROOT).as_posix()] = metadata
        for path, data in outputs.items():
            if path.is_file() and path == (ROOT / GLOBAL).with_suffix(".png"):
                assert path.read_bytes() == data, "Existing global PNG must remain byte-identical"
            else:
                path.write_bytes(data)
        all_outputs = list(svg_sources) + [p.with_suffix(".png") for p in svg_sources]
        manifest = {
            "schema_version": "public-readme-figures-v1",
            "source_hash_mode": SOURCE_HASH_MODE,
            "source_sha256": source_hashes,
            "output_sha256": {
                p.relative_to(ROOT).as_posix(): digest(p.read_bytes()) for p in all_outputs
            },
            "curve_controls": controls,
            "readability": readability,
            "png_renderers": png_metadata,
            "method": (
                "Saved public statistics and existing rounded cumulative aggregates; "
                "original figure style and Sharp rasterizer. The README workflow and timeline "
                "use dedicated compact Archify sources, checked at 831 pixels wide. "
                "Archify PNGs resolve the existing light palette to explicit CSS values "
                "for librsvg compatibility, preserving SVG geometry and text."
            ),
            "verification_command": (
                "python docs/figures/public_refresh/render_readme_figures.py --verify"
            ),
            "render_command": (
                "python docs/figures/public_refresh/render_readme_figures.py --render"
            ),
            "visual_review": "pending",
            "new_model_fits": 0,
            "new_inference_runs": 0,
            "private_forecast_or_raw_inputs_read": 0,
            "capital_go": False,
        }
        MANIFEST.write_bytes((json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8"))
    else:
        manifest = json.loads(MANIFEST.read_text("utf-8"))
        assert manifest["source_hash_mode"] == SOURCE_HASH_MODE
        assert source_hashes == manifest["source_sha256"], "Figure source changed"
        assert controls == manifest["curve_controls"]
        assert readability == manifest["readability"]
        for path, data in outputs.items():
            assert data == path.read_bytes(), f"Regenerated figure differs: {path.name}"
        for path, expected in manifest["output_sha256"].items():
            assert digest((ROOT / path).read_bytes()) == expected, f"Saved figure differs: {path}"
    print(
        json.dumps(
            {
                "status": "PASS",
                "svg_outputs": len(svg_sources),
                "png_outputs": len(svg_sources),
                "source_inputs": len(source_hashes),
                "curve_controls": controls,
                "mode": "render" if args.render else "verify",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
