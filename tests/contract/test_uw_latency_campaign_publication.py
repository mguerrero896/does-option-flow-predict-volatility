"""The harvested UW campaign state is authoritative over published prose."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from tests.withdrawn_claims import carries_supersession_notice, normalize

from mds650.uw_latency_campaign import canonical_sha256

REPO = Path(__file__).resolve().parents[2]
AGGREGATE = REPO / "artifacts" / "gate5_pit" / "uw_latency_campaign_20260901_v1.json"
STATE = REPO / "artifacts" / "gate5_pit" / "uw_latency_campaign_state_20260901_v1.json"
ANOMALY = REPO / "artifacts" / "gate5_pit" / "uw_latency_anomaly_20260821_v1.json"
GATE5 = REPO / "docs" / "gate5_pit_foundations_v1.md"
REGISTERS = {"docs/methodology_decisions.md"}
CAMPAIGN = re.compile(r"(?:UW|Unusual Whales).{0,80}(?:latency|created_at)", re.I | re.S)
OUTDATED = re.compile(
    r"RUNNING\s*\(unattended\)|\b(?:COLLECTING|COLLECTED_UNRECONCILED|ABANDONED)\b"
)
LIFECYCLE_ESCAPE = re.compile(r"supersed|historical|not a current|no longer|retired", re.I)


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _tracked_markdown() -> list[str]:
    output = subprocess.run(
        ["git", "ls-files", "*.md"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return sorted(output.splitlines())


def _asserts_outdated_campaign_state(text: str) -> bool:
    """Match a local UW lifecycle claim, not unrelated state words elsewhere."""
    for match in OUTDATED.finditer(text):
        context = normalize(text[max(0, match.start() - 400) : match.end() + 400])
        if CAMPAIGN.search(context) and not LIFECYCLE_ESCAPE.search(context):
            return True
    return False


def test_campaign_artifacts_are_self_hashed_and_target_blind() -> None:
    for path in (AGGREGATE, STATE, ANOMALY):
        payload = _load(path)
        assert payload["self_sha256"] == canonical_sha256(payload)
        serialized = json.dumps(payload).lower()
        assert not any(
            token in serialized
            for token in (
                "rv30",
                "qlike",
                "forecast",
                "record" + "_id",
                "historical" + "_tape_",
            )
        )
        assert "\\" not in serialized


def test_campaign_state_is_registered_canonical_authority() -> None:
    state = _load(STATE)
    canonical = _load(REPO / "data" / "CANONICAL_STATE.json")
    assert state["state"] == "RECONCILED_PARTIAL"
    assert canonical["uw_latency_campaign"]["state"] == state["state"]
    assert canonical["uw_latency_campaign"]["state_self_sha256"] == state["self_sha256"]
    assert STATE.relative_to(REPO).as_posix() in canonical["authorized_sources"]
    assert AGGREGATE.relative_to(REPO).as_posix() in canonical["authorized_sources"]
    assert ANOMALY.relative_to(REPO).as_posix() in canonical["authorized_sources"]


def test_published_campaign_state_is_current_or_explicitly_historical() -> None:
    failures: list[str] = []
    for relative in _tracked_markdown():
        if relative in REGISTERS:
            continue
        text = (REPO / relative).read_text(encoding="utf-8", errors="replace")
        if _asserts_outdated_campaign_state(text) and not carries_supersession_notice(text):
            failures.append(relative)
    assert not failures, (
        "published UW campaign lifecycle contradicts state artifact: " + ", ".join(failures)
    )


def test_gate5_publishes_partial_state_and_cross_channel_boundary() -> None:
    text = GATE5.read_text(encoding="utf-8")
    required = (
        "RECONCILED_PARTIAL",
        "PROXY_ONLY_CROSS_CHANNEL",
        "CROSS_CHANNEL_NOT_IDENTIFIABLE",
        "AGGREGATE_ALERT_VS_INDIVIDUAL_TRADE_NOT_COMPARABLE",
        "2,418",
        "100%",
        "2026-08-21",
        "COLLECTOR_RESTART_REPLAY_DUPLICATION",
    )
    assert not [token for token in required if token not in text]


def test_campaign_uses_only_the_existing_alert_channel() -> None:
    aggregate = _load(AGGREGATE)
    assert aggregate["alerting"] == {
        "operational_path": "logs/UW_LATENCY_ALERT.txt",
        "desktop_popup": True,
        "new_channel_created": False,
    }
