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
    assert "60-second cutoff: not yet completed" not in current
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


@pytest.mark.parametrize(
    ("cutoff", "contrast_sha256"),
    (
        (60, "65cce2e2c23602249ce2eb1f1f00917729580689d14900134a59ded89bc0d698"),
        (300, "976c95b896f9f2a836ee53a985e8462f7a6cfe2139690d66e264367f1ab78df4"),
    ),
)
def test_pit_import_is_closed_and_hash_bound(cutoff: int, contrast_sha256: str) -> None:
    prefix = f"pit_{cutoff}"
    imported = json.loads((PLACEBO / "import_receipt.json").read_text("utf-8"))[prefix]
    entries = imported["files"]
    assert len(entries) == 5
    assert {entry["path"] for entry in entries} == {
        f"{prefix}_{suffix}"
        for suffix in (
            "summary_receipt.json",
            "contrasts.csv",
            "session_losses.csv",
            "availability.csv",
            "fit_receipt.json",
        )
    }
    for entry in entries:
        assert (
            hashlib.sha256((PLACEBO / entry["path"]).read_bytes()).hexdigest()
            == entry["public_sha256"]
        )
        if entry["path"].endswith(".csv"):
            assert entry["byte_identical"] and not entry["transformations"]
            assert entry["source_sha256"] == entry["public_sha256"]
        else:
            assert not entry["byte_identical"] and entry["transformations"]
    assert (
        hashlib.sha256((PLACEBO / f"{prefix}_contrasts.csv").read_bytes()).hexdigest()
        == contrast_sha256
    )
    close = imported["source_close"]
    assert close["status"] == "COMPLETE_CONTRACT_PASS" and close["contract_exit_code"] == 0
    sources = {entry["path"]: entry["source_sha256"] for entry in entries}
    assert close["receipt_sha256"] == sources[f"{prefix}_fit_receipt.json"]
    assert close["summary_sha256"] == sources[f"{prefix}_summary_receipt.json"]
    assert imported["scientific_model_fits_during_import"] == 0
    assert imported["licensed_granular_data_imported"] is False
    assert imported["primary_statistics_changed"] is False
    summary = json.loads((PLACEBO / f"{prefix}_summary_receipt.json").read_text("utf-8"))
    assert summary["status"] == "COMPLETE"
    for name, digest in summary["output_sha256"].items():
        assert digest == sources[name]
    fit = json.loads((PLACEBO / f"{prefix}_fit_receipt.json").read_text("utf-8"))
    assert fit["status"] == "COMPLETE" and fit["cutoff"] == cutoff
    assert "executable" not in fit["environment"]


@pytest.mark.parametrize(("cutoff", "positive_sessions"), ((60, 277), (300, 217)))
def test_pit_current_matches_saved_contrasts_and_120_primary_control(
    cutoff: int, positive_sessions: int
) -> None:
    prefix = f"pit_{cutoff}"
    with (PLACEBO / f"{prefix}_contrasts.csv").open(encoding="utf-8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    contrasts = {(int(row["cutoff_seconds"]), row["contrast"]): row for row in rows}
    assert len(rows) == len(contrasts) == 4
    assert set(contrasts) == {
        (seconds, contrast)
        for seconds in (120, cutoff)
        for contrast in ("B1_over_B0", "B2_over_B1")
    }
    with (PLACEBO / f"{prefix}_session_losses.csv").open(encoding="utf-8", newline="") as stream:
        losses = list(csv.DictReader(stream))
    assert len(losses) == len({row["session_date"] for row in losses}) == 419
    means = {name: fmean(float(row[name]) for row in losses) for name in ("B0", "B1", "B2")}
    assert sum(float(row["B1"]) > float(row["B2"]) for row in losses) == positive_sessions
    current = (ROOT / "docs/CURRENT.md").read_text("utf-8").replace("**", "")
    paragraph = next(
        line
        for line in current.splitlines()
        if line.startswith("Point-in-time sensitivity (complete: 60, 120 and 300 seconds)")
    )
    table_row = next(line for line in current.splitlines() if line.startswith(f"| {cutoff} |"))
    assert str(positive_sessions) in table_row
    summary = json.loads((PLACEBO / f"{prefix}_summary_receipt.json").read_text("utf-8"))
    for saved in summary["summary"]:
        row = contrasts[(saved["cutoff_seconds"], saved["contrast"])]
        for name, value in saved.items():
            assert (float(row[name]) if isinstance(value, (int, float)) else row[name]) == value
    for contrast, baseline, richer in (("B1_over_B0", "B0", "B1"), ("B2_over_B1", "B1", "B2")):
        row = contrasts[(cutoff, contrast)]
        delta = fmean(float(loss[baseline]) - float(loss[richer]) for loss in losses)
        assert delta == pytest.approx(float(row["estimate"]), abs=1e-15, rel=0)
        assert f"{100 * delta / means[baseline]:.3f}%" in table_row
        assert f"{float(row['p_raw']):.4f}" in table_row
        assert f"{float(row['estimate']):.6f}" in table_row
        control = contrasts[(120, contrast)]
        claim = next(
            claim
            for claim in producer.build_current_claims()
            if claim["selector"]
            == {
                "horizon_minutes": 15,
                "window": "primary",
                "family": "log_ridge_harq",
                "contrast": contrast,
            }
        )
        for field in ("estimate", "ci_low", "ci_high", "N_sessions", "N_origins"):
            assert float(control[field]) == claim["numbers"][field]
        assert float(control["p_raw"]) == claim["numbers"]["p_for_decision"]
    for row in rows:
        assert row["N_sessions"] == "419" and row["N_origins"] == "160832"
        assert row["role"] == "POST_PRIMARY_SOURCE_TIME_PROXY_SENSITIVITY"
    flow = contrasts[(cutoff, "B2_over_B1")]
    assert (float(flow["ci_low"]) < 0) == (cutoff == 300)
    assert float(flow["ci_high"]) > 0
    assert f"[{float(flow['ci_low']):.6f}; {float(flow['ci_high']):.6f}]" in current
    assert "60-second cutoff: not yet completed" not in current
    assert "does not strengthen the registered finding" in paragraph
    assert "300 and 60 seconds: not yet completed" not in current


def test_pit_three_cutoff_table_preserves_primary_and_monotone_flow_series() -> None:
    current = (ROOT / "docs/CURRENT.md").read_text("utf-8")
    primary_row = next(line for line in current.splitlines() if line.startswith("| 120 |"))
    primary_flow_percent = 0.0
    for claim in producer.build_current_claims():
        selector = claim["selector"]
        if selector["window"] != "primary" or selector["family"] != "log_ridge_harq":
            continue
        numbers = claim["numbers"]
        assert (
            f"+{numbers['estimate']:.6f} / {numbers['qlike_reduction_percent']:.3f}% / "
            f"{numbers['p_for_decision']:.4f}" in primary_row
        )
        if selector["contrast"] == "B2_over_B1":
            primary_flow_percent = numbers["qlike_reduction_percent"]
    with (ROOT / "artifacts/rp4_v4_b2_rv15/session_losses.csv").open(
        encoding="utf-8", newline=""
    ) as stream:
        losses = list(csv.DictReader(stream))
    positive = sum(
        float(row["loss__log_ridge_harq__B1"]) > float(row["loss__log_ridge_harq__B2"])
        for row in losses
    )
    assert len(losses) == 419 and positive == 249
    assert f"{positive}/{len(losses)}" in primary_row
    flow_percent = {120: primary_flow_percent}
    for cutoff in (60, 300):
        with (PLACEBO / f"pit_{cutoff}_session_losses.csv").open(
            encoding="utf-8", newline=""
        ) as stream:
            losses = list(csv.DictReader(stream))
        flow_percent[cutoff] = (
            100
            * fmean(float(row["B1"]) - float(row["B2"]) for row in losses)
            / fmean(float(row["B1"]) for row in losses)
        )
    assert flow_percent[60] > flow_percent[120] > flow_percent[300] > 0
    assert "decreases monotonically" in current
    assert "Stability across conservative timing assumptions is not established" in current


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
    assert len(definitions) == 3
    assert "B0 + option state" in definitions[1]
    assert "B1 + a heterogeneous option-information block" in definitions[2]
    assert "docs/B2_INTERPRETATION.md" in readme
    assert "mixed B2 block" in readme
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
        for value in ("160,832", "2,514", "419", "25 sessions"):
            assert value in prose
        assert "Independent prospective confirmation" in prose
        assert "pending" in prose
        assert "[0.000335; 0.001932]" in prose
        assert "cross-version research search is not multiplicity-adjusted" in prose.lower()
    # Detailed gate arithmetic stays on the linked evidence page, not mandatory front-page prose.
    assert "docs/CURRENT.md" in readme
    assert "H2 remains unopened" in readme
    for value in (
        "9,750",
        "0.3908",
        "0.0568",
        "both H2 gates are closed",
        "0.0918 / 0.0248",
        "0.0447 / 0.8048",
    ):
        assert value in current.replace("**", "")
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
            if name != "README.md":
                assert distinction in prose, (name, distinction)
    payload = json.loads((ROOT / "docs/figures/public_refresh/glossary.json").read_text("utf-8"))
    current = (ROOT / "docs/CURRENT.md").read_text("utf-8")
    glossary = (ROOT / "docs/glossary.md").read_text("utf-8")
    definitions = [row for row in payload["method_rows"] if row["label"] in ("B0", "B1", "B2")]
    assert len(definitions) == 3
    for row in definitions:
        assert f"- **{row['label']}:** {row['meaning']}" in current
        assert f"| {row['label']} | {row['meaning']} |" in glossary
