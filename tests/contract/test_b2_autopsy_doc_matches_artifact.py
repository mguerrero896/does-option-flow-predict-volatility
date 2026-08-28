"""The autopsy document must agree with the artifact it reports.

`docs/rp2/extension_b2_autopsy_v1.md` states six contrasts, a localisation result and two
published reference deltas. Nothing recomputes those figures when the artifact changes, so
a rerun that moves a number leaves the document asserting the old one. This parses every
figure out of the document and checks it against `artifacts/rp2_b2_autopsy/results.json`
— and checks the two reference deltas against the Block 10 inference of the run the
artifact names, because a comparison against a misquoted baseline is not a comparison.

The parse is asserted to yield the expected shape before any comparison runs; a parser
that silently drops rows passes vacuously (the lesson `test_verdict_matches_artifact.py`
records from its own writing).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
DOC = REPO / "docs" / "rp2" / "extension_b2_autopsy_v1.md"
ARTIFACT = REPO / "artifacts" / "rp2_b2_autopsy" / "results.json"

#: The document's index column against the artifact's keys.
INDEX_KEY = {"linear": "linear_index", "tree": "tree_index"}

#: Five-decimal figures round within 5e-6 of the artifact; p-values are printed at four
#: decimals and the Spearman rho at three, so each gets the tolerance of its own rounding.
TOLERANCE = 6e-6
P_TOLERANCE = 6e-5
RHO_TOLERANCE = 6e-4


def _number(text: str) -> float:
    """Parse a stated figure, accepting the document's typographic minus sign."""

    return float(text.replace("−", "-").replace("+", "").strip())


@pytest.fixture(scope="module")
def document() -> str:
    if not DOC.is_file():
        pytest.fail(f"the autopsy document is missing: {DOC}")
    return DOC.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def artifact() -> dict:
    if not ARTIFACT.is_file():
        # Not a skip. The artifact is a small committed JSON, so its absence is not "this
        # checkout is thin" - it is drift between the document and the repository, which
        # is exactly what this contract exists to catch. Skipping would report agreement.
        pytest.fail(
            f"RP3_AUTOPSY_ARTIFACT_MISSING: {ARTIFACT.relative_to(REPO).as_posix()} does "
            "not exist, so every figure in the document is UNVERIFIED. Re-run "
            "scripts/rp2_b2_autopsy_extension.py and commit its output, or fix the path."
        )
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def contrasts(document: str) -> list[tuple[str, str, float, float, float, float, float]]:
    rows: list[tuple[str, str, float, float, float, float, float]] = []
    unparsed: list[tuple[str, int]] = []
    for line in document.splitlines():
        if not line.startswith("| `"):
            continue
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 6:
            unparsed.append((line[:80], len(cells)))
            continue
        family, index, delta, interval, p_value, mde = cells
        low, high = interval.strip("[]").split(",")
        rows.append(
            (
                family.strip("`"),
                index,
                _number(delta),
                _number(low),
                _number(high),
                _number(p_value),
                _number(mde),
            )
        )
    assert not unparsed, f"table rows the parser could not read: {unparsed}"
    assert len(rows) == 6, (
        f"expected the six-contrast table, parsed {len(rows)} rows; a parser that drops "
        "rows makes every comparison below pass vacuously"
    )
    return rows


def test_the_document_names_the_artifact_run_and_label(document: str, artifact: dict) -> None:
    assert artifact["label"] == "EXPLORATORY_DIAGNOSTIC"
    assert artifact["role"] == "D"
    assert "EXPLORATORY_DIAGNOSTIC" in document, "the document dropped its exploratory label"
    assert f"`{artifact['run']}`" in document, (
        f"the document no longer names the run the artifact was measured on ({artifact['run']})"
    )


def test_every_contrast_matches_the_artifact(contrasts, artifact: dict) -> None:
    wrong: list[str] = []
    for family, index, delta, low, high, p_value, mde in contrasts:
        key = INDEX_KEY.get(index)
        if key is None:
            wrong.append(f"{family}/{index}: not an index this test can read")
            continue
        measured = artifact["families"][family][key]
        for field, published, value, tolerance in (
            ("estimate", delta, measured["estimate"], TOLERANCE),
            ("ci_low", low, measured["ci_low"], TOLERANCE),
            ("ci_high", high, measured["ci_high"], TOLERANCE),
            ("wild_cluster_p", p_value, measured["wild_cluster_p_value"], P_TOLERANCE),
            ("mde", mde, measured["mde"], TOLERANCE),
        ):
            if abs(published - value) >= tolerance:
                wrong.append(f"{family}/{index}.{field}: doc {published} vs {value}")
    assert not wrong, "the document disagrees with its artifact:\n  " + "\n  ".join(wrong)


def test_the_localisation_figures_match_the_artifact(document: str, artifact: dict) -> None:
    d3 = artifact["d3_localisation"]
    wrong: list[str] = []

    best = re.search(r"best candidate \(`(\w+)` \+ (\w+) index\)", document)
    assert best, "the document no longer states which candidate D3 ran on"
    if best.group(1) != d3["model_family"] or INDEX_KEY.get(best.group(2)) != d3["index"]:
        wrong.append(
            f"candidate: doc {best.group(1)}+{best.group(2)} vs "
            f"{d3['model_family']}+{d3['index']}"
        )

    rho = re.search(r"Spearman ρ = ([+−\-]?[\d.]+)", document)
    assert rho, "the document no longer states the Spearman correlation"
    if abs(_number(rho.group(1)) - d3["spearman_rho"]) >= RHO_TOLERANCE:
        wrong.append(f"rho: doc {rho.group(1)} vs {d3['spearman_rho']}")

    gains = re.search(
        r"top\s+flow quintile is \*\*([+−\-]?[\d.]+)\*\* against \*\*([+−\-]?[\d.]+)\*\*",
        document,
    )
    assert gains, "the document no longer states the two quintile gains"
    for label, stated, key in (
        ("top_flow_quintile_gain", gains.group(1), "top_flow_quintile_gain"),
        ("remaining_gain", gains.group(2), "remaining_gain"),
    ):
        if abs(_number(stated) - d3[key]) >= TOLERANCE:
            wrong.append(f"{label}: doc {stated} vs {d3[key]}")
    assert not wrong, "the localisation prose disagrees:\n  " + "\n  ".join(wrong)


def test_the_published_reference_deltas_match_block10(document: str, artifact: dict) -> None:
    """The document compares its indices against the published remeasure; the baseline of
    a comparison is as checkable as the comparison, so both quoted deltas are verified
    against the Block 10 inference of the run the artifact names."""

    inference_path = (
        REPO / "artifacts" / "rp2_v3" / artifact["run"] / "rp2_block10_inference"
        / "inference.json"
    )
    if not inference_path.is_file():
        pytest.fail(
            f"RP3_AUTOPSY_BASELINE_MISSING: the artifact was measured on `{artifact['run']}` "
            f"and {inference_path.relative_to(REPO).as_posix()} does not exist, so the "
            "document's reference deltas are UNVERIFIED."
        )
    inference = json.loads(inference_path.read_text(encoding="utf-8"))

    quoted = re.search(
        r"`lightgbm_qlike` ΔB2\|B1 = ([+−\-][\d.]+); `gamma_glm` ([+−\-][\d.]+)",
        document,
    )
    assert quoted, "the document no longer quotes the published remeasure deltas"
    wrong: list[str] = []
    for family, stated in (("lightgbm_qlike", quoted.group(1)), ("gamma_glm", quoted.group(2))):
        value = inference["D"]["nested_tests"][family]["b2_over_b1"]["estimate"]
        if abs(_number(stated) - value) >= TOLERANCE:
            wrong.append(f"{family}: doc {stated} vs {value}")
    assert not wrong, "a quoted reference delta no longer matches:\n  " + "\n  ".join(wrong)
