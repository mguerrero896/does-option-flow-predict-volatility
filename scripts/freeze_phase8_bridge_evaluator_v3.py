"""Freeze the complete executable closure of the target-blind Phase 8 evaluator."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from mds650.executable_closure import build_executable_closure
from mds650.storage import assert_outside_frozen

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "artifacts" / "phase8_bridge" / "bridge_contract_v2.json"
OUTPUT = ROOT / "artifacts" / "phase8_bridge" / "evaluator_freeze_v3.json"
EXECUTABLE_SCRIPTS = (
    "scripts/evaluate_phase8_bridge_v2.py",
    "scripts/download_calibration_20d.py",
    "scripts/rp3_acquire_batch.py",
    "scripts/rp3_build_eval_panels.py",
    "scripts/rp2_block3_target_panel.py",
    "scripts/rp2_block4_b0_panel.py",
    "scripts/rp2_block5_surface_panel.py",
    "scripts/rp2_block6_flow_panel.py",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _canonical_sha256(payload: dict[str, Any]) -> str:
    body = {key: value for key, value in payload.items() if key != "freeze_sha256"}
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_freeze(
    *, schema_version: str = "phase8-bridge-evaluator-freeze-v3.0"
) -> dict[str, Any]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    closure = build_executable_closure(ROOT, scripts=EXECUTABLE_SCRIPTS)
    evaluator = next(
        row for row in closure["files"] if row["path"] == "scripts/evaluate_phase8_bridge_v2.py"
    )
    document = {
        "schema_version": schema_version,
        "status": "TARGET_BLIND_EXECUTABLE_CLOSURE_FROZEN_READ_NOT_AUTHORIZED",
        "protocol_id": contract["protocol_id"],
        "contract_sha256": contract["contract_sha256"],
        "contract_file_sha256": _sha256(CONTRACT),
        "evaluator": evaluator["path"],
        "evaluator_sha256": evaluator["sha256"],
        "executable_closure": closure,
        "materialization": "BLIND_STORE_TO_EXISTING_RP3_PANEL_ADAPTER",
        "models": ["gamma_glm", "lightgbm"],
        "windows": {"primary_sessions": 20, "sensitivity_sessions": 30},
        "one_shot_claim": "holdout/evaluation_claim_v2.json",
        "sealed_cohorts_read": 0,
    }
    document["freeze_sha256"] = _canonical_sha256(document)
    return document


def main() -> None:
    output = assert_outside_frozen(OUTPUT)
    output.write_text(
        json.dumps(build_freeze(), indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        f"[phase8-bridge] froze executable closure at {output} "
        "(sealed_cohorts_read=0)"
    )


if __name__ == "__main__":
    main()
