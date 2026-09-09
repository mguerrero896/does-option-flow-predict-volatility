"""Render and verify the glossary using versioned text and the existing figure tools."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import subprocess
import sys
import textwrap
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
WIDTH = 838
LINE_HEIGHT = 26
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


def wrap_exact(value: str, width: int) -> list[str]:
    """Introduce line breaks without changing or deleting any supplied wording."""
    lines = textwrap.wrap(value, width, break_long_words=False, break_on_hyphens=False)
    assert " ".join(lines) == value, "Wrapping changed the supplied wording"
    return lines


def layout(source: dict) -> dict:
    assert [len(s["rows"]) for s in source["sections"]] == [9, 8, 9, 10]
    title = wrap_exact(source["title"], 48)
    y = 28 + len(title) * 38 + 28
    sections = []
    for section in source["sections"]:
        heading = wrap_exact(section["title"], 58)
        start = y
        header_height = 24 + len(heading) * 30
        y += header_height + 44
        rows = []
        for row in section["rows"]:
            label = wrap_exact(row["label"], 16)
            meaning = wrap_exact(row["meaning"], 50)
            height = 32 + max(len(label), len(meaning)) * LINE_HEIGHT
            rows.append({"top": y, "height": height, "label": label, "meaning": meaning})
            y += height
        footer = wrap_exact(section["footer"], 76)
        footer_top = y
        y += 32 + len(footer) * LINE_HEIGHT
        sections.append(
            {
                "top": start,
                "bottom": y,
                "heading": heading,
                "header_height": header_height,
                "rows": rows,
                "footer": footer,
                "footer_top": footer_top,
            }
        )
        y += 32
    note = wrap_exact(source["reading_note"], 76)
    note_top = y
    y += 32 + len(note) * LINE_HEIGHT + 24
    return {"height": y, "title": title, "sections": sections, "note": note, "note_top": note_top}


def field(canvas, name, lines, x, y, size=20, weight="400", color=style.INK):
    canvas.front(f'<g data-glossary-field="{name}">')
    for index, value in enumerate(lines):
        text(canvas, x, y + index * LINE_HEIGHT, value, size, weight, color)
    canvas.front("</g>")


def render_svg(source: dict) -> bytes:
    plan = layout(source)
    height = plan["height"]
    canvas = style.Canvas(
        WIDTH,
        height,
        source["title"],
        "Four reference tables containing the complete supplied wording for 36 entries, "
        "with four footers and a separate timing clarification.",
        "public-glossary",
    )
    field(canvas, "title", plan["title"], 24, 52, 30, "600")
    for section_index, section in enumerate(plan["sections"], 1):
        top = section["top"]
        canvas.front(
            f'<g data-glossary-section="{section_index}" '
            f'data-section-top="{top}" data-section-bottom="{section["bottom"]}">'
            f'<rect x="24" y="{top}" width="790" height="{section["header_height"]}" '
            f'fill="{style.LINK_TINT}"/>'
        )
        field(canvas, "section-title", section["heading"], 40, top + 34, 24, "600", style.LINK)
        header_y = top + section["header_height"]
        text(canvas, 40, header_y + 29, "Label", weight="600")
        text(canvas, 266, header_y + 29, "Meaning in this study", weight="600")
        for row_index, row in enumerate(section["rows"], 1):
            fill = style.PAPER_2 if row_index % 2 else style.PAPER
            canvas.front(
                f'<g data-glossary-row="{row_index}">'
                f'<rect x="24" y="{row["top"]}" width="790" height="{row["height"]}" '
                f'fill="{fill}" stroke="{style.RULE}" stroke-width="1"/>'
                f'<line x1="250" y1="{row["top"]}" x2="250" '
                f'y2="{row["top"] + row["height"]}" stroke="{style.RULE}"/>'
            )
            field(canvas, "label", row["label"], 40, row["top"] + 30, weight="600")
            field(canvas, "meaning", row["meaning"], 266, row["top"] + 30)
            canvas.front("</g>")
        field(
            canvas, "footer", section["footer"], 40, section["footer_top"] + 30, color=style.MUTED
        )
        canvas.front("</g>")
    canvas.front(
        f'<rect x="24" y="{plan["note_top"]}" width="790" '
        f'height="{32 + len(plan["note"]) * LINE_HEIGHT}" '
        f'fill="{style.ACCENT_TINT}" stroke="{style.ACCENT_RULE}"/>'
    )
    field(canvas, "reading-note", plan["note"], 40, plan["note_top"] + 30)
    svg = canvas.render().replace(
        f'width="{WIDTH}" height="{height}"',
        f'width="{2 * WIDTH}" height="{2 * height}"',
        1,
    )
    return (svg + "\n").encode("utf-8")


def render_markdown(source: dict) -> bytes:
    lines = [
        f"# {source['title']}",
        "",
        "Reference glossary of the labels and option-market terms used in the study. "
        "The four tables preserve the supplied wording. The methodology table adds "
        "24 definitions; the reference image preserves the original 36 entries.",
        "",
        "**Status: CURRENT.** [Current scientific evidence](CURRENT.md).",
        "",
        "[Complete PNG sheet](figures/public_refresh/glossary.png) · "
        "[Scalable SVG](figures/public_refresh/glossary.svg) · [Study overview](../README.md)",
        "",
    ]
    for section in source["sections"]:
        lines += [
            f"## {section['title']}",
            "",
            "| Label | Meaning in this study |",
            "| --- | --- |",
        ]
        for row in section["rows"]:
            assert "|" not in row["label"] + row["meaning"]
            lines.append(f"| {row['label']} | {row['meaning']} |")
        lines += ["", section["footer"], ""]
    note_source = Path(source["reading_note_source"])
    assert note_source.parts[0] == "docs" and (ROOT / note_source).is_file()
    lines += [
        "> " + source["reading_note"],
        "",
        f"[Timing rule]({Path(*note_source.parts[1:]).as_posix()}).",
        "",
    ]
    method_rows = source["method_rows"]
    assert len(method_rows) == 24 and len({row["label"] for row in method_rows}) == 24
    lines += [
        "## Methodology and evidence status",
        "",
        "| Term | Meaning in this study |",
        "| --- | --- |",
    ]
    for row in method_rows:
        assert "|" not in row["label"] + row["meaning"]
        lines.append(f"| {row['label']} | {row['meaning']} |")
    lines += [
        "",
        "OOS fitting ≠ prospective scientific design. Predictive information ≠ causality. "
        "Predictive information ≠ tradability. Statistical significance ≠ economic significance.",
        "",
        "B0, B1 and B2 are nested information sets, not necessarily independent economic feeds. "
        "The B2/B1 comparison tests for incremental information beyond the implemented B1 representation.",
        "",
        "<details>",
        "<summary>Reproduce and verify this reference sheet</summary>",
        "",
        "The [versioned text source](figures/public_refresh/glossary.json) drives both this "
        "page and the image. The [producer](figures/public_refresh/glossary.py) uses the "
        "existing repository figure palette and SVG-to-PNG rasterizer. Verification checks "
        "all 36 labels and meanings, the four section titles and footers, and the separate "
        "timing note against that source. No wording is shortened to fit the image. "
        "No model fits, statistical tests, market-data requests or prospective reads are run.",
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
        "</details>",
        "",
    ]
    return "\n".join(lines).encode("utf-8")


def inspect_svg(data: bytes, source: dict | None = None) -> dict:
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
    assert fonts
    sections = root.findall(".//*[@data-glossary-section]")
    counts = [len(s.findall("./*[@data-glossary-row]")) for s in sections]
    assert counts == [9, 8, 9, 10]
    if source is not None:

        def contents(parent, name):
            matches = parent.findall(f'./*[@data-glossary-field="{name}"]')
            assert len(matches) == 1
            return " ".join("".join(t.itertext()) for t in matches[0])

        assert contents(root, "title") == source["title"]
        for actual, expected in zip(sections, source["sections"], strict=True):
            assert contents(actual, "section-title") == expected["title"]
            assert contents(actual, "footer") == expected["footer"]
            for row, expected_row in zip(
                actual.findall("./*[@data-glossary-row]"), expected["rows"], strict=True
            ):
                assert contents(row, "label") == expected_row["label"]
                assert contents(row, "meaning") == expected_row["meaning"]
        assert contents(root, "reading-note") == source["reading_note"]
    return {
        "available_width_px": available,
        "intrinsic_width_px": int(root.attrib["width"]),
        "minimum_text_px": min(fonts),
        "text_elements": len(fonts),
        "section_rows": counts,
        "verbatim_source_checked": source is not None,
        "external_resources": 0,
    }


def rasterize(data: bytes) -> tuple[bytes, dict]:
    height = int(ET.fromstring(data).attrib["viewBox"].split()[3])
    # The existing rasterizer uses 96 dpi: a 1.5x SVG input yields a 2x PNG.
    raster_input = data.replace(
        f'width="{2 * WIDTH}" height="{2 * height}"'.encode(),
        f'width="{WIDTH * 1.5:g}" height="{height * 1.5:g}"'.encode(),
        1,
    )
    node = os.environ["RP4_FIGURE_NODE"]
    sharp = Path(os.environ["RP4_FIGURE_NODE_MODULES"]) / "sharp"
    result = subprocess.run(
        [node, str(RASTERIZER), str(sharp)], input=raster_input, capture_output=True, check=True
    )
    metadata = json.loads(result.stderr)
    assert metadata["width"] == 2 * WIDTH and metadata["height"] == 2 * height
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
    assert source["schema_version"] == "public-glossary-v2"
    svg, markdown = render_svg(source), render_markdown(source)
    readability = inspect_svg(svg, source)
    inputs = [SOURCE, Path(__file__), ROOT / "scripts/figure_style.py", RASTERIZER]
    inputs.append(ROOT / source["reading_note_source"])
    hashes = {p.relative_to(ROOT).as_posix(): input_hash(p) for p in inputs}
    if args.render:
        png, renderer = rasterize(svg)
        for path, data in [(SVG, svg), (PNG, png), (MARKDOWN, markdown)]:
            assert not path.exists() or path.is_file()
            path.write_bytes(data)
        receipt = {
            "schema_version": "public-glossary-render-v2",
            "source_wording_sha256": source["source_wording_sha256"],
            "input_sha256": hashes,
            "input_hash_mode": {"code": "utf8-crlf-to-lf", "other": "raw-bytes"},
            "output_sha256": {
                p.relative_to(ROOT).as_posix(): sha(p.read_bytes()) for p in [MARKDOWN, SVG, PNG]
            },
            "readability": readability,
            "png_renderer": renderer,
            "visual_review": {"status": "pending"},
            "scope": (
                "Verbatim reference wording and a separately identified timing clarification; "
                "no new empirical results or scientific execution."
            ),
        }
        RECEIPT.write_bytes((json.dumps(receipt, indent=2, ensure_ascii=False) + "\n").encode())
    else:
        receipt = json.loads(RECEIPT.read_text("utf-8"))
        assert receipt["source_wording_sha256"] == source["source_wording_sha256"]
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
        assert struct.unpack(">II", png[16:24]) == (2 * WIDTH, 2 * layout(source)["height"])
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
