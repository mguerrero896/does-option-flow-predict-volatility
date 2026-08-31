"""Figures shown to readers must not assert claims this project withdrew.

`test_readme_matches_artifacts` forbids the withdrawn headline figures, but it greps
README prose only. On 2026-08-31 a timeline figure was added to the front page that
rendered "-0.028 / year" and "TOST-armed" inside the SVG, reinstating two claims that
`docs/rp2_v3/SUPERSEDED_RESULTS.md` records as invalidated. Text checks could not see
it, because the assertion was drawn rather than written.

This contract closes that route. It reads the text out of every figure a public
document actually shows a reader and matches on the *claim*, not on one spelling of
it, so a reformatted number ("-0.028 / year" versus "-0.028 per year") cannot slip
through.

Frozen evidence under `artifacts/` is out of scope: those files legitimately preserve
the historical measurements they were registered with.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from tests.withdrawn_claims import WITHDRAWN_CLAIMS, normalize

REPO = Path(__file__).resolve().parents[2]

# Documents whose figures a reader meets as the project's current position.
PUBLIC_SURFACES = ("README.md", "STATUS.md", "docs/README.md", "reports/README.md")

MARKDOWN_IMAGE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)")
SVG_TEXT = re.compile(r">([^<>]{2,200})<")

# Reviewed 2026-08-31 against data/CANONICAL_STATE.json: the diagram states structure and
# custody rules only. It carries no effect size, p-value, date or eligibility claim.
REVIEWED_RASTERS: frozenset[str] = frozenset({"docs/figures/system-architecture.png"})


def _tracked(pattern: str) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", pattern],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def _figures_shown_by(document: str) -> list[str]:
    path = REPO / document
    if not path.is_file():
        return []
    base = (REPO / document).parent
    shown = []
    for target in MARKDOWN_IMAGE.findall(path.read_text(encoding="utf-8")):
        if target.startswith(("http://", "https://", "data:")):
            continue
        # GitHub badges are written as repository-relative URLs that climb above the
        # root (`../../actions/...`). They address the hosting site, not a file here.
        resolved = (base / target).resolve()
        try:
            shown.append(resolved.relative_to(REPO).as_posix())
        except ValueError:
            continue
    return shown


def _published_figures() -> list[tuple[str, str]]:
    """(surface, figure) pairs, excluding frozen evidence under artifacts/."""
    pairs = []
    for surface in PUBLIC_SURFACES:
        for figure in _figures_shown_by(surface):
            if figure.startswith("artifacts/"):
                continue
            pairs.append((surface, figure))
    return pairs


def test_published_svg_figures_assert_no_withdrawn_claim() -> None:
    violations = []
    for surface, figure in _published_figures():
        path = REPO / figure
        if path.suffix.lower() != ".svg" or not path.is_file():
            continue
        drawn = normalize(" ".join(SVG_TEXT.findall(path.read_text(encoding="utf-8"))))
        for claim, pattern in WITHDRAWN_CLAIMS:
            found = re.search(pattern, drawn)
            if found:
                violations.append(
                    f"{surface} shows {figure}, which draws {found.group(0)!r} — {claim}"
                )
    assert not violations, "withdrawn claims reinstated through a figure:\n" + "\n".join(violations)


def test_no_illustration_asserts_a_withdrawn_claim_even_when_unreferenced() -> None:
    """An unreferenced figure is still browsable, and still gets lifted into slides.

    Two figures sat in `docs/figures/` referenced by nothing, drawing the withdrawn
    decay line and per-campaign effect sizes. Nothing surfaced them, because no index
    or review pass walks a file no document mentions.
    """
    violations = []
    for figure in _tracked("docs/**/*.svg"):
        path = REPO / figure
        if not path.is_file():
            continue
        drawn = normalize(" ".join(SVG_TEXT.findall(path.read_text(encoding="utf-8"))))
        for claim, pattern in WITHDRAWN_CLAIMS:
            found = re.search(pattern, drawn)
            if found:
                violations.append(f"{figure} draws {found.group(0)!r} — {claim}")
    assert not violations, (
        "illustrations under docs/ assert withdrawn claims. Being referenced by no "
        "document is not a defence — the directory is browsable:\n" + "\n".join(violations)
    )


def test_public_surfaces_show_no_unreviewed_raster_figure() -> None:
    """A raster cannot be read by this contract, so it needs a recorded human check."""
    unreviewed = [
        f"{surface} shows {figure}"
        for surface, figure in _published_figures()
        if Path(figure).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".gif"}
        and figure not in REVIEWED_RASTERS
    ]
    assert not unreviewed, (
        "raster figures on a public surface cannot be checked for withdrawn claims.\n"
        "Verify the content against data/CANONICAL_STATE.json, then add the path to "
        "REVIEWED_RASTERS in this module:\n" + "\n".join(unreviewed)
    )


def test_every_public_surface_figure_reference_resolves() -> None:
    missing = [
        f"{surface} references {figure}, which does not exist"
        for surface, figure in _published_figures()
        if not (REPO / figure).is_file()
    ]
    assert not missing, "\n".join(missing)
