"""Tripwire: polars ``dt.hour()``/``dt.minute()`` must cast before anything else.

``dt.hour()`` returns Int8, and ``15 * 60`` overflows it silently: measured on
polars 1.42.1, the 9:30 New York open computed as −512 and the 15:59 close as
−635 — a deterministic sawtooth, not a crash, which is why it fed HAR's
seasonality basis (`minute_fraction`) and Gate 8's `session_minute` garbage until
2026-08-25 without any test noticing. `bars.normalise_bars` had sidestepped the
trap years of code earlier by casting first; the v2 tape extractor hit it live.

The rule this test enforces is the one every surviving call site now follows:
**every ``.dt.hour()`` and ``.dt.minute()`` in src/ and scripts/ is immediately
followed by ``.cast(``** — arithmetic on the Int8 is never allowed, and the
sanctioned spelling for session minutes is ``mds650.har.session_minute_expression``.
"""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

#: The call, captured with whatever follows it (whitespace and newlines allowed
#: between the call and its continuation, because these expressions span lines).
_CALL = re.compile(r"\.dt\.(hour|minute)\(\)\s*\n?\s*(\.\w+\(|[^\s.])")


def test_every_hour_minute_call_casts_before_arithmetic() -> None:
    offenders = []
    for path in sorted((ROOT / "src").rglob("*.py")) + sorted((ROOT / "scripts").rglob("*.py")):
        source = path.read_text(encoding="utf-8", errors="replace")
        for match in _CALL.finditer(source):
            follower = match.group(2)
            if follower.startswith(".cast("):
                continue
            line = source.count("\n", 0, match.start()) + 1
            rel = path.relative_to(ROOT)
            offenders.append(f"{rel}:{line}: dt.{match.group(1)}() -> {follower!r}")
    assert not offenders, (
        "Int8-returning dt.hour()/dt.minute() used without an immediate .cast( — "
        "arithmetic overflows silently (9:30 -> -512). Use "
        "mds650.har.session_minute_expression or cast first:\n" + "\n".join(offenders)
    )
