"""Synthetic runner checks: transforms, causality and immutable component reuse."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd  # type: ignore[import-untyped]
import pytest
from artifacts.rp4_code import evaluate as v1
from artifacts.rp4_v3_code import evaluate_v3 as runner
from artifacts.rp4_v3_code import execute
from artifacts.rp4_v3_code.empty_windows import INDICATORS
from artifacts.rp4_v3_code.freeze import BASE_SHA, FEATURES


def test_new_transforms_once_and_old_routes_preserved() -> None:
    panel = pd.DataFrame(
        {
            "asset": ["A", "B"],
            "rv_back": [2.0, 4.0],
            **{x: [-3.0, 7.0] for x in FEATURES[:3]},
            FEATURES[3]: [0.0, 4.0],
        }
    )
    spec = {
        "assets": ["A", "B"],
        "feature_sets": {"B0": ["rv_back"], "B1": ["rv_back"], "B2": ["rv_back"] + FEATURES},
        "feature_transforms": {
            "rv_back": "log",
            **dict.fromkeys(FEATURES[:3], "signed"),
            FEATURES[3]: "log1p",
        },
    }
    trees, linear = runner.designs(panel, spec)
    np.testing.assert_array_equal(trees["B0"][:, 0], [2, 4])
    np.testing.assert_allclose(linear["B0"][:, 0], np.log([2, 4]))
    np.testing.assert_allclose(trees["B2"][:, 1], [-np.log(4), np.log(8)])
    np.testing.assert_allclose(linear["B2"][:, 1:5], trees["B2"][:, 1:5])
    np.testing.assert_allclose(trees["B2"][:, 4], [0, np.log(5)])
    panel.loc[0, FEATURES[3]] = -1
    with pytest.raises(ValueError, match="COUNT_NEGATIVE"):
        runner.designs(panel, spec)


def test_component_is_not_refitted_and_rejects_target_or_byte_drift(tmp_path: Path) -> None:
    frame = pd.DataFrame(
        {"asset": ["A"], "session_date": ["2020-01-02"], "origin_minute": [60], "rv30": [1.0]}
    )
    calls: list[int] = []

    def fit() -> tuple[runner.Array, dict[str, Any]]:
        calls.append(1)
        return np.array([1.1]), {"train_rows": 3}

    first = runner.component(tmp_path, "2020-01-02", "mean__linear__B0", {"pin": 1}, frame, fit)
    assert (
        runner.component(tmp_path, "2020-01-02", "mean__linear__B0", {"pin": 1}, frame, fit)
        == first
    )
    assert len(calls) == 1
    changed = frame.assign(rv30=2.0)
    with pytest.raises(ValueError, match="PARITY_DRIFT"):
        runner.component(tmp_path, "2020-01-02", "mean__linear__B0", {"pin": 1}, changed, fit)
    path = tmp_path / "components/2020-01-02/sessions/mean__linear__B0.json"
    value = json.loads(path.read_text())
    value["forecast"] = [9.0]
    path.write_text(json.dumps(value))
    with pytest.raises(ValueError, match="HASH_OR_BINDING_DRIFT"):
        runner.component(tmp_path, "2020-01-02", "mean__linear__B0", {"pin": 1}, frame, fit)


def test_high_gamma_threshold_uses_training_only_and_unknown_not_false() -> None:
    panel = pd.DataFrame(
        {
            "asset": ["A"] * 4 + ["B"],
            "session_date": ["2020-01-01"] * 3 + ["2020-01-03"] * 2,
            "origin_minute": [60, 65, 70, 305, 305],
            FEATURES[1]: [1.0, 2.0, 3.0, 100.0, np.nan],
        }
    )
    dates = panel["session_date"].to_numpy()
    train, test = dates < "2020-01-03", dates == "2020-01-03"
    args = (
        panel,
        {"embargo_minutes": 60},
        "2020-01-03",
        train,
        test,
        train,
        dates,
        np.arange(5),
        np.arange(5),
    )
    membership, threshold = runner.secondary_membership(*args)
    assert threshold["high_gamma"] == {"A": pytest.approx(7 / 3)}
    assert membership["high_gamma"] == [True, None]
    assert membership["last_hour"] == [True, True]
    assert membership["weekly_expiration"] == [True, True]
    panel.loc[3, FEATURES[1]] = 1e20
    assert runner.secondary_membership(*args)[1] == threshold


def test_empty_windows_are_raw_optional_indicators_and_nullable_strata() -> None:
    panel = pd.DataFrame(
        {
            "asset": ["A", "B", "A"],
            "base": [1.0, 2.0, 3.0],
            "session_date": ["2020-01-01", "2020-01-01", "2020-01-03"],
            "origin_minute": [60, 65, 305],
            FEATURES[1]: [1.0, 2.0, 4.0],
            INDICATORS[0]: [1.0, 0.0, np.nan],
            INDICATORS[1]: [0.0, 1.0, 1.0],
        }
    )
    spec = {
        "assets": ["A", "B"],
        "embargo_minutes": 60,
        "feature_sets": {"B0": ["base"], "B1": ["base"], "B2": ["base"] + INDICATORS},
        "feature_transforms": {"base": "log", **dict.fromkeys(INDICATORS, "raw")},
    }
    trees, linear = runner.designs(panel, spec)
    np.testing.assert_array_equal(trees["B2"][:, 1:3], panel[INDICATORS].to_numpy())
    np.testing.assert_array_equal(linear["B2"][:, 1:3], panel[INDICATORS].to_numpy())
    dates = panel["session_date"].to_numpy()
    test = np.ones(3, dtype=bool)
    train = dates == "2020-01-01"
    membership, _ = runner.secondary_membership(
        panel, spec, "2020-01-03", train, test, train, dates, np.arange(3), np.arange(3)
    )
    assert membership["window_empty_5m"] == [True, False, None]
    assert membership["window_empty_30m"] == [False, True, True]
    panel.loc[0, INDICATORS[0]] = 0.5
    with pytest.raises(ValueError, match="INDICATOR_NOT_BINARY"):
        runner.designs(panel, spec)


def _registration_copy(root: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, str]:
    """Copy only already-public registration/code metadata, never any panel."""
    original_root = runner.ROOT
    paths = [
        "artifacts/rp4_v3_a1/specification.json",
        "artifacts/rp4_v3_a1/freeze.json",
        "artifacts/rp4_v3_a1_empty_window/specification.json",
        "artifacts/rp4_v3_a1_empty_window/freeze.json",
        "artifacts/rp4_v2_a1/specification.json",
        "artifacts/rp4_v3_code/empty_windows.py",
        "docs/rp4/specification_v3.md",
        "docs/rp4/decision_131_v3.md",
        "docs/rp4/v3_addendum_stability_calibration.md",
        "docs/rp4/v3_window_empty_addendum.md",
        "docs/rp4/decision_132_v3_empty_windows.md",
    ]
    for relative in paths:
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes((original_root / relative).read_bytes())
    monkeypatch.setattr(runner, "ROOT", root)
    path = root / "artifacts/rp4_v3_a1_empty_window/specification.json"
    return path, v1.sha256(path)


def test_effective_registration_validates_full_original_and_addendum_chain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path, digest = _registration_copy(tmp_path, monkeypatch)
    spec = runner.load_spec(path, digest)
    assert [len(spec["feature_sets"][name]) for name in ("B0", "B1", "B2")] == [29, 69, 138]
    assert spec["feature_sets"]["B2"][-2:] == INDICATORS
    assert runner.evaluation_panel_path(spec).name == "panel.parquet"
    assert runner.evaluation_panel_path(spec).parent.name == "materialized_empty_windows"


@pytest.mark.parametrize(
    "relative",
    [
        "artifacts/rp4_v3_a1/specification.json",
        "artifacts/rp4_v3_a1/freeze.json",
        "artifacts/rp4_v3_a1_empty_window/freeze.json",
        "docs/rp4/v3_window_empty_addendum.md",
        "docs/rp4/decision_132_v3_empty_windows.md",
    ],
)
def test_effective_registration_rejects_ancestry_or_document_drift(
    relative: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path, digest = _registration_copy(tmp_path, monkeypatch)
    changed = tmp_path / relative
    changed.write_bytes(changed.read_bytes() + b"\n")
    with pytest.raises(ValueError, match="DRIFT|MISMATCH"):
        runner.load_spec(path, digest)


def test_effective_registration_cannot_change_models_even_with_consistent_fixture_hashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path, _ = _registration_copy(tmp_path, monkeypatch)
    spec = json.loads(path.read_text())
    spec["model"]["ridge"]["lambda_grid"] = [99]
    path.write_text(json.dumps(spec))
    digest = v1.sha256(path)
    freeze = path.parent / "freeze.json"
    payload = json.loads(freeze.read_text())
    payload["specification_sha256"] = digest
    freeze.write_text(json.dumps(payload))
    monkeypatch.setattr(runner, "EFFECTIVE_FREEZE_SHA", v1.sha256(freeze))
    with pytest.raises(ValueError, match="UNAUTHORIZED_SPECIFICATION_CHANGE"):
        runner.load_spec(path, digest)


def _prepare_fixture(root: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[dict[str, Any], Path]:
    data = root / "private"
    panel = data / "materialized_empty_windows/panel.parquet"
    panel.parent.mkdir(parents=True)
    panel.write_bytes(b"synthetic panel bytes; not a parquet and never loaded")
    recode = panel.parent / "recode_audit.json"
    recode.write_text("[]")
    census = panel.parent / "census.csv"
    census.write_text("N_origins\n1\n")
    spec: dict[str, Any] = {
        "data_root": str(data),
        "evaluation_panel_relative_path": runner.EVALUATION_PANEL_RELATIVE_PATH,
        "empty_window_addendum": {"columns_to_nan": {"5": ["ratio5"], "30": ["ratio30"]}},
    }
    spec_path = root / "metadata/specification.json"
    spec_path.parent.mkdir(parents=True)
    spec_path.write_text(json.dumps(spec))
    (spec_path.parent / "freeze.json").write_text('{"synthetic":true}')
    manifest = {
        "spec_sha256": "synthetic",
        "preserved_unaffected_values_exact_by_keys": True,
        "preserved_values_exact_by_keys": False,
        "base_panel_sha256": BASE_SHA,
        "model_fits": 0,
        "excluded_origins": 0,
        "excluded_sessions": 0,
        "changed_columns_only": spec["empty_window_addendum"]["columns_to_nan"],
        "changed_origins_only": "finite_corresponding_trade_count_equal_zero",
        "recode_producer_sha256": v1.sha256(runner.ROOT / "artifacts/rp4_v3_code/empty_windows.py"),
        "artifacts": {str(p): v1.sha256(p) for p in (panel, recode, census)},
    }
    manifest_path = panel.parent / "manifest.json"
    manifest_path.write_text(json.dumps(manifest))
    monkeypatch.setattr(execute, "SPEC", spec_path)
    monkeypatch.setattr(execute, "RELEASE", root / "synthetic_release.json")
    monkeypatch.setattr(execute, "load_spec", lambda *_: spec)
    return spec, manifest_path


def test_prepare_pins_effective_panel_and_is_idempotent_without_models(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec, manifest = _prepare_fixture(tmp_path, monkeypatch)
    release, data = execute.prepare("synthetic")
    assert release["panel_sha256"] == v1.sha256(runner.evaluation_panel_path(spec))
    assert release["materialization_manifest_sha256"] == v1.sha256(manifest)
    assert release["evaluation_panel_relative_path"] == runner.EVALUATION_PANEL_RELATIVE_PATH
    assert data == Path(spec["data_root"])
    assert execute.prepare("synthetic") == (release, data)


@pytest.mark.parametrize(
    "defect", ["exclusion", "unaffected_drift", "panel_unpinned", "relative_path"]
)
def test_prepare_rejects_contract_or_hash_shortcuts(
    defect: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec, path = _prepare_fixture(tmp_path, monkeypatch)
    manifest = json.loads(path.read_text())
    if defect == "exclusion":
        manifest["excluded_origins"] = 1
    elif defect == "unaffected_drift":
        manifest["preserved_unaffected_values_exact_by_keys"] = False
    elif defect == "panel_unpinned":
        del manifest["artifacts"][str(runner.evaluation_panel_path(spec))]
    else:
        manifest["artifacts"] = {"panel.parquet": "not_a_hash"}
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="CONTRACT|NOT_PINNED|NOT_ABSOLUTE"):
        execute.prepare("synthetic")


def test_launcher_failed_child_start_preserves_receipt_and_uses_new_panel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    spec, _ = _prepare_fixture(tmp_path, monkeypatch)
    release, data = execute.prepare("synthetic")
    monkeypatch.setattr(execute, "prepare", lambda _digest: (release, data))
    monkeypatch.setattr(execute, "ROOT", tmp_path)
    commands: list[list[str]] = []

    class Child:
        returncode: int | None = None
        terminated = False

        def poll(self) -> int | None:
            return self.returncode

        def terminate(self) -> None:
            self.terminated = True
            self.returncode = 1

        def wait(self, timeout: int) -> int | None:
            return self.returncode

    child = Child()

    def start(command: list[str], **kwargs: Any) -> Child:
        commands.append(command)
        if len(commands) == 2:
            raise OSError("synthetic second-child startup failure")
        return child

    def forbidden(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("Failed shards must not trigger aggregation")

    monkeypatch.setattr(subprocess, "Popen", start)
    monkeypatch.setattr(subprocess, "run", forbidden)
    assert execute._run_window_locked("synthetic", "primary") == 1
    assert child.terminated is True
    assert commands[0][commands[0].index("--panel") + 1] == str(runner.evaluation_panel_path(spec))
    receipt = json.loads(next((data / "operations").glob("primary_*/receipt.json")).read_text())
    assert receipt["status"] == "FAILED_ATTEMPT_PRESERVED"
    assert receipt["execution_failure"]["type"] == "OSError"
    assert len(receipt["commands"]) == 1


def test_real_estimators_synthetic_session_smoke_checks_all_scales_and_18_components(
    tmp_path: Path,
) -> None:
    generator = np.random.default_rng(407)
    day = np.repeat(np.arange(22), 30)
    dates = np.asarray(pd.date_range("2023-01-01", periods=22).strftime("%Y-%m-%d"), dtype=object)[
        day
    ]
    assets = np.where(np.arange(len(day)) % 3 == 0, "B", "A")
    base = generator.normal(size=len(day))
    panel = pd.DataFrame(
        {
            "asset": assets,
            "session_date": dates,
            "origin_minute": np.tile(np.arange(60, 210, 5), 22),
            "rv30": np.exp(-8 + 0.2 * base + generator.normal(0, 0.2, len(day))),
            "jump30": (generator.random(len(day)) > 0.55).astype(float) * 0.0001,
            "base": base,
            "surface": generator.normal(size=len(day)),
            **{name: generator.normal(size=len(day)) for name in FEATURES[:3]},
            FEATURES[-1]: generator.integers(0, 20, len(day)).astype(float),
            INDICATORS[0]: (np.arange(len(day)) % 7 == 0).astype(float),
            INDICATORS[1]: (np.arange(len(day)) % 11 == 0).astype(float),
        }
    )
    panel.loc[np.arange(len(panel)) % 8 == 0, "surface"] = np.nan
    origins = (
        pd.to_datetime(dates, utc=True).as_unit("ns").asi8
        + panel["origin_minute"].to_numpy() * 60 * 1_000_000_000
    )
    end = origins + 30 * 60 * 1_000_000_000
    spec = {
        "assets": ["A", "B"],
        "embargo_minutes": 60,
        "feature_sets": {
            "B0": ["base"],
            "B1": ["base", "surface"],
            "B2": ["base", "surface"] + FEATURES + INDICATORS,
        },
        "missing_allowed": ["surface"] + FEATURES + INDICATORS,
        "feature_transforms": {"base": "raw", "surface": "raw", **dict.fromkeys(INDICATORS, "raw")},
        "model": {
            "tuning_sessions": 10,
            "ridge": {"lambda_grid": [100]},
            "lightgbm": {
                "num_leaves": [3],
                "min_data_in_leaf": 10,
                "num_threads": 1,
                "num_boost_round": 25,
                "early_stopping_rounds": 5,
            },
        },
        "tail_models": {
            "linear_quantile": {
                "rho_initial": 1,
                "maxiter": 5000,
                "absolute_tolerance": 1e-5,
                "relative_tolerance": 1e-4,
                "balance_every": 25,
                "balance_ratio": 10,
                "balance_factor": 2,
            },
            "linear_jump": {"maxiter": 1000, "gtol": 1e-8, "ftol": 1e-12},
        },
    }
    trees, linear = runner.designs(panel, spec)
    mask = np.ones(len(panel), dtype=bool)
    record = runner.fit_session(
        tmp_path,
        str(dates[-1]),
        {"synthetic_fixture": True},
        panel,
        spec,
        trees,
        linear,
        dates,
        assets,
        origins,
        end,
        mask,
        mask,
        1,
    )
    assert len(record["fits"]) == 18
    assert record["tail_status"] == {
        "quantile": {"status": "COMPUTED"},
        "jump": {"status": "COMPUTED"},
    }
    assert len(record["mz_forecasts"]) == 3
    assert len(list((tmp_path / "components" / str(dates[-1]) / "sessions").glob("*.json"))) == 18
    for family in runner.FAMILIES:
        for name in v1.SETS:
            file = (
                tmp_path
                / "components"
                / str(dates[-1])
                / "sessions"
                / f"quantile__{family}__{name}.json"
            )
            component = json.loads(file.read_text())
            levels = np.asarray(component["forecast"])
            logs = np.asarray(record["tail_forecasts"]["quantile"][family][name])
            assert component["forecast_scale"] == "RV30_level"
            np.testing.assert_array_equal(logs, np.log(levels))
            residual = np.log(np.asarray(record["target"])) - np.log(levels)
            manual_pinball = np.maximum(0.9 * residual, -0.1 * residual)
            wired_residual = np.log(np.asarray(record["target"])) - logs
            np.testing.assert_array_equal(
                manual_pinball, np.maximum(0.9 * wired_residual, -0.1 * wired_residual)
            )
            assert np.all(np.isfinite(manual_pinball))
            assert (
                record["fits"][f"mean__{family}__{name}"]["inner_valid_sessions"]
                == np.unique(dates[(day >= 11) & (day < 21)]).tolist()
            )
    assert (
        record["secondary"]["window_empty_5m"]
        == (panel.loc[day == 21, INDICATORS[0]] == 1).tolist()
    )
    json.dumps(record, allow_nan=False)
