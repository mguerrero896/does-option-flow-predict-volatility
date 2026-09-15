"""The public verification notebooks embed exactly the repository's aggregate files."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
NOTEBOOKS = [
    ROOT / "notebooks" / "quick_verification.ipynb",
    ROOT / "notebooks" / "extended_walkthrough.ipynb",
]
FORBIDDEN_TERMS = ("mds650", "capstone", "codex", "claude", "auditor", "sandbox", "docente")
MINIMUM_EMBEDDED_INPUTS = 13


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _code(notebook: dict) -> str:
    return "\n".join(
        "".join(cell["source"]) for cell in notebook["cells"] if cell["cell_type"] == "code"
    )


def _prose(notebook: dict) -> str:
    return "\n".join("".join(cell["source"]) for cell in notebook["cells"])


def _digests(raw: bytes) -> set[str]:
    # Windows checkouts may carry CRLF endings; the embedded copy uses the blob bytes.
    return {
        hashlib.sha256(raw).hexdigest(),
        hashlib.sha256(raw.replace(b"\r\n", b"\n")).hexdigest(),
    }


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.name)
def test_embedded_inputs_match_repository_files(path: Path) -> None:
    notebook = _load(path)
    match = re.search(r"PUBLIC_HASHES\s*=\s*\{(.*?)\}", _code(notebook), re.S)
    assert match is not None, "PUBLIC_HASHES declaration missing"
    pairs = re.findall(r"'([^']+\.(?:csv|json))'\s*:\s*'([0-9a-f]{64})'", match.group(1))
    assert len(pairs) >= MINIMUM_EMBEDDED_INPUTS
    for relative, digest in pairs:
        file = ROOT / relative
        assert file.is_file(), relative
        assert digest in _digests(file.read_bytes()), relative


@pytest.mark.parametrize("path", NOTEBOOKS, ids=lambda p: p.name)
def test_notebook_is_public_facing(path: Path) -> None:
    notebook = _load(path)
    assert notebook.get("nbformat") == 4
    lowered = _prose(notebook).lower()
    leaks = [term for term in FORBIDDEN_TERMS if term in lowered]
    assert not leaks, leaks
    ids = [cell["metadata"].get("id") for cell in notebook["cells"] if cell["cell_type"] == "code"]
    assert all(ids) and len(set(ids)) == len(ids)
    assert "PASS_PUBLIC_SAVED_RESULTS" in _code(notebook)
