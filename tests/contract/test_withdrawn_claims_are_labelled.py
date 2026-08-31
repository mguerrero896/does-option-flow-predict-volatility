"""A document may keep a retracted claim. It may not present one as current.

This repository deliberately retains superseded protocols and measurements, because
their hashes and citations are what let a reviewer audit the replacement against the
thing it replaced. The register of what was retracted is
`docs/rp2_v3/SUPERSEDED_RESULTS.md`.

The failure mode is not retention, it is silence. A consistency audit on 2026-08-31
found documents asserting retracted content with no notice at the top: gates describing
Phase 8 as `TOST-armed`, a validation report calling the withdrawn `3 x 10^-46` joint
test a finding that "survived the control", and an inference document whose every
estimate is superseded twice over. A reader arriving from a search result or an index
link had nothing to warn them.

This contract requires the notice, not the deletion. It sweeps the narrative claims,
which are wrong wherever they appear; the bare effect sizes stay with
`test_readme_matches_artifacts`, where "headline" is the right frame and a diagnostic
table is not accused of asserting the number it recorded.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
from tests.withdrawn_claims import (
    WITHDRAWN_NARRATIVE_CLAIMS,
    carries_supersession_notice,
    claims_asserted_in,
)

REPO = Path(__file__).resolve().parents[2]

SEARCHED_TREES = ("docs", "reports", "specs")

# Documents whose subject IS the retraction. They must name the withdrawn claims to do
# their job, and labelling them superseded would be false.
REGISTERS = {
    "docs/rp2_v3/SUPERSEDED_RESULTS.md",
    "docs/methodology_decisions.md",
    "docs/canonical_claims_and_limitations.md",
}


def _tracked_markdown() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", *SEARCHED_TREES],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    return sorted({line for line in result.stdout.splitlines() if line.endswith(".md")})


def test_documents_asserting_withdrawn_claims_carry_a_supersession_notice() -> None:
    unlabelled = []
    for relative in _tracked_markdown():
        if relative in REGISTERS:
            continue
        path = REPO / relative
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8")
        asserted = claims_asserted_in(text, WITHDRAWN_NARRATIVE_CLAIMS)
        if not asserted or carries_supersession_notice(text):
            continue
        unlabelled.append(f"{relative}: {', '.join(asserted)}")

    assert not unlabelled, (
        "documents assert retracted claims with no notice near the top.\n"
        "Keep the content and add a supersession banner naming the current authority "
        "(see docs/canonical_claims_and_limitations.md for the house pattern):\n"
        + "\n".join(unlabelled)
    )


def test_the_sweep_actually_reaches_the_documents_it_claims_to_cover() -> None:
    """A `git ls-files` glob that quietly matches nothing would pass forever."""
    covered = _tracked_markdown()
    assert len(covered) > 100, f"only {len(covered)} documents swept; the glob is wrong"
    for expected in ("README.md", "docs/INDEX.md", "reports/final_report_draft_v2.md"):
        assert any(path.endswith(expected) for path in covered), f"{expected} not swept"


@pytest.mark.parametrize("claim,_pattern", WITHDRAWN_NARRATIVE_CLAIMS)
def test_each_pattern_matches_a_real_spelling_of_its_claim(claim: str, _pattern: str) -> None:
    """A pattern that silently stopped matching would pass forever, protecting nothing."""
    spellings = {
        "invalidated -0.0277/year decay line": "a decay of -0.028 / year",
        "withdrawn formal-equivalence claim": "the families are formally equivalent",
        "withdrawn temporal-decay reading": "the decay pattern remains time-linked",
        "withdrawn mechanism claim": "The mechanism is real",
        "Phase 8 was never TOST-armed or confirmatory": "Phase 8 is TOST-armed and sealed",
    }
    assert claim in claims_asserted_in(spellings[claim], WITHDRAWN_NARRATIVE_CLAIMS)


def test_a_retraction_beside_the_claim_is_not_an_assertion() -> None:
    """The protocol forbidding a phrase has to write the phrase down."""
    forbidding = "Calling the result formally equivalent or preregistered is forbidden."
    denying = "The implementation does not perform TOST for Phase 8 or establish equivalence."
    assert not claims_asserted_in(forbidding, WITHDRAWN_NARRATIVE_CLAIMS)
    assert not claims_asserted_in(denying, WITHDRAWN_NARRATIVE_CLAIMS)


def test_tost_is_only_retracted_when_it_arms_phase_8() -> None:
    """Phase 9 may specify an equivalence test for a read that has not happened."""
    phase9 = "Phase 9 declares equivalence in both families (TOST at delta = 0.005)."
    phase8 = "Phase 8 is positioned as a TOST-armed confirmatory read."
    assert not claims_asserted_in(phase9, WITHDRAWN_NARRATIVE_CLAIMS)
    assert claims_asserted_in(phase8, WITHDRAWN_NARRATIVE_CLAIMS)


def test_supersession_notice_is_not_satisfied_by_a_mention_far_below() -> None:
    """The notice must be readable before the claim, not buried at the bottom."""
    buried = "# A report\n\n" + "\n".join(f"line {n}" for n in range(80)) + "\nsuperseded\n"
    assert not carries_supersession_notice(buried)
    assert carries_supersession_notice("# A report\n\n> **SUPERSEDED.** Use the canonical state.")
