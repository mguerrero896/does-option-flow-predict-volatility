"""Draw the twelve headline contrasts against the bar each one set for itself.

The repository used to publish a chart of a decaying option-flow effect. Its subject was
the `-0.0277/year` decay line, which is withdrawn: era point estimates rise rather than
fall, all below their familywise threshold, and a time split cannot separate a regime
change from a smaller training sample. There is nothing to update that chart to.

What the evidence does support is sharper, and it is the study's actual result. Each
nested contrast declares a minimum detectable effect before it is measured. Twelve
contrasts were run. Three clear their own threshold, and one of those three is a *flow*
contrast — the cell that the sealed RP3 program exists to settle. A chart of estimate
against declared threshold shows that in one picture, including the exception, which a
decay line never could.

Every number is read from the run named by `data/CANONICAL_STATE.json`; nothing here is
authored by hand.

    uv run python scripts/render_evidence_figure.py
"""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
STATE = REPO / "data" / "CANONICAL_STATE.json"
TARGET = REPO / "docs" / "figures" / "contrasts_against_their_threshold.svg"

FAMILY_LABEL = {
    "gamma_glm": "Gamma GLM",
    "ridge_log": "ridge-log",
    "lightgbm_qlike": "LightGBM",
}
CONTRAST_LABEL = {"b1_over_b0": "ΔB1 (state)", "b2_over_b1": "ΔB2|B1 (flow)"}
UNIVERSE_LABEL = {"D": "discovery", "V": "validation"}

WIDTH = 900
ROW_HEIGHT = 34
TOP = 118
LEFT = 268
PLOT_WIDTH = 560
#: The axis is the ratio of estimate to declared threshold, so 1.0 is "cleared its bar".
AXIS_MAX = 2.0

INK = "#1a2332"
MUTED = "#6b7684"
RULE = "#d8dee7"
STATE_COLOUR = "#2f6f5e"
FLOW_COLOUR = "#c2410c"
BELOW = "#9aa4b2"


def _cells() -> list[dict[str, Any]]:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    run_id = state["scientific_bundle"]["run_id"]
    path = REPO / "artifacts" / "rp2_v3" / run_id / "rp2_block10_inference" / "inference.json"
    if not path.is_file():
        raise SystemExit(f"EVIDENCE_ARTIFACT_MISSING: {path.relative_to(REPO).as_posix()}")
    artifact = json.loads(path.read_text(encoding="utf-8"))

    cells = []
    for universe in ("D", "V"):
        for family, contrasts in artifact[universe]["nested_tests"].items():
            for key, label in CONTRAST_LABEL.items():
                if key not in contrasts:
                    continue
                cell = contrasts[key]
                estimate, mde = cell["estimate"], cell["mde"]
                cells.append(
                    {
                        "universe": universe,
                        "family": family,
                        "key": key,
                        "label": label,
                        "estimate": estimate,
                        "mde": mde,
                        "ratio": estimate / mde,
                        "clears": abs(estimate) > mde,
                        "flow": key == "b2_over_b1",
                    }
                )
    if len(cells) != 12:
        raise SystemExit(f"EVIDENCE_CELL_COUNT: expected twelve contrasts, read {len(cells)}")
    return cells


def _x(ratio: float) -> float:
    clamped = max(-AXIS_MAX, min(AXIS_MAX, ratio))
    return LEFT + PLOT_WIDTH * (clamped + AXIS_MAX) / (2 * AXIS_MAX)


def _svg(cells: list[dict[str, Any]]) -> str:
    cleared = [c for c in cells if c["clears"]]
    flow_cleared = [c for c in cleared if c["flow"]]
    height = TOP + ROW_HEIGHT * len(cells) + 92

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{height}" '
        f'viewBox="0 0 {WIDTH} {height}" role="img" aria-label="Twelve nested contrasts '
        f'against the minimum detectable effect each declared">',
        "<style>"
        f"text{{font-family:'DejaVu Sans',Arial,sans-serif;fill:{INK}}}"
        ".t{font-size:19px;font-weight:700}"
        f".s{{font-size:13px;fill:{MUTED}}}"
        ".row{font-size:12.5px}"
        f".ax{{font-size:11px;fill:{MUTED}}}"
        ".k{font-size:11.5px}"
        "</style>",
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        '<text x="34" y="42" class="t">Twelve contrasts, and the bar each one set for '
        "itself</text>",
        '<text x="34" y="66" class="s">Estimate divided by its own declared minimum '
        "detectable effect. Past ±1, a contrast cleared the threshold it registered "
        "before it was measured.</text>",
    ]

    zero, one, minus_one = _x(0.0), _x(1.0), _x(-1.0)
    bottom = TOP + ROW_HEIGHT * len(cells)

    for x, dash in ((minus_one, "5 4"), (one, "5 4")):
        out.append(
            f'<line x1="{x:.1f}" y1="{TOP - 16}" x2="{x:.1f}" y2="{bottom + 6}" '
            f'stroke="{RULE}" stroke-width="1.5" stroke-dasharray="{dash}"/>'
        )
    out.append(
        f'<line x1="{zero:.1f}" y1="{TOP - 16}" x2="{zero:.1f}" y2="{bottom + 6}" '
        f'stroke="{RULE}" stroke-width="1.5"/>'
    )
    out.append(
        f'<text x="{one:.1f}" y="{TOP - 24}" class="ax" text-anchor="middle">'
        f"declared threshold</text>"
    )

    for index, cell in enumerate(cells):
        y = TOP + index * ROW_HEIGHT
        mid = y + ROW_HEIGHT / 2
        colour = (FLOW_COLOUR if cell["flow"] else STATE_COLOUR) if cell["clears"] else BELOW
        name = (
            f"{UNIVERSE_LABEL[cell['universe']]} · {FAMILY_LABEL[cell['family']]} · "
            f"{cell['label']}"
        )
        out.append(
            f'<text x="{LEFT - 16}" y="{mid + 4}" class="row" text-anchor="end" '
            f'fill="{INK if cell["clears"] else MUTED}">{html.escape(name)}</text>'
        )
        out.append(
            f'<line x1="{zero:.1f}" y1="{mid:.1f}" x2="{_x(cell["ratio"]):.1f}" '
            f'y2="{mid:.1f}" stroke="{colour}" stroke-width="{5 if cell["clears"] else 3}" '
            f'stroke-linecap="round"/>'
        )
        out.append(
            f'<circle cx="{_x(cell["ratio"]):.1f}" cy="{mid:.1f}" '
            f'r="{5.5 if cell["clears"] else 4}" fill="{colour}"/>'
        )
        if cell["clears"]:
            out.append(
                f'<text x="{_x(cell["ratio"]) + 14:.1f}" y="{mid + 4}" class="k" '
                f'fill="{colour}">{cell["estimate"]:+.5f}</text>'
            )

    for ratio in (-2, -1, 0, 1, 2):
        out.append(
            f'<text x="{_x(ratio):.1f}" y="{bottom + 24}" class="ax" '
            f'text-anchor="middle">{ratio:+d}×</text>'.replace("+0×", "0")
        )

    summary = (
        f"{len(cleared)} of {len(cells)} clear their own threshold. "
        f"{len(cleared) - len(flow_cleared)} are option state; "
        f"{len(flow_cleared)} is option flow — the cell the sealed RP3 program exists to settle."
    )
    out.append(f'<text x="34" y="{bottom + 58}" class="s">{html.escape(summary)}</text>')
    out.append("</svg>")
    return "\n".join(out)


def main() -> int:
    cells = _cells()
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(_svg(cells) + "\n", encoding="utf-8")
    cleared = [c for c in cells if c["clears"]]
    print(
        f"[figure] {TARGET.relative_to(REPO).as_posix()} "
        f"{len(cleared)}/{len(cells)} clear their threshold "
        f"({', '.join(c['universe'] + ' ' + c['family'] + ' ' + c['key'] for c in cleared)})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
