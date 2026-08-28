"""Standing tripwire: no licensed-derived dataset may sit in the published HISTORY.

`tests/test_gated_publish_contract.py` guards the working tree: it runs
`git ls-files` and checks every tracked parquet. That is necessary and it is not
sufficient, and on 2026-08-26 an adversarial verifier proved it. Two granular
panels — `artifacts/rp2_block3_target/target_panel.parquet` (21.4 MB, 67,560
origin-level rows x 52 columns of realized-volatility features derived from
licensed 1-minute bars) and `artifacts/rp2_block4_b0/b0_panel.parquet` (12.2 MB)
— had been committed, then deleted from the tree. `git ls-files` stopped seeing
them, the contract went quiet, and every `git clone` of the public repository
kept shipping both files inside `.git` for six days.

Deleting a file from the tree does not delete it from history. This test asks
the question the other one cannot: is there ANY blob, at any commit reachable
from the published tip, that looks like granular licensed data?

The measurement that sets the threshold: after the purge, the largest legitimate
tabular artifact reachable from `main` is 1.18 MB
(`artifacts/provider_timing_v21/b2_canonical_traceability_v21.csv`, 5,401 rows of
per-session-per-asset audit aggregates). The two leaked panels were 21.4 MB and
12.2 MB. A 2 MB ceiling separates them by an order of magnitude in both
directions, so it neither misses a granular panel nor nags about an aggregate.
"""

from __future__ import annotations

import fnmatch
import os
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
INTERNAL_EXCLUDE_LIST = REPO / "scripts" / "_mirror_internal_exclude_list.txt"
#: Above every legitimate aggregate measured on 2026-08-26, an order of magnitude
#: below the smallest leaked panel. See the module docstring.
GRANULAR_MIN_BYTES = 2 * 1024 * 1024
TABULAR_SUFFIXES = (".parquet", ".csv")
#: Synthetic fixtures are committed on purpose: they contain no provider data.
FIXTURE_PREFIXES = ("artifacts/pilot_preview/fixture_",)
OPT_OUT = "MDS650_HISTORY_GUARD_MAY_SKIP"
PERSONAL_PATHS = (
    "C:/" + "Users/mguer",
    "C:\\" + "Users\\mguer",
    "C:\\\\" + "Users\\\\mguer",  # JSON-escaped Windows path
)


def _internal_patterns() -> list[str]:
    """Read the same structural exclusions that the public publisher applies."""
    if not INTERNAL_EXCLUDE_LIST.is_file():
        raise RuntimeError(f"INTERNAL_EXCLUDE_LIST_MISSING:{INTERNAL_EXCLUDE_LIST}")
    return [
        line.strip().removeprefix("glob:")
        for line in INTERNAL_EXCLUDE_LIST.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]


def _internal_history_paths(ref: str) -> list[str]:
    """Every publisher-excluded path still reachable from one public ref."""
    listing = subprocess.run(
        ["git", "rev-list", "--objects", ref],
        capture_output=True, text=True, cwd=REPO, check=False,
    )
    if listing.returncode != 0:
        raise RuntimeError(f"HISTORY_GUARD_REF_UNREADABLE:{ref}")
    patterns = _internal_patterns()
    found = {
        path
        for line in listing.stdout.splitlines()
        for _, _, path in [line.partition(" ")]
        if path and any(path == pattern or fnmatch.fnmatch(path, pattern) for pattern in patterns)
    }
    return sorted(found)


def _personal_path_commits(ref: str) -> list[str]:
    """Commits that introduced or removed the workstation's personal path."""
    found: set[str] = set()
    for token in PERSONAL_PATHS:
        result = subprocess.run(
            ["git", "log", ref, "--format=%H", f"-S{token}", "--"],
            capture_output=True,
            text=True,
            cwd=REPO,
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"HISTORY_GUARD_REF_UNREADABLE:{ref}")
        found.update(result.stdout.split())
    return sorted(found)


def test_the_internal_history_detector_recognises_every_exclusion_form() -> None:
    patterns = _internal_patterns()
    assert any(pattern == "AGENTS.md" for pattern in patterns)
    assert any(fnmatch.fnmatch("AGENTS.md", pattern) for pattern in patterns)
    assert any(
        fnmatch.fnmatch(".agents/skills/example/SKILL.md", pattern) for pattern in patterns
    )
    assert any(
        fnmatch.fnmatch("docs/phase8_one_shot_protocol_v1.md", pattern) for pattern in patterns
    )
    assert any(
        fnmatch.fnmatch("reports/supervisor_pack_v3.md", pattern) for pattern in patterns
    )


def _published_refs() -> list[str]:
    """Every ref that belongs to the PUBLISHED lineage — and nothing else.

    Three refinements, each paid for by a defect:

    1. `HEAD` alone missed a leak reachable only through a tag; an adversarial
       verifier proved it in one move (tag the commit, reset the branch). Tags
       are scanned now, and this repository publishes six of them.
    2. `--all` overcorrected: this machine also holds a disjoint local archive
       lineage that intentionally contains licensed panels. Scanning it made
       the guard cry wolf about files that were never published.
    3. GitHub pull-request refs are also publicly retrievable but are not fetched
       by a normal clone. CI fetches them explicitly and this function scans them.
    4. So the rule is lineage, not location: a ref is in scope when it shares an
       ancestor with `origin/main`. The archive lineage has no merge-base with
       it — measured, not assumed — and drops out automatically.
    """
    refs = ["HEAD"]
    listed = subprocess.run(
        [
            "git",
            "for-each-ref",
            "--format=%(refname)",
            "refs/remotes",
            "refs/tags",
            "refs/pull",
        ],
        capture_output=True,
        text=True,
        cwd=REPO,
        check=False,
    ).stdout.split()
    for ref in listed:
        shares_lineage = subprocess.run(
            ["git", "merge-base", "origin/main", ref],
            capture_output=True,
            text=True,
            cwd=REPO,
            check=False,
        )
        if shares_lineage.returncode == 0:
            refs.append(ref)
    return refs


def _granular_blobs(ref: str) -> list[str]:
    """Every tabular blob over the threshold reachable from *ref*, as 'size path'."""
    listing = subprocess.run(
        ["git", "rev-list", "--objects", ref],
        capture_output=True,
        text=True,
        cwd=REPO,
        check=False,
    )
    if listing.returncode != 0:
        raise RuntimeError(f"HISTORY_GUARD_REF_UNREADABLE:{ref}")
    checked = subprocess.run(
        ["git", "cat-file", "--batch-check=%(objecttype) %(objectsize) %(rest)"],
        input=listing.stdout,
        capture_output=True,
        text=True,
        cwd=REPO,
        check=False,
    )
    found = []
    for line in checked.stdout.splitlines():
        fields = line.split(maxsplit=2)
        if len(fields) < 3 or fields[0] != "blob":
            continue
        size, path = int(fields[1]), fields[2]
        if size <= GRANULAR_MIN_BYTES or not path.endswith(TABULAR_SUFFIXES):
            continue
        if path.startswith(FIXTURE_PREFIXES):
            continue
        found.append(f"{size / 1048576:.1f} MB  {path}")
    return sorted(set(found))


def test_the_clone_is_deep_enough_for_this_guard_to_mean_anything() -> None:
    """A shallow clone makes this guard a tree check wearing a history costume.

    Measured 2026-08-26: under `actions/checkout` with the default
    `fetch-depth: 1`, `git rev-list --objects HEAD` sees exactly one commit, so
    a branch that adds a file and then deletes it passes here while a full clone
    flags it. CI now checks out with `fetch-depth: 0`; this test fails loudly if
    that ever regresses, instead of passing on a repository it cannot see.
    """
    if os.environ.get(OPT_OUT) == "1":
        pytest.skip(f"history guard skipped deliberately via {OPT_OUT}=1")
    shallow = subprocess.run(
        ["git", "rev-parse", "--is-shallow-repository"],
        capture_output=True,
        text=True,
        cwd=REPO,
        check=False,
    ).stdout.strip()
    if shallow != "false" and os.environ.get("CI") != "true":
        pytest.skip("shallow local checkout: the guard below reports reduced scope")
    assert shallow == "false", (
        "CI checked out SHALLOW, so the history guard can only see the tip and "
        "would pass on a leak it cannot reach. Set fetch-depth: 0 on this job."
    )


def test_no_granular_dataset_is_reachable_in_the_published_history() -> None:
    if os.environ.get(OPT_OUT) == "1":
        pytest.skip(f"history guard skipped deliberately via {OPT_OUT}=1")
    leaks = {ref: _granular_blobs(ref) for ref in _published_refs()}
    offending = {ref: found for ref, found in leaks.items() if found}
    assert not offending, (
        "granular licensed-derived data is reachable in the git history — deleting "
        "it from the tree is NOT enough, every clone still ships it:\n"
        + "\n".join(
            f"  {ref}:\n    " + "\n    ".join(found) for ref, found in offending.items()
        )
        + "\n\nPurging requires rewriting history (git filter-repo --invert-paths) and "
        "a force push, which is an owner decision — see docs/rp2_v3/MIRROR_HAZARD.md."
    )


def test_the_detector_recognises_a_granular_blob() -> None:
    """A guard that cannot see a violation passes for the same reason a clean
    repository does, and reads identically in review."""
    line = "blob 22470000 artifacts/rp2_block3_target/target_panel.parquet"
    fields = line.split(maxsplit=2)
    size, path = int(fields[1]), fields[2]
    assert size > GRANULAR_MIN_BYTES
    assert path.endswith(TABULAR_SUFFIXES)
    assert not path.startswith(FIXTURE_PREFIXES)

def test_no_internal_document_is_reachable_in_the_published_history() -> None:
    """Publisher-excluded documents must be absent from every reachable public blob."""
    if os.environ.get(OPT_OUT) == "1":
        pytest.skip(f"history guard skipped deliberately via {OPT_OUT}=1")
    leaks = {ref: _internal_history_paths(ref) for ref in _published_refs()}
    offending = {ref: found for ref, found in leaks.items() if found}
    assert not offending, (
        "PUBLISHED_HISTORY_INTERNAL_DOCUMENTS: a path excluded by "
        "scripts/_mirror_internal_exclude_list.txt remains reachable. Deleting it from "
        "HEAD is not enough; every clone still receives the blob. Remediation requires "
        "an owner-authorized history rewrite and coordinated tag/remote handling: "
        + "; ".join(f"{ref}: {found[:5]}" for ref, found in offending.items())
    )


def test_no_personal_workstation_path_is_published_now_or_in_history() -> None:
    if os.environ.get(OPT_OUT) == "1":
        pytest.skip(f"history guard skipped deliberately via {OPT_OUT}=1")
    grep_patterns = [argument for token in PERSONAL_PATHS for argument in ("-e", token)]
    current = subprocess.run(
        ["git", "grep", "-FIl", *grep_patterns],
        capture_output=True,
        text=True,
        cwd=REPO,
        check=False,
    )
    assert current.returncode in (0, 1)
    assert not current.stdout.splitlines(), (
        f"PUBLISHED_PERSONAL_PATHS_CURRENT:{current.stdout.splitlines()}"
    )
    leaks = {ref: _personal_path_commits(ref) for ref in _published_refs()}
    offending = {ref: commits for ref, commits in leaks.items() if commits}
    assert not offending, (
        "PUBLISHED_HISTORY_PERSONAL_PATHS: personal workstation paths remain reachable; "
        "an owner-authorized history rewrite is required: "
        + "; ".join(f"{ref}: {commits[:5]}" for ref, commits in offending.items())
    )
