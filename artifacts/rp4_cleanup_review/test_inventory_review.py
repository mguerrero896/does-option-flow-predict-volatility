"""Synthetic metadata fixtures only; no scientific runtime imports."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from artifacts.rp4_cleanup_review import inventory_review as audit


def fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path]:
    root = tmp_path / "repository"
    stage = root / "artifacts/rp4_test"
    stage.mkdir(parents=True)
    timing = root / "artifacts/rp4_v4_b4/timing.csv"
    timing.parent.mkdir(parents=True)
    timing.write_text("horizon_minutes,window\n15,primary\n", encoding="utf-8")
    private = tmp_path / "private_output.json"
    private.write_text('{"closed": true}', encoding="utf-8")
    release = stage / "release.json"
    release.write_text("{}", encoding="utf-8")
    receipt = stage / "receipt.json"
    receipt.write_text(
        json.dumps(
            {
                "status": "COMPLETE",
                "exit_code": 0,
                "release_sha256": audit.sha(release),
                "artifacts_sha256": {str(private): audit.sha(private)},
                "evaluation_code_sha256": {},
                "commands": [],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(audit, "ROOT", root)
    monkeypatch.setattr(audit, "PINS", {"artifacts/rp4_test/receipt.json": audit.sha(receipt)})
    monkeypatch.setattr(audit, "RECEIPTS", (("rp4_test", "rp4_test/release.json"),))
    return receipt, private


def test_public_scope_explicitly_skips_private_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    fixture(tmp_path, monkeypatch)
    result = audit.verify(False)
    assert result["status"] == "PASS"
    assert result["private_hash_checks_skipped"] == 1
    assert result["model_fits"] == result["inference_runs"] == 0


def test_licensed_scope_detects_corrupted_result(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, private = fixture(tmp_path, monkeypatch)
    assert audit.verify(True)["status"] == "PASS"
    private.write_text('{"closed": false}', encoding="utf-8")
    assert audit.verify(True)["failures"] == ["rp4_test/result_00"]


def test_pinned_receipt_drift_fails_before_parsing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    receipt, _ = fixture(tmp_path, monkeypatch)
    receipt.write_text("not json", encoding="utf-8")
    assert audit.verify(True)["failures"] == ["artifacts/rp4_test/receipt.json"]


def test_deletion_is_not_implied_by_reference_owner() -> None:
    assert audit.artifact_owner("artifacts/rp4_test/receipt.json") == "rp4_test"
    assert audit.artifact_owner("docs/rp4/specification_v3.md") is None


def test_related_missing_repository_is_explicit(tmp_path: Path) -> None:
    result = audit.related_repository(tmp_path / "absent", "related_01")
    assert result["exists"] is False
    assert result["status"].startswith("NO VERIFICABLE")
    assert result["deletion_authorized"] is False
    assert str(tmp_path) not in json.dumps(result)
