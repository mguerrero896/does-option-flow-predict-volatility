"""Evidence-binding contracts for the canonical RV30 documentation."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CLAIMS_PATH = ROOT / "docs" / "canonical_claims_and_limitations.md"
CONCLUSION_PATH = ROOT / "docs" / "canonical_validation_conclusion.md"
MODEL_CARDS = (
    "gamma_glm_rv30.md",
    "har_rv_rv30.md",
    "ridge_rv30.md",
    "elastic_net_rv30.md",
    "lightgbm_rv30.md",
)
REQUIRED_CLAIM_COLUMNS = (
    "claim_id",
    "claim_text",
    "status",
    "evidence_path",
    "metric",
    "model_role",
    "block",
    "limitation",
    "allowed_presentation_context",
)


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _claim_rows() -> list[dict[str, str]]:
    """Parse the compact Markdown claim ledger without an external dependency."""

    lines = CLAIMS_PATH.read_text(encoding="utf-8").splitlines()
    header_index = next(
        index for index, line in enumerate(lines) if line.startswith("| claim_id |")
    )
    header = [cell.strip() for cell in lines[header_index].strip("|").split("|")]
    assert tuple(header) == REQUIRED_CLAIM_COLUMNS
    rows: list[dict[str, str]] = []
    for line in lines[header_index + 2 :]:
        if not line.startswith("|"):
            break
        cells = [cell.strip() for cell in line.strip("|").split("|")]
        assert len(cells) == len(header)
        rows.append(dict(zip(header, cells, strict=True)))
    return rows


def test_every_claim_has_machine_evidence_and_declared_status() -> None:
    """A numerical or qualitative conclusion cannot exist without an evidence path."""

    rows = _claim_rows()

    assert rows
    for row in rows:
        assert row["claim_id"]
        assert row["claim_text"]
        assert row["status"] in {
            "SUPPORTED",
            "CONDITIONAL",
            "NOT_SUPPORTED",
            "INVALIDATED_INPUT",
        }
        assert row["evidence_path"]
        for evidence_path in row["evidence_path"].split(";"):
            assert (ROOT / evidence_path.strip()).is_file()
        assert row["metric"]
        assert row["model_role"]
        assert row["block"]
        assert row["limitation"]
        assert row["allowed_presentation_context"]


def test_post_read_extensions_are_not_presented_as_registered_evidence() -> None:
    """HAR/Ridge/Elastic-Net remain descriptive post-read extensions everywhere."""

    text = "\n".join(
        [
            CLAIMS_PATH.read_text(encoding="utf-8"),
            CONCLUSION_PATH.read_text(encoding="utf-8"),
            *[
                (ROOT / "docs" / "model_cards" / name).read_text(encoding="utf-8")
                for name in MODEL_CARDS
            ],
        ]
    ).lower()

    assert "post-read fixed extension" in text
    assert "fresh oos" not in text


def test_conclusion_retains_model_family_dependent_decision() -> None:
    """The documentation cannot relabel inconsistent registered models as global evidence."""

    text = CONCLUSION_PATH.read_text(encoding="utf-8")

    assert "MODEL_FAMILY_DEPENDENT" in text
    assert "GLOBAL_EDGE" not in text


def test_historical_claim_ledgers_cannot_authorize_current_results() -> None:
    claims = _read("docs/canonical_claims_and_limitations.md")
    final_report = _read("docs/rp2/FINAL_REPORT.md")
    reconciliation = _read("docs/results_reconciliation_v2.md")
    decisions = _read("docs/methodology_decisions.md")
    superseded = _read("docs/rp2_v3/SUPERSEDED_RESULTS.md")

    assert "**SUPERSEDED AUTHORITY.**" in claims
    assert "This ledger is the only allowed source" not in claims
    assert "**HISTORICAL CROSS-CAMPAIGN VIEW.**" in reconciliation
    assert "The current figures are in" not in reconciliation
    assert "**HISTORICAL RP2-V2 REPORT.**" in final_report
    assert "The current figures are in" not in final_report
    assert "canonical cross-campaign numbers live in" in decisions
    assert "**Supersession, 2026-08-30:**" in decisions
    assert "CLM-016" in superseded
    assert "rival v2 numerical-authority claims" in superseded
    assert "+0.03396090" in superseded
    assert "−0.00002" in superseded


def test_current_threats_and_reports_match_corrected_evidence() -> None:
    matrix = _read("docs/threats_to_validity_matrix_v1.md")
    assert "NO_CURRENT_ELIGIBLE_RESULT" in matrix
    assert "PIT_V22_RECONCILIATION_BLOCKED" in matrix
    assert "NOT_EVALUATED_AFTER_PIT_CORRECTION" in matrix
    assert "sealed_cohorts_read=0" in matrix

    corrected = json.loads(_read("artifacts/gate3_har/results_corrected_int8.json"))
    displays = (
        f"{corrected['contrasts']['har_vs_har_b2']['cluster_t']['estimate']:.5f}",
        f"{corrected['contrasts']['harq_vs_harq_b2']['cluster_t']['estimate']:.5f}",
    )
    for relative_path in (
        "docs/results_reconciliation_v2.md",
        "reports/final_report_draft_v2.md",
    ):
        text = _read(relative_path)
        for display in displays:
            assert display.replace("-", "−") in text
        assert "−0.00102" not in text
        assert "−0.00090" not in text
