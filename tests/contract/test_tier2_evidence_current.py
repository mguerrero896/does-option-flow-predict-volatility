"""The PR #55 remediation Tier 2 result is durable and machine-checkable."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EVIDENCE = REPO / "artifacts/local_evidence_gates/pr55_remediation_20260902_v1.json"
EXPECTED_GATES = (
    "versioned-hook",
    "ruff",
    "mypy",
    "full-pytest",
    "ci-sim",
    "gated-hashes",
    "access-posture",
)


def test_pr55_remediation_tier2_evidence_is_complete_and_registered() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    relative = EVIDENCE.relative_to(REPO).as_posix()
    registry = json.loads((REPO / "data/FROZEN_ARTIFACTS.json").read_text(encoding="utf-8"))
    canonical = json.loads((REPO / "data/CANONICAL_STATE.json").read_text(encoding="utf-8"))

    assert payload["schema_version"] == "mds650-tier2-evidence-v1.0"
    assert payload["runner"] == "scripts/run_local_evidence_gates.py"
    assert payload["required_ancestor"] == "c1e331e247d411eb21141b1cd271130ae16bfd89"
    assert payload["overall_exit_code"] == 0
    assert [(gate["name"], gate["exit_code"]) for gate in payload["gates"]] == [
        (name, 0) for name in EXPECTED_GATES
    ]
    assert payload["environment_contract"] == {
        "ci_sim_declared_opt_outs": {
            "MDS650_PANEL_GUARD_MAY_SKIP": "1",
            "MDS650_UW_LATENCY_FRESHNESS_MAY_SKIP": "1",
        },
        "licensed_gate_opt_outs": {
            "MDS650_PANEL_GUARD_MAY_SKIP": "absent",
            "MDS650_UW_LATENCY_FRESHNESS_MAY_SKIP": "absent",
        },
    }
    assert datetime.fromisoformat(payload["executed_at_utc"]).tzinfo is not None
    assert re.fullmatch(r"[0-9a-f]{40}", payload["tested_commit"])
    assert re.fullmatch(r"[0-9a-f]{40}", payload["tested_tree"])
    assert relative in {entry["path"] for entry in registry["entries"]}
    assert relative in canonical["authorized_sources"]
