"""Correct Phase 9 power planning without reading the sealed collection.

The frozen protocol collects 60 complete sessions but scores only 36 after its
24-session warm-up.  Its original power table used 60 as the scored-session count.
This producer derives the corrected MDEs from the same Gate-11 standard errors and
records what can exist by the three-week academic deadline.  No Phase 9 path is read.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import exchange_calendars  # type: ignore[import-untyped]

from mds650.rp2.inference import minimum_detectable_effect_from_long_run_variance

ROOT = Path(__file__).resolve().parents[1]
PRODUCER = Path(__file__).resolve()
SOURCE = ROOT / "artifacts" / "gate11_era_map" / "results.json"
PROTOCOL = ROOT / "docs" / "phase9_total_contribution_protocol_v1.md"
MULTIPLICITY = ROOT / "docs" / "sequential_multiplicity_policy_v1.md"
MDE_CONTRACT = ROOT / "src" / "mds650" / "rp2" / "inference.py"
OUTPUT = ROOT / "artifacts" / "phase9" / "power_deadline_audit_v1.json"

WARMUP_SESSIONS = 24
TEST_BLOCK_SESSIONS = 12
ENDPOINT_COMPLETE_SESSIONS = 60
POWER = 0.80
NOMINAL_ALPHA = 0.05
BINDING_ALPHA = 0.05 / (2 * 3)
MILESTONES = (20, 30, 36, 48, 60)
MISSED_SESSIONS = frozenset({"2026-08-25", "2026-08-26"})
SCENARIOS = {
    "recent_log_ols": ("era_2026H1_devpanel", "log_ols|B0->B2_total"),
    "recent_lightgbm": ("era_2026H1_devpanel", "lightgbm|B0->B2_total"),
    "p6_log_ols": ("era_2025H2_2026Q1_p6panel", "log_ols|B0->B2_total"),
    "p6_lightgbm": ("era_2025H2_2026Q1_p6panel", "lightgbm|B0->B2_total"),
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def canonical_sha256(document: dict[str, Any]) -> str:
    payload = {key: value for key, value in document.items() if key != "audit_sha256"}
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _mde(session_sigma: float, scored_sessions: int, alpha: float) -> float | None:
    if scored_sessions < 3:
        return None
    return minimum_detectable_effect_from_long_run_variance(
        session_sigma**2,
        scored_sessions,
        alpha=alpha,
        power=POWER,
    )


def _completion_dates() -> dict[str, str]:
    calendar = exchange_calendars.get_calendar("XNYS")
    sessions = [
        stamp.date().isoformat()
        for stamp in calendar.sessions_in_range("2026-08-19", "2026-12-31")
        if stamp.date().isoformat() not in MISSED_SESSIONS
    ]
    return {str(total): sessions[total - 1] for total in MILESTONES}


def _three_week_deadline() -> dict[str, Any]:
    calendar = exchange_calendars.get_calendar("XNYS")
    remaining = calendar.sessions_in_range("2026-08-27", "2026-09-17")
    maximum_complete = 4 + len(remaining)
    return {
        "academic_horizon_sydney": "2026-09-18",
        "last_collectable_xnys_session": "2026-09-17",
        "complete_sessions_before_2026_08_27": 4,
        "additional_xnys_sessions_if_no_more_misses": len(remaining),
        "maximum_complete_sessions": maximum_complete,
        "scored_sessions": max(0, maximum_complete - WARMUP_SESSIONS),
        "phase9_result_possible": maximum_complete >= WARMUP_SESSIONS + TEST_BLOCK_SESSIONS,
    }


def build_audit() -> dict[str, Any]:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    completion_dates = _completion_dates()
    scenarios: dict[str, Any] = {}
    for name, (era, contrast) in SCENARIOS.items():
        row = source["eras"][era]["contrasts"][contrast]
        source_clusters = int(row["clusters"])
        source_standard_error = float(row["standard_error"])
        session_sigma = source_standard_error * math.sqrt(source_clusters)
        milestones: dict[str, Any] = {}
        for total in MILESTONES:
            scored = max(0, total - WARMUP_SESSIONS)
            milestones[str(total)] = {
                "complete_sessions": total,
                "scored_sessions": scored,
                "complete_test_blocks": scored // TEST_BLOCK_SESSIONS,
                "earliest_nominal_completion": completion_dates[str(total)],
                "mde_nominal_alpha_0_05": _mde(session_sigma, scored, NOMINAL_ALPHA),
                "mde_binding_alpha_0_008333": _mde(
                    session_sigma, scored, BINDING_ALPHA
                ),
            }
        scenarios[name] = {
            "source_era": era,
            "source_contrast": contrast,
            "source_clusters": source_clusters,
            "source_standard_error": source_standard_error,
            "session_sigma": session_sigma,
            "original_mde_assuming_60_scored_sessions": _mde(
                session_sigma, 60, NOMINAL_ALPHA
            ),
            "milestones": milestones,
        }

    document: dict[str, Any] = {
        "schema_version": "phase9-power-deadline-audit-v1.0",
        "status": "TARGET_BLIND_PLANNING_CORRECTION_NO_OUTCOME_READ",
        "issue": (
            "The frozen protocol power table treated n=60 as 60 scored sessions; "
            "the frozen folds collect 60 but score 36 after a 24-session warm-up."
        ),
        "inputs": {
            "producer": {
                "path": "scripts/build_phase9_power_deadline_audit.py",
                "sha256": _sha256(PRODUCER),
            },
            "mde_contract": {
                "path": "src/mds650/rp2/inference.py",
                "sha256": _sha256(MDE_CONTRACT),
            },
            "gate11_results": {
                "path": "artifacts/gate11_era_map/results.json",
                "sha256": _sha256(SOURCE),
            },
            "frozen_protocol": {
                "path": "docs/phase9_total_contribution_protocol_v1.md",
                "sha256": _sha256(PROTOCOL),
            },
            "multiplicity_policy": {
                "path": "docs/sequential_multiplicity_policy_v1.md",
                "sha256": _sha256(MULTIPLICITY),
            },
        },
        "method": {
            "power": POWER,
            "nominal_two_sided_alpha": NOMINAL_ALPHA,
            "binding_two_sided_alpha": BINDING_ALPHA,
            "mde_formula": "(t_(1-alpha/2,df)+t_(power,df))*session_sigma/sqrt(scored_sessions)",
            "session_sigma_formula": "gate11_standard_error*sqrt(gate11_clusters)",
        },
        "endpoint": {
            "complete_sessions": ENDPOINT_COMPLETE_SESSIONS,
            "scored_sessions": ENDPOINT_COMPLETE_SESSIONS - WARMUP_SESSIONS,
            "test_blocks": (ENDPOINT_COMPLETE_SESSIONS - WARMUP_SESSIONS)
            // TEST_BLOCK_SESSIONS,
        },
        "three_week_deadline": _three_week_deadline(),
        "scenarios": scenarios,
        "decision": {
            "endpoint_complete_sessions": ENDPOINT_COMPLETE_SESSIONS,
            "interim_activated": False,
            "academic_submission_waits_for_phase9": False,
            "recommended_academic_use": "ONGOING_FUTURE_FOLLOW_UP_NO_PHASE9_RESULT",
        },
        "read_gate": {
            "outcome_paths_read": [],
            "sealed_cohorts_read": 0,
        },
    }
    document["audit_sha256"] = canonical_sha256(document)
    return document


def main() -> None:
    audit = build_audit()
    OUTPUT.write_text(
        json.dumps(audit, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"[phase9-power] wrote {OUTPUT.relative_to(ROOT)} reads=0")


if __name__ == "__main__":
    main()
