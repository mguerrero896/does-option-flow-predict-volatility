"""Bind current public claims to saved inference, without fitting or resampling."""

from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from statistics import fmean, median, quantiles, stdev

import pytest
from scripts import generate_canonical_state as producer

ROOT = Path(__file__).resolve().parents[2]
PLACEBO = ROOT / "artifacts/rp4_robustness_public_v1"
PLACEBO_PREFIX = "placebo_log_ridge_harq_rv15_"


def _placebo_rows(suffix: str) -> list[dict[str, str]]:
    with (PLACEBO / (PLACEBO_PREFIX + suffix)).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_placebo_import_preserves_closed_hashes_and_public_scope() -> None:
    receipt = json.loads((PLACEBO / "import_receipt.json").read_text("utf-8"))
    report = receipt["report"]
    assert (
        hashlib.sha256((ROOT / report["path"]).read_bytes()).hexdigest() == report["public_sha256"]
    )
    assert report["byte_identical"] is False and report["transformations"]
    expected = {
        PLACEBO_PREFIX + name
        for name in (
            "summary.csv",
            "summary.json",
            "draws.csv",
            "session_deltas.csv",
            "complete_receipt.json",
        )
    }
    assert {entry["path"] for entry in receipt["files"]} == expected
    assert len(receipt["files"]) == 5
    for entry in receipt["files"]:
        assert (
            hashlib.sha256((PLACEBO / entry["path"]).read_bytes()).hexdigest()
            == entry["public_sha256"]
        )
        if entry["byte_identical"]:
            assert entry["public_sha256"] == entry["source_sha256"]
            assert not entry["transformations"]
        else:
            assert entry["transformations"] and entry["path"].endswith(".json")
    assert hashlib.sha256(
        (PLACEBO / (PLACEBO_PREFIX + "summary.csv")).read_bytes()
    ).hexdigest() == ("b02d927e789297f5667507c40320c2316f3f8a640de8a2852d048c64c2ef2e73")
    close = receipt["source_close"]
    assert close["status"] == "COMPLETE_CONTRACT_PASS" and close["contract_exit_code"] == 0
    sources = {entry["path"]: entry["source_sha256"] for entry in receipt["files"]}
    assert close["summary_sha256"] == sources[PLACEBO_PREFIX + "summary.json"]
    assert close["receipt_sha256"] == sources[PLACEBO_PREFIX + "complete_receipt.json"]
    assert receipt["scientific_model_fits_during_import"] == 0
    assert receipt["primary_statistics_changed"] is False
    assert receipt["licensed_granular_data_imported"] is False
    public_receipt = json.loads(
        (PLACEBO / (PLACEBO_PREFIX + "complete_receipt.json")).read_text("utf-8")
    )
    assert public_receipt["status"] == "COMPLETE" and public_receipt["count"] == 50
    assert "command_argv" not in public_receipt
    assert "executable" not in public_receipt["environment"]
    assert all("filepath" not in item for item in public_receipt["environment"]["threadpools"])


def test_placebo_saved_aggregation_and_empirical_rank() -> None:
    rows = _placebo_rows("summary.csv")
    assert len(rows) == 1
    summary = rows[0]
    assert summary["horizon"] == "15" and summary["family"] == "log_ridge_harq"
    draws = _placebo_rows("draws.csv")
    assert len(draws) == int(summary["permutations"]) == 50
    assert {int(row["k"]) for row in draws} == set(range(50))
    sessions: dict[int, dict[str, float]] = defaultdict(dict)
    for row in _placebo_rows("session_deltas.csv"):
        k = int(row["k"])
        assert row["session_date"] not in sessions[k]
        sessions[k][row["session_date"]] = float(row["delta"])
    assert set(sessions) == set(range(50))
    for row in draws:
        k = int(row["k"])
        assert int(row["seed"]) == 20260908 + k
        assert len(sessions[k]) == int(row["N_sessions"]) == 419
        assert set(sessions[k]) == set(sessions[0])
        assert int(row["N_origins"]) == 160832
        assert fmean(sessions[k].values()) == pytest.approx(float(row["delta"]), abs=1e-15)
    values = [float(row["delta"]) for row in draws]
    observed = float(summary["observed_delta"])
    exceedances = sum(value >= observed for value in values)
    assert exceedances == int(summary["exceedances"]) == 12
    assert (1 + exceedances) / (len(values) + 1) == float(summary["p_empirical"])
    assert (
        1 + sum(value < observed for value in values)
        == int(summary["observed_rank_ascending"])
        == 39
    )
    for field, actual in {
        "mean": fmean(values),
        "median": median(values),
        "sd": stdev(values),
        "minimum": min(values),
        "maximum": max(values),
        "percentile_2_5": quantiles(values, n=40, method="inclusive")[0],
        "percentile_97_5": quantiles(values, n=40, method="inclusive")[-1],
    }.items():
        assert actual == pytest.approx(float(summary[field]), abs=1e-15)


def test_placebo_current_values_match_imported_summary_without_changing_headline() -> None:
    summary = _placebo_rows("summary.csv")[0]
    report = (ROOT / "docs/rp4/robustness_committed_v1_placebo_linear_rv15.md").read_text("utf-8")
    for field in (
        "observed_delta",
        "mean",
        "median",
        "sd",
        "minimum",
        "maximum",
        "percentile_2_5",
        "percentile_97_5",
        "p_empirical",
    ):
        assert summary[field] in report
    current = (ROOT / "docs/CURRENT.md").read_text("utf-8").replace("**", "")
    paragraph = next(
        line for line in current.splitlines() if line.startswith("Placebo (completed):")
    )
    assert (
        f"placebo mean {float(summary['mean']):.6f} "
        f"vs observed {float(summary['observed_delta']):.6f}" in paragraph
    )
    assert f"empirical p = {float(summary['p_empirical']):.3f}" in paragraph
    assert f"{summary['exceedances']} of {summary['permutations']}" in paragraph
    assert "Timely order flow is not demonstrated" in paragraph
    assert "registered decision is unchanged" in paragraph
    assert "300 and 60 seconds: not yet completed" in paragraph
    assert "does not identify its causal source" in paragraph
    primary = next(
        claim
        for claim in producer.build_current_claims()
        if claim["selector"]
        == {
            "horizon_minutes": 15,
            "window": "primary",
            "family": "log_ridge_harq",
            "contrast": "B2_over_B1",
        }
    )
    assert float(summary["observed_delta"]) == primary["numbers"]["estimate"]


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
