"""Generate the repository's figure set from evidence, in one visual system.

Five figures, one palette, one type scale, one drawing grammar — see `figure_style`.
They are built to be read in order, and the README places them that way: what was found,
when it was tested, what was compared, where the data comes from, and why a measurement is
allowed to become a claim.

Nothing is drawn by hand. The evidence figure reads its numbers from the inference
artifact named by `data/CANONICAL_STATE.json`, so it cannot drift from the run it
describes. The others state design and governance, which are structural rather than
numeric, and carry no result.

    uv run python scripts/render_figures.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from figure_style import (  # noqa: E402
    ACCENT,
    ACCENT_TINT,
    INK,
    MONO,
    MUTED,
    PAPER,
    RULE_STRONG,
    SANS,
    SOFT,
    T_EDGE,
    T_SUB,
    T_TAG,
    Canvas,
    arrow_down,
    arrow_right,
    esc,
    footnote,
    header,
    legend,
    node,
    plane,
)

FIGURES = REPO / "docs" / "figures"
WIDTH = 880

FAMILY = {"gamma_glm": "Gamma GLM", "ridge_log": "ridge-log", "lightgbm_qlike": "LightGBM"}
UNIVERSE = {"D": "discovery", "V": "validation"}
CONTRAST = {"b1_over_b0": "ΔB1 · state", "b2_over_b1": "ΔB2|B1 · flow"}


# --- 1. the answer -----------------------------------------------------------------
def _contrasts() -> list[dict[str, Any]]:
    state = json.loads((REPO / "data" / "CANONICAL_STATE.json").read_text(encoding="utf-8"))
    run = state["scientific_bundle"]["run_id"]
    path = REPO / "artifacts" / "rp2_v3" / run / "rp2_block10_inference" / "inference.json"
    if not path.is_file():
        raise SystemExit(f"FIGURE_ARTIFACT_MISSING: {path.relative_to(REPO).as_posix()}")
    artifact = json.loads(path.read_text(encoding="utf-8"))

    rows = []
    for universe in ("D", "V"):
        for family, contrasts in artifact[universe]["nested_tests"].items():
            for key in ("b1_over_b0", "b2_over_b1"):
                if key not in contrasts:
                    continue
                cell = contrasts[key]
                rows.append(
                    {
                        "name": f"{UNIVERSE[universe]} · {FAMILY[family]} · {CONTRAST[key]}",
                        "estimate": cell["estimate"],
                        "ratio": cell["estimate"] / cell["mde"],
                        "clears": abs(cell["estimate"]) > cell["mde"],
                        "flow": key == "b2_over_b1",
                    }
                )
    if len(rows) != 12:
        raise SystemExit(f"FIGURE_CELL_COUNT: expected twelve contrasts, read {len(rows)}")
    return rows


def evidence() -> Canvas:
    rows = _contrasts()
    state_clears = sum(not row["flow"] and row["clears"] for row in rows)
    flow_clears = sum(row["flow"] and row["clears"] for row in rows)
    left, plot, row_h, top = 300, 440, 32, 132
    bottom = top + row_h * len(rows)
    canvas = Canvas(
        WIDTH,
        bottom + 108,
        "Twelve contrasts against the threshold each one declared",
        "Each nested contrast registered a minimum detectable effect before it was "
        f"measured. {state_clears + flow_clears} of twelve exceed their own threshold: "
        f"{state_clears} option state and {flow_clears} option flow.",
        "evidence",
    )
    header(
        canvas,
        "the answer",
        "Twelve contrasts, and the bar each one set for itself",
        "Past ±1 a contrast beat the threshold it registered before being measured.",
    )

    def x_of(ratio: float) -> float:
        clamped = max(-2.0, min(2.0, ratio))
        return left + plot * (clamped + 2.0) / 4.0

    zero = x_of(0.0)
    for ratio, dash in ((-1.0, "5,4"), (1.0, "5,4")):
        canvas.back(
            f'<line x1="{x_of(ratio):.0f}" y1="{top - 16}" x2="{x_of(ratio):.0f}" '
            f'y2="{bottom + 8}" stroke="{RULE_STRONG}" stroke-width="1" '
            f'stroke-dasharray="{dash}"/>'
        )
    canvas.back(
        f'<line x1="{zero:.0f}" y1="{top - 16}" x2="{zero:.0f}" y2="{bottom + 8}" '
        f'stroke="{RULE_STRONG}" stroke-width="1.2"/>'
        f'<text x="{x_of(1.0):.0f}" y="{top - 24}" fill="{SOFT}" font-family="{MONO}" '
        f'font-size="{T_TAG}" text-anchor="middle" letter-spacing="0.08em">'
        f"DECLARED THRESHOLD</text>"
    )

    for index, row in enumerate(rows):
        mid = top + index * row_h + row_h // 2
        if row["clears"]:
            colour = ACCENT if row["flow"] else INK
            weight = 5
        else:
            colour = RULE_STRONG
            weight = 3
        canvas.back(
            f'<text x="{left - 20}" y="{mid + 5}" fill="'
            f'{INK if row["clears"] else MUTED}" font-family="{SANS}" '
            f'font-size="{T_SUB}" text-anchor="end">{esc(row["name"])}</text>'
            f'<line x1="{zero:.0f}" y1="{mid}" x2="{x_of(row["ratio"]):.0f}" y2="{mid}" '
            f'stroke="{colour}" stroke-width="{weight}" stroke-linecap="round"/>'
            f'<circle cx="{x_of(row["ratio"]):.0f}" cy="{mid}" '
            f'r="{6 if row["clears"] else 4}" fill="{colour}"/>'
        )
        if row["clears"]:
            canvas.back(
                f'<text x="{x_of(row["ratio"]) + 16:.0f}" y="{mid + 5}" fill="{colour}" '
                f'font-family="{MONO}" font-size="{T_EDGE}">'
                f'{row["estimate"]:+.5f}</text>'
            )

    for ratio in (-2, -1, 0, 1, 2):
        canvas.back(
            f'<text x="{x_of(ratio):.0f}" y="{bottom + 28}" fill="{SOFT}" '
            f'font-family="{MONO}" font-size="{T_TAG}" text-anchor="middle">'
            f'{"0" if ratio == 0 else f"{ratio:+d}×"}</text>'
        )

    legend(
        canvas,
        bottom + 62,
        [(INK, "cleared · option state"), (ACCENT, "cleared · option flow"),
         (RULE_STRONG, "below its threshold")],
    )
    footnote(
        canvas,
        bottom + 92,
        "The amber cell is the one the sealed RP3 program exists to settle.",
    )
    return canvas


# --- 2. the programme in time ------------------------------------------------------
def timeline() -> Canvas:
    canvas = Canvas(
        WIDTH,
        330,
        "The programme from retrospective study to sealed future read",
        "A timeline: retrospective discovery and validation, one sealed prospective read "
        "already consumed, a cohort still collecting, and a preregistered read scheduled "
        "for 2029.",
        "timeline",
    )
    header(
        canvas,
        "when it was tested",
        "One read is spent, one is collecting, one is sealed until 2029",
        "A sealed cohort opens exactly once, under a protocol written before it existed.",
    )

    axis_y = 188
    canvas.back(
        f'<line x1="56" y1="{axis_y}" x2="{WIDTH - 56}" y2="{axis_y}" '
        f'stroke="{RULE_STRONG}" stroke-width="2"/>'
    )

    stops = [
        (108, "2024–2026", "Discovery", "retrospective", False, True),
        (268, "to 2026-05", "Validation", "not replicated", False, True),
        (436, "2026-08-30", "Phase 8 read", "MIXED_EXPLORATORY", False, False),
        (596, "~2026-11", "Phase 9", "still collecting", False, False),
        (768, "est. 2029-01-30", "RP3 sealed read", "662 sessions", True, False),
    ]
    for x, when, name, note, focal, above in stops:
        colour = ACCENT if focal else INK
        canvas.back(
            f'<circle cx="{x}" cy="{axis_y}" r="8" fill="{PAPER}" stroke="{colour}" '
            f'stroke-width="2.4"/>'
        )
        if focal:
            canvas.back(f'<circle cx="{x}" cy="{axis_y}" r="3.5" fill="{ACCENT}"/>')
        tick_y = axis_y - 20 if above else axis_y + 20
        text_y = axis_y - 84 if above else axis_y + 44
        canvas.back(
            f'<line x1="{x}" y1="{tick_y}" x2="{x}" y2="{axis_y - 8 if above else axis_y + 8}" '
            f'stroke="{RULE_STRONG}" stroke-width="1"/>'
        )
        canvas.front(
            f'<text x="{x}" y="{text_y}" fill="{SOFT}" font-family="{MONO}" '
            f'font-size="{T_TAG}" text-anchor="middle" letter-spacing="0.06em">'
            f"{esc(when.upper())}</text>"
            f'<text x="{x}" y="{text_y + 22}" fill="{colour}" font-family="{SANS}" '
            f'font-size="{T_SUB + 2}" font-weight="600" text-anchor="middle">'
            f"{esc(name)}</text>"
            f'<text x="{x}" y="{text_y + 40}" fill="{MUTED}" font-family="{SANS}" '
            f'font-size="{T_SUB}" text-anchor="middle">{esc(note)}</text>'
        )

    legend(
        canvas,
        300,
        [(INK, "measured or consumed"), (ACCENT, "sealed, not yet opened")],
    )
    return canvas


# --- 3. what was compared ----------------------------------------------------------
def information_sets() -> Canvas:
    canvas = Canvas(
        WIDTH,
        424,
        "Three nested information sets on one shared row mask",
        "B0 holds underlying and market history; B1 adds contemporaneous option state; "
        "B2 adds recent option flow. Because the sets nest and share one row mask, the "
        "step between two rungs isolates exactly one layer.",
        "sets",
    )
    header(
        canvas,
        "what was compared",
        "Each rung adds one layer, and nothing else",
        "The sets nest and share one row mask, so a step isolates a single information layer.",
    )

    boxes = [
        (72, 132, 736, 232, "B0 + B1 + B2", "adds recent point-in-time option flow", True),
        (120, 176, 640, 144, "B0 + B1", "adds contemporaneous option state", False),
        (168, 220, 544, 56, "B0", "underlying and broad-market history", False),
    ]
    for x, y, w, h, label, note, focal in boxes:
        fill = ACCENT_TINT if focal else PAPER
        stroke = ACCENT if focal else INK
        canvas.back(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="1.2"/>'
        )
        canvas.front(
            f'<text x="{x + 20}" y="{y + 26}" fill="{stroke}" font-family="{SANS}" '
            f'font-size="{T_SUB + 3}" font-weight="600">{esc(label)}</text>'
            f'<text x="{x + 20 + 12 * len(label)}" y="{y + 26}" fill="{MUTED}" '
            f'font-family="{SANS}" font-size="{T_SUB}">{esc(note)}</text>'
        )

    footnote(
        canvas,
        392,
        "The contrast under test is the outermost step: what recent option flow adds once "
        "option state is already known.",
    )
    return canvas


# --- 4. where the data comes from --------------------------------------------------
def pipeline() -> Canvas:
    canvas = Canvas(
        WIDTH,
        612,
        "From licensed provider data to a published, hash-pinned record",
        "Licensed panels are built and evaluated on one machine and never redistributed; "
        "what the repository publishes is aggregates, schemas and SHA-256 pointers, "
        "governed by a canonical state that refuses to promote what it cannot support.",
        "pipeline",
    )
    header(
        canvas,
        "where the data comes from",
        "Two planes, and the line between them",
        "Licensed panels never leave the machine. What is published is aggregates and hashes.",
    )

    plane(canvas, 56, 216, 768, 216, "licensed plane · local machine only")
    plane(canvas, 56, 468, 768, 96, "public plane · what the repository publishes", amber=True)

    node(canvas, 264, 120, 352, 60, "Market data providers", "FMP · Massive · Unusual Whales")
    node(canvas, 264, 244, 352, 60, "Point-in-time panel", "availability, not source time")
    node(canvas, 264, 352, 352, 60, "Frozen models and inference", "QLIKE · bootstrap · Holm")
    node(canvas, 264, 488, 352, 60, "Published record", "aggregates and SHA-256 pointers",
         focal=True)

    arrow_down(canvas, 440, 180, 240, "acquire")
    arrow_down(canvas, 440, 304, 348, "fit per information set")
    arrow_down(canvas, 440, 412, 484, "freeze and hash", accent=True)

    legend(canvas, 582, [(RULE_STRONG, "stays local"), (ACCENT, "leaves the machine")])
    return canvas


# --- 5. why a measurement may become a claim ---------------------------------------
def eligibility() -> Canvas:
    canvas = Canvas(
        WIDTH,
        560,
        "How a measurement becomes an eligible claim, or does not",
        "A measurement passes three gates: its method must have been frozen and hashed "
        "before any outcome was seen, its cohort must be opened only under an authorised "
        "one-shot read, and its point-in-time inputs must reconcile. Failing any gate "
        "keeps the number auditable but not current.",
        "eligibility",
    )
    header(
        canvas,
        "why you can trust it",
        "Three gates, and what happens when one does not open",
        "The canonical state refuses to promote a measurement it cannot support.",
    )

    node(canvas, 40, 132, 232, 64, "A measurement", "produced by a run")
    node(canvas, 324, 132, 232, 64, "Method frozen first?", "hashed before any outcome")
    node(canvas, 608, 132, 232, 64, "Read authorised?", "sealed cohort, opened once")
    node(canvas, 608, 268, 232, 64, "PIT inputs reconcile?", "availability proven")
    node(canvas, 608, 404, 232, 64, "Eligible claim", "may be stated as current", focal=True)
    node(canvas, 40, 404, 448, 64, "Historical measurement",
         "auditable, never a current claim", quiet=True)

    arrow_right(canvas, 272, 320, 164, "")
    arrow_right(canvas, 556, 604, 164, "")
    arrow_down(canvas, 724, 196, 264, "yes")
    arrow_down(canvas, 724, 332, 400, "yes", accent=True)

    # Any gate that does not open routes to the same place.
    canvas.back(
        f'<path d="M 608 300 H 520 Q 512 300 512 308 V 396" fill="none" stroke="{MUTED}" '
        f'stroke-width="1.6" stroke-dasharray="5,4" marker-end="url(#head)"/>'
        f'<rect x="450" y="330" width="60" height="18" rx="3" fill="{PAPER}"/>'
        f'<text x="480" y="344" fill="{MUTED}" font-family="{SANS}" font-size="{T_EDGE}" '
        f'text-anchor="middle">no</text>'
    )

    footnote(
        canvas,
        512,
        "The current bundle stops at the third gate, so its numbers stay historical. "
        "That is the state the repository publishes.",
    )
    legend(
        canvas,
        532,
        [(ACCENT, "eligible as a current claim"), (RULE_STRONG, "retained for audit")],
    )
    return canvas


BUILDERS = {
    "evidence": evidence,
    "programme-timeline": timeline,
    "information-sets": information_sets,
    "data-pipeline": pipeline,
    "eligibility-gates": eligibility,
}


def main() -> int:
    FIGURES.mkdir(parents=True, exist_ok=True)
    for slug, build in BUILDERS.items():
        canvas = build()
        target = FIGURES / f"{slug}.svg"
        target.write_text(canvas.render() + "\n", encoding="utf-8")
        print(f"[figure] {target.relative_to(REPO).as_posix()} {canvas.width}x{canvas.height}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
