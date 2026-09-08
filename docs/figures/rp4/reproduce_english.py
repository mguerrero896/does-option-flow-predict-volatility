"""Reproduce English presentation figures from five saved public aggregate CSVs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
ARCHIVE = ROOT / "docs/archive/rp4/figure_originals"
sys.path.insert(0, str(ROOT))

from artifacts.rp4_closeout_figures_code import additions, build  # noqa: E402

NS = "http://www.w3.org/2000/svg"
ET.register_namespace("", NS)
NUMBER = re.compile(r"\d+(?:\.\d+)?")
SPANISH = re.compile(
    r"frente|diferencias|sesiones|orígenes|Primaria|Confirmación|reescalado|"
    r"Lineal|lineal|Positivo|observado|[áéíóúñ]"
)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load_json(path: Path) -> Any:
    return json.loads(path.read_text("utf-8"))


def public_csv_inputs() -> list[Path]:
    return [ROOT / "artifacts/rp4_closeout_figures/comparison_v1_v4.csv"] + [
        ROOT / build.source_folder("v4", horizon, window) / "session_losses.csv"
        for horizon in (15, 5)
        for window in build.WINDOWS
    ]


def original_svg_bytes() -> dict[str, bytes]:
    """Call existing pure renderers without their sealed, write-once run entry points."""
    rows = build.read_csv(public_csv_inputs()[0])
    assert len(rows) == 40, "The saved comparison must retain all 40 rows"
    for row in rows:
        row["horizon_minutes"] = int(row["horizon_minutes"])
    results = {}
    for horizon in (15, 5):
        for window in build.WINDOWS:
            sessions = build.read_csv(
                ROOT / build.source_folder("v4", horizon, window) / "session_losses.csv"
            )
            # The curve renderer uses only N_sessions from its summary argument.
            # Derive that count directly from the saved CSV; no targets are read.
            results["v4", horizon, window] = ({"N_sessions": len(sessions)}, sessions)
    figures = {
        "comparison_v1_v4.svg": build.comparison_svg(rows),
        "thesis_summary.svg": additions.thesis_svg(rows)[0],
    }
    for contrast, base, richer in build.CONTRASTS:
        figures[f"v4_{contrast}_cumulative.svg"] = build.cumulative_svg(
            results, contrast, base, richer
        )[0]
        figures[f"v4_{contrast}_cumulative_v2.svg"] = additions.revised_curve(
            results, contrast, base, richer
        )[0]
    return figures


def english_svg(data: bytes, labels: dict[str, Any]) -> tuple[bytes, dict[str, int]]:
    root = ET.fromstring(data)
    changed = 0
    numbers = 0
    for element in root.iter():
        before = element.text
        if not before or not before.strip():
            continue
        after = labels["exact"].get(before, before)
        if before not in labels["exact"]:
            for old, new in labels["phrases"]:
                after = after.replace(old, new)
        assert NUMBER.findall(before) == NUMBER.findall(after), "Numeric label drift"
        assert not SPANISH.search(after), f"Untranslated label: {after}"
        numbers += len(NUMBER.findall(before))
        changed += before != after
        element.text = after
    translated = ET.tostring(root, encoding="utf-8")
    old_nodes, new_nodes = list(ET.fromstring(data).iter()), list(root.iter())
    assert len(old_nodes) == len(new_nodes)
    for old, new in zip(old_nodes, new_nodes, strict=True):
        assert (old.tag, old.attrib, old.tail) == (new.tag, new.attrib, new.tail), (
            "Non-text SVG geometry or structure changed"
        )
    return translated, {
        "xml_elements_with_identical_attributes": len(old_nodes),
        "numeric_tokens_preserved_in_order_per_text_node": numbers,
        "translated_text_nodes": changed,
    }


def render_svg_set() -> tuple[dict[str, bytes], dict[str, dict[str, int]]]:
    mapping = load_json(ARCHIVE / "original_paths.json")
    labels = load_json(HERE / "labels_en.json")
    assert labels["schema_version"] == "rp4-figure-labels-en-v1"
    figures, checks = {}, {}
    for name, original in original_svg_bytes().items():
        logical = f"docs/figures/rp4/{name}"
        record = mapping[logical]
        saved = (ROOT / record["archive_path"]).read_bytes()
        assert sha(saved) == record["sha256"], f"Archived original changed: {name}"
        assert original == saved, f"Existing producer no longer reproduces its original: {name}"
        figures[name], checks[name] = english_svg(original, labels)
    return figures, checks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--verify", action="store_true", help="Verify without writing outputs")
    mode.add_argument("--render", action="store_true", help="Reproduce the six current SVGs")
    parser.add_argument(
        "--png", action="store_true", help="Also rasterize using the saved renderer"
    )
    args = parser.parse_args()
    if args.png and not args.render:
        parser.error("--png requires --render")
    receipt = load_json(HERE / "translation_receipt.json")
    assert receipt["schema_version"] == "rp4-figure-english-presentation-v1"
    assert (
        sha((ARCHIVE / "original_paths.json").read_bytes()) == receipt["original_paths_map_sha256"]
    ), "Original figure map changed"
    assert set(receipt["input_sha256"]) == {
        path.relative_to(ROOT).as_posix() for path in public_csv_inputs()
    }
    for collection in ("input_sha256", "producer_sha256"):
        for relative, expected in receipt[collection].items():
            assert sha((ROOT / relative).read_bytes()) == expected, (
                f"Changed {collection}: {relative}"
            )
    for relative, record in load_json(ARCHIVE / "original_paths.json").items():
        assert sha((ROOT / record["archive_path"]).read_bytes()) == record["sha256"], relative
    figures, checks = render_svg_set()
    assert checks == receipt["svg_invariants"]
    for name, data in figures.items():
        relative = f"docs/figures/rp4/{name}"
        assert sha(data) == receipt["output_sha256"][relative], f"Regenerated SVG changed: {name}"
    if args.png:
        node = Path(os.environ["RP4_FIGURE_NODE"])
        modules = Path(os.environ["RP4_FIGURE_NODE_MODULES"])
        for name, data in list(figures.items()):
            png, metadata = build.rasterize(
                data, node, modules, ROOT / "artifacts/rp4_closeout_figures_code/rasterize.cjs"
            )
            png_name = str(Path(name).with_suffix(".png"))
            assert metadata == receipt["png_renderers"][png_name], "Renderer environment changed"
            assert sha(png) == receipt["output_sha256"][f"docs/figures/rp4/{png_name}"], (
                "PNG bytes changed; compare the recorded renderer and installed fonts"
            )
            figures[png_name] = png
    if args.render:
        for name, data in figures.items():
            (HERE / name).write_bytes(data)
    for relative, expected in receipt["output_sha256"].items():
        assert sha((ROOT / relative).read_bytes()) == expected, (
            f"Changed current figure: {relative}"
        )
    print(
        json.dumps(
            {
                "status": "PASS",
                "public_csv_inputs": 5,
                "original_svgs_reproduced_byte_exact": 6,
                "current_figures_verified": 12,
                "geometry_and_numeric_labels_preserved": True,
                "model_fits": 0,
                "new_bootstrap_repetitions": 0,
                "outputs_written": len(figures) if args.render else 0,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
