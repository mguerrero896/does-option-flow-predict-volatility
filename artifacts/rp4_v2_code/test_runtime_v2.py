"""Adversarial runtime contracts using synthetic panels and fake child processes only."""

from __future__ import annotations

import argparse
import copy
import json
import subprocess
import tempfile
import threading
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pytest
from artifacts.rp4_code import evaluate as v1
from artifacts.rp4_v2_code import evaluate_v2 as v2
from artifacts.rp4_v2_code import execute


@pytest.fixture
def synthetic_root() -> Iterator[Path]:
    with tempfile.TemporaryDirectory(prefix="rp4-v2-runtime-", dir="private-input/acbcf2ed66faca1f9565") as name:
        yield Path(name)


def make_runtime(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    insufficient: bool = False,
) -> dict[str, Any]:
    """No model implementation is called: every fit is an instrumented constant stub."""
    days = pd.bdate_range("2024-08-02", periods=72).strftime("%Y-%m-%d").to_numpy()
    rows = []
    for index, date in enumerate(days):
        for asset in ("A", "B"):
            for minute in (60, 65):
                origin = (
                    pd.Timestamp(date, tz="America/New_York") + pd.Timedelta(minutes=570 + minute)
                ).tz_convert("UTC")
                rows.append(
                    {
                        "asset": asset,
                        "session_date": date,
                        "origin_minute": minute,
                        "rv30": 1.0 + index / 100 + (asset == "B") / 10,
                        "base": np.nan if insufficient and index < 63 else 1.0 + index / 100,
                        "option": (np.nan, np.inf, -np.inf)[index % 3],
                        "flow": np.nan,
                        "rp4_eligible": True,
                        "forecast_origin_utc": origin,
                        "target_end_utc": origin + pd.Timedelta(minutes=30),
                    }
                )
    frame = pd.DataFrame(rows)
    panel = root / "materialized/panel.parquet"
    panel.parent.mkdir(parents=True)
    frame.to_parquet(panel, index=False)
    manifest = panel.parent / "manifest.json"
    v1.write_json_once(manifest, {"status": "SYNTHETIC"})
    spec = {
        "data_root": str(root),
        "assets": ["A", "B"],
        "windows": {"primary": {"start": days[0], "end": days[-1], "warmup_sessions": 60}},
        "model": {"lightgbm": {"num_threads": 4}, "ridge": {}, "tuning_sessions": 10},
        "embargo_minutes": 60,
        "mandatory_predictors": ["base"],
        "missing_allowed": ["option", "flow"],
        "feature_sets": {
            "B0": ["base"],
            "B1": ["base", "option"],
            "B2": ["base", "option", "flow"],
        },
        "feature_transforms": {"option": "log"},
        "inference": {"bootstrap": {"replications": 19}},
        "label": "SYNTHETIC RUNTIME TEST ONLY",
    }
    monkeypatch.setattr(v2, "load_spec", lambda *_: spec)
    release = root / "release.json"
    v1.write_json_once(
        release,
        {
            "panel_sha256": v1.sha256(panel),
            "materialization_manifest_sha256": v1.sha256(manifest),
            "specification_sha256": "synthetic",
            "evaluation_code_sha256": v2.evaluation_code_hashes(),
            "execution": {"session_shards": 4, "threads_per_model": 4},
        },
    )
    calls: list[dict[str, Any]] = []
    call_lock = threading.Lock()

    def fake_fit(*args: Any, **kwargs: Any) -> tuple[np.ndarray, dict[str, Any]]:
        design, target, train, inner_fit, inner_valid, test = args[:6]
        dates = args[7] if len(args) == 10 else args[6]
        session = str(np.unique(dates[test]).item())
        expected_train = set(frame.loc[frame["session_date"] < session, "session_date"])
        actual_train = set(dates[train])
        assert actual_train == expected_train
        assert set(dates[inner_valid]) == set(sorted(expected_train)[-10:])
        assert not (train & test).any()
        assert not (inner_fit & inner_valid).any()
        assert np.array_equal(train, inner_fit | inner_valid)
        assert frame.loc[train, "target_end_utc"].max() <= (
            frame.loc[test, "forecast_origin_utc"].min() - pd.Timedelta(minutes=60)
        )
        # Infinities must become missing BEFORE the pointwise log transformation.
        if design.shape[1] >= 3:
            assert np.isnan(design[:, 1]).all()
        with call_lock:
            calls.append({"session": session, "training_sessions": len(actual_train)})
        return np.full(int(test.sum()), float(target[train].mean())), {"synthetic": True}

    monkeypatch.setattr(v2, "fit_ridge", fake_fit)
    monkeypatch.setattr(v2, "fit_lightgbm", fake_fit)
    args = argparse.Namespace(
        spec=root / "spec.json",
        spec_sha256="synthetic",
        panel=panel,
        release=release,
        window="primary",
        output=root / "evaluation/primary",
        public_output=root / "public",
        threads=4,
        shard_count=4,
        shard_index=None,
        aggregate_only=True,
    )
    return {
        "args": args,
        "spec": spec,
        "frame": frame,
        "days": days,
        "calls": calls,
        "fit": fake_fit,
    }


def shard_args(runtime: dict[str, Any], index: int) -> argparse.Namespace:
    args = argparse.Namespace(**vars(runtime["args"]))
    args.shard_index, args.aggregate_only = index, False
    return args


@pytest.mark.parametrize(
    ("count", "index", "aggregate"),
    [
        (0, None, True),
        (-1, None, True),
        (4, -1, False),
        (4, 4, False),
        (4, 0, True),
        (4, None, False),
    ],
)
def test_invalid_shards_fail_before_any_fit(
    synthetic_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    count: int,
    index: int | None,
    aggregate: bool,
) -> None:
    runtime = make_runtime(synthetic_root, monkeypatch)
    args = runtime["args"]
    args.shard_count, args.shard_index, args.aggregate_only = count, index, aggregate
    with pytest.raises(ValueError, match="INVALID_SESSION_SHARD"):
        v2.run(args)
    assert runtime["calls"] == []


@pytest.mark.parametrize("drift", ["execution", "code"])
def test_release_drift_fails_before_any_fit(
    synthetic_root: Path, monkeypatch: pytest.MonkeyPatch, drift: str
) -> None:
    runtime = make_runtime(synthetic_root, monkeypatch)
    args = shard_args(runtime, 0)
    if drift == "execution":
        args.shard_count = 2
    else:
        hashes = v2.evaluation_code_hashes()
        hashes["artifacts/rp4_v2_code/models.py"] = "synthetic altered code"
        monkeypatch.setattr(v2, "evaluation_code_hashes", lambda: hashes)
    with pytest.raises(ValueError, match=f"RELEASE_{drift.upper()}_DRIFT"):
        v2.run(args)
    assert runtime["calls"] == []
    assert not (args.output / "sessions").exists()


def test_four_concurrent_shards_preserve_full_past_and_aggregate_without_refit(
    synthetic_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime = make_runtime(synthetic_root, monkeypatch)
    args = runtime["args"]
    with pytest.raises(ValueError, match="AGGREGATION_MISSING_COMPLETED_SESSION"):
        v2.run(args)
    assert runtime["calls"] == []
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda index: v2.run(shard_args(runtime, index)), range(4)))
    for index, result in enumerate(results):
        assert result["assigned_sessions"] == result["completed_sessions"] == 3
        assert result["shard_index"] == index
        assert result["skipped_sessions"] == []
    assert not (args.public_output / "summary.json").exists()
    assert len(runtime["calls"]) == 72
    for call in runtime["calls"]:
        assert call["training_sessions"] == list(runtime["days"]).index(call["session"])
    summary = v2.run(args)
    assert summary["N_sessions"] == summary["scheduled_sessions"] == 12
    losses = pd.read_csv(args.public_output / "session_losses.csv")
    assert list(losses["session_date"]) == list(runtime["days"][60:])
    saved = {
        str(path): v1.sha256(path)
        for folder in (args.output, args.public_output)
        for path in folder.rglob("*")
        if path.is_file()
    }
    for index in range(4):
        assert v2.run(shard_args(runtime, index)) == results[index]
    assert v2.run(args) == summary
    assert len(runtime["calls"]) == 72
    assert all(v1.sha256(Path(name)) == digest for name, digest in saved.items())


def test_interrupted_shard_resumes_only_incomplete_sessions(
    synthetic_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime = make_runtime(synthetic_root, monkeypatch)
    args = shard_args(runtime, 0)
    fit = runtime["fit"]
    ridge_calls = 0

    def fail_on_next_session(*fit_args: Any, **kwargs: Any) -> tuple[np.ndarray, dict[str, Any]]:
        nonlocal ridge_calls
        ridge_calls += 1
        if ridge_calls == 4:
            raise RuntimeError("synthetic interruption before second session completes")
        return fit(*fit_args, **kwargs)

    monkeypatch.setattr(v2, "fit_ridge", fail_on_next_session)
    with pytest.raises(RuntimeError, match="synthetic interruption"):
        v2.run(args)
    checkpoint = args.output / "sessions" / f"{runtime['days'][60]}.json"
    saved = v1.sha256(checkpoint)
    assert len(runtime["calls"]) == 6
    assert len(list((args.output / "sessions").glob("*.json"))) == 1
    monkeypatch.setattr(v2, "fit_ridge", fit)
    result = v2.run(args)
    assert result["completed_sessions"] == 3
    assert len(runtime["calls"]) == 18
    assert v1.sha256(checkpoint) == saved
    assert sum(call["session"] == runtime["days"][60] for call in runtime["calls"]) == 6


def test_insufficient_training_is_counted_without_fit_or_fabricated_prediction(
    synthetic_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    runtime = make_runtime(synthetic_root, monkeypatch, insufficient=True)
    for index in range(4):
        shard = v2.run(shard_args(runtime, index))
        assert shard["completed_sessions"] == 0
        assert len(shard["skipped_sessions"]) == 3
    summary = v2.run(runtime["args"])
    assert summary["status"] == "NO VERIFICABLE"
    assert len(summary["skipped_sessions"]) == 12
    assert {item["reason"] for item in summary["skipped_sessions"]} == {
        "no eligible origins",
        "RP4_INSUFFICIENT_TRAINING_SESSIONS",
    }
    assert runtime["calls"] == []
    assert not (runtime["args"].output / "sessions").exists()


@pytest.mark.parametrize("shape", ["scalar", "column", "short", "long"])
def test_malformed_forecast_is_never_sealed(
    synthetic_root: Path, monkeypatch: pytest.MonkeyPatch, shape: str
) -> None:
    runtime = make_runtime(synthetic_root, monkeypatch)

    def malformed(*args: Any, **kwargs: Any) -> tuple[np.ndarray, dict[str, Any]]:
        count = int(args[5].sum())
        shapes = {"scalar": (), "column": (count, 1), "short": (count - 1,), "long": (count + 1,)}
        return np.ones(shapes[shape]), {"synthetic": True}

    monkeypatch.setattr(v2, "fit_ridge", malformed)
    args = shard_args(runtime, 0)
    with pytest.raises(ValueError, match="FORECAST_SHAPE_MISMATCH"):
        v2.run(args)
    assert not (args.output / "sessions").exists()
    assert not (args.output / "session_receipts").exists()


def make_launcher(root: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Any]:
    checkout = root / "checkout"
    checkout.mkdir()
    (checkout / "uv.lock").write_text("synthetic lockfile only", encoding="utf-8")
    data = root / "private"
    materialized = data / "materialized"
    materialized.mkdir(parents=True)
    panel = materialized / "panel.parquet"
    # The launcher only hashes this fixture; it never reads it as market data.
    panel.write_bytes(b"synthetic panel bytes")
    spec = {
        "data_root": str(data),
        "feature_sets": {"B0": ["base"], "B2": ["base", "optional"]},
    }
    manifest = {
        "spec_sha256": "synthetic",
        "preserved_values_exact_by_keys": True,
        "iv_inclusive_bounds": [0.03, 3.0],
        "model_fits": 0,
        "replaced_columns": ["optional"],
        "artifacts": {str(panel): v1.sha256(panel)},
    }
    v1.write_json_once(materialized / "manifest.json", manifest)
    monkeypatch.setattr(execute, "ROOT", checkout)
    monkeypatch.setattr(execute, "SPEC", checkout / "spec.json")
    monkeypatch.setattr(execute, "RELEASE", checkout / "release.json")
    monkeypatch.setattr(execute, "load_spec", lambda *_: spec)
    monkeypatch.setattr(execute, "evaluation_code_hashes", lambda: {"synthetic": "code digest"})
    commands: list[list[str]] = []
    children = []

    class FakeProcess:
        def __init__(self, command: list[str], *, returncode: int | None = 0) -> None:
            self.command = command
            self.returncode = returncode
            self.terminated = self.killed = self.waited = False
            self.pid = 999999 + len(children)

        def poll(self) -> int | None:
            return self.returncode

        def terminate(self) -> None:
            self.terminated, self.returncode = True, -15

        def kill(self) -> None:
            self.killed, self.returncode = True, -9

        def wait(self, timeout: float | None = None) -> int:
            self.waited = True
            if self.returncode is None:
                raise subprocess.TimeoutExpired(self.command, timeout)
            return self.returncode

    def popen(command: list[str], **kwargs: Any) -> FakeProcess:
        commands.append(command)
        kwargs["stdout"].write(b"synthetic shard log\n")
        kwargs["stdout"].flush()
        child = FakeProcess(command)
        children.append(child)
        return child

    def run(command: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        assert len(children) == 4 and all(child.poll() == 0 for child in children)
        assert "--aggregate-only" in command
        public = Path(command[command.index("--public-output") + 1])
        output = Path(command[command.index("--output") + 1])
        v1.write_json_once(public / "summary.json", {"synthetic": True})
        v1.write_bytes_once(public / "session_losses.csv", b"synthetic\n")
        v1.write_json_once(output / "fit_diagnostics.json", [])
        kwargs["stdout"].write(b"synthetic aggregate log\n")
        kwargs["stdout"].flush()
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(execute.subprocess, "Popen", popen)
    monkeypatch.setattr(execute.subprocess, "run", run)
    return {
        "data": data,
        "checkout": checkout,
        "panel": panel,
        "manifest": manifest,
        "commands": commands,
        "children": children,
        "popen": popen,
        "process_type": FakeProcess,
    }


def test_launcher_prepare_is_idempotent_and_checks_materialization(
    synthetic_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = make_launcher(synthetic_root, monkeypatch)
    release, root = execute.prepare("synthetic")
    assert root == launcher["data"]
    assert release["execution"] == {"session_shards": 4, "threads_per_model": 4}
    assert execute.prepare("synthetic") == (release, root)
    assert launcher["commands"] == []
    launcher["panel"].write_bytes(b"synthetic altered panel")
    with pytest.raises(ValueError, match="MATERIALIZATION_ARTIFACT_DRIFT"):
        execute.prepare("synthetic")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("spec_sha256", "wrong"),
        ("preserved_values_exact_by_keys", False),
        ("iv_inclusive_bounds", [0.03, 4.0]),
        ("model_fits", 1),
        ("replaced_columns", []),
    ],
)
def test_launcher_prepare_rejects_each_materialization_contract_drift(
    synthetic_root: Path, monkeypatch: pytest.MonkeyPatch, field: str, value: Any
) -> None:
    launcher = make_launcher(synthetic_root, monkeypatch)
    manifest = copy.deepcopy(launcher["manifest"])
    manifest[field] = value
    (launcher["panel"].parent / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="MATERIALIZATION_CONTRACT"):
        execute.prepare("synthetic")
    assert launcher["commands"] == []
    assert not execute.RELEASE.exists()


def test_launcher_prepare_requires_the_panel_in_materialization_hashes(
    synthetic_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = make_launcher(synthetic_root, monkeypatch)
    manifest = copy.deepcopy(launcher["manifest"])
    manifest["artifacts"] = {}
    (launcher["panel"].parent / "manifest.json").write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="MATERIALIZATION"):
        execute.prepare("synthetic")
    assert launcher["commands"] == []
    assert not execute.RELEASE.exists()


def test_launcher_full_success_and_completed_reuse_never_spawn_again(
    synthetic_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = make_launcher(synthetic_root, monkeypatch)
    assert execute.run_window("synthetic", "primary") == 0
    assert [command[-2:] for command in launcher["commands"][:4]] == [
        ["--shard-index", str(index)] for index in range(4)
    ]
    assert launcher["commands"][-1][-1] == "--aggregate-only"
    receipt_path = launcher["checkout"] / "artifacts/rp4_v2_b2/receipt.json"
    receipt = json.loads(receipt_path.read_text())
    saved = v1.sha256(receipt_path)
    assert receipt["status"] == "COMPLETE"
    assert len(receipt["commands"]) == 5 and len(receipt["artifacts_sha256"]) == 3
    assert execute.run_window("synthetic", "primary") == 0
    assert len(launcher["commands"]) == 5
    assert v1.sha256(receipt_path) == saved
    log = Path(receipt["commands"][0]["log"])
    log.write_bytes(b"synthetic altered log")
    with pytest.raises(ValueError, match="COMPLETED_WINDOW_RECEIPT_DRIFT"):
        execute.run_window("synthetic", "primary")
    assert len(launcher["commands"]) == 5


def test_launcher_failed_shard_preserves_attempt_and_never_aggregates(
    synthetic_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = make_launcher(synthetic_root, monkeypatch)

    def failed_child(command: list[str], **kwargs: Any) -> Any:
        child = launcher["popen"](command, **kwargs)
        if command[-1] == "2":
            child.returncode = 7
        return child

    monkeypatch.setattr(execute.subprocess, "Popen", failed_child)
    assert execute.run_window("synthetic", "primary") == 1
    assert len(launcher["commands"]) == 4
    assert not (launcher["checkout"] / "artifacts/rp4_v2_b2/receipt.json").exists()
    receipts = list((launcher["data"] / "operations").glob("*/receipt.json"))
    assert len(receipts) == 1
    failed = json.loads(receipts[0].read_text())
    assert failed["status"] == "FAILED_ATTEMPT_PRESERVED"
    assert failed["exit_code"] == 1
    assert failed["artifacts_sha256"] == {}
    assert [item["exit_code"] for item in failed["commands"]] == [0, 0, 7, 0]


def test_launcher_partial_spawn_failure_reaps_started_children(
    synthetic_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = make_launcher(synthetic_root, monkeypatch)

    def fail_fourth(command: list[str], **kwargs: Any) -> Any:
        if command[-1] == "3":
            raise OSError("synthetic fourth child creation failed")
        child = launcher["popen"](command, **kwargs)
        child.returncode = None
        return child

    monkeypatch.setattr(execute.subprocess, "Popen", fail_fourth)
    try:
        result = execute.run_window("synthetic", "primary")
        assert result != 0
    except OSError as error:
        assert "synthetic fourth child" in str(error)
    assert len(launcher["children"]) == 3
    assert all(child.terminated or child.killed for child in launcher["children"])
    assert all(child.waited for child in launcher["children"])
    assert not (launcher["checkout"] / "artifacts/rp4_v2_b2/receipt.json").exists()
    receipts = list((launcher["data"] / "operations").glob("*/receipt.json"))
    assert len(receipts) == 1
    receipt = json.loads(receipts[0].read_text())
    assert receipt["status"] == "FAILED_ATTEMPT_PRESERVED"
    assert receipt["execution_failure"]["type"] == "OSError"
    assert len(receipt["commands"]) == 3


def test_launcher_lock_rejects_simultaneous_window_before_second_spawn(
    synthetic_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = make_launcher(synthetic_root, monkeypatch)
    entered, allow_return = threading.Event(), threading.Event()

    def held_first_child(command: list[str], **kwargs: Any) -> Any:
        child = launcher["popen"](command, **kwargs)
        if command[-1] == "0":
            entered.set()
            assert allow_return.wait(timeout=5)
        return child

    monkeypatch.setattr(execute.subprocess, "Popen", held_first_child)
    with ThreadPoolExecutor(max_workers=1) as pool:
        running = pool.submit(execute.run_window, "synthetic", "primary")
        try:
            assert entered.wait(timeout=5)
            with pytest.raises(OSError):
                execute.run_window("synthetic", "primary")
            assert len(launcher["commands"]) == 1
        finally:
            allow_return.set()
        assert running.result(timeout=5) == 0
    assert len(launcher["commands"]) == 5
    assert execute.run_window("synthetic", "primary") == 0
    assert len(launcher["commands"]) == 5


def test_launcher_wait_interruption_reaps_all_own_children_and_preserves_failure(
    synthetic_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = make_launcher(synthetic_root, monkeypatch)

    def running_child(command: list[str], **kwargs: Any) -> Any:
        child = launcher["popen"](command, **kwargs)
        child.returncode = None
        return child

    def interrupt_wait(_: float) -> None:
        raise KeyboardInterrupt("synthetic interruption")

    monkeypatch.setattr(execute.subprocess, "Popen", running_child)
    monkeypatch.setattr(execute.time, "sleep", interrupt_wait)
    assert execute.run_window("synthetic", "primary") == 1
    assert len(launcher["commands"]) == 4
    assert all(child.terminated and child.waited for child in launcher["children"])
    receipts = list((launcher["data"] / "operations").glob("*/receipt.json"))
    assert len(receipts) == 1
    receipt = json.loads(receipts[0].read_text())
    assert receipt["execution_failure"]["type"] == "KeyboardInterrupt"
    assert receipt["status"] == "FAILED_ATTEMPT_PRESERVED"


def test_launcher_failed_start_uses_kill_only_after_owned_child_timeout(
    synthetic_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = make_launcher(synthetic_root, monkeypatch)

    def stubborn_child(command: list[str], **kwargs: Any) -> Any:
        if command[-1] == "1":
            raise OSError("synthetic second child creation failed")
        child = launcher["popen"](command, **kwargs)
        child.returncode = None

        def ignore_terminate() -> None:
            child.terminated = True

        child.terminate = ignore_terminate
        return child

    monkeypatch.setattr(execute.subprocess, "Popen", stubborn_child)
    assert execute.run_window("synthetic", "primary") == 1
    assert len(launcher["children"]) == 1
    child = launcher["children"][0]
    assert child.terminated and child.killed and child.waited
    receipts = list((launcher["data"] / "operations").glob("*/receipt.json"))
    assert len(receipts) == 1
    receipt = json.loads(receipts[0].read_text())
    assert receipt["commands"][0]["exit_code"] == -9


def test_launcher_aggregate_start_failure_preserves_attempt_without_refitting(
    synthetic_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    launcher = make_launcher(synthetic_root, monkeypatch)

    def fail_aggregate(*_: Any, **kwargs: Any) -> Any:
        raise OSError("synthetic aggregate process creation failed")

    monkeypatch.setattr(execute.subprocess, "run", fail_aggregate)
    try:
        assert execute.run_window("synthetic", "primary") == 1
    except OSError as error:
        assert "synthetic aggregate" in str(error)
    assert len(launcher["commands"]) == 4
    assert all(child.returncode == 0 for child in launcher["children"])
    receipts = list((launcher["data"] / "operations").glob("*/receipt.json"))
    assert len(receipts) == 1
    receipt = json.loads(receipts[0].read_text())
    assert receipt["status"] == "FAILED_ATTEMPT_PRESERVED"
    assert receipt["execution_failure"]["type"] == "OSError"
    assert not (launcher["checkout"] / "artifacts/rp4_v2_b2/receipt.json").exists()


@pytest.mark.parametrize("field", ["commands", "artifacts_sha256"])
def test_launcher_completed_receipt_cannot_drop_required_evidence(
    synthetic_root: Path, monkeypatch: pytest.MonkeyPatch, field: str
) -> None:
    launcher = make_launcher(synthetic_root, monkeypatch)
    assert execute.run_window("synthetic", "primary") == 0
    path = launcher["checkout"] / "artifacts/rp4_v2_b2/receipt.json"
    receipt = json.loads(path.read_text())
    receipt[field] = [] if field == "commands" else {}
    path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ValueError, match="COMPLETED_WINDOW_RECEIPT_DRIFT"):
        execute.run_window("synthetic", "primary")
    assert len(launcher["commands"]) == 5
