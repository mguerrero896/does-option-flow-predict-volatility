"""The exploratory-campaign document may not drift from its artifact — same doctrine
as the autopsy's contract: every number the prose cites is re-derived from
`artifacts/rp2_b2_exploratory/results.json`, and the artifact's self-hash must hold.
"""

from __future__ import annotations

import json
from pathlib import Path

from mds650.b1v3_confirmation import canonical_sha256

ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / "artifacts" / "rp2_b2_exploratory" / "results.json"
DOC = ROOT / "docs" / "rp2" / "extension_b2_exploratory_v1.md"


def _artifact() -> dict:  # type: ignore[type-arg]
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    recorded = payload.pop("self_sha256")
    assert canonical_sha256(payload) == recorded, "artifact self-hash broken"
    payload["self_sha256"] = recorded
    return payload


def _doc() -> str:
    # The prose uses a typographic minus; numbers compare in ASCII.
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


def test_the_anchor_and_verdict_match_the_artifact() -> None:
    payload = _artifact()
    doc = _doc()
    anchor_d = payload["evaluations"]["dtest"]["anchor_r0_to_r1"]
    anchor_v = payload["evaluations"]["vcheck"]["anchor_r0_to_r1"]
    assert f"{anchor_d['estimate']:+.6f}" == "+0.001015"
    assert f"{anchor_d['wild_cluster_p_value']:.4f}" == "0.0010"
    assert "+0.001015" in doc and "0.0010" in doc
    assert f"{anchor_v['estimate']:+.6f}" == "+0.001010"
    assert "+0.001010" in doc
    # The verdict "no candidate clears the registered bar" must remain true of the
    # artifact: every BH q-value on V exceeds 0.10.
    assert all(q > 0.10 for q in payload["v_q_values_vs_incumbent"].values())
    assert "No candidate clears the registered bar" in _doc()
    # And the doc cites the artifact it was written from.
    assert payload["self_sha256"][:16] in doc


def test_the_campaign_touched_no_sealed_session() -> None:
    payload = _artifact()
    assert payload["label"] == "EXPLORATORY_DIAGNOSTIC"
    assert payload["registered_candidates"] == [
        "c1_flow_regime", "c2_vol_regime", "c3_curvature", "c4_sparse", "c5_second_index"
    ]
    # The campaign script refuses any session past the frozen partition end; the
    # committed panels end 2026-07-17 by construction. Re-assert the contract text.
    assert "virgin" in str(payload["contract"])
