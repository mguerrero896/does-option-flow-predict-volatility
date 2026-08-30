"""Target-blind base-panel contracts for the independent replication."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import exchange_calendars as xcals
import polars as pl
import pytest

from mds650 import b1_replication_build as sut
from mds650.b1_replication_build import (
    CANONICAL_ASSETS,
    ReplicationBaseInputs,
    build_replication_origin_grid,
)
from mds650.b1v3_confirmation import canonical_sha256


def _seal(document: dict[str, Any], field: str) -> dict[str, Any]:
    document.pop(field, None)
    document[field] = canonical_sha256(document)
    return document


def _write_json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document), encoding="utf-8")


def _replication_sessions() -> tuple[date, ...]:
    calendar = xcals.get_calendar("XNYS")
    return tuple(
        value.date()
        for value in calendar.sessions_in_range("2024-08-01", "2024-09-30")[:30]
    )


def _input_documents(tmp_path: Path) -> tuple[dict[str, Path], dict[str, dict[str, Any]]]:
    sessions = _replication_sessions()
    session_rows = [
        {"date": day.isoformat(), "role": "confirmation"} for day in sessions
    ]
    prereg = _seal(
        {
            "status": "FROZEN_BEFORE_PROVIDER_PAYLOAD",
            "target_blind": True,
            "replication_target_reads": 0,
        },
        "manifest_sha256",
    )
    primary_plan = _seal(
        {
            "source_confirmation_plan_sha256": prereg["manifest_sha256"],
            "target_blind": True,
            "outcome_read_count": 0,
            "sessions": [dict(row) for row in session_rows],
            "assets": list(CANONICAL_ASSETS),
        },
        "plan_sha256",
    )
    market_plan = _seal(
        {
            "source_confirmation_plan_sha256": prereg["manifest_sha256"],
            "target_blind": True,
            "outcome_read_count": 0,
            "sessions": [dict(row) for row in session_rows],
            "assets": ["SPY", "QQQ"],
        },
        "plan_sha256",
    )

    def report(plan: dict[str, Any], assets: tuple[str, ...]) -> dict[str, Any]:
        records = [
            {"session_date": day.isoformat(), "asset": asset}
            for day in sessions
            for asset in assets
        ]
        return _seal(
            {
                "plan_sha256": plan["plan_sha256"],
                "status": "PASS_PROVIDER_PREFLIGHT_ASSUMPTION_BOUND",
                "target_blind": True,
                "safe_to_acquire_predictors": True,
                "safe_to_read_outcomes": False,
                "outcome_read_count": 0,
                "records": {"fmp": records},
            },
            "report_sha256",
        )

    documents = {
        "prereg": prereg,
        "primary_plan": primary_plan,
        "primary_report": report(primary_plan, CANONICAL_ASSETS),
        "market_plan": market_plan,
        "market_report": report(market_plan, ("SPY", "QQQ")),
    }
    paths = {name: tmp_path / f"{name}.json" for name in documents}
    for name, document in documents.items():
        _write_json(paths[name], document)
    return paths, documents


def _load_inputs(paths: dict[str, Path]) -> ReplicationBaseInputs:
    return sut.load_replication_base_inputs(
        preregistration_path=paths["prereg"],
        primary_plan_path=paths["primary_plan"],
        primary_report_path=paths["primary_report"],
        market_plan_path=paths["market_plan"],
        market_report_path=paths["market_report"],
    )


def _persist_documents(
    paths: dict[str, Path],
    documents: dict[str, dict[str, Any]],
) -> None:
    for name, document in documents.items():
        _write_json(paths[name], document)


def _resign_plan_and_report(
    documents: dict[str, dict[str, Any]],
    label: str,
) -> None:
    plan = _seal(documents[f"{label}_plan"], "plan_sha256")
    report = documents[f"{label}_report"]
    report["plan_sha256"] = plan["plan_sha256"]
    _seal(report, "report_sha256")


def _fmp_cache_fixture(tmp_path: Path) -> tuple[ReplicationBaseInputs, Path, dict[str, Any]]:
    day = date(2024, 8, 2)
    opened = datetime(2024, 8, 2, 9, 30)
    payload = [
        {
            "date": (opened + timedelta(minutes=offset)).isoformat(sep=" "),
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "volume": 1000,
        }
        for offset in range(390)
    ]
    document: dict[str, Any] = {
        "schema_version": "b1v3-provider-preflight-cache-2.0",
        "provider": "fmp",
        "request_fingerprint": "a" * 64,
        "status_code": 200,
        "payload": payload,
        "response_sha256": "b" * 64,
    }
    document["cache_self_hash"] = canonical_sha256(document)
    cache_path = tmp_path / "fmp" / day.isoformat() / "AAPL.json"
    _write_json(cache_path, document)
    record: dict[str, Any] = {
        "asset": "AAPL",
        "session_date": day.isoformat(),
        "evidence_key": f"fmp/{day.isoformat()}/AAPL.json",
        "provider": "fmp",
        "pass": True,
        "request_fingerprint": "a" * 64,
        "response_sha256": "b" * 64,
        "exact_session_row_count": 390,
        "returned_row_count": 390,
        "provider_over_return_count": 0,
    }
    inputs = ReplicationBaseInputs(
        "c" * 64,
        "d" * 64,
        "e" * 64,
        "f" * 64,
        "0" * 64,
        (day,),
        (record,),
    )
    return inputs, tmp_path, document


def _install_base_artifact_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    *,
    spot_available: bool = True,
    preserve_origins: bool = True,
    forbidden_column: bool = False,
) -> None:
    origin_ids = ["AAPL:1", "AAPL:2"]
    origins = pl.DataFrame(
        {
            "origin_id": origin_ids,
            "asset": ["AAPL", "AAPL"],
            "session_date": ["2024-08-02", "2024-08-02"],
        }
    )
    bars_payload: dict[str, list[object]] = {
        "asset": ["AAPL", "AAPL"],
        "session_date": ["2024-08-02", "2024-08-02"],
        "bar_timestamp_raw_utc": [
            datetime(2024, 8, 2, 13, 30, tzinfo=UTC),
            datetime(2024, 8, 2, 13, 31, tzinfo=UTC),
        ],
    }
    if forbidden_column:
        bars_payload["rv30_outcome"] = [0.1, 0.2]
    bars = pl.DataFrame(bars_payload)
    spots = pl.DataFrame(
        {
            "origin_id": origin_ids,
            "spot": [100.0, 101.0],
            "spot_bar_timestamp_raw_utc": [
                datetime(2024, 8, 2, 13, 30, tzinfo=UTC),
                datetime(2024, 8, 2, 13, 31, tzinfo=UTC),
            ],
            "spot_available_at_utc": [
                datetime(2024, 8, 2, 13, 31, tzinfo=UTC),
                datetime(2024, 8, 2, 13, 32, tzinfo=UTC),
            ],
            "spot_available": [spot_available, spot_available],
            "spot_missing_reason": [None, None],
        }
    )
    b0_count = len(origin_ids) if preserve_origins else 1
    b0 = pl.DataFrame(
        {
            "origin_id": origin_ids[:b0_count],
            "b0_complete": [True] * b0_count,
        }
    )
    monkeypatch.setattr(sut, "build_replication_origin_grid", lambda _sessions: origins)
    monkeypatch.setattr(
        sut,
        "build_replication_fmp_corpus",
        lambda _inputs, *, cache_root: (bars, ({"cache_root": cache_root.name},)),
    )
    monkeypatch.setattr(sut, "build_spot_frame", lambda _bars, _origins: spots)
    monkeypatch.setattr(sut, "build_b0_target_blind", lambda _bars, _origins: b0)


def test_replication_origin_grid_is_early_close_aware_and_target_free() -> None:
    frame = build_replication_origin_grid((date(2024, 12, 23), date(2024, 12, 24)))

    counts = {
        str(row["session_date"]): int(row["len"])
        for row in frame.group_by("session_date").len().iter_rows(named=True)
    }
    assert counts == {"2024-12-23": 72 * 6, "2024-12-24": 36 * 6}
    assert tuple(sorted(frame["asset"].unique().to_list())) == CANONICAL_ASSETS
    assert frame["origin_id"].n_unique() == frame.height
    assert frame["role"].unique().to_list() == ["independent_replication"]
    assert not any(
        token in column.lower()
        for column in frame.columns
        for token in ("rv30", "qlike", "prediction", "outcome")
    )


def test_replication_origin_grid_rejects_non_session_or_unsorted_dates() -> None:
    with pytest.raises(ValueError, match="REPLICATION_ORIGIN_ALLOWLIST_INVALID"):
        build_replication_origin_grid((date(2024, 12, 24), date(2024, 12, 23)))
    with pytest.raises(ValueError, match="REPLICATION_ORIGIN_NOT_XNYS_SESSION"):
        build_replication_origin_grid((date(2024, 12, 25),))


def test_origin_grid_rejects_duplicate_origin_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Stamp:
        def __init__(self, value: datetime) -> None:
            self.value = value

        def to_pydatetime(self) -> datetime:
            return self.value

    class RepeatedClockCalendar:
        def is_session(self, _session: str) -> bool:
            return True

        def session_open(self, _session: str) -> Stamp:
            return Stamp(datetime(2024, 8, 2, 13, 30, tzinfo=UTC))

        def session_close(self, _session: str) -> Stamp:
            return Stamp(datetime(2024, 8, 2, 20, 0, tzinfo=UTC))

    monkeypatch.setattr(
        sut.xcals,
        "get_calendar",
        lambda _name: RepeatedClockCalendar(),
    )

    with pytest.raises(ValueError, match="^REPLICATION_ORIGIN_GRID_INVALID$"):
        build_replication_origin_grid((date(2024, 8, 2), date(2024, 8, 5)))


def test_replication_base_inputs_bind_both_reports_to_one_frozen_scope(tmp_path: Path) -> None:
    paths, _documents = _input_documents(tmp_path)

    inputs = _load_inputs(paths)

    assert inputs.sessions == _replication_sessions()
    assert len(inputs.fmp_records) == 30 * 8
    assert inputs.preregistration_sha256 == json.loads(
        paths["prereg"].read_text(encoding="utf-8")
    )["manifest_sha256"]


def test_replication_base_json_and_session_parsers_fail_closed(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{", encoding="utf-8")
    non_object = tmp_path / "array.json"
    non_object.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="BROKEN"):
        sut._json_object(malformed, code="BROKEN")
    with pytest.raises(ValueError, match="BROKEN"):
        sut._json_object(non_object, code="BROKEN")
    with pytest.raises(ValueError, match="REPLICATION_BASE_PLAN_SESSION_INVALID"):
        sut._session_dates({"sessions": "invalid"})
    with pytest.raises(ValueError, match="REPLICATION_BASE_PLAN_SESSION_INVALID"):
        sut._session_dates({"sessions": []})


def test_replication_base_inputs_reject_hash_and_preregistration_gate_drift(
    tmp_path: Path,
) -> None:
    paths, documents = _input_documents(tmp_path / "hash")
    documents["prereg"]["manifest_sha256"] = "0" * 64
    _persist_documents(paths, documents)
    with pytest.raises(ValueError, match="REPLICATION_BASE_PREREG_HASH_INVALID"):
        _load_inputs(paths)

    paths, documents = _input_documents(tmp_path / "gate")
    documents["prereg"]["target_blind"] = False
    _seal(documents["prereg"], "manifest_sha256")
    _persist_documents(paths, documents)
    with pytest.raises(ValueError, match="REPLICATION_BASE_PREREG_GATE_INVALID"):
        _load_inputs(paths)


@pytest.mark.parametrize(
    "document_name, hash_field, expected",
    [
        ("primary_plan", "plan_sha256", "REPLICATION_BASE_PRIMARY_PLAN_HASH_INVALID"),
        ("primary_report", "report_sha256", "REPLICATION_BASE_PRIMARY_REPORT_HASH_INVALID"),
        ("market_plan", "plan_sha256", "REPLICATION_BASE_MARKET_PLAN_HASH_INVALID"),
        ("market_report", "report_sha256", "REPLICATION_BASE_MARKET_REPORT_HASH_INVALID"),
    ],
)
def test_replication_base_inputs_reject_each_tampered_plan_or_report(
    tmp_path: Path,
    document_name: str,
    hash_field: str,
    expected: str,
) -> None:
    paths, documents = _input_documents(tmp_path)
    documents[document_name][hash_field] = "0" * 64
    _persist_documents(paths, documents)

    with pytest.raises(ValueError, match=expected):
        _load_inputs(paths)


@pytest.mark.parametrize("label", ["primary", "market"])
def test_replication_base_inputs_reject_each_plan_report_gate(
    tmp_path: Path,
    label: str,
) -> None:
    paths, documents = _input_documents(tmp_path)
    documents[f"{label}_report"]["safe_to_acquire_predictors"] = False
    _seal(documents[f"{label}_report"], "report_sha256")
    _persist_documents(paths, documents)

    with pytest.raises(ValueError, match=f"REPLICATION_BASE_{label.upper()}_GATE_INVALID"):
        _load_inputs(paths)


def test_replication_base_inputs_reject_session_and_asset_scope_drift(tmp_path: Path) -> None:
    paths, documents = _input_documents(tmp_path / "sessions")
    market_sessions = documents["market_plan"]["sessions"]
    market_sessions[-1]["date"] = "2024-10-01"
    _resign_plan_and_report(documents, "market")
    _persist_documents(paths, documents)
    with pytest.raises(ValueError, match="REPLICATION_BASE_PLAN_SESSION_MISMATCH"):
        _load_inputs(paths)

    paths, documents = _input_documents(tmp_path / "primary-assets")
    documents["primary_plan"]["assets"] = list(CANONICAL_ASSETS[:-1])
    _resign_plan_and_report(documents, "primary")
    _persist_documents(paths, documents)
    with pytest.raises(ValueError, match="REPLICATION_BASE_PRIMARY_ASSET_INVALID"):
        _load_inputs(paths)

    paths, documents = _input_documents(tmp_path / "market-assets")
    documents["market_plan"]["assets"] = ["QQQ", "SPY"]
    _resign_plan_and_report(documents, "market")
    _persist_documents(paths, documents)
    with pytest.raises(ValueError, match="REPLICATION_BASE_MARKET_ASSET_INVALID"):
        _load_inputs(paths)


def test_replication_base_inputs_reject_fmp_record_shape_and_scope_drift(tmp_path: Path) -> None:
    paths, documents = _input_documents(tmp_path / "container")
    documents["primary_report"]["records"] = None
    _seal(documents["primary_report"], "report_sha256")
    _persist_documents(paths, documents)
    with pytest.raises(ValueError, match="REPLICATION_BASE_FMP_RECORD_INVALID"):
        _load_inputs(paths)

    paths, documents = _input_documents(tmp_path / "record")
    documents["primary_report"]["records"]["fmp"][0] = "invalid"
    _seal(documents["primary_report"], "report_sha256")
    _persist_documents(paths, documents)
    with pytest.raises(ValueError, match="REPLICATION_BASE_FMP_RECORD_INVALID"):
        _load_inputs(paths)

    paths, documents = _input_documents(tmp_path / "scope")
    documents["primary_report"]["records"]["fmp"].pop()
    _seal(documents["primary_report"], "report_sha256")
    _persist_documents(paths, documents)
    with pytest.raises(ValueError, match="REPLICATION_BASE_FMP_SCOPE_INVALID"):
        _load_inputs(paths)


@pytest.mark.parametrize(
    "evidence_key",
    [None, "/absolute.json", "../escape.json", "other/file.json"],
)
def test_replication_cache_path_rejects_unsafe_or_missing_keys(
    tmp_path: Path,
    evidence_key: object,
) -> None:
    with pytest.raises(ValueError, match="REPLICATION_BASE_FMP_EVIDENCE_KEY_INVALID"):
        sut._safe_cache_path(tmp_path, evidence_key)

    with pytest.raises(FileNotFoundError, match="REPLICATION_BASE_FMP_CACHE_MISSING"):
        sut._safe_cache_path(tmp_path, "fmp/missing.json")


def test_replication_cache_path_rejects_a_resolved_escape(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache_root = tmp_path / "cache"
    cache_root.mkdir()
    resolved_root = cache_root.absolute()
    candidate = resolved_root / "fmp" / "escape.json"
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    original_resolve = Path.resolve

    def resolve(path: Path, *args: object, **kwargs: object) -> Path:
        if path == cache_root:
            return resolved_root
        if path == candidate:
            return outside
        return original_resolve(path, *args, **kwargs)

    monkeypatch.setattr(Path, "resolve", resolve)

    with pytest.raises(ValueError, match="REPLICATION_BASE_FMP_EVIDENCE_KEY_INVALID"):
        sut._safe_cache_path(cache_root, "fmp/escape.json")


def test_replication_fmp_corpus_builds_exact_grid_and_records_over_return(tmp_path: Path) -> None:
    inputs, cache_root, _document = _fmp_cache_fixture(tmp_path / "exact")
    frame, records = sut.build_replication_fmp_corpus(inputs, cache_root=cache_root)
    assert frame.height == 390
    assert records[0]["provider_over_return"] is False

    inputs, cache_root, document = _fmp_cache_fixture(tmp_path / "over-return")
    record = dict(inputs.fmp_records[0])
    document["payload"].insert(
        0,
        {
            "date": "2024-08-01 15:59:00",
            "open": 100.0,
            "high": 101.0,
            "low": 99.0,
            "close": 100.0,
            "volume": 1000,
        },
    )
    _seal(document, "cache_self_hash")
    cache_path = cache_root / str(record["evidence_key"])
    _write_json(cache_path, document)
    record["returned_row_count"] = 391
    record["provider_over_return_count"] = 1
    over_return_inputs = ReplicationBaseInputs(
        inputs.preregistration_sha256,
        inputs.primary_plan_sha256,
        inputs.primary_report_sha256,
        inputs.market_plan_sha256,
        inputs.market_report_sha256,
        inputs.sessions,
        (record,),
    )
    frame, records = sut.build_replication_fmp_corpus(
        over_return_inputs,
        cache_root=cache_root,
    )
    assert frame.height == 390
    assert records[0]["provider_over_return"] is True


def test_replication_fmp_corpus_rejects_grid_counts_and_duplicate_identity(tmp_path: Path) -> None:
    inputs, cache_root, document = _fmp_cache_fixture(tmp_path / "grid")
    document["payload"].pop()
    _seal(document, "cache_self_hash")
    _write_json(cache_root / str(inputs.fmp_records[0]["evidence_key"]), document)
    with pytest.raises(ValueError, match="REPLICATION_BASE_FMP_SESSION_GRID_INVALID"):
        sut.build_replication_fmp_corpus(inputs, cache_root=cache_root)

    inputs, cache_root, _document = _fmp_cache_fixture(tmp_path / "counts")
    record = dict(inputs.fmp_records[0])
    record["exact_session_row_count"] = 389
    mismatch = ReplicationBaseInputs(
        inputs.preregistration_sha256,
        inputs.primary_plan_sha256,
        inputs.primary_report_sha256,
        inputs.market_plan_sha256,
        inputs.market_report_sha256,
        inputs.sessions,
        (record,),
    )
    with pytest.raises(ValueError, match="REPLICATION_BASE_FMP_REPORT_COUNT_MISMATCH"):
        sut.build_replication_fmp_corpus(mismatch, cache_root=cache_root)

    duplicate = ReplicationBaseInputs(
        inputs.preregistration_sha256,
        inputs.primary_plan_sha256,
        inputs.primary_report_sha256,
        inputs.market_plan_sha256,
        inputs.market_report_sha256,
        inputs.sessions,
        (inputs.fmp_records[0], inputs.fmp_records[0]),
    )
    with pytest.raises(ValueError, match="REPLICATION_BASE_FMP_CORPUS_IDENTITY_INVALID"):
        sut.build_replication_fmp_corpus(duplicate, cache_root=cache_root)


def test_replication_base_writers_are_idempotent_and_fail_on_conflict(tmp_path: Path) -> None:
    frame = pl.DataFrame({"value": [1, 2]})
    parquet = tmp_path / "frame.parquet"
    first_hash = sut._write_parquet_if_identical(frame, parquet)
    assert first_hash == sut._write_parquet_if_identical(frame, parquet)
    with pytest.raises(ValueError, match="REPLICATION_BASE_OUTPUT_CONFLICT:frame.parquet"):
        sut._write_parquet_if_identical(pl.DataFrame({"value": [3]}), parquet)

    manifest = tmp_path / "manifest.json"
    payload = sut._json_bytes({"status": "PASS"})
    sut._write_json_if_identical(manifest, payload)
    sut._write_json_if_identical(manifest, payload)
    with pytest.raises(ValueError, match="REPLICATION_BASE_OUTPUT_CONFLICT:manifest.json"):
        sut._write_json_if_identical(manifest, sut._json_bytes({"status": "FAIL"}))
    with pytest.raises(ValueError, match="REPLICATION_BASE_MANIFEST_HYGIENE_INVALID"):
        sut._write_json_if_identical(tmp_path / "secret.json", b'{"api_key":"redacted"}\n')


def test_replication_base_artifact_builder_writes_target_blind_outputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _install_base_artifact_dependencies(monkeypatch)
    schema = tmp_path / "schema.json"
    _write_json(schema, {})
    inputs = ReplicationBaseInputs(
        "a" * 64,
        "b" * 64,
        "c" * 64,
        "d" * 64,
        "e" * 64,
        (date(2024, 8, 2),),
        (),
    )

    first = sut.build_replication_base_artifacts(
        inputs=inputs,
        fmp_cache_root=tmp_path / "cache",
        output_root=tmp_path / "output",
        manifest_path=tmp_path / "manifest.json",
        manifest_schema_path=schema,
    )
    second = sut.build_replication_base_artifacts(
        inputs=inputs,
        fmp_cache_root=tmp_path / "cache",
        output_root=tmp_path / "output",
        manifest_path=tmp_path / "manifest.json",
        manifest_schema_path=schema,
    )

    assert first == second
    assert all(
        path.is_file()
        for path in (
            first.origins_path,
            first.fmp_bars_path,
            first.b1_origins_path,
            first.b0_path,
            first.manifest_path,
        )
    )
    manifest = json.loads(first.manifest_path.read_text(encoding="utf-8"))
    assert manifest["target_blind"] is True
    assert manifest["outcome_read_count"] == 0


@pytest.mark.parametrize(
    "options, expected",
    [
        ({"spot_available": False}, "REPLICATION_BASE_ORIGIN_SPOT_INCOMPLETE"),
        ({"preserve_origins": False}, "REPLICATION_BASE_ORIGIN_PRESERVATION_FAILURE"),
        ({"forbidden_column": True}, "REPLICATION_BASE_FORBIDDEN_COLUMN"),
    ],
)
def test_replication_base_artifact_builder_fails_closed_on_invalid_intermediate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    options: dict[str, bool],
    expected: str,
) -> None:
    _install_base_artifact_dependencies(monkeypatch, **options)
    schema = tmp_path / "schema.json"
    _write_json(schema, {})
    inputs = ReplicationBaseInputs(
        "a" * 64,
        "b" * 64,
        "c" * 64,
        "d" * 64,
        "e" * 64,
        (date(2024, 8, 2),),
        (),
    )

    with pytest.raises(ValueError, match=expected):
        sut.build_replication_base_artifacts(
            inputs=inputs,
            fmp_cache_root=tmp_path / "cache",
            output_root=tmp_path / "output",
            manifest_path=tmp_path / "manifest.json",
            manifest_schema_path=schema,
        )
