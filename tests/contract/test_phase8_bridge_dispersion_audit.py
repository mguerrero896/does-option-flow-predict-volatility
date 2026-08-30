"""Phase 8 dispersion audit and addendum remain bound to frozen evidence."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from build_phase8_bridge_dispersion_audit_v1 import main as build_audit_main  # noqa: E402

AUDIT_V1 = REPO / "artifacts" / "phase8_bridge" / "dispersion_audit_20260830_v1.json"
AUDIT_V2 = REPO / "artifacts" / "phase8_bridge" / "dispersion_audit_20260830_v2.json"
AUDIT_V3 = REPO / "artifacts" / "phase8_bridge" / "dispersion_audit_20260830_v3.json"
AUDIT_V4 = REPO / "artifacts" / "phase8_bridge" / "dispersion_audit_20260830_v4.json"
RESULT = REPO / "artifacts" / "phase8_bridge" / "result_20260830_v1.json"
REPORT_V1 = REPO / "reports" / "phase8a_exploratory_bridge_addendum_v1.md"
REPORT_V2 = REPO / "reports" / "phase8a_exploratory_bridge_addendum_v2.md"
REPORT_V3 = REPO / "reports" / "phase8a_exploratory_bridge_addendum_v3.md"
REPORT_V4 = REPO / "reports" / "phase8a_exploratory_bridge_addendum_v4.md"
REPORT_V5 = REPO / "reports" / "phase8a_exploratory_bridge_addendum_v5.md"
REGISTRY = REPO / "data" / "FROZEN_ARTIFACTS.json"


def _load(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))  # type: ignore[no-any-return]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _canonical_sha(payload: dict[str, Any]) -> str:
    body = {key: value for key, value in payload.items() if key != "audit_sha256"}
    encoded = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def test_dispersion_audit_replays_the_primary_result_and_resolves_aggregation() -> None:
    audit = _load(AUDIT_V4)
    result = _load(RESULT)

    assert audit["audit_sha256"] == _canonical_sha(audit)
    assert audit["source_identity"]["forecast_cube"]["sha256"] == (
        result["forecast_cube_sha256"]
    )
    assert audit["source_identity"]["result"]["result_sha256"] == (
        result["result_sha256"]
    )
    producer = audit["source_identity"]["current_dv_reference"]["producer"]
    assert producer["path"] == "scripts/rp2_block12_prospective_design.py"
    assert producer["sha256"] == (
        "4ab2d426cdf92f96d3e6a2fefd5b768db382c362ca924b604c82d7d0543694a8"
    )
    closure = producer["executable_closure"]
    assert closure["algorithm"] == "sha256-of-sorted-path-and-normalized-sha256-v1"
    assert closure["file_count"] == 126
    assert closure["sha256"] == (
        "939a238b1ff703e57b597582bca24205bf8e2b947227e264fcc0140fb08dd95d"
    )
    assert {row["path"] for row in closure["files"]} >= {
        "scripts/rp2_block12_prospective_design.py",
        "src/mds650/metrics.py",
        "src/mds650/rp2/ladder.py",
        "src/mds650/rp2/panel.py",
        "src/mds650/rp2/preprocessing.py",
        "uv.lock",
    }
    historical = audit["source_identity"]["contract_power_design"]
    assert historical["producer_bytes_available_to_this_audit"] is False
    assert historical["producer_identity_status"] == "RECORDED_UNRESOLVABLE_FROM_PUBLIC_ROOT"
    assert audit["status"] == "COMPLETE_WITH_HISTORICAL_PRODUCER_UNRESOLVED"
    assert audit["checks"] == {
        "cube_duplicate_keys": 0,
        "cube_nulls": 0,
        "cube_rows": 190000,
        "published_statistics_replayed_exactly": True,
        "replayed_contrast_rows": 20,
        "replayed_statistic_fields": 140,
        "sealed_store_reopened": False,
        "second_evaluator_execution": False,
    }
    assert audit["conclusion"]["aggregation_change_supported"] is False
    assert audit["conclusion"]["delta_b1_holm_below_0_05_cells"] == 3
    assert audit["conclusion"]["delta_b2_given_b1_holm_below_0_05_cells"] == 0
    assert audit["conclusion"]["delta_b2_given_b1_intervals_crossing_zero"] == 4

    significant = []
    for role in ("D", "V"):
        for model in ("gamma_glm", "lightgbm"):
            cell = audit["cells"][role][model]
            published = result["evaluation"][role][model]["windows"]["primary_20"]
            for contrast in ("delta_b1", "delta_b2_given_b1"):
                for field in (
                    "estimate",
                    "ci_low",
                    "ci_high",
                    "p_value_raw",
                    "p_value_holm_descriptive",
                ):
                    assert cell[contrast][field] == published[contrast][field]
            if cell["delta_b1"]["holm_below_0_05"]:
                significant.append((role, model))
                assert (
                    cell["delta_b1"]["contract_reference"][
                        "reference_to_phase8_sigma"
                    ]
                    > 1.0
                )
                assert (
                    cell["delta_b1"]["current_dv_reference"][
                        "reference_to_phase8_sigma"
                    ]
                    > 1.0
                )
    assert significant == [
        ("D", "lightgbm"),
        ("V", "gamma_glm"),
        ("V", "lightgbm"),
    ]


def test_addendum_v5_publishes_all_holm_values_and_preserves_history() -> None:
    report = REPORT_V5.read_text(encoding="utf-8")
    for value in ("0.9802", "0.0050", "0.0208", "0.0040"):
        assert value in report
    for value in ("0.5756", "0.3940", "0.9528", "1.0000"):
        assert value in report
    for phrase in (
        "80% power",
        "alpha = 0.005",
        "aggregation-change hypothesis is not supported",
        "historical panel bytes are not available",
        "cannot be independently rehashed",
        "126-file",
        "executable closure",
        "sealed_store_reopened = false",
    ):
        assert phrase in report

    registered = {entry["path"]: entry["sha256"] for entry in _load(REGISTRY)["entries"]}
    assert registered[REPORT_V1.relative_to(REPO).as_posix()] == _sha(REPORT_V1)
    assert registered[REPORT_V2.relative_to(REPO).as_posix()] == _sha(REPORT_V2)
    assert registered[REPORT_V3.relative_to(REPO).as_posix()] == _sha(REPORT_V3)
    assert registered[REPORT_V4.relative_to(REPO).as_posix()] == _sha(REPORT_V4)
    assert registered[REPORT_V5.relative_to(REPO).as_posix()] == _sha(REPORT_V5)
    assert registered[AUDIT_V1.relative_to(REPO).as_posix()] == _sha(AUDIT_V1)
    assert registered[AUDIT_V2.relative_to(REPO).as_posix()] == _sha(AUDIT_V2)
    assert registered[AUDIT_V3.relative_to(REPO).as_posix()] == _sha(AUDIT_V3)
    assert registered[AUDIT_V4.relative_to(REPO).as_posix()] == _sha(AUDIT_V4)


def test_dispersion_producer_refuses_a_registered_output() -> None:
    missing = str(REPO / "does-not-exist")
    with pytest.raises(ValueError, match="FROZEN_ARTIFACT_WRITE_REJECTED"):
        build_audit_main(
            [
                "--forecast-cube",
                missing,
                "--b0-panel",
                missing,
                "--b1-panel",
                missing,
                "--b2-panel",
                missing,
                "--output",
                str(AUDIT_V4),
            ]
        )
