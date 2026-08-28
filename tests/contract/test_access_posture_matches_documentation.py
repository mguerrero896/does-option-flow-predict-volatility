"""The published access policy has to say what the database does.

`data/DATA_ACCESS.md` is the page an examiner or a data provider reads to learn who can
reach what. Until 2026-08-24 it stated, in bold, that every table had "Row Level Security
enabled with **no policies**: anonymous and authenticated keys read nothing; access is
service-role only". Measured against the live REST endpoint
with the anonymous key, six aggregate tables and eight SECURITY DEFINER views were readable,
four of the views publishing rows from tables that deny anon at the table level.

Nothing licensed leaked and nothing is writable, so the damage was to veracity rather than
to the data. But a false statement in the document that governs access is the same failure
shape this repository already codified against: a rule that lives only in prose is a rule
nobody checks.

The split here is deliberate. This contract is hermetic and always runs: it compares the
prose with `data/access_posture.json`, the machine-readable record of what was measured. The
measurement itself needs a network and a key, so it lives in `scripts/verify_access_posture.py`
and runs where those exist. Neither half skips: the half that cannot run everywhere is not a
test, and the half that is a test needs nothing but the repository.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Final

REPO: Final = Path(__file__).resolve().parents[2]
POSTURE: Final = REPO / "data" / "access_posture.json"
POLICY_PAGE: Final = REPO / "data" / "DATA_ACCESS.md"
#: The six licensed-derived dataset tables. These must be closed, whatever else changes.
LICENSED_TABLES: Final = frozenset(
    {
        "dev_training_all_origins",
        "dev_training_common",
        "c1_development_forecasts",
        "c5_frozen_evaluation_forecasts",
        "b1v3_features",
        "b2_mechanism_forecasts",
    }
)

#: Sentences that were false when they were written. Any of them reappearing means the page
#: has drifted back to describing a posture the database does not have.
RETIRED_CLAIMS: Final = (
    "anonymous and\nauthenticated keys read nothing",
    "anonymous and authenticated keys read nothing",
    "same RLS-locked posture as the catalog — service-role only, never public",
)


def _posture() -> dict:
    assert POSTURE.is_file(), f"ACCESS_POSTURE_MISSING: {POSTURE}"
    return json.loads(POSTURE.read_text(encoding="utf-8"))


def test_the_posture_file_declares_both_sides() -> None:
    """A record that lists only what is open, or only what is closed, is half a record."""

    posture = _posture()
    assert posture["schema_version"] == "mds650-access-posture-v1.1"
    open_tables = set(posture["anon_readable_tables"]["tables"])
    closed_tables = set(posture["closed_tables"]["tables"])
    assert open_tables, "the posture declares nothing readable, which contradicts its purpose"
    assert closed_tables, "the posture declares nothing closed"
    overlap = open_tables & closed_tables
    assert not overlap, f"a table cannot be both open and closed: {sorted(overlap)}"


def test_current_result_views_are_declared_closed() -> None:
    posture = _posture()
    assert set(posture["closed_views"]["views"]) == {
        "current_rp2_block_results",
        "current_rp2_contrasts",
        "current_rp2_extension_results",
        "current_rp2_power_results",
    }
    assert not set(posture["closed_views"]["views"]) & set(
        posture["anon_readable_views"]["views"]
    )


def test_every_licensed_dataset_is_declared_closed() -> None:
    """The one invariant that is not a matter of taste."""

    posture = _posture()
    closed = set(posture["closed_tables"]["tables"])
    exposed = sorted(LICENSED_TABLES - closed)
    assert not exposed, (
        f"licensed-derived table(s) not declared closed: {exposed}. If the database really "
        f"opened them, that is an incident, not a documentation update."
    )
    also_open = sorted(LICENSED_TABLES & set(posture["anon_readable_tables"]["tables"]))
    assert not also_open, f"licensed-derived table(s) declared anon-readable: {also_open}"


def test_the_policy_page_names_every_table_it_leaves_open() -> None:
    """A reader must be able to learn from the page itself what anyone can read."""

    page = POLICY_PAGE.read_text(encoding="utf-8")
    missing = [
        table
        for table in _posture()["anon_readable_tables"]["tables"]
        if table not in page
    ]
    assert not missing, (
        f"{POLICY_PAGE.name} does not name anon-readable table(s) {missing}; the page would "
        f"leave a reader believing they are closed."
    )


def test_closed_current_views_are_documented() -> None:
    """Closing only the base tables would leave the API view route ambiguous."""

    page = POLICY_PAGE.read_text(encoding="utf-8")
    assert "Closed versioned results" in page
    assert "api.current_rp2_*" in page


def test_the_retired_claims_do_not_come_back() -> None:
    """The specific sentences that were false, pinned by their text.

    Pinned rather than paraphrased because the defect was not a wrong nuance: it was a
    concrete sentence, in bold, that a provider or an examiner would have relied on.
    """

    for path in _documents_to_check():
        text = path.read_text(encoding="utf-8")
        for claim in RETIRED_CLAIMS:
            assert claim not in text, (
                f"{path.name} states again a claim measured false on 2026-08-24: "
                f"{claim!r}. Re-measure with scripts/verify_access_posture.py before "
                f"describing the posture."
            )


def _documents_to_check() -> tuple[Path, ...]:
    """Return the public policy documents governed by this contract."""
    return (POLICY_PAGE,)


def test_the_documents_point_at_the_measurement() -> None:
    """Prose that cannot be re-checked is what produced this defect in the first place."""

    for path in _documents_to_check():
        text = path.read_text(encoding="utf-8")
        assert "access_posture.json" in text, (
            f"{path.name} describes the access posture without pointing at the record that "
            f"can be re-measured."
        )


def test_explicit_postgrest_privilege_denial_proves_a_closed_table() -> None:
    script = REPO / "scripts" / "verify_access_posture.py"
    spec = importlib.util.spec_from_file_location("verify_access_posture", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["verify_access_posture"] = module
    spec.loader.exec_module(module)
    assert module._is_explicit_access_denial(401, '{"code":"42501"}')
