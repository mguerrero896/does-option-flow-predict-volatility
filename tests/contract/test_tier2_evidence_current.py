"""The PR #55 remediation Tier 2 result is durable and machine-checkable."""

from __future__ import annotations

import json
import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
EVIDENCE = REPO / "artifacts/local_evidence_gates/pr55_remediation_20260902_v8.json"
EXPECTED_GATES = (
    "versioned-hook",
    "ruff",
    "mypy",
    "full-pytest",
    "ci-sim",
    "gated-hashes",
    "access-posture",
)
EVIDENCE_OVERLAY = {
    "STATUS.md",
    "artifacts/local_evidence_gates/pr55_remediation_20260902_v8.json",
    "data/CANONICAL_STATE.json",
    "data/FROZEN_ARTIFACTS.json",
    "docs/methodology_decisions.md",
    "scripts/generate_canonical_state.py",
    "tests/contract/test_tier2_evidence_current.py",
}


def test_pr55_remediation_tier2_evidence_is_complete_and_registered() -> None:
    payload = json.loads(EVIDENCE.read_text(encoding="utf-8"))
    relative = EVIDENCE.relative_to(REPO).as_posix()
    registry = json.loads((REPO / "data/FROZEN_ARTIFACTS.json").read_text(encoding="utf-8"))
    canonical = json.loads((REPO / "data/CANONICAL_STATE.json").read_text(encoding="utf-8"))

    assert payload["schema_version"] == "mds650-tier2-evidence-v1.0"
    assert payload["runner"] == "scripts/run_local_evidence_gates.py"
    assert payload["required_ancestor"] == "e951a6b30961588bcc51066505b5604944120e14"
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

    tested_commit = payload["tested_commit"]
    commit_probe = subprocess.run(
        ["git", "cat-file", "-e", f"{tested_commit}^{{commit}}"],
        cwd=REPO,
        capture_output=True,
        check=False,
    )
    if commit_probe.returncode == 0:
        tested_tree = subprocess.run(
            ["git", "show", "-s", "--format=%T", tested_commit],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        assert tested_tree == payload["tested_tree"]
        assert (
            subprocess.run(
                [
                    "git",
                    "merge-base",
                    "--is-ancestor",
                    payload["required_ancestor"],
                    tested_commit,
                ],
                cwd=REPO,
                capture_output=True,
                check=False,
            ).returncode
            == 0
        )
        registration_commit = subprocess.run(
            ["git", "log", "--diff-filter=A", "-n", "1", "--format=%H", "--", relative],
            cwd=REPO,
            capture_output=True,
            text=True,
            check=True,
        ).stdout.strip()
        assert re.fullmatch(r"[0-9a-f]{40}", registration_commit)
        assert (
            subprocess.run(
                ["git", "merge-base", "--is-ancestor", registration_commit, "HEAD"],
                cwd=REPO,
                capture_output=True,
                check=False,
            ).returncode
            == 0
        )
        overlay = set(
            subprocess.run(
                ["git", "diff", "--name-only", f"{tested_commit}..{registration_commit}"],
                cwd=REPO,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.splitlines()
        )
        assert overlay == EVIDENCE_OVERLAY
    else:
        assert os.environ.get("GITHUB_EVENT_NAME") != "pull_request", (
            "the tested Tier 2 commit must be present in the public PR history"
        )
