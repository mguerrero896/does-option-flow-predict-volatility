"""Autopsy of the B2 increment: where does the information die on the way to a forecast?

EXPLORATORY_DIAGNOSTIC. Role D only; no sealed cohort is read. The partition, the common
evaluation mask and the 60/40 chronological cut are exactly the ones Block 10 of the
`rp2-v3-20260824-remeasure` run used, so every delta here is comparable with the published
table for that run.

The DML says B2 carries information beyond B0+B1, yet two of the three frozen families
convert none of it into forecast improvement. Three diagnostics interrogate the chain one
link at a time, and each link is designed so that its outcome discards one hypothesis:

D1  ESTIMATION COST. The published panel hands each family twelve B2 columns. Here B2
    enters as ONE linear index: theta is a ridge fit, on training rows only, of the
    residual of log-RV30 given B0+B1 onto the B2 columns, and the final model sees
    [B0+B1, index]. One extra degree of freedom cannot overfit. If this converts where
    twelve columns did not, the killer was estimation cost and the remedy is dimension
    reduction — which is what the RP3 preregistration freezes.

D2  NON-LINEARITY OF THE INDEX. Same construction, but the index is produced by a small
    boosted tree on the same residual. If D2 converts and D1 does not, the information is
    non-linear in B2 and a linear compression throws it away. If D2 is *worse* than D1,
    the extra flexibility overfits instantly and linear compression is the right call.

D3  LOCALISATION. The per-session loss difference of the best candidate is correlated
    with the session's ex-ante flow state (aggregate 5-minute premium). If the benefit
    concentrates in high-flow sessions, the path forward is conditioning on events, not
    averaging over the whole tape.

Output: session-aggregated QLIKE deltas with block-bootstrap intervals, one artifact,
committed. The numbers feed `docs/rp2/extension_b2_autopsy_v1.md` and the RP3
preregistration's choice of a frozen linear index for the primary test.
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import numpy.typing as npt
import polars as pl

from mds650.b1v3_confirmation import canonical_sha256
from mds650.metrics import qlike_losses
from mds650.rp2.inference import session_contrast
from mds650.rp2.ladder import LADDER
from mds650.rp2.panel import (
    B0_FEATURES,
    B1_FEATURES,
    B2_FEATURES,
    DEFAULT_TRAIN_SHARE,
    chronological_split,
    common_evaluation_mask,
    load_merged_panel,
    mask_sha256,
    session_rank,
)
from mds650.rp2.preprocessing import fold_design

type FloatArray = npt.NDArray[np.float64]
type BoolArray = npt.NDArray[np.bool_]

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PANEL_ROOT = ROOT / "artifacts" / "rp2_v3" / "rp2-v3-20260824-remeasure"
DEFAULT_OUTPUT = ROOT / "artifacts" / "rp2_b2_autopsy" / "results.json"

#: The three frozen primary families of the ladder — the ones the published Block 10
#: table reports — so each delta below lands next to a published number.
FAMILIES: tuple[str, ...] = ("gamma_glm", "ridge_log", "lightgbm_qlike")

#: Variance floor before taking logs, identical to the ladder's.
FLOOR = 1e-12
#: Ridge penalty per training row for both the B0+B1 partial-out and the theta fit. The
#: value is small enough to leave the fit essentially unregularised and exists to make the
#: closed-form solve well-posed; the diagnostic's conclusions do not ride on it.
RIDGE_PER_ROW = 1e-3
#: The D2 tree is deliberately small — the point is a low-capacity non-linear index, not a
#: tuned model — and fully pinned so the run is deterministic.
TREE_PARAMS: dict[str, object] = {
    "objective": "regression",
    "num_leaves": 15,
    "learning_rate": 0.05,
    "verbosity": -1,
    "seed": 20260818,
    "deterministic": True,
}
TREE_ROUNDS = 120
#: Bootstrap seed for every session contrast, matching the exploratory run.
CONTRAST_SEED = 650
#: The ex-ante flow state D3 conditions on: total 5-minute option premium, the coarsest
#: "is anything happening in the options market" variable the panel carries.
FLOW_COLUMN = "b2_5m_premium"
#: Top-quintile threshold for the localisation split.
FLOW_QUANTILE = 0.8


def _ridge_solve(design: FloatArray, response: FloatArray, penalty: float) -> FloatArray:
    """Closed-form ridge coefficients; the penalty makes the solve well-posed."""

    gram = design.T @ design + penalty * np.eye(design.shape[1])
    return np.asarray(np.linalg.solve(gram, design.T @ response), dtype=np.float64)


def _standardised(score: FloatArray, train: BoolArray) -> FloatArray:
    """Z-score an index using training statistics only, so test rows leak nothing."""

    return np.asarray(
        (score - score[train].mean()) / (score[train].std() + 1e-12), dtype=np.float64
    )


def build_indices(
    frame: pl.DataFrame, target: FloatArray, train: BoolArray
) -> tuple[dict[str, FloatArray], FloatArray]:
    """Compress the B2 block into the D1 linear and D2 tree indices.

    Both indices are fits of the *residual* of log-RV30 given B0+B1 — estimated on
    training rows only — onto the B2 columns, so each one carries exactly the information
    B2 adds beyond the base set and nothing the base set already had.
    """

    base_columns = [column for mapping in (B0_FEATURES, B1_FEATURES) for column in mapping]
    design_base, _, _ = fold_design(frame, base_columns, train)
    design_b2, _, _ = fold_design(frame, list(B2_FEATURES), train, intercept=False)
    log_target = np.log(np.maximum(target, FLOOR))

    penalty = RIDGE_PER_ROW * float(train.sum())
    beta = _ridge_solve(design_base[train], log_target[train], penalty)
    residual = log_target - design_base @ beta

    theta = _ridge_solve(design_b2[train], residual[train], penalty)
    linear_index = _standardised(np.asarray(design_b2 @ theta, dtype=np.float64), train)

    import lightgbm as lgb

    booster = lgb.train(
        TREE_PARAMS,
        lgb.Dataset(design_b2[train], label=residual[train]),
        num_boost_round=TREE_ROUNDS,
    )
    tree_index = _standardised(
        np.asarray(booster.predict(design_b2), dtype=np.float64), train
    )
    return {"linear_index": linear_index, "tree_index": tree_index}, design_base


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--panel-root",
        type=Path,
        default=DEFAULT_PANEL_ROOT,
        help="run directory holding rp2_block4_b0/, rp2_block5_surface/, rp2_block6_flow/",
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    panel_paths = (
        args.panel_root / "rp2_block4_b0" / "b0_panel.parquet",
        args.panel_root / "rp2_block5_surface" / "b1_surface_panel.parquet",
        args.panel_root / "rp2_block6_flow" / "b2_flow_panel.parquet",
    )
    for path in panel_paths:
        if not path.is_file():
            raise FileNotFoundError(f"RP3_AUTOPSY_PANEL_MISSING: {path}")

    panel = load_merged_panel(*panel_paths)
    frame = panel.filter(pl.col("role") == "D").sort(["session_date", "asset", "origin_minute"])
    target = np.asarray(frame["rv30"].to_numpy(), dtype=np.float64)
    keep = common_evaluation_mask(frame, target)
    frame = frame.filter(pl.Series(keep))
    target = target[keep]

    rank = session_rank(frame["session_date"].to_numpy())
    train, test = chronological_split(rank, train_share=DEFAULT_TRAIN_SHARE)
    clusters = rank[test]
    digest = mask_sha256(test)
    print(
        f"D: {target.size:,} rows | train {int(train.sum()):,} | test {int(test.sum()):,} | "
        f"sessions evaluated {np.unique(clusters).size}"
    )

    indices, design_base = build_indices(frame, target, train)

    families: dict[str, dict[str, dict[str, object]]] = {}
    losses: dict[tuple[str, str], tuple[FloatArray, FloatArray]] = {}
    estimates: dict[tuple[str, str], float] = {}
    for family in FAMILIES:
        fitter = LADDER[family]
        base_loss = qlike_losses(target[test], fitter(design_base, target, train)[test])
        row: dict[str, dict[str, object]] = {}
        for name, index in indices.items():
            expanded = np.column_stack([design_base, index])
            expanded_loss = qlike_losses(target[test], fitter(expanded, target, train)[test])
            contrast = session_contrast(
                base_loss,
                expanded_loss,
                clusters,
                model_family=family,
                base_information_set="B0+B1",
                expanded_information_set=f"B0+B1+{name}",
                common_mask_sha256=digest,
                seed=CONTRAST_SEED,
            )
            row[name] = contrast.as_record()
            losses[(family, name)] = (base_loss, expanded_loss)
            estimates[(family, name)] = contrast.estimate
            print(
                f"  {family:<16} +{name:<13} dQLIKE={contrast.estimate:+.5f} "
                f"[{contrast.ci_low:+.5f},{contrast.ci_high:+.5f}] "
                f"p={contrast.wild_cluster_p_value:.4f}"
            )
        families[family] = row

    # D3 runs on the strongest candidate — the point is to locate a benefit, so it is
    # asked of the one combination that has a benefit to locate.
    best_family, best_index = max(estimates, key=lambda pair: estimates[pair])
    base_loss, expanded_loss = losses[(best_family, best_index)]
    per_row_gain = base_loss - expanded_loss
    flow = np.asarray(frame[FLOW_COLUMN].to_numpy(), dtype=np.float64)[test]
    labels = np.unique(clusters)
    session_gain = np.array([np.nanmean(per_row_gain[clusters == label]) for label in labels])
    session_flow = np.array([np.nanmean(flow[clusters == label]) for label in labels])
    finite = np.isfinite(session_gain) & np.isfinite(session_flow)
    # Spearman rho: Pearson correlation of the two rank vectors.
    rho = float(
        np.corrcoef(
            np.argsort(np.argsort(session_flow[finite])),
            np.argsort(np.argsort(session_gain[finite])),
        )[0, 1]
    )
    threshold = np.quantile(session_flow[finite], FLOW_QUANTILE)
    top_gain = float(session_gain[finite][session_flow[finite] >= threshold].mean())
    remaining_gain = float(session_gain[finite][session_flow[finite] < threshold].mean())
    print(f"\nD3 ({best_family}+{best_index}): spearman rho(flow, gain) = {rho:+.3f}")
    print(
        f"   mean gain in the top flow quintile: {top_gain:+.5f} | "
        f"remainder: {remaining_gain:+.5f}"
    )

    document: dict[str, object] = {
        "label": "EXPLORATORY_DIAGNOSTIC",
        "role": "D",
        "run": args.panel_root.name,
        "question": "where does the B2 information die on the way to a forecast?",
        "rows": int(target.size),
        "train_rows": int(train.sum()),
        "test_rows": int(test.sum()),
        "sessions_evaluated": int(np.unique(clusters).size),
        "common_mask_sha256": digest,
        "index_construction": {
            "ridge_penalty_per_train_row": RIDGE_PER_ROW,
            "tree_params": dict(TREE_PARAMS),
            "tree_rounds": TREE_ROUNDS,
            "contrast_seed": CONTRAST_SEED,
        },
        "families": families,
        "d3_localisation": {
            "model_family": best_family,
            "index": best_index,
            "flow_variable": FLOW_COLUMN,
            "flow_quantile": FLOW_QUANTILE,
            "sessions": int(finite.sum()),
            "spearman_rho": rho,
            "top_flow_quintile_gain": top_gain,
            "remaining_gain": remaining_gain,
        },
    }
    document["autopsy_sha256"] = canonical_sha256(document)
    document["generated_at_utc"] = datetime.now(UTC).isoformat()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(document, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"\nwritten: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
