"""The cumulative-loss figure is regenerated from a public aggregate, not a local run."""

from __future__ import annotations

import itertools
import json
import math
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
SERIES = REPO / "artifacts/rp2_v3/cumulative_loss_session_series_v1.json"
FIGURE = REPO / "docs/figures/cumulative-loss-difference.svg"
RENDERER = REPO / "scripts/render_cumulative_loss_figure.py"

EXPECTED = {
    "D": {
        "gamma_glm": (156, 0.0007631421427452478, 0.019108831561461207, 0.000007749581391977567),
        "ridge_log": (156, 0.0008399734583116126, 0.044091803448265396, -0.014123798147764668),
        "lightgbm_qlike": (156, 0.000887242132839889, 0.08120957903900833, 0.07081209218164627),
    },
    "V": {
        "gamma_glm": (32, 0.004373582424938237, -0.08432751882547587, -0.037331836809825374),
        "ridge_log": (32, 0.0053304815648397485, -0.08010403032978657, -0.024085183645071118),
        "lightgbm_qlike": (32, 0.00908004487686229, 0.06333015264781783, -0.05460551328974103),
    },
}

TOP_DATES = {
    "D": {
        "gamma_glm": ["2026-01-21", "2025-09-19", "2025-11-20"],
        "ridge_log": ["2026-03-16", "2026-03-19", "2026-01-21"],
        "lightgbm_qlike": ["2025-09-17", "2026-01-21", "2025-10-28"],
    },
    "V": {
        family: ["2026-06-05", "2026-06-08", "2026-06-11"]
        for family in ("gamma_glm", "ridge_log", "lightgbm_qlike")
    },
}


def _payload() -> dict[str, object]:
    return json.loads(SERIES.read_text(encoding="utf-8"))


def test_public_series_closes_the_figure_governance_and_scientific_contract() -> None:
    payload = _payload()
    relative = SERIES.relative_to(REPO).as_posix()
    registry = json.loads(
        (REPO / "data/FROZEN_ARTIFACTS.json").read_text(encoding="utf-8")
    )
    canonical = json.loads(
        (REPO / "data/CANONICAL_STATE.json").read_text(encoding="utf-8")
    )
    assert relative in {entry["path"] for entry in registry["entries"]}
    assert relative in canonical["authorized_sources"]
    assert payload["schema_version"] == "rp2-cumulative-loss-session-series-v1.0"
    assert payload["source"]["published_nested_estimates_compared"] == 12
    assert payload["source"]["maximum_absolute_estimate_difference"] == 0.0
    assert payload["source"]["maximum_series_mean_difference"] == pytest.approx(
        4.336808689942018e-19
    )

    final_ratios: list[float] = []
    roles = payload["roles"]
    for role, expected_models in EXPECTED.items():
        models = roles[role]["models"]
        dates = roles[role]["session_dates"]
        assert len(dates) == roles[role]["sessions"]
        for family, (sessions, mde, endpoint, counterfactual_endpoint) in expected_models.items():
            model = models[family]
            deltas = [float(value) for value in model["delta_loss"]]
            assert len(deltas) == sessions == roles[role]["sessions"]
            assert not ({"loss_without_flow", "loss_with_flow", "origins"} & set(model))

            cumulative = list(itertools.accumulate(deltas))
            assert sum(deltas) / sessions == pytest.approx(model["estimate"], abs=1e-15)
            assert float(model["mde_per_session"]) == pytest.approx(mde)
            assert cumulative[-1] == pytest.approx(endpoint)

            ranked = sorted(range(sessions), key=lambda index: abs(deltas[index]), reverse=True)[:3]
            assert [dates[index] for index in ranked] == TOP_DATES[role][family]
            counterfactual = sum(value for index, value in enumerate(deltas) if index not in ranked)
            assert counterfactual == pytest.approx(counterfactual_endpoint)

            bound = mde * sessions
            final_ratios.append(abs(endpoint) / bound)
            assert abs(endpoint) < bound
            # The full-window threshold is not a prefix-specific sequential test. The
            # observed paths cross its linear visual extension early, so the figure must
            # not claim that they remain inside it at every point.
            assert max(abs(value) / (mde * index) for index, value in enumerate(cumulative, 1)) > 1

    assert round(max(final_ratios), 2) == 0.60
    assert EXPECTED["D"]["ridge_log"][2] * EXPECTED["D"]["ridge_log"][3] < 0
    assert EXPECTED["V"]["lightgbm_qlike"][2] * EXPECTED["V"]["lightgbm_qlike"][3] < 0


def test_renderer_reproduces_the_committed_bytes_and_visible_contract(tmp_path: Path) -> None:
    regenerated = tmp_path / FIGURE.name
    subprocess.run(
        [
            sys.executable,
            str(RENDERER),
            "--series-source",
            str(SERIES),
            "--output",
            str(regenerated),
        ],
        cwd=REPO,
        check=True,
    )
    assert regenerated.read_bytes() == FIGURE.read_bytes()

    svg = regenerated.read_text(encoding="utf-8")
    root = ET.fromstring(svg)
    panels = {
        node.attrib["data-panel"]: node
        for node in root.iter()
        if "data-panel" in node.attrib
    }
    assert set(panels) == {"model-development", "held-out-check"}
    densities = {
        float(node.attrib["data-plot-width"]) / int(node.attrib["data-session-count"])
        for node in panels.values()
    }
    assert len(densities) == 1
    assert sum("data-boundary" in node.attrib for node in root.iter()) == 12
    assert sum("data-counterfactual" in node.attrib for node in root.iter()) == 6
    assert sum(node.attrib.get("data-axis-tick") == "zero" for node in root.iter()) == 1

    lowered = svg.lower()
    for forbidden in (
        "b0",
        "b1",
        "b2",
        "mde",
        "qlike",
        "had helped up to that date",
        "stopped working",
        "ceased working",
        "decay",
        "decaimiento",
        "distinguishable at every point",
    ):
        assert forbidden not in lowered
    assert "model development" in lowered
    assert "held-out check" in lowered
    assert "below 61%" in lowered
    assert math.isclose(next(iter(densities)), 4.0)
