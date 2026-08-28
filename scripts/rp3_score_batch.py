"""Score one RP3 evaluation batch into the bank — rows in, nothing aggregated out.

This is step 3 of the RP3 runbook's operating cycle, and the last piece of engineering
the sealed program needed. It takes one built batch (`rp3_build_eval_panels.py`
output), reproduces the exact RP2 merge (`mds650.rp2.panel.load_merged_panel` — the
same function the freeze itself used), keeps only the preregistered evaluation
universe (`common_evaluation_mask`, the block-10 common mask: H1 scored anywhere else
"would be a different experiment wearing the same name"), scores every origin with the
frozen forecasters (`load_frozen(...).predict` — hash-verified models, index computed
internally, `RP3_EVAL_WINDOW_VIOLATION` on any pre-window row), computes
`signed_return_120` from the batch's own bars with the ext1 recipe that defined it
(equivalence pinned by test against `rp2_ext1_mechanism_utility.build_target_battery`),
and appends one row per origin to the evaluation bank:

    session_date, asset, origin_minute, index, b1, b1_plus_index, rv30,
    signed_return_120, batch_id

**What this script never does, by construction and by tripwire:** it computes no
QLIKE, no contrast, no mean of anything, no hit rate — nothing that compares a
forecast to a realization or to another forecast. The look counter must read 0 before
it will bank a single row, and it prints only operational facts: row counts, session
counts, hashes. The bank is gitignored (licensed-derived granular rows); duplicated
origins are refused, not deduplicated silently — a duplicate would inflate the
session count that triggers the single read at N = 662.

    uv run python scripts/rp3_score_batch.py --batch-id rp3-batch-YYYYMMDD
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Final

import numpy as np
import polars as pl

from mds650.config import provisional_data_root
from mds650.exchange_clock import ny_today
from mds650.rp2.bars import build_session_grid, normalise_bars
from mds650.rp2.panel import (
    JOIN_KEYS,
    common_evaluation_mask,
    load_merged_panel,
    mask_sha256,
)
from mds650.rp2.realized import log_returns
from mds650.rp3.eval_inventory import EVAL_BAR_SOURCES, assert_eval_session
from mds650.rp3.frozen_forecasters import load_frozen

ROOT: Final = Path(__file__).resolve().parents[1]
DEFAULT_BATCH_ROOT: Final = ROOT / "artifacts" / "rp3" / "eval_panels"
DEFAULT_BANK_ROOT: Final = ROOT / "artifacts" / "rp3" / "evaluation_bank"
DEFAULT_FROZEN_DIR: Final = ROOT / "artifacts" / "rp3" / "frozen"
DEFAULT_LOOK_COUNTER: Final = ROOT / "artifacts" / "rp3" / "look_counter.json"
SIZING: Final = ROOT / "artifacts" / "rp3" / "sizing.json"

#: The H2 horizon, in minutes forward from the origin — the ext1 recipe's 120.
RETURN_HORIZON: Final = 120

#: One bank row per origin, in this exact column order.
BANK_COLUMNS: Final = (
    "session_date",
    "asset",
    "origin_minute",
    "index",
    "b1",
    "b1_plus_index",
    "rv30",
    "signed_return_120",
    "batch_id",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def assert_look_counter_zero(path: Path) -> None:
    """Banking with a spent look counter means the program state is wrong. Stop."""

    counter = json.loads(path.read_text(encoding="utf-8"))
    if counter.get("confirmatory_reads") != 0:
        raise RuntimeError(f"RP3_LOOK_COUNTER_NOT_ZERO:{counter.get('confirmatory_reads')}")


def _ny_today() -> date:
    """The exchange clock, behind a module seam the tests can pin."""

    return ny_today()


def _assert_bankable_session(session: str) -> None:
    """A banked session must be a real, completed trading date — not just a string.

    `assert_eval_session` bounds the window lexicographically; this adds what an
    adversarial review showed a hand-built batch could smuggle past it: a
    non-calendar string, a weekend, or a session that has not finished trading.
    """

    assert_eval_session(session)
    try:
        day = date.fromisoformat(session)
    except ValueError as error:
        raise ValueError(f"RP3_SCORE_INVALID_SESSION:{session}") from error
    if day.weekday() >= 5:
        raise ValueError(f"RP3_SCORE_NON_TRADING_SESSION:{session}")
    if day >= _ny_today():
        raise ValueError(f"RP3_SCORE_INCOMPLETE_SESSION:{session}")


def banked_sessions(bank_root: Path) -> set[str]:
    """Sessions banked by VERIFIED batches only — the census toward the read trigger.

    A parquet with no PASS manifest, or whose hash no longer matches its manifest,
    contributes nothing: the count that ends a 2.5-year program must not be
    inflatable by a stray file dropped into the directory.
    """

    sessions: set[str] = set()
    for manifest_path in bank_root.glob("*.manifest.json"):
        record = _reusable_manifest(manifest_path)
        if record is None:
            continue
        parquet = bank_root / f"{record.get('batch_id')}.parquet"
        if parquet.is_file() and _sha256(parquet) == record.get("parquet_sha256"):
            sessions.update(str(value) for value in record.get("sessions", []))
    return sessions


def _reusable_manifest(path: Path) -> dict[str, Any] | None:
    try:
        record: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return record if isinstance(record, dict) and record.get("status") == "PASS" else None


def _read_target_sessions() -> int:
    """The sealed sizing artifact's N — never a number restated in this script."""

    payload = json.loads(SIZING.read_text(encoding="utf-8"))
    return int(payload["n_primary"])


def load_eval_bars(data_root: Path) -> pl.DataFrame:
    """The batch's bar stores, normalised to the session-minute shape ext1 consumed."""

    frames = []
    for name, _, relative in EVAL_BAR_SOURCES:
        path = data_root / relative
        if not path.is_file():
            raise FileNotFoundError(f"RP3_EVAL_BAR_STORE_MISSING:{name}:{path}")
        frames.append(normalise_bars(pl.read_parquet(path)))
    return pl.concat(frames, how="vertical")


def signed_return_frame(
    bars: pl.DataFrame, origins_by_key: dict[tuple[str, str], np.ndarray]
) -> pl.DataFrame:
    """`signed_return_120` per origin, with exactly the ext1 target-battery arithmetic.

    Full session grid from position zero, forward-filled closes, fill-share gate at
    0.05, forward window ``(t, t+120]`` of one-minute log returns. A session the gate
    drops (or with fewer than 120 minutes remaining) yields NaN, never a dropped row.
    The equivalence with `rp2_ext1_mechanism_utility.build_target_battery` is pinned
    by `tests/unit/test_rp3_score_batch.py` — the recipe cannot drift silently.
    """

    rows = []
    grouped = bars.sort(["asset", "session_date", "minute"]).group_by(
        ["asset", "session_date"], maintain_order=True
    )
    for (asset, session_date), group in grouped:
        key = (str(asset), str(session_date))
        origins = origins_by_key.get(key)
        if origins is None:
            continue
        index = origins.astype(np.int64)
        blank = np.full(index.size, np.nan)
        grid = build_session_grid(group, session=date.fromisoformat(key[1]))
        if grid.fill_share > 0.05 or grid.close.min() <= 0.0:
            forward = blank
        elif not np.isfinite(grid.close).all():
            # Leading unfillable minutes: forward-fill has nothing before the open, the
            # fill gate does not count them, and ext1 would crash on the NaN with an
            # error naming nothing. Refuse with the session's name instead.
            raise RuntimeError(f"RP3_SCORE_SESSION_UNFILLED_OPEN:{key[0]}:{key[1]}")
        else:
            returns = log_returns(grid.close)
            cumulative = np.concatenate([[0.0], np.cumsum(returns)])
            valid = index + RETURN_HORIZON <= returns.size
            forward = np.where(
                valid,
                cumulative[np.minimum(index + RETURN_HORIZON, returns.size)]
                - cumulative[index],
                blank,
            )
        rows.append(
            pl.DataFrame(
                {
                    "asset": [key[0]] * index.size,
                    "session_date": [key[1]] * index.size,
                    "origin_minute": origins,
                    "signed_return_120": forward,
                }
            )
        )
    if not rows:
        raise RuntimeError("RP3_SCORE_NO_BAR_SESSIONS")
    return pl.concat(rows, how="vertical")


def _existing_bank_keys(bank_root: Path, exclude: str) -> pl.DataFrame | None:
    """Origin keys already banked by OTHER batches, for the duplicate refusal."""

    frames = []
    for path in sorted(bank_root.glob("*.parquet")):
        if path.stem == exclude:
            continue
        frames.append(pl.read_parquet(path, columns=list(JOIN_KEYS)))
    return pl.concat(frames, how="vertical") if frames else None


def score_batch(
    batch_dir: Path,
    data_root: Path,
    bank_root: Path,
    *,
    frozen_dir: Path = DEFAULT_FROZEN_DIR,
    look_counter: Path = DEFAULT_LOOK_COUNTER,
) -> dict[str, Any]:
    """Merge → mask → predict → returns → bank. Returns the batch's bank manifest."""

    assert_look_counter_zero(look_counter)
    resolved_bank = bank_root.resolve()
    if resolved_bank != DEFAULT_BANK_ROOT.resolve() and ROOT.resolve() in resolved_bank.parents:
        # Licensed-derived rows anywhere else inside the repo tree are trackable by
        # git and shaped so no gated-publish rule recognizes them. Refuse the foot-gun.
        raise RuntimeError(f"RP3_BANK_ROOT_UNSAFE:{bank_root}")
    batch_id = batch_dir.name
    bank_path = bank_root / f"{batch_id}.parquet"
    manifest_path = bank_root / f"{batch_id}.manifest.json"
    panel_paths = {
        "b0": batch_dir / "rp2_block4_b0" / "b0_panel.parquet",
        "b1": batch_dir / "rp2_block5_surface" / "b1_surface_panel.parquet",
        "b2": batch_dir / "rp2_block6_flow" / "b2_flow_panel.parquet",
    }
    input_hashes = {
        name: _sha256(path) for name, path in panel_paths.items() if path.is_file()
    }

    if bank_path.exists():
        if not manifest_path.exists():
            # A crash between the parquet and its manifest leaves this orphan. It is
            # recoverable, and it is NOT the tamper signal: delete the parquet and
            # re-run — its rows were never manifested into the bank.
            raise RuntimeError(f"RP3_BANK_ORPHAN_PARQUET:{bank_path}: delete it and re-run")
        recorded: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
        if recorded.get("status") == "PASS" and recorded.get("parquet_sha256") == _sha256(
            bank_path
        ):
            if recorded.get("input_sha256") != input_hashes:
                # The panels were rebuilt after banking: the bank holds rows from
                # inputs that no longer exist. Silent reuse here would carry a stale
                # build into the 2029 read.
                raise RuntimeError(f"RP3_BANK_INPUT_DRIFT:{batch_id}")
            print(f"[bank] {batch_id}: PASS (reused, parquet and inputs verified)")
            return recorded
        raise RuntimeError(f"RP3_BANK_BATCH_CONFLICT:{bank_path}")

    merged = load_merged_panel(panel_paths["b0"], panel_paths["b1"], panel_paths["b2"])
    for session in merged["session_date"].unique().to_list():
        _assert_bankable_session(str(session))

    target = np.asarray(merged["rv30"].to_numpy(), dtype=np.float64)
    mask = common_evaluation_mask(merged, target)
    universe = merged.filter(pl.Series(mask))
    if not universe.height:
        raise RuntimeError("RP3_SCORE_EMPTY_UNIVERSE")

    forecasts = load_frozen(frozen_dir).predict(universe)

    origins_by_key: dict[tuple[str, str], np.ndarray] = {}
    for (asset, session_date), group in universe.group_by(
        ["asset", "session_date"], maintain_order=True
    ):
        origins_by_key[(str(asset), str(session_date))] = np.asarray(
            group["origin_minute"].to_numpy(), dtype=np.float64
        )
    bars = load_eval_bars(data_root)
    bar_keys = {
        (str(asset), str(session)) for asset, session in
        bars.select(["asset", "session_date"]).unique().rows()
    }
    uncovered = sorted(set(origins_by_key) - bar_keys)
    if uncovered:
        # A panel session with no bars would LEFT-join to null realizations that sit
        # silently in the bank until 2029. A store/batch mismatch is refused, named.
        raise RuntimeError(
            f"RP3_SCORE_BARS_MISSING_SESSION:{uncovered[0][0]}:{uncovered[0][1]}"
        )
    returns_frame = signed_return_frame(bars, origins_by_key)

    # The panels carry Int64 origins; the returns frame was built from float arrays
    # (the ext1 arithmetic's dtype). Cast the join key to the panel's own dtype —
    # polars refuses mismatched key dtypes, and it would refuse on the first REAL
    # batch, not in a float-only synthetic test.
    returns_frame = returns_frame.with_columns(
        pl.col("origin_minute").cast(universe.schema["origin_minute"])
    )
    bank = (
        universe.select(["session_date", "asset", "origin_minute", "rv30"])
        .with_columns(
            index=pl.Series(forecasts["index"]),
            b1=pl.Series(forecasts["b1"]),
            b1_plus_index=pl.Series(forecasts["b1_plus_index"]),
            batch_id=pl.lit(batch_id),
        )
        .join(returns_frame, on=list(JOIN_KEYS), how="left")
        .select(BANK_COLUMNS)
        .sort("session_date", "asset", "origin_minute")
    )

    # One writer at a time: the duplicate scan below reads directory state, and two
    # concurrent writers with overlapping origins would both pass it. The lock is a
    # plain O_EXCL file; a stale one after a crash is removed by the operator, named.
    bank_root.mkdir(parents=True, exist_ok=True)
    lock_path = bank_root / ".lock"
    try:
        lock_fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as error:
        raise RuntimeError(
            f"RP3_BANK_LOCKED:{lock_path}: another scoring run holds the bank "
            "(or crashed holding it — verify, then delete the lock)"
        ) from error
    try:
        already = _existing_bank_keys(bank_root, exclude=batch_id)
        if already is not None:
            overlap = bank.join(already, on=list(JOIN_KEYS), how="inner")
            if overlap.height:
                first = overlap.row(0, named=True)
                raise RuntimeError(
                    "RP3_BANK_DUPLICATE_ORIGIN:"
                    f"{first['session_date']}:{first['asset']}:{first['origin_minute']}"
                )

        # Census BEFORE the write (an interrupted run must never have advanced the
        # count), and from VERIFIED manifests only — a stray parquet counts nothing.
        sessions = sorted(bank["session_date"].unique().to_list())
        total_sessions = len(banked_sessions(bank_root) | set(sessions))

        # Unique tmp names per writer, and the recorded sha256 is computed over the
        # tmp BEFORE the rename — never over a path another process could replace.
        tmp = bank_path.with_suffix(f".{os.getpid()}.parquet.tmp")
        bank.write_parquet(tmp)
        parquet_sha = _sha256(tmp)
        os.replace(tmp, bank_path)

        manifest: dict[str, Any] = {
            "schema": "rp3_bank_batch/1",
            "banked_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
            "batch_id": batch_id,
            "rows": bank.height,
            "sessions": sessions,
            "evaluation_mask_sha256": mask_sha256(mask),
            "input_sha256": input_hashes,
            "parquet_sha256": parquet_sha,
            "status": "PASS",
        }
        tmp_manifest = manifest_path.with_suffix(f".{os.getpid()}.json.tmp")
        tmp_manifest.write_bytes(
            (json.dumps(manifest, sort_keys=True, indent=2) + "\n").encode("utf-8")
        )
        os.replace(tmp_manifest, manifest_path)
    finally:
        os.close(lock_fd)
        lock_path.unlink(missing_ok=True)

    # Operational facts only: counts, never anything comparing forecasts to outcomes.
    needed = _read_target_sessions()
    print(f"[bank] {batch_id}: {bank.height} origin rows across {len(sessions)} sessions")
    print(f"[bank] evaluable sessions banked so far: {total_sessions} of {needed}")
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch-id", type=str, required=True)
    parser.add_argument("--batch-root", type=Path, default=DEFAULT_BATCH_ROOT)
    parser.add_argument("--data-root", type=Path, default=provisional_data_root())
    parser.add_argument("--bank-root", type=Path, default=DEFAULT_BANK_ROOT)
    arguments = parser.parse_args(argv)
    batch_dir = arguments.batch_root / arguments.batch_id
    if not batch_dir.is_dir():
        raise SystemExit(f"RP3_SCORE_BATCH_MISSING:{batch_dir}")
    score_batch(batch_dir, arguments.data_root, arguments.bank_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
