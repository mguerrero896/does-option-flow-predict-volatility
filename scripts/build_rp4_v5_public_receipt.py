"""Bind the closed Part 34 receipt to the separate public presentation.

Read only its preserved receipt, sidecar and the named public files. No model,
forecast, licensed input, private operational file or prospective store is read.
The default checks the derived LF receipt; --write writes that receipt and its
sidecar. Run after presentation/path projection and before registering the new
public path. This script never edits the frozen-artifact registry.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
from pathlib import Path
from typing import Any

_archive = importlib.import_module("scripts.rp4_archive_sources")
ROOT = Path(__file__).resolve().parents[1]
SOURCE = "artifacts/rp4_v5_part34/receipt.json"
SOURCE_SIDECAR = "artifacts/rp4_v5_part34/receipt.sha256"
SOURCE_SHA256 = "cdbf75390600b8ae72d7303d535de9dc6c4d3dd915fb06c61b64f5e16a550b6c"
SOURCE_SIDECAR_SHA256 = "6e46fa9c24e28dce380f5ad72b60331abd9214e679819c29ee66360f0ad1e56d"
PUBLIC = "artifacts/rp4_v5_part34/public_receipt_v3.json"
PUBLIC_SIDECAR = "artifacts/rp4_v5_part34/public_receipt_v3.sha256"
PRIVATE = "artifacts/rp4_v5_a3_operations/inbox_ledger.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_receipt() -> dict[str, Any]:
    _archive.assert_historical_sha256(SOURCE, SOURCE_SHA256)
    _archive.assert_historical_sha256(SOURCE_SIDECAR, SOURCE_SIDECAR_SHA256)
    original = _archive.original_path(SOURCE)
    sidecar = _archive.original_path(SOURCE_SIDECAR).read_text(encoding="utf-8")
    assert sidecar.split() == [SOURCE_SHA256, "receipt.json"]
    source: dict[str, Any] = json.loads(original.read_bytes())
    assert len(source["hashes"]) == 25
    assert source["status"] == "PASS_PART34_HISTORICAL_AUDIT_AND_NEW_REGISTRATION"
    assert source["prospective_data_reads"] == source["refits"] == 0
    assert source["auditor_p_values_exactly_reproduced"] is False
    assert source["ridge_drift_cause_proven"] is False
    return source


def public_receipt() -> dict[str, Any]:
    source = source_receipt()
    references: list[dict[str, Any]] = []
    for raw, historical_hash in sorted(source["hashes"].items()):
        logical = raw.replace("\\", "/")
        identity = hashlib.sha256(logical.encode("utf-8")).hexdigest()
        # The private ledger is represented by its identity and historical pin.
        # Its content is never consulted, even if a local copy happens to exist.
        entry: dict[str, Any] = {
            "source_identity_sha256": identity,
            "source_path": None if logical == PRIVATE else logical,
            "original_sha256": historical_hash,
            "public_path": None,
            "public_sha256": None,
        }
        if logical == PRIVATE:
            entry.update(
                relation="private_source_not_distributed",
                evidence="Historical provenance pin only; private operational ledger omitted.",
            )
        else:
            path = _archive.public_path(logical)
            assert path.is_relative_to(ROOT), "Public reference leaves the repository"
            if path.is_file():
                public_hash = sha256(path)
                entry.update(
                    public_path=path.relative_to(ROOT).as_posix(),
                    public_sha256=public_hash,
                    relation=(
                        "original_bytes" if public_hash == historical_hash else "public_derivative"
                    ),
                    evidence=(
                        "Public bytes reproduce the original hash."
                        if public_hash == historical_hash
                        else "Public bytes have their own hash; the historical pin authenticates "
                        "the earlier source, not this derivative."
                    ),
                )
            else:
                entry.update(
                    relation="source_not_distributed",
                    evidence="Historical provenance pin only; the earlier file is not distributed.",
                )
        references.append(entry)
    original = _archive.original_path(SOURCE)
    sidecar = _archive.original_path(SOURCE_SIDECAR)
    return {
        "schema_version": "rp4-v5-part34-public-receipt-v3",
        "supersedes_public_presentation": "artifacts/rp4_v5_part34/public_receipt_v2.json",
        "status": "PUBLIC_PRESENTATION_OF_CLOSED_HISTORICAL_RECEIPT",
        "source_status": source["status"],
        "source_created_at_utc": source["created_at_utc"],
        "original_receipt": {
            "logical_path": SOURCE,
            "original_sha256": SOURCE_SHA256,
            "archive_path": original.relative_to(ROOT).as_posix(),
            "distributed_archive_sha256": sha256(original),
            "sidecar_original_sha256": SOURCE_SIDECAR_SHA256,
            "sidecar_archive_path": sidecar.relative_to(ROOT).as_posix(),
            "sidecar_distributed_archive_sha256": sha256(sidecar),
        },
        "source_reference_count": len(references),
        "references": references,
        "historical_audit_scope": {
            key: source[key]
            for key in (
                "prospective_data_reads",
                "refits",
                "canonical_roundtrip_max_abs_error",
                "auditor_p_values_exactly_reproduced",
                "ridge_drift_cause_proven",
            )
        },
        "publication_scope": {
            "v4_headline_replaced": False,
            "part34_is_post_hoc": True,
            "prospective_registration_executed": False,
            "scientific_execution_performed": False,
            "private_inputs_read": False,
            "private_operational_files_read": False,
            "source_registry_modified": False,
            "capital_go": False,
        },
        "hash_scope": (
            "Original hashes retain the closed source identities. Public derivatives carry "
            "separate raw-byte hashes and never inherit original hashes. Missing and private "
            "sources provide historical provenance pins only, not publicly reproduced evidence. "
            "This new receipt and sidecar use LF so raw and registry-normalized hashes agree. "
            "Register only this new public receipt after final projection; preserve every "
            "earlier frozen-artifact entry unchanged."
        ),
    }


def rendered_files() -> dict[str, bytes]:
    payload = (json.dumps(public_receipt(), ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()
    return {
        PUBLIC: payload,
        PUBLIC_SIDECAR: f"{digest}  {Path(PUBLIC).name}\n".encode(),
    }


def write_files(expected: dict[str, bytes]) -> None:
    registry = ROOT / "data/FROZEN_ARTIFACTS.json"
    pins = {
        row["path"]: row["sha256"] for row in json.loads(registry.read_bytes())["entries"]
    }
    for relative, payload in expected.items():
        if relative in pins:
            if hashlib.sha256(payload).hexdigest() != pins[relative]:
                raise ValueError("FROZEN_PUBLIC_RECEIPT_REQUIRES_NEW_VERSION")
            if not (ROOT / relative).is_file() or sha256(ROOT / relative) != pins[relative]:
                raise ValueError("FROZEN_PUBLIC_RECEIPT_CHANGED_ON_DISK")
    for relative, payload in expected.items():
        destination = ROOT / relative
        if not destination.is_file() or destination.read_bytes() != payload:
            destination.write_bytes(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    expected = rendered_files()
    if args.write:
        write_files(expected)
    mismatches = [
        relative
        for relative, payload in expected.items()
        if not (ROOT / relative).is_file() or (ROOT / relative).read_bytes() != payload
    ]
    if mismatches:
        print("Public receipt differs: " + ", ".join(mismatches))
        return 1
    print("PASS: public receipt and sidecar bind all 25 closed historical references.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
