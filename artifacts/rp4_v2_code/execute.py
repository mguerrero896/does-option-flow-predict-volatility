"""Pin a completed v2 panel, then run disjoint session shards and aggregate once."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import subprocess
import sys
import time
from collections.abc import Iterator
from contextlib import ExitStack, contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from artifacts.rp4_code.evaluate import sha256, write_json_once
from artifacts.rp4_v2_code.evaluate_v2 import ROOT, evaluation_code_hashes, load_spec

SHARDS = 4
THREADS = 4
SPEC = ROOT / "artifacts/rp4_v2_a1/specification.json"
RELEASE = ROOT / "artifacts/rp4_v2_a2/evaluation_release.json"


def prepare(digest: str) -> tuple[dict[str, Any], Path]:
    spec = load_spec(SPEC, digest)
    root = Path(spec["data_root"]).resolve()
    materialized = root / "materialized"
    manifest_path = materialized / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest["spec_sha256"] != digest
        or manifest["preserved_values_exact_by_keys"] is not True
        or manifest["iv_inclusive_bounds"] != [0.03, 3.0]
        or manifest["model_fits"] != 0
        or manifest["replaced_columns"]
        != [c for c in spec["feature_sets"]["B2"] if c not in spec["feature_sets"]["B0"]]
    ):
        raise ValueError("RP4_V2_RELEASE_MATERIALIZATION_CONTRACT")
    for name, pinned in manifest["artifacts"].items():
        path = Path(name).resolve()
        if path.parent != materialized or sha256(path) != pinned:
            raise ValueError("RP4_V2_RELEASE_MATERIALIZATION_ARTIFACT_DRIFT")
    panel_hash = sha256(materialized / "panel.parquet")
    if {Path(name).resolve(): value for name, value in manifest["artifacts"].items()}.get(
        materialized / "panel.parquet"
    ) != panel_hash:
        raise ValueError("RP4_V2_RELEASE_PANEL_MISSING_FROM_MATERIALIZATION")
    release = {
        "schema_version": "rp4-v2-evaluation-release-v1",
        "specification_sha256": digest,
        "panel_sha256": panel_hash,
        "materialization_manifest_sha256": sha256(manifest_path),
        "evaluation_code_sha256": evaluation_code_hashes(),
        "launcher_sha256": sha256(Path(__file__)),
        "execution": {"session_shards": SHARDS, "threads_per_model": THREADS},
        "python_version": platform.python_version(),
        "dependencies": {
            name: importlib.metadata.version(name)
            for name in ("numpy", "pandas", "polars", "scipy", "lightgbm", "pyarrow")
        },
        "lockfile_sha256": sha256(ROOT / "uv.lock"),
        "shard_rule": "sorted_scheduled_sessions[index::4]; every session uses full past panel",
        "aggregation_rule": "all completed checkpoints verified; no fit in aggregate-only",
        "RESEARCH_ONLY": True,
        "capital_go": False,
    }
    write_json_once(RELEASE, release)
    return release, root


@contextmanager
def window_lock(path: Path) -> Iterator[None]:
    """Use the same kernel-lock pattern as v1 acquire.tape_lock, in the v2 root."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        handle.seek(0)
        if not handle.read(1):
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        if sys.platform == "win32":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            handle.seek(0)
            if sys.platform == "win32":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def run_window(digest: str, window: str) -> int:
    spec = load_spec(SPEC, digest)
    with window_lock(Path(spec["data_root"]) / "operations" / f"{window}.lock"):
        return _run_window_locked(digest, window)


def _run_window_locked(digest: str, window: str) -> int:
    release, root = prepare(digest)
    stage = "b2" if window == "primary" else "b3"
    output = root / "evaluation" / window
    public = ROOT / "artifacts" / f"rp4_v2_{stage}"
    result_paths = [
        public / "summary.json",
        public / "session_losses.csv",
        output / "fit_diagnostics.json",
    ]
    common = [
        sys.executable,
        "-B",
        "-m",
        "artifacts.rp4_v2_code.evaluate_v2",
        "--spec",
        str(SPEC),
        "--spec-sha256",
        digest,
        "--panel",
        str(root / "materialized/panel.parquet"),
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
    expected_commands = [
        subprocess.list2cmdline(common + ["--shard-index", str(i)]) for i in range(SHARDS)
    ]
    expected_commands.append(subprocess.list2cmdline(common + ["--aggregate-only"]))
    previous_receipt = public / "receipt.json"
    if previous_receipt.exists():
        previous = json.loads(previous_receipt.read_text(encoding="utf-8"))
        if (
            previous["status"] != "COMPLETE"
            or previous["exit_code"] != 0
            or previous["release_sha256"] != sha256(RELEASE)
            or previous["evaluation_code_sha256"] != release["evaluation_code_sha256"]
            or previous["window"] != window
            or previous["stage"] != stage.upper()
            or [item["command"] for item in previous["commands"]] != expected_commands
            or set(previous["artifacts_sha256"]) != {str(path) for path in result_paths}
            or any(
                sha256(Path(path)) != digest
                for path, digest in previous["artifacts_sha256"].items()
            )
            or any(
                item["exit_code"] != 0 or sha256(Path(item["log"])) != item["log_sha256"]
                for item in previous["commands"]
            )
        ):
            raise ValueError("RP4_V2_COMPLETED_WINDOW_RECEIPT_DRIFT")
        print(f"RP4_V2_WINDOW_ALREADY_COMPLETE:{window}", flush=True)
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
                    command,
                    cwd=ROOT,
                    stdout=stream,
                    stderr=subprocess.STDOUT,
                    creationflags=flags,
                )
                processes.append((process, command, log))
            while any(process.poll() is None for process, _, _ in processes):
                count = len(list((output / "sessions").glob("*.json")))
                print(f"RP4_V2_PROGRESS:{window}:completed_checkpoints={count}", flush=True)
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
    codes = [item["exit_code"] for item in commands]
    if failure is None and len(commands) == SHARDS and all(code == 0 for code in codes):
        command = common + ["--aggregate-only"]
        log = attempt / "aggregate.log"
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
        and all(item["exit_code"] == 0 for item in commands)
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
        print("RP4_V2_RELEASE_PINNED:" + sha256(RELEASE), flush=True)
        return 0
    return run_window(args.spec_sha256, args.window)


if __name__ == "__main__":
    raise SystemExit(main())
