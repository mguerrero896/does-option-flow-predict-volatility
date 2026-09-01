"""The replacement PIT v2.2 contract must be isolated from the consumed v1 run."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import ModuleType
from typing import Any

from mds650.phase6_evaluation import authorize_phase6_oos
from mds650.study_design import canonical_sha256


REPO = Path(__file__).resolve().parents[2]
ARTIFACTS = REPO / "artifacts" / "target_blind_v22"
FREEZE = ARTIFACTS / "successor_method_freeze_v2.json"
AUTHORIZATION = ARTIFACTS / "successor_owner_authorization_v2.json"
RESOLUTION = ARTIFACTS / "target_source_discrepancy_resolution_v1.json"
RUNNER = REPO / "scripts" / "run_pit_v22_successor_once.py"


def _load(path: Path) -> dict[str, Any]:
    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return payload


def _runner_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("pit_v22_successor_v2_runner", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_v2_contract_binds_complete_case_resolution_and_fresh_authorization() -> None:
    resolution = _load(RESOLUTION)
    resolution_unsigned = {
        key: value for key, value in resolution.items() if key != "manifest_sha256"
    }
    freeze = _load(FREEZE)
    authorization = _load(AUTHORIZATION)

    assert resolution["manifest_sha256"] == canonical_sha256(resolution_unsigned)
    assert resolution["decision"] == "PROSPECTIVE_COMPLETE_CASE_EXCLUSION_NO_IMPUTATION"
    assert resolution["oos_read_count"] == 0
    assert freeze["target_linkage_eligibility_policy"] == {
        "eligible_origin_set": "PREDICTOR_COMPLETE_INTERSECT_TARGET_COMPLETE",
        "required_target_price_count": 31,
        "required_target_return_count": 30,
        "require_finite_rv30": True,
        "missing_target_action": "EXCLUDE_ORIGIN",
        "imputation": "FORBIDDEN",
        "cross_provider_bar_substitution": "FORBIDDEN",
    }
    assert freeze["data_defect_resolution_sha256"] == hashlib.sha256(
        RESOLUTION.read_bytes()
    ).hexdigest()
    assert authorization["protocol_id"] == "pit-v22-successor-method-freeze-v2"
    assert authorization["contract_sha256"] == hashlib.sha256(FREEZE.read_bytes()).hexdigest()
    assert authorization["sealed_cohorts_read_before"] == 0


def test_v2_authorization_is_accepted_by_the_shared_single_use_gate() -> None:
    freeze = _load(FREEZE)
    authorization = _load(AUTHORIZATION)

    consumed = authorize_phase6_oos(
        authorization,
        common_panel_sha256=freeze["bound_panel_sha256"],
        preregistration_manifest_sha256=freeze["provenance"]["preregistration_sha256"],
        results_exist=False,
        contract_sha256=hashlib.sha256(FREEZE.read_bytes()).hexdigest(),
    )

    assert consumed["status"] == "OOS_EVALUATION_IN_PROGRESS"
    assert consumed["oos_read_count"] == 1
    assert consumed["evaluation_attempt_count"] == 1


def test_runner_selects_a_fresh_v2_run_without_mutating_v1_defaults() -> None:
    runner = _runner_module()
    v1_run_id = runner.RUN_ID

    runner.configure_protocol("v2")

    assert v1_run_id == "pit-v22-successor-evaluation-v1-20260901"
    assert runner.RUN_ID == "pit-v22-successor-evaluation-v2-20260902"
    assert runner.SIGNED_FREEZE.name == "successor_method_freeze_v2.json"
    assert runner.OWNER_AUTHORIZATION.name == "successor_owner_authorization_v2.json"
    assert runner.TRACKED_RESULT.name == "successor_evaluation_result_v2.json"
    assert runner.TRACKED_LOG.name == "successor_evaluation_run_v2.json"


def test_v2_runner_does_not_equate_predictor_complete_with_target_complete_count() -> None:
    source = RUNNER.read_text(encoding="utf-8")

    assert 'common.height != 62_266' not in source
    assert "PREDICTOR_COMPLETE_INTERSECT_TARGET_COMPLETE" in source
