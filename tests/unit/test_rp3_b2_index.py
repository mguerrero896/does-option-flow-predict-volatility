"""The frozen B2 index answers for itself, and the panels can reproduce it.

Two tiers, on the two failure modes a frozen coefficient vector has.

**The artifact drifts.** RP3's primary test reads theta from the committed artifact; an
edited, truncated or hand-patched file would silently change the hypothesis being tested.
The hermetic half therefore verifies the artifact against its own canonical self-hash and
against the registry's B2 definition, with no data on disk required.

**The artifact stops matching its inputs.** A theta that the declared parquets no longer
reproduce is a coefficient vector with no provenance. The guarded half recomputes the whole
recipe from the panels and compares, element by element, at 1e-12 — through the same
`panel_guard` policy every other panel-reading check uses: present panels verify, absent
panels skip only where CI declared the skip, and fail closed anywhere else.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Final

import pytest
from scripts.rp3_freeze_b2_index import canonical_sha256, freeze_theta
from tests.panel_guard import panel_is_available

from mds650.rp2.panel import B2_FEATURES
from mds650.rp2.preprocessing import MISSING_SUFFIX

REPO: Final = Path(__file__).resolve().parents[2]
ARTIFACT: Final = REPO / "artifacts" / "rp3" / "b2_index_theta.json"
RUN_NAME: Final = "rp2-v3-20260824-remeasure"

#: The three inputs theta was fitted on, relative to a run directory.
PANEL_RELATIVES: Final[tuple[tuple[str, str], ...]] = (
    ("B0", "rp2_block4_b0/b0_panel.parquet"),
    ("B1", "rp2_block5_surface/b1_surface_panel.parquet"),
    ("B2", "rp2_block6_flow/b2_flow_panel.parquet"),
)

#: Every field the freeze writes. A consumer reads the artifact blind, so a missing field
#: is a broken contract even when the values still verify.
REQUIRED_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "schema",
        "recipe",
        "run_id",
        "role",
        "train_share",
        "lam",
        "log_floor",
        "standardisation_epsilon",
        "b2_design_columns",
        "theta",
        "index_train_mean",
        "index_train_std",
        "rows",
        "train_rows",
        "test_rows",
        "train_mask_sha256",
        "input_parquet_sha256",
        "self_sha256",
    }
)


def load_artifact() -> dict[str, object]:
    assert ARTIFACT.is_file(), f"RP3_B2_INDEX_ARTIFACT_MISSING:{ARTIFACT}"
    payload = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_artifact_schema_is_complete() -> None:
    payload = load_artifact()
    missing = REQUIRED_FIELDS - set(payload)
    assert not missing, f"missing fields: {sorted(missing)}"
    assert payload["schema"] == "rp3_b2_index_theta/1"
    assert payload["run_id"] == RUN_NAME
    assert payload["role"] == "D"
    assert payload["train_share"] == 0.6
    hashes = payload["input_parquet_sha256"]
    assert isinstance(hashes, dict)
    assert set(hashes) == {"b0_panel", "b1_surface_panel", "b2_flow_panel"}
    for value in hashes.values():
        assert isinstance(value, str) and len(value) == 64


def test_self_hash_verifies() -> None:
    """The canonical payload, minus the hash field, must hash to the hash field."""

    payload = load_artifact()
    assert payload["self_sha256"] == canonical_sha256(payload)


def test_theta_matches_the_registered_b2_design() -> None:
    """One coefficient per design column: the dozen registered mechanisms first, then only
    the missingness indicators the training fold actually earned.

    The count is not hard-coded at twelve on purpose: `fold_design` appends an indicator
    for every B2 feature that was ever absent in training, the autopsy fitted theta on that
    full design, and freezing fewer coefficients than the design has columns would be a
    different (and unfitted) index.
    """

    payload = load_artifact()
    columns = payload["b2_design_columns"]
    theta = payload["theta"]
    assert isinstance(columns, list) and isinstance(theta, list)
    assert len(theta) == len(columns)
    features = list(B2_FEATURES)
    assert len(features) == 12
    assert columns[: len(features)] == features
    for indicator in columns[len(features) :]:
        assert isinstance(indicator, str) and indicator.endswith(MISSING_SUFFIX)
        assert indicator.removesuffix(MISSING_SUFFIX) in B2_FEATURES
    assert all(isinstance(value, float) for value in theta)
    std = payload["index_train_std"]
    assert isinstance(std, float) and std > 0.0


def resolve_panel_root() -> Path:
    """Where the remeasured run's panels are, on this machine.

    The parquets are licensed-derived and never versioned, so the run directory inside the
    repo usually holds only the small JSON artifacts. ``MDS650_RP3_PANEL_ROOT`` points the
    recompute at a directory that has the panels. Without it, the original run directory,
    the canonical flat artifact root and the sibling ``integracion`` worktree are probed.
    Input hashes still have to match the frozen artifact, so a newer location cannot
    silently substitute different panels. When none holds them, `panel_guard` decides what
    absence means here.
    """

    override = os.environ.get("MDS650_RP3_PANEL_ROOT")
    if override:
        return Path(override)
    default = REPO / "artifacts" / "rp2_v3" / RUN_NAME
    canonical = REPO / "artifacts"
    sibling = REPO.parent / "integracion" / "artifacts" / "rp2_v3" / RUN_NAME
    for candidate in (default, canonical, sibling):
        if all((candidate / relative).is_file() for _, relative in PANEL_RELATIVES):
            return candidate
    return default


def test_recomputed_theta_matches_the_artifact() -> None:
    root = resolve_panel_root()
    for label, relative in PANEL_RELATIVES:
        path = root / relative
        if path.is_file():
            continue
        if root.is_relative_to(REPO):
            assert panel_is_available(label, path)
        else:
            pytest.fail(f"RP3_B2_INDEX_PANEL_ROOT_INCOMPLETE:{label}:{path}")

    payload = load_artifact()
    recomputed = freeze_theta(root)
    assert recomputed["input_parquet_sha256"] == payload["input_parquet_sha256"]
    assert recomputed["b2_design_columns"] == payload["b2_design_columns"]
    assert recomputed["train_mask_sha256"] == payload["train_mask_sha256"]
    frozen = payload["theta"]
    fresh = recomputed["theta"]
    assert isinstance(frozen, list) and isinstance(fresh, list)
    for index, (old, new) in enumerate(zip(frozen, fresh, strict=True)):
        assert abs(old - new) <= 1e-12, f"theta[{index}]: {old} vs {new}"
    for field in ("index_train_mean", "index_train_std", "lam"):
        old_value = payload[field]
        new_value = recomputed[field]
        assert isinstance(old_value, float) and isinstance(new_value, float)
        assert abs(old_value - new_value) <= 1e-12, field
    # Self-hash covers `run_id`; its integrity is checked independently above. This
    # recomputation may read the byte-identical panels from their current canonical root.
