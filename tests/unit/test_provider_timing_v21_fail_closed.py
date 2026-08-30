from __future__ import annotations

import math
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

import mds650.provider_timing_v21 as timing


def test_timestamp_and_session_helpers_reject_invalid_inputs(monkeypatch, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="TIMING_V21_TIMESTAMP_TYPE_REQUIRED"):
        timing.timestamp_array_to_ns(pa.array([1], type=pa.int64()))
    with pytest.raises(ValueError, match="TIMING_V21_TIMESTAMP_TYPE_REQUIRED"):
        timing._timestamp_array_numpy(pa.array([1], type=pa.int64()))
    with pytest.raises(ValueError, match="TIMING_V21_SESSION_DATE_INVALID"):
        timing._session_bounds_ns("not-a-date")
    with pytest.raises(ValueError, match="TIMING_V21_XNYS_SESSION_UNAVAILABLE"):
        timing._session_bounds_ns("2025-01-04")

    assert (
        timing._expected_origin_counts(
            expected_origins_per_asset_date=1, expected_origins_path=None
        )
        == {}
    )
    with pytest.raises(FileNotFoundError, match="TIMING_V21_EXPECTED_ORIGIN_PROJECTION_MISSING"):
        timing._expected_origin_counts(
            expected_origins_per_asset_date=1, expected_origins_path=tmp_path / "missing.parquet"
        )
    empty = tmp_path / "empty.parquet"
    pq.write_table(
        pa.table(
            {
                "asset": pa.array([], type=pa.string()),
                "session_date": pa.array([], type=pa.string()),
            }
        ),
        empty,
    )
    with pytest.raises(ValueError, match="TIMING_V21_EXPECTED_ORIGIN_PROJECTION_EMPTY"):
        timing._expected_origin_counts(
            expected_origins_per_asset_date=1, expected_origins_path=empty
        )


@pytest.mark.parametrize(
    ("counts", "expected"),
    [
        ((0, 0, 0, 0), "ROW_ABSENT"),
        ((2, 0, 0, 1), "NUMERIC_MISSING"),
        ((2, 2, 0, 0), "NUMERIC_ZERO"),
        ((2, 1, 1, 0), "MIXED_NUMERIC_ZERO_AND_NONZERO"),
        ((2, 0, 2, 0), "NUMERIC_NONZERO"),
        ((2, 0, 1, 0), "UNCLASSIFIED_NUMERIC_CODING"),
    ],
)
def test_canonical_value_coding_is_exhaustive(
    counts: tuple[int, int, int, int], expected: str
) -> None:
    assert (
        timing._canonical_value_coding(
            observed_count=counts[0],
            zero_origin_count=counts[1],
            nonzero_origin_count=counts[2],
            null_count=counts[3],
        )
        == expected
    )


def test_sensitivity_accumulator_counts_future_invalid_spread_and_iv_failure() -> None:
    accumulator = timing._SensitivityAccumulator(attempt_count=4)
    origin = 10 * timing.NANOSECONDS_PER_SECOND

    accumulator.add_quote(
        origin_ns=origin,
        cutoff_ns=origin,
        quote=(origin + 1, 1, 1.0, 1.1),
        iv_result={"success": True},
    )
    accumulator.add_quote(
        origin_ns=origin,
        cutoff_ns=origin,
        quote=(origin - 1, 2, 1.0, 2.0),
        iv_result={"success": True},
    )
    accumulator.add_quote(
        origin_ns=origin,
        cutoff_ns=origin,
        quote=(origin - 2, 3, 1.0, 1.1),
        iv_result=None,
    )
    accumulator.add_quote(
        origin_ns=origin,
        cutoff_ns=origin,
        quote=(origin - 3, 4, -1.0, 1.0),
        iv_result={"success": False, "failure_reason": "bad"},
    )

    row = accumulator.as_row(cutoff_delay_seconds=0, asset="AAPL")
    assert row["future_quote_count"] == 1
    assert row["relative_spread_exceeds_25pct_count"] == 1
    assert row["invalid_selected_nbbo_count"] == 1
    assert row["iv_failure_reason_counts"] == {"IV_NO_CONVERGENCE": 1}


def test_massive_cache_loader_classifies_ambiguous_and_malformed_envelopes(tmp_path: Path) -> None:
    contract = "O:AAPL250117C00100000"
    prefix = f"AAPL_2025-01-02_{contract.replace(':', '_')}"
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text("not json", encoding="utf-8")
    second.write_text("{}", encoding="utf-8")

    def status(paths: list[Path]) -> str:
        result, _ = timing._load_and_validate_massive_cache(
            cache_index={prefix: paths},
            cache_root=tmp_path,
            asset="AAPL",
            session_date="2025-01-02",
            contract=contract,
            source_request_hash="a" * 64,
        )
        return result

    assert status([]) == "CACHE_FILE_MISSING"
    assert status([first, second]) == "CACHE_FILE_AMBIGUOUS"
    assert status([first]) == "CACHE_JSON_INVALID"
    first.write_text("[]", encoding="utf-8")
    assert status([first]) == "CACHE_ENVELOPE_INVALID"
    first.write_text("{}", encoding="utf-8")
    assert status([first]) == "CACHE_ENVELOPE_IDENTITY_INVALID"
    first.write_text(
        timing._canonical_json(
            {
                "asset": "AAPL",
                "day": "2025-01-02",
                "route": "B1Q",
                "schema_version": 4,
                "http_status": 200,
                "contract": {"contract": contract},
                "source_request_hash": "a" * 64,
            }
        ),
        encoding="utf-8",
    )
    assert status([first]) == "CACHE_CONTRACT_METADATA_INVALID"


def test_massive_request_pagination_and_quote_guards_fail_closed() -> None:
    contract = "O:AAPL250117C00100000"
    with pytest.raises(ValueError, match="TIMING_V21_CACHE_CONTRACT_METADATA_INVALID"):
        timing._expected_massive_cache_key(
            asset="AAPL",
            session_date="2025-01-02",
            contract=contract,
            contract_metadata={"expiry": "2025-01-17"},
        )
    assert timing._massive_request_parameters_status(
        request_params={}, session_date="not-a-date"
    ) == ("INVALID", {})
    assert (
        timing._massive_request_parameters_status(request_params={}, session_date="2025-01-02")[0]
        == "INVALID"
    )

    assert not timing._massive_pagination_verified(payload={"pagination_complete": False}, rows=[])
    assert not timing._massive_pagination_verified(
        payload={"provider_duplicate_rows_removed": True}, rows=[]
    )
    assert timing._massive_pagination_verified(payload={}, rows=[])

    with pytest.raises(ValueError, match="TIMING_V21_CACHE_QUOTE_TIMESTAMP_OR_SEQUENCE_INVALID"):
        timing._prepare_quotes([{"sip_timestamp": "bad", "sequence_number": 1}])
    with pytest.raises(ValueError, match="TIMING_V21_CACHE_QUOTE_PRICE_INVALID"):
        timing._prepare_quotes(
            [{"sip_timestamp": 1, "sequence_number": 1, "bid_price": "bad", "ask_price": 2.0}]
        )
    quote = {"sip_timestamp": 1, "sequence_number": 1, "bid_price": 1.0, "ask_price": 2.0}
    with pytest.raises(ValueError, match="TIMING_V21_CACHE_QUOTE_DUPLICATE"):
        timing._prepare_quotes([quote, quote])


def _iv_row() -> dict[str, float | str]:
    return {
        "spot": 100.0,
        "strike": 100.0,
        "dte": 30.0,
        "rate": 0.02,
        "dividend_yield": 0.0,
        "option_type": "call",
    }


def test_iv_reselection_guards_cover_invalid_nbbo_spread_and_inputs() -> None:
    assert timing._iv_from_reselected_quote(row=_iv_row(), quote=(1, 1, 0.0, 1.0)) == {
        "success": False,
        "failure_reason": "INVALID_SELECTED_NBBO",
    }
    assert timing._iv_from_reselected_quote(row=_iv_row(), quote=(1, 1, 1.0, 2.0)) == {
        "success": False,
        "failure_reason": "RELATIVE_SPREAD_EXCEEDS_LIMIT",
    }
    result = timing._iv_from_reselected_quote(row=_iv_row(), quote=(1, 1, 1.0e308, 1.7e308))
    assert result == {"success": False, "failure_reason": "IV_INPUT_INVALID"}

    assert (
        timing._invert_iv(
            spot=100.0,
            strike=100.0,
            time_years=1.0,
            rate=0.0,
            dividend=0.0,
            midpoint=10.0,
            option_type="other",
        )["failure_reason"]
        == "INVALID_OPTION_TYPE"
    )
    assert (
        timing._invert_iv(
            spot=math.nan,
            strike=100.0,
            time_years=1.0,
            rate=0.0,
            dividend=0.0,
            midpoint=10.0,
            option_type="call",
        )["failure_reason"]
        == "IV_INPUT_INVALID"
    )
    assert (
        timing._invert_iv(
            spot=100.0,
            strike=100.0,
            time_years=1.0,
            rate=0.0,
            dividend=0.0,
            midpoint=101.0,
            option_type="call",
        )["failure_reason"]
        == "ARBITRAGE_BOUND"
    )
    assert (
        timing._invert_iv(
            spot=100.0,
            strike=100.0,
            time_years=1e-6,
            rate=0.0,
            dividend=0.0,
            midpoint=50.0,
            option_type="call",
        )["failure_reason"]
        == "IV_UPPER_BOUND"
    )


def test_bsm_cutoff_and_optional_helpers_cover_boundary_paths(monkeypatch) -> None:
    assert timing._bsm_price(0.0, 100.0, 1.0, 0.0, 0.0, 0.2, "call") == 0.0
    assert timing._bsm_price(100.0, 100.0, 1.0, 0.0, 0.0, 0.2, "put") > 0.0
    with pytest.raises(ValueError, match="TIMING_V21_CUTOFFS_MUST_BE_UNIQUE_ASCENDING"):
        timing._validate_cutoffs((60, 0))
    with pytest.raises(ValueError, match="TIMING_V21_CUTOFFS_MUST_BE_NONNEGATIVE_INTEGERS"):
        timing._validate_cutoffs((-1,))
    assert timing._ns_to_iso(None) is None
    assert timing._min_optional(None, 2) == 2
    assert timing._min_optional(1, 2) == 1
    assert timing._max_optional(None, 2) == 2
    assert timing._max_optional(3, 2) == 3
    assert timing._rate(1, 0) is None

    midpoint = 10.0
    monkeypatch.setattr(
        timing,
        "_bsm_price",
        lambda _spot, _strike, _time, _rate, _dividend, sigma, _type: (
            midpoint + 1.0 if sigma > 2.5 else midpoint - 1.0
        ),
    )
    result = timing._invert_iv(
        spot=100.0,
        strike=100.0,
        time_years=1.0,
        rate=0.0,
        dividend=0.0,
        midpoint=midpoint,
        option_type="call",
    )
    assert result["success"] is True
