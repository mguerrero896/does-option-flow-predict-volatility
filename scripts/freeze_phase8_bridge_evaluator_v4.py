"""Freeze the Phase 8 executable closure after the Phase 9 calendar correction."""

from __future__ import annotations

import json
from pathlib import Path

from freeze_phase8_bridge_evaluator_v3 import build_freeze

from mds650.storage import assert_outside_frozen

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "artifacts" / "phase8_bridge" / "evaluator_freeze_v4.json"


def main() -> None:
    output = assert_outside_frozen(OUTPUT)
    output.write_text(
        json.dumps(
            build_freeze(schema_version="phase8-bridge-evaluator-freeze-v4.0"),
            indent=1,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"[phase8-bridge] froze executable closure at {output} (sealed_cohorts_read=0)")


if __name__ == "__main__":
    main()
