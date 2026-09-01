"""Evidence-bound, target-blind claims and limitations for MDS650 PIT v2.2.

This module is intentionally unable to accept predictions, RV30, QLIKE or any
out-of-sample payload. It accepts only the sanitized public one-shot log needed
to record the failed pre-OOS disposition alongside target-blind input evidence.
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from typing import Any

_SHA256 = re.compile(r"^[a-f0-9]{64}$")
_SOURCE_KEYS = (
    "panel_manifest",
    "confirmation_readiness",
    "availability_manifest",
    "availability_summary",
    "pit_contract_v21",
    "claim_matrix_v21",
    "uw_latency_campaign_aggregate",
    "uw_latency_campaign_state",
    "successor_evaluation_log",
)


def canonical_sha256(value: Mapping[str, Any]) -> str:
    """Return the stable SHA-256 digest for one JSON-compatible mapping.

    Parameters
    ----------
    value:
        Mapping to encode with sorted keys and compact JSON separators.

    Returns
    -------
    str
        Lowercase 64-character SHA-256 digest.

    Notes
    -----
    The function never serializes filesystem paths supplied by a caller; path
    strings in the ledger are fixed logical repository-relative identifiers.
    """
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_claim_ledger(
    panel_manifest: Mapping[str, Any],
    readiness: Mapping[str, Any],
    availability_manifest: Mapping[str, Any],
    availability_summary: Mapping[str, Any],
    uw_latency_state: Mapping[str, Any],
    uw_latency_aggregate: Mapping[str, Any],
    successor_log: Mapping[str, Any],
    source_hashes: Mapping[str, str],
) -> dict[str, Any]:
    """Build a self-hashing PIT v2.2 claim ledger without evaluation data.

    Parameters
    ----------
    panel_manifest:
        Target-blind v2.2 common-predictor manifest.
    readiness:
        Confirmation-readiness v1 report.
    availability_manifest, availability_summary:
        Target-blind B2 availability-sidecar evidence.
    uw_latency_state:
        Target-blind UW campaign lifecycle and cross-channel boundary.
    uw_latency_aggregate:
        Immutable target-blind latency snapshot referenced by the state authority.
    successor_log:
        Sanitized public log of the consumed attempt; it contains no OOS payload
        or scientific result.
    source_hashes:
        SHA-256 values keyed by the fixed logical evidence identifiers.

    Returns
    -------
    dict[str, Any]
        Self-hashing ledger of supported, proxy-only, conservative-rule and
        not-evaluated claims. It never contains a predictive metric or result.

    Raises
    ------
    ValueError
        If any input opens reconciliation/OOS access, fails target-blind
        identity validation, lacks the primary availability totals, or has an
        invalid source hash.

    Notes
    -----
    The resulting ledger marks the three scientific questions as not evaluated
    after the PIT correction because the only authorized attempt failed before
    OOS access. A future attempt requires an entirely new contract and read gate.
    """
    _validate_panel_manifest(panel_manifest)
    _validate_readiness(readiness)
    _validate_availability_manifest(availability_manifest)
    _validate_uw_latency_state(uw_latency_state, uw_latency_aggregate)
    opening_receipts = _opening_receipt_counts(uw_latency_aggregate)
    _validate_successor_log(successor_log)
    _validate_source_hashes(source_hashes)
    primary = _primary_availability_totals(availability_summary)

    panel_output = _mapping(panel_manifest, "output", "PIT_V22_CLAIM_LEDGER_PANEL_INVALID")
    panel_summary = _mapping(panel_manifest, "summary", "PIT_V22_CLAIM_LEDGER_PANEL_INVALID")
    row_count = _positive_int(panel_output, "row_count", "PIT_V22_CLAIM_LEDGER_PANEL_INVALID")
    common_count = _positive_int(
        panel_output,
        "common_complete_row_count",
        "PIT_V22_CLAIM_LEDGER_PANEL_INVALID",
    )
    asset_count = _positive_int(panel_summary, "asset_count", "PIT_V22_CLAIM_LEDGER_PANEL_INVALID")
    claims = _claims(
        row_count=row_count,
        common_count=common_count,
        asset_count=asset_count,
        primary=primary,
        opening_receipts=opening_receipts,
        source_hashes=source_hashes,
    )
    ledger: dict[str, Any] = {
        "schema_version": "pit-v22-claim-ledger-v1.0",
        "status": "PASS_TARGET_BLIND_CLAIMS_NO_RESULT",
        "scope": "target_blind_pit_readiness_and_failed_pre_oos_disposition",
        "no_target_or_metric_payload_read": True,
        "model_fit_performed": False,
        "safe_to_reconcile_existing_results": "NO",
        "safe_to_open_or_evaluate_oos": "NO",
        "source_hashes": {key: source_hashes[key] for key in _SOURCE_KEYS},
        "claims": claims,
        "evaluation_questions": [
            {
                "question_id": "Q1_B1_VERSUS_B0",
                "status": "NOT_EVALUATED_AFTER_PIT_CORRECTION",
                "reason": (
                    "The only authorized successor attempt failed before OOS access and "
                    "produced no scientific result."
                ),
            },
            {
                "question_id": "Q2_B2_INCREMENTAL_OVER_B1",
                "status": "NOT_EVALUATED_AFTER_PIT_CORRECTION",
                "reason": (
                    "The consumed successor attempt produced no result; pre-v2.2 sealed "
                    "results remain ineligible for reconciliation."
                ),
            },
            {
                "question_id": "Q3_STABILITY_BY_ASSET_TIME_REGIME_AND_LATENCY",
                "status": "NOT_EVALUATED_AFTER_PIT_CORRECTION",
                "reason": (
                    "The consumed successor attempt failed before corrected forecasts, "
                    "contrasts or stability outputs were produced."
                ),
            },
        ],
        "next_required_gate": "NEW_CONTRACT_RUN_ID_OWNER_AUTHORIZATION_AND_READ_GATE",
    }
    ledger["claim_ledger_sha256"] = canonical_sha256(ledger)
    return ledger


def render_claims_markdown(ledger: Mapping[str, Any]) -> str:
    """Render a compact, evidence-bound human-readable claim ledger.

    Parameters
    ----------
    ledger:
        Validated output from :func:`build_claim_ledger`.

    Returns
    -------
    str
        Markdown that names every claim, status, evidence location and
        limitation without universal-edge or profitability language.

    Raises
    ------
    ValueError
        If the supplied ledger is not the expected target-blind, no-evaluation
        format.
    """
    if ledger.get("status") != "PASS_TARGET_BLIND_CLAIMS_NO_RESULT":
        raise ValueError("PIT_V22_CLAIM_LEDGER_RENDER_INPUT_INVALID")
    claims = ledger.get("claims")
    questions = ledger.get("evaluation_questions")
    if not isinstance(claims, list) or not isinstance(questions, list):
        raise ValueError("PIT_V22_CLAIM_LEDGER_RENDER_INPUT_INVALID")
    lines = [
        "# MDS650 PIT v2.2 — Claims and Limitations Ledger",
        "",
        "## Scope",
        "",
        "This ledger is target-blind. It contains no RV30, forecast, loss, QLIKE,",
        "model-fit or sealed out-of-sample payload. It binds the corrected PIT input",
        "evidence to the sanitized public log of the consumed pre-OOS failure.",
        "",
        "```text",
        "SAFE_TO_RECONCILE_EXISTING_RESULTS=NO",
        "SAFE_TO_OPEN_OR_EVALUATE_OOS=NO",
        "MODEL_FIT_PERFORMED=NO",
        "SUCCESSOR_ATTEMPT_STATUS=FAIL_CLOSED_PRE_OOS",
        "SUCCESSOR_RERUN_ALLOWED=NO",
        "```",
        "",
        "## Claims",
        "",
        "| ID | Status | Claim | Limitation | Evidence |",
        "| --- | --- | --- | --- | --- |",
    ]
    for claim in claims:
        if not isinstance(claim, Mapping):
            raise ValueError("PIT_V22_CLAIM_LEDGER_RENDER_INPUT_INVALID")
        evidence = claim.get("evidence")
        if not isinstance(evidence, list):
            raise ValueError("PIT_V22_CLAIM_LEDGER_RENDER_INPUT_INVALID")
        evidence_text = "; ".join(
            str(item.get("path", "")) for item in evidence if isinstance(item, Mapping)
        )
        lines.append(
            "| {claim_id} | {status} | {claim_text} | {limitation} | {evidence} |".format(
                claim_id=_markdown_cell(claim.get("claim_id")),
                status=_markdown_cell(claim.get("status")),
                claim_text=_markdown_cell(claim.get("claim_text")),
                limitation=_markdown_cell(claim.get("limitation")),
                evidence=_markdown_cell(evidence_text),
            )
        )
    lines.extend(
        [
            "",
            "## Scientific questions not yet evaluated",
            "",
            "| Question | Status | Reason |",
            "| --- | --- | --- |",
        ]
    )
    for question in questions:
        if not isinstance(question, Mapping):
            raise ValueError("PIT_V22_CLAIM_LEDGER_RENDER_INPUT_INVALID")
        lines.append(
            "| {question_id} | {status} | {reason} |".format(
                question_id=_markdown_cell(question.get("question_id")),
                status=_markdown_cell(question.get("status")),
                reason=_markdown_cell(question.get("reason")),
            )
        )
    lines.extend(
        [
            "",
            "## Future evaluation authority",
            "",
            "The consumed attempt cannot be rerun. Any future evaluation requires a new",
            "method contract, run id, owner authorization and separately justified read gate;",
            "this ledger grants none of them.",
            "",
        ]
    )
    return "\n".join(lines)


def _claims(
    *,
    row_count: int,
    common_count: int,
    asset_count: int,
    primary: Mapping[str, int],
    opening_receipts: Mapping[str, int],
    source_hashes: Mapping[str, str],
) -> list[dict[str, Any]]:
    """Create fixed claims whose status cannot depend on an evaluation result."""
    panel_evidence = _evidence(source_hashes, "panel_manifest", "confirmation_readiness")
    timing_evidence = _evidence(source_hashes, "pit_contract_v21", "claim_matrix_v21")
    measured_timing_evidence = timing_evidence + _evidence(
        source_hashes,
        "uw_latency_campaign_state",
        "uw_latency_campaign_aggregate",
    )
    availability_evidence = _evidence(
        source_hashes,
        "availability_manifest",
        "availability_summary",
        "panel_manifest",
    )
    return [
        {
            "claim_id": "PITV22-C001",
            "status": "SUPPORTED_TARGET_BLIND",
            "claim_text": (
                f"The corrected B0/B1Q/B2 predictor construction preserved {row_count} "
                f"forecast origins and {common_count} common-complete origins across "
                f"{asset_count} outcome assets."
            ),
            "limitation": "These are input-coverage counts, not predictive metrics.",
            "allowed_presentation_context": "data_engineering_and_pit_readiness",
            "evidence": panel_evidence,
        },
        {
            "claim_id": "PITV22-C002",
            "status": "PROXY_ONLY",
            "claim_text": (
                "The measured live receipt latency campaign is RECONCILED_PARTIAL; "
                "Unusual Whales created_at remains only an operational availability proxy "
                "at the registered cutoff. The five clean sessions have "
                f"{opening_receipts['over_60_count']}/{opening_receipts['count']} opening "
                "receipts beyond 60 seconds and "
                f"{opening_receipts['over_120_count']}/{opening_receipts['count']} beyond "
                "120 seconds."
            ),
            "limitation": (
                "The registered 60-second buffer is not a strict opening availability bound "
                "in this sample; two hour-14 receipts also exceed 120 seconds. The "
                "cross-channel design cannot identify backfill or revision and does not prove "
                "provider publication time or client receipt time."
            ),
            "allowed_presentation_context": "timing_assumption",
            "evidence": measured_timing_evidence,
        },
        {
            "claim_id": "PITV22-C003",
            "status": "STUDY_CONSERVATIVE_RULE",
            "claim_text": (
                "FMP plus one minute (with plus two minutes sensitivity) and Massive SIP "
                "as-of selection remain conservative study rules."
            ),
            "limitation": "They do not prove provider or client-side message receipt latency.",
            "allowed_presentation_context": "timing_assumption",
            "evidence": timing_evidence,
        },
        {
            "claim_id": "PITV22-C004",
            "status": "SUPPORTED_TARGET_BLIND",
            "claim_text": (
                "The primary B2 availability sidecar marks "
                f"{primary['excluded_row_count']} of {primary['row_count']} rows as excluded "
                "rather than treating delayed source records as zero activity."
            ),
            "limitation": (
                "The correction changes eligibility only; it does not validate performance."
            ),
            "allowed_presentation_context": "data_quality_and_pit_readiness",
            "evidence": availability_evidence,
        },
        {
            "claim_id": "PITV22-C005",
            "status": "BLOCKED_RECONCILIATION",
            "claim_text": "Pre-v2.2 sealed results are not eligible for reconciliation.",
            "limitation": "No prior sign, metric or ranking may be carried into a corrected claim.",
            "allowed_presentation_context": "methodological_limitation",
            "evidence": panel_evidence + availability_evidence,
        },
        {
            "claim_id": "PITV22-C006",
            "status": "NOT_EVALUATED_AFTER_PIT_CORRECTION",
            "claim_text": "Whether B1 improves B0 for RV30 is not yet evaluated after PIT v2.2.",
            "limitation": (
                "The consumed attempt produced no result; any future evaluation requires a "
                "new contract, run id, owner authorization and read gate."
            ),
            "allowed_presentation_context": "research_question_status",
            "evidence": panel_evidence
            + availability_evidence
            + _evidence(source_hashes, "successor_evaluation_log"),
        },
        {
            "claim_id": "PITV22-C007",
            "status": "NOT_EVALUATED_AFTER_PIT_CORRECTION",
            "claim_text": (
                "Whether B2 adds incremental value over B1 is not yet evaluated after PIT v2.2."
            ),
            "limitation": "The consumed attempt produced no loss or model output.",
            "allowed_presentation_context": "research_question_status",
            "evidence": panel_evidence
            + availability_evidence
            + _evidence(source_hashes, "successor_evaluation_log"),
        },
        {
            "claim_id": "PITV22-C008",
            "status": "NOT_EVALUATED_AFTER_PIT_CORRECTION",
            "claim_text": (
                "Stability by asset, session segment, volatility regime and latency assumption "
                "is not yet evaluated after PIT v2.2."
            ),
            "limitation": "No corrected forecasts, contrasts or stability payloads were produced.",
            "allowed_presentation_context": "research_question_status",
            "evidence": panel_evidence
            + timing_evidence
            + _evidence(source_hashes, "successor_evaluation_log"),
        },
    ]


def _validate_panel_manifest(panel_manifest: Mapping[str, Any]) -> None:
    """Fail closed unless the panel remains target-blind and unreconciled."""
    required = {
        "schema_version": "target-blind-common-predictor-manifest-v2.2",
        "status": "PASS_TARGET_BLIND_INPUTS_RECONCILIATION_REMAINS_BLOCKED",
        "no_target_or_metric_payload_read": True,
        "model_fit_performed": False,
        "safe_to_reconcile_existing_results": "NO",
    }
    if any(panel_manifest.get(key) != value for key, value in required.items()):
        raise ValueError("PIT_V22_CLAIM_LEDGER_PANEL_MANIFEST_INVALID")


def _validate_readiness(readiness: Mapping[str, Any]) -> None:
    """Fail closed unless readiness itself remains before acquisition/OOS access."""
    required = {
        "schema_version": "confirmation-readiness-v1.0",
        "status": "PASS_READY_FOR_CONFIRMATION_ACQUISITION_NOT_REQUESTED",
        "no_target_or_metric_payload_read": True,
        "model_fit_performed": False,
        "safe_to_reconcile_existing_results": "NO",
        "safe_to_open_or_evaluate_oos": "NO",
        "ready_for_confirmation": "YES",
        "safe_to_acquire_new_sample": "NO",
    }
    if any(readiness.get(key) != value for key, value in required.items()):
        raise ValueError("PIT_V22_CLAIM_LEDGER_READINESS_INVALID")
    expected_hash = readiness.get("readiness_sha256")
    unsigned = {key: value for key, value in readiness.items() if key != "readiness_sha256"}
    if not isinstance(expected_hash, str) or expected_hash != canonical_sha256(unsigned):
        raise ValueError("PIT_V22_CLAIM_LEDGER_READINESS_INVALID")


def _validate_availability_manifest(availability_manifest: Mapping[str, Any]) -> None:
    """Require a target-blind availability sidecar with reconciliation blocked."""
    required = {
        "schema_version": "2.2",
        "generation_mode": "deterministic_target_blind_rebuild",
        "model_or_metric_payload_read": False,
        "oos_payload_read": False,
        "safe_to_reconcile_existing_results": "NO",
    }
    if any(availability_manifest.get(key) != value for key, value in required.items()):
        raise ValueError("PIT_V22_CLAIM_LEDGER_AVAILABILITY_MANIFEST_INVALID")


def _validate_uw_latency_state(
    state: Mapping[str, Any], aggregate: Mapping[str, Any]
) -> None:
    """Keep measured latency evidence inside its target-blind proxy boundary."""
    required = {
        "schema_version": "uw-latency-campaign-state-v2.0",
        "state": "RECONCILED_PARTIAL",
        "claim_classification": "PROXY_ONLY_CROSS_CHANNEL",
        "target_blind": True,
        "safe_to_reconcile_existing_results": "NO",
        "safe_to_open_or_evaluate_oos": "NO",
    }
    counts = state.get("counts")
    backfill = state.get("backfill")
    revision = state.get("revision")
    aggregate_ref = state.get("aggregate")
    lifecycle = state.get("artifact_lifecycle")
    if (
        any(state.get(key) != value for key, value in required.items())
        or not isinstance(counts, Mapping)
        or counts.get("collected") != 11
        or counts.get("reconciled") != 6
        or counts.get("unreconciled") != 5
        or backfill != {"value": None, "reason": "CROSS_CHANNEL_NOT_IDENTIFIABLE"}
        or revision
        != {
            "value": None,
            "reason": "AGGREGATE_ALERT_VS_INDIVIDUAL_TRADE_NOT_COMPARABLE",
        }
        or aggregate_ref
        != {
            "path": "artifacts/gate5_pit/uw_latency_campaign_20260901_v2.json",
            "self_sha256": aggregate.get("self_sha256"),
        }
        or lifecycle
        != {
            "policy": "IMMUTABLE_DATED_SNAPSHOT",
            "freshness_check": "REGENERATE_AND_COMPARE_WITH_LIVE_SESSION_INVENTORY",
            "on_drift": "PUBLISH_NEW_DATED_SNAPSHOT_NEVER_OVERWRITE",
        }
        or state.get("self_sha256")
        != canonical_sha256({key: value for key, value in state.items() if key != "self_sha256"})
    ):
        raise ValueError("PIT_V22_CLAIM_LEDGER_UW_LATENCY_STATE_INVALID")


def _opening_receipt_counts(aggregate: Mapping[str, Any]) -> Mapping[str, int]:
    """Validate the immutable v2 aggregate and return its opening-hour counts."""
    expected_boundary = {
        "value": None,
        "reason": "CROSS_CHANNEL_NOT_IDENTIFIABLE",
    }
    expected_revision = {
        "value": None,
        "reason": "AGGREGATE_ALERT_VS_INDIVIDUAL_TRADE_NOT_COMPARABLE",
    }
    operational = aggregate.get("operational_latency")
    if not isinstance(operational, Mapping):
        raise ValueError("PIT_V22_CLAIM_LEDGER_UW_LATENCY_AGGREGATE_INVALID")
    by_hour = operational.get("by_ny_hour")
    values = by_hour.get("values") if isinstance(by_hour, Mapping) else None
    opening = values.get("9") if isinstance(values, Mapping) else None
    hour_14 = values.get("14") if isinstance(values, Mapping) else None
    if (
        aggregate.get("schema_version") != "uw-latency-campaign-v2.0"
        or aggregate.get("scope") != "TARGET_BLIND_OPERATIONAL_PROVIDER_TIMING"
        or aggregate.get("claim_classification") != "PROXY_ONLY_CROSS_CHANNEL"
        or aggregate.get("target_blind") is not True
        or aggregate.get("model_fit_performed") is not False
        or aggregate.get("sealed_cohort_read") is not False
        or aggregate.get("backfill") != expected_boundary
        or aggregate.get("revision") != expected_revision
        or aggregate.get("self_sha256")
        != canonical_sha256(
            {key: value for key, value in aggregate.items() if key != "self_sha256"}
        )
        or not isinstance(opening, Mapping)
        or not isinstance(hour_14, Mapping)
        or opening.get("session_count") != 5
        or opening.get("count") != 406
        or not isinstance(opening.get("over_60_seconds"), Mapping)
        or opening["over_60_seconds"].get("count") != 6
        or not isinstance(opening.get("over_120_seconds"), Mapping)
        or opening["over_120_seconds"].get("count") != 0
        or not isinstance(hour_14.get("over_120_seconds"), Mapping)
        or hour_14["over_120_seconds"].get("count") != 2
    ):
        raise ValueError("PIT_V22_CLAIM_LEDGER_UW_LATENCY_AGGREGATE_INVALID")
    return {"count": 406, "over_60_count": 6, "over_120_count": 0}


def _validate_successor_log(log: Mapping[str, Any]) -> None:
    """Accept only the public fail-closed log emitted before OOS authorization."""
    events = log.get("events")
    if not isinstance(events, list) or not all(isinstance(event, Mapping) for event in events):
        raise ValueError("PIT_V22_CLAIM_LEDGER_SUCCESSOR_LOG_INVALID")
    names = [event.get("event") for event in events]
    failure = events[-1] if events else {}
    if (
        log.get("schema_version") != "pit-v22-successor-evaluation-log-1.0"
        or log.get("run_id") != "pit-v22-successor-evaluation-v1-20260901"
        or names != ["ONE_SHOT_CLAIMED", "RUNTIME_PREREGISTRATION_FROZEN", "FAIL_CLOSED"]
        or failure.get("error") != "RuntimeError:PIT_V22_TARGET_LINKAGE_INVALID"
        or failure.get("rerun_allowed") is not False
    ):
        raise ValueError("PIT_V22_CLAIM_LEDGER_SUCCESSOR_LOG_INVALID")


def _validate_source_hashes(source_hashes: Mapping[str, str]) -> None:
    """Require every fixed logical source to carry a complete SHA-256 value."""
    if set(source_hashes) != set(_SOURCE_KEYS):
        raise ValueError("PIT_V22_CLAIM_LEDGER_SOURCE_HASHES_INVALID")
    if any(
        not isinstance(value, str) or not _SHA256.fullmatch(value)
        for value in source_hashes.values()
    ):
        raise ValueError("PIT_V22_CLAIM_LEDGER_SOURCE_HASHES_INVALID")


def _primary_availability_totals(summary: Mapping[str, Any]) -> Mapping[str, int]:
    """Return validated primary-variant counts from target-free availability evidence."""
    if summary.get("schema_version") != "2.2":
        raise ValueError("PIT_V22_CLAIM_LEDGER_AVAILABILITY_SUMMARY_INVALID")
    totals = summary.get("variant_totals")
    if not isinstance(totals, list):
        raise ValueError("PIT_V22_CLAIM_LEDGER_AVAILABILITY_SUMMARY_INVALID")
    primary = next(
        (
            value
            for value in totals
            if isinstance(value, Mapping) and value.get("canonical_variant") == "primary_5m_60s"
        ),
        None,
    )
    if not isinstance(primary, Mapping):
        raise ValueError("PIT_V22_CLAIM_LEDGER_AVAILABILITY_SUMMARY_INVALID")
    row_count = _positive_int(
        primary,
        "row_count",
        "PIT_V22_CLAIM_LEDGER_AVAILABILITY_SUMMARY_INVALID",
    )
    eligible_count = _nonnegative_int(
        primary,
        "eligible_row_count",
        "PIT_V22_CLAIM_LEDGER_AVAILABILITY_SUMMARY_INVALID",
    )
    excluded_count = _nonnegative_int(
        primary,
        "excluded_row_count",
        "PIT_V22_CLAIM_LEDGER_AVAILABILITY_SUMMARY_INVALID",
    )
    if eligible_count + excluded_count != row_count:
        raise ValueError("PIT_V22_CLAIM_LEDGER_AVAILABILITY_SUMMARY_INVALID")
    return {
        "row_count": row_count,
        "eligible_row_count": eligible_count,
        "excluded_row_count": excluded_count,
    }


def _evidence(source_hashes: Mapping[str, str], *keys: str) -> list[dict[str, str]]:
    """Return logical relative evidence identifiers paired with validated hashes."""
    logical_paths = {
        "panel_manifest": (
            "artifacts/target_blind_v22/target_blind_common_predictor_manifest_v22.json"
        ),
        "confirmation_readiness": "artifacts/target_blind_v22/confirmation_readiness_v1.json",
        "availability_manifest": "artifacts/provider_timing_v22/b2_availability_manifest_v22.json",
        "availability_summary": "artifacts/provider_timing_v22/b2_availability_summary_v22.json",
        "pit_contract_v21": "docs/provider_timing_pit_contract_v21.md",
        "claim_matrix_v21": "docs/provider_timing_claim_matrix_v21.md",
        "uw_latency_campaign_state": (
            "artifacts/gate5_pit/uw_latency_campaign_state_20260901_v2.json"
        ),
        "uw_latency_campaign_aggregate": (
            "artifacts/gate5_pit/uw_latency_campaign_20260901_v2.json"
        ),
        "successor_evaluation_log": (
            "artifacts/target_blind_v22/successor_evaluation_run_v1.json"
        ),
    }
    return [{"path": logical_paths[key], "sha256": source_hashes[key]} for key in keys]


def _mapping(payload: Mapping[str, Any], key: str, error_code: str) -> Mapping[str, Any]:
    """Return one nested mapping or fail with the caller's evidence code."""
    value = payload.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(error_code)
    return value


def _positive_int(payload: Mapping[str, Any], key: str, error_code: str) -> int:
    """Return a strictly positive integer or fail with the caller's evidence code."""
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError(error_code)
    return value


def _nonnegative_int(payload: Mapping[str, Any], key: str, error_code: str) -> int:
    """Return a nonnegative integer or fail with the caller's evidence code."""
    value = payload.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(error_code)
    return value


def _markdown_cell(value: object) -> str:
    """Render one scalar safely inside a Markdown table cell."""
    return str(value).replace("|", "\\|").replace("\n", " ")
