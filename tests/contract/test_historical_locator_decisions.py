"""Verify nine scoped historical-location decisions without private originals."""

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECEIPT = ROOT / "artifacts/rp4_public_refresh/historical_locator_decisions_v1.json"
PINS = {
    "artifacts/canonical_validation_v1/full_pytest.stdout.log": (
        "df233b8e8e5995b5555b2200d129ccb422ef03b67a5e869cf8bd894072e208ed",
        "e2999b6156c907fcb794b99cb31290907290a378e930c79fd70116080f0dfec8",
    ),
    "artifacts/independent_replication/evaluation_incidents/20260811_bootstrap_contract.json": (
        "6731a904f19c76f01c64326c0fea3e626d92018a4f1cd80d1376b6393ca9079c",
        "7c39abeb68cc7ed6472893b518eb50961ed0106af5091be7a8ce17f2ea168473",
    ),
    "artifacts/independent_replication/target_acquisition_summary_v1.json": (
        "8141d1da015b81bbcd39779d60c841f993d7f5278d1baceb353eb78851343d21",
        "196deb1f53afd5a0fc44ed79396a9e57668ee52a12e576c96f8d28f32a9b5c51",
    ),
    "artifacts/rp2_block1_partition/partition.json": (
        "f85f13fb1c259922ee9c19c1324cbca9cc8f91036884b5e82cf362ffc87848d6",
        "ccf19de60b1ed9d2baf5276413917376bf5881cb9e6090bae51a0d4ff1e4696a",
    ),
    "artifacts/rp2_validation_market/acquisition.json": (
        "349951c7fe9fbfd50a933913299c5d34284a8fb81098aaa15be1a944405e60d2",
        "c84e97e2797a440f2677a3336106b3438fe54248ed9d69655d99171a1724d9a7",
    ),
    "artifacts/target_blind_v22/target_blind_common_predictor_manifest_v22.json": (
        "b0e31927418b1768024db6f79d7c2492f01b1104e8500d903037745dae8fbfdd",
        "91ee9e6d6b1d54dfcc9f0c1266a6819f1316191bbd721871000ac9ab219ba6e5",
    ),
    "artifacts/target_blind_v23/target_blind_common_predictor_manifest_v23.json": (
        "7a98f835b4e16b2604ddab1c5bb1b89b3b10d22ebc8aab3ce03ef9990b603002",
        "3713606cf3aa4bb77421ff9d2a09be87c6c78171c28d4fa7e661da1b01fbb052",
    ),
    (
        "artifacts/target_blind_v23_committed_20260812/"
        "target_blind_common_predictor_manifest_v23.json"
    ): (
        "c31427328bfd63de311fea3240430b7780385eedc2904daf258f20c0203c31c2",
        "d37c4fcde5a0c045fd3cda1db46c90754b9804672b5c93049e139aed58122d3c",
    ),
    (
        "artifacts/target_blind_v23_sourcebound_20260812/"
        "target_blind_common_predictor_manifest_v23.json"
    ): (
        "3fefae030e81138822a2057b3a5ff7a82d16d234e18340987690b585538c223e",
        "e799fcdd920fe4aa001b383fe1dac2e4c709dab4b3ee330d399b54f00d3ca2d8",
    ),
}


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def pointer_value(document: object, pointer: str) -> object:
    value = document
    for key in pointer.strip("/").split("/"):
        key = key.replace("~1", "/").replace("~0", "~")
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def masked_json(document: object, fields: list[dict[str, object]]) -> bytes:
    masked = copy.deepcopy(document)
    for field in fields:
        keys = str(field["pointer"]).strip("/").split("/")
        value = masked
        for key in keys[:-1]:
            key = key.replace("~1", "/").replace("~0", "~")
            value = value[int(key)] if isinstance(value, list) else value[key]
        key = keys[-1].replace("~1", "/").replace("~0", "~")
        value[int(key) if isinstance(value, list) else key] = "<historical-locator>"
    return json.dumps(masked, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def test_nine_receipt_entries_keep_original_identity_and_other_content() -> None:
    data = json.loads(RECEIPT.read_bytes())
    assert data["schema_version"] == "historical-locator-decisions-v1"
    assert data["source_public_commit"] == "387d9552305bd729e6549b4152d3e37bc9c2ea10"
    assert len(data["entries"]) == 9
    assert {x["path"] for x in data["entries"]} == set(PINS)
    preserved = []
    redacted_values = 0
    for row in data["entries"]:
        original_pin, content_pin = PINS[row["path"]]
        assert row["original_git_blob_sha256"] == original_pin
        assert row["unchanged_content_canonical_sha256"] == content_pin
        content = (ROOT / row["path"]).read_bytes()
        normalized = content.replace(b"\r\n", b"\n")
        assert row["hash_mode"] == "lf_normalized_text"
        assert digest(normalized) == row["public_sha256"]
        if row["format"] == "json":
            document = json.loads(content)
            assert digest(masked_json(document, row["locator_fields"])) == content_pin
            if row["decision"].startswith("PRESERVE"):
                preserved.append(row)
                assert digest(normalized) == original_pin
                assert digest(content) in {row["original_source_checkout_sha256"], original_pin}
                assert row["changed_locator_values"] == 0
            else:
                redacted_values += len(row["locator_fields"])
                assert row["decision"] == "REDACT_LOCATORS_ONLY"
                for field in row["locator_fields"]:
                    value = pointer_value(document, field["pointer"])
                    assert value == field["public_value"]
                    assert str(value).startswith("private-input/")
                    assert digest(str(value).encode()) != field["original_value_sha256"]
        else:
            prefix = row["location_prefix"]["public_value"].encode()
            assert prefix == b"historical-workspace/"
            assert normalized.count(prefix) == row["location_prefix"]["occurrences"] == 4
            assert digest(normalized.replace(prefix, b"<historical-location>/")) == content_pin
    assert len(preserved) == 3 and redacted_values == 8
    assert {x["seal_classification"] for x in preserved} == {
        "VERIFIED_SELF_HASHED_FROZEN_PARTITION",
        "TRANSITIVE_SELF_SEALED_EVIDENCE_PIN_NOT_FROZEN_REGISTRY",
        "VERIFIED_RAW_FILE_HASH_PREREGISTRATION_BINDING",
    }


def test_receipt_and_archive_note_disclose_scope_without_repeating_private_locations() -> None:
    raw = RECEIPT.read_text(encoding="utf-8")
    note = (ROOT / "docs/archive/README.md").read_text(encoding="utf-8")
    assert not re.search(r"[A-Z]:[\\/]", raw + note)
    assert "historical_locator_decisions_v1.json" in note
    for name in PINS:
        assert "../../" + name in note
    assert "distinct LF public Git" in note
    data = json.loads(raw)
    assert data["validation"]["unchanged_content_checks_passed"] == 9
    assert data["validation"]["scientific_values_changed"] is False
    assert data["validation"]["new_frozen_registry_entries"] == 0
    assert data["validation"]["prospective_reads"] == 0
    attrs = (ROOT / "artifacts/canonical_validation_v1/.gitattributes").read_text("utf-8")
    assert "/full_pytest.stdout.log text eol=lf" in attrs.splitlines()
