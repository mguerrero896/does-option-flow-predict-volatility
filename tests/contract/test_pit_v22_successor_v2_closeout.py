"""The published successor-v2 closeout must stay immutable and internally linked."""

from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
ARTIFACTS = REPO / "artifacts" / "target_blind_v22"
RESULT = ARTIFACTS / "successor_evaluation_result_v2.json"
LOG = ARTIFACTS / "successor_evaluation_run_v2.json"
AUDIT = ARTIFACTS / "successor_custody_audit_v2.json"
LEDGER = ARTIFACTS / "pit_v22_claim_ledger_v2.json"
MARKDOWN = REPO / "docs" / "pit_v22_claims_and_limitations_v2.md"

_spec = importlib.util.spec_from_file_location(
    "build_pit_v22_successor_v2_closeout",
    REPO / "scripts" / "build_pit_v22_successor_v2_closeout.py",
)
assert _spec is not None and _spec.loader is not None
_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_module)


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _self_sha(payload: dict[str, object], field: str) -> str:
    body = {key: value for key, value in payload.items() if key != field}
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def test_successor_v2_closeout_is_hash_linked_and_public_safe() -> None:
    result = _load(RESULT)
    log = _load(LOG)
    audit = _load(AUDIT)
    ledger = _load(LEDGER)

    assert _sha(RESULT) == "ddad159bc02067fd14ef1f7b1c35b9ed02eef26ebd5d19e9e88c5838d6b97775"
    assert _sha(LOG) == "0507ccf5903d46ccd7fee2dc7a535faa8455501e7a1061bafceadd1d8e5f96a3"
    assert result["manifest_sha256"] == _self_sha(result, "manifest_sha256")
    assert audit["audit_sha256"] == _self_sha(audit, "audit_sha256")
    assert ledger["ledger_sha256"] == _self_sha(ledger, "ledger_sha256")
    assert audit["result_file_sha256"] == _sha(RESULT)
    assert audit["full_log_file_sha256"] == _sha(LOG)
    assert audit["status"] == "PASS_INDEPENDENT_POST_OOS_CUSTODY_AUDIT"
    assert audit["evaluation_attempt_count"] == audit["oos_read_count"] == 1
    assert audit["independent_review"]["status"] == "PASS"
    assert audit["target_linkage"] == {
        "all_eligible_origins": 62_254,
        "all_excluded_origins": 12,
        "all_predictor_complete_origins": 62_266,
        "development_eligible_origins": 37_306,
        "development_excluded_origins": 6,
        "development_predictor_complete_origins": 37_312,
    }
    assert len(audit["verified_content_addressed_payloads"]) == 10
    assert ledger["custody_audit_sha256"] == audit["audit_sha256"]
    assert ledger["status"] == "SCIENTIFIC_RESULT_ELIGIBLE_EDGE_NOT_CONFIRMED"
    assert ledger["decision"] == "GLOBAL_EDGE_NOT_CONFIRMED"
    assert ledger["eligibility"] == {
        "capital_eligible": False,
        "capital_go": False,
        "edge_claim_eligible": False,
        "edge_claim_reason": "NO_BINARY_EDGE_PROMOTION_RULE_IN_SIGNED_SUCCESSOR_FREEZE",
        "research_only": True,
        "scientific_result_eligible": True,
        "scientific_result_reason": "PASS_POST_OOS_CUSTODY_VALIDATION",
    }
    assert ledger["historical_bundle_comparison"]["historical_aggregate_count"] == 12
    assert all(
        contrast["estimate_at_least_mde"] is False
        for role in ledger["contrasts"].values()
        for contrast in role.values()
    )
    assert [event["event"] for event in log["events"]] == _module.EXPECTED_EVENTS
    assert MARKDOWN.read_bytes().replace(b"\r\n", b"\n").decode() == _module.render_markdown(ledger)
    public_text = "\n".join(
        path.read_text(encoding="utf-8") for path in (AUDIT, LEDGER, MARKDOWN)
    ).casefold()
    assert "c:\\users" not in public_text
    assert "d:\\" not in public_text
    assert result["personal_paths_emitted"] is False
    assert result["secret_values_emitted"] is False
