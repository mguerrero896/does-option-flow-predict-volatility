"""The same-session Phase 8 repair stays post-hoc, paired and path-free."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

REPO = Path(__file__).resolve().parents[2]
ROOT = REPO / "artifacts" / "phase8_bridge"
CONTRACT = ROOT / "materialized_remediation_contract_20260831_v1.json"
WARMUP = ROOT / "materialized_remediation_contract_amendment_20260831_v1.json"
GRID = ROOT / "materialized_remediation_contract_amendment_20260831_v2.json"
RESULT = ROOT / "materialized_remediation_20260831_v1.json"
REPORT = REPO / "reports" / "phase8a_exploratory_bridge_addendum_v13.md"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _semantic_sha(payload: dict[str, Any], field: str) -> str:
    body = {key: value for key, value in payload.items() if key != field}
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def test_contract_chain_precedes_measurement_and_preserves_the_one_shot_result() -> None:
    contract, warmup, grid, result = map(_load, (CONTRACT, WARMUP, GRID, RESULT))

    assert contract["contract_sha256"] == _semantic_sha(contract, "contract_sha256")
    assert warmup["amendment_sha256"] == _semantic_sha(warmup, "amendment_sha256")
    assert grid["amendment_sha256"] == _semantic_sha(grid, "amendment_sha256")
    assert result["result_sha256"] == _semantic_sha(result, "result_sha256")
    assert warmup["amends_contract_sha256"] == contract["contract_sha256"]
    assert grid["amends_contract_sha256"] == contract["contract_sha256"]
    assert grid["supersedes_amendment_sha256"] == warmup["amendment_sha256"]
    assert result["contract_sha256"] == contract["contract_sha256"]
    assert result["warmup_amendment_sha256"] == warmup["amendment_sha256"]
    assert result["grid_amendment_sha256"] == grid["amendment_sha256"]
    assert result["historical_result_preserved"] is True
    assert result["new_sessions_collected"] == 0
    assert result["sealed_cohorts_read"] == 0
    assert result["sealed_store_reopened"] is False
    assert result["confirmatory_promotion_allowed"] is False


def test_paired_comparison_separates_admissibility_from_predictive_improvement() -> None:
    result = _load(RESULT)
    comparison = result["forecast_comparison"]

    assert comparison["grid"] == {
        "historical_only_origins": 175,
        "historical_rows": 11875,
        "paired_common_origins": 11700,
        "remediated_only_origins": 0,
        "remediated_rows": 11700,
    }
    assert comparison["rv30_exactly_equal_on_paired_grid"] is True
    assert result["b2_panel_negative_control"]["all_features_exact_on_paired_grid"] is True
    primary_b1 = [
        row
        for row in comparison["mean_qlike_cells"]
        if row["window"] == "primary_20" and "B1" in row["information_set"]
    ]
    assert len(primary_b1) == comparison["primary_b1_inclusive_cells"] == 8
    assert sum(bool(row["improved"]) for row in primary_b1) == 1
    assert comparison["primary_b1_inclusive_cells_improved"] == 1
    assert comparison["global_label"] == "MIXED"


def test_public_result_and_report_state_the_actual_coverage_and_claim_boundary() -> None:
    result = _load(RESULT)
    encoded = json.dumps(result)
    report = REPORT.read_text(encoding="utf-8")

    assert result["personal_paths_emitted"] is False
    assert result["secret_values_emitted"] is False
    assert "C:\\" not in encoded and "D:\\" not in encoded
    risk_reversal = result["b1_panel_comparison"]["features"]["b1_risk_reversal_25"]
    assert risk_reversal["remediated_paired_finite"] == 11664
    assert "11,664/11,700 = 99.6923%" in report
    assert "only one of eight B1-inclusive" in report
    assert "POST_HOC_REMEDIATION_SENSITIVITY_NOT_CONFIRMATORY" in report
