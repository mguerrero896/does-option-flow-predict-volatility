from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import replace
from pathlib import Path

import pytest

import mds650.date_level_pit_preflight_v2 as pit

ROOT = Path(__file__).resolve().parents[2]


def _operation(**overrides: object) -> pit.PreflightOperation:
    values: dict[str, object] = {
        "operation_id": "fmp:minute-bars:2025-01-02:AAPL:none",
        "provider": pit.Provider.FMP,
        "kind": pit.OperationKind.MINUTE_BARS,
        "session_date": "2025-01-02",
        "asset": "AAPL",
        "origin_ns": None,
        "page": None,
        "shared_across_assets": False,
        "disposition": pit.OperationDisposition.DATE_BOUNDED_ONLY_NO_PIT_CLAIM,
        "execution_permitted": False,
    }
    values.update(overrides)
    return pit.PreflightOperation(**values)  # type: ignore[arg-type]


def test_preflight_operations_reject_every_invalid_provider_kind_shape() -> None:
    cases = [
        {"operation_id": ""},
        {"execution_permitted": True},
        {"asset": None},
        {
            "provider": pit.Provider.UNUSUAL_WHALES,
            "kind": pit.OperationKind.FULL_TAPE_ZIP_DOWNLOAD,
            "asset": "AAPL",
            "shared_across_assets": True,
        },
        {
            "provider": pit.Provider.MASSIVE,
            "kind": pit.OperationKind.CONTRACT_SEARCH,
            "origin_ns": 1_700_000_000_000_000_000,
            "page": 4,
        },
        {
            "provider": pit.Provider.MASSIVE,
            "kind": pit.OperationKind.CONTRACT_REFERENCE,
            "origin_ns": 1_700_000_000_000_000_000,
            "contract_candidate": None,
        },
        {
            "provider": pit.Provider.MASSIVE,
            "kind": pit.OperationKind.QUOTE_AS_OF,
            "origin_ns": 1_700_000_000_000_000_000,
            "contract_candidate": "O:AAPL",
            "quote_parameters": pit.QuoteAsOfParameters(1_700_000_000_000_000_001),
        },
    ]
    for overrides in cases:
        with pytest.raises(pit.PitPreflightV2Error, match="PREFLIGHT_V2_OPERATION_INVALID"):
            _operation(**overrides)


def test_historical_availability_observation_and_attempt_ledger_fail_closed() -> None:
    availability = pit.current_historical_source_availability()
    with pytest.raises(
        pit.PitPreflightV2Error, match="PREFLIGHT_V2_HISTORICAL_AVAILABILITY_INVALID"
    ):
        replace(availability, fmp_evidence_sha256="0" * 64)
    with pytest.raises(pit.PitPreflightV2Error, match="PREFLIGHT_V2_PROVIDER_OBSERVATION_INVALID"):
        pit.ProviderObservation(
            http_status=True,
            entitlement_error=False,
            schema_valid=True,
            pagination_valid=True,
        )
    with pytest.raises(
        pit.AttemptBudgetError, match="PREFLIGHT_V2_ATTEMPT_LEDGER_CONFIGURATION_INVALID"
    ):
        pit.AttemptLedger(http_attempt_cap=0)
    ledger = pit.AttemptLedger(http_attempt_cap=1)
    with pytest.raises(pit.AttemptBudgetError, match="PREFLIGHT_V2_OPERATION_ID_INVALID"):
        ledger.reserve_attempt("")


def _massive_state(**overrides: object) -> pit.MassiveAssetSessionState:
    values: dict[str, object] = {
        "asset": "AAPL",
        "session_date": "2025-01-02",
        "origin_ns": 1_700_000_000_000_000_000,
        "stage": pit.MassiveStage.CONTRACT_SEARCH,
        "current_page": 1,
        "contract_candidate": None,
        "contract_candidate_count": 0,
        "contract_reference_count": 0,
        "quote_count": 0,
        "reference_validated": False,
        "disposition": (
            pit.OperationDisposition.LOCAL_CONTRACT_PENDING_OFFICIAL_MACHINE_READABLE_CONFIRMATION
        ),
        "failure": None,
    }
    values.update(overrides)
    return pit.MassiveAssetSessionState(**values)  # type: ignore[arg-type]


def test_massive_state_rejects_count_candidate_and_reference_contradictions() -> None:
    cases = [
        {"asset": ""},
        {"contract_candidate": "O:AAPL"},
        {"contract_candidate_count": 1},
        {"contract_reference_count": 1},
        {
            "contract_candidate_count": 1,
            "contract_candidate": "O:AAPL",
            "quote_count": 1,
        },
        {"reference_validated": True},
    ]
    for overrides in cases:
        with pytest.raises(pit.PitPreflightV2Error, match="PREFLIGHT_V2_MASSIVE_STATE_INVALID"):
            _massive_state(**overrides)


def test_plan_and_catalog_semantics_reject_shape_and_descriptor_drift() -> None:
    with pytest.raises(pit.PitPreflightV2Error, match="PREFLIGHT_V2_PLAN_DIMENSIONS_INVALID"):
        pit._plan_dimensions({})
    with pytest.raises(pit.PitPreflightV2Error, match="PREFLIGHT_V2_PLAN_DIMENSIONS_INVALID"):
        pit._plan_dimensions({"assets": ["AAPL"] * 8, "sentinel_sessions": []})
    with pytest.raises(pit.PitPreflightV2Error, match="PREFLIGHT_V2_PLAN_DIMENSIONS_INVALID"):
        pit._plan_dimensions(
            {"assets": [f"A{index}" for index in range(8)], "sentinel_sessions": [1]}
        )

    catalog = json.loads(
        (ROOT / "config/date_level_pit_preflight_endpoint_catalog_v2.json").read_text(
            encoding="utf-8"
        )
    )
    pit._validate_catalog_semantics(catalog)
    invalid_catalogs = [
        {},
        {"endpoints": ["bad"]},
        {"endpoints": []},
    ]
    for candidate in invalid_catalogs:
        with pytest.raises(pit.PitPreflightV2Error, match="PREFLIGHT_V2_CATALOG_INVALID"):
            pit._validate_catalog_semantics(candidate)

    for provider in ("fmp", "unusual_whales", "massive"):
        candidate = deepcopy(catalog)
        descriptor = next(item for item in candidate["endpoints"] if item["provider"] == provider)
        descriptor["endpoint_id"] = "drifted"
        with pytest.raises(pit.PitPreflightV2Error, match="PREFLIGHT_V2_CATALOG_INVALID"):
            pit._validate_catalog_semantics(candidate)

    assert not pit._is_massive_catalog_descriptor({"routes": []})
    assert not pit._is_massive_catalog_descriptor({"routes": [1, 2, 3]})


def test_budget_semantics_reject_every_independent_dimension() -> None:
    dimensions = {"asset_count": 8, "session_count": 7, "asset_day_count": 56}
    counts = {
        "fmp_one_minute_requests": 56,
        "unusual_whales_full_tape_zip_requests": 7,
        "massive_initial_contract_search_requests": 56,
        "massive_initial_contract_reference_conditional_max": 56,
        "massive_initial_quote_as_of_conditional_max": 56,
        "cap_request_count": pit.LOGICAL_REQUEST_CAP,
    }
    pagination = {
        "max_contract_pages_per_asset_day": pit.MAX_CONTRACT_SEARCH_PAGES,
        "contract_stage_order": [
            pit.OperationKind.CONTRACT_SEARCH.value,
            pit.OperationKind.CONTRACT_REFERENCE.value,
            pit.OperationKind.QUOTE_AS_OF.value,
        ],
        "contract_reference_max_per_asset_day": 1,
        "quote_as_of_max_per_asset_day": 1,
    }
    valid = {
        "dimensions": dimensions,
        "request_budget": counts,
        "massive_contract_pagination": pagination,
    }
    pit._validate_budget_semantics(valid, asset_count=8, session_count=7)
    candidates = [
        {},
        {**valid, "dimensions": {**dimensions, "asset_count": 9}},
        {**valid, "request_budget": {**counts, "cap_request_count": 1}},
        {
            **valid,
            "massive_contract_pagination": {**pagination, "quote_as_of_max_per_asset_day": 2},
        },
    ]
    for candidate in candidates:
        with pytest.raises(pit.PitPreflightV2Error, match="PREFLIGHT_V2_BUDGET_INVALID"):
            pit._validate_budget_semantics(candidate, asset_count=8, session_count=7)


def test_schema_evidence_hash_and_origin_helpers_fail_closed(tmp_path: Path) -> None:
    for value in (True, 1, 1_000_000_000):
        with pytest.raises(pit.PitPreflightV2Error, match="PREFLIGHT_V2_ORIGIN_NS_INVALID"):
            pit._validate_origin_ns(value)

    missing = tmp_path / "missing.json"
    with pytest.raises(pit.PitPreflightV2Error, match="PREFLIGHT_V2_SOURCE_SCHEMA_UNAVAILABLE"):
        pit._load_schema(missing)
    invalid = tmp_path / "invalid.json"
    invalid.write_text("[]", encoding="utf-8")
    with pytest.raises(pit.PitPreflightV2Error, match="PREFLIGHT_V2_SOURCE_SCHEMA_UNAVAILABLE"):
        pit._load_schema(invalid)
    with pytest.raises(
        pit.PitPreflightV2Error, match="PREFLIGHT_V2_HISTORICAL_AVAILABILITY_INVALID"
    ):
        pit._load_evidence_mapping(invalid)
    with pytest.raises(
        pit.PitPreflightV2Error, match="PREFLIGHT_V2_HISTORICAL_AVAILABILITY_INVALID"
    ):
        pit._file_sha256(missing)

    with pytest.raises(pit.PitPreflightV2Error, match="PREFLIGHT_V2_SOURCE_SCHEMA_UNAVAILABLE"):
        pit._schema_validator({"type": 1})
    with pytest.raises(pit.PitPreflightV2Error, match="SELF_HASH_INVALID"):
        pit._validated_self_hash({}, artifact_type="fixture", error_code="SELF_HASH_INVALID")
    document = {"artifact_type": "fixture", "value": 1}
    document["semantic_self_hash"] = "sha256:" + "0" * 64
    with pytest.raises(pit.PitPreflightV2Error, match="SELF_HASH_INVALID"):
        pit._validated_self_hash(document, artifact_type="fixture", error_code="SELF_HASH_INVALID")
    assert not pit._is_sha256("sha256:" + "A" * 64)
