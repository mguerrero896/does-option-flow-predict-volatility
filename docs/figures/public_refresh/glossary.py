"""Render and verify the glossary using versioned text and the existing figure tools."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT))
from scripts import figure_style as style  # noqa: E402

SOURCE = HERE / "glossary.json"
RECEIPT = HERE / "glossary.receipt.json"
SVG = HERE / "glossary.svg"
PNG = HERE / "glossary.png"
MARKDOWN = ROOT / "docs/glossary.md"
RASTERIZER = ROOT / "artifacts/rp4_closeout_figures_code/rasterize.cjs"
WIDTH, HEIGHT = 838, 1280
TEXT_HASH_SUFFIXES = {".py", ".cjs"}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def input_hash(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix in TEXT_HASH_SUFFIXES:
        data.decode("utf-8")
        data = data.replace(b"\r\n", b"\n")
    return sha(data)


def text(canvas, x, y, value, size=20, weight="400", color=style.INK):
    canvas.front(
        f'<text x="{x}" y="{y}" font-family="{style.SANS}" font-size="{size}" '
        f'font-weight="{weight}" fill="{color}">{style.esc(value)}</text>'
    )


def render_svg(source: dict) -> bytes:
    cards = source["cards"]
    assert len(cards) == 12 and len({c["id"] for c in cards}) == 12
    canvas = style.Canvas(
        WIDTH,
        HEIGHT,
        source["title"],
        "Twelve definitions for reading a study of options and volatility. "
        "The text version provides expanded definitions, qualifications and sources.",
        "public-glossary",
    )
    text(canvas, 24, 46, source["title"], 34, "600")
    text(canvas, 24, 79, source["subtitle"], 22, color=style.MUTED)
    for index, card in enumerate(cards):
        x, y = 24 + (index % 2) * 405, 106 + (index // 2) * 184
        assert len(card["lines"]) == 4
        fill = style.ACCENT_TINT if index in {3, 11} else style.PAPER_2
        canvas.front(
            f'<g id="{card["id"]}" data-glossary-card="true">'
            f'<rect x="{x}" y="{y}" width="385" height="168" rx="10" '
            f'fill="{fill}" stroke="{style.RULE_STRONG}" stroke-width="1.2"/>'
        )
        text(canvas, x + 18, y + 32, card["title"], 22, "600", style.LINK)
        for line, value in enumerate(card["lines"]):
            text(canvas, x + 18, y + 66 + line * 24, value)
        canvas.front("</g>")
    canvas.front(
        f'<line x1="24" y1="1226" x2="814" y2="1226" '
        f'stroke="{style.RULE_STRONG}" stroke-width="1"/>'
    )
    text(canvas, 24, 1260, source["footer"], color=style.MUTED)
    svg = canvas.render()
    svg = svg.replace(
        f'width="{WIDTH}" height="{HEIGHT}"',
        f'width="{2 * WIDTH}" height="{2 * HEIGHT}"',
        1,
    )
    return (svg + "\n").encode("utf-8")


def render_markdown(source: dict) -> bytes:
    lines = [
        "# Glossary",
        "",
        "Plain-language definitions for reading *Options Order Flow and Intraday Volatility*. "
        "These terms explain the method and its limits; they do not add results or establish "
        "investment value.",
        "",
        "![Twelve research terms, from volatility and option inputs to uncertainty and "
        "prospective replication](figures/public_refresh/glossary.png)",
        "",
        "[Scalable image](figures/public_refresh/glossary.svg) · "
        "[Study overview](../README.md) · [Current report](rp4/results_v4.md)",
        "",
    ]
    for card in source["cards"]:
        lines += [f'<a id="{card["id"]}"></a>', "", f"## {card['title']}", "", card["detail"], ""]
        links = []
        for source_link in card["sources"]:
            path = Path(source_link["path"])
            assert path.parts[0] == "docs" and (ROOT / path).is_file()
            links.append(f"[{source_link['title']}]({Path(*path.parts[1:]).as_posix()})")
        lines += ["Sources: " + " · ".join(links) + ".", ""]
    lines += [
        "## Reproduce this glossary",
        "",
        "The [versioned text source](figures/public_refresh/glossary.json) drives both this "
        "page and the image. The [producer](figures/public_refresh/glossary.py) uses the "
        "existing repository figure palette and SVG-to-PNG rasterizer. It reads public "
        "documents and creates no model fits, statistical tests, market-data requests or "
        "prospective observations.",
        "",
        "From the repository root, source and output verification needs Python only:",
        "",
        "```sh",
        "python docs/figures/public_refresh/glossary.py --verify",
        "```",
        "",
        "To regenerate, use an existing Node.js and Sharp installation. Set "
        "`RP4_FIGURE_NODE` to the Node executable and `RP4_FIGURE_NODE_MODULES` to the "
        "directory containing the installed `sharp` package. No packages are installed "
        "by the producer.",
        "",
        "```sh",
        "python docs/figures/public_refresh/glossary.py --render",
        "python docs/figures/public_refresh/glossary.py --verify-raster",
        "```",
        "",
        "The [render receipt](figures/public_refresh/glossary.receipt.json) records source "
        "and output hashes, dimensions, renderer versions and review status. Code-source "
        "hashes normalize CRLF to LF; other inputs and all outputs use exact bytes. "
        "The SVG has an intrinsic width of 1676 pixels and a viewBox width of 838. "
        "At 838 pixels of available page width, all visible text is at least 20 pixels. "
        "The PNG is 1676 pixels wide. SVG files contain no scripts or external resources.",
        "",
        "PNG byte reproduction depends on the recorded Sharp and libvips versions and the "
        "installed-font environment. Source and SVG verification is independent of the rasterizer. "
        "A fresh render resets visual review to pending; inspect the full-size image "
        "before recording a new review.",
        "",
    ]
    return "\n".join(lines).encode("utf-8")


def inspect_svg(data: bytes) -> dict:
    root = ET.fromstring(data)
    view_width = float(root.attrib["viewBox"].split()[2])
    available = min(838, float(root.attrib["width"]))
    fonts = []
    for element in root.iter():
        kind = element.tag.rsplit("}", 1)[-1]
        assert kind not in {"script", "foreignObject", "style"}
        assert not any(key.lower().startswith("on") for key in element.attrib)
        for key, value in element.attrib.items():
            if key.rsplit("}", 1)[-1] in {"href", "src"}:
                assert value.startswith("#")
        if kind == "text":
            assert not element.get("transform")
            effective = float(element.attrib["font-size"]) * available / view_width
            assert effective >= 20, "Text is too small at the available README width"
            fonts.append(effective)
    assert len(fonts) == 63
    return {
        "available_width_px": available,
        "intrinsic_width_px": int(root.attrib["width"]),
        "minimum_text_px": min(fonts),
        "text_elements": len(fonts),
        "external_resources": 0,
    }


def rasterize(data: bytes) -> tuple[bytes, dict]:
    # The existing rasterizer uses 96 dpi: a 1.5x SVG input yields a 2x PNG.
    raster_input = data.replace(
        f'width="{2 * WIDTH}" height="{2 * HEIGHT}"'.encode(),
        f'width="{WIDTH * 1.5:g}" height="{HEIGHT * 1.5:g}"'.encode(),
        1,
    )
    node = os.environ["RP4_FIGURE_NODE"]
    sharp = Path(os.environ["RP4_FIGURE_NODE_MODULES"]) / "sharp"
    result = subprocess.run(
        [node, str(RASTERIZER), str(sharp)], input=raster_input, capture_output=True, check=True
    )
    metadata = json.loads(result.stderr)
    assert metadata["width"] == 2 * WIDTH and metadata["height"] == 2 * HEIGHT
    metadata["font_stack"] = style.SANS
    metadata["font_environment"] = (
        "Installed Segoe UI on Windows; other font environments may change PNG bytes."
    )
    return result.stdout, metadata


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--render", action="store_true")
    mode.add_argument("--verify", action="store_true")
    mode.add_argument("--verify-raster", action="store_true")
    args = parser.parse_args()
    source = json.loads(SOURCE.read_text("utf-8"))
    assert source["schema_version"] == "public-glossary-v1"
    svg, markdown = render_svg(source), render_markdown(source)
    readability = inspect_svg(svg)
    inputs = [SOURCE, Path(__file__), ROOT / "scripts/figure_style.py", RASTERIZER]
    inputs += sorted({ROOT / link["path"] for c in source["cards"] for link in c["sources"]})
    hashes = {p.relative_to(ROOT).as_posix(): input_hash(p) for p in inputs}
    if args.render:
        png, renderer = rasterize(svg)
        for path, data in [(SVG, svg), (PNG, png), (MARKDOWN, markdown)]:
            assert not path.exists() or path.is_file()
            path.write_bytes(data)
        receipt = {
            "schema_version": "public-glossary-render-v1",
            "input_sha256": hashes,
            "input_hash_mode": {"code": "utf8-crlf-to-lf", "other": "raw-bytes"},
            "output_sha256": {
                p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in [MARKDOWN, SVG, PNG]
            },
            "readability": readability,
            "png_renderer": renderer,
            "visual_review": {"status": "pending"},
            "scope": (
                "Definitions and presentation only; no new empirical results "
                "or scientific execution."
            ),
        }
        RECEIPT.write_bytes((json.dumps(receipt, indent=2, ensure_ascii=False) + "\n").encode())
    else:
        receipt = json.loads(RECEIPT.read_text("utf-8"))
        assert hashes == receipt["input_sha256"], "Glossary input changed"
        assert svg == SVG.read_bytes() and markdown == MARKDOWN.read_bytes()
        assert readability == receipt["readability"]
        assert set(receipt["output_sha256"]) == {
            p.relative_to(ROOT).as_posix() for p in [MARKDOWN, SVG, PNG]
        }
        for relative, expected in receipt["output_sha256"].items():
            assert sha((ROOT / relative).read_bytes()) == expected, f"Output changed: {relative}"
        png = PNG.read_bytes()
        assert png[:8] == b"\x89PNG\r\n\x1a\n"
        assert struct.unpack(">II", png[16:24]) == (2 * WIDTH, 2 * HEIGHT)
        if args.verify_raster:
            regenerated, renderer = rasterize(svg)
            assert regenerated == png, "PNG raster regeneration differs"
            assert renderer == receipt["png_renderer"]
    print(
        json.dumps(
            {
                "status": "PASS",
                "mode": "render" if args.render else "verify",
                "sources": len(hashes),
                "outputs": 3,
                "readability": readability,
                "raster_regeneration": bool(args.verify_raster),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
