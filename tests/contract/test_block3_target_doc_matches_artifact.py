"""The target-horizon page must resolve to the latest recorded comparison."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUN_ID = "rp2-v3-20260827-remediation3"
ARTIFACT = ROOT / "artifacts" / "rp2_v3" / RUN_ID / "rp2_block3_target" / "comparison.json"
DOCUMENT = ROOT / "docs" / "rp2" / "block3_target_validation_v1.md"


def test_target_horizon_document_matches_current_artifact() -> None:
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    document = DOCUMENT.read_text(encoding="utf-8")
    assert RUN_ID in document
    assert artifact["comparison_sha256"] in document
    assert f"{artifact['panel_rows']:,}" in document
    assert f"{artifact['panel_sessions']:,}" in document
    for role, source in (
        ("D", artifact["comparison"]),
        ("V", artifact["validation_comparison"]),
    ):
        assert f"| {role} |" in document
        for horizon in (5, 15, 30, 60, 120):
            assert f"{source['rv'][str(horizon)]['oos_log_r2']:.5f}" in document


def test_target_horizon_document_withdraws_the_old_universal_rv60_claim() -> None:
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    development = artifact["comparison"]["rv"]
    validation = artifact["validation_comparison"]["rv"]
    assert development["60"]["oos_log_r2"] > development["30"]["oos_log_r2"]
    assert validation["30"]["oos_log_r2"] > validation["60"]["oos_log_r2"]
    document = DOCUMENT.read_text(encoding="utf-8")
    assert "RV60 wins in both roles is withdrawn" in document
