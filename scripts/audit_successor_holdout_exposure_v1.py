"""Audit whether the successor-v2 holdout can be classified from public metadata alone.

This producer is deliberately metadata-only: it does not open outcomes, Phase 9, a C
cohort, or a sealed root.  A missing materialized successor session-date vector is a
failed-closed finding, not evidence that the holdout was fresh.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "artifacts" / "target_blind_v22" / "successor_holdout_exposure_v1.json"
MANIFEST = (
    ROOT / "artifacts" / "target_blind_v22" / "target_blind_common_predictor_manifest_v22.json"
)
FREEZE = ROOT / "artifacts" / "target_blind_v22" / "successor_method_freeze_v2.json"
PHASE6_FREEZE = ROOT / "artifacts" / "phase6" / "method_freeze.json"
RP2_WINDOW = ROOT / "docs" / "rp2_v3" / "STUDY_WINDOW.md"
PHASE8_PROTOCOL = ROOT / "docs" / "phase8_bridge_protocol_v2.md"
SUCCESSOR_RUNNER = ROOT / "scripts" / "run_pit_v22_successor_once.py"
DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
RP2_D_WINDOW = re.compile(r"D\s+389 sessions\s+(\d{4}-\d{2}-\d{2})\s+->\s+(\d{4}-\d{2}-\d{2})")
PHASE8_WINDOW = re.compile(
    r"\| (Primary|Sensitivity) \| (\d+) \| (\d{4}-\d{2}-\d{2})\.\.(\d{4}-\d{2}-\d{2}) \|"
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _self_sha(payload: Mapping[str, Any]) -> str:
    body = {key: value for key, value in payload.items() if key != "audit_sha256"}
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _load_mapping(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"HOLDOUT_EXPOSURE_MAPPING_REQUIRED:{path.name}")
    return value


def _phase6_window() -> dict[str, Any]:
    freeze = _load_mapping(PHASE6_FREEZE)
    dates = sorted(
        {
            str(date)
            for fold in freeze.get("folds", [])
            if isinstance(fold, dict)
            for date in fold.get("test_dates", [])
            if isinstance(date, str) and DATE.fullmatch(date)
        }
    )
    if not dates:
        raise ValueError("HOLDOUT_EXPOSURE_PHASE6_TEST_DATES_MISSING")
    return {
        "source": PHASE6_FREEZE.relative_to(ROOT).as_posix(),
        "session_count": len(dates),
        "start": dates[0],
        "end": dates[-1],
    }


def _rp2_window() -> dict[str, Any]:
    match = RP2_D_WINDOW.search(RP2_WINDOW.read_text(encoding="utf-8"))
    if match is None:
        raise ValueError("HOLDOUT_EXPOSURE_RP2_D_WINDOW_MISSING")
    return {
        "source": RP2_WINDOW.relative_to(ROOT).as_posix(),
        "session_count": 389,
        "start": match.group(1),
        "end": match.group(2),
    }


def _phase8_windows() -> list[dict[str, Any]]:
    matches = PHASE8_WINDOW.findall(PHASE8_PROTOCOL.read_text(encoding="utf-8"))
    if len(matches) != 2:
        raise ValueError("HOLDOUT_EXPOSURE_PHASE8_WINDOWS_MISSING")
    return [
        {
            "role": role.casefold(),
            "source": PHASE8_PROTOCOL.relative_to(ROOT).as_posix(),
            "session_count": int(count),
            "start": start,
            "end": end,
        }
        for role, count, start, end in matches
    ]


def mde_role_after_exposure(*, intersects_prior_read: bool, explicit_override: bool) -> str:
    """Apply the non-promotion rule without reading any run outcome."""
    if intersects_prior_read and not explicit_override:
        return "EXPLORATORY_DESCRIPTIVE"
    return "CONFIRMATORY_THRESHOLD"


def build_audit() -> dict[str, Any]:
    manifest = _load_mapping(MANIFEST)
    freeze = _load_mapping(FREEZE)
    summary = manifest.get("summary", {})
    split = freeze.get("temporal_train_validation_holdout_definition", {})
    if (
        manifest.get("no_target_or_metric_payload_read") is not True
        or not isinstance(summary, dict)
        or summary.get("session_count") != 180
        or not isinstance(split, dict)
        or split.get("method") != "chronological_by_session"
        or split.get("train_share") != 0.6
    ):
        raise ValueError("HOLDOUT_EXPOSURE_SOURCE_CONTRACT_DRIFT")

    payload: dict[str, Any] = {
        "schema_version": "successor-holdout-exposure-v1.0",
        "status": "NO_VERIFICABLE_DATE_VECTOR_UNAVAILABLE",
        "scope": "metadata_only_no_outcome_access",
        "read_guard": {
            "fresh_outcome_reads": 0,
            "sealed_cohort_reads": 0,
            "phase9_reads": 0,
            "c_cohort_reads": 0,
            "sealed_root_reads": 0,
        },
        "source_contract": {
            "predictor_manifest_session_count": 180,
            "split_method": split["method"],
            "train_share": split["train_share"],
            "materialized_split_session_counts": None,
            "holdout_session_dates": None,
            "reason": (
                "The permitted predictor manifest and signed method freeze contain no "
                "materialized successor session-date vector."
            ),
        },
        "prior_outcome_read_windows": {
            "phase6_c3": _phase6_window(),
            "rp2_development": _rp2_window(),
            "phase8": _phase8_windows(),
        },
        "classification": {
            "holdout_intersection_with_prior_reads": "NOT_VERIFIABLE",
            "reclassification_applied": False,
            "result_role": "UNCHANGED_PENDING_DATE_VECTOR_EVIDENCE",
            "rule_if_intersection_is_later_verified": (
                "RETROSPECTIVE_REMEASUREMENT_UNDER_PIT_V22; "
                "EXPLORATORY_DESCRIPTIVE; mde_role=EXPLORATORY_DESCRIPTIVE unless an "
                "explicit overriding decision exists."
            ),
        },
        "inputs": {
            path.relative_to(ROOT).as_posix(): _sha256(path)
            for path in (
                MANIFEST,
                FREEZE,
                PHASE6_FREEZE,
                RP2_WINDOW,
                PHASE8_PROTOCOL,
                SUCCESSOR_RUNNER,
            )
        },
        "producer": {
            "path": Path(__file__).relative_to(ROOT).as_posix(),
            "sha256": _sha256(Path(__file__)),
            "command": "uv run python scripts/audit_successor_holdout_exposure_v1.py",
            "exit_code": 0,
        },
    }
    payload["audit_sha256"] = _self_sha(payload)
    return payload


def _write_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    os.replace(temporary, path)


def main(argv: Sequence[str] | None = None) -> int:
    if argv:
        raise ValueError("HOLDOUT_EXPOSURE_NO_ARGUMENTS_SUPPORTED")
    audit = build_audit()
    _write_atomic(ARTIFACT, audit)
    print(f"SUCCESSOR_HOLDOUT_EXPOSURE={audit['status']}")
    print(f"AUDIT_SHA256={audit['audit_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
