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
import tomllib
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[1]
STATE_PATH = REPO / "data" / "CANONICAL_STATE.json"
STATUS_PATH = REPO / "STATUS.md"
CURRENT_RUN_ID = "rp2-v3-20260831-b1-spot-cutoff-remediation"
CURRENT_RUN = Path("artifacts") / "rp2_v3" / CURRENT_RUN_ID
PHASE8_DIR = Path("artifacts") / "phase8_bridge"
PHASE8_AUTHORIZATION = PHASE8_DIR / "owner_authorization_20260830_v1.json"
PHASE8_CUSTODY = PHASE8_DIR / "one_shot_custody_20260830_v3.json"
PHASE8_LAYOUT_RECOVERY = PHASE8_DIR / "layout_recovery_manifest_20260830_v1.json"
PHASE8_RECOVERY = PHASE8_DIR / "execution_recovery_20260830_v1.json"
PHASE8_RESULT = PHASE8_DIR / "result_20260830_v1.json"
PHASE8_DISPERSION_AUDIT = PHASE8_DIR / "dispersion_audit_20260831_v11.json"
PHASE8_REMEDIATION_CONTRACT = (
    PHASE8_DIR / "materialized_remediation_contract_20260831_v1.json"
)
PHASE8_REMEDIATION_WARMUP_AMENDMENT = (
    PHASE8_DIR / "materialized_remediation_contract_amendment_20260831_v1.json"
)
PHASE8_REMEDIATION_GRID_AMENDMENT = (
    PHASE8_DIR / "materialized_remediation_contract_amendment_20260831_v2.json"
)
PHASE8_REMEDIATION_RESULT = PHASE8_DIR / "materialized_remediation_20260831_v1.json"
PHASE8_ADDENDUM = Path("reports") / "phase8a_exploratory_bridge_addendum_v13.md"
UW_LATENCY_AGGREGATE = (
    Path("artifacts") / "gate5_pit" / "uw_latency_campaign_20260902_v1.json"
)
UW_LATENCY_STATE = (
    Path("artifacts") / "gate5_pit" / "uw_latency_campaign_state_20260902_v1.json"
)
UW_LATENCY_ANOMALY = (
    Path("artifacts") / "gate5_pit" / "uw_latency_anomaly_20260821_v1.json"
)
PIT_V22_DIR = Path("artifacts") / "target_blind_v22"
PIT_V22_PREREGISTRATION = PIT_V22_DIR / "next_confirmation_preregistration_v2.json"
PIT_V22_FREEZE = PIT_V22_DIR / "successor_method_freeze_v1.json"
PIT_V22_AUTHORIZATION = PIT_V22_DIR / "successor_owner_authorization_v1.json"
PIT_V22_LOG = PIT_V22_DIR / "successor_evaluation_run_v1.json"
PIT_V22_RESULT = PIT_V22_DIR / "successor_evaluation_result_v1.json"
PIT_V22_PREREGISTRATION_V2 = PIT_V22_DIR / "next_confirmation_preregistration_v3.json"
PIT_V22_FREEZE_V2 = PIT_V22_DIR / "successor_method_freeze_v2.json"
PIT_V22_AUTHORIZATION_V2 = PIT_V22_DIR / "successor_owner_authorization_v2.json"
PIT_V22_LOG_V2 = PIT_V22_DIR / "successor_evaluation_run_v2.json"
PIT_V22_RESULT_V2 = PIT_V22_DIR / "successor_evaluation_result_v2.json"
PIT_V22_CUSTODY_AUDIT_V2 = PIT_V22_DIR / "successor_custody_audit_v2.json"
PIT_V22_CLAIM_LEDGER_V2 = PIT_V22_DIR / "pit_v22_claim_ledger_v2.json"
PIT_V22_CLAIMS_DOC_V2 = Path("docs") / "pit_v22_claims_and_limitations_v2.md"
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
    UW_LATENCY_AGGREGATE.as_posix(),
    UW_LATENCY_STATE.as_posix(),
    UW_LATENCY_ANOMALY.as_posix(),
    "artifacts/rp2_v3/cumulative_loss_session_series_v1.json",
    "artifacts/local_evidence_gates/pr55_remediation_20260902_v1.json",
    PIT_V22_PREREGISTRATION.as_posix(),
    PIT_V22_FREEZE.as_posix(),
    PIT_V22_AUTHORIZATION.as_posix(),
    PIT_V22_LOG.as_posix(),
    PIT_V22_PREREGISTRATION_V2.as_posix(),
    PIT_V22_FREEZE_V2.as_posix(),
    PIT_V22_AUTHORIZATION_V2.as_posix(),
    PIT_V22_LOG_V2.as_posix(),
    PIT_V22_RESULT_V2.as_posix(),
    PIT_V22_CUSTODY_AUDIT_V2.as_posix(),
    PIT_V22_CLAIM_LEDGER_V2.as_posix(),
    PIT_V22_CLAIMS_DOC_V2.as_posix(),
    (CURRENT_RUN / "run_manifest.json").as_posix(),
    (CURRENT_RUN / "scorecard.json").as_posix(),
    "artifacts/target_blind_v22/pit_v22_claim_ledger_v1.json",
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
    PHASE8_REMEDIATION_CONTRACT.as_posix(),
    PHASE8_REMEDIATION_WARMUP_AMENDMENT.as_posix(),
    PHASE8_REMEDIATION_GRID_AMENDMENT.as_posix(),
    PHASE8_REMEDIATION_RESULT.as_posix(),
    "artifacts/phase9/power_deadline_audit_v1.json",
    "reports/final_report_draft_v2.md",
    "reports/final_report_draft_v2.docx",
    PHASE8_ADDENDUM.as_posix(),
)



def _enforced_coverage_floor() -> int:
    """Read the floor CI actually enforces instead of restating a remembered number.

    This value was hardcoded at 80 while CI moved to 90, so the machine-readable
    authority published a threshold no gate used. Deriving it from the same file pytest
    reads means the authority cannot drift from the rule again.
    """

    config = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    floor = config["tool"]["coverage"]["report"]["fail_under"]
    return int(floor)


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
    frozen_by_path = {str(entry["path"]): entry for entry in frozen["entries"]}
    for relative in (
        PIT_V22_PREREGISTRATION,
        PIT_V22_FREEZE,
        PIT_V22_AUTHORIZATION,
        PIT_V22_LOG,
    ):
        entry = frozen_by_path.get(relative.as_posix())
        if entry is None or entry.get("sha256") != _sha(REPO / relative):
            raise ValueError(f"PIT_V22_SUCCESSOR_FROZEN_ARTIFACT_DRIFT:{relative.as_posix()}")
    successor_preregistration = json.loads(
        (REPO / PIT_V22_PREREGISTRATION).read_text(encoding="utf-8")
    )
    successor_freeze = json.loads((REPO / PIT_V22_FREEZE).read_text(encoding="utf-8"))
    successor_authorization = json.loads(
        (REPO / PIT_V22_AUTHORIZATION).read_text(encoding="utf-8")
    )
    successor_log = json.loads((REPO / PIT_V22_LOG).read_text(encoding="utf-8"))
    successor_events = successor_log.get("events", [])
    successor_event_names = [event.get("event") for event in successor_events]
    successor_failure = successor_events[-1] if successor_events else {}
    if (
        successor_preregistration.get("preregistration_sha256")
        != _canonical_sha(successor_preregistration, omit="preregistration_sha256")
        or successor_freeze.get("provenance", {}).get("preregistration_sha256")
        != successor_preregistration.get("preregistration_sha256")
        or successor_authorization.get("contract_sha256") != _sha(REPO / PIT_V22_FREEZE)
        or successor_authorization.get("authorize_read_and_evaluation") is not True
        or successor_authorization.get("sealed_cohorts_read_before") != 0
        or successor_freeze.get("bound_panel_sha256")
        != successor_preregistration.get("bound_panel", {}).get("panel_sha256")
        or successor_freeze.get("bound_panel_rows") != 77_328
        or successor_freeze.get("bound_panel_common_complete_rows") != 62_266
        or successor_log.get("run_id") != "pit-v22-successor-evaluation-v1-20260901"
        or successor_event_names
        != ["ONE_SHOT_CLAIMED", "RUNTIME_PREREGISTRATION_FROZEN", "FAIL_CLOSED"]
        or successor_failure.get("error") != "RuntimeError:PIT_V22_TARGET_LINKAGE_INVALID"
        or successor_failure.get("rerun_allowed") is not False
        or (REPO / PIT_V22_RESULT).exists()
    ):
        raise ValueError("PIT_V22_SUCCESSOR_FAILURE_CUSTODY_DRIFT")
    for relative in (
        PIT_V22_PREREGISTRATION_V2,
        PIT_V22_FREEZE_V2,
        PIT_V22_AUTHORIZATION_V2,
        PIT_V22_LOG_V2,
        PIT_V22_RESULT_V2,
        PIT_V22_CUSTODY_AUDIT_V2,
        PIT_V22_CLAIM_LEDGER_V2,
        PIT_V22_CLAIMS_DOC_V2,
    ):
        entry = frozen_by_path.get(relative.as_posix())
        if entry is None or entry.get("sha256") != _sha(REPO / relative):
            raise ValueError(
                f"PIT_V22_SUCCESSOR_V2_FROZEN_ARTIFACT_DRIFT:{relative.as_posix()}"
            )
    successor_v2_preregistration = json.loads(
        (REPO / PIT_V22_PREREGISTRATION_V2).read_text(encoding="utf-8")
    )
    successor_v2_freeze = json.loads(
        (REPO / PIT_V22_FREEZE_V2).read_text(encoding="utf-8")
    )
    successor_v2_authorization = json.loads(
        (REPO / PIT_V22_AUTHORIZATION_V2).read_text(encoding="utf-8")
    )
    successor_v2_log = json.loads((REPO / PIT_V22_LOG_V2).read_text(encoding="utf-8"))
    successor_v2_result = json.loads(
        (REPO / PIT_V22_RESULT_V2).read_text(encoding="utf-8")
    )
    successor_v2_audit = json.loads(
        (REPO / PIT_V22_CUSTODY_AUDIT_V2).read_text(encoding="utf-8")
    )
    successor_v2_claims = json.loads(
        (REPO / PIT_V22_CLAIM_LEDGER_V2).read_text(encoding="utf-8")
    )
    successor_v2_events = [
        event.get("event") for event in successor_v2_log.get("events", [])
    ]
    expected_v2_events = [
        "ONE_SHOT_CLAIMED",
        "RUNTIME_PREREGISTRATION_FROZEN",
        "DEVELOPMENT_RV30_LINKED",
        "DEVELOPMENT_MDE_FROZEN",
        "OOS_AUTHORIZATION_CONSUMED",
        "OOS_RV30_LINKED_AND_VALIDATED",
        "TWO_EXPANDING_FOLDS_FORECAST",
        "EVALUATION_COMPLETE",
        "PRIMARY_PAYLOADS_CONTENT_ADDRESSED",
        "RESULT_WRITTEN",
        "LEDGER_CLOSED",
        "CLAIM_CLOSED",
    ]
    if (
        successor_v2_preregistration.get("preregistration_sha256")
        != _canonical_sha(successor_v2_preregistration, omit="preregistration_sha256")
        or successor_v2_freeze.get("provenance", {}).get("preregistration_sha256")
        != successor_v2_preregistration.get("preregistration_sha256")
        or successor_v2_authorization.get("contract_sha256")
        != _sha(REPO / PIT_V22_FREEZE_V2)
        or successor_v2_authorization.get("authorize_read_and_evaluation") is not True
        or successor_v2_authorization.get("sealed_cohorts_read_before") != 0
        or successor_v2_authorization.get("run_id")
        != "pit-v22-successor-evaluation-v2-20260902"
        or successor_v2_log.get("run_id") != successor_v2_authorization.get("run_id")
        or successor_v2_events != expected_v2_events
        or successor_v2_result.get("manifest_sha256")
        != _canonical_sha(successor_v2_result, omit="manifest_sha256")
        or successor_v2_result.get("status")
        != "SCIENTIFIC_EVALUATION_COMPLETE_PENDING_CUSTODY_VALIDATION"
        or successor_v2_result.get("evaluation_attempt_count") != 1
        or successor_v2_result.get("oos_read_count") != 1
        or successor_v2_result.get("evaluation", {}).get("decision")
        != "GLOBAL_EDGE_NOT_CONFIRMED"
        or successor_v2_result.get("target_linkage_excluded_origins") != 12
        or successor_v2_result.get("linked_common_complete_rows") != 62_254
        or successor_v2_result.get("personal_paths_emitted") is not False
        or successor_v2_result.get("secret_values_emitted") is not False
        or successor_v2_audit.get("audit_sha256")
        != _canonical_sha(successor_v2_audit, omit="audit_sha256")
        or successor_v2_audit.get("status")
        != "PASS_INDEPENDENT_POST_OOS_CUSTODY_AUDIT"
        or successor_v2_audit.get("evaluation_attempt_count") != 1
        or successor_v2_audit.get("oos_read_count") != 1
        or successor_v2_audit.get("result_file_sha256") != _sha(REPO / PIT_V22_RESULT_V2)
        or successor_v2_audit.get("full_log_file_sha256") != _sha(REPO / PIT_V22_LOG_V2)
        or len(successor_v2_audit.get("verified_content_addressed_payloads", {})) != 10
        or successor_v2_claims.get("ledger_sha256")
        != _canonical_sha(successor_v2_claims, omit="ledger_sha256")
        or successor_v2_claims.get("status")
        != "SCIENTIFIC_RESULT_ELIGIBLE_EDGE_NOT_CONFIRMED"
        or successor_v2_claims.get("custody_audit_sha256")
        != successor_v2_audit.get("audit_sha256")
        or successor_v2_claims.get("result_file_sha256")
        != successor_v2_audit.get("result_file_sha256")
        or successor_v2_claims.get("full_log_file_sha256")
        != successor_v2_audit.get("full_log_file_sha256")
        or successor_v2_claims.get("eligibility", {}).get("scientific_result_eligible")
        is not True
        or successor_v2_claims.get("eligibility", {}).get("edge_claim_eligible") is not False
        or successor_v2_claims.get("eligibility", {}).get("capital_go") is not False
        or successor_v2_claims.get("historical_bundle_comparison", {}).get(
            "historical_aggregate_count"
        )
        != 12
    ):
        raise ValueError("PIT_V22_SUCCESSOR_V2_CUSTODY_DRIFT")
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
    translation_status = translation.get("status")
    if translation_status == "HISTORICAL_REFERENCES_NOT_REACHABLE_FROM_ROOT_RELEASE":
        if "published_equivalent_commit" in translation:
            raise ValueError("CANONICAL_PUBLIC_COMMIT_REACHABILITY_OVERCLAIM")
    elif translation_status == "RECORDED_COMMIT_REACHABLE_FROM_ROOT_RELEASE":
        reachable = subprocess.run(
            ["git", "merge-base", "--is-ancestor", str(manifest["code_commit"]), "HEAD"],
            cwd=REPO,
            check=False,
        )
        if reachable.returncode != 0:
            raise ValueError("CANONICAL_RECORDED_COMMIT_NOT_REACHABLE")
    else:
        raise ValueError("CANONICAL_PUBLIC_COMMIT_PROVENANCE_STATUS_INVALID")
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
    remediation_contract_path = REPO / PHASE8_REMEDIATION_CONTRACT
    remediation_contract = json.loads(
        remediation_contract_path.read_text(encoding="utf-8")
    )
    remediation_warmup_path = REPO / PHASE8_REMEDIATION_WARMUP_AMENDMENT
    remediation_warmup = json.loads(remediation_warmup_path.read_text(encoding="utf-8"))
    remediation_grid_path = REPO / PHASE8_REMEDIATION_GRID_AMENDMENT
    remediation_grid = json.loads(remediation_grid_path.read_text(encoding="utf-8"))
    remediation_result_path = REPO / PHASE8_REMEDIATION_RESULT
    remediation_result = json.loads(remediation_result_path.read_text(encoding="utf-8"))
    phase9_audit_path = REPO / "artifacts" / "phase9" / "power_deadline_audit_v1.json"
    phase9_audit = json.loads(phase9_audit_path.read_text(encoding="utf-8"))
    uw_latency_aggregate = json.loads((REPO / UW_LATENCY_AGGREGATE).read_text(encoding="utf-8"))
    uw_latency_state = json.loads((REPO / UW_LATENCY_STATE).read_text(encoding="utf-8"))
    uw_latency_anomaly = json.loads((REPO / UW_LATENCY_ANOMALY).read_text(encoding="utf-8"))
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
        remediation_contract["status"]
        != "PRECOMMITTED_BEFORE_REMEDIATION_MEASUREMENT"
        or remediation_contract["claim_classification"]
        != "POST_HOC_REMEDIATION_SENSITIVITY_NOT_CONFIRMATORY"
        or remediation_contract["execution"]["new_sessions_collected"] != 0
        or remediation_contract["execution"]["sealed_cohorts_read"] != 0
        or remediation_contract["execution"]["sealed_store_reopened"] is not False
        or remediation_contract["decision_rules"]["confirmatory_promotion_allowed"]
        is not False
        or remediation_contract["decision_rules"]["historical_one_shot_result_preserved"]
        is not True
        or remediation_contract["contract_sha256"]
        != _canonical_sha(remediation_contract, omit="contract_sha256")
    ):
        raise ValueError("PHASE8_MATERIALIZED_REMEDIATION_CONTRACT_DRIFT")
    if (
        remediation_warmup["status"]
        != "PRECOMMITTED_BEFORE_FIRST_REMEDIATION_MODEL_FIT"
        or remediation_warmup["amends_contract_sha256"]
        != remediation_contract["contract_sha256"]
        or remediation_warmup["invariants"]["new_phase8_sessions_collected"] != 0
        or remediation_warmup["invariants"]["phase8_scoring_started_before_amendment"]
        is not False
        or remediation_warmup["invariants"]["target_or_forecast_read_from_warmup"]
        is not False
        or remediation_warmup["amendment_sha256"]
        != _canonical_sha(remediation_warmup, omit="amendment_sha256")
    ):
        raise ValueError("PHASE8_MATERIALIZED_REMEDIATION_WARMUP_DRIFT")
    if (
        remediation_grid["status"]
        != "PRECOMMITTED_BEFORE_FIRST_REMEDIATION_MODEL_FIT"
        or remediation_grid["amends_contract_sha256"]
        != remediation_contract["contract_sha256"]
        or remediation_grid["supersedes_amendment_sha256"]
        != remediation_warmup["amendment_sha256"]
        or remediation_grid["comparison_grid"]
        != {
            "historical_only_origins": 175,
            "historical_only_origin_minute": 30,
            "historical_rows": 11875,
            "paired_common_origins": 11700,
            "remediated_only_origins": 0,
            "remediated_rows": 11700,
        }
        or remediation_grid["invariants"]["b2_core_features_exact_on_paired_common_grid"]
        is not True
        or remediation_grid["invariants"]["rv30_exact_on_paired_common_grid"] is not True
        or remediation_grid["amendment_sha256"]
        != _canonical_sha(remediation_grid, omit="amendment_sha256")
    ):
        raise ValueError("PHASE8_MATERIALIZED_REMEDIATION_GRID_DRIFT")
    if (
        remediation_result["status"]
        != "POST_HOC_REMEDIATION_SENSITIVITY_COMPLETE"
        or remediation_result["claim_classification"]
        != "POST_HOC_REMEDIATION_SENSITIVITY_NOT_CONFIRMATORY"
        or remediation_result["confirmatory_promotion_allowed"] is not False
        or remediation_result["historical_result_preserved"] is not True
        or remediation_result["session_count"] != 30
        or remediation_result["new_sessions_collected"] != 0
        or remediation_result["sealed_cohorts_read"] != 0
        or remediation_result["sealed_store_reopened"] is not False
        or remediation_result["personal_paths_emitted"] is not False
        or remediation_result["secret_values_emitted"] is not False
        or remediation_result["bridge_contract_sha256"] != bridge["contract_sha256"]
        or remediation_result["contract_sha256"]
        != remediation_contract["contract_sha256"]
        or remediation_result["warmup_amendment_sha256"]
        != remediation_warmup["amendment_sha256"]
        or remediation_result["grid_amendment_sha256"]
        != remediation_grid["amendment_sha256"]
        or remediation_result["evaluation"]["overall_classification"]
        != "MIXED_EXPLORATORY"
        or remediation_result["forecast_comparison"]["global_label"] != "MIXED"
        or remediation_result["forecast_comparison"]["grid"]
        != {
            "historical_only_origins": 175,
            "historical_rows": 11875,
            "paired_common_origins": 11700,
            "remediated_only_origins": 0,
            "remediated_rows": 11700,
        }
        or remediation_result["forecast_comparison"]["rv30_exactly_equal_on_paired_grid"]
        is not True
        or remediation_result["b2_panel_negative_control"][
            "all_features_exact_on_paired_grid"
        ]
        is not True
        or remediation_result["forecast_comparison"]["primary_b1_inclusive_cells"] != 8
        or remediation_result["forecast_comparison"][
            "primary_b1_inclusive_cells_improved"
        ]
        != 1
        or remediation_result["result_sha256"]
        != _canonical_sha(remediation_result, omit="result_sha256")
    ):
        raise ValueError("PHASE8_MATERIALIZED_REMEDIATION_RESULT_DRIFT")
    if (
        phase9_audit["endpoint"]
        != {"complete_sessions": 60, "scored_sessions": 36, "test_blocks": 3}
        or phase9_audit["read_gate"]
        != {"outcome_paths_read": [], "sealed_cohorts_read": 0}
    ):
        raise ValueError("PHASE9_POWER_DEADLINE_AUDIT_DRIFT")
    if (
        uw_latency_aggregate.get("self_sha256")
        != _canonical_sha(uw_latency_aggregate, omit="self_sha256")
        or uw_latency_state.get("self_sha256")
        != _canonical_sha(uw_latency_state, omit="self_sha256")
        or uw_latency_anomaly.get("self_sha256")
        != _canonical_sha(uw_latency_anomaly, omit="self_sha256")
        or uw_latency_state.get("state") != "RECONCILED_PARTIAL"
        or uw_latency_state.get("counts")
        != {"collected": 12, "reconciled": 6, "unreconciled": 6}
        or uw_latency_state.get("claim_classification") != "PROXY_ONLY_CROSS_CHANNEL"
        or uw_latency_state.get("artifact_lifecycle", {}).get("policy")
        != "IMMUTABLE_DATED_SNAPSHOT"
        or uw_latency_state.get("safe_to_reconcile_existing_results") != "NO"
        or uw_latency_state.get("safe_to_open_or_evaluate_oos") != "NO"
        or uw_latency_state.get("aggregate", {}).get("path")
        != UW_LATENCY_AGGREGATE.as_posix()
        or uw_latency_state.get("aggregate", {}).get("self_sha256")
        != uw_latency_aggregate.get("self_sha256")
        or uw_latency_anomaly.get("classification")
        != "COLLECTOR_RESTART_REPLAY_DUPLICATION"
        or uw_latency_anomaly.get("campaign_disposition")
        != "EXCLUDE_LATENCY_KEEP_CONTRACT_SUPPORT"
        or uw_latency_aggregate.get("operational_latency", {})
        .get("by_ny_hour", {})
        .get("values", {})
        .get("9", {})
        .get("over_60_seconds", {})
        != {"count": 6, "rate": 6 / 406}
    ):
        raise ValueError("UW_LATENCY_CAMPAIGN_AUTHORITY_DRIFT")
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
        "uw_latency_campaign": {
            "state": uw_latency_state["state"],
            "counts": uw_latency_state["counts"],
            "claim_classification": uw_latency_state["claim_classification"],
            "state_artifact": UW_LATENCY_STATE.as_posix(),
            "state_self_sha256": uw_latency_state["self_sha256"],
            "aggregate_artifact": UW_LATENCY_AGGREGATE.as_posix(),
            "aggregate_self_sha256": uw_latency_aggregate["self_sha256"],
            "opening_receipt_hour": uw_latency_aggregate["operational_latency"][
                "by_ny_hour"
            ]["values"]["9"],
            "artifact_lifecycle": uw_latency_state["artifact_lifecycle"],
            "anomaly_artifact": UW_LATENCY_ANOMALY.as_posix(),
            "anomaly_classification": uw_latency_anomaly["classification"],
            "backfill": uw_latency_state["backfill"],
            "revision": uw_latency_state["revision"],
            "safe_to_reconcile_existing_results": uw_latency_state[
                "safe_to_reconcile_existing_results"
            ],
            "safe_to_open_or_evaluate_oos": uw_latency_state[
                "safe_to_open_or_evaluate_oos"
            ],
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
                "posthoc_materialized_remediation": {
                    "contract": {
                        "artifact": PHASE8_REMEDIATION_CONTRACT.as_posix(),
                        "contract_sha256": remediation_contract["contract_sha256"],
                        "sha256": _sha(remediation_contract_path),
                    },
                    "amendments": [
                        {
                            "artifact": PHASE8_REMEDIATION_WARMUP_AMENDMENT.as_posix(),
                            "amendment_sha256": remediation_warmup["amendment_sha256"],
                            "sha256": _sha(remediation_warmup_path),
                        },
                        {
                            "artifact": PHASE8_REMEDIATION_GRID_AMENDMENT.as_posix(),
                            "amendment_sha256": remediation_grid["amendment_sha256"],
                            "sha256": _sha(remediation_grid_path),
                        },
                    ],
                    "result": {
                        "artifact": PHASE8_REMEDIATION_RESULT.as_posix(),
                        "claim_classification": remediation_result[
                            "claim_classification"
                        ],
                        "overall_classification": remediation_result["evaluation"][
                            "overall_classification"
                        ],
                        "primary_b1_inclusive_cells": remediation_result[
                            "forecast_comparison"
                        ]["primary_b1_inclusive_cells"],
                        "primary_b1_inclusive_cells_improved": remediation_result[
                            "forecast_comparison"
                        ]["primary_b1_inclusive_cells_improved"],
                        "result_sha256": remediation_result["result_sha256"],
                        "sha256": _sha(remediation_result_path),
                    },
                    "historical_result_preserved": True,
                    "new_sessions_collected": 0,
                    "sealed_cohorts_read": 0,
                    "sealed_store_reopened": False,
                },
                "state": (
                    "EXPLORATORY_BRIDGE_EVALUATION_COMPLETE_WITH_RECORDED_RECOVERY_"
                    "AND_DISPERSION_AUDIT_AND_POSTHOC_MATERIALIZED_REMEDIATION"
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
        "pit_v22_successor_evaluation": {
            "run_id": successor_v2_log["run_id"],
            "status": "SCIENTIFIC_EVALUATION_COMPLETE_CUSTODY_VALIDATED",
            "decision": successor_v2_result["evaluation"]["decision"],
            "evaluation_attempt_count": 1,
            "oos_read_count": 1,
            "results_inspected": True,
            "rerun_allowed": False,
            "development_mde_estimated": True,
            "confirmatory_contrasts_evaluated": True,
            "historical_bundle_aggregate_comparison_performed": True,
            "previous_attempt": {
                "run_id": successor_log["run_id"],
                "status": "FAIL_CLOSED_BEFORE_OOS_AUTHORIZATION",
                "failure_code": successor_failure["error"],
                "evaluation_attempt_count": 1,
                "oos_read_count": 0,
                "rerun_allowed": False,
                "log": {
                    "path": PIT_V22_LOG.as_posix(),
                    "sha256": _sha(REPO / PIT_V22_LOG),
                },
            },
            "bound_target_free_panel": {
                "sha256": successor_v2_freeze["bound_panel_sha256"],
                "rows": successor_v2_freeze["bound_panel_rows"],
                "predictor_common_rows": successor_v2_freeze[
                    "bound_panel_common_complete_rows"
                ],
            },
            "signed_inputs": {
                "preregistration": {
                    "path": PIT_V22_PREREGISTRATION_V2.as_posix(),
                    "file_sha256": _sha(REPO / PIT_V22_PREREGISTRATION_V2),
                    "semantic_sha256": successor_v2_preregistration[
                        "preregistration_sha256"
                    ],
                },
                "method_freeze": {
                    "path": PIT_V22_FREEZE_V2.as_posix(),
                    "sha256": _sha(REPO / PIT_V22_FREEZE_V2),
                },
                "owner_authorization": {
                    "path": PIT_V22_AUTHORIZATION_V2.as_posix(),
                    "sha256": _sha(REPO / PIT_V22_AUTHORIZATION_V2),
                },
            },
            "full_log": {
                "path": PIT_V22_LOG_V2.as_posix(),
                "sha256": _sha(REPO / PIT_V22_LOG_V2),
                "events": successor_v2_events,
            },
            "scientific_result": {
                "exists": True,
                "eligible": True,
                "reason": "PASS_POST_OOS_CUSTODY_VALIDATION",
                "path": PIT_V22_RESULT_V2.as_posix(),
                "sha256": _sha(REPO / PIT_V22_RESULT_V2),
                "manifest_sha256": successor_v2_result["manifest_sha256"],
                "immutable_payload_status": successor_v2_result["status"],
            },
            "custody_audit": {
                "path": PIT_V22_CUSTODY_AUDIT_V2.as_posix(),
                "sha256": _sha(REPO / PIT_V22_CUSTODY_AUDIT_V2),
                "audit_sha256": successor_v2_audit["audit_sha256"],
                "status": successor_v2_audit["status"],
            },
            "claims_and_limitations": {
                "path": PIT_V22_CLAIM_LEDGER_V2.as_posix(),
                "sha256": _sha(REPO / PIT_V22_CLAIM_LEDGER_V2),
                "ledger_sha256": successor_v2_claims["ledger_sha256"],
                "markdown": PIT_V22_CLAIMS_DOC_V2.as_posix(),
            },
            "target_linkage": successor_v2_audit["target_linkage"],
            "registered_contrasts": successor_v2_claims["contrasts"],
            "historical_bundle_comparison": successor_v2_claims[
                "historical_bundle_comparison"
            ],
            "edge_claim_eligible": False,
            "capital_eligible": False,
            "capital_go": False,
            "research_only": True,
        },
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
                "status": "HISTORICAL_MEASUREMENT_NOT_CURRENT_CLAIM",
                "reasons": ["SUPERSEDED_BY_PIT_V22_SUCCESSOR_V2"],
                "safe_to_reconcile_existing_results": False,
                "safe_to_open_or_evaluate_oos": False,
                "model_fit_after_pit_v22": False,
            },
        },
        "canonical_results": {
            "status": "CURRENT_ELIGIBLE_SCIENTIFIC_RESULT_EDGE_NOT_CONFIRMED",
            "run_id": successor_v2_log["run_id"],
            "decision": successor_v2_result["evaluation"]["decision"],
            "result_sha256": _sha(REPO / PIT_V22_RESULT_V2),
            "scientific_result_eligible": True,
            "edge_claim_eligible": False,
            "capital_go": False,
            "headline_claims": [],
            "confirmatory_contrasts": successor_v2_claims["contrasts"][
                "gamma_glm_confirmatory"
            ],
            "robustness_contrasts": successor_v2_claims["contrasts"][
                "lightgbm_robustness"
            ],
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
            "evidence_cutoff": "2026-08-31",
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
            "coverage_min_percent": _enforced_coverage_floor(),
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
    uw_latency = state["uw_latency_campaign"]
    lines += [
        "",
        "## UW latency campaign",
        "",
        f"- Lifecycle: **{uw_latency['state']}** "
        f"({uw_latency['counts']['reconciled']}/{uw_latency['counts']['collected']} "
        "sessions reconciled).",
        f"- Claim boundary: **{uw_latency['claim_classification']}**; backfill and "
        "revision remain non-identifiable under the cross-channel design.",
        f"- State authority: `{uw_latency['state_artifact']}`.",
    ]
    successor = state["pit_v22_successor_evaluation"]
    gamma = successor["registered_contrasts"]["gamma_glm_confirmatory"]
    lightgbm = successor["registered_contrasts"]["lightgbm_robustness"]
    lines += [
        "",
        "## PIT v2.2 successor evaluation",
        "",
        f"- Status: **{successor['status']}**; decision: **{successor['decision']}**.",
        f"- One-shot custody: {successor['evaluation_attempt_count']} attempt, "
        f"{successor['oos_read_count']} OOS read, rerun allowed = "
        f"{str(successor['rerun_allowed']).lower()}.",
        "- Target linkage: development "
        f"{successor['target_linkage']['development_predictor_complete_origins']:,} -> "
        f"{successor['target_linkage']['development_eligible_origins']:,} "
        f"({successor['target_linkage']['development_excluded_origins']} excluded); all "
        f"{successor['target_linkage']['all_predictor_complete_origins']:,} -> "
        f"{successor['target_linkage']['all_eligible_origins']:,} "
        f"({successor['target_linkage']['all_excluded_origins']} excluded).",
        "- Gamma confirmatory `delta_b1v2`: "
        f"{gamma['delta_b1v2']['estimate']:.12g} "
        f"[{gamma['delta_b1v2']['ci_low']:.12g}, {gamma['delta_b1v2']['ci_high']:.12g}], "
        f"Holm p={gamma['delta_b1v2']['p_value_holm']:.12g}, "
        f"MDE={gamma['delta_b1v2']['training_mde']:.12g}, >=MDE=false.",
        "- Gamma confirmatory `delta_b2v2`: "
        f"{gamma['delta_b2v2']['estimate']:.12g} "
        f"[{gamma['delta_b2v2']['ci_low']:.12g}, {gamma['delta_b2v2']['ci_high']:.12g}], "
        f"Holm p={gamma['delta_b2v2']['p_value_holm']:.12g}, "
        f"MDE={gamma['delta_b2v2']['training_mde']:.12g}, >=MDE=false.",
        "- LightGBM robustness `delta_b1v2` / `delta_b2v2`: "
        f"{lightgbm['delta_b1v2']['estimate']:.12g} / "
        f"{lightgbm['delta_b2v2']['estimate']:.12g}; both are descriptive MDE references, "
        "not confirmatory promotion tests.",
        f"- Frozen result: `{successor['scientific_result']['path']}` "
        f"(SHA-256 `{successor['scientific_result']['sha256']}`).",
        f"- Frozen public log: `{successor['full_log']['path']}` "
        f"(SHA-256 `{successor['full_log']['sha256']}`).",
        "- Eligibility: scientific result = true after independent custody validation; "
        "edge claim = false, capital = false; "
        "`capital_go=false`, `RESEARCH_ONLY`, `NOT INVESTMENT ADVICE`.",
    ]
    bundle = state["scientific_bundle"]
    eligibility = bundle["eligibility"]
    provenance = bundle["historical_code_provenance"]
    if provenance["status"] == "RECORDED_COMMIT_REACHABLE_FROM_ROOT_RELEASE":
        provenance_line = (
            "- Code provenance: recorded run commit "
            f"`{provenance['recorded_code_commit'][:12]}` is reachable from this root "
            "release."
        )
    else:
        provenance_line = (
            "- Historical code provenance: recorded run commit "
            f"`{provenance['recorded_code_commit'][:12]}` and the pre-root sanitization "
            "audit are external references; neither is claimed reachable from this "
            "root-only public release."
        )
    lines += [
        "",
        "## Current scientific bundle",
        "",
        f"- Run: `{bundle['run_id']}`.",
        f"- Scientific hash: `{bundle['manifest']['scientific_sha256']}`.",
        provenance_line,
        f"- Eligibility: **{eligibility['status']}**.",
        f"- Disposition: {', '.join(eligibility['reasons'])}.",
        "- Current canonical scientific result: the PIT v2.2 successor-v2 result above; "
        "no edge headline is eligible because no registered estimate met its frozen MDE "
        "and the signed contract contained no binary edge-promotion rule.",
        "- Historical measurements remain traceable in "
        "`docs/rp2_v3/SUPERSEDED_RESULTS.md`; they are not current claims.",
        "- Current academic report: `reports/final_report_draft_v2.md` with the Word "
        "submission rendering pinned under `current_report` in the machine state.",
        "- Post-cutoff Phase 8A result: "
        f"`{PHASE8_ADDENDUM.as_posix()}`.",
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
