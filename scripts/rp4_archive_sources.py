"""Resolve historical citations to preserved bytes and readable archive documents."""

import hashlib
import json
import re
from functools import lru_cache
from pathlib import Path
from typing import Literal

ROOT = Path(__file__).resolve().parents[1]


@lru_cache
def _withheld_sources() -> dict[str, dict[str, str]]:
    receipt = ROOT / "artifacts/rp4_public_refresh/archive_redactions.json"
    if not receipt.is_file():
        return {}
    data = json.loads(receipt.read_text("utf-8"))
    assert data["schema_version"] == "public-archive-redactions-v1"
    entries = data.get("withheld_sources", [])
    result = {}
    for entry in entries:
        assert set(entry) == {"logical_path_sha256", "original_sha256", "reason"}
        for field in ("logical_path_sha256", "original_sha256"):
            assert re.fullmatch(r"[0-9a-f]{64}", entry[field]), "Invalid withheld-source pin"
        assert entry["reason"], "Withheld source requires an explicit reason"
        key = entry["logical_path_sha256"]
        assert key not in result, "Duplicate withheld-source identity"
        result[key] = entry
    return result


@lru_cache
def _redactions() -> dict[str, dict[str, object]]:
    receipt = ROOT / "artifacts/rp4_public_refresh/archive_redactions.json"
    if not receipt.is_file():
        return {}
    data = json.loads(receipt.read_text("utf-8"))
    assert data["schema_version"] == "public-archive-redactions-v1"
    entries = data["entries"]
    result = {entry["logical_path"]: entry for entry in entries}
    assert len(result) == len(entries), "Duplicate public redaction identity"
    return result


@lru_cache
def _paths() -> dict[str, dict[str, str]]:
    result = {
        "README.md": {
            "archive_path": "docs/archive/public_refresh_baseline/README.md.original",
            "public_path": "README.md",
        },
        "docs/rp4/results_v3.md": {
            "archive_path": "docs/archive/rp4/results_v3_original/results_v3.md.original"
        },
        "artifacts/rp4_v3_code/report_v3.py": {
            "archive_path": "docs/archive/rp4/results_v3_original/report_v3.py.original"
        },
    }
    for relative in (
        "docs/archive/public_refresh_baseline/original_paths.json",
        "docs/archive/rp4/presentation_originals/original_paths.json",
        "docs/archive/rp4/DEFENSE_PACKAGE/original_paths.json",
        "docs/archive/rp4/DEFENSE_PACKAGE/revision_2/correction_7/original_paths.json",
        "docs/archive/public_history/original_paths.json",
        "docs/archive/rp4/figure_originals/original_paths.json",
    ):
        path = ROOT / relative
        if path.is_file():
            result.update(json.loads(path.read_text("utf-8")))
    result = {name: {**entry, "logical_path": name} for name, entry in result.items()}
    aliases = {}
    for entry in result.values():
        for field in ("archive_path", "public_path"):
            if field in entry:
                aliases[entry[field]] = entry
    for name, redaction in _redactions().items():
        if name in result:
            aliases[str(redaction["public_path"])] = result[name]
    return result | aliases


def original_path(value: str | Path) -> Path:
    path = (ROOT / value).resolve()
    if not path.is_relative_to(ROOT):
        return path  # Temporary mutation fixtures retain their own changed bytes.
    entry = _paths().get(path.relative_to(ROOT).as_posix())
    if entry:
        path = (ROOT / entry["archive_path"]).resolve()
        assert path.is_relative_to(ROOT), "Historical source leaves the repository"
        if not path.is_file():
            redaction = _redactions().get(entry["logical_path"])
            if redaction:
                path = (ROOT / str(redaction["public_path"])).resolve()
                assert path.is_relative_to(ROOT), "Public redaction leaves the repository"
    return path


def public_path(value: str | Path) -> Path:
    path = (ROOT / value).resolve()
    if not path.is_relative_to(ROOT):
        return path
    entry = _paths().get(path.relative_to(ROOT).as_posix())
    if entry:
        target = entry.get("public_path")
        if target is None and not path.is_file():
            target = entry["archive_path"]
        if target is not None:
            path = (ROOT / target).resolve()
        assert path.is_relative_to(ROOT), "Public link leaves the repository"
        if not path.exists():
            redaction = _redactions().get(entry["logical_path"])
            if redaction:
                path = (ROOT / str(redaction["public_path"])).resolve()
                assert path.is_relative_to(ROOT), "Public redaction leaves the repository"
    return path


def logical_path(value: str | Path) -> Path:
    """Retain original manifest identities even when a caller starts in the archive."""
    path = (ROOT / value).resolve()
    if not path.is_relative_to(ROOT):
        return path
    entry = _paths().get(path.relative_to(ROOT).as_posix())
    if entry:
        return ROOT / entry["logical_path"]
    archive = ROOT / "docs/archive/rp4/DEFENSE_PACKAGE"
    if path.is_relative_to(archive):
        return ROOT / "docs/rp4/DEFENSE_PACKAGE" / path.relative_to(archive)
    return path


def frozen_public_baseline_path(value: str | Path, expected: str) -> Path:
    """Resolve only a byte-exact archived PUBLIC baseline with this precise pin.

    This verification-only route does not use original-source redactions or
    non-distribution receipts. Every other frozen identity remains physical.
    """
    path = (ROOT / value).resolve()
    if not path.is_relative_to(ROOT) or path.suffix != ".md":
        return path
    entry = _paths().get(path.relative_to(ROOT).as_posix())
    if entry is None or entry.get("public_baseline_sha256") != expected:
        return path
    name = entry.get("public_baseline_path")
    if not name:
        raise ValueError("FROZEN_PUBLIC_BASELINE_MAPPING_INCOMPLETE")
    baseline = (ROOT / name).resolve()
    if not baseline.is_relative_to(ROOT / "docs/archive"):
        raise ValueError("FROZEN_PUBLIC_BASELINE_PATH_UNSAFE")
    if not baseline.is_file():
        raise ValueError("FROZEN_PUBLIC_BASELINE_MISSING")
    if hashlib.sha256(baseline.read_bytes()).hexdigest() != expected:
        raise ValueError("FROZEN_PUBLIC_BASELINE_MUTATED")
    return baseline


def assert_historical_sha256(
    value: str | Path, expected: str
) -> Literal["original_bytes", "public_redaction_provenance", "private_source_not_distributed"]:
    """Verify exact bytes or explicitly limited, receipt-bound public provenance.

    A public redaction is never assigned the original content hash. Its own bytes
    must match the public hash, and the receipt must retain the expected original
    pin. Numeric/selector contracts still run independently on the readable data.
    Explicitly withheld source metadata verifies only a historical provenance pin
    and present absence. It supplies no file, executable code or numerical value.
    """
    source = original_path(value)
    logical = logical_path(value)
    if logical.is_relative_to(ROOT):
        identity = logical.relative_to(ROOT).as_posix()
        withheld = _withheld_sources().get(hashlib.sha256(identity.encode("utf-8")).hexdigest())
        if withheld is not None:
            assert identity not in _redactions(), "Source cannot be both redacted and withheld"
            assert withheld["original_sha256"] == expected, "Incompatible withheld-source pin"
            assert not source.exists() and not logical.exists(), (
                "A source recorded as not distributed is present"
            )
            return "private_source_not_distributed"
    record = (
        _redactions().get(logical.relative_to(ROOT).as_posix())
        if logical.is_relative_to(ROOT)
        else None
    )
    if record is not None:
        assert record["original_sha256"] == expected, "Incompatible original provenance pin"
        assert record["numeric_invariant"] is True, "Numeric invariance is not recorded"
        assert isinstance(record["rule"], str) and record["rule"], "Missing redaction rule"
        public = (ROOT / str(record["public_path"])).resolve()
        assert public.is_relative_to(ROOT) and public.is_file(), "Missing public redaction"
        assert hashlib.sha256(public.read_bytes()).hexdigest() == record["public_sha256"], (
            "Public redaction bytes changed"
        )
    assert source.is_file(), f"Unregistered missing historical source: {logical}"
    actual = hashlib.sha256(source.read_bytes()).hexdigest()
    if actual == expected:
        return "original_bytes"
    assert record is not None, f"Historical source bytes changed: {logical}"
    assert source == public, "Changed original bytes cannot be replaced by a provenance assertion"
    assert actual == record["public_sha256"], "Public source bytes do not match the receipt"
    return "public_redaction_provenance"
