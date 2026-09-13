"""Opt-in RP4 activity overlay; frozen IV-dependent producers remain unchanged."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import materialize_iv as baseline
import numpy as np
import polars as pl
import rp2_block6_flow_panel as flow

ACTIVITY_COLUMNS = tuple(
    f"b2_{window}_{name}"
    for window, _ in flow.WINDOWS
    for name in ("trades", "contracts", "size", "premium")
)


def activity_features(raw: pl.DataFrame, base: pl.DataFrame, grid: Any) -> pl.DataFrame:
    """Compute only IV-independent totals using the registered two-clock windows."""
    if base.is_empty() or base.select("asset", "session_date").n_unique() != 1:
        raise ValueError("RP4_ACTIVITY_REQUIRES_ONE_SESSION")
    baseline.v1.assert_unique(base)
    asset, session = str(base["asset"][0]), str(base["session_date"][0])
    keys = base.select(baseline.KEYS)
    for name in ("created_at", "executed_at"):
        dtype = raw.schema[name]
        if not isinstance(dtype, pl.Datetime) or dtype.time_zone != "UTC":
            raise ValueError("RP4_ACTIVITY_CLOCK_REQUIRES_UTC")
    tape = raw.filter(
        (pl.col("underlying_symbol") == asset)
        & pl.col("size").is_finite()
        & (pl.col("size") > 0)
        & pl.col("strike").is_finite()
        & (pl.col("strike") > 0)
        & pl.col("premium").is_finite()
        & (pl.col("premium") >= 0)
        & pl.col("expiry").is_not_null()
        & (pl.col("expiry") >= datetime.fromisoformat(session).date())
        & pl.col("option_type").is_in(["call", "put"])
        & pl.col("executed_at").is_not_null()
        & pl.col("created_at").is_not_null()
        & (pl.col("created_at") >= pl.col("executed_at"))
    ).with_columns(pl.col("created_at", "executed_at").dt.cast_time_unit("us"))
    tape = flow._in_session(tape, session, grid.close, grid.open).sort("created_at")
    if tape.height < flow.MINIMUM_SESSION_PRINTS:
        return keys.with_columns(pl.lit(None, pl.Float64).alias(n) for n in ACTIVITY_COLUMNS)
    created = tape["created_at"].cast(pl.Int64).to_numpy()
    executed = tape["executed_at"].cast(pl.Int64).to_numpy()
    session_open = (
        datetime.fromisoformat(session).replace(tzinfo=flow.NY)
        + timedelta(minutes=flow.SESSION_OPEN_MINUTE)
    ).astimezone(UTC)
    rows = []
    for minute in base["origin_minute"]:
        cutoff = session_open + timedelta(minutes=int(minute), seconds=-flow.CUTOFF_SECONDS)
        cutoff_us = int(np.datetime64(cutoff.replace(tzinfo=None), "us").astype(np.int64))
        visible = np.searchsorted(created, cutoff_us, side="right")
        row = {}
        for label, seconds in flow.WINDOWS:
            # ponytail: scan visible rows per origin; use indexed sums if profiling warrants it.
            selected = (executed[:visible] >= cutoff_us - seconds * 1_000_000) & (
                executed[:visible] <= cutoff_us
            )
            window = tape.head(int(visible)).filter(pl.Series(selected))
            row.update(
                {
                    f"b2_{label}_trades": float(window.height),
                    f"b2_{label}_contracts": float(
                        window.select("expiry", "strike", "option_type").n_unique()
                    ),
                    f"b2_{label}_size": float(window["size"].sum()),
                    f"b2_{label}_premium": float(window["premium"].sum()),
                }
            )
        rows.append(row)
    return keys.hstack(pl.DataFrame(rows))


def option_features(
    raw: pl.DataFrame,
    base: pl.DataFrame,
    grid: Any,
    columns: list[str],
    *,
    filtered: bool,
    independent_activity: bool = False,
) -> pl.DataFrame:
    """Default is exact baseline; explicit opt-in replaces only eight activity columns."""
    original = baseline.option_features(raw, base, grid, columns, filtered=filtered)
    names = [name for name in columns if name in ACTIVITY_COLUMNS]
    if not independent_activity or not names:
        return original
    replacement = activity_features(raw, base, grid)
    return baseline.replace_columns(original, replacement, names).select(baseline.KEYS + columns)
