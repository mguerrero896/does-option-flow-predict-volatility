"""The published defense package must be what its producer actually generates.

`test_canonical_defense_package` proves the builder is deterministic, but it builds
into a temporary directory and never looks at the copy committed under
`reports/canonical_validation_v1/`. Those two drifted: the committed SVG figures had
picked up CRLF line endings from a checkout before `.gitattributes` covered `*.svg`,
so the published bytes stopped matching the bytes the producer emits, and nothing
noticed. A reader regenerating the package to verify it would have got a diff and no
explanation.

This contract compares the published package to a fresh build, byte for byte. It is
the check that turns "the builder is reproducible" into "what we published is what
the builder produces".
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SOURCE = REPO / "artifacts" / "canonical_validation_v1"
PUBLISHED = REPO / "reports" / "canonical_validation_v1"

sys.path.insert(0, str(REPO / "scripts"))

import build_canonical_defense_package as defense  # noqa: E402


def _build_fresh() -> Path:
    output = Path(tempfile.mkdtemp()) / "package"
    defense.build_defense_package(SOURCE, output)
    return output


def test_published_defense_package_is_byte_identical_to_a_fresh_build() -> None:
    fresh = _build_fresh()

    mismatches = []
    for generated in sorted(path for path in fresh.rglob("*") if path.is_file()):
        relative = generated.relative_to(fresh)
        published = PUBLISHED / relative
        if not published.is_file():
            mismatches.append(f"{relative.as_posix()}: produced by the builder but not published")
            continue
        produced_bytes = generated.read_bytes()
        published_bytes = published.read_bytes()
        if produced_bytes == published_bytes:
            continue
        detail = f"{len(published_bytes)}B published vs {len(produced_bytes)}B produced"
        if produced_bytes.replace(b"\r\n", b"\n") == published_bytes.replace(b"\r\n", b"\n"):
            detail += " — line endings only; check .gitattributes covers this extension"
        mismatches.append(f"{relative.as_posix()}: {detail}")

    assert not mismatches, (
        "the published defense package does not match its producer.\n"
        "Regenerate with `uv run python scripts/build_canonical_defense_package.py`:\n"
        + "\n".join(mismatches)
    )


def test_published_package_carries_no_file_the_producer_does_not_emit() -> None:
    """A stray file in the package would be published as evidence nothing produced."""

    fresh = _build_fresh()
    produced = {path.relative_to(fresh).as_posix() for path in fresh.rglob("*") if path.is_file()}
    # The pytest log is committed alongside the package as provenance, not generated.
    allowed_extras = {"test_report.txt"}

    published = {
        path.relative_to(PUBLISHED).as_posix() for path in PUBLISHED.rglob("*") if path.is_file()
    }
    stray = sorted(published - produced - allowed_extras)

    assert not stray, "published but not produced by the builder: " + ", ".join(stray)


def test_package_text_files_are_committed_with_lf_endings() -> None:
    """CRLF is how the published copy drifted from the producer in the first place."""

    text_suffixes = {".md", ".html", ".svg", ".csv", ".json", ".txt"}
    crlf = [
        path.relative_to(REPO).as_posix()
        for path in PUBLISHED.rglob("*")
        if path.is_file() and path.suffix.lower() in text_suffixes and b"\r\n" in path.read_bytes()
    ]
    assert not crlf, (
        "package files committed with CRLF; confirm .gitattributes marks these "
        "extensions `text eol=lf`:\n" + "\n".join(crlf)
    )
