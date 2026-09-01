"""Harvest target-blind UW latency reconciliations and derive lifecycle state."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from datetime import date
from pathlib import Path

from mds650.uw_latency_campaign import (
    build_campaign_artifact,
    build_campaign_state,
    build_hourly_latency_distribution,
    latency_outlier_alerts,
    read_artifact,
    write_new_json,
)


def _parse_iso_date(value: str, error_code: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise ValueError(error_code) from error


def build_snapshot(
    *,
    external_root: Path,
    anomaly_artifact: Path,
    aggregate_path: str,
    as_of_date: str,
) -> tuple[dict[str, object], dict[str, object]]:
    """Regenerate one safe snapshot from the authorized UW session directory."""

    sessions_root = external_root / "uw_latency" / "sessions"
    if not sessions_root.is_dir():
        raise ValueError("UW_LATENCY_SESSION_STORE_MISSING")
    cutoff = _parse_iso_date(as_of_date, "UW_LATENCY_AS_OF_DATE_INVALID")
    session_dirs = []
    for path in sorted(path for path in sessions_root.iterdir() if path.is_dir()):
        session_date = _parse_iso_date(path.name, "UW_LATENCY_SESSION_NAME_INVALID")
        if session_date <= cutoff:
            session_dirs.append(path)
    reconciliations = [
        path / "reconciliation.json"
        for path in session_dirs
        if (path / "reconciliation.json").is_file()
    ]
    anomaly = read_artifact(anomaly_artifact, "UW_LATENCY_ANOMALY_ARTIFACT_INVALID")
    clean_sessions = [
        path
        for path in session_dirs
        if (path / "reconciliation.json").is_file()
        and path.name != anomaly.get("session")
    ]
    hourly = build_hourly_latency_distribution(clean_sessions)
    aggregate = build_campaign_artifact(
        reconciliations,
        anomaly=anomaly,
        as_of_date=as_of_date,
        hourly_latency=hourly,
    )
    state = build_campaign_state(
        session_dirs,
        aggregate_path=aggregate_path,
        aggregate=aggregate,
        as_of_date=as_of_date,
        immutable_snapshot=True,
    )
    return aggregate, state


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--external-root", type=Path)
    parser.add_argument("--reconciliation", type=Path, action="append")
    parser.add_argument("--session-dir", type=Path, action="append")
    parser.add_argument("--anomaly-artifact", type=Path, required=True)
    parser.add_argument("--aggregate-output", type=Path, required=True)
    parser.add_argument("--state-output", type=Path, required=True)
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--emit-alert", action="store_true")
    args = parser.parse_args(argv)

    if args.external_root is not None:
        if args.reconciliation or args.session_dir:
            parser.error("--external-root cannot be combined with explicit inputs")
        aggregate, state = build_snapshot(
            external_root=args.external_root,
            anomaly_artifact=args.anomaly_artifact,
            aggregate_path=args.aggregate_output.as_posix(),
            as_of_date=args.as_of_date,
        )
    else:
        if not args.reconciliation or not args.session_dir:
            parser.error("provide --external-root or both explicit input lists")
        cutoff = _parse_iso_date(args.as_of_date, "UW_LATENCY_AS_OF_DATE_INVALID")
        explicit_sessions = [
            (path.name, "UW_LATENCY_SESSION_NAME_INVALID")
            for path in args.session_dir
        ] + [
            (path.parent.name, "UW_LATENCY_RECONCILIATION_SESSION_INVALID")
            for path in args.reconciliation
        ]
        for session, error_code in explicit_sessions:
            if _parse_iso_date(session, error_code) > cutoff:
                raise ValueError("UW_LATENCY_EXPLICIT_INPUT_AFTER_AS_OF_DATE")
        anomaly = read_artifact(
            args.anomaly_artifact, "UW_LATENCY_ANOMALY_ARTIFACT_INVALID"
        )
        aggregate = build_campaign_artifact(
            args.reconciliation,
            anomaly=anomaly,
            as_of_date=args.as_of_date,
        )
        state = build_campaign_state(
            args.session_dir,
            aggregate_path=args.aggregate_output.as_posix(),
            aggregate=aggregate,
            as_of_date=args.as_of_date,
        )
    write_new_json(args.aggregate_output, aggregate)
    write_new_json(args.state_output, state)
    if args.emit_alert:
        from uw_latency_verify import _alert

        for message in latency_outlier_alerts(aggregate):
            _alert(message)
    print(f"UW_LATENCY_CAMPAIGN_STATE={state['state']}")
    print(f"UW_LATENCY_CAMPAIGN_SELF_SHA256={aggregate['self_sha256']}")
    print(f"UW_LATENCY_STATE_SELF_SHA256={state['self_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
