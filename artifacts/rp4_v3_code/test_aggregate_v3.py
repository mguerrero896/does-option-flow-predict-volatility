"""Synthetic aggregation/report contracts; no empirical panels, training, or provider reads."""

from __future__ import annotations

import argparse
import copy
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from artifacts.rp4_v2_code import evaluate_v2 as v2
from artifacts.rp4_v3_code import aggregate_v3 as agg
from artifacts.rp4_v3_code import inference as inf
from artifacts.rp4_v3_code import report_v3 as report

OPTIONS = {"bootstrap": {"replications": 99, "block_length": 5, "seed": 20260907}}


def synthetic_records(size: int = 24) -> list[dict]:
    records = []
    for i, day in enumerate(pd.bdate_range("2025-01-02", periods=size).strftime("%Y-%m-%d")):
        target = np.array([1.0, 1.7, 0.8, 2.0, 1.2]) * (1 + i / 50)
        forecasts = {
            family: {
                name: (target * (1.0 + scale + 0.1 * np.sin(i + k))).tolist()
                for k, (name, scale) in enumerate(zip(inf.SETS, [0.6, 0.3, 0.35], strict=True))
            }
            for family in inf.FAMILIES
        }
        records.append(
            {
                "session": day,
                "keys": [
                    {"asset": asset, "session_date": day, "origin_minute": minute}
                    for asset, minute in [("A", 0), ("A", 60), ("A", 300), ("B", 0), ("B", 300)]
                ],
                "target": target.tolist(),
                "forecasts": forecasts,
                "fits": {},
                "secondary": {
                    "first_hour": [True, False, False, True, False],
                    "high_flow": [True, True, True, None, None],
                    "event": [None] * 5,
                    "last_hour": [False, False, True, False, True],
                    "weekly_expiration": [i % 5 == 0] * 5,
                    "third_friday": [False] * 5,
                    "high_gamma": [True, False, False, True, False],
                },
                "mz_forecasts": {
                    name: (np.asarray(forecasts["lightgbm_qlike"][name]) * 0.95).tolist()
                    for name in inf.SETS
                },
                "tail_forecasts": {
                    "quantile": {
                        family: {
                            name: (np.log(target) + 0.15 + k * 0.02 + 0.01 * i).tolist()
                            for k, name in enumerate(inf.SETS)
                        }
                        for family in inf.FAMILIES
                    },
                    "jump": {
                        family: {
                            name: [0.2, 0.8 - k * 0.03, 0.3 + 0.1 * (i % 3), 0.6, 0.8]
                            for k, name in enumerate(inf.SETS)
                        }
                        for family in inf.FAMILIES
                    },
                },
                "jump_positions": [0, 1, 2, 3, 4],
                "jump_target": [0, 1, 0, 1, i % 2],
                "tail_status": {name: {"status": "COMPUTED"} for name in ("quantile", "jump")},
            }
        )
    return records


@pytest.fixture(scope="module")
def completed() -> tuple[list[dict], dict, pd.DataFrame]:
    records = synthetic_records()
    summary, losses = agg.aggregate_records(records, OPTIONS)
    return records, summary, losses


def test_v2_arithmetic_unchanged_and_primary_separate(completed: tuple) -> None:
    records, summary, losses = completed
    original = copy.deepcopy(records)
    old, old_losses = v2.aggregate_records(records, OPTIONS)
    assert records == original
    assert summary["comparability_bilateral"] == old["contrasts"]
    for key in (
        "mincer_zarnowitz",
        "robustness",
        "top_loss_sessions",
        "tail_secondary",
        "secondary",
    ):
        assert summary[key] == old[key]
    pd.testing.assert_frame_equal(losses, old_losses)
    for item in summary["contrasts"]:
        _, base, rich = next(c for c in inf.CONTRASTS if c[0] == item["contrast"])
        delta = (
            losses[f"loss__{item['family']}__{base}"] - losses[f"loss__{item['family']}__{rich}"]
        )
        expected = inf.session_contrast(delta, repetitions=99)
        for key in ("estimate", "ci_low", "ci_high", "p_raw", "status"):
            assert item[key] == expected[key]
        assert item["alternative"] == "greater" and "p_holm" not in item
    assert summary["global_joint_reject"] == summary["primary_sequence"]["global_joint_reject"]
    assert summary["secondary_can_rescue_primary"] is False
    json.dumps(summary, allow_nan=False)


def test_equal_asset_then_session_weights_and_paired_distribution(completed: tuple) -> None:
    records, summary, losses = completed
    frame = agg._frame(records)
    name = "loss__lightgbm_qlike__B0"
    expected = frame.groupby(["session_date", "asset"])[name].mean().groupby("session_date").mean()
    np.testing.assert_array_equal(losses[name], expected)
    assert len(summary["distribution_secondary"]) == 8
    for statistic in ("median", "trimmed_mean_5pct"):
        rows = [r for r in summary["distribution_secondary"] if r["statistic"] == statistic]
        assert len(rows) == 4 and all(r["holm_family_size"] == 4 for r in rows)
        for row in rows:
            _, base, rich = next(c for c in inf.CONTRASTS if c[0] == row["contrast"])
            delta = (
                losses[f"loss__{row['family']}__{base}"] - losses[f"loss__{row['family']}__{rich}"]
            )
            expected = inf.session_contrast(
                delta, statistic=statistic, alternative="two-sided", repetitions=99
            )
            for key in ("estimate", "ci_low", "ci_high", "p_raw", "removed_each_tail"):
                assert row[key] == expected[key]


def test_unknown_strata_are_not_false_zero_and_interaction_is_paired(completed: tuple) -> None:
    records, summary, _ = completed
    events = [r for r in summary["regime_secondary"] if r["subset"] == "event"]
    assert len(events) == 12
    assert all(r["N_unknown_membership_origins"] == 120 for r in events)
    assert all(r["N_origins"] == 0 and r["estimate"] is None for r in events)
    flow = [r for r in summary["regime_secondary"] if r["subset"] == "high_flow"]
    assert all(r["N_unknown_membership_origins"] == 48 and r["N_origins"] == 72 for r in flow)
    high = summary["high_gamma_vs_rest"]
    assert all(r["N_asset_sessions"] == 48 and r["N_sessions"] == 24 for r in high)
    # Both models' pointwise proportional errors are identical within each day:
    # interaction must be zero to floating-point error, not an unpaired date difference.
    assert all(abs(r["estimate"]) < 1e-14 for r in high)
    mutated = copy.deepcopy(records)
    mutated[0]["secondary"]["high_gamma"] = [True] * 5
    interaction = agg._high_vs_rest(agg._frame(mutated), agg._options(OPTIONS))
    assert all(r["N_asset_sessions"] == 46 and r["N_sessions"] == 23 for r in interaction)


def test_secondary_endpoint_failure_never_drops_primary_session(completed: tuple) -> None:
    records, baseline, losses = completed
    changed = copy.deepcopy(records)
    changed[3]["tail_status"]["quantile"] = {
        "status": "NO VERIFICABLE",
        "reason": "synthetic solver failure",
    }
    changed[4]["tail_status"]["jump"] = {
        "status": "NO VERIFICABLE",
        "reason": "synthetic class fit failure",
    }
    result, current = agg.aggregate_records(changed, OPTIONS)
    pd.testing.assert_frame_equal(current, losses)
    assert result["contrasts"] == baseline["contrasts"]
    assert result["quantile_secondary"]["N_sessions"] == 23
    assert result["jump_secondary"]["N_sessions"] == 23
    assert result["quantile_secondary"]["excluded_sessions"][0]["session"] == changed[3]["session"]
    assert all(r["N_sessions"] == 23 for r in result["jump_secondary"]["contrasts"])


def test_pinball_auc_and_mz_are_separate_units(completed: tuple) -> None:
    records, summary, _ = completed
    assert summary["quantile_secondary"]["tau"] == 0.9
    assert summary["quantile_secondary"]["sequence"]["scope"] == "SECONDARY_ENDPOINT_JOINT"
    frame, _ = agg._endpoint_frames(records, "jump")
    first = summary["jump_secondary"]["families"][0]
    expected = inf.pooled_auc_inference(
        frame["actual"],
        {s: frame[f"forecast__{inf.FAMILIES[0]}__{s}"] for s in inf.SETS},
        frame["session_date"],
        family=inf.FAMILIES[0],
        repetitions=99,
    )
    assert first == expected
    assert summary["mz_secondary"]["primary_predictions_replaced"] is False
    assert {r["information_set"] for r in summary["mz_secondary"]["model_losses"]} == set(inf.SETS)
    assert all(r["inference_role"] == "SECONDARY" for r in summary["mz_secondary"]["contrasts"])
    for row in summary["mz_secondary"]["model_losses"]:
        assert row["N_sessions"] == 24 and row["N_origins"] == 120
        assert row["calibration_reduction_percent"] == pytest.approx(
            100 * (row["raw_qlike"] - row["recalibrated_qlike"]) / row["raw_qlike"]
        )


@pytest.mark.parametrize(
    "mutation,match",
    [
        (lambda r: r.reverse(), "SESSION_ORDER"),
        (lambda r: r[0]["keys"].__setitem__(1, r[0]["keys"][0]), "KEY_DATE_OR_DUPLICATE"),
        (
            lambda r: r[0]["forecasts"][inf.FAMILIES[0]]["B1"].__setitem__(0, float("nan")),
            "NONFINITE_OR_MISALIGNED",
        ),
        (lambda r: r[0]["secondary"]["high_gamma"].__setitem__(0, 1), "MEMBERSHIP_CONTRACT"),
        (lambda r: r[0].__setitem__("jump_positions", [0, 2, 1, 3, 4]), "JUMP_POSITION_ALIGNMENT"),
        (
            lambda r: r[0]["tail_forecasts"]["quantile"][inf.FAMILIES[0]].pop("B2"),
            "TAIL_COMMON_MASK",
        ),
    ],
)
def test_bad_records_fail_closed(mutation: object, match: str) -> None:
    records = synthetic_records(12)
    mutation(records)
    with pytest.raises(ValueError, match=match):
        agg.aggregate_records(records, OPTIONS)


def test_empty_tail_samples_remain_unavailable(completed: tuple) -> None:
    records, _, _ = completed
    changed = copy.deepcopy(records)
    for record in changed:
        record["tail_status"] = {}
    result, _ = agg.aggregate_records(changed, OPTIONS)
    assert result["N_sessions"] == 24
    for endpoint in ("jump_secondary", "quantile_secondary"):
        assert result[endpoint]["status"] == "NO VERIFICABLE"
        assert len(result[endpoint]["excluded_sessions"]) == 24
        assert not result[endpoint]["sequence"]["global_joint_reject"]
    empty, loss = agg.aggregate_records([], OPTIONS)
    assert empty["status"] == "NO VERIFICABLE" and loss.empty


def test_empty_window_census_keeps_unknown_and_nonempty_distinct() -> None:
    records = synthetic_records(12)
    for record in records:
        record["secondary"]["window_empty_5m"] = [True, False, None, True, False]
        record["secondary"]["window_empty_30m"] = [False, False, False, None, None]
    summary, _ = agg.aggregate_records(records, OPTIONS)
    census = summary["empty_window_secondary"]["census"]
    assert sum(r["N_empty_origins"] for r in census if r["horizon"] == "5m") == 24
    assert sum(r["N_nonempty_origins"] for r in census if r["horizon"] == "5m") == 24
    assert sum(r["N_unknown_origins"] for r in census if r["horizon"] == "5m") == 12
    inside = [
        r
        for r in summary["empty_window_secondary"]["contrasts"]
        if r["subset"] == "window_empty_5m"
    ]
    outside = [
        r
        for r in summary["empty_window_secondary"]["contrasts"]
        if r["subset"] == "window_nonempty_5m"
    ]
    assert all(r["N_origins"] == 24 for r in inside + outside)
    assert all(r["contrast"] == "B2_over_B1" for r in inside + outside)


def test_quantile_record_scale_is_already_logarithmic() -> None:
    records = synthetic_records(12)
    for record in records:
        actual = np.asarray(record["target"])
        # Runtime stores log of a LEVEL quantile exactly once.
        for family in inf.FAMILIES:
            record["tail_forecasts"]["quantile"][family] = {
                name: np.log(actual * factor).tolist()
                for name, factor in zip(inf.SETS, (2.0, 3.0, 4.0), strict=True)
            }
    result = agg._quantile(records, agg._options(OPTIONS))
    for row in result["model_losses"]:
        factor = {"B0": 2.0, "B1": 3.0, "B2": 4.0}[row["information_set"]]
        assert row["mean_pinball"] == pytest.approx(0.1 * np.log(factor))


def _report_windows(completed: tuple) -> dict:
    records, summary, losses = completed
    old, old_losses = v2.aggregate_records(records, OPTIONS)
    windows = {version: {} for version in report.VERSIONS}
    for version in report.VERSIONS:
        for window in report.WINDOWS:
            current = copy.deepcopy(summary if version == "v3" else old)
            rows = (losses if version == "v3" else old_losses).to_dict("records")
            if version == "v1":
                current = json.loads(json.dumps(current).replace("log_ridge_harq", "log_ols_harq"))
                rows = json.loads(json.dumps(rows).replace("log_ridge_harq", "log_ols_harq"))
            current.update(
                {
                    "window": window,
                    "binding": {"specification_sha256": version},
                    "completed_session_sha256": {
                        r["session_date"] + ".json": "synthetic" for r in rows
                    },
                    "scheduled_sessions": len(rows),
                    "skipped_sessions": [],
                    "result_label": "SYNTHETIC ONLY",
                    "quality_gate_column_present": False,
                    "evaluation_quality_by_asset": [
                        {
                            "asset": asset,
                            "scheduled_rows": n,
                            "eligible_rows": n,
                            "invalid_target": 0,
                            "incomplete_mandatory_predictors": 0,
                            "failed_quality_gate": 0,
                        }
                        for asset, n in (("A", 72), ("B", 48))
                    ],
                }
            )
            windows[version][window] = (current, rows)
    return windows


def test_report_validates_numbers_sequence_and_displays_all_signs(completed: tuple) -> None:
    windows = _report_windows(completed)
    for version in report.VERSIONS:
        for window in report.WINDOWS:
            summary, rows = windows[version][window]
            report.validate_window(summary, rows, version, window, version)
    output = report.render_report(
        windows, {"label": "SYNTHETIC ONLY", "assets": ["A", "B"]}, [], [], {}
    )
    assert "NOT SATISFIED IN THIS WINDOW" in output
    assert "nominal one-sided p" in output and "two-sided p" in output
    assert "diagnostic that cannot be promoted to primary evidence" in output
    assert "window_nonempty_5m" in output and "UNVERIFIABLE" in output
    assert "does not integrate variance uncertainty" in output
    assert "b2_5m_observed_span_s" in output and "capital_go=false" in output
    assert "Recalibrated" in output and "The median of differences" in output
    assert "The optional gate column rp4_eligible is absent" in output
    changed = copy.deepcopy(windows["v3"]["primary"][0])
    changed["contrasts"][0]["estimate"] += 1
    with pytest.raises(ValueError, match="ESTIMATE_MISMATCH"):
        report.validate_window(changed, windows["v3"]["primary"][1], "v3", "primary", "v3")
    changed = copy.deepcopy(windows["v3"]["primary"][0])
    changed["primary_sequence"]["global_joint_reject"] = True
    with pytest.raises(ValueError, match="SEQUENCE_DRIFT"):
        report.validate_window(changed, windows["v3"]["primary"][1], "v3", "primary", "v3")


def test_two_svg_figures_preserve_all_twenty_four_endpoints(completed: tuple) -> None:
    windows = _report_windows(completed)
    endpoints = 0
    for contrast, base, richer in inf.CONTRASTS:
        svg = ET.fromstring(report.cumulative_figure(windows, contrast, base, richer))
        paths = svg.findall(".//{http://www.w3.org/2000/svg}path")
        assert len(paths) == 12
        for path in paths:
            version, window, family = (
                path.attrib[f"data-{k}"] for k in ("version", "window", "family")
            )
            rows = windows[version][window][1]
            expected = sum(report.differences(rows, family, base, richer))
            assert float(path.attrib["data-endpoint"]) == pytest.approx(expected, abs=1e-14)
            assert int(path.attrib["data-sessions"]) == len(rows)
            assert path.attrib["d"].count("L") == len(rows)
            endpoints += 1
    assert endpoints == 24


def test_report_requires_real_successful_receipts_and_pins(tmp_path: Path) -> None:
    root, private = tmp_path / "repo", tmp_path / "private"
    root.mkdir()
    private.mkdir()
    summary, loss, diagnostics = (
        root / "summary.json",
        root / "session_losses.csv",
        private / "fit_diagnostics.json",
    )
    for path in (summary, loss, diagnostics):
        path.write_text("synthetic", encoding="utf-8")
    log = private / "command.log"
    log.write_text("synthetic exit evidence", encoding="utf-8")
    value = {
        "status": "COMPLETE",
        "exit_code": 0,
        "stage": "B2",
        "window": "primary",
        "execution_failure": None,
        "artifacts_sha256": {str(p): report.sha256(p) for p in (summary, loss, diagnostics)},
        "commands": [
            {
                "command": "synthetic-only",
                "exit_code": 0,
                "log": str(log),
                "log_sha256": report.sha256(log),
            }
        ],
    }
    receipt = root / "receipt.json"
    receipt.write_text(json.dumps(value), encoding="utf-8")
    kwargs = {
        "root": root,
        "private_root": private,
        "stage": "B2",
        "window": "primary",
        "required": [summary, loss, diagnostics],
    }
    assert report.validate_receipt(receipt, **kwargs) == value
    value["commands"][0]["exit_code"] = 1
    receipt.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="COMMAND_EXIT_NOT_ZERO"):
        report.validate_receipt(receipt, **kwargs)
    value["commands"][0]["exit_code"] = 0
    receipt.write_text(json.dumps(value), encoding="utf-8")
    summary.write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="ARTIFACT_HASH_DRIFT"):
        report.validate_receipt(receipt, **kwargs)


def test_report_fit_diagnostics_keep_endpoints_and_train_only_mz() -> None:
    day = "2025-01-02"
    previous = pd.bdate_range("2024-12-10", periods=10).strftime("%Y-%m-%d").tolist()
    records = []
    for endpoint in ("mean", "quantile", "jump"):
        for family in inf.FAMILIES:
            for name in inf.SETS:
                row = {
                    "session": day,
                    "model": f"{endpoint}__{family}__{name}",
                    "endpoint": endpoint,
                    "inner_valid_sessions": previous,
                    "selected": {"lambda": 1}
                    if family == "log_ridge_harq"
                    else {"rounds": 400, "num_leaves": 31},
                }
                if endpoint == "mean" and family == "lightgbm_qlike":
                    row["mz_secondary"] = {
                        "calibration": {
                            "calibration_sessions": previous,
                            "inner_fit_last_session": "2024-12-09",
                            "applied_coefficients": {"intercept": 0.1, "slope": 1.4},
                            "N_sessions": 10,
                            "training_identity_fallback": False,
                            "training_fallback_reason": None,
                            "origin_identity_fallback_count": 0,
                            "count_floor": 1,
                            "prediction_rows": 5,
                        }
                    }
                records.append(row)
    records[0].update(
        {
            "selected": {"lambda": 1.0, "count_low": 2, "count_high": 1, "prediction_rows": 20},
            "count_low": 1,
            "count_high": 2,
            "prediction_rows": 10,
            "train_rows": 100,
            "inner_fit_rows": 70,
            "inner_valid_rows": 20,
            "bounds": {
                "inner_fit": {
                    "percentile_1": 2.0,
                    "percentile_99": 6.0,
                    "lower": 1.0,
                    "upper": 12.0,
                },
                "refit": {"percentile_1": 3.0, "percentile_99": 7.0, "lower": 1.5, "upper": 14.0},
            },
            "preprocessing": {
                phase: {
                    "active_columns": ["intercept", "feature:0"],
                    "removed_columns": [],
                    "winsorization": {
                        "standard_deviation_limit": 5.0,
                        "training": [{"column": "feature:0", "count_low": 2, "count_high": 1}],
                        "predicting": [{"column": "feature:0", "count_low": 1, "count_high": 0}],
                    },
                }
                for phase in ("inner_fit", "refit")
            },
        }
    )
    selected, calibration = report.fit_diagnostics(records, [day], "primary")
    assert len(selected) == 18 and len(calibration) == 3
    assert set(r["endpoint"] for r in selected) == {"mean", "quantile", "jump"}
    assert all(r["slope"] == 1.4 and r["count_floor"] == 1 for r in calibration)
    assert all("coefficients" not in r and "forecast" not in r for r in selected)
    first = next(r for r in selected if r["model"] == "mean__log_ridge_harq__B0")
    assert first["inner_percentile_1"] == 2.0 and first["percentile_99"] == 7.0
    assert first["validation_prediction_rows"] == 20 and first["prediction_rows"] == 10
    bounds = [
        r
        for r in report.bound_summary(selected)
        if (r["window"], r["endpoint"], r["family"], r["information_set"])
        == ("primary", "mean", "log_ridge_harq", "B0")
    ]
    assert [(r["phase"], r["percent_low"], r["percent_high"]) for r in bounds] == [
        ("validation", 10.0, 5.0),
        ("evaluation", 10.0, 20.0),
    ]
    missing = [r for r in report.bound_summary(selected) if r["family"] == "lightgbm_qlike"]
    assert all(r["count_low"] is None and r["status"] == "NO VERIFICABLE" for r in missing)
    winsor = report.winsor_diagnostics([records[0], records[0]], "primary")
    assert len(winsor) == 4 and all(r["N_fit_records"] == 2 for r in winsor)
    assert all(r["count_low"] == 4 for r in winsor if r["partition"] == "training")
    corrupted = copy.deepcopy(selected)
    corrupted[0]["count_low"] = -1
    with pytest.raises(ValueError, match="BOUND_HITS"):
        report.bound_summary(corrupted)
    records[0]["inner_valid_sessions"][-1] = day
    with pytest.raises(ValueError, match="NONCAUSAL_TUNING"):
        report.fit_diagnostics(records, [day], "primary")


def test_report_checks_unchanged_lgb_columns_by_session(completed: tuple) -> None:
    windows = _report_windows(completed)
    rows = report.unchanged_lgb_parity(windows)
    assert len(rows) == 8 and all(
        r["exact"] and r["maximum_absolute_difference"] == 0 for r in rows
    )
    windows["v3"]["confirmation"][1][0]["forecast__lightgbm_qlike__B0"] += 1e-10
    with pytest.raises(ValueError, match="UNCHANGED_LGB_PARITY_DRIFT"):
        report.unchanged_lgb_parity(windows)


def test_raw_and_executed_empty_census_join_by_asset_session_horizon(completed: tuple) -> None:
    windows = _report_windows(completed)
    records = []
    for row in windows["v3"]["primary"][0]["empty_window_secondary"]["census_by_session"]:
        if row["horizon"] != "5m":
            continue
        records.append(
            {
                "asset": row["asset"],
                "session_date": row["session_date"],
                "N_origins": row["N_origins"] + 1,
                "b2_5m_window_empty_count": 1,
                "b2_30m_window_empty_count": 1,
                "b2_5m_window_empty_unknown": row["N_origins"],
                "b2_30m_window_empty_unknown": row["N_origins"],
            }
        )
    result = report.empty_census_comparison(records[::-1], windows)
    assert len(result) == 2 * 24 * 2 * 2
    assert all(r["available_origins"] == r["executed_N_origins"] + 1 for r in result)
    assert all(r["available_empty"] == 1 and r["executed_N_empty_origins"] == 0 for r in result)
    assert all(r["executed_N_unknown_origins"] == r["executed_N_origins"] for r in result)
    records[0]["N_origins"] = 0
    with pytest.raises(ValueError, match="CENSUS_ACCOUNTING"):
        report.empty_census_comparison(records, windows)


def test_synthetic_report_end_to_end_pins_both_manifests_without_panel_reads(
    completed: tuple,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root, private = tmp_path / "repo", tmp_path / "private"
    monkeypatch.setattr(report, "ROOT", root)

    def write(path: Path, value: object) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value if isinstance(value, str) else json.dumps(value), encoding="utf-8")
        return path

    def write_csv(path: Path, value: list[dict]) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(report.csv_bytes(value))
        return path

    fake_source = write(root / "artifacts/rp4_v3_code/report_v3.py", "synthetic report source")
    monkeypatch.setattr(report, "__file__", str(fake_source))
    inference_source = write(
        root / "artifacts/rp4_v3_code/inference.py", "synthetic inference source"
    )
    code_pins = {inference_source.relative_to(root).as_posix(): report.sha256(inference_source)}
    for name in (
        "results_v1.md",
        "results_v2.md",
        "specification_v3.md",
        "decision_131_v3.md",
        "v3_addendum_stability_calibration.md",
        "v3_window_empty_addendum.md",
        "decision_132_v3_empty_windows.md",
    ):
        write(root / "docs/rp4" / name, "synthetic immutable " + name)
    original = write(root / "artifacts/rp4_v3_a1/specification.json", {"synthetic": "original"})
    original_freeze = write(original.parent / "freeze.json", {"synthetic": "freeze"})
    rule = {
        "md_path": "docs/rp4/v3_window_empty_addendum.md",
        "md_sha256": report.sha256(root / "docs/rp4/v3_window_empty_addendum.md"),
        "decision_path": "docs/rp4/decision_132_v3_empty_windows.md",
        "decision_sha256": report.sha256(root / "docs/rp4/decision_132_v3_empty_windows.md"),
        "columns_to_nan": {"5": ["synthetic_share"], "30": []},
    }
    spec = {
        "label": "SYNTHETIC ONLY",
        "assets": ["A", "B"],
        "data_root": str(private),
        "evaluation_panel_relative_path": "materialized_empty_windows/panel.parquet",
        "empty_window_addendum": rule,
        "specification_md_path": "docs/rp4/specification_v3.md",
        "specification_md_sha256": report.sha256(root / "docs/rp4/specification_v3.md"),
        "decision_sha256": report.sha256(root / "docs/rp4/decision_131_v3.md"),
        "addendum_sha256": report.sha256(root / "docs/rp4/v3_addendum_stability_calibration.md"),
        "original_v3_specification_sha256": report.sha256(original),
    }
    spec_path = write(root / "artifacts/rp4_v3_a1_empty_window/specification.json", spec)
    digest = report.sha256(spec_path)
    write(
        spec_path.parent / "freeze.json",
        {
            "specification_sha256": digest,
            "addendum": rule,
            "original_v3_freeze_sha256": report.sha256(original_freeze),
        },
    )
    gamma_dir, recode_dir = private / "materialized", private / "materialized_empty_windows"
    gamma_exports = {}
    for name in ("comparison.csv", "coverage.csv", "counts.csv"):
        path = write_csv(gamma_dir / name, [{"synthetic": "aggregate"}])
        gamma_exports[str(path)] = report.sha256(path)
    gamma_panel_digest, recoded_panel_digest = "a" * 64, "b" * 64
    gamma_exports[str(gamma_dir / "panel.parquet")] = gamma_panel_digest
    gamma_manifest = write(
        gamma_dir / "manifest.json",
        {
            "spec_sha256": report.sha256(original),
            "preserved_values_exact_by_keys": True,
            "artifacts": gamma_exports,
            "rv30_alignment": {"maximum_absolute_difference": 0.0},
        },
    )
    windows = _report_windows(completed)
    raw_census = [
        {
            "asset": r["asset"],
            "session_date": r["session_date"],
            "N_origins": r["N_origins"],
            "b2_5m_window_empty_count": 0,
            "b2_30m_window_empty_count": 0,
            "b2_5m_window_empty_unknown": r["N_origins"],
            "b2_30m_window_empty_unknown": r["N_origins"],
        }
        for r in windows["v3"]["primary"][0]["empty_window_secondary"]["census_by_session"]
        if r["horizon"] == "5m"
    ]
    census_path = write_csv(recode_dir / "census.csv", raw_census)
    recode_audit = write(
        recode_dir / "recode_audit.json",
        [{"window_minutes": 5, "column": "synthetic_share", "empty_rows": 0}],
    )
    recode_manifest = write(
        recode_dir / "manifest.json",
        {
            "spec_sha256": digest,
            "source_gamma_manifest_sha256": report.sha256(gamma_manifest),
            "source_gamma_panel_sha256": gamma_panel_digest,
            "preserved_unaffected_values_exact_by_keys": True,
            "preserved_values_exact_by_keys": False,
            "changed_columns_only": rule["columns_to_nan"],
            "excluded_origins": 0,
            "excluded_sessions": 0,
            "artifacts": {
                str(recode_dir / "panel.parquet"): recoded_panel_digest,
                str(census_path): report.sha256(census_path),
                str(recode_audit): report.sha256(recode_audit),
            },
        },
    )
    release = write(
        root / "artifacts/rp4_v3_a2/evaluation_release.json",
        {
            "specification_sha256": digest,
            "panel_sha256": recoded_panel_digest,
            "materialization_manifest_sha256": report.sha256(recode_manifest),
        },
    )
    legacy = {
        "parent_specification_sha256": "v1",
        "specification_sha256": "v2",
        "inputs_sha256": {},
        "outputs_sha256": {},
    }
    for name in ("results_v1.md", "results_v2.md"):
        path = root / "docs/rp4" / name
        legacy["inputs_sha256"][path.relative_to(root).as_posix()] = report.sha256(path)
    for version in report.VERSIONS:
        prefix = "rp4" if version == "v1" else f"rp4_{version}"
        for window, stage in (("primary", "b2"), ("confirmation", "b3")):
            summary, rows = copy.deepcopy(windows[version][window])
            directory = root / "artifacts" / f"{prefix}_{stage}"
            fit_records = []
            if version == "v3":
                summary["binding"] = {
                    "specification_sha256": digest,
                    "panel_sha256": recoded_panel_digest,
                    "release_sha256": report.sha256(release),
                    "code_sha256": code_pins,
                }
                summary["materialization_manifest_sha256"] = report.sha256(recode_manifest)
                for day in [r["session_date"] for r in rows]:
                    validation = (
                        pd.bdate_range(end=pd.Timestamp(day) - pd.offsets.BDay(1), periods=10)
                        .strftime("%Y-%m-%d")
                        .tolist()
                    )
                    for endpoint in ("mean", "quantile", "jump"):
                        for family in inf.FAMILIES:
                            for name in inf.SETS:
                                fit = {
                                    "session": day,
                                    "model": f"{endpoint}__{family}__{name}",
                                    "endpoint": endpoint,
                                    "inner_valid_sessions": validation,
                                    "selected": {"lambda": 1.0}
                                    if family == "log_ridge_harq"
                                    else {"rounds": 400, "num_leaves": 31},
                                }
                                if endpoint == "mean" and family == "lightgbm_qlike":
                                    fit["mz_secondary"] = {
                                        "calibration": {
                                            "calibration_sessions": validation,
                                            "inner_fit_last_session": str(
                                                pd.Timestamp(validation[0]).date()
                                                - pd.Timedelta(days=1)
                                            ),
                                            "applied_coefficients": {
                                                "intercept": 0.0,
                                                "slope": 1.0,
                                            },
                                            "N_sessions": 10,
                                            "training_identity_fallback": False,
                                            "training_fallback_reason": None,
                                            "origin_identity_fallback_count": 0,
                                            "count_floor": 0,
                                            "prediction_rows": 5,
                                        }
                                    }
                                fit_records.append(fit)
            summary_path = write(directory / "summary.json", summary)
            loss_path = write_csv(directory / "session_losses.csv", rows)
            if version != "v3":
                for path in (summary_path, loss_path):
                    legacy["inputs_sha256"][path.relative_to(root).as_posix()] = report.sha256(path)
                continue
            fit_path = write(private / "evaluation" / window / "fit_diagnostics.json", fit_records)
            log = write(private / "operations" / (window + ".log"), "synthetic completed exit 0")
            write(
                directory / "receipt.json",
                {
                    "status": "COMPLETE",
                    "exit_code": 0,
                    "stage": stage.upper(),
                    "window": window,
                    "execution_failure": None,
                    "release_sha256": report.sha256(release),
                    "evaluation_code_sha256": code_pins,
                    "artifacts_sha256": {
                        str(p): report.sha256(p) for p in (summary_path, loss_path, fit_path)
                    },
                    "commands": [
                        {
                            "command": "synthetic-only fixture",
                            "exit_code": 0,
                            "log": str(log),
                            "log_sha256": report.sha256(log),
                        }
                    ],
                },
            )
    legacy_path = write(root / "artifacts/rp4_v2_b4/report_manifest.json", legacy)
    monkeypatch.setattr(report, "LEGACY_MANIFEST_SHA", report.sha256(legacy_path))
    args = argparse.Namespace(spec=spec_path, spec_sha256=digest)
    result = report.run(args)
    assert result["models_fitted"] == 0 and result["raw_or_origin_panels_read"] is False
    assert (
        not (gamma_dir / "panel.parquet").exists() and not (recode_dir / "panel.parquet").exists()
    )
    assert result["specification_sha256"] == digest
    assert "private/materialized/manifest.json" in result["inputs_sha256"]
    assert "private/materialized_empty_windows/manifest.json" in result["inputs_sha256"]
    assert all(r["maximum_absolute_difference"] == 0 for r in result["unchanged_lgb_parity"])
    assert report.run(args) == result
    rendered = (root / "docs/rp4/results_v3.md").read_text(encoding="utf-8")
    assert "SYNTHETIC ONLY" in rendered and "Source unknown" in rendered
    assert "Linear (quantile)" in rendered and "LightGBM (binary)" in rendered
