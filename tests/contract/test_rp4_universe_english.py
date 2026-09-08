"""Bind the closed eight-asset account to safe aggregates and the original v4 control."""

from __future__ import annotations

import hashlib
import json
from statistics import fmean

import pytest
from scripts import build_rp4_universe_english as report
from scripts.rp4_archive_sources import assert_historical_sha256, original_path

ROOT = report.ROOT
DATA = report.DATA
COMMIT = "a11a5c93446cb3fccafc1d1663d9d334d522f01a"
COUNTS = dict(
    zip(report.ASSETS, [26898, 26743, 26853, 26729, 26764, 26845, 26791, 26586], strict=True)
)


def test_closed_sources_and_explicit_public_projection() -> None:
    receipt = json.loads((DATA / "import_receipt.json").read_bytes())
    assert receipt["source_commit"] == COMMIT
    assert receipt["source_report_original_sha256"] == (
        "1a0418e2d6f74c39bd1bfb63ec24133d885b008aa0afeb67260588a8811851b2"
    )
    assert len(receipt["original_source_entries"]) == 11
    for row in receipt["original_source_entries"]:
        assert_historical_sha256(ROOT / row["source_path"], row["source_sha256"])
    for row in [receipt["derived_summary"], *receipt["derived_csv"]]:
        assert hashlib.sha256((ROOT / row["path"]).read_bytes()).hexdigest() == row["sha256"]
    assert {p.name for p in DATA.glob("*.csv")} == {
        "by_asset.csv",
        "coverage.csv",
        "control_six_rv15_losses.csv",
    }
    for path in DATA.glob("*.csv"):
        rows = report.read_csv(path)
        assert len(rows) <= 419
        assert not any(
            key.startswith("forecast") or key in {"actual", "origin_minute", "price", "prediction"}
            for key in rows[0]
        )
    assert receipt["scope"]["new_empirical_model_fits"] == 0
    assert receipt["scope"]["new_bootstrap_runs"] == 0
    assert receipt["scope"]["prospective_data_reads"] == 0
    assert not receipt["scope"]["forecast_columns_distributed"]
    assert not list(DATA.glob("*.sha256"))


def test_all_eight_assets_counts_and_pooled_mean_identity() -> None:
    coverage = report.read_csv(DATA / "coverage.csv")
    assert len(coverage) == 8
    assert {r["asset"]: int(r["N_origins"]) for r in coverage} == COUNTS
    assert {r["N_sessions"] for r in coverage} == {"419"}
    assert {float(r["weight_in_every_session"]) for r in coverage} == {0.125}
    assert sum(COUNTS.values()) == 214209
    rows = report.read_csv(DATA / "by_asset.csv")
    assert len(rows) == 32
    assert len({(r["asset"], r["family"], r["contrast"]) for r in rows}) == 32
    assert {r["inference_role"] for r in rows} == {"SECONDARY"}
    assert {r["cannot_rescue_primary"].lower() for r in rows} == {"true"}
    for row in rows:
        assert row["asset"] in COUNTS
        assert int(row["N_origins"]) == COUNTS[row["asset"]]
        assert row["N_sessions"] == "419" and row["horizon_minutes"] == "15"
    saved = json.loads((DATA / "primary_summary.json").read_bytes())
    assert saved["N_asset_sessions"] == 3352
    assert saved["N_sessions"] == 419 and saved["N_origins"] == 214209
    assert saved["first_session"] == "2024-10-28" and saved["last_session"] == "2026-07-31"
    assert saved["global_joint_reject"] is False
    assert saved["predeclared_closure"]["satisfied"] is True
    assert not saved["confirmation_executed"] and not saved["v5_selector_executed"]
    assert [r["p_raw"] for r in saved["contrasts"]] == [0.0208, 0.0093, 0.0794, 0.6738]
    assert [r["hypothesis_status"] for r in saved["contrasts"]] == [
        "REJECTED",
        "REJECTED",
        "NOT_REJECTED",
        "NOT_TESTED",
    ]
    assert saved["contrasts"][-1]["p_for_decision"] is None
    for pooled in saved["contrasts"]:
        selected = [
            r
            for r in rows
            if r["family"] == pooled["family"] and r["contrast"] == pooled["contrast"]
        ]
        assert len(selected) == 8
        baseline = fmean(float(r["baseline_loss"]) for r in selected)
        expanded = fmean(float(r["expanded_loss"]) for r in selected)
        assert baseline == pytest.approx(pooled["baseline_loss"], abs=1e-14)
        assert baseline - expanded == pytest.approx(pooled["estimate"], abs=1e-14)
        assert 100 * (baseline - expanded) / baseline == pytest.approx(
            pooled["percent_reduction_mean"], abs=1e-11
        )


def test_original_six_control_matches_every_public_loss_cell() -> None:
    copied = report.read_csv(DATA / "control_six_rv15_losses.csv")
    public = report.read_csv(ROOT / "artifacts/rp4_v4_b2_rv15/session_losses.csv")
    columns = [
        f"loss__{family}__{block}" for family in report.FAMILIES for block in ("B0", "B1", "B2")
    ]
    assert len(copied) == len(public) == 419
    indexed = {row["session_date"]: row for row in public}
    for row in copied:
        assert set(row) == {"session_date", *columns}
        for column in columns:
            assert float(row[column]) == float(indexed[row["session_date"]][column])
    control = json.loads(
        original_path(
            ROOT / ("artifacts/rp4_universe_v1/phase2/control_six/rv15/receipt.json")
        ).read_bytes()
    )
    assert control["status"] == "EXACT_ZERO_DIFFERENCE"
    assert control["sessions"] == 419 and control["origins"] == 160832
    assert control["session_loss_cells_compared"] == 2514
    assert control["session_deltas_compared"] == 1676
    assert control["max_abs_session_qlike_difference"] == 0
    assert control["max_abs_session_delta_difference"] == 0
    assert control["model_fits"] == control["bootstrap_reruns"] == 0
    primary = [
        r
        for r in report.read_csv(ROOT / "artifacts/rp4_v4_b4/primary_statistics.csv")
        if r["window"] == "primary" and r["horizon_minutes"] == "15"
    ]
    assert [float(r["p_raw"]) for r in primary] == [0.039, 0.0032, 0.0135, 0.628]
    assert report.result_table(primary) in report.render()


def test_complete_eight_row_appendix_and_qualifications() -> None:
    actual = report.REPORT.read_text(encoding="utf-8")
    assert actual == report.render()
    assert "## Eight-asset extension (registered, closed)" in actual
    assert "sixth read of the same sessions" in actual
    assert "first evaluation of SPY/QQQ as forecast targets" in actual
    assert (
        "**The joint claim across both families is not satisfied. V4 retains the headline.**"
        in actual
    )
    assert "No new Holm result or bootstrap is introduced here." in actual
    appendix = report.appendix_rows()
    assert len(appendix) == 8 and {r[0] for r in appendix} == set(COUNTS)
    for row in appendix:
        assert "| " + " | ".join(map(str, row)) + " |" in actual
    assert [r[-1] for r in report.transport_rows()] == ["1.1142%", "0.4177%", "1.4337%", "-0.0446%"]
    assert "neither a new sample nor independent confirmation" in actual
    assert "RESEARCH_ONLY. NOT INVESTMENT ADVICE. capital_go=false." in actual
