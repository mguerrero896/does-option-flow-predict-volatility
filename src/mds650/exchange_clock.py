"""The exchange clock: market-facing date decisions name their zone, explicitly.

This machine runs at UTC+10 (Sydney). Its local midnight is mid-morning on the NYSE
floor, so any market decision taken from the machine clock — ``date.today()``, a naive
``datetime.now()`` — is wrong for up to fourteen hours a day: the RP3 acquirer's
adversarial review proved that a session *still trading* in New York would have been
acquired as "complete" and its truncation made permanent by idempotency.

The durable rule is NOT to move the machine's clock to New York time. The machine
clock is correct for where the machine is, and local automation depends on it — the
Phase 8 watchdog fires daily at 20:00 *local*, and re-zoning the machine mid-cohort
would shift that trigger ~14 real-world hours. The rule is that code never trusts the
machine's zone for market decisions: it asks this module, which answers in the
exchange's own zone regardless of where it runs (laptop, CI, cloud).

``tests/contract/test_exchange_clock_contract.py`` enforces the rule as a tripwire:
no RP3 surface may read the machine-local clock.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Final
from zoneinfo import ZoneInfo

#: The venue every current project trades on. A future non-NYSE project adds its own
#: constant here rather than reaching for the machine clock.
NEW_YORK: Final = ZoneInfo("America/New_York")


def ny_now() -> datetime:
    """The current moment on the exchange's clock, timezone-aware."""

    return datetime.now(NEW_YORK)


def ny_today() -> date:
    """Today as the exchange sees it — the only 'today' market decisions may use."""

    return ny_now().date()
