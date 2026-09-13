"""The public record must say which producer made the frozen v4 aggregates.

After the B2 history-eligibility repair (public commit 1c9db3e5), the current
producer differs from the one that produced the frozen RP4 v4 aggregates. This
contract binds the documentary statement to the producer hashes so the
statement cannot drift silently when the producer changes again.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
LINEAGE = ROOT / "data/b2_producer_lineage.json"


def _record() -> dict[str, Any]:
    record: dict[str, Any] = json.loads(LINEAGE.read_text("utf-8"))
    return record


def test_lineage_record_pins_the_current_producer_bytes() -> None:
    record = _record()
    assert record["schema"] == "b2-producer-lineage-v1"
    assert record["frozen_rp4_v4_aggregates_recomputed_with_repaired_producer"] is False
    for path, digest in record["producer_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest, (
            f"{path} changed: update data/b2_producer_lineage.json and the code-lineage statements"
        )
    assert set(record["producer_sha256"]) == {
        "src/mds650/phase6.py",
        "src/mds650/phase5_features.py",
        "src/mds650/target_blind_panel_v22.py",
        "scripts/build_target_blind_common_panel_v22.py",
    }


def test_current_and_readme_state_the_code_lineage() -> None:
    record = _record()
    current = (ROOT / "docs/CURRENT.md").read_text("utf-8")
    paragraph = next(line for line in current.splitlines() if line.startswith("**Code lineage:**"))
    assert "have not been recomputed" in paragraph
    assert "would not reproduce the frozen aggregates byte-for-byte" in paragraph
    assert "not on the 419-session v4 panel" in paragraph
    effect = record["measured_effect"]
    universe = effect["b2_universe_180_sessions"]["origins_with_changed_features"]
    panel = effect["published_common_panel_159_sessions"]["origins_with_changed_features"]
    assert f"{universe:,}" in paragraph
    assert f"{panel:,}" in paragraph
    gamma = effect["isolated_reevaluation_b2_over_b1_qlike_gain"]["gamma"]
    lgbm = effect["isolated_reevaluation_b2_over_b1_qlike_gain"]["lightgbm"]
    assert f"{gamma['previous']:.6f} to {gamma['repaired']:.6f}" in paragraph
    assert f"+{lgbm['previous']:.6f} to +{lgbm['repaired']:.6f}" in paragraph
    assert record["closeout_document"].split("/")[-1] in paragraph
    readme = (ROOT / "README.md").read_text("utf-8")
    assert "will not reproduce them byte-for-byte" in readme
    assert "Defect D89" in readme


def test_defect_register_and_closeout_are_published() -> None:
    register = (ROOT / "docs/known_defects_and_resolutions.md").read_text("utf-8")
    row = next(line for line in register.splitlines() if line.startswith("| D89 |"))
    assert "stored results not recomputed" in row
    assert "b2_repair_and_evidence_closeout_20260905.md" in row
    closeout = ROOT / _record()["closeout_document"]
    assert closeout.exists()
    text = closeout.read_text("utf-8")
    for linked in (
        "artifacts/b2_history_repair_v1/evaluation_protocol.json",
        "artifacts/b2_history_repair_v1/evaluation_result.json",
        "artifacts/b2_history_repair_v1/feature_impact.json",
    ):
        assert (ROOT / linked).exists(), linked
    assert "27,153" in text and "244,377" in text
