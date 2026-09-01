"""Target-blind harvest and lifecycle evidence for the UW latency campaign."""

from __future__ import annotations

import collections
import datetime as dt
import hashlib
import json
import math
import statistics
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np

from mds650.storage import assert_outside_frozen

ASSETS = ("AAPL", "AMZN", "META", "MSFT", "NVDA", "TSLA")
BACKFILL_REASON = "CROSS_CHANNEL_NOT_IDENTIFIABLE"
REVISION_REASON = "AGGREGATE_ALERT_VS_INDIVIDUAL_TRADE_NOT_COMPARABLE"
ANOMALY_CLASSIFICATION = "COLLECTOR_RESTART_REPLAY_DUPLICATION"
ANOMALY_DISPOSITION = "EXCLUDE_LATENCY_KEEP_CONTRACT_SUPPORT"
LIFECYCLE_STATES = (
    "COLLECTING",
    "COLLECTED_UNRECONCILED",
    "RECONCILED_PARTIAL",
    "ABANDONED",
)
NY = ZoneInfo("America/New_York")


def canonical_sha256(payload: Mapping[str, Any]) -> str:
    """Hash a JSON mapping, excluding its own ``self_sha256`` field."""

    body = {key: value for key, value in payload.items() if key != "self_sha256"}
    encoded = json.dumps(
        body,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_campaign_artifact(
    reconciliation_paths: Sequence[Path],
    *,
    anomaly: Mapping[str, Any],
    as_of_date: str,
    hourly_latency: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Consolidate explicit reconciliations and optional safe hourly aggregates."""

    _iso_date(as_of_date, "UW_LATENCY_AS_OF_DATE_INVALID")
    _validate_anomaly(anomaly)
    if not reconciliation_paths:
        raise ValueError("UW_LATENCY_RECONCILIATIONS_EMPTY")
    sessions: list[dict[str, Any]] = []
    seen: set[str] = set()
    for path in reconciliation_paths:
        if path.name != "reconciliation.json":
            raise ValueError("UW_LATENCY_RECONCILIATION_FILENAME_INVALID")
        payload = _load_mapping(path, "UW_LATENCY_RECONCILIATION_JSON_INVALID")
        session = _validated_reconciliation(payload, path)
        if session["session"] in seen:
            raise ValueError("UW_LATENCY_RECONCILIATION_SESSION_DUPLICATE")
        seen.add(str(session["session"]))
        sessions.append(session)
    sessions.sort(key=lambda item: str(item["session"]))

    anomaly_session = str(anomaly["session"])
    if anomaly_session not in seen:
        raise ValueError("UW_LATENCY_ANOMALY_SESSION_NOT_RECONCILED")
    for session in sessions:
        excluded = session["session"] == anomaly_session
        session["latency_included"] = not excluded
        session["latency_exclusion_reason"] = ANOMALY_CLASSIFICATION if excluded else None

    included = [session for session in sessions if session["latency_included"]]
    p50_values = [float(session["latency_seconds_quantiles"]["0.5"]) for session in included]
    asset_medians = {
        asset: float(
            statistics.median(
                float(session["latency_by_asset_median"][asset]) for session in included
            )
        )
        for asset in ASSETS
    }
    flow_alerts = sum(int(session["live_flow_alerts_in_session"]) for session in sessions)
    supported = sum(int(session["flow_alerts_with_tape_support"]) for session in sessions)
    unmatched = sum(int(session["unmatched_flow_alerts"]) for session in sessions)
    artifact: dict[str, Any] = {
        "schema_version": "uw-latency-campaign-v1.0",
        "as_of_date": as_of_date,
        "scope": "TARGET_BLIND_OPERATIONAL_PROVIDER_TIMING",
        "target_blind": True,
        "model_fit_performed": False,
        "sealed_cohort_read": False,
        "claim_classification": "PROXY_ONLY_CROSS_CHANNEL",
        "contract_window_support": {
            "sessions_reconciled": len(sessions),
            "flow_alerts": flow_alerts,
            "supported": supported,
            "unmatched": unmatched,
            "support_rate": supported / flow_alerts,
        },
        "operational_latency": {
            "estimand": "LOCAL_RECEIPT_UTC_MINUS_PROVIDER_CREATED_AT",
            "included_sessions": len(included),
            "excluded_sessions": [
                {"session": anomaly_session, "reason": ANOMALY_CLASSIFICATION}
            ],
            "p50_cross_session_median_seconds": float(statistics.median(p50_values)),
            "by_asset": {
                "method": "MEDIAN_OF_INCLUDED_SESSION_MEDIANS",
                "values_seconds": asset_medians,
            },
            "by_ny_hour": {
                "status": "NOT_AVAILABLE_IN_RECONCILIATION_JSON",
                "values_seconds": None,
                "reason": (
                    "SESSION_RECONCILIATIONS_DID_NOT_PERSIST_NY_HOUR_AGGREGATES; "
                    "CAMPAIGN_HARVEST_MAY_NOT_READ_LICENSED_ROW_DATA"
                ),
            },
            "per_session": {
                str(session["session"]): {
                    "quantiles_seconds": session["latency_seconds_quantiles"],
                    "by_asset_median_seconds": session["latency_by_asset_median"],
                    "included": session["latency_included"],
                    "exclusion_reason": session["latency_exclusion_reason"],
                }
                for session in sessions
            },
        },
        "backfill": {"value": None, "reason": BACKFILL_REASON},
        "revision": {"value": None, "reason": REVISION_REASON},
        "source_reconciliations": [
            {
                "session": session["session"],
                "sha256": session["source_sha256"],
            }
            for session in sessions
        ],
        "anomaly": {
            "session": anomaly_session,
            "classification": anomaly["classification"],
            "disposition": anomaly["campaign_disposition"],
            "evidence_self_sha256": anomaly["self_sha256"],
        },
        "alerting": {
            "operational_path": "logs/UW_LATENCY_ALERT.txt",
            "desktop_popup": True,
            "new_channel_created": False,
        },
    }
    if hourly_latency is not None:
        expected_sessions = [str(session["session"]) for session in included]
        if hourly_latency.get("included_sessions") != expected_sessions:
            raise ValueError("UW_LATENCY_HOURLY_SESSION_SET_INVALID")
        artifact["schema_version"] = "uw-latency-campaign-v2.0"
        latency = artifact["operational_latency"]
        latency["by_ny_hour"] = {
            "status": "MEASURED_FROM_LICENSED_OBSERVATION_AGGREGATES",
            "hour_basis": hourly_latency["hour_basis"],
            "receipt_selection": hourly_latency["receipt_selection"],
            "included_first_receipts": hourly_latency["included_first_receipts"],
            "values": hourly_latency["by_ny_hour"],
        }
        latency["by_ny_hour_asset"] = {
            "status": "MEASURED_WHERE_SAMPLE_SUPPORTS",
            "support_rule": hourly_latency["cross_tab_support_rule"],
            "values": hourly_latency["by_ny_hour_asset"],
            "insufficient": hourly_latency["insufficient_by_ny_hour_asset"],
        }
        latency["source_observation_sha256"] = hourly_latency[
            "source_observation_sha256"
        ]
    artifact["self_sha256"] = canonical_sha256(artifact)
    return artifact


def build_hourly_latency_distribution(session_dirs: Sequence[Path]) -> dict[str, Any]:
    """Aggregate first-receipt latency by receipt hour without emitting licensed rows."""

    if not session_dirs:
        raise ValueError("UW_LATENCY_HOURLY_SESSIONS_EMPTY")
    hourly: dict[int, list[tuple[float, str]]] = collections.defaultdict(list)
    hourly_asset: dict[tuple[int, str], list[tuple[float, str]]] = collections.defaultdict(
        list
    )
    included_sessions: list[str] = []
    source_hashes: list[dict[str, str]] = []
    seen_sessions: set[str] = set()
    duplicate_valid_receipts = 0
    for session_dir in sorted(session_dirs, key=lambda path: path.name):
        session = session_dir.name
        session_date = _iso_date(session, "UW_LATENCY_HOURLY_SESSION_INVALID")
        if session in seen_sessions or not session_dir.is_dir():
            raise ValueError("UW_LATENCY_HOURLY_SESSION_INVALID")
        seen_sessions.add(session)
        observations_path = session_dir / "observations.jsonl"
        if not observations_path.is_file():
            raise ValueError("UW_LATENCY_OBSERVATION_LOG_MISSING")
        calendar_start = dt.datetime.combine(
            session_date, dt.time.min, tzinfo=NY
        ).astimezone(dt.UTC)
        calendar_end = dt.datetime.combine(
            session_date + dt.timedelta(days=1), dt.time.min, tzinfo=NY
        ).astimezone(dt.UTC)
        first_receipts: dict[str, tuple[dt.datetime, dt.datetime, str]] = {}
        with observations_path.open(encoding="utf-8") as handle:
            for raw in handle:
                try:
                    row = _loads_strict(raw)
                except (json.JSONDecodeError, ValueError):
                    continue
                if not isinstance(row, Mapping) or row.get("kind") != "observation":
                    continue
                record = row.get("record")
                if not isinstance(record, Mapping):
                    continue
                start = _epoch_datetime(record.get("start_time"))
                receipt = _timestamp(row.get("receipt_utc"))
                created = _timestamp(record.get("created_at"))
                if (
                    start is None
                    or not calendar_start <= start < calendar_end
                    or receipt is None
                    or created is None
                ):
                    continue
                latency = (receipt - created).total_seconds()
                if not math.isfinite(latency) or latency < 0:
                    continue
                identity = _private_record_identity(row, record)
                asset = str(record.get("ticker") or row.get("asset") or "").upper()
                previous = first_receipts.get(identity)
                if previous is not None:
                    duplicate_valid_receipts += 1
                if previous is None or receipt < previous[0]:
                    first_receipts[identity] = (receipt, created, asset)
        if not first_receipts:
            raise ValueError("UW_LATENCY_HOURLY_SESSION_EMPTY")
        included_sessions.append(session)
        source_hashes.append(
            {"session": session, "sha256": _file_sha256(observations_path)}
        )
        for receipt, created, asset in first_receipts.values():
            value = (receipt - created).total_seconds()
            hour = receipt.astimezone(NY).hour
            hourly[hour].append((value, session))
            if asset in ASSETS:
                hourly_asset[(hour, asset)].append((value, session))

    by_hour = {
        str(hour): _distribution_summary(values)
        for hour, values in sorted(hourly.items())
    }
    by_hour_asset: dict[str, dict[str, Any]] = {}
    insufficient: dict[str, dict[str, Any]] = {}
    for (hour, asset), values in sorted(hourly_asset.items()):
        count = len(values)
        session_count = len({session for _, session in values})
        if count >= 30 and session_count >= 3:
            by_hour_asset.setdefault(str(hour), {})[asset] = _distribution_summary(values)
            continue
        reason = "COUNT_BELOW_30" if count < 30 else "SESSION_COUNT_BELOW_3"
        insufficient.setdefault(str(hour), {})[asset] = {
            "count": count,
            "session_count": session_count,
            "reason": reason,
        }
    return {
        "hour_basis": "RECEIPT_UTC_CONVERTED_TO_AMERICA_NEW_YORK",
        "receipt_selection": "FIRST_VALID_RECEIPT_PER_RECORD",
        "included_sessions": included_sessions,
        "included_first_receipts": sum(len(values) for values in hourly.values()),
        "duplicate_valid_receipts": duplicate_valid_receipts,
        "cross_tab_support_rule": {"minimum_count": 30, "minimum_sessions": 3},
        "by_ny_hour": by_hour,
        "by_ny_hour_asset": by_hour_asset,
        "insufficient_by_ny_hour_asset": insufficient,
        "source_observation_sha256": source_hashes,
    }


def build_campaign_state(
    session_dirs: Sequence[Path],
    *,
    aggregate_path: str,
    aggregate: Mapping[str, Any],
    as_of_date: str,
    immutable_snapshot: bool = False,
) -> dict[str, Any]:
    """Derive the four-state campaign lifecycle from named session files."""

    _iso_date(as_of_date, "UW_LATENCY_AS_OF_DATE_INVALID")
    if not session_dirs:
        raise ValueError("UW_LATENCY_SESSION_INVENTORY_EMPTY")
    if not isinstance(aggregate.get("self_sha256"), str):
        raise ValueError("UW_LATENCY_AGGREGATE_HASH_INVALID")
    inventory: list[dict[str, Any]] = []
    seen: set[str] = set()
    for directory in session_dirs:
        session = directory.name
        _iso_date(session, "UW_LATENCY_SESSION_NAME_INVALID")
        if session in seen or not directory.is_dir():
            raise ValueError("UW_LATENCY_SESSION_INVENTORY_INVALID")
        seen.add(session)
        inventory.append(
            {
                "session": session,
                "collection_payload_present": (directory / "observations.jsonl").is_file(),
                "collector_summary_present": (directory / "collector_summary.json").is_file(),
                "capture_report_present": (directory / "capture_report.json").is_file(),
                "heartbeat_present": (directory / "heartbeat.json").is_file(),
                "reconciliation_present": (directory / "reconciliation.json").is_file(),
            }
        )
    inventory.sort(key=lambda item: str(item["session"]))
    collected = sum(bool(item["collection_payload_present"]) for item in inventory)
    reconciled = sum(bool(item["reconciliation_present"]) for item in inventory)
    collecting = any(
        item["collection_payload_present"]
        and not item["collector_summary_present"]
        and not item["capture_report_present"]
        for item in inventory
    )
    marker = session_dirs[0].parents[1] / "campaign_abandoned.json"
    if marker.is_file():
        lifecycle = "ABANDONED"
    elif reconciled:
        lifecycle = "RECONCILED_PARTIAL"
    elif collecting or not collected:
        lifecycle = "COLLECTING"
    else:
        lifecycle = "COLLECTED_UNRECONCILED"
    if lifecycle not in LIFECYCLE_STATES:
        raise AssertionError("UW_LATENCY_LIFECYCLE_UNREACHABLE")
    state: dict[str, Any] = {
        "schema_version": "uw-latency-campaign-state-v1.0",
        "as_of_date": as_of_date,
        "state": lifecycle,
        "state_space": list(LIFECYCLE_STATES),
        "derived_from_session_files": True,
        "abandonment_marker_present": marker.is_file(),
        "counts": {
            "collected": collected,
            "reconciled": reconciled,
            "unreconciled": collected - reconciled,
        },
        "session_inventory": inventory,
        "claim_classification": "PROXY_ONLY_CROSS_CHANNEL",
        "backfill": {"value": None, "reason": BACKFILL_REASON},
        "revision": {"value": None, "reason": REVISION_REASON},
        "aggregate": {
            "path": aggregate_path,
            "self_sha256": aggregate["self_sha256"],
        },
        "target_blind": True,
        "safe_to_reconcile_existing_results": "NO",
        "safe_to_open_or_evaluate_oos": "NO",
    }
    if immutable_snapshot:
        state["schema_version"] = "uw-latency-campaign-state-v2.0"
        state["artifact_lifecycle"] = {
            "policy": "IMMUTABLE_DATED_SNAPSHOT",
            "freshness_check": "REGENERATE_AND_COMPARE_WITH_LIVE_SESSION_INVENTORY",
            "on_drift": "PUBLISH_NEW_DATED_SNAPSHOT_NEVER_OVERWRITE",
        }
    state["self_sha256"] = canonical_sha256(state)
    return state


def build_anomaly_evidence(session_dir: Path) -> dict[str, Any]:
    """Classify one session from safe metadata and row structure, never row output."""

    session = session_dir.name
    session_date = _iso_date(session, "UW_LATENCY_ANOMALY_SESSION_INVALID")
    capture = _load_mapping(
        session_dir / "capture_report.json", "UW_LATENCY_CAPTURE_REPORT_INVALID"
    )
    summary = _load_mapping(
        session_dir / "collector_summary.json", "UW_LATENCY_COLLECTOR_SUMMARY_INVALID"
    )
    heartbeat = _load_mapping(
        session_dir / "heartbeat.json", "UW_LATENCY_HEARTBEAT_INVALID"
    )
    observations_path = session_dir / "observations.jsonl"
    if not observations_path.is_file():
        raise ValueError("UW_LATENCY_OBSERVATION_LOG_MISSING")

    calendar_start = dt.datetime.combine(session_date, dt.time.min, tzinfo=NY).astimezone(dt.UTC)
    calendar_end = calendar_start + dt.timedelta(days=1)
    market_start = dt.datetime.combine(session_date, dt.time(9, 30), tzinfo=NY).astimezone(dt.UTC)
    market_end = dt.datetime.combine(session_date, dt.time(16, 5), tzinfo=NY).astimezone(dt.UTC)
    identities: collections.Counter[str] = collections.Counter()
    in_session: set[str] = set()
    out_of_session: set[str] = set()
    first_receipts: dict[str, tuple[dt.datetime, dt.datetime]] = {}
    all_latencies: list[float] = []
    start_dates: collections.Counter[str] = collections.Counter()
    receipt_hours: collections.Counter[int] = collections.Counter()
    lines = observations = invalid = in_session_lines = market_lines = 0
    receipt_min: dt.datetime | None = None
    receipt_max: dt.datetime | None = None
    with observations_path.open(encoding="utf-8") as handle:
        for raw in handle:
            lines += 1
            try:
                row = _loads_strict(raw)
            except (json.JSONDecodeError, ValueError):
                invalid += 1
                continue
            if not isinstance(row, Mapping) or row.get("kind") != "observation":
                continue
            observations += 1
            record = row.get("record")
            if not isinstance(record, Mapping):
                continue
            identity = _private_record_identity(row, record)
            identities[identity] += 1
            start = _epoch_datetime(record.get("start_time"))
            receipt = _timestamp(row.get("receipt_utc"))
            created = _timestamp(record.get("created_at"))
            if receipt is not None:
                receipt_min = receipt if receipt_min is None else min(receipt_min, receipt)
                receipt_max = receipt if receipt_max is None else max(receipt_max, receipt)
                receipt_hours[receipt.astimezone(NY).hour] += 1
            if start is None:
                continue
            start_dates[start.astimezone(NY).date().isoformat()] += 1
            if calendar_start <= start < calendar_end:
                in_session_lines += 1
                in_session.add(identity)
                if market_start <= start <= market_end:
                    market_lines += 1
                if receipt is not None and created is not None:
                    all_latencies.append((receipt - created).total_seconds())
                    previous = first_receipts.get(identity)
                    if previous is None or receipt < previous[0]:
                        first_receipts[identity] = (receipt, created)
            else:
                out_of_session.add(identity)
    first_latencies = [
        (receipt - created).total_seconds() for receipt, created in first_receipts.values()
    ]
    all_quantiles = _quantiles(all_latencies)
    first_quantiles = _quantiles(first_latencies)
    duplicate_lines = sum(identities.values()) - len(identities)
    complete = capture.get("complete") is True
    poll_errors = capture.get("poll_errors")
    replay_shape = (
        duplicate_lines > 0
        and all_quantiles["p50"] >= 300.0
        and first_quantiles["p50"] <= 60.0
        and complete
        and poll_errors == 0
    )
    if replay_shape:
        classification = ANOMALY_CLASSIFICATION
        disposition = ANOMALY_DISPOSITION
    elif not complete:
        classification = "COLLECTOR_STOP_OR_INCOMPLETE_SESSION"
        disposition = "EXCLUDE_UNRESOLVED"
    elif first_quantiles["p50"] >= 300.0:
        classification = "POSSIBLE_PROVIDER_DEGRADATION"
        disposition = "EXCLUDE_UNRESOLVED"
    else:
        classification = "OTHER_UNRESOLVED"
        disposition = "EXCLUDE_UNRESOLVED"
    evidence: dict[str, Any] = {
        "schema_version": "uw-latency-anomaly-v1.0",
        "session": session,
        "scope": "TARGET_BLIND_OPERATIONAL_STRUCTURE_ONLY",
        "classification": classification,
        "campaign_disposition": disposition,
        "contaminates_latency_distribution": classification == ANOMALY_CLASSIFICATION,
        "contract_window_support_contaminated": False,
        "line_counts": {
            "file_lines": lines,
            "observation_lines": observations,
            "invalid_json_lines": invalid,
            "distinct_records": len(identities),
            "duplicate_lines": duplicate_lines,
            "in_session_lines": in_session_lines,
            "in_session_distinct_records": len(in_session),
            "in_market_window_lines": market_lines,
            "out_of_session_distinct_records": len(out_of_session),
            "multiplicity_histogram": {
                str(key): value
                for key, value in sorted(collections.Counter(identities.values()).items())
            },
        },
        "start_date_line_counts": dict(sorted(start_dates.items())),
        "receipt_ny_hour_line_counts": {
            str(key): value for key, value in sorted(receipt_hours.items())
        },
        "receipt_range_utc": {
            "min": receipt_min.astimezone(dt.UTC).isoformat() if receipt_min else None,
            "max": receipt_max.astimezone(dt.UTC).isoformat() if receipt_max else None,
        },
        "latency_seconds": {
            "all_receipts": all_quantiles,
            "first_receipt_per_record": first_quantiles,
        },
        "operational_metadata": {
            "capture_complete": complete,
            "poll_errors": poll_errors,
            "capture_total": capture.get("total"),
            "collector_observed_records": summary.get("observed_records"),
            "collector_finished_utc": summary.get("finished_utc"),
            "collector_termination": summary.get("termination"),
            "final_heartbeat_utc": heartbeat.get("utc"),
            "heartbeat_observed_records": heartbeat.get("observed_records"),
        },
        "source_sha256": {
            "licensed_observation_log": _file_sha256(observations_path),
            "capture_report": _file_sha256(session_dir / "capture_report.json"),
            "collector_summary": _file_sha256(session_dir / "collector_summary.json"),
            "heartbeat": _file_sha256(session_dir / "heartbeat.json"),
        },
        "target_blind": True,
        "model_fit_performed": False,
        "sealed_cohort_read": False,
    }
    evidence["first_receipt_p50_seconds"] = first_quantiles["p50"]
    evidence["all_receipts_p50_seconds"] = all_quantiles["p50"]
    evidence["duplicate_lines"] = duplicate_lines
    evidence["self_sha256"] = canonical_sha256(evidence)
    return evidence


def latency_outlier_alerts(artifact: Mapping[str, Any]) -> list[str]:
    """Return stable alert messages for p50 >= 300 seconds and >= 10x peers."""

    latency = artifact.get("operational_latency")
    if not isinstance(latency, Mapping) or not isinstance(latency.get("per_session"), Mapping):
        raise ValueError("UW_LATENCY_ALERT_INPUT_INVALID")
    per_session = latency["per_session"]
    values = {
        str(session): float(payload["quantiles_seconds"]["0.5"])
        for session, payload in per_session.items()
        if isinstance(payload, Mapping)
        and isinstance(payload.get("quantiles_seconds"), Mapping)
    }
    alerts = []
    for session, value in sorted(values.items()):
        peers = [peer for other, peer in values.items() if other != session]
        if not peers:
            continue
        ratio = value / statistics.median(peers)
        if value >= 300.0 and ratio >= 10.0:
            alerts.append(
                f"UW_LATENCY_P50_OUTLIER session={session} "
                f"ratio={ratio:.3f} threshold=10.000"
            )
    return alerts


def write_new_json(path: Path, payload: Mapping[str, Any]) -> None:
    """Create one deterministic JSON artifact; identical replay is a no-op."""

    encoded = (
        json.dumps(payload, indent=1, sort_keys=True, ensure_ascii=True, allow_nan=False)
        + "\n"
    ).encode("utf-8")
    if path.exists():
        if path.read_bytes() == encoded:
            return
        raise FileExistsError("UW_LATENCY_ARTIFACT_CONFLICT")
    assert_outside_frozen(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with path.open("xb") as handle:
            handle.write(encoded)
    except FileExistsError as error:
        if path.read_bytes() == encoded:
            return
        raise FileExistsError("UW_LATENCY_ARTIFACT_CONFLICT") from error


def read_artifact(path: Path, error_code: str) -> Mapping[str, Any]:
    """Read a strict JSON mapping for CLI composition."""

    return _load_mapping(path, error_code)


def _validated_reconciliation(payload: Mapping[str, Any], path: Path) -> dict[str, Any]:
    session = payload.get("session")
    if not isinstance(session, str) or path.parent.name != session:
        raise ValueError("UW_LATENCY_RECONCILIATION_SESSION_INVALID")
    _iso_date(session, "UW_LATENCY_RECONCILIATION_SESSION_INVALID")
    if payload.get("status") != "PROXY_ONLY_CROSS_CHANNEL":
        raise ValueError("UW_LATENCY_RECONCILIATION_STATUS_INVALID")
    live = _nonnegative_int(payload, "live_flow_alerts_in_session")
    supported = _nonnegative_int(payload, "flow_alerts_with_tape_support")
    unmatched = _nonnegative_int(payload, "unmatched_flow_alerts")
    rate = _finite_number(payload.get("flow_alert_tape_support_rate"))
    if not live or supported + unmatched != live or not math.isclose(rate, supported / live):
        raise ValueError("UW_LATENCY_SUPPORT_ARITHMETIC_INVALID")
    if payload.get("backfill_upper_bound_rate") is not None or payload.get(
        "backfill_rate_reason"
    ) != BACKFILL_REASON:
        raise ValueError("UW_LATENCY_BACKFILL_CONTRACT_INVALID")
    if payload.get("revision_rate_among_matched") is not None or payload.get(
        "revision_rate_reason"
    ) != REVISION_REASON:
        raise ValueError("UW_LATENCY_REVISION_CONTRACT_INVALID")
    quantiles = payload.get("latency_seconds_quantiles")
    assets = payload.get("latency_by_asset_median")
    if not isinstance(quantiles, Mapping) or set(quantiles) != {"0.1", "0.5", "0.9", "0.99"}:
        raise ValueError("UW_LATENCY_QUANTILES_INVALID")
    if not isinstance(assets, Mapping) or set(assets) != set(ASSETS):
        raise ValueError("UW_LATENCY_ASSET_MEDIANS_INVALID")
    clean_quantiles = {key: _finite_number(value) for key, value in quantiles.items()}
    clean_assets = {asset: _finite_number(assets[asset]) for asset in ASSETS}
    return {
        "session": session,
        "source_sha256": _file_sha256(path),
        "status": payload["status"],
        "live_flow_alerts_in_session": live,
        "flow_alerts_with_tape_support": supported,
        "unmatched_flow_alerts": unmatched,
        "flow_alert_tape_support_rate": rate,
        "latency_seconds_quantiles": clean_quantiles,
        "latency_by_asset_median": clean_assets,
        "backfill_upper_bound_rate": None,
        "backfill_rate_reason": BACKFILL_REASON,
        "revision_rate_among_matched": None,
        "revision_rate_reason": REVISION_REASON,
    }


def _validate_anomaly(anomaly: Mapping[str, Any]) -> None:
    if anomaly.get("self_sha256") != canonical_sha256(anomaly):
        raise ValueError("UW_LATENCY_ANOMALY_HASH_INVALID")
    if (
        anomaly.get("classification") != ANOMALY_CLASSIFICATION
        or anomaly.get("campaign_disposition") != ANOMALY_DISPOSITION
        or anomaly.get("contaminates_latency_distribution") is not True
    ):
        raise ValueError("UW_LATENCY_ANOMALY_DISPOSITION_INVALID")


def _load_mapping(path: Path, error_code: str) -> Mapping[str, Any]:
    try:
        value = _loads_strict(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise ValueError(error_code) from error
    if not isinstance(value, Mapping):
        raise ValueError(error_code)
    return value


def _loads_strict(value: str) -> Any:
    def reject_constant(constant: str) -> None:
        raise ValueError(f"NONFINITE_JSON_CONSTANT:{constant}")

    return json.loads(value, parse_constant=reject_constant)


def _iso_date(value: str, error_code: str) -> dt.date:
    try:
        return dt.date.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise ValueError(error_code) from error


def _finite_number(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("UW_LATENCY_NUMBER_INVALID")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("UW_LATENCY_NUMBER_INVALID")
    return result


def _nonnegative_int(payload: Mapping[str, Any], key: str) -> int:
    value = payload.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("UW_LATENCY_COUNT_INVALID")
    return value


def _timestamp(value: Any) -> dt.datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=dt.UTC)


def _epoch_datetime(value: Any) -> dt.datetime | None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return None
    return dt.datetime.fromtimestamp(value / 1000, tz=dt.UTC)


def _private_record_identity(row: Mapping[str, Any], record: Mapping[str, Any]) -> str:
    value = row.get("record_id") or record.get("id")
    if value not in (None, ""):
        return hashlib.sha256(str(value).encode("utf-8")).hexdigest()
    encoded = json.dumps(
        record, sort_keys=True, separators=(",", ":"), default=str
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _quantiles(values: Sequence[float]) -> dict[str, float]:
    if not values:
        raise ValueError("UW_LATENCY_QUANTILE_INPUT_EMPTY")
    array = np.asarray(values, dtype=float)
    if not np.isfinite(array).all():
        raise ValueError("UW_LATENCY_QUANTILE_INPUT_INVALID")
    return {
        "p10": float(np.quantile(array, 0.1)),
        "p50": float(np.quantile(array, 0.5)),
        "p90": float(np.quantile(array, 0.9)),
        "p99": float(np.quantile(array, 0.99)),
    }


def _distribution_summary(values: Sequence[tuple[float, str]]) -> dict[str, Any]:
    latencies = [value for value, _ in values]
    count = len(latencies)
    over_60 = sum(value > 60.0 for value in latencies)
    over_120 = sum(value > 120.0 for value in latencies)
    return {
        "count": count,
        "session_count": len({session for _, session in values}),
        "quantiles_seconds": _quantiles(latencies),
        "over_60_seconds": {"count": over_60, "rate": over_60 / count},
        "over_120_seconds": {"count": over_120, "rate": over_120 / count},
    }


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
