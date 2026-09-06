"""RP4 keyed, causal panel materialization; no estimation or outcome-based selection."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from collections.abc import Sequence
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
import polars as pl
from rp2_block4_b0_panel import build_b0_panel, build_market_controls
from rp2_block5_surface_panel import build_session_surface, load_inventory
from rp2_block6_flow_panel import build_session_flow

from mds650.b1q_exogenous_provenance_v1 import parse_treasury_yield_curve_xml
from mds650.har import HAR_COLUMNS, HARQ_COLUMN, build_har_features, session_minute_expression
from mds650.rp2.b1_snapshot import latest_quote_per_contract, snapshot_window
from mds650.rp2.bars import (
    BAR_SOURCES,
    apply_volume_repair,
    build_session_grid,
    deduplicate_bar_sources,
    load_bar_sources,
    normalise_bars,
    session_length_minutes,
)
from mds650.rp2.option_clock import expiry_close_timestamps
from mds650.rp2.realized import forward_measures, log_returns

ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path("D:/MDS650")
REGISTERED = DATA_ROOT / "registered_runs/rp2_v3/rp2-v3-20260901-flow-session-loss-registration"
KEYS = ["asset", "session_date", "origin_minute"]
HAR_NAMES = [*HAR_COLUMNS, HARQ_COLUMN]
TENORS = ["dte_0_1", "dte_2_7", "dte_8_30", "dte_31_90", "dte_gt90"]
MONEYNESS = ["m_lt090", "m_090_097", "m_097_103", "m_103_110", "m_gt110"]
GRID_COLUMNS = [f"rp4_iv_{tenor}_{money}" for tenor in TENORS for money in MONEYNESS]
GRID_COUNT = "rp4_surface_populated_cells"
DEALER_COLUMNS = [
    "rp4_dealer_gamma_net",
    "rp4_dealer_gamma_near_spot",
    "rp4_dealer_max_gamma_distance",
]
SECONDS_PER_YEAR = 365 * 24 * 3600
NY = ZoneInfo("America/New_York")
TAPE_COLUMNS = [
    "id",
    "underlying_symbol",
    "created_at",
    "implied_volatility",
    "size",
    "open_interest",
    "expiry",
    "strike",
    "option_type",
    "nbbo_bid",
    "nbbo_ask",
]


def sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if json.loads(path.read_text(encoding="utf-8")) != value:
            raise ValueError(f"RP4_EXISTING_JSON_DIFFERS:{path.name}")
        return
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True, allow_nan=False)
        handle.write("\n")


def assert_unique(frame: pl.DataFrame, keys: Sequence[str] = KEYS) -> None:
    if frame.select(list(keys)).n_unique() != frame.height:
        raise ValueError("RP4_DUPLICATE_IDENTITY_KEYS")


def session_window(frame: pl.DataFrame, start: str, end: str) -> pl.DataFrame:
    return frame.filter(pl.col("session_date").is_between(pl.lit(start), pl.lit(end)))


def weighted_median(values: np.ndarray, weights: np.ndarray) -> float:
    valid = np.isfinite(values) & np.isfinite(weights) & (weights > 0)
    if not valid.any():
        return math.nan
    selected = values[valid]
    selected_weights = weights[valid]
    order = np.argsort(selected, kind="stable")
    cumulative = np.cumsum(selected_weights[order])
    position = np.searchsorted(cumulative, cumulative[-1] / 2.0, side="left")
    return float(selected[order[position]])


def cell_indices(dte: np.ndarray, moneyness: np.ndarray) -> np.ndarray:
    tenor = np.searchsorted([1, 7, 30, 90], dte, side="left")
    money = np.searchsorted([0.90, 0.97, 1.03, 1.10], moneyness, side="right")
    money = np.where(moneyness == 1.10, 3, money)
    return np.asarray(tenor * 5 + money, dtype=np.int64)


def gamma_with_carry(
    spot: float,
    strike: np.ndarray,
    tenor: np.ndarray,
    iv: np.ndarray,
    rate: float,
    dividend_yield: float,
) -> np.ndarray:
    if not (
        math.isfinite(spot) and spot > 0 and math.isfinite(rate) and math.isfinite(dividend_yield)
    ):
        return np.full(strike.shape, math.nan)
    valid = (
        np.isfinite(strike)
        & (strike > 0)
        & np.isfinite(tenor)
        & (tenor > 0)
        & np.isfinite(iv)
        & (iv > 0)
    )
    result = np.full(strike.shape, math.nan)
    sigma_sqrt_t = iv[valid] * np.sqrt(tenor[valid])
    d1 = (
        np.log(spot / strike[valid]) + (rate - dividend_yield + 0.5 * iv[valid] ** 2) * tenor[valid]
    ) / sigma_sqrt_t
    result[valid] = np.exp(-dividend_yield * tenor[valid] - 0.5 * d1**2) / (
        math.sqrt(2 * math.pi) * spot * sigma_sqrt_t
    )
    return result


def dealer_measures(
    spot: float,
    strikes: np.ndarray,
    gamma: np.ndarray,
    open_interest: np.ndarray,
    is_call: np.ndarray,
) -> tuple[float, float, float]:
    valid = (
        np.isfinite(strikes)
        & np.isfinite(gamma)
        & np.isfinite(open_interest)
        & (open_interest >= 0)
    )
    if not valid.any() or not math.isfinite(spot) or spot <= 0:
        return math.nan, math.nan, math.nan
    strikes = strikes[valid]
    exposure = open_interest[valid] * gamma[valid] * spot**2 * 100.0
    exposure *= np.where(is_call[valid], 1.0, -1.0)
    unique, inverse = np.unique(strikes, return_inverse=True)
    by_strike = np.bincount(inverse, weights=exposure, minlength=unique.size)
    # Exact ties: nearest spot, then the lower strike, including the all-zero case.
    order = np.lexsort((unique, np.abs(unique / spot - 1), -np.abs(by_strike)))
    peak = float(unique[order[0]] / spot - 1)
    return (
        float(exposure.sum()),
        float(exposure[np.abs(strikes / spot - 1) <= 0.05 + 1e-12].sum()),
        peak,
    )


def origin_timestamp(session: str, minute: int) -> datetime:
    return (
        datetime.fromisoformat(session).replace(tzinfo=NY) + timedelta(minutes=570 + minute)
    ).astimezone(UTC)


def build_new_option_features(
    tape: pl.DataFrame,
    asset: str,
    session: str,
    origins: np.ndarray,
    closes: np.ndarray,
    rate: float,
    dividend_cash: float,
) -> pl.DataFrame:
    """Current-day OI is the owner's adopted prior-close field, never trade volume."""
    tape = tape.filter(
        (pl.col("underlying_symbol") == asset)
        & pl.col("implied_volatility").is_between(0.01, 5.0)
        & (pl.col("nbbo_bid") > 0)
        & (pl.col("nbbo_ask") > pl.col("nbbo_bid"))
        & (pl.col("strike") > 0)
        & (pl.col("size") > 0)
        & pl.col("option_type").is_in(["call", "put"])
    ).sort("created_at")
    created = tape["created_at"].cast(pl.Datetime("us", "UTC")).cast(pl.Int64).to_numpy()
    strike = tape["strike"].cast(pl.Float64).to_numpy()
    iv = tape["implied_volatility"].cast(pl.Float64).to_numpy()
    size = tape["size"].cast(pl.Float64).to_numpy()
    oi = tape["open_interest"].cast(pl.Float64).to_numpy()
    expiry = tape["expiry"].cast(pl.Date).to_numpy()
    expiry_us = expiry_close_timestamps(expiry, "America/New_York")
    dte = (expiry - np.datetime64(session, "D")).astype("timedelta64[D]").astype(int)
    calls = (tape["option_type"] == "call").to_numpy()
    # Tuple factorization avoids the arithmetic contract-key overflow/collision problem.
    contract = np.rec.fromarrays([expiry.astype(np.int64), strike, calls])
    _, contract_ids = np.unique(contract, return_inverse=True)
    rows: list[dict[str, Any]] = []
    for minute in origins:
        row: dict[str, Any] = {
            "asset": asset,
            "session_date": session,
            "origin_minute": int(minute),
        }
        row.update(dict.fromkeys(GRID_COLUMNS + DEALER_COLUMNS, math.nan))
        row[GRID_COUNT] = 0.0
        spot = float(closes[int(minute) - 3]) if 3 <= minute < closes.size else math.nan
        if not math.isfinite(spot) or spot <= 0:
            rows.append(row)
            continue
        stamp = origin_timestamp(session, int(minute))
        origin_us = int(stamp.timestamp() * 1_000_000)
        cutoff = origin_us - 120_000_000
        lo = int(np.searchsorted(created, cutoff - 300_000_000, side="right"))
        hi = int(np.searchsorted(created, cutoff, side="right"))
        positions = np.arange(lo, hi)
        positions = positions[(dte[positions] >= 0) & (expiry_us[positions] > cutoff)]
        cells = cell_indices(dte[positions], strike[positions] / spot)
        for cell in np.unique(cells):
            selected = positions[cells == cell]
            row[GRID_COLUMNS[cell]] = weighted_median(iv[selected], size[selected])
        row[GRID_COUNT] = float(sum(math.isfinite(row[name]) for name in GRID_COLUMNS))
        snapshot = latest_quote_per_contract(created, contract_ids, snapshot_window(origin_us))
        positions = snapshot.positions
        positions = positions[(dte[positions] >= 0) & (expiry_us[positions] > cutoff)]
        tenor = (expiry_us[positions] - cutoff) / 1_000_000 / SECONDS_PER_YEAR
        gamma = gamma_with_carry(
            spot, strike[positions], tenor, iv[positions], rate, dividend_cash / spot
        )
        measures = dealer_measures(spot, strike[positions], gamma, oi[positions], calls[positions])
        row.update(dict(zip(DEALER_COLUMNS, measures, strict=True)))
        rows.append(row)
    return pl.DataFrame(rows, infer_schema_length=None)


def reconstruct_rv30(bars: pl.DataFrame, keys: pl.DataFrame) -> tuple[pl.DataFrame, dict[str, int]]:
    """Reuse RP2 Block3's grid/return/measure producer on the requested keyed RV30 grid."""
    assert_unique(keys)
    groups = {
        tuple(map(str, key)): frame for key, frame in bars.group_by(["asset", "session_date"])
    }
    rows: list[pl.DataFrame] = []
    counters = {"missing_bar_keys": 0, "quality_excluded_keys": 0, "unobserved_target_bar_keys": 0}
    for (asset, session), frame in keys.group_by(["asset", "session_date"], maintain_order=True):
        group = groups.get((str(asset), str(session)))
        if group is None:
            counters["missing_bar_keys"] += frame.height
            continue
        grid = build_session_grid(group, session=date.fromisoformat(str(session)))
        present = np.flatnonzero(grid.valid)
        first = int(present[0]) if present.size else grid.minutes
        close = grid.close[first:]
        if grid.fill_share > 0.05 or close.size < 31 or not np.isfinite(close).all():
            counters["quality_excluded_keys"] += frame.height
            continue
        origins = frame["origin_minute"].to_numpy().astype(np.int64)
        valid = (origins >= first) & (origins + 30 < grid.minutes)
        counters["quality_excluded_keys"] += int((~valid).sum())
        observed = np.zeros(grid.minutes, dtype=np.int64)
        actual_minutes = group["minute"].to_numpy().astype(np.int64)
        actual_close = group["close"].to_numpy()
        actual = (actual_minutes >= 0) & (actual_minutes < grid.minutes)
        actual &= np.isfinite(actual_close) & (actual_close > 0)
        observed[actual_minutes[actual]] = 1
        prefix = np.r_[0, np.cumsum(observed)]
        complete = np.zeros(origins.size, dtype=bool)
        complete[valid] = prefix[origins[valid] + 31] - prefix[origins[valid]] == 31
        counters["unobserved_target_bar_keys"] += int((valid & ~complete).sum())
        valid &= complete
        selected = frame.filter(pl.Series(valid))
        rv = forward_measures(log_returns(close), origins[valid] - first, 30).rv
        rows.append(selected.with_columns(pl.Series("rv30", rv)))
    return (
        pl.concat(rows) if rows else keys.head(0).with_columns(rv30=pl.lit(None, pl.Float64)),
        counters,
    )


def compare_targets(rebuilt: pl.DataFrame, registered_path: Path) -> dict[str, Any]:
    registered = pl.read_parquet(registered_path, columns=KEYS + ["rv_30"])
    assert_unique(registered)
    joined = rebuilt.join(registered, on=KEYS, how="inner", validate="1:1")
    difference = joined["rv30"].to_numpy() - joined["rv_30"].to_numpy()
    finite = np.isfinite(difference)
    magnitude = np.abs(difference[finite])
    same = np.isclose(joined["rv30"].to_numpy(), joined["rv_30"].to_numpy(), atol=1e-12, rtol=1e-8)
    return {
        "registered_rows": registered.height,
        "rebuilt_rows": rebuilt.height,
        "overlapping_keys": joined.height,
        "finite_pairs": int(finite.sum()),
        "pairs_within_registered_tolerance": int((same & finite).sum()),
        "share_within_registered_tolerance": float(same[finite].mean()) if finite.any() else None,
        "pairs_above_1e_minus_12": int((magnitude > 1e-12).sum()),
        "maximum_absolute_difference": float(magnitude.max()) if magnitude.size else None,
        "mean_absolute_difference": float(magnitude.mean()) if magnitude.size else None,
        "target_used": "rebuilt_rv30",
        "join": "asset,session_date,origin_minute;1:1",
    }


def har_features_for_session(bars: pl.DataFrame, keys: pl.DataFrame) -> pl.DataFrame:
    """Include bars completed exactly at t-120s, keeping true-origin seasonality."""
    timestamps = [
        origin_timestamp(str(day), int(minute))
        for day, minute in keys.select("session_date", "origin_minute").iter_rows()
    ]
    origins = keys.with_columns(
        pl.Series("forecast_origin_utc", timestamps, dtype=pl.Datetime("us", "UTC")),
        pl.Series("origin_id", [f"{a}:{d}:{m}" for a, d, m in keys.iter_rows()]),
    )
    effective = origins.with_columns(
        (
            pl.col("forecast_origin_utc") - pl.duration(seconds=120) + pl.duration(microseconds=1)
        ).alias("forecast_origin_utc"),
        pl.col("session_date").str.to_date(),
    )
    raw_bars = bars.select(
        "asset",
        pl.col("bar_ny").dt.convert_time_zone("UTC").alias("bar_start_utc"),
        "close",
    )
    features = build_har_features(raw_bars, effective, label_shift_minutes=1)
    return (
        origins.join(
            features.select("origin_id", *HAR_NAMES), on="origin_id", how="left", validate="1:1"
        )
        .with_columns((session_minute_expression() / 390.0).alias("minute_fraction"))
        .with_columns((pl.col("minute_fraction") ** 2).alias("minute_fraction_sq"))
        .select(*KEYS, *HAR_NAMES)
    )


def exogenous_sources(output_root: Path) -> tuple[dict[str, float], dict[str, list], list[Path]]:
    old = DATA_ROOT / "phase6/raw/fmp_exogenous_v1"
    paths = sorted(old.glob("treasury_*.xml"))
    paths += sorted((output_root / "raw/exogenous").glob("treasury_*.xml"))
    rates: dict[str, float] = {}
    for path in paths:
        for day, value in parse_treasury_yield_curve_xml(path.read_bytes()).items():
            if day in rates and rates[day] != value:
                raise ValueError(f"RP4_TREASURY_SOURCE_DISAGREES:{day}")
            rates[day] = value
    dividends: dict[str, list] = {}
    for path in sorted(old.glob("dividends_*.json")):
        dividends[path.stem.removeprefix("dividends_")] = json.loads(path.read_text())
        paths.append(path)
    return rates, dividends, paths


def carry_for_session(
    session: str,
    asset: str,
    rates: dict[str, float],
    dividends: dict[str, list],
) -> tuple[float, float]:
    days = [day for day in rates if day < session]
    day = max(days) if days else None
    rate = rates[day] if day else math.nan
    if asset not in dividends:
        return rate, math.nan
    session_day = date.fromisoformat(session)
    cash = 0.0
    for event in dividends[asset]:
        try:
            declared = date.fromisoformat(str(event["declarationDate"]))
            value = float(event.get("adjDividend") or event.get("dividend") or 0.0)
        except (KeyError, TypeError, ValueError):
            continue
        if session_day - timedelta(days=365) <= declared < session_day and value > 0:
            cash += value
    return rate, cash


def load_rp4_bars(output_root: Path, end: str) -> tuple[pl.DataFrame, list[Path]]:
    original = load_bar_sources(DATA_ROOT)
    paths = [
        DATA_ROOT / relative for _, _, relative in BAR_SOURCES if (DATA_ROOT / relative).is_file()
    ]
    added = sorted(
        path
        for path in (output_root / "data/fmp").glob("date=*/asset=*.parquet")
        if path.parent.name.removeprefix("date=") <= end
    )
    frames = [original]
    for path in added:
        frame = normalise_bars(pl.read_parquet(path)).with_columns(
            source=pl.lit("rp4_acquired"),
            role=pl.lit("RP4"),
        )
        frames.append(frame)
    bars = deduplicate_bar_sources(pl.concat(frames, how="diagonal_relaxed"))
    return apply_volume_repair(bars, DATA_ROOT), paths + added


def tape_index(output_root: Path) -> dict[tuple[str, str], list[str]]:
    index = load_inventory(ROOT / "artifacts/rp2_block1_partition/inventory.jsonl")
    extension = DATA_ROOT / "data/phase5_holdout/data/option_events"
    for path in sorted(extension.glob("date=*/asset=*/events.parquet")):
        day = path.parent.parent.name.removeprefix("date=")
        asset = path.parent.name.removeprefix("asset=")
        if "2026-07-20" <= day <= "2026-07-31":
            index.setdefault((day, asset), []).append(str(path))
    for path in sorted((output_root / "data/option_events").glob("date=*/asset=*/*.parquet")):
        day = path.parent.parent.name.removeprefix("date=")
        asset = path.parent.name.removeprefix("asset=")
        key = (day, asset)
        if key not in index:
            index[key] = []
        index[key].append(str(path))
    return index


def read_new_tape(paths: Sequence[str], asset: str) -> pl.DataFrame:
    frames = [
        pl.read_parquet(path, columns=TAPE_COLUMNS).filter(pl.col("underlying_symbol") == asset)
        for path in dict.fromkeys(paths)
    ]
    combined = pl.concat(frames, how="vertical_relaxed")
    if combined["id"].null_count():
        raise ValueError("RP4_TAPE_EVENT_ID_MISSING")
    duplicates = combined.filter(pl.col("id").is_duplicated())
    if duplicates.height and duplicates.unique().height != duplicates["id"].n_unique():
        raise ValueError("RP4_TAPE_DUPLICATE_ID_CONFLICT")
    return combined.unique(subset="id", keep="first", maintain_order=True)


def coverage_table(frame: pl.DataFrame) -> pl.DataFrame:
    rows = []
    for (asset,), group in frame.group_by("asset"):
        for index, column in enumerate(GRID_COLUMNS):
            finite = group[column].is_finite().fill_null(False).sum()
            rows.append(
                {
                    "asset": asset,
                    "tenor": TENORS[index // 5],
                    "moneyness": MONEYNESS[index % 5],
                    "column": column,
                    "origins": group.height,
                    "populated": finite,
                    "coverage": finite / group.height if group.height else 0.0,
                }
            )
    return pl.DataFrame(rows).sort("asset", "tenor", "moneyness")


def event_sources(output_root: Path) -> dict[str, dict[str, Any]]:
    paths = sorted((output_root / "manifests/events").glob("earnings_*.json"))
    paths += [output_root / "manifests/events/fomc_meetings_v1.json"]
    return {path.stem: json.loads(path.read_text()) for path in paths if path.is_file()}


def attach_secondaries(
    panel: pl.DataFrame, historical_flow: pl.DataFrame, events: dict[str, dict[str, Any]]
) -> pl.DataFrame:
    """Calendar and previous-session flow are reporting strata only, never X."""
    daily = historical_flow.group_by("asset", "session_date").agg(pl.col("b2_30m_premium").mean())
    extra = panel.group_by("asset", "session_date").agg(pl.col("b2_30m_premium").mean())
    extra = extra.join(
        daily.select("asset", "session_date"), on=["asset", "session_date"], how="anti"
    )
    lookup = {(a, d): v for a, d, v in pl.concat([daily, extra]).iter_rows()}
    rows: list[dict[str, Any]] = []
    for asset, session in panel.select("asset", "session_date").unique().iter_rows():
        day = date.fromisoformat(session)
        prior = day - timedelta(days=1)
        while session_length_minutes(prior) == 0:
            prior -= timedelta(days=1)
        first = day.replace(day=1)
        third_friday = first + timedelta(days=(4 - first.weekday()) % 7 + 14)
        while session_length_minutes(third_friday) == 0:
            third_friday -= timedelta(days=1)
        earning = events.get(f"earnings_{asset}", {})
        fomc = events.get("fomc_meetings_v1", {})
        e_known = earning.get("status") == "PASS"
        f_known = fomc.get("status") == "PASS"
        is_earnings = session in earning.get("session_dates", []) if e_known else None
        is_fomc = session in fomc.get("session_dates", []) if f_known else None
        is_monthly = day == third_friday
        is_event = (
            True if is_earnings or is_fomc or is_monthly else False if e_known and f_known else None
        )
        rows.append(
            {
                "asset": asset,
                "session_date": session,
                "previous_day_b2_30m_premium": lookup.get((asset, prior.isoformat())),
                "is_earnings": is_earnings,
                "is_fomc": is_fomc,
                "is_monthly_expiration": is_monthly,
                "is_event": is_event,
                "earnings_calendar_known": e_known,
                "fomc_calendar_known": f_known,
                "event_calendar_status": "PASS" if e_known and f_known else "NO VERIFICABLE",
            }
        )
    return panel.join(
        pl.DataFrame(rows, infer_schema_length=None),
        on=["asset", "session_date"],
        how="left",
        validate="m:1",
    )


def combine_parts(
    output_root: Path, stage: str, parts: list[str], spec_hash: str, code_hash: str
) -> int:
    manifests = [
        json.loads((output_root / part.lower() / "manifest.json").read_text()) for part in parts
    ]
    panel_paths = []
    for part, manifest in zip(parts, manifests, strict=True):
        if manifest["spec_sha256"] != spec_hash or manifest["code_sha256"] != code_hash:
            raise ValueError("RP4_PART_SPEC_CODE_MISMATCH")
        panel_path = output_root / part.lower() / "panel.parquet"
        if manifest["artifacts"][str(panel_path)] != sha256(panel_path):
            raise ValueError("RP4_PART_PANEL_HASH_MISMATCH")
        panel_paths.append(panel_path)
    output = output_root / stage.lower()
    output.mkdir(parents=True, exist_ok=True)
    if (output / "panel.parquet").exists():
        raise ValueError("RP4_COMBINED_PANEL_ALREADY_EXISTS")
    panel = pl.concat([pl.read_parquet(path) for path in panel_paths], how="diagonal_relaxed").sort(
        KEYS
    )
    assert_unique(panel)
    panel.write_parquet(output / "panel.parquet")
    coverage_table(panel).write_csv(output / "coverage.csv")
    manifest = {
        "stage": stage,
        "spec_sha256": spec_hash,
        "code_sha256": code_hash,
        "parts": {
            str(output_root / part.lower() / "manifest.json"): sha256(
                output_root / part.lower() / "manifest.json"
            )
            for part in parts
        },
        "rows": panel.height,
        "sessions": panel["session_date"].n_unique(),
        "assets": sorted(panel["asset"].unique()),
        "first_session": panel["session_date"].min(),
        "last_session": panel["session_date"].max(),
        "target_rows_finite": panel["rv30"].is_finite().fill_null(False).sum(),
        "artifacts": {
            str(output / name): sha256(output / name) for name in ["panel.parquet", "coverage.csv"]
        },
        "model_fits": 0,
        "research_only": True,
        "capital_go": False,
    }
    write_json(output / "manifest.json", manifest)
    print(
        json.dumps(
            {
                "status": "PASS_COMBINE",
                "rows": panel.height,
                "manifest": str(output / "manifest.json"),
                "manifest_sha256": sha256(output / "manifest.json"),
            }
        )
    )
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--spec-sha256", required=True)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--start", default="2024-08-02")
    parser.add_argument("--end", default="2026-07-31")
    parser.add_argument("--stage", default="A2")
    parser.add_argument("--assets", nargs="+")
    parser.add_argument("--combine-parts", nargs="+")
    args = parser.parse_args(argv)
    if sha256(args.spec) != args.spec_sha256:
        raise ValueError("RP4_SPECIFICATION_HASH_MISMATCH")
    spec = json.loads(args.spec.read_text(encoding="utf-8"))
    code_hash = sha256(Path(__file__))
    if not re.fullmatch(r"[A-Za-z0-9_]+", args.stage) or any(
        not re.fullmatch(r"[A-Za-z0-9_]+", part) for part in args.combine_parts or []
    ):
        raise ValueError("RP4_STAGE_PATH_INVALID")
    output_root = args.output_root.resolve()
    if output_root != (DATA_ROOT / "artifacts/rp4_20260907").resolve():
        raise ValueError("RP4_OUTPUT_ROOT_NOT_AUTHORIZED")
    if args.combine_parts:
        return combine_parts(
            output_root, args.stage, args.combine_parts, args.spec_sha256, code_hash
        )
    output = output_root / args.stage.lower()
    output.mkdir(parents=True, exist_ok=True)
    if (output / "manifest.json").exists():
        raise ValueError("RP4_STAGE_ALREADY_MATERIALIZED")
    # The JSON allowlists are frozen by A1; no column selection from values is permitted.
    sets = spec["registered_feature_sets"]
    if spec["grid_columns"] != GRID_COLUMNS or spec["dealer_columns"] != DEALER_COLUMNS:
        raise ValueError("RP4_SPECIFICATION_OUTPUT_SCHEMA_MISMATCH")
    b0_names = sets["B0"]
    b1_names = sets["B1"]
    b2_names = sets["B2"]
    b0_path = REGISTERED / "rp2_block4_b0/b0_panel.parquet"
    b1_path = REGISTERED / "rp2_block5_surface/b1_surface_panel.parquet"
    b2_path = REGISTERED / "rp2_block6_flow/b2_flow_panel.parquet"
    targets_path = REGISTERED / "rp2_block3_target/target_panel.parquet"
    inventory = json.loads((ROOT / "artifacts/rp4_inventory_v1/inventory.json").read_text())
    for item in inventory["panels"].values():
        if sha256(Path(item["path"])) != item["sha256"]:
            raise ValueError("RP4_REGISTERED_INPUT_HASH_MISMATCH")
    b0 = pl.read_parquet(b0_path, columns=KEYS + b0_names)
    b1 = pl.read_parquet(b1_path, columns=KEYS + b1_names)
    b2 = pl.read_parquet(b2_path, columns=KEYS + b2_names)
    for frame in (b0, b1, b2):
        assert_unique(frame)
    bars, bar_paths = load_rp4_bars(output_root, args.end)
    bars = bars.filter(pl.col("session_date") <= date.fromisoformat(args.end))
    last_registered = b0["session_date"].max()
    if args.end > str(last_registered):
        rebuilt_b0, _ = build_b0_panel(bars, max_fill_share=0.05)
        market = build_market_controls(bars)
        rebuilt_b0 = rebuilt_b0.join(market, on=["session_date", "origin_minute"], how="left")
        extra = rebuilt_b0.filter(pl.col("session_date") > last_registered).select(KEYS + b0_names)
        b0 = pl.concat([b0, extra], how="vertical_relaxed")
    b0 = session_window(b0, args.start, args.end).sort(KEYS)
    if args.assets:
        if set(args.assets) - set(spec["assets"]):
            raise ValueError("RP4_ASSET_NOT_REGISTERED")
        b0 = b0.filter(pl.col("asset").is_in(args.assets))
    index = tape_index(output_root)
    rates, dividends, exogenous_paths = exogenous_sources(output_root)
    events = event_sources(output_root)
    event_paths = [output_root / "manifests/events" / f"{name}.json" for name in events]
    input_paths = [
        ROOT / "artifacts/rp2_block1_partition/inventory.jsonl",
        b0_path,
        b1_path,
        b2_path,
        targets_path,
        *bar_paths,
        *exogenous_paths,
        *event_paths,
    ]
    input_pins = {str(path): sha256(path) for path in input_paths}
    input_identity = hashlib.sha256(json.dumps(input_pins, sort_keys=True).encode()).hexdigest()
    rebuilt_target, target_counters = reconstruct_rv30(bars, b0.select(KEYS))
    target_comparison = compare_targets(rebuilt_target, targets_path)
    target_comparison["counters"] = target_counters
    write_json(output / "target_comparison.json", target_comparison)
    grids = {
        tuple(map(str, key)): build_session_grid(group, session=key[1])
        for key, group in bars.group_by(["asset", "session_date"])
    }
    bar_by_asset = {str(key[0]): group for key, group in bars.group_by("asset")}
    seen_sources: dict[str, str] = {}
    exclusions: list[dict[str, Any]] = []
    all_shards: list[Path] = []
    groups = b0.group_by(["asset", "session_date"], maintain_order=True)
    for count, ((asset, session), base) in enumerate(groups, 1):
        asset, session = str(asset), str(session)
        shard = output / "sessions" / f"{session}_{asset}.parquet"
        receipt = shard.with_suffix(".json")
        if shard.exists() and receipt.exists():
            previous = json.loads(receipt.read_text())
            if (
                previous["spec_sha256"] != args.spec_sha256
                or previous["sha256"] != sha256(shard)
                or previous["code_sha256"] != code_hash
                or previous["input_identity"] != input_identity
            ):
                raise ValueError("RP4_SHARD_CUSTODY_MISMATCH")
            for path, digest in previous["source_sha256"].items():
                if path not in seen_sources:
                    seen_sources[path] = sha256(Path(path))
                if seen_sources[path] != digest:
                    raise ValueError("RP4_SHARD_SOURCE_CHANGED")
            all_shards.append(shard)
            continue
        paths = index.get((session, asset)) or index.get((session, "__ALL__"))
        grid = grids.get((asset, session))
        if not paths or grid is None or grid.fill_share > 0.05:
            exclusions.append(
                {
                    "asset": asset,
                    "session_date": session,
                    "origins": base.height,
                    "reason": "NO_TAPE" if not paths else "BAR_QUALITY",
                }
            )
            continue
        origins = base["origin_minute"].to_numpy().astype(np.int64)
        rate, cash = carry_for_session(session, asset, rates, dividends)
        try:
            tape = read_new_tape(paths, asset)
            new_options = build_new_option_features(
                tape, asset, session, origins, grid.close, rate, cash
            )
            del tape
            surface = b1.filter((pl.col("asset") == asset) & (pl.col("session_date") == session))
            flow = b2.filter((pl.col("asset") == asset) & (pl.col("session_date") == session))
            if not surface.height:
                surface = build_session_surface(
                    asset, session, paths, origins, grid.close, base["rv_back_30"].to_numpy()
                )
            if not flow.height:
                flow, reason = build_session_flow(
                    asset, session, paths, origins, grid.close, grid.open
                )
                if flow is None:
                    raise ValueError(f"RP4_FLOW_QUALITY:{reason}")
            if surface is None or not surface.height:
                raise ValueError("RP4_SURFACE_QUALITY")
        except (OSError, pl.exceptions.PolarsError, ValueError) as error:
            exclusions.append(
                {
                    "asset": asset,
                    "session_date": session,
                    "origins": base.height,
                    "reason": f"{type(error).__name__}:{error}",
                }
            )
            continue
        local_bars = bar_by_asset[asset]
        local_dates = sorted(
            day
            for day in local_bars["session_date"].unique().to_list()
            if day <= date.fromisoformat(session)
        )[-7:]
        har = har_features_for_session(
            local_bars.filter(pl.col("session_date").is_in(local_dates)), base.select(KEYS)
        )
        combined = base
        for frame in (
            surface.select(KEYS + b1_names),
            flow.select(KEYS + b2_names),
            new_options,
            har,
            rebuilt_target.filter((pl.col("asset") == asset) & (pl.col("session_date") == session)),
        ):
            combined = combined.join(frame, on=KEYS, how="left", validate="1:1")
        combined = (
            combined.with_columns(
                pl.Series(
                    "forecast_origin_utc",
                    [origin_timestamp(session, int(x)) for x in origins],
                    dtype=pl.Datetime("us", "UTC"),
                ),
                rate=pl.lit(rate),
                dividend_cash_prior365=pl.lit(cash),
                rate_source_date=pl.lit(max((day for day in rates if day < session), default=None)),
                dividend_yield=pl.Series(
                    [cash / grid.close[int(minute) - 3] for minute in origins], dtype=pl.Float64
                ),
            )
            .with_columns(
                (pl.col("forecast_origin_utc") + pl.duration(minutes=30)).alias("target_end_utc")
            )
            .sort(KEYS)
        )
        shard.parent.mkdir(parents=True, exist_ok=True)
        combined.write_parquet(shard)
        for path in paths:
            if path not in seen_sources:
                seen_sources[path] = sha256(Path(path))
        write_json(
            receipt,
            {
                "spec_sha256": args.spec_sha256,
                "code_sha256": code_hash,
                "input_identity": input_identity,
                "sha256": sha256(shard),
                "rows": combined.height,
                "source_sha256": {p: seen_sources[p] for p in paths},
            },
        )
        all_shards.append(shard)
        if count % 20 == 0:
            print(
                f"RP4_MATERIALIZE:{count}:shards={len(all_shards)}:excluded={len(exclusions)}",
                flush=True,
            )
    if not all_shards:
        write_json(output / "exclusions.json", exclusions)
        raise ValueError("RP4_NO_MATERIALIZED_SESSION_ASSETS")
    panel = pl.concat([pl.read_parquet(path) for path in all_shards], how="diagonal_relaxed").sort(
        KEYS
    )
    assert_unique(panel)
    panel = attach_secondaries(panel, b2, events)
    panel_path = output / "panel.parquet"
    panel.write_parquet(panel_path)
    coverage_path = output / "coverage.csv"
    coverage_table(panel).write_csv(coverage_path)
    write_json(output / "exclusions.json", exclusions)
    inputs = {str(path): sha256(path) for path in input_paths}
    if inputs != input_pins:
        raise ValueError("RP4_INPUT_SOURCE_CHANGED_DURING_MATERIALIZATION")
    manifest = {
        "stage": args.stage,
        "spec_sha256": args.spec_sha256,
        "code_sha256": code_hash,
        "requested_start": args.start,
        "requested_end": args.end,
        "rows": panel.height,
        "sessions": panel["session_date"].n_unique(),
        "assets": sorted(panel["asset"].unique()),
        "first_session": panel["session_date"].min(),
        "last_session": panel["session_date"].max(),
        "target_rows_finite": panel["rv30"].is_finite().fill_null(False).sum(),
        "exclusions": exclusions,
        "input_sha256": inputs,
        "input_identity": input_identity,
        "artifacts": {
            str(path): sha256(path)
            for path in [
                panel_path,
                coverage_path,
                output / "target_comparison.json",
                output / "exclusions.json",
            ]
        },
        "licensed_tape_sha256_in_session_receipts": True,
        "oi_previous_close_provenance": "OWNER_ATTESTED_NOT_CLIENT_RECEIPT_CERTIFIED",
        "model_fits": 0,
        "RESEARCH_ONLY": True,
        "capital_go": False,
    }
    if sha256(Path(__file__)) != code_hash or sha256(args.spec) != args.spec_sha256:
        raise ValueError("RP4_RUNTIME_SOURCE_CHANGED")
    write_json(output / "manifest.json", manifest)
    print(
        json.dumps(
            {
                "status": "PASS_MATERIALIZATION",
                "rows": panel.height,
                "manifest": str(output / "manifest.json"),
                "manifest_sha256": sha256(output / "manifest.json"),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
