"""Complete only missing, frozen-v3 jump components with a two-thread resource cap."""

from __future__ import annotations

import argparse
import copy
import importlib.metadata
import json
import os
import subprocess
import sys
import time
from collections import Counter
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd  # type: ignore[import-untyped]
from artifacts.rp4_code import evaluate as base
from artifacts.rp4_v2_code import evaluate_v2 as v2
from artifacts.rp4_v2_code.execute import window_lock
from artifacts.rp4_v3_code import aggregate_v3 as aggregate
from artifacts.rp4_v3_code import evaluate_v3 as v3
from artifacts.rp4_v3_code import models as original
from artifacts.rp4_v3_secondary_repair import jump_inventory as inventory
from artifacts.rp4_v3_secondary_repair.jump_repair import fit_jump_linear

ROOT, OUT = inventory.ROOT, inventory.NEW_ROOT
ADDENDUM_PATH = ROOT / "artifacts/rp4_v3_secondary_repair/addendum.json"
ADDENDUM_SHA = "606a8c8d5dbe51628e7507b504cf7c5f8483a9aa5e7c80f62be33b2cb12e55de"
INVENTORY_PATH = OUT / "jump_inventory.json"
INVENTORY_SHA = "a7f0bd85aa2d817cfc7d1da7b463fc7c8751ee7e966b13fb662a63e403731c38"
RELEASE_PATH = OUT / "jump_release.json"
THREADS = 2
SOURCE_PATHS = tuple(
    dict.fromkeys(
        (
            *v3.SOURCE_PATHS,
            "artifacts/rp4_v2_code/execute.py",
            "artifacts/rp4_v3_secondary_repair/jump_repair.py",
            "artifacts/rp4_v3_secondary_repair/jump_inventory.py",
            "artifacts/rp4_v3_secondary_repair/jump_runner.py",
        )
    )
)
ENVIRONMENT = {
    name: str(THREADS)
    for name in (
        "OPENBLAS_NUM_THREADS",
        "OMP_NUM_THREADS",
        "MKL_NUM_THREADS",
        "NUMEXPR_NUM_THREADS",
        "POLARS_MAX_THREADS",
    )
}


def code_hashes() -> dict[str, str]:
    return {name: base.sha256(ROOT / name) for name in SOURCE_PATHS}


def prepare() -> dict[str, Any]:
    addendum = inventory.read_verified(ADDENDUM_PATH, ADDENDUM_SHA)
    spec = v3.load_spec(inventory.SPEC_PATH, inventory.SPEC_SHA)
    if (
        base.sha256(ROOT / addendum["document_path"]) != addendum["document_sha256"]
        or base.sha256(ROOT / addendum["solver_path"]) != addendum["solver_sha256"]
        or base.sha256(ROOT / "artifacts/rp4_v3_secondary_repair/test_jump_repair.py")
        != addendum["test_sha256"]
        or Path(addendum["output_root"]).resolve() != OUT
        or addendum["threads_total_max"] != THREADS
        or any(addendum[k] is not False for k in ("refit_mean", "refit_quantile", "refit_mz"))
    ):
        raise ValueError("RP4_JUMP_REPAIR_ADDENDUM_DRIFT")
    audit = inventory.read_verified(INVENTORY_PATH, INVENTORY_SHA)
    # Read-only revalidation of every original receipt, session and saved jump
    # component. No panel is read or any model fitted by this inventory check.
    if inventory.audit_inventory() != audit:
        raise ValueError("RP4_JUMP_REPAIR_INVENTORY_CHANGED")
    if audit["reusable_components"] != 962 or audit["missing_components"] != 1702:
        raise ValueError("RP4_JUMP_REPAIR_INVENTORY_COUNT_DRIFT")
    panel_path = v3.evaluation_panel_path(spec)
    if base.sha256(panel_path) != addendum["base_panel_sha256"]:
        raise ValueError("RP4_JUMP_REPAIR_PANEL_DRIFT")
    release = {
        "schema_version": "rp4-v3-jump-secondary-repair-release-v1",
        "addendum_sha256": ADDENDUM_SHA,
        "specification_sha256": inventory.SPEC_SHA,
        "inventory_sha256": INVENTORY_SHA,
        "original_release_sha256": inventory.RELEASE_SHA,
        "panel_sha256": addendum["base_panel_sha256"],
        "code_sha256": code_hashes(),
        "threads_total_max": THREADS,
        "priority": "BELOW_NORMAL_OR_IDLE",
        "window_order": ["primary", "confirmation"],
        "reusable_components": 962,
        "missing_components": 1702,
        "endpoint": "jump_only",
        "inference": aggregate._options(spec["inference"]),
        "lockfile_sha256": base.sha256(ROOT / "uv.lock"),
        "python_version": sys.version,
        "dependencies": {
            name: importlib.metadata.version(name)
            for name in (
                "numpy",
                "pandas",
                "scipy",
                "lightgbm",
                "pyarrow",
                "psutil",
                "threadpoolctl",
            )
        },
        "RESEARCH_ONLY": True,
        "capital_go": False,
    }
    base.write_json_once(RELEASE_PATH, release)
    return release


@contextmanager
def resource_scope() -> Iterator[dict[str, Any]]:
    """Change only this process; no affinity changes or manipulation of v4."""
    import psutil
    import pyarrow as pa  # type: ignore[import-untyped]
    from threadpoolctl import threadpool_info, threadpool_limits  # type: ignore[import-untyped]

    if os.name != "nt":
        raise ValueError("RP4_JUMP_REPAIR_WINDOWS_PRIORITY_REQUIRED")
    process = psutil.Process()
    process.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
    if process.nice() not in (psutil.BELOW_NORMAL_PRIORITY_CLASS, psutil.IDLE_PRIORITY_CLASS):
        raise ValueError("RP4_JUMP_REPAIR_LOW_PRIORITY_NOT_VERIFIED")
    os.environ.update(ENVIRONMENT)
    # Arrow may already have initialized its independent pool before this scope.
    pa.set_cpu_count(THREADS)
    pa.set_io_thread_count(1)
    with threadpool_limits(limits=THREADS):
        pools = threadpool_info()
        if any(row["num_threads"] > THREADS for row in pools) or pa.cpu_count() > THREADS:
            raise ValueError("RP4_JUMP_REPAIR_THREAD_CAP_NOT_VERIFIED")
        yield {
            "process_id": process.pid,
            "priority": str(process.nice()),
            "threads_total_max": THREADS,
            "arrow_cpu_threads": pa.cpu_count(),
            "arrow_io_threads": pa.io_thread_count(),
            "parquet_use_threads": False,
            "threadpools": [
                {k: r[k] for k in ("user_api", "internal_api", "num_threads")} for r in pools
            ],
        }


def prepared_panel(spec: dict[str, Any], window: str) -> tuple[Any, ...]:
    panel = pd.read_parquet(v3.evaluation_panel_path(spec), use_threads=False)
    panel["session_date"] = panel["session_date"].astype(str)
    panel = panel[
        panel["session_date"].between(
            spec["windows"]["primary"]["start"], spec["windows"][window]["end"]
        )
    ]
    if panel.duplicated(base.KEYS).any():
        raise ValueError("RP4_JUMP_REPAIR_PANEL_DUPLICATE_KEYS")
    panel = panel.sort_values(["session_date", "asset", "origin_minute"]).reset_index(drop=True)
    origins, ends = (
        pd.to_datetime(panel[c], utc=True) for c in ("forecast_origin_utc", "target_end_utc")
    )
    if (
        origins.isna().any()
        or ends.isna().any()
        or not (ends - origins).eq(pd.Timedelta(minutes=30)).all()
    ):
        raise ValueError("RP4_JUMP_REPAIR_ORIGINAL_CAUSAL_INTERVAL_DRIFT")
    origins_ns, ends_ns = (x.dt.as_unit("ns").astype("int64").to_numpy() for x in (origins, ends))
    eligible = v2.panel_masks(panel, spec)[0]
    raw_jump = panel["jump30"].to_numpy(dtype=float)
    jump_eligible = eligible & np.isfinite(raw_jump) & (raw_jump >= 0)
    target = np.where(np.isfinite(raw_jump), (raw_jump > 0).astype(float), np.nan)
    trees, linear = v3.designs(panel, spec)
    return panel, eligible, jump_eligible, target, origins_ns, ends_ns, trees, linear


def saved_component(
    output: Path,
    session: str,
    model: str,
    binding: dict[str, Any],
    keys: list[dict[str, Any]],
    labels: list[float],
    source: dict[str, Any] | None,
    fitting: Callable[[], tuple[np.ndarray, dict[str, Any]]],
) -> dict[str, Any]:
    """An immutable completed attempt, including failures, is never fitted twice."""
    if model not in inventory.MODELS:
        raise ValueError("RP4_JUMP_REPAIR_UNREGISTERED_COMPONENT")
    path = output / "components" / session / f"{model}.json"
    receipt_path = output / "component_receipts" / session / f"{model}.json"
    identity = {
        "binding": binding,
        "session": session,
        "model": model,
        "keys_sha256": inventory.canonical_digest(keys),
        "labels_sha256": inventory.canonical_digest(labels),
    }
    if path.exists():
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        if {k: receipt.get(k) for k in identity} != identity:
            raise ValueError("RP4_JUMP_REPAIR_CHECKPOINT_BINDING")
        record = inventory.read_verified(path, receipt["sha256"])
        if any(record.get(k) != v for k, v in identity.items()):
            raise ValueError("RP4_JUMP_REPAIR_CHECKPOINT_CONTENT")
        return record
    if receipt_path.exists():
        raise ValueError("RP4_JUMP_REPAIR_ORPHAN_RECEIPT")
    started = time.perf_counter()
    if source is not None:
        original_path = inventory.ORIGINAL / source["relative_path"]
        original_receipt = original_path.parent.parent / "session_receipts" / original_path.name
        if base.sha256(original_receipt) != source["receipt_sha256"]:
            raise ValueError("RP4_JUMP_REPAIR_ORIGINAL_RECEIPT_DRIFT")
        original_record = inventory.read_verified(original_path, source["component_sha256"])
        if original_record["keys"] != keys or original_record["target"] != labels:
            raise ValueError("RP4_JUMP_REPAIR_REUSE_TARGET_KEY_DRIFT")
        prediction, fit = np.asarray(original_record["forecast"]), original_record["fit"]
        provenance = "REUSED_FROZEN_V3"
        failure = None
    else:
        provenance = "NEW_MISSING_COMPONENT"
        try:
            prediction, fit = fitting()
            failure = None
        except original.ModelConvergenceError as error:
            prediction, fit = np.empty(0), {}
            failure = {"reason": str(error), "diagnostics": error.diagnostics}
        except np.linalg.LinAlgError as error:
            prediction, fit = np.empty(0), {}
            failure = {"reason": "linear_algebra_failure", "diagnostics": {"message": str(error)}}
    if failure is None and (
        np.asarray(prediction).shape != (len(keys),)
        or not np.isfinite(prediction).all()
        or not ((prediction > 0) & (prediction < 1)).all()
    ):
        raise ValueError("RP4_JUMP_REPAIR_INVALID_PROBABILITY_COMPONENT")
    record = {
        **identity,
        "status": "COMPUTED" if failure is None else "NO VERIFICABLE",
        "provenance": provenance,
        "N_origins": len(keys),
        "forecast": np.asarray(prediction, dtype=float).tolist() if failure is None else None,
        "fit": fit,
        "failure": failure,
        "original_component_sha256": source["component_sha256"] if source else None,
        "original_receipt_sha256": source["receipt_sha256"] if source else None,
        "elapsed_seconds": time.perf_counter() - started,
    }
    base.write_json_once(path, v3.jsonable(record))
    base.write_json_once(receipt_path, {**identity, "sha256": base.sha256(path)})
    return record


def completed_records(
    output: Path,
    binding: dict[str, Any],
    planned: list[dict[str, Any]],
    sources: dict[tuple[str, str], dict[str, Any]],
) -> list[dict[str, Any]]:
    records = []
    for row in planned:
        path = output / "sessions" / f"{row['session']}.json"
        receipt = json.loads((output / "session_receipts" / path.name).read_text(encoding="utf-8"))
        record = inventory.read_verified(path, receipt["sha256"])
        if (
            receipt.get("binding") != binding
            or record["binding"] != binding
            or record["session"] != row["session"]
            or record["source_session_sha256"] != row["source_session_sha256"]
        ):
            raise ValueError("RP4_JUMP_REPAIR_SESSION_BINDING_DRIFT")
        positions = record["jump_positions"]
        if (
            any(type(i) is not int or not 0 <= i < len(record["keys"]) for i in positions)
            or positions != sorted(set(positions))
            or inventory.canonical_digest([record["keys"][i] for i in positions])
            != row["keys_sha256"]
            or inventory.canonical_digest(record["jump_target"]) != row["labels_sha256"]
            or len(positions) != len(record["jump_target"])
        ):
            raise ValueError("RP4_JUMP_REPAIR_SESSION_TARGET_KEY_DRIFT")
        if set(record["component_sha256"]) != set(inventory.MODELS) or set(
            record["component_receipt_sha256"]
        ) != set(inventory.MODELS):
            raise ValueError("RP4_JUMP_REPAIR_SESSION_COMPONENT_SET")
        forecasts: dict[str, dict[str, Any]] = {family: {} for family in v3.FAMILIES}
        components = []
        failed = False
        for model, digest in record["component_sha256"].items():
            component_path = output / "components" / row["session"] / f"{model}.json"
            receipt_path = output / "component_receipts" / row["session"] / f"{model}.json"
            if (
                base.sha256(component_path) != digest
                or base.sha256(receipt_path) != record["component_receipt_sha256"][model]
            ):
                raise ValueError("RP4_JUMP_REPAIR_SESSION_COMPONENT_DRIFT")
            component = inventory.read_verified(component_path, digest)
            component_receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            identity = {
                "binding": binding,
                "session": row["session"],
                "model": model,
                "keys_sha256": row["keys_sha256"],
                "labels_sha256": row["labels_sha256"],
            }
            if (
                any(component.get(k) != v for k, v in identity.items())
                or any(component_receipt.get(k) != v for k, v in identity.items())
                or component_receipt.get("sha256") != digest
                or component["N_origins"] != len(positions)
                or component["status"] not in ("COMPUTED", "NO VERIFICABLE")
            ):
                raise ValueError("RP4_JUMP_REPAIR_SESSION_COMPONENT_IDENTITY")
            source = sources.get((row["session"], model))
            if source is not None:
                original_path = inventory.ORIGINAL / source["relative_path"]
                original_receipt = (
                    original_path.parent.parent / "session_receipts" / original_path.name
                )
                original_record = inventory.read_verified(original_path, source["component_sha256"])
                if (
                    component["provenance"] != "REUSED_FROZEN_V3"
                    or component["status"] != "COMPUTED"
                    or component["original_component_sha256"] != source["component_sha256"]
                    or component["original_receipt_sha256"] != source["receipt_sha256"]
                    or base.sha256(original_receipt) != source["receipt_sha256"]
                    or component["forecast"] != original_record["forecast"]
                    or component["fit"] != original_record["fit"]
                ):
                    raise ValueError("RP4_JUMP_REPAIR_REUSED_COMPONENT_CONTENT_DRIFT")
            elif (
                model not in row["missing_models"]
                or component["provenance"] != "NEW_MISSING_COMPONENT"
                or component["original_component_sha256"] is not None
                or component["original_receipt_sha256"] is not None
            ):
                raise ValueError("RP4_JUMP_REPAIR_UNAUTHORIZED_COMPONENT")
            if component["status"] == "COMPUTED":
                probability = np.asarray(component["forecast"], dtype=float)
                if (
                    probability.shape != (len(positions),)
                    or not np.isfinite(probability).all()
                    or not ((probability > 0) & (probability < 1)).all()
                    or component["failure"] is not None
                ):
                    raise ValueError("RP4_JUMP_REPAIR_INVALID_PROBABILITY_COMPONENT")
                _, family, info = model.split("__")
                forecasts[family][info] = component["forecast"]
            else:
                failed = True
                if component["forecast"] is not None or not component["failure"]:
                    raise ValueError("RP4_JUMP_REPAIR_FAILURE_CONTENT_DRIFT")
            components.append(
                {
                    k: component[k]
                    for k in ("model", "status", "provenance", "failure", "elapsed_seconds")
                }
            )
        if (
            record["tail_status"]["jump"]["status"] != ("NO VERIFICABLE" if failed else "COMPUTED")
            or record["tail_forecasts"]["jump"] != ({} if failed else forecasts)
            or sorted(record["components"], key=lambda x: x["model"])
            != sorted(components, key=lambda x: x["model"])
        ):
            raise ValueError("RP4_JUMP_REPAIR_SESSION_FORECAST_COMPONENT_PARITY")
        records.append(record)
    return records


def gradient_census(fits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Old ftol successes remain valid reuse; only NEW fits require the new certificate."""
    result = []
    for provenance in ("REUSED_FROZEN_V3", "NEW_MISSING_COMPONENT"):
        rows = [
            r
            for r in fits
            if r["provenance"] == provenance
            and "__log_ridge_harq__" in r["model"]
            and r["status"] == "COMPUTED"
        ]
        refit = [r["fit"]["solver_refit"].get("gradient_inf_norm_objective_over_n") for r in rows]
        candidates = [
            c["solver"].get("gradient_inf_norm_objective_over_n")
            for r in rows
            for c in r["fit"]["candidates"]
        ]
        output: dict[str, Any] = {
            "provenance": provenance,
            "N_components": len(rows),
            "new_certificate_required": provenance == "NEW_MISSING_COMPONENT",
            "gradient_threshold": 1e-8,
        }
        for label, values in (("refit", refit), ("candidate", candidates)):
            finite = [float(v) for v in values if v is not None and np.isfinite(v)]
            output.update(
                {
                    f"{label}_gradients_available": len(finite),
                    f"{label}_gradients_missing_or_single_class": len(values) - len(finite),
                    f"{label}_gradients_above_1e_minus8": sum(v > 1e-8 for v in finite),
                    f"{label}_gradient_max": max(finite) if finite else None,
                }
            )
        result.append(output)
    return result


def read_completed_summary(output: Path, binding: dict[str, Any]) -> dict[str, Any]:
    receipt = json.loads((output / "summary_receipt.json").read_text(encoding="utf-8"))
    if receipt.get("binding") != binding:
        raise ValueError("RP4_JUMP_REPAIR_SUMMARY_BINDING_DRIFT")
    for name, digest in receipt["artifacts_sha256"].items():
        if Path(name).name != name or base.sha256(output / name) != digest:
            raise ValueError("RP4_JUMP_REPAIR_SUMMARY_ARTIFACT_DRIFT")
    required = {"summary.json", "fit_diagnostics.json", "component_manifest.json"}
    if set(receipt["artifacts_sha256"]) != required:
        raise ValueError("RP4_JUMP_REPAIR_SUMMARY_RECEIPT_SET")
    summary = inventory.read_verified(
        output / "summary.json", receipt["artifacts_sha256"]["summary.json"]
    )
    if summary.get("binding") != binding or summary.get("status") != "COMPLETE_SECONDARY_ATTEMPTS":
        raise ValueError("RP4_JUMP_REPAIR_SUMMARY_CONTENT_DRIFT")
    return summary


def verify_complete_window(output: Path, binding: dict[str, Any]) -> dict[str, Any]:
    """A summary alone is not a successful CLI closeout, including after a crash."""
    receipt = json.loads((output / "receipt.json").read_text(encoding="utf-8"))
    required = {
        str(output / name)
        for name in (
            "summary.json",
            "fit_diagnostics.json",
            "component_manifest.json",
            "summary_receipt.json",
        )
    }
    if (
        receipt.get("status") != "COMPLETE"
        or receipt.get("exit_code") != 0
        or receipt.get("window") != binding["window"]
        or receipt.get("release_sha256") != binding["release_sha256"]
        or receipt.get("code_sha256") != code_hashes()
        or set(receipt.get("artifacts_sha256", {})) != required
    ):
        raise ValueError("RP4_JUMP_REPAIR_COMPLETE_WINDOW_RECEIPT_DRIFT")
    if (
        any(base.sha256(Path(p)) != digest for p, digest in receipt["artifacts_sha256"].items())
        or base.sha256(Path(receipt["log"])) != receipt["log_sha256"]
        or receipt["summary_sha256"] != base.sha256(output / "summary.json")
    ):
        raise ValueError("RP4_JUMP_REPAIR_COMPLETE_WINDOW_ARTIFACT_DRIFT")
    return read_completed_summary(output, binding)


def run_window(window: str) -> dict[str, Any]:
    with window_lock(OUT / "operations" / "jump_execution.lock"), resource_scope() as resources:
        release = prepare()
        binding = {
            "release_sha256": base.sha256(RELEASE_PATH),
            "window": window,
            "endpoint": "jump",
        }
        output = OUT / "evaluation" / window
        base.write_json_once(output / "binding.json", binding)
        if window == "confirmation":
            verify_complete_window(OUT / "evaluation/primary", {**binding, "window": "primary"})
        audit = inventory.read_verified(INVENTORY_PATH, INVENTORY_SHA)
        plan = next(row for row in audit["windows"] if row["window"] == window)
        sources = {(row["session"], row["model"]): row for row in plan["components"]}
        if (output / "summary.json").exists():
            completed_records(output, binding, plan["sessions"], sources)
            return read_completed_summary(output, binding)
        spec = v3.load_spec(inventory.SPEC_PATH, inventory.SPEC_SHA)
        panel, eligible, jump_eligible, labels, origins_ns, ends_ns, trees, linear = prepared_panel(
            spec, window
        )
        dates, assets = panel["session_date"].to_numpy(), panel["asset"].to_numpy()
        optional = set(spec["missing_allowed"])
        for row in plan["sessions"]:
            session = row["session"]
            session_path = output / "sessions" / f"{session}.json"
            if session_path.exists():
                completed_records(output, binding, [row], sources)
                continue
            masks = base.causal_masks(
                dates,
                origins_ns,
                ends_ns,
                jump_eligible,
                session,
                embargo_minutes=spec["embargo_minutes"],
                validation_sessions=spec["model"]["tuning_sessions"],
            )
            main_test = eligible & (dates == session)
            keys = panel.loc[masks[-1], base.KEYS].to_dict("records")
            target = labels[masks[-1]].tolist()
            if (
                inventory.canonical_digest(keys) != row["keys_sha256"]
                or inventory.canonical_digest(target) != row["labels_sha256"]
            ):
                raise ValueError("RP4_JUMP_REPAIR_ORIGINAL_JUMP_MASK_OR_TARGET_DRIFT")
            forecasts: dict[str, dict[str, Any]] = {family: {} for family in v3.FAMILIES}
            components = []
            for name in base.SETS:
                nullable = [i for i, c in enumerate(spec["feature_sets"][name]) if c in optional]
                for family in v3.FAMILIES:
                    model = f"jump__{family}__{name}"
                    source = sources.get((session, model))
                    if source is None and model not in row["missing_models"]:
                        raise ValueError("RP4_JUMP_REPAIR_UNAUTHORIZED_COMPONENT")
                    if code_hashes() != release["code_sha256"]:
                        raise ValueError("RP4_JUMP_REPAIR_CODE_CHANGED_BEFORE_COMPONENT")
                    options = copy.deepcopy(v3.tail_options(spec, family))
                    if family == "lightgbm_qlike":
                        options["num_threads"] = THREADS

                    def fitting(
                        family: str = family,
                        name: str = name,
                        nullable: list[int] = nullable,
                        options: dict[str, Any] = options,
                        masks: tuple[base.Mask, base.Mask, base.Mask, base.Mask] = masks,
                    ) -> tuple[np.ndarray, dict[str, Any]]:
                        if family == "log_ridge_harq":
                            return fit_jump_linear(
                                linear[name], labels, *masks, nullable, dates, assets, options
                            )
                        return original.fit_jump(
                            trees[name],
                            labels,
                            *masks,
                            nullable,
                            dates,
                            assets,
                            options,
                            family="lightgbm",
                            threads=THREADS,
                        )

                    component = saved_component(
                        output, session, model, binding, keys, target, source, fitting
                    )
                    components.append(
                        {
                            k: component[k]
                            for k in ("model", "status", "provenance", "failure", "elapsed_seconds")
                        }
                    )
                    if component["status"] == "COMPUTED":
                        forecasts[family][name] = component["forecast"]
            failures = [item for item in components if item["status"] != "COMPUTED"]
            record = {
                "binding": binding,
                "session": session,
                "source_session_sha256": row["source_session_sha256"],
                "keys": panel.loc[main_test, base.KEYS].to_dict("records"),
                "jump_positions": np.flatnonzero(jump_eligible[main_test]).tolist(),
                "jump_target": target,
                "tail_status": {
                    "jump": {"status": "COMPUTED"}
                    if not failures
                    else {
                        "status": "NO VERIFICABLE",
                        "reason": ";".join(
                            x["model"] + ":" + x["failure"]["reason"] for x in failures
                        ),
                    }
                },
                "tail_forecasts": {"jump": forecasts if not failures else {}},
                "components": components,
                "component_sha256": {
                    model: base.sha256(output / "components" / session / f"{model}.json")
                    for model in inventory.MODELS
                },
                "component_receipt_sha256": {
                    model: base.sha256(output / "component_receipts" / session / f"{model}.json")
                    for model in inventory.MODELS
                },
                "max_training_target_end_utc": str(pd.Timestamp(ends_ns[masks[0]].max(), tz="UTC")),
                "first_evaluation_origin_utc": str(
                    pd.Timestamp(origins_ns[masks[-1]].min(), tz="UTC")
                ),
                "train_last_session": str(dates[masks[0]].max()),
                "inner_valid_sessions": np.unique(dates[masks[2]]).tolist(),
            }
            base.write_json_once(session_path, v3.jsonable(record))
            base.write_json_once(
                output / "session_receipts" / session_path.name,
                {"binding": binding, "sha256": base.sha256(session_path)},
            )
            print(
                json.dumps(
                    {
                        "event": "JUMP_SESSION_COMPLETE",
                        "window": window,
                        "session": session,
                        "failed_components": len(failures),
                        "completed_sessions": len(list((output / "sessions").glob("*.json"))),
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
        records = completed_records(output, binding, plan["sessions"], sources)
        if code_hashes() != release["code_sha256"]:
            raise ValueError("RP4_JUMP_REPAIR_CODE_CHANGED_BEFORE_INFERENCE")
        # ONLY jump AUC; not the full v3 aggregator, mean losses, quantile or MZ.
        result = aggregate._jump(records, aggregate._options(spec["inference"]))
        counts = Counter((c["provenance"], c["status"]) for r in records for c in r["components"])
        diagnostics = []
        component_manifest = []
        for record in records:
            for model in inventory.MODELS:
                path = output / "components" / record["session"] / f"{model}.json"
                component = inventory.read_verified(path, record["component_sha256"][model])
                diagnostics.append(
                    {
                        k: component[k]
                        for k in (
                            "session",
                            "model",
                            "status",
                            "provenance",
                            "fit",
                            "failure",
                            "elapsed_seconds",
                        )
                    }
                )
                component_manifest.append(
                    {
                        "session": record["session"],
                        "model": model,
                        "status": component["status"],
                        "provenance": component["provenance"],
                        "component_sha256": record["component_sha256"][model],
                        "receipt_sha256": record["component_receipt_sha256"][model],
                        "original_component_sha256": component["original_component_sha256"],
                    }
                )
        summary = {
            "status": "COMPLETE_SECONDARY_ATTEMPTS",
            "binding": binding,
            "jump_secondary": result,
            "scheduled_sessions": len(plan["sessions"]),
            "component_counts": [
                {"provenance": key[0], "status": key[1], "N": value}
                for key, value in sorted(counts.items())
            ],
            "resources": resources,
            "gradient_diagnostics": gradient_census(diagnostics),
            "session_sha256": {
                r["session"] + ".json": base.sha256(output / "sessions" / f"{r['session']}.json")
                for r in records
            },
            "primary_changed": False,
            "quantile_changed": False,
            "mz_changed": False,
            "RESEARCH_ONLY": True,
            "capital_go": False,
        }
        base.write_json_once(output / "fit_diagnostics.json", v3.jsonable(diagnostics))
        base.write_json_once(output / "component_manifest.json", component_manifest)
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


def supervise(window: str) -> int:
    prepare()
    output = OUT / "evaluation" / window
    binding = {"release_sha256": base.sha256(RELEASE_PATH), "window": window, "endpoint": "jump"}
    final_receipt_path = output / "receipt.json"
    if final_receipt_path.exists():
        verify_complete_window(output, binding)
        print(json.dumps({"status": "ALREADY_COMPLETE_NO_REFIT", "window": window}))
        return 0
    attempt = OUT / "operations" / (window + "_" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ"))
    attempt.mkdir(parents=True, exist_ok=False)
    log = attempt / "stdout.log"
    command = [
        sys.executable,
        "-B",
        "-m",
        "artifacts.rp4_v3_secondary_repair.jump_runner",
        "--worker",
        "--window",
        window,
    ]
    environment = {**os.environ, **ENVIRONMENT}
    environment["PYTHONPATH"] = os.pathsep.join(
        str(ROOT / p) for p in ("", "src", "scripts", "artifacts/rp4_code")
    )
    started = time.perf_counter()
    started_at = datetime.now(UTC).isoformat()
    with log.open("xb") as stream:
        result = subprocess.run(
            command,
            cwd=ROOT,
            env=environment,
            stdout=stream,
            stderr=subprocess.STDOUT,
            check=False,
            creationflags=subprocess.CREATE_NO_WINDOW | subprocess.BELOW_NORMAL_PRIORITY_CLASS
            if os.name == "nt"
            else 0,
        )
    summary_path = OUT / "evaluation" / window / "summary.json"
    receipt = {
        "window": window,
        "command": subprocess.list2cmdline(command),
        "exit_code": result.returncode,
        "started_at_utc": started_at,
        "completed_at_utc": datetime.now(UTC).isoformat(),
        "elapsed_seconds": time.perf_counter() - started,
        "log": str(log),
        "log_sha256": base.sha256(log),
        "release_sha256": base.sha256(RELEASE_PATH),
        "code_sha256": code_hashes(),
        "summary_sha256": base.sha256(summary_path) if result.returncode == 0 else None,
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
        "status": "COMPLETE" if result.returncode == 0 else "FAILED_ATTEMPT_PRESERVED",
    }
    base.write_json_once(attempt / "receipt.json", receipt)
    if result.returncode == 0:
        base.write_json_once(OUT / "evaluation" / window / "receipt.json", receipt)
    print(
        json.dumps(
            {"receipt": str(attempt / "receipt.json"), "exit_code": result.returncode},
            sort_keys=True,
        )
    )
    return result.returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare-only", action="store_true")
    group.add_argument("--window", choices=("primary", "confirmation"))
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    if args.prepare_only:
        if args.worker:
            raise ValueError("RP4_JUMP_REPAIR_WORKER_PREPARE_CONFLICT")
        prepare()
        print(
            json.dumps(
                {
                    "status": "RELEASE_PINNED",
                    "release_sha256": base.sha256(RELEASE_PATH),
                    "real_model_fits": 0,
                }
            )
        )
        return 0
    if args.worker:
        run_window(args.window)
        return 0
    return supervise(args.window)


if __name__ == "__main__":
    raise SystemExit(main())
