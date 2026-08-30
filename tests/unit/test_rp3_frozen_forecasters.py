"""Behavioral coverage for the serialized RP3 forecaster boundary."""

from __future__ import annotations

import copy
import json
from dataclasses import replace
from pathlib import Path

import exchange_calendars as xcals
import numpy as np
import polars as pl
import pytest

from mds650.rp2.panel import (
    B0_FEATURES,
    B1_FEATURES,
    B2_FEATURES,
    chronological_split,
    common_evaluation_mask,
    load_merged_panel,
    session_rank,
)
from mds650.rp2.preprocessing import fit_preprocessor, transform_features
from mds650.rp3 import frozen_forecasters as sut


def _write_json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document), encoding="utf-8")


def _panel_fixture(
    tmp_path: Path,
    *,
    start: str = "2026-06-01",
    end: str = "2026-07-17",
) -> tuple[Path, Path, pl.DataFrame, dict[str, object]]:
    calendar = xcals.get_calendar("XNYS")
    sessions = [value.date().isoformat() for value in calendar.sessions_in_range(start, end)[:30]]
    rows = [
        (session, asset, minute)
        for session in sessions
        for asset in ("AAPL", "MSFT")
        for minute in (30, 35)
    ]
    keys = {
        "asset": [asset for _, asset, _ in rows],
        "session_date": [session for session, _, _ in rows],
        "origin_minute": [minute for _, _, minute in rows],
    }
    count = len(rows)

    def values(offset: float) -> list[float]:
        return [offset + 0.01 * index for index in range(1, count + 1)]

    b0 = pl.DataFrame(
        {
            **keys,
            "role": ["D"] * count,
            "rv30": values(0.1),
            **{name: values(1.0 + index) for index, name in enumerate(B0_FEATURES)},
        }
    )
    b1_payload = {
        name: values(2.0 + index) for index, name in enumerate(B1_FEATURES)
    }
    b1_payload["b1_surface_coverage"] = [1.0] * count
    b1 = pl.DataFrame({**keys, **b1_payload})
    b2 = pl.DataFrame(
        {
            **keys,
            **{name: values(3.0 + index) for index, name in enumerate(B2_FEATURES)},
            "b2_5m_is_empty_window": [0.0] * count,
        }
    )
    paths = {
        "b0_panel": tmp_path / "rp2_block4_b0" / "b0_panel.parquet",
        "b1_surface_panel": tmp_path
        / "rp2_block5_surface"
        / "b1_surface_panel.parquet",
        "b2_flow_panel": tmp_path / "rp2_block6_flow" / "b2_flow_panel.parquet",
    }
    for label, frame in (
        ("b0_panel", b0),
        ("b1_surface_panel", b1),
        ("b2_flow_panel", b2),
    ):
        paths[label].parent.mkdir(parents=True, exist_ok=True)
        frame.write_parquet(paths[label])

    panel = load_merged_panel(
        paths["b0_panel"],
        paths["b1_surface_panel"],
        paths["b2_flow_panel"],
    )
    development = panel.filter(pl.col("role") == "D").sort(
        ["session_date", "asset", "origin_minute"]
    )
    target = np.asarray(development["rv30"].to_numpy(), dtype=np.float64)
    keep = common_evaluation_mask(development, target)
    development = development.filter(pl.Series(keep))
    rank = session_rank(development["session_date"].to_numpy())
    train, _ = chronological_split(rank, train_share=0.6)
    fitted = fit_preprocessor(development, list(B2_FEATURES), train)
    design = transform_features(
        development,
        list(B2_FEATURES),
        fitted,
        intercept=False,
    )
    theta = np.linspace(0.01, 0.02, design.shape[1], dtype=np.float64)
    raw_index = design @ theta
    theta_payload: dict[str, object] = {
        "train_share": 0.6,
        "b2_design_columns": list(fitted.column_names(intercept=False)),
        "theta": theta.tolist(),
        "index_train_mean": float(raw_index[train].mean()),
        "index_train_std": float(raw_index[train].std()),
        "standardisation_epsilon": 1e-12,
        "input_parquet_sha256": {
            label: sut._sha256_file(path) for label, path in paths.items()
        },
    }
    theta_payload["self_sha256"] = sut._canonical_sha256(theta_payload)
    theta_path = tmp_path / "theta.json"
    _write_json(theta_path, theta_payload)
    return tmp_path, theta_path, panel, theta_payload


def test_freeze_round_trips_real_models_and_scores_only_future_rows(tmp_path: Path) -> None:
    panel_root, theta_path, panel, _theta = _panel_fixture(tmp_path / "panels")
    output = tmp_path / "frozen"

    manifest = sut.freeze(panel_root, theta_path, output)
    frozen = sut.load_frozen(output)
    future = panel.with_columns(pl.lit("2026-07-20").alias("session_date"))
    predictions = frozen.predict(future)

    assert manifest["training_rows"] == panel.height
    assert manifest["latest_training_session"] <= sut.TRAINING_WINDOW_END
    assert set(predictions) == {"index", sut.BASE_MODEL, sut.EXPANDED_MODEL}
    assert all(values.shape == (panel.height,) for values in predictions.values())
    assert np.isfinite(predictions["index"]).all()
    assert (predictions[sut.BASE_MODEL] > 0.0).all()
    assert (predictions[sut.EXPANDED_MODEL] > 0.0).all()


def test_frozen_preprocessor_round_trip_and_index_column_guard(tmp_path: Path) -> None:
    panel_root, theta_path, panel, _theta = _panel_fixture(tmp_path / "panels")
    output = tmp_path / "frozen"
    sut.freeze(panel_root, theta_path, output)
    frozen = sut.load_frozen(output)
    payload = sut._preprocessor_payload(frozen.model_preprocessor)

    assert sut._preprocessor_from_payload(payload) == frozen.model_preprocessor

    manifest = copy.deepcopy(frozen.manifest)
    index = manifest["index"]
    assert isinstance(index, dict)
    index["design_columns"] = []
    invalid = replace(frozen, manifest=manifest)
    with pytest.raises(ValueError, match="RP3_FROZEN_INDEX_COLUMNS_MISMATCH"):
        invalid.index_values(panel)


def test_freeze_rejects_window_theta_panel_and_index_reproduction_drift(tmp_path: Path) -> None:
    panel_root, theta_path, panel, theta = _panel_fixture(tmp_path / "valid")

    invalid_hash = dict(theta)
    invalid_hash["self_sha256"] = "0" * 64
    invalid_hash_path = tmp_path / "invalid-hash.json"
    _write_json(invalid_hash_path, invalid_hash)
    with pytest.raises(ValueError, match="RP3_FREEZE_THETA_HASH_MISMATCH"):
        sut.freeze(panel_root, invalid_hash_path, tmp_path / "invalid-hash-output")

    missing_root = tmp_path / "missing-panels"
    with pytest.raises(FileNotFoundError, match="RP3_FREEZE_PANEL_MISSING:b0_panel"):
        sut.freeze(missing_root, theta_path, tmp_path / "missing-output")

    panel_mismatch = dict(theta)
    hashes = dict(panel_mismatch["input_parquet_sha256"])
    hashes["b0_panel"] = "0" * 64
    panel_mismatch["input_parquet_sha256"] = hashes
    panel_mismatch["self_sha256"] = sut._canonical_sha256(panel_mismatch)
    mismatch_path = tmp_path / "panel-mismatch.json"
    _write_json(mismatch_path, panel_mismatch)
    with pytest.raises(ValueError, match="RP3_FREEZE_PANEL_MISMATCH:b0_panel"):
        sut.freeze(panel_root, mismatch_path, tmp_path / "mismatch-output")

    wrong_columns = dict(theta)
    wrong_columns["b2_design_columns"] = []
    target = np.asarray(panel["rv30"].to_numpy(), dtype=np.float64)
    with pytest.raises(ValueError, match="RP3_FREEZE_INDEX_COLUMNS_MISMATCH"):
        sut._reproduce_index_fold(panel, target, wrong_columns)

    wrong_statistics = dict(theta)
    wrong_statistics["index_train_mean"] = float(theta["index_train_mean"]) + 1.0
    with pytest.raises(ValueError, match="RP3_FREEZE_INDEX_REPRODUCTION_MISMATCH"):
        sut._reproduce_index_fold(panel, target, wrong_statistics)

    late_root, late_theta, _late_panel, _late_payload = _panel_fixture(
        tmp_path / "late",
        start="2026-07-20",
        end="2026-08-31",
    )
    with pytest.raises(ValueError, match="RP3_FREEZE_WINDOW_VIOLATION"):
        sut.freeze(late_root, late_theta, tmp_path / "late-output")


def test_freeze_rejects_round_trip_prediction_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    panel_root, theta_path, _panel, _theta = _panel_fixture(tmp_path / "panels")

    class Drifted:
        def predict(
            self,
            frame: pl.DataFrame,
            *,
            allow_training_window: bool,
        ) -> dict[str, np.ndarray]:
            assert allow_training_window is True
            return {
                sut.BASE_MODEL: np.zeros(frame.height),
                sut.EXPANDED_MODEL: np.zeros(frame.height),
            }

    monkeypatch.setattr(sut, "load_frozen", lambda _directory: Drifted())

    with pytest.raises(ValueError, match="RP3_FREEZE_ROUND_TRIP_DRIFT"):
        sut.freeze(panel_root, theta_path, tmp_path / "frozen")


def test_load_frozen_fails_closed_on_missing_or_tampered_bytes(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="RP3_FROZEN_MANIFEST_MISSING"):
        sut.load_frozen(tmp_path / "missing")

    panel_root, theta_path, _panel, _theta = _panel_fixture(tmp_path / "panels")
    output = tmp_path / "frozen"
    sut.freeze(panel_root, theta_path, output)

    manifest_path = output / sut.MANIFEST_NAME
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["training_rows"] += 1
    _write_json(manifest_path, manifest)
    with pytest.raises(ValueError, match="RP3_FROZEN_MANIFEST_HASH_MISMATCH"):
        sut.load_frozen(output)

    sut.freeze(panel_root, theta_path, output)
    model = output / sut._MODEL_FILES[sut.BASE_MODEL]
    model.write_text(model.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="RP3_FROZEN_MODEL_HASH_MISMATCH:b1"):
        sut.load_frozen(output)
