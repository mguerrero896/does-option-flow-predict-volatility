"""Full Tape source-binding tests for replication B2 predictors."""

from __future__ import annotations

import json
from pathlib import Path

import polars as pl
import pytest
from jsonschema import Draft202012Validator

from mds650 import b1_replication_b2 as sut
from mds650.b1_replication_b2 import validate_full_tape_document
from mds650.b1v3_b2_confirmation import FullTapeContract
from mds650.b1v3_confirmation import canonical_sha256, sha256_file

ROOT = Path(__file__).resolve().parents[2]


def _checkpoint(
    preregistration_hash: str, provider_report_hash: str, session: str
) -> dict[str, object]:
    record: dict[str, object] = {
        "status": "PASS",
        "session_date": session,
        "preregistration_sha256": preregistration_hash,
        "provider_report_sha256": provider_report_hash,
        "session_contract_sha256": canonical_sha256(
            {
                "session_date": session,
                "preregistration_sha256": preregistration_hash,
                "provider_report_sha256": provider_report_hash,
            }
        ),
        "target_outcome_read": False,
        "outcome_read_count": 0,
        "secret_values_emitted": False,
        "personal_paths_emitted": False,
        "parquet_files": [],
    }
    record["checkpoint_sha256"] = canonical_sha256(record)
    return record


def _full_tape_document(
    preregistration_hash: str,
    provider_report_hash: str,
    sessions: tuple[str, ...],
) -> dict[str, object]:
    document: dict[str, object] = {
        "status": "PASS",
        "target_blind": True,
        "preregistration_sha256": preregistration_hash,
        "provider_report_sha256": provider_report_hash,
        "authorized_session_count": len(sessions),
        "completed_session_count": len(sessions),
        "pending_session_count": 0,
        "pending_sessions": [],
        "sessions": [
            _checkpoint(preregistration_hash, provider_report_hash, session)
            for session in sessions
        ],
        "target_outcome_read": False,
        "outcome_read_count": 0,
        "secret_values_emitted": False,
        "personal_paths_emitted": False,
    }
    document["manifest_sha256"] = canonical_sha256(document)
    return document


def _rehash(document: dict[str, object]) -> dict[str, object]:
    document.pop("manifest_sha256", None)
    document["manifest_sha256"] = canonical_sha256(document)
    return document


def _write_json(path: Path, document: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document), encoding="utf-8")


def _base_fixture(
    tmp_path: Path, preregistration_hash: str
) -> tuple[dict[str, Path], pl.DataFrame]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    paths = {
        "base": tmp_path / "base.json",
        "origins": tmp_path / "origins.parquet",
        "schema": tmp_path / "schema.json",
        "output": tmp_path / "output",
        "manifest": tmp_path / "manifest.json",
    }
    origins = pl.DataFrame({"origin_id": [f"origin-{index}" for index in range(12_744)]})
    origins.write_parquet(paths["origins"])
    base: dict[str, object] = {
        "status": "PASS_TARGET_BLIND_BASE_PREDICTORS",
        "preregistration_sha256": preregistration_hash,
        "target_blind": True,
        "outcome_read_count": 0,
        "safe_to_read_outcomes": False,
        "outputs": {"origins": {"sha256": sha256_file(paths["origins"])}},
    }
    base["manifest_sha256"] = canonical_sha256(base)
    _write_json(paths["base"], base)
    _write_json(paths["schema"], {})
    return paths, origins


def _install_builder_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    origins: pl.DataFrame,
    *,
    origin_mode: str = "valid",
) -> None:
    variants = {
        "primary_5m_60s": (),
        "sensitivity_5m_0s": (),
        "sensitivity_15m_60s": (),
    }
    monkeypatch.setattr(sut, "_partition_index", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(sut, "_build_raw_matrices", lambda **_kwargs: variants)
    monkeypatch.setattr(sut, "audit_uw_session_asset_incidents", lambda **_kwargs: [])
    monkeypatch.setattr(
        sut,
        "audit_b2_canonical_traceability",
        lambda **_kwargs: ([], "PASS_NO_CONFOUNDED_ZERO_OBSERVED"),
    )
    sidecar = pl.DataFrame(
        {
            "origin_id": origins["origin_id"],
            "variant": ["primary_5m_60s"] * origins.height,
        }
    )
    monkeypatch.setattr(
        sut,
        "build_b2_availability_sidecar",
        lambda **_kwargs: (sidecar, {"eligible": origins.height}),
    )

    def combine(
        _paths: object,
        *,
        sidecar: pl.DataFrame,
        variant: str,
        destination: Path,
    ) -> tuple[pl.DataFrame, str]:
        assert sidecar.height == origins.height
        count = origins.height - 1 if origin_mode == "missing" else origins.height
        origin_ids = origins["origin_id"].head(count).to_list()
        if origin_mode == "duplicate":
            origin_ids[-1] = origin_ids[0]
        frame = pl.DataFrame(
            {
                "origin_id": origin_ids,
                "b2v2_availability_eligible": [index % 2 == 0 for index in range(count)],
            }
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        frame.write_parquet(destination)
        return frame, sha256_file(destination)

    monkeypatch.setattr(sut, "_combine_variant", combine)


def _build_b2(
    paths: dict[str, Path],
    preregistration_hash: str,
    contract: FullTapeContract,
) -> sut.ReplicationB2Artifacts:
    return sut.build_replication_b2_artifacts(
        preregistration_sha256=preregistration_hash,
        full_tape_contract=contract,
        base_manifest_path=paths["base"],
        origins_path=paths["origins"],
        sessions=("2024-12-10",),
        data_root=paths["output"] / "data",
        event_root=paths["output"] / "events",
        output_root=paths["output"],
        manifest_path=paths["manifest"],
        manifest_schema_path=paths["schema"],
    )


def test_full_tape_document_is_bound_to_preregistration_and_provider_report() -> None:
    preregistration_hash = "a" * 64
    provider_report_hash = "b" * 64
    session = "2024-12-10"
    document = _full_tape_document(preregistration_hash, provider_report_hash, (session,))

    contract = validate_full_tape_document(
        document,
        preregistration_sha256=preregistration_hash,
        provider_report_sha256=provider_report_hash,
        sessions=(session,),
    )

    assert contract.manifest_sha256 == document["manifest_sha256"]
    assert tuple(contract.session_records) == (session,)


def test_replication_b2_schema_encodes_three_variant_sidecar_contract() -> None:
    """The sidecar has one row per origin and latency variant, not per origin."""
    schema = json.loads(
        (
            ROOT / "specs/001-pit-options-rv30/contracts/"
            "b1-independent-replication-b2-v1.schema.json"
        ).read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(schema)

    assert schema["$defs"]["sidecar"]["properties"]["row_count"] == {"const": 38_232}
    assert schema["$defs"]["variant"]["properties"]["row_count"] == {"const": 12_744}
    assert (
        "PASS_NO_CONFOUNDED_ZERO_OBSERVED"
        in schema["properties"]["legacy_zero_coding_gate"]["enum"]
    )


@pytest.mark.parametrize(
    "field, invalid",
    [
        ("status", "FAIL"),
        ("target_blind", False),
        ("preregistration_sha256", "wrong"),
        ("provider_report_sha256", "wrong"),
        ("authorized_session_count", 2),
        ("completed_session_count", 0),
        ("pending_session_count", 1),
        ("pending_sessions", ["2024-12-11"]),
        ("target_outcome_read", True),
        ("outcome_read_count", 1),
        ("secret_values_emitted", True),
        ("personal_paths_emitted", True),
        ("sessions", "not-a-list"),
    ],
)
def test_full_tape_document_rejects_every_top_level_gate(field: str, invalid: object) -> None:
    preregistration_hash = "a" * 64
    provider_report_hash = "b" * 64
    document = _full_tape_document(
        preregistration_hash,
        provider_report_hash,
        ("2024-12-10",),
    )
    document[field] = invalid
    _rehash(document)

    with pytest.raises(ValueError, match="REPLICATION_B2_ACQUISITION_GATE_INVALID"):
        validate_full_tape_document(
            document,
            preregistration_sha256=preregistration_hash,
            provider_report_sha256=provider_report_hash,
            sessions=("2024-12-10",),
        )


def test_full_tape_document_rejects_a_bad_manifest_hash() -> None:
    document = _full_tape_document("a" * 64, "b" * 64, ("2024-12-10",))
    document["manifest_sha256"] = "0" * 64

    with pytest.raises(ValueError, match="REPLICATION_B2_ACQUISITION_GATE_INVALID"):
        validate_full_tape_document(
            document,
            preregistration_sha256="a" * 64,
            provider_report_sha256="b" * 64,
            sessions=("2024-12-10",),
        )


@pytest.mark.parametrize(
    "field, invalid",
    [
        ("status", "FAIL"),
        ("preregistration_sha256", "wrong"),
        ("provider_report_sha256", "wrong"),
        ("session_contract_sha256", "wrong"),
        ("target_outcome_read", True),
        ("outcome_read_count", 1),
        ("secret_values_emitted", True),
        ("personal_paths_emitted", True),
        ("checkpoint_sha256", 7),
    ],
)
def test_full_tape_document_rejects_every_session_gate(field: str, invalid: object) -> None:
    preregistration_hash = "a" * 64
    provider_report_hash = "b" * 64
    document = _full_tape_document(
        preregistration_hash,
        provider_report_hash,
        ("2024-12-10",),
    )
    records = document["sessions"]
    assert isinstance(records, list)
    record = records[0]
    assert isinstance(record, dict)
    record[field] = invalid
    if field != "checkpoint_sha256":
        record.pop("checkpoint_sha256")
        record["checkpoint_sha256"] = canonical_sha256(record)
    _rehash(document)

    with pytest.raises(ValueError, match="REPLICATION_B2_ACQUISITION_SESSION_INVALID"):
        validate_full_tape_document(
            document,
            preregistration_sha256=preregistration_hash,
            provider_report_sha256=provider_report_hash,
            sessions=("2024-12-10",),
        )


def test_full_tape_document_rejects_non_mapping_duplicate_and_scope_drift() -> None:
    preregistration_hash = "a" * 64
    provider_report_hash = "b" * 64
    document = _full_tape_document(
        preregistration_hash,
        provider_report_hash,
        ("2024-12-10",),
    )
    document["sessions"] = ["invalid"]
    _rehash(document)
    with pytest.raises(ValueError, match="REPLICATION_B2_ACQUISITION_SESSION_INVALID"):
        validate_full_tape_document(
            document,
            preregistration_sha256=preregistration_hash,
            provider_report_sha256=provider_report_hash,
            sessions=("2024-12-10",),
        )

    duplicate = _full_tape_document(
        preregistration_hash,
        provider_report_hash,
        ("2024-12-10", "2024-12-10"),
    )
    with pytest.raises(ValueError, match="REPLICATION_B2_ACQUISITION_SESSION_INVALID"):
        validate_full_tape_document(
            duplicate,
            preregistration_sha256=preregistration_hash,
            provider_report_sha256=provider_report_hash,
            sessions=("2024-12-10", "2024-12-10"),
        )

    scope = _full_tape_document(
        preregistration_hash,
        provider_report_hash,
        ("2024-12-10",),
    )
    scope["authorized_session_count"] = 2
    scope["completed_session_count"] = 2
    _rehash(scope)
    with pytest.raises(ValueError, match="REPLICATION_B2_ACQUISITION_SESSION_SCOPE_INVALID"):
        validate_full_tape_document(
            scope,
            preregistration_sha256=preregistration_hash,
            provider_report_sha256=provider_report_hash,
            sessions=("2024-12-10", "2024-12-11"),
        )


def test_full_tape_contract_loader_validates_json_and_schema(tmp_path: Path) -> None:
    preregistration_hash = "a" * 64
    provider_report_hash = "b" * 64
    document = _full_tape_document(
        preregistration_hash,
        provider_report_hash,
        ("2024-12-10",),
    )
    path = tmp_path / "contract.json"
    schema = tmp_path / "schema.json"
    _write_json(path, document)
    _write_json(schema, {})

    contract = sut.load_replication_full_tape_contract(
        path,
        schema_path=schema,
        preregistration_sha256=preregistration_hash,
        provider_report_sha256=provider_report_hash,
        sessions=("2024-12-10",),
    )

    assert contract.manifest_sha256 == document["manifest_sha256"]


def test_replication_b2_json_reader_and_manifest_writer_fail_closed(tmp_path: Path) -> None:
    malformed = tmp_path / "malformed.json"
    malformed.write_text("{", encoding="utf-8")
    non_object = tmp_path / "array.json"
    non_object.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="BROKEN"):
        sut._json_object(malformed, code="BROKEN")
    with pytest.raises(ValueError, match="BROKEN"):
        sut._json_object(non_object, code="BROKEN")

    path = tmp_path / "manifest.json"
    first_hash = sut._write_manifest(path, {"status": "PASS"})
    assert first_hash == sut._write_manifest(path, {"status": "PASS"})
    with pytest.raises(ValueError, match="REPLICATION_B2_MANIFEST_OUTPUT_CONFLICT"):
        sut._write_manifest(path, {"status": "FAIL"})
    with pytest.raises(ValueError, match="REPLICATION_B2_MANIFEST_HYGIENE_INVALID"):
        sut._write_manifest(tmp_path / "secret.json", {"authorization": "redacted"})


def test_replication_b2_builder_writes_three_source_bound_variants(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preregistration_hash = "a" * 64
    paths, origins = _base_fixture(tmp_path, preregistration_hash)
    _install_builder_dependencies(monkeypatch, origins)
    contract = FullTapeContract("c" * 64, {"2024-12-10": {}})

    first = _build_b2(paths, preregistration_hash, contract)
    second = _build_b2(paths, preregistration_hash, contract)

    assert first == second
    assert first.primary_path.is_file()
    assert first.sidecar_path.is_file()
    manifest = json.loads(first.manifest_path.read_text(encoding="utf-8"))
    assert set(manifest["variants"]) == {
        "primary_5m_60s",
        "sensitivity_5m_0s",
        "sensitivity_15m_60s",
    }
    assert manifest["outcome_read_count"] == 0


def test_replication_b2_builder_rejects_base_origin_and_corrected_scope_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    preregistration_hash = "a" * 64
    contract = FullTapeContract("c" * 64, {"2024-12-10": {}})

    paths, origins = _base_fixture(tmp_path / "base", preregistration_hash)
    base = json.loads(paths["base"].read_text(encoding="utf-8"))
    base["status"] = "FAIL"
    _write_json(paths["base"], _rehash(base))
    with pytest.raises(ValueError, match="REPLICATION_B2_BASE_GATE_INVALID"):
        _build_b2(paths, preregistration_hash, contract)

    paths, origins = _base_fixture(tmp_path / "binding", preregistration_hash)
    base = json.loads(paths["base"].read_text(encoding="utf-8"))
    base["outputs"] = None
    _write_json(paths["base"], _rehash(base))
    with pytest.raises(ValueError, match="REPLICATION_B2_ORIGIN_BINDING_INVALID"):
        _build_b2(paths, preregistration_hash, contract)

    paths, origins = _base_fixture(tmp_path / "origin-scope", preregistration_hash)
    origins = origins.slice(1)
    origins.write_parquet(paths["origins"])
    base = json.loads(paths["base"].read_text(encoding="utf-8"))
    base["outputs"]["origins"]["sha256"] = sha256_file(paths["origins"])
    _write_json(paths["base"], _rehash(base))
    with pytest.raises(ValueError, match="REPLICATION_B2_ORIGIN_SCOPE_INVALID"):
        _build_b2(paths, preregistration_hash, contract)

    for mode in ("missing", "duplicate"):
        paths, origins = _base_fixture(tmp_path / mode, preregistration_hash)
        _install_builder_dependencies(monkeypatch, origins, origin_mode=mode)
        with pytest.raises(
            ValueError,
            match="REPLICATION_B2_CORRECTED_ORIGIN_PRESERVATION_FAILURE",
        ):
            _build_b2(paths, preregistration_hash, contract)
