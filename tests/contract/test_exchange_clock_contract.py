"""Tripwire: no RP3 surface reads the machine-local clock. Ever.

This machine runs at UTC+10; the exchange runs at America/New_York. The adversarial
review of the RP3 acquirer proved what a machine-local ``date.today()`` does here: a
session still trading in New York gets acquired as "complete" and idempotency makes
the truncation permanent. The owner's instinct was to re-zone the machine's clock to
New York; the recorded decision is the opposite — the machine clock stays correct for
where the machine is (the Phase 8 watchdog fires at 20:00 *local*), and CODE names its
zone explicitly through ``mds650.exchange_clock``. This test is that decision as a
tripwire: prose can be forgotten, a failing test cannot.
"""

from __future__ import annotations

import re
from pathlib import Path

from mds650 import exchange_clock

ROOT = Path(__file__).resolve().parents[2]

#: Every file that plans, guards, scores, or banks RP3 sessions. Extend this list
#: when a new RP3 surface appears — the glob below catches new files automatically.
_RP3_SURFACES = (
    sorted((ROOT / "scripts").glob("rp3_*.py"))
    + sorted((ROOT / "src" / "mds650" / "rp3").glob("*.py"))
)

#: Machine-local clock reads. ``datetime.now(...)`` with an explicit zone argument is
#: fine and deliberately not matched; a bare ``datetime.now()`` is not.
_NAIVE_CLOCK = re.compile(
    r"date\.today\(\)|datetime\.utcnow\(|datetime\.now\(\s*\)|time\.localtime\("
)


def test_no_rp3_surface_reads_the_machine_clock() -> None:
    assert _RP3_SURFACES, "the RP3 surfaces disappeared — the glob is broken, not clean"
    offenders = []
    for path in _RP3_SURFACES:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if _NAIVE_CLOCK.search(line):
                offenders.append(f"{path.relative_to(ROOT)}:{number}: {line.strip()}")
    assert not offenders, (
        "machine-local clock read in an RP3 surface — use mds650.exchange_clock "
        "(ny_today/ny_now) instead:\n" + "\n".join(offenders)
    )


def test_the_exchange_clock_answers_in_new_york() -> None:
    """The helper's date equals UTC-now rendered in America/New_York, by definition."""

    from datetime import UTC, datetime
    from zoneinfo import ZoneInfo

    expected = datetime.now(UTC).astimezone(ZoneInfo("America/New_York")).date()
    assert exchange_clock.ny_today() == expected
    now = exchange_clock.ny_now()
    assert now.tzinfo is not None
    assert str(now.tzinfo) == "America/New_York"
