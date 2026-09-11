"""Render schematic reader routes, without opening observations or evaluating models."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from docs.figures.public_refresh.render_readme_figures import box, label, line  # noqa: E402
from scripts import figure_style as s  # noqa: E402

OUT = Path(__file__).resolve().parent
ROUTE_PATHS = (
    "README.md",
    "docs/rp4/specification_v4.md",
    "artifacts/rp4_v4_b4/primary_statistics.csv",
    "docs/figures/public_refresh/render_reader_diagnostics.py",
    "docs/reproduce.md",
    "scripts/verify_public_projection.py",
    "data/DATA_ACCESS.md",
)


def forecast_timeline() -> bytes:
    c = s.Canvas(
        1200,
        650,
        "One forecast, in time order",
        "Schematic, not observed prices. Eligible option source times precede t by at least "
        "120 seconds. At t each model predicts the next 15 minutes of realized variance. "
        "The later observation scores the forecast; it is not an input to that forecast.",
        "forecast-timeline",
    )
    label(c, 40, 55, "One forecast, in time order", 32, weight="600")
    label(
        c,
        40,
        96,
        "A timing schematic — no invented observations; horizontal spacing is not to scale.",
        22,
        s.MUTED,
    )
    cards = (
        (
            40,
            350,
            "1 · Admit past information",
            "Option source time ≤ t − 120 s",
            "Plus quality and eligibility rules",
            s.LINK_TINT,
        ),
        (445, 305, "2 · Forecast at t", "B0 / B1 / B2", "Linear and tree models", s.PAPER_2),
        (
            805,
            355,
            "3 · Observe what follows",
            "Next 15 minutes",
            "Realized variance for scoring",
            s.ACCENT_TINT,
        ),
    )
    for x, w, title, first, second, fill in cards:
        box(c, x, 165, w, 170, fill)
        label(c, x + 20, 208, title, 23, weight="600")
        label(c, x + 20, 258, first, 22)
        label(c, x + 20, 302, second, 20, s.MUTED)
    s.arrow_right(c, 395, 440, 250)
    s.arrow_right(c, 755, 800, 250)
    label(c, 40, 386, "PAST", 22, s.LINK, weight="600")
    label(c, 597, 386, "FORECAST ORIGIN", 22, weight="600", anchor="middle")
    label(c, 1160, 386, "FUTURE TARGET", 22, weight="600", anchor="end")
    line(c, 40, 413, 1160, 413)
    label(
        c,
        40,
        462,
        "Training uses eligible historical targets, never this forecast's future target.",
        24,
    )
    label(
        c,
        40,
        506,
        "Compare forecast with later realized variance using QLIKE: lower loss is better.",
        24,
    )
    label(
        c,
        40,
        565,
        "The 120-second rule uses source timestamps, not measured client receipt.",
        22,
        s.MUTED,
    )
    label(
        c,
        40,
        609,
        "Predicting variance means predicting the size of variation, not price direction.",
        22,
        s.MUTED,
    )
    return c.render().encode("utf-8")


def repository_route() -> bytes:
    assert all((ROOT / path).is_file() for path in ROUTE_PATHS)
    c = s.Canvas(
        1200,
        930,
        "Follow a claim through the repository",
        "Read the question, inspect the method and saved statistics, reproduce the figures, "
        "then verify the public files. Licensed reconstruction is a separate route, not an "
        "outcome established by public checks.",
        "repository-route",
    )
    label(c, 40, 55, "Follow a claim through the repository", 32, weight="600")
    label(
        c, 40, 96, "Question → method → saved evidence → visible figure → verification", 24, s.MUTED
    )
    for i, (title, description) in enumerate(
        zip(
            (
                "1 · Read the question",
                "2 · Inspect the method",
                "3 · Inspect the numbers",
                "4 · Recreate the charts",
            ),
            (
                "Research overview",
                "Frozen methodology",
                "Saved comparison statistics",
                "Figure reproduction",
            ),
            strict=True,
        )
    ):
        y = 135 + 105 * i
        box(c, 40, y, 1120, 80, s.LINK_TINT if i == 2 else s.PAPER_2)
        label(c, 62, y + 48, title, 24, weight="600")
        label(c, 405, y + 48, description, 24)
        if i < 3:
            s.arrow_down(c, 600, y + 81, y + 100)
    s.arrow_down(c, 600, 531, 575)
    line(c, 315, 575, 885, 575)
    s.arrow_down(c, 315, 575, 603)
    s.arrow_down(c, 885, 575, 603)
    for x, title, fill in (
        (40, "5A · Public verification", s.LINK_TINT),
        (630, "5B · Licensed reconstruction", s.ACCENT_TINT),
    ):
        box(c, x, 610, 530, 240, fill)
        label(c, x + 24, 655, title, 26, weight="600")
    label(c, 64, 700, "Public verification guide", 22)
    label(c, 64, 735, "Verification tool", 21)
    label(c, 64, 778, "Output: receipt and logs outside the clone", 21)
    label(c, 64, 820, "Checks public files; does not refit models", 21)
    label(c, 654, 700, "Data access and licensing", 22)
    label(c, 654, 735, "Requires licensed inputs and frozen identities", 21)
    label(c, 654, 778, "Separate reconstruction and authorization", 21)
    label(c, 654, 820, "Not demonstrated by a public check", 21)
    label(
        c,
        40,
        898,
        "Reading and rendering existing evidence does not open a prospective cohort.",
        23,
        s.MUTED,
    )
    return c.render().encode("utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Compare saved SVG bytes without writing"
    )
    args = parser.parse_args()
    for name, render in (
        ("forecast_timeline.svg", forecast_timeline),
        ("repository_route.svg", repository_route),
    ):
        data = render()
        if args.check:
            assert (OUT / name).read_bytes() == data, name
        else:
            (OUT / name).write_bytes(data)
        print(name, "verified" if args.check else "rendered")


if __name__ == "__main__":
    main()
