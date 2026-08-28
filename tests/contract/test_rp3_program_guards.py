"""Standing guards of the sealed RP3 program: the rules of decision 93, as tests.

The preregistration commits the program to a frozen design, a hard window boundary, and a
one-read look policy. Prose committed the previous programme to things too, and prose was
breached without anyone noticing — so each rule here is held by an assertion that runs in
every checkout, hermetically: everything checked is a committed artifact.

What each guard protects, in the order a reader meets them below: the preregistration's
bytes cannot drift from the hash every citation names; the freeze manifest and both model
files must be exactly what was sealed; the frozen training data must end at the window;
the frozen index inside the manifest must be the committed theta, coefficient by
coefficient; the look counter's only legal pre-read value is zero; and the window refusal
in the prediction path must actually refuse.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Final

import polars as pl
import pytest

from mds650.rp3.frozen_forecasters import (
    TRAINING_WINDOW_END,
    load_frozen,
)

REPO: Final = Path(__file__).resolve().parents[2]
PREREG: Final = REPO / "docs" / "rp3" / "PREREGISTRATION.md"
FROZEN_DIR: Final = REPO / "artifacts" / "rp3" / "frozen"
THETA: Final = REPO / "artifacts" / "rp3" / "b2_index_theta.json"
LOOK_COUNTER: Final = REPO / "artifacts" / "rp3" / "look_counter.json"

#: SHA-256 of the preregistration as git stores it (LF line endings). Computed over the
#: normalised bytes so the pin holds on Windows checkouts (autocrlf) and Linux ones alike.
PREREG_BLOB_SHA256: Final = "66906a88b0d8ff76d9bbc6556e0aa64e32de494254d2ebdccc49140fce7f77e7"


def _sha256_lf(path: Path) -> str:
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _sha256_raw(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_the_preregistration_bytes_match_the_sealed_hash() -> None:
    """Every citation of the seal names this hash; the file must still be that file."""

    assert PREREG.is_file(), f"RP3_PREREG_MISSING:{PREREG}"
    assert _sha256_lf(PREREG) == PREREG_BLOB_SHA256, (
        "docs/rp3/PREREGISTRATION.md no longer hashes to the sealed value. A sealed "
        "preregistration is never edited; a genuinely new program gets a new file and a "
        "new seal."
    )


def test_the_freeze_manifest_and_model_bytes_verify() -> None:
    """The manifest's self-hash and every recorded model hash must hold."""

    frozen = load_frozen(FROZEN_DIR)  # raises on any hash mismatch
    manifest = frozen.manifest
    assert manifest["schema"] == "rp3_freeze/1"
    assert manifest["theta_artifact"] == "artifacts/rp3/b2_index_theta.json"
    theta = json.loads(THETA.read_text(encoding="utf-8"))
    assert manifest["theta_self_sha256"] == theta["self_sha256"]


def test_the_frozen_training_data_ends_at_the_window() -> None:
    manifest = json.loads((FROZEN_DIR / "freeze_manifest.json").read_text(encoding="utf-8"))
    assert manifest["training_window_end"] == TRAINING_WINDOW_END == "2026-07-17"
    latest = manifest["latest_training_session"]
    assert isinstance(latest, str)
    assert latest <= "2026-07-17", f"training reached {latest}, past the window end"


def test_the_manifest_index_is_the_committed_theta() -> None:
    """Coefficient-by-coefficient equality, not just a hash citation."""

    manifest = json.loads((FROZEN_DIR / "freeze_manifest.json").read_text(encoding="utf-8"))
    theta = json.loads(THETA.read_text(encoding="utf-8"))
    index = manifest["index"]
    assert isinstance(index, dict)
    assert index["design_columns"] == theta["b2_design_columns"]
    assert index["theta"] == theta["theta"]
    assert index["train_mean"] == theta["index_train_mean"]
    assert index["train_std"] == theta["index_train_std"]


def test_the_look_counter_is_zero_until_the_read() -> None:
    payload = json.loads(LOOK_COUNTER.read_text(encoding="utf-8"))
    assert payload["confirmatory_reads"] == 0, (
        "the look counter moved. If a confirmatory read legitimately happened, this pin "
        "moves to 1 in the same commit that publishes the read; anything else is a "
        "violated look policy, recorded."
    )


def test_prediction_refuses_the_training_window() -> None:
    """The window boundary is code, not prose: pre-window rows are refused up front."""

    frozen = load_frozen(FROZEN_DIR)
    stale = pl.DataFrame({"session_date": ["2026-07-17"]})
    with pytest.raises(ValueError, match="RP3_EVAL_WINDOW_VIOLATION"):
        frozen.predict(stale)


def test_the_model_files_are_tracked_text_not_gated_parquets() -> None:
    """The frozen models are parameter text files; the evaluation bank is gitignored.

    The bank will hold per-origin forecasts on licensed-derived features, which is exactly
    the class of file the gated tripwire exists for — so the ignore rule is asserted here,
    before the first bank file ever exists.
    """

    for name in ("b1_model.txt", "b1_plus_index_model.txt"):
        path = FROZEN_DIR / name
        assert path.is_file(), f"missing frozen model {name}"
        assert _sha256_raw(path)  # readable, hashable
    gitignore = (REPO / ".gitignore").read_text(encoding="utf-8")
    assert "artifacts/rp3/evaluation_bank/" in gitignore
