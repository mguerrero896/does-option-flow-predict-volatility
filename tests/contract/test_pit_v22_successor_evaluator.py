"""The signed PIT v2.2 successor contract must be executable exactly once."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from mds650.phase6 import (
    B0V2_FEATURES,
    B1V2A_FEATURES,
    B1V2B_FEATURES,
    B1V2C_FEATURES,
    B2V2_FEATURES,
)
from mds650.phase6_evaluation import (
    authorize_phase6_oos,
    phase6_fold_definitions,
    phase6_information_sets,
)

REPO = Path(__file__).resolve().parents[2]
ARTIFACTS = REPO / "artifacts" / "target_blind_v22"
FREEZE = ARTIFACTS / "successor_method_freeze_v1.json"
AUTHORIZATION = ARTIFACTS / "successor_owner_authorization_v1.json"
RUNNER = REPO / "scripts" / "run_pit_v22_successor_once.py"


def _load(path: Path) -> dict[str, Any]:
    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return payload


def test_signed_successor_authorization_is_accepted_by_oos_gate() -> None:
    freeze = _load(FREEZE)
    authorization = _load(AUTHORIZATION)
    contract_sha256 = hashlib.sha256(FREEZE.read_bytes()).hexdigest()

    consumed = authorize_phase6_oos(
        authorization,
        common_panel_sha256=freeze["bound_panel_sha256"],
        preregistration_manifest_sha256=freeze["provenance"]["preregistration_sha256"],
        results_exist=False,
        contract_sha256=contract_sha256,
    )

    assert consumed["status"] == "OOS_EVALUATION_IN_PROGRESS"
    assert consumed["oos_read_count"] == 1
    assert consumed["evaluation_attempt_count"] == 1
    assert consumed["owner_authorization"]["authorized_by"] == authorization["authorized_by"]


def test_successor_information_sets_include_registered_b1_robustness() -> None:
    sets = phase6_information_sets(include_b1_robustness=True)

    assert sets["B0v2"] == B0V2_FEATURES
    assert sets["B1v2a"] == (*B0V2_FEATURES, *B1V2A_FEATURES)
    assert sets["B1v2b"] == (*sets["B1v2a"], *B1V2B_FEATURES)
    assert sets["B1v2c"] == (*sets["B1v2b"], *B1V2C_FEATURES)
    assert sets["B2v2"] == (*sets["B1v2a"], *B2V2_FEATURES)


def test_successor_folds_accept_development_validation_and_holdout() -> None:
    preregistration = {
        "schema_version": "pit-v22-successor-runtime-preregistration-1.0",
        "folds": [
            {
                "fold": 1,
                "train_dates": ["2026-01-01", "2026-01-02", "2026-01-03"],
                "test_dates": ["2026-01-04"],
            },
            {
                "fold": 2,
                "train_dates": [
                    "2026-01-01",
                    "2026-01-02",
                    "2026-01-03",
                    "2026-01-04",
                ],
                "test_dates": ["2026-01-05"],
            },
        ],
    }

    folds = phase6_fold_definitions(preregistration)

    assert [fold.fold for fold in folds] == [1, 2]
    assert folds[0].train_end.isoformat() == "2026-01-03"
    assert folds[1].test_start.isoformat() == "2026-01-05"


def test_one_shot_runner_wires_only_the_frozen_producers() -> None:
    assert RUNNER.is_file(), "PIT_V22_SUCCESSOR_RUNNER_MISSING"
    source = RUNNER.read_text(encoding="utf-8")
    required = {
        "build_phase6_common_panel",
        "build_phase6_origins",
        "validate_phase6_evaluation_panel",
        "estimate_training_mde",
        "authorize_phase6_oos",
        "training_only_oof_forecasts",
        "forecast_phase6_fold",
        "evaluate_phase6",
        "DEFAULT_TRAIN_SHARE",
    }
    assert not (required - set(source.split())), sorted(required - set(source.split()))
