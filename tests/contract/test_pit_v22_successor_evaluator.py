"""The signed PIT v2.2 successor contract must be executable exactly once."""

from __future__ import annotations

import ast
import hashlib
import importlib.util
import json
from datetime import date, timedelta
from pathlib import Path
from types import ModuleType
from typing import Any

import polars as pl
import pytest

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


def _runner_module() -> ModuleType:
    assert RUNNER.is_file(), "PIT_V22_SUCCESSOR_RUNNER_MISSING"
    spec = importlib.util.spec_from_file_location("pit_v22_successor_runner", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def test_runner_pins_the_physical_signed_input_hashes() -> None:
    runner = _runner_module()

    assert hashlib.sha256(FREEZE.read_bytes()).hexdigest() == runner.EXPECTED_SIGNED_FREEZE_SHA256
    assert (
        hashlib.sha256(AUTHORIZATION.read_bytes()).hexdigest()
        == runner.EXPECTED_OWNER_AUTHORIZATION_SHA256
    )


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


def test_successor_split_fixes_equal_remainder_halves_before_targets() -> None:
    runner = _runner_module()
    start = date(2025, 8, 4)
    sessions = [(start + timedelta(days=index)).isoformat() for index in range(159)]

    split = runner.successor_session_split(sessions)

    assert len(split["development"]) == 95
    assert len(split["validation"]) == 32
    assert len(split["holdout"]) == 32
    assert [*split["development"], *split["validation"], *split["holdout"]] == sessions


def test_target_linkage_excludes_predictor_complete_rows_with_missing_rv30() -> None:
    runner = _runner_module()
    source = pl.DataFrame(
        {
            "origin_id": ["kept", "target-missing"],
            "common_predictor_complete": [True, True],
        }
    )
    targets = pl.DataFrame(
        {
            "origin_id": ["kept", "target-missing"],
            "target_price_count": [31, 30],
            "target_return_count": [30, 0],
            "rv30": [0.1, None],
        }
    )
    common = pl.DataFrame({"origin_id": ["kept"]})

    runner._validate_target_linkage(source, targets, common)


def test_one_shot_claim_rejects_a_second_process(tmp_path: Path) -> None:
    runner = _runner_module()
    claim = tmp_path / "successor.claim"

    runner.claim_one_shot(claim, {"contract_sha256": "a" * 64})

    with pytest.raises(FileExistsError, match="PIT_V22_SUCCESSOR_ALREADY_CLAIMED"):
        runner.claim_one_shot(claim, {"contract_sha256": "a" * 64})


def test_public_outputs_are_exclusive_and_reject_absolute_paths(tmp_path: Path) -> None:
    runner = _runner_module()
    output = tmp_path / "result.json"
    digest = runner._write_new_json(output, {"status": "PASS"})

    assert digest == hashlib.sha256(output.read_bytes()).hexdigest()

    with pytest.raises(FileExistsError, match="TRACKED_OUTPUT_ALREADY_EXISTS"):
        runner._write_new_json(output, {"status": "OVERWRITE"})
    with pytest.raises(RuntimeError, match="PERSONAL_PATH_IN_PUBLIC_PAYLOAD"):
        runner._assert_public_payload({"path": "X:/private/outcome.parquet"})


def test_evaluator_is_called_once_on_holdout_only() -> None:
    tree = ast.parse(RUNNER.read_text(encoding="utf-8"))
    calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "evaluate_phase6"
    ]

    assert len(calls) == 1
    assert isinstance(calls[0].args[0], ast.Name)
    assert calls[0].args[0].id == "holdout_predictions"


def test_one_shot_runner_wires_only_the_frozen_producers() -> None:
    assert RUNNER.is_file(), "PIT_V22_SUCCESSOR_RUNNER_MISSING"
    source = RUNNER.read_text(encoding="utf-8")
    required = {
        "build_phase6_common_panel",
        "build_phase6_origins",
        "validate_phase6_evaluation_panel",
        "training_mde_from_forecasts",
        "authorize_phase6_oos",
        "training_only_oof_forecasts",
        "forecast_phase6_fold",
        "evaluate_phase6",
        "DEFAULT_TRAIN_SHARE",
        "assert_outside_frozen",
        "write_content_addressed",
    }
    assert not (missing := {name for name in required if name not in source}), sorted(missing)
    assert "D:\\MDS650" not in source
    assert 'freeze["provenance"]["preregistration_sha256"]' in source
    assert '"scientific_result_eligible": True' not in source
    assert '"scientific_result_eligible": False' in source


def test_public_log_is_sealed_after_result_and_custody_closeout() -> None:
    source = RUNNER.read_text(encoding="utf-8")
    writer = source[
        source.index("def _write_new_json") : source.index("def _assert_public_payload")
    ]
    result_write = source.index("_write_new_json(TRACKED_RESULT, result)")
    ledger_close = source.index('_write_json(paths["ledger"], completed_ledger)', result_write)
    claim_close = source.index('paths["claim"]', ledger_close)
    result_event = source.index('"RESULT_WRITTEN"', result_write)
    ledger_event = source.index('"LEDGER_CLOSED"', result_event)
    claim_event = source.index('"CLAIM_CLOSED"', ledger_event)
    log_write = source.index("_write_new_json(TRACKED_LOG, public_log)", claim_event)

    assert result_write < result_event < ledger_close < ledger_event
    assert ledger_event < claim_close < claim_event < log_write
    assert writer.index("digest =") < writer.index("os.link")
    assert '_sha256(paths["method"]) != runtime_method_sha256' in source
