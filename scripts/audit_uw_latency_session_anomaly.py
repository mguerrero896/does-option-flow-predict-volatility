"""Write sanitized structural evidence for one UW latency session anomaly."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from pathlib import Path

from mds650.uw_latency_campaign import build_anomaly_evidence, write_new_json


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    evidence = build_anomaly_evidence(args.session_dir)
    write_new_json(args.output, evidence)
    print(f"UW_LATENCY_ANOMALY_CLASSIFICATION={evidence['classification']}")
    print(f"UW_LATENCY_ANOMALY_SELF_SHA256={evidence['self_sha256']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
