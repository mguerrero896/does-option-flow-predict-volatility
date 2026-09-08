"""Synthetic gamma contracts; no licensed rows, targets, or fitted models."""

from __future__ import annotations

import ast
import math
import os
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import materialize as rp4
import materialize_gamma as gamma
import materialize_iv as rp4_v2
import numpy as np
import polars as pl
import pytest
import rp2_block6_flow_panel as flow
from polars.testing import assert_frame_equal

from mds650.rp2.bars import build_session_grid
from mds650.rp2.option_clock import expiry_close_timestamps, time_to_expiry_years

SESSION = "2026-06-09"


def trade(index: int, minute: float, **changes: Any) -> dict[str, Any]:
    stamp = rp4.origin_timestamp(SESSION, 0) + timedelta(minutes=minute)
    result = {
        "id": str(index),
        "underlying_symbol": "AAPL",
        "created_at": stamp,
        "executed_at": stamp,
        "implied_volatility": 0.3,
        "size": 10.0,
        "expiry": date(2026, 6, 12),
        "strike": 100.0,
        "option_type": "call",
        "nbbo_bid": 1.0,
        "nbbo_ask": 2.0,
        "tags": "ask_side",
        "multi_vol": 0.0,
    }
    result.update(changes)
    return result


def derive(rows: list[dict[str, Any]], origins: list[int], **kwargs: Any) -> pl.DataFrame:
    frame = pl.DataFrame(rows) if rows else pl.DataFrame([trade(0, 0)]).head(0)
    closes = kwargs.pop("closes", np.full(390, 100.0))
    opens = kwargs.pop("opens", np.full(390, 100.0))
    return gamma.derive_session(
        frame,
        "AAPL",
        SESSION,
        np.array(origins, dtype=np.int64),
        closes,
        opens,
        0.043,
        0.91,
        **kwargs,
    )[0]


def test_vector_gamma_agrees_with_independent_scalar_contract() -> None:
    spots = np.array([90.0, 100.0, 120.0, np.nan])
    strikes = np.array([100.0, 100.0, 105.0, 100.0])
    tenors = np.array([0.2, 0.01, 0.001, 0.1])
    ivs = np.array([0.5, 0.03, 3.0, 0.2])
    actual = gamma.vector_gamma(spots, strikes, tenors, ivs, 0.043, 0.91)
    expected = np.array(
        [
            rp4.gamma_with_carry(
                float(s), np.array([k]), np.array([t]), np.array([iv]), 0.043, 0.91 / s
            )[0]
            for s, k, t, iv in zip(spots, strikes, tenors, ivs, strict=True)
        ]
    )
    np.testing.assert_allclose(actual, expected, rtol=1e-14, atol=0, equal_nan=True)
    zero_carry = gamma.vector_gamma(spots, strikes, tenors, ivs, 0.0, 0.0)
    assert not np.allclose(actual[:3], zero_carry[:3])


def test_count_is_unsigned_number_of_signed_trades_and_put_buy_is_positive() -> None:
    rows = [
        trade(1, 1),
        trade(2, 1, tags="bid_side"),
        trade(3, 1, option_type="put", tags="ask_side"),
        trade(4, 1, tags="mid_side"),
    ]
    result = derive(rows, [5])
    one_buy = derive([rows[0]], [5])
    assert result[gamma.FEATURES[3]][0] == 3
    assert result[gamma.FEATURES[0]][0] > 0
    np.testing.assert_allclose(result[gamma.FEATURES[0]], one_buy[gamma.FEATURES[0]])


def test_iv_bounds_inclusive_and_removed_rows_cannot_enter_multileg_history() -> None:
    rows = [
        trade(1, 1, implied_volatility=0.03),
        trade(2, 2, implied_volatility=3.0),
        trade(3, 3, implied_volatility=0.029),
        trade(4, 4, implied_volatility=3.01),
        trade(5, 4, implied_volatility=float("nan")),
    ]
    result = derive(rows, [10])
    assert result[gamma.FEATURES[3]][0] == 2
    retained = derive(rows[:2], [10])
    assert_frame_equal(result, retained, check_exact=True)
    legacy = derive(rows, [10], iv_bounds=gamma.IV_LEGACY, causal=False)
    assert legacy[gamma.FEATURES[3]][0] == 4
    original = [
        trade(1, 1, implied_volatility=4.0, multi_vol=200),
        trade(2, 2, multi_vol=100),
        trade(3, 3, multi_vol=120),
    ]
    changed = [{**original[0], "multi_vol": 0}, *original[1:]]
    assert_frame_equal(derive(original, [6]), derive(changed, [6]), check_exact=True)


def test_empty_prefix_is_nan_and_unsigned_visible_prefix_is_zero() -> None:
    future = [trade(1, 10)]
    assert derive(future, [5])[gamma.FEATURES].to_numpy().size == 4
    assert np.isnan(derive(future, [5])[gamma.FEATURES].to_numpy()).all()
    assert np.isnan(derive([], [5])[gamma.FEATURES].to_numpy()).all()
    assert np.array_equal(
        derive([trade(1, 1, tags="mid_side")], [5])[gamma.FEATURES], np.zeros((1, 4))
    )
    legacy = derive(future, [5], causal=False)
    np.testing.assert_array_equal(legacy[gamma.FEATURES], np.zeros((1, 4)))


def test_future_print_mutation_cannot_change_visible_prefix_or_multileg_direction() -> None:
    early = trade(1, 2, multi_vol=10)
    future = trade(2, 6, created_at=rp4.origin_timestamp(SESSION, 1), multi_vol=20)
    changed = {
        **future,
        "size": 900.0,
        "multi_vol": 0.0,
        "implied_volatility": 2.9,
        "tags": "bid_side",
    }
    base = derive([future, early], [5])
    assert base[gamma.FEATURES[3]][0] == 1
    assert_frame_equal(base, derive([changed, early], [5]), check_exact=True)
    assert_frame_equal(base, derive([early], [5]), check_exact=True)
    late_created = trade(3, 1, created_at=rp4.origin_timestamp(SESSION, 9))
    assert_frame_equal(base, derive([early, late_created], [5]), check_exact=True)


def test_exact_cutoff_and_prior_minute_bar_mark_are_causal() -> None:
    at_cutoff = trade(1, 3)
    after_cutoff = trade(2, 3 + 1 / 60)
    result = derive([at_cutoff, after_cutoff], [5])
    assert result[gamma.FEATURES[3]][0] == 1
    closes = np.full(390, 100.0)
    closes[3:] = 150.0
    assert_frame_equal(
        result, derive([at_cutoff, after_cutoff], [5], closes=closes), check_exact=True
    )
    first = [trade(0, 0.5)]
    opens = np.full(390, 110.0)
    opening_mark = derive(first, [4], opens=opens)
    closes[:] = 1000.0
    assert_frame_equal(
        opening_mark, derive(first, [4], opens=opens, closes=closes), check_exact=True
    )


def test_near_spot_dte_and_multileg_boundaries() -> None:
    rows = [
        trade(1, 1, expiry=date(2026, 6, 16), strike=105.0),
        trade(2, 1, expiry=date(2026, 6, 17), strike=105.0),
        trade(3, 1, expiry=date(2026, 9, 7), strike=100.0),
        trade(4, 1, expiry=date(2026, 9, 8), strike=100.0),
    ]
    result = derive(rows, [5])
    assert result[gamma.FEATURES[3]][0] == 3
    first = derive(rows[:1], [5])
    np.testing.assert_allclose(result[gamma.FEATURES[2]], first[gamma.FEATURES[2]])
    assert result[gamma.FEATURES[1]][0] > result[gamma.FEATURES[2]][0] > 0
    multileg = derive([trade(1, 1, multi_vol=1), trade(2, 2, multi_vol=11)], [5])
    assert multileg[gamma.FEATURES[3]][0] == 1


def test_dedup_rejects_side_or_clock_conflict_and_append_preserves_all_originals() -> None:
    row = trade(1, 1)
    original = pl.DataFrame([row, row])
    assert gamma.deduplicate_tape(original).height == 1
    for changed in (
        {**row, "tags": "bid_side"},
        {**row, "multi_vol": 2.0},
        {**row, "executed_at": rp4.origin_timestamp(SESSION, 2)},
    ):
        with pytest.raises(ValueError, match="ID_CONFLICT"):
            gamma.deduplicate_tape(pl.DataFrame([row, changed]))
    features = derive([row], [5, 10])
    base = (
        features.select(gamma.KEYS)
        .reverse()
        .with_columns(
            rv30=pl.Series([np.nan, 0.3]),
            quality=pl.Series([True, False]),
        )
    )
    result = gamma.append_features(base, features)
    assert_frame_equal(result.select(base.columns), base, check_exact=True)
    with pytest.raises(AssertionError):
        gamma.append_features(base, features.head(1))


def test_first_available_version_is_immutable_and_ambiguous_direction_is_zero() -> None:
    a = trade(1, 1)
    raw = pl.DataFrame([a, {**a, "tags": "bid_side"}, trade(2, 2), trade(2, 2)])
    clean, counts = gamma.sanitize_tape(raw)
    assert counts["conflicting_ids_audit_only"] == 1
    assert counts["first_available_tie_conflicts_audit_only"] == 1
    assert counts["exact_duplicate_rows_removed"] == 1
    assert counts["selected_rows"] == 2
    assert clean["id"].to_list() == ["1", "2"]
    assert clean["tags"][0] == "ask_side"
    both = [trade(1, 1, tags="ask_side,bid_side")]
    np.testing.assert_array_equal(derive(both, [5])[gamma.FEATURES], np.zeros((1, 4)))
    assert derive(both, [5], causal=False)[gamma.FEATURES[3]][0] == 1


def test_future_conflicting_duplicate_never_deletes_or_updates_past_feature() -> None:
    first = trade(1, 1)
    future = trade(1, 10, tags="bid_side", multi_vol=100, size=900.0)
    baseline = derive([first, trade(2, 2)], [5])
    # Reverse source order is intentional: production uses first availability, not
    # whatever revision happened to be stored first in the historical file.
    augmented = derive([future, first, trade(2, 2)], [5])
    assert_frame_equal(baseline, augmented, check_exact=True)
    changed = {**future, "implied_volatility": 2.9, "strike": 110.0}
    assert_frame_equal(baseline, derive([first, trade(2, 2), changed], [5]), check_exact=True)
    baseline_later = derive([first, trade(2, 2)], [20])
    assert_frame_equal(baseline_later, derive([future, first, trade(2, 2)], [20]), check_exact=True)


def _synthetic_bars() -> pl.DataFrame:
    returns = np.full(389, 0.0001)
    returns[44] = 0.04
    close = 100 * np.exp(np.r_[0, np.cumsum(returns)])
    return pl.DataFrame(
        {
            "asset": ["AAPL"] * 390,
            "session_date": [SESSION] * 390,
            "minute": np.arange(390),
            "close": close,
            "open": close,
        }
    )


def test_jump_uses_original_strict_31_observed_bar_mask_and_does_not_replace_rv() -> None:
    bars = _synthetic_bars().filter(pl.col("minute") != 30)
    grid = build_session_grid(bars, session=date.fromisoformat(SESSION))
    keys = derive([trade(1, 1)], [10, 31, 60, 365]).select(gamma.KEYS)
    target, counters = gamma.reconstruct_jump(bars, keys, grid)
    old_rv, old_counters = rp4.reconstruct_rv30(bars, keys)
    assert counters == old_counters
    assert counters["unobserved_target_bar_keys"] == 1
    assert np.isnan(target["jump30"][0])
    assert target["jump30"][1] > 0
    assert np.isnan(target["jump30"][-1])
    joined = target.join(old_rv, on=gamma.KEYS, how="inner", validate="1:1")
    np.testing.assert_array_equal(joined["rv30"], joined["rv30_reconstructed"])
    feature = derive([trade(1, 1)], [10, 31, 60, 365]).join(
        target.select(gamma.KEYS + ["jump30"]), on=gamma.KEYS, validate="1:1"
    )
    base = keys.with_columns(rv30=pl.lit(0.789))
    appended = gamma.append_features(base, feature)
    np.testing.assert_array_equal(appended["rv30"], base["rv30"])
    assert np.isnan(appended["jump30"][0])
    unavailable, missing_counts = gamma.reconstruct_jump(None, keys, None)
    assert missing_counts["missing_bar_keys"] == keys.height
    assert np.isnan(unavailable["jump30"].to_numpy()).all()


def _synthetic_loader(pins: dict[str, Any]) -> dict[tuple[str, str], Any]:
    return {
        ("AAPL", SESSION): build_session_grid(pins["frame"], session=date.fromisoformat(SESSION))
    }


def test_grid_capture_changes_only_return_value_not_loader_or_global(monkeypatch: Any) -> None:
    monkeypatch.setattr(rp4_v2, "load_price_grids", _synthetic_loader)
    bars = _synthetic_bars()
    expected = _synthetic_loader({"frame": bars})["AAPL", SESSION]
    actual, observed = gamma.paired_price_grids({"frame": bars})["AAPL", SESSION]
    np.testing.assert_array_equal(actual.close, expected.close)
    np.testing.assert_array_equal(actual.open, expected.open)
    assert_frame_equal(observed, bars.select("asset", "session_date", "minute", "close"))
    assert _synthetic_loader.__globals__["build_session_grid"] is build_session_grid


def test_synthetic_session_pipeline_and_idempotent_checkpoint(
    tmp_path: Path, monkeypatch: Any
) -> None:
    raw_path = tmp_path / "tape.parquet"
    pl.DataFrame([trade(1, 1), trade(2, 2, implied_volatility=4.0)]).write_parquet(raw_path)
    bars = _synthetic_bars()
    grid = build_session_grid(bars, session=date.fromisoformat(SESSION))
    base = (
        derive([trade(1, 1)], [35, 40])
        .select(gamma.KEYS)
        .with_columns(
            rate=pl.lit(0.043),
            dividend_cash_prior365=pl.lit(0.91),
            rv30=pl.lit(0.001),
        )
    )
    source = {
        "indexed_paths": [str(raw_path)],
        "source_sha256": {str(raw_path): rp4.sha256(raw_path)},
        "used_all_fallback": False,
    }
    receipt = gamma.materialize_session(base, source, grid, bars, tmp_path / "out", "synthetic")
    assert receipt["origins"] == 2
    shard_path = tmp_path / "out/sessions" / f"{SESSION}_AAPL.parquet"
    shard = pl.read_parquet(shard_path)
    assert shard[gamma.FEATURES[3]].to_list() == [1.0, 1.0]
    assert shard[gamma.LEGACY_NAMES[gamma.FEATURES[3]]].to_list() == [2.0, 2.0]
    appended = gamma.append_features(base, shard.select(gamma.KEYS + gamma.FEATURES + ["jump30"]))
    assert_frame_equal(appended.select(base.columns), base, check_exact=True)

    def forbidden_read(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("Completed checkpoint must not re-read tape or reconstruct values")

    monkeypatch.setattr(pl, "read_parquet", forbidden_read)
    assert (
        gamma.materialize_session(base, source, grid, bars, tmp_path / "out", "synthetic")
        == receipt
    )
    with pytest.raises(ValueError, match="IDENTITY_CHANGED"):
        gamma.materialize_session(base, source, grid, bars, tmp_path / "out", "changed")


def test_comparison_aligns_keys_and_separates_missingness_from_numeric_difference() -> None:
    original = derive([trade(1, 10)], [5, 15])
    changed = original.reverse().with_columns(pl.col(gamma.FEATURES[0]) + 2.0)
    rows = gamma.compare_panels(original, changed, "synthetic", "known two-unit perturbation")
    total = next(
        row for row in rows if row["asset"] == "ALL" and row["column"] == gamma.FEATURES[0]
    )
    assert total["both_nonfinite"] == 1
    assert total["finite_pairs"] == 1
    assert total["maximum_absolute_difference"] == 2.0
    with pytest.raises(AssertionError):
        gamma.compare_panels(original, changed.head(1), "invalid", "missing key")


def test_legacy_bridge_against_pinned_candidate_functions_on_synthetic_rows() -> None:
    candidate_path = os.environ.get("RP4_GAMMA_CANDIDATE_SOURCE")
    if not candidate_path:
        pytest.skip("Private candidate source required only for this local oracle check")
    assert candidate_path is not None
    path = Path(candidate_path)
    assert rp4.sha256(path) == "ddd4cc94c75f8df3b8a0e657d8aca93ff850b44019fa3d77eca79f20bca4b885"
    parsed = ast.parse(path.read_text(encoding="utf-8"))
    selected: list[ast.stmt] = [
        node
        for node in parsed.body
        if isinstance(node, ast.FunctionDef)
        and node.name in {"gamma_with_carry_vec", "session_gamma_imbalance"}
    ]
    assert len(selected) == 2
    namespace: dict[str, Any] = {
        "np": np,
        "pl": pl,
        "math": math,
        "mz": rp4,
        "Any": Any,
        "_multileg_size": flow._multileg_size,
        "mark_price": flow.mark_price,
        "expiry_close_timestamps": expiry_close_timestamps,
        "time_to_expiry_years": time_to_expiry_years,
        "FEATURES": gamma.FEATURES,
        "NEAR_SPOT": 0.05,
        "MAX_DTE": 90,
        "SHORT_DTE": 7,
        "CUTOFF_US": 120_000_000,
    }
    # Only the two inspected pure functions; no module imports/path changes/main/I/O.
    exec(compile(ast.Module(body=selected, type_ignores=[]), str(path), "exec"), namespace)
    rows = [
        trade(1, -1, multi_vol=10),
        trade(2, 1, multi_vol=11),
        trade(3, 2, multi_vol=20, tags="ask_side,bid_side"),
        trade(4, 3, multi_vol=None, implied_volatility=4.0),
        trade(5, 10, tags="bid_side", strike=107.0),
    ]
    raw = pl.DataFrame(rows)
    expected = namespace["session_gamma_imbalance"](
        raw,
        "AAPL",
        SESSION,
        np.array([1, 5, 15]),
        np.full(390, 100.0),
        np.full(390, 100.0),
        0.043,
        0.91,
    )
    actual = derive(rows, [1, 5, 15], iv_bounds=gamma.IV_LEGACY, causal=False)
    assert_frame_equal(actual, expected, check_exact=False, rel_tol=1e-10, abs_tol=1e-8)
