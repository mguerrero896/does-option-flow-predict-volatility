"""Small regression checks for publication redaction and preserved custody."""

import hashlib
import io
import zipfile
from pathlib import Path

import pytest
from verify_delivery import safe_path, scan_payload, verify


def test_personal_path_scan_covers_json_and_zip() -> None:
    personal = "private-input/8545a81f99f36eda523c" + "Users/researcher/private"
    for value in (personal, personal.replace("/", "\\"), personal.replace("/", "\\\\")):
        with pytest.raises(ValueError, match="RP4_PUBLIC_PERSONAL_PATH"):
            scan_payload(value.encode(), "receipt.json")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("history.txt", personal)
    with pytest.raises(ValueError, match="RP4_PUBLIC_PERSONAL_PATH"):
        scan_payload(buffer.getvalue(), "history.zip")
    assert scan_payload(b"artifacts/rp4_b2/summary.json", "receipt.json") == 1


def test_projection_paths_cannot_escape(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="RP4_PROJECTION_PATH_ESCAPE"):
        safe_path(tmp_path, "../unrelated.txt")


def test_published_projection_and_results_are_pinned() -> None:
    root = Path(__file__).resolve().parents[2]
    result = verify(root)
    assert result["figure_endpoints_verified"] == 8
    assert result["models_fitted"] == 0
    assert result["original_checkout_verified"] is False
    expected = "77f7de950386f13b80800c78a77fba8f1db4c33a486217eea3d248d15bf02b26"
    assert hashlib.sha256((root / "docs/rp4/results_v1.md").read_bytes()).hexdigest() == expected
