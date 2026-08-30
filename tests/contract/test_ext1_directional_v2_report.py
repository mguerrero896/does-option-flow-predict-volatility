"""The Ext1 directional report is bound to its versioned aggregate artifact."""

from __future__ import annotations

import json
from pathlib import Path

from mds650.b1v3_confirmation import canonical_sha256, sha256_file

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "artifacts" / "rp2_ext1_directional_v2" / "results.json"
FROZEN = ROOT / "artifacts" / "rp2_ext1_mechanism_utility" / "mechanism_utility.json"
REPORT = ROOT / "docs" / "rp2" / "extension_b2_directional_utility_v2.md"
DECISIONS = ROOT / "docs" / "methodology_decisions.md"


def _results() -> dict[str, object]:
    return json.loads(RESULTS.read_text(encoding="utf-8"))


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
