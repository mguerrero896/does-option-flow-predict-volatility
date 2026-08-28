"""Freeze the executable identity of the target-blind Phase 8 bridge evaluator."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "artifacts" / "phase8_bridge" / "bridge_contract_v2.json"
EVALUATOR = ROOT / "scripts" / "evaluate_phase8_bridge_v2.py"
OUTPUT = ROOT / "artifacts" / "phase8_bridge" / "evaluator_freeze_v2.json"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _canonical_sha256(payload: dict[str, Any]) -> str:
    body = {key: value for key, value in payload.items() if key != "freeze_sha256"}
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_freeze() -> dict[str, Any]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    document = {
        "schema_version": "phase8-bridge-evaluator-freeze-v2.0",
        "status": "TARGET_BLIND_EXECUTABLE_FROZEN_READ_NOT_AUTHORIZED",
        "protocol_id": contract["protocol_id"],
        "contract_sha256": contract["contract_sha256"],
        "contract_file_sha256": _sha256(CONTRACT),
        "evaluator": "scripts/evaluate_phase8_bridge_v2.py",
        "evaluator_sha256": _sha256(EVALUATOR),
        "materialization": "BLIND_STORE_TO_EXISTING_RP3_PANEL_ADAPTER",
        "models": ["gamma_glm", "lightgbm"],
        "windows": {"primary_sessions": 20, "sensitivity_sessions": 30},
        "one_shot_claim": "holdout/evaluation_claim_v2.json",
        "sealed_cohorts_read": 0,
    }
    document["freeze_sha256"] = _canonical_sha256(document)
    return document


def main() -> None:
    OUTPUT.write_text(
        json.dumps(build_freeze(), indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(f"[phase8-bridge] froze evaluator at {OUTPUT} (sealed_cohorts_read=0)")


if __name__ == "__main__":
    main()
