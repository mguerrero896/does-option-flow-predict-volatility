"""The live UW inventory must match the current immutable campaign snapshot."""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
AGGREGATE = REPO / "artifacts/gate5_pit/uw_latency_campaign_20260902_v1.json"
STATE = REPO / "artifacts/gate5_pit/uw_latency_campaign_state_20260902_v1.json"
ANOMALY = REPO / "artifacts/gate5_pit/uw_latency_anomaly_20260821_v1.json"
OPTOUT = "MDS650_UW_LATENCY_FRESHNESS_MAY_SKIP"
CONFIGURED_ROOT = os.environ.get("MDS650_EXTERNAL_ROOT") or os.environ.get(
    "MDS650_DATA_ROOT"
)
MAY_SKIP = os.environ.get(OPTOUT) == "1"

_spec = importlib.util.spec_from_file_location(
    "harvest_uw_latency_campaign", REPO / "scripts/harvest_uw_latency_campaign.py"
)
assert _spec is not None and _spec.loader is not None
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def _external_root() -> Path:
    sessions = (
        Path(CONFIGURED_ROOT) / "uw_latency" / "sessions" if CONFIGURED_ROOT else None
    )
    if sessions is not None and sessions.is_dir():
        return Path(CONFIGURED_ROOT)
    if MAY_SKIP:
        pytest.skip(f"licensed UW store unavailable and {OPTOUT}=1")
    pytest.fail(
        "UW latency freshness cannot be verified without the licensed store; "
        f"set {OPTOUT}=1 only in a documented environment without that disk"
    )


def test_uw_latency_snapshot_matches_live_regeneration() -> None:
    builder = getattr(_module, "build_snapshot", None)
    assert callable(builder), "harvester lacks build_snapshot regeneration entry point"
    fresh_aggregate, fresh_state = builder(
        external_root=_external_root(),
        anomaly_artifact=ANOMALY,
        aggregate_path=AGGREGATE.relative_to(REPO).as_posix(),
        as_of_date="2026-09-02",
    )
    committed_aggregate = json.loads(AGGREGATE.read_text(encoding="utf-8"))
    committed_state = json.loads(STATE.read_text(encoding="utf-8"))
    assert committed_aggregate == fresh_aggregate, (
        "UW latency aggregate is stale; run scripts/harvest_uw_latency_campaign.py "
        "with --external-root and new dated --aggregate-output/--state-output paths, "
        "then advance the current v2 authority"
    )
    assert committed_state == fresh_state, (
        "UW latency lifecycle state is stale; run scripts/harvest_uw_latency_campaign.py "
        "with --external-root and new dated --aggregate-output/--state-output paths, "
        "then advance the current v2 authority"
    )


def test_freshness_optout_is_explicit_in_hosted_and_local_ci_simulation() -> None:
    workflow = (REPO / ".github/workflows/ci.yml").read_text(encoding="utf-8")
    tier2 = (REPO / "scripts/run_local_evidence_gates.py").read_text(encoding="utf-8")
    contributing = (REPO / "CONTRIBUTING.md").read_text(encoding="utf-8")
    assert workflow.count(OPTOUT) == 2
    assert OPTOUT in tier2
    assert OPTOUT in contributing
