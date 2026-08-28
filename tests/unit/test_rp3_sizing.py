"""The committed sizing artifact answers for itself, with no panels required.

Hermetic on purpose: the sizing run needs the gitignored remeasure parquets, but every
claim the artifact makes downstream — the schema, the self-hash, the winner's-curse
arithmetic, the coherence of each measurement's N with its own MDE curve, and the read
date — is checkable from the committed JSON alone.

Two properties carry the program's honesty and are pinned here rather than trusted. Every
listed target's measurement is present whether or not it favours the program: rv_60 was
the exploratory selection, measured negative through the frozen index, and it must stay in
the artifact as the recorded dead end. And the primary is a named choice among recorded
measurements — `primary_target` with a written rationale — not the survivor of a silent
race, so the top-level N_PRIMARY and read date must equal the primary measurement's own,
byte for byte. A declared NOT_ACHIEVABLE is a valid terminal state, accepted exactly when
that measurement's halved effect is not positive.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

from scripts.rp3_sizing import (
    MEASURED_TARGETS,
    NOT_ACHIEVABLE,
    PRIMARY_TARGET,
    WINNER_CURSE_DIVISOR,
    canonical_sha256,
    mde_at_sessions,
    read_date_for,
)

from mds650.rp2.inference import DEFAULT_ALPHA, DEFAULT_POWER

REPO: Final = Path(__file__).resolve().parents[2]
ARTIFACT: Final = REPO / "artifacts" / "rp3" / "sizing.json"
THETA_ARTIFACT: Final = REPO / "artifacts" / "rp3" / "b2_index_theta.json"
RUN_NAME: Final = "rp2-v3-20260824-remeasure"

#: Every field the sizing script writes at the top level. A consumer reads the artifact
#: blind, so a missing field is a broken contract even when the values still verify.
REQUIRED_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "schema",
        "run_id",
        "role",
        "theta_artifact",
        "theta_self_sha256",
        "measurements",
        "primary_target",
        "primary_rationale",
        "winner_curse_divisor",
        "alpha",
        "power",
        "n_primary",
        "session_bank",
        "secondary",
        "self_sha256",
    }
)

#: The evaluation universe each target is allowed to be measured on. rv_30 must be scored
#: on the block-10 universe — the rows the budget-clearing cell was published on — because
#: on the target-panel grid the same contrast reads negative: the grid drops the early and
#: late origins where the index earns its keep, and a primary measured there would be a
#: different experiment wearing the same name.
EXPECTED_UNIVERSE: Final = {
    "rv_30": "block10_common_mask",
    "rv_60": "target_panel_grid",
}


def load_artifact() -> dict[str, object]:
    assert ARTIFACT.is_file(), f"RP3_SIZING_ARTIFACT_MISSING:{ARTIFACT}"
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def measurement(payload: dict[str, object], column: str) -> dict[str, object]:
    measurements = payload["measurements"]
    assert isinstance(measurements, dict)
    measured = measurements[column]
    assert isinstance(measured, dict)
    return measured


def test_artifact_schema_is_complete() -> None:
    payload = load_artifact()
    missing = REQUIRED_FIELDS - set(payload)
    assert not missing, f"missing fields: {sorted(missing)}"
    assert payload["schema"] == "rp3_sizing/2"
    assert payload["run_id"] == RUN_NAME
    assert payload["role"] == "D"
    assert payload["alpha"] == DEFAULT_ALPHA
    assert payload["power"] == DEFAULT_POWER
    assert payload["winner_curse_divisor"] == WINNER_CURSE_DIVISOR
    measurements = payload["measurements"]
    assert isinstance(measurements, dict)
    assert set(measurements) == set(MEASURED_TARGETS)
    for column in MEASURED_TARGETS:
        measured = measurement(payload, column)
        assert measured["target"] == column
        assert measured["model_family"] == "lightgbm_qlike"
        assert measured["base_information_set"] == "B0+B1"
        assert measured["expanded_information_set"] == "B0+B1+b2_index"
        assert measured["evaluation_universe"] == EXPECTED_UNIVERSE[column]
        observed = measured["observed"]
        assert isinstance(observed, dict)
        for field in (
            "estimate",
            "ci_low",
            "ci_high",
            "wild_cluster_p_value",
            "mde",
            "sessions",
        ):
            assert field in observed, f"{column}: observed record missing {field}"


def test_self_hash_verifies() -> None:
    """The canonical payload, minus the hash field, must hash to the hash field."""

    payload = load_artifact()
    assert payload["self_sha256"] == canonical_sha256(payload)


def test_theta_reference_matches_the_committed_theta() -> None:
    """Sizing must cite the same frozen index the primary test will read."""

    payload = load_artifact()
    theta = json.loads(THETA_ARTIFACT.read_text(encoding="utf-8"))
    assert payload["theta_self_sha256"] == theta["self_sha256"]


def test_winner_curse_arithmetic_per_measurement() -> None:
    """target_effect = max(effect/2, 0) for every measurement, favourable or not."""

    payload = load_artifact()
    for column in MEASURED_TARGETS:
        measured = measurement(payload, column)
        observed = measured["observed"]
        assert isinstance(observed, dict)
        effect = observed["estimate"]
        target = measured["target_effect"]
        assert isinstance(effect, float) and isinstance(target, float)
        assert target == max(effect / WINNER_CURSE_DIVISOR, 0.0), column


def test_mde_curves_recompute_and_decrease() -> None:
    """Every curve point is that measurement's long-run variance through the MDE formula."""

    payload = load_artifact()
    for column in MEASURED_TARGETS:
        measured = measurement(payload, column)
        long_run = measured["long_run_variance"]
        assert isinstance(long_run, float) and long_run > 0.0
        curve = measured["mde_curve"]
        assert isinstance(curve, list) and len(curve) >= 10
        previous: float | None = None
        for point in curve:
            assert isinstance(point, dict)
            sessions = point["sessions"]
            mde = point["mde"]
            assert isinstance(sessions, int) and isinstance(mde, float)
            assert abs(mde - mde_at_sessions(long_run, sessions)) < 1e-12, column
            if previous is not None:
                assert mde < previous, f"{column}: MDE must fall as sessions accrue"
            previous = mde


def test_each_n_is_coherent_with_its_curve() -> None:
    """Either the minimal sufficient N, or a declared NOT_ACHIEVABLE — consistently."""

    payload = load_artifact()
    for column in MEASURED_TARGETS:
        measured = measurement(payload, column)
        long_run = measured["long_run_variance"]
        target = measured["target_effect"]
        n_sessions = measured["n_sessions"]
        assert isinstance(long_run, float) and isinstance(target, float)
        if n_sessions == NOT_ACHIEVABLE:
            assert target <= 0.0, f"{column}: a positive target must come with a count"
            assert measured["read_date"] == NOT_ACHIEVABLE
            continue
        assert isinstance(n_sessions, int) and n_sessions >= 3
        assert target > 0.0
        assert mde_at_sessions(long_run, n_sessions) <= target
        if n_sessions > 3:
            assert mde_at_sessions(long_run, n_sessions - 1) > target, (
                f"{column}: N must be minimal"
            )
        assert measured["read_date"] == read_date_for(n_sessions)


def test_the_primary_is_a_named_choice_with_matching_headline() -> None:
    """The top-level N and read date must be the primary measurement's own, verbatim."""

    payload = load_artifact()
    assert payload["primary_target"] == PRIMARY_TARGET == "rv_30"
    rationale = payload["primary_rationale"]
    assert isinstance(rationale, str) and "rv_60" in rationale, (
        "the rationale must name the recorded dead end it supersedes"
    )
    primary = measurement(payload, PRIMARY_TARGET)
    assert payload["n_primary"] == primary["n_sessions"]
    bank = payload["session_bank"]
    assert isinstance(bank, dict)
    assert bank["read_date"] == primary["read_date"]


def test_session_bank_declares_its_assumptions() -> None:
    payload = load_artifact()
    bank = payload["session_bank"]
    assert isinstance(bank, dict)
    assert bank["window_opens"] == "2026-07-18"
    assert bank["sessions_per_month_nominal"] == 21
    calendar = bank["calendar"]
    assert isinstance(calendar, str) and "business days" in calendar


def test_secondary_is_a_citation_not_a_measurement() -> None:
    """Direction-120 sizing is the frozen power artifact times four, and says so."""

    payload = load_artifact()
    secondary = payload["secondary"]
    assert isinstance(secondary, dict)
    assert secondary["test"] == "direction_120"
    assert secondary["cited_artifact"] == "artifacts/rp2_ext4_power/power.json"
    cited = secondary["cited_sessions_for_80pct"]
    assert isinstance(cited, float) and round(cited) == 42
    assert secondary["sessions_multiplier"] == 4
    assert secondary["n_secondary_nominal"] == 168
    caveat = secondary["cited_caveat"]
    assert isinstance(caveat, str) and caveat, "the upper-bound caveat must travel with it"
