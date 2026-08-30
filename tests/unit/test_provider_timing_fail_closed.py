from __future__ import annotations

import numpy as np
import pytest

import mds650.provider_timing as timing


def test_latency_summary_rejects_inconsistent_counts_and_nonfinite_values() -> None:
    cases = [
        ({"row_count": -1}, "TIMING_COUNTS_MUST_BE_NON_NEGATIVE"),
        ({"row_count": 1, "created_at_non_null_count": 2}, "TIMING_NON_NULL_COUNT_EXCEEDS_ROWS"),
        ({"latency_seconds": [float("nan")]}, "TIMING_LATENCY_MUST_BE_FINITE"),
        (
            {"latency_seconds": [1.0], "both_timestamps_count": 0},
            "TIMING_VALID_COUNT_SMALLER_THAN_SAMPLE",
        ),
        ({"both_timestamps_count": 2}, "TIMING_BOTH_COUNT_EXCEEDS_FIELD_COMPLETENESS"),
        ({"negative_latency_count": 2}, "TIMING_NEGATIVE_COUNT_INVALID"),
        (
            {"within_cutoff_counts": {60: 2}, "both_timestamps_count": 1},
            "TIMING_CUTOFF_COUNT_INVALID",
        ),
    ]
    base = {
        "row_count": 1,
        "created_at_non_null_count": 1,
        "executed_at_non_null_count": 1,
        "latency_seconds": [],
        "percentile_method": "fixture",
    }
    for overrides, error in cases:
        with pytest.raises(ValueError, match=error):
            timing.summarize_latency_seconds(**{**base, **overrides})


def test_latency_accumulator_preserves_empty_and_sampled_paths() -> None:
    accumulator = timing._LatencyAccumulator()
    empty = np.array([], dtype=np.int64)
    accumulator.add(
        row_count=1,
        created_at_non_null_count=0,
        executed_at_non_null_count=0,
        latency_microseconds=empty,
        sample_microseconds=empty,
    )
    assert accumulator.summarize(percentile_method="fixture")["quantile_sample_count"] == 0

    values = np.array([-1_000_000, 2_000_000], dtype=np.int64)
    accumulator.add(
        row_count=2,
        created_at_non_null_count=2,
        executed_at_non_null_count=2,
        latency_microseconds=values,
        sample_microseconds=values,
    )
    summary = accumulator.summarize(percentile_method="fixture")
    assert summary["negative_latency_count"] == 1
    assert summary["latency_min_seconds"] == -1.0
    assert summary["latency_max_seconds"] == 2.0


def test_fmp_replay_and_uw_receipt_timestamp_order_fail_closed() -> None:
    valid = {
        "bar_timestamp": "2025-01-02T14:30:00Z",
        "request_started_at_utc": "2025-01-02T14:31:00Z",
        "request_completed_at_utc": "2025-01-02T14:31:01Z",
        "received_at_utc": "2025-01-02T14:31:02Z",
    }
    assert timing.summarize_fmp_bar_replay([valid])["replay_record_count"] == 1
    with pytest.raises(ValueError, match="FMP_REPLAY_REQUEST_ORDER_INVALID"):
        timing.summarize_fmp_bar_replay(
            [{**valid, "request_completed_at_utc": "2025-01-02T14:30:59Z"}]
        )
    with pytest.raises(ValueError, match="FMP_REPLAY_BAR_AFTER_RECEIPT"):
        timing.summarize_fmp_bar_replay([{**valid, "bar_timestamp": "2025-01-02T14:32:00Z"}])
    with pytest.raises(ValueError, match="UW_RECEIPT_SOURCE_AND_CONNECTION_REQUIRED"):
        timing.build_uw_receipt_record(
            {},
            received_at_utc="2025-01-02T14:31:02Z",
            source="",
            connection_type="replay",
            local_clock_offset="0",
        )

    receipt = timing.build_uw_receipt_record(
        {"id": "event-1", "api_key": "secret", "executed_at": None},
        received_at_utc="2025-01-02T14:31:02Z",
        source="fixture",
        connection_type="replay",
        local_clock_offset="0",
    )
    assert receipt["event_id"] == "event-1"
    assert receipt["executed_at"] is None


def test_uw_reconciliation_counts_matches_unmatched_and_duplicate_identifiers() -> None:
    result = timing.reconcile_uw_replay_records(
        [
            {"event_id": "event-1"},
            {"trade_id": "missing"},
        ],
        [
            {"id": "event-1"},
            {"event_id": "event-1"},
        ],
    )

    assert result["matched_count"] == 1
    assert result["unmatched_receipt_count"] == 1
    assert result["duplicate_full_tape_identifier_count"] == 1


def test_provider_timing_numeric_and_timestamp_helpers_cover_boundaries() -> None:
    assert timing._sample_threshold(10, 10) == timing._UINT64_SPACE
    assert timing._sample_threshold(1, 10) >= 1
    assert timing._concatenate([]).size == 0
    assert timing._concatenate([np.array([1]), np.array([2])]).tolist() == [1, 2]
    assert timing._ratio(1, 0) is None
    assert timing._ratio(1, 2) == 0.5
    assert timing._absolute_difference(None, 1) is None
    assert timing._absolute_difference(1, 3) == 2.0

    with pytest.raises(ValueError, match="TIMING_TIMESTAMP_MISSING:value"):
        timing._parse_utc_timestamp(None, "value")
    with pytest.raises(ValueError, match="TIMING_TIMESTAMP_INVALID:value"):
        timing._parse_utc_timestamp("not-a-date", "value")
    with pytest.raises(ValueError, match="TIMING_TIMESTAMP_NOT_UTC_AWARE:value"):
        timing._parse_utc_timestamp("2025-01-02T14:30:00", "value")
    assert timing._optional_utc(None, "value") is None
    assert timing._optional_utc("2025-01-02T14:30:00Z", "value") == "2025-01-02T14:30:00Z"
    assert timing._first_optional_string({"a": 1, "b": "value"}, "a", "b") == "value"
    assert timing._first_optional_string({}, "a") is None
    assert timing._without_secret_fields({"api_key": "secret", "value": 1}) == {"value": 1}
    assert timing._record_identifier_keys({"id": "event"}, full_tape=True) == [
        ("event_id", "event")
    ]
