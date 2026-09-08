"""Bind defense prose and every displayed number to stored, hashed evidence."""

import csv
import hashlib
import json
import re
import shutil
import xml.etree.ElementTree as ET
from functools import lru_cache
from pathlib import Path

import pytest
from scripts.rp4_archive_sources import assert_historical_sha256, original_path, public_path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "docs/rp4/DEFENSE_PACKAGE"
LINK_PACKAGE: Path | None = None
DOCUMENTS = ("executive_summary.md", "examiner_qa.md", "defense_slides.md")
NUMBER = re.compile(
    r"(?<![\w])(?:[12]\d{3}-\d{2}-\d{2}|[+−-]?\d+(?:[.,]\d+)*(?:[eE][+-]?\d+)?)(?![\w])"
)


def digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def prose(text: str) -> str:
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    text = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(
        r"`([^`]+)`",
        lambda match: "" if re.search(r"/|_|[a-f0-9]{32}", match[1]) else match[1],
        text,
    )
    # Slide/question/disclosure ordinals are navigation, not research quantities.
    text = re.sub(r"(?m)^(#{1,6}\s+)?\d+\.\s+", r"\1", text)
    return text


def passages(text: str) -> list[str]:
    """Inventory every non-heading prose block and table row, including history."""
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    result = []
    for block in re.split(r"\n\s*\n", text):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines or all(line.startswith(("#", "<", "![")) for line in lines):
            continue
        if lines[0].startswith("|"):
            result.extend(line for line in lines if not re.fullmatch(r"[| :\-]+", line))
        else:
            result.append(" ".join(lines))
    return [
        sentence
        for block in result
        for sentence in re.split(r"(?<=[.!?])\s+(?=[A-ZÁÉÍÓÚÜÑ«])|\s+(?=- )", block)
        if sentence
    ]


def tokens(text: str) -> list[str]:
    return NUMBER.findall(prose(text))


def public_claim(text: str) -> str:
    """Preserve the source claim while replacing private program labels in prose."""
    text = re.sub(r"\brp[23]-[\w-]+", "registro histórico", text, flags=re.I)
    text = prose(text)
    for label, replacement in {
        "RP2": "programa previo",
        "RP3": "cohorte reservada",
        "C10": "cohorte inactiva",
    }.items():
        text = re.sub(rf"\b{label}\b", replacement, text, flags=re.I)
    return text


@lru_cache
def source(name: str) -> object:
    path = (ROOT / name).resolve()
    assert path.is_relative_to(ROOT) and original_path(path).is_file(), name
    assert path.suffix in {".json", ".csv", ".md", ".svg", ".py"}, name
    if path.suffix == ".json":
        return json.loads(original_path(path).read_text(encoding="utf-8-sig"))
    if path.suffix == ".csv":
        with original_path(path).open(encoding="utf-8-sig", newline="") as stream:
            return list(csv.DictReader(stream))
    return original_path(path).read_text(encoding="utf-8-sig")


def selected(name: str, selector: str) -> object:
    value = source(name)
    selection = json.loads(selector)
    if isinstance(selection, dict):
        if selection["operation"] == "weighted_mean":
            rows = [row for row in value if all(row[k] == v for k, v in selection["where"].items())]
            weights = [float(row[selection["weight"]]) for row in rows]
            assert rows and all(weight > 0 for weight in weights)
            return sum(
                float(row[selection["field"]]) * weight
                for row, weight in zip(rows, weights, strict=True)
            ) / sum(weights)
        assert selection["operation"] == "share_of_primary_sessions"
        return (
            100
            * float(value[selection["row"]]["N_sessions"])
            / source("artifacts/rp4_v4_b2_rv15/summary.json")["N_sessions"]
        )
    for key in selection:
        if key == "@length":
            value = len(value)
        elif key == "@percent":
            value *= 100
        elif key in {"@date", "@day", "@year", "@hour", "@minute"}:
            date, _, time = str(value).partition("T")
            value = {
                "@date": date,
                "@day": date[-2:],
                "@year": date[:4],
                "@hour": time[:2],
                "@minute": time[3:5],
            }[key]
        else:
            value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def rendered(value: object, style: str) -> str:
    if style == "literal":
        return str(value)
    if style.startswith("text_number:"):
        return tokens(str(value))[int(style.split(":")[1])]
    specification, locale = style.split("|")
    number = float(value)
    result = format(number, specification)
    if locale == "es":
        result = result.replace(",", "@").replace(".", ",").replace("@", ".")
    return result.replace("-", "−")


def test_defense_sources_claim_coverage_and_all_numbers() -> None:
    manifest = json.loads(
        (original_path(PACKAGE / "evidence_manifest.json")).read_text(encoding="utf-8")
    )
    with (original_path(PACKAGE / "claims_matrix.csv")).open(
        encoding="utf-8", newline=""
    ) as stream:
        rows = list(csv.DictReader(stream))
    assert len({row["claim_id"] for row in rows}) == len(rows)
    for name, expected in manifest["source_sha256"].items():
        assert_historical_sha256(original_path(ROOT / name), expected)
    for name, expected in manifest["document_sha256"].items():
        assert_historical_sha256(original_path(PACKAGE / name), expected)
    for name in ("README.md", "docs/rp4/RESULTADO_FINAL.md"):
        blocks = passages((original_path(ROOT / name)).read_text("utf-8"))
        expected = [digest(block.encode()) for block in blocks]
        actual = [
            row["source_passage_sha256"]
            for row in rows
            if row["kind"] == "source_claim" and row["source_document"] == name
        ]
        assert actual == expected, f"Unmapped or changed source passage: {name}"
        claims = [
            row["claim"]
            for row in rows
            if row["kind"] == "source_claim" and row["source_document"] == name
        ]
        assert claims == [public_claim(block) for block in blocks], name
    for row in rows:
        assert row["artifact_sha256"] == manifest["source_sha256"][row["artifact"]]
        assert row["test"] == "tests/contract/test_rp4_defense_package.py"
        for field in ("claim", "context"):
            assert not re.search(
                r"(?i)\b(codex|claude|chatgpt|mds650|capstone|RP2|RP3|C10)\b|[A-Za-z]:[\\/]",
                row[field],
            ), (row["claim_id"], field)
        for name, expected in json.loads(row["supporting_artifacts"]).items():
            assert manifest["source_sha256"][name] == expected
        if row["kind"] == "package_number":
            value = selected(row["artifact"], row["selector"])
            assert rendered(value, row["rendering"]) == row["claim"], row["claim_id"]
    for name in DOCUMENTS:
        text = (original_path(PACKAGE / name)).read_text(encoding="utf-8")
        actual = [
            row["claim"]
            for row in rows
            if row["kind"] == "package_number" and row["source_document"] == name
        ]
        assert actual == tokens(text), f"Unbound, removed or altered number: {name}"
        assert not re.search(
            r"(?i)\b(codex|claude|chatgpt|mds650|capstone|RP2|RP3|C10)\b", prose(text)
        )
        assert not re.search(r"[A-Za-z]:[\\/]", text)
        assert not re.search(r"\{\{|\bTODO\b|\bTBD\b", text)
        for target in re.findall(r"!?\[[^\]]*\]\(([^)]+)\)", text):
            if not target.startswith(("http", "#")):
                path = ((LINK_PACKAGE or PACKAGE) / target.split("#")[0]).resolve()
                assert path.is_relative_to(ROOT) and public_path(path).is_file(), target


def test_defense_table_and_decisions_match_saved_inference() -> None:
    report = (original_path(ROOT / "docs/rp4/RESULTADO_FINAL.md")).read_text(encoding="utf-8")
    slides = (original_path(PACKAGE / "defense_slides.md")).read_text(encoding="utf-8")
    assert [line for line in report.splitlines() if line.startswith("|")] == [
        line for line in slides.splitlines() if line.startswith("|")
    ]
    v3 = source("artifacts/rp4_v3_b2/summary.json")
    assert all(row["rejected"] for row in v3["contrasts"] if row["contrast"] == "B1_over_B0")
    assert not any(row["rejected"] for row in v3["contrasts"] if row["contrast"] == "B2_over_B1")
    for horizon in (15, 5):
        summary = source(f"artifacts/rp4_v4_b2_rv{horizon}/summary.json")
        assert summary["N_sessions"] == 419 and summary["N_origins"] == 160832
        linear = [row for row in summary["contrasts"] if row["family"] == "log_ridge_harq"]
        assert len(linear) == 2 and all(row["rejected"] for row in linear)
        tree = next(
            row
            for row in summary["contrasts"]
            if row["family"] == "lightgbm_qlike" and row["contrast"] == "B2_over_B1"
        )
        assert not tree["rejected"]
        if horizon == 5:
            assert tree["p_for_decision"] is None
        confirmation = source(f"artifacts/rp4_v4_b3_rv{horizon}/summary.json")
        assert confirmation["N_sessions"] == 25
        assert not confirmation["predeclared_closure"]["satisfied"]
    summary = source("artifacts/rp4_v4_b2_rv15/summary.json")
    cell = next(
        row
        for row in summary["contrasts"]
        if row["family"] == "log_ridge_harq" and row["contrast"] == "B2_over_B1"
    )
    executive = (original_path(PACKAGE / "executive_summary.md")).read_text(encoding="utf-8")
    assert f"{cell['qlike_reduction_percent']:+.3f}" in executive
    assert f"{cell['qlike_reduction_percent']:+.3f}".replace(".", ",") in executive
    for key in ("ci_low", "ci_high"):
        assert f"{cell[key]:.6f}" in executive
        assert f"{cell[key]:.6f}".replace(".", ",") in executive
    headings = re.findall(r"^## (\d+)[. ·—–:-]", slides, flags=re.M)
    assert headings == [str(i) for i in range(1, 13)], headings
    assert "thesis_summary.svg" in slides
    assert "v4_B1_over_B0_cumulative_v2.svg" in slides
    assert "v4_B2_over_B1_cumulative_v2.svg" in slides
    comparison = source("artifacts/rp4_closeout_figures/comparison_v1_v4.csv")
    percent = next(
        row
        for row in comparison
        if all(
            row[k] == v
            for k, v in {
                "version": "v4",
                "target": "RV15",
                "window": "primary",
                "family_group": "linear",
                "contrast": "B2_over_B1",
            }.items()
        )
    )
    for bound in ("low", "high"):
        value = float(percent[f"ci_{bound}_rescaled_percent"])
        assert value == pytest.approx(100 * cell[f"ci_{bound}"] / cell["baseline_qlike"])
        assert f"{value:+.3f}" in executive and f"{value:+.3f}".replace(".", ",") in executive
    for contrast in ("B1_over_B0", "B2_over_B1"):
        base = ROOT / f"docs/figures/rp4/v4_{contrast}_cumulative.svg"
        revised = ROOT / f"docs/figures/rp4/v4_{contrast}_cumulative_v2.svg"
        curves = [
            [
                element.attrib["points"]
                for element in ET.fromstring(original_path(path).read_bytes()).iter()
                if element.tag.endswith("polyline")
            ]
            for path in (base, revised)
        ]
        assert len(curves[0]) == 8 and curves[0] == curves[1]


def test_reviewed_bindings_keep_their_scientific_context() -> None:
    """Equal numbers in unrelated rows must not silently replace reviewed evidence."""
    with (original_path(PACKAGE / "claims_matrix.csv")).open(
        encoding="utf-8", newline=""
    ) as stream:
        rows = list(csv.DictReader(stream))
    expected = {
        "+0.184": (
            "artifacts/rp4_closeout_figures/comparison_v1_v4.csv",
            [25, "ci_low_rescaled_percent"],
        ),
        "+1.061": (
            "artifacts/rp4_closeout_figures/comparison_v1_v4.csv",
            [25, "ci_high_rescaled_percent"],
        ),
        "0.0870": ("artifacts/rp4_v4_b4/distribution_secondary.csv", [3, "p_holm"]),
        "0.0096": ("artifacts/rp4_v4_b4/distribution_secondary.csv", [19, "p_holm"]),
        "138": ("artifacts/rp4_v4_a1/specification.json", ["feature_sets", "B2", "@length"]),
        "134": (
            "docs/rp4/prospective_confirmation_v1_amendment_1_receipt.json",
            ["ablated_predictors"],
        ),
        "0.0001": ("artifacts/rp4_closeout_audit/ridge_lambda_counts.csv", [41, "lambda"]),
        "88": (
            "artifacts/rp4_closeout_audit/ridge_bounds_pruning_summary.csv",
            [11, "removed_min"],
        ),
        "97": (
            "artifacts/rp4_closeout_audit/ridge_bounds_pruning_summary.csv",
            [11, "removed_max"],
        ),
        "0.103": (
            "artifacts/rp4_closeout_audit/descriptive_profiles.csv",
            [461, "base_qlike_equal_session_asset"],
        ),
    }
    for row in rows:
        if row["kind"] != "package_number":
            continue
        key = row["claim"].replace(",", ".")
        if key in expected:
            path, selector = expected[key]
            assert (row["artifact"], json.loads(row["selector"])) == (path, selector), row[
                "claim_id"
            ]


@pytest.mark.parametrize("mutation", ["displayed_number", "source_claim", "wrong_metric_selector"])
def test_contract_rejects_corrupted_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    """Mutations affect temporary copies only; no frozen input or real document changes."""
    copied = tmp_path / "package"
    copied.mkdir()
    # Restore only this layer's sealed inputs into the temporary mutation fixture.
    manifest = json.loads(original_path(PACKAGE / "evidence_manifest.json").read_text("utf-8"))
    for name in {"evidence_manifest.json", *manifest["document_sha256"]}:
        shutil.copyfile(original_path(PACKAGE / name), copied / name)
    # First prove that the unchanged temporary package passes. Link identity remains
    # the original logical directory while the bytes under test are the temp copy.
    monkeypatch.setitem(globals(), "LINK_PACKAGE", PACKAGE)
    monkeypatch.setitem(globals(), "PACKAGE", copied)
    test_defense_sources_claim_coverage_and_all_numbers()
    manifest_path = copied / "evidence_manifest.json"
    manifest = json.loads(original_path(manifest_path).read_text("utf-8"))
    if mutation == "displayed_number":
        name = "executive_summary.md"
        path = copied / name
        text = original_path(path).read_text("utf-8")
        assert "+0,623" in text
        path.write_text(text.replace("+0,623", "+0,624", 1), encoding="utf-8")
    else:
        name = "claims_matrix.csv"
        path = copied / name
        with original_path(path).open(encoding="utf-8", newline="") as stream:
            rows = list(csv.DictReader(stream))
        if mutation == "source_claim":
            rows[0]["claim"] = "Unsupported claim with a copied source hash."
        else:
            row = next(
                row for row in rows if row["kind"] == "package_number" and row["claim"] == "+0,623"
            )
            row["selector"] = '[25,"baseline_qlike_observed"]'
        with path.open("w", encoding="utf-8", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
    # Refreshing a document hash must not bypass source/value/passage checks.
    manifest["document_sha256"][name] = digest(original_path(path).read_bytes())
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(AssertionError):
        test_defense_sources_claim_coverage_and_all_numbers()
