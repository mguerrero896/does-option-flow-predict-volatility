"""EXPLORATORY_DIAGNOSTIC v2: a learned index from the RAW tape, against theta.

**Registration, written before any window was extracted or any weight trained.**
Campaign v1 (decision 94) searched recombinations of the twelve hand-crafted B2
aggregates and found none that beat the frozen index; its strongest lead was a second
LINEAR direction. The remaining unexplored axis is the information those twelve
5-minute summaries throw away: the raw full-tape event stream itself (~25 fields per
option trade). This campaign asks exactly one question: **does a small learned
representation of the last 30 minutes of raw events carry rv30 information beyond the
frozen index?** — under the same discipline as v1:

- **Closed candidate list of three**, fixed here: L1 = base + learned index,
  L2 = base + theta + learned index, L3 = base + theta + second-index (v1's c5
  recipe) + learned index. The bar is the incumbent ``B0+B1+theta``; success is
  positive against it on V with BH q <= 0.10 across the three.
- **Capacity minimal, by D2's lesson**: the encoder is ~20k parameters (per-event
  MLP -> masked attention pooling -> tiny head, dropout + weight decay), trained ONLY
  on the D-role 60% chronological training fold, early-stopped on its inner 20% of
  sessions. The output is ONE scalar per origin, standardized on D-train — a learned
  feature, evaluated exactly like every hand-crafted one.
- **The measurement harness stays CPU-deterministic.** GPU training is not
  bit-reproducible; the extracted index array is therefore SAVED with its SHA-256,
  and every contrast (anchor included) runs through the same CPU LightGBM +
  session-clustered inference as v1, seeded. The anchor R0 -> R1 must reproduce the
  committed +0.001015 on D-test before any candidate is believed.
- **One look at V — disclosed as V's second exploratory look** (v1 spent the first).
  All results reported. Nothing here is confirmatory: a surviving candidate's only
  path is a NEW preregistered program on virgin data, with the encoder frozen at
  seal time.
- **Nothing sealed is touched**: the block-1 inventory ends at 2026-07-17 by
  construction; the extractor refuses any later session anyway.

Subcommands: ``extract`` (tape -> per-origin event windows, CPU, hours),
``train`` (encoder on the 5090, minutes), ``evaluate`` (v1 harness verbatim).
Windows and the learned index are licensed-derived granular data: they live under
``MDS650_DATA_ROOT/rp3/exploratory_v2/`` and are never committed; the committed
artifact is aggregates only (`artifacts/rp2_b2_exploratory_v2/results.json`).
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

import numpy as np
import numpy.typing as npt
import polars as pl

from mds650.config import provisional_data_root

type FloatArray = npt.NDArray[np.float64]
type BoolArray = npt.NDArray[np.bool_]

ROOT: Final = Path(__file__).resolve().parents[1]
INVENTORY: Final = ROOT / "artifacts" / "rp2_block1_partition" / "inventory.jsonl"
DEFAULT_PANEL_ROOT: Final = ROOT / "artifacts" / "rp2_v3" / "rp2-v3-20260824-remeasure"
DEFAULT_WORK_ROOT: Final = provisional_data_root() / "rp3" / "exploratory_v2"
DEFAULT_OUTPUT: Final = ROOT / "artifacts" / "rp2_b2_exploratory_v2" / "results.json"

TARGETS: Final = ("AAPL", "AMZN", "META", "MSFT", "NVDA", "TSLA")
WINDOW_MINUTES: Final = 30
MAX_EVENTS: Final = 256
N_FEATURES: Final = 13
TRAIN_SHARE: Final = 0.6
SEED: Final = 20260825
#: The registered candidate list; the bar is the incumbent B0+B1+theta.
CANDIDATES_V2: Final = ("l1_learned_only", "l2_learned_plus_theta", "l3_full_stack")
#: NYSE regular session open, minutes after midnight New York wall time.
OPEN_MINUTE: Final = 570


def _v1() -> Any:
    """The v1 campaign module: frozen_index, candidates, contrasts, BH — reused verbatim."""

    spec = importlib.util.spec_from_file_location(
        "rp2_b2_exploratory_campaign", ROOT / "scripts" / "rp2_b2_exploratory_campaign.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _universe(panel_root: Path) -> tuple[pl.DataFrame, FloatArray, BoolArray, BoolArray, BoolArray]:
    """The exact v1 frame and masks: D+V common-mask rows, D 60/40 split, V check."""

    v1 = _v1()
    from mds650.rp2.panel import common_evaluation_mask, session_rank

    panel = v1.load_merged_panel(
        panel_root / "rp2_block4_b0" / "b0_panel.parquet",
        panel_root / "rp2_block5_surface" / "b1_surface_panel.parquet",
        panel_root / "rp2_block6_flow" / "b2_flow_panel.parquet",
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
    return frame, target, train, dtest, vcheck


def _event_features(events: pl.DataFrame, origin_minute: float) -> FloatArray:
    """One window's [n_events, 13] feature block; robust transforms, NaN -> 0 + flags."""

    n = events.height
    out = np.zeros((n, N_FEATURES), dtype=np.float32)
    size = np.nan_to_num(events["size"].cast(pl.Float64).to_numpy(), nan=0.0)
    premium = np.nan_to_num(events["premium"].cast(pl.Float64).to_numpy(), nan=0.0)
    bid = events["nbbo_bid"].cast(pl.Float64).to_numpy()
    ask = events["nbbo_ask"].cast(pl.Float64).to_numpy()
    price = events["price"].cast(pl.Float64).to_numpy()
    mid = (np.nan_to_num(bid) + np.nan_to_num(ask)) / 2.0
    spread = np.nan_to_num(ask) - np.nan_to_num(bid)
    iv = events["implied_volatility"].cast(pl.Float64).to_numpy()
    dte = events["dte"].to_numpy()
    minute = events["minute_ny"].to_numpy()
    ask_vol = np.nan_to_num(events["ask_vol"].cast(pl.Float64).to_numpy(), nan=0.0)
    bid_vol = np.nan_to_num(events["bid_vol"].cast(pl.Float64).to_numpy(), nan=0.0)
    oi = np.nan_to_num(events["open_interest"].cast(pl.Float64).to_numpy(), nan=0.0)

    out[:, 0] = np.log1p(np.maximum(size, 0.0))
    out[:, 1] = np.log1p(np.maximum(premium, 0.0))
    out[:, 2] = (ask_vol > 0).astype(np.float32)
    out[:, 3] = (bid_vol > 0).astype(np.float32)
    out[:, 4] = (events["option_type"].to_numpy() == "call").astype(np.float32) * 2 - 1
    out[:, 5] = np.log1p(np.maximum(np.nan_to_num(dte, nan=0.0), 0.0))
    out[:, 6] = (np.nan_to_num(dte, nan=99.0) == 0).astype(np.float32)  # zero-DTE flag
    out[:, 7] = np.clip(np.nan_to_num(iv, nan=0.0), 0.0, 5.0)
    out[:, 8] = np.float32(1.0) * np.isnan(iv)
    with np.errstate(divide="ignore", invalid="ignore"):
        rel_spread = np.where(mid > 0, spread / mid, 0.0)
        aggressor = np.where(spread > 0, (np.nan_to_num(price) - mid) / spread, 0.0)
    out[:, 9] = np.clip(np.nan_to_num(rel_spread, nan=0.0, posinf=0.0, neginf=0.0), 0.0, 1.0)
    out[:, 10] = np.clip(np.nan_to_num(aggressor, nan=0.0, posinf=0.0, neginf=0.0), -2.0, 2.0)
    out[:, 11] = np.log1p(np.maximum(oi, 0.0)) / 10.0
    out[:, 12] = np.clip((origin_minute - minute) / WINDOW_MINUTES, 0.0, 1.0)
    return np.asarray(out, dtype=np.float32)


def extract(panel_root: Path, work_root: Path) -> None:
    """Tape -> per-origin windows, one .npz per (asset, session). Idempotent."""

    frame, _, _, _, _ = _universe(panel_root)
    inventory: dict[tuple[str, str], list[str]] = {}
    combined: dict[str, list[str]] = {}
    for line in INVENTORY.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row["asset"] in TARGETS:
            inventory.setdefault((row["asset"], row["session_date"]), []).append(row["path"])
        elif row["asset"] == "__ALL__":
            # The last sessions of the window live as combined all-asset partitions;
            # they carry underlying_symbol and are filtered per asset at read time.
            combined.setdefault(row["session_date"], []).append(row["path"])

    windows_root = work_root / "windows"
    windows_root.mkdir(parents=True, exist_ok=True)
    groups = list(
        frame.group_by(["asset", "session_date"], maintain_order=True)
    )
    done = 0
    for (asset, session_date), group in groups:
        key = (str(asset), str(session_date))
        shard = windows_root / f"{key[0]}_{key[1]}.npz"
        if shard.exists():
            done += 1
            continue
        paths = inventory.get(key)
        if paths:
            events = pl.concat(
                [pl.read_parquet(path) for path in paths], how="vertical_relaxed"
            )
        elif combined.get(key[1]):
            events = pl.concat(
                [pl.read_parquet(path) for path in combined[key[1]]],
                how="vertical_relaxed",
            ).filter(pl.col("underlying_symbol") == key[0])
        else:
            raise RuntimeError(f"RP2_EXPLORATORY_TAPE_MISSING:{key[0]}:{key[1]}")
        events = events.with_columns(
            pl.col("executed_at").dt.convert_time_zone("America/New_York").alias("ts_ny")
        ).with_columns(
            # hour() returns Int8: 15*60 overflows it, so cast BEFORE multiplying —
            # the same trap bars.normalise_bars sidesteps the same way.
            (
                pl.col("ts_ny").dt.hour().cast(pl.Int64) * 60
                + pl.col("ts_ny").dt.minute().cast(pl.Int64)
                - OPEN_MINUTE
            )
            .cast(pl.Float64)
            .alias("minute_ny"),
            (pl.col("expiry").cast(pl.Date) - pl.col("ts_ny").dt.date())
            .dt.total_days()
            .cast(pl.Float64)
            .alias("dte"),
        ).sort("ts_ny")

        origins = group["origin_minute"].to_numpy().astype(np.float64)
        block = np.zeros((origins.size, MAX_EVENTS, N_FEATURES), dtype=np.float16)
        mask = np.zeros((origins.size, MAX_EVENTS), dtype=bool)
        minute_all = events["minute_ny"].to_numpy()
        for i, origin in enumerate(origins):
            in_window = (minute_all >= origin - WINDOW_MINUTES) & (minute_all < origin)
            window = events.filter(pl.Series(in_window)).tail(MAX_EVENTS)
            if window.height:
                features = _event_features(window, float(origin))
                block[i, -window.height :, :] = features.astype(np.float16)
                mask[i, -window.height :] = True
        np.savez_compressed(
            shard, windows=block, mask=mask, origins=origins.astype(np.float64)
        )
        done += 1
        if done % 100 == 0:
            print(f"[extract] {done}/{len(groups)} asset-sessions", flush=True)
    print(f"[extract] complete: {done}/{len(groups)} shards under {windows_root}")


def train(panel_root: Path, work_root: Path) -> None:
    """Fit the small encoder on D-train windows only; write the learned index for ALL rows."""

    from typing import cast

    import torch
    from torch import nn

    torch.manual_seed(SEED)
    np.random.seed(SEED)
    torch.use_deterministic_algorithms(True, warn_only=True)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"[train] device: {device}")

    v1 = _v1()
    frame, target, train_mask, _, _ = _universe(panel_root)
    from mds650.rp2.panel import B0_FEATURES, B1_FEATURES, session_rank
    from mds650.rp2.preprocessing import fold_design

    base_columns = [column for mapping in (B0_FEATURES, B1_FEATURES) for column in mapping]
    design_base, _, _ = fold_design(frame, base_columns, train_mask)
    log_target = np.log(np.maximum(target, v1.FLOOR))
    penalty = v1.RIDGE_PER_ROW * float(train_mask.sum())
    beta = v1._ridge_solve(design_base[train_mask], log_target[train_mask], penalty)
    residual = (log_target - design_base @ beta).astype(np.float32)

    windows_root = work_root / "windows"
    keys = frame.select(["asset", "session_date", "origin_minute"])
    blocks, masks = [], []
    for (asset, session_date), group in frame.group_by(
        ["asset", "session_date"], maintain_order=True
    ):
        shard = np.load(windows_root / f"{asset}_{session_date}.npz")
        assert shard["origins"].shape[0] == group.height, (asset, session_date)
        blocks.append(shard["windows"])
        masks.append(shard["mask"])
    windows = np.concatenate(blocks, axis=0)
    pad_mask = np.concatenate(masks, axis=0)
    del blocks, masks  # the float16 master already costs ~1.2 GiB; keep one copy
    assert windows.shape[0] == frame.height

    rank = session_rank(frame["session_date"].to_numpy())
    train_sessions = np.unique(rank[train_mask])
    inner_boundary = train_sessions[int(train_sessions.size * 0.8)]
    fit_rows = train_mask & (rank < inner_boundary)
    val_rows = train_mask & (rank >= inner_boundary)
    print(f"[train] fit {int(fit_rows.sum()):,} rows | inner-val {int(val_rows.sum()):,}")

    class Encoder(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.event = nn.Sequential(
                nn.Linear(N_FEATURES, 64), nn.GELU(), nn.Dropout(0.1), nn.Linear(64, 64)
            )
            self.query = nn.Parameter(torch.zeros(64))
            self.head = nn.Sequential(nn.Linear(64, 32), nn.GELU(), nn.Linear(32, 1))

        def forward(self, x: torch.Tensor, mask: torch.Tensor) -> torch.Tensor:
            h = self.event(x)
            scores = h @ self.query
            scores = scores.masked_fill(~mask, float("-inf"))
            weights = torch.softmax(scores, dim=1)
            weights = torch.nan_to_num(weights, nan=0.0)  # all-pad windows
            pooled = (weights.unsqueeze(-1) * h).sum(dim=1)
            out: torch.Tensor = self.head(pooled).squeeze(-1)
            return out

    model = Encoder().to(device)
    optimiser = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-3)
    # Master tensor stays float16 (a float32 copy OOMed the host RAM); each batch
    # converts on the GPU, where 512x256x13 float32 is nothing.
    x_all = torch.from_numpy(windows)
    m_all = torch.from_numpy(pad_mask)
    y_all = torch.from_numpy(residual)
    fit_idx = np.flatnonzero(fit_rows)
    val_idx = np.flatnonzero(val_rows)

    def _batches(indices: np.ndarray, shuffle: bool) -> Any:
        order = np.random.permutation(indices) if shuffle else indices
        for start in range(0, order.size, 512):
            chunk = order[start : start + 512]
            yield (
                x_all[chunk].to(device).float(),
                m_all[chunk].to(device),
                y_all[chunk].to(device),
            )

    best_val, best_state, patience = np.inf, None, 0
    for epoch in range(30):
        model.train()
        for x, m, y in _batches(fit_idx, shuffle=True):
            optimiser.zero_grad()
            loss = nn.functional.mse_loss(model(x, m), y)
            cast(Any, loss).backward()  # via Any: CUDA/CPU stubs disagree here
            optimiser.step()
        model.eval()
        with torch.no_grad():
            val_losses = [
                nn.functional.mse_loss(model(x, m), y, reduction="sum").item()
                for x, m, y in _batches(val_idx, shuffle=False)
            ]
        val = sum(val_losses) / val_idx.size
        print(f"[train] epoch {epoch + 1}: inner-val MSE {val:.6f}", flush=True)
        if val < best_val - 1e-6:
            best_val, patience = val, 0
            best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
        else:
            patience += 1
            if patience >= 5:
                break
    assert best_state is not None
    model.load_state_dict(best_state)

    model.eval()
    scores = np.zeros(frame.height, dtype=np.float64)
    with torch.no_grad():
        for start in range(0, frame.height, 1024):
            end = min(start + 1024, frame.height)
            scores[start:end] = (
                model(x_all[start:end].to(device).float(), m_all[start:end].to(device))
                .cpu()
                .numpy()
            )
    learned = (scores - scores[train_mask].mean()) / (scores[train_mask].std() + 1e-12)
    out = keys.with_columns(pl.Series("learned_index", learned))
    index_path = work_root / "learned_index.parquet"
    out.write_parquet(index_path)
    meta = {
        "sha256": _sha256_file(index_path),
        "best_inner_val_mse": float(best_val),
        "seed": SEED,
        "parameters": int(sum(p.numel() for p in model.parameters())),
        "device": str(device),
        "trained_utc": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    (work_root / "learned_index_meta.json").write_text(
        json.dumps(meta, indent=1, sort_keys=True), encoding="utf-8"
    )
    print(f"[train] wrote {index_path} ({meta['parameters']} params, val {best_val:.6f})")


def evaluate(panel_root: Path, work_root: Path, output: Path) -> None:
    """The v1 harness verbatim over the three registered v2 candidates."""

    v1 = _v1()
    from mds650.b1v3_confirmation import canonical_sha256
    from mds650.metrics import qlike_losses
    from mds650.rp2.ladder import LADDER
    from mds650.rp2.panel import B0_FEATURES, B1_FEATURES, mask_sha256, session_rank
    from mds650.rp2.preprocessing import fold_design

    frame, target, train_mask, dtest, vcheck = _universe(panel_root)
    rank = session_rank(frame["session_date"].to_numpy())

    index_path = work_root / "learned_index.parquet"
    learned_frame = pl.read_parquet(index_path)
    joined = frame.select(["asset", "session_date", "origin_minute"]).join(
        learned_frame, on=["asset", "session_date", "origin_minute"], how="left"
    )
    learned = np.asarray(joined["learned_index"].to_numpy(), dtype=np.float64)
    if not np.isfinite(learned).all():
        raise RuntimeError("RP2_EXPLORATORY_V2_INDEX_INCOMPLETE")
    meta = json.loads((work_root / "learned_index_meta.json").read_text(encoding="utf-8"))
    if _sha256_file(index_path) != meta["sha256"]:
        raise RuntimeError("RP2_EXPLORATORY_V2_INDEX_HASH_MISMATCH")

    theta_payload = v1._load_theta(ROOT / "artifacts" / "rp3" / "b2_index_theta.json")
    base_columns = [column for mapping in (B0_FEATURES, B1_FEATURES) for column in mapping]
    design_base, _, _ = fold_design(frame, base_columns, train_mask)
    index = v1.frozen_index(frame, train_mask, theta_payload)
    candidates_v1, _ = v1.build_candidates(frame, target, train_mask, index, design_base)
    index2 = candidates_v1["c5_second_index"]

    fitter = LADDER[v1.FAMILY]
    designs: dict[str, FloatArray] = {
        "r0_base": design_base,
        "r1_incumbent": np.column_stack([design_base, index]),
        "l1_learned_only": np.column_stack([design_base, learned]),
        "l2_learned_plus_theta": np.column_stack([design_base, index, learned]),
        "l3_full_stack": np.column_stack([design_base, index, index2, learned]),
    }
    losses: dict[str, dict[str, FloatArray]] = {}
    for name, design in designs.items():
        forecast = fitter(design, target, train_mask)
        losses[name] = {
            "dtest": qlike_losses(target[dtest], forecast[dtest]),
            "vcheck": qlike_losses(target[vcheck], forecast[vcheck]),
        }
        print(f"  fitted {name} ({design.shape[1]} columns)", flush=True)

    evaluations: dict[str, dict[str, object]] = {}
    windows = {
        "dtest": (rank[dtest].astype(np.int64), mask_sha256(dtest)),
        "vcheck": (rank[vcheck].astype(np.int64), mask_sha256(vcheck)),
    }
    for window, (clusters, digest) in windows.items():
        block: dict[str, object] = {
            "anchor_r0_to_r1": v1._contrast(
                losses["r0_base"][window], losses["r1_incumbent"][window],
                clusters, digest, "B0+B1", "B0+B1+index",
            )
        }
        for name in CANDIDATES_V2:
            block[name] = {
                "vs_base": v1._contrast(
                    losses["r0_base"][window], losses[name][window],
                    clusters, digest, "B0+B1", f"B0+B1+{name}",
                ),
                "vs_incumbent": v1._contrast(
                    losses["r1_incumbent"][window], losses[name][window],
                    clusters, digest, "B0+B1+index", f"B0+B1+{name}",
                ),
            }
        evaluations[window] = block

    v_p_values: dict[str, float] = {}
    for name in CANDIDATES_V2:
        entry = evaluations["vcheck"][name]
        assert isinstance(entry, dict)
        inner = entry["vs_incumbent"]
        assert isinstance(inner, dict)
        v_p_values[name] = float(inner["wild_cluster_p_value"])
    q_values = v1.benjamini_hochberg(v_p_values)

    payload: dict[str, object] = {
        "label": "EXPLORATORY_DIAGNOSTIC",
        "campaign": "b2_exploratory_v2_learned_tape",
        "registered_candidates": list(CANDIDATES_V2),
        "family": v1.FAMILY,
        "generated_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "panel_root": panel_root.name,
        "theta_self_sha256": theta_payload["self_sha256"],
        "learned_index_sha256": meta["sha256"],
        "encoder": {
            "parameters": meta["parameters"],
            "best_inner_val_mse": meta["best_inner_val_mse"],
            "seed": meta["seed"],
            "window_minutes": WINDOW_MINUTES,
            "max_events": MAX_EVENTS,
            "event_features": N_FEATURES,
        },
        "rows": int(target.size),
        "evaluations": evaluations,
        "v_q_values_vs_incumbent": q_values,
        "v_look_disclosure": (
            "This is V's SECOND exploratory look (campaign v1 spent the first); both are "
            "disclosed, both BH-corrected within campaign, and neither is confirmatory."
        ),
        "contract": (
            "Closed list of three candidates registered before extraction or training; "
            "encoder ~20k params trained on D-train only; measurement harness "
            "CPU-deterministic over the saved, hashed index; the incumbent B0+B1+theta "
            "is the bar; a surviving candidate's only path is a new preregistered "
            "program on virgin data with the encoder frozen at seal time."
        ),
    }
    payload["self_sha256"] = canonical_sha256(payload)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes((json.dumps(payload, indent=1, sort_keys=True) + "\n").encode("utf-8"))
    print(f"\nwrote {output}")
    for name in CANDIDATES_V2:
        entry = evaluations["vcheck"][name]
        assert isinstance(entry, dict)
        v = entry["vs_incumbent"]
        assert isinstance(v, dict)
        print(
            f"  {name:<22} V dQLIKE vs incumbent = {v['estimate']:+.5f} "
            f"p={v['wild_cluster_p_value']:.4f} q={q_values[name]:.4f}"
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["extract", "train", "evaluate"])
    parser.add_argument("--panel-root", type=Path, default=DEFAULT_PANEL_ROOT)
    parser.add_argument("--work-root", type=Path, default=DEFAULT_WORK_ROOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    if args.command == "extract":
        extract(args.panel_root, args.work_root)
    elif args.command == "train":
        train(args.panel_root, args.work_root)
    else:
        evaluate(args.panel_root, args.work_root, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
