"""Contract tests for the authenticated, bounded B1v3 preflight runner."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import httpx
import pytest
from jsonschema import Draft202012Validator

import mds650.b1v3_provider_preflight_runner_v2 as runner
from mds650.b1v3_provider_preflight_runner_v2 import (
    ProviderSecrets,
    execute_preflight,
    render_report,
    write_if_identical,
)
from mds650.b1v3_provider_preflight_v2 import CandidatePreflightPlan, CandidateSession


def _plan() -> CandidatePreflightPlan:
    origin = datetime(2024, 8, 2, 13, 35, tzinfo=UTC)
    return CandidatePreflightPlan(
        schema_version="b1v3-date-level-pit-preflight-plan-2.0",
        status="FROZEN_TARGET_BLIND_PENDING_PROVIDER_EXECUTION",
        target_blind=True,
        outcome_read_count=0,
        assets=("AAPL",),
        sessions=(
            CandidateSession(
                date="2024-08-02",
                role="training_warmup",
                open_utc="2024-08-02T13:30:00+00:00",
                close_utc="2024-08-02T20:00:00+00:00",
                forecast_origin_utc=origin.isoformat(),
                forecast_origin_ns=int(origin.timestamp() * 1_000_000_000),
                expected_regular_minutes=2,
            ),
        ),
        training_session_count=1,
        confirmation_session_count=0,
        source_confirmation_plan_sha256="a" * 64,
        plan_sha256="b" * 64,
    )


def _handler(seen: list[httpx.Request]) -> httpx.MockTransport:
    origin_ns = _plan().sessions[0].forecast_origin_ns

    def handle(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        if request.url.host == "financialmodelingprep.com":
            assert request.url.params["apikey"] == "fmp-secret"
            return httpx.Response(
                200,
                request=request,
                json=[
                    {
                        "date": "2024-08-02 09:30:00",
                        "open": 4.0,
                        "high": 4.1,
                        "low": 3.9,
                        "close": 4.0,
                    },
                    {
                        "date": "2024-08-02 09:31:00",
                        "open": 4.0,
                        "high": 4.2,
                        "low": 3.9,
                        "close": 4.1,
                    },
                ],
            )
        if request.url.host == "api.unusualwhales.com":
            assert request.method == "GET"
            assert "range" not in request.headers
            assert request.headers["authorization"] == "Bearer uw-secret"
            assert request.headers["accept"] == "application/json"
            return httpx.Response(
                200,
                request=request,
                headers={
                    "content-type": "application/zip",
                    "content-length": "1024",
                    "x-request-id": "uw-request",
                },
                content=b"not-read-by-runner",
            )
        if request.url.path == "/v3/reference/options/contracts":
            assert request.url.params["apiKey"] == "massive-secret"
            assert request.url.params["expiration_date.gte"] == "2024-09-01"
            assert request.url.params["expiration_date.lte"] == "2024-10-01"
            assert float(request.url.params["strike_price.gte"]) == 3.9975
            assert float(request.url.params["strike_price.lte"]) == 4.2025
            if request.url.params["expired"] == "true":
                return httpx.Response(200, request=request, json={"results": []})
            return httpx.Response(
                200,
                request=request,
                json={
                    "results": [
                        {
                            "ticker": "O:AAPL240920C00004000",
                            "underlying_ticker": "AAPL",
                            "expiration_date": "2024-09-20",
                            "strike_price": 4.0,
                            "contract_type": "call",
                        }
                    ]
                },
            )
        if request.url.path == "/v3/reference/options/contracts/O:AAPL240920C00004000":
            assert request.url.params["as_of"] == "2024-08-02"
            return httpx.Response(
                200,
                request=request,
                json={
                    "results": {
                        "ticker": "O:AAPL240920C00004000",
                        "underlying_ticker": "AAPL",
                    }
                },
            )
        if request.url.path == "/v3/quotes/O:AAPL240920C00004000":
            assert request.url.params["timestamp.lte"] == str(origin_ns)
            return httpx.Response(
                200,
                request=request,
                json={
                    "results": [
                        {
                            "sip_timestamp": origin_ns - 10_000_000_000,
                            "bid_price": 4.0,
                            "ask_price": 4.4,
                            "sequence_number": 9,
                        }
                    ]
                },
            )
        raise AssertionError(f"unexpected request {request.url}")

    return httpx.MockTransport(handle)


def test_bounded_runner_executes_documented_routes_and_is_idempotent(tmp_path: Path) -> None:
    seen: list[httpx.Request] = []
    secrets = ProviderSecrets(
        fmp="fmp-secret",
        unusual_whales="uw-secret",
        massive="massive-secret",
    )
    raw_root = tmp_path / "raw"
    report = execute_preflight(
        _plan(),
        secrets=secrets,
        raw_root=raw_root,
        free_bytes=100 * 1024**3,
        transport=_handler(seen),
    )

    assert report["status"] == "PASS_PROVIDER_PREFLIGHT_ASSUMPTION_BOUND"
    assert report["safe_to_acquire_predictors"] is True
    assert report["pit_semantics_confirmed"] is False
    assert report["network_attempt_count"] == 6
    massive_record = report["records"]["massive"][0]
    assert massive_record["primary_filter_pass"] is True
    assert massive_record["sensitivity_filter_pass"] is True
    assert len(seen) == 6
    rendered = render_report(report)
    assert b"fmp-secret" not in rendered
    assert b"uw-secret" not in rendered
    assert b"massive-secret" not in rendered
    assert str(tmp_path).encode() not in rendered

    def fail_if_called(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("cache replay unexpectedly called network")

    replay = execute_preflight(
        _plan(),
        secrets=secrets,
        raw_root=raw_root,
        free_bytes=100 * 1024**3,
        transport=httpx.MockTransport(fail_if_called),
    )
    assert render_report(replay) == rendered

    output = tmp_path / "report.json"
    assert write_if_identical(output, rendered) == "CREATED"
    assert write_if_identical(output, rendered) == "IDENTICAL"
    parsed = json.loads(output.read_text(encoding="utf-8"))
    assert parsed["report_sha256"] == report["report_sha256"]
    schema = json.loads(
        Path(
            "specs/001-pit-options-rv30/contracts/b1v3-provider-preflight-report-v2.schema.json"
        ).read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER).validate(
        parsed
    )


def test_retryable_http_failure_is_not_persisted_in_cache(tmp_path: Path) -> None:
    secrets = ProviderSecrets(
        fmp="fmp-secret",
        unusual_whales="uw-secret",
        massive="massive-secret",
    )
    raw_root = tmp_path / "raw"

    def fail_fmp(request: httpx.Request) -> httpx.Response:
        if request.url.host == "api.unusualwhales.com":
            return httpx.Response(
                200,
                request=request,
                headers={"content-type": "application/zip", "content-length": "1024"},
                content=b"not-read",
            )
        if request.url.host == "financialmodelingprep.com":
            return httpx.Response(503, request=request, json={"error": "retry"})
        raise AssertionError(f"unexpected request {request.url}")

    blocked = execute_preflight(
        _plan(),
        secrets=secrets,
        raw_root=raw_root,
        free_bytes=100 * 1024**3,
        transport=httpx.MockTransport(fail_fmp),
    )

    assert blocked["status"] == "BLOCKED_PROVIDER_PREFLIGHT"
    assert not (raw_root / "fmp/2024-08-02/AAPL.json").exists()

    seen: list[httpx.Request] = []
    recovered = execute_preflight(
        _plan(),
        secrets=secrets,
        raw_root=raw_root,
        free_bytes=100 * 1024**3,
        transport=_handler(seen),
    )
    assert recovered["status"] == "PASS_PROVIDER_PREFLIGHT_ASSUMPTION_BOUND"
    assert any(request.url.host == "financialmodelingprep.com" for request in seen)


def _cached_response(**overrides: object) -> runner._CachedResponse:
    values: dict[str, object] = {
        "provider": "massive",
        "evidence_key": "massive/fixture.json",
        "request_fingerprint": "fingerprint",
        "status_code": 200,
        "headers": {"content-type": "application/json"},
        "payload": {"results": {}},
        "response_sha256": "a" * 64,
        "network_attempts": 1,
    }
    values.update(overrides)
    return runner._CachedResponse(**values)  # type: ignore[arg-type]


def test_runner_secret_cache_and_report_boundaries_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(runner.B1V3PreflightError, match="B1V3_PREFLIGHT_PROVIDER_SECRET_MISSING"):
        ProviderSecrets(fmp="", unusual_whales="uw", massive="massive")

    store = runner._EvidenceStore(tmp_path / "cache")
    assert store.load("fixture.json", "fingerprint") is None
    cache_path = tmp_path / "cache" / "fixture.json"
    cache_path.write_text("not json", encoding="utf-8")
    with pytest.raises(runner.B1V3PreflightError, match="B1V3_PREFLIGHT_CACHE_INVALID"):
        store.load("fixture.json", "fingerprint")
    cache_path.write_text("[]", encoding="utf-8")
    with pytest.raises(runner.B1V3PreflightError, match="B1V3_PREFLIGHT_CACHE_INVALID"):
        store.load("fixture.json", "fingerprint")
    cache_path.write_text('{"request_fingerprint":"other"}', encoding="utf-8")
    with pytest.raises(runner.B1V3PreflightError, match="B1V3_PREFLIGHT_CACHE_REQUEST_CONFLICT"):
        store.load("fixture.json", "fingerprint")
    cache_path.write_text('{"request_fingerprint":"fingerprint"}', encoding="utf-8")
    with pytest.raises(runner.B1V3PreflightError, match="B1V3_PREFLIGHT_CACHE_HASH_INVALID"):
        store.load("fixture.json", "fingerprint")
    with pytest.raises(runner.B1V3PreflightError, match="B1V3_PREFLIGHT_EVIDENCE_KEY_INVALID"):
        store.load("../escape.json", "fingerprint")

    response = _cached_response()
    cache_path.unlink()
    store.store("fixture.json", response)
    cache_path.write_text("conflict", encoding="utf-8")
    with pytest.raises(runner.B1V3PreflightError, match="B1V3_PREFLIGHT_CACHE_OUTPUT_CONFLICT"):
        store.store("fixture.json", response)

    with pytest.raises(runner.B1V3PreflightError, match="B1V3_PREFLIGHT_REPORT_HASH_INVALID"):
        render_report({})
    report_path = tmp_path / "report.json"
    assert write_if_identical(report_path, b"first") == "CREATED"
    with pytest.raises(runner.B1V3PreflightError, match="B1V3_PREFLIGHT_REPORT_OUTPUT_CONFLICT"):
        write_if_identical(report_path, b"second")


def test_cached_response_reference_and_contract_schema_guards() -> None:
    valid = {
        "provider": "massive",
        "request_fingerprint": "fingerprint",
        "status_code": 200,
        "headers": {"content-type": "application/json"},
        "payload": {},
        "response_sha256": "a" * 64,
        "network_attempts": 1,
    }
    for key, value in (
        ("provider", None),
        ("status_code", True),
        ("headers", {1: "bad"}),
        ("network_attempts", 0),
    ):
        with pytest.raises(runner.B1V3PreflightError, match="B1V3_PREFLIGHT_CACHE_INVALID"):
            runner._cached_response({**valid, key: value}, evidence_key="fixture.json")

    with pytest.raises(
        runner.B1V3PreflightError, match="B1V3_PREFLIGHT_MASSIVE_CONTRACT_SCHEMA_INVALID"
    ):
        runner._historical_contract({})
    contract = runner._historical_contract(
        {
            "ticker": "O:AAPL250117C00100000",
            "underlying_ticker": "AAPL",
            "expiration_date": "2025-01-17",
            "strike_price": 100.0,
            "contract_type": "call",
        }
    )
    assert contract.underlying_ticker == "AAPL"

    with pytest.raises(runner.B1V3PreflightError, match="MASSIVE_REFERENCE_HTTP_500"):
        runner._validate_massive_reference(
            _cached_response(status_code=500), asset="AAPL", contract_id=contract.contract_id
        )
    with pytest.raises(
        runner.B1V3PreflightError, match="B1V3_PREFLIGHT_MASSIVE_REFERENCE_SCHEMA_INVALID"
    ):
        runner._validate_massive_reference(
            _cached_response(payload={}), asset="AAPL", contract_id=contract.contract_id
        )
    with pytest.raises(
        runner.B1V3PreflightError, match="B1V3_PREFLIGHT_MASSIVE_REFERENCE_MISMATCH"
    ):
        runner._validate_massive_reference(
            _cached_response(payload={"results": {"ticker": "wrong", "underlying_ticker": "AAPL"}}),
            asset="AAPL",
            contract_id=contract.contract_id,
        )


def test_runner_sanitizes_urls_headers_retries_and_attempt_counts() -> None:
    first = runner._request_fingerprint(
        provider="massive",
        method="GET",
        url="https://api.massive.com/v3/quotes/O:AAPL?apiKey=secret-one&cursor=1",
        params={"apiKey": "secret-one", "limit": 1},
        headers={"Accept": "application/json"},
    )
    second = runner._request_fingerprint(
        provider="massive",
        method="GET",
        url="https://api.massive.com/v3/quotes/O:AAPL?apiKey=secret-two&cursor=1",
        params={"apiKey": "secret-two", "limit": 1},
        headers={"Accept": "application/json"},
    )
    assert first == second
    assert runner._sanitized_request_headers(
        {"Authorization": "secret", "api-key": "secret", "Accept": "application/json"}
    ) == {"Accept": "application/json"}
    assert runner._sanitized_response_headers(
        {"Set-Cookie": "secret", "Retry-After": "2", "X-Request-Id": "request"}
    ) == {"retry-after": "2", "x-request-id": "request"}

    with pytest.raises(runner.B1V3PreflightError, match="B1V3_PREFLIGHT_MASSIVE_NEXT_URL_INVALID"):
        runner._normalized_massive_next_url("https://attacker.example/page=2")
    url, params = runner._normalized_massive_next_url(
        "https://api.massive.com/v3/reference/options/contracts?cursor=2&apiKey=secret"
    )
    assert url == "https://api.massive.com/v3/reference/options/contracts"
    assert params == {"cursor": "2"}
    assert runner._retry_delay({"retry-after": "-1"}, 1) == 0.0
    assert runner._retry_delay({"retry-after": "bad"}, 2) == 1.0
    assert runner._retry_delay({}, 20) == 60.0

    for value in (True, -1, "1"):
        with pytest.raises(
            runner.B1V3PreflightError, match="B1V3_PREFLIGHT_NETWORK_ATTEMPT_COUNT_INVALID"
        ):
            runner._record_attempt_count({"network_attempts": value})
    assert runner._record_attempt_count({}) == 0


def test_runner_execution_plan_validation_rejects_each_top_level_drift() -> None:
    runner._validate_execution_plan(_plan())
    candidates = [
        replace(_plan(), status="BLOCKED"),
        replace(_plan(), target_blind=False),
        replace(_plan(), outcome_read_count=1),
        replace(_plan(), assets=()),
        replace(_plan(), sessions=()),
        replace(_plan(), plan_sha256="short"),
    ]
    for candidate in candidates:
        with pytest.raises(
            runner.B1V3PreflightError, match="B1V3_PREFLIGHT_EXECUTION_PLAN_INVALID"
        ):
            runner._validate_execution_plan(candidate)


def test_transport_network_retry_budget_and_cache_write_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secrets = ProviderSecrets(fmp="fmp", unusual_whales="uw", massive="massive")
    store = runner._EvidenceStore(tmp_path / "cache")
    blocked = tmp_path / "cache" / "blocked.json"
    blocked.mkdir()
    with pytest.raises(runner.B1V3PreflightError, match="B1V3_PREFLIGHT_CACHE_WRITE_FAILED"):
        store.store("blocked.json", _cached_response())

    def connect_error(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("offline", request=request)

    client = runner._Transport(
        secrets=secrets,
        store=store,
        ledger=runner.AttemptLedger(http_attempt_cap=3, max_attempts_per_logical_request=3),
        transport=httpx.MockTransport(connect_error),
    )
    try:
        with pytest.raises(runner.B1V3PreflightError, match="B1V3_PREFLIGHT_NETWORK_FAILURE"):
            client.json_request(
                provider="fmp",
                operation_id="fmp:failure",
                evidence_key="fmp/failure.json",
                url="https://financialmodelingprep.com/test",
                params={},
            )
    finally:
        client.close()

    monkeypatch.setattr(runner.time, "sleep", lambda _delay: None)

    def unavailable(request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, request=request, content=b"not-json")

    client = runner._Transport(
        secrets=secrets,
        store=store,
        ledger=runner.AttemptLedger(http_attempt_cap=6, max_attempts_per_logical_request=3),
        transport=httpx.MockTransport(unavailable),
    )
    try:
        response = client.json_request(
            provider="fmp",
            operation_id="fmp:retry",
            evidence_key="fmp/retry.json",
            url="https://financialmodelingprep.com/test",
            params={},
        )
        uw_response = client.uw_zip_metadata(
            session_date="2024-08-02",
            evidence_key="uw/retry.json",
        )
        assert response.status_code == 503
        assert response.payload is None
        assert response.network_attempts == 3
        assert uw_response.status_code == 503
        assert uw_response.network_attempts == 3
        with pytest.raises(runner.B1V3PreflightError, match="B1V3_PREFLIGHT_PROVIDER_INVALID"):
            client._authenticated_request("unknown", {})
        with pytest.raises(
            runner.B1V3PreflightError,
            match="B1V3_PREFLIGHT_HTTP_ATTEMPT_CAP_EXCEEDED",
        ):
            client._reserve("extra")
    finally:
        client.close()


def test_massive_candidate_search_fail_closed_branches() -> None:
    session = _plan().sessions[0]
    contract = {
        "ticker": "O:AAPL240920C00004000",
        "underlying_ticker": "AAPL",
        "expiration_date": "2024-09-20",
        "strike_price": 4.0,
        "contract_type": "call",
    }

    class StubClient:
        def __init__(self, responses: list[runner._CachedResponse]) -> None:
            self.responses = iter(responses)

        def json_request(self, **_kwargs: object) -> runner._CachedResponse:
            return next(self.responses)

    def search(responses: list[runner._CachedResponse]) -> object:
        return runner._massive_candidates(
            StubClient(responses),  # type: ignore[arg-type]
            session,
            "AAPL",
            4.0,
            "massive/fixture",
        )

    candidates, _ = search([_cached_response(payload={"results": [contract]})])
    assert len(candidates) == 1

    with pytest.raises(runner.B1V3PreflightError, match="MASSIVE_SEARCH_HTTP_500"):
        search([_cached_response(status_code=500)])
    with pytest.raises(
        runner.B1V3PreflightError,
        match="B1V3_PREFLIGHT_MASSIVE_CONTRACT_SCHEMA_INVALID",
    ):
        search([_cached_response(payload={"results": [1]})])
    with pytest.raises(
        runner.B1V3PreflightError,
        match="B1V3_PREFLIGHT_MASSIVE_NEXT_URL_INVALID",
    ):
        search([_cached_response(payload={"results": [], "next_url": 1})])
    with pytest.raises(
        runner.B1V3PreflightError,
        match="B1V3_PREFLIGHT_MASSIVE_NO_HISTORICAL_CONTRACT",
    ):
        search(
            [
                _cached_response(payload={"results": []}),
                _cached_response(payload={"results": []}),
            ]
        )

    next_url = "https://api.massive.com/v3/reference/options/contracts?cursor=next"
    with pytest.raises(
        runner.B1V3PreflightError,
        match="B1V3_PREFLIGHT_MASSIVE_PAGINATION_CAP_EXCEEDED",
    ):
        search(
            [
                _cached_response(payload={"results": [], "next_url": next_url}),
                _cached_response(payload={"results": [], "next_url": next_url}),
                _cached_response(payload={"results": [], "next_url": next_url}),
            ]
        )

    with pytest.raises(
        runner.B1V3PreflightError,
        match="B1V3_PREFLIGHT_MASSIVE_CONTRACT_SCHEMA_INVALID",
    ):
        runner._historical_contract({**contract, "strike_price": True})
    with pytest.raises(
        runner.B1V3PreflightError,
        match="B1V3_PREFLIGHT_MASSIVE_ATM_MEDIUM_CONTRACT_MISSING",
    ):
        runner._select_preflight_contract(())
