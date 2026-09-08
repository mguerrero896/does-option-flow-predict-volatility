"""Read-only descriptive audit of expiry availability and minute-bar integrity."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

for _name in (
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "POLARS_MAX_THREADS",
):
    os.environ[_name] = "2"

import numpy as np  # noqa: E402
import polars as pl  # noqa: E402
import psutil  # noqa: E402
from artifacts.rp4_code import materialize as source  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ("AAPL", "AMZN", "META", "MSFT", "NVDA", "TSLA")
NY = ZoneInfo("America/New_York")
PANEL_SHA = "a63ff5e61092d2bc00917c5de4e0e73f928005acc475f46370348eaca6ad4637"
KEYS = ["asset", "session_date", "origin_minute"]
POP = "rp4_surface_populated_cells"
ATM = "rp4_iv_dte_0_1_m_097_103"
ZERO = "b1_zero_dte_contracts"
PANEL_COLUMNS = KEYS + [POP, ATM, ZERO]
TAPE_COLUMNS = [
    "id",
    "underlying_symbol",
    "created_at",
    "executed_at",
    "expiry",
    "implied_volatility",
    "size",
    "strike",
    "option_type",
    "nbbo_bid",
    "nbbo_ask",
]
WEEKDAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")


def sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write_once(path: Path, payload: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError("IMMUTABLE_AUDIT_OUTPUT_CHANGED:" + path.name)
        return
    with path.open("xb") as handle:
        handle.write(payload)


def json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode()


def csv_bytes(rows: list[dict[str, Any]]) -> bytes:
    stream = io.BytesIO()
    pl.DataFrame(rows, infer_schema_length=None).write_csv(stream)
    return stream.getvalue()


def finite_stat(values: pl.Series, which: str) -> float | None:
    clean = values.cast(pl.Float64).filter(values.cast(pl.Float64).is_finite().fill_null(False))
    if not len(clean):
        return None
    result = clean.mean() if which == "mean" else clean.median()
    if not isinstance(result, (int, float)):
        raise ValueError("NUMERIC_STATISTIC_TYPE")
    return float(result)


def coverage_rows(panel: pl.DataFrame, transition: str) -> list[dict[str, Any]]:
    if panel.select(KEYS).n_unique() != panel.height:
        raise ValueError("PANEL_DUPLICATE_KEYS")
    dates = pl.col("session_date").cast(pl.String)
    lower = (date.fromisoformat(transition) - timedelta(days=28)).isoformat()
    upper = (date.fromisoformat(transition) + timedelta(days=28)).isoformat()
    rows: list[dict[str, Any]] = []
    for scope, frame in (
        ("all_available_origins", panel),
        (
            "transition_plus_minus_28_calendar_days",
            panel.filter(dates.is_between(pl.lit(lower), pl.lit(upper))),
        ),
    ):
        frame = frame.with_columns(
            dates.str.to_date().dt.weekday().alias("weekday_number"),
            pl.when(dates < transition)
            .then(pl.lit("before"))
            .otherwise(pl.lit("from_date"))
            .alias("period"),
        )
        for asset in ("ALL", *ASSETS):
            selected = frame if asset == "ALL" else frame.filter(pl.col("asset") == asset)
            for (period, weekday), group in selected.group_by("period", "weekday_number"):
                finite_atm = group[ATM].is_finite().fill_null(False)
                finite_zero = group[ZERO].is_finite().fill_null(False)
                rows.append(
                    {
                        "scope": scope,
                        "transition_date": transition,
                        "asset": asset,
                        "period": period,
                        "weekday": WEEKDAYS[int(weekday) - 1],
                        "N_origins": group.height,
                        "N_sessions": group["session_date"].n_unique(),
                        "first_session": str(group["session_date"].min()),
                        "last_session": str(group["session_date"].max()),
                        "surface_populated_cells_mean": finite_stat(group[POP], "mean"),
                        "surface_populated_cells_finite_N": int(
                            group[POP].is_finite().fill_null(False).sum()
                        ),
                        "atm_0_1dte_present_N": int(finite_atm.sum()),
                        "atm_0_1dte_presence_pct": 100.0 * int(finite_atm.sum()) / group.height,
                        "zero_dte_contracts_median_finite": finite_stat(group[ZERO], "median"),
                        "zero_dte_contracts_finite_N": int(finite_zero.sum()),
                        "zero_dte_contracts_positive_N": int(
                            (finite_zero & (group[ZERO] > 0)).sum()
                        ),
                    }
                )
    return sorted(rows, key=lambda r: (r["scope"], r["asset"], r["period"], r["weekday"]))


def select_projected_first_versions(tape: pl.DataFrame) -> tuple[pl.DataFrame, dict[str, int]]:
    """Same first-available ordering as the producer, projected to count-relevant fields."""
    tape = tape.select(TAPE_COLUMNS)
    if tape["id"].null_count():
        raise ValueError("TAPE_ID_MISSING")
    distinct = tape.unique(maintain_order=True)
    ordered = distinct.filter(
        pl.col("created_at").is_not_null() & pl.col("executed_at").is_not_null()
    ).with_columns(pl.max_horizontal("created_at", "executed_at").alias("available"))
    ordered = ordered.sort("available", maintain_order=True)
    first = ordered.unique(subset="id", keep="first", maintain_order=True)
    return first, {
        "raw_rows": tape.height,
        "projected_exact_duplicates": tape.height - distinct.height,
        "projected_conflicting_ids": distinct.group_by("id").len().filter(pl.col("len") > 1).height,
        "unorderable_rows": distinct.height - ordered.height,
        "later_projected_versions_ignored": ordered.height - first.height,
    }


def tape_counts(tape: pl.DataFrame, asset: str, session: str) -> dict[str, Any]:
    first, counts = select_projected_first_versions(tape)
    clean = first.filter(
        (pl.col("underlying_symbol") == asset)
        & pl.col("implied_volatility").is_finite()
        & pl.col("implied_volatility").is_between(0.03, 3.0)
        & (pl.col("nbbo_bid") > 0)
        & (pl.col("nbbo_ask") > pl.col("nbbo_bid"))
        & (pl.col("strike") > 0)
        & (pl.col("size") > 0)
        & pl.col("option_type").is_in(["call", "put"])
        & pl.col("expiry").is_not_null()
        & (pl.col("expiry") >= date.fromisoformat(session))
    )
    opening = source.origin_timestamp(session, 0)
    closing = source.origin_timestamp(session, 390)
    valid = clean.filter((pl.col("executed_at") >= opening) & (pl.col("executed_at") < closing))
    available = valid.filter(pl.col("available") <= closing - timedelta(seconds=120))
    expiries = sorted(available["expiry"].unique().to_list())
    row: dict[str, Any] = {
        "asset": asset,
        "session_date": session,
        "weekday": WEEKDAYS[date.fromisoformat(session).weekday()],
        "status": "VERIFIED_LOCAL",
        **counts,
        "valid_regular_rows": valid.height,
        "available_by_close_minus_120s_rows": available.height,
        "valid_distinct_expiries_full_regular_session": valid["expiry"].n_unique(),
        "distinct_expiries_by_close_minus_120s": len(expiries),
        "expiry_dates": ";".join(day.isoformat() for day in expiries),
    }
    for daynum, dayname in enumerate(WEEKDAYS):
        row["expiry_count_" + dayname.lower()] = sum(day.weekday() == daynum for day in expiries)
    same_day = available.filter(pl.col("expiry") == date.fromisoformat(session))
    row["zero_dte_trade_rows"] = same_day.height
    row["zero_dte_distinct_contracts_day_union"] = same_day.select(
        "expiry", "strike", "option_type"
    ).n_unique()
    early = available.filter(pl.col("expiry").dt.weekday().is_in([1, 3]))
    earliest = early["available"].min()
    if early.height and not isinstance(earliest, datetime):
        raise ValueError("AVAILABLE_CLOCK_TYPE")
    row["first_mon_wed_available_ny"] = (
        earliest.astimezone(NY).isoformat() if isinstance(earliest, datetime) else None
    )
    return row


def bar_audit(
    frame: pl.DataFrame, asset: str, session: str, event_hm: str
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    frame = frame.sort("bar_start_utc")
    if frame["asset"].unique().to_list() != [asset]:
        raise ValueError("BAR_ASSET_IDENTITY")
    stamps = frame["bar_start_utc"].to_list()
    expected = {source.origin_timestamp(session, minute) for minute in range(390)}
    observed = set(stamps)
    columns = ["open", "high", "low", "close", "volume"]
    values = frame.select(columns).to_numpy().astype(float)
    opened, high, low, close, volume = values.T
    nonfinite = ~np.isfinite(values).all(axis=1)
    invalid_ohlc = (
        (values[:, :4] <= 0).any(axis=1)
        | (high < np.maximum(opened, close))
        | (low > np.minimum(opened, close))
        | (high < low)
    )
    returns = np.full(len(close), np.nan)
    gap = np.full(len(close), np.nan)
    if len(close) > 1:
        returns[1:] = np.log(close[1:] / close[:-1]) * 10000
        gap[1:] = np.log(opened[1:] / close[:-1]) * 10000
    med = float(np.median(volume[np.isfinite(volume)]))
    event = datetime.fromisoformat(session + "T" + event_hm).replace(tzinfo=NY)
    positions = [i for i, stamp in enumerate(stamps) if stamp == event]
    if len(positions) != 1 or positions[0] == 0 or positions[0] + 1 >= len(close):
        raise ValueError("BAR_EVENT_IDENTITY")
    i = positions[0]
    previous = volume[max(0, i - 30) : i]
    prior_median = float(np.median(previous[np.isfinite(previous)]))
    summary = {
        "asset": asset,
        "session_date": session,
        "event_bar_start_ny": event.isoformat(),
        "N_bars": frame.height,
        "unique_minutes": len(observed),
        "duplicate_minutes": frame.height - len(observed),
        "missing_regular_minutes": len(expected - observed),
        "outside_regular_minutes": len(observed - expected),
        "nonfinite_ohlcv_rows": int(nonfinite.sum()),
        "inconsistent_ohlc_rows": int(invalid_ohlc.sum()),
        "negative_volume_rows": int((volume < 0).sum()),
        "zero_volume_rows": int((volume == 0).sum()),
        "full_session_volume_median": med,
        "prior_30_minutes_volume_median": prior_median,
        "event_close_to_close_log_return_bp": float(returns[i]),
        "next_close_to_close_log_return_bp": float(returns[i + 1]),
        "event_simple_return_bp": float((close[i] / close[i - 1] - 1) * 10000),
        "next_simple_return_bp": float((close[i + 1] / close[i] - 1) * 10000),
        "event_volume": float(volume[i]),
        "next_volume": float(volume[i + 1]),
        "event_volume_over_session_median": float(volume[i] / med),
        "next_volume_over_session_median": float(volume[i + 1] / med),
        "event_open_gap_log_bp": float(gap[i]),
        "next_open_gap_log_bp": float(gap[i + 1]),
        "two_minute_net_log_return_bp": float(returns[i] + returns[i + 1]),
        "max_abs_close_to_close_log_return_bp": float(np.nanmax(np.abs(returns))),
        "event_abs_return_rank_within_session": int(np.sum(np.abs(returns) > abs(returns[i])) + 1),
        "internal_consistency_not_external_price_validation": True,
    }
    windows = []
    for j in range(max(1, i - 10), min(i + 11, len(close))):
        windows.append(
            {
                "asset": asset,
                "session_date": session,
                "bar_start_ny": stamps[j].astimezone(NY).isoformat(),
                "minutes_from_event": int((stamps[j] - event).total_seconds() / 60),
                "close_to_close_log_return_bp": float(returns[j]),
                "open_gap_log_bp": float(gap[j]),
                "volume_over_session_median": float(volume[j] / med),
                "gap_from_previous_bar_seconds": (stamps[j] - stamps[j - 1]).total_seconds(),
            }
        )
    return summary, windows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--panel", type=Path, required=True)
    parser.add_argument("--lineage", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/rp4_market_audit")
    args = parser.parse_args()
    psutil.Process().nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
    if pl.thread_pool_size() > 2:
        raise ValueError("RESOURCE_CAP")
    pins = json.loads(args.lineage.read_text(encoding="utf-8"))["sha256"]
    normalized_pins = {str(Path(key).resolve()): value for key, value in pins.items()}
    provenance: list[dict[str, Any]] = []

    def verify(path: Path, alias: str, expected: str | None = None) -> str:
        digest = sha256(path)
        recorded = normalized_pins.get(str(path.resolve()))
        if expected is not None and recorded is not None and expected != recorded:
            raise ValueError("RECEIPT_LINEAGE_HASH_CONFLICT:" + alias)
        previous = expected or recorded
        if previous is None or digest != previous:
            raise ValueError("SOURCE_HASH_NOT_BOUND:" + alias)
        provenance.append(
            {
                "alias": alias,
                "sha256": digest,
                "bytes": path.stat().st_size,
                "binding": "matches_preexisting_pin",
            }
        )
        return digest

    verify(args.panel, "frozen_feature_panel", PANEL_SHA)
    panel = pl.read_parquet(args.panel, columns=PANEL_COLUMNS)
    if set(panel["asset"].unique().to_list()) != set(ASSETS):
        raise ValueError("PANEL_ASSET_SET")
    daily_features = (
        panel.group_by("asset", "session_date")
        .agg(
            pl.len().alias("N_origins"),
            pl.col(POP).mean().alias("surface_populated_cells_mean"),
            (pl.col(ATM).is_finite().fill_null(False).mean() * 100).alias(
                "atm_0_1dte_presence_pct"
            ),
            pl.col(ZERO)
            .filter(pl.col(ZERO).is_finite())
            .median()
            .alias("zero_dte_contracts_median"),
        )
        .sort("session_date", "asset")
    )
    index = source.tape_index(args.source_root)
    start, end = "2026-01-12", "2026-02-13"
    dates = sorted({d for d, asset in index if start <= d <= end and asset in ASSETS})
    daily: list[dict[str, Any]] = []
    for day in dates:
        for asset in ASSETS:
            paths = list(dict.fromkeys(index.get((day, asset), index.get((day, "__ALL__"), []))))
            if not paths:
                raise ValueError("TAPE_INDEX_MISSING:" + asset + ":" + day)
            for j, name in enumerate(paths):
                verify(Path(name), f"option_tape/{day}/{asset}/{j}")
            tape = pl.concat(
                [
                    pl.read_parquet(name, columns=TAPE_COLUMNS).filter(
                        pl.col("underlying_symbol") == asset
                    )
                    for name in paths
                ],
                how="vertical_relaxed",
            )
            daily.append(tape_counts(tape, asset, day))
        print(
            json.dumps({"event": "EXPIRY_DAY_COMPLETE", "session": day, "assets": len(ASSETS)}),
            flush=True,
        )
    first_dates = {
        asset: min(
            (
                r["session_date"]
                for r in daily
                if r["asset"] == asset
                and r["expiry_count_monday"] + r["expiry_count_wednesday"] > 0
            ),
            default=None,
        )
        for asset in ASSETS
    }
    if any(value is None or value == dates[0] for value in first_dates.values()):
        raise ValueError("TRANSITION_NOT_BRACKETED_EXPAND_AUDIT_RANGE")
    events, windows = [], []
    for asset, day, hm in (("AMZN", "2026-08-31", "14:00"), ("TSLA", "2026-08-17", "15:25")):
        receipt_path = args.source_root / "manifests/fmp" / day / (asset + ".json")
        receipt_sha = sha256(receipt_path)
        record = json.loads(receipt_path.read_text(encoding="utf-8"))
        if record["status"] != "PASS" or record["session"] != day or record["asset"] != asset:
            raise ValueError("BAR_RECEIPT_IDENTITY")
        if sha256(receipt_path) != receipt_sha:
            raise ValueError("RECEIPT_CHANGED_DURING_READ")
        provenance.append(
            {
                "alias": f"minute_bars_receipt/{day}/{asset}",
                "sha256": receipt_sha,
                "bytes": receipt_path.stat().st_size,
                "binding": "metadata_hash_recorded_at_read",
            }
        )
        path = args.source_root / "data/fmp" / ("date=" + day) / ("asset=" + asset + ".parquet")
        expected = next(
            row["sha256"]
            for row in record["files"]
            if Path(row["path"]).resolve() == path.resolve()
        )
        verify(path, f"minute_bars/{day}/{asset}", expected)
        bars = pl.read_parquet(
            path, columns=["asset", "bar_start_utc", "open", "high", "low", "close", "volume"]
        )
        result, window = bar_audit(bars, asset, day, hm)
        events.append(result)
        windows.extend(window)
    first = min(str(value) for value in first_dates.values())
    coverage = coverage_rows(panel, "2026-01-29")
    if first != "2026-01-29":
        coverage.extend(coverage_rows(panel, first))
    summary = {
        "status": "COMPLETE_DESCRIPTIVE_AUDIT",
        "method": "descriptive_no_fits_no_bootstrap",
        "panel_rows": panel.height,
        "panel_sessions": panel["session_date"].n_unique(),
        "tape_range": [start, end],
        "tape_asset_sessions": len(daily),
        "first_observed_mon_or_wed_expiry_by_asset": first_dates,
        "claim_transition_date": "2026-01-29",
        "bars": events,
        "panel_columns_read": PANEL_COLUMNS,
        "tape_columns_read": TAPE_COLUMNS,
        "source_time_cutoff_seconds": 120,
        "resources": {
            "max_numeric_threads": 2,
            "polars_threads": pl.thread_pool_size(),
            "priority": "BELOW_NORMAL",
        },
        "limitations": [
            "First occurrence in local tape is not the official listing date "
            "or proof of market causality.",
            "Daily expiry union is not the per-origin snapshot count of zero-day contracts.",
            "Coverage uses every panel origin, not an outcome-dependent "
            "or complete-case model mask.",
            "OHLCV continuity is an internal check of one provider, not independent "
            "validation of a traded price or a news explanation.",
            "Source timestamps remain availability proxies; no client receipt times are inferred.",
        ],
        "new_targets": 0,
        "model_fits": 0,
        "bootstrap_replications": 0,
        "downloads": 0,
        "original_files_modified": 0,
    }
    outputs = {
        "summary.json": json_bytes(summary),
        "expiry_daily.csv": csv_bytes(daily),
        "coverage_weekday.csv": csv_bytes(coverage),
        "feature_daily.csv": daily_features.write_csv().encode(),
        "bar_event_windows.csv": csv_bytes(windows),
        "sources.json": json_bytes(
            {"source_lineage_sha256": sha256(args.lineage), "sources": provenance}
        ),
    }
    for name, payload in outputs.items():
        write_once(args.output / name, payload)
    manifest = {
        "status": "COMPLETE",
        "code_sha256": sha256(Path(__file__)),
        "artifacts_sha256": {name: sha256(args.output / name) for name in outputs},
        "source_count": len(provenance),
        "only_new_outputs_written": True,
    }
    write_once(args.output / "manifest.json", json_bytes(manifest))
    print(
        json.dumps(
            {
                "status": "COMPLETE",
                "first_observed": first_dates,
                "bar_events": events,
                "manifest_sha256": sha256(args.output / "manifest.json"),
            },
            allow_nan=False,
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
