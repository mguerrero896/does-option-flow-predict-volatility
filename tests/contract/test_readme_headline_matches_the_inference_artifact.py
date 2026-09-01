"""The front page's answer must remain bound to the canonical inference artifact.

The README once kept an illustrative flow estimate, interval, MDE and sign summary after
their source run had been superseded. The numeric checks skipped whenever no flow cell
cleared its MDE, so that stale prose passed. This contract always checks the largest
discovery-flow illustration, its interval and MDE, the validation sign summary, and the
count of cells clearing their registered thresholds.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Final

import pytest

REPO = Path(__file__).resolve().parents[2]
README = REPO / "README.md"
STATE = REPO / "data" / "CANONICAL_STATE.json"

#: Nested-test keys, and whether each isolates the state layer or the flow layer.
LAYER: Final = {"b1_over_b0": "state", "b2_over_b1": "flow"}

SPELLED: Final = {1: "one", 2: "two", 3: "three", 4: "four", 5: "five"}

#: The count must be stated about the thing it counts, not merely appear on the page.
NEAR_THRESHOLD: Final = r"[^.]{0,120}(threshold|minimum detectable effect)"


def _inference_artifact() -> dict[str, Any]:
    """Follow the canonical state to the bundle rather than hardcoding a run id."""
    state = json.loads(STATE.read_text(encoding="utf-8"))
    run_id = state["scientific_bundle"]["run_id"]
    path = REPO / "artifacts" / "rp2_v3" / run_id / "rp2_block10_inference" / "inference.json"
    if not path.is_file():
        pytest.skip(f"inference artifact for {run_id} is not in this checkout")
    artifact: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return artifact


def _cells_clearing_their_mde() -> dict[str, list[str]]:
    artifact = _inference_artifact()
    clearing: dict[str, list[str]] = {"state": [], "flow": []}
    total = 0
    for universe in ("D", "V"):
        for family, contrasts in artifact[universe]["nested_tests"].items():
            for key, layer in LAYER.items():
                if key not in contrasts:
                    continue
                total += 1
                cell = contrasts[key]
                if abs(cell["estimate"]) > cell["mde"]:
                    clearing[layer].append(f"{universe} {family} {key}")
    assert total == 12, f"expected twelve headline contrasts, counted {total}"
    return clearing


def test_the_readme_states_the_number_of_contrasts_that_clear_their_mde() -> None:
    clearing = _cells_clearing_their_mde()
    count = len(clearing["state"]) + len(clearing["flow"])
    readme = README.read_text(encoding="utf-8")

    # Match the statement, not one wording of it. The page may say "three of the twelve
    # beat their own threshold" or "the three contrasts that clear their own minimum
    # detectable effect". Only the count, and what it counts, are load-bearing.
    stated = re.search(SPELLED[count] + NEAR_THRESHOLD, readme, re.IGNORECASE)
    assert stated, (
        f"{count} of twelve contrasts exceed their own MDE "
        f"({', '.join(clearing['state'] + clearing['flow'])}), and README.md does not say so."
    )


def test_the_readme_does_not_claim_a_clean_sweep_while_a_flow_cell_clears_its_mde() -> None:
    """The specific sentence that was wrong, stated as a property rather than a string."""
    clearing = _cells_clearing_their_mde()
    readme = README.read_text(encoding="utf-8")

    unanimity = re.search(r"all four (?:agree|instruments agree)", readme, re.IGNORECASE)
    assert not (clearing["flow"] and unanimity), (
        "README.md claims the instruments agree on a flow null while these flow contrasts "
        "clear their own MDE: " + ", ".join(clearing["flow"])
    )


def _largest_discovery_flow_cell() -> tuple[str, dict[str, Any]]:
    nested_tests = _inference_artifact()["D"]["nested_tests"]
    family, contrasts = max(
        nested_tests.items(), key=lambda item: abs(item[1]["b2_over_b1"]["estimate"])
    )
    return family, contrasts["b2_over_b1"]


def test_the_readme_names_the_largest_discovery_flow_estimate_and_sealed_programme() -> None:
    readme = README.read_text(encoding="utf-8")
    family, cell = _largest_discovery_flow_cell()

    estimate = f"{cell['estimate']:+.5f}"
    assert estimate in readme, (
        f"the largest discovery flow estimate is {estimate} for {family}; README.md does "
        "not take its illustrative flow estimate from the canonical artifact."
    )
    interval = f"[{cell['ci_low']:+.5f}, {cell['ci_high']:+.5f}]"
    assert interval in readme, (
        f"the {family} discovery flow interval is {interval}; README.md does not take "
        "its illustrative interval from the canonical artifact."
    )
    assert f"{interval} contains zero" in readme, (
        f"the {family} discovery flow interval contains zero, but README.md does not say so."
    )
    assert "docs/rp3/PREREGISTRATION.md" in readme, (
        "README.md states the exception without routing to the sealed programme that settles it."
    )


def test_the_stated_mde_for_the_largest_discovery_flow_cell_comes_from_the_artifact() -> None:
    family, cell = _largest_discovery_flow_cell()
    readme = README.read_text(encoding="utf-8")

    assert f"{cell['mde']:.5f}" in readme, (
        f"README.md compares the {family} flow estimate against a threshold it does not "
        f"take from the canonical artifact; the declared MDE is {cell['mde']:.5f}."
    )


def test_the_readme_states_that_validation_flow_estimates_have_mixed_signs() -> None:
    cells = [
        contrasts["b2_over_b1"] for contrasts in _inference_artifact()["V"]["nested_tests"].values()
    ]
    assert any(cell["estimate"] > 0 for cell in cells)
    assert any(cell["estimate"] < 0 for cell in cells)
    readme = README.read_text(encoding="utf-8")
    assert "validation flow estimates have mixed signs" in readme.lower()
