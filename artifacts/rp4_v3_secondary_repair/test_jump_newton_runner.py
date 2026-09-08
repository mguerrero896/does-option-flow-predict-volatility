"""Synthetic/mocked failed-only custody; no empirical data or endpoint reads."""

from __future__ import annotations

import copy
import json
from contextlib import contextmanager

import numpy as np
import pytest
from artifacts.rp4_v3_secondary_repair import jump_newton_runner as run
from artifacts.rp4_v3_secondary_repair.test_jump_runner import linear_fit, sample


def numerical_failure():
    return {
        "reason": "RP4_V3_LOGISTIC_REPAIR_NOT_CONVERGED:SYNTHETIC",
        "diagnostics": {
            "converged": False,
            "original_gradient_certificate_applicable": True,
            "gtol": 1e-8,
            "ftol": 1e-12,
            "maxiter": 1000,
            "lambda": 0.0001,
            "stable_gradient_inf_norm": 1.02e-8,
            "gradient_inf_norm_objective_over_n": 1.02e-8,
            "objective_total_divided_by_n": 0.65,
            "objective_initial_divided_by_n": 0.69,
            "literal_original_objective_abs_difference": 0.0,
            "literal_original_gradient_max_abs_difference": 1e-18,
        },
    }


def certified_fit():
    fit = linear_fit(1e-9)
    for d in [fit["solver_refit"], *(c["solver"] for c in fit["candidates"])]:
        d["stable_gradient_inf_norm"] = 1e-9
        d["original_gradient_certificate_applicable"] = True
        d["single_class_training"] = False
    return fit


def test_eligibility_is_only_failure_metadata_not_score_or_success():
    component = {
        "status": "NO VERIFICABLE",
        "provenance": "NEW_MISSING_COMPONENT",
        "model": "jump__log_ridge_harq__B2",
        "failure": numerical_failure(),
    }
    assert run.eligible_failure(component)
    success = {**component, "status": "COMPUTED"}
    assert not run.eligible_failure(success)
    assert not run.eligible_failure({**component, "model": "jump__lightgbm_qlike__B2"})
    assert not run.eligible_failure(
        {**component, "failure": {"reason": "linear_algebra_failure", "diagnostics": {}}}
    )
    for key, value in (
        ("gradient_inf_norm_objective_over_n", float("nan")),
        ("literal_original_objective_abs_difference", 1e-4),
        ("objective_total_divided_by_n", 1.0),
        ("gtol", 2e-8),
    ):
        altered = copy.deepcopy(component)
        altered["failure"]["diagnostics"][key] = value
        assert not run.eligible_failure(altered)


def test_completed_new_component_requires_each_gradient_certificate():
    component = {"status": "COMPUTED", "fit": certified_fit()}
    run.validate_new_result(component)
    component["fit"]["candidates"][2]["solver"]["gradient_inf_norm_objective_over_n"] = 1.01e-8
    with pytest.raises(ValueError, match="NOT_CERTIFIED"):
        run.validate_new_result(component)


def test_delegated_first_validator_rejection_prevents_loading_or_fitting(tmp_path, monkeypatch):
    panel_path = tmp_path / "synthetic_panel.bin"
    panel_path.write_bytes(b"synthetic predictor and historical labels")
    lock = tmp_path / "uv.lock"
    lock.write_bytes(b"synthetic locked environment")
    release_path = tmp_path / "first_release.json"
    release = {
        "panel_sha256": run.base.sha256(panel_path),
        "lockfile_sha256": run.base.sha256(lock),
        "python_version": run.sys.version,
        "code_sha256": {"SYNTHETIC": "HASH"},
        "dependencies": {"numpy": "synthetic-version"},
    }
    run.base.write_json_once(release_path, release)
    monkeypatch.setattr(run, "ROOT", tmp_path)
    monkeypatch.setattr(run.first, "RELEASE_PATH", release_path)
    monkeypatch.setattr(run, "FIRST_RELEASE_SHA", run.base.sha256(release_path))
    validator_calls = []

    def frozen_validator_stub():
        validator_calls.append(1)
        if run.base.sha256(panel_path) != release["panel_sha256"]:
            raise ValueError("RP4_JUMP_REPAIR_PANEL_DRIFT")
        if run.base.sha256(lock) != release["lockfile_sha256"]:
            raise ValueError("FROZEN_RELEASE_DIFFERENT_ENVIRONMENT")
        return release

    monkeypatch.setattr(run.first, "prepare", frozen_validator_stub)
    assert run.verify_first_inputs()["panel_sha256"] == release["panel_sha256"]
    assert len(validator_calls) == 1
    panel_path.write_bytes(b"changed predictor; test keys are still identical")
    calls = []
    with pytest.raises(ValueError, match="PANEL_DRIFT"):
        run.verify_first_inputs()
        calls.append("would load or fit")
    assert calls == []
    panel_path.write_bytes(b"synthetic predictor and historical labels")
    lock.write_bytes(b"changed environment")
    with pytest.raises(ValueError, match="DIFFERENT_ENVIRONMENT"):
        run.verify_first_inputs()


def test_mock_adapter_refits_only_failed_linear_and_preserves_successes(tmp_path, monkeypatch):
    panel, spec = sample()
    old_root, new_root = tmp_path / "first", tmp_path / "newton"
    monkeypatch.setattr(run.first, "OUT", old_root)
    monkeypatch.setattr(run, "OUT", new_root)
    monkeypatch.setattr(run.first.pd, "read_parquet", lambda *a, **k: panel.copy())
    monkeypatch.setattr(run.first.v3, "evaluation_panel_path", lambda *_: tmp_path / "SYNTHETIC")
    prepared = run.first.prepared_panel(spec, "primary")
    keys = prepared[0].iloc[-4:][run.first.base.KEYS].to_dict("records")
    labels = prepared[3][-4:].tolist()
    session = keys[0]["session_date"]
    bad_model = "jump__log_ridge_harq__B2"
    old_sha, rows = {}, []
    for model in run.first.inventory.MODELS:
        bad = model == bad_model
        component = {
            "binding": {
                "window": "primary",
                "endpoint": "jump",
                "release_sha256": run.FIRST_RELEASE_SHA,
            },
            "session": session,
            "model": model,
            "keys_sha256": run.first.inventory.canonical_digest(keys),
            "labels_sha256": run.first.inventory.canonical_digest(labels),
            "N_origins": 4,
            "status": "NO VERIFICABLE" if bad else "COMPUTED",
            "provenance": "NEW_MISSING_COMPONENT",
            "forecast": None if bad else [0.4, 0.6, 0.4, 0.6],
            "failure": numerical_failure() if bad else None,
            "fit": {} if bad else certified_fit(),
            "elapsed_seconds": 0.1,
        }
        path = old_root / "evaluation/primary/components" / session / f"{model}.json"
        run.first.base.write_json_once(path, component)
        digest = run.first.base.sha256(path)
        old_receipt = old_root / "evaluation/primary/component_receipts" / session / f"{model}.json"
        run.base.write_json_once(old_receipt, {"binding": component["binding"], "sha256": digest})
        old_sha[str(path)] = digest
        rows.append(
            {
                "session": session,
                "model": model,
                "first_component_sha256": digest,
                "first_component_receipt_sha256": run.base.sha256(old_receipt),
                "eligible_newton": bad,
            }
        )
    source = {
        "session": session,
        "keys": keys,
        "jump_positions": [0, 1, 2, 3],
        "jump_target": labels,
    }
    new_inventory = {
        "windows": [
            {
                "window": "primary",
                "components": rows,
                "eligible_components": 1,
                "first_session_sha256": {session: "ORIGINAL_SESSION"},
            }
        ]
    }
    run.first.base.write_json_once(new_root / "inventory.json", new_inventory)
    release = {
        "code_sha256": {"MOCK": "HASH"},
        "inventory_sha256": run.first.base.sha256(new_root / "inventory.json"),
    }
    run.first.base.write_json_once(new_root / "release.json", release)
    monkeypatch.setattr(run, "prepare", lambda *a: release)
    monkeypatch.setattr(run, "code_hashes", lambda: {"MOCK": "HASH"})
    monkeypatch.setattr(run, "source_records", lambda *a: [source])
    reader = run.first.inventory.read_verified
    monkeypatch.setattr(
        run.first.inventory,
        "read_verified",
        lambda path, digest: (
            {"windows": [{"window": "primary"}]}
            if path == run.first.INVENTORY_PATH
            else reader(path, digest)
        ),
    )
    monkeypatch.setattr(run.first.v3, "load_spec", lambda *a: spec)
    monkeypatch.setattr(run.first.v3, "tail_options", lambda *a: {})
    monkeypatch.setattr(run.first, "prepared_panel", lambda *a: prepared)

    @contextmanager
    def resources():
        yield {"threads_total_max": 2, "priority": "BELOW_NORMAL", "process_id": 0}

    monkeypatch.setattr(run.first, "resource_scope", resources)
    calls = []

    def fitting(design, target, train, inner, valid, test, nullable, dates, assets, options):
        calls.append(1)
        assert len(np.unique(dates[valid])) == 10 and dates[train].max() < session
        return np.full(int(test.sum()), 0.55), certified_fit()

    monkeypatch.setattr(run.solver, "fit_jump_linear", fitting)

    def forbidden(*args, **kwargs):
        raise AssertionError("No mean, quantile, MZ, LGB or complete aggregate")

    for module, names in (
        (
            run.first.original,
            ("fit_jump", "fit_ridge", "fit_lightgbm", "fit_quantile", "mz_secondary"),
        ),
        (run.first.aggregate, ("aggregate_records", "_mz", "_quantile")),
    ):
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    summary = run.run_window("primary", tmp_path / "METHOD", "MOCK")
    assert len(calls) == 1
    assert summary["successful_components_refitted"] == 0
    assert summary["eligible_newton_components"] == 1
    assert summary["jump_secondary"]["N_origins"] == 4
    assert {r["lineage"]: r["N"] for r in summary["component_counts"]} == {
        "REUSED_FIRST_REPAIR_SUCCESS": 5,
        "NEWTON_FAILED_ONLY_ATTEMPT": 1,
    }
    assert run.run_window("primary", tmp_path / "METHOD", "MOCK") == summary
    assert len(calls) == 1
    assert all(run.first.base.sha256(run.Path(path)) == digest for path, digest in old_sha.items())
    output = new_root / "evaluation/primary"
    log = new_root / "synthetic_stdout.log"
    log.write_text("synthetic complete CLI", encoding="utf-8")
    final_receipt = {
        "status": "COMPLETE",
        "exit_code": 0,
        "binding": summary["binding"],
        "code_sha256": run.code_hashes(),
        "log": str(log),
        "log_sha256": run.base.sha256(log),
        "artifacts_sha256": {
            str(output / name): run.base.sha256(output / name)
            for name in (
                "summary.json",
                "fit_diagnostics.json",
                "component_manifest.json",
                "summary_receipt.json",
            )
        },
    }
    run.base.write_json_once(output / "receipt.json", final_receipt)
    assert run.verify_closeout(output, summary["binding"]) == summary
    new_component_path = output / "components" / session / f"{bad_model}.json"
    original_bytes = new_component_path.read_bytes()
    new_component_path.write_bytes(original_bytes + b" ")
    with pytest.raises(ValueError):
        run.verify_closeout(output, summary["binding"])
    new_component_path.write_bytes(original_bytes)
    assert len(calls) == 1
    session_path = new_root / "evaluation/primary/sessions" / f"{session}.json"
    receipt_path = new_root / "evaluation/primary/session_receipts" / session_path.name
    session_bytes = session_path.read_bytes()
    session_path.unlink()
    with pytest.raises(ValueError, match="CLOSEOUT_SESSION_SET_DRIFT"):
        run.verify_closeout(output, summary["binding"])
    session_path.write_bytes(session_bytes)
    altered = json.loads(session_path.read_text(encoding="utf-8"))
    altered["tail_forecasts"]["jump"]["log_ridge_harq"]["B2"][0] = 0.99
    session_path.write_text(json.dumps(altered), encoding="utf-8")
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["sha256"] = run.first.base.sha256(session_path)
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ValueError, match="RESUME_SESSION_PARITY_DRIFT"):
        run.run_window("primary", tmp_path / "METHOD", "MOCK")
    assert len(calls) == 1
