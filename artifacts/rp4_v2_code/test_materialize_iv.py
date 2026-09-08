"""Synthetic checks for the sole IV rule and exact keyed v1 preservation."""

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
import pytest
import rp2_block5_surface_panel as surface_v1
import rp2_block6_flow_panel as flow_v1
from materialize_iv import (
    KEYS,
    TAPE_COLUMNS,
    bind_reader,
    iv_counts,
    iv_filter,
    new_tape,
    option_features,
    parity,
    reader_frames,
    replace_columns,
)
from polars.testing import assert_frame_equal


def tape_fixture() -> pl.DataFrame:
    start = datetime(2026, 7, 1, 13, 45, tzinfo=UTC)
    rows = []
    for index in range(120):
        stamp = start + timedelta(seconds=index * 8)
        row: dict[str, Any] = dict.fromkeys(TAPE_COLUMNS, 0.0)
        row.update(
            id=str(index),
            underlying_symbol="AAPL",
            created_at=stamp,
            executed_at=stamp - timedelta(seconds=1),
            implied_volatility=0.2 + (index % 5) * 0.01,
            size=10.0,
            open_interest=20.0,
            expiry=date(2026, 7, 17),
            strike=95.0 + index % 12,
            option_type="call" if index % 2 else "put",
            nbbo_bid=1.0,
            nbbo_ask=1.1,
            premium=1000.0,
            tags="ask_side",
            report_flags="",
            multi_vol=0.0,
        )
        rows.append(row)
    return pl.DataFrame(rows)


def test_inclusive_iv_rule_and_counts_keep_no_nonfinite() -> None:
    frame = pl.DataFrame(
        {"implied_volatility": [None, np.nan, np.inf, -np.inf, 0.01, 0.029, 0.03, 3.0, 3.01, 5.0]}
    )
    assert iv_filter(frame)["implied_volatility"].to_list() == [0.03, 3.0]
    counts = iv_counts(frame)
    assert counts["raw_asset_rows"] == 10
    assert counts["iv_null_rows"] == 1
    assert counts["iv_nonfinite_nonnull_rows"] == 3
    assert counts["iv_rejected_total_rows"] == 8
    assert counts["newly_rejected_within_old_iv_range"] == 4


def test_reader_adapter_matches_original_without_mutating_globals(tmp_path: Path) -> None:
    raw = tape_fixture()
    path = tmp_path / "tape.parquet"
    raw.write_parquet(path)
    surface, flow = reader_frames(raw, filtered=False)
    assert_frame_equal(surface, surface_v1._read_tape([str(path)], "AAPL"))
    assert_frame_equal(flow, flow_v1._read_tape([str(path)], "AAPL"))
    original = flow_v1.build_session_flow.__globals__["_read_tape"]
    bound = bind_reader(flow_v1.build_session_flow, flow)
    assert bound.__globals__["_read_tape"]([], "AAPL").equals(flow)
    assert flow_v1.build_session_flow.__globals__["_read_tape"] is original
    assert bound.__code__ is flow_v1.build_session_flow.__code__


def test_keyed_replacement_preserves_targets_nan_and_other_columns() -> None:
    base = pl.DataFrame(
        {
            "asset": ["AAPL"] * 2,
            "session_date": ["2026-07-01"] * 2,
            "origin_minute": [40, 35],
            "rv30": [0.2, np.nan],
            "fixed": [7, 9],
            "b2_flow": [1.0, 2.0],
        }
    )
    replacement = base.select(KEYS).reverse().with_columns(b2_flow=pl.Series([10.0, 20.0]))
    result = replace_columns(base, replacement, ["b2_flow"])
    assert result["b2_flow"].to_list() == [10.0, 20.0]
    assert_frame_equal(base.drop("b2_flow").sort(KEYS), result.drop("b2_flow"), check_exact=True)
    with pytest.raises((AssertionError, ValueError)):
        replace_columns(base, replacement.head(1), ["b2_flow"])


def test_rejected_trade_cannot_change_eligible_future_iv_or_intensity() -> None:
    from types import SimpleNamespace

    raw = tape_fixture().with_columns(
        pl.when(pl.col("id") == "110")
        .then(4.0)
        .otherwise(pl.col("implied_volatility"))
        .alias("implied_volatility")
    )
    changed = raw.with_columns(
        pl.when(pl.col("id") == "110")
        .then(4.9)
        .otherwise(pl.col("implied_volatility"))
        .alias("implied_volatility")
    )
    base = pl.DataFrame(
        {
            "asset": ["AAPL"],
            "session_date": ["2026-07-01"],
            "origin_minute": [35],
            "rv_back_30": [0.001],
            "rate": [0.04],
            "dividend_cash_prior365": [1.0],
        }
    )
    grid = SimpleNamespace(close=np.full(390, 100.0), open=np.full(390, 100.0))
    names = [
        "b2_30m_vega_flow",
        "b2_30m_d_iv",
        "b2_30m_premium",
        "b2_30m_decay_intensity_last",
        "rp4_iv_dte_8_30_m_097_103",
        "rp4_surface_populated_cells",
        "rp4_dealer_gamma_net",
    ]
    original = option_features(raw, base, grid, names, filtered=True)
    other = option_features(changed, base, grid, names, filtered=True)
    assert_frame_equal(original, other, check_exact=True)
    baseline = option_features(raw, base, grid, names, filtered=False)
    assert baseline["b2_30m_premium"][0] > original["b2_30m_premium"][0]
    assert baseline["b2_30m_decay_intensity_last"][0] > original["b2_30m_decay_intensity_last"][0]
    with pytest.raises(ValueError, match="UNFILTERED_V1_PRODUCER_PARITY"):
        parity(baseline, original, names)


def test_deduplication_uses_only_v1_new_feature_identity_columns() -> None:
    raw = tape_fixture().head(1)
    doubled = pl.concat([raw, raw.with_columns(tags=pl.lit("bid_side"))])
    assert new_tape(doubled).height == 1
    with pytest.raises(ValueError, match="DUPLICATE_ID_CONFLICT"):
        new_tape(pl.concat([raw, raw.with_columns(implied_volatility=pl.lit(0.4))]))
