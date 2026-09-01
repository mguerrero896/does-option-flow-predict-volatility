"""TDD tests for market-clock and point-in-time timestamp semantics."""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta, timezone

import pytest

from mds650.time import (
    align_five_minute_origin,
    is_regular_session_minute,
    parse_market_timestamp,
    session_date,
    to_new_york,
    to_utc,
)


def test_naive_provider_timestamp_requires_explicit_timezone() -> None:
    """Naive FMP-like timestamps cannot enter the pipeline by assumption."""
    with pytest.raises(ValueError, match="TIMESTAMP_TIMEZONE_REQUIRED"):
        parse_market_timestamp("2026-07-17 09:30:00")


def test_dst_fall_back_keeps_distinct_instants() -> None:
    """Both New York 01:30 occurrences remain distinct through UTC conversion."""
    first = parse_market_timestamp("2026-11-01 01:30:00-04:00")
    second = parse_market_timestamp("2026-11-01 01:30:00-05:00")

    assert to_utc(first) != to_utc(second)
    assert to_new_york(first).utcoffset() != to_new_york(second).utcoffset()


def test_regular_session_and_origin_alignment() -> None:
    """Only five-minute regular-session boundaries are valid forecast origins."""
    valid = parse_market_timestamp("2026-07-17 09:35:00-04:00")
    invalid = parse_market_timestamp("2026-07-17 09:36:00-04:00")

    assert is_regular_session_minute(valid)
    assert align_five_minute_origin(valid) == valid
    with pytest.raises(ValueError, match="ORIGIN_NOT_FIVE_MINUTE_BOUNDARY"):
        align_five_minute_origin(invalid)


def test_timezone_aware_datetime_is_normalized_to_utc() -> None:
    """Aware datetimes are accepted and normalized without losing the instant."""
    value = datetime(2026, 7, 17, 13, 30, tzinfo=UTC)

    assert to_utc(value).isoformat() == "2026-07-17T13:30:00+00:00"


@pytest.mark.parametrize(
    ("value", "source_timezone", "error"),
    [
        ("not-a-timestamp", None, "TIMESTAMP_INVALID_FORMAT"),
        ("2026-07-17 09:30:00", "Not/A_Zone", "TIMESTAMP_INVALID_TIMEZONE"),
    ],
)
def test_timestamp_parser_rejects_invalid_format_or_timezone(
    value: str, source_timezone: str | None, error: str
) -> None:
    """Malformed time or an unknown source zone cannot enter PIT calculations."""
    with pytest.raises(ValueError, match=error):
        parse_market_timestamp(value, source_timezone)


def test_aware_datetime_preserves_original_instant_and_offset() -> None:
    """An already-aware instant keeps its explicit non-UTC offset."""
    offset = timedelta(hours=5, minutes=30)
    value = datetime(2026, 7, 17, 13, 30, tzinfo=timezone(offset))
    observed = parse_market_timestamp(value)

    assert observed == value
    assert observed.utcoffset() == offset


def test_origin_outside_regular_session_fails_closed() -> None:
    """A five-minute boundary before the open is still not a valid origin."""
    before_open = parse_market_timestamp("2026-07-17 09:25:00-04:00")

    with pytest.raises(ValueError, match="ORIGIN_OUTSIDE_REGULAR_SESSION"):
        align_five_minute_origin(before_open)


def test_session_date_uses_new_york_not_utc_date() -> None:
    """A post-close UTC instant remains attached to its New York calendar date."""
    value = datetime(2026, 7, 18, 1, 0, tzinfo=UTC)

    assert session_date(value) == date(2026, 7, 17)


def test_utc_conversion_rejects_naive_datetime() -> None:
    """A direct conversion cannot bypass the parser's explicit-timezone rule."""
    with pytest.raises(ValueError, match="TIMESTAMP_TIMEZONE_REQUIRED"):
        to_utc(datetime(2026, 7, 17, 13, 30))
