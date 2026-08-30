"""Target-blind contract for the owner-authorized Phase 8 exploratory bridge."""

from __future__ import annotations

import importlib.util
import json
import math
from pathlib import Path
from statistics import NormalDist

import pytest

REPO = Path(__file__).resolve().parents[2]
ARTIFACT = REPO / "artifacts" / "phase8_bridge" / "bridge_contract_v2.json"

_spec = importlib.util.spec_from_file_location(
    "freeze_phase8_bridge_v2", REPO / "scripts" / "freeze_phase8_bridge_v2.py"
)
assert _spec is not None and _spec.loader is not None
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def _contract() -> dict[str, object]:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


def test_frozen_contract_matches_target_blind_regeneration() -> None:
    committed = _contract()
    assert committed == _module.build_contract()
    assert committed["contract_sha256"] == _module.canonical_sha256(committed)


def test_the_twenty_session_window_is_primary_and_thirty_is_sensitivity() -> None:
    cohort = _contract()["cohort"]
    assert cohort["new_cohort_created"] is False
    assert cohort["primary"]["sessions"] == 20
    assert cohort["primary"]["strictly_unobserved"] is True
    assert cohort["primary"]["window"] == "2026-08-03..2026-08-28"
    assert cohort["sensitivity"]["sessions"] == 30
    assert cohort["sensitivity"]["window"] == "2026-07-20..2026-08-28"
    assert cohort["c2_overlap"]["sessions"] == 10
    assert cohort["c2_overlap"]["permitted_role"] == "SENSITIVITY_ONLY"


def test_the_bridge_cannot_open_or_promote_the_sealed_cohort() -> None:
    contract = _contract()
    gate = contract["read_gate"]
    assert contract["claim_classification"] == "EXPLORATORY_DESCRIPTIVE_NOT_CONFIRMATORY"
    assert gate == {
        "one_shot_authorization_required": True,
        "safe_to_open_or_evaluate_oos": False,
        "sealed_cohorts_read": 0,
    }
    assert "CONFIRMED" not in contract["decision_rules"]["permitted_labels"]
    assert contract["decision_rules"]["confirmatory_promotion_allowed"] is False


def test_current_estimands_models_and_multiplicity_are_frozen() -> None:
    contract = _contract()
    assert contract["estimands"]["primary"] == "delta_total"
    assert [row["id"] for row in contract["estimands"]["reported_together"]] == [
        "delta_b1",
        "delta_b2_given_b1",
        "delta_b2_given_b0",
        "delta_total",
        "delta_interaction",
    ]
    assert contract["models"]["families"] == ["gamma_glm", "lightgbm"]
    multiplicity = contract["multiplicity"]
    assert multiplicity["sequential_slot"] == 1
    assert multiplicity["campaign_alpha_budget"] == pytest.approx(0.025)
    assert multiplicity["holm_family_size_per_model"] == 5
    assert multiplicity["holm_first_step_reference"] == pytest.approx(0.005)
    assert multiplicity["slot_recycled"] is False


def test_power_is_development_only_and_never_fabricated_for_delta_total() -> None:
    power = _contract()["power"]
    assert power["sealed_cohort_used"] is False
    assert power["power"] == pytest.approx(0.80)
    assert power["primary_estimand_status"] == "NOT_ESTIMATED_FROM_CURRENT_SOURCE"
    assert power["primary_estimand_claim_allowed"] is False
    rows = power["calibration"]
    assert rows
    for row in rows:
        assert row["mde_n20"] > row["mde_n30"] > 0
        critical = NormalDist().inv_cdf(1 - power["reference_alpha"])
        power_quantile = NormalDist().inv_cdf(power["power"])
        expected = (critical + power_quantile) * row["session_sigma"] / math.sqrt(20)
        assert row["mde_n20"] == pytest.approx(expected)


def test_contract_provenance_has_no_phase8_payload_input() -> None:
    provenance = _contract()["provenance"]
    assert provenance["decision_number"] == 99
    inputs = set(provenance["inputs"])
    assert inputs == {
        "artifacts/rp2_block12_prospective/design.json",
        "docs/DISCOVERY_VALIDATION_CONFIRMATION_PROTOCOL.md",
        "docs/phase8_bridge_protocol_v2.md",
        "docs/sequential_multiplicity_policy_v1.md",
        "src/mds650/rp2/ladder.py",
    }
    forbidden_payload_terms = ("holdout", "sealed_cohort", "target", "forecast", "loss")
    assert all(not any(term in path.lower() for term in forbidden_payload_terms) for path in inputs)


def test_canonical_state_points_to_the_frozen_bridge() -> None:
    state = json.loads((REPO / "data" / "CANONICAL_STATE.json").read_text(encoding="utf-8"))
    bridge = next(
        row for row in state["active_protocols"] if row["id"] == "phase8-prospective-bridge"
    )
    assert bridge["document"] == "docs/phase8_bridge_protocol_v2.md"
    assert bridge["artifact"] == "artifacts/phase8_bridge/bridge_contract_v2.json"
    assert bridge["evaluator"]["artifact"] == (
        "artifacts/phase8_bridge/evaluator_freeze_v4.json"
    )
    assert bridge["evaluator"]["script"] == "scripts/evaluate_phase8_bridge_v2.py"
    assert bridge["state"] == (
        "EXPLORATORY_BRIDGE_EVALUATION_COMPLETE_WITH_RECORDED_RECOVERY_"
        "AND_DISPERSION_AUDIT"
    )
    assert bridge["sealed_cohorts_read"] == 1
    assert bridge["authorization"]["authorization_id"] == (
        "phase8a-one-shot-4e7c4139-97bd-4d60-8ad7-29a87da8cf75"
    )
    assert bridge["execution_recovery"]["initial_failure"] == "RP3_EVAL_NO_SESSIONS"
    assert bridge["execution_recovery"]["sealed_store_reopened"] is False
    assert bridge["result"]["overall_classification"] == "MIXED_EXPLORATORY"
    assert bridge["result"]["confirmatory_promotion_allowed"] is False


def test_published_result_contains_every_registered_outcome_without_private_paths() -> None:
    result = json.loads(
        (REPO / "artifacts" / "phase8_bridge" / "result_20260830_v1.json").read_text(
            encoding="utf-8"
        )
    )
    expected_contrasts = {
        "delta_b1",
        "delta_b2_given_b0",
        "delta_b2_given_b1",
        "delta_interaction",
        "delta_total",
    }
    cells = [
        result["evaluation"][role][model]
        for role in ("D", "V")
        for model in ("gamma_glm", "lightgbm")
    ]
    assert [cell["classification"] for cell in cells].count(
        "DIRECTIONALLY_SUPPORTIVE_EXPLORATORY"
    ) == 2
    assert [cell["classification"] for cell in cells].count("IMPRECISE_EXPLORATORY") == 2
    for cell in cells:
        assert set(cell["windows"]) == {"primary_20", "sensitivity_30"}
        assert all(set(window) == expected_contrasts for window in cell["windows"].values())
        assert cell["windows"]["primary_20"]["delta_total"]["estimate"] > 0
        b2 = cell["windows"]["primary_20"]["delta_b2_given_b1"]
        assert b2["ci_low"] <= 0 <= b2["ci_high"]
    encoded = json.dumps(result)
    assert "C:\\" not in encoded
    assert "D:\\" not in encoded


def test_bridge_inputs_and_outputs_are_in_the_append_only_registry() -> None:
    registry = json.loads((REPO / "data" / "FROZEN_ARTIFACTS.json").read_text(encoding="utf-8"))
    registered = {row["path"]: row["sha256"] for row in registry["entries"]}
    assert registered["artifacts/phase8_bridge/bridge_contract_v2.json"] == _module._sha(ARTIFACT)
    document = REPO / "docs" / "phase8_bridge_protocol_v2.md"
    assert registered["docs/phase8_bridge_protocol_v2.md"] == _module._sha(document)
    evaluator = REPO / "artifacts" / "phase8_bridge" / "evaluator_freeze_v4.json"
    assert registered["artifacts/phase8_bridge/evaluator_freeze_v4.json"] == _module._sha(
        evaluator
    )
    for relative in (
        "artifacts/phase8_bridge/execution_recovery_20260830_v1.json",
        "artifacts/phase8_bridge/layout_recovery_manifest_20260830_v1.json",
        "artifacts/phase8_bridge/one_shot_custody_20260830_v1.json",
        "artifacts/phase8_bridge/one_shot_custody_20260830_v2.json",
        "artifacts/phase8_bridge/one_shot_custody_20260830_v3.json",
        "artifacts/phase8_bridge/owner_authorization_20260830_v1.json",
        "artifacts/phase8_bridge/result_20260830_v1.json",
        "artifacts/phase8_bridge/dispersion_audit_20260830_v1.json",
        "reports/phase8a_exploratory_bridge_addendum_v1.md",
        "reports/phase8a_exploratory_bridge_addendum_v2.md",
    ):
        assert registered[relative] == _module._sha(REPO / relative)
