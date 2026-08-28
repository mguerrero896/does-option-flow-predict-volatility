"""Phase 9 completion is metadata-only until the owner-authorized one-read evaluation."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from mds650 import phase9_contract as contract

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "phase9_collect.py"
REGISTER_SCRIPT = ROOT / "scripts" / "register_phase9_tasks.ps1"
PROTOCOL = ROOT / "docs" / "phase9_total_contribution_protocol_v1.md"
PROTOCOL_FREEZE = ROOT / "artifacts" / "phase9" / "protocol_freeze.json"


def _load() -> Any:
    spec = importlib.util.spec_from_file_location("phase9_collect", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["phase9_collect"] = module
    previous = os.environ.get("MDS650_DATA_ROOT")
    os.environ["MDS650_DATA_ROOT"] = str(ROOT / ".test-data-unavailable")
    try:
        spec.loader.exec_module(module)
    finally:
        if previous is None:
            os.environ.pop("MDS650_DATA_ROOT", None)
        else:
            os.environ["MDS650_DATA_ROOT"] = previous
    return module


def _manifest(module: Any) -> dict[str, Any]:
    session = "2026-08-19"
    expected = len(contract.ASSETS) * len(
        contract.origins_utc(module.dt.date.fromisoformat(session))
    )
    return {
        "session": session,
        "bars_rows": len(contract.ASSETS) * 380,
        "bars_by_asset": {asset: 380 for asset in contract.ASSETS},
        "tape_bytes": 1_000_000,
        "quote_rows": expected,
        "quote_ok": expected,
        "quote_ok_by_asset": {
            asset: expected // len(contract.ASSETS) for asset in contract.ASSETS
        },
        "sha256": {
            "bars.parquet": "a" * 64,
            f"full_tape_{session}.zip": "b" * 64,
            "quotes.parquet": "c" * 64,
        },
    }


def test_phase9_only_counts_a_manifest_with_full_quote_coverage() -> None:
    module = _load()
    manifest = _manifest(module)
    manifest["quote_ok"] = 1
    assert not contract.session_is_complete(manifest)


def test_phase9_rejects_missing_or_malformed_manifest_hashes_without_reading_raw_files() -> None:
    module = _load()
    manifest = _manifest(module)
    manifest["sha256"]["quotes.parquet"] = "not-a-digest"
    problems = contract.capture_problems(manifest)
    assert any("sha256" in problem for problem in problems)


def test_phase9_accepts_full_per_asset_coverage_and_complete_manifest_metadata() -> None:
    module = _load()
    assert contract.session_is_complete(_manifest(module))


def test_collector_runs_after_observed_full_tape_publication_window() -> None:
    source = REGISTER_SCRIPT.read_text(encoding="utf-8")
    assert '-Time "09:45"' in source
    assert '-Time "08:10"' not in source


def test_phase9_protocol_bytes_and_read_gate_remain_frozen() -> None:
    freeze = json.loads(PROTOCOL_FREEZE.read_text(encoding="utf-8"))
    assert hashlib.sha256(PROTOCOL.read_bytes()).hexdigest() == freeze["protocol_sha256"]
    assert freeze["sessions"] == "first 60 XNYS sessions strictly after 2026-08-18"
    assert freeze["reads"] == 0
    assert contract.TARGET_SESSIONS == 60


def test_phase9_checkpoint_survives_before_a_manifest_exists(tmp_path: Path) -> None:
    module = _load()
    module._checkpoint(tmp_path, "tape")

    checkpoint = contract.last_checkpoint(tmp_path)

    assert checkpoint is not None
    assert checkpoint.startswith("tape at ")


def test_last_closed_session_uses_the_previous_date_before_new_york_close() -> None:
    early_friday = datetime(2026, 8, 28, 1, 0, tzinfo=ZoneInfo("America/New_York"))
    assert contract.last_closed_session(early_friday).isoformat() == "2026-08-27"
