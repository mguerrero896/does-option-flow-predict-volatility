"""Guard the additive examiner revision using saved research and public metadata only."""

import copy
import csv
import importlib.util
import json
import re
from datetime import UTC, datetime
from decimal import Decimal, localcontext
from math import isclose
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
from scripts.rp4_archive_sources import assert_historical_sha256, original_path, public_path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "docs/rp4/DEFENSE_PACKAGE/revision_2/correction_2"
SPEC = importlib.util.spec_from_file_location(
    "examiner_readers", Path(__file__).with_name("test_rp4_defense_package.py")
)
assert SPEC and SPEC.loader
readers = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(readers)
EVIDENCE = "docs/rp4/DEFENSE_PACKAGE/revision_2/correction_2/examiner_evidence.json"
STUDY = "artifacts/rp4_v4_a1/specification.json"
A3 = "docs/rp4/prospective_confirmation_v1_amendment_3_receipt.json"
FINAL = "docs/rp4/RESULTADO_FINAL_revision_2.md"
TEST = "tests/contract/test_rp4_defense_examiner_revision.py"
PRIVATE = r"(?i)\b(codex|claude|chatgpt|mds650|capstone|RP2|RP3|C10)\b|[A-Za-z]:[\\/]"


def matrix() -> list[dict[str, str]]:
    with (original_path(PACKAGE / "claims_matrix.csv")).open(
        encoding="utf-8", newline=""
    ) as stream:
        return list(csv.DictReader(stream))


def test_every_number_source_claim_hash_and_link_is_accounted_for() -> None:
    manifest = json.loads((original_path(PACKAGE / "evidence_manifest.json")).read_text("utf-8"))
    for name, expected in manifest["source_sha256"].items():
        path = (ROOT / name).resolve()
        assert path.is_relative_to(ROOT) and not re.search(r"(?:^|/)(?:rp3|c10)(?:/|$)", name, re.I)
        assert_historical_sha256(original_path(path), expected)
    for name, expected in manifest["document_sha256"].items():
        assert_historical_sha256(original_path(PACKAGE / name), expected)
    rows = matrix()
    assert len(rows) == len({r["claim_id"] for r in rows})
    assert sum(r["kind"] == "source_claim" for r in rows) == manifest["source_claims"]
    assert (
        sum(r["kind"] == "package_number" for r in rows) == manifest["package_number_occurrences"]
    )
    for name in manifest["source_documents"]:
        passages = readers.passages((original_path(ROOT / name)).read_text("utf-8"))
        claims = [r for r in rows if r["kind"] == "source_claim" and r["source_document"] == name]
        assert [r["claim"] for r in claims] == [readers.public_claim(p) for p in passages]
        assert [r["source_passage_sha256"] for r in claims] == [
            readers.digest(p.encode()) for p in passages
        ]
    for row in rows:
        assert row["current_test"] == TEST
        assert row["artifact_sha256"] == manifest["source_sha256"][row["artifact"]]
        assert not re.search(PRIVATE, row["claim"] + " " + row["context"]), row["claim_id"]
        for name, expected in json.loads(row["supporting_artifacts"]).items():
            assert manifest["source_sha256"][name] == expected
        if row["kind"] == "package_number":
            assert (
                readers.rendered(
                    readers.selected(row["artifact"], row["selector"]), row["rendering"]
                )
                == row["claim"]
            ), row["claim_id"]
    for name in readers.DOCUMENTS:
        text = (original_path(PACKAGE / name)).read_text("utf-8")
        assert [
            r["claim"]
            for r in rows
            if r["kind"] == "package_number" and r["source_document"] == name
        ] == readers.tokens(text)
        assert not re.search(PRIVATE, readers.prose(text)), name
        assert not re.search(r"[A-Za-z]:[\\/]", re.sub(r"https?://[^\s)]+", "", text))
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text):
            if not target.startswith(("http://", "https://", "#")):
                path = (PACKAGE / target.split("#")[0]).resolve()
                assert path.is_relative_to(ROOT) and public_path(path).is_file(), target
    for generation, expected in manifest["prior_receipt_sha256"].items():
        assert_historical_sha256(original_path(ROOT / generation), expected)
    circular = [r for r in rows if "circular" in r["evidence_status"]]
    assert manifest["circular_evidence_declared"] == [r["claim_id"] for r in circular]


def test_chronology_uses_source_literals_and_distinguishes_declared_times() -> None:
    evidence = readers.source(EVIDENCE)
    chronology = evidence["chronology"]
    assert len(chronology) == 21
    for i, row in enumerate(chronology):
        original = readers.selected(row["artifact"], json.dumps(row["selector"]))
        if i < 3:
            assert original == row["market_date" if i == 0 else "declared_date"]
            assert row["time_of_day"] is None
            continue
        assert original == row["literal"] and not row["independent_timestamp"]
        if i == 5:
            date = datetime.strptime(original, "%Y-%m-%d %H:%M Australia/Sydney").replace(
                tzinfo=ZoneInfo("Australia/Sydney")
            )
        elif original.endswith(" UTC"):
            date = datetime.strptime(original, "%Y-%m-%d %H:%M:%S UTC").replace(tzinfo=UTC)
        else:
            date = datetime.fromisoformat(original)
        assert date.astimezone(UTC).isoformat() == row["utc"]
        assert date.astimezone(ZoneInfo("Australia/Sydney")).isoformat() == row["sydney"]
    study = readers.source(STUDY)
    assert chronology[1]["calendar_split"] == study["calendar_split"]
    assert chronology[0]["market_date"] < chronology[1]["declared_design_date"]
    assert readers.source(chronology[3]["artifact"])["prior_v1_v2_results_known"]
    times = [datetime.fromisoformat(r["utc"]) for r in chronology[3:]]
    assert times == sorted(times) and len(times) == len(set(times))
    assert "no hora autenticada" in chronology[5]["evidence_role"]
    assert "Cota superior" in chronology[16]["evidence_role"]
    for name in ("examiner_qa.md", "defense_slides.md"):
        text = (original_path(PACKAGE / name)).read_text("utf-8")
        for row in chronology[3:]:
            assert row["utc"] in text and row["sydney"] in text


def test_projected_predeclaration_preserves_science_and_has_its_own_seal() -> None:
    stem = ROOT / "docs/rp4/predeclaration_v4_text"
    receipt = readers.source("docs/rp4/predeclaration_v4_text_receipt.json")
    data = original_path(stem.with_suffix(".md")).read_bytes()
    assert (
        readers.digest(data)
        == receipt["projected_document_sha256"]
        == "b7e13877a3090b0724d9a90792afefef3f009124d2766197da637a42eb24d4a9"
    )
    assert (
        receipt["original_sha256"]
        == "6f8ad8d53a8f4336851415a99c25b316bf44db74165e29246110a3bb133eabee"
    )
    assert receipt["original_sha256"] != receipt["projected_document_sha256"]
    for line in original_path(stem.with_suffix(".sha256")).read_text("utf-8").splitlines():
        expected, name = line.split("  ", 1)
        assert Path(name).name == name
        assert_historical_sha256(original_path(stem.parent / name), expected)
    lines = (
        data.decode()
        .split("## Texto proyectado\n\n", 1)[1]
        .splitlines()[: receipt["original_line_count"]]
    )
    assert readers.digest(("\n".join(lines) + "\n").encode()) == receipt["projected_body_sha256"]
    for number, expected in receipt["retained_line_sha256"].items():
        assert readers.digest(lines[int(number) - 1].encode()) == expected
    assert (
        receipt["changed_original_lines"] == [3, 19]
        and len(receipt["retained_original_lines"]) == 26
    )
    assert [r["id"] for r in receipt["redactions"]] == ["R1", "R2", "R3", "R4"]
    assert not receipt["original_modified"] and not receipt["reference_panel_opened"]
    assert receipt["scientific_constraints_preserved"] and not receipt["independent_timestamp"]
    evidence = readers.source(EVIDENCE)
    assert evidence["horizon_rationale"]["quote_exact"] in data.decode()
    for field in (
        "original_predeclaration_success_quote",
        "original_predeclaration_failure_quote",
        "no_v5_literal",
    ):
        assert evidence["closure"][field] in data.decode()
    assert evidence["closure"]["quote_exact"] in readers.source("docs/rp4/specification_v4.md")


def test_saved_bilateral_holm_and_diagnostics_use_the_correct_contrasts() -> None:
    evidence = readers.source(EVIDENCE)["statistics"]
    stored = readers.source("artifacts/rp4_v4_b4/primary_statistics.csv")
    holm = evidence["holm"]
    original = [Decimal(stored[i]["p_bilateral"]) for i in range(8, 12)]
    order = sorted(range(4), key=lambda i: original[i])
    adjusted = [Decimal(0)] * 4
    running = Decimal(0)
    for rank, i in enumerate(order):
        running = max(running, (4 - rank) * original[i])
        adjusted[i] = min(Decimal(1), running)
    assert adjusted == list(map(Decimal, ["0.0918", "0.0248", "0.0447", "0.8048"]))
    for i, row in enumerate(holm["rows"]):
        source = stored[row["source"]["row_index_zero_based"]]
        assert row["source"]["row_index_zero_based"] == 8 + i
        assert (row["family"], row["contrast"]) == (source["family"], source["contrast"])
        assert row["stored_p_bilateral"] == float(original[i])
        assert row["calculated_holm_p"] == float(adjusted[i])
        assert isclose(float(source["p_holm_bilateral"]), float(adjusted[i]), abs_tol=1e-15)
        assert row["reject_at_alpha_0_05"] == (adjusted[i] <= Decimal("0.05"))
    assert [r["reject_at_alpha_0_05"] for r in holm["rows"]] == [False, True, True, False]
    assert not holm["linear_complete_hierarchy_supported"]
    for i, row in enumerate(evidence["diagnostics"]["rows"]):
        source = stored[8 + i]
        assert row["source"]["row_index_zero_based"] == 8 + i
        assert (row["family"], row["contrast"]) == (source["family"], source["contrast"])
        for output, field in {
            "dm_hac_statistic": "dm_hac_statistic",
            "dm_hac_p_two_sided": "dm_hac_p_two_sided",
            "gw_statistic": "gw_hac_diagnostic_statistic",
            "gw_p": "gw_hac_diagnostic_p",
            "gw_df": "gw_hac_diagnostic_df",
        }.items():
            assert row[output] == float(source[field])
        assert row["dm_hac_lags"] == int(source["dm_hac_lags"]) == 5
        assert row["gw_df"] == 2 and row["gw_status"] == "ASYMPTOTIC_DIAGNOSTIC"
    assert evidence["diagnostics"]["gw_instruments"] == [
        "constant",
        "previous_session_loss_difference",
    ]


def assert_concentration(row: dict) -> None:
    losses = readers.source("artifacts/rp4_v4_b3_rv15/session_losses.csv")
    with localcontext() as context:
        context.prec = 50
        deltas = [
            Decimal(r["loss__log_ridge_harq__B1"]) - Decimal(r["loss__log_ridge_harq__B2"])
            for r in losses
        ]
        index = row["event_source"]["row_index_zero_based"]
        assert losses[index]["session_date"] == row["event_session"] == "2026-08-31"
        assert index == 20 and row["event_source"]["file_line_one_based"] == 22
        assert (
            row["session_count"] == len(losses) == 25
            and row["other_session_count"] == len(losses) - 1
        )
        total, event = sum(deltas), deltas[index]
        assert str(total) == row["cumulative_delta_decimal_from_saved_csv"]
        assert str(event) == row["event_delta_decimal_from_saved_csv"]
        assert str(total - event) == row["other_24_cumulative_delta_decimal"]
        assert str(event / total) == row["event_fraction_decimal"]
        assert isclose(
            float(100 * event / total), row["event_percent_of_net_cumulative_delta"], abs_tol=1e-12
        )
        assert isclose(float(total / len(losses)), row["stored_summary_mean_delta"], abs_tol=1e-15)


def test_concentration_bridge_overlap_and_cross_section_have_bounded_scope() -> None:
    evidence = readers.source(EVIDENCE)
    assert_concentration(evidence["statistics"]["concentration"])
    bridge = evidence["prior_bridge"]
    dates = [r["session_date"] for r in readers.source(bridge["final_window_session_source"])]
    overlap = [d for d in dates if bridge["window_start"] <= d <= bridge["window_end"]]
    assert dates == bridge["final_window_sessions"]
    assert overlap == bridge["overlap_sessions"]
    assert (
        len(overlap) == bridge["overlap_count"] == 20 and len(dates) == bridge["final_count"] == 25
    )
    assert 100 * len(overlap) / len(dates) == bridge["overlap_percent"] == 80
    assert (
        not bridge["prior_read_independently_verified"]
        and not bridge["protected_bridge_artifacts_opened"]
    )
    for passage in bridge["public_readme_passages"]:
        actual = "\n".join(
            (original_path(ROOT / "README.md"))
            .read_text("utf-8")
            .splitlines()[passage["start_line"] - 1 : passage["end_line"]]
        )
        assert actual == passage["text"]
    assert evidence["statistics"]["sample"]["assets"] == readers.source(STUDY)["assets"]
    assert evidence["statistics"]["sample"]["measured_cross_asset_correlation"] is None
    for item in evidence["statistics"]["versions"]["per_asset_linear_B2"]:
        source = readers.source(f"artifacts/rp4_v4_b2_rv{item['horizon_minutes']}/summary.json")
        rows = [
            r
            for r in source["robustness"]
            if r["family"] == "log_ridge_harq"
            and r["contrast"] == "B2_over_B1"
            and r["subset"].startswith("asset_")
        ]
        assert len(rows) == item["asset_count"] == 6
        assert (
            sum(r["estimate"] > 0 for r in rows)
            == item["positive_estimate_count"]
            == (6 if item["horizon_minutes"] == 15 else 3)
        )


def test_registered_baseline_and_horizon_search_do_not_expand_to_sealed_inputs() -> None:
    evidence = readers.source(EVIDENCE)
    baseline = evidence["b0"]
    assert baseline["columns"] == readers.source(STUDY)["feature_sets"]["B0"]
    assert baseline["count"] == len(baseline["columns"]) == 29
    assert sorted(x for group in baseline["groups"].values() for x in group) == sorted(
        baseline["columns"]
    )
    assert (
        baseline["backward_rv_minutes"]
        == [
            int(n.removeprefix("rv_back_"))
            for n in baseline["groups"]["past_realized_variance"]
            if n.startswith("rv_back_")
        ]
        == [5, 15, 30]
    )
    for path, anchors in baseline["code_bindings"].items():
        code = (original_path(ROOT / path)).read_text("utf-8")
        assert all(anchor.split()[0] in code for anchor in anchors)
    search = evidence["bounded_horizon_search"]
    assert len(search["scope_files"]) == search["scope_file_count"] == 62
    assert not search["raw_or_origin_panels_in_scope"] and not search["protected_cohorts_in_scope"]
    for name in search["scope_files"]:
        assert name.startswith(("artifacts/rp4_v3_", "artifacts/rp4_v4_"))
        path = ROOT / name
        assert path.suffix in {".py", ".json", ".csv"}
        assert_historical_sha256(original_path(path), search["scope_file_sha256"][name])
        assert not re.search(
            r"rv_10|rv_20|rv_60|rv_45", original_path(path).read_text("utf-8"), re.I
        )
    assert search["exit_code"] == 1 and search["stdout"] == search["stderr"] == ""
    assert [r["year"] for r in evidence["literature"]] == [2009, 2016, 2015]
    assert (
        evidence["literature"][0]["method_reading"]["status"]
        == "PARTIAL_FULL_TEXT_WORKING_PAPER_PREDECESSOR"
    )


def test_current_narrative_preserves_results_and_states_the_actual_power_limit() -> None:
    evidence = readers.source(EVIDENCE)
    executive = (original_path(PACKAGE / "executive_summary.md")).read_text("utf-8")
    qa = (original_path(PACKAGE / "examiner_qa.md")).read_text("utf-8")
    slides = (original_path(PACKAGE / "defense_slides.md")).read_text("utf-8")
    assert len(re.findall(r"^## \d+\.", slides, re.M)) == 12
    assert len(re.findall(r"^## \d+\.", qa, re.M)) == 26
    assert (
        "Sí en la muestra de desarrollo" in executive
        and "Yes within the development sample" in executive
    )
    assert "medianas pareadas positivas" in executive and "positive paired medians" in executive
    assert "54,98" in executive and "54.98" in executive
    assert "sin 80 % conjunto" in executive and "not 80% joint power" in executive
    closing = (
        "Si ninguna rechaza" + evidence["closure"]["quote_exact"].split("Si ninguna rechaza", 1)[1]
    )
    assert qa.count(closing) >= 1
    assert slides.count(closing) == 2
    pages = executive.split('<div style="page-break-after: always;"></div>')
    assert len(pages) == 2
    for page in pages:
        assert len(readers.prose(page).split()) <= 650
        assert re.findall(r"^([1-4])\. ", page, re.M) == ["1", "2", "3", "4"]
    for figure in (
        "thesis_summary.svg",
        "v4_B1_over_B0_cumulative_v2.svg",
        "v4_B2_over_B1_cumulative_v2.svg",
    ):
        assert figure in slides
    assert "## 26. Multiplicidad entre versiones" in qa
    assert evidence["documentation"]["bonferroni_examiner_question"] == 26
    a3 = readers.source(A3)
    quantiles = evidence["prospective_amendment_3"]["normal_quantiles"]
    assert (
        quantiles["ci_upper_probability"]
        == (1 + a3["normal_approximation"]["ci_nominal_coverage"]) / 2
    )
    assert quantiles["test_upper_probability"] == 1 - a3["normal_approximation"]["alpha"]
    assert not a3["sequence_power"]["actual_joint_power_estimated"]
    assert not a3["power_for_actual_pooled_D_estimated"]
    assert not a3["global_between_look_alpha_control_claimed"]
    assert a3["additional_reading"]["sessions"] == 335
    final = (original_path(ROOT / FINAL)).read_text("utf-8")
    previous = (original_path(ROOT / "docs/rp4/RESULTADO_FINAL_revision_1.md")).read_text("utf-8")
    assert [s for s in final.splitlines() if s.startswith("|")] == [
        s for s in previous.splitlines() if s.startswith("|")
    ]
    prior_slides = (original_path(PACKAGE.parent / "correction_1/defense_slides.md")).read_text(
        "utf-8"
    )

    def table(text: str) -> list[str]:
        return [s for s in text.splitlines() if re.match(r"\| v[1-4] · RV", s)]

    assert table(slides) == table(prior_slides) and len(table(slides)) == 5
    assert "Sí en la muestra de desarrollo" in final
    assert (
        "cierre de v4 exige" in final
        and "sin verificar de forma independiente una interrupción" in final
    )
    assert "sólo en tres activos" in final and "sin rescate" in final
    for line in (
        (original_path(ROOT / "docs/rp4/RESULTADO_FINAL_revision_2.sha256"))
        .read_text("utf-8")
        .splitlines()
    ):
        expected, name = line.split("  ", 1)
        assert Path(name).name == name
        assert_historical_sha256(original_path(ROOT / "docs/rp4" / name), expected)
    assert "revision_2/correction_2/README.md" in (
        original_path(PACKAGE.parents[1] / "README.md")
    ).read_text("utf-8")


def test_contract_rejects_wrong_event_row_and_changed_numeric_claim() -> None:
    wrong = copy.deepcopy(readers.source(EVIDENCE)["statistics"]["concentration"])
    wrong["event_source"]["row_index_zero_based"] = 8
    with pytest.raises(AssertionError):
        assert_concentration(wrong)
    row = next(r for r in matrix() if r["kind"] == "package_number" and r["claim"] == "0,0032")
    assert (
        readers.rendered(readers.selected(row["artifact"], row["selector"]), row["rendering"])
        != "0,0390"
    )
