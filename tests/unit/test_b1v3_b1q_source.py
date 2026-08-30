"""Contract tests for the target-blind B1v3 Massive source sealer."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import pytest

import mds650.b1v3_b1q_source as source
from mds650.b1v3_b1q_source import seal_b1q_source
from mds650.b1v3_confirmation import canonical_sha256, sha256_file
from mds650.b1v3_confirmation_build import (
    B1V3_CANONICAL_ASSETS,
    FrozenBuildInputs,
)

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = (
    ROOT
    / "specs"
    / "001-pit-options-rv30"
    / "contracts"
    / "b1v3-confirmation-b1q-source-v1.schema.json"
)


@dataclass(frozen=True, slots=True)
class Fixture:
    inputs: FrozenBuildInputs
    base_manifest_path: Path
    origins_path: Path
    attempts_path: Path
    contract_grid_path: Path
    cache_root: Path
    inventory_path: Path
    manifest_path: Path


def _source_request_hash(contract: str, params: dict[str, str]) -> str:
    material = (
        f"https://api.massive.com/v3/quotes/{contract}|"
        f"{json.dumps(params, sort_keys=True)}|route=B1Q|schema_version=4"
    )
    return hashlib.sha256(material.encode()).hexdigest()


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True), encoding="utf-8")


def _fixture(tmp_path: Path) -> Fixture:
    day = "2024-08-02"
    origin = datetime(2024, 8, 2, 13, 35, tzinfo=UTC)
    origin_ns = int(origin.timestamp() * 1_000_000_000)
    open_ns = int(datetime(2024, 8, 2, 13, 30, tzinfo=UTC).timestamp() * 1_000_000_000)
    close_ns = int(datetime(2024, 8, 2, 20, 0, tzinfo=UTC).timestamp() * 1_000_000_000)
    plan_hash = "a" * 64
    inputs = FrozenBuildInputs(
        plan_sha256=plan_hash,
        report_sha256="b" * 64,
        provider_candidate_plan_sha256="c" * 64,
        source_confirmation_plan_sha256="d" * 64,
        training_sessions=(day,),
        confirmation_sessions=(),
        fmp_records=(),
    )
    origins_rows: list[dict[str, object]] = []
    attempt_rows: list[dict[str, object]] = []
    contract_records: list[dict[str, object]] = []
    cache_root = tmp_path / "massive-cache"
    cache_root.mkdir(parents=True)
    for index, asset in enumerate(B1V3_CANONICAL_ASSETS, start=1):
        spot = 100.0 + index
        origin_id = f"{asset}|{day}|09:35"
        contract = f"O:{asset}240920C00100000"
        metadata = {
            "contract": contract,
            "expiry": "2024-09-20",
            "strike": 100.0,
            "option_type": "call",
            "dte": 49,
            "target_moneyness": 1.0,
            "bucket": "medium",
        }
        params = {
            "timestamp.gte": str(open_ns),
            "timestamp.lte": str(close_ns),
            "sort": "timestamp",
            "order": "asc",
            "limit": "50000",
        }
        source_hash = _source_request_hash(contract, params)
        cache_key = (
            f"provider=massive|asset={asset}|session_date={day}|expiry=2024-09-20|"
            f"strike=100.0|option_type=call|contract={contract}|route=B1Q|"
            "schema_version=4"
        )
        digest = hashlib.sha256(cache_key.encode()).hexdigest()[:16]
        cache_path = cache_root / f"{asset}_{day}_{contract.replace(':', '_')}_{digest}.json"
        sip_timestamp = origin_ns - 30_000_000_000
        _write_json(
            cache_path,
            {
                "schema_version": 4,
                "route": "B1Q",
                "asset": asset,
                "day": day,
                "contract": metadata,
                "cache_key": cache_key,
                "quote_cache_key": (
                    f"provider=massive|contract={contract}|session_date={day}|"
                    "route=B1Q|schema_version=4"
                ),
                "source_request_hash": source_hash,
                "request_params_sanitized": params,
                "request_id": f"request-{index}",
                "http_status": 200,
                "pages": 1,
                "pagination_complete": True,
                "provider_duplicate_rows_removed": 0,
                "results": [
                    {
                        "sip_timestamp": sip_timestamp,
                        "sequence_number": 1,
                        "bid_price": 1.0,
                        "ask_price": 1.2,
                    }
                ],
            },
        )
        origins_rows.append(
            {
                "origin_id": origin_id,
                "asset": asset,
                "session_date": day,
                "forecast_origin_utc": origin,
                "spot": spot,
                "session_segment": "first",
            }
        )
        attempt_rows.append(
            {
                **metadata,
                "asset": asset,
                "session_date": day,
                "origin_id": origin_id,
                "forecast_origin_utc": origin.isoformat(),
                "forecast_origin_ns": origin_ns,
                "spot": spot,
                "moneyness": 100.0 / spot,
                "rate": 0.05,
                "rate_source_date": "2024-08-01",
                "dividend_yield": 0.0,
                "dividend_assumption": "NO_PRE_ORIGIN_DIVIDEND_Q_ZERO",
                "source_request_hash": source_hash,
                "iv_success": True,
                "iv": 0.25,
                "failure_reason": None,
                "sip_timestamp": sip_timestamp,
                "bid": 1.0,
                "ask": 1.2,
                "quote_age_seconds": 30.0,
                "relative_spread": 2.0 / 11.0,
                "midpoint": 1.1,
            }
        )
        contract_records.append(
            {
                "asset": asset,
                "session_date": day,
                "spot": spot,
                "contracts": [metadata],
            }
        )
    origins_path = tmp_path / "b1_origins_target_blind.parquet"
    attempts_path = tmp_path / "b1_iv_attempts_20d.parquet"
    contract_grid_path = tmp_path / "resolved_contracts_b1v3_canonical_spot_v1.json"
    pl.DataFrame(origins_rows).write_parquet(origins_path)
    pl.DataFrame(attempt_rows, strict=False).write_parquet(attempts_path)
    _write_json(
        contract_grid_path,
        {"schema_version": "b1q-contract-grid-3.0", "records": contract_records},
    )
    base: dict[str, object] = {
        "schema_version": "1.0",
        "status": "PASS_TARGET_BLIND_BASE_PREDICTORS",
        "plan_sha256": plan_hash,
        "target_blind": True,
        "outcome_read_count": 0,
        "safe_to_read_outcomes": False,
        "origin_count": len(origins_rows),
        "origin_identity_sha256": canonical_sha256(
            {"origin_ids": [str(row["origin_id"]) for row in origins_rows]}
        ),
        "outputs": {
            "b1_origins": {
                "sha256": sha256_file(origins_path),
                "row_count": len(origins_rows),
            }
        },
    }
    base["manifest_sha256"] = canonical_sha256(base)
    base_path = tmp_path / "base_predictor_manifest.json"
    _write_json(base_path, base)
    return Fixture(
        inputs=inputs,
        base_manifest_path=base_path,
        origins_path=origins_path,
        attempts_path=attempts_path,
        contract_grid_path=contract_grid_path,
        cache_root=cache_root,
        inventory_path=tmp_path / "out" / "b1q_raw_payload_inventory.parquet",
        manifest_path=tmp_path / "out" / "b1q_source_manifest.json",
    )


def _seal(paths: Fixture) -> object:
    return seal_b1q_source(
        inputs=paths.inputs,
        base_manifest_path=paths.base_manifest_path,
        origins_path=paths.origins_path,
        attempts_path=paths.attempts_path,
        contract_grid_path=paths.contract_grid_path,
        cache_root=paths.cache_root,
        inventory_path=paths.inventory_path,
        manifest_path=paths.manifest_path,
        manifest_schema_path=SCHEMA,
    )


def _refresh_base_binding(paths: Fixture) -> None:
    origins = pl.read_parquet(paths.origins_path)
    base = json.loads(paths.base_manifest_path.read_text(encoding="utf-8"))
    base["origin_count"] = origins.height
    base["origin_identity_sha256"] = source._origin_identity_sha256(origins)
    base["outputs"]["b1_origins"]["sha256"] = sha256_file(paths.origins_path)
    base["manifest_sha256"] = canonical_sha256(
        {key: value for key, value in base.items() if key != "manifest_sha256"}
    )
    _write_json(paths.base_manifest_path, base)


def test_sealer_binds_attempts_contract_grid_and_raw_caches(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    first = _seal(paths)
    second = _seal(paths)

    assert first == second
    inventory = pl.read_parquet(paths.inventory_path)
    manifest = json.loads(paths.manifest_path.read_text(encoding="utf-8"))
    assert inventory.height == len(B1V3_CANONICAL_ASSETS)
    assert inventory["cache_file_sha256"].n_unique() == inventory.height
    assert manifest["status"] == "PASS_TARGET_BLIND_B1Q_SOURCE_BOUND"
    assert manifest["raw_payload_binding"]["status"] == "PRESENT_AND_VALIDATED"
    assert manifest["pit_invariants"]["future_selected_quote_rows"] == 0
    assert manifest["outcome_read_count"] == 0
    assert manifest["safe_to_read_outcomes"] is False
    assert manifest["manifest_sha256"] == canonical_sha256(
        {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    )


def test_sealer_rejects_target_columns_and_future_quotes(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    attempts_path = paths.attempts_path
    attempts = pl.read_parquet(attempts_path)
    attempts.with_columns(pl.lit(0.1).alias("rv30")).write_parquet(attempts_path)
    with pytest.raises(ValueError, match="B1V3_B1Q_SOURCE_TARGET_COLUMN_FORBIDDEN"):
        _seal(paths)

    paths = _fixture(tmp_path / "future")
    attempts_path = paths.attempts_path
    attempts = pl.read_parquet(attempts_path).with_columns(
        (pl.col("forecast_origin_ns") + 1).alias("sip_timestamp")
    )
    attempts.write_parquet(attempts_path)
    with pytest.raises(ValueError, match="B1V3_B1Q_SOURCE_FUTURE_QUOTE"):
        _seal(paths)


def test_sealer_rejects_cache_tamper_and_conflicting_output(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    cache_path = next(paths.cache_root.glob("*.json"))
    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    cache["source_request_hash"] = "f" * 64
    _write_json(cache_path, cache)
    with pytest.raises(ValueError, match="B1V3_B1Q_SOURCE_CACHE_INVALID"):
        _seal(paths)

    paths = _fixture(tmp_path / "conflict")
    _seal(paths)
    manifest_path = paths.manifest_path
    manifest_path.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="B1V3_B1Q_SOURCE_OUTPUT_CONFLICT"):
        _seal(paths)


def test_sealer_rejects_duplicate_attempt_identity(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    attempts_path = paths.attempts_path
    attempts = pl.read_parquet(attempts_path)
    pl.concat([attempts, attempts.head(1)]).write_parquet(attempts_path)
    with pytest.raises(ValueError, match="B1V3_B1Q_SOURCE_ATTEMPT_DUPLICATE"):
        _seal(paths)


@pytest.mark.parametrize(
    ("column", "value", "code"),
    [
        ("rate_source_date", "2024-08-02", "RATE_NOT_PRE_ORIGIN"),
        ("source_request_hash", "bad", "REQUEST_HASH_INVALID"),
        ("asset", "SPY", "ATTEMPT_ASSET_SCOPE_INVALID"),
    ],
)
def test_sealer_rejects_invalid_attempt_provenance(
    tmp_path: Path,
    column: str,
    value: object,
    code: str,
) -> None:
    paths = _fixture(tmp_path)
    attempts = pl.read_parquet(paths.attempts_path).with_columns(pl.lit(value).alias(column))
    attempts.write_parquet(paths.attempts_path)

    with pytest.raises(ValueError, match=f"B1V3_B1Q_SOURCE_{code}"):
        _seal(paths)


def test_sealer_rejects_contract_grid_drift_and_unverified_pagination(
    tmp_path: Path,
) -> None:
    paths = _fixture(tmp_path)
    grid = json.loads(paths.contract_grid_path.read_text(encoding="utf-8"))
    grid["records"][0]["contracts"][0]["strike"] = 99.0
    _write_json(paths.contract_grid_path, grid)
    with pytest.raises(ValueError, match="B1V3_B1Q_SOURCE_CONTRACT_METADATA_MISMATCH"):
        _seal(paths)

    paths = _fixture(tmp_path / "pagination")
    cache_path = next(paths.cache_root.glob("*.json"))
    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    cache["pagination_complete"] = False
    _write_json(cache_path, cache)
    with pytest.raises(ValueError, match="B1V3_B1Q_SOURCE_CACHE_INVALID"):
        _seal(paths)


def test_sealer_accepts_sequence_reordering_within_equal_sip_timestamp(
    tmp_path: Path,
) -> None:
    """Massive promises timestamp order, not sequence order inside timestamp ties."""
    paths = _fixture(tmp_path)
    cache_path = next(paths.cache_root.glob("*.json"))
    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    first = dict(cache["results"][0])
    cache["results"] = [
        {**first, "sequence_number": 21},
        {**first, "sequence_number": 1},
    ]
    _write_json(cache_path, cache)

    artifacts = _seal(paths)
    manifest = json.loads(artifacts.manifest_path.read_text(encoding="utf-8"))

    assert manifest["status"] == "PASS_TARGET_BLIND_B1Q_SOURCE_BOUND"


def test_sealer_rejects_decreasing_sip_timestamp_even_if_sequence_increases(
    tmp_path: Path,
) -> None:
    """A genuine timestamp reversal still violates the requested ascending sort."""
    paths = _fixture(tmp_path)
    cache_path = next(paths.cache_root.glob("*.json"))
    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    first = dict(cache["results"][0])
    cache["results"] = [
        {**first, "sequence_number": 1},
        {
            **first,
            "sip_timestamp": int(first["sip_timestamp"]) - 1,
            "sequence_number": 2,
        },
    ]
    _write_json(cache_path, cache)

    with pytest.raises(ValueError, match="B1V3_B1Q_SOURCE_CACHE_INVALID"):
        _seal(paths)


def test_sealer_rejects_base_hash_and_cache_identity_ambiguity(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    base = json.loads(paths.base_manifest_path.read_text(encoding="utf-8"))
    base["origin_count"] = 999
    _write_json(paths.base_manifest_path, base)
    with pytest.raises(ValueError, match="B1V3_B1Q_SOURCE_BASE_MANIFEST_HASH_INVALID"):
        _seal(paths)

    paths = _fixture(tmp_path / "ambiguous")
    cache_path = next(paths.cache_root.glob("*.json"))
    duplicate = cache_path.with_name(f"{cache_path.stem.rsplit('_', 1)[0]}_ffffffffffffffff.json")
    duplicate.write_bytes(cache_path.read_bytes())
    with pytest.raises(ValueError, match="B1V3_B1Q_SOURCE_CACHE_FILE_AMBIGUOUS"):
        _seal(paths)


def test_sealer_rejects_inventory_conflict_and_missing_schema(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    _seal(paths)
    pl.DataFrame({"broken": [1]}).write_parquet(paths.inventory_path)
    with pytest.raises(ValueError, match="B1V3_B1Q_SOURCE_OUTPUT_CONFLICT"):
        _seal(paths)

    paths = _fixture(tmp_path / "schema")
    with pytest.raises(ValueError, match="B1V3_CONFIRMATION_SCHEMA_MISSING"):
        seal_b1q_source(
            inputs=paths.inputs,
            base_manifest_path=paths.base_manifest_path,
            origins_path=paths.origins_path,
            attempts_path=paths.attempts_path,
            contract_grid_path=paths.contract_grid_path,
            cache_root=paths.cache_root,
            inventory_path=paths.inventory_path,
            manifest_path=paths.manifest_path,
            manifest_schema_path=tmp_path / "missing.schema.json",
        )


def test_json_and_attempt_schema_fail_closed(tmp_path: Path) -> None:
    invalid_json = tmp_path / "invalid.json"
    invalid_json.write_text("{", encoding="utf-8")
    with pytest.raises(ValueError, match="INVALID_DOCUMENT"):
        source._json_object(invalid_json, code="INVALID_DOCUMENT")

    invalid_json.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="INVALID_DOCUMENT"):
        source._json_object(invalid_json, code="INVALID_DOCUMENT")

    with pytest.raises(ValueError, match="B1V3_B1Q_SOURCE_ATTEMPTS_INVALID"):
        source._validate_attempt_schema(tmp_path / "missing.parquet")

    paths = _fixture(tmp_path / "schema")
    attempts = pl.read_parquet(paths.attempts_path)
    attempts.drop("ask").write_parquet(paths.attempts_path)
    with pytest.raises(ValueError, match="B1V3_B1Q_SOURCE_ATTEMPT_SCHEMA_INVALID"):
        source._validate_attempt_schema(paths.attempts_path)

    attempts.with_columns(pl.lit(1).alias("unexpected")).write_parquet(paths.attempts_path)
    with pytest.raises(ValueError, match="B1V3_B1Q_SOURCE_COLUMN_NOT_ALLOWLISTED"):
        source._validate_attempt_schema(paths.attempts_path)


@pytest.mark.parametrize(
    ("mutation", "code"),
    [
        ("missing", "ORIGIN_SCHEMA_INVALID"),
        ("target", "TARGET_COLUMN_FORBIDDEN"),
        ("scope", "ORIGIN_SCOPE_INVALID"),
    ],
)
def test_base_and_origin_validation_fail_closed(
    tmp_path: Path,
    mutation: str,
    code: str,
) -> None:
    paths = _fixture(tmp_path)
    origins = pl.read_parquet(paths.origins_path)
    if mutation == "missing":
        origins = origins.drop("spot")
    elif mutation == "target":
        origins = origins.with_columns(pl.lit(0.1).alias("rv30"))
    else:
        origins = origins.with_columns(pl.lit(0.0).alias("spot"))
    origins.write_parquet(paths.origins_path)
    _refresh_base_binding(paths)

    with pytest.raises(ValueError, match=f"B1V3_B1Q_SOURCE_{code}"):
        source._validate_base_and_origins(
            inputs=paths.inputs,
            base_manifest_path=paths.base_manifest_path,
            origins_path=paths.origins_path,
        )


def test_base_gate_and_attempt_semantics_fail_closed(tmp_path: Path) -> None:
    paths = _fixture(tmp_path / "base")
    base = json.loads(paths.base_manifest_path.read_text(encoding="utf-8"))
    base["status"] = "FAIL"
    base["manifest_sha256"] = canonical_sha256(
        {key: value for key, value in base.items() if key != "manifest_sha256"}
    )
    _write_json(paths.base_manifest_path, base)
    with pytest.raises(ValueError, match="B1V3_B1Q_SOURCE_BASE_GATE_INVALID"):
        source._validate_base_and_origins(
            inputs=paths.inputs,
            base_manifest_path=paths.base_manifest_path,
            origins_path=paths.origins_path,
        )

    paths = _fixture(tmp_path / "attempts")
    origins = pl.read_parquet(paths.origins_path)
    attempts = pl.read_parquet(paths.attempts_path)
    attempts.head(0).write_parquet(paths.attempts_path)
    with pytest.raises(ValueError, match="B1V3_B1Q_SOURCE_ATTEMPTS_EMPTY"):
        source._load_and_validate_attempts(paths.attempts_path, origins=origins)

    attempts.with_columns(pl.lit("unknown").alias("origin_id")).write_parquet(paths.attempts_path)
    with pytest.raises(ValueError, match="B1V3_B1Q_SOURCE_ATTEMPT_ORIGIN_SCOPE_INVALID"):
        source._load_and_validate_attempts(paths.attempts_path, origins=origins)

    attempts.with_columns((pl.col("spot") + 1.0).alias("spot")).write_parquet(paths.attempts_path)
    with pytest.raises(ValueError, match="B1V3_B1Q_SOURCE_ATTEMPT_ORIGIN_METADATA_INVALID"):
        source._load_and_validate_attempts(paths.attempts_path, origins=origins)

    attempts.with_columns(pl.lit("f" * 64).alias("source_request_hash")).write_parquet(
        paths.attempts_path
    )
    with pytest.raises(ValueError, match="B1V3_B1Q_SOURCE_REQUEST_HASH_REUSED"):
        source._load_and_validate_attempts(paths.attempts_path, origins=origins)


def test_contract_grid_shape_and_scope_fail_closed(tmp_path: Path) -> None:
    paths = _fixture(tmp_path)
    origins = pl.read_parquet(paths.origins_path)
    identities, _, _ = source._load_and_validate_attempts(
        paths.attempts_path,
        origins=origins,
    )
    valid = json.loads(paths.contract_grid_path.read_text(encoding="utf-8"))

    def assert_rejected(document: object, code: str) -> None:
        _write_json(paths.contract_grid_path, document)
        with pytest.raises(ValueError, match=f"B1V3_B1Q_SOURCE_{code}"):
            source._load_contract_grid(
                paths.contract_grid_path,
                origins=origins,
                identities=identities,
            )

    assert_rejected(
        {"schema_version": "wrong", "records": []},
        "CONTRACT_GRID_INVALID",
    )
    assert_rejected(
        {"schema_version": "b1q-contract-grid-3.0", "records": [None]},
        "CONTRACT_GRID_RECORD_INVALID",
    )

    document = json.loads(json.dumps(valid))
    document["records"][0]["spot"] = True
    assert_rejected(document, "CONTRACT_GRID_SCOPE_INVALID")

    document = json.loads(json.dumps(valid))
    document["records"][0]["contracts"] = []
    assert_rejected(document, "CONTRACT_GRID_EMPTY")

    document = json.loads(json.dumps(valid))
    document["records"][0]["contracts"] = [None]
    assert_rejected(document, "CONTRACT_GRID_RECORD_INVALID")

    document = json.loads(json.dumps(valid))
    document["records"][0]["contracts"].append(dict(document["records"][0]["contracts"][0]))
    assert_rejected(document, "CONTRACT_GRID_DUPLICATE")

    document = json.loads(json.dumps(valid))
    document["records"].pop()
    assert_rejected(document, "CONTRACT_GRID_SCOPE_INVALID")

    document = json.loads(json.dumps(valid))
    document["records"][0]["contracts"][0]["contract"] = "O:DIFFERENT"
    assert_rejected(document, "CONTRACT_SCOPE_INVALID")


@pytest.mark.parametrize(
    "mutation",
    ["secret", "invalid_json", "non_object", "pages", "row", "price"],
)
def test_cache_envelope_fail_closed(tmp_path: Path, mutation: str) -> None:
    paths = _fixture(tmp_path)
    cache_path = next(paths.cache_root.glob("*.json"))
    cache = json.loads(cache_path.read_text(encoding="utf-8"))
    if mutation == "secret":
        cache["api_key"] = "redacted"
        _write_json(cache_path, cache)
    elif mutation == "invalid_json":
        cache_path.write_text("{", encoding="utf-8")
    elif mutation == "non_object":
        _write_json(cache_path, [])
    elif mutation == "pages":
        cache["pages"] = 0
        _write_json(cache_path, cache)
    elif mutation == "row":
        cache["results"] = [1]
        _write_json(cache_path, cache)
    else:
        cache["results"][0]["bid_price"] = True
        _write_json(cache_path, cache)

    with pytest.raises(
        ValueError,
        match="B1V3_B1Q_SOURCE_CACHE_(?:SECRET_OR_PATH|INVALID)",
    ):
        _seal(paths)


def test_inventory_and_manifest_guards_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(ValueError, match="B1V3_B1Q_SOURCE_CACHE_ROOT_INVALID"):
        source._cache_index(tmp_path / "missing")
    with pytest.raises(ValueError, match="B1V3_B1Q_SOURCE_MANIFEST_HYGIENE_INVALID"):
        source._write_json_if_identical(
            tmp_path / "manifest.json",
            {"path": "C:/Users/example"},
        )

    paths = _fixture(tmp_path / "inventory")
    origins = pl.read_parquet(paths.origins_path)
    identities, _, _ = source._load_and_validate_attempts(
        paths.attempts_path,
        origins=origins,
    )
    _, _, contracts = source._load_contract_grid(
        paths.contract_grid_path,
        origins=origins,
        identities=identities,
    )
    first = identities.row(0, named=True)
    prefix = f"{first['asset']}_{first['session_date']}_{str(first['contract']).replace(':', '_')}"
    outside = tmp_path / "outside.json"
    outside.write_text("{}", encoding="utf-8")
    real_cache_index = source._cache_index
    monkeypatch.setattr(source, "_cache_index", lambda _: {prefix: (outside,)})
    with pytest.raises(ValueError, match="B1V3_B1Q_SOURCE_CACHE_PATH_INVALID"):
        source._build_inventory(
            cache_root=paths.cache_root,
            identities=identities,
            contracts=contracts,
        )

    monkeypatch.setattr(source, "_cache_index", real_cache_index)
    monkeypatch.setattr(
        source,
        "_validate_cache_payload",
        lambda **_: {"cache_file_sha256": "same"},
    )
    with pytest.raises(ValueError, match="B1V3_B1Q_SOURCE_DUPLICATE_PAYLOAD_HASH"):
        source._build_inventory(
            cache_root=paths.cache_root,
            identities=identities,
            contracts=contracts,
        )


def test_inventory_scope_guard_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    paths = _fixture(tmp_path)
    monkeypatch.setattr(source, "_build_inventory", lambda **_: pl.DataFrame())
    with pytest.raises(ValueError, match="B1V3_B1Q_SOURCE_INVENTORY_SCOPE_INVALID"):
        _seal(paths)
