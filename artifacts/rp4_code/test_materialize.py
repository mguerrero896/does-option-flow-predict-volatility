"""Small synthetic RP4 checks: cutoff, OI uniqueness, carry and keyed target identity."""

import json
from datetime import UTC, date, datetime, timedelta

import numpy as np
import polars as pl
import pytest
from materialize import (
    DEALER_COLUMNS,
    GRID_COLUMNS,
    GRID_COUNT,
    KEYS,
    TAPE_COLUMNS,
    append_extension,
    attach_secondaries,
    build_new_option_features,
    carry_for_session,
    cell_indices,
    dealer_measures,
    gamma_with_carry,
    har_features_for_session,
    read_new_tape,
    reconstruct_rv30,
    session_window,
    sha256,
    weighted_median,
)


def test_session_window_uses_literal_dates():
    frame = pl.DataFrame({"session_date": ["2026-07-31", "2026-08-03", "2026-08-04"]})
    assert session_window(frame, "2026-08-01", "2026-08-03")["session_date"].to_list() == [
        "2026-08-03"
    ]


def test_parquet_loader_deduplicates_ids_and_rejects_conflicts(tmp_path):
    values = {name: [1.0, 1.0] for name in TAPE_COLUMNS}
    values["id"] = ["same-id", "same-id"]
    values["underlying_symbol"] = ["AAPL", "AAPL"]
    path = tmp_path / "tape.parquet"
    pl.DataFrame(values).write_parquet(path)
    assert read_new_tape([str(path)], "AAPL").height == 1
    values["implied_volatility"] = [0.2, 0.4]
    pl.DataFrame(values).write_parquet(path)
    with pytest.raises(ValueError, match="RP4_TAPE_DUPLICATE_ID_CONFLICT"):
        read_new_tape([str(path)], "AAPL")


def test_missing_target_bar_is_not_forward_filled():
    bars = synthetic_bars().filter(
        ~((pl.col("session_date") == date(2026, 6, 30)) & (pl.col("minute") == 40))
    )
    keys = pl.DataFrame(
        {"asset": ["AAPL", "AAPL"], "session_date": ["2026-06-30"] * 2, "origin_minute": [35, 65]}
    )
    targets, counts = reconstruct_rv30(bars, keys)
    assert targets["origin_minute"].to_list() == [65]
    assert counts["unobserved_target_bar_keys"] == 1


def test_secondary_previous_session_and_unknown_events():
    panel = pl.DataFrame(
        {
            "asset": ["AAPL"] * 2,
            "session_date": ["2026-06-29", "2026-06-30"],
            "b2_30m_premium": [20.0, 999.0],
        }
    )
    history = pl.DataFrame(
        {"asset": ["AAPL"], "session_date": ["2026-06-26"], "b2_30m_premium": [10.0]}
    )
    result = attach_secondaries(panel, history, {})
    assert result["previous_day_b2_30m_premium"].to_list() == [10.0, 20.0]
    assert result["is_event"].null_count() == 2
    assert result["event_calendar_status"].to_list() == ["NO VERIFICABLE"] * 2


def test_weighted_median_and_exact_cell_edges():
    assert weighted_median(np.array([0.2, 0.4, 0.7]), np.array([1, 4, 1])) == 0.4
    assert np.isnan(weighted_median(np.array([0.2]), np.array([0.0])))
    dte = np.array([1, 2, 7, 8, 30, 31, 90, 91])
    money = np.array([0.89, 0.90, 0.97, 1.03, 1.10, 1.10001, 1, 1])
    np.testing.assert_array_equal(cell_indices(dte, money), [0, 6, 7, 13, 13, 19, 17, 22])


def test_nonzero_carry_changes_gamma_and_call_put_net():
    strikes = np.array([100.0, 100.0])
    gamma = gamma_with_carry(100, strikes, np.array([0.25, 0.25]), np.array([0.3, 0.3]), 0.04, 0.02)
    zero = gamma_with_carry(100, strikes, np.array([0.25, 0.25]), np.array([0.3, 0.3]), 0, 0)
    assert np.all(gamma > 0)
    assert not np.allclose(gamma, zero)
    net, near, distance = dealer_measures(
        100, strikes, gamma, np.array([20, 10]), np.array([True, False])
    )
    assert np.isclose(net, gamma[0] * 10 * 100**2 * 100)
    assert near == net
    assert distance == 0


def test_no_future_cutoff_and_no_repeated_contract_oi():
    # 10:05 New York == 14:05 UTC; exact cutoff14:03 is eligible.
    cutoff = datetime(2026, 7, 1, 14, 3, tzinfo=UTC)
    times = [cutoff - timedelta(seconds=180), cutoff, cutoff + timedelta(microseconds=1)]
    tape = pl.DataFrame(
        {
            "underlying_symbol": ["AAPL"] * 3,
            "created_at": times,
            "implied_volatility": [0.3, 0.4, 4.0],
            "size": [1.0, 10.0, 10000.0],
            "open_interest": [20, 20, 50000],
            "expiry": [date(2026, 7, 17)] * 3,
            "strike": [100.0] * 3,
            "option_type": ["call"] * 3,
            "nbbo_bid": [1.0] * 3,
            "nbbo_ask": [1.1] * 3,
        }
    )
    features = build_new_option_features(
        tape, "AAPL", "2026-07-01", np.array([35]), np.full(390, 100.0), 0.04, 1.0
    )
    assert features[GRID_COUNT][0] == 1
    assert features[GRID_COLUMNS[12]][0] == 0.4
    without_future = build_new_option_features(
        tape.head(2), "AAPL", "2026-07-01", np.array([35]), np.full(390, 100.0), 0.04, 1.0
    )
    assert features.equals(without_future)
    latest_only = build_new_option_features(
        tape.slice(1, 1), "AAPL", "2026-07-01", np.array([35]), np.full(390, 100.0), 0.04, 1.0
    )
    np.testing.assert_allclose(
        features.select(DEALER_COLUMNS).to_numpy(), latest_only.select(DEALER_COLUMNS).to_numpy()
    )


def test_exogenous_only_prior_declarations_and_no_future_rates():
    rates = {"2026-07-01": 0.04, "2026-07-02": 0.99}
    events = {
        "AAPL": [
            {"declarationDate": "2026-06-01", "dividend": 1},
            {"declarationDate": "2026-07-02", "dividend": 999},
        ]
    }
    assert carry_for_session("2026-07-02", "AAPL", rates, events) == (0.04, 1.0)
    assert np.isnan(carry_for_session("2026-06-01", "AAPL", rates, events)[0])


def synthetic_bars():
    days = [date(2026, 6, d) for d in [22, 23, 24, 25, 26, 29, 30]]
    frames = []
    for day in days:
        close = 100 * np.exp(np.arange(390) * 0.0001)
        frames.append(
            pl.DataFrame(
                {
                    "asset": ["AAPL"] * 390,
                    "session_date": [day] * 390,
                    "bar_ny": [
                        datetime(day.year, day.month, day.day, 13, 30, tzinfo=UTC)
                        + timedelta(minutes=m)
                        for m in range(390)
                    ],
                    "minute": np.arange(390),
                    "open": close,
                    "close": close,
                    "high": close + 0.01,
                    "low": close - 0.01,
                    "volume": [100.0] * 390,
                }
            )
        )
    return pl.concat(frames)


def test_rv30_keys_and_har_cutoff():
    bars = synthetic_bars()
    keys = pl.DataFrame(
        {"asset": ["AAPL", "AAPL"], "session_date": ["2026-06-30"] * 2, "origin_minute": [65, 35]}
    )
    target, counts = reconstruct_rv30(bars, keys)
    assert target.select(KEYS).equals(keys)
    np.testing.assert_allclose(target["rv30"].to_numpy(), 30 * 0.0001**2)
    assert sum(counts.values()) == 0
    har = har_features_for_session(bars, keys)
    assert har.select(KEYS).equals(keys)
    np.testing.assert_allclose(har["minute_fraction"].to_numpy(), np.array([65, 35]) / 390)
    changed = bars.with_columns(
        pl.when((pl.col("session_date") == date(2026, 6, 30)) & (pl.col("minute") >= 33))
        .then(pl.col("close") * 4)
        .otherwise(pl.col("close"))
        .alias("close")
    )
    original_early = har_features_for_session(bars, keys.tail(1))
    changed_early = har_features_for_session(changed, keys.tail(1))
    assert original_early.equals(changed_early)


def test_append_preserves_each_keyed_development_value(tmp_path):
    spec = {
        "windows": {
            "primary": {"end": "2026-07-31"},
            "confirmation": {"start": "2026-08-03", "end": "2026-09-04"},
        }
    }
    paths = []
    for name, session, values in (
        ("development", "2026-07-31", [float("nan"), 0.2]),
        ("extension", "2026-08-03", [0.3, float("nan")]),
    ):
        folder = tmp_path / name
        folder.mkdir()
        path = folder / "panel.parquet"
        pl.DataFrame(
            {
                "asset": ["AAPL"] * 2,
                "session_date": [session] * 2,
                "origin_minute": [40, 35],
                "rv30": [0.001, 0.002],
                "grid": values,
            }
        ).write_parquet(path)
        (folder / "manifest.json").write_text(
            json.dumps({"spec_sha256": "spec", "artifacts": {str(path): sha256(path)}})
        )
        paths.append(path)
    before = sha256(paths[0])
    output = tmp_path / "combined"
    assert append_extension(*paths, output, spec, "spec", "code") == 0
    receipt = json.loads((output / "manifest.json").read_text())
    assert receipt["development_prefix_equal_by_keys"] is True
    assert receipt["combined_rows"] == 4 and sha256(paths[0]) == before
    with pytest.raises(ValueError, match="ALREADY_EXISTS"):
        append_extension(*paths, output, spec, "spec", "code")
