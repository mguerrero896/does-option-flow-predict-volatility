"""Empty-window corrections never invent activity, remove rows or touch targets."""

import numpy as np
import polars as pl
import pytest
from artifacts.rp4_v3_code.empty_windows import affected_columns, recode
from polars.testing import assert_frame_equal


def test_empty_shape_nan_activity_zero_unknown_separate():
    source = pl.DataFrame(
        {
            "asset": ["A"] * 3,
            "session_date": ["2020-01-02"] * 3,
            "origin_minute": [60, 65, 70],
            "rv30": [1.0, 2.0, 3.0],
            "b2_5m_trades": [0.0, 2.0, float("nan")],
            "b2_30m_trades": [3.0, 0.0, 4.0],
            "b2_5m_premium": [0.0, 200.0, float("nan")],
            "b2_5m_delta_flow": [0.0, -20.0, 1.0],
            "b2_5m_contract_entropy": [0.0, 0.5, 0.0],
            "b2_30m_d_iv": [0.2, 0.0, 0.1],
            "b2_5m_decay_intensity_last": [4.0, 5.0, 6.0],
            "b2_5m_decay_intensity_innovation": [0.0, 0.1, 0.2],
        }
    )
    rule = {"columns_to_nan": {str(m): affected_columns(source.columns, m) for m in (5, 30)}}
    result, audit = recode(source, rule)
    assert result.height == source.height
    assert np.isnan(result["b2_5m_contract_entropy"][0])
    assert result["b2_5m_contract_entropy"][2] == 0
    assert np.isnan(result["b2_30m_d_iv"][1])
    assert result["b2_5m_window_empty"].to_list()[:2] == [1.0, 0.0]
    assert np.isnan(result["b2_5m_window_empty"][2])
    for column in ("rv30", "b2_5m_premium", "b2_5m_delta_flow", "b2_5m_decay_intensity_last"):
        assert_frame_equal(result.select(column), source.select(column), check_exact=True)
    assert all(row["empty_rows"] == 1 for row in audit)
    invalid = source.with_columns(pl.lit(-1.0).alias("b2_5m_trades"))
    with pytest.raises(ValueError, match="INVALID_TRADE_COUNT"):
        recode(invalid, rule)


def test_only_registered_shapes_and_shares_selected():
    names = [
        "b2_5m_contracts",
        "b2_5m_buy_premium_share",
        "b2_5m_gamma_flow",
        "b2_5m_d_mid_rel",
        "b2_30m_d_mid_rel",
        "b2_5m_decay_intensity_last",
    ]
    assert affected_columns(names, 5) == ["b2_5m_buy_premium_share", "b2_5m_d_mid_rel"]
