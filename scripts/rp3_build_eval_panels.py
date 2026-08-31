"""Build one RP3 evaluation batch's panels — the adapter the runbook declared open.

The v3 runner validates its sessions against the frozen D/V partition, which by design
excludes every post-window date, so it can never build panels for the sessions RP3 needs
to score. This driver runs the same four block builders over an RP3 batch instead,
without touching anything the sealed programme depends on:

- Blocks 3 and 4 are driven **by import**: their pure functions (`normalise_bars`,
  `build_panel`, `build_b0_panel`, `build_market_controls`) run over the batch's own bar
  stores (`mds650.rp3.eval_inventory.EVAL_BAR_SOURCES`), so `BAR_SOURCES` — the frozen
  registry every RP2 input manifest names — is never edited.
- Blocks 5 and 6 are driven **as subprocesses** through their ``--inventory`` flag,
  pointed at the batch's own tape inventory. Their defaults are untouched; a frozen-run
  replay behaves byte-for-byte as before.

Every session is window-checked at discovery (`RP3_EVAL_WINDOW_VIOLATION` on anything at
or before 2026-07-17), the outputs land under one batch directory that is gitignored
(licensed-derived granular rows, same regime as the fifteen gated files), and
``--dry-run`` validates the whole wiring — stores present, sessions in window, builders
reachable — without reading a data page, which is how this script is tested in CI.

    uv run python scripts/rp3_build_eval_panels.py \
        --data-root <DATA_ROOT> --batch-id rp3-batch-YYYYMMDD [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Final

import polars as pl

from mds650.config import provisional_data_root
from mds650.rp2.bars import normalise_bars
from mds650.rp2.panel import TARGET_ASSETS
from mds650.rp3.eval_inventory import (
    EVAL_BAR_SOURCES,
    EVAL_ROLE,
    discover_tape_sessions,
    write_eval_inventory,
)

ROOT: Final = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_ROOT: Final = ROOT / "artifacts" / "rp3" / "eval_panels"
#: The tape of an RP3 batch lives under the data root at this relative directory,
#: ``date=``-partitioned exactly like the five RP2 tape stores.
TAPE_RELATIVE: Final = "rp3/tape/full_tape_eval"
#: The panels carry the six frozen target assets (``mds650.rp2.panel.TARGET_ASSETS``,
#: imported rather than restated so this driver can never drift from what the frozen
#: forecasters were trained on) plus the two market controls B0 needs.
MARKET_ASSETS: Final = ("SPY", "QQQ")


def _load_block(name: str):  # type: ignore[no-untyped-def]  # a script module has no stub
    """Import one block builder script as a module, the way the test suite does."""

    import importlib.util

    path = ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def join_market_controls(b0_panel: pl.DataFrame, controls: pl.DataFrame) -> pl.DataFrame:
    """Exactly block 4's own join (`rp2_block4_b0_panel.py`): keyed on the origin key,
    skipped when the batch carries no market assets. This function exists because the
    inline version briefly joined on a nonexistent ``minute`` column — a bug only a
    real (non-dry-run) build would have hit, on 2026-08-30, at the worst moment.
    `tests/unit/test_rp3_eval_inventory.py` pins the key and the skip."""

    if not controls.height:
        return b0_panel
    return b0_panel.join(controls, on=["session_date", "origin_minute"], how="left")


def _load_eval_bars(data_root: Path) -> pl.DataFrame:
    """Concatenate the batch's bar stores with the RP3 role, in block 3's own shape."""

    frames: list[pl.DataFrame] = []
    for name, role, relative in EVAL_BAR_SOURCES:
        path = data_root / relative
        if not path.is_file():
            raise FileNotFoundError(f"RP3_EVAL_BAR_STORE_MISSING:{name}:{path}")
        normalised = normalise_bars(pl.read_parquet(path))
        frames.append(normalised.with_columns(source=pl.lit(name), role=pl.lit(role)))
    bars = pl.concat(frames, how="vertical")
    stale = bars.filter(pl.col("session_date") <= date(2026, 7, 17))
    if stale.height:
        earliest = str(stale["session_date"].min())
        raise ValueError(f"RP3_EVAL_WINDOW_VIOLATION:{earliest}")
    return bars


def build_batch(data_root: Path, batch_dir: Path, *, workers: int) -> dict[str, object]:
    """Blocks 3 → 4 → 5 → 6 over one batch; returns the batch summary."""

    tape_sessions = discover_tape_sessions(data_root / TAPE_RELATIVE)
    inventory_path = batch_dir / "eval_inventory.jsonl"
    inventory_rows = write_eval_inventory(
        tape_sessions, list(TARGET_ASSETS), inventory_path
    )

    bars = _load_eval_bars(data_root)
    block3 = _load_block("rp2_block3_target_panel")
    block4 = _load_block("rp2_block4_b0_panel")

    target_dir = batch_dir / "rp2_block3_target"
    target_dir.mkdir(parents=True, exist_ok=True)
    target_panel, target_counters = block3.build_panel(bars, max_fill_share=0.05)  # noqa: SLF001
    target_panel.write_parquet(target_dir / "target_panel.parquet")

    b0_dir = batch_dir / "rp2_block4_b0"
    b0_dir.mkdir(parents=True, exist_ok=True)
    b0_panel, b0_counters = block4.build_b0_panel(bars, max_fill_share=0.05)  # noqa: SLF001
    controls = block4.build_market_controls(bars)  # noqa: SLF001
    b0_panel = join_market_controls(b0_panel, controls)
    b0_panel.write_parquet(b0_dir / "b0_panel.parquet")

    for script, out_name in (
        ("rp2_block5_surface_panel", "rp2_block5_surface"),
        ("rp2_block6_flow_panel", "rp2_block6_flow"),
    ):
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "scripts" / f"{script}.py"),
                "--data-root",
                str(data_root),
                "--output-dir",
                str(batch_dir / out_name),
                "--panel-root",
                str(batch_dir),
                "--inventory",
                str(inventory_path),
                "--workers",
                str(workers),
            ],
            cwd=ROOT,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"RP3_EVAL_BLOCK_FAILED:{script}:{completed.returncode}")

    summary = {
        "schema": "rp3_eval_batch/1",
        "built_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "role": EVAL_ROLE,
        "sessions": sorted(tape_sessions),
        "inventory_rows": inventory_rows,
        "target_counters": target_counters,
        "b0_counters": b0_counters,
    }
    (batch_dir / "batch_summary.json").write_bytes(
        (json.dumps(summary, sort_keys=True, indent=2) + "\n").encode("utf-8")
    )
    return summary


def dry_run(data_root: Path) -> dict[str, object]:
    """Validate the wiring without reading a data page: what would build, from what."""

    tape_root = data_root / TAPE_RELATIVE
    plan: dict[str, object] = {"tape_root": str(tape_root)}
    tape_sessions = discover_tape_sessions(tape_root)
    plan["sessions"] = sorted(tape_sessions)
    plan["tape_files"] = sum(len(files) for files in tape_sessions.values())
    stores = {}
    for name, _, relative in EVAL_BAR_SOURCES:
        path = data_root / relative
        stores[name] = {"path": str(path), "present": path.is_file()}
    plan["bar_stores"] = stores
    for script in ("rp2_block5_surface_panel", "rp2_block6_flow_panel"):
        assert (ROOT / "scripts" / f"{script}.py").is_file(), script
    plan["builders"] = "reachable"
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=provisional_data_root())
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--batch-id", type=str, required=True)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--dry-run", action="store_true")
    arguments = parser.parse_args()

    if arguments.dry_run:
        plan = dry_run(arguments.data_root)
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 0

    batch_dir = arguments.output_root / arguments.batch_id
    if batch_dir.exists():
        raise SystemExit(f"RP3_EVAL_BATCH_EXISTS:{batch_dir}")
    summary = build_batch(arguments.data_root, batch_dir, workers=arguments.workers)
    print(f"batch {arguments.batch_id}: {len(summary['sessions'])} sessions built")  # type: ignore[arg-type]
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
