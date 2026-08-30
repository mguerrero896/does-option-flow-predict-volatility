"""A cited document must exist, or the citation must say why it does not.

This repository was recreated twice to purge licensed data and internal tooling from
its history. Documents removed in those purges kept being cited by documents that
stayed, so a reader following a reference for the pre-statement of a decision rule, or
for the master dossier a decision names as the project index, arrived at nothing. The
pre-registration claim then cannot be checked, which is the one thing citations are for.

Deleting the citation would be worse: it hides that the record ever existed. The rule is
that an unresolvable reference must carry its explanation inline.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

SEARCHED_TREES = ("docs", "reports", "specs")

# Documents only. Paths under `artifacts/` and `data/` are frequently gated by design —
# their absence from the public tree is the access model working, recorded in
# `data/GATED_DATA_POINTERS.json`, not a broken citation.
CITED_PATH = re.compile(r"`((?:docs|reports|specs)/[^`\s]+\.(?:md|docx|xlsx))`")

# Template and shell-expansion notation stands for a family of paths, not one file.
PLACEHOLDER = re.compile(r"[*?\[\]<>{}]")

# The register's job is to name what was removed. Requiring those paths to resolve would
# require un-removing them.
REGISTERS = {"docs/rp2_v3/SUPERSEDED_RESULTS.md"}

# A document whose bytes are hashed into a frozen contract cannot receive an inline note:
# adding one changes the hash and breaks the seal it was written under. The exemption is
# checked against the artifacts below, so it cannot be claimed for a file that is merely
# inconvenient to edit.
SEALED_INPUTS = {"docs/DISCOVERY_VALIDATION_CONFIRMATION_PROTOCOL.md"}

EXPLANATIONS = (
    "not part of the public release",
    "removed from the public release",
    "not in this release",
    "absent from",
    "does not exist",
)

_EXPLANATION_WINDOW = 260


def _tracked_markdown() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", *SEARCHED_TREES],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    )
    return sorted({line for line in result.stdout.splitlines() if line.endswith(".md")})


def test_every_cited_document_resolves_or_explains_its_absence() -> None:
    unexplained = []
    for relative in _tracked_markdown():
        if relative in REGISTERS or relative in SEALED_INPUTS:
            continue
        text = (REPO / relative).read_text(encoding="utf-8")
        for match in CITED_PATH.finditer(text):
            cited = match.group(1)
            if PLACEHOLDER.search(cited):
                continue
            if (REPO / cited).exists():
                continue
            window = text[match.end() : match.end() + _EXPLANATION_WINDOW].lower()
            if any(phrase in window for phrase in EXPLANATIONS):
                continue
            unexplained.append(f"{relative} cites {cited}, which does not exist")

    assert not unexplained, (
        "citations point at documents that are not in this release, with no note "
        "saying so. Add the inline explanation rather than deleting the citation:\n"
        + "\n".join(unexplained)
    )


def test_the_sweep_reaches_the_documents_it_claims_to_cover() -> None:
    """A glob that quietly matches nothing would pass forever."""
    covered = _tracked_markdown()
    assert len(covered) > 100, f"only {len(covered)} documents swept; the glob is wrong"
    assert "docs/methodology_decisions.md" in covered


def test_a_resolvable_citation_needs_no_explanation() -> None:
    assert (REPO / "docs/INDEX.md").is_file()
    text = "See `docs/INDEX.md` for the map."
    matches = [m.group(1) for m in CITED_PATH.finditer(text)]
    assert matches == ["docs/INDEX.md"]
    assert all((REPO / cited).exists() for cited in matches)


def test_every_sealed_exemption_is_actually_hashed_into_a_contract() -> None:
    """The exemption is for documents whose bytes are sealed, not for awkward ones."""
    sealed_elsewhere = set()
    for artifact in REPO.glob("artifacts/**/*.json"):
        try:
            content = artifact.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for candidate in SEALED_INPUTS:
            # The path appears as a key in the contract's input_sha256 map.
            if f'"{candidate}"' in content and "sha256" in content:
                sealed_elsewhere.add(candidate)

    unjustified = SEALED_INPUTS - sealed_elsewhere
    assert not unjustified, (
        "these paths claim a frozen-contract exemption but no artifact hashes them; "
        "annotate the citation instead: " + ", ".join(sorted(unjustified))
    )
