"""Synthetic checks for aggregate-only tables and denominator preservation."""

from artifacts.rp4_market_audit_code import report


def test_tables_keep_five_weekdays_and_separate_listing_from_expiration():
    coverage = [
        {
            "scope": "all_available_origins",
            "asset": "ALL",
            "transition_date": "2026-01-26",
            "weekday": day,
            "period": period,
            "N_origins": "10",
            "N_sessions": "1",
            "atm_0_1dte_presence_pct": "50",
            "surface_populated_cells_mean": "20",
            "zero_dte_contracts_median_finite": "0",
        }
        for day in report.DAY_NAMES
        for period in ("before", "from_date")
    ]
    daily = [
        {
            "asset": asset,
            "session_date": session,
            "weekday": day,
            "expiry_count_monday": "2",
            "expiry_count_wednesday": "1",
            "expiry_dates": "2026-02-02;2026-02-04;2026-02-09",
            "distinct_expiries_by_close_minus_120s": "3",
            "first_mon_wed_available_ny": session + "T09:30:00-05:00",
            "zero_dte_trade_rows": "0" if session == "2026-01-26" else "5",
        }
        for asset in report.ASSETS
        for session, day in (
            ("2026-01-26", "Monday"),
            ("2026-02-02", "Monday"),
            ("2026-02-04", "Wednesday"),
        )
    ]
    wide, first, days = report.aggregates(coverage, daily)
    assert (len(wide), len(first), len(days)) == (5, 6, 3)
    assert all(row["first_observed_session"] == "2026-01-26" for row in first)
    assert all(row["first_zero_dte_monday"] == "2026-02-02" for row in first)
    assert all(row["first_zero_dte_wednesday"] == "2026-02-04" for row in first)
    assert sum(row["before__N_origins"] for row in wide) == 50
    summary = {"tape_asset_sessions": 18, "panel_rows": 100, "panel_sessions": 10, "bars": []}
    rendered = report.render(summary, wide, first, days)
    assert "20.000000 antes" in rendered
    assert "No se publica ningún extracto por minuto" in rendered
    assert "bar_event_windows.csv" not in rendered
