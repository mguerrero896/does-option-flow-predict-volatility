"""Recalibrating a mean forecast must not quietly turn it back into a median.

`fit_log_ols` and `fit_ridge_log` multiply `exp(fitted)` by `exp(0.5 Var(resid_train))`,
the lognormal retransformation that makes the forecast a conditional MEAN, which is what
QLIKE scores. The block-8 recalibration then regresses `log rv30` on `log forecast` over
the same training rows and rebuilds the forecast as `exp(a + b log f)`, with no
`sigma^2 / 2` term.

For an OLS fit the residuals are orthogonal to the fitted values, so that regression
returns `b = 1` and `a = -0.5 Var(resid)` exactly: the correction is algebraically the
inverse of the smearing factor the fitter has just applied. Recalibration therefore
divides the forecast by `exp(0.5 Var(resid))` and reports a median where a mean is
required. The published artifact carries the fingerprint - `log_ols` slope
`0.9999999999999961`, intercept `-0.112598` (D) and `-0.115683` (V), identical across all
four information sets.

The second test covers the reason the first one went unnoticed: `run_role` publishes a
QLIKE level only for the raw branch, so the recalibrated branch could carry a level shift
of that size without any level in the artifact showing it.
"""

from __future__ import annotations

import importlib.util
import sys
from datetime import date, timedelta
from pathlib import Path
from types import ModuleType

import numpy as np
import polars as pl
import pytest

from mds650.rp2.ladder import fit_log_ols
from mds650.rp2.panel import AVAILABILITY_COLUMNS, B0_FEATURES, B1_FEATURES, B2_FEATURES

REPO = Path(__file__).resolve().parents[2]


def _load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_recalibrating_an_already_calibrated_mean_forecast_leaves_it_alone() -> None:
    """The exact algebraic property: on an OLS fit the correction has to be the identity."""

    rng = np.random.default_rng(650)
    rows = 4000
    design = np.column_stack(
        [np.ones(rows), rng.normal(0.0, 1.0, rows), rng.normal(0.0, 1.0, rows)]
    )
    coefficients = np.asarray([-11.0, 0.6, -0.3])
    target = np.exp(design @ coefficients + rng.normal(0.0, 0.5, rows))
    train = np.zeros(rows, dtype=bool)
    train[: rows // 2] = True

    forecast = fit_log_ols(design, target, train)
    ladder = _load("rp2_block8_ladder")
    corrected, calibration = ladder._recalibrate(forecast, target, train)

    # The regression cannot return anything else: slope one, intercept minus half the
    # residual variance the fitter has just added back as smearing.
    fit, *_ = np.linalg.lstsq(design[train], np.log(target[train]), rcond=None)
    residual_variance = float(np.var(np.log(target[train]) - (design @ fit)[train]))
    assert calibration["slope"] == pytest.approx(1.0, abs=1e-9)
    assert calibration["intercept"] == pytest.approx(-0.5 * residual_variance, abs=1e-9)

    # And therefore the correction must be a no-op, not a division by the smearing factor.
    ratio = corrected / forecast
    assert float(np.max(np.abs(ratio - 1.0))) < 1e-9, (
        "recalibration rescaled an already mean-calibrated forecast by "
        f"{float(np.median(ratio)):.6f}; exp(-0.5 Var(resid)) is "
        f"{float(np.exp(-0.5 * residual_variance)):.6f}"
    )


def _session_label(offset: int) -> str:
    return (date(2026, 1, 5) + timedelta(days=offset)).isoformat()


def _synthetic_panel(sessions: int = 40, origins: int = 40) -> pl.DataFrame:
    rng = np.random.default_rng(650)
    assets = ("AAA", "BBB")
    rows = sessions * origins * len(assets)
    frame = pl.DataFrame(
        {
            "asset": [a for _ in range(sessions * origins) for a in assets],
            "session_date": [
                _session_label(index // origins)
                for index in range(sessions * origins)
                for _ in assets
            ],
            "origin_minute": [
                30 + index % origins for index in range(sessions * origins) for _ in assets
            ],
            "role": ["D"] * rows,
            "source": ["synthetic"] * rows,
            "rv30": rng.lognormal(-11.0, 0.4, rows),
        }
    )
    registered = {**B0_FEATURES, **B1_FEATURES, **B2_FEATURES}
    return frame.with_columns(
        **{name: pl.Series(rng.lognormal(0.0, 0.3, rows)) for name in registered},
        **{
            name: pl.Series(np.zeros(rows))
            for name in AVAILABILITY_COLUMNS
            if name not in registered
        },
    )


def test_the_recalibrated_branch_publishes_its_own_loss_level() -> None:
    """A contrast published without its levels is a contrast nobody can audit."""

    ladder = _load("rp2_block8_ladder")
    result = ladder.run_role(_synthetic_panel(), role="D", train_share=0.6, models=("log_ols",))
    assert result["status"] == "MEASURED"
    record = result["models"]["log_ols"]  # type: ignore[index]
    assert "qlike_recalibrated" in record, (
        "the recalibrated contrasts are published without the levels they are built from"
    )
    assert set(record["qlike_recalibrated"]) == set(record["qlike"])
