"""The front page's answer must survive a count against the primary artifact.

On 2026-08-31 the README said four independent tests agreed that option flow produces
"no incremental contribution above the minimum detectable effect each test declared for
itself". The repository's own primary artifact falsifies that in one of twelve cells:
`lightgbm_qlike` D ΔB2|B1 estimates +0.00060 against a declared MDE of 0.00056, with a
95 % interval excluding zero. That cell is the reason `docs/rp3/PREREGISTRATION.md`
exists — the thesis calls it the one question it leaves open — and the front page did not
mention it.

The sentence was checkable and nothing checked it. This contract counts the cells that
clear their own MDE, splits them into state and flow, and requires the README to state
the count and to name the flow exception whenever one exists. A future run that removes
the exception fails this test too, which is correct: the claim would have changed and the
page would need to say so.
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


def test_the_readme_names_the_flow_exception_and_its_sealed_programme() -> None:
    clearing = _cells_clearing_their_mde()
    if not clearing["flow"]:
        pytest.skip("no flow contrast clears its MDE in the current bundle")

    readme = README.read_text(encoding="utf-8")
    artifact = _inference_artifact()
    universe, family, key = clearing["flow"][0].split()
    cell = artifact[universe]["nested_tests"][family][key]

    estimate = f"{cell['estimate']:+.5f}"
    assert estimate in readme, (
        f"the flow contrast that clears its MDE estimates {estimate}; README.md does not "
        "state it, so a reader cannot see the exception the sealed programme exists for."
    )
    assert "docs/rp3/PREREGISTRATION.md" in readme, (
        "README.md states the exception without routing to the sealed programme that "
        "settles it."
    )


def test_the_stated_mde_for_that_cell_is_the_artifacts() -> None:
    clearing = _cells_clearing_their_mde()
    if not clearing["flow"]:
        pytest.skip("no flow contrast clears its MDE in the current bundle")

    artifact = _inference_artifact()
    universe, family, key = clearing["flow"][0].split()
    mde = artifact[universe]["nested_tests"][family][key]["mde"]
    readme = README.read_text(encoding="utf-8")

    assert f"{mde:.5f}" in readme, (
        "README.md compares the exception against a threshold it does not take from the "
        f"artifact; the declared MDE is {mde:.5f}."
    )
