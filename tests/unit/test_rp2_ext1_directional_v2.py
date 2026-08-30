"""Regression tests for the versioned Ext1 directional reanalysis."""

from __future__ import annotations

import importlib.util
import sys
from datetime import date
from pathlib import Path

import numpy as np
import polars as pl
import pytest

ROOT = Path(__file__).resolve().parents[2]


def _load(name: str):  # type: ignore[no-untyped-def]
    scripts = str(ROOT / "scripts")
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _bars(session: date, *, first_minute: int, minutes: int) -> pl.DataFrame:
    observed = np.arange(first_minute, minutes, dtype=np.int64)
    return pl.DataFrame(
        {
            "asset": ["AAPL"] * observed.size,
            "session_date": [session] * observed.size,
            "minute": observed,
            "close": 100.0 * np.exp(0.0001 * observed),
            "source": ["synthetic"] * observed.size,
            "role": ["D"] * observed.size,
        }
    )


def test_target_builder_counts_and_drops_an_unfilled_open(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    ext1 = _load("rp2_ext1_mechanism_utility")
    late = _bars(date(2026, 3, 2), first_minute=2, minutes=390)
    clean = _bars(date(2026, 3, 3), first_minute=0, minutes=390)
    monkeypatch.setattr(ext1, "load_bar_sources", lambda root, sources: pl.concat([late, clean]))
    origins = {
        ("AAPL", "2026-03-02"): np.array([30.0]),
        ("AAPL", "2026-03-03"): np.array([30.0]),
    }
    coverage: dict[str, object] = {}

    targets = ext1.build_target_battery(
        Path("unused"), origins, sources=(("synthetic", "D", "unused"),), coverage=coverage
    )

    assert targets["session_date"].unique().to_list() == ["2026-03-03"]
    assert coverage["candidate_asset_sessions"] == 2
    assert coverage["rejected_nonfinite_close"] == 1
    assert coverage["accepted_asset_sessions"] == 1


def test_target_builder_accepts_a_true_early_close(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    ext1 = _load("rp2_ext1_mechanism_utility")
    half_day = _bars(date(2025, 11, 28), first_minute=0, minutes=210)
    monkeypatch.setattr(ext1, "load_bar_sources", lambda root, sources: half_day)
    coverage: dict[str, object] = {}

    targets = ext1.build_target_battery(
        Path("unused"),
        {("AAPL", "2025-11-28"): np.array([60.0])},
        sources=(("synthetic", "D", "unused"),),
        coverage=coverage,
    )

    assert targets.height == 1
    assert np.isfinite(targets["y_signed_return_120"][0])
    assert coverage["early_close_asset_sessions"] == 1
    assert coverage["session_minutes"] == {"210": 1}
    assert coverage["rejected_fill_share"] == 0
    assert coverage["rejected_nonfinite_close"] == 0
    assert coverage["rejected_nonpositive_close"] == 0


def test_legacy_dml_keeps_coefficient_magnitudes() -> None:
    ext1 = _load("rp2_ext1_mechanism_utility")
    rng = np.random.default_rng(650)
    rows = 2400
    sessions = np.repeat(np.arange(24, dtype=np.int64), 100)
    nuisance = np.column_stack([np.ones(rows), rng.normal(size=rows)])
    treatment = rng.normal(size=(rows, 1))
    response = 0.02 * treatment[:, 0] + rng.normal(scale=0.1, size=rows)
    frame = pl.DataFrame({"b1_term_slope": nuisance[:, 1]})

    result = ext1._dml_on_target(
        nuisance,
        treatment,
        response,
        sessions,
        ("mechanism",),
        folds=3,
        evaluation_base=np.ones(rows, dtype=bool),
        frame=frame,
        nuisance_features=["b1_term_slope"],
    )

    assert result is not None
    coefficient = result["coefficients"]["mechanism"]
    assert {"theta", "standard_error", "ci_95_low", "ci_95_high", "nominal_mde"} <= set(coefficient)


def test_legacy_ranking_passes_sessions_to_the_booster(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    ext1 = _load("rp2_ext1_mechanism_utility")
    rows = 20
    target = np.linspace(0.01, 0.20, rows)
    train = np.arange(rows) < 10
    test = ~train
    sessions = np.repeat(np.arange(10, dtype=np.int64), 2)
    captured: dict[str, np.ndarray] = {}

    def fitted(model, design, response, train_mask, *, sessions=None):  # type: ignore[no-untyped-def]
        captured["sessions"] = sessions
        return response

    monkeypatch.setattr(ext1, "fit_ladder_model", fitted)
    ext1.ranking_utility(target, {"B0+B1": target[:, None]}, train, test, sessions)
    assert np.array_equal(captured["sessions"], sessions)


@pytest.fixture(scope="module")
def directional():  # type: ignore[no-untyped-def]
    return _load("rp2_ext1_directional_v2")


def test_preregistration_hash_and_family_are_frozen(directional) -> None:  # type: ignore[no-untyped-def]
    contract = directional.load_contract(ROOT / "configs" / "rp2_ext1_directional_v2.json")
    assert contract["family"]["dml_effect_tests"] == 60
    assert contract["family"]["directional_metric_tests"] == 8
    assert contract["family"]["size"] == 68


def test_matched_mode_uses_identical_rows_at_every_horizon(directional) -> None:  # type: ignore[no-untyped-def]
    frame = pl.DataFrame(
        {
            "y_signed_return_5": [0.1, 0.2, 0.3, 0.4],
            "y_signed_return_60": [0.1, 0.2, 0.3, np.nan],
            "y_signed_return_120": [0.1, np.nan, 0.3, np.nan],
        }
    )
    cell = np.ones(frame.height, dtype=bool)
    masks = [
        directional.analysis_mask(frame, cell, horizon, "matched120_tod")
        for horizon in (5, 60, 120)
    ]
    assert all(np.array_equal(mask, np.array([True, False, True, False])) for mask in masks)
    assert directional.analysis_mask(frame, cell, 60, "native_tod").sum() == 3


def test_effect_record_keeps_magnitude_uncertainty_and_mde(directional) -> None:  # type: ignore[no-untyped-def]
    record = directional.effect_record(
        theta=0.01,
        standard_error=0.002,
        p_value=0.004,
        rows=4000,
        clusters=40,
        evaluation_mask_sha256="a" * 64,
        family_size=68,
    )
    assert record["theta"] == pytest.approx(0.01)
    assert record["standard_error"] == pytest.approx(0.002)
    assert record["ci_95_low"] < 0.01 < record["ci_95_high"]
    assert record["familywise_mde"] > 0.0
    assert record["below_familywise_mde"] == (record["familywise_mde"] > 0.01)


def test_directional_metric_is_session_balanced(directional) -> None:  # type: ignore[no-untyped-def]
    score = np.array([1.0, -1.0] * 4)
    response = np.array([0.2, -0.1] * 4)
    sessions = np.repeat(np.arange(4, dtype=np.int64), 2)

    record = directional.directional_metric(
        score,
        response,
        sessions,
        family_size=68,
        evaluation_mask_sha256="b" * 64,
    )

    assert record["sign_accuracy"] == pytest.approx(1.0)
    assert record["balanced_accuracy"] == pytest.approx(1.0)
    assert record["theta"] == pytest.approx(0.5)
    assert record["sessions"] == 4
    assert record["evaluation_mask_sha256"] == "b" * 64
