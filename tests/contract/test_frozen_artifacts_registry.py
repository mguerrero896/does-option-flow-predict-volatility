"""Physical-immutability tripwires (decision 62).

The registry data/FROZEN_ARTIFACTS.json pins every frozen artifact to its
SHA-256 at freeze time. Any physical mutation — by any script, any tool, any
direct filesystem write — fails this suite. Hermetic: every registered path is
git-tracked, so the check runs identically on the hosted runner.

A relocated public documentary baseline is accepted only through its explicit
archive map and byte-exact public pin. This does not change a registry entry,
writer protection, withdrawal rule or the original research-protocol identity.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from fnmatch import fnmatch
from pathlib import Path

import pytest
from scripts import freeze_registry as freezer
from scripts import rp4_archive_sources as archive_sources

from mds650 import storage

REPO = Path(__file__).resolve().parents[2]
REGISTRY = REPO / "data" / "FROZEN_ARTIFACTS.json"
REDACTIONS = REPO / "data" / "PUBLIC_METADATA_REDACTIONS.json"
LIVING_COUNT_CLAIMS = (
    (
        REPO / "STATUS.md",
        re.compile(r"Frozen evidence:\s*(?P<count>\d+)\s+artifacts registered\b"),
    ),
    (
        REPO / "docs" / "evidence_immutability_v1.md",
        re.compile(r"\b(?P<count>\d+)\s+frozen artifacts\b", re.IGNORECASE),
    ),
)


def _entries() -> list[dict[str, object]]:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))["entries"]  # type: ignore[no-any-return]


def _registry_at(revision: str) -> list[dict[str, object]] | None:
    relative = REGISTRY.relative_to(REPO).as_posix()
    spec = f"{revision}:{relative}"
    exists = subprocess.run(
        ["git", "cat-file", "-e", spec],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    if exists.returncode != 0:
        return None
    payload = subprocess.run(
        ["git", "show", spec],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return json.loads(payload)["entries"]  # type: ignore[no-any-return]


def _sha(path: Path) -> str:
    """Same platform-stable digest as scripts/freeze_registry.py: text bytes
    LF-normalized (git blob under .gitattributes eol=lf), parquet raw."""
    data = path.read_bytes()
    if path.suffix != ".parquet":
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def _redactions() -> dict[str, dict[str, object]]:
    payload = json.loads(REDACTIONS.read_text(encoding="utf-8"))
    assert payload["schema_version"] == 1
    entries = payload["entries"]
    paths = [str(entry["path"]) for entry in entries]
    assert len(paths) == len(set(paths)), "duplicate metadata-redaction path"
    return {str(entry["path"]): entry for entry in entries}


def _scientific_payload_sha(path: Path) -> str:
    def without_path_metadata(value: object) -> object:
        if isinstance(value, dict):
            return {
                key: "<PATH_METADATA>"
                if key in {"path", "input_path", "train_path", "data_root"}
                else without_path_metadata(item)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [without_path_metadata(item) for item in value]
        return value

    payload = without_path_metadata(json.loads(path.read_text(encoding="utf-8")))
    canonical = json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False
    ).encode()
    return hashlib.sha256(canonical).hexdigest()


def test_registry_is_append_only_and_living_counts_match() -> None:
    """A >= 61 floor gave false safety; HEAD^ also misses earlier branch corruption."""
    entries = _entries()
    relative = REGISTRY.relative_to(REPO).as_posix()
    history = subprocess.run(
        ["git", "log", "--full-history", "--format=%H %P", "--", relative],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    assert history, f"{relative} has no reachable Git history"

    def indexed(snapshot: list[dict[str, object]], label: str) -> dict[str, dict[str, object]]:
        paths = [str(entry["path"]) for entry in snapshot]
        assert len(paths) == len(set(paths)), f"duplicate registry paths at {label}"
        return {str(entry["path"]): entry for entry in snapshot}

    def assert_transition(
        older: list[dict[str, object]],
        newer: list[dict[str, object]],
        label: str,
    ) -> None:
        newer_by_path = indexed(newer, label)
        removed_or_changed = [
            path
            for path, entry in indexed(older, label).items()
            if newer_by_path.get(path) != entry
        ]
        assert not removed_or_changed, (
            f"append-only registry lost or changed entries across {label}: "
            + ", ".join(removed_or_changed)
        )

    for line in history:
        commit, *parents = line.split()
        current = _registry_at(commit)
        assert current is not None, f"{relative} is absent at {commit[:12]}"
        for parent in parents:
            previous = _registry_at(parent)
            if previous is not None:
                assert_transition(previous, current, f"{parent[:12]} -> {commit[:12]}")

    committed = _registry_at("HEAD")
    assert committed is not None, f"{relative} is absent at HEAD"
    assert_transition(committed, entries, "HEAD -> working tree")

    expected = len(entries)
    claims: list[str] = []
    mismatches: list[str] = []
    for document, pattern in LIVING_COUNT_CLAIMS:
        relative = document.relative_to(REPO).as_posix()
        for match in pattern.finditer(document.read_text(encoding="utf-8")):
            stated = int(match.group("count"))
            claims.append(relative)
            if stated != expected:
                mismatches.append(
                    f"{relative} states {stated} frozen artifacts; "
                    f"{REGISTRY.relative_to(REPO).as_posix()} contains {expected}"
                )

    assert "STATUS.md" in claims, "STATUS.md must publish the generated frozen-artifact count"
    assert not mismatches, "frozen-artifact documentation drift: " + "; ".join(mismatches)


def _withdrawn_paths() -> frozenset[str]:
    """Paths a frozen artifact may legitimately be ABSENT from in this checkout.

    Two lists, one meaning: `publish_mirror.sh` strips both from the published
    history, so the artifact lives — with its registered digest intact — only in
    the local canonical tree, where tier 2 verifies it. Until 2026-08-26 this
    read the licensed-dataset list alone, which left the internal-document list
    unable to withdraw anything: a frozen operator runbook could not be pulled
    out of the public tree without the registry calling it MISSING. That is what
    forced `docs/phase8_one_shot_protocol_v1.md` to stay published with an
    operator's machine path in it.
    """
    lists = (
        REPO / "scripts" / "_gated_exclude_list.txt",
        REPO / "scripts" / "_mirror_internal_exclude_list.txt",
    )
    paths: set[str] = set()
    for source in lists:
        for raw in source.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if line and not line.startswith("#"):
                paths.add(line.removeprefix("glob:"))
    return frozenset(paths)


def _is_withdrawn(relative: str, withdrawn: frozenset[str]) -> bool:
    """Exact path or glob. The exclude lists carry PATTERNS since 2026-08-26 —
    naming every internal document individually meant publishing the catalogue —
    so a literal set-membership test would miss every pattern entry."""
    return relative in withdrawn or any(
        fnmatch(relative, pattern) for pattern in withdrawn if "*" in pattern
    )


def test_every_frozen_artifact_is_physically_intact() -> None:
    withdrawn = _withdrawn_paths()
    redactions = _redactions()
    mutated = []
    for entry in _entries():
        relative = str(entry["path"])
        path = REPO / relative
        try:
            path = archive_sources.frozen_public_baseline_path(path, str(entry["sha256"]))
        except ValueError as error:
            mutated.append(f"{error} {relative}")
            continue
        if not path.is_file():
            if _is_withdrawn(relative, withdrawn):
                continue  # stripped from the public mirror; verified locally (tier 2)
            mutated.append(f"MISSING {relative}")
            continue
        actual = _sha(path)
        if actual != entry["sha256"]:
            redaction = redactions.get(relative)
            if not redaction or (
                redaction["original_sha256"] != entry["sha256"]
                or redaction["redacted_sha256"] != actual
            ):
                mutated.append(f"MUTATED {relative}")
    assert not mutated, mutated


def test_registry_cli_verifier_uses_the_same_redaction_and_withdrawal_rules() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/freeze_registry.py", "--verify"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    count = len(_entries())
    assert f"{count}/{count} intact" in completed.stdout


def _sidecar_artifact_and_digest(sidecar: Path) -> tuple[Path, str]:
    """Resolve legacy JSON hashes or a GNU checksum naming one local file."""
    content = sidecar.read_text(encoding="utf-8").strip()
    if re.fullmatch(r"[0-9a-fA-F]{64}", content):
        artifact, digest = sidecar.with_suffix(".json"), content
    else:
        match = re.fullmatch(r"([0-9a-fA-F]{64}) [ *]([^\r\n]+)", content)
        if match is None:
            raise ValueError("SIDECAR_FORMAT_INVALID")
        digest, filename = match.groups()
        if (
            filename in {".", ".."}
            or filename != filename.strip()
            or any(character in filename for character in "/\\:")
        ):
            raise ValueError("SIDECAR_TARGET_UNSAFE")
        artifact = sidecar.parent / filename
    resolved = artifact.resolve()
    if resolved.parent != sidecar.parent.resolve() or not resolved.is_relative_to(REPO.resolve()):
        raise ValueError("SIDECAR_TARGET_UNSAFE")
    return artifact, digest.lower()


def test_gate_sidecars_agree_with_registry() -> None:
    """Every checksum names a safe, registered artifact with the same digest."""
    registered = {str(entry["path"]): str(entry["sha256"]) for entry in _entries()}
    redactions = _redactions()
    disagreements = []
    for sidecar in REPO.glob("artifacts/**/*.sha256"):
        try:
            artifact, sidecar_digest = _sidecar_artifact_and_digest(sidecar)
        except ValueError as error:
            disagreements.append(f"{error} {sidecar.relative_to(REPO).as_posix()}")
            continue
        relative = artifact.relative_to(REPO).as_posix()
        if relative not in registered:
            disagreements.append(f"UNREGISTERED {relative}")
            continue
        try:
            artifact = archive_sources.frozen_public_baseline_path(artifact, registered[relative])
        except ValueError as error:
            disagreements.append(f"{error} {relative}")
            continue
        if not artifact.is_file():
            disagreements.append(f"MISSING {relative}")
            continue
        actual = _sha(artifact)
        redaction = redactions.get(relative)
        if actual != registered[relative] and (
            not redaction
            or redaction["original_sha256"] != registered[relative]
            or redaction["redacted_sha256"] != actual
        ):
            disagreements.append(f"REGISTRY_MISMATCH {relative}")
        if sidecar_digest != actual:
            # sidecars hash the LF payload string at write time; LF-normalized
            # file bytes must agree — divergence means real content drift
            disagreements.append(f"SIDECAR_MISMATCH {relative}")
    assert not disagreements, disagreements


@pytest.fixture
def archived_public_baseline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    logical = "artifacts/fixture/protocol.md"
    physical = tmp_path / logical
    physical.parent.mkdir(parents=True)
    physical.write_text("English reading route\n", encoding="utf-8")
    baseline = tmp_path / "docs/archive/protocol.md.public_baseline.original"
    baseline.parent.mkdir(parents=True)
    baseline.write_bytes(b"Frozen public baseline: N = 419.\n")
    expected = hashlib.sha256(baseline.read_bytes()).hexdigest()
    record = {
        "archive_path": "docs/archive/distinct_registered_original.md.original",
        "public_baseline_path": baseline.relative_to(tmp_path).as_posix(),
        "public_baseline_sha256": expected,
    }
    map_file = tmp_path / "docs/archive/public_history/original_paths.json"
    map_file.parent.mkdir()
    map_file.write_text(json.dumps({logical: record}), encoding="utf-8")
    registry = tmp_path / "data/FROZEN_ARTIFACTS.json"
    registry.parent.mkdir()
    registry.write_text(
        json.dumps({"entries": [{"path": logical, "sha256": expected}]}), encoding="utf-8"
    )
    (physical.parent / "protocol.md.sha256").write_text(
        f"{expected}  protocol.md\n", encoding="utf-8"
    )
    monkeypatch.setattr(archive_sources, "ROOT", tmp_path)
    archive_sources._paths.cache_clear()
    archive_sources._redactions.cache_clear()
    monkeypatch.setattr(freezer, "REPO", tmp_path)
    monkeypatch.setattr(freezer, "REGISTRY", registry)
    monkeypatch.setattr(freezer, "REDACTIONS", tmp_path / "absent_redactions.json")
    monkeypatch.setattr(freezer, "WITHDRAWAL_LISTS", ())
    monkeypatch.setitem(globals(), "REPO", tmp_path)
    monkeypatch.setitem(globals(), "REGISTRY", registry)
    monkeypatch.setitem(globals(), "_redactions", lambda: {})
    monkeypatch.setitem(globals(), "_withdrawn_paths", lambda: frozenset())
    yield physical, baseline, expected, map_file, record, registry
    archive_sources._paths.cache_clear()
    archive_sources._redactions.cache_clear()


def test_public_baseline_relocation_checks_exact_bytes_and_rejects_corruption(
    archived_public_baseline,
) -> None:
    physical, baseline, expected, _, _, registry = archived_public_baseline
    registry_before = registry.read_bytes()
    assert archive_sources.frozen_public_baseline_path(physical, expected) == baseline
    assert freezer.verify() == 0
    test_every_frozen_artifact_is_physically_intact()
    test_gate_sidecars_agree_with_registry()
    baseline.write_bytes(b"Corrupted public baseline: N = 420.\n")
    assert freezer.verify() == 1
    with pytest.raises(AssertionError, match="FROZEN_PUBLIC_BASELINE_MUTATED"):
        test_every_frozen_artifact_is_physically_intact()
    with pytest.raises(AssertionError, match="FROZEN_PUBLIC_BASELINE_MUTATED"):
        test_gate_sidecars_agree_with_registry()
    assert registry.read_bytes() == registry_before


def test_public_baseline_relocation_rejects_false_pin_and_nonarchive_path(
    archived_public_baseline,
) -> None:
    physical, baseline, expected, map_file, record, registry = archived_public_baseline
    registry_before = registry.read_bytes()
    logical = physical.relative_to(REPO).as_posix()
    record["public_baseline_sha256"] = "0" * 64
    map_file.write_text(json.dumps({logical: record}), encoding="utf-8")
    archive_sources._paths.cache_clear()
    assert archive_sources.frozen_public_baseline_path(physical, expected) == physical
    assert freezer.verify() == 1
    with pytest.raises(AssertionError, match="MUTATED"):
        test_every_frozen_artifact_is_physically_intact()
    with pytest.raises(AssertionError, match="REGISTRY_MISMATCH.*SIDECAR_MISMATCH"):
        test_gate_sidecars_agree_with_registry()
    other_path = physical.parent / "same_bytes_outside_archive.md"
    other_path.write_bytes(baseline.read_bytes())
    record["public_baseline_sha256"] = expected
    record["public_baseline_path"] = other_path.relative_to(REPO).as_posix()
    map_file.write_text(json.dumps({logical: record}), encoding="utf-8")
    archive_sources._paths.cache_clear()
    assert freezer.verify() == 1
    with pytest.raises(AssertionError, match="FROZEN_PUBLIC_BASELINE_PATH_UNSAFE"):
        test_every_frozen_artifact_is_physically_intact()
    assert archive_sources.frozen_public_baseline_path(other_path, expected) == other_path
    assert registry.read_bytes() == registry_before


def test_public_baseline_mapping_cannot_redirect_data_or_code(archived_public_baseline) -> None:
    physical, _, expected, map_file, record, _ = archived_public_baseline
    for suffix in (".json", ".py"):
        scientific = physical.with_suffix(suffix)
        logical = scientific.relative_to(REPO).as_posix()
        map_file.write_text(json.dumps({logical: record}), encoding="utf-8")
        archive_sources._paths.cache_clear()
        assert archive_sources.frozen_public_baseline_path(scientific, expected) == scientific


@pytest.mark.parametrize("filename", ["results.json", "producer.py", "protocol.md"])
def test_checksum_formats_preserve_exact_registered_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, filename: str
) -> None:
    monkeypatch.setitem(globals(), "REPO", tmp_path)
    directory = tmp_path / "artifacts" / "fixture"
    directory.mkdir(parents=True)
    artifact = directory / filename
    artifact.write_text("immutable fixture\n", encoding="utf-8")
    digest = _sha(artifact)
    legacy = filename == "results.json"
    sidecar = directory / ("results.sha256" if legacy else f"{filename}.sha256")
    sidecar.write_text(digest if legacy else f"{digest}  {filename}\n", encoding="utf-8")
    relative = artifact.relative_to(tmp_path).as_posix()
    monkeypatch.setitem(globals(), "_entries", lambda: [{"path": relative, "sha256": digest}])
    monkeypatch.setitem(globals(), "_redactions", lambda: {})

    assert _sidecar_artifact_and_digest(sidecar) == (artifact, digest)
    test_gate_sidecars_agree_with_registry()
    artifact.write_text("changed fixture\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="REGISTRY_MISMATCH.*SIDECAR_MISMATCH"):
        test_gate_sidecars_agree_with_registry()


@pytest.mark.parametrize(
    "filename", ["../outside.py", "..\\outside.py", "/outside.py", "C:outside.py"]
)
def test_checksum_rejects_nonlocal_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, filename: str
) -> None:
    monkeypatch.setitem(globals(), "REPO", tmp_path)
    sidecar = tmp_path / "fixture.sha256"
    sidecar.write_text(f"{'0' * 64}  {filename}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="SIDECAR_TARGET_UNSAFE"):
        _sidecar_artifact_and_digest(sidecar)


def test_checksum_rejects_unregistered_gnu_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setitem(globals(), "REPO", tmp_path)
    monkeypatch.setitem(globals(), "_entries", lambda: [])
    monkeypatch.setitem(globals(), "_redactions", lambda: {})
    directory = tmp_path / "artifacts" / "fixture"
    directory.mkdir(parents=True)
    artifact = directory / "producer.py"
    artifact.write_text("immutable fixture\n", encoding="utf-8")
    (directory / "producer.py.sha256").write_text(
        f"{_sha(artifact)}  producer.py\n", encoding="utf-8"
    )
    with pytest.raises(AssertionError, match="UNREGISTERED artifacts/fixture/producer.py"):
        test_gate_sidecars_agree_with_registry()


def test_public_metadata_redactions_preserve_scientific_payloads() -> None:
    registered = {str(entry["path"]): str(entry["sha256"]) for entry in _entries()}
    personal_roots = (
        "C:/" + "Users/mguer",
        "C:\\\\" + "Users\\\\mguer",
        "D:/" + "MDS650",
        "D:\\\\" + "MDS650",
    )
    for relative, redaction in _redactions().items():
        path = REPO / relative
        assert redaction["redaction"] == "PERSONAL_PATH_METADATA_ONLY"
        assert redaction["original_sha256"] == registered[relative]
        assert redaction["redacted_sha256"] == _sha(path)
        assert redaction["scientific_payload_sha256"] == _scientific_payload_sha(path)
        serialized = path.read_text(encoding="utf-8")
        assert not any(root in serialized for root in personal_roots)


def test_writer_guard_rejects_frozen_output_paths() -> None:
    frozen_example = REPO / "artifacts" / "b2_confirmation" / "b2_manifest.json"
    with pytest.raises(ValueError, match="FROZEN_ARTIFACT_WRITE_REJECTED"):
        storage.assert_outside_frozen(frozen_example)
    with pytest.raises(ValueError, match="FROZEN_ARTIFACT_WRITE_REJECTED"):
        storage.assert_outside_frozen(REGISTRY)


def test_writer_guard_fails_closed_without_registry(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="FROZEN_ARTIFACT_REGISTRY_MISSING"):
        storage.frozen_artifact_paths(tmp_path / "missing.json")


def test_writer_guard_allows_new_version_paths(tmp_path: Path) -> None:
    allowed = REPO / "artifacts" / "b2_confirmation_delay120" / "new_output.json"
    assert storage.assert_outside_frozen(allowed) == allowed
    assert storage.assert_outside_frozen(tmp_path / "anything.json") is not None


def test_content_addressed_writer_cannot_update(tmp_path: Path) -> None:
    first = storage.write_content_addressed(b"payload-v1", root=tmp_path, protocol_id="p1")
    assert first.name == hashlib.sha256(b"payload-v1").hexdigest() + ".bin"
    again = storage.write_content_addressed(b"payload-v1", root=tmp_path, protocol_id="p1")
    assert again == first  # identical bytes: verified no-op
    second = storage.write_content_addressed(b"payload-v2", root=tmp_path, protocol_id="p1")
    assert second != first  # different bytes: NEW file, never an overwrite
    assert first.read_bytes() == b"payload-v1"
