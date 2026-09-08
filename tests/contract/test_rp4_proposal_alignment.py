"""Check proposal alignment against saved evidence, without scientific execution."""

import csv
import importlib.util
import json
import re
from pathlib import Path

from scripts.rp4_archive_sources import assert_historical_sha256, original_path, public_path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "docs/rp4/DEFENSE_PACKAGE"
PACKAGE = BASE / "revision_2/correction_4"
PRIOR = PACKAGE.parent / "correction_3"
CONTEXT = "docs/rp4/prospective_confirmation_v1_amendment_3_context_1.md"
TEST = "tests/contract/test_rp4_proposal_alignment.py"
SPEC = importlib.util.spec_from_file_location(
    "proposal_readers", Path(__file__).with_name("test_rp4_defense_package.py")
)
assert SPEC and SPEC.loader
readers = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(readers)
PRIVATE = r"(?i)\b(codex|claude|chatgpt|mds650|capstone)\b|[A-Za-z]:[\\/]"
RP3_PUBLIC_DOCS = {"docs/rp3/EXECUTION_GUIDE.md", "docs/rp3/PREREGISTRATION.md"}
PROPOSAL_HASH = "808275831ca2c7ee253634eb8ad79510e0690cb54cc9447c8613608958ecaf6e"
NOTEBOOK_HASHES = {
    "notebooks/canonical_rv30_defense.ipynb": (
        "5c93fe9cd4f503df74324b8d31a419ec9d5a138355611bb715ce414b96be33d5"
    ),
    "notebooks/research_pipeline.ipynb": (
        "01180e8a2af11be57645f180bef1b84919e22aa1327149f5fb677e9d16502045"
    ),
}
PRIOR_RECEIPTS = {
    "receipt.json": "d88a075767bad2b661d90e77b675b7896e1a04f77fcfd70018f96287646ef79f",
    "revision_2/receipt.json": "595e2a9873c13096e802a8d137949f1293544dbf2ef7e8168dff794e7f7d1383",
    "revision_2/correction_1/receipt.json": (
        "9a0b4d16917fefef43c89a12bf2c1f2cfa06190d744460849db5a4f49153a201"
    ),
    "revision_2/correction_2/receipt.json": (
        "1c7eab523b72499ec8d40bd4eeae1d563d907f1dbf59072eb21a7a373121c56c"
    ),
    "revision_2/correction_3/receipt.json": (
        "6a1ba97d337efc0761a452e8ae8167e1124dcc6b700c862c638371b47099e273"
    ),
}


def safe_source(name: str) -> Path:
    path = (ROOT / name).resolve()
    assert path.is_relative_to(ROOT), name
    if any(re.match(r"(?:rp3|c10)(?:$|[_-])", part, re.I) for part in Path(name).parts):
        assert name in RP3_PUBLIC_DOCS, name
    assert not any(part.lower() in {"raw", "inputs"} for part in Path(name).parts), name
    assert path.suffix not in {".parquet", ".feather"}, name
    assert path.suffix != ".ipynb" or name in NOTEBOOK_HASHES, name
    return path


def safe_file(name: str) -> Path:
    path = safe_source(name)
    assert original_path(path).is_file(), name
    return path


def matrix(package: Path) -> list[dict]:
    with (original_path(package / "claims_matrix.csv")).open(
        encoding="utf-8", newline=""
    ) as stream:
        return list(csv.DictReader(stream))


def evidence() -> dict:
    return json.loads(
        (original_path(PACKAGE / "proposal_alignment_evidence.json")).read_text("utf-8")
    )


def fact_value(fact: dict) -> object:
    safe_file(fact["artifact"])
    return readers.selected(fact["artifact"], json.dumps(fact["selector"]))


def assert_fact(fact: dict, pins: dict) -> None:
    assert fact["sha256"] == pins[fact["artifact"]]
    value = fact_value(fact)
    if "quote" in fact:
        assert isinstance(value, str) and fact["quote"] and fact["quote"] in value
        if "line_start" in fact:
            assert (
                "\n".join(value.splitlines()[fact["line_start"] - 1 : fact["line_end"]])
                == fact["quote"]
            )
    else:
        assert fact["value"] == value


def moved_links(text: str) -> str:
    return text.replace(
        "(convergence_evidence.json)", "(../correction_3/convergence_evidence.json)"
    )


def test_complete_source_and_number_coverage_preserves_inherited_claims() -> None:
    manifest = json.loads((original_path(PACKAGE / "evidence_manifest.json")).read_text("utf-8"))
    for name, expected in manifest["source_sha256"].items():
        assert_historical_sha256(safe_source(name), expected)
    for name, expected in manifest["document_sha256"].items():
        path = PACKAGE / name
        assert path.resolve().is_relative_to(PACKAGE)
        assert_historical_sha256(original_path(path), expected)
    rows = matrix(PACKAGE)
    assert len(rows) == len({row["claim_id"] for row in rows})
    programs = json.loads((original_path(PRIOR / "convergence_evidence.json")).read_text("utf-8"))[
        "facts"
    ]
    alignment = evidence()["facts"]
    for row in rows:
        assert row["current_test"] == TEST
        assert row["artifact_sha256"] == manifest["source_sha256"][row["artifact"]]
        assert not re.search(PRIVATE, readers.prose(row["claim"] + " " + row["context"]))
        for name, expected in json.loads(row["supporting_artifacts"]).items():
            assert manifest["source_sha256"][name] == expected
        if row["kind"] == "package_number":
            safe_file(row["artifact"])
            value = readers.selected(row["artifact"], row["selector"])
            assert readers.rendered(value, row["rendering"]) == row["claim"], row["claim_id"]
        elif row["kind"] in {"program_evidence", "proposal_evidence"}:
            facts = programs if row["kind"] == "program_evidence" else alignment
            fact = facts[row["claim"]]
            assert row["artifact"] == fact["artifact"]
            assert json.loads(row["selector"]) == fact["selector"]
            assert_fact(fact, manifest["source_sha256"])
        else:
            assert row["kind"] == "source_claim"
    for name in manifest["source_documents"]:
        passages = readers.passages(original_path(safe_file(name)).read_text("utf-8"))
        actual = [r for r in rows if r["kind"] == "source_claim" and r["source_document"] == name]
        assert [r["claim"] for r in actual] == [readers.public_claim(p) for p in passages]
        assert [r["source_passage_sha256"] for r in actual] == [
            readers.digest(p.encode()) for p in passages
        ]
    for name in (*readers.DOCUMENTS, CONTEXT):
        path = ROOT / name if name == CONTEXT else PACKAGE / name
        text = original_path(path).read_text("utf-8")
        actual = [
            r["claim"]
            for r in rows
            if r["kind"] == "package_number" and r["source_document"] == name
        ]
        assert actual == readers.tokens(text), name
        assert not re.search(PRIVATE, readers.prose(text)), name
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text):
            if not target.startswith(("http://", "https://", "#")):
                linked = (path.parent / target.split("#")[0]).resolve()
                assert linked.is_relative_to(ROOT) and public_path(linked).is_file(), target
    counters = {
        "source_claim": "source_claims",
        "package_number": "package_number_occurrences",
        "program_evidence": "program_evidence_records",
        "proposal_evidence": "proposal_evidence_records",
    }
    for kind, counter in counters.items():
        assert sum(r["kind"] == kind for r in rows) == manifest[counter]
    assert manifest["program_evidence_records"] == len(programs)
    assert manifest["proposal_evidence_records"] == len(alignment)
    # Historical mappings remain reviewable; a new test name is not a new claim.
    fields = (
        "kind",
        "source_document",
        "source_passage_sha256",
        "claim",
        "artifact",
        "artifact_sha256",
        "rendering",
        "context",
        "evidence_status",
    )
    for kind in ("source_claim", "program_evidence"):
        old = [r for r in matrix(PRIOR) if r["kind"] == kind]
        new = [r for r in rows if r["kind"] == kind]
        assert len(old) == len(new)
        for before, after in zip(old, new, strict=True):
            assert [before[k] for k in fields] == [after[k] for k in fields]
            for key in ("selector", "supporting_artifacts"):
                assert json.loads(before[key]) == json.loads(after[key])


def test_exact_original_proposal_projection_and_documentary_limits() -> None:
    path = PACKAGE / "proposal_source_extract.json"
    assert_historical_sha256(original_path(path), PROPOSAL_HASH)
    proposal = json.loads(original_path(path).read_text("utf-8"))
    assert proposal["schema"] == "rp4-original-proposal-scientific-excerpts-v1"
    originals = {
        "en": "6f50797daec4f6108862122cd77f791efbf347912f3b1f74f6a3dc55449b3662",
        "es": "b65776432e805872b79ddbefc74ebe2d7d49ff56f0edfb05f65e7919f7a104ca",
    }
    for language, expected in originals.items():
        source = proposal["sources"][language]
        assert source["docx_sha256"] == expected
        assert source["declared_date_iso"] == "2026-07-26"
        for paragraph in source["paragraphs"].values():
            assert readers.digest(paragraph["text"].encode()) == paragraph["text_sha256"]
    assert proposal["sources"]["en"]["paragraphs"]["40"]["text"] == "2.3 Research Questions"
    assert proposal["sources"]["es"]["paragraphs"]["41"]["text"] == "2.3 Preguntas de investigación"
    assert proposal["sources"]["en"]["equation_1_image_sha256"] == (
        "3abb7e24dae83049ee5076793a85eb6a936c7923f3bb7bb42bc4420ab519e93e"
    )
    qa = (original_path(PACKAGE / "examiner_qa.md")).read_text("utf-8").split("\n## 1.")[0]
    for language, label in (("en", "english"), ("es", "spanish")):
        paragraphs = proposal["sources"][language]["paragraphs"]
        for clause, paragraph in (("commitment", "74"), ("null_clause", "79")):
            quote = proposal[f"exact_{label}_{clause}"]
            assert quote in paragraphs[paragraph]["text"] and quote in qa
        assert "31" in paragraphs["72"]["text"] and "30" in paragraphs["72"]["text"]
    assert (
        "unannualised sum of thirty squared future one-minute log returns"
        in proposal["equation_1_visual_check"]
    )
    assert "declared date only" in proposal["source_file_status"]
    assert "no una marca temporal independiente" in qa
    assert "sin raíz ni anualización" in qa
    assert "no son la misma regla inferencial" in qa
    assert "no pre-especificaba esa regla de éxito" in qa
    assert proposal["new_scientific_calculations"] == 0


def test_rv30_answers_are_typed_by_family_and_precede_the_extension() -> None:
    data = evidence()
    assert data["schema"] == "rp4-proposal-alignment-evidence-v1"
    for name, expected in data["source_sha256"].items():
        assert_historical_sha256(original_path(safe_file(name)), expected)
    for fact in data["facts"].values():
        assert_fact(fact, data["source_sha256"])
    facts = data["facts"]
    expected = {
        "linear": ("log_ridge_harq", 0.0439, 0.0525),
        "trees": ("lightgbm_qlike", 0.0053, 0.6631),
    }
    for label, (family, p1, p2) in expected.items():
        for number, contrast, p in ((1, "B1_over_B0", p1), (2, "B2_over_B1", p2)):
            record = fact_value(facts[f"rv30_{label}_h{number}"])
            assert record["family"] == family and record["contrast"] == contrast
            assert record["inference_role"] == "PRIMARY" and record["alternative"] == "greater"
            assert record["p_for_decision"] == fact_value(facts[f"rv30_{label}_h{number}_p"]) == p
            assert record["rejected"] is (number == 1)
    sequence = fact_value(facts["v3_fixed_sequence"])
    assert sequence["order"] == ["B1_over_B0", "B2_over_B1"] and sequence["alpha"] == 0.05
    assert fact_value(facts["v3_joint_rule"]) == "both_contrasts_reject_in_both_families"
    assert (
        fact_value(facts["v4_joint_rule"])
        == "both_contrasts_reject_in_at_least_one_family_at_15min_primary"
    )
    assets = [fact_value(facts[name]) for name in data["rq3_scope"]["asset_fact_ids"]]
    assert len(assets) == 12 and len({row["subset"] for row in assets}) == 6
    assert all(row["contrast"] == "B1_over_B0" and row["estimate"] > 0 for row in assets)
    assert all(row["p_holm"] > sequence["alpha"] for row in assets)
    assert min(row["p_holm"] for row in assets) == 0.0624
    assert fact_value(facts["v3_secondary_definition"])["last_hour"] == "origin_minute_ge_300"
    qa = (original_path(PACKAGE / "examiner_qa.md")).read_text("utf-8").split("\n## 1.")[0]
    assert qa.index("### Primero, las preguntas originales a RV30") < qa.index(
        "### Después, la extensión"
    )
    for rq in ("rq1", "rq2", "rq3"):
        assert fact_value(facts[f"proposal_es_{rq}"]) in qa
    for phrase in (
        "**No se detecta al 5 %**",
        "**Parcial**",
        "no rechazo no demuestra efecto cero",
        "no tres regímenes estadísticos predefinidos",
        "sin acreditar toda la estabilidad propuesta",
        "sin resultados de variantes del corte",
        "búsqueda histórica no corregida",
    ):
        assert phrase in qa, phrase


def test_universe_configuration_and_pending_deliverables_keep_their_scope() -> None:
    data = evidence()
    facts = data["facts"]
    assert fact_value(facts["v3_assets"]) == ["AAPL", "AMZN", "META", "MSFT", "NVDA", "TSLA"]
    assert fact_value(facts["v3_market_assets"]) == ["SPY", "QQQ"]
    b0, b1, b2 = (fact_value(facts[f"v3_{name}_features"]) for name in ("B0", "B1", "B2"))
    assert set(b0) < set(b1) < set(b2)
    for ticker in ("SPY", "QQQ"):
        assert any(name.startswith(ticker + "_") for name in b0)
        assert ticker in fact_value(facts["proposal_en_scope"])
    assert data["universe"]["written_rationale"] is None
    assert data["universe"]["rationale_status"] == "NO LOCALIZADA EN BUSQUEDA ACOTADA"
    for field in ("bootstrap_block", "bootstrap_repetitions", "source_cutoff", "primary_horizon"):
        value_key = {
            "bootstrap_block": "bootstrap_block_sessions",
            "bootstrap_repetitions": "bootstrap_repetitions",
            "source_cutoff": "source_cutoff_seconds",
            "primary_horizon": "primary_horizon_minutes",
        }[field]
        fact_key = {"bootstrap_repetitions": "bootstrap_repetitions_fact"}.get(
            field, field + "_fact"
        )
        assert data["configuration"][value_key] == fact_value(
            facts[data["configuration"][fact_key]]
        )
    assert facts["origin_step_code"]["quote"] == "ORIGIN_STEP = 5"
    assert data["configuration"]["origin_step_minutes"] == 5
    assert (
        fact_value(facts["v3_model_families"])
        == fact_value(facts["v4_model_families"])
        == ["log_ridge_harq", "lightgbm_qlike"]
    )
    assert "bar semantics blocked" in facts["data_dictionary_historical_status"]["quote"]
    assert "B1 blocked" in facts["data_dictionary_historical_status"]["quote"]
    assert fact_value(facts["literature_matrix_row_count"]) == 10
    assert "working paper" in fact_value(facts["literature_working_paper_status"])
    assert fact_value(facts["versioned_target_panel_hash"]) == fact_value(
        facts["materialization_target_hash"]
    )
    assert float(fact_value(facts["uncertainty_ci_low"])) < float(
        fact_value(facts["uncertainty_ci_high"])
    )
    expected = {
        "final_research_report": "ALINEADO",
        "presentation": "ALINEADO",
        "literature_matrix": "ALINEADO",
        "data_dictionary": "PENDIENTE",
        "reproducible_extraction_qc_code": "ALINEADO",
        "versioned_analytical_panel": "DESVIACION DECLARADA",
        "model_comparison_tables": "ALINEADO",
        "uncertainty_intervals": "ALINEADO",
        "robustness_analyses": "ALINEADO",
        "examiner_facing_notebook": "PENDIENTE",
    }
    assert {row["id"]: row["status"] for row in data["deliverables"]} == expected
    assert len(data["deliverables"]) == 10
    for row in data["deliverables"]:
        assert row["fact_ids"] and row["limits"] and row["finding"]
        assert all(name in facts for name in row["fact_ids"])
    pending = {row["id"]: row for row in data["pending_items"]}
    assert set(pending) == {
        "mae_rmse",
        "pit_variants",
        "placebo",
        "separate_har_benchmark",
        "separate_seasonal_persistence",
        "data_dictionary_update",
        "examiner_notebook_update",
        "peer_review_requirement",
    }
    assert all(
        row["status"] == "PENDIENTE" and row["analyses_executed"] is False
        for row in pending.values()
    )
    scope = data["scope"]
    assert (
        scope["new_statistical_calculations"]
        == scope["model_fits"]
        == scope["bootstrap_replications"]
        == 0
    )
    assert scope["pending_analyses_executed"] is scope["raw_or_sealed_payloads_read"] is False
    qa = (original_path(PACKAGE / "examiner_qa.md")).read_text("utf-8").split("\n## 1.")[0]
    for phrase in (
        "no se localizó una razón escrita",
        "no a todo el repositorio",
        "Pendientes documentados, sin ejecución",
        "no se ejecutó en esta revisión",
        "no se presenta como el cuaderno prometido",
        "esa matriz por sí sola no acredita",
    ):
        assert phrase in qa, phrase
    table = qa.split("| Entregable comprometido |", 1)[1].split("**Pendientes documentados", 1)[0]
    table_rows = [
        line.split("|")[1:3]
        for line in table.splitlines()
        if line.startswith("| ") and not line.startswith("| ---")
    ]
    titles = [
        "Informe final",
        "Presentación",
        "Matriz de literatura",
        "Diccionario de datos",
        "Código reproducible de extracción y calidad",
        "Panel analítico versionado",
        "Tablas de comparación",
        "Intervalos de incertidumbre",
        "Análisis de robustez",
        "Cuaderno para el examinador",
    ]
    assert [title.strip() for title, _ in table_rows] == titles
    assert [re.findall(r"\*\*([^*]+)\*\*", cell)[0] for _, cell in table_rows] == [
        state.replace("DESVIACION", "DESVIACIÓN") for state in expected.values()
    ]
    notebook_sources = {}
    for name, expected_hash in NOTEBOOK_HASHES.items():
        assert data["source_sha256"][name] == expected_hash
        path = safe_file(name)
        assert_historical_sha256(original_path(path), expected_hash)
        # Only cell source is inspected; outputs and linked files are never consulted.
        cells = json.loads(original_path(path).read_text("utf-8"))["cells"]
        notebook_sources[name] = "\n".join(
            "".join(cell["source"]) if isinstance(cell["source"], list) else cell["source"]
            for cell in cells
        )
    canonical = notebook_sources["notebooks/canonical_rv30_defense.ipynb"]
    pipeline = notebook_sources["notebooks/research_pipeline.ipynb"]
    assert "artifacts/canonical_validation_v1" in canonical and "B0v2" in canonical
    assert "nine target-blind trade-activity features" in canonical
    assert "'b1_status': 'INFEASIBLE'" in pipeline
    assert "'fallback_comparison': 'B2-vs-B0'" in pipeline
    for row in data["bounded_review"]["search_results"]:
        assert row["exit_code"] == 1 and "Not a repository-wide" in row["scope"]
        pattern = re.compile(row["pattern"], re.I)
        for name in data["bounded_review"]["source_files"]:
            assert not pattern.search(original_path(safe_file(name)).read_text("utf-8")), (
                row["name"],
                name,
            )


def test_new_material_preserves_the_entire_prior_defense_and_four_sentence_answers() -> None:
    qa = (original_path(PACKAGE / "examiner_qa.md")).read_text("utf-8")
    old_qa = (original_path(PRIOR / "examiner_qa.md")).read_text("utf-8")
    assert re.findall(r"(?m)^## (\d+)\.", qa) == [str(i) for i in range(1, 28)]
    assert qa.split("\n## 1.", 1)[1] == moved_links(old_qa.split("\n## 1.", 1)[1])
    slides = (original_path(PACKAGE / "defense_slides.md")).read_text("utf-8")
    old_slides = (original_path(PRIOR / "defense_slides.md")).read_text("utf-8")
    assert re.findall(r"(?m)^## (\d+)\.", slides) == [str(i) for i in range(1, 14)]
    sections = re.split(r"(?m)^## \d+\. ", slides)[1:]
    assert sections[2].startswith("Propuesta → entrega:")
    assert sections[:2] + sections[3:] == [
        moved_links(s) for s in re.split(r"(?m)^## \d+\. ", old_slides)[1:]
    ]
    for prefix in ("| v", "!["):
        assert [line for line in slides.splitlines() if line.startswith(prefix)] == [
            line for line in old_slides.splitlines() if line.startswith(prefix)
        ]
    summary = (original_path(PACKAGE / "executive_summary.md")).read_text("utf-8")
    old_summary = (original_path(PRIOR / "executive_summary.md")).read_text("utf-8")
    assert "page-break-after: always" in summary
    assert re.findall(r"(?m)^[1-4]\. .*$", summary) == re.findall(r"(?m)^[1-4]\. .*$", old_summary)
    for marker, answer in (
        ("**Respuesta a las preguntas de la propuesta.**", "**Respuesta y magnitud.**"),
        ("**Answers to the proposal questions.**", "**Answer and magnitude.**"),
    ):
        start = summary.index(marker)
        assert start < summary.index(answer, start)
        block = summary[start:].split("\n\n", 1)[0].removeprefix(marker).strip()
        scientific = re.sub(r"\[[^\]]+\]\([^)]+\)\.?$", "", block).strip()
        sentences = re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÜÑ])", scientific)
        assert len(sentences) == 4
        assert all(label in sentences[i] for i, label in enumerate(("RQ1", "RQ2", "RQ3", "RV15")))
        assert "RV30" in sentences[0] and "RV5" in sentences[3]
        assert summary.count(marker) == 1


def test_all_prior_packages_and_historical_context_remain_sealed() -> None:
    for name, expected in PRIOR_RECEIPTS.items():
        path = BASE / name
        assert_historical_sha256(original_path(path), expected)
        receipt = json.loads(original_path(path).read_text("utf-8"))
        manifest_path = path.parent / "evidence_manifest.json"
        assert_historical_sha256(original_path(manifest_path), receipt["evidence_manifest_sha256"])
        manifest = json.loads(original_path(manifest_path).read_text("utf-8"))
        for document, pin in manifest["document_sha256"].items():
            assert_historical_sha256(original_path(path.parent / document), pin)
        for document, pin in receipt.get("prior_seals_sha256", {}).items():
            assert_historical_sha256(original_path(safe_file(document)), pin)
    receipt = json.loads((original_path(PACKAGE / "receipt.json")).read_text("utf-8"))
    for name, expected in receipt["prior_seals_sha256"].items():
        assert_historical_sha256(original_path(safe_file(name)), expected)
    assert_historical_sha256(
        original_path(safe_file(CONTEXT)),
        "ce1372ab888a52a18cae425cf02c526a1d68cbccebcb30137d365d16cebf6cc0",
    )
    sidecar = ROOT / CONTEXT.replace(".md", ".sha256")
    for line in original_path(sidecar).read_text("utf-8").splitlines():
        expected, name = line.split("  ", 1)
        assert Path(name).name == name
        assert_historical_sha256(original_path(sidecar.parent / name), expected)
