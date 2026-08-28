"""EXPLORATORY_DIAGNOSTIC: can B2 be extracted better than the frozen linear index?

**Registration, written before any measurement ran.** The owner authorized an
exploratory campaign (2026-08-25) to search for better B2 extractions than the theta
index RP3 froze — with the discipline that makes exploration publishable instead of
significance-hunting:

- **Closed candidate list of five**, fixed here, grounded in the autopsy's committed
  findings (D2: the increment is linear, trees overfit instantly; D3: the benefit
  concentrates ~5.3x in high-flow sessions): C1 flow-regime interaction, C2
  volatility-regime interaction, C3 curvature (index squared), C4 sparse index
  (top-4 |theta| features refit), C5 second orthogonal index.
- **Selection on D, one look at V.** Models fit on the D-role 60% chronological
  training fold; D-test is the selection metric; V (2026-03-24..2026-07-17, after
  every D session) is scored ONCE per candidate, walk-forward, and every result is
  reported with Benjamini-Hochberg q-values across the five V contrasts. No sealed
  session (> 2026-07-17) is touched anywhere.
- **The incumbent is the bar.** Each candidate is contrasted against B0+B1+index
  (what RP3 already tests), not only against B0+B1 — a candidate that does not beat
  the incumbent out of sample is a recorded lead, nothing more.
- **Anchor first.** The campaign re-measures R0 -> R1 with the exact sizing harness
  (same fitter, same calling convention, same seed 650, same universe) and must
  reproduce the committed +0.0010148 on D-test before any candidate is believed.
- **Nothing here is confirmatory.** A surviving candidate's only legitimate future
  is a NEW preregistered program (RP4) with its own frozen artifacts and virgin
  window. The RP3 seal, its closed two-test list, and the look counter are untouched.

Output: `artifacts/rp2_b2_exploratory/results.json` (session-aggregated deltas and
intervals only — aggregates, committable) feeding
`docs/rp2/extension_b2_exploratory_v1.md`.
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
DEFAULT_THETA = ROOT / "artifacts" / "rp3" / "b2_index_theta.json"
DEFAULT_OUTPUT = ROOT / "artifacts" / "rp2_b2_exploratory" / "results.json"

FAMILY = "lightgbm_qlike"  # the frozen RP3 family; the only one the campaign asks
FLOOR = 1e-12
RIDGE_PER_ROW = 1e-3  # identical to theta's recipe: essentially unregularised
CONTRAST_SEED = 650
TRAIN_SHARE = 0.6

#: C1's ex-ante flow state: the autopsy's D3 variable and quantile, unchanged.
FLOW_COLUMN = "b2_5m_premium"
FLOW_QUANTILE = 0.8
#: C2's volatility state: trailing 30-minute realized variance, split at the
#: D-train median.
VOL_COLUMN = "rv_back_30"
#: C4's sparse support: the top-4 |theta| features of the frozen index, fixed here
#: from artifacts/rp3/b2_index_theta.json before any fit ran.
SPARSE_FEATURES = (
    "b2_5m_zero_dte_premium_share",
    "b2_5m_premium",
    "b2_5m_delta_flow",
    "b2_5m_decay_intensity_innovation",
)
#: The registered candidate list. Adding a sixth after seeing results is the exact
#: failure mode this file exists to make impossible.
CANDIDATES = ("c1_flow_regime", "c2_vol_regime", "c3_curvature", "c4_sparse", "c5_second_index")


def _ridge_solve(design: FloatArray, response: FloatArray, penalty: float) -> FloatArray:
    gram = design.T @ design + penalty * np.eye(design.shape[1])
    return np.asarray(np.linalg.solve(gram, design.T @ response), dtype=np.float64)


def _standardised(score: FloatArray, train: BoolArray) -> FloatArray:
    return np.asarray(
        (score - score[train].mean()) / (score[train].std() + 1e-12), dtype=np.float64
    )


def _load_theta(path: Path) -> dict[str, object]:
    """The frozen index artifact, self-hash verified — never refit, never edited."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    recorded = payload.pop("self_sha256")
    if canonical_sha256(payload) != recorded:
        raise RuntimeError("RP2_EXPLORATORY_THETA_HASH_MISMATCH")
    payload["self_sha256"] = recorded
    return dict(payload)


def frozen_index(
    frame: pl.DataFrame, train: BoolArray, theta_payload: dict[str, object]
) -> FloatArray:
    """The sizing convention: the fold's own B2 preprocessor + the committed theta."""

    design_b2, columns, _ = fold_design(frame, list(B2_FEATURES), train, intercept=False)
    expected = theta_payload["b2_design_columns"]
    assert isinstance(expected, list)
    if list(columns) != expected:
        raise RuntimeError("RP2_EXPLORATORY_INDEX_COLUMNS_MISMATCH")
    theta = np.asarray(theta_payload["theta"], dtype=np.float64)
    raw = np.asarray(design_b2 @ theta, dtype=np.float64)
    mean = float(theta_payload["index_train_mean"])  # type: ignore[arg-type]
    std = float(theta_payload["index_train_std"])  # type: ignore[arg-type]
    epsilon = float(theta_payload["standardisation_epsilon"])  # type: ignore[arg-type]
    return np.asarray((raw - mean) / (std + epsilon), dtype=np.float64)


def build_candidates(
    frame: pl.DataFrame,
    target: FloatArray,
    train: BoolArray,
    index: FloatArray,
    design_base: FloatArray,
) -> tuple[dict[str, FloatArray], dict[str, float]]:
    """The five registered extra columns, every statistic learned on train rows only."""

    log_target = np.log(np.maximum(target, FLOOR))
    penalty = RIDGE_PER_ROW * float(train.sum())
    rank = session_rank(frame["session_date"].to_numpy())

    # C1: the D3 lead — does the index deserve extra weight in high-flow sessions?
    flow = np.asarray(frame[FLOW_COLUMN].to_numpy(), dtype=np.float64)
    session_flow = np.full(rank.size, np.nan)
    for label in np.unique(rank):
        members = rank == label
        session_flow[members] = np.nanmean(flow[members])
    flow_threshold = float(np.quantile(session_flow[train], FLOW_QUANTILE))
    c1 = index * (session_flow >= flow_threshold).astype(np.float64)

    # C2: same question for trailing-volatility state.
    vol = np.asarray(frame[VOL_COLUMN].to_numpy(), dtype=np.float64)
    vol_threshold = float(np.nanmedian(vol[train]))
    c2 = index * (vol >= vol_threshold).astype(np.float64)

    # C3: curvature — the cheapest nonlinearity D2 did not already kill.
    c3 = _standardised(index * index, train)

    # C4: a sparse re-fit of the two-stage recipe on the four dominant features.
    beta = _ridge_solve(design_base[train], log_target[train], penalty)
    residual = log_target - design_base @ beta
    design_sparse, _, _ = fold_design(frame, list(SPARSE_FEATURES), train, intercept=False)
    theta4 = _ridge_solve(design_sparse[train], residual[train], penalty)
    c4 = _standardised(np.asarray(design_sparse @ theta4, dtype=np.float64), train)

    # C5: a second index, fit on what remains after the first one has spoken.
    index_column = index.reshape(-1, 1)
    gamma = _ridge_solve(index_column[train], residual[train], penalty)
    residual2 = residual - (index_column @ gamma).ravel()
    design_b2, _, _ = fold_design(frame, list(B2_FEATURES), train, intercept=False)
    theta2 = _ridge_solve(design_b2[train], residual2[train], penalty)
    c5 = _standardised(np.asarray(design_b2 @ theta2, dtype=np.float64), train)

    columns = {
        "c1_flow_regime": c1,
        "c2_vol_regime": c2,
        "c3_curvature": c3,
        "c4_sparse": c4,
        "c5_second_index": c5,
    }
    thresholds = {"flow_threshold": flow_threshold, "vol_threshold": vol_threshold}
    return columns, thresholds


def benjamini_hochberg(p_values: dict[str, float]) -> dict[str, float]:
    """BH q-values across the registered candidates — every result reported."""

    names = sorted(p_values, key=lambda name: p_values[name])
    m = len(names)
    q_values: dict[str, float] = {}
    previous = 1.0
    for i, name in enumerate(reversed(names)):
        k = m - i
        q = min(previous, p_values[name] * m / k)
        q_values[name] = q
        previous = q
    return q_values


def _contrast(
    base_loss: FloatArray,
    cand_loss: FloatArray,
    clusters: npt.NDArray[np.int64],
    digest: str,
    base_label: str,
    cand_label: str,
) -> dict[str, object]:
    record = session_contrast(
        base_loss,
        cand_loss,
        clusters,
        model_family=FAMILY,
        base_information_set=base_label,
        expanded_information_set=cand_label,
        common_mask_sha256=digest,
        seed=CONTRAST_SEED,
    )
    return dict(record.as_record())


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--panel-root", type=Path, default=DEFAULT_PANEL_ROOT)
    parser.add_argument("--theta", type=Path, default=DEFAULT_THETA)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)

    panel = load_merged_panel(
        args.panel_root / "rp2_block4_b0" / "b0_panel.parquet",
        args.panel_root / "rp2_block5_surface" / "b1_surface_panel.parquet",
        args.panel_root / "rp2_block6_flow" / "b2_flow_panel.parquet",
    )
    frame = panel.filter(pl.col("role").is_in(["D", "V"])).sort(
        ["session_date", "asset", "origin_minute"]
    )
    latest = str(frame["session_date"].max())
    if latest > "2026-07-17":
        raise RuntimeError(f"RP2_EXPLORATORY_SEALED_SESSION:{latest}")
    target = np.asarray(frame["rv30"].to_numpy(), dtype=np.float64)
    keep = common_evaluation_mask(frame, target)
    frame = frame.filter(pl.Series(keep))
    target = target[keep]

    rank = session_rank(frame["session_date"].to_numpy())
    role = np.asarray(frame["role"].to_numpy())
    d_mask = role == "D"
    d_sessions = np.unique(rank[d_mask])
    boundary = d_sessions[int(d_sessions.size * TRAIN_SHARE)]
    train = d_mask & (rank < boundary)
    dtest = d_mask & (rank >= boundary)
    vcheck = role == "V"
    print(
        f"rows {target.size:,} | D-train {int(train.sum()):,} | "
        f"D-test {int(dtest.sum()):,} | V {int(vcheck.sum()):,}"
    )

    theta_payload = _load_theta(args.theta)
    base_columns = [column for mapping in (B0_FEATURES, B1_FEATURES) for column in mapping]
    design_base, _, _ = fold_design(frame, base_columns, train)
    index = frozen_index(frame, train, theta_payload)
    candidates, thresholds = build_candidates(frame, target, train, index, design_base)

    fitter = LADDER[FAMILY]
    designs: dict[str, FloatArray] = {
        "r0_base": design_base,
        "r1_incumbent": np.column_stack([design_base, index]),
        "c1_flow_regime": np.column_stack([design_base, index, candidates["c1_flow_regime"]]),
        "c2_vol_regime": np.column_stack([design_base, index, candidates["c2_vol_regime"]]),
        "c3_curvature": np.column_stack([design_base, index, candidates["c3_curvature"]]),
        "c4_sparse": np.column_stack([design_base, candidates["c4_sparse"]]),
        "c5_second_index": np.column_stack([design_base, index, candidates["c5_second_index"]]),
    }
    losses: dict[str, dict[str, FloatArray]] = {}
    for name, design in designs.items():
        forecast = fitter(design, target, train)
        losses[name] = {
            "dtest": qlike_losses(target[dtest], forecast[dtest]),
            "vcheck": qlike_losses(target[vcheck], forecast[vcheck]),
        }
        print(f"  fitted {name} ({design.shape[1]} columns)")

    evaluations: dict[str, dict[str, object]] = {}
    windows = {
        "dtest": (dtest, rank[dtest].astype(np.int64), mask_sha256(dtest)),
        "vcheck": (vcheck, rank[vcheck].astype(np.int64), mask_sha256(vcheck)),
    }
    for window, (_, clusters, digest) in windows.items():
        anchor = _contrast(
            losses["r0_base"][window], losses["r1_incumbent"][window],
            clusters, digest, "B0+B1", "B0+B1+index",
        )
        block: dict[str, object] = {"anchor_r0_to_r1": anchor}
        for name in CANDIDATES:
            block[name] = {
                "vs_base": _contrast(
                    losses["r0_base"][window], losses[name][window],
                    clusters, digest, "B0+B1", f"B0+B1+{name}",
                ),
                "vs_incumbent": _contrast(
                    losses["r1_incumbent"][window], losses[name][window],
                    clusters, digest, "B0+B1+index", f"B0+B1+{name}",
                ),
            }
        evaluations[window] = block

    v_p_values: dict[str, float] = {}
    for name in CANDIDATES:
        entry = evaluations["vcheck"][name]
        assert isinstance(entry, dict)
        inner = entry["vs_incumbent"]
        assert isinstance(inner, dict)
        v_p_values[name] = float(inner["wild_cluster_p_value"])
    q_values = benjamini_hochberg(v_p_values)

    payload: dict[str, object] = {
        "label": "EXPLORATORY_DIAGNOSTIC",
        "campaign": "b2_exploratory_v1",
        "registered_candidates": list(CANDIDATES),
        "family": FAMILY,
        "generated_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "panel_root": args.panel_root.name,
        "theta_self_sha256": theta_payload["self_sha256"],
        "train_share": TRAIN_SHARE,
        "thresholds": thresholds,
        "rows": int(target.size),
        "evaluations": evaluations,
        "v_q_values_vs_incumbent": q_values,
        "contract": (
            "Closed list of five candidates registered before measurement; selection on "
            "D-test, one walk-forward look at V with BH q-values; the incumbent "
            "B0+B1+index is the bar; nothing here is confirmatory — a surviving "
            "candidate's only path is a new preregistered program on virgin data."
        ),
    }
    payload["self_sha256"] = canonical_sha256(payload)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes((json.dumps(payload, indent=1, sort_keys=True) + "\n").encode("utf-8"))
    print(f"\nwrote {args.output}")
    for name in CANDIDATES:
        entry = evaluations["vcheck"][name]
        assert isinstance(entry, dict)
        v = entry["vs_incumbent"]
        assert isinstance(v, dict)
        print(
            f"  {name:<16} V dQLIKE vs incumbent = {v['estimate']:+.5f} "
            f"p={v['wild_cluster_p_value']:.4f} q={q_values[name]:.4f}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
