"""English protocol copies preserve quantities, rules, commands and original seals."""

from __future__ import annotations

import json
import re
from decimal import Decimal
from pathlib import Path

from scripts.rp4_archive_sources import (
    assert_historical_sha256,
    original_path,
    public_path,
)
from tests.contract.rp4_translation_checks import historical_links

ROOT = Path(__file__).resolve().parents[2]
ARCHIVE = ROOT / "docs/archive/rp4/presentation_originals"
FILES = (
    "RUNBOOK.md",
    "data_and_execution_v1.md",
    "specification_v4.md",
    "decision_133_v4.md",
    "prospective_confirmation_v1.md",
    "prospective_confirmation_v1_amendment_1.md",
    "prospective_confirmation_v1_amendment_2.md",
    "prospective_confirmation_v1_amendment_3.md",
    "prospective_confirmation_v1_amendment_3_context_1.md",
)
TRANSLATION_LABEL = (
    "**English translation. Historical seals refer to the preserved original bytes.**"
)


def prose_values(text: str, *, spanish: bool) -> list[Decimal]:
    # Code, identifiers and references have separate exact comparisons below.
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    text = re.sub(r"`[^`]*`", "", text)
    text = re.sub(r"(!?\[[^\]]*\])\([^)]*\)", r"\1", text)
    if spanish:
        text = re.sub(
            r"(?<![\d.])([1-9]\d{0,2}(?:\.\d{3})+)(?!\d)",
            lambda match: match[1].replace(".", ""),
            text,
        )
        text = re.sub(r"(?<=\d),(?=\d)", ".", text)
    else:
        text = re.sub(r"(?<=\d),(?=\d)", "", text)
    return [Decimal(value) for value in re.findall(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", text)]


def inline_identifiers(text: str) -> list[str]:
    text = re.sub(r"```.*?```", "", text, flags=re.S)
    # The two local roots in the historical specification are publication-redacted.
    return [
        value
        for value in re.findall(r"`([^`]*)`", text)
        if not re.match(r"(?:[A-Z]:[/\\]|private-input/)", value)
    ]


def command_blocks(text: str) -> list[str]:
    def without_display_prose(code: str) -> str:
        code = re.sub(r"(?m)^\s*#.*$", "", code)
        return re.sub(r"throw '[^']*'", "throw '<translated error>'", code)

    return [without_display_prose(code) for code in re.findall(r"```(.*?)```", text, re.S)]


def test_full_protocol_translations_retain_all_registered_content() -> None:
    sources = json.loads((ARCHIVE / "original_paths.json").read_bytes())
    for name in FILES:
        entry = sources["docs/rp4/" + name]
        logical = ROOT / "docs/rp4" / name
        expected = entry["sha256"]
        if name == "RUNBOOK.md":
            # Closure pinned CRLF; the translation receipt independently retains LF.
            expected = "5890e0f3d68d34be9cb40575d6c1905da90dfd0574e00e1eeb7b9295d16ece31"
        assert_historical_sha256(logical, expected)
        original = original_path(logical).read_bytes()
        old = original.decode("utf-8").replace("\r\n", "\n")
        destination = public_path(logical)
        new = destination.read_text(encoding="utf-8")
        assert prose_values(old, spanish=True) == prose_values(new, spanish=False), name
        assert inline_identifiers(old) == inline_identifiers(new), name
        assert command_blocks(old) == command_blocks(new), name
        assert re.findall(r"[0-9a-f]{64}", old) == re.findall(r"[0-9a-f]{64}", new), name
        assert historical_links(old, logical) == historical_links(new, destination), name
        assert new.count(TRANSLATION_LABEL) == 1, name
        assert len(re.split(r"\n\s*\n", old.strip())) + 1 == len(
            re.split(r"\n\s*\n", new.strip())
        ), name
        assert ("capital_go=false" in old) == ("capital_go=false" in new), name


def test_prospective_reads_keep_their_distinct_scope_and_power() -> None:
    final = public_path(ROOT / "docs/rp4/prospective_confirmation_v1_amendment_3.md").read_text(
        encoding="utf-8"
    )
    assert "45 is D on reaching 20 prospective sessions" in final
    assert "not a read of 45 prospective sessions" in final
    assert "80.05% applies exclusively to isolated H2" in final
    assert "approximately 54.98% under these approximations" in final
    assert "No additional intermediate read is permitted" in final
