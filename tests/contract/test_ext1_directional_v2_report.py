"""The Ext1 directional report is bound to its versioned aggregate artifact."""

from __future__ import annotations

import json
from pathlib import Path

from mds650.b1v3_confirmation import canonical_sha256, sha256_file

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "artifacts" / "rp2_ext1_directional_v2" / "results.json"
FACTORIAL_RESULTS = ROOT / "artifacts" / "rp2_ext1_directional_factorial_v3" / "results.json"
FROZEN = ROOT / "artifacts" / "rp2_ext1_mechanism_utility" / "mechanism_utility.json"
REPORT = ROOT / "docs" / "rp2" / "extension_b2_directional_utility_v2.md"
DECISIONS = ROOT / "docs" / "methodology_decisions.md"


def _results() -> dict[str, object]:
    return json.loads(RESULTS.read_text(encoding="utf-8"))


def _factorial_results() -> dict[str, object]:
    return json.loads(FACTORIAL_RESULTS.read_text(encoding="utf-8"))


def test_directional_artifact_is_self_hashed_and_complete() -> None:
    document = _results()
    stored = document.pop("self_sha256")
    assert stored == canonical_sha256(document)
    assert document["sealed_cohorts_read"] == 0
    directional = document["directional"]
    assert isinstance(directional, dict)
    tests = directional["tests"]
    assert isinstance(tests, dict) and len(tests) == 68
    assert directional["decision"]["status"] == "DO_NOT_PURSUE"  # type: ignore[index]


def test_frozen_ext1_artifact_was_not_changed() -> None:
    assert sha256_file(FROZEN) == "604e1e40990b1a9a6e0800691f0cb1dca0db658781f23838b8f49d47f263f499"


def test_factorial_artifact_is_self_hashed_and_complete() -> None:
    document = _factorial_results()
    stored = document.pop("self_sha256")
    assert stored == canonical_sha256(document)
    assert document["sealed_cohorts_read"] == 0
    tests = document["tests"]
    assert isinstance(tests, dict) and len(tests) == 40
    assert document["mask_invariants"][  # type: ignore[index]
        "same_coverage_role_horizon_same_mask_across_treatment_sets"
    ]
    assert document["mask_invariants"]["august_mask_subset_of_complete_mask"]  # type: ignore[index]
    assert document["attribution"]["classification"] == "TREATMENT_SET"  # type: ignore[index]


def test_factorial_uses_exact_treatments_and_recorded_alias() -> None:
    designs = _factorial_results()["designs"]
    assert isinstance(designs, dict)
    ext1 = designs["ext1_exact/august/D"]
    b2 = designs["b2_panel_12/august/D"]
    assert isinstance(ext1, dict) and isinstance(b2, dict)
    assert len(ext1["requested_treatments"]) == len(ext1["resolved_panel_columns"]) == 10
    assert len(b2["requested_treatments"]) == len(b2["resolved_panel_columns"]) == 12
    assert ext1["requested_treatments"][5] == "b2_5m_hawkes_innovation"
    assert ext1["resolved_panel_columns"][5] == "b2_5m_decay_intensity_innovation"
    assert ext1["alias_resolution"] == [
        {
            "panel_column": "b2_5m_decay_intensity_innovation",
            "requested_feature": "b2_5m_hawkes_innovation",
            "resolution": "RECORDED_SEMANTIC_RENAME",
            "value_operation": "IN_MEMORY_DESIGN_ALIAS_NO_RECOMPUTATION",
        }
    ]
    assert all(
        design["treatment_design_policy"] == "EXACT_REQUESTED_FEATURES_NO_MISSING_INDICATORS"
        for design in designs.values()
    )


def test_report_contains_all_four_factorial_cells_and_limits() -> None:
    document = _factorial_results()
    tests = document["tests"]
    assert isinstance(tests, dict)
    report = REPORT.read_text(encoding="utf-8")
    for treatment_set in ("ext1_exact", "b2_panel_12"):
        for coverage in ("august", "complete"):
            for role in ("D", "V"):
                for horizon in (60, 120):
                    record = tests[f"{treatment_set}/{coverage}/{role}/h{horizon}"]
                    assert isinstance(record, dict)
                    assert f"{float(record['joint_wald']):.3f}" in report
    assert str(document["self_sha256"]) in report
    assert "290debdca033737e386c5abe9cca4e0b1d7632435e07f747823198864da256a4" in report
    assert "RECORDED_SEMANTIC_RENAME" in report
    assert "NEITHER_TREATMENT_SET_NOR_COVERAGE" in report
    assert "historical byte equality cannot be tested" in report


def test_report_names_the_measured_result_and_its_limits() -> None:
    document = _results()
    report = REPORT.read_text(encoding="utf-8")
    assert str(document["self_sha256"]) in report
    assert "DO_NOT_PURSUE" in report
    assert "fc083b0d9df26e913f4348d9c64f4cd8e83b8e963169743d0d5cd6dd5488ebde" in report
    assert "y_rs_up_60" in report and "0.03576" in report
    assert "exact reproduction cannot be confirmed" in report.lower()
    assert "Phase 8, Phase 9, and cohort C were not read" in report
    assert "previously" not in report.lower()


def test_methodology_decision_103_binds_the_follow_up() -> None:
    decisions = DECISIONS.read_text(encoding="utf-8")
    assert '<a id="decision-103"></a>' in decisions
    assert "fc083b0d9df26e913f4348d9c64f4cd8e83b8e963169743d0d5cd6dd5488ebde" in decisions
    assert "DO_NOT_PURSUE" in decisions


def test_report_headline_numbers_come_from_the_artifact() -> None:
    document = _results()
    directional = document["directional"]
    coverage = document["coverage"]
    assert isinstance(directional, dict) and isinstance(coverage, dict)
    tests = directional["tests"]
    assert isinstance(tests, dict)
    report = REPORT.read_text(encoding="utf-8")
    for key in ("dml/V_all/matched120_tod/h60", "dml/V_all/matched120_tod/h120"):
        record = tests[key]
        assert isinstance(record, dict)
        assert f"{float(record['theta']) * 10_000:.3f}" in report
        assert f"{float(record['familywise_mde']) * 10_000:.3f}" in report
    for key in ("metric/V_all/matched120_tod/h60", "metric/V_all/matched120_tod/h120"):
        record = tests[key]
        assert isinstance(record, dict)
        assert f"{float(record['balanced_accuracy']):.3%}" in report
    current = coverage["current"]
    assert isinstance(current, dict)
    assert f"{int(current['target_rows_emitted']):,}" in report
