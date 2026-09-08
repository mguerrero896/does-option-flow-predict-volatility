"""Synthetic-only tests of the descriptive audit definitions."""

from datetime import date, timedelta

import polars as pl
import pytest
from artifacts.rp4_market_audit_code import audit


def trade(**updates):
    value = {
        "id": "a",
        "underlying_symbol": "AAPL",
        "created_at": audit.source.origin_timestamp("2026-01-29", 10),
        "executed_at": audit.source.origin_timestamp("2026-01-29", 9),
        "expiry": date(2026, 2, 2),
        "implied_volatility": 0.5,
        "size": 2.0,
        "strike": 100.0,
        "option_type": "call",
        "nbbo_bid": 1.0,
        "nbbo_ask": 1.1,
    }
    value.update(updates)
    return value


def test_expiry_counts_use_first_available_quality_and_calendar():
    rows = [
        trade(),
        trade(),
        trade(expiry=date(2026, 2, 4), created_at=audit.source.origin_timestamp("2026-01-29", 20)),
        trade(id="b", expiry=date(2026, 2, 4), implied_volatility=0.01),
        trade(id="c", expiry=date(2026, 2, 4)),
        trade(id="d", expiry=date(2026, 1, 29)),
        trade(id="e", expiry=date(2026, 1, 28)),
        trade(id="f", created_at=audit.source.origin_timestamp("2026-01-29", 389)),
        trade(id="g", executed_at=audit.source.origin_timestamp("2026-01-29", -1)),
    ]
    result = audit.tape_counts(pl.DataFrame(rows), "AAPL", "2026-01-29")
    assert result["expiry_count_monday"] == 1
    assert result["expiry_count_wednesday"] == 1
    assert result["expiry_count_thursday"] == 1
    assert result["available_by_close_minus_120s_rows"] == 3
    assert result["projected_exact_duplicates"] == 1
    assert result["later_projected_versions_ignored"] == 1
    assert result["zero_dte_distinct_contracts_day_union"] == 1


def test_coverage_denominator_includes_missing_origins():
    panel = pl.DataFrame(
        {
            "asset": ["AAPL"] * 4,
            "session_date": ["2026-01-26"] * 2 + ["2026-02-02"] * 2,
            "origin_minute": [5, 10, 5, 10],
            audit.POP: [0.0, 20.0, 24.0, 25.0],
            audit.ATM: [None, float("nan"), 0.4, None],
            audit.ZERO: [0.0, 0.0, 30.0, 32.0],
        }
    )
    rows = audit.coverage_rows(panel, "2026-01-29")
    row = next(
        r
        for r in rows
        if r["scope"] == "all_available_origins"
        and r["asset"] == "ALL"
        and r["period"] == "from_date"
    )
    assert row["N_origins"] == 2
    assert row["atm_0_1dte_presence_pct"] == 50.0
    assert row["zero_dte_contracts_median_finite"] == 31.0


def test_bar_check_keeps_bounce_and_detects_missing_minute():
    stamps = [audit.source.origin_timestamp("2026-08-31", i) for i in range(390)]
    close = [100.0] * 390
    close[270], close[271] = 98.5, 99.2
    rows = []
    for i, stamp in enumerate(stamps):
        opened = close[i - 1] if i else 100.0
        rows.append(
            {
                "asset": "AMZN",
                "bar_start_utc": stamp,
                "open": opened,
                "high": max(opened, close[i]),
                "low": min(opened, close[i]),
                "close": close[i],
                "volume": 100.0 if i != 270 else 300.0,
            }
        )
    result, windows = audit.bar_audit(pl.DataFrame(rows), "AMZN", "2026-08-31", "14:00")
    assert result["missing_regular_minutes"] == result["inconsistent_ohlc_rows"] == 0
    assert result["event_simple_return_bp"] == pytest.approx(-150.0)
    assert result["event_volume_over_session_median"] == 3.0
    assert result["next_close_to_close_log_return_bp"] > 0
    assert all(row["gap_from_previous_bar_seconds"] == 60 for row in windows)
    missing = pl.DataFrame(rows).filter(pl.col("bar_start_utc") != stamps[20])
    result, _ = audit.bar_audit(missing, "AMZN", "2026-08-31", "14:00")
    assert result["missing_regular_minutes"] == 1
    assert stamps[0] + timedelta(minutes=270) == stamps[270]
