"""Freeze theta: the linear B2 index the RP3 primary test will read, computed once in D.

RP3's primary contrast (DeltaB2|B1 on RV60, lightgbm_qlike) feeds B2 to the model as ONE
frozen linear index rather than twelve free columns. The exploratory autopsy of the
rp2-v3-20260824-remeasure run showed why: with twelve columns the tree families burn the
information on estimation cost, while the same information compressed to a single ridge
index reproduces the published increment (+0.00101 vs +0.00108) with one degree of freedom.
Freezing theta here — from the D role only, before any Phase B training and long before the
virgin window is read — is what makes the index a hypothesis rather than a fit.

The recipe is EXACTLY the autopsy's, restated in prose inside the artifact so the artifact
answers for itself. Recomputing theta from the same three parquets must reproduce the
committed artifact byte for byte; `tests/unit/test_rp3_b2_index.py` holds both directions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Final

import numpy as np
import polars as pl

from mds650.rp2.panel import (
    B0_FEATURES,
    B1_FEATURES,
    B2_FEATURES,
    chronological_split,
    common_evaluation_mask,
    load_merged_panel,
    mask_sha256,
    session_rank,
)
from mds650.rp2.preprocessing import fold_design

ROOT: Final = Path(__file__).resolve().parents[1]
DEFAULT_PANEL_ROOT: Final = ROOT / "artifacts" / "rp2_v3" / "rp2-v3-20260824-remeasure"
DEFAULT_OUTPUT: Final = ROOT / "artifacts" / "rp3" / "b2_index_theta.json"

#: The autopsy's constants, restated once. The variance floor guards log(rv30) against a
#: zero that the target's positivity mask has already excluded, so it never actually bites;
#: it is kept because the frozen recipe must match the measured one to the letter.
LOG_FLOOR: Final = 1e-12
#: Added to the training standard deviation before dividing, exactly as the autopsy did.
STANDARDISATION_EPSILON: Final = 1e-12
TRAIN_SHARE: Final = 0.6
ROLE: Final = "D"

RECIPE: Final = (
    "Role D of run rp2-v3-20260824-remeasure only. Merge the B0, B1 and B2 panels on the "
    "origin key, filter to role D, sort by (session_date, asset, origin_minute). Keep the "
    "common evaluation mask (finite positive rv30, valid keys, valid availability "
    "columns). Split chronologically by session with train_share=0.6; only the training "
    "rows fit anything. Build X01 = fold_design(B0+B1, intercept) and X2 = fold_design(B2, "
    "no intercept), both imputed and standardised with training statistics of this fold. "
    "With lam = 1e-3 * n_train: beta = ridge of log(max(rv30, 1e-12)) on X01 over the "
    "training rows (closed form, penalty on every column); theta = ridge of the residual "
    "log(max(rv30, 1e-12)) - X01 @ beta on X2 over the training rows, same lam. The index "
    "of a row is X2 @ theta, standardised as (s - train_mean) / (train_std + 1e-12) with "
    "the training mean and std recorded here. Frozen: consumers apply theta and these two "
    "scalars, and never refit."
)


def sha256_file(path: Path) -> str:
    """Content hash of one input parquet, so the artifact names its exact inputs."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(payload: dict[str, object]) -> str:
    """Hash of the canonical JSON serialisation, excluding the self-hash field itself."""

    body = {key: value for key, value in payload.items() if key != "self_sha256"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def freeze_theta(panel_root: Path) -> dict[str, object]:
    """Recompute the autopsy's linear index on the D role and package it for freezing."""

    paths = {
        "b0_panel": panel_root / "rp2_block4_b0" / "b0_panel.parquet",
        "b1_surface_panel": panel_root / "rp2_block5_surface" / "b1_surface_panel.parquet",
        "b2_flow_panel": panel_root / "rp2_block6_flow" / "b2_flow_panel.parquet",
    }
    for label, path in paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"RP3_B2_INDEX_INPUT_MISSING:{label}:{path}")

    panel = load_merged_panel(
        paths["b0_panel"], paths["b1_surface_panel"], paths["b2_flow_panel"]
    )
    frame = panel.filter(pl.col("role") == ROLE).sort(
        ["session_date", "asset", "origin_minute"]
    )
    target = np.asarray(frame["rv30"].to_numpy(), dtype=np.float64)
    keep = common_evaluation_mask(frame, target)
    frame = frame.filter(pl.Series(keep))
    target = target[keep]
    rank = session_rank(frame["session_date"].to_numpy())
    train, test = chronological_split(rank, train_share=TRAIN_SHARE)

    b01 = [c for mapping in (B0_FEATURES, B1_FEATURES) for c in mapping]
    b2 = list(B2_FEATURES)
    x01, _, _ = fold_design(frame, b01, train)
    x2, b2_columns, _ = fold_design(frame, b2, train, intercept=False)
    log_t = np.log(np.maximum(target, LOG_FLOOR))

    lam = 1e-3 * float(train.sum())
    a = x01[train]
    beta = np.linalg.solve(a.T @ a + lam * np.eye(a.shape[1]), a.T @ log_t[train])
    resid = log_t - x01 @ beta

    b = x2[train]
    theta = np.linalg.solve(b.T @ b + lam * np.eye(b.shape[1]), b.T @ resid[train])
    index = x2 @ theta
    train_mean = float(index[train].mean())
    train_std = float(index[train].std())

    run_identity = panel_root / "run_identity.json"
    run_id = panel_root.name
    if run_identity.is_file():
        recorded = json.loads(run_identity.read_text(encoding="utf-8")).get("run_id")
        if isinstance(recorded, str) and recorded:
            run_id = recorded

    payload: dict[str, object] = {
        "schema": "rp3_b2_index_theta/1",
        "recipe": RECIPE,
        "run_id": run_id,
        "role": ROLE,
        "train_share": TRAIN_SHARE,
        "lam": lam,
        "log_floor": LOG_FLOOR,
        "standardisation_epsilon": STANDARDISATION_EPSILON,
        "b2_design_columns": list(b2_columns),
        "theta": [float(value) for value in theta],
        "index_train_mean": train_mean,
        "index_train_std": train_std,
        "rows": int(target.size),
        "train_rows": int(train.sum()),
        "test_rows": int(test.sum()),
        "train_mask_sha256": mask_sha256(train),
        "input_parquet_sha256": {label: sha256_file(path) for label, path in paths.items()},
    }
    payload["self_sha256"] = canonical_sha256(payload)
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Freeze theta: the linear B2 index RP3's primary test will read."
    )
    parser.add_argument(
        "--panel-root",
        type=Path,
        default=DEFAULT_PANEL_ROOT,
        help="Run directory holding rp2_block{4,5,6} panels of the remeasured run.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Where the frozen theta artifact is written.",
    )
    arguments = parser.parse_args()

    payload = freeze_theta(arguments.panel_root)
    output: Path = arguments.output
    output.parent.mkdir(parents=True, exist_ok=True)
    # One serialisation for the bytes on disk, a second (compact) one for the self-hash.
    # Sorted keys and a fixed newline are what make same input -> same byte.
    text = json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    output.write_bytes(text.encode("utf-8"))

    theta = payload["theta"]
    assert isinstance(theta, list)
    print(f"frozen: {output}")
    print(
        f"  run_id={payload['run_id']} rows={payload['rows']} "
        f"train={payload['train_rows']} test={payload['test_rows']}"
    )
    print(
        f"  columns={len(theta)} index_train_mean={payload['index_train_mean']:+.6f} "
        f"index_train_std={payload['index_train_std']:.6f}"
    )
    print(f"  self_sha256={payload['self_sha256']}")


if __name__ == "__main__":
    main()
