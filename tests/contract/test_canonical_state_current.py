"""The generated canonical state must remain current, single and public-safe."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]

_spec = importlib.util.spec_from_file_location(
    "generate_canonical_state", REPO / "scripts" / "generate_canonical_state.py"
)
assert _spec is not None and _spec.loader is not None
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def test_state_file_matches_regeneration() -> None:
    committed = json.loads((REPO / "data" / "CANONICAL_STATE.json").read_text(encoding="utf-8"))
    fresh = _module.build_state()
    assert committed == fresh, (
        "CANONICAL_STATE.json is stale — run: uv run python scripts/generate_canonical_state.py"
    )


def test_status_md_matches_rendering() -> None:
    committed = (REPO / "STATUS.md").read_bytes().replace(b"\r\n", b"\n").decode("utf-8")
    fresh = _module.render_status(_module.build_state())
    assert committed == fresh, (
        "STATUS.md is stale — run: uv run python scripts/generate_canonical_state.py"
    )


def test_public_commit_provenance_does_not_claim_reachability() -> None:
    ledger = json.loads(
        (REPO / "data" / "PUBLIC_COMMIT_TRANSLATIONS.json").read_text(encoding="utf-8")
    )
    translation = ledger["entries"][0]
    assert translation["status"] == "HISTORICAL_REFERENCES_NOT_REACHABLE_FROM_ROOT_RELEASE"
    assert "published_equivalent_commit" not in translation
    assert len(translation["historical_sanitized_commit_reference"]) == 40


def test_scientific_bundle_is_single_and_fail_closed() -> None:
    state = json.loads((REPO / "data" / "CANONICAL_STATE.json").read_text(encoding="utf-8"))
    bundle = state["scientific_bundle"]

    assert bundle["run_id"] == "rp2-v3-20260831-b1-spot-cutoff-remediation"
    translation = bundle["historical_code_provenance"]
    manifest = json.loads((REPO / translation["manifest"]).read_text(encoding="utf-8"))
    assert translation["recorded_code_commit"] == manifest["code_commit"]
    assert translation["status"] == "RECORDED_COMMIT_REACHABLE_FROM_ROOT_RELEASE"
    assert translation["verification_scope"] == "GIT_ANCESTOR_OF_CANONICAL_STATE_COMMIT"
    assert bundle["manifest"]["scientific_sha256"] == (
        "033f2eb6be35e5db06aec2f9e01ef5f3379a8be68b0372087f24e40fa681bea4"
    )
    assert bundle["eligibility"]["status"] == "REBUILD_COMPLETE_PIT_V22_BLOCKED"
    assert bundle["eligibility"]["reasons"] == [
        "PIT_V22_RECONCILIATION_BLOCKED",
        "PIT_V22_SUCCESSOR_FAIL_CLOSED_PRE_OOS",
    ]
    assert state["canonical_results"] == {
        "status": "NO_CURRENT_ELIGIBLE_RESULT",
        "headline_claims": [],
    }
    successor = state["pit_v22_successor_evaluation"]
    assert successor["status"] == "FAIL_CLOSED_BEFORE_OOS_AUTHORIZATION"
    assert successor["failure_code"] == "RuntimeError:PIT_V22_TARGET_LINKAGE_INVALID"
    assert successor["evaluation_attempt_count"] == 1
    assert successor["oos_read_count"] == 0
    assert successor["results_inspected"] is False
    assert successor["rerun_allowed"] is False
    assert successor["development_mde_estimated"] is False
    assert successor["confirmatory_contrasts_evaluated"] is False
    assert successor["historical_bundle_aggregate_comparison_performed"] is False
    assert successor["scientific_result"] == {
        "exists": False,
        "eligible": False,
        "reason": "NO_RESULT_FAIL_CLOSED_PRE_OOS",
    }
    assert successor["full_log"]["sha256"] == (
        "33b04913e579fb4e429f0f1bf59e48c1b8c8a48dc39c22530a70acb5a1151169"
    )
    redactions = state["frozen_evidence"]["public_metadata_redactions"]
    assert redactions["ledger"] == "data/PUBLIC_METADATA_REDACTIONS.json"
    assert redactions["artifact_count"] == 14
    assert state["external_publication"]["supabase"] == {
        "schema_evidence": "artifacts/supabase_schema_audit_20260828.json",
        "status": (
            "NO_CURRENT_RESULTS_PUBLICATION_AND_DIRECT_DML_DISABLED_"
            "DATASET_REGISTRY_EXACT"
        ),
        "writes": {
            "schema_migrations_committed": 19,
            "catalog_syncs_committed": 1,
            "dataset_loads_committed": 6,
            "this_audit": 0,
        },
    }
    phase8 = next(
        protocol
        for protocol in state["active_protocols"]
        if protocol["id"] == "phase8-prospective-bridge"
    )
    assert phase8["state"] == (
        "EXPLORATORY_BRIDGE_EVALUATION_COMPLETE_WITH_RECORDED_RECOVERY_"
        "AND_DISPERSION_AUDIT_AND_POSTHOC_MATERIALIZED_REMEDIATION"
    )
    assert phase8["sealed_cohorts_read"] == 1
    assert phase8["result"]["artifact"] == (
        "artifacts/phase8_bridge/result_20260830_v1.json"
    )
    assert phase8["result"]["overall_classification"] == "MIXED_EXPLORATORY"
    assert phase8["result"]["confirmatory_promotion_allowed"] is False
    assert phase8["dispersion_audit"]["artifact"] == (
        "artifacts/phase8_bridge/dispersion_audit_20260831_v11.json"
    )
    assert phase8["dispersion_audit"]["aggregation_change_supported"] is False
    assert phase8["dispersion_audit"]["delta_b1_holm_below_0_05_cells"] == 3
    assert phase8["dispersion_audit"]["delta_b2_given_b1_holm_below_0_05_cells"] == 0
    remediation = phase8["posthoc_materialized_remediation"]
    assert remediation["historical_result_preserved"] is True
    assert remediation["new_sessions_collected"] == 0
    assert remediation["sealed_cohorts_read"] == 0
    assert remediation["sealed_store_reopened"] is False
    assert remediation["result"]["claim_classification"] == (
        "POST_HOC_REMEDIATION_SENSITIVITY_NOT_CONFIRMATORY"
    )
    assert remediation["result"]["overall_classification"] == "MIXED_EXPLORATORY"
    assert remediation["result"]["primary_b1_inclusive_cells"] == 8
    assert remediation["result"]["primary_b1_inclusive_cells_improved"] == 1
    assert state["current_report"]["phase8_addendum"]["path"] == (
        "reports/phase8a_exploratory_bridge_addendum_v13.md"
    )
    assert state["current_report"]["evidence_cutoff"] == "2026-08-31"
    assert all("Phase 8" not in campaign for campaign in state["future_campaigns"])
    phase9 = next(
        protocol
        for protocol in state["active_protocols"]
        if protocol["id"] == "phase9-total-contribution"
    )
    reporting = phase9["academic_reporting"]
    assert reporting["document"] == "docs/phase9_academic_reporting_policy_v2.md"
    assert reporting["state"] == "ONGOING_NOT_SUBMISSION_GATE_POWER_CORRECTED"
    assert reporting["planning_audit"]["artifact"] == (
        "artifacts/phase9/power_deadline_audit_v1.json"
    )
    assert reporting["planning_audit"]["endpoint_complete_sessions"] == 60
    assert reporting["planning_audit"]["endpoint_scored_sessions"] == 36
    assert reporting["sealed_cohorts_read"] == 0


def test_generated_paths_are_platform_independent() -> None:
    state = _module.build_state()
    assert all("\\" not in path for path in state["authorized_sources"])


def test_generated_public_state_does_not_catalog_internal_working_material() -> None:
    state_text = (REPO / "data" / "CANONICAL_STATE.json").read_text(encoding="utf-8")
    status_text = (REPO / "STATUS.md").read_text(encoding="utf-8")
    for forbidden in (
        "reports/remaining_work",
        "internal working record",
        "AGENTS.md",
        "RP2_V3_MASTER_PLAN.md",
        "test_final_validation_handoff.py",
    ):
        assert forbidden not in state_text
        assert forbidden not in status_text


def test_citation_does_not_claim_an_unpublished_release() -> None:
    citation = (REPO / "CITATION.cff").read_text(encoding="utf-8")
    attributes = (REPO / ".gitattributes").read_text(encoding="utf-8")

    assert "\nversion:" not in citation
    assert "\ndate-released:" not in citation
    assert "evidence-freeze-2026-08-18" not in citation
    assert "*.cff text eol=lf" in attributes


def test_immutability_contract_records_the_current_release_anchor() -> None:
    contract = (REPO / "docs" / "evidence_immutability_v1.md").read_text(encoding="utf-8")
    layer6 = next(line for line in contract.splitlines() if line.startswith("| 6 |"))

    assert "`evidence-freeze-2026-08-30-phase8-dispersion`" in layer6
    assert "`8429f73933e378e3ad03572af44ed0d4f83c6c9b`" in layer6
    assert "103-entry registry asset" in layer6
    assert "SHA-256 `cf69c349671cd1cda636fdc4fb0c0c0a45e976d93a7563b82b64cd1befee9bad`" in layer6
    assert "both source archives resolve" in layer6
    assert "`evidence-freeze-2026-08-30`" in layer6
    assert "81-entry asset" in layer6
    assert "SHA-256 `e3337d0eb6703a6356c30fdf66867714dc7ffc9fd0f8bafb3e5c75c24382a571`" in layer6
    assert "Release ID `376899713`" in layer6
    assert "`evidence-freeze-2026-08-18` tag ref and source archives are absent" in layer6
    assert "Off-machine anchor through the 103-entry batch" in layer6
    assert "fresh release snapshot is pending" not in layer6
    assert "awaiting its release anchor" not in layer6
