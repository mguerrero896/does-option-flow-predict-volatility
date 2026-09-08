"""Synthetic contracts for the mean-only v4 aggregator; no empirical data or fits."""

from __future__ import annotations

import copy
import json

import numpy as np
import pandas as pd
import pytest
from artifacts.rp4_v3_code import aggregate_v3 as v3
from artifacts.rp4_v3_code import inference as inf
from artifacts.rp4_v4_code import aggregate_v4 as agg

OPTIONS = {"bootstrap": {"replications": 99, "block_length": 5, "seed": 20260907}}


def synthetic_records(size: int = 24, *, horizon: int = 15, window: str = "primary") -> list[dict]:
    records = []
    for index, day in enumerate(pd.bdate_range("2025-01-02", periods=size).strftime("%Y-%m-%d")):
        target = np.array([1.0, 1.7, 0.8, 2.0, 1.2]) * 1e-5 * (1 + index / 50)
        forecasts = {}
        for family in inf.FAMILIES:
            scales = [1.8, 1.4, 1.1 if family == "log_ridge_harq" else 1.7]
            forecasts[family] = {
                name: (target * (scale + 0.07 * np.sin(index + k) + 0.01 * np.arange(5))).tolist()
                for k, (name, scale) in enumerate(zip(inf.SETS, scales, strict=True))
            }
        records.append(
            {
                "binding": {"window": window, "release": "SYNTHETIC"},
                "session": day,
                "target_key": f"rv_{horizon}",
                "horizon_minutes": horizon,
                "keys": [
                    {"asset": asset, "session_date": day, "origin_minute": minute}
                    for asset, minute in [
                        ("AAPL", 35),
                        ("AAPL", 60),
                        ("AAPL", 300),
                        ("MSFT", 35),
                        ("MSFT", 300),
                    ]
                ],
                "target": target.tolist(),
                "forecasts": forecasts,
                "fits": {
                    f"mean__{family}__{name}": {} for family in inf.FAMILIES for name in inf.SETS
                },
                "secondary": {
                    "first_hour": [True, False, False, True, False],
                    "high_flow": [True, True, True, None, None],
                    "event": [None] * 5,
                    "last_hour": [False, False, True, False, True],
                    "weekly_expiration": [index % 5 == 0] * 5,
                    "third_friday": [False] * 5,
                    "high_gamma": [True, False, False, True, False],
                    "window_empty_5m": [True, False, None, False, True],
                    "window_empty_30m": [False, False, False, True, False],
                },
            }
        )
    return records


@pytest.fixture(scope="module")
def completed() -> tuple:
    records = synthetic_records()
    summary, losses = agg.aggregate_records(records, OPTIONS)
    return records, summary, losses


def test_mean_only_never_invokes_full_aggregators_or_excluded_endpoints(monkeypatch) -> None:
    def forbidden(*args, **kwargs):
        raise AssertionError("Excluded endpoint or complete legacy aggregator invoked")

    for module in (agg.v1, v3.v2, v3):
        monkeypatch.setattr(module, "aggregate_records", forbidden)
    monkeypatch.setattr(agg.v1, "mincer_zarnowitz", forbidden)
    for name in ("_mz", "_jump", "_quantile"):
        monkeypatch.setattr(v3, name, forbidden)
    records = synthetic_records()
    original = copy.deepcopy(records)
    summary, losses = agg.aggregate_records(records, OPTIONS)
    assert records == original
    assert summary["endpoint_scope"] == ["mean"]
    assert len(losses) == 24
    assert all(name not in summary for name in summary["excluded_endpoint_diagnostics"])
    json.dumps(summary, allow_nan=False)


def test_legacy_comparability_primary_direction_and_session_weights(completed: tuple) -> None:
    records, summary, losses = completed
    frame = v3._frame(records)
    numeric = [c for c in frame if c.startswith(("loss__", "forecast__"))] + ["actual"]
    expected = (
        frame.groupby(["session_date", "asset"])[numeric].mean().groupby("session_date").mean()
    )
    pd.testing.assert_frame_equal(losses, expected.reset_index())
    first = records[0]
    ratio = np.asarray(first["target"]) / np.asarray(first["forecasts"][inf.FAMILIES[0]]["B0"])
    per_origin = ratio - np.log(ratio) - 1
    correct = np.mean([per_origin[:3].mean(), per_origin[3:].mean()])
    assert losses.iloc[0]["loss__log_ridge_harq__B0"] == pytest.approx(correct)
    assert not np.isclose(correct, per_origin.mean(), atol=1e-10)
    p_values = {}
    for row, primary in zip(summary["comparability_bilateral"], summary["contrasts"], strict=True):
        _, base, rich = next(c for c in inf.CONTRASTS if c[0] == row["contrast"])
        baseline = losses[f"loss__{row['family']}__{base}"].to_numpy()
        expanded = losses[f"loss__{row['family']}__{rich}"].to_numpy()
        exact = agg.v1.mean_inference(baseline - expanded, **v3._options(OPTIONS))
        assert all(row[k] == value for k, value in exact.items())
        assert (
            row["qlike_reduction_percent"]
            == 100 * (baseline.mean() - expanded.mean()) / baseline.mean()
        )
        p_values[f"{row['family']}__{row['contrast']}"] = row.get("p_raw", 1.0)
        expected_primary = inf.session_contrast(baseline - expanded, repetitions=99)
        assert all(
            primary[k] == expected_primary[k] for k in ("estimate", "ci_low", "ci_high", "p_raw")
        )
        assert primary["alternative"] == "greater" and "p_holm" not in primary
        assert primary["dm_hac_statistic"] == row["dm_hac_statistic"]
        assert primary["gw_hac_diagnostic_statistic"] == row["gw_hac_diagnostic_statistic"]
    adjusted = agg.v1.holm_adjust(p_values)
    for row in summary["comparability_bilateral"]:
        assert row["p_holm"] == adjusted[f"{row['family']}__{row['contrast']}"]


def test_predeclared_one_family_closure_separate_from_both_families(completed: tuple) -> None:
    _, summary, _ = completed
    closure = summary["predeclared_closure"]
    assert closure["applies"] and closure["satisfied"]
    assert closure["successful_families"] == ["log_ridge_harq"]
    assert closure["global_alpha_0_05_control_claimed"] is False
    assert summary["global_joint_reject"] is False
    assert summary["primary_sequence"]["global_joint_reject"] is False
    assert summary["global_joint_role"] == "ALL_FAMILIES_DIAGNOSTIC_NOT_V4_CLOSURE"


@pytest.mark.parametrize(
    "horizon,window", [(5, "primary"), (5, "confirmation"), (15, "confirmation")]
)
def test_other_windows_never_promote_registered_primary_closure(horizon: int, window: str) -> None:
    summary, _ = agg.aggregate_records(synthetic_records(horizon=horizon, window=window), OPTIONS)
    assert summary["predeclared_closure"]["status"] == "NOT_APPLICABLE"
    assert summary["predeclared_closure"]["satisfied"] is None
    assert summary["predeclared_closure"]["at_least_one_family_rejects"] is True
    expected_role = "PRIMARY" if horizon == 15 else "SECONDARY"
    assert summary["target_horizon_role"] == expected_role
    assert all(row["inference_role"] == expected_role for row in summary["contrasts"])


def test_h1_closed_blocks_h2_even_when_nominal_h2_favorable() -> None:
    records = synthetic_records()
    for index, record in enumerate(records):
        for family in inf.FAMILIES:
            target = np.asarray(record["target"])
            record["forecasts"][family]["B1"] = (target * (2.2 + 0.02 * np.sin(index))).tolist()
            record["forecasts"][family]["B2"] = (target * (1.1 + 0.01 * np.cos(index))).tolist()
    summary, _ = agg.aggregate_records(records, OPTIONS)
    for row in summary["contrasts"]:
        if row["contrast"] == "B2_over_B1":
            assert row["estimate"] > 0 and row["p_raw"] <= 0.05
            assert row["hypothesis_status"] == "NOT_TESTED"
            assert row["p_for_decision"] is None and row["rejected"] is False
    assert summary["predeclared_closure"]["satisfied"] is False


def test_distribution_posterior_regimes_census_and_extreme_signs(completed: tuple) -> None:
    records, summary, losses = completed
    frame = v3._frame(records)
    parameters = v3._options(OPTIONS)
    regimes = v3._regimes(frame, parameters)
    assert summary["regime_secondary"] == regimes
    assert summary["empty_window_secondary"] == v3._empty_windows(frame, regimes)
    assert summary["high_gamma_vs_rest"] == v3._high_vs_rest(frame, parameters)
    assert summary["distribution_secondary"] == v3._distribution(
        frame, parameters, endpoint="qlike_distribution_secondary", statistics=v3.STATISTICS[1:]
    )
    for row in summary["posterior_mean"]:
        _, base, rich = next(c for c in inf.CONTRASTS if c[0] == row["contrast"])
        delta = losses[f"loss__{row['family']}__{base}"] - losses[f"loss__{row['family']}__{rich}"]
        expected = inf.posterior_probability_mean(delta)
        assert all(row[key] == value for key, value in expected.items())
    event = next(r for r in summary["secondary"] if r["subset"] == "event")
    assert event["status"] == "NO VERIFICABLE" and event["N_unknown_membership_origins"] == 120
    assert len(summary["top_loss_sessions"]) == 60
    for row in summary["top_loss_sessions"]:
        source = losses.set_index("session_date").loc[row["session_date"]]
        for contrast, base, rich in inf.CONTRASTS:
            delta = (
                source[f"loss__{row['family']}__{base}"] - source[f"loss__{row['family']}__{rich}"]
            )
            assert row[contrast] == delta and row[contrast + "_sign"] == int(np.sign(delta))
    assert any(r["B2_over_B1_sign"] == -1 for r in summary["top_loss_sessions"])


def test_robustness_matches_independent_subset_means(completed: tuple) -> None:
    records, summary, losses = completed
    frame = v3._frame(records)
    dates = losses["session_date"].tolist()
    for row in summary["robustness"]:
        name = row["subset"]
        if name.startswith("asset_"):
            subset = frame[frame["asset"] == name.removeprefix("asset_")]
        elif name == "last30sessions":
            subset = frame[frame["session_date"].isin(dates[-30:])]
        else:
            index = int(name.split("_")[2]) - 1
            blocks = [dates[:8], dates[8:16], dates[16:]]
            member = frame["session_date"].isin(blocks[index])
            subset = frame[~member if name.startswith("leave_") else member]
        means = (
            subset.groupby(["session_date", "asset"])
            .mean(numeric_only=True)
            .groupby("session_date")
            .mean()
        )
        _, base, rich = next(c for c in inf.CONTRASTS if c[0] == row["contrast"])
        delta = means[f"loss__{row['family']}__{base}"] - means[f"loss__{row['family']}__{rich}"]
        assert row["estimate"] == delta.mean()
        assert row["N_origins"] == len(subset) and row["N_sessions"] == len(means)


@pytest.mark.parametrize(
    "change",
    [
        lambda r: r[0].update(target_key="rv30"),
        lambda r: r[1].update(horizon_minutes=5, target_key="rv_5"),
        lambda r: r[0].update(horizon_minutes=True),
        lambda r: r[0].pop("target_key"),
        lambda r: r[1]["binding"].update(window="confirmation"),
        lambda r: r[0]["binding"].update(target_key="rv30"),
        lambda r: r[0]["fits"].update({"jump__lightgbm_qlike__B0": {}}),
        lambda r: r[0]["target"].__setitem__(0, np.nan),
        lambda r: r[0]["keys"].append(r[0]["keys"][0]),
    ],
)
def test_invalid_or_mixed_inputs_fail_closed(change) -> None:
    records = synthetic_records()
    change(records)
    with pytest.raises(ValueError):
        agg.aggregate_records(records, OPTIONS)


def test_empty_and_insufficient_samples_do_not_create_confirmation() -> None:
    summary, losses = agg.aggregate_records([], OPTIONS)
    assert summary["status"] == "NO VERIFICABLE" and losses.empty
    summary, _ = agg.aggregate_records(synthetic_records(size=4), OPTIONS)
    assert all(r["p_for_decision"] is None for r in summary["contrasts"])
    assert summary["predeclared_closure"]["satisfied"] is False
