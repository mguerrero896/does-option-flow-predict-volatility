"""Office documents leak in their metadata, not only in their visible text.

Measured 2026-08-26: two published workbooks named an assistant as their
`dc:creator` ("Codex evidence-first audit"), invisible in the spreadsheet and
present in every download. Deleting text does not touch `docProps/`, so the
class needs its own check.

Scope is deliberately the PUBLISHED tree. Frozen artifacts are exempt from
editing by decision 62; where one carries such metadata the remedy is a
sanitised copy under a new name, not a modification of sealed evidence.
"""

from __future__ import annotations

import re
import subprocess
import zipfile
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OFFICE_SUFFIXES = (".docx", ".xlsx", ".pptx")
#: Assistant names and machine paths. Not a secret-scanner: a professionalism check.
#: The separator class needs an ESCAPED backslash as well as a slash — in a raw
#: string `[\/]` matches only the slash, so a Windows-authored path (the common
#: case for these files) slipped straight through the first version of this guard.
INTERNAL_MARKERS = re.compile(
    r"(Codex|Claude|ChatGPT|Anthropic|OpenAI|[A-Z]:[\\\\/]Users[\\\\/])", re.IGNORECASE
)


def _tracked_office_documents() -> list[Path]:
    listed = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, cwd=REPO, check=False
    ).stdout.split()
    return [REPO / name for name in listed if name.lower().endswith(OFFICE_SUFFIXES)]


def test_no_published_office_document_names_an_assistant_or_a_local_path() -> None:
    offenders = []
    for document in _tracked_office_documents():
        if not document.is_file():
            continue
        with zipfile.ZipFile(document) as archive:
            for entry in archive.namelist():
                if not (entry.startswith("docProps/") or "comment" in entry.lower()):
                    continue
                body = archive.read(entry).decode("utf-8", "ignore")
                found = sorted(set(INTERNAL_MARKERS.findall(body)))
                if found:
                    offenders.append(f"{document.relative_to(REPO)} [{entry}]: {found}")
    assert not offenders, (
        "published Office documents carry internal metadata (invisible in the "
        "document, present in every download):\n  " + "\n  ".join(offenders)
    )
