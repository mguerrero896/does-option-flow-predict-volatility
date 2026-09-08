"""Synthetic contracts for RP4 v2; never fit or score market data."""

from __future__ import annotations

import argparse
import copy
import json
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from artifacts.rp4_code import evaluate as v1
from artifacts.rp4_v2_code import evaluate_v2 as v2


def test_frozen_scope_and_original_inference_unchanged() -> None:
    path = v2.ROOT / "artifacts/rp4_v2_a1/specification.json"
    spec = v2.load_spec(path, v1.sha256(path))
    old = json.loads((v2.ROOT / "artifacts/rp4_a1/specification.json").read_text())
    assert [len(spec["feature_sets"][name]) for name in v1.SETS] == [29, 69, 132]
    assert spec["windows"] == old["windows"]
    assert spec["inference"] == old["inference"]
    assert not set(v2.REMOVED) & set(spec["feature_sets"]["B2"])
    with pytest.raises(ValueError, match="HASH_MISMATCH"):
        v2.load_spec(path, "wrong")


def test_adapter_preserves_every_v1_inference_number_and_tail_pairing() -> None:
    records = []
    for i in range(24):
        records.append(
            {
                "keys": [
                    {"asset": "A", "session_date": f"2026-01-{i + 1:02}", "origin_minute": 60}
                ],
                "target": [1.0 + i / 15],
                "forecasts": {
                    family: {"B0": [1.4], "B1": [1.5 + 0.01 * i], "B2": [1.7]}
                    for family in v2.FAMILIES
                },
                "secondary": {"first_hour": [True], "high_flow": [None], "event": [False]},
            }
        )
    original = copy.deepcopy(records)
    for record in original:
        record["forecasts"]["log_ols_harq"] = record["forecasts"].pop(v2.LINEAR)
    before, old_losses = v1.aggregate_records(original, {"bootstrap": {"replications": 99}})
    after, losses = v2.aggregate_records(records, {"bootstrap": {"replications": 99}})
    normalized = json.loads(json.dumps(after).replace("log_ridge_harq", "log_ols_harq"))
    for key in before:
        assert before[key] == normalized[key]
    pd.testing.assert_frame_equal(
        old_losses, losses.rename(columns=lambda c: c.replace(v2.LINEAR, "log_ols_harq"))
    )
    assert v2.LINEAR in records[0]["forecasts"]
    assert "log_ols_harq" not in records[0]["forecasts"]
    delta = (losses[f"loss__{v2.LINEAR}__B0"] - losses[f"loss__{v2.LINEAR}__B1"]).to_numpy()
    assert after["tail_secondary"][0]["median_paired_contrast"] == float(np.median(delta))
    assert after["tail_secondary"][0]["trimmed_mean_5pct_each_tail"] == float(
        np.sort(delta)[1:-1].mean()
    )
    assert len(after["top_loss_sessions"]) == 60
    empty, empty_losses = v2.aggregate_records([], {})
    assert empty["status"] == "NO VERIFICABLE" and empty_losses.empty


def test_only_mandatory_predictors_and_original_quality_restrict_mask() -> None:
    panel = pd.DataFrame(
        {
            "rv30": [1.0, 1.0, 1.0, 0.0],
            "mandatory": [1.0, np.nan, 1.0, 1.0],
            "optional": [np.nan, 1.0, np.inf, 1.0],
            "rp4_eligible": [True, True, False, True],
        }
    )
    mask, _, _, _ = v2.panel_masks(panel, {"mandatory_predictors": ["mandatory"]})
    np.testing.assert_array_equal(mask, [True, False, False, False])
    absent_quality, _, _, _ = v2.panel_masks(
        panel.drop(columns="rp4_eligible"), {"mandatory_predictors": ["mandatory"]}
    )
    np.testing.assert_array_equal(absent_quality, [True, False, True, False])


@pytest.mark.parametrize("shard_count", [1, 2])
def test_synthetic_pipeline_and_completed_sessions_never_refit(
    monkeypatch: pytest.MonkeyPatch,
    shard_count: int,
) -> None:
    # A task-specific temporary directory keeps synthetic outputs away from v1.
    with tempfile.TemporaryDirectory(prefix="rp4-v2-synthetic-", dir="private-input/acbcf2ed66faca1f9565") as temp:
        root = Path(temp)
        dates = pd.bdate_range("2024-08-02", periods=62).strftime("%Y-%m-%d")
        origins = pd.to_datetime(dates + "T14:30:00Z")
        frame = pd.DataFrame(
            {
                "asset": "A",
                "session_date": dates,
                "origin_minute": 60,
                "rv30": np.linspace(1, 2, 62),
                "base": np.linspace(1, 2, 62),
                "option": np.nan,
                "flow": np.nan,
                "rp4_eligible": True,
                "forecast_origin_utc": origins,
                "target_end_utc": origins + pd.Timedelta(minutes=30),
            }
        )
        panel = root / "materialized/panel.parquet"
        panel.parent.mkdir()
        frame.to_parquet(panel, index=False)
        manifest = panel.parent / "manifest.json"
        manifest.write_text('{"status":"SYNTHETIC"}', encoding="utf-8")
        spec = {
            "data_root": str(root),
            "assets": ["A", "B"],
            "windows": {"primary": {"start": dates[0], "end": dates[-1], "warmup_sessions": 60}},
            "model": {"lightgbm": {"num_threads": 4}, "ridge": {}, "tuning_sessions": 10},
            "embargo_minutes": 60,
            "mandatory_predictors": ["base"],
            "missing_allowed": ["option", "flow"],
            "feature_sets": {
                "B0": ["base"],
                "B1": ["base", "option"],
                "B2": ["base", "option", "flow"],
            },
            "feature_transforms": {},
            "inference": {"bootstrap": {"replications": 19}},
            "label": "SYNTHETIC",
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
                "execution": {"session_shards": shard_count, "threads_per_model": 4},
            },
        )
        calls = []

        def fake_fit(*args: object, **kwargs: object) -> tuple[np.ndarray, dict]:
            calls.append(1)
            return np.full(int(args[5].sum()), float(args[1][args[2]].mean())), {"synthetic": True}

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
            shard_count=shard_count,
            shard_index=None,
            aggregate_only=shard_count > 1,
        )
        if shard_count > 1:
            with pytest.raises(ValueError, match="AGGREGATION_MISSING_COMPLETED_SESSION"):
                v2.run(args)
            assert calls == []
            for shard_index in reversed(range(shard_count)):
                partial = argparse.Namespace(**vars(args))
                partial.shard_index, partial.aggregate_only = shard_index, False
                shard = v2.run(partial)
                assert shard["assigned_sessions"] == shard["completed_sessions"] == 1
                assert not (args.public_output / "summary.json").exists()
                assert v2.run(partial) == shard
            assert len(calls) == 12
        summary = v2.run(args)
        assert summary["N_sessions"] == 2
        assert len(calls) == 12
        assert v2.run(args) == summary
        assert len(calls) == 12
        losses = pd.read_csv(args.public_output / "session_losses.csv")
        assert list(losses["session_date"]) == list(dates[-2:])
        # Every shard trains on the entire past, not only its assigned sessions.
        first = json.loads((args.output / "sessions" / f"{dates[-2]}.json").read_text())
        last = json.loads((args.output / "sessions" / f"{dates[-1]}.json").read_text())
        assert first["train_sessions"] == 60 and last["train_sessions"] == 61
        frame.loc[0, "base"] = 99
        frame.to_parquet(panel, index=False)
        with pytest.raises(ValueError, match="PANEL_RELEASE_MISMATCH"):
            v2.run(args)


def test_checkpoint_requires_matching_bytes_receipt_keys_and_target(tmp_path: Path) -> None:
    expected = pd.DataFrame(
        {"asset": ["A"], "session_date": ["2026-08-03"], "origin_minute": [60], "rv30": [1.0]}
    )
    session, binding = "2026-08-03", {"test": "synthetic"}
    record = {
        "binding": binding,
        "session": session,
        "keys": expected[v2.KEYS].to_dict("records"),
        "target": [1.0],
        "forecasts": {"test": [1.1]},
    }
    v2.write_checkpoint(tmp_path, session, record)
    assert v2.read_checkpoint(tmp_path, session, binding, expected) == record
    with pytest.raises(ValueError, match="PANEL_PARITY_DRIFT"):
        v2.read_checkpoint(tmp_path, session, binding, expected.assign(rv30=2.0))
    checkpoint = tmp_path / "sessions" / f"{session}.json"
    checkpoint.write_text(checkpoint.read_text().replace("1.1", "1.2"))
    with pytest.raises(ValueError, match="HASH_OR_BINDING_DRIFT"):
        v2.read_checkpoint(tmp_path, session, binding, expected)
    (tmp_path / "session_receipts" / f"{session}.json").unlink()
    with pytest.raises(ValueError, match="WITHOUT_RECEIPT"):
        v2.read_checkpoint(tmp_path, session, binding, expected)


def test_recovered_origins_do_not_redefine_high_flow() -> None:
    dates = pd.bdate_range("2024-08-02", periods=61).strftime("%Y-%m-%d").to_numpy()
    origins = pd.to_datetime(dates + "T14:30:00Z").as_unit("ns").astype("int64").to_numpy()
    old_eligible = np.ones(61, dtype=bool)
    old_eligible[40:50] = False
    test = dates == dates[-1]
    frame = pd.DataFrame(
        {"asset": "A", "session_date": dates, "previous_day_b2_30m_premium": [*range(60), 36]}
    )
    membership, thresholds = v2.high_flow_membership(
        frame, old_eligible, dates, origins, origins + 30 * 60 * 10**9, dates[-1], test, 60
    )
    assert membership == [True]
    assert thresholds["A"] == pytest.approx(32.666666666666664)
    changed, _ = v2.high_flow_membership(
        frame,
        np.ones(61, dtype=bool),
        dates,
        origins,
        origins + 30 * 60 * 10**9,
        dates[-1],
        test,
        60,
    )
    assert changed == [False]
