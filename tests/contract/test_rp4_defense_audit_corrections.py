"""Guard the seven documentary corrections and preserve all earlier research seals."""

import csv
import importlib.util
import json
import re
from pathlib import Path

import pytest
from scripts.rp4_archive_sources import assert_historical_sha256, original_path, public_path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "docs/rp4/DEFENSE_PACKAGE/revision_2/correction_1"
SPEC = importlib.util.spec_from_file_location(
    "defense_audit_readers", Path(__file__).with_name("test_rp4_defense_package.py")
)
assert SPEC and SPEC.loader
defense = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(defense)
defense.PACKAGE = PACKAGE
V1 = "docs/rp4/prospective_confirmation_v1_receipt.json"
A2 = "docs/rp4/prospective_confirmation_v1_amendment_2_receipt.json"
STUDY = "artifacts/rp4_v4_a1/specification.json"
HISTORICAL_SENTENCE = (
    "La enmienda 2 sustituye el Holm de dos de la enmienda 1; "
    "no modifica sus recetas nominales A/B."
)


def assert_current_secondary_family(text: str) -> None:
    current = " ".join(text.split()).replace(HISTORICAL_SENTENCE, "")
    assert not re.search(
        r"\b(?:dos|two|2)\s+(?:secundarios|pruebas\s+secundarias|"
        r"secondaries|secondary\s+(?:tests|contrasts))\b|"
        r"\bHolm(?:\s+family)?\s+(?:de|entre|of)\s+(?:dos|two|2)\b",
        current,
        flags=re.I,
    )


def matrix() -> list[dict[str, str]]:
    with (original_path(PACKAGE / "claims_matrix.csv")).open(
        encoding="utf-8", newline=""
    ) as stream:
        return list(csv.DictReader(stream))


def test_corrected_packet_covers_sources_numbers_links_and_prior_seals() -> None:
    manifest = json.loads((original_path(PACKAGE / "evidence_manifest.json")).read_text("utf-8"))
    assert_historical_sha256(
        original_path(PACKAGE / "claims_matrix.csv"),
        "ce143ae77aeff89507843f5b1b2ff431ac8ca88decd1bec54e7ca9d0dc1b419a",
    )
    for name, expected in manifest["source_sha256"].items():
        assert_historical_sha256(original_path(ROOT / name), expected)
    for name, expected in manifest["document_sha256"].items():
        assert_historical_sha256(original_path(PACKAGE / name), expected)
    rows = matrix()
    assert len({row["claim_id"] for row in rows}) == len(rows)
    for name in manifest["source_documents"]:
        passages = defense.passages((original_path(ROOT / name)).read_text("utf-8"))
        claims = [r for r in rows if r["kind"] == "source_claim" and r["source_document"] == name]
        assert [r["claim"] for r in claims] == [defense.public_claim(p) for p in passages]
        assert [r["source_passage_sha256"] for r in claims] == [
            defense.digest(p.encode()) for p in passages
        ]
    private = r"(?i)\b(codex|claude|chatgpt|mds650|capstone|RP2|RP3|C10)\b|[A-Za-z]:[\\/]"
    for row in rows:
        assert row["artifact_sha256"] == manifest["source_sha256"][row["artifact"]]
        assert row["correction_test"] == "tests/contract/test_rp4_defense_audit_corrections.py"
        for field in ("claim", "context"):
            assert not re.search(private, row[field]), (row["claim_id"], field)
            assert_current_secondary_family(row[field])
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
        assert_current_secondary_family(defense.prose(text))
        assert [
            r["claim"]
            for r in rows
            if r["kind"] == "package_number" and r["source_document"] == name
        ] == defense.tokens(text), name
        assert not re.search(private, defense.prose(text)), name
        assert not re.search(r"[A-Za-z]:[\\/]", re.sub(r"https?://[^\s)]+", "", text))
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text):
            if not target.startswith(("http://", "https://", "#")):
                path = (PACKAGE / target.split("#")[0]).resolve()
                assert path.is_relative_to(ROOT) and public_path(path).is_file(), target
    defense.test_defense_table_and_decisions_match_saved_inference()
    defense.test_reviewed_bindings_keep_their_scientific_context()
    assert_historical_sha256(
        original_path(PACKAGE.parent / "receipt.json"),
        "595e2a9873c13096e802a8d137949f1293544dbf2ef7e8168dff794e7f7d1383",
    )
    assert (
        manifest["prior_receipt_sha256"]
        == "595e2a9873c13096e802a8d137949f1293544dbf2ef7e8168dff794e7f7d1383"
    )
    for stem in (
        "prospective_confirmation_v1",
        "prospective_confirmation_v1_amendment_1",
        "prospective_confirmation_v1_amendment_2",
        "administrative_verification_20260908",
        "RESULTADO_FINAL_revision_1",
    ):
        if stem == "administrative_verification_20260908":
            scope = assert_historical_sha256(
                ROOT / f"docs/rp4/{stem}.sha256",
                "95bc6d6eac43d923f4e9fdb33646e2acddf28a201dad33cdb92a4bff2c1e0045",
            )
            if scope == "private_source_not_distributed":
                continue  # Explicit custody pin only; no numerical source is omitted.
        for line in (
            (original_path(ROOT / f"docs/rp4/{stem}.sha256")).read_text("utf-8").splitlines()
        ):
            expected, name = line.split("  ", 1)
            assert Path(name).name == name
            assert_historical_sha256(original_path(ROOT / "docs/rp4" / name), expected)


def test_primary_anchors_and_current_holm_family_are_exact() -> None:
    rows = {row["claim_id"]: row for row in matrix()}
    for suffix in ("0140", "0180", "0562"):
        row = rows[f"package_number_{suffix}"]
        assert row["artifact"] == V1
        assert json.loads(row["selector"]) == ["alpha", "@percent"]
    for suffix in ("0157", "0198", "0330", "0359", "0561"):
        row = rows[f"package_number_{suffix}"]
        assert row["artifact"] == V1
        assert json.loads(row["selector"]) == ["primary_look_sessions"]
    assert (
        defense.source(V1)["alpha"]
        == defense.source(STUDY)["inference"]["fixed_sequence"]["alpha"]
        == 0.05
    )
    amendment = defense.source(A2)
    assert amendment["secondary_multiplicity"]["members"] == ["A", "B", "C"]
    assert amendment["secondary_multiplicity"]["family_size"] == 3
    assert amendment["secondary_D"]["historical_sessions"] == 25
    assert amendment["secondary_D"]["prospective_sessions"] == 20
    assert amendment["secondary_D"]["pooled_sessions"] == 45
    for row in rows.values():
        if row["kind"] == "package_number" and "amendment_1_receipt" in row["artifact"]:
            assert "secondary_multiplicity" not in json.loads(row["selector"])


def test_paired_median_and_robustness_window_are_explicit() -> None:
    executive = (original_path(PACKAGE / "executive_summary.md")).read_text("utf-8")
    assert "medianas pareadas positivas" in executive and "positive paired medians" in executive
    slides = (original_path(PACKAGE / "defense_slides.md")).read_text("utf-8")
    slide = slides.split("## 7.", 1)[1].split("## 8.", 1)[0]
    assert slide.lower().count("ventana primaria (419 sesiones)") == 3
    for horizon, positive_assets in ((15, 6), (5, 3)):
        summary = defense.source(f"artifacts/rp4_v4_b2_rv{horizon}/summary.json")
        assert summary["window"] == "primary" and summary["N_sessions"] == 419
        selected = [
            r
            for r in summary["robustness"]
            if r["family"] == "log_ridge_harq" and r["contrast"] == "B2_over_B1"
        ]
        for prefix, total, positives in (
            ("asset_", 6, positive_assets),
            ("chronological_block_", 3, 3),
        ):
            rows = [r for r in selected if r["subset"].startswith(prefix)]
            assert len(rows) == total
            assert sum(r["estimate"] > 0 for r in rows) == positives


def test_premium_lookback_and_revised_final_preserve_original_results() -> None:
    evidence = json.loads((original_path(PACKAGE / "audit_evidence.json")).read_text("utf-8"))
    premium = evidence["premium_proportions"]
    rows = defense.source(premium["source"])
    selected = [
        r
        for r in rows
        if r["horizon_minutes"] == "15"
        and r["window"] == "primary"
        and r["kind"] == "feature"
        and "premium_share" in r["column"]
    ]
    assert len(selected) == premium["all_premium_share_columns"] == 14
    assert premium["lookback_minutes"] == 5 and premium["horizon_minutes"] == 15
    for entry, category in zip(
        premium["selected_columns"], ("buy", "passive", "sell"), strict=True
    ):
        row = rows[entry["source_row_zero_based"]]
        assert row["column"] == entry["column"] == f"b2_5m_{category}_premium_share"
        assert float(row["absolute_mean"]) == entry["absolute_mean"]
        assert int(row["N_sessions"]) == entry["N_sessions"] == 419
    phrase = "las tres proporciones de prima de 5 minutos (compra, pasiva y venta)"
    original = ROOT / "docs/rp4/RESULTADO_FINAL.md"
    assert_historical_sha256(
        original_path(original), "6d629b2416601af39a6e7f4fc0f04db1455b6c20ba4c298e7fb21a6ed00b2b19"
    )
    revised = (original_path(ROOT / "docs/rp4/RESULTADO_FINAL_revision_1.md")).read_text("utf-8")
    body, note = revised.split("\n## Nota de revisión documental\n", 1)
    assert note.strip()
    assert body == original_path(original).read_text("utf-8").replace(
        "en RV15, las tres shares de prima tienen coeficientes medios",
        f"en RV15 de la ventana primaria, {phrase} tienen coeficientes medios",
    )
    assert phrase in (original_path(PACKAGE / "defense_slides.md")).read_text("utf-8")
    assert phrase in next(r["claim"] for r in matrix() if r["claim_id"] == "source_claim_0094")


def test_gap_is_unified_and_residual_circular_evidence_is_declared() -> None:
    rows = matrix()
    for row in rows:
        if row["kind"] == "package_number" and row["claim"] in ("2025-01-25", "2025-02-24"):
            assert row["artifact"] == STUDY
            assert json.loads(row["selector"]) == [
                "accepted_tape_gap",
                "start" if row["claim"] == "2025-01-25" else "end",
            ]
    assert defense.source(STUDY)["accepted_tape_gap"]["fill"] is False
    circular = [r for r in rows if r["evidence_status"] == "reported_prose_circular_declared"]
    assert len(circular) == 9
    assert sorted(r["claim"] for r in circular) == [
        "1",
        "20",
        "20",
        "20",
        "20",
        "28",
        "28",
        "28",
        "28",
    ]
    manifest = json.loads((original_path(PACKAGE / "evidence_manifest.json")).read_text("utf-8"))
    assert manifest["circular_evidence_declared"] == [
        {
            k: r[k]
            for k in (
                "claim_id",
                "claim",
                "source_document",
                "artifact",
                "selector",
                "context",
                "evidence_status",
            )
        }
        for r in circular
    ]
    for row in rows:
        if row["kind"] == "package_number" and row["artifact"] in (
            "docs/rp4/RESULTADO_FINAL.md",
            "docs/rp4/specification_v4.md",
        ):
            assert row in circular


@pytest.mark.parametrize(
    "stale",
    ["Quedan dos secundarios.", "Holm entre 2.", "two secondary tests", "dos pruebas secundarias"],
)
def test_contract_rejects_stale_secondary_counts_even_beside_history(stale: str) -> None:
    assert_current_secondary_family(HISTORICAL_SENTENCE)
    with pytest.raises(AssertionError):
        assert_current_secondary_family(HISTORICAL_SENTENCE + " " + stale)
