"""RP4 v3 candidate feature: signed intraday customer gamma imbalance, target-blind.

Why this exists: the v1 dealer measures use prior-close open interest with a sign
convention. That is a stock. The hedging-feedback mechanism in the literature is driven by
the *flow* of customer-initiated option trades during the session: every customer buy of
gamma leaves a dealer short gamma who must hedge into moves. This feature is that flow,
signed by the tape's own aggressor tag, accumulated from the open to the origin cutoff.

Definition (this text is the contract for an independent re-derivation):

  For asset a, session d and origin minute m, the origin is 09:30 New York + m minutes
  and the cutoff is origin - 120 s applied to ``created_at`` (identical to the RP4 grid).
  Universe: option trades of ``a`` on ``d`` read from the same tape files the RP4 panel
  used (``materialize.tape_index``), keeping the same validity filter as
  ``materialize.build_new_option_features`` (IV in [0.01, 5], nbbo_bid > 0,
  nbbo_ask > nbbo_bid, strike > 0, size > 0, option_type in {call, put}) plus
  execution inside the session minute grid and 0 <= DTE <= 90.
  Direction: +1 when ``tags`` contains ``ask_side``, -1 when it contains ``bid_side``,
  else 0; multi-leg prints (block 6 ``_multileg_size`` > 0) are 0. Identical to
  ``rp2_block6_flow_panel``.
  Spot at the trade: block 6 ``mark_price(minute_of_trade, closes, opens)`` on the
  session grid built by ``mds650.rp2.bars.build_session_grid`` from the RP4 bars.
  Tenor: ``option_clock.time_to_expiry_years(expiry_close_timestamps(expiry), executed)``.
  Gamma: the ``materialize.gamma_with_carry`` formula evaluated at the trade's own spot,
  with the session's Treasury rate and dividend cash from ``materialize.exogenous_sources``
  and ``carry_for_session`` (dividend yield = cash / spot at the trade).
  Exposure per trade: direction * size * 100 * gamma * spot_trade ** 2, the same units as
  ``rp4_dealer_gamma_net``.
  Features at the origin, cumulative over trades with created_at <= cutoff:
    rp4_gamma_imb_total         sum of exposure over all valid trades
    rp4_gamma_imb_near_spot     restricted to |strike / spot_trade - 1| <= 0.05
    rp4_gamma_imb_near_short    near spot and DTE <= 7
    rp4_gamma_imb_signed_trades count of trades with direction != 0 and finite exposure
  A session-asset without a bar grid or without any valid trade yields NaN. Zero signed
  trades before the cutoff yields 0.0 sums and a 0 count: that is information, not a gap.

No target, loss or metric is read. Outputs are keyed by (asset, session_date, origin_minute).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl

WORKTREE = Path(os.environ.get(
    "RP4_WORKTREE", r"private-input/1909d6c989bb81e6f0ff"))
for sub in ("artifacts/rp4_code", "scripts"):
    p = str(WORKTREE / sub)
    if p not in sys.path:
        sys.path.insert(0, p)

import materialize as mz  # noqa: E402  (research's RP4 materializer: same inputs, same helpers)
from mds650.rp2.bars import build_session_grid  # noqa: E402
from mds650.rp2.option_clock import expiry_close_timestamps, time_to_expiry_years  # noqa: E402
from rp2_block6_flow_panel import _multileg_size, mark_price  # noqa: E402

RP4_ROOT = Path("private-input/66c0e77362caa29dd928")
OUT_ROOT = Path("private-input/30dc476bac34db1890c8")
KEYS = ["asset", "session_date", "origin_minute"]
FEATURES = [
    "rp4_gamma_imb_total",
    "rp4_gamma_imb_near_spot",
    "rp4_gamma_imb_near_short",
    "rp4_gamma_imb_signed_trades",
]
TAPE_COLUMNS = [
    "id", "underlying_symbol", "created_at", "executed_at", "implied_volatility", "size",
    "expiry", "strike", "option_type", "nbbo_bid", "nbbo_ask", "tags", "multi_vol",
]
NEAR_SPOT = 0.05
MAX_DTE = 90
SHORT_DTE = 7
CUTOFF_US = 120_000_000
CODE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def gamma_with_carry_vec(
    spot: np.ndarray, strike: np.ndarray, tenor: np.ndarray, iv: np.ndarray,
    rate: float, dividend_yield: np.ndarray,
) -> np.ndarray:
    """``materialize.gamma_with_carry`` with a per-trade spot and dividend yield."""
    valid = (
        np.isfinite(spot) & (spot > 0) & np.isfinite(strike) & (strike > 0)
        & np.isfinite(tenor) & (tenor > 0) & np.isfinite(iv) & (iv > 0)
        & np.isfinite(dividend_yield) & math.isfinite(rate)
    )
    out = np.full(strike.shape, math.nan)
    s, k, t, v, q = spot[valid], strike[valid], tenor[valid], iv[valid], dividend_yield[valid]
    root = v * np.sqrt(t)
    d1 = (np.log(s / k) + (rate - q + 0.5 * v**2) * t) / root
    out[valid] = np.exp(-q * t - 0.5 * d1**2) / (math.sqrt(2 * math.pi) * s * root)
    return out


def session_gamma_imbalance(
    tape: pl.DataFrame, asset: str, session: str, origins: np.ndarray,
    closes: np.ndarray, opens: np.ndarray, rate: float, dividend_cash: float,
) -> pl.DataFrame:
    """Cumulative signed gamma exposure at each origin cutoff for one asset-session."""
    rows = [{"asset": asset, "session_date": session, "origin_minute": int(m)} for m in origins]
    empty = pl.DataFrame(rows).with_columns([pl.lit(math.nan).alias(c) for c in FEATURES])
    if closes.size == 0 or not math.isfinite(rate) or not math.isfinite(dividend_cash):
        return empty
    tape = tape.filter(
        (pl.col("underlying_symbol") == asset)
        & pl.col("implied_volatility").is_between(0.01, 5.0)
        & (pl.col("nbbo_bid") > 0) & (pl.col("nbbo_ask") > pl.col("nbbo_bid"))
        & (pl.col("strike") > 0) & (pl.col("size") > 0)
        & pl.col("option_type").is_in(["call", "put"])
    ).sort("created_at")
    if not tape.height:
        return empty
    created = tape["created_at"].cast(pl.Datetime("us", "UTC")).cast(pl.Int64).to_numpy()
    executed = tape["executed_at"].cast(pl.Datetime("us", "UTC")).cast(pl.Int64).to_numpy()
    strike = tape["strike"].cast(pl.Float64).to_numpy()
    iv = tape["implied_volatility"].cast(pl.Float64).to_numpy()
    size = tape["size"].cast(pl.Float64).to_numpy()
    expiry = tape["expiry"].cast(pl.Date).to_numpy()
    is_call = (tape["option_type"] == "call").to_numpy()
    tags = tape["tags"].cast(pl.Utf8).fill_null("")
    direction = np.where(
        tags.str.contains("ask_side").to_numpy(), 1.0,
        np.where(tags.str.contains("bid_side").to_numpy(), -1.0, 0.0),
    )
    expiry_day = expiry.astype("datetime64[D]").astype(np.int64)
    keys = expiry_day * 20_000_000 + np.round(strike * 1000.0).astype(np.int64) * 2 + is_call.astype(np.int64)
    multileg = _multileg_size(keys, tape["multi_vol"].cast(pl.Float64).fill_null(0.0).to_numpy(), size)
    direction = np.where(multileg > 0.0, 0.0, direction)

    open_us = int(mz.origin_timestamp(session, 0).timestamp() * 1_000_000)
    minute_of_trade = ((executed - open_us) // 60_000_000).astype(np.int64)
    inside = (minute_of_trade >= 0) & (minute_of_trade < closes.size)
    spot = np.full(strike.shape, math.nan)
    if inside.any():
        spot[inside] = mark_price(minute_of_trade[inside], closes, opens)
    dte = (expiry - np.datetime64(session, "D")).astype("timedelta64[D]").astype(np.int64)
    expiry_us = expiry_close_timestamps(expiry, "America/New_York")
    tenor = time_to_expiry_years(expiry_us, executed)
    with np.errstate(divide="ignore", invalid="ignore"):
        q = np.where(np.isfinite(spot) & (spot > 0), dividend_cash / spot, math.nan)
    gamma = gamma_with_carry_vec(spot, strike, tenor, iv, rate, q)
    exposure = direction * size * 100.0 * gamma * spot**2
    valid = inside & (dte >= 0) & (dte <= MAX_DTE) & np.isfinite(exposure)
    if not valid.any():
        return empty
    exposure = np.where(valid, exposure, 0.0)
    with np.errstate(divide="ignore", invalid="ignore"):
        near = valid & (np.abs(strike / spot - 1.0) <= NEAR_SPOT + 1e-12)
    short = near & (dte <= SHORT_DTE)
    signed = valid & (direction != 0.0)
    cum_total = np.cumsum(exposure)
    cum_near = np.cumsum(np.where(near, exposure, 0.0))
    cum_short = np.cumsum(np.where(short, exposure, 0.0))
    cum_count = np.cumsum(signed.astype(np.int64))
    out: list[dict[str, Any]] = []
    for m in origins:
        cutoff = int(mz.origin_timestamp(session, int(m)).timestamp() * 1_000_000) - CUTOFF_US
        hi = int(np.searchsorted(created, cutoff, side="right"))
        row = {"asset": asset, "session_date": session, "origin_minute": int(m)}
        if hi == 0:
            row.update(dict.fromkeys(FEATURES, 0.0))
        else:
            row.update({
                "rp4_gamma_imb_total": float(cum_total[hi - 1]),
                "rp4_gamma_imb_near_spot": float(cum_near[hi - 1]),
                "rp4_gamma_imb_near_short": float(cum_short[hi - 1]),
                "rp4_gamma_imb_signed_trades": float(cum_count[hi - 1]),
            })
        out.append(row)
    return pl.DataFrame(out)


def _read_tape(paths: list[str]) -> pl.DataFrame:
    frames = [pl.read_parquet(p, columns=TAPE_COLUMNS) for p in dict.fromkeys(paths)]
    tape = pl.concat(frames, how="vertical_relaxed")
    return tape.unique(subset="id", keep="first", maintain_order=True)


def _worker(job: dict[str, Any]) -> dict[str, Any]:
    """One session date: read each tape file once, build every asset's rows."""
    session = job["session"]
    all_paths = sorted({p for paths in job["paths"].values() for p in paths})
    tape = _read_tape(all_paths) if all_paths else pl.DataFrame()
    frames = []
    for asset, spec in job["assets"].items():
        sub = tape.filter(pl.col("underlying_symbol") == asset) if tape.height else tape
        frames.append(session_gamma_imbalance(
            sub, asset, session, np.asarray(spec["origins"], dtype=np.int64),
            np.asarray(spec["closes"], dtype=np.float64), np.asarray(spec["opens"], dtype=np.float64),
            float(spec["rate"]), float(spec["dividend_cash"]),
        ))
    frame = pl.concat(frames, how="vertical_relaxed").sort(KEYS)
    shard = Path(job["shard"])
    shard.parent.mkdir(parents=True, exist_ok=True)
    frame.write_parquet(shard)
    return {"session": session, "rows": frame.height, "shard": str(shard),
            "sha256": mz.sha256(shard), "tape_files": all_paths}


def build_jobs(start: str, end: str) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    panel = (pl.scan_parquet(RP4_ROOT / "b1_complete_v1/panel.parquet").select(KEYS)
             .with_columns(pl.col("session_date").cast(pl.Utf8))
             .filter((pl.col("session_date") >= start) & (pl.col("session_date") <= end)).collect())
    bars, bar_paths = mz.load_rp4_bars(RP4_ROOT, end)
    rates, dividends, exo_paths = mz.exogenous_sources(RP4_ROOT)
    index = mz.tape_index(RP4_ROOT)
    jobs: list[dict[str, Any]] = []
    missing: list[str] = []
    for session in sorted(panel["session_date"].unique().to_list()):
        day = datetime.fromisoformat(session).date()
        job: dict[str, Any] = {"session": session, "paths": {}, "assets": {},
                               "shard": str(OUT_ROOT / "shards" / f"{session}.parquet")}
        for asset in sorted(panel.filter(pl.col("session_date") == session)["asset"].unique().to_list()):
            # The registered inventory keys the unpartitioned 2026-07-13..17 day files as
            # "__ALL__"; read_new_tape filters by underlying_symbol, so they serve every asset.
            paths = index.get((session, asset), []) or index.get((session, "__ALL__"), [])
            if not paths:
                missing.append(f"{session}/{asset}")
                continue
            group = bars.filter((pl.col("asset") == asset) & (pl.col("session_date") == day))
            if not group.height:
                missing.append(f"{session}/{asset}:bars")
                continue
            grid = build_session_grid(group, session=day)
            rate, cash = mz.carry_for_session(session, asset, rates, dividends)
            origins = panel.filter((pl.col("session_date") == session) & (pl.col("asset") == asset))["origin_minute"].to_list()
            job["paths"][asset] = paths
            job["assets"][asset] = {"origins": origins, "closes": grid.close.tolist(),
                                    "opens": grid.open.tolist(), "rate": rate, "dividend_cash": cash}
        if job["assets"]:
            jobs.append(job)
    meta = {"bar_sources": [str(p) for p in bar_paths], "exogenous_sources": [str(p) for p in exo_paths],
            "panel_keys_rows": panel.height, "missing_asset_sessions": missing}
    return jobs, meta


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="2024-08-02")
    ap.add_argument("--end", default="2026-09-04")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--limit", type=int, default=0, help="only the first N sessions (smoke run)")
    args = ap.parse_args(argv)
    t0 = time.time()
    jobs, meta = build_jobs(args.start, args.end)
    if args.limit:
        jobs = jobs[: args.limit]
    print(f"jobs={len(jobs)} sessions; missing={len(meta['missing_asset_sessions'])}", flush=True)
    receipts = []
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(_worker, job): job["session"] for job in jobs}
        for i, fut in enumerate(as_completed(futures), 1):
            r = fut.result()
            receipts.append(r)
            if i % 25 == 0 or i == len(jobs):
                print(f"  {i}/{len(jobs)} sessions done ({time.time()-t0:.0f}s)", flush=True)
    receipts.sort(key=lambda r: r["session"])
    frame = pl.concat([pl.read_parquet(r["shard"]) for r in receipts], how="vertical_relaxed").sort(KEYS)
    OUT_ROOT.mkdir(parents=True, exist_ok=True)
    out = OUT_ROOT / f"gamma_imbalance_{args.start}_{args.end}.parquet"
    frame.write_parquet(out)
    manifest = {
        "feature": "rp4_gamma_imbalance_v1", "code_sha256": CODE_SHA256, "definition": __doc__,
        "parameters": {"near_spot": NEAR_SPOT, "max_dte": MAX_DTE, "short_dte": SHORT_DTE,
                        "cutoff_seconds": 120, "start": args.start, "end": args.end},
        "rows": frame.height, "columns": frame.columns, "output": str(out), "output_sha256": mz.sha256(out),
        "sessions": [{"session": r["session"], "rows": r["rows"], "shard_sha256": r["sha256"],
                      "tape_files": r["tape_files"]} for r in receipts],
        **meta,
        "targets_read": 0, "built_at_utc": datetime.now(UTC).isoformat(),
    }
    io.open(OUT_ROOT / "manifest.json", "w", encoding="utf-8").write(json.dumps(manifest, indent=1))
    nf = frame.select([(pl.col(c).is_null() | pl.col(c).is_nan()).mean().alias(c) for c in FEATURES]).row(0)
    print(f"rows={frame.height} output={out}\nsha256={manifest['output_sha256']}\nnon-finite share per feature: "
          + ", ".join(f"{c}={v:.3f}" for c, v in zip(FEATURES, nf)) + f"\nelapsed={time.time()-t0:.0f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
