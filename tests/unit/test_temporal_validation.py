"""Temporal split contracts for the preregistered Phase 5 study."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

import polars as pl
import pytest

from mds650.temporal_validation import (
    FoldDefinition,
    parse_fold_definitions,
    purge_and_embargo_training,
    split_expanding_fold,
    split_inner_validation,
)


def _session_frame(days: list[date]) -> pl.DataFrame:
    return pl.DataFrame(
        {
            "session_date": [day.isoformat() for day in days],
            "forecast_origin_utc": [
                datetime.combine(day, datetime.min.time(), UTC) + timedelta(hours=15)
                for day in days
            ],
            "value": list(range(len(days))),
        }
    )


def test_purge_and_embargo_removes_overlapping_rv30_labels() -> None:
    test_start = datetime(2026, 6, 1, 15, 0, tzinfo=UTC)
    training = pl.DataFrame(
        {
            "forecast_origin_utc": [
                test_start - timedelta(minutes=90),
                test_start - timedelta(minutes=60),
                test_start - timedelta(minutes=55),
            ]
        }
    )

    filtered = purge_and_embargo_training(
        training,
        test_start,
        target_horizon_minutes=30,
        embargo_minutes=30,
    )

    assert filtered["forecast_origin_utc"].to_list() == [
        test_start - timedelta(minutes=90),
        test_start - timedelta(minutes=60),
    ]


def test_expanding_fold_uses_only_declared_train_and_test_dates() -> None:
    days = [
        date(2026, 5, 18),
        date(2026, 5, 19),
        date(2026, 5, 20),
        date(2026, 5, 21),
    ]
    fold = FoldDefinition(
        fold=1,
        train_end=date(2026, 5, 19),
        test_start=date(2026, 5, 20),
        test_end=date(2026, 5, 21),
    )

    training, testing = split_expanding_fold(_session_frame(days), fold)

    assert training["session_date"].to_list() == ["2026-05-18", "2026-05-19"]
    assert testing["session_date"].to_list() == ["2026-05-20", "2026-05-21"]
    assert set(training["session_date"].to_list()).isdisjoint(testing["session_date"].to_list())


def test_inner_validation_is_last_training_history_only() -> None:
    days = [date(2026, 5, day) for day in range(11, 19)]

    fitting, validation = split_inner_validation(
        _session_frame(days),
        validation_sessions=2,
    )

    assert fitting["session_date"].unique().sort().to_list() == [
        day.isoformat() for day in days[:-2]
    ]
    assert validation["session_date"].unique().sort().to_list() == [
        day.isoformat() for day in days[-2:]
    ]
    assert fitting["forecast_origin_utc"].max() < validation["forecast_origin_utc"].min()


def test_fold_definitions_parse_in_declared_order() -> None:
    folds = parse_fold_definitions(
        [
            {
                "fold": "1",
                "train_end": "2026-05-19",
                "test_start": "2026-05-20",
                "test_end": "2026-05-21",
            },
            {
                "fold": 2,
                "train_end": "2026-05-21",
                "test_start": "2026-05-22",
                "test_end": "2026-05-25",
            },
        ]
    )

    assert folds == (
        FoldDefinition(1, date(2026, 5, 19), date(2026, 5, 20), date(2026, 5, 21)),
        FoldDefinition(2, date(2026, 5, 21), date(2026, 5, 22), date(2026, 5, 25)),
    )


@pytest.mark.parametrize(
    "rows, message",
    [
        ([{"fold": 1}], "INVALID_FOLD_DEFINITION"),
        (
            [
                {
                    "fold": 1,
                    "train_end": "2026-05-20",
                    "test_start": "2026-05-20",
                    "test_end": "2026-05-21",
                }
            ],
            "INVALID_FOLD_DATE_ORDER",
        ),
        (
            [
                {
                    "fold": 1,
                    "train_end": "2026-05-19",
                    "test_start": "2026-05-20",
                    "test_end": "2026-05-21",
                },
                {
                    "fold": 1,
                    "train_end": "2026-05-21",
                    "test_start": "2026-05-22",
                    "test_end": "2026-05-23",
                },
            ],
            "DUPLICATE_FOLD_ID",
        ),
    ],
)
def test_fold_definitions_fail_closed(rows: list[dict[str, object]], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        parse_fold_definitions(rows)


def test_temporal_purge_rejects_missing_columns_and_negative_guards() -> None:
    start = datetime(2026, 6, 1, 15, 0, tzinfo=UTC)

    with pytest.raises(ValueError, match="TEMPORAL_COLUMN_MISSING:forecast_origin_utc"):
        purge_and_embargo_training(pl.DataFrame({"other": [start]}), start)
    with pytest.raises(ValueError, match="NEGATIVE_TEMPORAL_GUARD"):
        purge_and_embargo_training(
            pl.DataFrame({"forecast_origin_utc": [start]}),
            start,
            embargo_minutes=-1,
        )


def test_expanding_fold_rejects_invalid_or_empty_boundaries() -> None:
    fold = FoldDefinition(7, date(2026, 5, 19), date(2026, 5, 20), date(2026, 5, 21))
    valid = _session_frame([date(2026, 5, 18), date(2026, 5, 20)])

    with pytest.raises(ValueError, match="TEMPORAL_COLUMNS_MISSING:forecast_origin_utc"):
        split_expanding_fold(valid.drop("forecast_origin_utc"), fold)
    with pytest.raises(ValueError, match="EMPTY_TEMPORAL_FOLD:7"):
        split_expanding_fold(_session_frame([date(2026, 5, 18)]), fold)

    invalid_origin = valid.with_columns(pl.lit(None).alias("forecast_origin_utc"))
    with pytest.raises(ValueError, match="INVALID_TEST_ORIGIN"):
        split_expanding_fold(invalid_origin, fold)

    too_close = pl.DataFrame(
        {
            "session_date": ["2026-05-19", "2026-05-20"],
            "forecast_origin_utc": [
                datetime(2026, 5, 20, 14, 1, tzinfo=UTC),
                datetime(2026, 5, 20, 15, 0, tzinfo=UTC),
            ],
        }
    )
    with pytest.raises(ValueError, match="EMPTY_PURGED_TRAINING_FOLD:7"):
        split_expanding_fold(too_close, fold)


def test_inner_validation_rejects_invalid_history_and_origins() -> None:
    days = [date(2026, 5, day) for day in range(11, 14)]
    valid = _session_frame(days)

    with pytest.raises(ValueError, match="TEMPORAL_COLUMNS_MISSING:session_date"):
        split_inner_validation(valid.drop("session_date"), validation_sessions=1)
    with pytest.raises(ValueError, match="INSUFFICIENT_INNER_VALIDATION_HISTORY"):
        split_inner_validation(valid, validation_sessions=0)
    with pytest.raises(ValueError, match="INSUFFICIENT_INNER_VALIDATION_HISTORY"):
        split_inner_validation(valid, validation_sessions=3)

    invalid_origin = valid.with_columns(
        pl.when(pl.col("session_date") == days[-1].isoformat())
        .then(pl.lit(None))
        .otherwise(pl.col("forecast_origin_utc"))
        .alias("forecast_origin_utc")
    )
    with pytest.raises(ValueError, match="INVALID_INNER_VALIDATION_ORIGIN"):
        split_inner_validation(invalid_origin, validation_sessions=1)

    too_close = pl.DataFrame(
        {
            "session_date": ["2026-05-11", "2026-05-12"],
            "forecast_origin_utc": [
                datetime(2026, 5, 12, 14, 1, tzinfo=UTC),
                datetime(2026, 5, 12, 15, 0, tzinfo=UTC),
            ],
        }
    )
    with pytest.raises(ValueError, match="EMPTY_INNER_FITTING_HISTORY"):
        split_inner_validation(too_close, validation_sessions=1)
