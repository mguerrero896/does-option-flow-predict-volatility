"""The block 7 narrative, and the INDEX row that advertises it, must match a real run.

`docs/rp2/block7_dml_v1.md` was written for the 2026-08-19 cascade and kept its figures
after the panel was rebuilt. Nothing recomputed them, so the page went on asserting a
joint test, a treatment table and a sign that the current run contradicts, and
`docs/INDEX.md` went on advertising it as "the positive finding" with a p-value and a
cross-universe replication that no current artifact carries.

This reads the run id out of the document, opens that run's DML artifact, and checks the
figures the document publishes as current against it. Historical figures are allowed to
stay - the project never deletes a superseded result - but they must live outside the
anchored blocks this test reads, which is what makes the supersession visible.

The anchors are HTML comments rather than a heading regex on purpose: a heading can be
renamed by accident, and a parser that then matches nothing would pass vacuously. Every
fixture below asserts its parse is non-empty and of the expected shape before comparing.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Final

import pytest

REPO = Path(__file__).resolve().parents[2]
DOC = REPO / "docs" / "rp2" / "block7_dml_v1.md"
INDEX = REPO / "docs" / "INDEX.md"

JOINT_ANCHOR: Final = "BLOCK7_CURRENT_JOINT"
TREATMENT_ANCHOR: Final = "BLOCK7_CURRENT_TREATMENTS"

#: How the document spells each outcome, and the key it carries in the artifact.
OUTCOME_KEY: Final = {
    "log RV30": "log_rv30",
    "log jump30": "log_jump30",
    "delta log RV30": "delta_log_rv30",
}

#: Wald and theta are published to enough digits that a relative tolerance this tight
#: still passes on rounding alone; it is far too tight to absorb a stale figure.
REL_TOLERANCE: Final = 1e-3
T_TOLERANCE: Final = 6e-4

INDEX_ROW_PREFIX: Final = "| [`docs/rp2/block7_dml_v1.md`](rp2/block7_dml_v1.md)"


def _number(text: str) -> float:
    return float(text.replace("−", "-").replace("+", "").replace(",", "").strip())


def _between_anchors(document: str, name: str) -> list[str]:
    start = f"<!-- {name}_START -->"
    end = f"<!-- {name}_END -->"
    assert start in document and end in document, (
        f"the document no longer carries the {name} anchors, so nothing here is checked"
    )
    body = document.split(start, 1)[1].split(end, 1)[0]
    return [line for line in body.splitlines() if line.strip().startswith("|")]


def _index_row() -> str:
    rows = [
        line
        for line in INDEX.read_text(encoding="utf-8").splitlines()
        if line.startswith(INDEX_ROW_PREFIX)
    ]
    assert len(rows) == 1, f"expected exactly one INDEX row for block 7, found {len(rows)}"
    return rows[0]


@pytest.fixture(scope="module")
def document() -> str:
    if not DOC.is_file():
        pytest.fail(f"the block 7 narrative is missing: {DOC}")
    return DOC.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def run_id(document: str) -> str:
    match = re.search(r"Measured on `(rp2-v3-[\w-]+)`", document)
    assert match, "the block 7 narrative does not state the run its current figures come from"
    return match.group(1)


@pytest.fixture(scope="module")
def dml(run_id: str) -> dict:
    path = REPO / "artifacts" / "rp2_v3" / run_id / "rp2_block7_dml" / "dml.json"
    if not path.is_file():
        pytest.skip(f"run {run_id} is not present in this checkout: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def joint_rows(document: str) -> list[tuple[str, str, str, float, float, float, float]]:
    rows: list[tuple[str, str, str, float, float, float, float]] = []
    for line in _between_anchors(document, JOINT_ANCHOR):
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if len(cells) != 7:
            continue
        if cells[0] == "Design" or set(cells[0]) <= {"-", ":"}:
            continue
        design, universe, outcome, origins, clusters, wald, p_value = cells
        rows.append(
            (
                design.strip("`"),
                universe,
                outcome.strip("`"),
                _number(origins),
                _number(clusters),
                _number(wald),
                _number(p_value),
            )
        )
    assert len(rows) == 12, (
        f"expected two designs x two universes x three outcomes = 12 rows, parsed {len(rows)}; "
        "a parser that drops rows makes this test pass vacuously"
    )
    return rows


@pytest.fixture(scope="module")
def treatment_rows(document: str) -> list[tuple[str, float, float, float, float, float, float]]:
    cell = r"(?P<{0}>[-+][\d.e-]+)\s*\(t\s*=\s*(?P<{1}>[-+][\d.]+),\s*p\s*=\s*(?P<{2}>[\d.e-]+)\)"
    pattern = re.compile(
        r"^\|\s*`(?P<name>b2_\w+)`\s*\|\s*"
        + cell.format("td", "ttd", "pd")
        + r"\s*\|\s*"
        + cell.format("tv", "ttv", "pv")
        + r"\s*\|$"
    )
    rows: list[tuple[str, float, float, float, float, float, float]] = []
    for line in _between_anchors(document, TREATMENT_ANCHOR):
        match = pattern.match(line.strip())
        if match is None:
            if re.match(r"^\|\s*`b2_", line.strip()):
                pytest.fail(f"a treatment row the parser could not read: {line.strip()!r}")
            continue
        rows.append(
            (
                match["name"],
                _number(match["td"]),
                _number(match["ttd"]),
                _number(match["pd"]),
                _number(match["tv"]),
                _number(match["ttv"]),
                _number(match["pv"]),
            )
        )
    assert len(rows) == 10, f"expected the ten core treatments, parsed {len(rows)}"
    return rows


def test_every_joint_test_matches_the_run(joint_rows, dml) -> None:
    wrong: list[str] = []
    for design, universe, outcome, origins, clusters, wald, p_value in joint_rows:
        block = dml.get(f"{design}_{universe}")
        if block is None:
            wrong.append(f"{design}_{universe}: the run has no such design")
            continue
        key = OUTCOME_KEY[outcome]
        measured = block[key]
        for field, published, value in (
            ("origins", origins, measured["rows"]),
            ("clusters", clusters, measured["clusters"]),
            ("wald", wald, measured["joint_wald"]),
            ("p", p_value, measured["joint_p_value"]),
        ):
            if not math.isclose(published, value, rel_tol=REL_TOLERANCE):
                wrong.append(
                    f"{design}_{universe}/{key}.{field}: doc {published} vs run {value}"
                )
    assert not wrong, "the block 7 narrative disagrees with its own run:\n  " + "\n  ".join(wrong)


def test_every_treatment_matches_the_run(treatment_rows, dml) -> None:
    core = dml["core_treatments"]
    published_names = [row[0] for row in treatment_rows]
    assert sorted(published_names) == sorted(core), (
        f"the treatment table lists {published_names}, the run fitted {core}"
    )
    wrong: list[str] = []
    for name, theta_d, t_d, p_d, theta_v, t_v, p_v in treatment_rows:
        for universe, theta, t_stat, p_value in (
            ("D", theta_d, t_d, p_d),
            ("V", theta_v, t_v, p_v),
        ):
            measured = dml[f"core_{universe}"]["log_rv30"]["coefficients"][name]
            if not math.isclose(theta, measured["theta"], rel_tol=REL_TOLERANCE):
                wrong.append(f"{name}/{universe}.theta: doc {theta} vs run {measured['theta']}")
            if abs(t_stat - measured["t"]) > T_TOLERANCE:
                wrong.append(f"{name}/{universe}.t: doc {t_stat} vs run {measured['t']}")
            if not math.isclose(p_value, measured["p"], rel_tol=5e-3):
                wrong.append(f"{name}/{universe}.p: doc {p_value} vs run {measured['p']}")
    assert not wrong, "a published treatment no longer matches the run:\n  " + "\n  ".join(wrong)


def test_the_index_row_states_only_p_values_the_run_carries(dml, run_id) -> None:
    """`docs/INDEX.md` advertises this block. Whatever p it quotes must be in the run."""
    row = _index_row()
    available = {
        block[outcome]["joint_p_value"]
        for name, block in dml.items()
        if isinstance(block, dict) and name.split("_")[0] in {"core", "full"}
        for outcome in OUTCOME_KEY.values()
        if outcome in block
    }
    quoted = [_number(text) for text in re.findall(r"p\s*=\s*([\d.]+e?-?\d*)", row)]
    assert quoted, "the INDEX row for block 7 quotes no p-value at all"
    orphans = [
        value
        for value in quoted
        if not any(math.isclose(value, known, rel_tol=REL_TOLERANCE) for known in available)
    ]
    assert not orphans, (
        f"the INDEX row quotes {orphans}, which run {run_id} does not carry; "
        f"its joint p-values are {sorted(available)}"
    )


def test_no_replication_is_claimed_unless_a_treatment_replicates(dml) -> None:
    """A treatment "replicates across universes" only if it clears 0.05 in both, same sign."""
    validation = dml["core_V"]["log_rv30"]["coefficients"]
    replicating = [
        name
        for name, discovery in dml["core_D"]["log_rv30"]["coefficients"].items()
        if discovery["p"] < 0.05
        and name in validation
        and validation[name]["p"] < 0.05
        and math.copysign(1.0, discovery["theta"]) == math.copysign(1.0, validation[name]["theta"])
    ]
    row = _index_row()
    claimed = re.search(r"(?<!no )replicates? across universes", row) is not None
    assert not (claimed and not replicating), (
        "docs/INDEX.md claims a cross-universe replication, but no core treatment clears "
        "0.05 in both universes with the same sign in the run the narrative names"
    )
