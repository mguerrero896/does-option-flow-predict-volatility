"""The public Part 34 receipt preserves pins without relabelling derivatives."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest
from scripts import build_rp4_v5_public_receipt as producer
from scripts import rp4_archive_sources as archive
from scripts.build_rp4_v5_public_receipt import (
    PRIVATE,
    PUBLIC,
    PUBLIC_SIDECAR,
    SOURCE,
    SOURCE_SHA256,
    rendered_files,
    source_receipt,
)
from scripts.rp4_archive_sources import original_path, public_path

ROOT = Path(__file__).resolve().parents[2]


def test_receipt_writer_rejects_registered_drift_before_any_write(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(producer, "ROOT", tmp_path)
    (tmp_path / "data").mkdir()
    original = b"registered bytes\n"
    (tmp_path / "receipt.json").write_bytes(original)
    (tmp_path / "data/FROZEN_ARTIFACTS.json").write_text(
        json.dumps(
            {"entries": [{"path": "receipt.json", "sha256": hashlib.sha256(original).hexdigest()}]}
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="FROZEN_PUBLIC_RECEIPT_REQUIRES_NEW_VERSION"):
        producer.write_files({"new.json": b"new", "receipt.json": b"changed"})
    assert (tmp_path / "receipt.json").read_bytes() == original
    assert not (tmp_path / "new.json").exists()
    producer.write_files({"receipt.json": original})
    (tmp_path / "receipt.json").write_bytes(b"corrupted")
    with pytest.raises(ValueError, match="FROZEN_PUBLIC_RECEIPT_CHANGED_ON_DISK"):
        producer.write_files({"receipt.json": original})
    assert (tmp_path / "receipt.json").read_bytes() == b"corrupted"


def test_public_receipt_preserves_closed_scope_and_all_original_pins() -> None:
    original = source_receipt()
    published = json.loads((ROOT / PUBLIC).read_bytes())
    assert published["source_status"] == original["status"]
    assert published["source_created_at_utc"] == original["created_at_utc"]
    assert published["original_receipt"]["original_sha256"] == SOURCE_SHA256
    assert public_path(SOURCE) == ROOT / PUBLIC
    assert original_path(SOURCE) != public_path(SOURCE)
    assert len(published["references"]) == published["source_reference_count"] == 25
    expected = {
        hashlib.sha256(path.replace("\\", "/").encode("utf-8")).hexdigest(): digest
        for path, digest in original["hashes"].items()
    }
    assert {
        row["source_identity_sha256"]: row["original_sha256"] for row in published["references"]
    } == expected
    assert published["historical_audit_scope"] == {
        key: original[key] for key in published["historical_audit_scope"]
    }
    assert set(published["historical_audit_scope"]) == {
        "prospective_data_reads",
        "refits",
        "canonical_roundtrip_max_abs_error",
        "auditor_p_values_exactly_reproduced",
        "ridge_drift_cause_proven",
    }
    scope = published["publication_scope"]
    assert scope["part34_is_post_hoc"] is True
    assert all(value is False for key, value in scope.items() if key != "part34_is_post_hoc")


def test_public_hashes_are_distinct_and_withheld_sources_supply_no_bytes() -> None:
    published = producer.authenticated_frozen_public_receipt()
    assert published is not None
    private_id = hashlib.sha256(PRIVATE.encode("utf-8")).hexdigest()
    for entry in published["references"]:
        if entry["public_path"] is None:
            assert entry["public_sha256"] is None
            if entry["source_identity_sha256"] == private_id:
                assert entry["source_path"] is None
                assert entry["relation"] == "private_source_not_distributed"
            else:
                assert entry["relation"] == "source_not_distributed"
                assert not public_path(entry["source_path"]).exists()
        else:
            current = ROOT / entry["public_path"]
            current = archive.frozen_public_baseline_path(current, entry["public_sha256"])
            assert hashlib.sha256(current.read_bytes()).hexdigest() == entry["public_sha256"]
            if entry["relation"] == "original_bytes":
                assert entry["public_sha256"] == entry["original_sha256"]
            else:
                assert entry["relation"] == "public_derivative"
                assert entry["public_sha256"] != entry["original_sha256"]
    for path, data in rendered_files().items():
        assert b"\r" not in data
        assert (ROOT / path).read_bytes() == data
    digest, filename = (ROOT / PUBLIC_SIDECAR).read_text(encoding="utf-8").split()
    payload = (ROOT / PUBLIC).read_bytes()
    assert digest == hashlib.sha256(payload).hexdigest()
    assert digest == hashlib.sha256(payload.replace(b"\r\n", b"\n")).hexdigest()
    assert filename == Path(PUBLIC).name


@pytest.fixture
def frozen_methodology_reference(tmp_path, monkeypatch):
    logical = producer.METHODOLOGY
    active = tmp_path / logical
    active.parent.mkdir(parents=True)
    active.write_bytes(b"English translation: N = 419.\n")
    baseline = tmp_path / "docs/archive/public_refresh_baseline/ledger.md.original"
    baseline.parent.mkdir(parents=True)
    baseline.write_bytes(b"Original public ledger: N = 419.\n")
    expected = hashlib.sha256(baseline.read_bytes()).hexdigest()
    historical = "a" * 64
    record = {
        "archive_path": baseline.relative_to(tmp_path).as_posix(),
        "public_path": logical,
        "public_baseline_path": baseline.relative_to(tmp_path).as_posix(),
        "public_baseline_sha256": expected,
    }
    mapping = baseline.parent / "original_paths.json"
    mapping.write_text(json.dumps({logical: record}), encoding="utf-8")
    receipt = tmp_path / PUBLIC
    receipt.parent.mkdir(parents=True)
    receipt.write_text(
        json.dumps(
            {
                "references": [
                    {
                        "source_path": logical,
                        "public_path": logical,
                        "original_sha256": historical,
                        "public_sha256": expected,
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    registry = tmp_path / "data/FROZEN_ARTIFACTS.json"
    registry.parent.mkdir()
    registry.write_text(
        json.dumps(
            {
                "entries": [
                    {"path": PUBLIC, "sha256": hashlib.sha256(receipt.read_bytes()).hexdigest()}
                ]
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(producer, "ROOT", tmp_path)
    monkeypatch.setattr(archive, "ROOT", tmp_path)
    archive._paths.cache_clear()
    archive._redactions.cache_clear()
    yield active, baseline, receipt, mapping, record, historical, expected
    archive._paths.cache_clear()
    archive._redactions.cache_clear()


@pytest.mark.parametrize("mutation", ["baseline", "mapping"])
def test_frozen_methodology_baseline_and_mapping_fail_closed(
    frozen_methodology_reference, mutation
) -> None:
    active, baseline, _, mapping, record, historical, expected = frozen_methodology_reference
    assert producer.public_reference_sha256(producer.METHODOLOGY, active, historical) == expected
    if mutation == "baseline":
        baseline.write_bytes(b"Changed evidence: N = 420.\n")
        error = "FROZEN_PUBLIC_BASELINE_MUTATED"
    else:
        record["public_baseline_sha256"] = "0" * 64
        mapping.write_text(json.dumps({producer.METHODOLOGY: record}), encoding="utf-8")
        archive._paths.cache_clear()
        error = "FROZEN_PUBLIC_METHODOLOGY_REFERENCE_CHANGED"
    with pytest.raises(ValueError, match=error):
        producer.public_reference_sha256(producer.METHODOLOGY, active, historical)


def test_stored_receipt_is_authenticated_before_its_reference_is_used(
    frozen_methodology_reference, monkeypatch
) -> None:
    active, _, receipt, _, _, historical, _ = frozen_methodology_reference
    receipt.write_bytes(receipt.read_bytes() + b" ")

    def must_not_resolve(*args):
        raise AssertionError("Unauthenticated receipt reached the archive resolver")

    monkeypatch.setattr(archive, "frozen_public_baseline_path", must_not_resolve)
    with pytest.raises(ValueError, match="FROZEN_PUBLIC_RECEIPT_AUTHENTICATION_FAILED"):
        producer.public_reference_sha256(producer.METHODOLOGY, active, historical)


def test_methodology_translation_preserves_numbers_references_and_prior_decisions() -> None:
    receipt = json.loads(
        (ROOT / "artifacts/rp4_public_refresh/methodology_translation_v1.json").read_bytes()
    )
    old_bytes = (ROOT / receipt["original_public_baseline"]["path"]).read_bytes()
    new_bytes = (ROOT / receipt["logical_path"]).read_bytes()
    assert hashlib.sha256(old_bytes).hexdigest() == receipt["original_public_baseline"]["sha256"]
    assert hashlib.sha256(new_bytes).hexdigest() == receipt["english_sha256"]
    old, new = old_bytes.decode("utf-8"), new_bytes.decode("utf-8")
    before, original = old.split("128. **RP4:", 1)
    retained, translated = new.split("128. **RP4:", 1)
    assert before == retained
    numbers = r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?"
    assert re.findall(numbers, original) == re.findall(numbers, translated)
    assert len(re.findall(numbers, "128. **RP4:" + original)) == 131
    for pattern in (r"[0-9a-f]{64}", r"`[^`]*`", r"\]\([^)]*\)", r'<a id="[^"]+">'):
        assert re.findall(pattern, original) == re.findall(pattern, translated)
    assert "Phase 9 is withdrawn as a sealed cohort for RP4" in translated
    assert "**C10 is not\n       activated.**" in translated
    assert "does not remove prior exposure" in translated
    assert "does not establish new\n     independence" in translated
    archive.assert_historical_sha256(
        producer.METHODOLOGY, receipt["historical_source_pin_unchanged"]
    )
