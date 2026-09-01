"""Phase 5 session and canonical-hash contracts."""

from __future__ import annotations

import importlib
from datetime import date, timedelta
from pathlib import Path

import pytest

EXPECTED_HOLDOUT = [
    "2026-07-20",
    "2026-07-21",
    "2026-07-22",
    "2026-07-23",
    "2026-07-24",
    "2026-07-27",
    "2026-07-28",
    "2026-07-29",
    "2026-07-30",
    "2026-07-31",
]


def _study_design() -> object:
    return importlib.import_module("mds650.study_design")


def test_build_study_sessions_uses_exact_xnys_development_window() -> None:
    result = _study_design().build_study_sessions("XNYS", date(2026, 7, 17), 80, 10)

    assert len(result["development"]) == 80
    assert result["development"][0] == "2026-03-24"
    assert result["development"][-1] == "2026-07-17"
    assert "2026-06-19" not in result["development"]
    assert "2026-07-03" not in result["development"]


def test_build_study_sessions_reserves_exact_prospective_holdout() -> None:
    result = _study_design().build_study_sessions("XNYS", date(2026, 7, 17), 80, 10)

    assert result["holdout"] == EXPECTED_HOLDOUT


def test_build_study_sessions_returns_unique_disjoint_sets() -> None:
    result = _study_design().build_study_sessions("XNYS", date(2026, 7, 17), 80, 10)

    assert len(result["development"]) == len(set(result["development"]))
    assert len(result["holdout"]) == len(set(result["holdout"]))
    assert set(result["development"]).isdisjoint(result["holdout"])


def test_build_study_sessions_rejects_nonpositive_counts() -> None:
    with pytest.raises(ValueError, match="SESSION_COUNT_MUST_BE_POSITIVE"):
        _study_design().build_study_sessions("XNYS", date(2026, 7, 17), 0, 10)


def test_canonical_sha256_is_key_order_independent() -> None:
    left = {"b": [2, 1], "a": {"x": True}}
    right = {"a": {"x": True}, "b": [2, 1]}

    assert _study_design().canonical_sha256(left) == _study_design().canonical_sha256(right)


def test_source_sha256_is_line_ending_independent(tmp_path: Path) -> None:
    posix = tmp_path / "posix.py"
    windows = tmp_path / "windows.py"
    posix.write_bytes(b"first\nsecond\n")
    windows.write_bytes(b"first\r\nsecond\r\n")

    assert _study_design().source_sha256(posix) == _study_design().source_sha256(windows)


def test_build_study_sessions_rejects_non_session_end() -> None:
    """A weekend cannot silently become the terminal development session."""
    with pytest.raises(ValueError, match="DEVELOPMENT_END_NOT_SESSION"):
        _study_design().build_study_sessions("XNYS", date(2026, 7, 18), 80, 10)


@pytest.mark.parametrize(
    ("sessions", "error"),
    [
        ({"development": [], "holdout": ["2026-01-02"]}, "STUDY_SESSION_COUNT_INVALID"),
        (
            {"development": ["2026-01-02", "2026-01-02"], "holdout": ["2026-01-03"]},
            "STUDY_SESSION_ORDER_OR_DUPLICATE_INVALID",
        ),
        (
            {"development": ["2026-01-02"], "holdout": ["2026-01-02"]},
            "DEVELOPMENT_HOLDOUT_OVERLAP",
        ),
    ],
)
def test_session_manifest_rejects_invalid_partitions(
    sessions: dict[str, list[str]], error: str
) -> None:
    """The frozen development/holdout partition must be populated, ordered and disjoint."""
    with pytest.raises(ValueError, match=error):
        _study_design().build_session_manifest(sessions)


@pytest.mark.parametrize(
    ("case", "error"),
    [
        ("hash", "SESSION_MANIFEST_HASH_MISMATCH"),
        ("count", "STUDY_SESSION_COUNT_INVALID"),
        ("provenance", "PREREGISTRATION_PROVENANCE_INVALID"),
    ],
)
def test_preregistration_rejects_unbound_manifest_or_provenance(case: str, error: str) -> None:
    """A preregistration cannot detach from its session partition or provenance."""
    module = _study_design()
    start = date(2026, 1, 1)
    manifest = module.build_session_manifest(
        {
            "development": [
                (start + timedelta(days=offset)).isoformat() for offset in range(80)
            ],
            "holdout": [
                (start + timedelta(days=offset)).isoformat() for offset in range(80, 90)
            ],
        }
    )
    provenance = {
        "branch": "codex/test",
        "commit": "a" * 40,
        "python_version": "3.12",
        "uv_lock_sha256": "b" * 64,
        "design_sha256": "c" * 64,
        "spec_kit_commit": "d" * 40,
        "worktree_dirty": False,
    }
    if case == "hash":
        manifest["manifest_sha256"] = "0" * 64
    elif case == "count":
        manifest["development_count"] = 79
        unsigned = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
        manifest["manifest_sha256"] = module.canonical_sha256(unsigned)
    else:
        provenance.pop("commit")

    with pytest.raises(ValueError, match=error):
        module.build_preregistration(manifest, provenance=provenance)


def test_freeze_json_rejects_corrupt_existing_manifest(tmp_path: Path) -> None:
    """A corrupt frozen file is reported, never treated as a writable destination."""
    path = tmp_path / "manifest.json"
    path.write_text("{not-json", encoding="utf-8")

    with pytest.raises(ValueError, match="FROZEN_MANIFEST_CORRUPTED"):
        _study_design().freeze_json(path, {"status": "FROZEN"})
