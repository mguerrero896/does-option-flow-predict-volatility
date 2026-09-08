"""English public reports retain all original numerical assertions and references."""

from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path

from scripts.rp4_archive_sources import assert_historical_sha256, original_path, public_path
from tests.contract.rp4_translation_checks import historical_links, without_link_targets

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "docs/archive/rp4/presentation_originals"


def test_full_reports_preserve_quantitative_claims_and_links() -> None:
    originals = json.loads((ARCHIVE / "original_paths.json").read_bytes())
    number = re.compile(r"[-+]?\d+(?:[.,]\d+)*(?:[eE][-+]?\d+)?")

    def values(text: str, *, spanish_numbers: bool) -> list[Decimal]:
        return [
            Decimal(
                value.replace(".", "").replace(",", ".")
                if spanish_numbers
                else value.replace(",", "")
            )
            for value in number.findall(without_link_targets(text))
        ]

    for name in (
        "results_v4.md",
        "RESULTADO_FINAL.md",
        "RESULTADO_FINAL_revision_1.md",
        "RESULTADO_FINAL_revision_2.md",
    ):
        source = originals["docs/rp4/" + name]
        logical = ROOT / "docs/rp4" / name
        assert_historical_sha256(logical, source["sha256"])
        original = original_path(logical).read_bytes()
        old = original.decode("utf-8")
        destination = public_path(logical)
        new = destination.read_text(encoding="utf-8")
        assert values(old, spanish_numbers=name != "results_v4.md") == values(
            new, spanish_numbers=False
        ), name
        assert historical_links(old, logical) == historical_links(new, destination), name
        assert len(re.split(r"\n\s*\n", old.strip())) == len(re.split(r"\n\s*\n", new.strip())), (
            name
        )
        assert "capital_go=false" in new
        if name.startswith("RESULTADO_FINAL"):
            assert new.splitlines()[0] == (
                "Out-of-sample walk-forward evaluation; partition fixed on 2026-09-07."
            )
            assert "| v4 · RV15, primary |" in new
            assert "| v4 · RV5, secondary |" in new
            assert "not interchangeable" in new
