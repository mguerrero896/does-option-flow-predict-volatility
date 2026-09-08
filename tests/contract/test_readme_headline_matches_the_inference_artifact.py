"""Bind the current front-page claims to the stored RP4 primary mean inference.

Historical RP2 illustrations are not the current headline. These checks read the
complete saved summaries without fitting, resampling, or silently skipping a missing
source. Positive effects, uncertainty, sequential decisions and adverse results remain
separate requirements; a secondary median cannot replace the primary mean.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Final

REPO = Path(__file__).resolve().parents[2]
README = REPO / "README.md"
PRIMARY: Final = {
    "v3 · RV30": "artifacts/rp4_v3_b2/summary.json",
    "v4 · RV15, primario": "artifacts/rp4_v4_b2_rv15/summary.json",
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
    return f"{cell['qlike_reduction_percent']:+.3f}".replace(".", ",").replace("-", "−")


def _table_row(readme: str, label: str) -> list[str]:
    rows = [line for line in readme.splitlines() if line.startswith(f"| {label} |")]
    assert len(rows) == 1, f"Missing or duplicate headline table row: {label}"
    cells = [value.strip() for value in rows[0].strip("|").split("|")]
    assert len(cells) == 6
    return cells


def _prose(readme: str) -> str:
    return " ".join(readme.replace("**", "").split())


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
    headline = _prose(readme.split("## ", 1)[0])
    assert re.search(r"RV30 y RV15.{0,60}en ambas familias", headline)


def test_the_readme_does_not_claim_a_clean_sweep_when_tree_flow_does_not_reject() -> None:
    readme = README.read_text(encoding="utf-8")
    for label, source in PRIMARY.items():
        artifact = _summary(source)
        cell = _cell(artifact, TREES, "B2_over_B1")
        assert cell["estimate"] < 0 and cell["rejected"] is False
        assert cell["hypothesis_status"] == "NOT_REJECTED"
        assert artifact["global_joint_reject"] is False
        assert f"{_percent(cell)} %" in _table_row(readme, label)[4]
    headline = _prose(readme.split("## ", 1)[0])
    assert re.search(r"en árboles no supera la prueba de la media", headline)
    assert "No es una ventaja universal ni evidencia de rentabilidad" in headline


def test_the_readme_names_the_registered_linear_flow_estimate_and_interval() -> None:
    artifact = _summary(PRIMARY["v4 · RV15, primario"])
    cell = _cell(artifact, LINEAR, "B2_over_B1")
    assert 0 < cell["ci_low"] < cell["estimate"] < cell["ci_high"]
    assert cell["rejected"] is True
    headline = _prose(README.read_text(encoding="utf-8").split("## ", 1)[0])
    assert re.search(rf"15 minutos.{{0,30}}{re.escape(_percent(cell))} %", headline)
    assert "IC95 % positivo" in headline
    interval = f"[{cell['ci_low']:.6f}; {cell['ci_high']:.6f}]".replace(".", ",")
    assert f"diferencia QLIKE {interval}" in headline


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
            p_value = f"{cell['p_for_decision']:.4f}".replace(".", ",")
            assert row[column] == f"{_percent(cell)} % ({p_value})"
    text = _prose(readme)
    assert "H1→H2 unilateral al 5 % por familia" in text
    assert "H2 sólo se abre cuando H1 rechaza" in text
    assert "No se corrige la búsqueda entre versiones" in text
    closure = _summary(PRIMARY["v4 · RV15, primario"])["predeclared_closure"]
    assert closure["satisfied"] is True
    assert closure["successful_families"] == [LINEAR]
    assert "El programa termina en v4, sin v5" in text


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
        f"La ventana final de {artifact['N_sessions']} sesiones no confirma la secuencia completa"
        in text
    )


def test_the_readme_restores_the_existing_navigation_destinations() -> None:
    readme = README.read_text(encoding="utf-8")
    section = readme.rsplit("## Navegación", 1)
    assert len(section) == 2, "The final navigation section is missing."
    links = set(re.findall(r"\[[^\]]+\]\(([^)]+)\)", section[1]))
    for target in (
        "CONTRIBUTING.md",
        "docs/INDEX.md",
        "docs/AI_ASSISTANCE_STATEMENT.md",
        "docs/threats_to_validity_matrix_v1.md",
        "scripts/README.md",
        "reports/INDEX.md",
        "supabase/README.md",
    ):
        assert target in links, f"Missing navigation link: {target}"
        assert (REPO / target).is_file(), f"Broken navigation destination: {target}"
    assert "https://github.com/mguerrero896/does-option-flow-predict-volatility/issues" in links
