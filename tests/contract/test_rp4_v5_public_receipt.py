"""The public Part 34 receipt preserves pins without relabelling derivatives."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from scripts import build_rp4_v5_public_receipt as producer
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
    (tmp_path / "data/FROZEN_ARTIFACTS.json").write_text(json.dumps({"entries": [{
        "path": "receipt.json", "sha256": hashlib.sha256(original).hexdigest()
    }]}), encoding="utf-8")
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
        row["source_identity_sha256"]: row["original_sha256"]
        for row in published["references"]
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
    published = json.loads((ROOT / PUBLIC).read_bytes())
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
