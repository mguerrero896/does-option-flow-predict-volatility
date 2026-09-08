"""Build the English defense presentation from its retained numeric bindings.

Markdown is the editable presentation source. No model, prediction, bootstrap or
prospective payload is read. The original package remains an immutable archive.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.util
import io
import json
import re
import sys
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "docs/rp4/DEFENSE_PACKAGE/revision_2/correction_7"
ARCHIVE = ROOT / "docs/archive/rp4/DEFENSE_PACKAGE/revision_2/correction_7"
DOCUMENTS = ("executive_summary.md", "examiner_qa.md", "defense_slides.md")
ENGLISH_MARKER = "## Executive summary — English"
SOURCE_MATRIX_SHA256 = "ba55658de19b42fd810c9f558dad023b94a7befc3f81c93e356f5e8e37f1bb97"


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def readers() -> ModuleType:
    """Reuse the existing documentary reader instead of reimplementing selectors."""
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    spec = importlib.util.spec_from_file_location(
        "english_defense_readers", ROOT / "tests/contract/test_rp4_defense_package.py"
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def original(name: str) -> Path:
    path = ARCHIVE / name
    return path.with_suffix(".md.original") if path.suffix == ".md" else path


def source_rows() -> list[dict[str, str]]:
    payload = original("claims_matrix.csv").read_bytes()
    assert digest(payload) == SOURCE_MATRIX_SHA256, "Historical matrix changed"
    rows = list(csv.DictReader(io.StringIO(payload.decode("utf-8"))))
    return [row for row in rows if row["kind"] == "package_number"]


def display_value(row: dict[str, str]) -> str:
    value = row["claim"]
    if row["rendering"].endswith("|es"):
        value = value.translate(str.maketrans(",.", ".,"))
    return value


def number_matches(text: str, reader: ModuleType) -> list[re.Match[str]]:
    """Keep positions while masking the same non-prose spans as the reader."""
    mask = text

    def blank(match: re.Match[str]) -> str:
        return " " * len(match[0])

    for pattern in (r"```.*?```", r"<!--.*?-->"):
        mask = re.sub(pattern, blank, mask, flags=re.S)
    mask = re.sub(
        r"!?\[([^\]]*)\]\([^)]*\)",
        lambda m: " " * (m.start(1) - m.start()) + m[1] + " " * (m.end() - m.end(1)),
        mask,
    )
    mask = re.sub(r"https?://\S+", blank, mask)
    mask = re.sub(
        r"`([^`]+)`",
        lambda m: blank(m) if re.search(r"/|_|[a-f0-9]{32}", m[1]) else " " + m[1] + " ",
        mask,
    )
    mask = re.sub(r"(?m)^(#{1,6}\s+)?\d+\.\s+", blank, mask)
    matches = list(reader.NUMBER.finditer(mask))
    assert [match[0] for match in matches] == reader.tokens(text)
    return matches


def build(package: Path = PACKAGE) -> dict[str, bytes]:
    reader = readers()
    rows = source_rows()
    original_summary = original("executive_summary.md").read_text("utf-8")
    spanish_count = len(reader.tokens(original_summary.split(ENGLISH_MARKER)[0]))
    assert spanish_count == 80 and len(rows) == 1944
    summary_index = 0
    output_rows = []
    bindings: dict[str, list[dict[str, str]]] = {name: [] for name in DOCUMENTS}
    for old in rows:
        row = old.copy()
        document = row["source_document"]
        role = "current_english" if document in DOCUMENTS else "historical_external"
        if document == "executive_summary.md":
            if summary_index < spanish_count:
                role = "duplicate_spanish_summary"
            summary_index += 1
        row["display_value"] = display_value(row)
        row["presentation_role"] = role
        row["context"] = {
            "current_english": "English presentation; original value and selector retained.",
            "historical_external": "Historical external document; original numeric binding kept.",
            "duplicate_spanish_summary": (
                "Historical Spanish summary rendering; English text retained without duplication."
            ),
        }[role]
        if role == "current_english":
            bindings[document].append(row)
        output_rows.append(row)
    assert len(output_rows) == len(rows)
    output = {}
    for name in DOCUMENTS:
        text = (package / name).read_text("utf-8")
        matched = number_matches(text, reader)
        selected = bindings[name]
        assert len(matched) == len(selected), f"Numeric occurrence count changed: {name}"
        for match, row in reversed(list(zip(matched, selected, strict=True))):
            assert match[0] in {row["claim"], row["display_value"]}, (
                name,
                row["claim_id"],
                match[0],
                row["claim"],
            )
            text = text[: match.start()] + row["display_value"] + text[match.end() :]
        assert reader.tokens(text) == [row["display_value"] for row in selected]
        output[name] = text.encode("utf-8")
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=list(output_rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(output_rows)
    output["claims_matrix.csv"] = stream.getvalue().encode("utf-8")
    historical_manifest = json.loads(original("evidence_manifest.json").read_text("utf-8"))
    manifest = {
        "schema": "rp4-english-defense-presentation-v1",
        "language": "en",
        "source_matrix_sha256": SOURCE_MATRIX_SHA256,
        "source_sha256": historical_manifest["source_sha256"],
        "source_package": ARCHIVE.relative_to(ROOT).as_posix(),
        "source_manifest_sha256": digest(original("evidence_manifest.json").read_bytes()),
        "producer": Path(__file__).relative_to(ROOT).as_posix(),
        "producer_sha256": digest(Path(__file__).read_bytes()),
        "document_sha256": {name: digest(payload) for name, payload in output.items()},
        "readme_sha256": digest((package / "README.md").read_bytes()),
        "pdf_sha256": digest((package / "executive_summary.pdf").read_bytes()),
        "layout_receipt_sha256": digest((package / "summary_layout_receipt.json").read_bytes()),
        "historical_numeric_bindings": len(output_rows),
        "visible_numeric_bindings": {name: len(value) for name, value in bindings.items()},
        "duplicate_spanish_summary_bindings_retained": spanish_count,
        "external_historical_bindings_retained": sum(
            row["presentation_role"] == "historical_external" for row in output_rows
        ),
        "invariant_fields": [
            "claim_id",
            "claim",
            "artifact",
            "artifact_sha256",
            "selector",
            "rendering",
        ],
        "new_scientific_fits": 0,
        "new_bootstraps": 0,
        "new_statistical_results": 0,
        "sealed_payloads_read": 0,
        "research_only": True,
        "capital_go": False,
    }

    def encode(value: object) -> bytes:
        return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode()

    output["evidence_manifest.json"] = encode(manifest)
    receipt = {
        "schema": "rp4-english-defense-translation-receipt-v1",
        "scope": "Presentation translation; no scientific registration or result superseded.",
        "historical_receipt_sha256": digest(original("receipt.json").read_bytes()),
        "historical_verification_sha256": digest(
            original("verification_receipt.json").read_bytes()
        ),
        "original_files": json.loads((ARCHIVE / "original_paths.json").read_text("utf-8")),
        "evidence_manifest_sha256": digest(output["evidence_manifest.json"]),
        "document_sha256": manifest["document_sha256"],
        "numeric_bindings_retained": 1944,
        "visible_numeric_occurrences": sum(len(value) for value in bindings.values()),
        "omitted_visible_spanish_duplicates": spanish_count,
        "new_statistical_results": 0,
        "sealed_payloads_read": 0,
        "research_only": True,
        "capital_go": False,
    }
    output["translation_receipt.json"] = encode(receipt)
    output["receipt.json"] = encode(receipt)
    sealed = output | {
        name: (package / name).read_bytes()
        for name in (
            "README.md",
            "executive_summary.pdf",
            "summary_layout_receipt.json",
            "horizon_pit_evidence.json",
        )
    }
    output["SHA256SUMS"] = "".join(
        f"{digest(payload)}  {name}\n" for name, payload in sorted(sealed.items())
    ).encode()
    return output


def extract_english_pdf(package: Path = PACKAGE) -> None:
    """Retain the already verified English page; no re-layout or font substitution."""
    pdf_module = importlib.import_module("pypdf")

    source = original("executive_summary.pdf")
    pdf = pdf_module.PdfReader(source)
    assert len(pdf.pages) == 2
    writer = pdf_module.PdfWriter()
    writer.add_page(pdf.pages[1])
    writer.add_metadata({"/Title": "Executive summary — English"})
    with (package / "executive_summary.pdf").open("wb") as stream:
        writer.write(stream)
    extracted = pdf_module.PdfReader(package / "executive_summary.pdf").pages[0].extract_text()
    historical = json.loads(original("summary_layout_receipt.json").read_text("utf-8"))
    expected = historical["pages"][1]["extracted_text"]
    assert "".join(extracted.split()) == "".join(expected.split())
    receipt = {
        "schema": "rp4-english-summary-page-extraction-v1",
        "source_pdf_sha256": digest(source.read_bytes()),
        "source_page_index_zero_based": 1,
        "page_count": 1,
        "pdf_sha256": digest((package / "executive_summary.pdf").read_bytes()),
        "source_markdown_sha256": digest((package / "executive_summary.md").read_bytes()),
        "extracted_text": extracted,
        "source_numeric_sequence": readers().tokens(expected),
        "numeric_sequence_equal": readers().tokens(extracted) == readers().tokens(expected),
        "complete_original_english_page_retained": True,
        "historical_layout_receipt_sha256": digest(
            original("summary_layout_receipt.json").read_bytes()
        ),
    }
    (package / "summary_layout_receipt.json").write_text(
        json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8", newline="\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Compare without writing files.")
    parser.add_argument(
        "--pdf", action="store_true", help="Extract the retained English page (pypdf)."
    )
    args = parser.parse_args()
    if args.pdf:
        assert not args.check, "PDF extraction writes a presentation artifact"
        extract_english_pdf()
    outputs = build()
    changed = [
        name
        for name, data in outputs.items()
        if not (PACKAGE / name).is_file() or (PACKAGE / name).read_bytes() != data
    ]
    if not args.check:
        for name, data in outputs.items():
            (PACKAGE / name).write_bytes(data)
    print(
        json.dumps(
            {"status": "PASS" if not args.check or not changed else "DRIFT", "changed": changed}
        )
    )
    return int(args.check and bool(changed))


if __name__ == "__main__":
    raise SystemExit(main())
