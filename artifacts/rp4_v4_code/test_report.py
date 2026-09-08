"""Synthetic report checks: targets, decisions, and cumulative SVG endpoints."""

from __future__ import annotations

import copy
import xml.etree.ElementTree as ET
from itertools import accumulate

import pytest
from artifacts.rp4_v4_code import report_v4 as report
from artifacts.rp4_v4_code.aggregate_v4 import aggregate_records
from artifacts.rp4_v4_code.test_aggregate import OPTIONS, synthetic_records


@pytest.fixture(scope="module")
def result_set() -> report.Results:
    output = {}
    for h in report.LABELS:
        summary, frame = aggregate_records(synthetic_records(horizon=5 if h == 5 else 15), OPTIONS)
        rows = frame.to_dict("records")
        for window in report.WINDOWS:
            s = copy.deepcopy(summary)
            s.update(window=window, horizon_minutes=h, target_key=f"rv_{h}")
            s["binding"] = {"specification_sha256": report.SPEC_SHA}
            s["completed_session_sha256"] = {r["session_date"] + ".json": "SYNTHETIC" for r in rows}
            output[h, window] = s, rows
    return output


def test_report_checks_means_targets_and_gate(result_set: report.Results) -> None:
    for (h, window), (summary, rows) in result_set.items():
        report.verify_results(summary, rows, h, window)
    summary, rows = copy.deepcopy(result_set[15, "primary"])
    summary["target_key"] = "rv30"
    with pytest.raises(ValueError, match="WRONG_TARGET"):
        report.verify_results(summary, rows, 15, "primary")
    summary["target_key"] = "rv_15"
    summary["contrasts"][0]["estimate"] += 1
    with pytest.raises(ValueError, match="V4_ESTIMATE"):
        report.verify_results(summary, rows, 15, "primary")


def test_svg_contains_all_windows_families_horizons_and_exact_endpoints(
    result_set: report.Results,
) -> None:
    for contrast, base, richer in report.inf.CONTRASTS:
        svg = ET.fromstring(report.figure(result_set, contrast, base, richer))
        curves = svg.findall(".//{http://www.w3.org/2000/svg}path")
        assert len(curves) == 12
        seen = set()
        for curve in curves:
            h = int(curve.attrib["data-horizon"])
            window, family = curve.attrib["data-window"], curve.attrib["data-family"]
            seen.add((h, window, family))
            rows = result_set[h, window][1]
            expected = list(accumulate(report.differences(rows, family, base, richer)))[-1]
            assert float(curve.attrib["data-endpoint"]) == expected
            assert int(curve.attrib["data-sessions"]) == len(rows)
        assert len(seen) == 12


def test_tables_separate_secondary_and_diagnostic_p(result_set: report.Results) -> None:
    summary, _ = result_set[5, "confirmation"]
    original = copy.deepcopy(summary)
    try:
        summary["contrasts"][1]["p_for_decision"] = None
        summary["contrasts"][1]["hypothesis_status"] = "NOT_TESTED"
        text = report.main_table(result_set, "confirmation")
        assert "NO ABIERTA" in text
        assert "v4 RV5 secundario" in text
        assert "v4 RV15 primario" in text
        assert "v3 RV30" in text
    finally:
        summary.clear()
        summary.update(original)


def test_bound_counts_preserve_missing_and_reject_impossible() -> None:
    row = {
        "horizon_minutes": 15,
        "window": "primary",
        "information_set": "B2",
        "family": "log_ridge_harq",
        "prediction_rows": 12,
        "count_low": 1,
        "count_high": 2,
        "validation_rows": 100,
        "validation_count_low": 3,
        "validation_count_high": 4,
    }
    counts = report.bound_rows([row, row])
    assert counts[0]["N_predictions"] == 24
    assert counts[0]["count_low"] == 2
    unknown = {**row, "count_high": None}
    assert report.bound_rows([unknown])[0]["status"] == "NO VERIFICABLE"
    assert report.bound_rows([unknown])[0]["count_low"] is None
    with pytest.raises(ValueError, match="COUNTS_INVALID"):
        report.bound_rows([{**row, "count_low": 20}])
