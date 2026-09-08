"""Check English presentation, original numeric custody and drift rejection."""

import csv
import io
import json
import re
import shutil
from pathlib import Path

import pytest
from scripts import build_rp4_english_defense as producer
from scripts.rp4_archive_sources import assert_historical_sha256

PACKAGE = producer.PACKAGE


def test_english_defense_regenerates_and_preserves_all_original_numeric_bindings() -> None:
    generated = producer.build()
    for name, expected in generated.items():
        assert (PACKAGE / name).read_bytes() == expected, name
    rows = list(csv.DictReader(io.StringIO(generated["claims_matrix.csv"].decode())))
    originals = producer.source_rows()
    manifest = json.loads(generated["evidence_manifest.json"])
    assert len(rows) == len(originals) == manifest["historical_numeric_bindings"] == 1944
    assert manifest["visible_numeric_bindings"] == {
        "executive_summary.md": 81,
        "examiner_qa.md": 728,
        "defense_slides.md": 900,
    }
    assert manifest["duplicate_spanish_summary_bindings_retained"] == 80
    assert manifest["external_historical_bindings_retained"] == 155
    reader = producer.readers()
    checked = set()
    for row, old in zip(rows, originals, strict=True):
        for key in manifest["invariant_fields"]:
            assert row[key] == old[key], (row["claim_id"], key)
        if row["artifact"] not in checked:
            assert_historical_sha256(row["artifact"], row["artifact_sha256"])
            checked.add(row["artifact"])
        value = reader.selected(row["artifact"], row["selector"])
        assert reader.rendered(value, row["rendering"]) == row["claim"], row["claim_id"]
    for name, count in manifest["visible_numeric_bindings"].items():
        text = (PACKAGE / name).read_text("utf-8")
        visible = [
            row["display_value"]
            for row in rows
            if row["source_document"] == name and row["presentation_role"] == "current_english"
        ]
        assert len(visible) == count and reader.tokens(text) == visible
        assert not re.search(r"\b(?:Mensaje|Evidencia|Fuentes|sesiones|ventana|hipótesis)\b", text)
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text):
            if target.startswith(("http:", "https:", "#")):
                continue
            linked = (PACKAGE / target.split("#")[0]).resolve()
            assert linked.is_relative_to(producer.ROOT) and linked.is_file(), target
    assert manifest["new_statistical_results"] == manifest["sealed_payloads_read"] == 0


def test_english_summary_keeps_the_complete_original_english_pdf_page() -> None:
    receipt = json.loads((PACKAGE / "summary_layout_receipt.json").read_text("utf-8"))
    assert receipt["source_page_index_zero_based"] == receipt["page_count"] == 1
    assert receipt["complete_original_english_page_retained"] is True
    assert receipt["pdf_sha256"] == producer.digest(
        (PACKAGE / "executive_summary.pdf").read_bytes()
    )
    assert receipt["source_pdf_sha256"] == producer.digest(
        producer.original("executive_summary.pdf").read_bytes()
    )
    summary = (PACKAGE / "executive_summary.md").read_text("utf-8")
    assert receipt["source_markdown_sha256"] == producer.digest(summary.encode())
    assert producer.readers().tokens(summary) == receipt["source_numeric_sequence"]
    visible = re.sub(r"(?m)^#{1,6}\s+", "", summary)
    visible = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", visible)
    visible = re.sub(r"`([^`]*)`", r"\1", visible.replace("**", ""))
    assert "".join(visible.split()) == "".join(receipt["extracted_text"].split())
    assert receipt["numeric_sequence_equal"] is True


def test_english_producer_rejects_a_changed_scientific_number(tmp_path: Path) -> None:
    for name in (*producer.DOCUMENTS, "README.md", "executive_summary.pdf"):
        shutil.copyfile(PACKAGE / name, tmp_path / name)
    path = tmp_path / "executive_summary.md"
    original = path.read_text("utf-8")
    assert "+0.623%" in original
    path.write_text(original.replace("+0.623%", "+0.624%", 1), encoding="utf-8")
    with pytest.raises(AssertionError, match="executive_summary.md"):
        producer.build(tmp_path)
