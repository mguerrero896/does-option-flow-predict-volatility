"""End-to-end and boundary coverage for the RP2 scorecard producer."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
import pytest

from mds650.rp2 import scorecard as sut
from mds650.rp2.ladder import PRIMARY_MODELS
from mds650.rp2.panel import B1_FEATURES
from mds650.rp2.run_manifest import RunManifest, StepRecord


def _write_json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document), encoding="utf-8")


def _ladder() -> dict[str, object]:
    roles: dict[str, object] = {}
    for role_index, role in enumerate(("D", "V")):
        models: dict[str, object] = {}
        for family_index, family in enumerate(PRIMARY_MODELS):
            raw = {
                label: {
                    "raw": {
                        "estimate": -0.01 * (family_index + 1),
                        "ci_low": -0.02,
                        "ci_high": -0.001,
                        "mde": 0.005 + role_index * 0.001,
                    }
                }
                for label in ("delta_b1", "delta_b2_given_b1", "delta_total")
            }
            models[family] = {
                "qlike": {"B0": 1.0, "B0+B1": 0.9, "B0+B1+B2": 0.8},
                "contrasts": raw,
                "calibration": {
                    f"{family}|B0+B1+B2": {
                        "slope": 1.0 + family_index * 0.01,
                        "intercept": -0.1 * role_index,
                    }
                },
            }
        roles[role] = {
            "models": models,
            "test_rows": 40 + role_index,
            "rows": 100 + role_index,
            "sessions": 20 + role_index,
            "assets": ["AAPL", "AMZN", "META", "MSFT", "NVDA", "TSLA"],
            "evaluation_mask_sha256": f"mask-{role}",
        }
    return roles


def _manifest() -> RunManifest:
    step = StepRecord(
        name="build-b1",
        command=("python", "scripts/build.py"),
        exit_code=0,
        runtime_seconds=1.25,
        peak_memory_bytes=128,
        artifacts={"panel": "bytes"},
        content={"panel": "content"},
    )
    return RunManifest(
        run_id="test-run",
        code_commit="abc123",
        data_root="MDS650_DATA_ROOT",
        roles=("D", "V"),
        feature_registry_sha256="feature-hash",
        input_manifest_sha256="input-hash",
        model_config_sha256="model-hash",
        seeds={"model": 1},
        steps=(step,),
        started_at_utc="2026-08-29T00:00:00Z",
        finished_at_utc="2026-08-29T00:00:01Z",
    )


def _run_fixture(tmp_path: Path) -> tuple[Path, RunManifest]:
    keys = {
        "asset": ["AAPL", "MSFT"],
        "session_date": ["2026-06-01", "2026-06-01"],
        "origin_minute": [30, 35],
    }
    target = pl.DataFrame(keys)
    b0 = pl.DataFrame({**keys, "b0_value": [1.0, 2.0]})
    quote_bins = {
        f"b1_quote_age_bin_{index}": [10 if index == 10 else 0, 5 if index == 20 else 0]
        for index in range(len(sut.QUOTE_AGE_BIN_EDGES) + 1)
    }
    b1 = pl.DataFrame(
        {
            **keys,
            **{feature: [1.0, 2.0] for feature in B1_FEATURES},
            **quote_bins,
            "b1_contracts": [10, 20],
            "b1_rows_dropped_for_rate_or_dividend": [0, 0],
            "b1_post_cutoff_selected": [0, 0],
            "b1_duplicate_contracts_remaining": [0, 0],
        }
    )
    latency_bins = {
        f"b2_latency_bin_{index}": [100 if index == 5 else 0, 50 if index == 10 else 0]
        for index in range(len(sut.DURATION_BIN_EDGES) + 1)
    }
    b2 = pl.DataFrame(
        {
            **keys,
            **latency_bins,
            "b2_pit_violations": [0, 0],
            "b2_zero_dte_trades": [2, 3],
            "b2_counting_mean_latency_s": [1.0, 3.0],
            "b2_counting_trades": [10, 30],
            "b2_30m_multileg_premium_share": [0.1, 0.3],
            "b2_30m_premium": [100.0, 300.0],
            "b2_5m_is_empty_window": [0, 1],
        }
    )
    frames = {
        "rp2_block3_target/target_panel.parquet": target,
        "rp2_block4_b0/b0_panel.parquet": b0,
        "rp2_block5_surface/b1_surface_panel.parquet": b1,
        "rp2_block6_flow/b2_flow_panel.parquet": b2,
    }
    for relative, frame in frames.items():
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.write_parquet(path)
    _write_json(tmp_path / "rp2_block8_ladder/ladder.json", _ladder())
    _write_json(
        tmp_path / "rp2_block10_inference/inference.json",
        {"D": {"clusters": 20}, "V": {"clusters": 21}},
    )
    _write_json(
        tmp_path / "rp2_block5_surface/surface_coverage.json",
        {
            "coverage": {
                "b1_expiries": {"coverage": 0.9},
                "b1_implied_rate": {"coverage": 0.95},
            },
            "session_assets_without_tape": 1,
            "session_assets_too_sparse": 2,
        },
    )
    _write_json(
        tmp_path / "rp2_block6_flow/flow_coverage.json",
        {
            "session_assets_without_tape": 1,
            "session_assets_requested": 10,
            "provider_failures": ["one"],
        },
    )
    return tmp_path, _manifest()


def _complete_scorecard() -> dict[str, Any]:
    required = sut.required_fields()
    scorecard: dict[str, Any] = {
        group: dict.fromkeys(fields, 1.0)
        for group, fields in required.items()
        if group != "forecast"
    }
    scorecard["data"].update({"duplicate_keys": 0})
    scorecard["b1"].update(
        {
            "b1_post_cutoff_observations": 0,
            "b1_duplicate_contracts_per_snapshot": 0,
            "b1_rows_dropped_for_rate_or_dividend": 0,
        }
    )
    scorecard["b2"].update({"b2_pit_violation_count": 0})
    forecast_fields = [
        field
        for field in required["forecast"]
        if field not in ("calibration_slope", "calibration_intercept")
    ]
    scorecard["forecast"] = {
        family: {
            role: {field: 1.0 for field in forecast_fields} for role in ("D", "V")
        }
        for family in PRIMARY_MODELS
    }
    scorecard["forecast_calibration"] = {
        "calibration_slope": 1.0,
        "calibration_intercept": 0.0,
        "by_role_and_family": {
            role: {
                family: {"slope": 1.0, "intercept": 0.0} for family in PRIMARY_MODELS
            }
            for role in ("D", "V")
        },
    }
    return scorecard


def test_assemble_scorecard_measures_every_field_and_renders_stably(tmp_path: Path) -> None:
    run_dir, manifest = _run_fixture(tmp_path)

    scorecard = sut.assemble_scorecard(run_dir, manifest, peak_memory_bytes=256)
    rendered = sut.render_scorecard(scorecard)

    sut.assert_scorecard_complete(scorecard, required_roles=manifest.roles)
    assert scorecard["engineering"]["runtime_seconds"] == 1.25
    assert scorecard["engineering"]["peak_memory_bytes"] == 256
    assert scorecard["data"]["provider_failures"] == 2
    assert scorecard["b1"]["b1_core_coverage"] == 1.0
    assert scorecard["b1"]["b1_missing_rate_share"] == pytest.approx(0.05)
    assert scorecard["b2"]["b2_mean_provider_latency_s"] == pytest.approx(2.5)
    assert scorecard["b2"]["b2_multileg_share"] == pytest.approx(0.25)
    assert scorecard["b2"]["b2_empty_window_share"] == pytest.approx(0.5)
    assert scorecard["b2"]["b2_provider_failure_share"] == pytest.approx(0.1)
    assert "see `run_manifest.json`" in rendered
    assert "| `lightgbm_qlike` | D |" in rendered


def test_scorecard_helpers_measure_files_columns_and_distributions(tmp_path: Path) -> None:
    missing = tmp_path / "missing.parquet"
    path = tmp_path / "values.parquet"
    pl.DataFrame(
        {
            "number": [1.0, None, float("nan"), 3.0],
            "weighted": [1.0, None, 2.0, 3.0],
            "weight": [1.0, 0.0, 2.0, 3.0],
            "integer": [1, 2, 3, 4],
            "empty": [None, None, None, None],
        }
    ).write_parquet(path)

    assert sut._json(tmp_path / "missing.json") == {}
    json_path = tmp_path / "value.json"
    _write_json(json_path, {"ok": True})
    assert sut._json(json_path) == {"ok": True}
    assert sut._height(missing) is None
    assert sut._height(path) == 4
    assert sut._column(missing, "number") is None
    assert sut._column(path, "absent") is None
    assert sut._column(path, "number") is not None
    assert sut._quantile(missing, "number", 0.5) is None
    assert sut._quantile(path, "integer", 0.5) == 3.0
    assert sut._mean(missing, "number") is None
    assert sut._mean(path, "empty") is None
    assert sut._mean(path, "integer") == pytest.approx(2.5)
    assert sut._share(missing, "number", lambda values: values > 0) is None
    assert sut._share(path, "empty", lambda values: values.is_not_null()) == 0.0
    assert sut._share(path, "integer", lambda values: values > 2) == 0.5
    assert sut._sum(missing, "integer") is None
    assert sut._sum(path, "integer") == 10
    assert sut._null_count(missing, "number") is None
    assert sut._null_count(path, "number") == 2
    assert sut._null_count(path, "integer") == 0
    assert sut._quantile_where(missing, "number", "weight", 0.5) is None
    assert sut._quantile_where(path, "weighted", "weight", 0.5) == 2.0
    assert sut._weighted_mean(missing, "number", "weight") is None
    assert sut._weighted_mean(path, "weighted", "weight") == pytest.approx(14.0 / 6.0)
    assert sut._duplicate_keys(missing) is None

    keys = tmp_path / "keys.parquet"
    pl.DataFrame(
        {
            "asset": ["AAPL", "AAPL"],
            "session_date": ["2026-01-01", "2026-01-01"],
            "origin_minute": [30, 30],
        }
    ).write_parquet(keys)
    assert sut._duplicate_keys(keys) == 1

    zero = tmp_path / "zero.parquet"
    pl.DataFrame(
        {
            "share": [None, None],
            "value": [1.0, 2.0],
            "weight": [0.0, 0.0],
        }
    ).write_parquet(zero)
    assert sut.weighted_share(zero, "share", "weight") is None
    assert sut._quantile_where(zero, "value", "weight", 0.5) is None
    assert sut._weighted_mean(zero, "value", "weight") is None


def test_assemble_scorecard_covers_explicit_runtime_and_absent_b1(tmp_path: Path) -> None:
    run_dir, manifest = _run_fixture(tmp_path)
    (run_dir / "rp2_block5_surface/b1_surface_panel.parquet").unlink()

    with pytest.raises(ValueError, match="HISTOGRAM_BINS_INCOMPLETE"):
        sut.assemble_scorecard(run_dir, manifest, elapsed_seconds=2.0)


def test_assemble_scorecard_rejects_b1_without_core_features(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    run_dir, manifest = _run_fixture(tmp_path)
    from mds650.rp2 import feature_registry

    monkeypatch.setattr(feature_registry, "feature_map", lambda _group: ["absent_feature"])

    with pytest.raises(ValueError, match="b1_core_coverage:unmeasured"):
        sut.assemble_scorecard(run_dir, manifest)


def test_scorecard_coverage_duration_and_forecast_helpers_cover_boundaries() -> None:
    assert sut._coverage({"x": {"coverage": 0.5}}, "x") == 0.5
    assert sut._coverage({"x": {"coverage": None}}, "x") is None
    assert sut._coverage({"x": 0.25}, "x") == 0.25
    assert sut._coverage({}, "x") is None

    edges = np.asarray([1.0, 2.0], dtype=np.float64)
    assert sut.duration_bins(np.asarray([], dtype=np.float64), edges).tolist() == [0, 0, 0]
    counts = sut.duration_bins(np.asarray([0.5, 1.5, 3.0]), edges)
    assert counts.tolist() == [1, 1, 1]
    assert sut.duration_quantile(np.asarray([1, 0, 0]), 0.5, edges) == 1.0
    assert sut.duration_quantile(np.asarray([0, 0, 1]), 1.0, edges) == 2.0
    assert sut.duration_quantile(np.asarray([0, 1, 0]), 0.5, edges) == 1.0

    ladder = _ladder()
    block = sut._forecast_block(ladder, "gamma_glm")
    assert set(block) == {"D", "V"}
    assert block["D"]["delta_total"] == pytest.approx(-0.01)
    assert sut._forecast_block({"D": {"models": {}}}, "gamma_glm") == {}
    malformed = {
        "D": {
            "models": {
                "gamma_glm": {
                    "qlike": {},
                    "contrasts": {"delta_b1": "invalid"},
                }
            }
        }
    }
    assert sut._forecast_block(malformed, "gamma_glm")["D"]["delta_b1"] is None
    assert sut.calibration_table({"D": {"models": {}}}, ("D",)) == {}


@pytest.mark.parametrize(
    "value",
    [None, float("nan"), float("inf"), {}, [], (), {"x": None}, [1, None]],
)
def test_unmeasured_recurses_through_every_container(value: object) -> None:
    assert sut._unmeasured(value) is True


def test_scorecard_completeness_detects_all_structural_omissions() -> None:
    cases: list[tuple[str, Any, str]] = []

    absent = _complete_scorecard()
    absent["data"].pop("b0_rows")
    cases.append(("absent", absent, "data.b0_rows:absent"))

    undeclared = _complete_scorecard()
    undeclared["data"]["unexpected"] = 1
    cases.append(("undeclared", undeclared, "data.unexpected:undeclared"))

    empty_forecast = _complete_scorecard()
    empty_forecast["forecast"] = {}
    cases.append(("empty", empty_forecast, "forecast:empty"))

    absent_family = _complete_scorecard()
    absent_family["forecast"].pop(PRIMARY_MODELS[0])
    cases.append(("family", absent_family, f"forecast.{PRIMARY_MODELS[0]}:absent"))

    absent_role = _complete_scorecard()
    absent_role["forecast"][PRIMARY_MODELS[0]].pop("V")
    cases.append(("role", absent_role, f"forecast.{PRIMARY_MODELS[0]}.V:absent"))

    missing_leaf = _complete_scorecard()
    missing_leaf["forecast"][PRIMARY_MODELS[0]]["D"]["delta_b1"] = None
    cases.append(("leaf", missing_leaf, f"forecast.{PRIMARY_MODELS[0]}.D.delta_b1:unmeasured"))

    missing_headline = _complete_scorecard()
    missing_headline["forecast_calibration"]["calibration_slope"] = None
    cases.append(("headline", missing_headline, "forecast.calibration_slope:unmeasured"))

    missing_matrix = _complete_scorecard()
    missing_matrix["forecast_calibration"]["by_role_and_family"]["V"][PRIMARY_MODELS[0]][
        "intercept"
    ] = None
    cases.append(
        (
            "matrix",
            missing_matrix,
            f"forecast_calibration.V.{PRIMARY_MODELS[0]}.intercept:unmeasured",
        )
    )

    for _label, scorecard, expected in cases:
        with pytest.raises(ValueError, match=expected):
            sut.assert_scorecard_complete(scorecard)


def test_scorecard_invariants_reject_nonzero_counters() -> None:
    scorecard = _complete_scorecard()
    scorecard["data"]["duplicate_keys"] = 1

    with pytest.raises(ValueError, match="RP2_SCORECARD_INVARIANT_BREACH"):
        sut.assert_scorecard_invariants(scorecard)


def test_scorecard_config_falls_back_to_packaged_copy(monkeypatch: pytest.MonkeyPatch) -> None:
    original = Path.is_file

    def is_file(path: Path) -> bool:
        if path.name == "rp2_v3_scorecard_fields.json" and "configs" in path.parts:
            return False
        return original(path)

    monkeypatch.setattr(Path, "is_file", is_file)

    assert sut._config() == Path(sut.__file__).resolve().parent / "rp2_v3_scorecard_fields.json"
