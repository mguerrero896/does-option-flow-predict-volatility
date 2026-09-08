"""Failed-only secondary adapter; never refits a successful first-repair component."""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import subprocess
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from artifacts.rp4_code import evaluate as base
from artifacts.rp4_v2_code.execute import window_lock
from artifacts.rp4_v3_code import aggregate_v3 as aggregate
from artifacts.rp4_v3_code import evaluate_v3 as v3
from artifacts.rp4_v3_secondary_repair import jump_inventory as inventory
from artifacts.rp4_v3_secondary_repair import jump_newton as solver
from artifacts.rp4_v3_secondary_repair import jump_repair as prior
from artifacts.rp4_v3_secondary_repair import jump_runner as first

ROOT = first.ROOT
OUT = first.OUT / "newton_failed_only_v1"
FIRST_RELEASE_SHA = "7565795ddd4938f4c84068b2c2bb30c01905092150fb78c56aefa7626ca46bed"
METHOD_SHA = "529067473ff602d47e0466426ce2af2e0f525d1ac5e42b4fd4230e38d17c52fa"
SOURCE_PATHS = (
    *first.SOURCE_PATHS,
    "artifacts/rp4_v3_secondary_repair/jump_newton.py",
    "artifacts/rp4_v3_secondary_repair/jump_newton_runner.py",
)
TEST_PATHS = (
    "artifacts/rp4_v3_secondary_repair/test_jump_newton.py",
    "artifacts/rp4_v3_secondary_repair/test_jump_newton_runner.py",
)


def code_hashes() -> dict[str, str]:
    return {name: base.sha256(ROOT / name) for name in SOURCE_PATHS}


def validate_new_result(component: dict[str, Any]) -> None:
    if component["status"] != "COMPUTED":
        return
    fit = component["fit"]
    if (
        fit.get("objective") != "sum_binary_logloss_plus_lambda_l2_slopes"
        or fit.get("lambda_grid") != list(prior.REGISTERED_GRID)
        or len(fit.get("candidates", [])) != 5
        or [c.get("lambda") for c in fit["candidates"]] != list(prior.REGISTERED_GRID)
    ):
        raise ValueError("RP4_NEWTON_NEW_COMPONENT_OBJECTIVE_OR_GRID_DRIFT")
    for diagnostic in [fit["solver_refit"], *(c["solver"] for c in fit["candidates"])]:
        if diagnostic.get("converged") is not True:
            raise ValueError("RP4_NEWTON_NEW_COMPONENT_NOT_CERTIFIED")
        if (
            diagnostic.get("original_gradient_certificate_applicable") is False
            and diagnostic.get("single_class_training") is True
        ):
            continue
        gradients = [
            diagnostic.get(k)
            for k in ("stable_gradient_inf_norm", "gradient_inf_norm_objective_over_n")
        ]
        if diagnostic.get("original_gradient_certificate_applicable") is not True or any(
            not isinstance(g, (int, float)) or not math.isfinite(g) or g > 1e-8 or g < 0
            for g in gradients
        ):
            raise ValueError("RP4_NEWTON_NEW_COMPONENT_NOT_CERTIFIED")


def eligible_failure(component: dict[str, Any]) -> bool:
    """Predicate uses numerical diagnostics only, never validation/AUC outcomes."""
    if (
        component.get("status") != "NO VERIFICABLE"
        or not str(component.get("model", "")).startswith("jump__log_ridge_harq__")
        or component.get("provenance") != "NEW_MISSING_COMPONENT"
    ):
        return False
    failure = component.get("failure") or {}
    diagnostic = failure.get("diagnostics", {})
    names = (
        "stable_gradient_inf_norm",
        "gradient_inf_norm_objective_over_n",
        "objective_total_divided_by_n",
        "objective_initial_divided_by_n",
        "literal_original_objective_abs_difference",
        "literal_original_gradient_max_abs_difference",
    )
    if not all(
        isinstance(diagnostic.get(k), (int, float)) and math.isfinite(diagnostic[k]) for k in names
    ):
        return False
    return bool(
        str(failure.get("reason", "")).startswith("RP4_V3_LOGISTIC_REPAIR_NOT_CONVERGED:")
        and diagnostic.get("converged") is False
        and diagnostic.get("original_gradient_certificate_applicable") is True
        and diagnostic.get("gtol") == 1e-8
        and diagnostic.get("ftol") == 1e-12
        and diagnostic.get("maxiter") == 1000
        and diagnostic.get("lambda") in prior.REGISTERED_GRID
        and max(diagnostic[k] for k in names[:2]) > 1e-8
        and diagnostic["objective_total_divided_by_n"]
        <= diagnostic["objective_initial_divided_by_n"] + 1e-12
        and diagnostic["literal_original_objective_abs_difference"]
        <= 1e-10 * max(1.0, abs(diagnostic["objective_total_divided_by_n"]))
        and diagnostic["literal_original_gradient_max_abs_difference"] <= 1e-10
    )


def source_records(window: str, plan: dict[str, Any]) -> list[dict[str, Any]]:
    binding = {"release_sha256": FIRST_RELEASE_SHA, "window": window, "endpoint": "jump"}
    # This frozen custody validator checks final exit-zero receipts and hashes.
    # Its endpoint values are not consulted, selected on, or recomputed here.
    first.verify_complete_window(first.OUT / "evaluation" / window, binding)
    sources = {(row["session"], row["model"]): row for row in plan["components"]}
    return first.completed_records(
        first.OUT / "evaluation" / window, binding, plan["sessions"], sources
    )


def verify_first_inputs() -> dict[str, Any]:
    """Metadata/content pins before loading any predictors or historical labels."""
    inventory.read_verified(first.RELEASE_PATH, FIRST_RELEASE_SHA)
    # Reuse the frozen validator. write_json_once compares the already-pinned
    # release byte-for-byte/logically; it cannot replace it on any input drift.
    release = first.prepare()
    inventory.read_verified(first.RELEASE_PATH, FIRST_RELEASE_SHA)
    return {
        "panel_sha256": release["panel_sha256"],
        "lockfile_sha256": release["lockfile_sha256"],
        "python_version": release["python_version"],
        "dependencies": release["dependencies"],
    }


def prepare(addendum_path: Path, addendum_sha: str) -> dict[str, Any]:
    addendum = inventory.read_verified(addendum_path, addendum_sha)
    expected = {
        "base_first_repair_release_sha256": FIRST_RELEASE_SHA,
        "threads_total_max": 2,
        "max_newton_steps": 8,
        "max_halvings": 20,
        "armijo": 1e-4,
        "original_gradient_inf_tolerance": 1e-8,
        "solver_total_maxiter": 1000,
        "objective_increase_tolerance": 1e-12,
        "objective_equivalence_relative_tolerance": 1e-10,
        "gradient_equivalence_absolute_tolerance": 1e-10,
        "preserve_all_computed_components": True,
        "require_both_first_pass_windows_complete": True,
        "require_separate_code_test_release_before_empirical_refinement": True,
        "mean_refits": False,
        "quantile_refits": False,
        "mz_refits": False,
    }
    if (
        addendum_sha != METHOD_SHA
        or any(addendum.get(k) != v for k, v in expected.items())
        or Path(addendum["output_root"]).resolve() != OUT
        or Path(addendum["base_first_repair_root"]).resolve() != first.OUT
        or base.sha256(ROOT / addendum["document_path"]) != addendum["document_sha256"]
        or base.sha256(first.RELEASE_PATH) != FIRST_RELEASE_SHA
    ):
        raise ValueError("RP4_NEWTON_ADDENDUM_OR_FIRST_RELEASE_DRIFT")
    qa_path = OUT / "qa_receipt.json"
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    tested_sources = {name: base.sha256(ROOT / name) for name in (*SOURCE_PATHS, *TEST_PATHS)}
    if (
        qa.get("status") != "PASS"
        or qa.get("numeric_tests_executed") is not True
        or qa.get("source_sha256") != tested_sources
        or not qa.get("commands")
        or any(command.get("exit_code") != 0 for command in qa["commands"])
        or {command.get("kind") for command in qa["commands"]}
        != {"pytest", "ruff", "format", "mypy"}
    ):
        raise ValueError("RP4_NEWTON_EXECUTABLE_QA_NOT_VERIFIED")
    first_inputs = verify_first_inputs()
    original_inventory = inventory.read_verified(first.INVENTORY_PATH, first.INVENTORY_SHA)
    windows = []
    for plan in original_inventory["windows"]:
        window = plan["window"]
        rows = []
        records = source_records(window, plan)
        for record in records:
            for model, digest in record["component_sha256"].items():
                path = (
                    first.OUT
                    / "evaluation"
                    / window
                    / "components"
                    / record["session"]
                    / f"{model}.json"
                )
                component = inventory.read_verified(path, digest)
                rows.append(
                    {
                        "session": record["session"],
                        "model": model,
                        "first_component_sha256": digest,
                        "first_component_receipt_sha256": record["component_receipt_sha256"][model],
                        "first_status": component["status"],
                        "eligible_newton": eligible_failure(component),
                        "keys_sha256": component["keys_sha256"],
                        "labels_sha256": component["labels_sha256"],
                        "N_origins": component["N_origins"],
                    }
                )
        windows.append(
            {
                "window": window,
                "first_receipt_sha256": base.sha256(
                    first.OUT / "evaluation" / window / "receipt.json"
                ),
                "first_session_sha256": {
                    r["session"]: base.sha256(
                        first.OUT / "evaluation" / window / "sessions" / f"{r['session']}.json"
                    )
                    for r in records
                },
                "components": rows,
                "eligible_components": sum(r["eligible_newton"] for r in rows),
                "N_sessions": len(records),
            }
        )
    new_inventory = {
        "schema_version": "rp4-v3-jump-newton-failed-only-inventory-v1",
        "first_release_sha256": FIRST_RELEASE_SHA,
        "windows": windows,
    }
    base.write_json_once(OUT / "inventory.json", new_inventory)
    release = {
        "schema_version": "rp4-v3-jump-newton-failed-only-release-v1",
        "addendum_path": str(addendum_path),
        "addendum_sha256": addendum_sha,
        "inventory_sha256": base.sha256(OUT / "inventory.json"),
        "first_release_sha256": FIRST_RELEASE_SHA,
        "original_inventory_sha256": first.INVENTORY_SHA,
        "code_sha256": code_hashes(),
        "rules": expected,
        "test_sha256": {name: tested_sources[name] for name in TEST_PATHS},
        "qa_receipt_sha256": base.sha256(qa_path),
        "verified_first_inputs": first_inputs,
        "successful_components_refitted": 0,
        "prior_attempts_preserved": True,
        "iteration_budget_applies_to_each_new_solver_call_not_prior_preserved_attempt": True,
        "RESEARCH_ONLY": True,
        "capital_go": False,
    }
    base.write_json_once(OUT / "release.json", release)
    return release


def combine_record(
    source: dict[str, Any],
    binding: dict[str, Any],
    source_digest: str,
    components: list[tuple[dict[str, Any], dict[str, Any]]],
) -> dict[str, Any]:
    forecasts: dict[str, dict[str, Any]] = {family: {} for family in v3.FAMILIES}
    rows = []
    references = []
    for component, reference in components:
        _, family, information = component["model"].split("__")
        if (
            component["session"] != source["session"]
            or component["keys_sha256"]
            != inventory.canonical_digest([source["keys"][i] for i in source["jump_positions"]])
            or component["labels_sha256"] != inventory.canonical_digest(source["jump_target"])
        ):
            raise ValueError("RP4_NEWTON_COMPONENT_KEYS_OR_LABELS_DRIFT")
        if component["status"] == "COMPUTED":
            probability = np.asarray(component["forecast"], dtype=float)
            if (
                probability.shape != (len(source["jump_target"]),)
                or not np.isfinite(probability).all()
                or not ((probability > 0) & (probability < 1)).all()
            ):
                raise ValueError("RP4_NEWTON_INVALID_COMPONENT_PROBABILITY")
            forecasts[family][information] = component["forecast"]
        elif component["status"] != "NO VERIFICABLE" or component["forecast"] is not None:
            raise ValueError("RP4_NEWTON_INVALID_COMPONENT_STATUS")
        rows.append(
            {
                "model": component["model"],
                "status": component["status"],
                "lineage": reference["lineage"],
                "failure": component["failure"],
            }
        )
        references.append(reference)
    if {row["model"] for row in rows} != set(inventory.MODELS) or len(rows) != 6:
        raise ValueError("RP4_NEWTON_COMPONENT_SET_INCOMPLETE")
    failed = [r for r in rows if r["status"] != "COMPUTED"]
    return {
        "binding": binding,
        "session": source["session"],
        "first_repair_session_sha256": source_digest,
        "keys": source["keys"],
        "jump_positions": source["jump_positions"],
        "jump_target": source["jump_target"],
        "tail_status": {
            "jump": {
                "status": "NO VERIFICABLE",
                "reason": ";".join(r["model"] + ":" + r["failure"]["reason"] for r in failed),
            }
            if failed
            else {"status": "COMPUTED"}
        },
        "tail_forecasts": {"jump": {} if failed else forecasts},
        "components": rows,
        "component_references": references,
    }


def verify_closeout(output: Path, binding: dict[str, Any]) -> dict[str, Any]:
    receipt = json.loads((output / "receipt.json").read_text(encoding="utf-8"))
    required = {
        str(output / p)
        for p in (
            "summary.json",
            "fit_diagnostics.json",
            "component_manifest.json",
            "summary_receipt.json",
        )
    }
    if (
        receipt.get("status") != "COMPLETE"
        or receipt.get("exit_code") != 0
        or receipt.get("binding") != binding
        or receipt.get("code_sha256") != code_hashes()
        or set(receipt.get("artifacts_sha256", {})) != required
    ):
        raise ValueError("RP4_NEWTON_CLOSEOUT_RECEIPT_DRIFT")
    if (
        any(base.sha256(Path(p)) != digest for p, digest in receipt["artifacts_sha256"].items())
        or base.sha256(Path(receipt["log"])) != receipt["log_sha256"]
    ):
        raise ValueError("RP4_NEWTON_CLOSEOUT_ARTIFACT_DRIFT")
    summary = first.read_completed_summary(output, binding)
    release = inventory.read_verified(OUT / "release.json", binding["release_sha256"])
    new_inventory = inventory.read_verified(OUT / "inventory.json", release["inventory_sha256"])
    window = binding["window"]
    first_plan = next(row for row in new_inventory["windows"] if row["window"] == window)
    expected = {session + ".json" for session in first_plan["first_session_sha256"]}
    if (
        set(summary.get("session_sha256", {})) != expected
        or {path.name for path in (output / "sessions").glob("*.json")} != expected
        or {path.name for path in (output / "session_receipts").glob("*.json")} != expected
    ):
        raise ValueError("RP4_NEWTON_CLOSEOUT_SESSION_SET_DRIFT")
    original_inventory = inventory.read_verified(first.INVENTORY_PATH, first.INVENTORY_SHA)
    original_plan = next(row for row in original_inventory["windows"] if row["window"] == window)
    sources = {row["session"]: row for row in source_records(window, original_plan)}
    if set(sources) != set(first_plan["first_session_sha256"]):
        raise ValueError("RP4_NEWTON_CLOSEOUT_SOURCE_SESSION_SET_DRIFT")
    inventory_rows = {(row["session"], row["model"]): row for row in first_plan["components"]}
    for filename, digest in summary["session_sha256"].items():
        record = inventory.read_verified(output / "sessions" / filename, digest)
        session_receipt = json.loads(
            (output / "session_receipts" / filename).read_text(encoding="utf-8")
        )
        if session_receipt.get("binding") != binding or session_receipt.get("sha256") != digest:
            raise ValueError("RP4_NEWTON_CLOSEOUT_SESSION_RECEIPT_DRIFT")
        session = record["session"]
        if filename != session + ".json":
            raise ValueError("RP4_NEWTON_CLOSEOUT_SESSION_FILENAME_DRIFT")
        references = record["component_references"]
        if [ref["model"] for ref in references] != list(inventory.MODELS):
            raise ValueError("RP4_NEWTON_CLOSEOUT_COMPONENT_SET_DRIFT")
        components = []
        for ref in references:
            row = inventory_rows[(session, ref["model"])]
            path_root = output if row["eligible_newton"] else first.OUT / "evaluation" / window
            expected_path = path_root / "components" / session / f"{ref['model']}.json"
            receipt_path = path_root / "component_receipts" / session / f"{ref['model']}.json"
            if (
                Path(ref["path"]) != expected_path
                or ref["first_component_sha256"] != row["first_component_sha256"]
                or ref["first_component_receipt_sha256"] != row["first_component_receipt_sha256"]
                or base.sha256(receipt_path) != ref["component_receipt_sha256"]
            ):
                raise ValueError("RP4_NEWTON_CLOSEOUT_COMPONENT_REFERENCE_DRIFT")
            component = inventory.read_verified(expected_path, ref["sha256"])
            component_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            expected_binding = (
                binding
                if row["eligible_newton"]
                else {"release_sha256": FIRST_RELEASE_SHA, "window": window, "endpoint": "jump"}
            )
            if (
                component.get("binding") != expected_binding
                or component.get("model") != ref["model"]
                or component_receipt.get("binding") != expected_binding
                or component_receipt.get("sha256") != ref["sha256"]
            ):
                raise ValueError("RP4_NEWTON_CLOSEOUT_COMPONENT_RECEIPT_DRIFT")
            if row["eligible_newton"]:
                if ref["lineage"] != "NEWTON_FAILED_ONLY_ATTEMPT":
                    raise ValueError("RP4_NEWTON_CLOSEOUT_LINEAGE_DRIFT")
                validate_new_result(component)
            elif ref["sha256"] != row["first_component_sha256"]:
                raise ValueError("RP4_NEWTON_CLOSEOUT_REUSE_DRIFT")
            components.append((component, ref))
        expected_record = combine_record(
            sources[session], binding, first_plan["first_session_sha256"][session], components
        )
        if record != expected_record:
            raise ValueError("RP4_NEWTON_CLOSEOUT_SESSION_COMPONENT_PARITY_DRIFT")
    return summary


def run_window(window: str, addendum_path: Path, addendum_sha: str) -> dict[str, Any]:
    with (
        window_lock(first.OUT / "operations/jump_execution.lock"),
        first.resource_scope() as resources,
    ):
        release = prepare(addendum_path, addendum_sha)
        binding = {
            "release_sha256": base.sha256(OUT / "release.json"),
            "window": window,
            "endpoint": "jump",
        }
        output = OUT / "evaluation" / window
        if window == "confirmation":
            verify_closeout(OUT / "evaluation/primary", {**binding, "window": "primary"})
        base.write_json_once(output / "binding.json", binding)
        original_inventory = inventory.read_verified(first.INVENTORY_PATH, first.INVENTORY_SHA)
        plan = next(p for p in original_inventory["windows"] if p["window"] == window)
        recorded_inventory = inventory.read_verified(
            OUT / "inventory.json", release["inventory_sha256"]
        )
        first_plan = next(p for p in recorded_inventory["windows"] if p["window"] == window)
        rows = {(r["session"], r["model"]): r for r in first_plan["components"]}
        sources = source_records(window, plan)
        spec = v3.load_spec(inventory.SPEC_PATH, inventory.SPEC_SHA)
        prepared = None
        records, diagnostics, manifest = [], [], []
        for source in sources:
            session = source["session"]
            session_path = output / "sessions" / f"{session}.json"
            components = []
            for model in inventory.MODELS:
                row = rows[(session, model)]
                old_path = (
                    first.OUT / "evaluation" / window / "components" / session / f"{model}.json"
                )
                old_component = inventory.read_verified(old_path, row["first_component_sha256"])
                if row["eligible_newton"] != eligible_failure(old_component):
                    raise ValueError("RP4_NEWTON_ELIGIBILITY_DRIFT")
                if row["eligible_newton"]:
                    if code_hashes() != release["code_sha256"]:
                        raise ValueError("RP4_NEWTON_CODE_DRIFT_BEFORE_FIT")
                    path = output / "components" / session / f"{model}.json"
                    if session_path.exists() and not path.exists():
                        raise ValueError("RP4_NEWTON_RESUME_COMPONENT_MISSING")
                    keys = [source["keys"][i] for i in source["jump_positions"]]
                    target = source["jump_target"]
                    if not path.exists() and prepared is None:
                        prepared = first.prepared_panel(spec, window)

                    def fitting(
                        model: str = model,
                        session: str = session,
                        prepared: tuple[Any, ...] | None = prepared,
                        keys: list[dict[str, Any]] = keys,
                        target: list[float] = target,
                    ) -> tuple[np.ndarray, dict[str, Any]]:
                        if prepared is None:
                            raise ValueError("RP4_NEWTON_UNEXPECTED_REFIT_OF_CHECKPOINT")
                        panel, _, jump_eligible, labels, origins_ns, ends_ns, _, linear = prepared
                        dates, assets = panel["session_date"].to_numpy(), panel["asset"].to_numpy()
                        masks = base.causal_masks(
                            dates,
                            origins_ns,
                            ends_ns,
                            jump_eligible,
                            session,
                            embargo_minutes=spec["embargo_minutes"],
                            validation_sessions=spec["model"]["tuning_sessions"],
                        )
                        expected_keys = panel.loc[masks[-1], base.KEYS].to_dict("records")
                        if expected_keys != keys or labels[masks[-1]].tolist() != target:
                            raise ValueError("RP4_NEWTON_ORIGINAL_MASK_OR_TARGET_DRIFT")
                        information = model.split("__")[-1]
                        nullable = [
                            i
                            for i, c in enumerate(spec["feature_sets"][information])
                            if c in set(spec["missing_allowed"])
                        ]
                        return solver.fit_jump_linear(
                            linear[information],
                            labels,
                            *masks,
                            nullable,
                            dates,
                            assets,
                            copy.deepcopy(v3.tail_options(spec, "log_ridge_harq")),
                        )

                    component = first.saved_component(
                        output, session, model, binding, keys, target, None, fitting
                    )
                    validate_new_result(component)
                    reference = {
                        "model": model,
                        "lineage": "NEWTON_FAILED_ONLY_ATTEMPT",
                        "path": str(path),
                        "sha256": base.sha256(path),
                        "first_component_sha256": row["first_component_sha256"],
                        "first_component_receipt_sha256": row["first_component_receipt_sha256"],
                        "component_receipt_sha256": base.sha256(
                            output / "component_receipts" / session / f"{model}.json"
                        ),
                        "outcome": "RECOVERED"
                        if component["status"] == "COMPUTED"
                        else "PERSISTENT_FAILURE",
                    }
                else:
                    component = old_component
                    lineage = (
                        (
                            "REUSED_ORIGINAL_V3"
                            if component["provenance"] == "REUSED_FROZEN_V3"
                            else "REUSED_FIRST_REPAIR_SUCCESS"
                        )
                        if component["status"] == "COMPUTED"
                        else "PRESERVED_INELIGIBLE_FAILURE"
                    )
                    reference = {
                        "model": model,
                        "lineage": lineage,
                        "path": str(old_path),
                        "sha256": row["first_component_sha256"],
                        "first_component_sha256": row["first_component_sha256"],
                        "first_component_receipt_sha256": row["first_component_receipt_sha256"],
                        "component_receipt_sha256": row["first_component_receipt_sha256"],
                        "outcome": "PRESERVED_SUCCESS"
                        if component["status"] == "COMPUTED"
                        else "PERSISTENT_FAILURE",
                    }
                components.append((component, reference))
                diagnostics.append(
                    {
                        "session": session,
                        "model": model,
                        "lineage": reference["lineage"],
                        "status": component["status"],
                        "provenance": component["provenance"],
                        "fit": component["fit"],
                        "failure": component["failure"],
                        "prior_attempt_elapsed_seconds": old_component["elapsed_seconds"],
                        "prior_attempt_diagnostics": old_component["failure"]["diagnostics"]
                        if row["eligible_newton"]
                        else None,
                        "new_attempt_elapsed_seconds": component["elapsed_seconds"]
                        if row["eligible_newton"]
                        else 0.0,
                    }
                )
                manifest.append({"session": session, **reference, "status": component["status"]})
            record = combine_record(
                source, binding, first_plan["first_session_sha256"][session], components
            )
            if session_path.exists():
                receipt = json.loads(
                    (output / "session_receipts" / session_path.name).read_text(encoding="utf-8")
                )
                saved = inventory.read_verified(session_path, receipt["sha256"])
                if receipt.get("binding") != binding or saved != record:
                    raise ValueError("RP4_NEWTON_RESUME_SESSION_PARITY_DRIFT")
            else:
                base.write_json_once(session_path, v3.jsonable(record))
                base.write_json_once(
                    output / "session_receipts" / session_path.name,
                    {"binding": binding, "sha256": base.sha256(session_path)},
                )
            records.append(record)
            print(
                json.dumps(
                    {
                        "event": "NEWTON_SESSION_COMPLETE",
                        "window": window,
                        "session": session,
                        "failed_components": sum(
                            c["status"] != "COMPUTED" for c in record["components"]
                        ),
                    }
                ),
                flush=True,
            )
        if (output / "summary.json").exists():
            return first.read_completed_summary(output, binding)
        if code_hashes() != release["code_sha256"]:
            raise ValueError("RP4_NEWTON_CODE_DRIFT_BEFORE_INFERENCE")
        inference = aggregate._jump(records, aggregate._options(spec["inference"]))
        counts = Counter((r["lineage"], r["status"]) for r in diagnostics)
        summary = {
            "status": "COMPLETE_SECONDARY_ATTEMPTS",
            "binding": binding,
            "jump_secondary": inference,
            "scheduled_sessions": len(records),
            "eligible_newton_components": first_plan["eligible_components"],
            "component_counts": [
                {"lineage": k[0], "status": k[1], "N": v} for k, v in sorted(counts.items())
            ],
            "gradient_diagnostics": first.gradient_census(diagnostics),
            "resources": resources,
            "session_sha256": {
                r["session"] + ".json": base.sha256(output / "sessions" / f"{r['session']}.json")
                for r in records
            },
            "successful_components_refitted": 0,
            "prior_attempts_preserved": True,
            "primary_changed": False,
            "quantile_changed": False,
            "mz_changed": False,
            "RESEARCH_ONLY": True,
            "capital_go": False,
        }
        base.write_json_once(output / "fit_diagnostics.json", v3.jsonable(diagnostics))
        base.write_json_once(output / "component_manifest.json", manifest)
        base.write_json_once(output / "summary.json", v3.jsonable(summary))
        base.write_json_once(
            output / "summary_receipt.json",
            {
                "binding": binding,
                "artifacts_sha256": {
                    name: base.sha256(output / name)
                    for name in ("summary.json", "fit_diagnostics.json", "component_manifest.json")
                },
            },
        )
        return summary


def supervise(window: str, addendum_path: Path, addendum_sha: str) -> int:
    prepare(addendum_path, addendum_sha)
    output = OUT / "evaluation" / window
    binding = {
        "release_sha256": base.sha256(OUT / "release.json"),
        "window": window,
        "endpoint": "jump",
    }
    if (output / "receipt.json").exists():
        verify_closeout(output, binding)
        return 0
    attempt = OUT / "operations" / (window + "_" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ"))
    attempt.mkdir(parents=True, exist_ok=False)
    log = attempt / "stdout.log"
    command = [
        sys.executable,
        "-B",
        "-m",
        "artifacts.rp4_v3_secondary_repair.jump_newton_runner",
        "--worker",
        "--window",
        window,
        "--addendum",
        str(addendum_path),
        "--expected-addendum-sha",
        addendum_sha,
    ]
    started = time.perf_counter()
    started_at = datetime.now(UTC).isoformat()
    with log.open("xb") as stream:
        result = subprocess.run(
            command,
            cwd=ROOT,
            env={**os.environ, **first.ENVIRONMENT},
            stdout=stream,
            stderr=subprocess.STDOUT,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS
            if os.name == "nt"
            else 0,
        )
    receipt = {
        "binding": binding,
        "window": window,
        "command": subprocess.list2cmdline(command),
        "exit_code": result.returncode,
        "started_at_utc": started_at,
        "completed_at_utc": datetime.now(UTC).isoformat(),
        "elapsed_seconds": time.perf_counter() - started,
        "log": str(log),
        "log_sha256": base.sha256(log),
        "code_sha256": code_hashes(),
        "status": "COMPLETE" if result.returncode == 0 else "FAILED_ATTEMPT_PRESERVED",
        "artifacts_sha256": {
            str(output / name): base.sha256(output / name)
            for name in (
                "summary.json",
                "fit_diagnostics.json",
                "component_manifest.json",
                "summary_receipt.json",
            )
        }
        if result.returncode == 0
        else {},
    }
    base.write_json_once(attempt / "receipt.json", receipt)
    if result.returncode == 0:
        base.write_json_once(output / "receipt.json", receipt)
    print(json.dumps({"receipt": str(attempt / "receipt.json"), "exit_code": result.returncode}))
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare-only", action="store_true")
    group.add_argument("--window", choices=("primary", "confirmation"))
    parser.add_argument("--addendum", type=Path, required=True)
    parser.add_argument("--expected-addendum-sha", required=True)
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    if args.prepare_only:
        if args.worker:
            raise ValueError("RP4_NEWTON_WORKER_PREPARE_CONFLICT")
        prepare(args.addendum, args.expected_addendum_sha)
        print(
            json.dumps(
                {
                    "status": "NEWTON_RELEASE_PINNED",
                    "release_sha256": base.sha256(OUT / "release.json"),
                    "real_fits": 0,
                }
            )
        )
        return 0
    if args.worker:
        run_window(args.window, args.addendum, args.expected_addendum_sha)
        return 0
    return supervise(args.window, args.addendum, args.expected_addendum_sha)


if __name__ == "__main__":
    raise SystemExit(main())
