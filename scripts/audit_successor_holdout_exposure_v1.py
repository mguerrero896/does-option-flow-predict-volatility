"""Classify successor-v2 holdout exposure from its target-free session calendar.

The only private input is the signed target-free predictor panel. This producer reads
only ``session_date`` and ``common_predictor_complete`` from it; it never reads a target,
forecast, loss, metric, Phase 8/9 payload, C cohort, or one-shot result.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from types import ModuleType
from typing import Any

import polars as pl

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
FORBIDDEN_PANEL_FIELDS = frozenset({"rv30", "target", "forecast", "qlike", "loss"})


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha(payload: Mapping[str, Any], *, omit: str) -> str:
    body = {key: value for key, value in payload.items() if key != omit}
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _load_mapping(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"HOLDOUT_EXPOSURE_MAPPING_REQUIRED:{path.name}")
    return value


def _runner() -> ModuleType:
    spec = importlib.util.spec_from_file_location("pit_v22_successor_runner", SUCCESSOR_RUNNER)
    if spec is None or spec.loader is None:
        raise ValueError("HOLDOUT_EXPOSURE_RUNNER_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _read_target_free_session_dates(panel: Path) -> list[str]:
    """Read exactly the two target-free columns used by the signed runner preflight."""
    schema = pl.read_parquet_schema(panel)
    fields = {name.casefold() for name in schema}
    if FORBIDDEN_PANEL_FIELDS & fields:
        raise ValueError("HOLDOUT_EXPOSURE_SOURCE_PANEL_NOT_TARGET_FREE")
    required = {"session_date", "common_predictor_complete"}
    if not required <= set(schema):
        raise ValueError("HOLDOUT_EXPOSURE_SOURCE_PANEL_SCHEMA_INVALID")
    keys = pl.read_parquet(panel, columns=sorted(required))
    sessions = sorted(
        str(day)
        for day in keys.filter(pl.col("common_predictor_complete"))["session_date"]
        .unique()
        .to_list()
    )
    if len(sessions) != 159 or any(DATE.fullmatch(day) is None for day in sessions):
        raise ValueError("HOLDOUT_EXPOSURE_SOURCE_PANEL_SESSION_UNIVERSE_INVALID")
    return sessions


def _phase6_c3_window() -> dict[str, Any]:
    freeze = _load_mapping(PHASE6_FREEZE)
    dates = sorted(
        {
            str(date)
            for fold in freeze.get("folds", [])
            if isinstance(fold, dict)
            for field in ("train_dates", "test_dates")
            for date in fold.get(field, [])
            if isinstance(date, str) and DATE.fullmatch(date)
        }
    )
    if len(dates) != 160:
        raise ValueError("HOLDOUT_EXPOSURE_PHASE6_C3_SESSION_UNIVERSE_INVALID")
    return {
        "source": PHASE6_FREEZE.relative_to(ROOT).as_posix(),
        "session_count": len(dates),
        "start": dates[0],
        "end": dates[-1],
        "session_dates_sha256": _canonical_sha({"session_dates": dates}, omit="__never__"),
        "session_dates": dates,
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


def _intersection_count(dates: Sequence[str], start: str, end: str) -> int:
    return sum(start <= date <= end for date in dates)


def mde_role_after_exposure(*, intersects_prior_read: bool, explicit_override: bool) -> str:
    """A prior read removes the confirmatory threshold unless a decision overrides it."""
    if intersects_prior_read and not explicit_override:
        return "EXPLORATORY_DESCRIPTIVE"
    return "CONFIRMATORY_THRESHOLD"


def build_audit(
    session_dates: Sequence[str], *, source_panel_sha256: str
) -> dict[str, Any]:
    """Build the public audit from an already-read target-free session calendar."""
    sessions = [str(day) for day in session_dates]
    if len(sessions) != 159 or sessions != sorted(set(sessions)):
        raise ValueError("HOLDOUT_EXPOSURE_SESSION_DATES_INVALID")
    manifest = _load_mapping(MANIFEST)
    freeze = _load_mapping(FREEZE)
    summary = manifest.get("summary", {})
    split_definition = freeze.get("temporal_train_validation_holdout_definition", {})
    if (
        manifest.get("no_target_or_metric_payload_read") is not True
        or not isinstance(summary, dict)
        or summary.get("session_count") != 180
        or not isinstance(split_definition, dict)
        or split_definition.get("method") != "chronological_by_session"
        or split_definition.get("train_share") != 0.6
        or manifest.get("output", {}).get("panel_sha256") != source_panel_sha256
    ):
        raise ValueError("HOLDOUT_EXPOSURE_SOURCE_CONTRACT_DRIFT")

    split = _runner().successor_session_split(sessions)
    if {role: len(dates) for role, dates in split.items()} != {
        "development": 95,
        "validation": 32,
        "holdout": 32,
    }:
        raise ValueError("HOLDOUT_EXPOSURE_REGISTERED_SPLIT_INVALID")
    c3 = _phase6_c3_window()
    holdout = list(split["holdout"])
    c3_dates = set(c3["session_dates"])
    if not set(sessions) <= c3_dates:
        raise ValueError("HOLDOUT_EXPOSURE_SUCCESSOR_NOT_WITHIN_C3_UNIVERSE")
    rp2_d = _rp2_window()
    phase8 = _phase8_windows()
    c3_intersection = len(set(holdout) & c3_dates)
    rp2_intersection = _intersection_count(holdout, rp2_d["start"], rp2_d["end"])
    phase8_intersections = [
        _intersection_count(holdout, window["start"], window["end"]) for window in phase8
    ]
    if c3_intersection != 32 or rp2_intersection != 32 or any(phase8_intersections):
        raise ValueError("HOLDOUT_EXPOSURE_INTERSECTION_CONTRADICTION")

    payload: dict[str, Any] = {
        "schema_version": "successor-holdout-exposure-v1.0",
        "status": "PASS_RETROSPECTIVE_EXPOSURE_VERIFIED",
        "scope": "target_free_session_calendar_only",
        "read_guard": {
            "fresh_outcome_reads": 0,
            "sealed_cohort_outcome_reads": 0,
            "phase9_reads": 0,
            "c_cohort_reads": 0,
            "target_or_metric_columns_read": 0,
            "target_free_metadata_panel_reads": 1,
            "columns_read": ["common_predictor_complete", "session_date"],
        },
        "source_contract": {
            "target_free_panel_sha256": source_panel_sha256,
            "predictor_manifest_session_count": 180,
            "registered_session_universe_count": len(sessions),
            "registered_session_universe_sha256": _canonical_sha(
                {"session_dates": sessions}, omit="__never__"
            ),
            "split_method": split_definition["method"],
            "train_share": split_definition["train_share"],
            "splits": {
                role: {
                    "session_count": len(dates),
                    "start": dates[0],
                    "end": dates[-1],
                    "session_dates": dates,
                }
                for role, dates in split.items()
            },
        },
        "prior_outcome_read_windows": {
            "phase6_c3": {**c3, "holdout_intersection_count": c3_intersection},
            "rp2_development": {**rp2_d, "holdout_intersection_count": rp2_intersection},
            "phase8": [
                {**window, "holdout_intersection_count": count}
                for window, count in zip(phase8, phase8_intersections, strict=True)
            ],
        },
        "classification": {
            "holdout_outcomes_previously_read": True,
            "reason": "HOLDOUT_OUTCOMES_PREVIOUSLY_READ_BY_C3_AND_RP2V3_D",
            "result_role": "RETROSPECTIVE_REMEASUREMENT_UNDER_PIT_V22",
            "evidential_status": "EXPLORATORY_DESCRIPTIVE",
            "mde_role": mde_role_after_exposure(
                intersects_prior_read=True, explicit_override=False
            ),
            "one_shot_label_scope": "CONTRACT_ACCESS_CUSTODY_ONLY",
            "reclassification_applied": True,
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
            "command": (
                "uv run python scripts/audit_successor_holdout_exposure_v1.py "
                "--source-panel <target-free-panel.parquet>"
            ),
            "exit_code": 0,
        },
    }
    payload["audit_sha256"] = _canonical_sha(payload, omit="audit_sha256")
    return payload


def verify_recorded(audit: Mapping[str, Any]) -> None:
    """Verify a committed audit without reading the private target-free panel."""
    splits = audit.get("source_contract", {}).get("splits", {})
    if not isinstance(splits, dict):
        raise ValueError("HOLDOUT_EXPOSURE_RECORDED_SPLIT_INVALID")
    sessions = [
        *splits.get("development", {}).get("session_dates", []),
        *splits.get("validation", {}).get("session_dates", []),
        *splits.get("holdout", {}).get("session_dates", []),
    ]
    source_panel_sha256 = audit.get("source_contract", {}).get("target_free_panel_sha256")
    if not isinstance(source_panel_sha256, str):
        raise ValueError("HOLDOUT_EXPOSURE_RECORDED_PANEL_SHA_INVALID")
    if audit != build_audit(sessions, source_panel_sha256=source_panel_sha256):
        raise ValueError("HOLDOUT_EXPOSURE_RECORDED_AUDIT_DRIFT")


def _write_atomic(path: Path, payload: Mapping[str, Any]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    os.replace(temporary, path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-panel",
        type=Path,
        required=True,
        help="Signed target-free predictor parquet; only two metadata columns are read.",
    )
    args = parser.parse_args(argv)
    audit = build_audit(
        _read_target_free_session_dates(args.source_panel),
        source_panel_sha256=_sha256(args.source_panel),
    )
    _write_atomic(ARTIFACT, audit)
    print(f"SUCCESSOR_HOLDOUT_EXPOSURE={audit['status']}")
    print(f"AUDIT_SHA256={audit['audit_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
