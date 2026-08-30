"""Refreeze the Phase 8 dispersion audit at the current protected main lock."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from mds650.executable_closure import build_executable_closure
from mds650.storage import assert_outside_frozen

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "artifacts" / "phase8_bridge" / "bridge_contract_v2.json"
OUTPUT = (
    ROOT / "artifacts" / "phase8_bridge" / "dispersion_audit_producer_freeze_v3.json"
)
EXECUTABLE_SCRIPTS = (
    "scripts/build_phase8_bridge_dispersion_audit_v1.py",
    "scripts/evaluate_phase8_bridge_v2.py",
    "scripts/rp2_block12_prospective_design.py",
    "uv.lock",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _canonical_sha256(payload: dict[str, Any]) -> str:
    body = {key: value for key, value in payload.items() if key != "freeze_sha256"}
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def build_freeze() -> dict[str, Any]:
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    closure = build_executable_closure(ROOT, scripts=EXECUTABLE_SCRIPTS)
    files = {row["path"]: row["sha256"] for row in closure["files"]}
    document: dict[str, Any] = {
        "schema_version": "phase8-dispersion-audit-producer-freeze-v3.0",
        "status": "PHASE8_DISPERSION_AUDIT_EXECUTABLE_CLOSURE_FROZEN",
        "protocol_id": contract["protocol_id"],
        "contract_sha256": contract["contract_sha256"],
        "contract_file_sha256": _sha256(CONTRACT),
        "audit_producer": {
            "path": "scripts/build_phase8_bridge_dispersion_audit_v1.py",
            "sha256": files["scripts/build_phase8_bridge_dispersion_audit_v1.py"],
        },
        "phase8_replay_producer": {
            "path": "scripts/evaluate_phase8_bridge_v2.py",
            "sha256": files["scripts/evaluate_phase8_bridge_v2.py"],
        },
        "current_dv_producer": {
            "path": "scripts/rp2_block12_prospective_design.py",
            "sha256": files["scripts/rp2_block12_prospective_design.py"],
        },
        "executable_closure": closure,
        "supersedes": "artifacts/phase8_bridge/dispersion_audit_producer_freeze_v2.json",
        "supersession_reason": "DEPENDENCY_LOCK_UPDATED_BY_DEPENDABOT_PRS_22_AND_23",
        "sealed_store_reopened": False,
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
    print(f"[phase8-dispersion] refroze audit producer closure at {output}")


if __name__ == "__main__":
    main()
