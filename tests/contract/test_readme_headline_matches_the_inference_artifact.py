"""Bind the current front-page claims to the stored RP4 primary mean inference.

Historical RP2 illustrations are not the current headline. These checks read the
complete saved summaries without fitting, resampling, or silently skipping a missing
source. Positive effects, uncertainty, sequential decisions and adverse results remain
separate requirements; a secondary median cannot replace the primary mean.
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any, Final

REPO = Path(__file__).resolve().parents[2]
README = REPO / "README.md"
PRIMARY: Final = {
    "v3 · RV30": "artifacts/rp4_v3_b2/summary.json",
    "v4 · RV15, primary": "artifacts/rp4_v4_b2_rv15/summary.json",
}
LINEAR: Final = "log_ridge_harq"
TREES: Final = "lightgbm_qlike"


def _summary(name: str, window: str = "primary") -> dict[str, Any]:
    artifact: dict[str, Any] = json.loads((REPO / name).read_text(encoding="utf-8"))
    assert artifact["status"] == "COMPUTED"
    assert artifact["window"] == window
    assert artifact["N_sessions"] == (419 if window == "primary" else 25)
    assert len(artifact["contrasts"]) == 4
    return artifact


def _cell(artifact: dict[str, Any], family: str, contrast: str) -> dict[str, Any]:
    cells = [
        cell
        for cell in artifact["contrasts"]
        if cell["family"] == family and cell["contrast"] == contrast
    ]
    assert len(cells) == 1, (family, contrast)
    cell: dict[str, Any] = cells[0]
    assert cell["status"] == "COMPUTED"
    assert cell["endpoint"] == "qlike_mean" and cell["statistic"] == "mean"
    return cell


def _percent(cell: dict[str, Any]) -> str:
    return f"{cell['qlike_reduction_percent']:+.3f}".replace("-", "−")


def _table_row(readme: str, label: str, columns: int = 6) -> list[str]:
    rows = [line for line in readme.splitlines() if line.startswith(f"| {label} |")]
    assert len(rows) == 1, f"Missing or duplicate headline table row: {label}"
    cells = [value.strip() for value in rows[0].strip("|").split("|")]
    assert len(cells) == columns
    return cells


def _prose(readme: str) -> str:
    return " ".join(readme.replace("**", "").split())


def _section(readme: str, title: str) -> str:
    marker = f"## {title}\n"
    assert readme.count(marker) == 1, f"Missing or duplicate section: {title}"
    return readme.split(marker, 1)[1].split("\n## ", 1)[0]


def test_the_readme_states_the_registered_surface_improvements() -> None:
    readme = README.read_text(encoding="utf-8")
    for label, source in PRIMARY.items():
        artifact = _summary(source)
        row = _table_row(readme, label)
        for family, column in ((LINEAR, 1), (TREES, 3)):
            cell = _cell(artifact, family, "B1_over_B0")
            assert cell["estimate"] > 0 and cell["rejected"] is True
            assert cell["hypothesis_status"] == "REJECTED"
            assert f"{_percent(cell)} %" in row[column]
    results = _section(readme, "Results")
    artifact = _summary(PRIMARY["v4 · RV15, primary"])
    for family, label in ((LINEAR, "Linear"), (TREES, "Trees")):
        cell = _cell(artifact, family, "B1_over_B0")
        assert _table_row(results, label, 3)[1] == (
            f"{_percent(cell)}% (p = {cell['p_for_decision']:.4f})"
        )


def test_the_readme_does_not_claim_a_clean_sweep_when_tree_flow_does_not_reject() -> None:
    readme = README.read_text(encoding="utf-8")
    for label, source in PRIMARY.items():
        artifact = _summary(source)
        cell = _cell(artifact, TREES, "B2_over_B1")
        assert cell["estimate"] < 0 and cell["rejected"] is False
        assert cell["hypothesis_status"] == "NOT_REJECTED"
        assert artifact["global_joint_reject"] is False
        assert f"{_percent(cell)} %" in _table_row(readme, label)[4]
    headline = _prose(_section(readme, "In one minute"))
    assert "the tree model does not improve" in headline.lower()
    limits = _prose(_section(readme, "Limits"))
    assert "neither the dealer-hedging mechanism, economic alpha, profitability" in limits
    assert "nor broader generalization" in limits


def test_the_readme_names_the_registered_linear_flow_estimate_and_interval() -> None:
    artifact = _summary(PRIMARY["v4 · RV15, primary"])
    cell = _cell(artifact, LINEAR, "B2_over_B1")
    assert 0 < cell["ci_low"] < cell["estimate"] < cell["ci_high"]
    assert cell["rejected"] is True
    readme = README.read_text(encoding="utf-8")
    headline = _prose(_section(readme, "In one minute"))
    percent = f"{cell['qlike_reduction_percent']:+.2f}"
    assert f"{percent}% lower forecast loss" in headline
    assert "in the linear model at 15 minutes" in headline
    assert f"p = {cell['p_for_decision']:.3f}" in headline
    results = _prose(_section(readme, "Results"))
    assert "positive 95% interval" in results
    interval = f"[{cell['ci_low']:.6f}; {cell['ci_high']:.6f}]"
    assert f"{interval} in QLIKE units" in results


def test_the_readme_keeps_sequential_p_values_distinct_from_bilateral_comparisons() -> None:
    readme = README.read_text(encoding="utf-8")
    for label, source in PRIMARY.items():
        artifact = _summary(source)
        row = _table_row(readme, label)
        for family, contrast, column in (
            (LINEAR, "B1_over_B0", 1),
            (LINEAR, "B2_over_B1", 2),
            (TREES, "B1_over_B0", 3),
            (TREES, "B2_over_B1", 4),
        ):
            cell = _cell(artifact, family, contrast)
            assert cell["alternative"] == "greater" and cell["alpha"] == 0.05
            p_value = f"{cell['p_for_decision']:.4f}"
            assert row[column] == f"{_percent(cell)} % ({p_value})"
    text = _prose(readme)
    history = _prose(_section(readme, "Results"))
    assert "one-sided sequence at 5% per family" in history
    assert "H2 opened only if H1 rejects" in history
    assert "Cross-version search is not adjusted" in text
    closure = _summary(PRIMARY["v4 · RV15, primary"])["predeclared_closure"]
    assert closure["satisfied"] is True
    assert closure["successful_families"] == [LINEAR]
    assert "v4 supplies the headline" in history
    results = _section(readme, "Results")
    artifact = _summary(PRIMARY["v4 · RV15, primary"])
    for family, label in ((LINEAR, "Linear"), (TREES, "Trees")):
        row = _table_row(results, label, 3)
        for column, contrast in ((1, "B1_over_B0"), (2, "B2_over_B1")):
            cell = _cell(artifact, family, contrast)
            assert row[column] == f"{_percent(cell)}% (p = {cell['p_for_decision']:.4f})"
    assert "p-values belong to the declared one-sided sequence" in _prose(results)
    flow = _cell(artifact, LINEAR, "B2_over_B1")
    with (REPO / "artifacts/rp4_v4_b4/primary_statistics.csv").open(encoding="utf-8") as file:
        bilateral = [
            row
            for row in csv.DictReader(file)
            if row["horizon_minutes"] == "15"
            and row["window"] == "primary"
            and row["family"] == LINEAR
            and row["contrast"] == "B2_over_B1"
        ]
    assert len(bilateral) == 1
    assert float(bilateral[0]["p_raw"]) == flow["p_for_decision"]
    assert f"bilateral Holm-adjusted p = {float(bilateral[0]['p_holm_bilateral']):.4f}" in _prose(
        results
    )
    assert "separate comparability analysis" in _prose(results)
    assert "not another adjustment to the one-sided sequence" in _prose(results)


def test_the_readme_states_that_the_final_window_does_not_confirm_the_sequence() -> None:
    artifact = _summary("artifacts/rp4_v4_b3_rv15/summary.json", "confirmation")
    cells = [_cell(artifact, family, "B2_over_B1") for family in (LINEAR, TREES)]
    assert any(cell["estimate"] > 0 for cell in cells)
    assert any(cell["estimate"] < 0 for cell in cells)
    assert all(cell["hypothesis_status"] == "NOT_TESTED" for cell in cells)
    assert all(cell["p_for_decision"] is None for cell in cells)
    assert all(
        not result["both_rejected"] for result in artifact["primary_sequence"]["families"].values()
    )
    text = _prose(README.read_text(encoding="utf-8"))
    assert (
        f"The final {artifact['N_sessions']}-session window does not confirm the full test sequence"
        in text
    )


def test_the_readme_restores_the_existing_navigation_destinations() -> None:
    readme = README.read_text(encoding="utf-8")
    links = set(re.findall(r"\[[^\]]+\]\(([^)]+)\)", readme))
    for target in (
        "CITATION.cff",
        "CONTRIBUTING.md",
        "LICENSE",
        "SECURITY.md",
        "STATUS.md",
        "artifacts/rp4_closeout_figures/comparison_v1_v4.csv",
        "artifacts/rp4_v4_b4/primary_statistics.csv",
        "artifacts/rp4_v4_b4/robustness.csv",
        "data/CANONICAL_STATE.json",
        "data/DATA_ACCESS.md",
        "docs/AI_ASSISTANCE_STATEMENT.md",
        "docs/DEVELOPER_GUIDE.md",
        "docs/INDEX.md",
        "docs/figures/rp4/thesis_summary.svg",
        "docs/known_defects_and_resolutions.md",
        "docs/pit_v22_claims_and_limitations.md",
        "docs/reproduce.md",
        "docs/reproducibility_contract_v1.md",
        "docs/research_decisions_current.md",
        "docs/rp2_v3/SUPERSEDED_RESULTS.md",
        "docs/rp3/PREREGISTRATION.md",
        "docs/rp4/DEFENSE_PACKAGE/revision_2/correction_7/README.md",
        "docs/rp4/DEFENSE_PACKAGE/revision_2/correction_7/examiner_qa.md",
        "docs/rp4/results_universe_v1.md",
        "docs/rp4/results_v4.md",
        "docs/rp4/results_v5.md",
        "docs/rp4/specification_v4.md",
        "docs/scientific_findings_ledger.md",
        "docs/threats_to_validity_matrix_v1.md",
        "https://github.com/mguerrero896/does-option-flow-predict-volatility/actions/workflows/ci.yml/badge.svg",
        "https://github.com/mguerrero896/does-option-flow-predict-volatility/issues",
        "reports/INDEX.md",
        "reports/phase8a_exploratory_bridge_addendum_v13.md",
        "scripts/README.md",
        "supabase/README.md",
    ):
        assert target in links, f"Missing navigation link: {target}"
        if not target.startswith("https://"):
            assert (REPO / target).is_file(), f"Broken navigation destination: {target}"
    assert "https://github.com/mguerrero896/does-option-flow-predict-volatility/issues" in links
