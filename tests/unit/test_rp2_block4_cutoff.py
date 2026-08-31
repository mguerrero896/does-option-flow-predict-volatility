"""B0 and its direct-bar challengers must stop at the registered tape cutoff."""

from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path
from types import ModuleType

import numpy as np
import polars as pl
import pytest

REPO = Path(__file__).resolve().parents[2]
ORIGIN = 35
ASOF = ORIGIN - 3  # 120-second cutoff plus the start-labelled bar's closing minute.


def _load() -> ModuleType:
    name = "rp2_block4_b0_panel_cutoff_test"
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / "rp2_block4_b0_panel.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


BLOCK4 = _load()


def _bars(session: date, *, asset: str = "AAPL") -> pl.DataFrame:
    minutes = np.arange(390, dtype=np.int64)
    steps = 0.0001 + minutes * 1e-7
    close = 100.0 * np.exp(np.cumsum(steps))
    return pl.DataFrame(
        {
            "asset": [asset] * minutes.size,
            "session_date": [session] * minutes.size,
            "role": ["D"] * minutes.size,
            "source": ["synthetic"] * minutes.size,
            "minute": minutes,
            "close": close,
            "high": close * (1.001 + minutes * 1e-7),
            "low": close * (0.999 - minutes * 1e-7),
            "volume": 1_000.0 + minutes.astype(np.float64),
        }
    )


def _mutate_after_cutoff(bars: pl.DataFrame) -> pl.DataFrame:
    late = pl.col("minute").is_between(ASOF + 1, ORIGIN)
    return bars.with_columns(
        pl.when(late).then(pl.col("close") * 1.2).otherwise(pl.col("close")).alias("close"),
        pl.when(late).then(pl.col("high") * 1.3).otherwise(pl.col("high")).alias("high"),
        pl.when(late).then(pl.col("low") * 0.8).otherwise(pl.col("low")).alias("low"),
        pl.when(late).then(pl.col("volume") * 10.0).otherwise(pl.col("volume")).alias("volume"),
    )


def _origin_row(frame: pl.DataFrame) -> pl.DataFrame:
    row = frame.filter(pl.col("origin_minute") == ORIGIN)
    assert row.height == 1
    return row


def test_b0_predictors_stop_at_the_cutoff_but_the_forward_target_does_not() -> None:
    bars = _bars(date(2025, 6, 20))
    changed = _mutate_after_cutoff(bars)
    left, _ = BLOCK4.build_b0_panel(bars, max_fill_share=0.05)
    right, _ = BLOCK4.build_b0_panel(changed, max_fill_share=0.05)
    left_row, right_row = _origin_row(left), _origin_row(right)

    predictors = (
        "rv_back_5",
        "rv_back_15",
        "rv_back_30",
        "rq_back_30",
        "rs_up_back_30",
        "rs_down_back_30",
        "jump_back_30",
        "rv_session_to_date",
        "ret_5",
        "ret_30",
        "parkinson_30",
        "volume_30",
        "dollar_volume_30",
    )
    for column in predictors:
        assert left_row[column][0] == pytest.approx(right_row[column][0]), column
    assert left_row["rv30"][0] != pytest.approx(right_row["rv30"][0])


def test_first_origin_leaves_the_cutoff_and_a_full_trailing_window() -> None:
    panel, _ = BLOCK4.build_b0_panel(_bars(date(2025, 6, 20)), max_fill_share=0.05)
    assert int(panel["origin_minute"].min()) == ORIGIN


def test_market_controls_stop_at_the_same_cutoff_bar() -> None:
    bars = _bars(date(2025, 6, 20), asset="SPY")
    left = _origin_row(BLOCK4.build_market_controls(bars))
    right = _origin_row(BLOCK4.build_market_controls(_mutate_after_cutoff(bars)))
    assert left["SPY_rv_30"][0] == pytest.approx(right["SPY_rv_30"][0])
    assert left["SPY_ret_30"][0] == pytest.approx(right["SPY_ret_30"][0])


def test_ewma_challenger_stops_at_the_same_cutoff_bar() -> None:
    bars = _bars(date(2025, 6, 20))
    panel, _ = BLOCK4.build_b0_panel(bars, max_fill_share=0.05)
    left = BLOCK4.causal_ewma_forecasts(bars, panel, role="D", max_fill_share=0.05)
    right = BLOCK4.causal_ewma_forecasts(
        _mutate_after_cutoff(bars), panel, role="D", max_fill_share=0.05
    )
    index = (
        panel.filter(pl.col("role") == "D")
        .sort(["session_date", "asset", "origin_minute"])["origin_minute"]
        .to_list()
        .index(ORIGIN)
    )
    assert left[index] == pytest.approx(right[index])


def test_garch_challenger_filters_only_through_the_cutoff(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sessions = [date(2025, 6, 16), date(2025, 6, 17), date(2025, 6, 18), date(2025, 6, 20)]
    bars = pl.concat([_bars(session) for session in sessions], how="vertical")
    panel, _ = BLOCK4.build_b0_panel(bars, max_fill_share=0.05)

    class FakeGarch:
        omega = 1.0
        alpha = 0.0
        beta = 0.0
        persistence = 0.0

        @staticmethod
        def filter(returns: np.ndarray) -> np.ndarray:
            return np.arange(1, returns.size + 1, dtype=np.float64)

    captured: dict[str, np.ndarray] = {}

    def capture(
        _target: np.ndarray,
        forecast: np.ndarray,
        _test: np.ndarray,
        _response: np.ndarray,
        _train: np.ndarray,
    ) -> dict[str, float]:
        captured["forecast"] = forecast.copy()
        return {"qlike": 0.0}

    monkeypatch.setattr(BLOCK4, "fit_garch11", lambda _returns: FakeGarch())
    monkeypatch.setattr(BLOCK4, "_constant_forecast_metrics", capture)
    BLOCK4.fit_intraday_garch(bars, panel, role="D", train_share=0.5, max_fill_share=0.05)

    frame = panel.filter(pl.col("role") == "D").sort(["session_date", "asset", "origin_minute"])
    position = int(
        np.flatnonzero(
            (frame["session_date"].to_numpy() == str(sessions[2]))
            & (frame["origin_minute"].to_numpy() == ORIGIN)
        )[0]
    )
    expected = float((ASOF + 1) + (BLOCK4.TARGET_HORIZON - 1))
    assert captured["forecast"][position] == pytest.approx(expected)
