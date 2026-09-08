"""The English publication must preserve every historical result and diagnostic."""

from __future__ import annotations

import json
import re
from pathlib import Path

from scripts.rp4_archive_sources import assert_historical_sha256, original_path, public_path
from tests.contract.rp4_translation_checks import historical_links, without_link_targets

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "docs/archive/rp4/results_v3_original"


def test_complete_translation_preserves_numbers_links_and_diagnostics() -> None:
    logical = ROOT / "docs/rp4/results_v3.md"
    original = original_path(logical).read_bytes()
    manifest = json.loads((ARCHIVE / "report_manifest.json").read_bytes())
    assert_historical_sha256(logical, manifest["outputs_sha256"]["docs/rp4/results_v3.md"])
    assert_historical_sha256(
        ROOT / "artifacts/rp4_v3_code/report_v3.py",
        manifest["inputs_sha256"]["artifacts/rp4_v3_code/report_v3.py"],
    )
    old = original.decode("utf-8")
    destination = public_path(logical)
    new = destination.read_text(encoding="utf-8")

    def numeric_tokens(text: str) -> list[str]:
        text = without_link_targets(text)
        # Translate locale notation only; data tables and JSON already use decimal points.
        for source, target in (
            ("0,05", "0.05"),
            ("0,90", "0.90"),
            ("0,5", "0.5"),
            ("9.999 réplicas", "9999 resamples"),
            ("9,999 resamples", "9999 resamples"),
        ):
            text = text.replace(source, target)
        return re.findall(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", text)

    assert numeric_tokens(old) == numeric_tokens(new)
    assert len(old.splitlines()) == len(new.splitlines())

    # This sole former link is withdrawn because it exposes licensed fit-bound data.
    # Its descriptive text and every scientific assertion remain in the report.
    def permitted_links(text: str, document: Path) -> list[str]:
        return [
            link
            for link in historical_links(text, document)
            if not link.endswith("artifacts\\rp4_v3_b4\\fit_selection.csv")
            and not link.endswith("artifacts/rp4_v3_b4/fit_selection.csv")
        ]

    assert permitted_links(old, logical) == permitted_links(new, destination)
    pattern = r"RP4_V3_LOGISTIC_NOT_CONVERGED:(\{[^\n]*?\})"
    assert re.findall(pattern, old) == re.findall(pattern, new)
    assert new.startswith("# RP4 — v3 results and v1/v2 comparison\n")
    assert "NOT SATISFIED IN THIS WINDOW" in new
    assert "does not remove adaptive selection between versions" in new
    assert "capital_go=false" in new
