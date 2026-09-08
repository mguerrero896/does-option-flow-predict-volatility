"""Launch one target-specific mean evaluation with eight disjoint four-thread shards."""

from __future__ import annotations

import argparse
import csv
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import time
from contextlib import ExitStack
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from artifacts.rp4_code.evaluate import sha256, write_json_once
from artifacts.rp4_v2_code.execute import window_lock
from artifacts.rp4_v4_code.evaluate_v4 import (
    ROOT,
    SHARDS,
    THREADS,
    evaluation_code_hashes,
    horizon_contract,
    load_spec,
    target_panel_path,
)
from artifacts.rp4_v4_code.materialize_targets import select_bar_pins

SPEC = ROOT / "artifacts/rp4_v4_a1/specification.json"
RESOLUTION_SHA256 = "05ff5f4b8127238dc9fb8371e530c12a1d2bbf23c30ef1363edf0f829b87722f"


def resolution_cases(directory: Path) -> None:
    """Check the small keyed audit evidence, without opening financial target values."""
    with (directory / "resolution_rows.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    keys = {(r["asset"], r["session_date"], int(r["origin_minute"])) for r in rows}
    pairs = {
        (*key, int(r["horizon"]))
        for r in rows
        for key in [(r["asset"], r["session_date"], int(r["origin_minute"]))]
    }
    if (len(rows), len(pairs), len(keys)) != (6, 6, 4) or {
        h: sum(int(r["horizon"]) == h for r in rows) for h in (15, 5)
    } != {15: 4, 5: 2}:
        raise ValueError("RP4_V4_RESOLUTION_CASE_CENSUS")
    for row in rows:
        horizon, origin = int(row["horizon"]), int(row["origin_minute"])
        observed, required = int(row["observed_closes"]), int(row["required_closes"])
        missing = [int(value) for value in row["missing_minutes"].split(";") if value]
        if (
            row["eligible_v3"].lower() != "false"
            or row["reference_finite"].lower() != "true"
            or row["reconstructed_finite"].lower() != "false"
            or row["registered_fill_rule_reproduction_bit_exact"].lower() != "true"
            or row["reason"] != "missing_observed_closes"
            or row["resolution"] != "registered_forward_fill_versus_strict_actual_close_rule"
            or required != horizon + 1
            or not 0 <= observed < required
            or int(row["missing_closes"]) != required - observed
            or len(missing) != required - observed
            or len(set(missing)) != len(missing)
            or not all(origin <= minute <= origin + horizon for minute in missing)
            or not 0 < float(row["session_fill_share"]) <= 0.05
        ):
            raise ValueError("RP4_V4_RESOLUTION_CASE_NOT_EXPLAINED_OUTSIDE_MASK")
    with (directory / "rv30_null_rows.csv").open(encoding="utf-8", newline="") as stream:
        null_rows = list(csv.DictReader(stream))
    if (
        len(null_rows) != 14
        or len({(r["asset"], r["session_date"], int(r["origin_minute"])) for r in null_rows}) != 14
    ):
        raise ValueError("RP4_V4_RESOLUTION_NULL_CENSUS")
    for row in null_rows:
        origin = int(row["origin_minute"])
        missing = [int(value) for value in row["missing_minutes"].split(";") if value]
        if (
            row["eligible_v3"].lower() != "false"
            or row["base_is_null"].lower() != "true"
            or row["control_is_nan"].lower() != "true"
            or row["resolution"] != "same_missing_target_null_in_base_and_nan_in_control_only"
            or not missing
            or not all(origin <= minute <= origin + 30 for minute in missing)
        ):
            raise ValueError("RP4_V4_RESOLUTION_NULL_NOT_EXPLAINED_OUTSIDE_MASK")


def validate_resolution(
    spec: dict[str, Any], manifest: dict[str, Any], manifest_path: Path, digest: str
) -> str:
    """Accept only the adopted, source-pinned explanation of this unchanged failed preflight."""
    path = manifest_path.parent / "resolution.json"
    if not path.is_file() or sha256(path) != RESOLUTION_SHA256:
        raise ValueError("RP4_V4_RESOLUTION_MISSING_OR_NOT_ADOPTED")
    resolution = json.loads(path.read_text(encoding="utf-8"))
    expected = {
        "status": "PASS_DISCREPANCIES_EXPLAINED_OUTSIDE_V3_ELIGIBILITY",
        "spec_sha256": digest,
        "base_panel_sha256": manifest["base_panel_sha256"],
        "target_panel_sha256": sha256(target_panel_path(spec)),
        "original_manifest_sha256": sha256(manifest_path),
        "producer_sha256": manifest["producer_sha256"],
        "finite_pair_mismatches": 0,
        "eligible_key_changes": 0,
        "eligible_invalid_targets": {"rv_15": 0, "rv_5": 0},
        "eligible_rows": manifest["eligible_v3_rows"],
        "eligible_reference_finite_pairs": {"rv_15": 81845, "rv_5": 81845},
        "discrepancies": {
            "total": 6,
            "rv_15": 4,
            "rv_5": 2,
            "unique_origin_keys": 4,
            "all_outside_v3_eligibility": True,
            "all_caused_by_missing_observed_closes": True,
            "registered_filled_values_reproduced_bit_exact": True,
        },
        "rv30_nulls": {
            "total": 14,
            "all_outside_v3_eligibility": True,
            "all_control_nan": True,
            "all_base_null": True,
            "all_have_missing_actual_closes": True,
        },
        "resolution_code_path": "artifacts/rp4_v4_a2/resolve_target_mask.py",
        "original_artifacts_modified": False,
        "original_materialization_exit_code": 2,
        "model_fits": 0,
    }
    if any(resolution.get(key) != value for key, value in expected.items()):
        raise ValueError("RP4_V4_RESOLUTION_CONTRACT")
    code = ROOT / resolution["resolution_code_path"]
    if sha256(code) != resolution["resolution_code_sha256"]:
        raise ValueError("RP4_V4_RESOLUTION_AUDITOR_CODE_DRIFT")
    evidence = {
        Path(p).resolve(): value for p, value in resolution["evidence_artifacts_sha256"].items()
    }
    names = {
        "resolution_rows.csv",
        "rv30_null_rows.csv",
        "reference_comparison.json",
        "reference_discrepancies.parquet",
        "rv30_control.json",
        "rv30_control_discrepancies.parquet",
        "target_status.parquet",
    }
    expected_paths = {manifest_path.parent / name for name in names}
    if (
        any(not Path(p).is_absolute() for p in resolution["evidence_artifacts_sha256"])
        or set(evidence) != expected_paths
        or any(sha256(p) != value for p, value in evidence.items())
        or any(
            evidence.get(Path(p).resolve()) != value
            for p, value in manifest["artifacts"].items()
            if Path(p).resolve() in expected_paths
        )
    ):
        raise ValueError("RP4_V4_RESOLUTION_EVIDENCE_DRIFT")
    pins = spec["bar_input_pins"]
    if sha256(Path(pins["path"])) != pins["sha256"]:
        raise ValueError("RP4_V4_RESOLUTION_SOURCE_MANIFEST_DRIFT")
    inherited = json.loads(Path(pins["path"]).read_text(encoding="utf-8"))
    expected_sources = {
        Path(p).resolve(): value for p, value in select_bar_pins(inherited["sha256"]).items()
    }
    sources = {Path(p).resolve(): value for p, value in resolution["source_files_sha256"].items()}
    if (
        any(not Path(p).is_absolute() for p in resolution["source_files_sha256"])
        or sources != expected_sources
        or any(sha256(p) != value for p, value in sources.items())
    ):
        raise ValueError("RP4_V4_RESOLUTION_SOURCE_DRIFT")
    comparison = manifest["reference_comparison"]
    for key, count in (("rv_15", 4), ("rv_5", 2)):
        full, eligible = comparison["by_target"][key], comparison["eligible_v3_only"][key]
        if (
            full["finite_bit_mismatches"] != 0
            or full["finite_mask_mismatches"] != count
            or full["all_value_bit_mismatches"] != count
            or eligible["finite_pairs"] != 81845
            or any(
                eligible[k] != 0
                for k in (
                    "finite_bit_mismatches",
                    "finite_mask_mismatches",
                    "all_value_bit_mismatches",
                )
            )
        ):
            raise ValueError("RP4_V4_RESOLUTION_UNEXPLAINED_COMPARISON")
    control = manifest["rv30_control"]
    if (
        control["finite_bit_mismatches"] != 0
        or control["finite_mask_mismatches"] != 0
        or control["null_mask_mismatches"] != 14
    ):
        raise ValueError("RP4_V4_RESOLUTION_UNEXPLAINED_RV30_CONTROL")
    resolution_cases(manifest_path.parent)
    return RESOLUTION_SHA256


def release_path(horizon: int) -> Path:
    return ROOT / "artifacts/rp4_v4_a2" / f"evaluation_release_rv{horizon}.json"


def prepare(digest: str, horizon: int) -> tuple[dict[str, Any], Path]:
    spec = load_spec(SPEC, digest)
    target_key, end_key = horizon_contract(spec, horizon)
    root = Path(spec["data_root"]).resolve()
    targets, base = target_panel_path(spec), Path(spec["base_panel"]["path"]).resolve()
    manifest_path = targets.parent / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    producer = "artifacts/rp4_v4_code/materialize_targets.py"
    if (
        manifest["spec_sha256"] != digest
        or manifest["base_panel_sha256"] != spec["base_panel"]["sha256"]
        or manifest["model_fits"] != 0
        or manifest["key_set_exact"] is not True
        or manifest["preflight_pass"] is not False
        or manifest["status"] != "TARGET_PREFLIGHT_REQUIRES_INVESTIGATION"
        or manifest["excluded_origins"] != 0
        or manifest["excluded_sessions"] != 0
        or manifest["eligible_v3_invalid"] != {"rv_15": 0, "rv_5": 0}
        or manifest["producer_path"] != producer
        or manifest["producer_sha256"] != sha256(ROOT / producer)
        or sha256(base) != spec["base_panel"]["sha256"]
    ):
        raise ValueError("RP4_V4_RELEASE_TARGET_MATERIALIZATION_CONTRACT")
    if any(not Path(path).is_absolute() for path in manifest["artifacts"]):
        raise ValueError("RP4_V4_RELEASE_MATERIALIZATION_PATH_NOT_ABSOLUTE")
    pinned = {Path(path).resolve(): value for path, value in manifest["artifacts"].items()}
    if any(
        not path.is_relative_to(root) or sha256(path) != value for path, value in pinned.items()
    ):
        raise ValueError("RP4_V4_RELEASE_MATERIALIZATION_ARTIFACT_DRIFT")
    if pinned.get(targets) != sha256(targets):
        raise ValueError("RP4_V4_RELEASE_TARGET_PANEL_NOT_PINNED")
    resolution_digest = validate_resolution(spec, manifest, manifest_path, digest)
    release = {
        "schema_version": "rp4-v4-evaluation-release-v1",
        "specification_sha256": digest,
        "freeze_sha256": sha256(SPEC.parent / "freeze_manifest.json"),
        "base_panel_sha256": sha256(base),
        "target_panel_sha256": sha256(targets),
        "target_manifest_sha256": sha256(manifest_path),
        "target_resolution_sha256": resolution_digest,
        "original_target_preflight_pass": False,
        "resolved_target_preflight_pass": True,
        "horizon_minutes": horizon,
        "target_key": target_key,
        "target_end_key": end_key,
        "evaluation_code_sha256": evaluation_code_hashes(),
        "launcher_sha256": sha256(Path(__file__)),
        "target_producer_sha256": manifest["producer_sha256"],
        "execution": spec["execution"],
        "python_version": platform.python_version(),
        "dependencies": {
            name: importlib.metadata.version(name)
            for name in ("numpy", "pandas", "polars", "scipy", "lightgbm", "pyarrow")
        },
        "lockfile_sha256": sha256(ROOT / "uv.lock"),
        "shard_rule": "sorted_scheduled_sessions[index::8]; all permitted inherited past",
        "checkpoint_rule": (
            "target-specific immutable components and sessions; hash/key/target parity required"
        ),
        "aggregation_rule": "all eight shards exit zero; aggregate-only never fits",
        "RESEARCH_ONLY": True,
        "capital_go": False,
    }
    write_json_once(release_path(horizon), release)
    return release, root


def run_window(digest: str, window: str, horizon: int) -> int:
    spec = load_spec(SPEC, digest)
    # One global launcher lock caps the whole v4 run at eight simultaneous shards.
    with window_lock(Path(spec["data_root"]) / "operations" / "execution.lock"):
        require_predecessors(spec, digest, window, horizon)
        return _run_window_locked(digest, window, horizon)


def require_predecessors(spec: dict[str, Any], digest: str, window: str, horizon: int) -> None:
    """Inspect only completed receipts/hashes, never preceding estimates or signs."""
    order = spec["execution"]["order"]
    current = f"{horizon}/{window}"
    if current not in order:
        raise ValueError("RP4_V4_UNREGISTERED_EXECUTION_STEP")
    for entry in order[: order.index(current)]:
        previous_horizon_text, previous_window = entry.split("/")
        previous_horizon = int(previous_horizon_text)
        stage = "b2" if previous_window == "primary" else "b3"
        public = ROOT / "artifacts" / f"rp4_v4_{stage}_rv{previous_horizon}"
        receipt_path = public / "receipt.json"
        if not receipt_path.exists() or not release_path(previous_horizon).exists():
            raise ValueError(f"RP4_V4_PREDECESSOR_NOT_COMPLETE:{entry}")
        receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        previous_release = json.loads(release_path(previous_horizon).read_text(encoding="utf-8"))
        if (
            receipt["status"] != "COMPLETE"
            or receipt["exit_code"] != 0
            or receipt["window"] != previous_window
            or receipt["horizon_minutes"] != previous_horizon
            or receipt["stage"] != stage.upper()
            or previous_release["specification_sha256"] != digest
            or receipt["release_sha256"] != sha256(release_path(previous_horizon))
            or len(receipt["commands"]) != SHARDS + 1
            or any(
                item["exit_code"] != 0 or sha256(Path(item["log"])) != item["log_sha256"]
                for item in receipt["commands"]
            )
            or len(receipt["artifacts_sha256"]) != 3
            or any(
                sha256(Path(path)) != value for path, value in receipt["artifacts_sha256"].items()
            )
        ):
            raise ValueError(f"RP4_V4_PREDECESSOR_RECEIPT_DRIFT:{entry}")


def host_resources() -> dict[str, Any]:
    try:
        import psutil

        memory_bytes: int | None = int(psutil.virtual_memory().total)
    except ImportError:
        memory_bytes = None
    return {
        "logical_cpu_count": os.cpu_count(),
        "physical_memory_bytes": memory_bytes,
        "memory_status": "VERIFIED"
        if memory_bytes is not None
        else "NO VERIFICABLE: psutil unavailable",
        "os": platform.platform(),
        "session_shards": SHARDS,
        "threads_per_model": THREADS,
        "maximum_model_threads": SHARDS * THREADS,
        "blas_threads_per_child": THREADS,
    }


def _run_window_locked(digest: str, window: str, horizon: int) -> int:
    started_at = datetime.now(UTC).isoformat()
    started_clock = time.perf_counter()
    release, root = prepare(digest, horizon)
    stage = "b2" if window == "primary" else "b3"
    output = root / "evaluation" / f"rv{horizon}" / window
    public = ROOT / "artifacts" / f"rp4_v4_{stage}_rv{horizon}"
    results = [
        public / "summary.json",
        public / "session_losses.csv",
        output / "fit_diagnostics.json",
    ]
    common = [
        sys.executable,
        "-B",
        "-m",
        "artifacts.rp4_v4_code.evaluate_v4",
        "--spec",
        str(SPEC),
        "--spec-sha256",
        digest,
        "--release",
        str(release_path(horizon)),
        "--horizon",
        str(horizon),
        "--window",
        window,
        "--threads",
        str(THREADS),
        "--shard-count",
        str(SHARDS),
    ]
    expected = [subprocess.list2cmdline(common + ["--shard-index", str(i)]) for i in range(SHARDS)]
    expected.append(subprocess.list2cmdline(common + ["--aggregate-only"]))
    receipt_path = public / "receipt.json"
    if receipt_path.exists():
        previous = json.loads(receipt_path.read_text(encoding="utf-8"))
        if (
            previous["status"] != "COMPLETE"
            or previous["exit_code"] != 0
            or previous["release_sha256"] != sha256(release_path(horizon))
            or previous["evaluation_code_sha256"] != release["evaluation_code_sha256"]
            or previous["window"] != window
            or previous["stage"] != stage.upper()
            or previous["horizon_minutes"] != horizon
            or [item["command"] for item in previous["commands"]] != expected
            or set(previous["artifacts_sha256"]) != {str(path) for path in results}
            or any(
                sha256(Path(path)) != value for path, value in previous["artifacts_sha256"].items()
            )
            or any(
                item["exit_code"] != 0 or sha256(Path(item["log"])) != item["log_sha256"]
                for item in previous["commands"]
            )
        ):
            raise ValueError("RP4_V4_COMPLETED_WINDOW_RECEIPT_DRIFT")
        print(f"RP4_V4_WINDOW_ALREADY_COMPLETE:rv{horizon}:{window}", flush=True)
        return 0
    attempt = (
        root
        / "operations"
        / (f"rv{horizon}_{window}_" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ"))
    )
    attempt.mkdir(parents=True, exist_ok=False)
    env = os.environ.copy()
    env.update(
        dict.fromkeys(
            (
                "OPENBLAS_NUM_THREADS",
                "OMP_NUM_THREADS",
                "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS",
                "POLARS_MAX_THREADS",
            ),
            str(THREADS),
        )
    )
    env["PYTHONPATH"] = os.pathsep.join(
        (str(ROOT), str(ROOT / "src"), str(ROOT / "scripts"), str(ROOT / "artifacts/rp4_code"))
    )
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    commands, processes = [], []
    failure = None
    with ExitStack() as stack:
        try:
            for index in range(SHARDS):
                command = common + ["--shard-index", str(index)]
                log = attempt / f"shard_{index}.log"
                stream = stack.enter_context(log.open("xb"))
                process = subprocess.Popen(
                    command,
                    cwd=ROOT,
                    env=env,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                    creationflags=flags,
                )
                processes.append((process, command, log))
            while any(process.poll() is None for process, _, _ in processes):
                count = len(list((output / "sessions").glob("*.json")))
                print(
                    f"RP4_V4_PROGRESS:rv{horizon}:{window}:completed_checkpoints={count}",
                    flush=True,
                )
                time.sleep(30)
        except BaseException as error:
            failure = {"type": type(error).__name__, "message": str(error)}
            for process, _, _ in processes:
                if process.poll() is None:
                    process.terminate()
            for process, _, _ in processes:
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
        for process, command, log in processes:
            commands.append(
                {
                    "command": subprocess.list2cmdline(command),
                    "exit_code": process.returncode,
                    "log": str(log),
                    "log_sha256": sha256(log),
                }
            )
    if (
        failure is None
        and len(commands) == SHARDS
        and all(item["exit_code"] == 0 for item in commands)
    ):
        command, log = common + ["--aggregate-only"], attempt / "aggregate.log"
        try:
            with log.open("xb") as stream:
                completed = subprocess.run(
                    command,
                    cwd=ROOT,
                    env=env,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                    creationflags=flags,
                    check=False,
                )
            commands.append(
                {
                    "command": subprocess.list2cmdline(command),
                    "exit_code": completed.returncode,
                    "log": str(log),
                    "log_sha256": sha256(log),
                }
            )
        except BaseException as error:
            failure = {"type": type(error).__name__, "message": str(error)}
    success = (
        failure is None
        and len(commands) == SHARDS + 1
        and all(item["exit_code"] == 0 for item in commands)
    )
    receipt = {
        "stage": stage.upper(),
        "window": window,
        "horizon_minutes": horizon,
        "target_key": release["target_key"],
        "status": "COMPLETE" if success else "FAILED_ATTEMPT_PRESERVED",
        "exit_code": 0 if success else 1,
        "release_sha256": sha256(release_path(horizon)),
        "execution_failure": failure,
        "commands": commands,
        "artifacts_sha256": {str(path): sha256(path) for path in results if success},
        "evaluation_code_sha256": release["evaluation_code_sha256"],
        "started_at_utc": started_at,
        "completed_at_utc": datetime.now(UTC).isoformat(),
        "elapsed_seconds": time.perf_counter() - started_clock,
        "resources": host_resources(),
    }
    write_json_once(attempt / "receipt.json", receipt)
    if success:
        write_json_once(public / "receipt.json", receipt)
    print(
        json.dumps(
            {
                "status": receipt["status"],
                "horizon_minutes": horizon,
                "window": window,
                "receipt": str(attempt / "receipt.json"),
            }
        ),
        flush=True,
    )
    return int(receipt["exit_code"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec-sha256", required=True)
    parser.add_argument("--horizon", type=int, choices=(5, 15), required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare-only", action="store_true")
    mode.add_argument("--window", choices=("primary", "confirmation"))
    args = parser.parse_args()
    if args.prepare_only:
        prepare(args.spec_sha256, args.horizon)
        print("RP4_V4_RELEASE_PINNED:" + sha256(release_path(args.horizon)), flush=True)
        return 0
    return run_window(args.spec_sha256, args.window, args.horizon)


if __name__ == "__main__":
    raise SystemExit(main())
