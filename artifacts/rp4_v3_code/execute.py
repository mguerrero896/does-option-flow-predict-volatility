"""Bind v3 inputs/code, run disjoint session shards and aggregate without re-fitting."""

from __future__ import annotations

import argparse
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
from artifacts.rp4_v3_code.evaluate_v3 import (
    ROOT,
    evaluation_code_hashes,
    evaluation_panel_path,
    load_spec,
)
from artifacts.rp4_v3_code.freeze import BASE_SHA

SHARDS = 4
THREADS = 4
SPEC = ROOT / "artifacts/rp4_v3_a1_empty_window/specification.json"
RELEASE = ROOT / "artifacts/rp4_v3_a2/evaluation_release.json"


def prepare(digest: str) -> tuple[dict[str, Any], Path]:
    spec = load_spec(SPEC, digest)
    root = Path(spec["data_root"]).resolve()
    panel = evaluation_panel_path(spec)
    materialized = panel.parent
    manifest_path = materialized / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest["spec_sha256"] != digest
        or manifest["preserved_unaffected_values_exact_by_keys"] is not True
        or manifest["preserved_values_exact_by_keys"] is not False
        or manifest["base_panel_sha256"] != BASE_SHA
        or manifest["model_fits"] != 0
        or manifest["excluded_origins"] != 0
        or manifest["excluded_sessions"] != 0
        or manifest["changed_columns_only"] != spec["empty_window_addendum"]["columns_to_nan"]
        or manifest["changed_origins_only"] != "finite_corresponding_trade_count_equal_zero"
        or manifest["recode_producer_sha256"]
        != sha256(ROOT / "artifacts/rp4_v3_code/empty_windows.py")
    ):
        raise ValueError("RP4_V3_RELEASE_MATERIALIZATION_CONTRACT")
    if any(not Path(name).is_absolute() for name in manifest["artifacts"]):
        raise ValueError("RP4_V3_RELEASE_MATERIALIZATION_PATH_NOT_ABSOLUTE")
    pinned = {Path(name).resolve(): value for name, value in manifest["artifacts"].items()}
    for path, value in pinned.items():
        if not path.is_relative_to(root) or sha256(path) != value:
            raise ValueError("RP4_V3_RELEASE_MATERIALIZATION_ARTIFACT_DRIFT")
    panel_hash = sha256(panel)
    if pinned.get(panel) != panel_hash:
        raise ValueError("RP4_V3_RELEASE_PANEL_NOT_PINNED")
    release = {
        "schema_version": "rp4-v3-evaluation-release-v1",
        "specification_sha256": digest,
        "effective_freeze_sha256": sha256(SPEC.parent / "freeze.json"),
        "evaluation_panel_relative_path": spec["evaluation_panel_relative_path"],
        "panel_sha256": panel_hash,
        "materialization_manifest_sha256": sha256(manifest_path),
        "evaluation_code_sha256": evaluation_code_hashes(),
        "launcher_sha256": sha256(Path(__file__)),
        "lock_helper_sha256": sha256(ROOT / "artifacts/rp4_v2_code/execute.py"),
        "execution": {"session_shards": SHARDS, "threads_per_model": THREADS},
        "python_version": platform.python_version(),
        "dependencies": {
            name: importlib.metadata.version(name)
            for name in ("numpy", "pandas", "polars", "scipy", "lightgbm", "pyarrow")
        },
        "lockfile_sha256": sha256(ROOT / "uv.lock"),
        "shard_rule": "sorted_scheduled_sessions[index::4]; each session uses full permitted past",
        "checkpoint_rule": (
            "immutable model components then complete session; reuse only hash/key/target parity"
        ),
        "aggregation_rule": "all session checkpoints verified; zero new fits",
        "RESEARCH_ONLY": True,
        "capital_go": False,
    }
    write_json_once(RELEASE, release)
    return release, root


def run_window(digest: str, window: str) -> int:
    spec = load_spec(SPEC, digest)
    with window_lock(Path(spec["data_root"]) / "operations" / f"{window}.lock"):
        return _run_window_locked(digest, window)


def _run_window_locked(digest: str, window: str) -> int:
    release, root = prepare(digest)
    spec = load_spec(SPEC, digest)
    stage = "b2" if window == "primary" else "b3"
    output = root / "evaluation" / window
    public = ROOT / "artifacts" / f"rp4_v3_{stage}"
    result_paths = [
        public / "summary.json",
        public / "session_losses.csv",
        output / "fit_diagnostics.json",
    ]
    common = [
        sys.executable,
        "-B",
        "-m",
        "artifacts.rp4_v3_code.evaluate_v3",
        "--spec",
        str(SPEC),
        "--spec-sha256",
        digest,
        "--panel",
        str(evaluation_panel_path(spec)),
        "--release",
        str(RELEASE),
        "--window",
        window,
        "--output",
        str(output),
        "--public-output",
        str(public),
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
            or previous["release_sha256"] != sha256(RELEASE)
            or previous["evaluation_code_sha256"] != release["evaluation_code_sha256"]
            or previous["window"] != window
            or previous["stage"] != stage.upper()
            or [item["command"] for item in previous["commands"]] != expected
            or set(previous["artifacts_sha256"]) != {str(path) for path in result_paths}
            or any(
                sha256(Path(path)) != value for path, value in previous["artifacts_sha256"].items()
            )
            or any(
                item["exit_code"] != 0 or sha256(Path(item["log"])) != item["log_sha256"]
                for item in previous["commands"]
            )
        ):
            raise ValueError("RP4_V3_COMPLETED_WINDOW_RECEIPT_DRIFT")
        print(f"RP4_V3_WINDOW_ALREADY_COMPLETE:{window}", flush=True)
        return 0
    attempt = root / "operations" / (window + "_" + datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ"))
    attempt.mkdir(parents=True, exist_ok=False)
    commands = []
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    failure = None
    with ExitStack() as stack:
        processes = []
        try:
            for index in range(SHARDS):
                command = common + ["--shard-index", str(index)]
                log = attempt / f"shard_{index}.log"
                stream = stack.enter_context(log.open("xb"))
                process = subprocess.Popen(
                    command, cwd=ROOT, stdout=stream, stderr=subprocess.STDOUT, creationflags=flags
                )
                processes.append((process, command, log))
            while any(process.poll() is None for process, _, _ in processes):
                count = len(list((output / "sessions").glob("*.json")))
                print(f"RP4_V3_PROGRESS:{window}:completed_checkpoints={count}", flush=True)
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
    if failure is None and len(commands) == SHARDS and all(x["exit_code"] == 0 for x in commands):
        command, log = common + ["--aggregate-only"], attempt / "aggregate.log"
        try:
            with log.open("xb") as stream:
                completed = subprocess.run(
                    command,
                    cwd=ROOT,
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
        and all(x["exit_code"] == 0 for x in commands)
    )
    receipt = {
        "stage": stage.upper(),
        "window": window,
        "status": "COMPLETE" if success else "FAILED_ATTEMPT_PRESERVED",
        "exit_code": 0 if success else 1,
        "release_sha256": sha256(RELEASE),
        "execution_failure": failure,
        "commands": commands,
        "artifacts_sha256": {str(path): sha256(path) for path in result_paths if success},
        "evaluation_code_sha256": release["evaluation_code_sha256"],
    }
    write_json_once(attempt / "receipt.json", receipt)
    if success:
        write_json_once(public / "receipt.json", receipt)
    print(
        json.dumps(
            {
                "status": receipt["status"],
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
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare-only", action="store_true")
    mode.add_argument("--window", choices=("primary", "confirmation"))
    args = parser.parse_args()
    if args.prepare_only:
        prepare(args.spec_sha256)
        print("RP4_V3_RELEASE_PINNED:" + sha256(RELEASE), flush=True)
        return 0
    return run_window(args.spec_sha256, args.window)


if __name__ == "__main__":
    raise SystemExit(main())
