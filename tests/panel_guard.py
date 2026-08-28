"""One decision, shared: an absent panel is unverified, not approved.

Four contract checks read the built panels to hold the feature registry to the evidence --
that every registered feature reaches the panel, that no panel column is a feature nobody
registered, and that the core coverage floors hold on real data. All four treated a missing
parquet as a pass, by `pytest.skip` in three places and by a bare `continue` in the fourth,
which does not even leave an `s` in the output.

That was reasonable prose and false in practice. The docstring of
`test_feature_registry_reaches_the_panel.py` says the hermetic runner stays green "while the
local tier-2 run does the real work"; measured on 2026-08-24,
`scripts/run_local_evidence_gates.py` asserts the presence of no panel at all. So the checks
ran nowhere: green in tier 1 because the panel was absent, green in tier 2 because nothing
required it to be present.

The invariant they guard is not decorative. `SPY_rv_30`, `SPY_ret_30`, `QQQ_rv_30` and
`QQQ_ret_30` sat in the B0 panel and were never registered, so every block from 7 onward ran
a market-blind baseline -- and a B2 increment measured against a market-blind baseline
credits option flow with whatever the whole market was doing.

The tier boundary is kept, but it has to be asked for by name. CI sets
``MDS650_PANEL_GUARD_MAY_SKIP=1`` in the jobs that genuinely have no licensed data, so the
skip is a declared decision visible in `ci.yml` rather than an accident of a missing file.
Anywhere else -- a developer's machine, the tier-2 gate runner -- an absent panel fails.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Final

import pytest

REPO: Final = Path(__file__).resolve().parents[1]
#: Content hashes of the panels every RP2 block reads. A path listed here is a panel the
#: programme says should exist, which is what makes its absence a failure to verify rather
#: than a configuration.
POINTERS: Final = REPO / "artifacts" / "rp2_panel_pointers.json"
#: The one deliberate way out. Named, so that skipping is a decision someone wrote down.
OPT_OUT: Final = "MDS650_PANEL_GUARD_MAY_SKIP"


def declared_panels() -> frozenset[str]:
    """The repo-relative panel paths the pointer manifest declares."""

    if not POINTERS.is_file():
        pytest.fail(f"RP2_PANEL_POINTERS_MISSING: {POINTERS}")
    payload = json.loads(POINTERS.read_text(encoding="utf-8"))
    return frozenset(payload.get("panels", {}))


#: Panels under a dated run directory are copies produced BY that run, not registry
#: entries: their digests change per run, so `rp2_panel_pointers.json` records the four
#: canonical block panels and never these. Absence here means "this run's outputs are
#: not on this machine", which is what the opt-out is for.
_RUN_SCOPED_PREFIX = "artifacts/rp2_v3/"


def _is_run_scoped(relative: str) -> bool:
    return relative.startswith(_RUN_SCOPED_PREFIX)


def panel_is_available(label: str, path: Path) -> bool:
    """True when ``path`` can be read; otherwise skip deliberately or fail closed.

    Returns rather than raises so a caller iterating several panels can move on after a
    deliberate skip, which a bare `continue` did silently and this does loudly.
    """

    if path.is_file():
        return True
    relative = path.relative_to(REPO).as_posix()

    # Declaration is checked BEFORE the opt-out, and deliberately so. Until
    # 2026-08-26 the opt-out came first, which meant that under the documented
    # workflow (which sets it) a panel read by a check but registered nowhere
    # could never be reported: the tripwire was unreachable in the only
    # configuration anyone runs. A missing declaration is a defect in the code,
    # not a consequence of absent data, so the flag must not hide it.
    if not _is_run_scoped(relative) and relative not in declared_panels():
        pytest.fail(
            f"RP2_PANEL_NOT_DECLARED: {relative} is read by a contract check but is not in "
            f"{POINTERS.name}, so nothing records that it should exist. Register it, or "
            f"stop reading it here."
        )
    if os.environ.get(OPT_OUT) == "1":
        pytest.skip(f"{label} panel absent; skipped deliberately via {OPT_OUT}=1")
    pytest.fail(
        f"RP2_PANEL_UNVERIFIED: {label} is declared in {POINTERS.name} and is not at "
        f"{relative}, so the registry invariant is UNVERIFIED, not satisfied. Build the "
        f"panels, or set {OPT_OUT}=1 to accept an unverified run deliberately."
    )
    raise AssertionError("unreachable")  # pragma: no cover - pytest.fail does not return
