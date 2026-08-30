"""Target-blind panel tests for independent replication."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import polars as pl
import pytest

from mds650 import b1_replication_common as sut
from mds650.b1_replication_common import build_replication_common_frame
from mds650.b1v3 import B1V3_FEATURES
from mds650.b1v3_confirmation import canonical_sha256, sha256_file
from mds650.phase6 import B0V2_FEATURES
from mds650.study_design import B2_FEATURE_NAMES


def _self_hashed(document: dict[str, Any]) -> dict[str, Any]:
    document["manifest_sha256"] = canonical_sha256(document)
    return document


def _write_json(path: Path, document: object) -> None:
    path.write_text(json.dumps(document), encoding="utf-8")


def _artifact_inputs(tmp_path: Path, *, complete: bool = True) -> dict[str, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    days = [date(2024, 12, 1) + timedelta(days=offset) for offset in range(30)]
    assets = ("AAPL", "AMZN", "META", "MSFT", "NVDA", "TSLA")
    rows = [(day, asset) for day in days for asset in assets]
    origin_ids = [f"{asset}:{day.isoformat()}" for day, asset in rows]
    origins = pl.DataFrame(
        {
            "origin_id": origin_ids,
            "asset": [asset for _, asset in rows],
            "session_date": [day.isoformat() for day, _ in rows],
            "forecast_origin_utc": [
                datetime.combine(day, datetime.min.time(), UTC) + timedelta(hours=15)
                for day, _ in rows
            ],
            "forecast_origin_ns": list(range(1_000_000_000, 1_000_000_000 + len(rows))),
            "role": ["independent_replication"] * len(rows),
            "session_minute": [30] * len(rows),
            "session_tercile": [
                ("first" if index < 10 else "second" if index < 20 else "third")
                for index, _ in enumerate(days)
                for _ in assets
            ],
        }
    )
    b0_values: dict[str, list[object]] = {
        feature: (
            [asset for _, asset in rows]
            if feature == "b0v2_asset_identity"
            else [0.1] * len(rows)
        )
        for feature in B0V2_FEATURES
    }
    b0 = pl.DataFrame(
        {
            "origin_id": origin_ids,
            **b0_values,
            "b0_complete": [True] * len(rows),
            "b0_missing_reason": [None] * len(rows),
            "max_predictor_available_at_utc": [
                value - timedelta(minutes=1) for value in origins["forecast_origin_utc"]
            ],
        }
    )
    b1 = pl.DataFrame(
        {
            "origin_id": origin_ids,
            **{feature: [0.1] * len(rows) for feature in B1V3_FEATURES},
            "b1v3a_complete": [complete] * len(rows),
            "b1v3b_complete": [complete] * len(rows),
            "b1v3c_complete": [complete] * len(rows),
            "max_sip_timestamp_ns": [value - 1 for value in origins["forecast_origin_ns"]],
        }
    )
    cutoff = origins["forecast_origin_utc"]
    b2 = pl.DataFrame(
        {
            "origin_id": origin_ids,
            **{feature: [0.1] * len(rows) for feature in B2_FEATURE_NAMES},
            "b2v2_availability_eligible": [complete] * len(rows),
            "b2v2_availability_status": ["ELIGIBLE" if complete else "EXCLUDED"] * len(rows),
            "source_temporal_state": ["ON_TIME" if complete else "DELAYED"] * len(rows),
            "b2v2_max_created_at_utc": cutoff,
            "b2v2_cutoff_utc": cutoff,
        }
    )
    paths = {
        name: tmp_path / name
        for name in (
            "preregistration.json",
            "base.json",
            "b1_source.json",
            "b1_inventory.json",
            "b1.json",
            "b2.json",
            "origins.parquet",
            "b0.parquet",
            "b1.parquet",
            "b2.parquet",
            "schema.json",
            "output.parquet",
            "manifest.json",
        )
    }
    origins.write_parquet(paths["origins.parquet"])
    b0.write_parquet(paths["b0.parquet"])
    b1.write_parquet(paths["b1.parquet"])
    b2.write_parquet(paths["b2.parquet"])
    _write_json(paths["b1_inventory.json"], {"inventory": []})
    _write_json(paths["schema.json"], {})

    preregistration = _self_hashed(
        {
            "replication_target_reads": 0,
            "result_sign_selection": "PROHIBITED",
            "replication_sessions": [day.isoformat() for day in days],
        }
    )
    base = _self_hashed(
        {
            "preregistration_sha256": preregistration["manifest_sha256"],
            "origin_count": len(rows),
            "outputs": {
                "origins": {"sha256": sha256_file(paths["origins.parquet"])},
                "b0": {"sha256": sha256_file(paths["b0.parquet"])},
            },
        }
    )
    b1_source = _self_hashed(
        {
            "preregistration_manifest_sha256": preregistration["manifest_sha256"],
            "base_manifest_sha256": base["manifest_sha256"],
            "raw_payload_binding": {
                "inventory_sha256": sha256_file(paths["b1_inventory.json"])
            },
        }
    )
    b1_manifest = _self_hashed(
        {
            "output": {"sha256": sha256_file(paths["b1.parquet"])},
            "provenance": {
                "source_binding_manifest_sha256": b1_source["manifest_sha256"]
            },
        }
    )
    b2_manifest = _self_hashed(
        {
            "preregistration_sha256": preregistration["manifest_sha256"],
            "features": list(B2_FEATURE_NAMES),
            "variants": {
                "primary_5m_60s": {"sha256": sha256_file(paths["b2.parquet"])}
            },
        }
    )
    for name, document in (
        ("preregistration.json", preregistration),
        ("base.json", base),
        ("b1_source.json", b1_source),
        ("b1.json", b1_manifest),
        ("b2.json", b2_manifest),
    ):
        _write_json(paths[name], document)
    return paths


def _build_artifacts(paths: dict[str, Path]) -> dict[str, Any]:
    return sut.build_replication_common_artifacts(
        preregistration_path=paths["preregistration.json"],
        base_manifest_path=paths["base.json"],
        base_schema_path=paths["schema.json"],
        b1_source_manifest_path=paths["b1_source.json"],
        b1_source_schema_path=paths["schema.json"],
        b1_inventory_path=paths["b1_inventory.json"],
        b1_manifest_path=paths["b1.json"],
        b1_schema_path=paths["schema.json"],
        b2_manifest_path=paths["b2.json"],
        b2_schema_path=paths["schema.json"],
        origins_path=paths["origins.parquet"],
        b0_path=paths["b0.parquet"],
        b1_path=paths["b1.parquet"],
        b2_path=paths["b2.parquet"],
        output_path=paths["output.parquet"],
        manifest_path=paths["manifest.json"],
        manifest_schema_path=paths["schema.json"],
    )


def _write_base_chain(paths: dict[str, Path], base: dict[str, Any]) -> None:
    base.pop("manifest_sha256", None)
    base = _self_hashed(base)
    _write_json(paths["base.json"], base)
    b1_source = json.loads(paths["b1_source.json"].read_text(encoding="utf-8"))
    b1_source["base_manifest_sha256"] = base["manifest_sha256"]
    b1_source.pop("manifest_sha256")
    b1_source = _self_hashed(b1_source)
    _write_json(paths["b1_source.json"], b1_source)
    b1 = json.loads(paths["b1.json"].read_text(encoding="utf-8"))
    b1["provenance"]["source_binding_manifest_sha256"] = b1_source["manifest_sha256"]
    b1.pop("manifest_sha256")
    _write_json(paths["b1.json"], _self_hashed(b1))


def test_common_panel_preserves_origins_and_masks_unavailable_b2() -> None:
    origins = pl.DataFrame(
        {
            "origin_id": ["AAPL:1", "AAPL:2"],
            "asset": ["AAPL", "AAPL"],
            "session_date": ["2024-12-10", "2024-12-10"],
            "forecast_origin_utc": [
                datetime(2024, 12, 10, 15, tzinfo=UTC),
                datetime(2024, 12, 10, 15, 5, tzinfo=UTC),
            ],
            "forecast_origin_ns": [1_000_000_000, 2_000_000_000],
            "role": ["independent_replication", "independent_replication"],
            "session_minute": [30, 35],
            "session_tercile": ["first", "first"],
        }
    )
    b0_values: dict[str, list[object]] = {
        feature: (["AAPL", "AAPL"] if feature == "b0v2_asset_identity" else [0.1, 0.2])
        for feature in B0V2_FEATURES
    }
    b0 = pl.DataFrame(
        {
            "origin_id": ["AAPL:1", "AAPL:2"],
            **b0_values,
            "b0_complete": [True, True],
            "b0_missing_reason": [None, None],
            "max_predictor_available_at_utc": [
                datetime(2024, 12, 10, 14, 59, tzinfo=UTC),
                datetime(2024, 12, 10, 15, 4, tzinfo=UTC),
            ],
        }
    )
    b1 = pl.DataFrame(
        {
            "origin_id": ["AAPL:1", "AAPL:2"],
            **{feature: [0.1, 0.2] for feature in B1V3_FEATURES},
            "b1v3a_complete": [True, True],
            "b1v3b_complete": [True, True],
            "b1v3c_complete": [True, True],
            "max_sip_timestamp_ns": [900_000_000, 1_900_000_000],
        }
    )
    cutoff = datetime(2024, 12, 10, 14, 59, tzinfo=UTC)
    b2 = pl.DataFrame(
        {
            "origin_id": ["AAPL:1", "AAPL:2"],
            **{feature: [0.1, None] for feature in B2_FEATURE_NAMES},
            "b2v2_availability_eligible": [True, False],
            "b2v2_availability_status": ["ELIGIBLE", "EXCLUDED_DELAY"],
            "source_temporal_state": ["ON_TIME", "DELAYED"],
            "b2v2_max_created_at_utc": [cutoff, None],
            "b2v2_cutoff_utc": [cutoff, cutoff],
        }
    )

    panel = build_replication_common_frame(origins=origins, b0=b0, b1=b1, b2=b2)

    assert panel.height == 2
    assert panel["role"].unique().to_list() == ["confirmation"]
    assert panel["b1v3a_information_set_complete"].to_list() == [True, True]
    assert panel["b2_information_set_complete"].to_list() == [True, False]
    excluded = panel.filter(~pl.col("b2v2_availability_eligible"))
    assert all(excluded[feature].null_count() == 1 for feature in B2_FEATURE_NAMES)


def test_replication_common_artifacts_are_source_bound_and_idempotent(tmp_path: Path) -> None:
    paths = _artifact_inputs(tmp_path)

    first = _build_artifacts(paths)
    second = _build_artifacts(paths)

    assert first == second
    assert first["status"] == "PASS_TARGET_BLIND_COMMON_PREDICTOR_PANEL"
    assert first["outcome_read_count"] == 0
    assert first["technical_acceptance"]["status"] == "PASS"
    assert first["output"]["row_count"] == 180
    assert paths["output.parquet"].is_file()
    assert paths["manifest.json"].is_file()


def test_replication_common_artifacts_preserve_a_failed_technical_gate(tmp_path: Path) -> None:
    paths = _artifact_inputs(tmp_path, complete=False)

    document = _build_artifacts(paths)

    assert document["status"] == "FAIL_TARGET_BLIND_COMMON_PREDICTOR_PANEL"
    assert document["technical_acceptance"]["status"] == "FAIL"
    assert document["technical_acceptance"]["common_complete_origin_count"] == 0


def test_replication_common_json_reader_fails_closed(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{", encoding="utf-8")
    non_object = tmp_path / "array.json"
    non_object.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError, match="BROKEN"):
        sut._json_object(malformed, code="BROKEN")
    with pytest.raises(ValueError, match="BROKEN"):
        sut._json_object(non_object, code="BROKEN")


def test_replication_common_rejects_hash_and_nested_source_shape_drift(tmp_path: Path) -> None:
    paths = _artifact_inputs(tmp_path)
    base = json.loads(paths["base.json"].read_text(encoding="utf-8"))
    base["outputs"] = None
    base.pop("manifest_sha256")
    _write_json(paths["base.json"], _self_hashed(base))

    with pytest.raises(ValueError, match="B1_REPLICATION_COMMON_SOURCE_BINDING_INVALID"):
        _build_artifacts(paths)

    paths = _artifact_inputs(tmp_path / "b2-shape")
    b2 = json.loads(paths["b2.json"].read_text(encoding="utf-8"))
    b2["variants"] = None
    b2.pop("manifest_sha256")
    _write_json(paths["b2.json"], _self_hashed(b2))

    with pytest.raises(ValueError, match="B1_REPLICATION_COMMON_SOURCE_BINDING_INVALID"):
        _build_artifacts(paths)


def test_replication_common_rejects_a_tampered_source_manifest(tmp_path: Path) -> None:
    paths = _artifact_inputs(tmp_path)
    b1 = json.loads(paths["b1.json"].read_text(encoding="utf-8"))
    b1["output"]["sha256"] = "0" * 64
    _write_json(paths["b1.json"], b1)

    with pytest.raises(ValueError, match="B1_REPLICATION_COMMON_B1_HASH_INVALID"):
        _build_artifacts(paths)


def test_replication_common_rejects_a_non_confirmation_result(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    invalid = pl.DataFrame({"role": ["development"]})
    monkeypatch.setattr(sut, "build_common_predictor_frame", lambda **_: invalid)

    with pytest.raises(ValueError, match="B1_REPLICATION_COMMON_ROLE_INVALID"):
        sut.build_replication_common_frame(
            origins=pl.DataFrame(),
            b0=pl.DataFrame(),
            b1=pl.DataFrame(),
            b2=pl.DataFrame(),
        )


def test_replication_common_scope_guard_rejects_a_missing_origin(tmp_path: Path) -> None:
    paths = _artifact_inputs(tmp_path)
    b0 = pl.read_parquet(paths["b0.parquet"]).slice(1)
    b0.write_parquet(paths["b0.parquet"])
    base = json.loads(paths["base.json"].read_text(encoding="utf-8"))
    base["outputs"]["b0"]["sha256"] = sha256_file(paths["b0.parquet"])
    _write_base_chain(paths, base)

    with pytest.raises(ValueError, match="B1V3_COMMON_B0_ORIGIN_SCOPE_INVALID"):
        _build_artifacts(paths)


def test_replication_common_scope_guard_rejects_a_manifest_count_drift(tmp_path: Path) -> None:
    paths = _artifact_inputs(tmp_path)
    base = json.loads(paths["base.json"].read_text(encoding="utf-8"))
    base["origin_count"] = 179
    _write_base_chain(paths, base)

    with pytest.raises(ValueError, match="B1_REPLICATION_COMMON_SCOPE_INVALID"):
        _build_artifacts(paths)
