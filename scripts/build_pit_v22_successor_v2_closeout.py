"""Validate and publish the immutable PIT v2.2 successor-v2 closeout.

The private gated root is inspected only to reproduce custody hashes. Public outputs
contain logical paths, hashes, aggregate statistics and claim boundaries, never licensed
rows, personal paths or secrets.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "artifacts" / "target_blind_v22"
RUN_ID = "pit-v22-successor-evaluation-v2-20260902"
CONTRACT_SHA256 = "d803083ccbbaa23889db8ecae7fa5ed8323dc42cb8ae4613edcad5faa404dc40"
GATED_ROOT_PATH_SHA256 = "b0f7f75c38470bb9a6965c6187cf4814cfe8cf93109e18ca2c058e3b6a1bafb9"
RESULT = ARTIFACTS / "successor_evaluation_result_v2.json"
LOG = ARTIFACTS / "successor_evaluation_run_v2.json"
FREEZE = ARTIFACTS / "successor_method_freeze_v2.json"
AUTHORIZATION = ARTIFACTS / "successor_owner_authorization_v2.json"
RESOLUTION = ARTIFACTS / "target_source_discrepancy_resolution_v1.json"
HISTORICAL_SCORECARD = (
    ROOT / "artifacts" / "rp2_v3" / "rp2-v3-20260831-b1-spot-cutoff-remediation" / "scorecard.json"
)
AUDIT_OUTPUT = ARTIFACTS / "successor_custody_audit_v2.json"
LEDGER_OUTPUT = ARTIFACTS / "pit_v22_claim_ledger_v2.json"
MARKDOWN_OUTPUT = ROOT / "docs" / "pit_v22_claims_and_limitations_v2.md"

EXPECTED_EVENTS = [
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


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _canonical_sha256(payload: Mapping[str, Any], *, omit: str) -> str:
    body = {key: value for key, value in payload.items() if key != omit}
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _read_mapping(path: Path, error_code: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(error_code) from error
    if not isinstance(value, dict):
        raise ValueError(error_code)
    return value


def _require(condition: bool, error_code: str) -> None:
    if not condition:
        raise ValueError(error_code)


def _event(log: Mapping[str, Any], name: str) -> Mapping[str, Any]:
    events = log.get("events")
    if not isinstance(events, list):
        raise ValueError("PIT_V22_V2_CLOSEOUT_LOG_INVALID")
    match = next(
        (item for item in events if isinstance(item, Mapping) and item.get("event") == name),
        None,
    )
    if match is None:
        raise ValueError(f"PIT_V22_V2_CLOSEOUT_EVENT_MISSING:{name}")
    return match


def _contrast_summary(result: Mapping[str, Any]) -> dict[str, Any]:
    evaluation = result["evaluation"]
    global_results = evaluation["global"]
    annotations = result["mde_annotations"]
    output: dict[str, Any] = {}
    for role in ("gamma_glm_confirmatory", "lightgbm_robustness"):
        output[role] = {}
        for contrast in ("delta_b1v2", "delta_b2v2"):
            estimate = global_results[role][contrast]
            mde = annotations[role][contrast]
            output[role][contrast] = {
                "definition": estimate["definition"],
                "estimate": estimate["estimate"],
                "ci_low": estimate["ci_low"],
                "ci_high": estimate["ci_high"],
                "p_value_raw": estimate["p_value_raw"],
                "p_value_holm": estimate.get("p_value_holm"),
                "training_mde": mde["training_mde"],
                "estimate_at_least_mde": mde["estimate_at_least_mde"],
                "mde_role": mde["mde_role"],
                "result_sign": estimate["result_sign"],
                "observations": estimate["observations"],
                "clusters": estimate["clusters"],
            }
    return output


def _historical_comparison(
    result: Mapping[str, Any], scorecard: Mapping[str, Any]
) -> dict[str, Any]:
    historical = scorecard["forecast"]
    contrast_names = ("delta_b1", "delta_b2_given_b1")
    historical_count = sum(
        1
        for model in historical.values()
        for role in ("D", "V")
        for contrast in contrast_names
        if contrast in model[role]
    )
    _require(historical_count == 12, "PIT_V22_V2_HISTORICAL_CONTRAST_COUNT_INVALID")
    role_map = {
        "gamma_glm_confirmatory": "gamma_glm",
        "lightgbm_robustness": "lightgbm_qlike",
    }
    contrast_map = {"delta_b1v2": "delta_b1", "delta_b2v2": "delta_b2_given_b1"}
    comparable: list[dict[str, Any]] = []
    for new_role, old_role in role_map.items():
        for new_contrast, old_contrast in contrast_map.items():
            new_estimate = result["evaluation"]["global"][new_role][new_contrast]["estimate"]
            old_d = historical[old_role]["D"][old_contrast]
            old_v = historical[old_role]["V"][old_contrast]
            comparable.append(
                {
                    "new_model_role": new_role,
                    "new_contrast": new_contrast,
                    "new_estimate": new_estimate,
                    "historical_model": old_role,
                    "historical_development_estimate": old_d,
                    "historical_validation_estimate": old_v,
                    "sign_vs_historical_development": (
                        "SAME" if new_estimate * old_d > 0 else "DIFFERENT"
                    ),
                    "sign_vs_historical_validation": (
                        "SAME" if new_estimate * old_v > 0 else "DIFFERENT"
                    ),
                }
            )
    return {
        "historical_bundle_run_id": scorecard["run_id"],
        "historical_aggregate_count": historical_count,
        "comparison_scope": "DESCRIPTIVE_SIGN_CHECK_NOT_ONE_TO_ONE_REPLICATION",
        "direct_contradiction_disposition": (
            "NOT_IDENTIFIABLE_DIFFERENT_PARTITION_INFORMATION_SETS_AND_ESTIMANDS"
        ),
        "comparable_model_contrasts": comparable,
    }


def build_closeout(gated_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    """Reproduce private custody and return sanitized audit and claim ledgers."""
    resolved_root = gated_root.resolve()
    root_sha = hashlib.sha256(resolved_root.as_posix().casefold().encode()).hexdigest()
    _require(
        resolved_root.name == RUN_ID and root_sha == GATED_ROOT_PATH_SHA256,
        "PIT_V22_V2_CLOSEOUT_GATED_ROOT_INVALID",
    )
    result = _read_mapping(RESULT, "PIT_V22_V2_CLOSEOUT_RESULT_INVALID")
    log = _read_mapping(LOG, "PIT_V22_V2_CLOSEOUT_LOG_INVALID")
    freeze = _read_mapping(FREEZE, "PIT_V22_V2_CLOSEOUT_FREEZE_INVALID")
    authorization = _read_mapping(AUTHORIZATION, "PIT_V22_V2_CLOSEOUT_AUTHORIZATION_INVALID")
    resolution = _read_mapping(RESOLUTION, "PIT_V22_V2_CLOSEOUT_RESOLUTION_INVALID")
    scorecard = _read_mapping(HISTORICAL_SCORECARD, "PIT_V22_V2_CLOSEOUT_SCORECARD_INVALID")
    claim = _read_mapping(
        resolved_root / "one_shot_claim.json", "PIT_V22_V2_CLOSEOUT_CLAIM_INVALID"
    )
    access = _read_mapping(
        resolved_root / "oos_access_ledger.json",
        "PIT_V22_V2_CLOSEOUT_ACCESS_LEDGER_INVALID",
    )

    result_sha = _sha256(RESULT)
    log_sha = _sha256(LOG)
    event_names = [item.get("event") for item in log.get("events", [])]
    _require(event_names == EXPECTED_EVENTS, "PIT_V22_V2_CLOSEOUT_EVENT_SEQUENCE_INVALID")
    _require(
        result.get("run_id") == RUN_ID
        and result.get("status") == "SCIENTIFIC_EVALUATION_COMPLETE_PENDING_CUSTODY_VALIDATION"
        and result.get("evaluation_attempt_count") == 1
        and result.get("oos_read_count") == 1
        and result.get("personal_paths_emitted") is False
        and result.get("secret_values_emitted") is False
        and result.get("manifest_sha256") == _canonical_sha256(result, omit="manifest_sha256"),
        "PIT_V22_V2_CLOSEOUT_RESULT_CUSTODY_INVALID",
    )
    _require(
        _sha256(FREEZE) == CONTRACT_SHA256
        and authorization.get("contract_sha256") == CONTRACT_SHA256
        and authorization.get("run_id") == RUN_ID
        and authorization.get("sealed_cohorts_read_before") == 0
        and authorization.get("authorize_read_and_evaluation") is True,
        "PIT_V22_V2_CLOSEOUT_CONTRACT_INVALID",
    )
    _require(
        _sha256(RESOLUTION) == result["hashes"]["data_defect_resolution_sha256"]
        and freeze.get("target_linkage_eligibility_policy")
        == resolution.get("eligibility_policy")
        == result.get("target_linkage_eligibility_policy"),
        "PIT_V22_V2_CLOSEOUT_ELIGIBILITY_POLICY_INVALID",
    )
    _require(
        claim.get("status") == "COMPLETE_REPORTED"
        and claim.get("run_id") == RUN_ID
        and claim.get("contract_sha256") == CONTRACT_SHA256
        and claim.get("result_sha256") == result_sha,
        "PIT_V22_V2_CLOSEOUT_CLAIM_INVALID",
    )
    _require(
        access.get("status") == "OOS_CONSUMED_RESULTS_REPORTED"
        and access.get("run_id") == RUN_ID
        and access.get("evaluation_attempt_count") == 1
        and access.get("oos_read_count") == 1
        and access.get("results_inspected") is True
        and access.get("result_sha256") == result_sha
        and access.get("manifest_sha256") == _canonical_sha256(access, omit="manifest_sha256"),
        "PIT_V22_V2_CLOSEOUT_ACCESS_LEDGER_INVALID",
    )
    _require(
        _sha256(resolved_root / RESULT.name) == result_sha
        and _sha256(resolved_root / LOG.name) == log_sha,
        "PIT_V22_V2_CLOSEOUT_TRACKED_GATED_MISMATCH",
    )
    dev_event = _event(log, "DEVELOPMENT_RV30_LINKED")
    oos_event = _event(log, "OOS_RV30_LINKED_AND_VALIDATED")
    _require(
        dev_event.get("rows") == 37_306
        and dev_event.get("target_linkage_excluded_origins") == 6
        and oos_event.get("rows") == 62_254
        and oos_event.get("target_linkage_excluded_origins") == 12
        and result.get("linked_common_complete_rows") == 62_254
        and result.get("target_linkage_excluded_origins") == 12,
        "PIT_V22_V2_CLOSEOUT_LINKAGE_COUNTS_INVALID",
    )

    primary_payloads = result.get("content_addressed_primary_payloads")
    _require(
        isinstance(primary_payloads, dict) and len(primary_payloads) == 8,
        "PIT_V22_V2_CLOSEOUT_PRIMARY_PAYLOADS_INVALID",
    )
    assert isinstance(primary_payloads, dict)
    verified_payloads: dict[str, str] = {}
    for protocol_id, digest in primary_payloads.items():
        path = resolved_root / "content_addressed" / protocol_id / f"{digest}.bin"
        _require(
            isinstance(digest, str) and path.is_file() and _sha256(path) == digest,
            f"PIT_V22_V2_CLOSEOUT_CONTENT_ADDRESS_INVALID:{protocol_id}",
        )
        verified_payloads[protocol_id] = digest
    for protocol_id, digest in {"successor-result": result_sha, "successor-log": log_sha}.items():
        path = resolved_root / "content_addressed" / protocol_id / f"{digest}.bin"
        _require(
            path.is_file() and _sha256(path) == digest,
            f"PIT_V22_V2_CLOSEOUT_CONTENT_ADDRESS_INVALID:{protocol_id}",
        )
        verified_payloads[protocol_id] = digest

    contrasts = _contrast_summary(result)
    comparison = _historical_comparison(result, scorecard)
    audit: dict[str, Any] = {
        "schema_version": "pit-v22-successor-custody-audit-v2.0",
        "status": "PASS_INDEPENDENT_POST_OOS_CUSTODY_AUDIT",
        "run_id": RUN_ID,
        "gated_root_path_sha256": root_sha,
        "contract_sha256": CONTRACT_SHA256,
        "evaluation_attempt_count": 1,
        "oos_read_count": 1,
        "rerun_allowed": False,
        "claim_status": claim["status"],
        "claim_file_sha256": _sha256(resolved_root / "one_shot_claim.json"),
        "access_ledger_status": access["status"],
        "access_ledger_file_sha256": _sha256(resolved_root / "oos_access_ledger.json"),
        "result_file_sha256": result_sha,
        "full_log_file_sha256": log_sha,
        "result_manifest_sha256": result["manifest_sha256"],
        "verified_content_addressed_payloads": verified_payloads,
        "target_linkage": {
            "development_predictor_complete_origins": 37_312,
            "development_eligible_origins": dev_event["rows"],
            "development_excluded_origins": dev_event["target_linkage_excluded_origins"],
            "all_predictor_complete_origins": 62_266,
            "all_eligible_origins": result["linked_common_complete_rows"],
            "all_excluded_origins": result["target_linkage_excluded_origins"],
        },
        "public_safety": {
            "personal_paths_emitted": False,
            "secret_values_emitted": False,
            "licensed_rows_emitted": False,
        },
        "independent_review": {
            "method": "SEPARATE_READ_ONLY_AGENT_PLUS_PRIMARY_HASH_REPRODUCTION",
            "status": "PASS",
        },
    }
    audit["audit_sha256"] = _canonical_sha256(audit, omit="audit_sha256")
    ledger: dict[str, Any] = {
        "schema_version": "pit-v22-claims-and-limitations-ledger-v2.0",
        "status": "SCIENTIFIC_RESULT_ELIGIBLE_EDGE_NOT_CONFIRMED",
        "run_id": RUN_ID,
        "decision": result["evaluation"]["decision"],
        "custody_audit_sha256": audit["audit_sha256"],
        "result_file_sha256": result_sha,
        "full_log_file_sha256": log_sha,
        "data_defect_disposition": {
            "decision": resolution["decision"],
            "missing_bar_timestamp_utc": resolution["primary_source"]["bar_timestamp_missing_utc"],
            "provider_checks": resolution["provider_checks"],
            "eligibility_policy": resolution["eligibility_policy"],
        },
        "split_session_counts": result["split_session_counts"],
        "contrasts": contrasts,
        "historical_bundle_comparison": comparison,
        "eligibility": {
            "scientific_result_eligible": True,
            "scientific_result_reason": "PASS_POST_OOS_CUSTODY_VALIDATION",
            "edge_claim_eligible": False,
            "edge_claim_reason": "NO_BINARY_EDGE_PROMOTION_RULE_IN_SIGNED_SUCCESSOR_FREEZE",
            "capital_eligible": False,
            "capital_go": False,
            "research_only": True,
        },
        "claim_boundaries": [
            "NO_UNIVERSAL_EDGE_CONFIRMED",
            "NO_CAUSAL_CLAIM",
            "NO_TRADING_PROFITABILITY_CLAIM",
            "TIMING_SENSITIVITY_NOT_EVALUATED",
            "RESEARCH_ONLY",
            "NOT_INVESTMENT_ADVICE",
        ],
        "personal_paths_emitted": False,
        "secret_values_emitted": False,
    }
    ledger["ledger_sha256"] = _canonical_sha256(ledger, omit="ledger_sha256")
    return audit, ledger


def render_markdown(ledger: Mapping[str, Any]) -> str:
    """Render the public result/limitation mirror from the machine ledger."""
    lines = [
        "# PIT v2.2 successor-v2 claims and limitations",
        "",
        "> AUTO-GENERATED by `scripts/build_pit_v22_successor_v2_closeout.py`.",
        "> `RESEARCH_ONLY` · `NOT INVESTMENT ADVICE` · `capital_go=false`.",
        "",
        f"- Run: `{ledger['run_id']}`.",
        f"- Decision: **{ledger['decision']}**.",
        f"- Result SHA-256: `{ledger['result_file_sha256']}`.",
        f"- Full log SHA-256: `{ledger['full_log_file_sha256']}`.",
        "- Scientific result eligibility: **true after independent custody validation**; "
        "edge and capital eligibility remain false.",
        "",
        "## Registered global contrasts",
        "",
        "| Role | Contrast | Estimate | 95% CI | raw p | Holm p | development MDE | >= MDE |",
        "| --- | --- | ---: | --- | ---: | ---: | ---: | --- |",
    ]
    for role, contrasts in ledger["contrasts"].items():
        for name, value in contrasts.items():
            holm = "n/a" if value["p_value_holm"] is None else f"{value['p_value_holm']:.12g}"
            lines.append(
                f"| `{role}` | `{name}` | {value['estimate']:.12g} | "
                f"[{value['ci_low']:.12g}, {value['ci_high']:.12g}] | "
                f"{value['p_value_raw']:.12g} | {holm} | {value['training_mde']:.12g} | "
                f"{str(value['estimate_at_least_mde']).lower()} |"
            )
    lines += [
        "",
        "## Data-defect disposition",
        "",
        "The missing TSLA minute was confirmed by Massive as independent existence evidence. "
        "FMP reauthentication was unavailable and neighboring provider bars were not "
        "interchangeable, so no cross-provider bar was inserted. The rule frozen before OOS "
        "excludes every predictor-complete origin without 31 prices, 30 returns and finite, "
        "positive RV30; interpolation, imputation and provider substitution are forbidden.",
        "",
        "## Historical comparison and limits",
        "",
        "The twelve historical RP2-v3 aggregates use different partitions, information sets "
        "and estimands. Their direct contradiction is therefore not identifiable. The ledger "
        "retains a descriptive sign comparison without treating it as replication.",
        "",
    ]
    lines.extend(f"- `{value}`" for value in ledger["claim_boundaries"])
    return "\n".join(lines).rstrip() + "\n"


def _write_json_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    os.replace(temporary, path)


def _write_text_atomic(path: Path, value: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--gated-root", type=Path, required=True)
    args = parser.parse_args(argv)
    audit, ledger = build_closeout(args.gated_root)
    _write_json_atomic(AUDIT_OUTPUT, audit)
    _write_json_atomic(LEDGER_OUTPUT, ledger)
    _write_text_atomic(MARKDOWN_OUTPUT, render_markdown(ledger))
    print("PIT_V22_SUCCESSOR_V2_CLOSEOUT=PASS")
    print(f"RESULT_SHA256={ledger['result_file_sha256']}")
    print(f"FULL_LOG_SHA256={ledger['full_log_file_sha256']}")
    print("SCIENTIFIC_RESULT_ELIGIBLE=YES")
    print("EDGE_CLAIM_ELIGIBLE=NO")
    print("CAPITAL_GO=FALSE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
