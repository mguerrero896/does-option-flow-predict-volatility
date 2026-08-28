"""A restarted collector must resume the tape, not rewrite it.

Measured on the live 2026-08-21 session at 05:01 local. The watchdog restarted a
dead collector; the new process re-entered main() with seen={} and cursors
rewound to the open, re-fetched the whole session, and appended it again:

    observations.jsonl   1,940,303 B  ->  4,653,807 B
    4116 lines, 1738 unique record_id, 1200 duplicated, max repetition 3

58% of the tape was duplicate. The verifier counts lines, so the duplication
inflates the record count and makes a false green stronger, not weaker.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "uw_latency_collector.py"
ASSETS = ("AAPL", "AMZN", "META", "MSFT", "NVDA", "TSLA")


def _load(external_root: Path) -> Any:
    import os

    os.environ["MDS650_EXTERNAL_ROOT"] = str(external_root)
    sys.modules.pop("uw_latency_collector", None)
    spec = importlib.util.spec_from_file_location("uw_latency_collector", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["uw_latency_collector"] = module
    spec.loader.exec_module(module)
    return module


def _tape(session_dir: Path, count: int) -> None:
    session_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        json.dumps(
            {
                "kind": "observation",
                "asset": ASSETS[i % len(ASSETS)],
                "receipt_utc": "2026-08-21T14:00:00+00:00",
                "record_id": f"rec-{i}",
                "record": {"start_time": 1787319000000 + i},
            }
        )
        for i in range(count)
    ]
    (session_dir / "observations.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_resume_rebuilds_seen_so_a_restart_cannot_duplicate(tmp_path: Path) -> None:
    module = _load(tmp_path)
    session_dir = tmp_path / "uw_latency" / "sessions" / "2026-08-21"
    _tape(session_dir, 120)

    cursors = {asset: 1787319000000 for asset in ASSETS}
    seen: dict[str, set[str]] = {asset: set() for asset in ASSETS}
    total = module._resume(session_dir, cursors, seen)

    assert total == 120, "every record already on disk must be counted as observed"
    assert sum(len(ids) for ids in seen.values()) == 120, "seen must contain the whole tape"
    assert "rec-0" in seen["AAPL"]


def test_resume_advances_cursors_past_the_existing_tape(tmp_path: Path) -> None:
    """Rewound cursors are what make the restart re-fetch the session."""
    module = _load(tmp_path)
    session_dir = tmp_path / "uw_latency" / "sessions" / "2026-08-21"
    _tape(session_dir, 120)

    opened = 1787318999999
    cursors = {asset: opened for asset in ASSETS}
    seen: dict[str, set[str]] = {asset: set() for asset in ASSETS}
    module._resume(session_dir, cursors, seen)

    assert all(cursors[asset] > opened for asset in ASSETS), cursors


def test_resume_on_a_fresh_session_is_a_no_op(tmp_path: Path) -> None:
    module = _load(tmp_path)
    session_dir = tmp_path / "uw_latency" / "sessions" / "2026-08-21"
    session_dir.mkdir(parents=True)
    cursors = {asset: 1787319000000 for asset in ASSETS}
    seen: dict[str, set[str]] = {asset: set() for asset in ASSETS}
    assert module._resume(session_dir, cursors, seen) == 0


def test_resume_survives_a_torn_final_line(tmp_path: Path) -> None:
    """A hard kill mid-write leaves a truncated line; resume must not die on it."""
    module = _load(tmp_path)
    session_dir = tmp_path / "uw_latency" / "sessions" / "2026-08-21"
    _tape(session_dir, 12)
    tape = session_dir / "observations.jsonl"
    with tape.open("a", encoding="utf-8") as handle:
        handle.write('{"kind": "observation", "asset": "AAPL", "record_i')
    cursors = {asset: 1787319000000 for asset in ASSETS}
    seen: dict[str, set[str]] = {asset: set() for asset in ASSETS}
    assert module._resume(session_dir, cursors, seen) == 12


def test_poll_cycle_rejects_records_outside_the_session(tmp_path: Path) -> None:
    module = _load(tmp_path)
    session_dir = tmp_path / "uw_latency" / "sessions" / "2026-08-21"
    session_dir.mkdir(parents=True)
    opened = 1787319000000

    class Provider:
        def flow_alerts(self, **_kwargs: Any) -> SimpleNamespace:
            return SimpleNamespace(
                payload={
                    "data": [
                        {"id": "stale", "start_time": opened - 1},
                        {"id": "valid", "start_time": opened + 1},
                    ]
                }
            )

    cursors = {asset: opened for asset in ASSETS}
    seen: dict[str, set[str]] = {asset: set() for asset in ASSETS}
    observed = module._poll_cycle(
        Provider(), session_dir, cursors, seen, opened, opened + 10_000
    )

    assert observed == len(ASSETS)
    lines = (session_dir / "observations.jsonl").read_text().splitlines()
    rows = [json.loads(line) for line in lines]
    assert {row["record_id"] for row in rows} == {"valid"}
