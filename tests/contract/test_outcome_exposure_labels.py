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
    _module.verify_recorded(audit)
    assert audit["audit_sha256"] == _self_sha(audit)
    assert audit["status"] == "PASS_RETROSPECTIVE_EXPOSURE_VERIFIED"
    assert audit["read_guard"] == {
        "fresh_outcome_reads": 0,
        "sealed_cohort_outcome_reads": 0,
        "phase9_reads": 0,
        "c_cohort_reads": 0,
        "target_or_metric_columns_read": 0,
        "target_free_metadata_panel_reads": 1,
        "columns_read": ["common_predictor_complete", "session_date"],
    }
    assert audit["source_contract"]["registered_session_universe_count"] == 159
    assert audit["source_contract"]["splits"]["holdout"]["session_count"] == 32
    assert audit["source_contract"]["splits"]["holdout"]["start"] == "2026-02-05"
    assert audit["source_contract"]["splits"]["holdout"]["end"] == "2026-03-23"
    assert audit["classification"] == {
        "holdout_outcomes_previously_read": True,
        "reason": "HOLDOUT_OUTCOMES_PREVIOUSLY_READ_BY_C3_AND_RP2V3_D",
        "result_role": "RETROSPECTIVE_REMEASUREMENT_UNDER_PIT_V22",
        "evidential_status": "EXPLORATORY_DESCRIPTIVE",
        "mde_role": "EXPLORATORY_DESCRIPTIVE",
        "one_shot_label_scope": "CONTRACT_ACCESS_CUSTODY_ONLY",
        "reclassification_applied": True,
    }
    windows = audit["prior_outcome_read_windows"]
    assert windows["phase6_c3"]["holdout_intersection_count"] == 32
    assert windows["rp2_development"]["holdout_intersection_count"] == 32
    assert [item["holdout_intersection_count"] for item in windows["phase8"]] == [0, 0]


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
        REPO / "STATUS.md",
        REPO / "docs" / "threats_to_validity_matrix_v1.md",
        ADDENDUM,
    ):
        text = path.read_text(encoding="utf-8")
        assert "PASS_RETROSPECTIVE_EXPOSURE_VERIFIED" in text
    addendum = ADDENDUM.read_text(encoding="utf-8")
    assert audit["audit_sha256"] in addendum
    assert hashlib.sha256(ARTIFACT.read_bytes()).hexdigest() in addendum
    assert SCRIPT.relative_to(REPO).as_posix() in (REPO / "scripts" / "README.md").read_text(
        encoding="utf-8"
    )
    assert ARTIFACT.relative_to(REPO).as_posix() in (REPO / "README.md").read_text(
        encoding="utf-8"
    )
