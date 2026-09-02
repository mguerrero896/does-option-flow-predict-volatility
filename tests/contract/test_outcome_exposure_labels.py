"""The exposure label must fail closed without a materialized holdout date vector."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPT = REPO / "scripts" / "audit_successor_holdout_exposure_v1.py"
ARTIFACT = REPO / "artifacts" / "target_blind_v22" / "successor_holdout_exposure_v1.json"
ADDENDUM = REPO / "docs" / "pit_v22_claims_and_limitations_v3.md"

_spec = importlib.util.spec_from_file_location("successor_holdout_exposure", SCRIPT)
assert _spec is not None and _spec.loader is not None
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def _load() -> dict[str, object]:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def _self_sha(payload: dict[str, object]) -> str:
    body = {key: value for key, value in payload.items() if key != "audit_sha256"}
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def test_public_metadata_audit_is_reproducible_and_reads_no_outcomes() -> None:
    audit = _load()
    assert audit == _module.build_audit()
    assert audit["audit_sha256"] == _self_sha(audit)
    assert audit["status"] == "NO_VERIFICABLE_DATE_VECTOR_UNAVAILABLE"
    assert audit["read_guard"] == {
        "fresh_outcome_reads": 0,
        "sealed_cohort_reads": 0,
        "phase9_reads": 0,
        "c_cohort_reads": 0,
        "sealed_root_reads": 0,
    }
    assert audit["source_contract"]["holdout_session_dates"] is None
    assert audit["classification"]["reclassification_applied"] is False


def test_intersected_holdout_loses_confirmatory_mde_role_without_override() -> None:
    assert _module.mde_role_after_exposure(
        intersects_prior_read=True, explicit_override=False
    ) == "EXPLORATORY_DESCRIPTIVE"
    assert _module.mde_role_after_exposure(
        intersects_prior_read=True, explicit_override=True
    ) == "CONFIRMATORY_THRESHOLD"


def test_current_docs_disclose_the_failed_closed_exposure_audit() -> None:
    audit = _load()
    for path in (
        REPO / "README.md",
        REPO / "docs" / "threats_to_validity_matrix_v1.md",
        ADDENDUM,
    ):
        text = path.read_text(encoding="utf-8")
        assert "NO_VERIFICABLE_DATE_VECTOR_UNAVAILABLE" in text
    addendum = ADDENDUM.read_text(encoding="utf-8")
    assert audit["audit_sha256"] in addendum
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() in addendum
    assert SCRIPT.relative_to(REPO).as_posix() in (REPO / "scripts" / "README.md").read_text(
        encoding="utf-8"
    )
    assert ARTIFACT.relative_to(REPO).as_posix() in (REPO / "README.md").read_text(
        encoding="utf-8"
    )
