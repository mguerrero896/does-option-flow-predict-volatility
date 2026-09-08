"""Synthetic wiring and custody tests; no actual estimators or financial data."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import numpy as np
import pandas as pd  # type: ignore[import-untyped]
import pytest
from artifacts.rp4_code import evaluate as v1
from artifacts.rp4_v2_code import evaluate_v2 as v2
from artifacts.rp4_v4_code import evaluate_v4 as runner
from artifacts.rp4_v4_code import execute


def sample() -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
    days = np.repeat(pd.date_range("2023-01-01", periods=22).strftime("%Y-%m-%d"), 4)
    minute = np.tile([60, 65, 70, 75], 22)
    origins = pd.to_datetime(days, utc=True) + pd.to_timedelta(minute, unit="m")
    gamma = "rp4_gamma_imb_near_spot"
    base = pd.DataFrame(
        {
            "asset": np.tile(["A", "B", "A", "B"], 22),
            "session_date": days,
            "origin_minute": minute,
            "rv30": 20.0,
            "base": np.arange(88) + 1.0,
            "optional": np.nan,
            gamma: np.arange(88) / 100,
            "forecast_origin_utc": origins,
            "target_end_utc": origins + pd.Timedelta(minutes=30),
        }
    )
    targets = base[runner.KEYS].assign(
        rv_15=np.arange(88) / 100 + 1.0,
        rv_5=np.arange(88) / 100 + 0.5,
        target_end_15_utc=origins + pd.Timedelta(minutes=15),
        target_end_5_utc=origins + pd.Timedelta(minutes=5),
    )
    spec = {
        "assets": ["A", "B"],
        "mandatory_predictors": ["base"],
        "feature_sets": {
            "B0": ["base"],
            "B1": ["base", "optional"],
            "B2": ["base", "optional", gamma],
        },
        "feature_transforms": {"base": "raw", "optional": "raw", gamma: "signed"},
        "missing_allowed": ["optional", gamma],
        "horizons": {
            str(h): {"target_key": f"rv_{h}", "target_end_key": f"target_end_{h}_utc"}
            for h in (5, 15)
        },
        "embargo_minutes": 60,
        "model": {"tuning_sessions": 10, "ridge": {}, "lightgbm": {"num_threads": 4}},
    }
    return base, targets, spec


def test_real_spec_metadata_load_without_data_access() -> None:
    spec = runner.load_spec(
        execute.SPEC, "0a45b0a608110e2ca0dcf38accc2a0c2521ebbe9d223eb002e36ec51f78afd04"
    )
    assert [len(spec["feature_sets"][x]) for x in runner.SETS] == [29, 69, 138]
    assert spec["endpoint_scope"] == ["mean"]


@pytest.mark.parametrize("horizon", [5, 15])
def test_keyed_sidecar_preserves_old_target_features_and_mask(horizon: int) -> None:
    base, targets, spec = sample()
    base.loc[0, "rv30"] = np.nan
    targets.loc[0, f"rv_{horizon}"] = np.nan
    original = base.copy(deep=True)
    result = runner.prepare_panel(base, targets.iloc[::-1], spec, horizon)
    prepared, target, eligible = result[:3]
    pd.testing.assert_frame_equal(base, original)
    expected = original.sort_values(["session_date", "asset", "origin_minute"]).reset_index(
        drop=True
    )
    pd.testing.assert_frame_equal(prepared, expected)
    np.testing.assert_array_equal(eligible, v2.panel_masks(prepared, spec)[0])
    expected_targets = prepared[runner.KEYS].merge(targets, on=runner.KEYS, validate="one_to_one")
    np.testing.assert_array_equal(target, expected_targets[f"rv_{horizon}"].to_numpy())
    assert (prepared["rv30"].dropna() == 20).all()


@pytest.mark.parametrize("invalid", [np.nan, np.inf, 0.0, -1.0])
def test_invalid_new_target_cannot_silently_shrink_sample(invalid: float) -> None:
    base, targets, spec = sample()
    targets.loc[0, "rv_5"] = invalid
    with pytest.raises(
        ValueError, match='TARGET_INVALID_ON_INHERITED_MASK:.*"invalid_eligible_origins": 1'
    ):
        runner.prepare_panel(base, targets, spec, 5)


@pytest.mark.parametrize(
    "defect", ["missing", "duplicate", "wrong_key", "wrong_end", "wrong_original_end"]
)
def test_join_and_causal_interval_fail_closed(defect: str) -> None:
    base, targets, spec = sample()
    if defect == "missing":
        targets = targets.iloc[:-1]
    elif defect == "duplicate":
        targets = pd.concat([targets, targets.iloc[:1]])
    elif defect == "wrong_key":
        targets.loc[0, "origin_minute"] = 61
    elif defect == "wrong_end":
        targets.loc[0, "target_end_15_utc"] += pd.Timedelta(minutes=1)
    else:
        base.loc[0, "target_end_utc"] -= pd.Timedelta(minutes=15)
    with pytest.raises(ValueError, match="RP4_V4_"):
        runner.prepare_panel(base, targets, spec, 15)


def test_six_mean_components_receive_selected_target_and_never_refit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    base, targets, spec = sample()
    panel, target, eligible, _, _, _, origins, original_end, selected_end = runner.prepare_panel(
        base, targets, spec, 15
    )
    trees, linear = runner.v3.designs(panel, spec)
    calls: list[tuple[str, np.ndarray]] = []

    def fitted(
        family: str, target_values: np.ndarray, train: np.ndarray, test: np.ndarray
    ) -> tuple[np.ndarray, dict[str, Any]]:
        np.testing.assert_array_equal(target_values, target)
        assert not np.array_equal(target_values, panel["rv30"].to_numpy())
        calls.append((family, train.copy()))
        return np.full(int(test.sum()), float(np.mean(target_values[train]))), {
            "train_rows": int(train.sum())
        }

    def ridge(
        design: Any,
        y: Any,
        train: Any,
        inner: Any,
        valid: Any,
        test: Any,
        nullable: Any,
        dates: Any,
        assets: Any,
        options: Any,
    ) -> Any:
        return fitted("ridge", y, train, test)

    def tree(
        design: Any,
        y: Any,
        train: Any,
        inner: Any,
        valid: Any,
        test: Any,
        dates: Any,
        assets: Any,
        options: Any,
        *,
        threads: int,
    ) -> Any:
        assert threads == 4
        return fitted("tree", y, train, test)

    monkeypatch.setattr(runner, "fit_ridge", ridge)
    monkeypatch.setattr(runner, "fit_lightgbm", tree)
    binding = {"target_key": "rv_15", "horizon_minutes": 15, "window": "primary"}
    inputs = (
        tmp_path,
        "2023-01-22",
        binding,
        panel,
        target,
        spec,
        trees,
        linear,
        origins,
        original_end,
        selected_end,
        eligible,
        eligible,
    )
    record = runner.fit_session(*inputs)
    assert len(record["fits"]) == len(calls) == 6
    assert all(key.startswith("mean__") for key in record["fits"])
    assert not ({"mz_forecasts", "tail_forecasts", "jump_target"} & set(record))
    assert record["secondary"]["event"] == [None] * 4
    assert record["max_training_target_end_utc"] > record["max_training_selected_target_end_utc"]
    expected_masks = v1.causal_masks(
        panel["session_date"].to_numpy(), origins, original_end, eligible, "2023-01-22"
    )
    assert record["mask_counts"] == dict(
        zip(
            ("train", "inner_fit", "inner_valid", "test"),
            [int(x.sum()) for x in expected_masks],
            strict=True,
        )
    )
    assert runner.fit_session(*inputs) == record
    assert len(calls) == 6
    example = next((tmp_path / "components/2023-01-22/sessions").glob("*.json"))
    assert json.loads(example.read_text())["forecast_scale"] == "RV15_level"


def test_checkpoint_rejects_wrong_target_horizon_and_tampering(tmp_path: Path) -> None:
    base, _, _ = sample()
    expected = base.iloc[:1]
    binding = {"target_key": "rv_5", "horizon_minutes": 5}

    def call() -> tuple[np.ndarray, dict[str, Any]]:
        return np.array([1.1]), {}

    runner.component(
        tmp_path, "session", "mean__linear__B0", binding, expected, np.array([1.0]), call
    )
    with pytest.raises(ValueError, match="TARGET_OR_KEY_DRIFT"):
        runner.component(
            tmp_path, "session", "mean__linear__B0", binding, expected, np.array([2.0]), call
        )
    with pytest.raises(ValueError, match="HASH_OR_BINDING_DRIFT"):
        runner.component(
            tmp_path,
            "session",
            "mean__linear__B0",
            {**binding, "horizon_minutes": 15},
            expected,
            np.array([1.0]),
            call,
        )
    checkpoint = tmp_path / "components/session/sessions/mean__linear__B0.json"
    checkpoint.write_bytes(checkpoint.read_bytes() + b" ")
    with pytest.raises(ValueError, match="HASH_OR_BINDING_DRIFT"):
        runner.component(
            tmp_path, "session", "mean__linear__B0", binding, expected, np.array([1.0]), call
        )


@pytest.mark.parametrize(
    "index,count,threads,aggregate",
    [
        (-1, 8, 4, False),
        (8, 8, 4, False),
        (0, 4, 4, False),
        (0, 8, 8, False),
        (0, 8, 4, True),
        (None, 8, 4, False),
    ],
)
def test_invalid_shards_fail_before_any_panel_read(
    index: int | None, count: int, threads: int, aggregate: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, _, spec = sample()
    monkeypatch.setattr(runner, "load_spec", lambda *_: spec)
    args = argparse.Namespace(
        spec=Path("synthetic"),
        spec_sha256="synthetic",
        horizon=15,
        shard_count=count,
        shard_index=index,
        threads=threads,
        aggregate_only=aggregate,
    )
    with pytest.raises(ValueError, match="INVALID_SHARD_OR_THREAD"):
        runner.run(args)


def test_eight_shards_partition_419_without_overlap() -> None:
    scheduled = list(range(419))
    shards = [scheduled[index :: runner.SHARDS] for index in range(runner.SHARDS)]
    assert len(shards) == 8 and sorted(x for subset in shards for x in subset) == scheduled
    assert sum(map(len, shards)) == len(set(x for subset in shards for x in subset))


def launcher_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[dict[str, Any], Path]:
    _, _, spec = sample()
    data = tmp_path / "private"
    targets = data / "targets/panel.parquet"
    targets.parent.mkdir(parents=True)
    targets.write_bytes(b"synthetic; never read as a parquet")
    base = data / "base.parquet"
    base.write_bytes(b"synthetic base")
    producer = tmp_path / "artifacts/rp4_v4_code/materialize_targets.py"
    producer.parent.mkdir(parents=True)
    producer.write_text("# synthetic producer")
    (tmp_path / "uv.lock").write_text("synthetic")
    bar = data / "bar.parquet"
    bar.write_bytes(b"synthetic observed bars")
    bar_pins = data / "bar_input_pins.json"
    bar_pins.write_text(json.dumps({"sha256": {str(bar): v1.sha256(bar)}}))
    spec.update(
        data_root=str(data),
        target_panel_relative_path="targets/panel.parquet",
        base_panel={"path": str(base), "sha256": v1.sha256(base)},
        bar_input_pins={"path": str(bar_pins), "sha256": v1.sha256(bar_pins)},
        execution={
            "session_shards": 8,
            "threads_per_model": 4,
            "order": ["15/primary", "15/confirmation", "5/primary", "5/confirmation"],
        },
    )
    spec_path = tmp_path / "metadata/specification.json"
    spec_path.parent.mkdir()
    spec_path.write_text(json.dumps(spec))
    (spec_path.parent / "freeze_manifest.json").write_text("{}")
    manifest = {
        "spec_sha256": "synthetic",
        "base_panel_sha256": v1.sha256(base),
        "model_fits": 0,
        "key_set_exact": True,
        "preflight_pass": False,
        "status": "TARGET_PREFLIGHT_REQUIRES_INVESTIGATION",
        "excluded_origins": 0,
        "excluded_sessions": 0,
        "eligible_v3_rows": 192032,
        "eligible_v3_invalid": {"rv_15": 0, "rv_5": 0},
        "producer_path": "artifacts/rp4_v4_code/materialize_targets.py",
        "producer_sha256": v1.sha256(producer),
        "artifacts": {str(targets): v1.sha256(targets)},
        "reference_comparison": {
            "by_target": {
                key: {
                    "finite_bit_mismatches": 0,
                    "finite_mask_mismatches": count,
                    "all_value_bit_mismatches": count,
                }
                for key, count in (("rv_15", 4), ("rv_5", 2))
            },
            "eligible_v3_only": {
                key: {
                    "finite_bit_mismatches": 0,
                    "finite_mask_mismatches": 0,
                    "all_value_bit_mismatches": 0,
                    "finite_pairs": 81845,
                }
                for key in ("rv_15", "rv_5")
            },
        },
        "rv30_control": {
            "finite_bit_mismatches": 0,
            "finite_mask_mismatches": 0,
            "null_mask_mismatches": 14,
        },
    }
    evidence: dict[str, str] = {}
    for name in (
        "reference_comparison.json",
        "reference_discrepancies.parquet",
        "rv30_control.json",
        "rv30_control_discrepancies.parquet",
        "target_status.parquet",
    ):
        file = targets.parent / name
        file.write_text("synthetic audit input")
        manifest["artifacts"][str(file)] = evidence[str(file)] = v1.sha256(file)
    manifest_path = targets.parent / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    cases = [
        {
            "asset": "A",
            "session_date": "2023-01-01",
            "origin_minute": origin,
            "horizon": horizon,
            "eligible_v3": False,
            "missing_minutes": "255",
            "missing_closes": 1,
            "observed_closes": horizon,
            "required_closes": horizon + 1,
            "reference_finite": True,
            "reconstructed_finite": False,
            "reason": "missing_observed_closes",
            "session_fill_share": 1 / 390,
            "registered_fill_rule_reproduction_bit_exact": True,
            "resolution": "registered_forward_fill_versus_strict_actual_close_rule",
        }
        for origin, horizon in ((240, 15), (245, 15), (250, 5), (250, 15), (255, 5), (255, 15))
    ]
    nulls = [
        {
            "asset": "A",
            "session_date": "2023-01-02",
            "origin_minute": 200 + index,
            "base_is_null": True,
            "control_is_nan": True,
            "eligible_v3": False,
            "missing_minutes": "220",
            "resolution": "same_missing_target_null_in_base_and_nan_in_control_only",
        }
        for index in range(14)
    ]
    for name, rows in (("resolution_rows.csv", cases), ("rv30_null_rows.csv", nulls)):
        file = targets.parent / name
        pd.DataFrame(rows).to_csv(file, index=False)
        evidence[str(file)] = v1.sha256(file)
    auditor = tmp_path / "artifacts/rp4_v4_a2/resolve_target_mask.py"
    auditor.parent.mkdir(parents=True)
    auditor.write_text("# synthetic audit producer")
    resolution = {
        "status": "PASS_DISCREPANCIES_EXPLAINED_OUTSIDE_V3_ELIGIBILITY",
        "spec_sha256": "synthetic",
        "base_panel_sha256": v1.sha256(base),
        "target_panel_sha256": v1.sha256(targets),
        "original_manifest_sha256": v1.sha256(manifest_path),
        "producer_sha256": v1.sha256(producer),
        "finite_pair_mismatches": 0,
        "eligible_key_changes": 0,
        "eligible_invalid_targets": {"rv_15": 0, "rv_5": 0},
        "eligible_rows": 192032,
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
        "evidence_artifacts_sha256": evidence,
        "source_files_sha256": {str(bar): v1.sha256(bar)},
        "resolution_code_path": "artifacts/rp4_v4_a2/resolve_target_mask.py",
        "resolution_code_sha256": v1.sha256(auditor),
        "original_artifacts_modified": False,
        "original_materialization_exit_code": 2,
        "model_fits": 0,
    }
    resolution_path = targets.parent / "resolution.json"
    resolution_path.write_text(json.dumps(resolution))
    monkeypatch.setattr(execute, "ROOT", tmp_path)
    monkeypatch.setattr(execute, "SPEC", spec_path)
    monkeypatch.setattr(execute, "load_spec", lambda *_: spec)
    monkeypatch.setattr(execute, "evaluation_code_hashes", lambda: {"synthetic": "pinned"})
    monkeypatch.setattr(execute, "select_bar_pins", lambda pins: pins)
    monkeypatch.setattr(execute, "RESOLUTION_SHA256", v1.sha256(resolution_path))
    return spec, manifest_path


def test_prepare_target_specific_and_idempotent(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec, _ = launcher_fixture(tmp_path, monkeypatch)
    first = execute.prepare("synthetic", 15)
    assert execute.prepare("synthetic", 15) == first
    assert execute.prepare("synthetic", 5)[0]["target_key"] == "rv_5"
    assert first[0]["target_key"] == "rv_15" and first[1] == Path(spec["data_root"])
    assert first[0]["target_resolution_sha256"] == execute.RESOLUTION_SHA256
    assert first[0]["original_target_preflight_pass"] is False
    assert first[0]["resolved_target_preflight_pass"] is True


@pytest.mark.parametrize(
    "defect",
    ["missing", "unpinned", "finite", "eligible", "source", "case", "null", "evidence", "manifest"],
)
def test_resolution_requires_adopted_hash_original_pins_and_each_explanation(
    defect: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, manifest_path = launcher_fixture(tmp_path, monkeypatch)
    path = manifest_path.parent / "resolution.json"
    resolution = json.loads(path.read_text())
    if defect == "missing":
        path.unlink()
    elif defect == "unpinned":
        path.write_text(path.read_text() + " ")
    else:
        if defect == "finite":
            resolution["finite_pair_mismatches"] = 1
        elif defect == "eligible":
            resolution["eligible_key_changes"] = 1
        elif defect == "manifest":
            resolution["original_manifest_sha256"] = "changed"
        elif defect == "source":
            Path(next(iter(resolution["source_files_sha256"]))).write_bytes(b"source drift")
        elif defect == "evidence":
            del resolution["evidence_artifacts_sha256"][str(path.parent / "resolution_rows.csv")]
        else:
            csv_path = path.parent / (
                "resolution_rows.csv" if defect == "case" else "rv30_null_rows.csv"
            )
            rows = pd.read_csv(csv_path)
            rows.loc[0, "eligible_v3"] = True
            rows.to_csv(csv_path, index=False)
            resolution["evidence_artifacts_sha256"][str(csv_path)] = v1.sha256(csv_path)
        path.write_text(json.dumps(resolution))
        monkeypatch.setattr(execute, "RESOLUTION_SHA256", v1.sha256(path))
    with pytest.raises(ValueError, match="RP4_V4_RESOLUTION_"):
        execute.prepare("synthetic", 15)


@pytest.mark.parametrize("defect", ["mask", "keys", "hash", "unpin"])
def test_prepare_rejects_materialization_shortcuts(
    defect: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, path = launcher_fixture(tmp_path, monkeypatch)
    manifest = json.loads(path.read_text())
    if defect == "mask":
        manifest["eligible_v3_invalid"]["rv_5"] = 1
    elif defect == "keys":
        manifest["key_set_exact"] = False
    elif defect == "hash":
        manifest["producer_sha256"] = "changed"
    else:
        manifest["artifacts"] = {}
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="CONTRACT|NOT_PINNED"):
        execute.prepare("synthetic", 15)


def test_child_start_failure_stops_only_owned_process_and_does_not_aggregate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec, _ = launcher_fixture(tmp_path, monkeypatch)
    calls = []

    class Child:
        returncode: int | None = None

        def poll(self) -> int | None:
            return self.returncode

        def terminate(self) -> None:
            self.returncode = 1

        def wait(self, timeout: int) -> int | None:
            return self.returncode

    child = Child()

    def start(command: list[str], **kwargs: Any) -> Child:
        calls.append(command)
        assert kwargs["env"]["OMP_NUM_THREADS"] == "4"
        if len(calls) == 2:
            raise OSError("synthetic startup failure")
        return child

    def forbidden(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("aggregation forbidden")

    monkeypatch.setattr(subprocess, "Popen", start)
    monkeypatch.setattr(subprocess, "run", forbidden)
    assert execute._run_window_locked("synthetic", "primary", 15) == 1
    assert child.returncode == 1
    receipt = json.loads(
        next(
            (Path(spec["data_root"]) / "operations").glob("rv15_primary_*/receipt.json")
        ).read_text()
    )
    assert receipt["status"] == "FAILED_ATTEMPT_PRESERVED" and len(receipt["commands"]) == 1


def test_complete_window_reuse_starts_no_new_processes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec, _ = launcher_fixture(tmp_path, monkeypatch)
    calls = []

    def start(command: list[str], **kwargs: Any) -> Any:
        calls.append(command)
        return SimpleNamespace(returncode=0, poll=lambda: 0)

    def aggregate(command: list[str], **kwargs: Any) -> Any:
        public = tmp_path / "artifacts/rp4_v4_b2_rv15"
        output = Path(spec["data_root"]) / "evaluation/rv15/primary"
        public.mkdir(parents=True)
        output.mkdir(parents=True)
        (public / "summary.json").write_text("{}")
        (public / "session_losses.csv").write_text("synthetic\n")
        (output / "fit_diagnostics.json").write_text("[]")
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, "Popen", start)
    monkeypatch.setattr(subprocess, "run", aggregate)
    assert execute._run_window_locked("synthetic", "primary", 15) == 0
    assert len(calls) == 8
    execute.require_predecessors(spec, "synthetic", "confirmation", 15)
    with pytest.raises(ValueError, match="PREDECESSOR_NOT_COMPLETE:15/confirmation"):
        execute.require_predecessors(spec, "synthetic", "primary", 5)
    receipt = json.loads((tmp_path / "artifacts/rp4_v4_b2_rv15/receipt.json").read_text())
    assert receipt["elapsed_seconds"] >= 0
    assert receipt["started_at_utc"] <= receipt["completed_at_utc"]
    assert receipt["resources"]["maximum_model_threads"] == 32
    assert execute._run_window_locked("synthetic", "primary", 15) == 0
    assert len(calls) == 8


def test_execution_order_refuses_unfinished_predecessor(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec, _ = launcher_fixture(tmp_path, monkeypatch)
    execute.require_predecessors(spec, "synthetic", "primary", 15)
    with pytest.raises(ValueError, match="PREDECESSOR_NOT_COMPLETE"):
        execute.require_predecessors(spec, "synthetic", "confirmation", 15)
    with pytest.raises(ValueError, match="UNREGISTERED_EXECUTION_STEP"):
        execute.require_predecessors(spec, "synthetic", "primary", 30)
