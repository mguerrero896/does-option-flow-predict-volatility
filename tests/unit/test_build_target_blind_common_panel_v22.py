"""Unit tests for the target-blind common-panel builder guardrails."""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

import polars as pl
import pytest
from tests.unit.test_phase6_b2 import _frames

from mds650.phase6 import B2V2_FEATURES

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
builder = importlib.import_module("build_target_blind_common_panel_v22")


def _sensitivity_record(*, status: str = "PASS") -> dict[str, object]:
    """Return a minimum target-free Massive sensitivity record."""
    return {
        "status": status,
        "selection_rule": (
            "last_quote_by_sip_timestamp_then_sequence_at_or_before_origin_minus_delay"
        ),
        "no_targets_or_predictive_metrics_read": True,
    }


def test_massive_sensitivity_guard_accepts_registered_target_free_contract(
    tmp_path: Path,
) -> None:
    """The builder accepts only the documented target-free Massive contract."""
    path = tmp_path / "massive.json"
    path.write_text(json.dumps(_sensitivity_record()), encoding="utf-8")

    builder._validate_massive_sensitivity(path)


def test_massive_sensitivity_guard_rejects_non_pass_status(tmp_path: Path) -> None:
    """A non-PASS sensitivity record fails before panel construction."""
    path = tmp_path / "massive.json"
    path.write_text(json.dumps(_sensitivity_record(status="FAIL")), encoding="utf-8")

    with pytest.raises(ValueError, match="TARGET_BLIND_V22_MASSIVE_SENSITIVITY_NOT_ACCEPTED"):
        builder._validate_massive_sensitivity(path)


def test_combined_b2_digest_binds_name_and_content_deterministically(
    tmp_path: Path,
) -> None:
    """B2 source identity changes when a date partition's content changes."""
    first = tmp_path / "date=2026-01-05.parquet"
    second = tmp_path / "date=2026-01-06.parquet"
    first.write_bytes(b"one")
    second.write_bytes(b"two")

    initial = builder.combined_input_digest([second, first])
    repeat = builder.combined_input_digest([first, second])
    second.write_bytes(b"changed")

    assert initial == repeat
    assert builder.combined_input_digest([first, second]) != initial


def test_panel_excluded_activity_cannot_change_later_eligible_features(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Exercise the real file-reading producer and B2, isolating only B0/B1."""
    activity, origins = _frames(days=25)
    activity = activity.with_columns(
        (pl.col("forecast_origin_utc") - pl.duration(seconds=60)).alias("b2v2_cutoff_utc"),
        (pl.col("forecast_origin_utc") - pl.duration(seconds=90)).alias("b2v2_max_created_at_utc"),
    )
    excluded = origins.item(4, "origin_id")
    availability = origins.with_columns(
        pl.lit(builder.B2_PRIMARY_VARIANT).alias("canonical_variant"),
        (pl.col("origin_id") != excluded).alias("eligible_for_corrected_pit_panel"),
        pl.lit("SYNTHETIC_TEST").alias("row_status"),
    )
    # Another variant must not be used to determine the primary's eligibility.
    availability = pl.concat(
        [
            availability,
            availability.with_columns(
                pl.lit("latency_5m_120s").alias("canonical_variant"),
                pl.lit(True).alias("eligible_for_corrected_pit_panel"),
            ),
        ]
    )
    origins.write_parquet(tmp_path / "origins.parquet")
    availability.write_parquet(tmp_path / "availability.parquet")
    activity_path = tmp_path / "date=activity.parquet"
    activity.write_parquet(activity_path)
    sensitivity = tmp_path / "massive.json"
    sensitivity.write_text(json.dumps(_sensitivity_record()), encoding="utf-8")
    monkeypatch.setattr(builder, "build_target_blind_b0_v22", lambda *a, **k: origins)
    monkeypatch.setattr(builder, "adapt_b1q_source_to_v22", lambda *a: origins)
    monkeypatch.setattr(
        builder,
        "build_target_blind_common_predictor_panel_v22",
        lambda origins, b0, b1, b2: (b2, b2),
    )
    monkeypatch.setattr(builder, "summarize_target_blind_common_predictor_panel_v22", lambda p: {})
    inputs = {
        "origins_path": tmp_path / "origins.parquet",
        "b1_source_path": tmp_path / "origins.parquet",
        "fmp_bars_path": tmp_path / "origins.parquet",
        "b2_primary_root": tmp_path,
        "availability_path": tmp_path / "availability.parquet",
        "massive_sensitivity_path": sensitivity,
    }
    baseline = builder.build_panel(**inputs)[0]
    activity.with_columns(
        pl.when(pl.col("origin_id") == excluded)
        .then(1_000_000.0)
        .otherwise(pl.col("option_trade_count_5m"))
        .alias("option_trade_count_5m")
    ).write_parquet(activity_path)
    shocked = builder.build_panel(**inputs)[0]
    usable = baseline.filter(pl.col("b2v2_corrected_pit_complete"))
    assert usable.height > 0
    assert usable.select("origin_id", *B2V2_FEATURES).equals(
        shocked.filter(pl.col("b2v2_corrected_pit_complete")).select("origin_id", *B2V2_FEATURES)
    )
