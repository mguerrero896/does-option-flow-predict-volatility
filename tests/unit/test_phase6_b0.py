from __future__ import annotations

from datetime import UTC, datetime, timedelta

import polars as pl
import pytest

from mds650.phase6 import build_b0v2_features, build_phase6_origins

ORIGIN = datetime(2026, 1, 5, 15, 5, tzinfo=UTC)
SESSION_DATE = "2026-01-05"


def _bars(*, missing_timestamp: datetime | None = None) -> pl.DataFrame:
    rows: list[dict[str, object]] = []
    first = datetime(2026, 1, 5, 14, 30, tzinfo=UTC)
    for asset_index, asset in enumerate(("AAPL", "SPY", "QQQ"), start=1):
        for minute in range(65):
            timestamp = first + timedelta(minutes=minute)
            if asset == "AAPL" and timestamp == missing_timestamp:
                continue
            close = 100.0 + 10.0 * asset_index + 0.05 * minute
            rows.append(
                {
                    "asset": asset,
                    "session_date": SESSION_DATE,
                    "bar_timestamp_raw_utc": timestamp,
                    "available_at_utc": timestamp + timedelta(minutes=1),
                    "close": close,
                    "volume": 1_000.0 + minute,
                }
            )
    return pl.DataFrame(rows)


def _origins() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "origin_id": [f"AAPL:{ORIGIN.isoformat()}"],
            "asset": ["AAPL"],
            "session_date": [SESSION_DATE],
            "forecast_origin_utc": [ORIGIN],
        }
    )


def _origin_at(origin: datetime) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "origin_id": [f"AAPL:{origin.isoformat()}"],
            "asset": ["AAPL"],
            "session_date": [SESSION_DATE],
            "forecast_origin_utc": [origin],
        }
    )


def test_b0v2_uses_only_available_bars_and_exact_rv30_prices() -> None:
    result = build_b0v2_features(_bars(), _origins())
    row = result.row(0, named=True)

    assert row["drop_reason"] is None
    assert row["target_price_count"] == 31
    assert row["target_return_count"] == 30
    assert row["max_predictor_available_at_utc"] <= row["forecast_origin_utc"]
    assert row["b0v2_spy_return_5m"] is not None
    assert row["b0v2_qqq_rv_30m"] is not None
    assert row["rv30"] > 0


def test_b0v2_two_minute_delay_changes_predictors_not_rv30() -> None:
    primary = build_b0v2_features(_bars(), _origins()).row(0, named=True)
    delayed_bars = _bars().with_columns(
        (pl.col("bar_timestamp_raw_utc") + pl.duration(minutes=2)).alias("available_at_utc")
    )

    delayed = build_b0v2_features(delayed_bars, _origins(), delay_minutes=2).row(0, named=True)

    assert delayed["drop_reason"] is None
    assert delayed["rv30"] == primary["rv30"]
    assert delayed["anchor_timestamp_raw_utc"] == ORIGIN - timedelta(minutes=1)
    assert delayed["predictor_anchor_timestamp_raw_utc"] == ORIGIN - timedelta(minutes=2)
    assert delayed["max_predictor_available_at_utc"] <= ORIGIN


def test_b0v2_delay_never_changes_target_when_predictor_history_is_short() -> None:
    early_origin = datetime(2026, 1, 5, 15, 1, tzinfo=UTC)
    primary = build_b0v2_features(_bars(), _origin_at(early_origin)).row(0, named=True)
    delayed = build_b0v2_features(
        _bars().with_columns(
            (pl.col("bar_timestamp_raw_utc") + pl.duration(minutes=2)).alias("available_at_utc")
        ),
        _origin_at(early_origin),
        delay_minutes=2,
    ).row(0, named=True)

    assert primary["target_price_count"] == delayed["target_price_count"] == 31
    assert primary["target_return_count"] == delayed["target_return_count"] == 30
    assert primary["rv30"] == delayed["rv30"]
    assert delayed["drop_reason"] == "B0V2_UNDERLYING_HISTORY_MISSING"


def test_missing_future_close_rejects_origin_without_interpolation() -> None:
    missing = ORIGIN + timedelta(minutes=7)
    result = build_b0v2_features(_bars(missing_timestamp=missing), _origins())
    row = result.row(0, named=True)

    assert row["drop_reason"] == "RV30_CONSECUTIVE_CLOSE_MISSING"
    assert row["rv30"] is None
    assert row["target_price_count"] == 30
    assert row["target_return_count"] == 0


def test_future_predictor_availability_fails_closed() -> None:
    bars = _bars().with_columns(
        pl.when(
            (pl.col("asset") == "AAPL")
            & (pl.col("bar_timestamp_raw_utc") == ORIGIN - timedelta(minutes=1))
        )
        .then(pl.col("available_at_utc") + timedelta(seconds=1))
        .otherwise(pl.col("available_at_utc"))
        .alias("available_at_utc")
    )

    with pytest.raises(ValueError, match="B0V2_ORIGIN_CLOSE_NOT_AVAILABLE"):
        build_b0v2_features(bars, _origins())


def test_origins_include_last_valid_time_and_respect_early_close() -> None:
    normal = build_phase6_origins(["2026-01-05"], assets=["AAPL"])
    early = build_phase6_origins(["2025-11-28"], assets=["AAPL"])

    assert normal.height == 72
    assert normal["forecast_origin_ny"].max().strftime("%H:%M") == "15:30"
    assert early.height == 36
    assert early["forecast_origin_ny"].max().strftime("%H:%M") == "12:30"


def test_zero_dollar_volume_drops_origin_without_imputation() -> None:
    bars = _bars().with_columns(
        pl.when(
            (pl.col("asset") == "AAPL")
            & (pl.col("bar_timestamp_raw_utc") >= ORIGIN - timedelta(minutes=5))
            & (pl.col("bar_timestamp_raw_utc") < ORIGIN)
        )
        .then(0.0)
        .otherwise(pl.col("volume"))
        .alias("volume")
    )

    row = build_b0v2_features(bars, _origins()).row(0, named=True)

    assert row["drop_reason"] == "B0V2_DOLLAR_VOLUME_NOT_POSITIVE"
    assert row["b0v2_log_dollar_volume_5m"] is None


def test_phase6_origin_contract_rejects_duplicate_date_asset_and_unknown_date() -> None:
    with pytest.raises(ValueError, match="PHASE6_ORIGIN_SESSION_DUPLICATE"):
        build_phase6_origins([SESSION_DATE, SESSION_DATE], assets=["AAPL"])
    with pytest.raises(ValueError, match="PHASE6_ORIGIN_SESSION_NOT_AUTHORIZED"):
        build_phase6_origins(["2020-01-02"], assets=["AAPL"])
    with pytest.raises(ValueError, match="PHASE6_ORIGIN_ASSET_NOT_AUTHORIZED"):
        build_phase6_origins([SESSION_DATE], assets=["SPY"])


def test_b0v2_rejects_schema_identity_and_timestamp_drift() -> None:
    cases = [
        (_bars(), _origins(), 3, "B0V2_DELAY_NOT_REGISTERED"),
        (_bars().drop("close"), _origins(), 1, "B0V2_BAR_SCHEMA_INVALID"),
        (_bars(), _origins().drop("asset"), 1, "B0V2_ORIGIN_SCHEMA_INVALID"),
        (_bars(), pl.concat([_origins(), _origins()]), 1, "B0V2_DUPLICATE_ORIGIN"),
        (
            _bars().with_columns(pl.col("bar_timestamp_raw_utc").cast(pl.String)),
            _origins(),
            1,
            "B0V2_BAR_TIMESTAMP_INVALID",
        ),
        (pl.concat([_bars(), _bars().head(1)]), _origins(), 1, "B0V2_DUPLICATE_BAR"),
        (
            _bars(),
            _origins().with_columns(pl.col("forecast_origin_utc").cast(pl.String)),
            1,
            "B0V2_ORIGIN_TIMESTAMP_INVALID",
        ),
    ]

    for bars, origins, delay, error in cases:
        with pytest.raises(ValueError, match=error):
            build_b0v2_features(bars, origins, delay_minutes=delay)


def test_b0v2_reports_missing_anchor_predictor_and_market_control() -> None:
    missing_anchor = _bars().filter(
        ~(
            (pl.col("asset") == "AAPL")
            & (pl.col("bar_timestamp_raw_utc") == ORIGIN - timedelta(minutes=1))
        )
    )
    assert build_b0v2_features(missing_anchor, _origins()).item(0, "drop_reason") == (
        "RV30_ORIGIN_CLOSE_MISSING"
    )

    missing_predictor = _bars().filter(
        ~(
            (pl.col("asset") == "AAPL")
            & (pl.col("bar_timestamp_raw_utc") == ORIGIN - timedelta(minutes=2))
        )
    )
    assert (
        build_b0v2_features(missing_predictor, _origins(), delay_minutes=2).item(0, "drop_reason")
        == "B0V2_PREDICTOR_ANCHOR_MISSING"
    )

    missing_control = _bars().filter(pl.col("asset") != "QQQ")
    assert build_b0v2_features(missing_control, _origins()).item(0, "drop_reason") == (
        "B0V2_MARKET_CONTROL_MISSING"
    )


@pytest.mark.parametrize("asset", ["AAPL", "SPY"])
def test_b0v2_rejects_future_history_for_underlying_or_control(asset: str) -> None:
    bars = _bars().with_columns(
        pl.when(
            (pl.col("asset") == asset)
            & (pl.col("bar_timestamp_raw_utc") == ORIGIN - timedelta(minutes=5))
        )
        .then(pl.lit(ORIGIN + timedelta(seconds=1)))
        .otherwise(pl.col("available_at_utc"))
        .alias("available_at_utc")
    )

    with pytest.raises(ValueError, match="B0V2_FUTURE_PREDICTOR"):
        build_b0v2_features(bars, _origins())


def test_b0v2_rejects_nonpositive_close_in_predictor_window() -> None:
    bars = _bars().with_columns(
        pl.when(
            (pl.col("asset") == "AAPL")
            & (pl.col("bar_timestamp_raw_utc") == ORIGIN - timedelta(minutes=5))
        )
        .then(0.0)
        .otherwise(pl.col("close"))
        .alias("close")
    )

    with pytest.raises(ValueError, match="B0V2_CLOSE_NOT_POSITIVE"):
        build_b0v2_features(bars, _origins())
