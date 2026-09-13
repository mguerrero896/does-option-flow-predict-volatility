"""Bind completed historical reference/secondary claims to saved public aggregates."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from statistics import fmean

import pytest
from scripts import build_rp4_english_defense as defense

ROOT = Path(__file__).resolve().parents[2]
PUBLIC = ROOT / "artifacts/rp4_robustness_public_v1"


def rows(name: str) -> list[dict[str, str]]:
    with (PUBLIC / name).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def test_import_is_closed_hash_bound_and_preserves_scientific_scope() -> None:
    for name, expected in {
        "reference_contrasts.csv": (
            "3e59dcbab5760464b0abf41ca2f748016e7d42a51542c195c3cee6687a2e862e"
        ),
        "secondary_metrics.csv": "66ba437b3878bb4b2c5241863236b0eaf59712eaf3be8a63bbe40a1baca56f88",
    }.items():
        assert hashlib.sha256((PUBLIC / name).read_bytes()).hexdigest() == expected
    receipt = json.loads((PUBLIC / "import_receipt.json").read_text("utf-8"))
    for stage, count in (("references", 11), ("secondary_metrics", 4)):
        imported = receipt[stage]
        assert len(imported["files"]) == count
        sources = {}
        for entry in imported["files"]:
            name = entry["path"]
            sources[name] = entry["source_sha256"]
            public = (PUBLIC / name).read_bytes()
            assert hashlib.sha256(public).hexdigest() == entry["public_sha256"]
            if name.endswith(".csv"):
                assert entry["byte_identical"] and not entry["transformations"]
                assert entry["public_sha256"] == entry["source_sha256"]
            else:
                assert not entry["byte_identical"] and entry["transformations"]
        close = imported["source_close"]
        assert close["status"] == "COMPLETE_CONTRACT_PASS"
        assert close["contract_exit_code"] == 0
        assert close["receipt_sha256"] == sources[f"{stage}_receipt.json"]
        assert imported["source_close_sha256"] == sources[f"close_{stage}.json"]
        assert close["presentation_sha256"] == sources[f"{stage}.md"]
        assert imported["scientific_model_fits_during_import"] == 0
        assert imported["primary_statistics_changed"] is False
        assert imported["licensed_granular_data_imported"] is False
        result = json.loads((PUBLIC / f"{stage}_receipt.json").read_text("utf-8"))
        assert result["status"] == "COMPLETE"
        assert "executable" not in result["environment"]
        assert "command_argv" not in result
        if stage == "references":
            for name, expected in result["output_sha256"].items():
                assert sources[name] == expected
        else:
            assert result["new_fits"] == close["new_fits"] == 0
            assert sources["secondary_metrics.csv"] == result["output_sha256"]


def test_reference_claims_use_the_correct_matched_session_losses() -> None:
    contrasts = rows("reference_contrasts.csv")
    assert len(contrasts) == 24
    assert len({(r["horizon"], r["reference"], r["family"], r["set"]) for r in contrasts}) == 24
    current = (ROOT / "docs/CURRENT.md").read_text("utf-8").replace("**", "")
    paragraph = next(p for p in current.splitlines() if p.startswith("Reference models"))
    assert "24" in paragraph and "p = 0.0001" in paragraph
    for row in rows("reference_qlike.csv"):
        horizon, reference = row["horizon"], row["reference"]
        losses = rows(f"reference_session_losses_rv{horizon}_{reference}.csv")
        n = 419 if reference == "HAR_dwm" else 417
        excluded = 0 if reference == "HAR_dwm" else {"15": 1778, "30": 1873}[horizon]
        assert int(row["N_sessions"]) == len(losses) == n
        assert len({entry["session_date"] for entry in losses}) == n
        assert int(row["N_excluded"]) == excluded
        assert int(row["N_origins"]) == 160832 - excluded
        mean_reference = fmean(float(entry["reference_loss"]) for entry in losses)
        assert float(row["estimate"]) == pytest.approx(mean_reference, abs=1e-14)
        assert f"{float(row['estimate']):.8f}" in paragraph
        for contrast in contrasts:
            if (contrast["horizon"], contrast["reference"]) != (horizon, reference):
                continue
            field = f"loss__{contrast['family']}__{contrast['set']}"
            model_mean = fmean(float(entry[field]) for entry in losses)
            assert float(contrast["model_qlike"]) == pytest.approx(model_mean, abs=1e-14)
            assert float(contrast["estimate"]) == pytest.approx(mean_reference - model_mean)
            assert float(contrast["estimate"]) > 0
            assert float(contrast["p_raw"]) == 0.0001
            assert contrast["role"] == "POST_PRIMARY_NOMINAL_ROBUSTNESS"
            assert int(contrast["N_sessions"]) == n
            assert int(contrast["N_excluded"]) == excluded
    assert "nominal post-primary comparisons" in paragraph
    assert "nothing changes the headline or registered sequence" in paragraph


def test_secondary_claims_bind_all_saved_rows_and_keep_descriptive_limits() -> None:
    secondary = rows("secondary_metrics.csv")
    keys = {(r["horizon"], r["window"], r["family"], r["set"], r["metric"]) for r in secondary}
    assert len(secondary) == len(keys) == 72
    assert keys == {
        (horizon, window, family, information_set, metric)
        for horizon in ("5", "15", "30")
        for window in ("primary", "confirmation")
        for family in ("log_ridge_harq", "lightgbm_qlike")
        for information_set in ("B0", "B1", "B2")
        for metric in ("MAE", "RMSE")
    }
    current = (ROOT / "docs/CURRENT.md").read_text("utf-8").replace("**", "")
    paragraph = next(p for p in current.splitlines() if p.startswith("Secondary metrics"))
    for row in secondary:
        assert row["role"] == "DESCRIPTIVE_NO_TEST"
        assert float(row["ci_low"]) <= float(row["estimate"]) <= float(row["ci_high"])
        assert int(row["N_sessions"]) == (419 if row["window"] == "primary" else 25)
        if (row["horizon"], row["window"], row["family"]) == ("15", "primary", "log_ridge_harq"):
            assert f"{float(row['estimate']):.7e}" in paragraph
    assert "72" in paragraph and "zero new fits" in paragraph
    assert "descriptive without tests" in paragraph
    assert "nothing changes the headline or registered sequence" in paragraph
    package = ROOT / "docs/rp4/DEFENSE_PACKAGE/revision_2/correction_7"
    for name in ("examiner_qa.md", "defense_slides.md"):
        text = (package / name).read_text("utf-8")
        reference = next(
            line
            for line in text.splitlines()
            if line.startswith(("| Model comparison:", "| Seasonal persistence/HAR-RV/"))
        )
        secondary_line = next(
            line
            for line in text.splitlines()
            if line.startswith(("| Secondary MAE", "| Asset/regime analysis;"))
        )
        assert "COMPLETED" in reference and "DECLARED DEVIATION" in reference
        assert "COMPLETED" in secondary_line
        if name == "defense_slides.md":
            assert "historical **PENDING** inspection status" in secondary_line
        else:
            assert "PENDING" not in secondary_line


def test_defense_update_rejects_unreceipted_status_changes(tmp_path: Path) -> None:
    for name in defense.DOCUMENTS:
        (tmp_path / name).write_bytes((defense.PACKAGE / name).read_bytes())
    path = tmp_path / "examiner_qa.md"
    source = path.read_text("utf-8")
    assert "**COMPLETED** reference comparisons" in source
    path.write_text(
        source.replace(
            "**COMPLETED** reference comparisons", "**PENDING** reference comparisons", 1
        ),
        encoding="utf-8",
    )
    with pytest.raises(AssertionError, match="examiner_qa.md"):
        defense.build(tmp_path)
