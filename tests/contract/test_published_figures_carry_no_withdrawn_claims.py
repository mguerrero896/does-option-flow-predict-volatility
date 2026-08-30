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

import html
import re
import subprocess
import unicodedata
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]

# Documents whose figures a reader meets as the project's current position.
PUBLIC_SURFACES = ("README.md", "STATUS.md", "docs/README.md", "reports/README.md")

MARKDOWN_IMAGE = re.compile(r"!\[[^\]]*\]\(([^)\s]+)")
SVG_TEXT = re.compile(r">([^<>]{2,200})<")

# Each entry pairs a withdrawn claim with a pattern tolerant of formatting. The
# reasons are recorded in docs/rp2_v3/SUPERSEDED_RESULTS.md.
WITHDRAWN_CLAIMS: tuple[tuple[str, str], ...] = (
    ("invalidated -0.0277/year decay line", r"-?0\.02(7\d*|8)\s*(/|per)\s*(year|yr)"),
    ("withdrawn +0.057 headline effect", r"\+\s*0\.057"),
    ("withdrawn +0.013 headline effect", r"\+\s*0\.013"),
    ("withdrawn 3e-46 p-value", r"3\s*(x|×)\s*10\s*[-−^]*\s*46"),
    ("withdrawn p = 0.0070", r"p\s*=\s*0\.0070"),
    ("withdrawn formal-equivalence claim", r"formally\s+equivalent"),
    ("Phase 8 was never TOST-armed or confirmatory", r"tost"),
    ("withdrawn mechanism claim", r"the\s+mechanism\s+is\s+real"),
)

# Raster figures cannot be machine-read. Any raster shown on a public surface must be
# listed here, which forces a human to confirm its content against the canonical state.
REVIEWED_RASTERS: frozenset[str] = frozenset()


def _tracked(pattern: str) -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", pattern],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line.strip()]


def _normalize(text: str) -> str:
    """Fold a figure's drawn text into one comparable form.

    SVG carries numbers as HTML entities and typographic characters: a minus may be
    U+2212, a hyphen, or `&#8722;`, and words are split across `<tspan>` elements.
    Comparing raw strings therefore misses the same claim written differently.
    """
    decoded = html.unescape(text)
    decoded = unicodedata.normalize("NFKC", decoded)
    for dash in ("−", "–", "—", "‐", "‑"):
        decoded = decoded.replace(dash, "-")
    return re.sub(r"\s+", " ", decoded).strip().lower()


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
        drawn = _normalize(" ".join(SVG_TEXT.findall(path.read_text(encoding="utf-8"))))
        for claim, pattern in WITHDRAWN_CLAIMS:
            found = re.search(pattern, drawn)
            if found:
                violations.append(
                    f"{surface} shows {figure}, which draws {found.group(0)!r} — {claim}"
                )
    assert not violations, "withdrawn claims reinstated through a figure:\n" + "\n".join(violations)


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


@pytest.mark.parametrize("claim,pattern", WITHDRAWN_CLAIMS)
def test_withdrawn_patterns_match_their_own_claim(claim: str, pattern: str) -> None:
    """A guard whose pattern never matches would pass silently forever."""
    samples = {
        "invalidated -0.0277/year decay line": "decay -0.028 / year",
        "withdrawn +0.057 headline effect": "delta +0.057",
        "withdrawn +0.013 headline effect": "delta +0.013",
        "withdrawn 3e-46 p-value": "p = 3 x 10-46",
        "withdrawn p = 0.0070": "p = 0.0070",
        "withdrawn formal-equivalence claim": "formally equivalent",
        "Phase 8 was never TOST-armed or confirmatory": "tost-armed - sealed",
        "withdrawn mechanism claim": "the mechanism is real",
    }
    assert re.search(pattern, _normalize(samples[claim])), f"pattern for {claim!r} is dead"
