"""Public README must expose only the current, fail-closed scientific state."""

from __future__ import annotations

import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
README = REPO / "README.md"
STATE = REPO / "data" / "CANONICAL_STATE.json"


def test_readme_resolves_the_single_scientific_bundle() -> None:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    bundle = state["scientific_bundle"]
    readme = README.read_text(encoding="utf-8")

    assert bundle["run_id"] in readme
    assert bundle["manifest"]["scientific_sha256"] in readme
    assert bundle["eligibility"]["status"] in readme
    for reason in bundle["eligibility"]["reasons"]:
        assert reason in readme


def test_readme_contains_no_withdrawn_headline_figures() -> None:
    readme = README.read_text(encoding="utf-8")
    withdrawn = (
        "+0.057",
        "+0.013",
        "−0.028 per year",
        "-0.0277/yr",
        "3 × 10⁻⁴⁶",
        "p = 0.0070",
        "formally equivalent",
        "The mechanism is real",
    )
    assert not [claim for claim in withdrawn if claim in readme]


def test_readme_routes_the_completed_phase8_bridge_without_promoting_it() -> None:
    readme = README.read_text(encoding="utf-8")
    assert "MIXED_EXPLORATORY" in readme
    assert "reports/phase8a_exploratory_bridge_addendum_v7.md" in readme
    assert "Holm" in readme
    assert "no aggregation change" in readme
    assert "not confirmatory" in readme


def test_readme_routes_history_and_evidence_to_researcher_documents() -> None:
    readme = README.read_text(encoding="utf-8")
    required = (
        "data/CANONICAL_STATE.json",
        "docs/pit_v22_claims_and_limitations.md",
        "docs/rp2_v3/SUPERSEDED_RESULTS.md",
        "data/DATA_ACCESS.md",
        "docs/reproducibility_contract_v1.md",
    )
    for relative in required:
        assert relative in readme
        assert (REPO / relative).is_file()


def test_readme_does_not_publish_operator_or_agent_instructions() -> None:
    readme = README.read_text(encoding="utf-8").lower()
    forbidden = ("@codex", "agent instruction", "owner directive", "claude.md", "agents.md")
    assert not [phrase for phrase in forbidden if phrase in readme]


def test_ci_badge_names_the_hosted_tier() -> None:
    readme = README.read_text(encoding="utf-8")
    workflow = (REPO / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "[![Tier 1 CI]" in readme
    assert workflow.startswith("name: Tier 1 CI\n")
