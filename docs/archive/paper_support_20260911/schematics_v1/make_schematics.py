"""Schematic figures 1-4 for the MDS650 capstone report.

Visual language copied from the existing data charts (results_*.png):
card background, navy question-style title, grey subtitle, blue/orange
series colours, thin rules, grey source line. All text in English.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from pathlib import Path

OUT = Path(__file__).parent / "figs"
OUT.mkdir(exist_ok=True)

CARD   = "#EEF3F8"
PANEL  = "#FFFFFF"
NAVY   = "#123A5E"
BLUE   = "#1F6FB2"
ORANGE = "#C8551F"
GREEN  = "#2E7D32"
GREY   = "#5A6B7A"
RULE   = "#D5DEE7"
FAINT  = "#8592A0"

plt.rcParams.update({
    "font.family": "Segoe UI",
    "font.size": 9,
    "text.color": NAVY,
})


def card(w=12.0, h=5.4):
    fig = plt.figure(figsize=(w, h), dpi=200)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 100); ax.set_ylim(0, 100)
    ax.axis("off")
    ax.add_patch(FancyBboxPatch((0.6, 0.6), 98.8, 98.8,
                 boxstyle="round,pad=0,rounding_size=1.2",
                 fc=CARD, ec="none", zorder=0))
    return fig, ax


def header(ax, title, subtitle, note=None):
    ax.text(4, 92.5, title, fontsize=15.5, fontweight="bold", color=NAVY, va="center")
    ax.text(4, 86.5, subtitle, fontsize=9.5, color=GREY, va="center")
    y = 82.0
    ax.plot([4, 96], [y, y], color=RULE, lw=0.9, zorder=1)
    if note:
        ax.text(4, 78.5, note, fontsize=8.8, color=GREY, va="center")
    return y


def source(ax, text):
    ax.plot([4, 96], [8.5, 8.5], color=RULE, lw=0.9, zorder=1)
    ax.text(4, 5.2, text, fontsize=7.6, color=FAINT, va="center")


def box(ax, x, y, w, h, fc=PANEL, ec=RULE, lw=1.0, r=1.0, z=2):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
                 boxstyle=f"round,pad=0,rounding_size={r}",
                 fc=fc, ec=ec, lw=lw, zorder=z))


def arrow(ax, x1, y1, x2, y2, color=BLUE, lw=1.6):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2),
                 arrowstyle="-|>", mutation_scale=13,
                 color=color, lw=lw, shrinkA=0, shrinkB=0, zorder=4))


def text_width(fig, ax, s, fontsize):
    """Measured width of `s` in axis data units, so boxes never overflow."""
    t = ax.text(0, 0, s, fontsize=fontsize)
    fig.canvas.draw()
    bb = t.get_window_extent(renderer=fig.canvas.get_renderer())
    inv = ax.transData.inverted()
    x0 = inv.transform((bb.x0, bb.y0))[0]
    x1 = inv.transform((bb.x1, bb.y1))[0]
    t.remove()
    return x1 - x0


def chip_row(fig, ax, chips, x_start, x_end, y, h=4.6, pad=2.6, gap=1.6, fs=8.0):
    """Lay chips left to right, shrinking the font until the row fits."""
    while fs > 5.5:
        widths = [text_width(fig, ax, c, fs) + pad for c in chips]
        total = sum(widths) + gap * 2 * (len(chips) - 1)
        if total <= (x_end - x_start):
            break
        fs -= 0.25
    x = x_start
    for j, (c, w) in enumerate(zip(chips, widths)):
        ax.add_patch(FancyBboxPatch((x, y), w, h,
                     boxstyle="round,pad=0,rounding_size=0.8",
                     fc="#F4F7FA", ec=RULE, lw=0.8, zorder=3))
        ax.text(x + w / 2, y + h / 2, c, fontsize=fs, color=NAVY,
                ha="center", va="center", zorder=4)
        x += w
        if j < len(chips) - 1:
            ax.text(x + gap, y + h / 2, "→", fontsize=fs + 1, color=FAINT,
                    ha="center", va="center", zorder=4)
            x += gap * 2


# ---------------------------------------------------------------- Figure 1
def fig_report_progression():
    fig, ax = card(12.0, 4.6)
    header(ax, "How the report is organised",
           "Each chapter answers one question and hands a specific result to the next.")
    stages = [
        ("1", "Introduction", "Problem, research\nquestions, contribution", BLUE),
        ("2", "Literature", "Evidence, documented\nlimits, bounded gap", BLUE),
        ("3", "Methodology", "Development history,\ntiming, inference", BLUE),
        ("4", "Results", "Measured outcomes\nand uncertainty", ORANGE),
        ("5-6", "Discussion\nand conclusion", "Interpretation, limits,\nnext evidence", ORANGE),
    ]
    x0, w, gap = 4.0, 16.6, 2.8
    for i, (num, name, role, col) in enumerate(stages):
        x = x0 + i * (w + gap)
        box(ax, x, 30, w, 38)
        ax.add_patch(FancyBboxPatch((x, 63.2), w, 4.8,
                     boxstyle="round,pad=0,rounding_size=1.0",
                     fc=col, ec="none", zorder=3))
        ax.text(x + w / 2, 65.6, f"Chapter {num}", fontsize=8.6,
                color="white", fontweight="bold", ha="center", va="center", zorder=4)
        ax.text(x + w / 2, 55.5, name, fontsize=11.2, fontweight="bold",
                color=NAVY, ha="center", va="center", zorder=4)
        ax.text(x + w / 2, 41.5, role, fontsize=8.8, color=GREY,
                ha="center", va="center", linespacing=1.5, zorder=4)
        if i < len(stages) - 1:
            arrow(ax, x + w + 0.5, 49, x + w + gap - 0.5, 49, color="#9FB3C6", lw=1.4)
    ax.text(4, 22, "The chain is one-directional: a failed step is reported, not repaired by a later one.",
            fontsize=9, color=NAVY, va="center")
    source(ax, "Original schematic. Chapter roles follow the institute's capstone structure.")
    fig.savefig(OUT / "fig_report_progression.png", facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------- Figure 2
def fig_information_sets():
    fig, ax = card(12.0, 5.6)
    header(ax, "What does each information set add?",
           "Nested by construction: every larger set keeps the smaller set and adds predictors.")

    # genuinely nested rectangles
    specs = [
        (6, 14, 88, 56, "#E4EEF7", "#1F6FB2"),   # B2 outer
        (13, 19, 62, 46, "#D2E3F2", "#1F6FB2"),  # B1
        (20, 24, 36, 36, "#BBD5EC", "#123A5E"),  # B0 inner
    ]
    for x, y, w, h, fc, ec in specs:
        box(ax, x, y, w, h, fc=fc, ec=ec, lw=1.3, r=1.4, z=2)

    ax.text(24, 55, "B0", fontsize=13, fontweight="bold", color=NAVY, va="center")
    ax.text(24, 50, "29 predictors", fontsize=9.2, color=NAVY, va="center")
    ax.text(24, 45.0, "Price and volatility history:\nmultiscale realised variance,\nHARQ terms, semivariances,\nvolume, market controls,\nintraday calendar",
            fontsize=8.3, color=GREY, va="top", linespacing=1.55)

    ax.text(59, 60, "B1", fontsize=13, fontweight="bold", color=NAVY, va="center")
    ax.text(59, 55.4, "69 predictors   (+40)", fontsize=9.2, color=NAVY, va="center")
    ax.text(59, 50.5, "Adds option state:\nimplied-volatility surface\n(25 cells) and summaries",
            fontsize=8.3, color=GREY, va="top", linespacing=1.55)

    ax.text(78, 64, "B2", fontsize=13, fontweight="bold", color=NAVY, va="center")
    ax.text(78, 59.4, "138 predictors   (+69)", fontsize=9.2, color=NAVY, va="center")
    ax.text(78, 54.5, "Adds option activity:\nflow composition, premium,\nexposure proxies, signed\ngamma imbalance, empty-\nwindow indicators",
            fontsize=8.3, color=GREY, va="top", linespacing=1.55)

    # hypothesis bar
    ax.plot([20, 20], [12.5, 22], color=NAVY, lw=1.0, ls=(0, (3, 3)))
    ax.plot([56, 56], [12.5, 22], color=NAVY, lw=1.0, ls=(0, (3, 3)))
    ax.plot([94, 94], [12.5, 22], color=NAVY, lw=1.0, ls=(0, (3, 3)))
    arrow(ax, 21, 12.5, 55, 12.5, color=BLUE, lw=1.8)
    arrow(ax, 57, 12.5, 93, 12.5, color=ORANGE, lw=1.8)
    ax.text(38, 15.3, "H1:  does option state beat price history?",
            fontsize=9.0, color=BLUE, ha="center", va="center", fontweight="bold")
    ax.text(75, 15.3, "H2:  does activity add more, after state?",
            fontsize=9.0, color=ORANGE, ha="center", va="center", fontweight="bold")
    ax.text(4, 73.5, "H2 is tested only if H1 rejects. Both hypotheses are evaluated separately in each model family.",
            fontsize=9.0, color=NAVY, va="center")
    source(ax, "Counts exclude asset fixed effects and generated presence columns. "
               "Source: artifacts/rp4_v4_a1/specification.json.")
    fig.savefig(OUT / "fig_information_sets.png", facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------- Figure 3
def fig_programme_progression():
    fig, ax = card(12.0, 6.2)
    header(ax, "How the evidence was produced, stage by stage",
           "Ordered by scientific role, not by timestamp. Colour marks what each stage can support.")

    lanes = [
        (58, BLUE, "Historical development", "Reuses observed market history",
         ["Proposal: RV30 question", "v1: initial design", "v2: corrections",
          "v3: mechanism, empty windows", "v4: RV15 primary, RV5 secondary"]),
        (37, ORANGE, "Registered extensions", "Re-examines the same history",
         ["v5: five model families", "Universe: eight forecast targets"]),
        (16, GREEN, "Prospective programme", "Results pending, rules fixed in advance",
         ["20 sessions: early consistency", "40: stability", "45: pooled secondary",
          "335: final reading"]),
    ]
    for y, col, name, role, chips in lanes:
        box(ax, 4, y, 92, 17.5, fc=PANEL, r=1.2)
        ax.add_patch(FancyBboxPatch((4, y), 1.5, 17.5,
                     boxstyle="round,pad=0,rounding_size=0.6", fc=col, ec="none", zorder=3))
        ax.text(7.5, y + 13.0, name, fontsize=11.0, fontweight="bold", color=NAVY, va="center")
        ax.text(7.5, y + 8.9, role, fontsize=8.6, color=GREY, va="center")
        chip_row(fig, ax, chips, 7.5, 93.0, y + 2.2)

    arrow(ax, 50, 57.0, 50, 55.2, color="#9FB3C6", lw=1.4)
    arrow(ax, 50, 36.0, 50, 34.2, color="#9FB3C6", lw=1.4)
    ax.text(4, 77.0, "Earlier results were known when later historical stages were designed, so these are "
                     "not independent replications.", fontsize=9.0, color=NAVY, va="center")
    source(ax, "Prospective reading roles are protocol commitments, not observed outcomes. "
               "Source: docs/rp4/prospective_confirmation_v1 and amendments 1-3.")
    fig.savefig(OUT / "fig_programme_progression.png", facecolor="white")
    plt.close(fig)


# ---------------------------------------------------------------- Figure 4
def fig_research_workflow():
    fig, ax = card(12.0, 6.0)
    header(ax, "From licensed records to a registered decision",
           "Three controls stay separate: what a predictor may see, how forecasts are scored, and what is kept.")

    steps = [
        ("Licensed inputs", "Equity bars and option records,\nwith source timestamps, market\ncalendar and input hashes",
         "Availability", BLUE),
        ("Point-in-time construction", "Predictors limited to records\nadmitted at the origin; outcomes\ncomputed on a separate path",
         "Availability", BLUE),
        ("Nested information sets", "B0 inside B1 inside B2, scored\non common keys; past-only\ntransformations and selection",
         "Evaluation", ORANGE),
        ("Walk-forward forecasts", "Fit on earlier sessions, predict\nthe next; paired session losses\nand block-bootstrap intervals",
         "Evaluation", ORANGE),
        ("Registered decision", "Fixed state-then-flow sequence,\ndiagnostics, correction ledger\nand archived evidence",
         "Record-keeping", GREEN),
    ]
    x0, w, gap = 4.0, 16.6, 2.8
    for i, (name, detail, control, col) in enumerate(steps):
        x = x0 + i * (w + gap)
        box(ax, x, 22, w, 48)
        ax.add_patch(FancyBboxPatch((x, 65.2), w, 4.8,
                     boxstyle="round,pad=0,rounding_size=1.0", fc=col, ec="none", zorder=3))
        ax.text(x + w / 2, 67.6, control, fontsize=8.2, color="white",
                fontweight="bold", ha="center", va="center", zorder=4)
        ax.text(x + w / 2, 58.5, name, fontsize=10.0, fontweight="bold", color=NAVY,
                ha="center", va="center", zorder=4, linespacing=1.3)
        ax.text(x + w / 2, 39.0, detail, fontsize=8.2, color=GREY,
                ha="center", va="center", linespacing=1.6, zorder=4)
        ax.text(x + w / 2, 25.5, f"Step {i + 1}", fontsize=8.0, color=FAINT,
                ha="center", va="center", zorder=4)
        if i < len(steps) - 1:
            arrow(ax, x + w + 0.5, 46, x + w + gap - 0.5, 46, color="#9FB3C6", lw=1.4)

    ax.text(4, 15.5, "A failed origin stays visible in the eligibility census rather than being dropped, so an "
                     "exclusion under a quality rule\nis never confused with a removal that followed a poor forecast.",
            fontsize=9.0, color=NAVY, va="center", linespacing=1.6)
    source(ax, "Arrows show the order in which records become predictors, forecasts and evaluation results. "
               "Source: docs/rp4/specification_v4.md.")
    fig.savefig(OUT / "fig_research_workflow.png", facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    fig_report_progression()
    fig_information_sets()
    fig_programme_progression()
    fig_research_workflow()
    for p in sorted(OUT.glob("*.png")):
        print(f"{p.name:38s} {p.stat().st_size/1024:7.1f} KB")
