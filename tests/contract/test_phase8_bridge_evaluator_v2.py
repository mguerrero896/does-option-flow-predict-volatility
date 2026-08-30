"""The consumed Phase 8 closure stays auditable and implements all five estimands."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "evaluate_phase8_bridge_v2", ROOT / "scripts" / "evaluate_phase8_bridge_v2.py"
)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_evaluator_fails_closed_and_reports_all_five_estimands() -> None:
    contract = MODULE.load_contract(MODULE.DEFAULT_CONTRACT)
    freeze = json.loads(MODULE.DEFAULT_EVALUATOR_FREEZE.read_text(encoding="utf-8"))
    assert freeze["freeze_sha256"] == MODULE._canonical_sha256(
        freeze, omit="freeze_sha256"
    )
    evaluator_hash = hashlib.sha256(
        (ROOT / freeze["evaluator"]).read_bytes().replace(b"\r\n", b"\n")
    ).hexdigest()
    assert freeze["evaluator_sha256"] == evaluator_hash
    assert next(
        row["sha256"]
        for row in freeze["executable_closure"]["files"]
        if row["path"] == freeze["evaluator"]
    ) == evaluator_hash
    assert freeze["contract_sha256"] == contract["contract_sha256"]
    assert freeze["sealed_cohorts_read"] == 0
    with pytest.raises(
        PermissionError, match="PHASE8_BRIDGE_ONE_SHOT_AUTHORIZATION_REQUIRED"
    ):
        MODULE.validate_authorization(None, contract)

    sessions = np.repeat(np.arange(20, dtype=np.int64), 6)
    base = np.linspace(1.0, 1.4, sessions.size)
    losses = {
        "B0": base,
        "B0+B1": base - 0.04,
        "B0+B2": base - 0.02,
        "B0+B1+B2": base - 0.07,
    }
    rows = MODULE.analyse_losses(losses, sessions, repetitions=199, seed=650)
    assert set(rows) == {
        "delta_b1",
        "delta_b2_given_b1",
        "delta_b2_given_b0",
        "delta_total",
        "delta_interaction",
    }
    assert rows["delta_total"]["estimate"] == pytest.approx(0.07)
    assert rows["delta_interaction"]["estimate"] == pytest.approx(0.01)
    assert all(row["sessions"] == 20 for row in rows.values())
    assert all(0.0 <= row["p_value_holm_descriptive"] <= 1.0 for row in rows.values())


def test_one_shot_claim_is_atomic_and_advances_the_counter_once(tmp_path: Path) -> None:
    contract = MODULE.load_contract(MODULE.DEFAULT_CONTRACT)
    token = {
        "authorization_id": "owner-test-token",
        "authorized_by": "owner",
        "authorized_at_utc": "2026-08-29T00:00:00+00:00",
    }
    (tmp_path / "access_counter.json").write_text(
        json.dumps({"append_count": 750, "read_count": 0}),
        encoding="utf-8",
    )
    (tmp_path / "access.log").write_text("", encoding="utf-8")
    claim = MODULE.claim_one_shot(tmp_path, token, contract)
    assert claim["status"] == "CLAIMED_BEFORE_RAW_READ"
    counter = json.loads((tmp_path / "access_counter.json").read_text(encoding="utf-8"))
    assert counter["read_count"] == 1
    with pytest.raises(RuntimeError, match="PHASE8_BRIDGE_STORE_ALREADY_READ"):
        MODULE.claim_one_shot(tmp_path, token, contract)
