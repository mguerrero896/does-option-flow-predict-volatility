"""Phase 9 planning must count scored sessions, not collected warm-up sessions."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "build_phase9_power_deadline_audit.py"
ARTIFACT = ROOT / "artifacts" / "phase9" / "power_deadline_audit_v1.json"


def _load() -> Any:
    spec = importlib.util.spec_from_file_location("phase9_power_deadline_audit", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_phase9_deadline_and_mde_use_only_scored_sessions() -> None:
    module = _load()
    audit = module.build_audit()

    assert audit["read_gate"] == {
        "outcome_paths_read": [],
        "sealed_cohorts_read": 0,
    }
    assert audit["endpoint"] == {
        "complete_sessions": 60,
        "scored_sessions": 36,
        "test_blocks": 3,
    }
    assert audit["three_week_deadline"]["maximum_complete_sessions"] == 19
    assert audit["three_week_deadline"]["scored_sessions"] == 0
    assert audit["three_week_deadline"]["phase9_result_possible"] is False

    recent = audit["scenarios"]["recent_log_ols"]["milestones"]["60"]
    assert recent["scored_sessions"] == 36
    assert recent["mde_nominal_alpha_0_05"] == pytest.approx(0.01980439995534981)
    assert recent["mde_binding_alpha_0_008333"] == pytest.approx(0.025071359452286113)
    assert audit["decision"]["endpoint_complete_sessions"] == 60
    assert audit["decision"]["interim_activated"] is False
    assert audit["decision"]["academic_submission_waits_for_phase9"] is False
    assert audit["inputs"]["producer"]["path"] == (
        "scripts/build_phase9_power_deadline_audit.py"
    )
    assert audit["inputs"]["mde_contract"]["path"] == "src/mds650/rp2/inference.py"
    assert len(audit["inputs"]["producer"]["sha256"]) == 64
    assert len(audit["inputs"]["mde_contract"]["sha256"]) == 64


def test_phase9_power_deadline_artifact_is_reproducible() -> None:
    module = _load()
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    assert artifact == module.build_audit()
    assert artifact["audit_sha256"] == module.canonical_sha256(artifact)
