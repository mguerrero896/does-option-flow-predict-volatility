from __future__ import annotations

import json
from pathlib import Path

from scripts import render_figures

REPO = Path(__file__).resolve().parents[2]


def test_evidence_figure_uses_canonical_lifecycle_and_measured_flow_count() -> None:
    state = json.loads(
        (REPO / "data" / "CANONICAL_STATE.json").read_text(encoding="utf-8")
    )
    run = state["scientific_bundle"]["run_id"]
    artifact = json.loads(
        (
            REPO
            / "artifacts"
            / "rp2_v3"
            / run
            / "rp2_block10_inference"
            / "inference.json"
        ).read_text(encoding="utf-8")
    )
    flow_clears = sum(
        abs(cell["estimate"]) > cell["mde"]
        for universe in ("D", "V")
        for contrasts in artifact[universe]["nested_tests"].values()
        if (cell := contrasts.get("b2_over_b1")) is not None
    )

    rendered = render_figures.evidence().render()
    status = state["scientific_bundle"]["eligibility"]["status"]
    assert status in rendered
    assert f"{flow_clears} option-flow tests cleared their own bar." in rendered
    assert "amber cell" not in rendered.casefold()
    assert (REPO / "docs" / "figures" / "evidence.svg").read_text(
        encoding="utf-8"
    ) == rendered + "\n"
