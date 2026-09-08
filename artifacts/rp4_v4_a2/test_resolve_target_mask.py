"""Synthetic proof that a resolution cannot relax the unchanged eligible sample."""

from __future__ import annotations

from datetime import date
from typing import Any

import numpy as np
import polars as pl
import pytest
from artifacts.rp4_v4_a2.resolve_target_mask import audit_pair
from artifacts.rp4_v4_code.test_targets import bars

from mds650.rp2.bars import build_session_grid
from mds650.rp2.realized import forward_measures, log_returns


def fixture() -> tuple[dict[str, Any], Any, pl.DataFrame]:
    observed = bars().filter(pl.col("minute") != 35)
    grid = build_session_grid(observed, session=date(2026, 6, 9))
    registered = forward_measures(log_returns(grid.close), np.array([30], dtype=np.int64), 5).rv[0]
    row = {
        "asset": "AAPL",
        "session_date": "2026-06-09",
        "origin_minute": 30,
        "comparison": "registered_rv_5",
        "reason": "finite_mask_mismatch",
        "eligible_v3": False,
        "reference": registered,
        "reconstructed": float("nan"),
    }
    return row, grid, observed


def test_observed_close_difference_reproduces_registered_bits() -> None:
    row, grid, observed = fixture()
    result = audit_pair(row, grid, observed)
    assert result["missing_minutes"] == "35"
    assert result["registered_fill_rule_reproduction_bit_exact"] is True


def test_resolution_cannot_allow_any_eligible_target_difference() -> None:
    row, grid, observed = fixture()
    with pytest.raises(ValueError, match="INELIGIBLE_MISSING_TARGET"):
        audit_pair({**row, "eligible_v3": True}, grid, observed)


def test_resolution_rejects_even_one_bit_error_in_registered_replay() -> None:
    row, grid, observed = fixture()
    with pytest.raises(ValueError, match="NOT_BIT_EXACT"):
        audit_pair({**row, "reference": np.nextafter(row["reference"], 1.0)}, grid, observed)
