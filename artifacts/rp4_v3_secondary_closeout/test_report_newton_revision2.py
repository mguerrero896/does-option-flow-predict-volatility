"""Synthetic two-pass report tests; execute only after the first-pass resource cap is free."""

from __future__ import annotations

import ast
import copy
import hashlib
import json
from pathlib import Path
from typing import Any

import pytest
from artifacts.rp4_v3_secondary_closeout import report_newton_revision2 as newton
from artifacts.rp4_v3_secondary_closeout import report_revision2 as prior
from artifacts.rp4_v3_secondary_closeout.test_report_revision2 import (
    fixture_evidence,
    fixture_window,
)


def two_pass_fixture() -> tuple[dict[str, Any], dict[str, Any]]:
    first = fixture_evidence()
    final = fixture_evidence()
    for bundle in final["windows"].values():
        bundle["provenance_rows"] = [
            {
                "family": "log_ridge_harq",
                "provenance": "NEWTON_FAILED_ONLY",
                "N_components": 1,
                "computed": 1,
                "failed": 0,
            }
        ]
        bundle["solver_audit"] = [
            {
                "session": "2025-03-26",
                "model": "jump__log_ridge_harq__B2",
                "phase": "candidate",
                "status": "COMPUTED",
                "first_attempt_lbfgs_iterations": 27,
                "new_call_lbfgs_iterations": 27,
                "newton_attempted_steps": 1,
                "newton_accepted_steps": 1,
                "first_attempt_gradient": 1.0227e-8,
                "final_gradient": 1e-9,
                "certificate_status": "CERTIFIED",
            }
        ]
        for family in bundle["summary"]["jump_secondary"]["families"]:
            for row in family["auc"].values():
                row["estimate"] = 0.57
    return first, final


def test_first_and_final_auc_are_both_reported_without_primary_change() -> None:
    first, final = two_pass_fixture()
    encoded = newton.render(first, final)
    text = encoded.decode()
    assert prior.primary_block(encoded) == first["primary_block"]
    assert "| 0.55 |" in text and "| 0.57 |" in text
    assert "resultado final combinado" in text
    assert "Primer pase de salto: resultados preservados" in text
    assert "MZ: NO VERIFICABLE" in text
    assert "no se reclasifica como éxito del primer pase" in text


def test_newton_failure_and_unknown_cost_remain_visible() -> None:
    first, final = two_pass_fixture()
    bundle = final["windows"]["primary"]
    bundle["provenance_rows"][0].update(computed=0, failed=1)
    bundle["solver_audit"][0].update(
        status="NO VERIFICABLE",
        certificate_status="NO VERIFICABLE",
        first_attempt_lbfgs_iterations=None,
        final_gradient=None,
    )
    text = newton.render(first, final).decode()
    assert "NEWTON_FAILED_ONLY | 1 | 0 | 1" in text
    assert "candidate | NO VERIFICABLE | NO VERIFICABLE" in text
    assert "reconstruir" in text


def test_monoclass_final_auc_is_not_zero_or_promoted() -> None:
    first, final = two_pass_fixture()
    row = final["windows"]["primary"]["summary"]["jump_secondary"]["families"][0]["auc"]["B0"]
    row.update(
        estimate=None, ci_low=None, ci_high=None, status="NO VERIFICABLE", reason="monoclase"
    )
    text = newton.render(first, final).decode()
    assert "B0 | NO VERIFICABLE | [NO VERIFICABLE, NO VERIFICABLE]" in text
    assert "monoclase" in text


def test_missing_or_duplicate_anchor_fails_closed() -> None:
    for text in ("missing", "xx"):
        with pytest.raises(ValueError, match="ANCHOR_DRIFT"):
            newton.replace_once(text, "x", "new")


def test_no_training_or_inference_calls_exist() -> None:
    tree = ast.parse(Path(newton.__file__).read_text(encoding="utf-8"))
    calls = [
        ast.unparse(node.func).split(".")[-1]
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
    ]
    assert not set(calls).intersection(
        {
            "fit_jump_linear",
            "fit_jump_lightgbm",
            "minimize",
            "_jump",
            "pooled_auc_inference",
            "read_parquet",
        }
    )


def lineage_fixture() -> tuple[Any, ...]:
    first = fixture_window()
    fits = copy.deepcopy(first["fits"])
    summary = copy.deepcopy(first["summary"])
    summary["binding"]["release_sha256"] = "f" * 64
    summary.update(
        eligible_newton_components=0,
        successful_components_refitted=0,
        prior_attempts_preserved=True,
    )
    manifest, components = [], []
    for row in fits:
        original = row["provenance"] == "REUSED_FROZEN_V3"
        lineage = "REUSED_ORIGINAL_V3" if original else "REUSED_FIRST_REPAIR_SUCCESS"
        row.update(
            lineage=lineage, prior_attempt_elapsed_seconds=0.2, new_attempt_elapsed_seconds=0
        )
        for penalty, candidate in zip(
            [0.0001, 0.01, 1, 100, 10000], row["fit"]["candidates"], strict=True
        ):
            candidate["lambda"] = penalty
        manifest.append(
            {
                "session": row["session"],
                "model": row["model"],
                "status": row["status"],
                "lineage": lineage,
                "first_component_sha256": "a" * 64,
                "first_component_receipt_sha256": "b" * 64,
                "component_receipt_sha256": "b" * 64,
                "sha256": "a" * 64,
                "outcome": "PRESERVED_SUCCESS",
            }
        )
        components.append(
            {
                "session": row["session"],
                "model": row["model"],
                "eligible_newton": False,
                "first_status": "COMPUTED",
                "first_component_sha256": "a" * 64,
                "first_component_receipt_sha256": "b" * 64,
            }
        )
    first["fits"] = copy.deepcopy(fits)
    summary["component_counts"] = [
        {"lineage": lineage, "status": "COMPUTED", "N": 6}
        for lineage in ("REUSED_ORIGINAL_V3", "REUSED_FIRST_REPAIR_SUCCESS")
    ]
    plan = {"components": components, "eligible_components": 0}
    return first, summary, fits, manifest, plan


def test_all_successes_are_preserved_without_newton() -> None:
    first, summary, fits, manifest, plan = lineage_fixture()
    census, audit = newton.validate_lineage(first, summary, fits, manifest, plan, "f" * 64)
    assert audit == []
    assert sum(row["N_components"] for row in census) == 12
    assert (
        sum(
            row["N_components"]
            for row in census
            if row["provenance"] == "NEWTON_FAILED_ONLY_ATTEMPT"
        )
        == 0
    )


def test_success_cannot_be_selected_for_newton() -> None:
    first, summary, fits, manifest, plan = lineage_fixture()
    plan["components"][6]["eligible_newton"] = True
    with pytest.raises(ValueError, match="ELIGIBILITY_DRIFT"):
        newton.validate_lineage(first, summary, fits, manifest, plan, "f" * 64)


def test_preserved_success_cannot_change_coefficients_or_cost() -> None:
    first, summary, fits, manifest, plan = lineage_fixture()
    fits[6]["fit"]["new_coefficients"] = [1.0]
    with pytest.raises(ValueError, match="SUCCESS_OR_INELIGIBLE_CHANGED"):
        newton.validate_lineage(first, summary, fits, manifest, plan, "f" * 64)


def test_prior_failure_cost_is_reported_once_not_per_lambda() -> None:
    old = {
        "session": "2025-03-26",
        "model": "jump__log_ridge_harq__B2",
        "status": "NO VERIFICABLE",
        "failure": {
            "diagnostics": {
                "lambda": 0.0001,
                "iterations": 27,
                "gradient_inf_norm_objective_over_n": 1.0227e-8,
            }
        },
    }
    current = lineage_fixture()[2][6]
    rows = newton.solver_audit(old, current)
    assert sum(row.get("first_attempt_lbfgs_iterations", 0) for row in rows) == 27
    assert len(rows) == 7
    assert "fase no guardada" in rows[0]["phase"]
    assert rows[1].get("first_attempt_gradient") is None


def test_incomplete_newton_closure_cannot_open_first_auc(tmp_path: Path, monkeypatch: Any) -> None:
    hashes = {}
    for window in prior.WINDOWS:
        path = tmp_path / "newton" / "evaluation" / window / "receipt.json"
        path.parent.mkdir(parents=True)
        path.write_text(
            json.dumps(
                {
                    "status": "COMPLETE" if window == "primary" else "RUNNING",
                    "exit_code": 0,
                    "binding": {"release_sha256": "f" * 64, "window": window, "endpoint": "jump"},
                }
            ),
            encoding="utf-8",
        )
        hashes[window] = hashlib.sha256(path.read_bytes()).hexdigest()
    monkeypatch.setattr(prior, "load_evidence", lambda *a: pytest.fail("must not open first AUC"))
    with pytest.raises(ValueError, match="NEWTON_WINDOW_NOT_CLOSED:confirmation"):
        newton.load_evidence(
            tmp_path, tmp_path / "first", tmp_path / "newton", "f" * 64, {}, hashes
        )


def test_existing_revision2_is_never_overwritten(tmp_path: Path, monkeypatch: Any) -> None:
    path = tmp_path / prior.REPORT
    path.parent.mkdir(parents=True)
    path.write_bytes(b"KEEP")
    monkeypatch.setattr(newton, "load_evidence", lambda *a: pytest.fail("must not load"))
    with pytest.raises(ValueError, match="OUTPUT_ALREADY_EXISTS"):
        newton.execute(tmp_path, tmp_path / "first", tmp_path / "newton", "f" * 64, {}, {}, "test")
    assert path.read_bytes() == b"KEEP"
