"""Keep the submission Word report on the current evidence-cutoff narrative."""

from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[2]
WORD_TEXT = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"


def test_retired_proposal_is_not_part_of_the_current_release() -> None:
    assert not (ROOT / "reports" / "proposal_draft_v2.docx").exists()


def test_current_word_report_is_not_the_superseded_draft() -> None:
    with ZipFile(ROOT / "reports" / "final_report_draft_v2.docx") as archive:
        document = ElementTree.fromstring(archive.read("word/document.xml"))

    text = " ".join(
        " ".join(node.text or "" for node in document.iter(WORD_TEXT)).split()
    )
    assert "EVIDENCE_CUTOFF_COMPLETE" in text
    assert "rp2-v3-20260827-remediation3" in text
    assert "Phase 9 is an ongoing 60-session prospective follow-up" in text
    assert "60 complete sessions produce 36 scored sessions" in text
    assert "zero scored sessions" in text
    assert "sealed_cohorts_read=0" in text
    assert "PROSE_COMPLETE_PENDING_D003_AND_PHASE8" not in text
    assert "[D003]" not in text
    assert "[PHASE8]" not in text
    assert "[PHASE9-NOTE]" not in text
