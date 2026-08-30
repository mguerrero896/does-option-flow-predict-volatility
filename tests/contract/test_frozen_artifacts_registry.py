"""Physical-immutability tripwires (decision 62).

The registry data/FROZEN_ARTIFACTS.json pins every frozen artifact to its
SHA-256 at freeze time. Any physical mutation — by any script, any tool, any
direct filesystem write — fails this suite. Hermetic: every registered path is
git-tracked, so the check runs identically on the hosted runner.
"""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from fnmatch import fnmatch
from pathlib import Path

import pytest

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
    """The >= 61 floor could not detect later registry or living-document drift."""
    entries = _entries()
    paths = [str(entry["path"]) for entry in entries]
    assert len(paths) == len(set(paths)), "duplicate registry paths"

    parent_payload = subprocess.run(
        ["git", "show", f"HEAD^:{REGISTRY.relative_to(REPO).as_posix()}"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    parent_entries = json.loads(parent_payload)["entries"]
    current_by_path = {str(entry["path"]): entry for entry in entries}
    removed_or_changed = [
        str(entry["path"])
        for entry in parent_entries
        if current_by_path.get(str(entry["path"])) != entry
    ]
    assert not removed_or_changed, (
        "append-only registry lost or changed entries from HEAD^: "
        + ", ".join(removed_or_changed)
    )

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

    assert "STATUS.md" in claims, (
        "STATUS.md must publish the generated frozen-artifact count"
    )
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


def test_gate_sidecars_agree_with_registry() -> None:
    """Every results.sha256 sidecar value equals the registered digest of its JSON."""
    registered = {str(entry["path"]): str(entry["sha256"]) for entry in _entries()}
    redactions = _redactions()
    disagreements = []
    for sidecar in REPO.glob("artifacts/**/*.sha256"):
        artifact = sidecar.with_suffix(".json")
        relative = artifact.relative_to(REPO).as_posix()
        if relative not in registered:
            disagreements.append(f"UNREGISTERED {relative}")
            continue
        sidecar_digest = sidecar.read_text(encoding="utf-8").strip()
        actual = _sha(artifact)
        redaction = redactions.get(relative)
        if actual != registered[relative] and (
            not redaction
            or redaction["original_sha256"] != registered[relative]
            or redaction["redacted_sha256"] != actual
        ):
            disagreements.append(f"REGISTRY_MISMATCH {relative}")
        if sidecar_digest and sidecar_digest != actual:
            # sidecars hash the LF payload string at write time; LF-normalized
            # file bytes must agree — divergence means real content drift
            disagreements.append(f"SIDECAR_MISMATCH {relative}")
    assert not disagreements, disagreements


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
