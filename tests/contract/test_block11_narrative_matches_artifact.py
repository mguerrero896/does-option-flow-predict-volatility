"""The block 11 risk-utility table must be the artifact it cites.

Section 3 published twelve tracking errors and breach rates that appear in no artifact in
the repository. Every one disagreed with `artifacts/rp2_block11_economics/economics.json`,
the file the document pins by hash in its own header, and the prose built on them
overstated the block's only positive residue roughly threefold — "tracking error falls
15 %" against an actual 4.8 % — and reported the validation VaR arms as poorly calibrated
when five of six sit below the nominal rate.

Section 2 of the same document reproduced its artifact exactly, so this was not a stale
page: one table had drifted and nothing was watching it. `README.md` cites this document
as the record for the economic instrument, so a reader who followed the front page to
check the economic test met numbers that no evidence supports.

The anchors are HTML comments, matching `test_block7_narrative_matches_artifact`. A
heading regex can be defeated by renaming a heading, and a parser that then matches
nothing passes vacuously; the fixtures below assert their parse is non-empty and of the
expected shape before comparing anything.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Final

import pytest

REPO = Path(__file__).resolve().parents[2]
DOC = REPO / "docs" / "rp2" / "block11_economics_v1.md"
ARTIFACT = REPO / "artifacts" / "rp2_block11_economics" / "economics.json"

ANCHOR: Final = "BLOCK11_CURRENT_RISK_UTILITY"

#: How the table spells each model, and the key it carries in the artifact.
MODEL_KEY: Final = {"log-OLS": "log_ols", "Gamma": "gamma_glm", "LightGBM": "lightgbm"}

ARMS: Final = ("B0", "B0+B1+B2")

#: The table publishes four decimal places, so equality after rounding is exact. A stale
#: figure differs in the first or second, far outside this.
PLACES: Final = 4

ROW = re.compile(
    r"\|\s*(?P<universe>[DV])\s*\|\s*(?P<model>[\w-]+)\s+B0\s*&rarr;\s*B0\+B1\+B2\s*\|"
    r"\s*(?P<te0>[\d.]+)\s*&rarr;\s*(?P<te1>[\d.]+)\s*\|"
    r"\s*(?P<change>[+-][\d.]+)\s*%\s*\|"
    r"\s*(?P<var0>[\d.]+)\s*&rarr;\s*(?P<var1>[\d.]+)\s*\|"
)


@pytest.fixture(scope="module")
def artifact() -> dict:
    return json.loads(ARTIFACT.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def published_rows() -> list[re.Match[str]]:
    text = DOC.read_text(encoding="utf-8")
    block = re.search(f"<!-- {ANCHOR} -->(.*?)<!-- /{ANCHOR} -->", text, re.DOTALL)
    assert block, f"{DOC.name} has no {ANCHOR} block; the parser would pass vacuously"
    rows = list(ROW.finditer(block.group(1)))
    assert len(rows) == 6, f"expected 6 published rows inside {ANCHOR}, parsed {len(rows)}"
    return rows


def test_the_document_pins_the_artifact_it_is_checked_against(artifact: dict) -> None:
    """A document checked against the wrong artifact proves nothing."""
    pinned = artifact.get("economics_sha256")
    assert pinned, "the artifact carries no embedded economics_sha256 to pin"
    assert pinned in DOC.read_text(encoding="utf-8"), (
        f"{DOC.name} does not cite {pinned[:16]}..., so this contract would be comparing "
        "the document against an artifact it never claimed."
    )


def test_every_published_risk_utility_figure_matches_the_artifact(
    artifact: dict, published_rows: list[re.Match[str]]
) -> None:
    mismatches = []
    for row in published_rows:
        universe = row["universe"]
        model = MODEL_KEY[row["model"]]
        recorded = artifact[universe]["models"][model]
        for arm, published_te, published_var in (
            (ARMS[0], row["te0"], row["var0"]),
            (ARMS[1], row["te1"], row["var1"]),
        ):
            utility = recorded[arm]["risk_utility"]
            for field, published in (
                ("target_volatility_tracking_error", published_te),
                ("var_breach_rate", published_var),
            ):
                expected = round(utility[field], PLACES)
                if abs(float(published) - expected) >= 10**-PLACES:
                    mismatches.append(
                        f"{universe} {row['model']} {arm} {field}: "
                        f"document {published}, artifact {expected}"
                    )
    assert not mismatches, (
        "published risk-utility figures disagree with the artifact:\n" + "\n".join(mismatches)
    )


def test_the_published_change_column_follows_from_the_published_figures(
    published_rows: list[re.Match[str]],
) -> None:
    """The percentage is the reader's summary; a wrong one is what overstated the residue."""
    wrong = []
    for row in published_rows:
        before, after = float(row["te0"]), float(row["te1"])
        expected = 100.0 * (after - before) / before
        if abs(float(row["change"]) - expected) > 0.05:
            wrong.append(
                f"{row['universe']} {row['model']}: states {row['change']} %, "
                f"figures give {expected:+.1f} %"
            )
    assert not wrong, "the change column does not follow from its own row:\n" + "\n".join(wrong)


def test_the_evaluated_row_counts_are_the_artifacts(artifact: dict) -> None:
    """The section that frames the evaluation cited counts from a different run."""
    text = DOC.read_text(encoding="utf-8")
    for universe in ("D", "V"):
        count = f"{artifact[universe]['evaluated_rows']:,}"
        assert count in text, (
            f"{DOC.name} does not state the artifact's {universe} evaluated_rows ({count})"
        )
