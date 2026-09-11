"""Reader diagnostics from public aggregates; no refitting or new inference."""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from docs.figures.public_refresh.render_readme_figures import (  # noqa: E402
    ASSETS,
    FAMILIES,
    STATISTICS,
    box,
    curve_data,
    label,
    line,
    read_csv,
)
from scripts import figure_style as s  # noqa: E402

OUT = ROOT / "docs/figures/public_refresh"
LOSSES = "artifacts/rp4_v4_b2_rv15/session_losses.csv"


def canvas(title: str, subtitle: str, height: int = 620):
    c = s.Canvas(1200, height, title, subtitle, title.lower().replace(" ", "-"))
    label(c, 40, 52, title, 30, weight="600")
    label(c, 40, 88, subtitle, 19, s.MUTED)
    return c


def dot(c, x, y, color, radius=6, opacity=1):
    c.front(
        f'<circle cx="{x:.3f}" cy="{y:.3f}" r="{radius}" fill="{color}" fill-opacity="{opacity}"/>'
    )


def comparisons() -> bytes:
    rows = [
        r for r in read_csv(STATISTICS) if r["horizon_minutes"] == "15" and r["window"] == "primary"
    ]
    assert len(rows) == 4 and all(int(r["N_sessions"]) == 419 for r in rows)
    c = canvas(
        "Which information improves the forecast?",
        "Saved mean QLIKE differences and 95% bootstrap intervals · 419 historical sessions",
    )
    low = min(0, *(float(r["ci_low"]) for r in rows)) - 0.0003
    high = max(float(r["ci_high"]) for r in rows) + 0.0003

    def x(v):
        return 430 + (v - low) / (high - low) * 710

    line(c, x(0), 122, x(0), 430, s.INK, 2)
    for i, (family, contrast) in enumerate(
        (f, k) for f in FAMILIES for k in ("B1_over_B0", "B2_over_B1")
    ):
        r = next(r for r in rows if r["family"] == family and r["contrast"] == contrast)
        y = 160 + i * 78
        color = s.LINK if family == FAMILIES[0] else "#a8640a"
        label(
            c,
            40,
            y,
            ("Linear" if family == FAMILIES[0] else "Trees")
            + " · "
            + ("option state (B1/B0)" if contrast == "B1_over_B0" else "mixed block (B2/B1)"),
            20,
        )
        label(
            c,
            40,
            y + 25,
            f"Mean loss reduction: {float(r['percent_reduction_mean']):+.3f}%",
            17,
            s.MUTED,
        )
        line(c, x(float(r["ci_low"])), y, x(float(r["ci_high"])), y, color, 4)
        dot(c, x(float(r["estimate"])), y, color, 7)
    for v in (-0.002, -0.001, 0, 0.001, 0.002, 0.003, 0.004):
        if low <= v <= high:
            label(c, x(v), 461, f"{v:.3f}", 18, anchor="middle")
    label(c, 780, 496, "Baseline loss − expanded-model loss (QLIKE)", 18, anchor="middle")
    label(c, 40, 550, "Right of zero = lower forecast loss. These are not investment returns.", 19)
    label(
        c,
        40,
        582,
        "Intervals are descriptive percentile intervals; "
        "decisions use the declared one-sided sequence.",
        18,
        s.MUTED,
    )
    return c.render().encode()


def assets() -> bytes:
    rows, values, _ = curve_data()  # Existing per-asset and global reconciliation checks.
    means = {(f, a): values[f, a][-1] / len(rows) for f in FAMILIES for a in ASSETS}
    bound = max(abs(v) for v in means.values())
    c = canvas(
        "Does the added block help every stock?",
        "Mean session QLIKE difference: B1 − B2 · same 419 historical dates for each stock",
        610,
    )
    for j, a in enumerate(ASSETS):
        label(c, 267 + j * 158, 148, a, 23, weight="600", anchor="middle")
    for i, f in enumerate(FAMILIES):
        y = 175 + i * 138
        label(c, 40, y + 67, ("Linear", "Trees")[i], 24, weight="600")
        for j, a in enumerate(ASSETS):
            v = means[f, a]
            base = (25, 108, 118) if v >= 0 else (173, 99, 34)
            t = abs(v) / bound * 0.65
            color = "#" + "".join(f"{round(255 * (1 - t) + b * t):02x}" for b in base)
            box(c, 192 + j * 158, y, 150, 110, color)
            label(c, 267 + j * 158, y + 65, f"{v:+.5f}", 25, weight="600", anchor="middle")
    label(
        c,
        40,
        480,
        "Teal / positive: lower loss with B2. Amber / negative: higher loss with B2.",
        20,
    )
    label(
        c,
        40,
        515,
        "Color intensity uses one symmetric scale for all 12 cells; "
        "values are QLIKE, not percentages.",
        18,
        s.MUTED,
    )
    label(
        c,
        40,
        550,
        "Descriptive asset averages, not six independent replications "
        "or evidence of causal attribution.",
        18,
        s.MUTED,
    )
    label(
        c,
        40,
        585,
        "Fixed ticker order; no clustering, fitted groups or significance labels.",
        18,
        s.MUTED,
    )
    return c.render().encode()


def scatter() -> bytes:
    rows = read_csv(LOSSES)
    assert len(rows) == len({r["session_date"] for r in rows}) == 419
    points = {
        f: [(float(r[f"loss__{f}__B1"]), float(r[f"loss__{f}__B2"])) for r in rows]
        for f in FAMILIES
    }
    assert all(math.isfinite(v) and v >= 0 for ps in points.values() for p in ps for v in p)
    upper = math.ceil(max(v for ps in points.values() for p in ps for v in p) * 10) / 10
    c = canvas(
        "What does the average hide?",
        "Every dot pairs B1 and B2 mean forecast losses on one historical session",
        740,
    )
    for i, f in enumerate(FAMILIES):
        left, top, size = 115 + 575 * i, 180, 400
        label(c, left + 200, 144, ("Linear", "Trees")[i], 25, weight="600", anchor="middle")
        for j in range(5):
            v = upper * j / 4
            xx, yy = left + size * j / 4, top + size * (1 - j / 4)
            line(c, xx, top, xx, top + size)
            line(c, left, yy, left + size, yy)
            label(c, xx, top + size + 28, f"{v:.2f}", 17, anchor="middle")
            label(c, left - 12, yy + 6, f"{v:.2f}", 17, anchor="end")
        line(c, left, top + size, left + size, top, s.INK, 2)
        for a, b in points[f]:
            dot(
                c,
                left + a / upper * size,
                top + (1 - b / upper) * size,
                s.LINK if i == 0 else "#a8640a",
                3,
                0.45,
            )
        label(c, left + 200, 642, "B1 session mean loss (QLIKE)", 19, anchor="middle")
        label(c, left, 172, "B2 loss ↑", 18)
    label(
        c,
        40,
        689,
        "Below the diagonal: B2 wins that session. Above it: B1 wins. "
        "Equal scales; no points removed.",
        19,
    )
    label(
        c,
        40,
        722,
        "419 dots per panel. Session averages conceal intraday dispersion; "
        "this is not a calibration test.",
        18,
        s.MUTED,
    )
    return c.render().encode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Verify saved SVG bytes without writing"
    )
    args = parser.parse_args()
    for name, render in (
        ("effect_intervals.svg", comparisons),
        ("asset_heatmap.svg", assets),
        ("paired_session_losses.svg", scatter),
    ):
        data = render()
        if args.check:
            assert (OUT / name).read_bytes() == data, name
        else:
            (OUT / name).write_bytes(data)
        print(name, "verified" if args.check else "rendered")


if __name__ == "__main__":
    main()
