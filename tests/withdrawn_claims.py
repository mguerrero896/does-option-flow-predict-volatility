"""The claims this project retracted, and how to recognise them anywhere.

`docs/rp2_v3/SUPERSEDED_RESULTS.md` is the human register of withdrawn results. This
module is its machine-checkable half, so a contract can ask "does this file assert
something we retracted?" of prose, of JSON, and of text drawn inside a figure.

Matching is on the claim, not on one spelling of it. The withdrawn decay line has been
written `-0.0277/yr`, `−0.028 per year` and `−0.028 / year`; a literal-string check
caught the second and missed the others, which is how a retracted number reached the
front page inside an SVG on 2026-08-31.

Two kinds of retracted content need different treatment, and conflating them produces
false accusations:

*Narrative claims* are retracted wherever they appear. "Phase 8 is TOST-armed" is wrong
in a gate document, in a figure and in a slide alike.

*Headline figures* are retracted **as headlines**. `+0.013` in a diagnostic table is a
measurement the project made and should keep; the same number presented as the project's
answer is the withdrawn claim. Scope those to surfaces that speak for the project.
"""

from __future__ import annotations

import html
import re
import unicodedata

Claim = tuple[str, str]

# Retracted regardless of where they appear.
WITHDRAWN_NARRATIVE_CLAIMS: tuple[Claim, ...] = (
    ("invalidated -0.0277/year decay line", r"-?0\.02(7\d*|8)\s*(/|per)\s*(year|yr)"),
    ("withdrawn formal-equivalence claim", r"formally\s+equivalent"),
    ("withdrawn mechanism claim", r"the\s+mechanism\s+is\s+real"),
    # The retraction is Phase 8 being TOST-armed, not the existence of TOST. Phase 9 may
    # legitimately specify an equivalence test for a read that has not happened.
    (
        "Phase 8 was never TOST-armed or confirmatory",
        r"(phase\s*8|bridge)[^.]{0,120}tost|tost[^.]{0,120}(phase\s*8|bridge)",
    ),
)

# Retracted as the project's answer. A raw appearance in a data table is evidence.
WITHDRAWN_HEADLINE_FIGURES: tuple[Claim, ...] = (
    ("withdrawn +0.057 headline effect", r"\+\s*0\.057"),
    ("withdrawn +0.013 headline effect", r"\+\s*0\.013"),
    ("withdrawn 3e-46 joint-test p-value", r"3\s*(x|×)\s*10\s*[-−^]*\s*46|2\.99\d*e-?46"),
    ("withdrawn p = 0.0070", r"p\s*=\s*0\.0070"),
)

WITHDRAWN_CLAIMS: tuple[Claim, ...] = WITHDRAWN_NARRATIVE_CLAIMS + WITHDRAWN_HEADLINE_FIGURES

# Wording that marks a document as no longer speaking for the current project state.
SUPERSESSION_MARKERS: tuple[str, ...] = (
    "superseded",
    "withdrawn",
    "historical report",
    "historical measurement",
    "not a current claim",
    "no longer governs",
    "retired",
)

# Wording that, standing next to a retracted claim, shows the text is retracting or
# forbidding it rather than asserting it.
RETRACTION_NEARBY: tuple[str, ...] = (
    "withdraw",
    "supersed",
    "invalidat",
    "retired",
    "not a current",
    "never",
    "forbid",
    "must not",
    "cannot",
    "does not",
    "do not",
    "no longer",
    "historical",
    "was replaced",
    "not tost",
    "rather than",
)

_CONTEXT_WINDOW = 400


def normalize(text: str) -> str:
    """Fold text into one comparable form.

    Figures carry numbers as HTML entities and typographic characters: a minus may be
    U+2212, a hyphen, or `&#8722;`, and words are split across elements. Comparing raw
    strings therefore misses the same claim written differently.
    """
    decoded = unicodedata.normalize("NFKC", html.unescape(text))
    for dash in ("−", "–", "—", "‐", "‑"):
        decoded = decoded.replace(dash, "-")
    return re.sub(r"\s+", " ", decoded).strip().lower()


def claims_mentioned_in(text: str, claims: tuple[Claim, ...] = WITHDRAWN_CLAIMS) -> list[str]:
    """Names of withdrawn claims whose pattern appears anywhere in ``text``."""
    folded = normalize(text)
    return [claim for claim, pattern in claims if re.search(pattern, folded)]


def claims_asserted_in(text: str, claims: tuple[Claim, ...] = WITHDRAWN_CLAIMS) -> list[str]:
    """Withdrawn claims that ``text`` states without retracting them nearby.

    A document may name a retracted claim in order to retract it — the protocol that
    forbids calling a result "formally equivalent" has to write the phrase down, and the
    thesis has to say the implementation "does not perform TOST". Only a mention with no
    retraction in its immediate neighbourhood counts as an assertion.
    """
    folded = normalize(text)
    asserted = []
    for claim, pattern in claims:
        for match in re.finditer(pattern, folded):
            window = folded[max(0, match.start() - _CONTEXT_WINDOW) : match.end() + _CONTEXT_WINDOW]
            if not any(marker in window for marker in RETRACTION_NEARBY):
                asserted.append(claim)
                break
    return asserted


def carries_supersession_notice(markdown: str, *, within_lines: int = 25) -> bool:
    """True when the document opens with a notice that it is no longer authoritative.

    The notice has to be near the top: a reader who stops after the first screen must
    not carry away a retracted number as current.
    """
    head = normalize("\n".join(markdown.splitlines()[:within_lines]))
    return any(marker in head for marker in SUPERSESSION_MARKERS)
