"""Standing tripwire for the public research surface and its reachable history."""

from __future__ import annotations

import fnmatch
import os
import re
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
EXCLUDE_LIST = REPO / "scripts" / "_mirror_internal_exclude_list.txt"
# The published tip AND the candidate: checking only origin/main lets a PR add an
# internal document that passes CI (the file is not on origin/main *yet*) and leaks
# at merge. HEAD closes that window — the contract fails on the branch that would leak.
PUBLIC_REFS = ("origin/main", "HEAD")
PUBLIC_REF = "origin/main"  # kept for messages that name the published tip

PUBLIC_RESEARCH_ROOTS = (
    "configs/",
    "data/",
    "docs/",
    "reports/",
    "specs/",
    "supabase/",
)
PUBLIC_RESEARCH_FILES = {
    "README.md",
    "STATUS.md",
    "scripts/archive/README.md",
    "artifacts/b1v3_confirmation/post_confirmation_test_report.txt",
    "artifacts/b1_diagnostic_replication/final_evidence_index.csv",
    "artifacts/b1v3_target_blind/evidence_index.csv",
}
FORBIDDEN_PUBLIC_FILENAMES = {"RUNBOOK.md", "REBUILD_RUNBOOK.md"}
INTERNAL_PROSE = re.compile(
    r"(?i)(@codex|codex|claude|AGENTS\.md|\.agents/|\.specify|"
    r"docs/superpowers|[A-Z]:[\\/]Users[\\/])"
)
INTERNAL_WORKFLOW_PROSE = re.compile(r"(?i)(\bspec kit\b|\bfor agents\b)")
PRIVATE_WORKFLOW_PROSE = re.compile(
    r"(?i)([A-Z]:[\\/]MDS650(?:[\\/]|`|\s|$)|"
    r"\bsession (?:message|goal)\b|"
    r"\b(?:defense|public-mirror|user-owned) worktree\b|"
    r"\bowner action\b|\bthe owner must\b|\bowner elects\b|"
    r"\bowner supplied\b|\bowner(?:'s)? signature\b|"
    r"\boptions for the owner\b|\brecommendation to the owner\b|"
    r"\brequires? the owner to\b)"
)
PUBLIC_DESIGN_CONSUMERS = (
    "scripts/build_b1_independent_replication_b1v3.py",
    "scripts/build_b1_independent_replication_timing.py",
    "scripts/build_b1v3_target_blind.py",
    "scripts/plan_b1_independent_replication.py",
)


OPT_OUT = "MDS650_MIRROR_GUARD_MAY_SKIP"


def _unverifiable(reason: str) -> None:
    """The published tip could not be read, so the invariant is unverified.

    Until 2026-08-24 both exit paths below called `pytest.skip`, so a run without the
    `origin` remote — a fresh clone, a shallow CI checkout — reported the suite green
    while never once looking at what was published. A tripwire that cannot see the
    thing it guards has not cleared it. The escape hatch stays available for genuinely
    offline runs, but it has to be asked for by name.
    """
    if os.environ.get(OPT_OUT) == "1":
        pytest.skip(f"{reason} (skipped deliberately via {OPT_OUT}=1)")
    pytest.fail(
        f"{reason}: the published tip could not be read, so the invariant is "
        f"UNVERIFIED, not satisfied. Fetch it with `git fetch origin main`, or set "
        f"{OPT_OUT}=1 to accept an unverified run deliberately."
    )


def _patterns() -> list[str]:
    """The exclude list, minus comments and blanks, with `glob:` prefixes resolved.

    The list is published deliberately, and as PATTERNS rather than an inventory:
    an earlier version named all fifty-five internal documents, so publishing it
    published the catalogue it protected. Withdrawing it entirely was worse — the
    guard then skipped in every public checkout including CI, which is a guard
    that cannot fail, i.e. no guard at all.
    """
    if not EXCLUDE_LIST.is_file():
        pytest.fail(f"the internal exclude list is missing: {EXCLUDE_LIST}")
    entries = []
    for raw in EXCLUDE_LIST.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        entries.append(line[len("glob:") :] if line.startswith("glob:") else line)
    return entries


def _is_internal(path: str, patterns: list[str]) -> bool:
    """A path is internal if it equals a listed path or matches a listed glob."""
    return any(path == pattern or fnmatch.fnmatch(path, pattern) for pattern in patterns)


def test_the_matcher_catches_a_file_that_should_never_be_published() -> None:
    """The detector must fire on both entry forms, or the contract below proves nothing.

    A guard that cannot recognise a violation passes for the same reason a clean tree
    passes, and reads identically in review. This pins the recogniser separately from the
    invariant so the two failure modes stay distinguishable.
    """
    patterns = _patterns()

    assert _is_internal("AGENTS.md", patterns), (
        "an exact-path entry is not being recognised"
    )
    assert _is_internal("docs/handoffs/GOAL_RP2_PRE_PHASE8_20260823.md", patterns), (
        "a `glob:` directory entry is not being recognised"
    )
    assert _is_internal(".agents/skills/example/SKILL.md", patterns), (
        "a `glob:` entry for agent tooling is not being recognised"
    )
    assert _is_internal("reports/supervisor_pack_v3.md", patterns), (
        "a `glob:` entry matching by filename prefix is not being recognised"
    )
    assert _is_internal("docs/example/PRIVATE_MASTER_PLAN.md", patterns)
    assert _is_internal("specs/example/tasks.md", patterns)
    assert not _is_internal("README.md", patterns)
    assert not _is_internal("docs/rp2_v3/VERDICT.md", patterns)


def _tracked_paths() -> list[str]:
    listed = subprocess.run(
        ["git", "ls-files"],
        capture_output=True,
        text=True,
        cwd=REPO,
        check=True,
    )
    return listed.stdout.splitlines()


def test_public_research_prose_has_no_internal_tooling_or_personal_paths() -> None:
    """Research-facing prose must describe evidence, not the private workflow."""
    violations: list[str] = []
    for logical_path in _tracked_paths():
        if logical_path not in PUBLIC_RESEARCH_FILES and not logical_path.startswith(
            PUBLIC_RESEARCH_ROOTS
        ):
            continue
        path = REPO / logical_path
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        prose = path.suffix.lower() in {".md", ".csv", ".txt"}
        if INTERNAL_PROSE.search(content) or (
            prose
            and (
                PRIVATE_WORKFLOW_PROSE.search(content)
                or INTERNAL_WORKFLOW_PROSE.search(content)
            )
        ):
            violations.append(logical_path)
    assert not violations, (
        "public research prose still exposes private tooling or personal paths:\n  "
        + "\n  ".join(violations)
    )


def test_public_tree_uses_research_facing_document_names() -> None:
    leaked = [
        logical_path
        for logical_path in _tracked_paths()
        if Path(logical_path).name in FORBIDDEN_PUBLIC_FILENAMES
    ]
    assert not leaked, "public tree still exposes internal runbook names:\n  " + "\n  ".join(
        leaked
    )


def test_public_design_defaults_resolve_without_internal_documents() -> None:
    """A clean public checkout must contain every default design dependency."""
    assert (REPO / "specs/001-pit-options-rv30/spec.md").is_file()
    for logical_path in PUBLIC_DESIGN_CONSUMERS:
        content = (REPO / logical_path).read_text(encoding="utf-8")
        assert "docs/superpowers" not in content, logical_path
        assert "specs/001-pit-options-rv30/spec.md" in content, logical_path


def test_no_internal_document_is_present_on_the_public_mirror() -> None:
    remotes = subprocess.run(
        ["git", "remote"], capture_output=True, text=True, cwd=REPO, check=False
    ).stdout.split()
    if "origin" not in remotes:
        _unverifiable("MIRROR_GUARD_NO_ORIGIN_REMOTE_CONFIGURED")

    patterns = _patterns()
    for ref in PUBLIC_REFS:
        listed = subprocess.run(
            ["git", "ls-tree", "-r", "--name-only", ref],
            capture_output=True,
            text=True,
            cwd=REPO,
            check=False,
        )
        if listed.returncode != 0:
            _unverifiable(f"MIRROR_GUARD_REF_UNAVAILABLE:{ref}")

        published = listed.stdout.splitlines()
        assert published, f"{ref} lists no files, which cannot be right"

        leaks = sorted(path for path in published if _is_internal(path, patterns))
        if ref != "HEAD" and leaks:
            # A document being withdrawn for the first time is still on the published
            # tip while the branch that removes it is under review. Failing on that
            # would make the contract forbid its own remedy, so a leak that HEAD has
            # already deleted counts as fixed-by-this-branch rather than outstanding.
            # HEAD itself is never forgiven: that is the ref that would merge.
            head_files = set(
                subprocess.run(
                    ["git", "ls-tree", "-r", "--name-only", "HEAD"],
                    capture_output=True, text=True, cwd=REPO, check=False,
                ).stdout.splitlines()
            )
            leaks = [path for path in leaks if path in head_files]
        assert not leaks, (
            f"{len(leaks)} internal working document(s) found on {ref}; a candidate "
            f"branch carrying one would leak at merge, and a published tip must be "
            f"cleaned with `bash scripts/publish_mirror.sh`:\n  " + "\n  ".join(leaks)
        )
