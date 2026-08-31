"""Harvest target-blind UW latency reconciliations and derive lifecycle state."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from mds650.uw_latency_campaign import (
    build_campaign_artifact,
    build_campaign_state,
    latency_outlier_alerts,
    read_artifact,
    write_new_json,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reconciliation", type=Path, action="append", required=True)
    parser.add_argument("--session-dir", type=Path, action="append", required=True)
    parser.add_argument("--anomaly-artifact", type=Path, required=True)
    parser.add_argument("--aggregate-output", type=Path, required=True)
    parser.add_argument("--state-output", type=Path, required=True)
    parser.add_argument("--as-of-date", required=True)
    parser.add_argument("--emit-alert", action="store_true")
    args = parser.parse_args(argv)

    anomaly = read_artifact(args.anomaly_artifact, "UW_LATENCY_ANOMALY_ARTIFACT_INVALID")
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
