"""Complete v5 translations preserve closed aggregates and distinguish post hoc work."""

from __future__ import annotations

import csv
import hashlib
import json
import re
from decimal import Decimal
from pathlib import Path

from scripts.build_rp4_v5_english import LABEL, TRANSLATIONS, translated_document
from scripts.rp4_archive_sources import assert_historical_sha256, original_path, public_path
from tests.contract.rp4_translation_checks import historical_links, without_link_targets

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "docs/archive/rp4/presentation_originals"
RUN = "artifacts/rp4_v5_run_a3_20260908/reports/5_control/"
PART34 = "artifacts/rp4_v5_part34/"


def numeric_values(text: str, *, spanish: bool) -> list[Decimal]:
    text = without_link_targets(text)
    text = re.sub(r"`(?:[A-Z]:[/\\]|private-input/)[^`]*`", "", text)
    text = re.sub(r'"(?:[A-Z]:[/\\]|private-input/)[^"\n]*"', "", text)
    if spanish:
        text = re.sub(r"(?<![\d.])0,(\d+)", r"0.\1", text)
        # Source mixes machine lists, decimal points and Spanish prose notation.
        # Explicit replacements avoid treating grid separators as decimal marks.
        for old, new in (
            ("22,49", "22.49"),
            ("28,22", "28.22"),
            ("193,2075962", "193.2075962"),
            ("242,4896918", "242.4896918"),
            ("1,0104506", "1.0104506"),
            ("1,010", "1.010"),
            ("9.999", "9999"),
            ("1.193", "1193"),
            ("1.634", "1634"),
            ("2.095", "2095"),
        ):
            text = re.sub(r"(?<![\d.])" + re.escape(old) + r"(?![\d.])", new, text)
    else:
        for old, new in (
            ("9,999", "9999"),
            ("1,193", "1193"),
            ("1,634", "1634"),
            ("2,095", "2095"),
        ):
            text = text.replace(old, new)
    return [Decimal(value) for value in re.findall(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", text)]


def test_complete_v5_translation_and_safe_renderer() -> None:
    sources = json.loads((ARCHIVE / "original_paths.json").read_bytes())
    receipt = json.loads((ROOT / "docs/rp4/v5_translation_receipt.json").read_bytes())
    for row in receipt["documents"]:
        actual = (ROOT / row["path"]).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(actual).hexdigest() == row["english_sha256"]
    for name, digest in receipt["presentation_and_contracts_sha256"].items():
        actual = (ROOT / name).read_bytes().replace(b"\r\n", b"\n")
        assert hashlib.sha256(actual).hexdigest() == digest
    for name in TRANSLATIONS:
        logical = ROOT / "docs/rp4" / name
        entry = sources[logical.relative_to(ROOT).as_posix()]
        assert_historical_sha256(logical, entry["sha256"])
        old = original_path(logical).read_text(encoding="utf-8")
        destination = public_path(logical)
        new = destination.read_text(encoding="utf-8")
        assert numeric_values(old, spanish=True) == numeric_values(new, spanish=False), name
        assert re.findall(r"[0-9a-f]{64}", old) == re.findall(r"[0-9a-f]{64}", new), name
        assert historical_links(old, logical) == historical_links(new, destination), name
        assert len(re.split(r"\n\s*\n", old.strip())) + 1 == len(
            re.split(r"\n\s*\n", new.strip())
        ), name
        assert new.count(LABEL) == 1
        assert "capital_go=false" in new
        assert not re.search(r"[A-Z]:[/\\]", new)
        assert new == translated_document(name), name


def test_five_family_table_matches_saved_closed_aggregates() -> None:
    report = public_path(ROOT / "docs/rp4/results_v5.md").read_text(encoding="utf-8")
    with public_path(ROOT / RUN / "table.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert len(rows) == 24
    expected = {
        "seasonal_persistence",
        "log_har",
        "log_ridge_harq",
        "log_elastic_net",
        "lightgbm_qlike",
    }
    completed = [row for row in rows if row["family"] in expected]
    assert len(completed) == 15
    for row in rows:
        assert row["horizon_minutes"] == "15"
        metrics = [
            "NOT AVAILABLE" if not row[column] else format(float(row[column]), ".8g")
            for column in ("qlike", "mae", "rmse")
        ]
        start = "| v5 | 15 | " + row["family"] + " | " + row["information_set"]
        assert start + " | " + " | ".join(metrics) + " |" in report
        if row in completed:
            assert row["N_sessions"] == "419" and row["N_origins"] == "160832"
    saved = json.loads(public_path(ROOT / RUN / "summary.json").read_bytes())
    assert saved["status"] == "COMPLETE"
    assert set(saved["registered_base_families"]) == expected
    assert saved["decision"]["h1_gate_rejected"] is False
    assert saved["decision"]["nominal_status"] == "NOT_SATISFIED"
    assert saved["decision"]["v4_headline_replaced"] is False
    top2 = next(row for row in saved["selector_chains"] if row["family"] == "ensemble_top2")
    assert top2["p_holm_chain"] == 0.0498
    assert top2["p_holm_chain_bonferroni5"] == 0.249
    assert "v4 retains the headline; there is no direct v5/v4 test" in report
    assert "## Post hoc sensitivity" in report
    assert "results attributed to the auditor, not reproduced in this receipt" in report
    assert "the exact cause of that discrepancy cannot be confirmed" in report


def test_public_import_is_an_explicit_aggregate_and_code_allowlist() -> None:
    receipt = json.loads(
        (ROOT / "artifacts/rp4_v5_public_import/allowlist_receipt.json").read_bytes()
    )
    assert receipt["source_bytes_stable_during_copy"] is True
    assert receipt["source_part34_receipt_entries_verified"] == 25
    assert receipt["closed_5_control_outputs_verified"] == 9
    assert receipt["private_inputs_copied"] is False
    assert receipt["per_origin_forecasts_copied"] is False
    assert receipt["operational_or_worker_receipts_copied"] is False
    for entry in receipt["allowlist"]:
        logical = ROOT / entry["source_relative_path"]
        assert_historical_sha256(logical, entry["sha256"])
        assert logical.suffix not in {".parquet", ".feather", ".pkl", ".npy"}
        assert "/sessions/" not in entry["source_relative_path"]
        assert "_operations/" not in entry["source_relative_path"]
        if logical.suffix == ".csv":
            with public_path(logical).open(encoding="utf-8", newline="") as handle:
                reader = csv.DictReader(handle)
                columns = set(reader.fieldnames or ())
            assert not columns & {
                "asset",
                "origin_minute",
                "target",
                "prediction",
                "forecast",
                "coefficient",
                "price",
                "strike",
                "bid",
                "ask",
            }
    posthoc = json.loads(public_path(ROOT / PART34 / "summary.json").read_bytes())
    assert posthoc["status"] == "VERIFIED_HISTORICAL_POST_HOC"
    assert posthoc["refits"] == posthoc["prospective_data_reads"] == 0
    assert posthoc["sessions"] == 419 and posthoc["session_family_records"] == 2095
