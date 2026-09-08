"""Verify the public RP4 registration chain without invoking frozen executors.

This read-only presentation contract checks metadata custody in a relocated clone.
It does not load a panel, fit a model, authorize an evaluation, or replace load_spec.
The historical executor still requires its original registered execution context.
"""

from __future__ import annotations

import copy
import hashlib
import importlib
import json
import sys
from collections.abc import Callable
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
V1 = "artifacts/rp4_a1/specification.json"
V2 = "artifacts/rp4_v2_a1/specification.json"
V3 = "artifacts/rp4_v3_a1/specification.json"
PARENT = "artifacts/rp4_v3_a1_empty_window/specification.json"
V4 = "artifacts/rp4_v4_a1/specification.json"
PINS = {
    V1: "865865558087108356f4eb6da7f9d431f1c4d32fd330f20ea78eb126ec6462a5",
    V2: "08a749049f56a0d1dda09cef1f280328e7c84d59fc39d57e71c48caee81670a5",
    "artifacts/rp4_v2_a1/freeze.json": (
        "248abbedd5267552272da1a9f7c1d4d3cefd99ef4d3fdd7b4c1b8a2f10ef41d2"
    ),
    V3: "49b625a4dbca7b725a6b38defc25e76109be7b280d711355a55ce97a7443048b",
    "artifacts/rp4_v3_a1/freeze.json": (
        "89083510a18483ab078d63da718412dad1bc26276e008f4d377d153f38d4c38d"
    ),
    PARENT: "930f3ddb6ef6284f1129dda26ed705699a666ade005c6ad363cb67864794e6f5",
    "artifacts/rp4_v3_a1_empty_window/freeze.json": (
        "97e84fccde837b6cf2a45d11920282fb6067db64d4882295adb028547281aad6"
    ),
    V4: "0a45b0a608110e2ca0dcf38accc2a0c2521ebbe9d223eb002e36ec51f78afd04",
    "artifacts/rp4_v4_a1/freeze_manifest.json": (
        "830a87bd9c091d897739cbab2160d49ab32ae08550d5d4e4dd0bc8e8fc32468a"
    ),
    "artifacts/rp4_v2_code/evaluate_v2.py": (
        "2ecf51fe33e6753a89e0ef68590921c7d6776790883d390dd984e82d1e57ad37"
    ),
    "artifacts/rp4_v3_code/evaluate_v3.py": (
        "5411ba65476fb48fd0b835619479dbf29c73b400e99aa0ae05544c47d3c5e025"
    ),
    "artifacts/rp4_v4_code/evaluate_v4.py": (
        "42bab85ef140dc85357d1672838261475c84af797e582782a0c552625e987450"
    ),
    "artifacts/rp4_v3_code/freeze.py": (
        "ac7e80765b4e2b7b3e253a35b67e57feb29b5364d60097a9af57e58f26c663ea"
    ),
    "artifacts/rp4_v3_code/empty_windows.py": (
        "42c5bdc76fe1432a9d0fa2517ac157d4c02237da1ae8e0b331d1c960203564a5"
    ),
    "artifacts/rp4_v4_code/freeze.py": (
        "c114b23f80a35b93db7fec49066f313c9e745baa7312717af70e25d32d8f286b"
    ),
    "docs/rp4/specification_v2.md": (
        "3f360466d5730defbf14e4d16b9904cdf381624f33215d5ff611f55ea0d2e54c"
    ),
    "docs/rp4/decision_130_v2.md": (
        "0b7ca149f8a72ae93bfdf1bea112a56212d0899640a8644d7bdb209f8a0fee98"
    ),
    "docs/rp4/specification_v3.md": (
        "efb9ecf8130b422cb458ae924e85a9482c32c9c10741f7e1d33d21d812be0566"
    ),
    "docs/rp4/decision_131_v3.md": (
        "ce62e6b6aefa6dc5f5d7a46f5ddef7e58d09a1419334f8c8af7da8e51bdcf697"
    ),
    "docs/rp4/v3_addendum_stability_calibration.md": (
        "81a20523b205e014bd2e910272e280e6c412af120037a6fb1c565e263dd7fce5"
    ),
    "docs/rp4/v3_window_empty_addendum.md": (
        "5502cc7dce7917b233e85c360e45f176b6742b6759d3543d1d60841c05df1803"
    ),
    "docs/rp4/decision_132_v3_empty_windows.md": (
        "857cc8290058b0e61b100f9cfa50b42befea5f275f38619d6fa8bd0ebcb79189"
    ),
    "docs/rp4/specification_v4.md": (
        "443a0c2628d80f82b0f1a90a7ce7f7c3a8caac38a505c8d12366c7c1c81d6ee9"
    ),
    "docs/rp4/decision_133_v4.md": (
        "1003da2864d09b94f0a0f86a0a37b823a55447f28cfbe2b91b61a06ed48a3804"
    ),
}


def parent_identity(recorded_path: str, *, redacted_reference: dict[str, str] | None = None) -> str:
    """Check a logical suffix without touching a recorded machine-local path.

    A redacted path requires a separate, already verified provenance receipt.
    A placeholder alone never establishes a parent identity.
    """
    parts = PurePosixPath(recorded_path.replace("\\", "/")).parts
    expected = PurePosixPath(PARENT).parts
    if ".." not in parts and parts[-len(expected) :] == expected:
        return "registered_logical_suffix"
    assert redacted_reference == {"path": PARENT, "original_sha256": PINS[PARENT]}, (
        "RP4_PUBLIC_PARENT_LOGICAL_IDENTITY_DRIFT"
    )
    return "explicit_public_redaction_reference"


def verify_metadata(
    source_resolver: Callable[[str], Path] | None = None,
) -> dict[str, Any]:
    """Check exact metadata pins or explicit public provenance; never scientific data.

    The resolver supports alternate byte sources in corruption fixtures. It cannot
    change the expected hashes or the fixed allowlist of files read by this check.
    """
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    # Dynamic import keeps the scripts namespace's runtime identity while avoiding
    # duplicate mypy discovery of this directory, which is not a Python package.
    archive = importlib.import_module("scripts.rp4_archive_sources")
    resolve = source_resolver or (lambda name: ROOT / name)
    records: dict[str, dict[str, str]] = {}
    metadata: dict[str, dict[str, Any]] = {}
    for name, expected in PINS.items():
        location = resolve(name)
        mode = archive.assert_historical_sha256(location, expected)
        assert mode in {"original_bytes", "public_redaction_provenance"}, (
            "RP4_PUBLIC_METADATA_SOURCE_MUST_BE_DISTRIBUTED"
        )
        source = archive.original_path(location)
        public = archive.public_path(name)
        assert source.is_file() and public.is_file(), f"Missing public metadata: {name}"
        payload = source.read_bytes()
        records[name] = {
            "original_sha256": expected,
            "verification": mode,
            "verified_bytes_sha256": hashlib.sha256(payload).hexdigest(),
        }
        if name.endswith(".json"):
            metadata[name] = json.loads(payload)

    old, v2, v3, parent, v4 = (metadata[name] for name in (V1, V2, V3, PARENT, V4))
    for version, spec, decision in ((2, v2, 130), (3, v3, 131), (4, v4, 133)):
        assert spec["schema_version"] == f"rp4-walkforward-v{version}"
        assert spec["specification_md_sha256"] == PINS[f"docs/rp4/specification_v{version}.md"]
        assert spec["decision_sha256"] == PINS[f"docs/rp4/decision_{decision}_v{version}.md"]
    assert v2["parent_specification_sha256"] == PINS[V1]
    assert v3["parent_specification_sha256"] == PINS[V2]
    assert v3["addendum_sha256"] == PINS["docs/rp4/v3_addendum_stability_calibration.md"]
    for spec_name, freeze_name in (
        (V2, "artifacts/rp4_v2_a1/freeze.json"),
        (V3, "artifacts/rp4_v3_a1/freeze.json"),
        (PARENT, "artifacts/rp4_v3_a1_empty_window/freeze.json"),
        (V4, "artifacts/rp4_v4_a1/freeze_manifest.json"),
    ):
        assert metadata[freeze_name]["specification_sha256"] == PINS[spec_name]

    frozen = metadata["artifacts/rp4_v3_a1_empty_window/freeze.json"]
    rule = parent["empty_window_addendum"]
    assert frozen["original_v3_specification_sha256"] == PINS[V3]
    assert frozen["original_v3_freeze_sha256"] == PINS["artifacts/rp4_v3_a1/freeze.json"]
    assert frozen["producer_sha256"] == PINS["artifacts/rp4_v3_code/empty_windows.py"]
    assert frozen["addendum"] == rule
    assert rule["md_sha256"] == PINS["docs/rp4/v3_window_empty_addendum.md"]
    assert rule["decision_sha256"] == PINS["docs/rp4/decision_132_v3_empty_windows.md"]
    assert parent["original_v3_specification_sha256"] == PINS[V3]
    assert parent["schema_version"] == "rp4-walkforward-v3"
    assert v4["parent_specification"]["sha256"] == PINS[PARENT]

    reference = None
    if records[V4]["verification"] == "public_redaction_provenance":
        entry = archive._redactions()[V4]
        reference = entry.get("logical_references", {}).get("parent_specification")
    identity = parent_identity(v4["parent_specification"]["path"], redacted_reference=reference)
    for key in ("windows", "assets", "purge_minutes", "embargo_minutes", "source_cutoff_seconds"):
        assert old[key] == v2[key] == v3[key] == parent[key] == v4[key], key
    for key in (
        "feature_sets",
        "feature_transforms",
        "mandatory_predictors",
        "missing_allowed",
        "secondary",
    ):
        assert v4[key] == parent[key], key
    model = copy.deepcopy(parent["model"])
    model.pop("mz_secondary")
    model["lightgbm"]["initial_score"] = "log_training_mean_selected_target"
    model["ridge"]["forecast_bounds_reference"] = (
        "positive_training_selected_target_linear_quantiles"
    )
    assert v4["model"] == model and v4["endpoint_scope"] == ["mean"]
    widths = {name: len(v4["feature_sets"][name]) for name in ("B0", "B1", "B2")}
    assert widths == {"B0": 29, "B1": 69, "B2": 138}
    assert set(v4["horizons"]) == {"5", "15"}
    for horizon, rule in v4["horizons"].items():
        assert rule["target_key"] == f"rv_{horizon}"
        assert rule["target_end_key"] == f"target_end_{horizon}_utc"
    return {
        "schema_version": "rp4-public-metadata-verification-v1",
        "status": "PASS_PUBLIC_METADATA",
        "files": records,
        "parent_logical_path": PARENT,
        "parent_identity_verification": identity,
        "feature_widths": widths,
        "frozen_executor_portability": "OPEN_REQUIRES_ORIGINAL_REGISTERED_CONTEXT",
        "scientific_evaluation_executed": False,
        "licensed_or_sealed_payloads_read": 0,
        "external_panel_custody_verified": False,
        "capital_go": False,
    }


def main() -> None:
    print(json.dumps(verify_metadata(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
