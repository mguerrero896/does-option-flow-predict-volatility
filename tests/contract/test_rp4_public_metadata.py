"""A clone-safe documentary check, separate from registered executor acceptance."""

from pathlib import Path

import pytest
from scripts import verify_rp4_public_metadata as verifier
from scripts.rp4_archive_sources import original_path


def test_public_metadata_chain_in_a_clone_preserves_pins_and_rejects_drift(tmp_path: Path) -> None:
    result = verifier.verify_metadata()
    assert result["status"] == "PASS_PUBLIC_METADATA"
    assert result["parent_logical_path"] == verifier.PARENT
    assert result["feature_widths"] == {"B0": 29, "B1": 69, "B2": 138}
    assert result["frozen_executor_portability"] == "OPEN_REQUIRES_ORIGINAL_REGISTERED_CONTEXT"
    assert result["licensed_or_sealed_payloads_read"] == 0
    assert result["scientific_evaluation_executed"] is False
    assert set(result["files"]) == set(verifier.PINS)

    # Both exact JSON metadata and archived documentary bytes must reject drift.
    for name in (verifier.V4, "docs/rp4/specification_v4.md"):
        corrupt = tmp_path / Path(name).name
        corrupt.write_bytes(original_path(name).read_bytes() + b"\nCORRUPTED\n")

        def changed_source(
            logical: str, changed_name: str = name, changed_bytes: Path = corrupt
        ) -> Path:
            return changed_bytes if logical == changed_name else verifier.ROOT / logical

        with pytest.raises(AssertionError, match="Historical source bytes changed"):
            verifier.verify_metadata(changed_source)

    assert (
        verifier.parent_identity("relocated/clone/" + verifier.PARENT)
        == "registered_logical_suffix"
    )
    for wrong in ("[private path]", "other/specification.json", "../" + verifier.PARENT):
        with pytest.raises(AssertionError, match="PARENT_LOGICAL_IDENTITY_DRIFT"):
            verifier.parent_identity(wrong)
    reference = {"path": verifier.PARENT, "original_sha256": verifier.PINS[verifier.PARENT]}
    assert verifier.parent_identity("[private path]", redacted_reference=reference) == (
        "explicit_public_redaction_reference"
    )
    with pytest.raises(AssertionError, match="PARENT_LOGICAL_IDENTITY_DRIFT"):
        verifier.parent_identity(
            "[private path]", redacted_reference={**reference, "original_sha256": "0" * 64}
        )
