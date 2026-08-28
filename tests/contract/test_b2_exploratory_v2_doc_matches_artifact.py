"""The v2 campaign document may not drift from its artifact — same doctrine as v1."""

from __future__ import annotations

import json
from pathlib import Path

from mds650.b1v3_confirmation import canonical_sha256

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "artifacts" / "rp2_b2_exploratory_v2" / "results.json"
DOC = ROOT / "docs" / "rp2" / "extension_b2_exploratory_v2.md"


def _artifact() -> dict:  # type: ignore[type-arg]
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    recorded = payload.pop("self_sha256")
    assert canonical_sha256(payload) == recorded, "artifact self-hash broken"
    payload["self_sha256"] = recorded
    return payload


def _doc() -> str:
    return DOC.read_text(encoding="utf-8").replace("−", "-")


def test_the_doc_table_matches_the_artifact_row_for_row() -> None:
    payload = _artifact()
    doc = _doc()
    q_values = payload["v_q_values_vs_incumbent"]
    for name in payload["registered_candidates"]:
        dtest = payload["evaluations"]["dtest"][name]
        vcheck = payload["evaluations"]["vcheck"][name]
        row = (
            f"| {name} "
            f"| {dtest['vs_incumbent']['estimate']:+.5f} "
            f"({dtest['vs_incumbent']['wild_cluster_p_value']:.3f}) "
            f"| {vcheck['vs_incumbent']['estimate']:+.5f} "
            f"({vcheck['vs_incumbent']['wild_cluster_p_value']:.3f}) "
            f"| {q_values[name]:.3f} "
            f"| {dtest['vs_base']['estimate']:+.5f} "
            f"| {vcheck['vs_base']['estimate']:+.5f} |"
        )
        assert row in doc, f"doc drifted from artifact for {name}: expected {row!r}"


def test_the_anchor_verdict_and_provenance_match() -> None:
    payload = _artifact()
    doc = _doc()
    anchor = payload["evaluations"]["dtest"]["anchor_r0_to_r1"]
    assert f"{anchor['estimate']:+.6f}" == "+0.001015"
    assert f"{anchor['wild_cluster_p_value']:.4f}" == "0.0010"
    assert "+0.001015" in doc
    # The verdict: no candidate beats the incumbent on V (every estimate <= noise or
    # negative; every q above the 0.10 bar or the estimate itself negative).
    for name in payload["registered_candidates"]:
        entry = payload["evaluations"]["vcheck"][name]["vs_incumbent"]
        cleared = entry["estimate"] > 0 and payload["v_q_values_vs_incumbent"][name] <= 0.10
        assert not cleared, f"{name} cleared the bar but the doc says the axis closed"
    assert payload["self_sha256"][:16] in doc
    assert payload["label"] == "EXPLORATORY_DIAGNOSTIC"
    assert payload["encoder"]["parameters"] == 7233
    assert "7,233 parameters" in _doc()
