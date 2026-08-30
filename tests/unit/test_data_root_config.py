"""Active data roots come from configuration, never a workstation drive literal."""

from __future__ import annotations

from pathlib import Path

import pytest

from mds650.config import (
    effective_data_root,
    production_data_root,
    provisional_data_root,
    rp2_store_root,
)


def test_data_root_aliases_are_explicit_and_portable(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    store = tmp_path / "store"
    monkeypatch.setenv("MDS650_DATA_ROOT", str(store / "data"))
    monkeypatch.setenv("MDS650_EXTERNAL_ROOT", str(tmp_path / "sandbox"))
    monkeypatch.setenv("MDS650_RP2_STORE_ROOT", str(tmp_path / "rp2"))

    assert production_data_root() == store
    assert effective_data_root() == tmp_path / "sandbox"
    assert rp2_store_root() == tmp_path / "rp2"


def test_missing_data_root_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("MDS650_DATA_ROOT", "MDS650_EXTERNAL_ROOT", "MDS650_RP2_STORE_ROOT"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(RuntimeError, match="MDS650_DATA_ROOT_REQUIRED"):
        production_data_root()
    assert provisional_data_root() == Path("<MDS650_DATA_ROOT_REQUIRED>")


def test_active_entrypoints_do_not_embed_the_workstation_drive() -> None:
    root = Path(__file__).resolve().parents[2]
    index = (root / "scripts" / "README.md").read_text(encoding="utf-8")
    table = index.split("## Frozen evidence", 1)[0]
    active = tuple(
        line.split("`", 2)[1]
        for line in table.splitlines()
        if line.startswith("| `scripts/")
    )
    required = {
        "scripts/generate_canonical_state.py",
        "scripts/run_rp2_v3_pipeline.py",
        "scripts/run_local_evidence_gates.py",
        "scripts/verify_scheduled_tasks.py",
        "scripts/phase9_collect.py",
        "scripts/phase9_verify.py",
    }
    assert required <= set(active)
    assert len(active) == len(set(active))

    offenders = [
        relative
        for relative in active
        if "d:/mds650" in (root / relative).read_text(encoding="utf-8").lower()
        or "d:\\mds650" in (root / relative).read_text(encoding="utf-8").lower()
    ]

    assert offenders == []
