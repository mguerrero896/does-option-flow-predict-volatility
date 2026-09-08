"""The dry-run path must exit before any publishing or scientific execution."""

from pathlib import Path

from scripts.verify_public_projection import (
    HISTORICAL_QUOTE_PATH,
    INTERNAL_LABEL,
    collective_voice_tokens,
    language_counts,
    prose_text,
)


def test_dry_run_exits_before_the_existing_publication_path() -> None:
    shell = (Path(__file__).resolve().parents[2] / "scripts/publish_mirror.sh").read_text("utf-8")
    dry = shell.index('if [[ "${1:-}" == "--dry-run" ]]')
    finish = shell.index("exit 0", dry)
    assert dry < finish < shell.index("run_local_evidence_gates.py")
    assert "verify_public_projection.py" in shell[dry:finish]
    spanish, english = language_counts(
        "La evaluación de los resultados tiene una muestra con datos del registro. "
        "Las sesiones siguen pendientes para la prueba del flujo."
    )
    assert spanish >= 5 and spanish > english
    spanish, english = language_counts(
        "The registered evaluation uses the same sample and reports all results. "
        "```\nla muestra con los datos\n```"
    )
    assert english > spanish
    assert INTERNAL_LABEL.search(prose_text("The MDS650 capstone report."))
    assert not INTERNAL_LABEL.search(
        prose_text("Run `python -m mds650.cli`; see [code](../src/mds650/cli.py).")
    )
    assert not INTERNAL_LABEL.search(prose_text("The historical mds650.har module."))


def test_author_voice_screen_covers_prose_templates_and_preserves_only_the_frozen_quote() -> None:
    assert collective_voice_tokens("README.md", "We use our team's findings.") == [
        "We",
        "our",
        "team",
    ]
    assert collective_voice_tokens("docs/request.md", "```text\nWe request an answer.\n```") == [
        "We"
    ]
    assert (
        collective_voice_tokens("README.md", "US equities; this study uses `our_variable`.") == []
    )
    source = Path(__file__).resolve().parents[2] / HISTORICAL_QUOTE_PATH
    original = source.read_text("utf-8")
    assert collective_voice_tokens(HISTORICAL_QUOTE_PATH, original) == []
    assert collective_voice_tokens(HISTORICAL_QUOTE_PATH, original + " Changed.") == ["we"]
    assert collective_voice_tokens("docs/another.md", original) == ["we"]
