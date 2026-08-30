"""Every path a document names must exist, and every digest it quotes must be real.

The anti-drift tripwire (decision 63) regenerates CANONICAL_STATE.json and STATUS.md and
compares them, which catches a *stale generated* document. It cannot catch a hand-written
document that names a file which was later renamed, or that quotes the SHA-256 of an
artifact that has since been re-run. Both failures read as evidence to a reader and are
invisible to the generator, so they get their own tripwire here.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from functools import cache
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

#: Documents whose file-like claims must resolve now, not as prospective output names.
HEADLINE_DOCUMENTS: tuple[str, ...] = (
    "README.md",
    "STATUS.md",
    "docs/INDEX.md",
    "docs/DEVELOPER_GUIDE.md",
    "docs/architecture.md",
    "reports/INDEX.md",
    "scripts/README.md",
    "supabase/README.md",
)

# Keeping the maintained navigation surfaces here makes a
# missing onboarding link fail in CI instead of becoming tribal knowledge.
MAINTAINER_NAVIGATION: tuple[str, ...] = (
    "CONTRIBUTING.md",
    "docs/INDEX.md",
    "docs/AI_ASSISTANCE_STATEMENT.md",
    "docs/DEVELOPER_GUIDE.md",
    "scripts/README.md",
    "reports/INDEX.md",
    "supabase/README.md",
)

PATH_IN_BACKTICKS = re.compile(
    r"`([A-Za-z0-9_./-]+\.(?:md|py|json|jsonl|yml|yaml|parquet|txt|sql|csv))`"
)
MARKDOWN_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
QUOTED_DIGEST = re.compile(r"`?([a-z0-9_]*sha256)`?\s*=\s*`?([0-9a-f]{64})`?")


@cache
def _documents() -> tuple[Path, ...]:
    listing = subprocess.run(
        ["git", "ls-files", "*.md"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    return tuple(REPO / name for name in listing)


@cache
def _headline_documents() -> tuple[Path, ...]:
    return tuple(REPO / name for name in HEADLINE_DOCUMENTS) + tuple(
        sorted((REPO / "docs" / "rp2").glob("*.md"))
    )


@cache
def _tracked_basenames() -> dict[str, int]:
    listing = subprocess.run(
        ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.split()
    counts: dict[str, int] = {}
    for entry in listing:
        name = entry.rsplit("/", 1)[-1]
        counts[name] = counts.get(name, 0) + 1
    return counts


@cache
def _gated() -> frozenset[str]:
    return frozenset((REPO / "scripts" / "_gated_exclude_list.txt").read_text().split())


@cache
def _mirror_stripped() -> frozenset[str]:
    """Internal working documents the public mirror deliberately omits.

    The canonical repository is where this check has meaning: a reference to an internal
    document is valid here and is *expected* to be absent from the mirror. Without this the
    suite would demand that the mirror carry the very files it exists to strip.

    It does not excuse the reference being unreadable to a mirror reader — a clickable link
    to a stripped document is a 404 for them. That is why the link check below refuses these
    paths even though the prose check accepts them.
    """

    listing = REPO / "scripts" / "_mirror_internal_exclude_list.txt"
    if not listing.is_file():
        return frozenset()
    entries = [
        line.strip()
        for line in listing.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]
    return frozenset(entry.removeprefix("glob:") for entry in entries)


def _stripped_from_mirror(target: str) -> bool:
    """Whether the publish step removes this path from the public mirror.

    Documents name each other by bare filename as often as by full path — `docs/INDEX.md`
    lists its siblings without the directory — so the basename has to match too, or the
    same file reads as internal in one document and missing in another.
    """

    stripped = _mirror_stripped()
    if target in stripped:
        return True
    if target.rsplit("/", 1)[-1] in {entry.rsplit("/", 1)[-1] for entry in stripped}:
        return True
    return any(pattern.endswith("*") and target.startswith(pattern[:-1]) for pattern in stripped)


@cache
def _pointer_names() -> frozenset[str]:
    """Derived panels are licensed-provider outputs: pointers are tracked, bytes are not."""

    pointers = REPO / "artifacts" / "rp2_panel_pointers.json"
    if not pointers.is_file():
        return frozenset()
    text = pointers.read_text(encoding="utf-8")
    return frozenset(re.findall(r"[A-Za-z0-9_./-]+\.parquet", text))


#: How a document declares, in its own text, that a path it names is not published.
#: This is the self-documenting alternative to an inventory: after 2026-08-26 the
#: exclude list carries structural PATTERNS rather than fifty-five filenames, so a
#: reference to an individual internal document is validated by the note beside it
#: rather than by a central list that would have to name it — and publishing that
#: list would publish the catalogue it protects.
NOT_PUBLISHED_MARKERS = (
    "not part of the public mirror",
    "kept local",
    "withdrawn from the public mirror",
    "internal working record",
)


def _declared_unpublished_beside_the_reference(document: Path, target: str) -> bool:
    """True when the line naming *target* also says the file is not published."""
    for line in document.read_text(encoding="utf-8", errors="replace").splitlines():
        if target in line and any(marker in line for marker in NOT_PUBLISHED_MARKERS):
            return True
    return False


def _resolves(document: Path, target: str) -> bool:
    if (document.parent / target).exists() or (REPO / target).exists():
        return True
    if target in _gated() or target in _pointer_names():
        return True
    if _stripped_from_mirror(target):
        return True
    if _declared_unpublished_beside_the_reference(document, target):
        return True
    if any(target in name for name in _pointer_names()):
        return True
    # A bare filename is a valid reference when exactly one tracked file carries it.
    return _tracked_basenames().get(target.rsplit("/", 1)[-1], 0) == 1


def _link_resolves(document: Path, target: str) -> bool:
    """Resolve a Markdown link exactly as GitHub does: relative to its document."""

    candidate = (document.parent / target).resolve()
    try:
        logical = candidate.relative_to(REPO.resolve()).as_posix()
    except ValueError:
        return False
    return candidate.exists() and not _stripped_from_mirror(logical)


def test_every_path_named_in_a_headline_document_exists() -> None:
    missing: list[str] = []
    for document in _headline_documents():
        text = document.read_text(encoding="utf-8", errors="replace")
        for target in sorted(set(PATH_IN_BACKTICKS.findall(text))):
            if not _resolves(document, target):
                missing.append(f"{document.relative_to(REPO).as_posix()} -> {target}")
    assert not missing, f"documents naming files that do not exist: {missing}"


def test_every_internal_markdown_link_resolves() -> None:
    broken: list[str] = []
    for document in _documents():
        text = document.read_text(encoding="utf-8", errors="replace")
        for target in sorted(set(MARKDOWN_LINK.findall(text))):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            # The README badge is a GitHub repository-relative URL, not a file path.
            # Other ../../ links are ordinary relative links and must resolve exactly.
            if document == REPO / "README.md" and target.startswith("../../actions/"):
                continue
            relative = target.split("#", 1)[0]
            if not relative:
                continue
            # A clickable link is stricter than a mention: a reader of the public mirror
            # who follows one to a stripped document gets a 404.
            if not _link_resolves(document, relative):
                broken.append(f"{document.relative_to(REPO).as_posix()} -> {target}")
    assert not broken, f"broken internal links: {broken}"


def test_readme_links_every_maintainer_navigation_surface() -> None:
    """A new maintainer must not need to discover the repository by directory search."""

    readme = (REPO / "README.md").read_text(encoding="utf-8")
    missing = [path for path in MAINTAINER_NAVIGATION if f"]({path})" not in readme]
    assert not missing, f"README does not link maintainer navigation: {missing}"
    assert "[Issues](" in readme, "README does not link the public issue tracker"


def test_methodology_decision_index_covers_every_decision() -> None:
    """Numbered references must resolve without searching the decision ledger."""

    text = (REPO / "docs" / "methodology_decisions.md").read_text(encoding="utf-8")
    index, separator, _ = text.partition('<a id="decision-1"></a>')
    assert separator, "methodology decision index has no decision-1 anchor"

    indexed: list[int] = []
    targets: set[int] = set()
    for first, last, anchor in re.findall(
        r"\[(\d+)–(\d+)\]\(#decision-(\d+)\)", index
    ):
        assert first == anchor
        targets.add(int(anchor))
        indexed.extend(range(int(first), int(last) + 1))

    decisions = [int(number) for number in re.findall(r"(?m)^(\d+)\. \*\*", text)]
    assert indexed == decisions, "methodology decision index does not cover the ledger"
    targets.add(75)
    for target in targets:
        anchor = f'<a id="decision-{target}"></a>'
        assert f"\n\n{anchor}\n\n" in text
    assert "(#decision-75)" in index


def test_every_top_level_script_is_catalogued() -> None:
    """Every runnable top-level script needs a lifecycle and purpose in the script index."""

    catalog = (REPO / "scripts" / "README.md").read_text(encoding="utf-8")
    actual = {
        path.relative_to(REPO).as_posix()
        for path in (REPO / "scripts").iterdir()
        if path.is_file() and path.suffix in {".py", ".ps1", ".sh"}
    }
    indexed = {
        path
        for path in re.findall(r"`(scripts/[^`]+\.(?:py|ps1|sh))`", catalog)
        if Path(path).parent == Path("scripts")
    }
    missing = sorted(actual - indexed)
    stale = sorted(indexed - actual)
    assert not missing, f"top-level scripts missing from scripts/README.md: {missing}"
    assert not stale, f"scripts/README.md names missing top-level scripts: {stale}"


@cache
def _known_digests() -> frozenset[str]:
    """Every digest the repository can vouch for: registry, artifacts, pointers."""

    known: set[str] = set()
    registry = json.loads((REPO / "data" / "FROZEN_ARTIFACTS.json").read_text(encoding="utf-8"))
    known.update(str(entry["sha256"]) for entry in registry["entries"])
    for artifact in (REPO / "artifacts").rglob("*.json"):
        try:
            payload = json.loads(artifact.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError, OSError):
            continue
        known.update(_digests_within(payload))
    return frozenset(known)


def _digests_within(payload: object) -> set[str]:
    found: set[str] = set()
    if isinstance(payload, dict):
        for value in payload.values():
            found |= _digests_within(value)
    elif isinstance(payload, list):
        for value in payload:
            found |= _digests_within(value)
    elif isinstance(payload, str) and re.fullmatch(r"[0-9a-f]{64}", payload):
        found.add(payload)
    return found


def test_every_digest_quoted_in_a_block_document_is_one_the_repository_holds() -> None:
    """A quoted SHA-256 that matches nothing on disk is a claim about a run nobody can find.

    This is how a re-run silently orphans its own documentation: the artifact changes, the
    document keeps the old digest, and the digest still *looks* like provenance.
    """

    orphaned: list[str] = []
    known = _known_digests()
    for document in _documents():
        text = document.read_text(encoding="utf-8", errors="replace")
        for name, digest in QUOTED_DIGEST.findall(text):
            if digest not in known:
                orphaned.append(f"{document.relative_to(REPO).as_posix()} {name}={digest[:12]}")
    assert not orphaned, f"digests quoted but not held anywhere: {orphaned}"


def test_the_canonical_state_authorized_sources_all_exist() -> None:
    """The generator reads from a fixed list; a renamed source would silently drop a field."""

    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "generate_canonical_state", REPO / "scripts" / "generate_canonical_state.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    gated = _gated()
    missing = [
        source
        for source in module.AUTHORIZED_SOURCES
        if not (REPO / source).exists() and source not in gated
    ]
    assert not missing, f"CANONICAL_STATE sources that no longer exist: {missing}"


def test_the_registry_digest_recorded_in_canonical_state_is_current() -> None:
    state = json.loads((REPO / "data" / "CANONICAL_STATE.json").read_text(encoding="utf-8"))
    registry = REPO / "data" / "FROZEN_ARTIFACTS.json"
    digest = hashlib.sha256(registry.read_bytes().replace(b"\r\n", b"\n")).hexdigest()
    assert state["frozen_evidence"]["registry_sha256"] == digest
