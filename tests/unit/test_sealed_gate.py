"""Pins for the common sealed-cohort gate (audit 2026-08-25, P0).

The class of mistake being closed: a Supabase-facing script edited to touch a
table or artifact carrying sealed-cohort rows, with nothing structural in the
way. The gate refuses sealed-named targets by default; these tests pin the
refusal, the owner override, and that every Supabase producer actually calls it.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from mds650.sealed import (
    OWNER_ACK_ENV,
    OWNER_ACK_VALUE,
    guard_sealed_access,
    licensed_matches,
    sealed_matches,
)

REPO = Path(__file__).resolve().parents[2]

#: EVERY script that reaches Supabase or the gated bucket. The first version of
#: this list named four and called itself "every Supabase producer"; a review
#: found three more. A roster that is wrong is worse than no roster: it reports
#: coverage it does not have.
GATED_SCRIPTS = (
    "verify_access_posture.py",
    "sync_supabase_rp2_blocks.py",
    "sync_supabase_catalog.py",
    "load_supabase_datasets.py",
    "publish_rp2_v3_supabase.py",
    "upload_gated_data.py",
    "fetch_gated_data.py",
)

#: What the seal covers: the genuinely unobserved evidence. The protocol is explicit
#: that C1-C6 were already observed (DISCOVERY_VALIDATION_CONFIRMATION_PROTOCOL §2),
#: so they belong to licensing, not to the one-read seal.
REAL_SEALED_NAMES = (
    "phase8_cohort",
    "phase8_holdout",
    "phase9_collection",
    "cohort_c",
    "rp3-batch-20260830",
    "artifacts/rp3/eval_panels/rp3_eval_x.parquet",
)

#: Licensed but OBSERVED. These must NOT trip the seal: an earlier version listed
#: them as sealed, which aborted routine retrospective work and taught operators to
#: set the override by habit — the fastest way to render a gate meaningless.
LICENSED_BUT_NOT_SEALED = (
    "c1_development_forecasts",
    "c5_frozen_evaluation_forecasts",
    "dev_training_all_origins",
    "dev_training_common",
    "b1v3_features",
    "b2_mechanism_forecasts",
)

def test_clean_targets_pass_silently() -> None:
    guard_sealed_access(
        ["campaigns", "contrast_results", "artifacts/gate1_inference/results.json"],
        operation="test",
    )


def test_a_sealed_named_target_is_refused_by_default(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv(OWNER_ACK_ENV, raising=False)
    with pytest.raises(SystemExit, match="SEALED_ACCESS_REFUSED.*phase8_cohort_rows"):
        guard_sealed_access(["campaigns", "phase8_cohort_rows"], operation="test")


def test_the_owner_ack_is_the_only_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(OWNER_ACK_ENV, "1")
    with pytest.raises(SystemExit):
        guard_sealed_access(["rp3-batch-20260830/tape"], operation="test")
    monkeypatch.setenv(OWNER_ACK_ENV, OWNER_ACK_VALUE)
    guard_sealed_access(["rp3-batch-20260830/tape"], operation="test")  # no raise


def test_matching_is_case_insensitive_and_substring_based() -> None:
    assert sealed_matches(["Phase8_watch.log", "d/PHASE9/x", "clean"]) == [
        "Phase8_watch.log",
        "d/PHASE9/x",
    ]


def test_every_supabase_producer_calls_the_gate() -> None:
    """The gate only closes the class if every producer actually calls it."""
    for name in GATED_SCRIPTS:
        source = (REPO / "scripts" / name).read_text(encoding="utf-8")
        assert "guard_sealed_access(" in source, f"{name} does not call the sealed gate"
        assert "from mds650.sealed import" in source, f"{name} misses the import"


def test_the_gate_recognises_every_sealed_resource() -> None:
    unseen = [name for name in REAL_SEALED_NAMES if not sealed_matches([name])]
    assert not unseen, f"the seal would wave these through: {unseen}"


def test_licensed_but_observed_data_does_not_trip_the_seal() -> None:
    """Licensing and the one-read seal are different controls with different remedies."""
    tripped = [name for name in LICENSED_BUT_NOT_SEALED if sealed_matches([name])]
    assert not tripped, (
        "observed licensed datasets are being treated as sealed, so routine "
        f"retrospective work would abort: {tripped}"
    )
    assert licensed_matches(list(LICENSED_BUT_NOT_SEALED)) == list(LICENSED_BUT_NOT_SEALED), (
        "licensed datasets must still be identifiable as licensed"
    )


def test_aggregate_tables_are_not_swept_up() -> None:
    assert sealed_matches(["campaigns", "contrast_results", "mcs_cells", "rp2_blocks"]) == []
