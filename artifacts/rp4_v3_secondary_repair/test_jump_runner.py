"""Synthetic/mocked jump-only execution, reuse and receipt tests; never real fits."""

from __future__ import annotations

import copy
import json
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from artifacts.rp4_v3_secondary_repair import jump_runner as run


def linear_fit(gradient: float = 2e-9) -> dict:
    solver = {"converged": True, "gradient_inf_norm_objective_over_n": gradient}
    return {
        "objective": "sum_binary_logloss_plus_lambda_l2_slopes",
        "lambda_grid": [0.0001, 0.01, 1.0, 100.0, 10000.0],
        "selected": {"lambda": 1.0, "validation_logloss": 0.5},
        "candidates": [
            {"lambda": value, "solver": solver.copy()} for value in (0.0001, 0.01, 1, 100, 10000)
        ],
        "solver_refit": solver,
    }


def sample() -> tuple[pd.DataFrame, dict]:
    days = np.repeat(pd.bdate_range("2023-01-02", periods=22).strftime("%Y-%m-%d").to_numpy(), 4)
    minutes = np.tile([35, 60, 300, 305], 22)
    origins = pd.to_datetime(days, utc=True) + pd.to_timedelta(minutes, unit="m")
    panel = pd.DataFrame(
        {
            "asset": np.tile(["A", "A", "B", "B"], 22),
            "session_date": days,
            "origin_minute": minutes,
            "forecast_origin_utc": origins,
            "target_end_utc": origins + pd.Timedelta(minutes=30),
            "rv30": 1e-5,
            "jump30": np.tile([0.0, 1e-7, 0.0, 1e-7], 22),
            "x": np.arange(len(days), dtype=float),
            "optional": np.nan,
        }
    )
    spec = {
        "assets": ["A", "B"],
        "mandatory_predictors": ["x"],
        "missing_allowed": ["optional"],
        "feature_sets": {"B0": ["x"], "B1": ["x", "optional"], "B2": ["x", "optional"]},
        "feature_transforms": {},
        "embargo_minutes": 60,
        "windows": {
            name: {"start": days[0], "end": days[-1]} for name in ("primary", "confirmation")
        },
        "model": {"tuning_sessions": 10},
        "inference": {"bootstrap": {"replications": 99, "block_length": 5, "seed": 20260907}},
    }
    return panel, spec


def source_component(
    tmp_path: Path, monkeypatch, keys: list, labels: list, *, model="jump__log_ridge_harq__B0"
) -> dict:
    original = tmp_path / "original"
    monkeypatch.setattr(run.inventory, "ORIGINAL", original)
    session = keys[0]["session_date"]
    path = original / "primary/components" / session / "sessions" / f"{model}.json"
    record = {
        "forecast": [0.4, 0.6, 0.4, 0.6][: len(keys)],
        "fit": linear_fit(2e-6),
        "keys": keys,
        "target": labels,
    }
    run.base.write_json_once(path, record)
    receipt_path = path.parent.parent / "session_receipts" / path.name
    run.base.write_json_once(receipt_path, {"sha256": run.base.sha256(path)})
    return {
        "session": session,
        "model": model,
        "relative_path": path.relative_to(original).as_posix(),
        "component_sha256": run.base.sha256(path),
        "receipt_sha256": run.base.sha256(receipt_path),
    }


def test_reuses_original_forecasts_without_new_fit_and_checks_resume(
    tmp_path: Path, monkeypatch
) -> None:
    panel, _ = sample()
    keys = panel.iloc[-4:][run.base.KEYS].to_dict("records")
    labels = [0.0, 1.0, 0.0, 1.0]
    source = source_component(tmp_path, monkeypatch, keys, labels)
    binding = {"window": "primary", "release_sha256": "SYNTHETIC"}

    def forbidden():
        raise AssertionError("A completed v3 component must never be refitted")

    args = (
        tmp_path / "out",
        keys[0]["session_date"],
        source["model"],
        binding,
        keys,
        labels,
        source,
        forbidden,
    )
    first = run.saved_component(*args)
    assert first["provenance"] == "REUSED_FROZEN_V3"
    assert first["forecast"] == [0.4, 0.6, 0.4, 0.6]
    assert run.saved_component(*args) == first
    assert first["fit"]["solver_refit"]["gradient_inf_norm_objective_over_n"] > 1e-8
    bad = (*args[:5], [1.0, 0.0, 0.0, 1.0], *args[6:])
    with pytest.raises(ValueError, match="CHECKPOINT_BINDING"):
        run.saved_component(*bad)


def test_new_numerical_failure_is_preserved_and_never_retried(tmp_path: Path) -> None:
    calls = []
    model = "jump__log_ridge_harq__B2"
    keys = [{"asset": "A", "session_date": "2023-01-31", "origin_minute": 35}]

    def failed():
        calls.append(1)
        raise run.original.ModelConvergenceError(
            "LOGISTIC_REPAIR", {"converged": False, "reason": "synthetic"}
        )

    args = (tmp_path, "2023-01-31", model, {"window": "primary"}, keys, [1.0], None, failed)
    first = run.saved_component(*args)
    assert first["status"] == "NO VERIFICABLE" and first["forecast"] is None
    assert run.saved_component(*args) == first and len(calls) == 1


def test_prepared_panel_preserves_jump_specific_mask_and_original_end(monkeypatch) -> None:
    panel, spec = sample()
    panel.loc[0, "jump30"] = np.nan
    panel.loc[1, "jump30"] = -1.0
    panel.loc[2, "rv30"] = np.nan
    read_options = []

    def read_panel(*args, **kwargs):
        read_options.append(kwargs)
        return panel.copy()

    monkeypatch.setattr(run.pd, "read_parquet", read_panel)
    monkeypatch.setattr(run.v3, "evaluation_panel_path", lambda *_: Path("SYNTHETIC.parquet"))
    prepared, eligible, jump_eligible, labels, origins, ends, _, _ = run.prepared_panel(
        spec, "primary"
    )
    raw = prepared["jump30"].to_numpy()
    np.testing.assert_array_equal(jump_eligible, eligible & np.isfinite(raw) & (raw >= 0))
    np.testing.assert_array_equal(
        labels, np.where(np.isfinite(raw), (raw > 0).astype(float), np.nan)
    )
    assert not jump_eligible[:3].any()
    assert np.all(ends - origins == 30 * 60 * 1_000_000_000)
    assert read_options == [{"use_threads": False}]


def test_full_mock_execution_calls_only_missing_jump_models_and_pure_auc(
    tmp_path: Path, monkeypatch
) -> None:
    panel, spec = sample()
    monkeypatch.setattr(run.pd, "read_parquet", lambda *_, **__: panel.copy())
    monkeypatch.setattr(run.v3, "evaluation_panel_path", lambda *_: Path("SYNTHETIC.parquet"))
    prepared = run.prepared_panel(spec, "primary")
    keys = prepared[0].iloc[-4:][run.base.KEYS].to_dict("records")
    labels = prepared[3][-4:].tolist()
    source = source_component(tmp_path, monkeypatch, keys, labels)
    session = keys[0]["session_date"]
    plan = {
        "window": "primary",
        "components": [source],
        "sessions": [
            {
                "session": session,
                "source_session_sha256": "ORIGINAL-SYNTHETIC",
                "keys_sha256": run.inventory.canonical_digest(keys),
                "labels_sha256": run.inventory.canonical_digest(labels),
                "missing_models": [m for m in run.inventory.MODELS if m != source["model"]],
            }
        ],
    }
    out = tmp_path / "new"
    release_path = out / "jump_release.json"
    run.base.write_json_once(release_path, {"code_sha256": {"SYNTHETIC": "HASH"}})
    monkeypatch.setattr(run, "OUT", out)
    monkeypatch.setattr(run, "RELEASE_PATH", release_path)
    monkeypatch.setattr(run, "prepare", lambda: {"code_sha256": {"SYNTHETIC": "HASH"}})
    monkeypatch.setattr(run, "code_hashes", lambda: {"SYNTHETIC": "HASH"})
    monkeypatch.setattr(run.v3, "load_spec", lambda *_: spec)
    reader = run.inventory.read_verified
    monkeypatch.setattr(
        run.inventory,
        "read_verified",
        lambda path, digest: (
            {"windows": [plan]} if path == run.INVENTORY_PATH else reader(path, digest)
        ),
    )
    monkeypatch.setattr(run, "prepared_panel", lambda *_: prepared)

    @contextmanager
    def resources():
        yield {"threads_total_max": 2, "priority": "BELOW_NORMAL", "process_id": 0}

    monkeypatch.setattr(run, "resource_scope", resources)
    monkeypatch.setattr(
        run.v3,
        "tail_options",
        lambda spec, family: {"num_threads": 4} if family == "lightgbm_qlike" else {},
    )
    calls = []

    def line(design, y, train, inner, valid, test, nullable, days, assets, options):
        calls.append("linear")
        assert set(np.unique(y[train])) == {0.0, 1.0}
        assert len(np.unique(days[valid])) == 10
        assert days[train].max() < session
        return np.full(int(test.sum()), 0.55), linear_fit()

    def tree(
        design, y, train, inner, valid, test, nullable, days, assets, options, *, family, threads
    ):
        calls.append("lightgbm")
        assert family == "lightgbm" and threads == options["num_threads"] == 2
        assert len(np.unique(days[valid])) == 10
        return np.full(int(test.sum()), 0.45), {"objective": "binary"}

    def forbidden(*args, **kwargs):
        raise AssertionError("No mean, quantile, MZ or complete legacy aggregate is permitted")

    monkeypatch.setattr(run, "fit_jump_linear", line)
    monkeypatch.setattr(run.original, "fit_jump", tree)
    for module, names in (
        (run.original, ("fit_ridge", "fit_lightgbm", "fit_quantile", "mz_secondary")),
        (run.aggregate, ("aggregate_records", "_quantile", "_mz")),
    ):
        for name in names:
            monkeypatch.setattr(module, name, forbidden)
    summary = run.run_window("primary")
    assert calls.count("linear") == 2 and calls.count("lightgbm") == 3
    assert summary["jump_secondary"]["N_origins"] == 4
    assert summary["jump_secondary"]["inference_role"] == "SECONDARY"
    before = copy.deepcopy(summary)
    assert run.run_window("primary") == before
    assert len(calls) == 5
    session_path = out / "evaluation/primary/sessions" / f"{session}.json"
    receipt_path = out / "evaluation/primary/session_receipts" / session_path.name
    session_bytes, receipt_bytes = session_path.read_bytes(), receipt_path.read_bytes()
    for altered, reason in (
        ("target", "TARGET_KEY_DRIFT"),
        ("forecast", "FORECAST_COMPONENT_PARITY"),
    ):
        record = json.loads(session_bytes)
        if altered == "target":
            record["jump_target"][0] = 1.0
        else:
            record["tail_forecasts"]["jump"]["lightgbm_qlike"]["B2"][0] = 0.9
        session_path.write_text(json.dumps(record), encoding="utf-8")
        receipt = json.loads(receipt_bytes)
        receipt["sha256"] = run.base.sha256(session_path)
        receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
        with pytest.raises(ValueError, match=reason):
            run.run_window("primary")
        session_path.write_bytes(session_bytes)
        receipt_path.write_bytes(receipt_bytes)
    assert len(calls) == 5
    component = out / "evaluation/primary/components" / session / "jump__lightgbm_qlike__B2.json"
    component.write_bytes(component.read_bytes() + b" ")
    with pytest.raises(ValueError, match="SESSION_COMPONENT_DRIFT"):
        run.run_window("primary")


def test_gradient_census_does_not_reclassify_old_ftol_success() -> None:
    rows = [
        {
            "model": "jump__log_ridge_harq__B0",
            "status": "COMPUTED",
            "provenance": "REUSED_FROZEN_V3",
            "fit": linear_fit(1e-6),
        },
        {
            "model": "jump__log_ridge_harq__B1",
            "status": "COMPUTED",
            "provenance": "NEW_MISSING_COMPONENT",
            "fit": linear_fit(1e-9),
        },
    ]
    result = run.gradient_census(rows)
    assert result[0]["refit_gradients_above_1e_minus8"] == 1
    assert result[0]["candidate_gradients_above_1e_minus8"] == 5
    assert result[0]["gradient_threshold"] == 1e-8
    assert result[0]["new_certificate_required"] is False
    assert result[1]["refit_gradients_above_1e_minus8"] == 0
    assert result[1]["new_certificate_required"] is True


def test_summary_cannot_be_reused_without_all_pinned_artifacts(tmp_path: Path) -> None:
    run.base.write_json_once(
        tmp_path / "summary_receipt.json", {"binding": {}, "artifacts_sha256": {}}
    )
    with pytest.raises(ValueError, match="SUMMARY_RECEIPT_SET"):
        run.read_completed_summary(tmp_path, {})


def test_arrow_preinitialized_pool_is_capped_in_worker_scope() -> None:
    import pyarrow as pa

    pa.set_cpu_count(8)
    with run.resource_scope() as resources:
        assert pa.cpu_count() == resources["arrow_cpu_threads"] == 2
        assert pa.io_thread_count() == resources["arrow_io_threads"] == 1
        assert resources["parquet_use_threads"] is False


def test_primary_closeout_requires_successful_receipt_before_confirmation(
    tmp_path: Path, monkeypatch
) -> None:
    binding = {"window": "primary", "release_sha256": "SYNTHETIC", "endpoint": "jump"}
    summary = {"status": "COMPLETE_SECONDARY_ATTEMPTS", "binding": binding}
    run.base.write_json_once(tmp_path / "summary.json", summary)
    run.base.write_json_once(tmp_path / "fit_diagnostics.json", [])
    run.base.write_json_once(tmp_path / "component_manifest.json", [])
    run.base.write_json_once(
        tmp_path / "summary_receipt.json",
        {
            "binding": binding,
            "artifacts_sha256": {
                name: run.base.sha256(tmp_path / name)
                for name in ("summary.json", "fit_diagnostics.json", "component_manifest.json")
            },
        },
    )
    # A crash after summary creation is not an exit-zero completion.
    with pytest.raises(FileNotFoundError):
        run.verify_complete_window(tmp_path, binding)
    monkeypatch.setattr(run, "code_hashes", lambda: {"SYNTHETIC": "HASH"})
    log = tmp_path / "stdout.log"
    log.write_text("synthetic closeout", encoding="utf-8")
    receipt = {
        "status": "COMPLETE",
        "exit_code": 0,
        "window": "primary",
        "release_sha256": "SYNTHETIC",
        "code_sha256": run.code_hashes(),
        "summary_sha256": run.base.sha256(tmp_path / "summary.json"),
        "log": str(log),
        "log_sha256": run.base.sha256(log),
        "artifacts_sha256": {
            str(tmp_path / name): run.base.sha256(tmp_path / name)
            for name in (
                "summary.json",
                "fit_diagnostics.json",
                "component_manifest.json",
                "summary_receipt.json",
            )
        },
    }
    run.base.write_json_once(tmp_path / "receipt.json", receipt)
    assert run.verify_complete_window(tmp_path, binding) == summary
    receipt["exit_code"] = 2
    (tmp_path / "receipt.json").write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ValueError, match="COMPLETE_WINDOW_RECEIPT_DRIFT"):
        run.verify_complete_window(tmp_path, binding)


def test_inventory_rejects_nonconverged_old_component(tmp_path: Path) -> None:
    keys = [{"asset": "A", "session_date": "2023-01-31", "origin_minute": 35}]
    model = "jump__log_ridge_harq__B0"
    path = tmp_path / "sessions" / f"{model}.json"
    fit = linear_fit()
    fit["solver_refit"]["converged"] = False
    component = {
        "session": model,
        "evaluation_session": "2023-01-31",
        "binding": {},
        "forecast_scale": "probability",
        "keys": keys,
        "target": [1.0],
        "forecast": [0.6],
        "fit": fit,
    }
    run.base.write_json_once(path, component)
    run.base.write_json_once(
        tmp_path / "session_receipts" / path.name,
        {"binding": {}, "session": model, "sha256": run.base.sha256(path)},
    )
    with pytest.raises(ValueError, match="UNCONVERGED_COMPONENT"):
        run.inventory.verify_component(path, {}, "2023-01-31", keys, [1.0])
