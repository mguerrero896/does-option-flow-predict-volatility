from pathlib import Path

import pytest
from scripts.verify_omitted_contracts import complete, omitted_nodes


def test_selection_and_strict_success(tmp_path: Path):
    report = tmp_path / "test.xml"
    case = '<testcase classname="tests.contract.test_example" name="test_pair[B0]">{}</testcase>'
    report.write_text("<testsuite>" + case.format("<skipped/>") + "</testsuite>")
    nodes = omitted_nodes(report)
    assert nodes == ["tests/contract/test_example.py::test_pair[B0]"]
    assert not complete(report, nodes)
    for marker in ("<failure/>", "<error/>"):
        report.write_text("<testsuite>" + case.format(marker) + "</testsuite>")
        assert not complete(report, nodes)
    report.write_text("<testsuite>" + case.format("") + "</testsuite>")
    assert complete(report, nodes)
    assert not complete(report, nodes + ["missing"])


def test_selection_rejects_unreviewed_modules(tmp_path: Path):
    report = tmp_path / "test.xml"
    report.write_text(
        '<testsuite><testcase classname="other" name="test_x"><skipped/></testcase></testsuite>'
    )
    with pytest.raises(ValueError, match="CONTRACT_MODULES"):
        omitted_nodes(report)


def test_configured_rp4_inputs_fail_when_missing_or_changed(tmp_path: Path, monkeypatch):
    from tests.contract import test_rp4_defense_additions as audit

    monkeypatch.setenv("MDS650_RP4_AUDIT_ROOT", str(tmp_path))
    with pytest.raises(AssertionError, match="RP4_AUDIT_INPUT_MISSING"):
        audit.test_event_transcription_matches_local_aggregates_and_separates_windows()
    for name in audit.LOCAL_AGGREGATES:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("changed bytes\n")
    with pytest.raises(AssertionError, match="Historical source bytes changed"):
        audit.test_event_transcription_matches_local_aggregates_and_separates_windows()
