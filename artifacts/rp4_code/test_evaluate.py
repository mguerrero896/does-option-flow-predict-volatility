"""Synthetic-only RP4 evaluator checks: no provider or market-target input."""

from __future__ import annotations

import argparse
import json
import os
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from evaluate import (
    aggregate_records,
    causal_masks,
    equal_session_asset_mean,
    fit_lightgbm,
    fit_ols,
    mean_inference,
    ols_design,
    run,
    transform_ols,
    write_json_once,
)


def test_causal_masks_and_target_mutation_do_not_change_prediction() -> None:
    generator = np.random.default_rng(650)
    dates = np.repeat(np.array([f"2026-01-{index:02}" for index in range(1, 22)]), 12)
    times = np.arange(len(dates), dtype=np.int64) * 120 * 60 * 1_000_000_000
    end = times + 30 * 60 * 1_000_000_000
    eligible = np.ones(len(dates), dtype=bool)
    train, inner_fit, inner_valid, test = causal_masks(
        dates,
        times,
        end,
        eligible,
        "2026-01-21",
        validation_sessions=10,
    )
    assert len(set(dates[inner_valid])) == 10
    assert np.max(end[train]) <= np.min(times[test]) - 60 * 60 * 1_000_000_000
    assert np.max(end[inner_fit]) <= np.min(times[inner_valid]) - 60 * 60 * 1_000_000_000
    design = generator.normal(size=(len(dates), 3))
    design[::7, 2] = np.nan
    target = np.exp(-8 + 0.3 * design[:, 0] + generator.normal(0, 0.1, len(dates)))
    before, _ = fit_ols(design, target, train, test, [2])
    changed = target.copy()
    changed[test] *= 1e9
    after, _ = fit_ols(design, changed, train, test, [2])
    np.testing.assert_array_equal(before, after)
    assert np.isfinite(before).all() and (before > 0).all()


def test_presence_encoding_has_no_fabricated_raw_value() -> None:
    training = np.array([[1.0, 8.0], [2.0, np.nan], [3.0, 10.0]])
    predicting = np.array([[4.0, np.nan], [4.0, 9.0]])
    fitted, encoded = ols_design(training, predicting, [1])
    assert fitted.shape == (3, 4)
    assert encoded[0, 2] == 0
    assert encoded[0, 3] == 0
    assert encoded[1, 2] == 0
    assert encoded[1, 3] == 1
    np.testing.assert_array_equal(predicting[:, 1], np.array([np.nan, 9.0]))


def test_session_asset_weights_and_signed_inference() -> None:
    values = np.array([0.0, 0.0, 0.0, 4.0, 10.0])
    assert equal_session_asset_mean(values, [1, 1, 1, 1, 2], ["A", "A", "A", "B", "A"]) == 6
    difference = np.array([1.0, 2.0, -0.1, 1.2, 0.5, -0.1, 1.3, 2.1, 0.2, 0.4])
    positive = mean_inference(difference, repetitions=999, block_length=3, seed=650)
    negative = mean_inference(-difference, repetitions=999, block_length=3, seed=650)
    assert positive["estimate"] == -negative["estimate"]
    assert positive["p_raw"] == negative["p_raw"]
    assert positive["ci_low"] == pytest.approx(-negative["ci_high"])
    assert 0 < positive["p_raw"] <= 1


def test_lightgbm_selection_is_training_only() -> None:
    generator = np.random.default_rng(6)
    dates = np.repeat(np.arange(16), 20)
    design = generator.normal(size=(320, 4))
    design[::3, 2] = np.nan
    target = np.exp(-8 + 0.3 * design[:, 0] + generator.normal(0, 0.1, 320))
    train, inner_fit, inner_valid, test = (
        dates < 15,
        dates < 5,
        (dates >= 5) & (dates < 15),
        dates == 15,
    )
    assets = np.repeat("A", 320)
    options = {"num_boost_round": [2, 4], "num_leaves": [3, 5], "min_data_in_leaf": 8}
    original, record = fit_lightgbm(
        design,
        target,
        train,
        inner_fit,
        inner_valid,
        test,
        dates,
        assets,
        options,
        threads=1,
    )
    changed = target.copy()
    changed[test] *= 1000
    later, later_record = fit_lightgbm(
        design,
        changed,
        train,
        inner_fit,
        inner_valid,
        test,
        dates,
        assets,
        options,
        threads=1,
    )
    np.testing.assert_array_equal(original, later)
    assert record == later_record
    assert record["init_score"] == pytest.approx(np.log(target[train].mean()))
    assert np.isfinite(original).all() and (original > 0).all()


def test_atomic_checkpoint_refuses_mutation(tmp_path: Path) -> None:
    destination = tmp_path / "session.json"
    write_json_once(destination, {"immutable": True})
    write_json_once(destination, {"immutable": True})
    with pytest.raises(ValueError, match="IMMUTABLE_OUTPUT_MISMATCH"):
        write_json_once(destination, {"immutable": False})
    assert json.loads(destination.read_text()) == {"immutable": True}


def test_paired_four_contrasts_and_secondary_empty() -> None:
    records = []
    for index in range(12):
        records.append(
            {
                "keys": [
                    {"asset": "A", "session_date": f"2026-01-{index + 1:02}", "origin_minute": 600}
                ],
                "target": [1.0 + index / 20],
                "forecasts": {
                    family: {"B0": [2.0], "B1": [1.8], "B2": [1.6]}
                    for family in ("log_ols_harq", "lightgbm_qlike")
                },
                "secondary": {"first_hour": [False], "high_flow": [None], "event": [False]},
            }
        )
    summary, means = aggregate_records(records, {"bootstrap": {"replications": 99}})
    assert len(summary["contrasts"]) == 4
    assert len(means) == 12
    assert all(row["p_holm"] >= row["p_raw"] for row in summary["contrasts"])
    assert summary["capital_go"] is False
    assert all(row["status"] == "NO VERIFICABLE" for row in summary["secondary"])
    for index, record in enumerate(records):
        record["secondary"]["high_flow"] = [True if index < 3 else False if index < 7 else None]
    partial, _ = aggregate_records(records, {"bootstrap": {"replications": 99}})
    assert partial["contrasts"] == summary["contrasts"]
    high_flow = [row for row in partial["secondary"] if row["subset"] == "high_flow"]
    assert len(high_flow) == 4
    for row in high_flow:
        assert row["status"] == "PARTIAL_COVERAGE"
        assert row["N_origins"] == 3
        assert row["N_verified_membership_origins"] == 7
        assert row["N_unknown_membership_origins"] == 5
        assert row["N_verified_nonmember_origins"] == 4
        assert row["N_excluded_from_subset_origins"] == 9


def test_frozen_transforms_preserve_missing_and_sign() -> None:
    original = np.array([[0.0, -2.0, 3.0], [np.nan, 2.0, 4.0]])
    transformed = transform_ols(original, ["a", "b", "c"], {"a": "log", "b": "signed"})
    assert transformed[0, 0] == np.log(1e-12)
    assert transformed[0, 1] == -np.log1p(2)
    assert transformed[1, 1] == np.log1p(2)
    assert np.isnan(transformed[1, 0])
    np.testing.assert_array_equal(original[:, 2], transformed[:, 2])
    assert original[0, 0] == 0


def test_small_or_degenerate_samples_cannot_manufacture_pvalues() -> None:
    for values in (np.arange(9, dtype=float), np.ones(12)):
        result = mean_inference(values, repetitions=99, block_length=5, seed=650)
        assert result["status"] == "NO VERIFICABLE"
        assert "p_raw" not in result
        assert "ci_low" not in result


@pytest.mark.parametrize(
    "skip_reason",
    [None, "RP4_INSUFFICIENT_TRAINING_SESSIONS", "RP4_INNER_TRAINING_EMPTY_AFTER_EMBARGO"],
)
def test_synthetic_end_to_end_and_resume_without_refitting(
    monkeypatch: pytest.MonkeyPatch,
    skip_reason: str | None,
) -> None:
    parent = (
        Path("private-input/66c0e77362caa29dd928") if os.name == "nt" else Path(tempfile.gettempdir())
    )
    parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="rp4-synthetic-check-", dir=parent) as temporary:
        directory = Path(temporary)
        random = np.random.default_rng(650)
        day_count = 62
        row_count = day_count * 4
        days = pd.date_range("2024-08-02", periods=day_count, freq="B")
        dates = np.repeat(days.strftime("%Y-%m-%d"), 4)
        origins = pd.to_datetime(dates + "T14:00:00Z") + pd.to_timedelta(
            np.tile([0, 5, 10, 15], day_count), unit="min"
        )
        frame = pd.DataFrame(
            {
                "asset": "A",
                "session_date": dates,
                "origin_minute": np.tile([30, 35, 40, 45], day_count),
                "forecast_origin_utc": origins,
                "target_end_utc": origins + pd.Timedelta(minutes=30),
                "rv30": np.exp(-8 + random.normal(0, 0.1, row_count)),
                "a": random.normal(size=row_count),
                "b": random.normal(size=row_count),
                "grid": np.where(
                    np.arange(row_count) % 3, random.uniform(0.1, 0.5, row_count), np.nan
                ),
                "previous_day_b2_30m_premium": random.uniform(1, 10, row_count),
                "is_event": False,
            }
        )
        panel = directory / "synthetic.parquet"
        frame.to_parquet(panel)
        specification = {
            "data_root": str(directory),
            "assets": ["A", "B"],
            "label": "SYNTHETIC_ONLY",
            "feature_sets": {"B0": ["a"], "B1": ["a", "grid"], "B2": ["a", "grid", "b"]},
            "feature_transforms": {"a": "raw", "b": "signed", "grid": "log"},
            "missing_allowed": ["grid"],
            "embargo_minutes": 60,
            "windows": {"primary": {"start": dates[0], "end": dates[-1], "warmup_sessions": 60}},
            "model": {
                "tuning_sessions": 10,
                "lightgbm": {
                    "num_threads": 1,
                    "num_boost_round": [2, 4],
                    "num_leaves": [3],
                    "min_data_in_leaf": 8,
                },
            },
            "inference": {"bootstrap": {"replications": 99}},
        }
        monkeypatch.setattr("evaluate.load_spec", lambda *_: specification)
        first_scoring_session = str(days[60].date())

        def causal_or_skip(*args: object, **kwargs: object) -> object:
            if skip_reason and args[4] == first_scoring_session:
                raise ValueError(skip_reason)
            return causal_masks(*args, **kwargs)

        monkeypatch.setattr("evaluate.causal_masks", causal_or_skip)
        arguments = argparse.Namespace(
            panel=panel,
            spec=directory / "synthetic-spec.json",
            spec_sha256="synthetic",
            window="primary",
            output=directory / "private",
            public_output=directory / "aggregate",
            threads=1,
        )
        first = run(arguments)
        expected_sessions = 1 if skip_reason else 2
        assert first["N_sessions"] == expected_sessions
        assert first["N_origins"] == expected_sessions * 4
        assert first["scheduled_sessions"] == 2
        assert first["skipped_sessions"] == (
            [{"session": first_scoring_session, "reason": skip_reason}] if skip_reason else []
        )
        assert len(first["contrasts"]) == 4
        assert all(row["status"] == "NO VERIFICABLE" for row in first["contrasts"])

        def forbidden_refit(*_args: object, **_kwargs: object) -> None:
            raise AssertionError("completed session was refitted")

        monkeypatch.setattr("evaluate.fit_ols", forbidden_refit)
        monkeypatch.setattr("evaluate.fit_lightgbm", forbidden_refit)
        assert run(arguments) == first
