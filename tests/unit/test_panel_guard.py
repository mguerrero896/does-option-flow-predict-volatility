from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from tests import panel_guard


def _configure(monkeypatch: pytest.MonkeyPatch, root: Path, content: bytes) -> Path:
    relative = "artifacts/rp2_block4_b0/b0_panel.parquet"
    pointers = root / "artifacts/rp2_panel_pointers.json"
    pointers.parent.mkdir(parents=True)
    pointers.write_text(
        json.dumps(
            {
                "panels": {
                    relative: {
                        "bytes": len(content),
                        "sha256": hashlib.sha256(content).hexdigest(),
                    }
                }
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(panel_guard, "REPO", root)
    monkeypatch.setattr(panel_guard, "POINTERS", pointers)
    monkeypatch.delenv(panel_guard.PANEL_ROOT, raising=False)
    monkeypatch.delenv(panel_guard.OPT_OUT, raising=False)
    return root / relative


def test_declared_panel_requires_exact_bytes_and_hash(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _configure(monkeypatch, tmp_path, b"right")
    path.parent.mkdir(parents=True)
    path.write_bytes(b"wrong")
    with pytest.raises(pytest.fail.Exception, match="RP2_PANEL_SHA256_MISMATCH"):
        panel_guard.verified_panel_path("B0", path)


def test_panel_root_is_the_resolved_verified_custody(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    content = b"verified"
    path = _configure(monkeypatch, tmp_path / "repo", content)
    evidence = tmp_path / "evidence"
    resolved = evidence / path.relative_to(tmp_path / "repo")
    resolved.parent.mkdir(parents=True)
    resolved.write_bytes(content)
    monkeypatch.setenv(panel_guard.PANEL_ROOT, str(evidence))
    assert panel_guard.verified_panel_path("B0", path) == resolved


def test_wrong_size_fails_before_content_can_be_used(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = _configure(monkeypatch, tmp_path, b"expected")
    path.parent.mkdir(parents=True)
    path.write_bytes(b"short")
    with pytest.raises(pytest.fail.Exception, match="RP2_PANEL_SIZE_MISMATCH"):
        panel_guard.verified_panel_path("B0", path)
