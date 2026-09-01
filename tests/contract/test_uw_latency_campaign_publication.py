"""The harvested UW campaign state is authoritative over published prose."""

from __future__ import annotations

import json
import re
import subprocess
from decimal import Decimal
from pathlib import Path

from tests.withdrawn_claims import carries_supersession_notice, normalize

from mds650.uw_latency_campaign import canonical_sha256

REPO = Path(__file__).resolve().parents[2]
AGGREGATE = REPO / "artifacts" / "gate5_pit" / "uw_latency_campaign_20260902_v1.json"
STATE = REPO / "artifacts" / "gate5_pit" / "uw_latency_campaign_state_20260902_v1.json"
PRIOR_AGGREGATE = (
    REPO / "artifacts" / "gate5_pit" / "uw_latency_campaign_20260901_v2.json"
)
PRIOR_STATE = (
    REPO / "artifacts" / "gate5_pit" / "uw_latency_campaign_state_20260901_v2.json"
)
LEGACY_AGGREGATE = (
    REPO / "artifacts" / "gate5_pit" / "uw_latency_campaign_20260901_v1.json"
)
LEGACY_STATE = (
    REPO / "artifacts" / "gate5_pit" / "uw_latency_campaign_state_20260901_v1.json"
)
ANOMALY = REPO / "artifacts" / "gate5_pit" / "uw_latency_anomaly_20260821_v1.json"
GATE5 = REPO / "docs" / "gate5_pit_foundations_v1.md"
REPORT = REPO / "reports" / "final_report_draft_v2.md"
REGISTERS = {"docs/methodology_decisions.md"}
CAMPAIGN = re.compile(r"(?:UW|Unusual Whales).{0,80}(?:latency|created_at)", re.I | re.S)
OUTDATED = re.compile(
    r"RUNNING\s*\(unattended\)|\b(?:COLLECTING|COLLECTED_UNRECONCILED|ABANDONED)\b"
)
OUTDATED_HOURLY = re.compile(
    r"NOT_AVAILABLE_IN_RECONCILIATION_JSON|CAMPAIGN_HARVEST_MAY_NOT_READ_LICENSED_ROW_DATA"
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
    for path in (
        AGGREGATE,
        STATE,
        PRIOR_AGGREGATE,
        PRIOR_STATE,
        LEGACY_AGGREGATE,
        LEGACY_STATE,
        ANOMALY,
    ):
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


def test_declined_hourly_claim_is_current_only_with_supersession_notice() -> None:
    failures = []
    for relative in _tracked_markdown():
        if relative in REGISTERS:
            continue
        text = (REPO / relative).read_text(encoding="utf-8", errors="replace")
        if OUTDATED_HOURLY.search(text) and not carries_supersession_notice(text):
            failures.append(relative)
    assert not failures, "published hourly claim contradicts v2 artifact: " + ", ".join(
        failures
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
        "406 first receipts across all five clean sessions",
        "6/406 (1.48%)",
        "0/406",
        "does not hold as a strict conservative bound at the NY opening",
    )
    folded = normalize(text)
    assert not [token for token in required if normalize(token) not in folded]


def test_final_report_carries_the_hourly_cutoff_finding() -> None:
    values = _load(AGGREGATE)["operational_latency"]["by_ny_hour"]["values"]
    opening = values["9"]
    hour_14 = values["14"]
    report = REPORT.read_text(encoding="utf-8")
    abstract = report.partition("## Abstract")[2].partition("## 1. Introduction")[0]
    timing_results = report.partition(
        "### 5.6 Operational timing result: the 60-second opening bound"
    )[2].partition("## 6. Discussion")[0]
    required = (
        f"{opening['over_60_seconds']['count']}/{opening['count']} "
        f"({opening['over_60_seconds']['rate'] * 100:.2f} per cent)",
        f"p99 was {opening['quantiles_seconds']['p99']:.6f} seconds",
        f"{opening['over_120_seconds']['count']}/{opening['count']} exceeded 120 seconds",
        "does not hold as a strict conservative bound at the NY opening in this sample",
        f"two of {hour_14['count']} receipts in hour 14 exceeded 120 seconds",
        "cannot certify future sessions",
    )
    folded = normalize(report)
    abstract_folded = normalize(abstract)
    timing_results_folded = normalize(timing_results)
    assert not [token for token in required if normalize(token) not in folded]
    assert "6/406" in abstract_folded
    assert "not a strict conservative opening bound" in abstract_folded
    assert "6/406" in timing_results_folded
    assert "PROXY_ONLY_CROSS_CHANNEL" in timing_results


def test_hourly_distribution_answers_the_registered_opening_cutoff() -> None:
    aggregate = _load(AGGREGATE)
    latency = aggregate["operational_latency"]
    assert aggregate["schema_version"] == "uw-latency-campaign-v2.0"
    assert latency["by_ny_hour"]["status"] == (
        "MEASURED_FROM_LICENSED_OBSERVATION_AGGREGATES"
    )
    assert latency["by_ny_hour"]["included_first_receipts"] == 1768
    opening = latency["by_ny_hour"]["values"]["9"]
    assert opening["count"] == 406
    assert opening["session_count"] == 5
    assert opening["over_60_seconds"] == {"count": 6, "rate": 6 / 406}
    assert opening["over_120_seconds"] == {"count": 0, "rate": 0.0}
    assert opening["quantiles_seconds"]["p99"] == 60.2168978
    assert latency["by_ny_hour"]["values"]["14"]["over_120_seconds"]["count"] == 2
    assert set(latency["by_ny_hour_asset"]["values"]["9"]) == {
        "AAPL",
        "META",
        "NVDA",
        "TSLA",
    }
    assert latency["by_ny_hour_asset"]["insufficient"]["9"] == {
        "AMZN": {"count": 25, "reason": "COUNT_BELOW_30", "session_count": 5},
        "MSFT": {"count": 24, "reason": "COUNT_BELOW_30", "session_count": 4},
    }


def test_gate5_hourly_table_is_rendered_exactly_from_the_artifact() -> None:
    values = _load(AGGREGATE)["operational_latency"]["by_ny_hour"]["values"]
    rows = re.findall(
        r"^\| (\d{1,2}) \| (\d+) \| (\d+) \| ([0-9.]+) \| ([0-9.]+) \| "
        r"([0-9.]+) \| ([0-9.]+) \| (\d+) \| (\d+) \|$",
        GATE5.read_text(encoding="utf-8"),
        re.M,
    )
    expected = []
    six_places = Decimal("0.000001")
    for hour, payload in sorted(values.items(), key=lambda item: int(item[0])):
        quantiles = payload["quantiles_seconds"]
        expected.append(
            (
                hour,
                str(payload["count"]),
                str(payload["session_count"]),
                str(Decimal(str(quantiles["p10"])).quantize(six_places)),
                str(Decimal(str(quantiles["p50"])).quantize(six_places)),
                str(Decimal(str(quantiles["p90"])).quantize(six_places)),
                str(Decimal(str(quantiles["p99"])).quantize(six_places)),
                str(payload["over_60_seconds"]["count"]),
                str(payload["over_120_seconds"]["count"]),
            )
        )
    assert rows == expected


def test_snapshot_policy_never_mutates_a_frozen_campaign_artifact() -> None:
    state = _load(STATE)
    assert state["artifact_lifecycle"] == {
        "policy": "IMMUTABLE_DATED_SNAPSHOT",
        "freshness_check": "REGENERATE_AND_COMPARE_WITH_LIVE_SESSION_INVENTORY",
        "on_drift": "PUBLISH_NEW_DATED_SNAPSHOT_NEVER_OVERWRITE",
    }


def test_campaign_uses_only_the_existing_alert_channel() -> None:
    aggregate = _load(AGGREGATE)
    assert aggregate["alerting"] == {
        "operational_path": "logs/UW_LATENCY_ALERT.txt",
        "desktop_popup": True,
        "new_channel_created": False,
    }
