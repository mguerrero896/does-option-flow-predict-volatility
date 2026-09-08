"""Relocation preserves sealed bytes and leaves readable, working public routes."""

import hashlib
import json
import re
from pathlib import Path

import pytest
from scripts import rp4_archive_sources as archive
from scripts.rp4_archive_sources import (
    ROOT,
    assert_historical_sha256,
    logical_path,
    original_path,
    public_path,
)

ARCHIVE = ROOT / "docs/archive/rp4/DEFENSE_PACKAGE"
LINK = re.compile(r"!?\[([^\]]*)\]\(([^)]+)\)")


def pin_receipt(receipt: Path) -> Path:
    registry = archive.ROOT / "data/FROZEN_ARTIFACTS.json"
    registry.parent.mkdir(exist_ok=True)
    registry.write_text(
        json.dumps(
            {
                "entries": [
                    {
                        "path": receipt.relative_to(archive.ROOT).as_posix(),
                        "sha256": hashlib.sha256(receipt.read_bytes()).hexdigest(),
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    return registry


def test_archive_map_preserves_original_bytes_and_identities() -> None:
    mapping = json.loads((ARCHIVE / "original_paths.json").read_text("utf-8"))
    assert len(mapping) >= 91
    for logical, record in mapping.items():
        archived = (ROOT / record["archive_path"]).resolve()
        assert archived.is_relative_to(ROOT / "docs/archive"), logical
        scope = assert_historical_sha256(logical, record["sha256"])
        assert scope in {"original_bytes", "public_redaction_provenance"}
        if scope == "original_bytes":
            assert hashlib.sha256(archived.read_bytes()).hexdigest() == record["sha256"], logical
            assert original_path(logical) == archived
            assert original_path(archived) == archived
        assert logical_path(archived) == ROOT / logical
        if "public_path" in record:
            public = public_path(logical)
            assert public.is_relative_to(ROOT) and public.is_file(), logical
            recorded = (ROOT / record["public_path"]).resolve()
            if recorded.is_file():
                assert public == recorded


def test_archive_display_changes_links_only_and_all_links_work() -> None:
    mapping = json.loads((ARCHIVE / "original_paths.json").read_text("utf-8"))
    documents = 0
    for logical, _record in mapping.items():
        if not logical.startswith("docs/rp4/DEFENSE_PACKAGE/") or not logical.endswith(".md"):
            continue
        original = original_path(logical).read_text("utf-8")
        public = public_path(logical).read_text("utf-8")
        # Labels and all prose, table values, code, headings and ordering are unchanged.
        assert LINK.sub(lambda match: match[1], original) == LINK.sub(
            lambda match: match[1], public
        ), logical
        documents += 1
    assert documents == 30
    checked = 0
    for document in ARCHIVE.rglob("*.md"):
        for _, target in LINK.findall(document.read_text("utf-8")):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            linked = (document.parent / target.split("#")[0]).resolve()
            assert linked.is_relative_to(ROOT) and linked.is_file(), (document, target)
            checked += 1
    assert checked > 300


def test_archive_contains_each_english_summary_and_current_route() -> None:
    layers = [ARCHIVE, ARCHIVE / "revision_2"] + [
        ARCHIVE / "revision_2" / f"correction_{index}" for index in range(1, 7)
    ]
    for layer in layers:
        summary = (layer / "SUMMARY.md").read_text("utf-8")
        assert len(summary.split()) >= 190
        assert "current English defense" in summary
        assert "RESEARCH_ONLY" in summary and "capital_go=false" in summary
        assert ".original" in summary


def test_temporary_mutation_sources_are_never_redirected(tmp_path: Path) -> None:
    source = tmp_path / "README.md"
    source.write_text("Altered fixture bytes", encoding="utf-8")
    assert original_path(source) == public_path(source) == logical_path(source) == source
    assert original_path(source).read_text("utf-8") == "Altered fixture bytes"


def test_protocol_retains_distinct_registered_and_public_baseline_pins() -> None:
    logical = "artifacts/rp4_v4_prereg/protocol.md"
    mapping = json.loads(
        (ROOT / "docs/archive/public_history/original_paths.json").read_text("utf-8")
    )
    record = mapping[logical]
    assert record["sha256"] == ("6f8ad8d53a8f4336851415a99c25b316bf44db74165e29246110a3bb133eabee")
    assert record["public_baseline_sha256"] == (
        "4ef4a84f14179312635e01afdbe5df6cc2f50c1f81b4d53f534c1fabb362bd08"
    )
    assert_historical_sha256(logical, record["sha256"])
    baseline = ROOT / record["public_baseline_path"]
    assert hashlib.sha256(baseline.read_bytes()).hexdigest() == record["public_baseline_sha256"]
    numbers = r"\d+(?:\.\d+)?"
    assert re.findall(numbers, original_path(logical).read_text("utf-8")) == re.findall(
        numbers, baseline.read_text("utf-8")
    )


def test_historical_document_archive_preserves_content_and_working_routes() -> None:
    historical = ROOT / "docs/archive/public_history"
    mapping = json.loads((historical / "original_paths.json").read_text("utf-8"))
    assert len(mapping) == 50
    for logical, record in mapping.items():
        assert_historical_sha256(logical, record["sha256"])
        original = original_path(logical).read_text("utf-8")
        display = (ROOT / record["public_path"]).read_text("utf-8")
        assert LINK.sub(lambda match: match[1], original) == LINK.sub(
            lambda match: match[1], display
        ), logical
        summary = (ROOT / record["summary_path"]).read_text("utf-8")
        assert "Historical English summary" in summary
        assert "RESEARCH_ONLY" in summary and "capital_go=false" in summary
        stub = (ROOT / logical).read_text("utf-8")
        assert "This document is archived" in stub
    for document in historical.rglob("*.md"):
        for _, target in LINK.findall(document.read_text("utf-8")):
            if target.startswith(("http://", "https://", "mailto:", "#")):
                continue
            linked = (document.parent / target.split("#")[0]).resolve()
            assert linked.is_relative_to(ROOT) and linked.exists(), (document, target)


@pytest.fixture
def redacted_archive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(archive, "ROOT", tmp_path)
    archive._paths.cache_clear()
    archive._redactions.cache_clear()
    archive._withheld_sources.cache_clear()
    original = tmp_path / "docs/archive/example.md.original"
    original.parent.mkdir(parents=True)
    original.write_text("Private directory: /private/example. Sessions: 419.\n", encoding="utf-8")
    public = tmp_path / "docs/archive/example.public.md"
    public.write_text("Directory: [redacted]. Sessions: 419.\n", encoding="utf-8")
    pin = hashlib.sha256(original.read_bytes()).hexdigest()
    mapping = tmp_path / "docs/archive/public_refresh_baseline/original_paths.json"
    mapping.parent.mkdir()
    mapping.write_text(
        json.dumps({"docs/example.md": {"archive_path": "docs/archive/example.md.original"}}),
        encoding="utf-8",
    )
    receipt = tmp_path / "artifacts/rp4_public_refresh/archive_redactions.json"
    receipt.parent.mkdir(parents=True)
    data = {
        "schema_version": "public-archive-redactions-v1",
        "entries": [
            {
                "logical_path": "docs/example.md",
                "original_sha256": pin,
                "public_path": "docs/archive/example.public.md",
                "public_sha256": hashlib.sha256(public.read_bytes()).hexdigest(),
                "rule": "Remove a private directory from prose",
                "numeric_invariant": True,
            }
        ],
    }
    receipt.write_text(json.dumps(data), encoding="utf-8")
    pin_receipt(receipt)
    yield original, public, pin, receipt, data
    archive._paths.cache_clear()
    archive._redactions.cache_clear()
    archive._withheld_sources.cache_clear()


def test_public_redaction_never_claims_original_byte_equality_and_rejects_drift(
    redacted_archive,
) -> None:
    original, public, pin, _, _ = redacted_archive
    assert assert_historical_sha256("docs/example.md", pin) == "original_bytes"
    original.unlink()
    assert assert_historical_sha256("docs/example.md", pin) == "public_redaction_provenance"
    assert public_path("docs/example.md") == public
    public.write_text("Changed sessions: 420.\n", encoding="utf-8")
    with pytest.raises(AssertionError, match="Public redaction bytes changed"):
        assert_historical_sha256("docs/example.md", pin)


def test_public_redaction_rejects_incompatible_receipt(redacted_archive) -> None:
    original, _, _, _, _ = redacted_archive
    original.unlink()
    with pytest.raises(AssertionError, match="Incompatible original provenance pin"):
        assert_historical_sha256("docs/example.md", "0" * 64)


def test_redaction_and_receipt_cannot_be_rewritten_together(redacted_archive) -> None:
    original, public, pin, receipt, data = redacted_archive
    original.unlink()
    registry = archive.ROOT / "data/FROZEN_ARTIFACTS.json"
    frozen = registry.read_bytes()
    assert assert_historical_sha256("docs/example.md", pin) == "public_redaction_provenance"
    public.write_text("Directory: [redacted]. Sessions: 420.\n", encoding="utf-8")
    data["entries"][0]["public_sha256"] = hashlib.sha256(public.read_bytes()).hexdigest()
    data["entries"][0]["numeric_invariant"] = True
    receipt.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="MANIFEST_HASH_MISMATCH"):
        assert_historical_sha256("docs/example.md", pin)
    archive._paths.cache_clear()
    archive._redactions.cache_clear()
    archive._withheld_sources.cache_clear()
    with pytest.raises(ValueError, match="MANIFEST_HASH_MISMATCH"):
        assert_historical_sha256("docs/example.md", pin)
    assert registry.read_bytes() == frozen


@pytest.mark.parametrize("failure", ["missing_pin", "duplicate_pin", "bad_pin", "missing_receipt"])
def test_redaction_manifest_requires_one_valid_present_pin(redacted_archive, failure: str) -> None:
    _, _, _, receipt, _ = redacted_archive
    registry = archive.ROOT / "data/FROZEN_ARTIFACTS.json"
    data = json.loads(registry.read_bytes())
    if failure == "missing_pin":
        data["entries"] = []
    elif failure == "duplicate_pin":
        data["entries"] *= 2
    elif failure == "bad_pin":
        data["entries"][0]["sha256"] = "invalid"
    else:
        receipt.unlink()
    registry.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="MANIFEST_(PIN_INVALID|MISSING)"):
        archive.verified_redaction_receipt()


@pytest.fixture
def withheld_archive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(archive, "ROOT", tmp_path)
    archive._paths.cache_clear()
    archive._redactions.cache_clear()
    archive._withheld_sources.cache_clear()
    logical = "scripts/internal_projection.py"
    pin = "a" * 64
    receipt = tmp_path / "artifacts/rp4_public_refresh/archive_redactions.json"
    receipt.parent.mkdir(parents=True)
    receipt.write_text(
        json.dumps(
            {
                "schema_version": "public-archive-redactions-v1",
                "entries": [],
                "withheld_sources": [
                    {
                        "logical_path_sha256": hashlib.sha256(logical.encode("utf-8")).hexdigest(),
                        "original_sha256": pin,
                        "reason": "Internal operational source is not distributed",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    pin_receipt(receipt)
    yield logical, pin
    archive._paths.cache_clear()
    archive._redactions.cache_clear()
    archive._withheld_sources.cache_clear()


def test_withheld_source_rejects_unregistered_missing_and_does_not_supply_values(
    withheld_archive,
) -> None:
    logical, pin = withheld_archive
    assert assert_historical_sha256(logical, pin) == "private_source_not_distributed"
    with pytest.raises(AssertionError, match="Unregistered missing historical source"):
        assert_historical_sha256("scripts/unregistered_missing.py", pin)
    with pytest.raises(FileNotFoundError):
        original_path(logical).read_bytes()
    source = original_path(logical)
    source.parent.mkdir()
    source.write_text("A distributed stub is not absence", encoding="utf-8")
    with pytest.raises(AssertionError, match="not distributed is present"):
        assert_historical_sha256(logical, pin)


def test_withheld_source_rejects_an_incompatible_pin(withheld_archive) -> None:
    logical, _ = withheld_archive
    with pytest.raises(AssertionError, match="Incompatible withheld-source pin"):
        assert_historical_sha256(logical, "b" * 64)


def test_withheld_receipt_cannot_supply_a_rewritten_provenance_pin(withheld_archive) -> None:
    logical, pin = withheld_archive
    assert assert_historical_sha256(logical, pin) == "private_source_not_distributed"
    receipt = archive.ROOT / "artifacts/rp4_public_refresh/archive_redactions.json"
    data = json.loads(receipt.read_bytes())
    data["withheld_sources"][0]["original_sha256"] = "b" * 64
    receipt.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError, match="MANIFEST_HASH_MISMATCH"):
        assert_historical_sha256(logical, "b" * 64)
