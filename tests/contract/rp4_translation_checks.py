"""Compare translated references by historical identity after public relocation."""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

from scripts.rp4_archive_sources import logical_path


def without_link_targets(text: str) -> str:
    return re.sub(r"(!?\[[^\]]*\])\([^)]*\)", r"\1", text)


def historical_links(text: str, document: Path) -> list[str]:
    result = []
    for target in re.findall(r"!?\[[^\]]*\]\(([^)]*)\)", text):
        link = urlsplit(target)
        if link.scheme or link.netloc or not link.path:
            result.append(target)
        else:
            result.append(
                str(logical_path(document.parent / unquote(link.path)))
                + ("#" + link.fragment if link.fragment else "")
            )
    return result
