"""Verify the additive defense revision without rerunning research inference."""

import csv
import importlib.util
import json
import re
from decimal import Decimal
from pathlib import Path

import pytest
from scripts.rp4_archive_sources import assert_historical_sha256, original_path, public_path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "docs/rp4/DEFENSE_PACKAGE/revision_2"
SPEC = importlib.util.spec_from_file_location(
    "defense_revision_contract", Path(__file__).with_name("test_rp4_defense_package.py")
)
assert SPEC and SPEC.loader
defense = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(defense)
defense.PACKAGE = PACKAGE
EVIDENCE_PATH = "docs/rp4/DEFENSE_PACKAGE/revision_2/additions_evidence.json"
LOCAL_AGGREGATES = {
    "artifacts/rp4_market_audit/feature_daily.csv",
    "artifacts/rp4_market_audit/bar_event_windows.csv",
}


def test_revision_preserves_original_and_covers_every_claim_number_and_figure() -> None:
    # Reuse the frozen readers and renderers. Its drive-path regex predates HTTPS links.
    manifest = json.loads((original_path(PACKAGE / "evidence_manifest.json")).read_text("utf-8"))
    # Anchor the independently reviewed meanings as well as numeric equality.
    assert_historical_sha256(
        original_path(PACKAGE / "claims_matrix.csv"),
        "211e8cc6e180d0b42deea207090f321a31754ec192ded213603a240a8b26d28e",
    )
    with (original_path(PACKAGE / "claims_matrix.csv")).open(
        encoding="utf-8", newline=""
    ) as stream:
        rows = list(csv.DictReader(stream))
    assert len({row["claim_id"] for row in rows}) == len(rows)
    for name, expected in manifest["source_sha256"].items():
        assert_historical_sha256(original_path(ROOT / name), expected)
    for name, expected in manifest["document_sha256"].items():
        assert_historical_sha256(original_path(PACKAGE / name), expected)
    for name in ("README.md", "docs/rp4/RESULTADO_FINAL.md"):
        passages = defense.passages((original_path(ROOT / name)).read_text("utf-8"))
        claims = [
            row for row in rows if row["kind"] == "source_claim" and row["source_document"] == name
        ]
        assert [row["claim"] for row in claims] == [defense.public_claim(p) for p in passages]
        assert [row["source_passage_sha256"] for row in claims] == [
            defense.digest(p.encode()) for p in passages
        ]
    private = r"(?i)\b(codex|claude|chatgpt|mds650|capstone|RP2|RP3|C10)\b|[A-Za-z]:[\\/]"
    for row in rows:
        assert row["artifact_sha256"] == manifest["source_sha256"][row["artifact"]]
        assert row["revision_test"] == "tests/contract/test_rp4_defense_additions.py"
        for field in ("claim", "context"):
            assert not re.search(private, row[field]), (row["claim_id"], field)
        for name, expected in json.loads(row["supporting_artifacts"]).items():
            assert manifest["source_sha256"][name] == expected
        if row["kind"] == "package_number":
            assert (
                defense.rendered(
                    defense.selected(row["artifact"], row["selector"]), row["rendering"]
                )
                == row["claim"]
            ), row["claim_id"]
    for name in defense.DOCUMENTS:
        text = (original_path(PACKAGE / name)).read_text("utf-8")
        assert [
            row["claim"]
            for row in rows
            if row["kind"] == "package_number" and row["source_document"] == name
        ] == defense.tokens(text), name
        assert not re.search(private, defense.prose(text)), name
        assert not re.search(r"[A-Za-z]:[\\/]", re.sub(r"https?://[^\s)]+", "", text))
        assert not re.search(r"\{\{|\bTODO\b|\bTBD\b", text)
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text):
            if not target.startswith(("https://", "http://", "#")):
                path = (PACKAGE / target.split("#")[0]).resolve()
                assert path.is_relative_to(ROOT) and public_path(path).is_file(), target
    defense.test_defense_table_and_decisions_match_saved_inference()
    defense.test_reviewed_bindings_keep_their_scientific_context()
    prior = PACKAGE.parent
    assert_historical_sha256(
        original_path(prior / "receipt.json"),
        "d88a075767bad2b661d90e77b675b7896e1a04f77fcfd70018f96287646ef79f",
    )
    assert (
        manifest["prior_receipt_sha256"]
        == "d88a075767bad2b661d90e77b675b7896e1a04f77fcfd70018f96287646ef79f"
    )
    assert_historical_sha256(
        original_path(prior / "evidence_manifest.json"),
        "4621ef8c2a3bbdffcdf20346413d5464519147adec11c26e9b1546c5b9fb77ed",
    )
    assert (
        manifest["prior_manifest_sha256"]
        == "4621ef8c2a3bbdffcdf20346413d5464519147adec11c26e9b1546c5b9fb77ed"
    )
    receipt = json.loads((original_path(prior / "receipt.json")).read_text("utf-8"))
    for name, expected in receipt["deliverable_sha256"].items():
        assert_historical_sha256(original_path(prior / name), expected)
    assert_historical_sha256(
        original_path(ROOT / receipt["contract"]["path"]), receipt["contract"]["sha256"]
    )
    assert "## 26. Multiplicidad entre versiones" in (
        original_path(PACKAGE / "examiner_qa.md")
    ).read_text("utf-8")


def test_bonferroni_is_arithmetic_on_saved_p_values_not_cross_family_rescue() -> None:
    evidence = defense.source(EVIDENCE_PATH)
    for name, expected in evidence["source_sha256"].items():
        if (original_path(ROOT / name)).exists():
            assert_historical_sha256(original_path(ROOT / name), expected)
        else:
            assert name in LOCAL_AGGREGATES, name
    rows = defense.source("artifacts/rp4_v4_b4/primary_statistics.csv")
    assert evidence["bonferroni_parameters"]["factors"] == [2, 4]
    assert evidence["bonferroni_parameters"]["cap"] == 1
    atm = evidence["atm_definition"]
    assert defense.selected(atm["source"], json.dumps(atm["selector"])) == atm["tenor"]
    assert atm["tenor"] == f"dte_{atm['dte_min']}_{atm['dte_max']}" == "dte_0_1"
    assert len(evidence["bonferroni"]) == 12
    for comparison in evidence["bonferroni"]:
        row = rows[comparison["source_row_zero_based"]]
        for field in ("horizon_minutes", "family", "contrast", "window", "hypothesis_status"):
            assert comparison[field] == row[field]
        assert row["window"] == "primary"
        p = Decimal(row["p_raw"])
        assert Decimal(str(comparison["p_raw"])) == p
        for factor in (2, 4):
            assert Decimal(str(comparison[f"times_{factor}"])) == min(Decimal(1), factor * p)
        assert comparison["in_declared_primary_pair"] == (row["horizon_minutes"] in {"30", "15"})
    linear15 = {
        row["contrast"]: row
        for row in evidence["bonferroni"]
        if row["family"] == "log_ridge_harq" and row["horizon_minutes"] == "15"
    }
    assert linear15["B2_over_B1"]["times_2"] == 0.0064 < 0.05
    assert linear15["B1_over_B0"]["times_2"] == 0.078 > 0.05
    assert evidence["new_fits"] == evidence["new_bootstraps"] == 0
    assert evidence["historical_results_changed"] is False


@pytest.mark.skipif(
    not all((original_path(ROOT / name)).is_file() for name in LOCAL_AGGREGATES),
    reason="Local licensed aggregate audit inputs are excluded from the publication projection.",
)
def test_event_transcription_matches_local_aggregates_and_separates_windows() -> None:
    evidence = defense.source(EVIDENCE_PATH)
    daily = defense.source("artifacts/rp4_market_audit/feature_daily.csv")
    bars = defense.source("artifacts/rp4_market_audit/bar_event_windows.csv")
    top = defense.source("artifacts/rp4_v4_b4/top_loss_sessions.csv")
    assert [(row["session_date"], row["window"]) for row in evidence["events"]] == [
        ("2025-04-07", "primary"),
        ("2026-08-31", "confirmation"),
    ]
    for event in evidence["events"]:
        rows = [row for row in daily if row["session_date"] == event["session_date"]]
        assert rows == [daily[i] for i in event["feature_source_rows"]]
        assert len(rows) == len({row["asset"] for row in rows}) == event["assets"] == 6
        for name, field in {
            "surface_cells": "surface_populated_cells_mean",
            "atm_presence": "atm_0_1dte_presence_pct",
            "origins_per_asset": "N_origins",
        }.items():
            values = [float(row[field]) for row in rows]
            suffix = "_percent" if name == "atm_presence" else ""
            assert min(values) == event[f"{name}_min{suffix}"]
            assert max(values) == event[f"{name}_max{suffix}"]
        for delta in event["deltas"]:
            row = top[delta["source_row_zero_based"]]
            assert row["session_date"] == event["session_date"]
            assert row["window"] == event["window"] and row["family"] == delta["family"]
            assert row["horizon_minutes"] == "15" and row["ranked_information_set"] == "B2"
            assert float(row["B2_over_B1"]) == delta["delta"]
        for minute in event.get("AMZN_event", []):
            row = bars[minute["source_row_zero_based"]]
            assert row["asset"] == "AMZN" and row["session_date"] == event["session_date"]
            assert row["bar_start_ny"] == minute["bar_start_ny"]
            assert int(float(row["minutes_from_event"])) == minute["minutes_from_event"]
            assert float(row["close_to_close_log_return_bp"]) == minute["return_bp"]
            assert float(row["volume_over_session_median"]) == minute["volume_over_session_median"]
    assert round(evidence["events"][1]["surface_cells_min"], 1) == 20.4


def test_favorable_frequency_and_literature_do_not_create_a_percent_benchmark() -> None:
    evidence = defense.source(EVIDENCE_PATH)
    frequency = evidence["frequency"]
    losses = defense.source("artifacts/rp4_v4_b2_rv15/session_losses.csv")
    changes = [
        float(row["loss__log_ridge_harq__B1"]) - float(row["loss__log_ridge_harq__B2"])
        for row in losses
    ]
    assert frequency["sessions"] == len(changes) == 419
    assert frequency["favorable_sessions"] == sum(value > 0 for value in changes) == 249
    assert frequency["adverse_sessions"] == sum(value < 0 for value in changes) == 170
    assert frequency["tied_sessions"] == sum(value == 0 for value in changes) == 0
    assert frequency["favorable_percent"] == 100 * 249 / 419
    summary = defense.source("artifacts/rp4_v4_b2_rv15/summary.json")
    for group, prefix, expected in (
        ("assets", "asset_", 6),
        ("blocks", "chronological_block_", 3),
    ):
        rows = [
            row
            for row in summary["robustness"]
            if row["family"] == "log_ridge_harq"
            and row["contrast"] == "B2_over_B1"
            and row["subset"].startswith(prefix)
        ]
        assert frequency[group] == len(rows) == expected
        assert frequency[f"positive_{group}"] == sum(row["estimate"] > 0 for row in rows)
    literature = evidence["literature"]
    assert literature["doi"] == "10.1016/j.jeconom.2015.10.007" and literature["year"] == 2016
    assert literature["comparable_percent_verified"] is False
    assert literature["percentage_from_paper_reported"] is None
    qa = (original_path(PACKAGE / "examiner_qa.md")).read_text("utf-8")
    assert literature["url"] in qa and literature["metadata_url"] in qa
