"""Bind successive documentary closeouts to saved evidence, without evaluation."""

import csv
import importlib.util
import json
import re
from decimal import Decimal
from pathlib import Path

from scripts.rp4_archive_sources import (
    assert_historical_sha256,
    logical_path,
    original_path,
    public_path,
)

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "docs/rp4/DEFENSE_PACKAGE/revision_2/correction_5"
TEST = "tests/contract/test_rp4_saved_holm_closeout.py"
SPEC = importlib.util.spec_from_file_location(
    "saved_holm_readers", Path(__file__).with_name("test_rp4_defense_package.py")
)
assert SPEC and SPEC.loader
readers = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(readers)
PRIVATE = r"(?i)\b(codex|claude|chatgpt|mds650|capstone)\b|[A-Za-z]:[\\/]"
PUBLIC_RESERVED_DOCS = {"docs/rp3/EXECUTION_GUIDE.md", "docs/rp3/PREREGISTRATION.md"}
PUBLIC_NOTEBOOKS = {
    "notebooks/canonical_rv30_defense.ipynb",
    "notebooks/research_pipeline.ipynb",
}


def _safe_source(name: str) -> Path:
    """Validate a source identity before checking bytes or explicit non-distribution."""
    path = (ROOT / name).resolve()
    assert path.is_relative_to(ROOT), name
    parts = Path(name).parts
    if any(re.match(r"(?:rp3|c10)(?:$|[_-])", part, re.I) for part in parts):
        assert name in PUBLIC_RESERVED_DOCS, name
    assert not any(part.lower() in {"raw", "inputs", "panels", "predictions"} for part in parts)
    assert path.suffix not in {".parquet", ".feather"}, name
    assert path.suffix != ".ipynb" or name in PUBLIC_NOTEBOOKS, name
    return path


def _safe_file(name: str) -> Path:
    path = _safe_source(name)
    assert original_path(path).is_file(), name
    return path


def assert_sealed_package(package_path: Path, current_test: str) -> None:
    """Check a manifest's complete documentary scope and the saved facts it cites."""
    package = logical_path(package_path).resolve()
    assert package.is_relative_to(ROOT)
    manifest = json.loads((original_path(package / "evidence_manifest.json")).read_text("utf-8"))
    for name in readers.DOCUMENTS:
        assert manifest["number_documents"][name] == (package / name).relative_to(ROOT).as_posix()
        assert name in manifest["document_sha256"]
    assert "README.md" in manifest["source_documents"]
    assert any(name.startswith("docs/rp4/RESULTADO_FINAL") for name in manifest["source_documents"])
    pins = manifest["source_sha256"]
    for name, expected in pins.items():
        assert_historical_sha256(_safe_source(name), expected)
    for name, expected in manifest["document_sha256"].items():
        path = (package / name).resolve()
        assert path.is_relative_to(package) and original_path(path).is_file(), name
        assert_historical_sha256(original_path(path), expected)
    with (original_path(package / "claims_matrix.csv")).open(
        encoding="utf-8", newline=""
    ) as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == len({row["claim_id"] for row in rows})
    fact_groups = {}
    assert manifest["fact_documents"]
    for kind, name in manifest["fact_documents"].items():
        assert name in pins
        fact_groups[kind] = json.loads(original_path(_safe_file(name)).read_text("utf-8"))["facts"]
    allowed_kinds = {"source_claim", "package_number", *fact_groups}
    for row in rows:
        assert row["kind"] in allowed_kinds, row["claim_id"]
        assert row["current_test"] == current_test, row["claim_id"]
        assert row["artifact_sha256"] == pins[row["artifact"]]
        assert not re.search(PRIVATE, readers.prose(row["claim"] + " " + row["context"]))
        for name, expected in json.loads(row["supporting_artifacts"]).items():
            assert pins[name] == expected
        if row["kind"] == "package_number":
            assert row["source_document"] in manifest["number_documents"]
            _safe_file(row["artifact"])
            value = readers.selected(row["artifact"], row["selector"])
            assert readers.rendered(value, row["rendering"]) == row["claim"], row["claim_id"]
        elif row["kind"] in fact_groups:
            fact = fact_groups[row["kind"]][row["claim"]]
            assert row["artifact"] == fact["artifact"]
            assert json.loads(row["selector"]) == fact["selector"]
            assert fact["sha256"] == pins[fact["artifact"]]
            _safe_file(fact["artifact"])
            value = readers.selected(fact["artifact"], json.dumps(fact["selector"]))
            if "quote" in fact:
                assert isinstance(value, str) and fact["quote"] and fact["quote"] in value
                if "line_start" in fact:
                    lines = value.splitlines()[fact["line_start"] - 1 : fact["line_end"]]
                    assert "\n".join(lines) == fact["quote"]
            else:
                assert fact["value"] == value
        else:
            assert row["source_document"] in manifest["source_documents"]
    for kind, facts in fact_groups.items():
        actual = [row["claim"] for row in rows if row["kind"] == kind]
        assert len(actual) == len(facts) and set(actual) == set(facts), kind
    for name in manifest["source_documents"]:
        passages = readers.passages(original_path(_safe_file(name)).read_text("utf-8"))
        actual = [r for r in rows if r["kind"] == "source_claim" and r["source_document"] == name]
        assert [r["claim"] for r in actual] == [readers.public_claim(p) for p in passages]
        assert [r["source_passage_sha256"] for r in actual] == [
            readers.digest(p.encode()) for p in passages
        ]
    for document, name in manifest["number_documents"].items():
        path = _safe_file(name)
        assert path.suffix == ".md"
        text = original_path(path).read_text("utf-8")
        actual = [
            r["claim"]
            for r in rows
            if r["kind"] == "package_number" and r["source_document"] == document
        ]
        assert actual == readers.tokens(text), name
        assert not re.search(PRIVATE, readers.prose(text)), name
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text):
            if not target.startswith(("http://", "https://", "#")):
                linked = (path.parent / target.split("#")[0]).resolve()
                assert linked.is_relative_to(ROOT) and public_path(linked).is_file(), target
    assert sum(r["kind"] == "source_claim" for r in rows) == manifest["source_claims"]
    assert (
        sum(r["kind"] == "package_number" for r in rows) == manifest["package_number_occurrences"]
    )
    receipt = json.loads((original_path(package / "receipt.json")).read_text("utf-8"))
    assert_historical_sha256(
        original_path(package / "evidence_manifest.json"), receipt["evidence_manifest_sha256"]
    )
    assert receipt["prior_seals_sha256"]
    for name, expected in receipt["prior_seals_sha256"].items():
        assert_historical_sha256(original_path(_safe_file(name)), expected)


def test_saved_holm_package_is_sealed_and_fully_bound() -> None:
    assert_sealed_package(PACKAGE, TEST)


def test_saved_holm_retains_all_twelve_comparisons_and_nominal_status() -> None:
    source = "artifacts/rp4_v4_b4/primary_statistics.csv"
    evidence = json.loads((original_path(PACKAGE / "holm_evidence.json")).read_text("utf-8"))
    assert evidence["window"] == "primary" and evidence["holm_family_size"] == 4
    assert evidence["cross_horizon_adjustment"] is False
    assert evidence["historical_rule_was_fixed_sequence"] is False
    assert (
        evidence["new_fits"]
        == evidence["new_bootstraps"]
        == evidence["new_statistical_results"]
        == 0
    )
    expected_hash = "5c215fc38344839ecedea7b27f69efcb85fbefea84f1367d06229cb7407902d4"
    assert_historical_sha256(original_path(_safe_file(source)), evidence["source_sha256"][source])
    assert evidence["source_sha256"][source] == expected_hash
    saved = readers.source(source)
    indices = [0, 1, 2, 3, 8, 9, 10, 11, 16, 17, 18, 19]
    rows = evidence["rows"]
    assert sorted(row["csv_row_index"] for row in rows) == indices
    for row in rows:
        original = saved[row["csv_row_index"]]
        assert original["window"] == "primary"
        assert row["horizon_minutes"] == int(original["horizon_minutes"])
        assert (row["family"], row["contrast"]) == (original["family"], original["contrast"])
        for key, column in (
            ("p_unilateral", "p_raw"),
            ("p_bilateral", "p_bilateral"),
            ("p_holm_bilateral", "p_holm_bilateral"),
        ):
            assert Decimal(str(row[key])) == Decimal(original[column])
        assert row["nominal_only"] is (original["p_for_decision"] == "")
        assert row["survives_holm"] is (
            Decimal(original["p_holm_bilateral"]) <= Decimal(original["alpha"])
        )
    for horizon in (30, 15, 5):
        group = [row for row in rows if row["horizon_minutes"] == horizon]
        assert len(group) == 4
        assert {(row["family"], row["contrast"]) for row in group} == {
            (family, contrast)
            for family in ("log_ridge_harq", "lightgbm_qlike")
            for contrast in ("B1_over_B0", "B2_over_B1")
        }
    assert sorted(row["csv_row_index"] for row in rows if row["survives_holm"]) == [2, 9, 10, 16]
    nominal = saved[19]
    assert nominal["p_raw"] == "0.1927" and nominal["p_for_decision"] == ""
    assert nominal["hypothesis_status"] == "NOT_TESTED"
    assert nominal["nominal_p_role"] == "NO_PROMOTABLE"
    assert nominal["inference_role"] == "SECONDARY"
    assert saved[18]["p_for_decision"] == "0.0608" and saved[18]["rejected"] == "False"
    qa = (original_path(PACKAGE / "examiner_qa.md")).read_text("utf-8")
    question = qa.split("\n## 26.", 1)[1].split("\n## 27.", 1)[0]
    slides = (original_path(PACKAGE / "defense_slides.md")).read_text("utf-8")
    for text in (question, slides):
        lines = [line.replace(",", ".") for line in text.splitlines() if line.startswith("|")]
        for row in rows:
            values = [
                f"{float(row[key]):.4f}"
                for key in ("p_unilateral", "p_bilateral", "p_holm_bilateral")
            ]
            matching = [line for line in lines if all(value in line for value in values)]
            assert len(matching) == 1, (row["csv_row_index"], values)
            line = matching[0]
            family = "Lineal" if row["family"] == "log_ridge_harq" else "Árboles"
            contrast = "B1/B0" if row["contrast"] == "B1_over_B0" else "B2/B1"
            assert family.casefold() in line.casefold() and contrast in line
            assert f"RV{row['horizon_minutes']}" in line
            decision = line.rstrip().rstrip("|").split("|")[-1].strip().strip("*")
            assert decision == ("Sí" if row["survives_holm"] else "No")
            assert ("nominal" in line.lower()) is row["nominal_only"]
        assert "nominal" in text.lower()
    assert "v1/v2 no usaban h1→h2" in question.lower()
    assert "condicional" in question.lower()
    assert "decisiones adaptativas" in question.lower()
    for name in readers.DOCUMENTS:
        assert "Bonferroni" not in (original_path(PACKAGE / name)).read_text("utf-8")
