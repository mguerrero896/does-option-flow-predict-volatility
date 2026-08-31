"""Target-blind harvest and lifecycle contracts for the UW latency campaign."""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import pytest

from mds650.uw_latency_campaign import (
    BACKFILL_REASON,
    REVISION_REASON,
    build_anomaly_evidence,
    build_campaign_artifact,
    build_campaign_state,
    canonical_sha256,
    latency_outlier_alerts,
    read_artifact,
    write_new_json,
)

ASSETS = ("AAPL", "AMZN", "META", "MSFT", "NVDA", "TSLA")
DATES = (
    "2026-08-17",
    "2026-08-18",
    "2026-08-19",
    "2026-08-20",
    "2026-08-21",
    "2026-08-24",
)
P50 = (29.500069, 33.0653445, 28.934705, 32.207282, 4294.886974, 28.97307)
LIVE = (461, 168, 339, 255, 636, 559)


def _write_reconciliation(root: Path, index: int) -> Path:
    session_dir = root / "uw_latency" / "sessions" / DATES[index]
    session_dir.mkdir(parents=True, exist_ok=True)
    live = LIVE[index]
    payload = {
        "session": DATES[index],
        "reconciled_utc": f"{DATES[index]}T21:00:00+00:00",
        "status": "PROXY_ONLY_CROSS_CHANNEL",
        "tape_rows_outcome_assets": 100_000 + index,
        "live_observations_total": live,
        "live_flow_alerts_in_session": live,
        "live_observations_out_of_session": 0,
        "flow_alerts_with_tape_support": live,
        "unmatched_flow_alerts": 0,
        "flow_alert_tape_support_rate": 1.0,
        "backfill_upper_bound_rate": None,
        "backfill_rate_reason": BACKFILL_REASON,
        "revision_rate_among_matched": None,
        "revision_rate_reason": REVISION_REASON,
        "latency_seconds_quantiles": {
            "0.1": 5.0,
            "0.5": P50[index],
            "0.9": P50[index] + 20.0,
            "0.99": P50[index] + 30.0,
        },
        "latency_by_asset_median": {
            asset: P50[index] + offset for offset, asset in enumerate(ASSETS)
        },
    }
    path = session_dir / "reconciliation.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _anomaly_payload() -> dict[str, Any]:
    payload: dict[str, Any] = {
        "schema_version": "uw-latency-anomaly-v1.0",
        "session": "2026-08-21",
        "classification": "COLLECTOR_RESTART_REPLAY_DUPLICATION",
        "contaminates_latency_distribution": True,
        "campaign_disposition": "EXCLUDE_LATENCY_KEEP_CONTRACT_SUPPORT",
        "first_receipt_p50_seconds": 34.172432,
        "all_receipts_p50_seconds": 4294.886974,
        "duplicate_lines": 2378,
        "target_blind": True,
    }
    payload["self_sha256"] = canonical_sha256(payload)
    return payload


def _collected_sessions(root: Path, *, reconciled: int = 6) -> list[Path]:
    dates = (
        "2026-08-17",
        "2026-08-18",
        "2026-08-19",
        "2026-08-20",
        "2026-08-21",
        "2026-08-24",
        "2026-08-25",
        "2026-08-26",
        "2026-08-27",
        "2026-08-28",
        "2026-08-31",
    )
    directories = []
    for index, session in enumerate(dates):
        directory = root / "uw_latency" / "sessions" / session
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "observations.jsonl").write_text("synthetic\n", encoding="utf-8")
        (directory / "collector_summary.json").write_text("{}", encoding="utf-8")
        (directory / "capture_report.json").write_text("{}", encoding="utf-8")
        if index < reconciled:
            (directory / "reconciliation.json").write_text("{}", encoding="utf-8")
        directories.append(directory)
    return directories


def _write_anomalous_session(
    root: Path,
    *,
    delays: tuple[int, ...] = (30, 4300, 17_000),
    complete: bool = True,
) -> Path:
    session_dir = root / "uw_latency" / "sessions" / "2026-08-21"
    session_dir.mkdir(parents=True)
    ny = ZoneInfo("America/New_York")
    open_utc = dt.datetime(2026, 8, 21, 9, 30, tzinfo=ny).astimezone(dt.UTC)
    records: list[str] = []
    for sequence in range(4):
        created = open_utc + dt.timedelta(minutes=sequence)
        record = {
            "sequence": sequence,
            "start_time": int(created.timestamp() * 1000),
            "created_at": created.isoformat(),
        }
        for delay in delays:
            records.append(
                json.dumps(
                    {
                        "kind": "observation",
                        "receipt_utc": (created + dt.timedelta(seconds=delay)).isoformat(),
                        "record": record,
                    }
                )
            )
    (session_dir / "observations.jsonl").write_text("\n".join(records) + "\n", encoding="utf-8")
    (session_dir / "heartbeat.json").write_text(
        json.dumps({"utc": "2026-08-21T20:04:39+00:00", "observed_records": 4}),
        encoding="utf-8",
    )
    (session_dir / "collector_summary.json").write_text(
        json.dumps(
            {
                "session": "2026-08-21",
                "observed_records": 4,
                "finished_utc": "2026-08-21T20:05:39+00:00",
                "termination": "normal",
            }
        ),
        encoding="utf-8",
    )
    (session_dir / "capture_report.json").write_text(
        json.dumps(
            {
                "session": "2026-08-21",
                "total": 4 * len(delays),
                "poll_errors": 0,
                "complete": complete,
            }
        ),
        encoding="utf-8",
    )
    return session_dir


def test_campaign_harvest_excludes_only_contaminated_latency(tmp_path: Path) -> None:
    reconciliations = [_write_reconciliation(tmp_path, index) for index in range(6)]

    artifact = build_campaign_artifact(
        reconciliations,
        anomaly=_anomaly_payload(),
        as_of_date="2026-09-01",
    )

    support = artifact["contract_window_support"]
    latency = artifact["operational_latency"]
    assert support == {
        "sessions_reconciled": 6,
        "flow_alerts": 2418,
        "supported": 2418,
        "unmatched": 0,
        "support_rate": 1.0,
    }
    assert latency["included_sessions"] == 5
    assert latency["excluded_sessions"] == [
        {
            "session": "2026-08-21",
            "reason": "COLLECTOR_RESTART_REPLAY_DUPLICATION",
        }
    ]
    assert latency["p50_cross_session_median_seconds"] == pytest.approx(29.500069)
    assert latency["by_ny_hour"]["status"] == "NOT_AVAILABLE_IN_RECONCILIATION_JSON"
    assert artifact["backfill"]["value"] is None
    assert artifact["backfill"]["reason"] == BACKFILL_REASON
    assert artifact["revision"]["value"] is None
    assert artifact["revision"]["reason"] == REVISION_REASON
    assert artifact["self_sha256"] == canonical_sha256(artifact)
    assert "2026-08-21" in latency["per_session"]
    assert not any(
        token in json.dumps(artifact).lower() for token in ("record" + "_id", ".zip")
    )


def test_campaign_rejects_cross_channel_reason_drift(tmp_path: Path) -> None:
    reconciliations = [_write_reconciliation(tmp_path, index) for index in range(6)]
    payload = json.loads(reconciliations[0].read_text(encoding="utf-8"))
    payload["backfill_rate_reason"] = "MEASURABLE"
    reconciliations[0].write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="UW_LATENCY_BACKFILL_CONTRACT_INVALID"):
        build_campaign_artifact(
            reconciliations,
            anomaly=_anomaly_payload(),
            as_of_date="2026-09-01",
        )


def test_campaign_harvest_fails_closed_on_input_identity_and_shape(tmp_path: Path) -> None:
    """Only explicit, unique reconciliations containing the anomaly may be harvested."""
    path = _write_reconciliation(tmp_path, 0)
    anomaly = _anomaly_payload()

    with pytest.raises(ValueError, match="UW_LATENCY_RECONCILIATIONS_EMPTY"):
        build_campaign_artifact([], anomaly=anomaly, as_of_date="2026-09-01")

    wrong_name = path.with_name("not-a-reconciliation.json")
    wrong_name.write_bytes(path.read_bytes())
    with pytest.raises(ValueError, match="UW_LATENCY_RECONCILIATION_FILENAME_INVALID"):
        build_campaign_artifact([wrong_name], anomaly=anomaly, as_of_date="2026-09-01")

    with pytest.raises(ValueError, match="UW_LATENCY_RECONCILIATION_SESSION_DUPLICATE"):
        build_campaign_artifact([path, path], anomaly=anomaly, as_of_date="2026-09-01")

    with pytest.raises(ValueError, match="UW_LATENCY_ANOMALY_SESSION_NOT_RECONCILED"):
        build_campaign_artifact([path], anomaly=anomaly, as_of_date="2026-09-01")


@pytest.mark.parametrize(
    ("mutation", "error"),
    (
        ({"status": "MEASURED"}, "UW_LATENCY_RECONCILIATION_STATUS_INVALID"),
        ({"unmatched_flow_alerts": 1}, "UW_LATENCY_SUPPORT_ARITHMETIC_INVALID"),
        ({"revision_rate_reason": "MEASURABLE"}, "UW_LATENCY_REVISION_CONTRACT_INVALID"),
        ({"live_flow_alerts_in_session": -1}, "UW_LATENCY_COUNT_INVALID"),
    ),
)
def test_campaign_rejects_reconciliation_contract_drift(
    tmp_path: Path, mutation: dict[str, object], error: str
) -> None:
    """Status, arithmetic, counts and non-identifiability reasons are binding."""
    paths = [_write_reconciliation(tmp_path, index) for index in range(6)]
    payload = json.loads(paths[0].read_text(encoding="utf-8"))
    payload.update(mutation)
    paths[0].write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match=error):
        build_campaign_artifact(paths, anomaly=_anomaly_payload(), as_of_date="2026-09-01")


@pytest.mark.parametrize(
    ("key", "error"),
    (
        ("latency_seconds_quantiles", "UW_LATENCY_QUANTILES_INVALID"),
        ("latency_by_asset_median", "UW_LATENCY_ASSET_MEDIANS_INVALID"),
    ),
)
def test_campaign_rejects_incomplete_latency_summaries(
    tmp_path: Path, key: str, error: str
) -> None:
    """A partial quantile or asset summary cannot become a campaign result."""
    paths = [_write_reconciliation(tmp_path, index) for index in range(6)]
    payload = json.loads(paths[0].read_text(encoding="utf-8"))
    summary = payload[key]
    assert isinstance(summary, dict)
    summary.pop(next(iter(summary)))
    paths[0].write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match=error):
        build_campaign_artifact(paths, anomaly=_anomaly_payload(), as_of_date="2026-09-01")


def test_campaign_rejects_anomaly_identity_or_disposition_drift(tmp_path: Path) -> None:
    """An unverified or unresolved anomaly cannot silently drive an exclusion."""
    paths = [_write_reconciliation(tmp_path, index) for index in range(6)]
    bad_hash = _anomaly_payload()
    bad_hash["self_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="UW_LATENCY_ANOMALY_HASH_INVALID"):
        build_campaign_artifact(paths, anomaly=bad_hash, as_of_date="2026-09-01")

    bad_disposition = _anomaly_payload()
    bad_disposition["campaign_disposition"] = "KEEP"
    bad_disposition["self_sha256"] = canonical_sha256(bad_disposition)
    with pytest.raises(ValueError, match="UW_LATENCY_ANOMALY_DISPOSITION_INVALID"):
        build_campaign_artifact(paths, anomaly=bad_disposition, as_of_date="2026-09-01")


@pytest.mark.parametrize(
    ("shape", "expected"),
    (
        ("collecting", "COLLECTING"),
        ("collected", "COLLECTED_UNRECONCILED"),
        ("reconciled", "RECONCILED_PARTIAL"),
        ("abandoned", "ABANDONED"),
    ),
)
def test_lifecycle_is_derived_from_session_files(
    tmp_path: Path, shape: str, expected: str
) -> None:
    session = tmp_path / "uw_latency" / "sessions" / "2026-08-17"
    session.mkdir(parents=True)
    (session / "observations.jsonl").write_text("synthetic\n", encoding="utf-8")
    if shape != "collecting":
        (session / "collector_summary.json").write_text("{}", encoding="utf-8")
        (session / "capture_report.json").write_text("{}", encoding="utf-8")
    if shape == "reconciled":
        (session / "reconciliation.json").write_text("{}", encoding="utf-8")
    if shape == "abandoned":
        (session.parents[1] / "campaign_abandoned.json").write_text("{}", encoding="utf-8")
    aggregate = {"self_sha256": "a" * 64}

    state = build_campaign_state(
        [session],
        aggregate_path="artifacts/gate5_pit/uw_latency_campaign_20260901_v1.json",
        aggregate=aggregate,
        as_of_date="2026-09-01",
    )

    assert state["state"] == expected
    assert state["self_sha256"] == canonical_sha256(state)


def test_current_inventory_is_reconciled_partial(tmp_path: Path) -> None:
    sessions = _collected_sessions(tmp_path)
    aggregate = {"self_sha256": "a" * 64}

    state = build_campaign_state(
        sessions,
        aggregate_path="artifacts/gate5_pit/uw_latency_campaign_20260901_v1.json",
        aggregate=aggregate,
        as_of_date="2026-09-01",
    )

    assert state["state"] == "RECONCILED_PARTIAL"
    assert state["counts"] == {"collected": 11, "reconciled": 6, "unreconciled": 5}
    serialized = json.dumps(state)
    assert str(tmp_path) not in serialized
    assert "observations.jsonl" not in serialized


def test_lifecycle_rejects_empty_duplicate_or_unhashed_inventory(tmp_path: Path) -> None:
    """Lifecycle state needs an explicit unique inventory and bound aggregate."""
    aggregate = {"self_sha256": "a" * 64}
    with pytest.raises(ValueError, match="UW_LATENCY_SESSION_INVENTORY_EMPTY"):
        build_campaign_state(
            [],
            aggregate_path="artifacts/gate5_pit/uw_latency_campaign_20260901_v1.json",
            aggregate=aggregate,
            as_of_date="2026-09-01",
        )

    session = _collected_sessions(tmp_path, reconciled=0)[0]
    with pytest.raises(ValueError, match="UW_LATENCY_AGGREGATE_HASH_INVALID"):
        build_campaign_state(
            [session],
            aggregate_path="artifacts/gate5_pit/uw_latency_campaign_20260901_v1.json",
            aggregate={},
            as_of_date="2026-09-01",
        )
    with pytest.raises(ValueError, match="UW_LATENCY_SESSION_INVENTORY_INVALID"):
        build_campaign_state(
            [session, session],
            aggregate_path="artifacts/gate5_pit/uw_latency_campaign_20260901_v1.json",
            aggregate=aggregate,
            as_of_date="2026-09-01",
        )


def test_anomaly_audit_identifies_restart_replay_without_row_output(tmp_path: Path) -> None:
    evidence = build_anomaly_evidence(_write_anomalous_session(tmp_path))

    assert evidence["classification"] == "COLLECTOR_RESTART_REPLAY_DUPLICATION"
    assert evidence["line_counts"]["duplicate_lines"] == 8
    assert evidence["latency_seconds"]["all_receipts"]["p50"] == pytest.approx(4300.0)
    assert evidence["latency_seconds"]["first_receipt_per_record"]["p50"] == 30.0
    assert evidence["contaminates_latency_distribution"] is True
    assert evidence["campaign_disposition"] == "EXCLUDE_LATENCY_KEEP_CONTRACT_SUPPORT"
    assert evidence["self_sha256"] == canonical_sha256(evidence)
    serialized = json.dumps(evidence).lower()
    assert not any(
        token in serialized for token in ("record" + "_id", "pri" + "ce", "prem" + "ium")
    )


@pytest.mark.parametrize(
    ("delays", "complete", "classification"),
    (
        ((30, 4300, 17_000), False, "COLLECTOR_STOP_OR_INCOMPLETE_SESSION"),
        ((4000,), True, "POSSIBLE_PROVIDER_DEGRADATION"),
        ((30,), True, "OTHER_UNRESOLVED"),
    ),
)
def test_anomaly_audit_keeps_unresolved_shapes_excluded(
    tmp_path: Path,
    delays: tuple[int, ...],
    complete: bool,
    classification: str,
) -> None:
    """Only restart replay gets the narrow keep-support disposition."""
    evidence = build_anomaly_evidence(
        _write_anomalous_session(tmp_path, delays=delays, complete=complete)
    )

    assert evidence["classification"] == classification
    assert evidence["campaign_disposition"] == "EXCLUDE_UNRESOLVED"
    assert evidence["contaminates_latency_distribution"] is False


def test_anomaly_audit_rejects_missing_or_unusable_observation_logs(tmp_path: Path) -> None:
    """Missing or latency-free structural evidence cannot support a classification."""
    session = _write_anomalous_session(tmp_path)
    log = session / "observations.jsonl"
    log.unlink()
    with pytest.raises(ValueError, match="UW_LATENCY_OBSERVATION_LOG_MISSING"):
        build_anomaly_evidence(session)

    log.write_text("not-json\n{}\n{\"kind\": \"observation\"}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="UW_LATENCY_QUANTILE_INPUT_EMPTY"):
        build_anomaly_evidence(session)


def test_outlier_guard_routes_the_known_order_of_deviation(tmp_path: Path) -> None:
    artifact = build_campaign_artifact(
        [_write_reconciliation(tmp_path, index) for index in range(6)],
        anomaly=_anomaly_payload(),
        as_of_date="2026-09-01",
    )

    assert latency_outlier_alerts(artifact) == [
        "UW_LATENCY_P50_OUTLIER session=2026-08-21 ratio=145.589 threshold=10.000"
    ]


def test_outlier_guard_rejects_malformed_input_and_needs_a_peer() -> None:
    """Alerting fails closed on malformed aggregates and does not flag one sample."""
    with pytest.raises(ValueError, match="UW_LATENCY_ALERT_INPUT_INVALID"):
        latency_outlier_alerts({})

    assert (
        latency_outlier_alerts(
            {
                "operational_latency": {
                    "per_session": {
                        "2026-08-21": {"quantiles_seconds": {"0.5": 4300.0}}
                    }
                }
            }
        )
        == []
    )


def test_artifact_write_is_idempotent_but_never_overwrites(tmp_path: Path) -> None:
    path = tmp_path / "artifact.json"
    payload = {"schema_version": "test", "self_sha256": "a" * 64}
    write_new_json(path, payload)
    write_new_json(path, payload)

    with pytest.raises(FileExistsError, match="UW_LATENCY_ARTIFACT_CONFLICT"):
        write_new_json(path, {**payload, "status": "different"})


def test_artifact_reader_rejects_missing_non_mapping_and_nonfinite_json(tmp_path: Path) -> None:
    """CLI composition never accepts absent, array-shaped or nonfinite evidence."""
    valid = tmp_path / "valid.json"
    valid.write_text('{"status":"ok"}', encoding="utf-8")
    assert read_artifact(valid, "BAD_ARTIFACT") == {"status": "ok"}

    for name, content in (("array.json", "[]"), ("nonfinite.json", '{"value":NaN}')):
        path = tmp_path / name
        path.write_text(content, encoding="utf-8")
        with pytest.raises(ValueError, match="BAD_ARTIFACT"):
            read_artifact(path, "BAD_ARTIFACT")

    with pytest.raises(ValueError, match="BAD_ARTIFACT"):
        read_artifact(tmp_path / "missing.json", "BAD_ARTIFACT")
