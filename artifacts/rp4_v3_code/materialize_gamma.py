"""Independent RP4 v3 signed gamma derivation, written before candidate-code inspection.

Definition, fixed from the owner's requested quantities and existing RP4 bar contract:

For trade i, S_i is the previous executed-minute close, or the session opening print
for minute zero. T_i is time from execution to expiry's exchange-calendar close in
365.25-day years, q_i = prior-365-day cash dividends / S_i, and r is the pinned session
carry. Gamma_i = exp(-q_i*T_i - d1_i**2/2)/(sqrt(2*pi)*S_i*IV_i*sqrt(T_i)).
The signed dollar-gamma flow is direction_i * size_i * 100 * Gamma_i * S_i**2.
It is a trade-initiation proxy, not observed customer identity or dealer inventory.

Production prefixes require BOTH created_at and executed_at <= origin minus 120s.
Sorting by max(the two observed clocks) is only an implementation of that intersection,
not a fabricated provider timestamp. It also prevents an unavailable print from altering
the preceding-print multileg detector. Ties retain pinned source order. Empty available
valid prefixes are NaN; valid but unsigned prefixes are zero. The fourth feature is the
RAW COUNT of finite-exposure trades with nonzero direction, not a sum of directions.

Independent legacy and IV-only bridges are audit outputs, never model inputs: created_at
only, creation-order multileg history, and full-day-universe missingness. Their separation
identifies IV-rule changes versus dual-clock/prefix-causal changes without changing data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from types import FunctionType
from typing import Any

import materialize as rp4
import materialize_iv as rp4_v2
import numpy as np
import numpy.typing as npt
import polars as pl
from polars.testing import assert_frame_equal
from rp2_block6_flow_panel import _multileg_size, mark_price

from mds650.rp2.bars import SessionGrid, build_session_grid
from mds650.rp2.option_clock import expiry_close_timestamps

KEYS = ["asset", "session_date", "origin_minute"]
FEATURES = [
    "rp4_gamma_imb_total",
    "rp4_gamma_imb_near_spot",
    "rp4_gamma_imb_near_short",
    "rp4_gamma_imb_signed_trades",
]
TAPE_COLUMNS = [
    "id",
    "underlying_symbol",
    "created_at",
    "executed_at",
    "implied_volatility",
    "size",
    "expiry",
    "strike",
    "option_type",
    "nbbo_bid",
    "nbbo_ask",
    "tags",
    "multi_vol",
]
SECONDS_PER_YEAR = 365.25 * 24 * 3600
IV_CLEAN = (0.03, 3.0)
IV_LEGACY = (0.01, 5.0)
NEAR_TOLERANCE = 1e-12
INITIAL_DERIVATION_SHA = "73e0a5f3eb6efa4bb20de8c13eb69bb88e9fed38001336d65e1df282d91c2155"
CANDIDATE_CODE_SHA = "ddd4cc94c75f8df3b8a0e657d8aca93ff850b44019fa3d77eca79f20bca4b885"
type FloatArray = npt.NDArray[np.float64]
type IntArray = npt.NDArray[np.int64]
ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = Path("private-input/e63a7488cbab65e3773b")
V2_ROOT = Path("private-input/f519340aa87e8330d56d")
CANDIDATE_ROOT = Path("private-input/30dc476bac34db1890c8")
CANDIDATE = CANDIDATE_ROOT / "gamma_imbalance_2024-08-02_2026-09-04.parquet"
SOURCE_PINS = {
    str(V2_ROOT / "panel.parquet"): (
        "5b7dd5cc4b2b1e64446d305a5ee0de92f6d18e790f94b5840664947da00fd19d"
    ),
    str(V2_ROOT / "manifest.json"): (
        "ba409cf18bb38c4025e602a68177d01a1197229881d0de442bbc6355d220d807"
    ),
    str(V2_ROOT / "input_pins.json"): (
        "9403b1d8f6ec03f14dad0de43fc01567585ccb1c523f2c9507dcd708c52a034b"
    ),
    str(CANDIDATE): "edc0263c8d8a76c897fc6d8e54462fd3ffb8f3aa475eb7ee4b55551b4a7fdfcc",
    str(CANDIDATE_ROOT / "manifest.json"): (
        "8619bfd4191e80d14e7c025dc7f3358d9d0f881eb65f55a341fc16bddaae645d"
    ),
}
CODE_PATHS = [
    "artifacts/rp4_v3_code/materialize_gamma.py",
    "artifacts/rp4_v2_code/materialize_iv.py",
    "artifacts/rp4_code/materialize.py",
    "scripts/rp2_block5_surface_panel.py",
    "scripts/rp2_block6_flow_panel.py",
    "src/mds650/rp2/bars.py",
    "src/mds650/rp2/option_clock.py",
    "src/mds650/rp2/realized.py",
    "uv.lock",
]
LEGACY_NAMES = {name: f"legacy__{name}" for name in FEATURES}
IV_ONLY_NAMES = {name: f"iv_only__{name}" for name in FEATURES}


def deduplicate_tape(tape: pl.DataFrame) -> pl.DataFrame:
    """Deduplicate exact IDs only; never hide conflicts in clocks or trade direction."""
    tape = tape.select(TAPE_COLUMNS)
    if tape["id"].null_count():
        raise ValueError("RP4_V3_GAMMA_ID_NULL")
    duplicate = tape.filter(pl.col("id").is_duplicated())
    if duplicate.height and duplicate.unique().height != duplicate["id"].n_unique():
        raise ValueError("RP4_V3_GAMMA_ID_CONFLICT")
    return tape.unique(subset="id", keep="first", maintain_order=True)


def sanitize_tape(
    tape: pl.DataFrame,
    *,
    causal: bool = True,
) -> tuple[pl.DataFrame, dict[str, int]]:
    """Immutable first available version; future contradictions are audit-only.

    The legacy bridge keeps the first source-order version, as the candidate reader did.
    No full-day conflict flag changes the selected production row or its eligibility.
    """
    tape = tape.select(TAPE_COLUMNS)
    if tape["id"].null_count():
        raise ValueError("RP4_V3_GAMMA_ID_NULL")
    distinct = tape.unique(maintain_order=True)
    conflicts = distinct.group_by("id").len().filter(pl.col("len") > 1).height
    unorderable = distinct.filter(
        pl.col("created_at").is_null() | pl.col("executed_at").is_null()
    ).height
    tie_conflicts = 0
    ordered = distinct
    if causal:
        ordered = (
            distinct.filter(
                pl.col("created_at").is_not_null() & pl.col("executed_at").is_not_null()
            )
            .with_columns(
                pl.max_horizontal(
                    pl.col("created_at").cast(pl.Datetime("us", "UTC")).cast(pl.Int64),
                    pl.col("executed_at").cast(pl.Datetime("us", "UTC")).cast(pl.Int64),
                ).alias("__both_clock")
            )
            .sort("__both_clock", maintain_order=True)
        )
        first = ordered.group_by("id").agg(pl.col("__both_clock").min().alias("__first"))
        initial = ordered.join(first, on="id", validate="m:1").filter(
            pl.col("__both_clock") == pl.col("__first")
        )
        tie_conflicts = initial.group_by("id").len().filter(pl.col("len") > 1).height
    selected = ordered.unique(subset="id", keep="first", maintain_order=True).select(TAPE_COLUMNS)
    return selected, {
        "raw_rows": tape.height,
        "conflicting_ids_audit_only": conflicts,
        "later_distinct_versions_ignored": ordered.height - selected.height,
        "first_available_tie_conflicts_audit_only": tie_conflicts,
        "unorderable_clock_rows": unorderable,
        "exact_duplicate_rows_removed": tape.height - distinct.height,
        "selected_rows": selected.height,
    }


def legacy_directions(tape: pl.DataFrame) -> FloatArray:
    """Audit-only candidate history universe, before grid/DTE/numeric eligibility.

    This ordering was discovered by reading the candidate AFTER the independent core
    was written. It is never reused for production's availability-safe history.
    """
    expiry = tape["expiry"].cast(pl.Date).to_numpy().astype("datetime64[D]").astype(np.int64)
    strike = tape["strike"].cast(pl.Float64).to_numpy()
    calls = (tape["option_type"] == "call").to_numpy()
    keys = (
        expiry * 20_000_000 + np.round(strike * 1000).astype(np.int64) * 2 + calls.astype(np.int64)
    )
    tags = tape["tags"].cast(pl.Utf8).fill_null("")
    ask = tags.str.contains("ask_side", literal=True).to_numpy()
    bid = tags.str.contains("bid_side", literal=True).to_numpy()
    size = tape["size"].cast(pl.Float64).to_numpy()
    multi = tape["multi_vol"].cast(pl.Float64).fill_null(0.0).to_numpy()
    amounts = _multileg_size(keys, multi, size)
    return np.where(amounts > 0, 0.0, np.where(ask, 1.0, np.where(bid, -1.0, 0.0)))


def vector_gamma(
    spot: FloatArray,
    strike: FloatArray,
    tenor: FloatArray,
    iv: FloatArray,
    rate: float,
    dividend_cash: float,
) -> FloatArray:
    """Array derivation of the same cash-carry Black-Scholes gamma used by RP4."""
    if not (spot.shape == strike.shape == tenor.shape == iv.shape):
        raise ValueError("RP4_V3_GAMMA_SHAPE")
    result = np.full(spot.shape, np.nan, dtype=np.float64)
    valid = (
        np.isfinite(spot)
        & (spot > 0)
        & np.isfinite(strike)
        & (strike > 0)
        & np.isfinite(tenor)
        & (tenor > 0)
        & np.isfinite(iv)
        & (iv > 0)
    )
    if not (math.isfinite(rate) and math.isfinite(dividend_cash)):
        return result
    s, k, t, sigma = spot[valid], strike[valid], tenor[valid], iv[valid]
    with np.errstate(over="ignore", under="ignore", invalid="ignore", divide="ignore"):
        q = dividend_cash / s
        denominator = sigma * np.sqrt(t)
        d1 = (np.log(s / k) + (rate - q + 0.5 * sigma**2) * t) / denominator
        result[valid] = np.exp(-q * t - 0.5 * d1**2) / (math.sqrt(2 * math.pi) * s * denominator)
    return result


def base_eligible(tape: pl.DataFrame, asset: str, bounds: tuple[float, float]) -> pl.DataFrame:
    """The build_new_option_features conditions, with the explicitly selected IV range."""
    return tape.filter(
        (pl.col("underlying_symbol") == asset)
        & pl.col("implied_volatility").is_finite()
        & pl.col("implied_volatility").is_between(*bounds, closed="both")
        & (pl.col("nbbo_bid") > 0)
        & (pl.col("nbbo_ask") > pl.col("nbbo_bid"))
        & (pl.col("strike") > 0)
        & (pl.col("size") > 0)
        & pl.col("option_type").is_in(["call", "put"])
        & pl.col("created_at").is_not_null()
        & pl.col("executed_at").is_not_null()
        & pl.col("expiry").is_not_null()
    )


def _frame(asset: str, session: str, origins: IntArray, values: FloatArray) -> pl.DataFrame:
    result: dict[str, Any] = {
        "asset": [asset] * origins.size,
        "session_date": [session] * origins.size,
        "origin_minute": origins,
    }
    result.update({name: values[:, index] for index, name in enumerate(FEATURES)})
    return pl.DataFrame(result)


def derive_session(
    tape: pl.DataFrame,
    asset: str,
    session: str,
    origins: IntArray,
    closes: FloatArray,
    opens: FloatArray,
    rate: float,
    dividend_cash: float,
    *,
    iv_bounds: tuple[float, float] = IV_CLEAN,
    causal: bool = True,
    versions_selected: bool = False,
) -> tuple[pl.DataFrame, dict[str, int]]:
    """Build four prefixes without looking at RV30, jump30, or any model result."""
    if origins.ndim != 1 or closes.ndim != 1 or opens.shape != closes.shape:
        raise ValueError("RP4_V3_GAMMA_GRID_SHAPE")
    if np.any(origins < 0) or np.any(origins >= closes.size):
        raise ValueError("RP4_V3_GAMMA_ORIGIN_OUTSIDE_GRID")
    tape = tape.filter(pl.col("underlying_symbol") == asset)
    if not versions_selected:
        tape, _ = sanitize_tape(tape, causal=causal)
    elif tape["id"].n_unique() != tape.height:
        raise ValueError("RP4_V3_SELECTED_VERSION_IDS_NOT_UNIQUE")
    tape = base_eligible(tape, asset, iv_bounds)
    if not causal and tape.height:
        tape = tape.sort("created_at")
        tape = tape.with_columns(pl.Series("__legacy_direction", legacy_directions(tape)))
    diagnostics = {"base_valid_rows": tape.height}
    empty = np.full((origins.size, len(FEATURES)), np.nan, dtype=np.float64)
    if tape.height == 0:
        diagnostics.update(
            calendar_valid_rows=0,
            numeric_valid_rows=0,
            created_before_executed_rows=0,
            nonfinite_multivol_rows=0,
            ambiguous_side_rows=0,
            signed_rows=0,
        )
        return _frame(asset, session, origins, empty), diagnostics
    created = tape["created_at"].cast(pl.Datetime("us", "UTC")).cast(pl.Int64).to_numpy()
    executed = tape["executed_at"].cast(pl.Datetime("us", "UTC")).cast(pl.Int64).to_numpy()
    session_open = int(rp4.origin_timestamp(session, 0).timestamp() * 1_000_000)
    minute = ((executed - session_open) // 60_000_000).astype(np.int64)
    expiry = tape["expiry"].cast(pl.Date).to_numpy()
    dte = (expiry - np.datetime64(session, "D")).astype("timedelta64[D]").astype(np.int64)
    calendar_valid = (minute >= 0) & (minute < closes.size) & (dte >= 0) & (dte <= 90)
    tape = tape.filter(pl.Series(calendar_valid))
    created, executed, minute, expiry, dte = (
        value[calendar_valid] for value in (created, executed, minute, expiry, dte)
    )
    diagnostics["calendar_valid_rows"] = tape.height
    diagnostics["created_before_executed_rows"] = int(np.sum(created < executed))
    if tape.height == 0:
        diagnostics.update(
            numeric_valid_rows=0, nonfinite_multivol_rows=0, ambiguous_side_rows=0, signed_rows=0
        )
        return _frame(asset, session, origins, empty), diagnostics
    spot = mark_price(minute, closes, opens)
    expiry_us = expiry_close_timestamps(expiry, "America/New_York")
    tenor = (expiry_us - executed) / 1_000_000 / SECONDS_PER_YEAR
    strike = tape["strike"].cast(pl.Float64).to_numpy()
    iv = tape["implied_volatility"].cast(pl.Float64).to_numpy()
    size = tape["size"].cast(pl.Float64).to_numpy()
    gamma = vector_gamma(spot, strike, tenor, iv, rate, dividend_cash)
    with np.errstate(over="ignore", invalid="ignore"):
        unsigned = size * 100.0 * gamma * spot**2
    numeric_valid = np.isfinite(unsigned) & np.isfinite(spot) & (spot > 0)
    tape = tape.filter(pl.Series(numeric_valid))
    created, executed, expiry, dte, strike, spot, size, unsigned = (
        value[numeric_valid]
        for value in (created, executed, expiry, dte, strike, spot, size, unsigned)
    )
    diagnostics["numeric_valid_rows"] = tape.height
    if tape.height == 0:
        diagnostics.update(nonfinite_multivol_rows=0, ambiguous_side_rows=0, signed_rows=0)
        return _frame(asset, session, origins, empty), diagnostics

    # A preceding print is itself required to have been available: no future-print
    # history can reclassify the multileg status of a visible trade.
    visible_clock = np.maximum(created, executed) if causal else created
    order = np.argsort(visible_clock, kind="stable")
    visible_clock, expiry, dte, strike, spot, size, unsigned = (
        value[order] for value in (visible_clock, expiry, dte, strike, spot, size, unsigned)
    )
    tags = tape["tags"].cast(pl.Utf8).fill_null("")
    ask = tags.str.contains("ask_side", literal=True).to_numpy()[order]
    bid = tags.str.contains("bid_side", literal=True).to_numpy()[order]
    calls = (tape["option_type"] == "call").to_numpy()[order]
    multi = tape["multi_vol"].cast(pl.Float64).to_numpy()[order]
    diagnostics["nonfinite_multivol_rows"] = int(np.sum(~np.isfinite(multi)))
    diagnostics["ambiguous_side_rows"] = int(np.sum(ask & bid))
    contract = np.rec.fromarrays([expiry.astype(np.int64), strike, calls])
    _, contract_ids = np.unique(contract, return_inverse=True)
    multi_size = _multileg_size(contract_ids.astype(np.int64), multi, size)
    if causal:
        direction = np.where(ask, 1.0, np.where(bid, -1.0, 0.0))
        direction = np.where(ask & bid, 0.0, direction)
        direction = np.where(multi_size > 0, 0.0, direction)
    else:
        direction = tape["__legacy_direction"].to_numpy()[order]
    signed = unsigned * direction
    near = np.abs(strike / spot - 1.0) <= 0.05 + NEAR_TOLERANCE
    increments = np.column_stack(
        (
            signed,
            np.where(near, signed, 0.0),
            np.where(near & (dte <= 7), signed, 0.0),
            (direction != 0).astype(np.float64),
        )
    )
    diagnostics["signed_rows"] = int(np.count_nonzero(direction))
    prefixes = np.vstack((np.zeros((1, len(FEATURES))), np.cumsum(increments, axis=0)))
    cutoffs = session_open + origins * 60_000_000 - 120_000_000
    positions = np.searchsorted(visible_clock, cutoffs, side="right")
    values = prefixes[positions]
    if causal:
        values[positions == 0] = np.nan
    return _frame(asset, session, origins, values), diagnostics


def append_features(base: pl.DataFrame, features: pl.DataFrame) -> pl.DataFrame:
    """One-to-one keyed append; all original values and dtypes remain exact."""
    rp4.assert_unique(base)
    rp4.assert_unique(features)
    if set(FEATURES) & set(base.columns):
        raise ValueError("RP4_V3_GAMMA_COLUMNS_ALREADY_PRESENT")
    assert_frame_equal(
        base.select(KEYS).sort(KEYS), features.select(KEYS).sort(KEYS), check_exact=True
    )
    result = base.join(features, on=KEYS, how="left", validate="1:1")
    assert_frame_equal(result.select(base.columns).sort(KEYS), base.sort(KEYS), check_exact=True)
    return result


def grid_and_observed_bars(
    group: pl.DataFrame,
    *,
    session: Any = None,
) -> tuple[SessionGrid, pl.DataFrame]:
    """Retain the observed bars needed for the exact strict 31-close target mask."""
    return build_session_grid(group, session=session), group.select(
        "asset", "session_date", "minute", "close"
    )


def paired_price_grids(pins: dict[str, str]) -> dict[tuple[str, str], Any]:
    """Execute the immutable v2 loader with only its returned grid enriched by raw bars.

    Private function globals prevent a process-global patch. Loading, source priority,
    duplicate checks and fill rules remain the exact code already pinned by RP4 v2.
    """
    namespace = dict(rp4_v2.load_price_grids.__globals__)
    namespace["build_session_grid"] = grid_and_observed_bars
    bound = FunctionType(rp4_v2.load_price_grids.__code__, namespace)
    result: dict[tuple[str, str], Any] = bound(pins)
    return result


def reconstruct_jump(
    observed_bars: pl.DataFrame | None,
    keys: pl.DataFrame,
    grid: SessionGrid | None,
) -> tuple[pl.DataFrame, dict[str, int]]:
    """Reuse the full original RV mask, then select the same producer's jump component."""
    if observed_bars is None or grid is None:
        return keys.with_columns(
            jump30=pl.lit(float("nan")), rv30_reconstructed=pl.lit(float("nan"))
        ), {
            "missing_bar_keys": keys.height,
            "quality_excluded_keys": 0,
            "unobserved_target_bar_keys": 0,
        }
    rebuilt, counters = rp4.reconstruct_rv30(observed_bars, keys)
    present = np.flatnonzero(grid.valid)
    first = int(present[0]) if present.size else grid.minutes
    if rebuilt.height:
        returns = rp4.log_returns(grid.close[first:])
        indices = rebuilt["origin_minute"].to_numpy().astype(np.int64) - first
        measures = rp4.forward_measures(returns, indices, 30)
        np.testing.assert_array_equal(measures.rv, rebuilt["rv30"].to_numpy())
        rebuilt = rebuilt.with_columns(pl.Series("jump30", measures.jump))
    else:
        rebuilt = rebuilt.with_columns(jump30=pl.lit(None, pl.Float64))
    full = keys.join(
        rebuilt.rename({"rv30": "rv30_reconstructed"}), on=KEYS, how="left", validate="1:1"
    )
    return full.with_columns(
        pl.col("jump30").fill_null(float("nan")),
        pl.col("rv30_reconstructed").fill_null(float("nan")),
    ), counters


def comparison_metrics(
    left: FloatArray,
    right: FloatArray,
    *,
    rtol: float = 1e-10,
    atol: float = 1e-8,
) -> dict[str, int | float | None]:
    """Direction is right minus left; report raw equality and numerical tolerance apart."""
    if left.shape != right.shape:
        raise ValueError("RP4_V3_COMPARISON_SHAPE")
    a, b = np.isfinite(left), np.isfinite(right)
    both = a & b
    delta = right[both] - left[both]
    absolute = np.abs(delta)
    close = np.isclose(left[both], right[both], rtol=rtol, atol=atol)
    return {
        "rows": left.size,
        "absolute_tolerance": atol,
        "relative_tolerance": rtol,
        "finite_pairs": int(both.sum()),
        "only_left_finite": int((a & ~b).sum()),
        "only_right_finite": int((~a & b).sum()),
        "both_nonfinite": int((~a & ~b).sum()),
        "nonzero_difference_pairs": int(np.count_nonzero(delta)),
        "outside_tolerance_pairs": int((~close).sum()),
        "maximum_absolute_difference": float(absolute.max()) if absolute.size else None,
        "mean_absolute_difference": float(absolute.mean()) if absolute.size else None,
        "mean_signed_difference": float(delta.mean()) if delta.size else None,
    }


def compare_panels(
    left: pl.DataFrame,
    right: pl.DataFrame,
    comparison: str,
    reason: str,
) -> list[dict[str, Any]]:
    rp4.assert_unique(left)
    rp4.assert_unique(right)
    left, right = left.sort(KEYS), right.sort(KEYS)
    assert_frame_equal(left.select(KEYS), right.select(KEYS), check_exact=True)
    rows = []
    assets = [None, *sorted(left["asset"].unique().to_list())]
    for asset in assets:
        mask = np.ones(left.height, dtype=bool) if asset is None else (left["asset"] == asset)
        for column in FEATURES:
            a = left.filter(mask)[column].to_numpy()
            b = right.filter(mask)[column].to_numpy()
            rows.append(
                {
                    "comparison": comparison,
                    "reason": reason,
                    "asset": asset or "ALL",
                    "column": column,
                    **comparison_metrics(a, b),
                }
            )
    return rows


def verify_pins(pins: dict[str, str]) -> None:
    for name, digest in pins.items():
        rp4_v2.verify_pin(Path(name), digest)


def input_contract(
    spec_path: Path,
    spec_hash: str,
) -> tuple[dict[str, str], dict[tuple[str, str], dict[str, Any]], str]:
    rp4_v2.verify_pin(spec_path, spec_hash)
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    gamma_contract = spec["gamma_imbalance"]
    expected = {
        "columns": FEATURES,
        "iv_range": list(IV_CLEAN),
        "dte_inclusive": [0, 90],
        "cutoff": "created_at_and_executed_at_le_origin_minus_120s",
        "history_order": "max_created_executed_then_stable_source_order",
        "empty_valid_prefix": "NaN",
        "valid_unsigned_prefix": 0,
        "direction": "ask_only_plus_one_bid_only_minus_one_neither_or_both_zero",
        "duplicates": "first_available_version_immutable_later_conflicts_audit_only_stable_ties",
        "year_days": 365.25,
        "near_spot_fraction": 0.05,
        "near_spot_tolerance": 1e-12,
        "short_dte_maximum": 7,
        "contract_multiplier": 100,
        "comparison_atol": 1e-8,
        "comparison_rtol": 1e-10,
        "fourth_column": "raw_count_of_finite_exposure_nonzero_direction_trades",
    }
    if any(gamma_contract.get(key) != value for key, value in expected.items()):
        raise ValueError("RP4_V3_GAMMA_SPECIFICATION_MISMATCH")
    if (
        spec["base_panel"]["sha256"] != SOURCE_PINS[str(V2_ROOT / "panel.parquet")]
        or spec["candidate_gamma"]["sha256"] != SOURCE_PINS[str(CANDIDATE)]
        or spec["jump_target"]["column"] != "jump30"
        or not spec["jump_target"]["compare_rv30_do_not_replace"]
    ):
        raise ValueError("RP4_V3_BASE_CANDIDATE_TARGET_CONTRACT_MISMATCH")
    pins = dict(SOURCE_PINS)
    verify_pins(pins)
    source = json.loads((V2_ROOT / "input_pins.json").read_text(encoding="utf-8"))
    pins.update(source["sha256"])
    receipts, lineage = rp4_v2.load_lineage()
    canonical = {str(Path(path).resolve()): digest for path, digest in pins.items()}
    for name, digest in lineage.items():
        if canonical.get(str(Path(name).resolve())) != digest:
            raise ValueError(f"RP4_V3_V2_SOURCE_PIN_NOT_REPRODUCED:{name}")
    index = rp4.tape_index(rp4_v2.OLD_ROOT)
    for (asset, session), receipt in receipts.items():
        paths = index.get((session, asset)) or index.get((session, "__ALL__"))
        if not paths:
            raise ValueError(f"RP4_V3_TAPE_INDEX_MISSING:{asset}:{session}")
        indexed = {str(Path(path).resolve()) for path in paths}
        original = {str(Path(path).resolve()) for path in receipt["source_sha256"]}
        if indexed != original:
            raise ValueError(f"RP4_V3_TAPE_INDEX_V2_RECEIPT_MISMATCH:{asset}:{session}")
        receipt["indexed_paths"] = list(dict.fromkeys(paths))
        receipt["used_all_fallback"] = (session, asset) not in index
    for relative in CODE_PATHS:
        code = ROOT / relative
        digest = rp4.sha256(code)
        previous = canonical.get(str(code.resolve()))
        if previous is not None and previous != digest:
            raise ValueError(f"RP4_V3_FROZEN_PARENT_CODE_DRIFT:{relative}")
        pins[str(code)] = digest
    pins[str(spec_path.resolve())] = spec_hash
    md_hash = spec.get("specification_md_sha256")
    if md_hash:
        md_path = ROOT / "docs/rp4/specification_v3.md"
        rp4_v2.verify_pin(md_path, md_hash)
        pins[str(md_path)] = md_hash
    verify_pins(pins)
    identity = hashlib.sha256(json.dumps(pins, sort_keys=True).encode()).hexdigest()
    return pins, receipts, identity


def materialize_session(
    base: pl.DataFrame,
    source: dict[str, Any],
    grid: SessionGrid | None,
    observed: pl.DataFrame | None,
    output: Path,
    identity: str,
) -> dict[str, Any]:
    asset, session = str(base["asset"][0]), str(base["session_date"][0])
    shard = output / "sessions" / f"{session}_{asset}.parquet"
    receipt = shard.with_suffix(".json")
    if receipt.exists():
        result: dict[str, Any] = json.loads(receipt.read_text(encoding="utf-8"))
        if result["identity"] != identity:
            raise ValueError("RP4_V3_SHARD_IDENTITY_CHANGED")
        rp4_v2.verify_pin(shard, result["sha256"])
        return result
    raw = pl.concat(
        [
            pl.read_parquet(path, columns=TAPE_COLUMNS).filter(pl.col("underlying_symbol") == asset)
            for path in source["indexed_paths"]
        ],
        how="vertical_relaxed",
    )
    clean, duplicate_counts = sanitize_tape(raw, causal=True)
    legacy_tape, legacy_duplicate_counts = sanitize_tape(raw, causal=False)
    iv_counts = rp4_v2.iv_counts(raw)
    carry = base.select("rate", "dividend_cash_prior365").unique()
    if carry.height != 1:
        raise ValueError("RP4_V3_CARRY_NOT_SESSION_CONSTANT")
    rate, cash = map(float, carry.row(0))
    origins = base["origin_minute"].to_numpy().astype(np.int64)
    if grid is None:
        missing = _frame(asset, session, origins, np.full((origins.size, len(FEATURES)), np.nan))
        legacy = iv_only = production = missing
        missing_counts = dict.fromkeys(
            (
                "base_valid_rows",
                "calendar_valid_rows",
                "numeric_valid_rows",
                "created_before_executed_rows",
                "nonfinite_multivol_rows",
                "ambiguous_side_rows",
                "signed_rows",
            ),
            0,
        )
        legacy_counts = iv_only_counts = production_counts = missing_counts
    else:
        args = (asset, session, origins, grid.close, grid.open, rate, cash)
        legacy, legacy_counts = derive_session(
            legacy_tape, *args, iv_bounds=IV_LEGACY, causal=False, versions_selected=True
        )
        iv_only, iv_only_counts = derive_session(
            legacy_tape, *args, iv_bounds=IV_CLEAN, causal=False, versions_selected=True
        )
        production, production_counts = derive_session(
            clean, *args, iv_bounds=IV_CLEAN, causal=True, versions_selected=True
        )
    target, target_counts = reconstruct_jump(observed, base.select(KEYS), grid)
    combined = (
        production.join(legacy.rename(LEGACY_NAMES), on=KEYS, validate="1:1")
        .join(iv_only.rename(IV_ONLY_NAMES), on=KEYS, validate="1:1")
        .join(target, on=KEYS, validate="1:1")
    )
    rp4_v2.write_parquet_once(shard, combined)
    target_aligned = base.select(KEYS + ["rv30"]).join(target, on=KEYS, validate="1:1")
    alignment = comparison_metrics(
        target_aligned["rv30"].to_numpy(),
        target_aligned["rv30_reconstructed"].to_numpy(),
        rtol=1e-8,
        atol=1e-12,
    )
    result = {
        "asset": asset,
        "session_date": session,
        "identity": identity,
        "sha256": rp4.sha256(shard),
        "source_sha256": source["source_sha256"],
        "origins": base.height,
        "used_all_fallback": source["used_all_fallback"],
        "missing_bar_grid": grid is None,
        "duplicates": duplicate_counts,
        "legacy_duplicates": legacy_duplicate_counts,
        "iv": iv_counts,
        "legacy": legacy_counts,
        "iv_only": iv_only_counts,
        "production": production_counts,
        "target_mask": target_counts,
        "rv30_alignment": alignment,
    }
    rp4_v2.write_json_once(receipt, result)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--spec-sha256", required=True)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args(argv)
    if args.output_root.resolve() != OUTPUT_ROOT.resolve() or not 1 <= args.workers <= 4:
        raise ValueError("RP4_V3_OUTPUT_OR_WORKERS_INVALID")
    output = args.output_root / "materialized"
    if (output / "manifest.json").exists():
        raise ValueError("RP4_V3_MATERIALIZATION_ALREADY_COMPLETE")
    pins, sources, identity = input_contract(args.spec, args.spec_sha256)
    rp4_v2.write_json_once(output / "input_pins.json", {"identity": identity, "sha256": pins})
    base = pl.read_parquet(V2_ROOT / "panel.parquet").sort(KEYS)
    if "jump30" in base.columns:
        raise ValueError("RP4_V3_JUMP30_ALREADY_PRESENT")
    grids = paired_price_grids(pins)
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {}
        for key, group in base.group_by(["asset", "session_date"], maintain_order=True):
            asset, session = map(str, key)
            grid, observed = grids.get((asset, session), (None, None))
            future = pool.submit(
                materialize_session,
                group,
                sources[asset, session],
                grid,
                observed,
                output,
                identity,
            )
            futures[future] = (asset, session)
        for future in as_completed(futures):
            try:
                results.append(future.result())
            except Exception as error:
                asset, session = futures[future]
                for remaining in futures:
                    remaining.cancel()
                raise ValueError(f"RP4_V3_SESSION_FAILED:{asset}:{session}:{error}") from error
            if len(results) % 20 == 0:
                print(
                    json.dumps({"completed_session_assets": len(results), "total": len(futures)}),
                    flush=True,
                )
    shards = pl.concat(
        [
            pl.read_parquet(output / "sessions" / f"{row['session_date']}_{row['asset']}.parquet")
            for row in results
        ],
        how="vertical_relaxed",
    ).sort(KEYS)
    panel = append_features(base, shards.select(KEYS + FEATURES + ["jump30"]))
    candidate = pl.read_parquet(CANDIDATE).select(KEYS + FEATURES)
    legacy = shards.select(KEYS + list(LEGACY_NAMES.values())).rename(
        {value: key for key, value in LEGACY_NAMES.items()}
    )
    iv_only = shards.select(KEYS + list(IV_ONLY_NAMES.values())).rename(
        {value: key for key, value in IV_ONLY_NAMES.items()}
    )
    production = shards.select(KEYS + FEATURES)
    comparison = pl.DataFrame(
        [
            *compare_panels(
                candidate,
                legacy,
                "candidate_vs_independent_legacy",
                "Independent implementation/source-order/dedup comparison",
            ),
            *compare_panels(
                legacy,
                iv_only,
                "legacy_vs_iv_only",
                "IV range and induced prior-print multileg history changes only",
            ),
            *compare_panels(
                iv_only,
                production,
                "iv_only_vs_production",
                "First-available versions, eligible-history, dual clocks, "
                "prefix NaN, ambiguous side zero",
            ),
            *compare_panels(
                candidate,
                production,
                "candidate_vs_production",
                "Combined registered IV, version/history and causal safety corrections",
            ),
        ]
    )
    flattened = []
    for result in results:
        row = {
            "asset": result["asset"],
            "session_date": result["session_date"],
            "origins": result["origins"],
            "used_all_fallback": result["used_all_fallback"],
            "missing_bar_grid": result["missing_bar_grid"],
        }
        for section in (
            "duplicates",
            "legacy_duplicates",
            "iv",
            "legacy",
            "iv_only",
            "production",
            "target_mask",
        ):
            row.update({f"{section}__{key}": value for key, value in result[section].items()})
        flattened.append(row)
    counts = pl.DataFrame(flattened).sort("asset", "session_date")
    aligned = base.select(KEYS + ["rv30"]).join(
        shards.select(KEYS + ["rv30_reconstructed", "jump30"]), on=KEYS, validate="1:1"
    )
    alignment = comparison_metrics(
        aligned["rv30"].to_numpy(), aligned["rv30_reconstructed"].to_numpy(), rtol=1e-8, atol=1e-12
    )
    coverage = []
    for (asset,), group in panel.group_by("asset"):
        for name in FEATURES + ["jump30"]:
            finite = int(np.isfinite(group[name].to_numpy()).sum())
            coverage.append(
                {
                    "asset": asset,
                    "column": name,
                    "origins": group.height,
                    "finite": finite,
                    "coverage": finite / group.height,
                }
            )
    rp4_v2.write_parquet_once(output / "panel.parquet", panel)
    rp4_v2.write_parquet_once(output / "independent_legacy.parquet", legacy)
    rp4_v2.write_parquet_once(output / "iv_only_bridge.parquet", iv_only)
    rp4_v2.write_parquet_once(output / "target_alignment.parquet", aligned)
    rp4_v2.write_bytes_once(output / "comparison.csv", comparison.write_csv().encode())
    rp4_v2.write_bytes_once(output / "counts.csv", counts.write_csv().encode())
    rp4_v2.write_bytes_once(
        output / "coverage.csv", pl.DataFrame(coverage).sort("asset", "column").write_csv().encode()
    )
    verify_pins(pins)
    files = [
        "panel.parquet",
        "independent_legacy.parquet",
        "iv_only_bridge.parquet",
        "target_alignment.parquet",
        "comparison.csv",
        "counts.csv",
        "coverage.csv",
        "input_pins.json",
    ]
    manifest = {
        "schema_version": "rp4-v3-gamma-materialization-v1",
        "spec_sha256": args.spec_sha256,
        "base_panel_sha256": SOURCE_PINS[str(V2_ROOT / "panel.parquet")],
        "input_identity": identity,
        "rows": panel.height,
        "sessions": panel["session_date"].n_unique(),
        "session_assets": len(results),
        "added_predictors": FEATURES,
        "added_target": "jump30",
        "preserved_columns": base.columns,
        "preserved_values_exact_by_keys": True,
        "rv30_alignment": alignment,
        "signed_trades_storage": "raw count; evaluator applies log1p once",
        "iv_bounds": IV_CLEAN,
        "seconds_per_year": SECONDS_PER_YEAR,
        "visibility": "created_at<=cutoff AND executed_at<=cutoff; no new timestamps",
        "empty_prefix": "NaN; visible valid but unsigned prefix zero",
        "target_feature_use": "none; v2 RV30 copied unchanged; jump separate classifier mask",
        "code_sha256": {path: pins[str(ROOT / path)] for path in CODE_PATHS},
        "independent_derivation_initial_sha256": INITIAL_DERIVATION_SHA,
        "candidate_producer_inspection": (
            "Only after independent derivation; audit bridge semantics, "
            "never imported in materialization"
        ),
        "candidate_producer_sha256": CANDIDATE_CODE_SHA,
        "artifacts": {str(output / name): rp4.sha256(output / name) for name in files},
        "model_fits": 0,
        "provider_requests": 0,
        "phase9_modified": False,
        "RESEARCH_ONLY": True,
        "capital_go": False,
    }
    rp4_v2.write_json_once(output / "manifest.json", manifest)
    print(
        json.dumps(
            {
                "status": "PASS_RP4_V3_GAMMA_MATERIALIZATION",
                "rows": panel.height,
                "manifest_sha256": rp4.sha256(output / "manifest.json"),
            }
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
