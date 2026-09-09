"""Bind current public claims to saved inference, without fitting or resampling."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest
from scripts import generate_canonical_state as producer

ROOT = Path(__file__).resolve().parents[2]


def test_claims_preserve_saved_rows_and_closed_final_gates() -> None:
    claims = producer.build_current_claims()
    with (ROOT / "artifacts/rp4_v4_b4/primary_statistics.csv").open(encoding="utf-8") as stream:
        rows = [row for row in csv.DictReader(stream) if row["horizon_minutes"] == "15"]
    assert len(claims) == len({claim["claim_id"] for claim in claims}) == 8
    for claim, row in zip(claims, rows, strict=True):
        assert claim["status"] == row["hypothesis_status"]
        for name, value in claim["numbers"].items():
            assert value == (float(row[name]) if row[name] else None)
        assert claim["confirmatory_status"] == "NOT_INDEPENDENT_PROSPECTIVE_CONFIRMATION"
        selector = claim["selector"]
        if selector["window"] == "confirmation" and selector["contrast"] == "B2_over_B1":
            assert claim["status"] == "NOT_TESTED"
            assert claim["gate"] == "NOT_OPENED"
            assert claim["numbers"]["p_for_decision"] is None
    state = producer.build_state()
    assert state["canonical_results"]["claims"] == claims
    assert state["canonical_results"]["independent_global_confirmation"] is False


def test_claims_reject_changed_source_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    source = tmp_path / "artifacts/rp4_v4_b4/primary_statistics.csv"
    source.parent.mkdir(parents=True)
    source.write_text("changed\n", encoding="utf-8")
    monkeypatch.setattr(producer, "REPO", tmp_path)
    with pytest.raises(ValueError, match="RP4_PRIMARY_STATISTICS_DRIFT"):
        producer.build_current_claims()


def test_current_surfaces_preserve_numbers_definitions_and_limits() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    current = (ROOT / "docs/CURRENT.md").read_text(encoding="utf-8")
    definitions = [line for line in current.splitlines() if line.startswith("- **B")]
    assert definitions == [line for line in readme.splitlines() if line.startswith("- **B")]
    assert len(definitions) == 3
    assert "B0 + option state" in definitions[1]
    assert "B1 + trade-derived option flow" in definitions[2]
    for claim in producer.build_current_claims():
        selector, numbers = claim["selector"], claim["numbers"]
        if selector["window"] != "primary":
            continue
        percent = f"{numbers['qlike_reduction_percent']:+.3f}".replace("-", "\u2212")
        probability = f"{numbers['p_for_decision']:.4f}"
        family = "Linear" if selector["family"] == "log_ridge_harq" else "LightGBM"
        column = 1 if selector["contrast"] == "B1_over_B0" else 2
        for text, label, cell in (
            (current, family, f"{percent}%; {probability}"),
            (
                readme,
                "Trees" if family == "LightGBM" else family,
                f"{percent}% (p = {probability})",
            ),
        ):
            row = next(line for line in text.splitlines() if line.startswith(f"| {label} |"))
            assert row.strip("|").split("|")[column].strip() == cell
    for text in (readme, current):
        prose = " ".join(text.replace("**", "").split())
        for value in ("160,832", "2,514", "419", "25 sessions", "9,750", "0.3908", "0.0568"):
            assert value in prose
        assert "both H2 gates are closed" in prose
        assert "Independent prospective confirmation" in prose
        assert "pending" in prose
        assert "[0.000335; 0.001932]" in prose
        assert "0.0918 / 0.0248" in prose and "0.0447 / 0.8048" in prose
        assert "cross-version research search is not multiplicity-adjusted" in prose.lower()
    assert "0.001134 QLIKE units" in current


def test_public_surfaces_keep_interpretation_boundaries_and_glossary_definitions() -> None:
    for name in ("README.md", "docs/CURRENT.md", "docs/FAQ.md", "docs/glossary.md"):
        prose = " ".join((ROOT / name).read_text(encoding="utf-8").replace("**", "").split())
        for assertion in (
            "independent prospective confirmation: completed",
            "historical evidence is confirmed",
            "causality: established",
            "economic/trading value: demonstrated",
        ):
            assert assertion not in prose.lower(), (name, assertion)
        for distinction in (
            "OOS fitting \u2260 prospective scientific design",
            "Predictive information \u2260 causality",
            "Predictive information \u2260 tradability",
            "Statistical significance \u2260 economic significance",
        ):
            assert distinction in prose, (name, distinction)
    payload = json.loads((ROOT / "docs/figures/public_refresh/glossary.json").read_text("utf-8"))
    current = (ROOT / "docs/CURRENT.md").read_text("utf-8")
    glossary = (ROOT / "docs/glossary.md").read_text("utf-8")
    definitions = [row for row in payload["method_rows"] if row["label"] in ("B0", "B1", "B2")]
    assert len(definitions) == 3
    for row in definitions:
        assert f"- **{row['label']}:** {row['meaning']}" in current
        assert f"| {row['label']} | {row['meaning']} |" in glossary
