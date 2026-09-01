"""Generate the five README figures from evidence, in one visual system.

Five README figures, one palette, one type scale, one drawing grammar — see `figure_style`.
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
    PAPER_2,
    RULE_STRONG,
    SANS,
    SOFT,
    Canvas,
    arrow_down,
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
UNIVERSE = {"D": "model development", "V": "held-out check"}
CONTRAST = {"b1_over_b0": "option state", "b2_over_b1": "option flow"}


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
                mde = cell["mde"]
                rows.append(
                    {
                        "group": UNIVERSE[universe],
                        "name": f"{FAMILY[family]} · {CONTRAST[key]}",
                        "estimate": cell["estimate"],
                        "ratio": cell["estimate"] / mde,
                        "lo": cell["ci_low"] / mde,
                        "hi": cell["ci_high"] / mde,
                        "sessions": cell["sessions"],
                        "clears": abs(cell["estimate"]) > mde,
                        "flow": key == "b2_over_b1",
                    }
                )
    if len(rows) != 12:
        raise SystemExit(f"FIGURE_CELL_COUNT: expected twelve contrasts, read {len(rows)}")
    return rows


# --- 1. the answer -----------------------------------------------------------------
def evidence() -> Canvas:
    rows = _contrasts()
    state = json.loads((REPO / "data" / "CANONICAL_STATE.json").read_text(encoding="utf-8"))
    lifecycle = state["scientific_bundle"]["eligibility"]["status"]
    state_clears = sum(not r["flow"] and r["clears"] for r in rows)
    flow_clears = sum(r["flow"] and r["clears"] for r in rows)

    gutter, plot_x, plot_w, row_h, top = 286, 306, 372, 31, 150
    span = 2.6
    groups: list[str] = []
    for r in rows:
        if r["group"] not in groups:
            groups.append(r["group"])
    gap = 26
    bottom = top + row_h * len(rows) + gap * (len(groups) - 1)

    canvas = Canvas(
        WIDTH,
        bottom + 104,
        "Twelve tests, and the bar each one set for itself before it ran",
        "Each test fixed in advance the smallest effect it could detect. "
        f"{state_clears + flow_clears} of twelve exceed their own threshold: "
        f"{state_clears} option state and {flow_clears} option flow.",
        "evidence",
    )
    header(
        canvas,
        "the answer",
        "Twelve tests, and the bar each one set for itself",
        "Option flow is always measured on top of option state. The line is the point "
        "estimate's uncertainty range.",
    )

    def x_of(ratio: float) -> float:
        return plot_x + plot_w * (max(-span, min(span, ratio)) + span) / (2 * span)

    for ratio, style in ((-1.0, "5,4"), (1.0, "5,4"), (0.0, "")):
        dash = f' stroke-dasharray="{style}"' if style else ""
        canvas.back(
            f'<line x1="{x_of(ratio):.0f}" y1="{top - 30}" x2="{x_of(ratio):.0f}" '
            f'y2="{bottom - 4}" stroke="{RULE_STRONG}" stroke-width="1.1"{dash}/>'
        )
    canvas.back(
        f'<text x="{x_of(1.0):.0f}" y="{top - 38}" fill="{SOFT}" font-family="{MONO}" '
        f'font-size="10" text-anchor="middle" letter-spacing="0.08em">'
        f"THE BAR IT SET BEFORE RUNNING</text>"
        f'<text x="{x_of(0.0):.0f}" y="{top - 38}" fill="{SOFT}" font-family="{MONO}" '
        f'font-size="10" text-anchor="middle" letter-spacing="0.08em">NO EFFECT</text>'
    )

    y = top
    current = None
    for row in rows:
        if row["group"] != current:
            current = row["group"]
            if row is not rows[0]:
                y += gap
            canvas.front(
                f'<text x="40" y="{y - 9}" fill="{SOFT}" font-family="{MONO}" font-size="10" '
                f'letter-spacing="0.1em">{esc(current.upper())}</text>'
            )
        cy = y + row_h // 2
        ink = INK if row["clears"] else MUTED
        band = INK if row["clears"] else RULE_STRONG
        lo, hi = x_of(row["lo"]), x_of(row["hi"])
        canvas.back(
            f'<rect x="{lo:.1f}" y="{cy - 4}" width="{max(2.0, hi - lo):.1f}" height="8" '
            f'rx="4" fill="{band}" opacity="{0.28 if row["clears"] else 0.55}"/>'
        )
        canvas.front(
            f'<text x="{gutter}" y="{cy + 4}" fill="{ink}" font-family="{SANS}" '
            f'font-size="12.5" text-anchor="end">{esc(row["name"])}</text>'
            f'<circle cx="{x_of(row["ratio"]):.1f}" cy="{cy}" r="4.6" fill="{ink}"/>'
            f'<text x="{plot_x + plot_w + 22}" y="{cy + 4}" fill="{ink}" font-family="{MONO}" '
            f'font-size="11.5">{row["ratio"]:+.2f}\u00d7</text>'
            f'<text x="{plot_x + plot_w + 94}" y="{cy + 4}" fill="{MUTED}" '
            f'font-family="{MONO}" font-size="11">{row["estimate"]:+.5f}</text>'
        )
        y += row_h

    for tick in (-2, -1, 0, 1, 2):
        canvas.front(
            f'<text x="{x_of(tick):.0f}" y="{bottom + 14}" fill="{SOFT}" '
            f'font-family="{MONO}" font-size="11" text-anchor="middle">'
            f'{"0" if tick == 0 else f"{tick:+d}\u00d7"}</text>'
        )
    canvas.front(
        f'<text x="{plot_x + plot_w + 22}" y="{top - 38}" fill="{SOFT}" font-family="{MONO}" '
        f'font-size="10" letter-spacing="0.08em">VS BAR</text>'
        f'<text x="{plot_x + plot_w + 94}" y="{top - 38}" fill="{SOFT}" font-family="{MONO}" '
        f'font-size="10" letter-spacing="0.08em">EFFECT</text>'
    )

    items = [(INK, "cleared the bar it set"), (RULE_STRONG, "did not clear it")]
    legend(canvas, bottom + 52, items, x=40)
    footnote(
        canvas,
        bottom + 84,
        f"{flow_clears} option-flow tests cleared their own bar. Status: {lifecycle}.",
        x=40,
    )
    return canvas


# --- 2. the programme in time ------------------------------------------------------
_A0, _A1 = "2024-07-01", "2026-07-17"   # panel A: the retrospective span
_B0, _B1 = "2026-07-18", "2026-12-31"   # panel B: the sealed programme, expanded
_AX, _AW = 214.0, 258.0
_BX, _BW = 516.0, 196.0


def _pos(day: str) -> float:
    """Two honest scales: a wide retrospective span, an expanded recent window."""
    from datetime import date

    d = date.fromisoformat(day)
    a0, a1 = date.fromisoformat(_A0), date.fromisoformat(_A1)
    b0, b1 = date.fromisoformat(_B0), date.fromisoformat(_B1)
    if d <= a1:
        f = (d - a0).days / (a1 - a0).days
        return _AX + max(0.0, min(1.0, f)) * _AW
    f = (d - b0).days / (b1 - b0).days
    return _BX + max(0.0, min(1.0, f)) * _BW


def timeline() -> Canvas:
    canvas = Canvas(
        WIDTH,
        446,
        "How the evidence accumulated, and what remains sealed",
        "Two years of retrospective sessions, one sealed read already spent, one cohort "
        "still collecting, and one read sealed until 2029.",
        "timeline",
    )
    header(
        canvas,
        "when it was tested",
        "What has been measured, and what is still sealed",
        "Bar length is time. A sealed test may be opened only once, and never reopened.",
    )

    top, step, bar_h = 168, 46, 20
    base, foot = top - 16, top + step * 4 - 12

    for x, w, label in ((_AX, _AW, "past data  2024 – 2026"),
                        (_BX, _BW, "sealed tests  from 2026")):
        canvas.back(
            f'<rect x="{x - 10}" y="{base}" width="{w + 20}" height="{foot - base}" rx="6" '
            f'fill="{PAPER_2}"/>'
            f'<text x="{x + w / 2}" y="{foot + 18}" fill="{SOFT}" font-family="{MONO}" '
            f'font-size="11" letter-spacing="0.08em" text-anchor="middle">{esc(label)}</text>'
        )

    for year in ("2025-01-01", "2026-01-01"):
        gx = _pos(year)
        canvas.back(
            f'<line x1="{gx:.1f}" y1="{base}" x2="{gx:.1f}" y2="{foot}" '
            f'stroke="{RULE_STRONG}" stroke-width="1" stroke-dasharray="3,4"/>'
            f'<text x="{gx:.1f}" y="{base - 8}" fill="{SOFT}" font-family="{MONO}" '
            f'font-size="12" text-anchor="middle">{year[:4]}</text>'
        )

    tx = _pos("2026-09-01")
    canvas.back(
        f'<line x1="{tx:.1f}" y1="{base}" x2="{tx:.1f}" y2="{foot}" stroke="{MUTED}" '
        f'stroke-width="1.4"/>'
        f'<text x="{tx:.1f}" y="{base - 8}" fill="{MUTED}" font-family="{MONO}" '
        f'font-size="12" text-anchor="middle">today</text>'
    )

    rows = [
        ("Model development", "2024-08-02", "2026-03-23", "389 trading days", "solid"),
        ("Held-out check", "2026-03-24", "2026-07-17", "80 trading days", "hollow"),
        ("Sealed test 1", "2026-07-20", "2026-08-28", "30 days · opened", "solid"),
        ("Sealed test 2", "2026-08-19", "2026-12-31", "10 of 60 days so far", "fade"),
    ]
    canvas.back(
        f'<defs><linearGradient id="collecting" x1="0" x2="1">'
        f'<stop offset="0" stop-color="{INK}" stop-opacity="0.9"/>'
        f'<stop offset="1" stop-color="{INK}" stop-opacity="0.10"/></linearGradient></defs>'
    )

    for i, (name, a, b, note, kind) in enumerate(rows):
        y = top + i * step
        x0, x1 = _pos(a), _pos(b)
        w = max(7.0, x1 - x0)
        canvas.front(
            f'<text x="40" y="{y + 14}" fill="{INK}" font-family="{SANS}" font-size="16" '
            f'font-weight="600">{esc(name)}</text>'
            f'<text x="40" y="{y + 32}" fill="{MUTED}" font-family="{SANS}" '
            f'font-size="12">{esc(note)}</text>'
        )
        fill = {"solid": INK, "hollow": PAPER, "fade": "url(#collecting)"}[kind]
        stroke = f' stroke="{INK}" stroke-width="1.6"' if kind == "hollow" else ""
        canvas.front(
            f'<rect x="{x0:.1f}" y="{y}" width="{w:.1f}" height="{bar_h}" rx="3" '
            f'fill="{fill}"{stroke}/>'
        )

    ry = top + 2 * step + bar_h // 2
    rx = _pos("2026-08-30")
    canvas.front(
        f'<circle cx="{rx:.1f}" cy="{ry}" r="7.5" fill="{PAPER}" stroke="{INK}" '
        f'stroke-width="2.4"/><circle cx="{rx:.1f}" cy="{ry}" r="3.2" fill="{INK}"/>'
    )

    for dx in (0, 8):
        canvas.back(
            f'<path d="M {486 + dx} {base + 8} l 8 12 l -8 12" fill="none" '
            f'stroke="{RULE_STRONG}" stroke-width="1.4"/>'
        )

    fx, fy = 748, top + step
    canvas.front(
        f'<rect x="{fx}" y="{fy}" width="88" height="74" rx="6" fill="{ACCENT_TINT}" '
        f'stroke="{ACCENT}" stroke-width="1.4"/>'
        f'<text x="{fx + 44}" y="{fy + 24}" fill="{INK}" font-family="{SANS}" font-size="15" '
        f'font-weight="600" text-anchor="middle">Sealed</text>'
        f'<text x="{fx + 44}" y="{fy + 42}" fill="{MUTED}" font-family="{SANS}" '
        f'font-size="11" text-anchor="middle">test 3</text>'
        f'<text x="{fx + 44}" y="{fy + 60}" fill="{ACCENT}" font-family="{MONO}" '
        f'font-size="12" text-anchor="middle">2029</text>'
    )

    legend(
        canvas,
        400,
        [(INK, "measured and reported"), (MUTED, "still collecting"),
         (ACCENT, "sealed, not yet opened")],
        x=40,
    )
    canvas.front(
        f'<circle cx="46" cy="{426}" r="6" fill="{PAPER}" stroke="{INK}" stroke-width="2"/>'
        f'<circle cx="46" cy="{426}" r="2.6" fill="{INK}"/>'
        f'<text x="60" y="{430}" fill="{INK}" font-family="{SANS}" font-size="13">'
        f'Sealed test 1 was opened on 2026-08-30 and gave a mixed result, not a confirmation. '
        f'Each test is locked to a written protocol before its data exists, and opens '
        f'only once.</text>'
    )
    return canvas


def _layer_counts() -> list[int]:
    """Feature counts read from the run the canonical state names."""
    state = json.loads((REPO / "data" / "CANONICAL_STATE.json").read_text(encoding="utf-8"))
    run = state["scientific_bundle"]["run_id"]
    path = REPO / "artifacts" / "rp2_v3" / run / "rp2_block10_inference" / "inference.json"
    sets = json.loads(path.read_text(encoding="utf-8"))["D"]["information_sets"]
    seen: list[str] = []
    counts: list[int] = []
    for key in ("B0", "B0+B1", "B0+B1+B2"):
        names = sets[key]["resolved_feature_names"]
        counts.append(len([n for n in names if n not in seen]))
        seen = list(names)
    return counts


def information_sets() -> Canvas:
    """Each chip is a plain reading of a registered feature name; nothing is added."""
    base, first, second = _layer_counts()
    total = base + first + second

    layers = [
        (
            "The stock and the market",
            base,
            ["movement 5, 15, 30 min", "previous day", "week", "session so far",
             "returns", "up and down moves", "jumps", "volume", "dollar volume",
             "time of day", "S&P 500", "Nasdaq"],
            False,
        ),
        (
            "The option surface, at that moment",
            first,
            ["implied volatility 7, 30, 60 days", "term slope", "smile", "risk reversal",
             "quote age", "spread width", "surface coverage", "implied minus realised"],
            False,
        ),
        (
            "Option trading, last five minutes",
            second,
            ["premium traded", "trade count", "buy share", "delta flow", "vega flow",
             "short-dated vega", "strike concentration", "same-day expiries",
             "multi-leg share", "implied-volatility change", "arrival intensity",
             "provider latency"],
            True,
        ),
    ]

    top, gap, pad = 132, 18, 26
    x0, x1 = 40, WIDTH - 40
    chip_h, chip_gap, line_h = 22, 7, 29

    def chip_w(text: str) -> float:
        return 6.05 * len(text) + 20

    def rows_for(chips: list[str]) -> list[list[str]]:
        out: list[list[str]] = []
        line: list[str] = []
        used = 0.0
        span = (x1 - pad) - (x0 + pad)
        for c in chips:
            w = chip_w(c)
            if line and used + w + chip_gap > span:
                out.append(line)
                line, used = [c], w
            else:
                line.append(c)
                used += w + chip_gap
        if line:
            out.append(line)
        return out

    laid = [rows_for(c) for _, _, c, _ in layers]
    heights = [58 + len(r) * line_h for r in laid]
    height = top + sum(heights) + gap * 2 + 76

    canvas = Canvas(
        WIDTH,
        height,
        "What went into each model",
        f"Three information sets on identical rows: {base} measures of the stock and market, "
        f"{first} of the option surface and {second} of recent option trading, {total} in all.",
        "information-sets",
    )
    header(
        canvas,
        "what was compared",
        "What went into each model",
        "Each step adds one kind of information and nothing else.",
    )

    y = top
    for index, ((name, count, _, focal), lines) in enumerate(zip(layers, laid, strict=True)):
        band_h = heights[index]
        canvas.back(
            f'<rect x="{x0}" y="{y}" width="{x1 - x0}" height="{band_h}" rx="8" '
            f'fill="{ACCENT_TINT if focal else PAPER}" stroke="{ACCENT if focal else RULE_STRONG}" '
            f'stroke-width="1.4"/>'
        )
        canvas.front(
            f'<text x="{x0 + pad}" y="{y + 32}" fill="{INK}" font-family="{SANS}" '
            f'font-size="17" font-weight="600">{esc(name)}</text>'
            f'<text x="{x1 - pad}" y="{y + 32}" fill="{ACCENT if focal else MUTED}" '
            f'font-family="{MONO}" font-size="13" text-anchor="end">'
            f'{"+" if index else ""}{count}</text>'
        )
        cy = y + 52
        for line in lines:
            cx = float(x0 + pad)
            for text in line:
                w = chip_w(text)
                canvas.front(
                    f'<rect x="{cx:.1f}" y="{cy}" width="{w:.1f}" height="{chip_h}" rx="11" '
                    f'fill="{PAPER}" stroke="{RULE_STRONG}" stroke-width="1"/>'
                    f'<text x="{cx + w / 2:.1f}" y="{cy + 15}" fill="{MUTED}" '
                    f'font-family="{SANS}" font-size="11.5" text-anchor="middle">'
                    f"{esc(text)}</text>"
                )
                cx += w + chip_gap
            cy += line_h
        if index < 2:
            canvas.back(
                f'<text x="{WIDTH // 2}" y="{y + band_h + 14}" fill="{SOFT}" '
                f'font-family="{SANS}" font-size="17" text-anchor="middle">+</text>'
            )
        y += band_h + gap

    footnote(
        canvas,
        height - 30,
        f"All three are scored on the same moments, so each step measures only what it adds. "
        f"{total} measures in total.",
        x=40,
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
    node(canvas, 264, 244, 352, 60, "Point-in-time panel", "what was knowable at the time")
    node(canvas, 264, 352, 352, 60, "Frozen models and inference", "scored, then error bars")
    node(canvas, 264, 488, 352, 60, "Published record", "summary results and fingerprints",
         focal=True)

    arrow_down(canvas, 440, 180, 240, "acquire")
    arrow_down(canvas, 440, 304, 348, "one model per step")
    arrow_down(canvas, 440, 412, 484, "freeze and hash", accent=True)

    legend(canvas, 582, [(RULE_STRONG, "stays local"), (ACCENT, "leaves the machine")])
    return canvas


# --- 5. why a measurement may become a claim ---------------------------------------
def eligibility() -> Canvas:
    """The three permissions the canonical state actually records, and their real values."""
    state = json.loads((REPO / "data" / "CANONICAL_STATE.json").read_text(encoding="utf-8"))
    successor = state["pit_v22_successor_evaluation"]
    headline = state["canonical_results"]["status"]

    checks = [
        (
            "Is the one-shot scientific result reportable?",
            successor["scientific_result"]["eligible"],
            "Yes. The frozen result, log, ledger and content-addressed payloads passed "
            "independent custody validation.",
        ),
        (
            "Does it establish a global option-information edge?",
            successor["edge_claim_eligible"],
            "No. No registered estimate met its development-frozen MDE, and the contract "
            "contained no binary edge-promotion rule.",
        ),
        (
            "May it authorize capital or live trading?",
            successor["capital_eligible"],
            "No. The result is research-only, observational and not evidence of live "
            "trading profitability.",
        ),
    ]

    card_h, gap, top = 96, 16, 138
    height = top + card_h * 3 + gap * 2 + 132
    canvas = Canvas(
        WIDTH,
        height,
        "The three permissions this project checks before a number becomes a claim",
        "The scientific result is reportable after custody validation; edge and capital "
        "promotion remain withheld.",
        "eligibility-gates",
    )
    header(
        canvas,
        "why you can trust it",
        "One reportable result; no edge or capital promotion",
        "The one-shot result stays visible without being promoted beyond its frozen rules.",
    )

    for index, (question, granted, why) in enumerate(checks):
        y = top + index * (card_h + gap)
        mark = "YES" if granted else "NO"
        canvas.back(
            f'<rect x="40" y="{y}" width="{WIDTH - 80}" height="{card_h}" rx="8" fill="{PAPER}" '
            f'stroke="{RULE_STRONG}" stroke-width="1.4"/>'
            f'<rect x="40" y="{y}" width="5" height="{card_h}" rx="2.5" fill="{INK}"/>'
        )
        canvas.front(
            f'<text x="70" y="{y + 34}" fill="{INK}" font-family="{SANS}" font-size="16" '
            f'font-weight="600">{esc(question)}</text>'
            f'<text x="70" y="{y + 62}" fill="{MUTED}" font-family="{SANS}" '
            f'font-size="12.5">{esc(why[:96])}</text>'
            f'<rect x="{WIDTH - 122}" y="{y + 30}" width="52" height="26" rx="13" '
            f'fill="{PAPER_2}" stroke="{INK}" stroke-width="1.4"/>'
            f'<text x="{WIDTH - 96}" y="{y + 48}" fill="{INK}" font-family="{MONO}" '
            f'font-size="13" font-weight="600" text-anchor="middle">{mark}</text>'
        )

    band = top + card_h * 3 + gap * 2 + 22
    canvas.back(
        f'<rect x="40" y="{band}" width="{WIDTH - 80}" height="60" rx="8" fill="{ACCENT_TINT}" '
        f'stroke="{ACCENT}" stroke-width="1.4"/>'
    )
    canvas.front(
        f'<text x="70" y="{band + 26}" fill="{INK}" font-family="{SANS}" font-size="15" '
        f'font-weight="600">Scientific result eligible; global edge not confirmed.</text>'
        f'<text x="70" y="{band + 47}" fill="{MUTED}" font-family="{SANS}" font-size="12.5">'
        f'One authorized OOS read, zero retuning, and no second execution permitted.</text>'
    )
    footnote(
        canvas,
        height - 26,
        f"Every number stays auditable; scientific eligibility does not imply an edge or "
        f"capital claim. Machine status: {headline}.",
        x=40,
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
