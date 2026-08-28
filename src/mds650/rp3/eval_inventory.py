"""The RP3 evaluation batch's own inputs: bar stores, tape inventory, window guards.

The RP2 world is frozen: `mds650.rp2.bars.BAR_SOURCES` and the block-1 partition
inventory name exactly the stores every sealed result was built from, and RP3 must not
touch either — an entry added there would flow into the v3 runner's input manifests and
into frozen-run replays. RP3 therefore carries its own registry, in the same shapes the
block builders already consume: bar stores as ``(name, role, relative_path)`` tuples for
blocks 3 and 4, and a JSONL tape inventory (``asset, path, role, session_date,
size_bytes, source`` per file) for blocks 5 and 6 through their ``--inventory`` flag.

Every session that enters here is window-checked: the preregistration's evaluation window
is sessions strictly after 2026-07-17, and a pre-window session in an evaluation batch is
refused at the door (`RP3_EVAL_WINDOW_VIOLATION`), not filtered silently — a batch that
contains one is a batch someone assembled wrong, and the difference matters.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Final

from mds650.rp3.frozen_forecasters import TRAINING_WINDOW_END

#: Role label carried by every RP3 evaluation row, in the same column the RP2 partition
#: used for D and V. Nothing downstream branches on it; it exists so a row's provenance
#: is readable in every panel that carries it.
EVAL_ROLE: Final = "RP3"

#: Bar stores of an RP3 evaluation batch, relative to the batch's ``--data-root``, in the
#: exact tuple shape `BAR_SOURCES` uses. One store for the six target assets plus SPY and
#: QQQ (the B0 market controls need them), appended by acquisition batch as they are
#: acquired. The names are dated so two batches can never collide.
EVAL_BAR_SOURCES: Final[tuple[tuple[str, str, str], ...]] = (
    ("rp3_eval", EVAL_ROLE, "rp3/data/fmp/underlying_1min_eval.parquet"),
)

#: A tape directory is one session of one store, named ``date=YYYY-MM-DD`` exactly as the
#: five RP2 tape stores on disk are partitioned.
_DATE_DIRECTORY: Final = re.compile(r"^date=(\d{4}-\d{2}-\d{2})$")


def assert_eval_session(session_date: str) -> str:
    """The window boundary, applied to one session date; returns it for chaining."""

    if session_date <= TRAINING_WINDOW_END:
        raise ValueError(f"RP3_EVAL_WINDOW_VIOLATION:{session_date}")
    return session_date


def discover_tape_sessions(tape_root: Path) -> dict[str, list[Path]]:
    """Map each ``date=`` partition under ``tape_root`` to its parquet files.

    Discovery is deliberately dumb — directories named by date, files inside them — so
    that what the driver reports is exactly what the acquisition wrote, with no inference
    to be wrong about. Every discovered session is window-checked here.
    """

    if not tape_root.is_dir():
        raise FileNotFoundError(f"RP3_EVAL_TAPE_ROOT_MISSING:{tape_root}")
    sessions: dict[str, list[Path]] = {}
    for entry in sorted(tape_root.iterdir()):
        match = _DATE_DIRECTORY.match(entry.name)
        if match is None or not entry.is_dir():
            continue
        session = assert_eval_session(match.group(1))
        files = sorted(path for path in entry.glob("*.parquet") if path.is_file())
        if files:
            sessions[session] = files
    if not sessions:
        raise ValueError(f"RP3_EVAL_NO_SESSIONS:{tape_root}")
    return sessions


def write_eval_inventory(
    sessions: dict[str, list[Path]],
    assets: list[str],
    output_path: Path,
    *,
    source: str = "rp3_eval_tape",
) -> int:
    """Write the batch's tape inventory in the block-1 row shape; returns rows written.

    One row per (session, asset, file): blocks 5 and 6 index by ``(session_date, asset)``
    and read every path listed for the pair, so a full-tape file that holds all assets is
    listed once per asset — the same convention the RP2 inventory uses for shared stores.
    """

    if not assets:
        raise ValueError("RP3_EVAL_NO_ASSETS")
    rows = 0
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        for session_date in sorted(sessions):
            assert_eval_session(session_date)
            for path in sessions[session_date]:
                size = path.stat().st_size
                for asset in assets:
                    handle.write(
                        json.dumps(
                            {
                                "asset": asset,
                                "path": str(path),
                                "role": EVAL_ROLE,
                                "session_date": session_date,
                                "size_bytes": size,
                                "source": source,
                            },
                            sort_keys=True,
                        )
                        + "\n"
                    )
                    rows += 1
    return rows
