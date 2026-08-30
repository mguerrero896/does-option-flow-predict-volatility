"""One coverage floor, stated in three places, must be the same number.

`data/CANONICAL_STATE.json` calls itself the machine-readable authority and `STATUS.md`
says it supersedes any narrative that disagrees. On 2026-08-31 both published a floor of
80% while `pyproject.toml` and the CI workflow enforced 90%, because the generator
carried the number as a literal and nobody updated it when the gate moved.

An authority that restates a remembered value is not an authority. The generator now
reads the floor from the same file pytest reads; this contract checks that the workflow
agrees with it too, so the three cannot drift apart again.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]


def _pyproject_floor() -> int:
    config = tomllib.loads((REPO / "pyproject.toml").read_text(encoding="utf-8"))
    return int(config["tool"]["coverage"]["report"]["fail_under"])


def _workflow_floors() -> list[int]:
    workflow = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    return [int(value) for value in re.findall(r"--cov-fail-under=(\d+)", workflow)]


def _canonical_floor() -> int:
    state = json.loads((REPO / "data" / "CANONICAL_STATE.json").read_text(encoding="utf-8"))
    return int(state["ci"]["coverage_min_percent"])


def test_the_workflow_enforces_the_floor_pyproject_declares() -> None:
    declared = _pyproject_floor()
    enforced = _workflow_floors()
    assert enforced, "no --cov-fail-under found in the CI workflow"
    mismatched = [value for value in enforced if value != declared]
    assert not mismatched, (
        f"pyproject declares fail_under = {declared} but the workflow enforces "
        f"{mismatched}. A run can then pass CI and fail locally, or the reverse."
    )


def test_the_canonical_state_publishes_the_floor_actually_enforced() -> None:
    declared = _pyproject_floor()
    published = _canonical_floor()
    assert published == declared, (
        f"data/CANONICAL_STATE.json publishes coverage_min_percent = {published} while "
        f"the enforced floor is {declared}. Regenerate with "
        "`uv run python scripts/generate_canonical_state.py`."
    )


def test_status_projects_the_canonical_floor_verbatim() -> None:
    """STATUS.md is generated; a stale copy means the generator did not run."""
    status = (REPO / "STATUS.md").read_text(encoding="utf-8")
    expected = f"coverage >= {_canonical_floor()}%"
    assert expected in status, (
        f"STATUS.md does not state {expected!r}; it is generated from the canonical "
        "state and has drifted from it."
    )
