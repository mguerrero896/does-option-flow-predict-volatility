"""Regression checks for the same-30-session Phase 8 remediation comparison."""

from __future__ import annotations

import sys
from pathlib import Path

import polars as pl
import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "scripts"))

from replay_phase8_materialized_remediation_v1 import (  # noqa: E402
    compare_forecast_cubes,
)


def _cube(*, change_negative_control: bool = False) -> tuple[pl.DataFrame, pl.DataFrame]:
    historical: list[dict[str, object]] = []
    remediated: list[dict[str, object]] = []
    for role in ("D", "V"):
        for model in ("gamma_glm", "lightgbm"):
            for information_set in ("B0", "B0+B1", "B0+B2", "B0+B1+B2"):
                for session in ("2026-08-03", "2026-08-04"):
                    old_forecast = 1.5 if "B1" in information_set else 1.2
                    new_forecast = 1.1 if "B1" in information_set else old_forecast
                    if change_negative_control and information_set == "B0":
                        new_forecast = 1.19
                    row = {
                        "training_role": role,
                        "model_family": model,
                        "information_set": information_set,
                        "session_date": session,
                        "asset": "AAPL",
                        "origin_minute": 60,
                        "rv30": 1.0,
                    }
                    historical.append({**row, "forecast": old_forecast})
                    remediated.append({**row, "forecast": new_forecast})
    return pl.DataFrame(historical), pl.DataFrame(remediated)


def _bridge() -> dict[str, object]:
    return {
        "cohort": {
            "primary": {"window": "2026-08-03..2026-08-04"},
            "sensitivity": {"window": "2026-08-03..2026-08-04"},
        }
    }


def test_comparison_requires_stable_controls_and_reports_improvement() -> None:
    historical, remediated = _cube()
    result = compare_forecast_cubes(historical, remediated, _bridge())

    assert result["negative_controls"] == {"B0": True, "B0+B2": True}
    assert result["primary_b1_inclusive_cells"] == 8
    assert result["primary_b1_inclusive_cells_improved"] == 8
    assert result["global_label"] == "UNANIMOUS_B1_INCLUSIVE_IMPROVEMENT"


def test_comparison_fails_if_b0_negative_control_moves() -> None:
    historical, remediated = _cube(change_negative_control=True)

    with pytest.raises(ValueError, match="NEGATIVE_CONTROL_CHANGED:B0"):
        compare_forecast_cubes(historical, remediated, _bridge())
