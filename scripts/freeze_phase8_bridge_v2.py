"""Freeze the target-blind Phase 8A exploratory bridge authorized on 2026-08-27.

This script reads only already-observed D/V methodology and power artifacts. It never
opens the Phase 8 cohort, target, forecasts, losses or metrics. V2 binds provenance to
the frozen bridge protocol rather than the append-only methodology ledger, whose hash
changes whenever an unrelated later decision is recorded.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from statistics import NormalDist
from typing import Any

from mds650.storage import assert_outside_frozen

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts" / "phase8_bridge" / "bridge_contract_v2.json"
POWER_SOURCE = ROOT / "artifacts" / "rp2_block12_prospective" / "design.json"
INPUTS = (
    "artifacts/rp2_block12_prospective/design.json",
    "docs/DISCOVERY_VALIDATION_CONFIRMATION_PROTOCOL.md",
    "docs/phase8_bridge_protocol_v2.md",
    "docs/sequential_multiplicity_policy_v1.md",
    "src/mds650/rp2/ladder.py",
)
REFERENCE_ALPHA = 0.025 / 5
POWER = 0.80


def _sha(path: Path) -> str:
    data = path.read_bytes()
    if path.suffix != ".parquet":
        data = data.replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def canonical_sha256(document: dict[str, Any]) -> str:
    payload = {key: value for key, value in document.items() if key != "contract_sha256"}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _mde(session_sigma: float, sessions: int) -> float:
    critical = NormalDist().inv_cdf(1.0 - REFERENCE_ALPHA)
    power_quantile = NormalDist().inv_cdf(POWER)
    return (critical + power_quantile) * session_sigma / math.sqrt(sessions)


def _power_calibration(source: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    source_labels = {
        "delta_b1": "delta_b1_session_sigma",
        "delta_b2_given_b1": "delta_b2_given_b1_session_sigma",
    }
    for role in ("D", "V"):
        for family in ("gamma_glm", "lightgbm"):
            measured = source["measured_dispersion"][role][family]
            for contrast, sigma_key in source_labels.items():
                sigma = float(measured[sigma_key])
                rows.append(
                    {
                        "contrast": contrast,
                        "family": family,
                        "mde_n20": _mde(sigma, 20),
                        "mde_n30": _mde(sigma, 30),
                        "reference_role": role,
                        "session_sigma": sigma,
                    }
                )
    return rows


def build_contract() -> dict[str, Any]:
    power_source = json.loads(POWER_SOURCE.read_text(encoding="utf-8"))
    document: dict[str, Any] = {
        "schema_version": "phase8-exploratory-bridge-v2.0",
        "protocol_id": "phase8a-exploratory-bridge-20of30-v2",
        "authorized_on": "2026-08-27",
        "status": "TARGET_BLIND_METHOD_FROZEN_READ_NOT_AUTHORIZED",
        "claim_classification": "EXPLORATORY_DESCRIPTIVE_NOT_CONFIRMATORY",
        "cohort": {
            "new_cohort_created": False,
            "primary": {
                "sessions": 20,
                "strictly_unobserved": True,
                "window": "2026-08-03..2026-08-28",
            },
            "sensitivity": {
                "sessions": 30,
                "strictly_unobserved": False,
                "window": "2026-07-20..2026-08-28",
            },
            "c2_overlap": {
                "sessions": 10,
                "window": "2026-07-20..2026-07-31",
                "permitted_role": "SENSITIVITY_ONLY",
            },
        },
        "training": {
            "universes": ["D", "V"],
            "phase8_rows_used_for_fit_or_selection": 0,
            "selection_status": "D_AND_V_ALREADY_OBSERVED_EXPLORATORY",
            "retraining_after_phase8_read": False,
        },
        "target_and_information": {
            "target": "RV30",
            "information_sets": ["B0", "B0+B1", "B0+B2", "B0+B1+B2"],
            "pit_cutoff_seconds": 120,
            "per_session_backfill_max_share": 0.01,
            "missing_or_inadmissible_session": "FAIL_CLOSED_NO_SUBSTITUTION",
        },
        "estimands": {
            "primary": "delta_total",
            "positive_means": "expanded option-information set lowers QLIKE",
            "reported_together": [
                {"id": "delta_b1", "formula": "L(B0)-L(B0+B1)"},
                {"id": "delta_b2_given_b1", "formula": "L(B0+B1)-L(B0+B1+B2)"},
                {"id": "delta_b2_given_b0", "formula": "L(B0)-L(B0+B2)"},
                {"id": "delta_total", "formula": "L(B0)-L(B0+B1+B2)"},
                {
                    "id": "delta_interaction",
                    "formula": "delta_total-delta_b1-delta_b2_given_b0",
                },
            ],
            "aggregation": "equal weight by XNYS session after within-session averaging",
        },
        "models": {
            "families": ["gamma_glm", "lightgbm"],
            "producer": "src/mds650/rp2/ladder.py",
            "gamma_glm": {"alpha": 0.0001, "link": "log", "max_iter": 500},
            "lightgbm": {
                "deterministic": True,
                "early_stopping_metric": "QLIKE",
                "early_stopping_rounds": 50,
                "inner_validation_share": 0.2,
                "learning_rate": 0.05,
                "max_rounds": 2000,
                "num_leaves": 31,
                "seed": 20260818,
            },
            "tuning_on_phase8": False,
        },
        "inference": {
            "independent_unit": "XNYS_SESSION",
            "primary_window": {
                "confidence_interval": "95_PERCENT_STUDENTIZED_SESSION_CLUSTER",
                "newey_west": True,
                "p_values": "RAW_AND_HOLM_ADJUSTED_REPORTED_DESCRIPTIVELY",
                "wild_cluster_bootstrap_repetitions": 9999,
                "seed": 650,
            },
            "sensitivity_window": {
                "confidence_interval": "95_PERCENT_SESSION_CLUSTER",
                "p_values": "NOT_USED_FOR_A_SECOND_DECISION",
            },
            "all_assets_and_signs_reported": True,
            "subgroup_selection_after_read": False,
        },
        "multiplicity": {
            "sequential_slot": 1,
            "campaign_alpha_budget": 0.025,
            "holm_family_size_per_model": 5,
            "holm_first_step_reference": REFERENCE_ALPHA,
            "slot_recycled": False,
            "confirmatory_threshold_enabled": False,
            "reason": "bridge is exploratory; alpha is retained only as a non-recycled reference",
        },
        "power": {
            "power": POWER,
            "reference_alpha": REFERENCE_ALPHA,
            "source": "artifacts/rp2_block12_prospective/design.json",
            "source_scope": "D_AND_V_ONLY",
            "sealed_cohort_used": False,
            "calibration": _power_calibration(power_source),
            "primary_estimand_status": "NOT_ESTIMATED_FROM_CURRENT_SOURCE",
            "primary_estimand_claim_allowed": False,
            "primary_estimand_reason": (
                "the current source does not expose session sigma for delta_total; no proxy "
                "or sealed-outcome variance is substituted"
            ),
        },
        "decision_rules": {
            "confirmatory_promotion_allowed": False,
            "permitted_labels": [
                "DIRECTIONALLY_SUPPORTIVE_EXPLORATORY",
                "MIXED_EXPLORATORY",
                "DIRECTIONALLY_ADVERSE_EXPLORATORY",
                "IMPRECISE_EXPLORATORY",
            ],
            "all_outcomes_published": True,
            "retrospective_salvage_analysis": False,
        },
        "read_gate": {
            "one_shot_authorization_required": True,
            "safe_to_open_or_evaluate_oos": False,
            "sealed_cohorts_read": 0,
        },
        "provenance": {
            "decision_number": 99,
            "inputs": list(INPUTS),
            "input_sha256": {path: _sha(ROOT / path) for path in INPUTS},
        },
    }
    document["contract_sha256"] = canonical_sha256(document)
    return document


def main() -> None:
    output = assert_outside_frozen(OUTPUT)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(build_contract(), indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"[phase8-bridge] wrote {output} (sealed_cohorts_read=0)")


if __name__ == "__main__":
    main()
