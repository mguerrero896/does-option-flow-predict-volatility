"""Tests for the target-blind B1Q panel-admissibility gate."""

from __future__ import annotations

import hashlib
import importlib
import importlib.util
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Protocol, cast

import pytest

MODULE_NAME = "mds650.target_blind_panel_b1q_eligibility_v1"
ROOT = Path(__file__).resolve().parents[2]
MANIFEST = (
    ROOT
    / "artifacts/target_blind_v24_sourcebound_20260812"
    / "target_blind_common_predictor_manifest_v24.json"
)
SOURCE_COVERAGE = ROOT / "artifacts/corrected_development_v1/source_coverage_ledger.json"


class _EligibilityGate(Protocol):
    """Public gate surface covered by this test."""

    def build_target_blind_panel_b1q_eligibility_v1(
        self, *, panel_manifest_path: Path, source_coverage_path: Path
    ) -> dict[str, object]:
        """Build a target-free panel eligibility decision."""

    def validate_target_blind_panel_b1q_eligibility_v1(
        self, decision: Mapping[str, object]
    ) -> None:
        """Validate the decision's schema, binding and fail-closed state."""

    def write_target_blind_panel_b1q_eligibility_v1(
        self,
        *,
        panel_manifest_path: Path,
        source_coverage_path: Path,
        output_path: Path,
    ) -> Path:
        """Write an immutable eligibility decision."""


def _module() -> _EligibilityGate:
    """Load the implementation only after proving the TDD RED state."""
    assert importlib.util.find_spec(MODULE_NAME) is not None, (
        "target-blind B1Q panel eligibility gate is required"
    )
    return cast(_EligibilityGate, importlib.import_module(MODULE_NAME))


def _canonical_sha256(document: Mapping[str, object]) -> str:
    """Compute the decision hash independently of production code."""
    payload = json.dumps(
        document,
        allow_nan=False,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _read_object(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def test_existing_v24_panel_is_not_admissible_for_evaluation() -> None:
    """A target-blind panel cannot bypass the current blocked B1Q ledger."""
    decision = _module().build_target_blind_panel_b1q_eligibility_v1(
        panel_manifest_path=MANIFEST,
        source_coverage_path=SOURCE_COVERAGE,
    )

    assert decision["status"] == "PANEL_NOT_ELIGIBLE_FOR_EVALUATION"
    assert decision["b1q_source_coverage_status"] == "BLOCKED"
    assert decision["b1q_unresolved_origin_count"] == 34080
    assert decision["safe_to_evaluate"] is False
    assert decision["safe_to_reconcile_existing_results"] == "NO"
    assert decision["safe_to_open_or_evaluate_oos"] == "NO"
    assert decision["reason_codes"] == ["B1Q_EXOGENOUS_INPUT_PROVENANCE_UNRESOLVED"]
    assert decision["semantic_self_hash"] == _canonical_sha256(
        {key: value for key, value in decision.items() if key != "semantic_self_hash"}
    )


def test_gate_binds_exact_manifest_and_source_coverage_bytes(tmp_path: Path) -> None:
    """A copied or changed evidence file cannot silently alter admissibility."""
    manifest_copy = tmp_path / "manifest.json"
    coverage_copy = tmp_path / "coverage.json"
    manifest_copy.write_bytes(MANIFEST.read_bytes())
    coverage_copy.write_bytes(SOURCE_COVERAGE.read_bytes())
    coverage_copy.write_text("{}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="B1Q_PANEL_ELIGIBILITY_SOURCE_COVERAGE_INVALID"):
        _module().build_target_blind_panel_b1q_eligibility_v1(
            panel_manifest_path=manifest_copy,
            source_coverage_path=coverage_copy,
        )


def test_validator_rejects_a_rehashed_positive_upgrade() -> None:
    """Rehashing a decision cannot turn an unresolved B1Q source into a pass."""
    module = _module()
    decision = module.build_target_blind_panel_b1q_eligibility_v1(
        panel_manifest_path=MANIFEST,
        source_coverage_path=SOURCE_COVERAGE,
    )
    decision["safe_to_evaluate"] = True
    decision["semantic_self_hash"] = _canonical_sha256(
        {key: value for key, value in decision.items() if key != "semantic_self_hash"}
    )

    with pytest.raises(ValueError, match="B1Q_PANEL_ELIGIBILITY_POLICY_INVALID"):
        module.validate_target_blind_panel_b1q_eligibility_v1(decision)


def test_writer_is_idempotent_and_rejects_divergent_output(tmp_path: Path) -> None:
    """Eligibility output is immutable and deterministic."""
    module = _module()
    output = tmp_path / "eligibility.json"
    module.write_target_blind_panel_b1q_eligibility_v1(
        panel_manifest_path=MANIFEST,
        source_coverage_path=SOURCE_COVERAGE,
        output_path=output,
    )
    first = output.read_bytes()
    module.write_target_blind_panel_b1q_eligibility_v1(
        panel_manifest_path=MANIFEST,
        source_coverage_path=SOURCE_COVERAGE,
        output_path=output,
    )
    assert output.read_bytes() == first
    output.write_text("{}\n", encoding="utf-8")

    with pytest.raises(ValueError, match="B1Q_PANEL_ELIGIBILITY_OUTPUT_CONFLICT"):
        module.write_target_blind_panel_b1q_eligibility_v1(
            panel_manifest_path=MANIFEST,
            source_coverage_path=SOURCE_COVERAGE,
            output_path=output,
        )


def test_missing_registered_input_fails_closed(tmp_path: Path) -> None:
    """A missing registered input is never treated as an empty pass."""
    with pytest.raises(ValueError, match="B1Q_PANEL_ELIGIBILITY_MANIFEST_INVALID"):
        _module().build_target_blind_panel_b1q_eligibility_v1(
            panel_manifest_path=tmp_path / "missing.json",
            source_coverage_path=SOURCE_COVERAGE,
        )


def test_non_object_registered_input_fails_closed(tmp_path: Path) -> None:
    """A syntactically valid non-object input is rejected before hashing."""
    invalid = tmp_path / "manifest.json"
    invalid.write_text("[]\n", encoding="utf-8")
    with pytest.raises(ValueError, match="B1Q_PANEL_ELIGIBILITY_MANIFEST_INVALID"):
        _module().build_target_blind_panel_b1q_eligibility_v1(
            panel_manifest_path=invalid,
            source_coverage_path=SOURCE_COVERAGE,
        )


def test_malformed_decision_hash_fails_closed() -> None:
    """A decision without a valid semantic hash cannot be accepted."""
    with pytest.raises(ValueError, match="B1Q_PANEL_ELIGIBILITY_SELF_HASH_INVALID"):
        _module().validate_target_blind_panel_b1q_eligibility_v1({})


@pytest.mark.parametrize(
    ("case", "error"),
    [
        ("manifest_hash", "B1Q_PANEL_ELIGIBILITY_MANIFEST_INVALID"),
        ("manifest_policy", "B1Q_PANEL_ELIGIBILITY_MANIFEST_INVALID"),
        ("coverage_hash", "B1Q_PANEL_ELIGIBILITY_SOURCE_COVERAGE_INVALID"),
        ("coverage_components", "B1Q_PANEL_ELIGIBILITY_SOURCE_COVERAGE_INVALID"),
        ("coverage_b1q", "B1Q_PANEL_ELIGIBILITY_SOURCE_COVERAGE_INVALID"),
        ("coverage_target_binding", "B1Q_PANEL_ELIGIBILITY_SOURCE_COVERAGE_INVALID"),
    ],
)
def test_registered_source_contracts_reject_rehashed_policy_drift(
    monkeypatch: pytest.MonkeyPatch, case: str, error: str
) -> None:
    """A valid self-hash cannot authorize a changed target-blind source policy."""
    module = importlib.import_module(MODULE_NAME)
    if case.startswith("manifest"):
        document = _read_object(MANIFEST)
        if case == "manifest_hash":
            document["manifest_sha256"] = "0" * 64
        else:
            document["status"] = "PASS"
            unsigned = {
                key: value for key, value in document.items() if key != "manifest_sha256"
            }
            digest = _canonical_sha256(unsigned)[7:]
            document["manifest_sha256"] = digest
            monkeypatch.setattr(module, "_MANIFEST_SELF_HASH", digest)
        with pytest.raises(ValueError, match=error):
            module._validate_manifest(document)
        return

    document = _read_object(SOURCE_COVERAGE)
    if case == "coverage_hash":
        document["ledger_sha256"] = "0" * 64
    else:
        components = document["components"]
        assert isinstance(components, dict)
        if case == "coverage_components":
            document["components"] = []
        elif case == "coverage_b1q":
            b1q = components["B1Q"]
            assert isinstance(b1q, dict)
            b1q["status"] = "PASS"
        else:
            document["target_binding_permitted"] = True
        unsigned = {key: value for key, value in document.items() if key != "ledger_sha256"}
        digest = _canonical_sha256(unsigned)[7:]
        document["ledger_sha256"] = digest
        monkeypatch.setattr(module, "_SOURCE_COVERAGE_SELF_HASH", digest)
    with pytest.raises(ValueError, match=error):
        module._validate_source_coverage(document)


@pytest.mark.parametrize(
    ("case", "error"),
    [
        ("hash", "B1Q_PANEL_ELIGIBILITY_SELF_HASH_INVALID"),
        ("unsafe", "B1Q_PANEL_ELIGIBILITY_UNSAFE_CONTENT"),
    ],
)
def test_decision_validator_rejects_hash_and_unsafe_content(case: str, error: str) -> None:
    """A decision cannot be altered or made unsafe even when an attacker rehashes it."""
    module = _module()
    decision = module.build_target_blind_panel_b1q_eligibility_v1(
        panel_manifest_path=MANIFEST,
        source_coverage_path=SOURCE_COVERAGE,
    )
    if case == "hash":
        decision["reason_codes"] = []
    else:
        decision["note"] = "owner@example.com"
        decision["semantic_self_hash"] = _canonical_sha256(
            {key: value for key, value in decision.items() if key != "semantic_self_hash"}
        )
    with pytest.raises(ValueError, match=error):
        module.validate_target_blind_panel_b1q_eligibility_v1(decision)


@pytest.mark.parametrize("case", ["non_object", "malformed", "instance"])
def test_schema_validation_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str
) -> None:
    """A malformed schema or schema-invalid decision never degrades to a pass."""
    module = importlib.import_module(MODULE_NAME)
    decision: Mapping[str, object] = module.build_target_blind_panel_b1q_eligibility_v1(
        panel_manifest_path=MANIFEST,
        source_coverage_path=SOURCE_COVERAGE,
    )
    if case == "instance":
        decision = {}
    else:
        schema = tmp_path / "schema.json"
        schema.write_text("[]" if case == "non_object" else "{", encoding="utf-8")
        monkeypatch.setattr(module, "_SCHEMA_PATH", schema)
    with pytest.raises(ValueError, match="B1Q_PANEL_ELIGIBILITY_SCHEMA_INVALID"):
        module._validate_schema(decision)


@pytest.mark.parametrize(
    ("mode", "error"),
    [
        ("race", "B1Q_PANEL_ELIGIBILITY_OUTPUT_CONFLICT"),
        ("io", "B1Q_PANEL_ELIGIBILITY_OUTPUT_UNWRITABLE"),
    ],
)
def test_writer_fails_closed_on_race_or_io_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, mode: str, error: str
) -> None:
    """Atomic creation cannot overwrite a racing writer or hide an I/O failure."""
    module = importlib.import_module(MODULE_NAME)
    output = tmp_path / "eligibility.json"

    def fail_link(source: Path, target: Path) -> None:
        if mode == "race":
            Path(target).write_bytes(b"different")
            raise FileExistsError
        raise OSError("synthetic write failure")

    monkeypatch.setattr(module.os, "link", fail_link)
    with pytest.raises(ValueError, match=error):
        module.write_target_blind_panel_b1q_eligibility_v1(
            panel_manifest_path=MANIFEST,
            source_coverage_path=SOURCE_COVERAGE,
            output_path=output,
        )


def test_validator_dependency_absence_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing jsonschema capability is an explicit startup failure."""
    module = importlib.import_module(MODULE_NAME)
    monkeypatch.setattr(module, "import_module", lambda _name: object())

    with pytest.raises(RuntimeError, match="B1Q_PANEL_ELIGIBILITY_JSONSCHEMA_UNAVAILABLE"):
        module._load_validator()
