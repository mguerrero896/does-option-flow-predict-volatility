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

    assert bundle["run_id"] == "rp2-v3-20260827-remediation3"
    translation = bundle["historical_code_provenance"]
    manifest = json.loads((REPO / translation["manifest"]).read_text(encoding="utf-8"))
    assert translation["recorded_code_commit"] == manifest["code_commit"]
    assert translation["status"] == "HISTORICAL_REFERENCES_NOT_REACHABLE_FROM_ROOT_RELEASE"
    assert len(translation["historical_sanitized_commit_reference"]) == 40
    assert len(translation["recorded_git_tree_sha1"]) == 40
    assert len(translation["retained_blobs_sha256"]) == 64
    assert translation["withdrawn_path_count"] == 5
    assert translation["withdrawn_path_classes"] == [
        "internal planning documents",
        "internal execution checklists",
        "internal handoff tests",
    ]
    assert bundle["manifest"]["scientific_sha256"] == (
        "386610a4908d601c1ad09688d8371cfa3fdd70e4e7ddf50c416e8d3b0907cb47"
    )
    assert bundle["eligibility"]["status"] == "REBUILD_COMPLETE_PIT_V22_BLOCKED"
    assert bundle["eligibility"]["reasons"] == ["PIT_V22_RECONCILIATION_BLOCKED"]
    assert state["canonical_results"] == {
        "status": "NO_CURRENT_ELIGIBLE_RESULT",
        "headline_claims": [],
    }
    redactions = state["frozen_evidence"]["public_metadata_redactions"]
    assert redactions["ledger"] == "data/PUBLIC_METADATA_REDACTIONS.json"
    assert redactions["artifact_count"] == 10
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
        "AND_DISPERSION_AUDIT"
    )
    assert phase8["sealed_cohorts_read"] == 1
    assert phase8["result"]["artifact"] == (
        "artifacts/phase8_bridge/result_20260830_v1.json"
    )
    assert phase8["result"]["overall_classification"] == "MIXED_EXPLORATORY"
    assert phase8["result"]["confirmatory_promotion_allowed"] is False
    assert phase8["dispersion_audit"]["artifact"] == (
        "artifacts/phase8_bridge/dispersion_audit_20260830_v8.json"
    )
    assert phase8["dispersion_audit"]["aggregation_change_supported"] is False
    assert phase8["dispersion_audit"]["delta_b1_holm_below_0_05_cells"] == 3
    assert phase8["dispersion_audit"]["delta_b2_given_b1_holm_below_0_05_cells"] == 0
    assert state["current_report"]["phase8_addendum"]["path"] == (
        "reports/phase8a_exploratory_bridge_addendum_v9.md"
    )
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


def test_immutability_contract_records_the_pending_freeze_batch_honestly() -> None:
    contract = (REPO / "docs" / "evidence_immutability_v1.md").read_text(encoding="utf-8")
    layer6 = next(line for line in contract.splitlines() if line.startswith("| 6 |"))

    assert "`evidence-freeze-2026-08-30`" in layer6
    assert "`908e35610e36558a163940a8586a4e1a22a62c20`" in layer6
    assert "81-entry registry asset" in layer6
    assert "SHA-256 `e3337d0eb6703a6356c30fdf66867714dc7ffc9fd0f8bafb3e5c75c24382a571`" in layer6
    assert "live registry adds the Phase 8 dispersion audits and addenda through v9" in layer6
    assert "fresh release snapshot is pending" in layer6
    assert "both source archives resolve" in layer6
    assert "Release ID `376899713`" in layer6
    assert "`evidence-freeze-2026-08-18` tag ref and source archives are absent" in layer6
    assert "current freeze batch awaiting its release anchor" in layer6
