"""The successor method freeze must satisfy the sealed preregistration that demands it.

`artifacts/target_blind_v22/next_confirmation_preregistration_v2.json` lists the minimum
contents a successor method freeze must carry, and requires an explicit human
authorization before any out-of-sample access. This contract holds the freeze and its
authorization to that list, and refuses a freeze that claims an out-of-sample read has
already happened.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
BASE = REPO / "artifacts" / "target_blind_v22"
PREREG = BASE / "next_confirmation_preregistration_v2.json"
FREEZE = BASE / "successor_method_freeze_v1.json"
AUTH = BASE / "successor_owner_authorization_v1.json"


def _load(path: Path) -> dict[str, Any]:
    payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return payload


def test_freeze_carries_every_content_the_preregistration_requires() -> None:
    required = _load(PREREG)["successor_method_freeze_minimum_contents"]
    freeze = _load(FREEZE)
    missing = [name for name in required if name not in freeze]
    assert not missing, f"successor method freeze omits required contents: {missing}"


def test_freeze_binds_the_panel_the_preregistration_sealed() -> None:
    prereg = _load(PREREG)
    freeze = _load(FREEZE)
    assert freeze["bound_panel_sha256"] == prereg["bound_panel"]["panel_sha256"]
    assert freeze["provenance"]["preregistration_sha256"] == prereg["preregistration_sha256"]


def test_freeze_declares_no_outcome_was_read_before_it_was_written() -> None:
    freeze = _load(FREEZE)
    assert freeze["zero_oos_reads_at_freeze"] is True
    assert freeze["model_fit_performed_at_freeze"] is False


def test_authorization_names_the_exact_freeze_it_authorises() -> None:
    body = FREEZE.read_text(encoding="utf-8")
    digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
    auth = _load(AUTH)
    assert auth["contract_sha256"] == digest, (
        "the authorization points at a different freeze than the one on disk; "
        "an authorization must name the exact document it signs"
    )
    assert auth["authorize_read_and_evaluation"] is True
    assert auth["authorized_by"]
    assert auth["sealed_cohorts_read_before"] == 0
