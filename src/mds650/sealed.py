"""Default-deny gate for anything that could touch a sealed cohort.

The 2026-08-25 follow-up audit observed that the Supabase-facing scripts
(`verify_access_posture`, `sync_supabase_catalog`, `sync_supabase_rp2_blocks`,
`load_supabase_datasets`) had no COMMON authorization gate: nothing structural
stopped a future edit from pointing one of them at a table or artifact carrying
sealed-cohort rows (C, the Phase 8 cohort, the Phase 9 collection, RP3
evaluation batches). Each script was individually clean; the class of mistake
was open.

This module closes the class. Every such script calls
:func:`guard_sealed_access` over the full list of tables/paths it is about to
touch, before its first byte of I/O. A target whose name matches a sealed hint
is refused unless the owner's acknowledgement is present in the environment —
so today's scripts run exactly as before (none touches a sealed surface), and
the FIRST edit that adds a sealed-named target fails loudly instead of quietly
reading what three years of protocol say must not be read.

RLS-posture note: closure of remote tables is proven by metadata and zero-row
answers under the anon key; nothing here ever needs to SELECT sealed rows to
validate anything, and the gate makes attempting it an error, not a choice.
"""

from __future__ import annotations

import os
from collections.abc import Iterable

#: Substrings that mark a table, view, bucket object or artifact path as part of a
#: sealed surface. Deliberately broad: a false trip costs one env var; a miss costs
#: the one-read seal.
#: Resources under the ONE-READ SEAL. This is a scientific control, not a licensing
#: one, and the distinction cost a review to establish: an earlier version listed the
#: six licensed datasets here, which made routine retrospective work abort. The
#: protocol is explicit that C1 through C6 have already been observed
#: (`docs/DISCOVERY_VALIDATION_CONFIRMATION_PROTOCOL.md` §2); the only genuinely
#: unobserved evidence is the Phase 8 cohort, Phase 9 collection, and the RP3
#: evaluation batches. Licensing is enforced elsewhere — private bucket, RLS, and
#: grants — and conflating the two weakens both.
SEALED_RESOURCES: frozenset[str] = frozenset({
    "phase8_holdout",
    "phase8_cohort",
    "phase9_collection",
    "cohort_c",
})

#: Substrings marking a sealed cohort or batch. Deliberately narrow for the same
#: reason: a gate that fires on ordinary work is a gate that gets switched off.
SEALED_HINTS: tuple[str, ...] = (
    "phase8",
    "phase9",
    "rp3_eval",
    "rp3-batch",
    "cohort_c",
    "holdout",
)

#: Licensed-derived datasets. NOT sealed — they have been observed and are read in
#: routine work — but they never reach a public surface. Named here so a caller can
#: check licensing explicitly rather than by spelling.
LICENSED_RESOURCES: frozenset[str] = frozenset({
    "dev_training_all_origins",
    "dev_training_common",
    "c1_development_forecasts",
    "c5_frozen_evaluation_forecasts",
    "b1v3_features",
    "b2_mechanism_forecasts",
})

OWNER_ACK_ENV = "MDS650_SEALED_OWNER_ACK"
OWNER_ACK_VALUE = "I_AM_THE_OWNER_AND_AUTHORIZE_SEALED_ACCESS"


def _basename(target: str) -> str:
    stem = target.lower().rsplit("/", 1)[-1].rsplit(chr(92), 1)[-1]
    for suffix in (".parquet", ".csv", ".json"):
        stem = stem.removesuffix(suffix)
    return stem


def sealed_matches(targets: Iterable[str]) -> list[str]:
    """Targets naming a SEALED resource — the one-read cohorts, not licensed data."""
    matched = []
    for target in targets:
        lowered = target.lower()
        named = _basename(target) in SEALED_RESOURCES or lowered in SEALED_RESOURCES
        if named or any(hint in lowered for hint in SEALED_HINTS):
            matched.append(target)
    return matched


def licensed_matches(targets: Iterable[str]) -> list[str]:
    """Targets naming a licensed-derived dataset. Observed, so not gated — but never
    publishable. Callers use this to reason about licensing without borrowing the
    seal's vocabulary for it."""
    return [t for t in targets if _basename(t) in LICENSED_RESOURCES]


def guard_sealed_access(targets: Iterable[str], *, operation: str) -> None:
    """Refuse *operation* over any sealed-named target without the owner's ack.

    Raises ``SystemExit`` naming every offending target, so the refusal is
    unmissable in a scheduled task's log and trivially testable.
    """
    offending = sealed_matches(targets)
    if not offending:
        return
    if os.environ.get(OWNER_ACK_ENV) == OWNER_ACK_VALUE:
        return
    raise SystemExit(
        "SEALED_ACCESS_REFUSED: "
        f"{operation} would touch sealed-named target(s) {sorted(offending)}; "
        f"sealed cohorts are read once, by the owner. Set {OWNER_ACK_ENV} to the "
        "documented value only under written authorization. NOTE: this is a brake "
        "against accidental execution, not an access control — the value lives in "
        "the source, so anything able to set an environment variable can pass it. "
        "Access control is the service key and the RLS posture; this gate does not "
        "replace either."
    )
