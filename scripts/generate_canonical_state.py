"""Generate the single machine-readable statement of current project state.

Emits data/CANONICAL_STATE.json and STATUS.md (both AUTO-GENERATED; never edit by
hand). A hermetic CI test regenerates the state and fails on ANY drift, so a
document claiming to be current cannot silently contradict the repository
(decision 63). Regenerate after every substantive change:

    uv run python scripts/generate_canonical_state.py
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
STATE_PATH = REPO / "data" / "CANONICAL_STATE.json"
STATUS_PATH = REPO / "STATUS.md"
CURRENT_RUN_ID = "rp2-v3-20260827-remediation3"
CURRENT_RUN = Path("artifacts") / "rp2_v3" / CURRENT_RUN_ID
PHASE8_DIR = Path("artifacts") / "phase8_bridge"
PHASE8_AUTHORIZATION = PHASE8_DIR / "owner_authorization_20260830_v1.json"
PHASE8_CUSTODY = PHASE8_DIR / "one_shot_custody_20260830_v3.json"
PHASE8_LAYOUT_RECOVERY = PHASE8_DIR / "layout_recovery_manifest_20260830_v1.json"
PHASE8_RECOVERY = PHASE8_DIR / "execution_recovery_20260830_v1.json"
PHASE8_RESULT = PHASE8_DIR / "result_20260830_v1.json"
PHASE8_DISPERSION_AUDIT = PHASE8_DIR / "dispersion_audit_20260830_v5.json"
PHASE8_ADDENDUM = Path("reports") / "phase8a_exploratory_bridge_addendum_v6.md"
TEXT_SUFFIXES = {".csv", ".json", ".jsonl", ".md", ".py", ".sql", ".txt", ".yaml", ".yml"}

AUTHORIZED_SOURCES = (
    "data/FROZEN_ARTIFACTS.json",
    "data/PUBLIC_METADATA_REDACTIONS.json",
    "data/PUBLIC_COMMIT_TRANSLATIONS.json",
    "artifacts/supabase_schema_audit_20260828.json",
    "data/GATED_DATA_POINTERS.json",
    "scripts/_gated_exclude_list.txt",
    ".github/workflows/ci.yml",
    "docs/methodology_decisions.md",
    "docs/model_naming_note_v1.md",
    "docs/ci_contract_v1.md",
    "docs/evidence_immutability_v1.md",
    "docs/provider_license_review_v1.md",
    (CURRENT_RUN / "run_manifest.json").as_posix(),
    (CURRENT_RUN / "scorecard.json").as_posix(),
    "docs/pit_v22_claims_and_limitations.md",
    "docs/rp2_v3/VERDICT.md",
    "docs/rp2_v3/SUPERSEDED_RESULTS.md",
    "docs/phase8_bridge_protocol_v2.md",
    "docs/phase9_academic_reporting_policy_v2.md",
    "artifacts/phase8_bridge/bridge_contract_v2.json",
    "artifacts/phase8_bridge/evaluator_freeze_v4.json",
    PHASE8_AUTHORIZATION.as_posix(),
    PHASE8_CUSTODY.as_posix(),
    PHASE8_LAYOUT_RECOVERY.as_posix(),
    PHASE8_RECOVERY.as_posix(),
    PHASE8_RESULT.as_posix(),
    PHASE8_DISPERSION_AUDIT.as_posix(),
    "artifacts/phase9/power_deadline_audit_v1.json",
    "reports/final_report_draft_v2.md",
    "reports/final_report_draft_v2.docx",
    PHASE8_ADDENDUM.as_posix(),
)


def _sha(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix.lower() in TEXT_SUFFIXES:
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def _canonical_sha(payload: dict[str, Any], *, omit: str) -> str:
    body = {key: value for key, value in payload.items() if key != omit}
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_state() -> dict[str, Any]:
    """Assemble the canonical state from the authorized sources only."""
    frozen = json.loads((REPO / "data" / "FROZEN_ARTIFACTS.json").read_text(encoding="utf-8"))
    frozen_present = sum(
        1 for entry in frozen["entries"] if (REPO / str(entry["path"])).is_file()
    )
    redactions = json.loads(
        (REPO / "data" / "PUBLIC_METADATA_REDACTIONS.json").read_text(encoding="utf-8")
    )
    supabase_state = json.loads(
        (REPO / "artifacts" / "supabase_schema_audit_20260828.json").read_text(
            encoding="utf-8"
        )
    )
    gated = json.loads((REPO / "data" / "GATED_DATA_POINTERS.json").read_text(encoding="utf-8"))
    manifest_path = REPO / CURRENT_RUN / "run_manifest.json"
    scorecard_path = REPO / CURRENT_RUN / "scorecard.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("run_id") != CURRENT_RUN_ID:
        raise ValueError(f"CANONICAL_RUN_ID_MISMATCH:{manifest.get('run_id')}!={CURRENT_RUN_ID}")
    translations = json.loads(
        (REPO / "data" / "PUBLIC_COMMIT_TRANSLATIONS.json").read_text(encoding="utf-8")
    )
    translation = next(
        entry for entry in translations["entries"] if entry["run_id"] == CURRENT_RUN_ID
    )
    if translation["recorded_code_commit"] != manifest.get("code_commit"):
        raise ValueError("CANONICAL_PUBLIC_COMMIT_TRANSLATION_MISMATCH")
    if translation.get("status") != "HISTORICAL_REFERENCES_NOT_REACHABLE_FROM_ROOT_RELEASE":
        raise ValueError("CANONICAL_PUBLIC_COMMIT_PROVENANCE_STATUS_INVALID")
    if "published_equivalent_commit" in translation:
        raise ValueError("CANONICAL_PUBLIC_COMMIT_REACHABILITY_OVERCLAIM")
    decisions_text = (REPO / "docs" / "methodology_decisions.md").read_text(encoding="utf-8")
    decision_numbers = [int(match) for match in re.findall(r"^(\d+)\.\s", decisions_text, re.M)]
    bridge_path = REPO / "artifacts" / "phase8_bridge" / "bridge_contract_v2.json"
    bridge = json.loads(bridge_path.read_text(encoding="utf-8"))
    bridge_evaluator_path = (
        REPO / "artifacts" / "phase8_bridge" / "evaluator_freeze_v4.json"
    )
    bridge_evaluator = json.loads(bridge_evaluator_path.read_text(encoding="utf-8"))
    bridge_authorization_path = REPO / PHASE8_AUTHORIZATION
    bridge_authorization = json.loads(
        bridge_authorization_path.read_text(encoding="utf-8")
    )
    bridge_custody_path = REPO / PHASE8_CUSTODY
    bridge_custody = json.loads(bridge_custody_path.read_text(encoding="utf-8"))
    bridge_layout_path = REPO / PHASE8_LAYOUT_RECOVERY
    bridge_layout = json.loads(bridge_layout_path.read_text(encoding="utf-8"))
    bridge_recovery_path = REPO / PHASE8_RECOVERY
    bridge_recovery = json.loads(bridge_recovery_path.read_text(encoding="utf-8"))
    bridge_result_path = REPO / PHASE8_RESULT
    bridge_result = json.loads(bridge_result_path.read_text(encoding="utf-8"))
    bridge_dispersion_path = REPO / PHASE8_DISPERSION_AUDIT
    bridge_dispersion = json.loads(bridge_dispersion_path.read_text(encoding="utf-8"))
    phase9_audit_path = REPO / "artifacts" / "phase9" / "power_deadline_audit_v1.json"
    phase9_audit = json.loads(phase9_audit_path.read_text(encoding="utf-8"))
    if bridge["read_gate"] != {
        "one_shot_authorization_required": True,
        "safe_to_open_or_evaluate_oos": False,
        "sealed_cohorts_read": 0,
    }:
        raise ValueError("PHASE8_BRIDGE_READ_GATE_DRIFT")
    if (
        bridge_evaluator["contract_sha256"] != bridge["contract_sha256"]
        or bridge_evaluator["sealed_cohorts_read"] != 0
    ):
        raise ValueError("PHASE8_BRIDGE_EVALUATOR_FREEZE_DRIFT")
    authorization_required = {
        "authorization_type": "PHASE8_BRIDGE_ONE_SHOT_READ",
        "protocol_id": bridge["protocol_id"],
        "contract_sha256": bridge["contract_sha256"],
        "authorize_read_and_evaluation": True,
        "sealed_cohorts_read_before": 0,
    }
    if any(
        bridge_authorization.get(key) != expected
        for key, expected in authorization_required.items()
    ):
        raise ValueError("PHASE8_BRIDGE_AUTHORIZATION_DRIFT")
    if (
        bridge_custody["authorization"]["authorization_id"]
        != bridge_authorization["authorization_id"]
        or bridge_custody["authorization"]["file_sha256"]
        != _sha(bridge_authorization_path)
        or bridge_custody["authorization"]["canonical_sha256"]
        != _canonical_sha(bridge_authorization, omit="__never__")
        or bridge_custody["access_ledger"]["read_count"] != 1
        or bridge_custody["sealed_cohorts_read_before"] != 0
        or bridge_custody["sealed_cohorts_read_after"] != 1
        or bridge_custody["reconciliation_classification"]
        != "POST_READ_RECONCILIATION_NO_SECOND_EXECUTION"
        or bridge_custody["owner_instruction_after_consumption"]["effect"]
        != "RECORDS_OWNER_INTENT_AND_CLASSIFICATION_NO_SECOND_EXECUTION"
        or bridge_custody["owner_instruction_after_consumption"][
            "received_after_claim"
        ]
        is not True
        or "statement" in bridge_custody["owner_instruction_after_consumption"]
        or bridge_custody["execution"]["closure_deviation"] is not True
        or bridge_custody["execution"]["recovery_script_in_frozen_closure"]
        is not False
        or bridge_custody["execution"]["second_execution_permitted"] is not False
    ):
        raise ValueError("PHASE8_BRIDGE_ONE_SHOT_CUSTODY_DRIFT")
    if (
        bridge_layout["status"] != "COMPLETE"
        or bridge_layout["session_count"] != 30
        or bridge_layout["sealed_cohorts_read"] != 1
        or bridge_layout["sealed_store_reopened"] is not False
        or bridge_custody["execution"]["layout_manifest_file_sha256"]
        != _sha(bridge_layout_path)
        or bridge_custody["execution"]["layout_manifest_canonical_sha256"]
        != bridge_layout["manifest_sha256"]
        or bridge_layout["manifest_sha256"]
        != _canonical_sha(bridge_layout, omit="manifest_sha256")
    ):
        raise ValueError("PHASE8_BRIDGE_LAYOUT_RECOVERY_DRIFT")
    if (
        bridge_recovery["status"] != "RESUME_COMPLETE"
        or bridge_recovery["initial_failure"] != "RP3_EVAL_NO_SESSIONS"
        or bridge_recovery["sealed_cohorts_read"] != 1
        or bridge_recovery["sealed_store_reopened"] is not False
        or bridge_recovery["recovery_sha256"]
        != _canonical_sha(bridge_recovery, omit="recovery_sha256")
        or bridge_custody["execution"]["recovery_file_sha256"]
        != _sha(bridge_recovery_path)
    ):
        raise ValueError("PHASE8_BRIDGE_EXECUTION_RECOVERY_DRIFT")
    if (
        bridge_result["status"] != "EXPLORATORY_BRIDGE_EVALUATION_COMPLETE"
        or bridge_result["claim_classification"]
        != "EXPLORATORY_DESCRIPTIVE_NOT_CONFIRMATORY"
        or bridge_result["contract_sha256"] != bridge["contract_sha256"]
        or bridge_result["sealed_cohorts_read"] != 1
        or bridge_result["confirmatory_promotion_allowed"] is not False
        or bridge_result["personal_paths_emitted"] is not False
        or bridge_result["secret_values_emitted"] is not False
        or bridge_result["evaluation"]["overall_classification"]
        != "MIXED_EXPLORATORY"
        or bridge_result["store_preflight"]
        != {"completed_count": 30, "records": 750, "sealed_cohorts_read": 0, "sessions": 30}
        or bridge_result["result_sha256"]
        != _canonical_sha(bridge_result, omit="result_sha256")
        or bridge_custody["output"]["result_file_sha256"] != _sha(bridge_result_path)
        or bridge_custody["output"]["forecast_cube_sha256"]
        != bridge_result["forecast_cube_sha256"]
        or bridge_recovery["result_sha256"] != bridge_result["result_sha256"]
        or bridge_recovery["forecast_cube_sha256"]
        != bridge_result["forecast_cube_sha256"]
    ):
        raise ValueError("PHASE8_BRIDGE_RESULT_DRIFT")
    if (
        bridge_dispersion["status"] != "COMPLETE_WITH_HISTORICAL_PRODUCER_UNRESOLVED"
        or bridge_dispersion["contract_sha256"] != bridge["contract_sha256"]
        or bridge_dispersion["source_identity"]["forecast_cube"]["sha256"]
        != bridge_result["forecast_cube_sha256"]
        or bridge_dispersion["source_identity"]["result"]["result_sha256"]
        != bridge_result["result_sha256"]
        or bridge_dispersion["checks"]["sealed_store_reopened"] is not False
        or bridge_dispersion["checks"]["second_evaluator_execution"] is not False
        or bridge_dispersion["checks"]["published_statistics_replayed_exactly"] is not True
        or bridge_dispersion["conclusion"]["delta_b1_holm_below_0_05_cells"] != 3
        or bridge_dispersion["conclusion"][
            "delta_b2_given_b1_holm_below_0_05_cells"
        ]
        != 0
        or bridge_dispersion["conclusion"][
            "delta_b2_given_b1_intervals_crossing_zero"
        ]
        != 4
        or bridge_dispersion["conclusion"]["aggregation_change_supported"] is not False
        or bridge_dispersion["audit_sha256"]
        != _canonical_sha(bridge_dispersion, omit="audit_sha256")
    ):
        raise ValueError("PHASE8_BRIDGE_DISPERSION_AUDIT_DRIFT")
    if (
        phase9_audit["endpoint"]
        != {"complete_sessions": 60, "scored_sessions": 36, "test_blocks": 3}
        or phase9_audit["read_gate"]
        != {"outcome_paths_read": [], "sealed_cohorts_read": 0}
    ):
        raise ValueError("PHASE9_POWER_DEADLINE_AUDIT_DRIFT")
    return {
        "schema_version": "canonical-state-v1.0",
        "note": (
            "AUTO-GENERATED by scripts/generate_canonical_state.py; never edit by hand. "
            "CI regenerates and fails on drift (decision 63)."
        ),
        "governance": {
            "latest_decision": max(decision_numbers),
            "decision_count": len(decision_numbers),
        },
        "frozen_evidence": {
            "registry": "data/FROZEN_ARTIFACTS.json",
            "artifact_count": len(frozen["entries"]),
            "physical_artifact_count": frozen_present,
            "external_custody_artifact_count": len(frozen["entries"]) - frozen_present,
            "registry_sha256": _sha(REPO / "data" / "FROZEN_ARTIFACTS.json"),
            "public_metadata_redactions": {
                "ledger": "data/PUBLIC_METADATA_REDACTIONS.json",
                "artifact_count": len(redactions["entries"]),
                "ledger_sha256": _sha(REPO / "data" / "PUBLIC_METADATA_REDACTIONS.json"),
            },
        },
        "gated_data": {
            "pointer_file": "data/GATED_DATA_POINTERS.json",
            "file_count": len(gated["files"]),
            "storage": gated["storage"],
        },
        "external_publication": {
            "supabase": {
                "schema_evidence": "artifacts/supabase_schema_audit_20260828.json",
                "status": supabase_state["verdict"],
                "writes": supabase_state["writes"],
            }
        },
        "active_protocols": [
            {
                "id": "phase8-prospective-bridge",
                "document": "docs/phase8_bridge_protocol_v2.md",
                "artifact": "artifacts/phase8_bridge/bridge_contract_v2.json",
                "sha256": _sha(bridge_path),
                "contract_sha256": bridge["contract_sha256"],
                "evaluator": {
                    "artifact": "artifacts/phase8_bridge/evaluator_freeze_v4.json",
                    "script": bridge_evaluator["evaluator"],
                    "sha256": _sha(bridge_evaluator_path),
                    "evaluator_sha256": bridge_evaluator["evaluator_sha256"],
                },
                "authorization": {
                    "artifact": PHASE8_AUTHORIZATION.as_posix(),
                    "authorization_id": bridge_authorization["authorization_id"],
                    "sha256": _sha(bridge_authorization_path),
                },
                "execution_recovery": {
                    "artifact": PHASE8_RECOVERY.as_posix(),
                    "initial_failure": bridge_recovery["initial_failure"],
                    "sealed_store_reopened": bridge_recovery["sealed_store_reopened"],
                    "sha256": _sha(bridge_recovery_path),
                },
                "result": {
                    "artifact": PHASE8_RESULT.as_posix(),
                    "claim_classification": bridge_result["claim_classification"],
                    "confirmatory_promotion_allowed": bridge_result[
                        "confirmatory_promotion_allowed"
                    ],
                    "overall_classification": bridge_result["evaluation"][
                        "overall_classification"
                    ],
                    "result_sha256": bridge_result["result_sha256"],
                    "sha256": _sha(bridge_result_path),
                },
                "dispersion_audit": {
                    "artifact": PHASE8_DISPERSION_AUDIT.as_posix(),
                    "aggregation_change_supported": bridge_dispersion["conclusion"][
                        "aggregation_change_supported"
                    ],
                    "delta_b1_holm_below_0_05_cells": bridge_dispersion["conclusion"][
                        "delta_b1_holm_below_0_05_cells"
                    ],
                    "delta_b2_given_b1_holm_below_0_05_cells": bridge_dispersion[
                        "conclusion"
                    ]["delta_b2_given_b1_holm_below_0_05_cells"],
                    "sha256": _sha(bridge_dispersion_path),
                    "audit_sha256": bridge_dispersion["audit_sha256"],
                },
                "state": (
                    "EXPLORATORY_BRIDGE_EVALUATION_COMPLETE_WITH_RECORDED_RECOVERY_"
                    "AND_DISPERSION_AUDIT"
                ),
                "sealed_cohorts_read": 1,
            },
            {
                "id": "phase9-total-contribution",
                "document": "docs/phase9_total_contribution_protocol_v1.md",
                "sha256": _sha(REPO / "docs" / "phase9_total_contribution_protocol_v1.md"),
                "state": (
                    "frozen; collection active for sessions strictly after 2026-08-18, "
                    "60 complete/36 scored sessions, evaluation authorization ~Nov 2026; ongoing "
                    "prospective follow-up, not an academic submission gate"
                ),
                "academic_reporting": {
                    "document": "docs/phase9_academic_reporting_policy_v2.md",
                    "state": "ONGOING_NOT_SUBMISSION_GATE_POWER_CORRECTED",
                    "planning_audit": {
                        "artifact": "artifacts/phase9/power_deadline_audit_v1.json",
                        "sha256": _sha(phase9_audit_path),
                        "audit_sha256": phase9_audit["audit_sha256"],
                        "endpoint_complete_sessions": 60,
                        "endpoint_scored_sessions": 36,
                    },
                    "sealed_cohorts_read": 0,
                },
            },
        ],
        "scientific_bundle": {
            "run_id": CURRENT_RUN_ID,
            "manifest": {
                "path": (CURRENT_RUN / "run_manifest.json").as_posix(),
                "sha256": _sha(manifest_path),
                "scientific_sha256": str(manifest["scientific_sha256"]),
            },
            "historical_code_provenance": translation,
            "scorecard": {
                "path": (CURRENT_RUN / "scorecard.json").as_posix(),
                "sha256": _sha(scorecard_path),
            },
            "verdict": {
                "path": "docs/rp2_v3/VERDICT.md",
                "sha256": _sha(REPO / "docs" / "rp2_v3" / "VERDICT.md"),
                "status": "HISTORICAL_MEASUREMENT_NOT_CURRENT_CLAIM",
            },
            "superseded_register": {
                "path": "docs/rp2_v3/SUPERSEDED_RESULTS.md",
                "sha256": _sha(REPO / "docs" / "rp2_v3" / "SUPERSEDED_RESULTS.md"),
            },
            "eligibility": {
                "status": "REBUILD_COMPLETE_PIT_V22_BLOCKED",
                "reasons": [
                    "PIT_V22_RECONCILIATION_BLOCKED",
                ],
                "safe_to_reconcile_existing_results": False,
                "safe_to_open_or_evaluate_oos": False,
                "model_fit_after_pit_v22": False,
            },
        },
        "canonical_results": {
            "status": "NO_CURRENT_ELIGIBLE_RESULT",
            "headline_claims": [],
        },
        "current_report": {
            "source": {
                "path": "reports/final_report_draft_v2.md",
                "sha256": _sha(REPO / "reports" / "final_report_draft_v2.md"),
            },
            "submission_rendering": {
                "path": "reports/final_report_draft_v2.docx",
                "sha256": _sha(REPO / "reports" / "final_report_draft_v2.docx"),
            },
            "phase8_addendum": {
                "path": PHASE8_ADDENDUM.as_posix(),
                "sha256": _sha(REPO / PHASE8_ADDENDUM),
            },
            "evidence_cutoff": "2026-08-28",
        },
        "future_campaigns": [
            (
                "Phase 9 requires 60 complete (36 scored), previously unseen sessions and "
                "a separate read gate; academic submission does not wait for its outcome"
            ),
        ],
        "ci": {
            "contract": "docs/ci_contract_v1.md",
            "required_checks": ["quality", "hermetic", "scientific-contracts"],
            "coverage_min_percent": 80,
            "tier2_runner": "scripts/run_local_evidence_gates.py",
            "publish_gate": "scripts/publish_mirror.sh refuses to push unless tier-2 passes",
        },
        "authorized_sources": {source: _sha(REPO / source) for source in AUTHORIZED_SOURCES},
    }


def render_status(state: dict[str, Any]) -> str:
    """Human-readable rendering of the same state."""
    lines = [
        "# STATUS — canonical project state",
        "",
        "> AUTO-GENERATED from `data/CANONICAL_STATE.json` by",
        "> `scripts/generate_canonical_state.py`. Never edit by hand; CI fails on drift.",
        "> This file supersedes any narrative document that disagrees with it.",
        "",
        f"- Governance: decision {state['governance']['latest_decision']} is the latest "
        f"({state['governance']['decision_count']} recorded).",
        f"- Frozen evidence: {state['frozen_evidence']['artifact_count']} artifacts registered; "
        f"{state['frozen_evidence']['physical_artifact_count']} are present in this release and "
        f"{state['frozen_evidence']['external_custody_artifact_count']} remain gated or withdrawn "
        "with their digests preserved in `data/FROZEN_ARTIFACTS.json`.",
        f"- Public metadata redactions: "
        f"{state['frozen_evidence']['public_metadata_redactions']['artifact_count']} frozen "
        "artifacts retain original and redacted SHA-256 custody in "
        "`data/PUBLIC_METADATA_REDACTIONS.json`.",
        f"- Gated data: {state['gated_data']['file_count']} files in private storage "
        "(`data/GATED_DATA_POINTERS.json`).",
        f"- Supabase publication: **{state['external_publication']['supabase']['status']}** "
        f"({state['external_publication']['supabase']['writes']['schema_migrations_committed']} "
        "schema migrations, "
        f"{state['external_publication']['supabase']['writes']['catalog_syncs_committed']} "
        "catalog reconciliation, and "
        f"{state['external_publication']['supabase']['writes']['dataset_loads_committed']} "
        "dataset manifests committed; sealed reads: Phase 8 = 1, Phase 9 = 0).",
        "",
        "## Active protocols",
        "",
    ]
    for protocol in state["active_protocols"]:
        document = f" — `{protocol['document']}`" if protocol.get("document") else ""
        lines.append(f"- **{protocol['id']}**{document}: {protocol['state']}")
    bundle = state["scientific_bundle"]
    eligibility = bundle["eligibility"]
    lines += [
        "",
        "## Current scientific bundle",
        "",
        f"- Run: `{bundle['run_id']}`.",
        f"- Scientific hash: `{bundle['manifest']['scientific_sha256']}`.",
        "- Historical code provenance: recorded run commit "
        f"`{bundle['historical_code_provenance']['recorded_code_commit'][:12]}` and "
        "the pre-root sanitization audit are external references; neither is claimed "
        "reachable from this root-only public release.",
        f"- Eligibility: **{eligibility['status']}**.",
        f"- Blocking reasons: {', '.join(eligibility['reasons'])}.",
        "- Current eligible headline results: none.",
        "- Historical measurements remain traceable in "
        "`docs/rp2_v3/SUPERSEDED_RESULTS.md`; they are not current claims.",
        "- Current academic report: `reports/final_report_draft_v2.md` with the Word "
        "submission rendering pinned under `current_report` in the machine state.",
        "- Post-cutoff Phase 8A result: "
        "`reports/phase8a_exploratory_bridge_addendum_v6.md`.",
    ]
    lines += ["", "## Future campaigns", ""]
    for campaign in state["future_campaigns"]:
        lines.append(f"- {campaign}")
    lines += [
        "",
        "## CI",
        "",
        f"- Required checks: {', '.join(state['ci']['required_checks'])} "
        f"(coverage >= {state['ci']['coverage_min_percent']}%).",
        f"- Tier 2 (licensed evidence): `{state['ci']['tier2_runner']}`; "
        f"{state['ci']['publish_gate']}.",
    ]
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    state = build_state()
    STATE_PATH.write_text(
        json.dumps(state, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    STATUS_PATH.write_text(render_status(state), encoding="utf-8", newline="\n")
    commit = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True, cwd=REPO
    ).stdout.strip()
    print(f"[state] wrote {STATE_PATH.name} + STATUS.md (at commit {commit})")


if __name__ == "__main__":
    main()
