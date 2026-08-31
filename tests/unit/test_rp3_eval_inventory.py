"""The RP3 batch adapter's guards, held on synthetic fixtures — no licensed byte needed.

What is pinned: the window boundary refuses a pre-window session at the door in every
entry path (discovery, inventory writing, bar loading); the inventory rows come out in
exactly the block-1 shape blocks 5 and 6 index; and the dry run reports the wiring it
found rather than a wiring it hoped for. The builders' own behaviour is not re-tested
here — their contracts do that — only the adapter's promises.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import polars as pl
import pytest

from mds650.rp3.eval_inventory import (
    EVAL_ROLE,
    assert_eval_session,
    discover_tape_sessions,
    load_eval_bars,
    write_eval_inventory,
)


def _tape_fixture(root: Path, dates: list[str]) -> Path:
    tape = root / "rp3" / "tape" / "full_tape_eval"
    for date in dates:
        day = tape / f"date={date}"
        day.mkdir(parents=True)
        (day / "full_tape.parquet").write_bytes(b"not-a-real-parquet")
    return tape


def test_the_window_boundary_refuses_at_the_door() -> None:
    assert assert_eval_session("2026-07-18") == "2026-07-18"
    with pytest.raises(ValueError, match="RP3_EVAL_WINDOW_VIOLATION:2026-07-17"):
        assert_eval_session("2026-07-17")
    with pytest.raises(ValueError, match="RP3_EVAL_WINDOW_VIOLATION:2024-08-02"):
        assert_eval_session("2024-08-02")


def test_discovery_maps_dated_partitions_and_guards_them(tmp_path: Path) -> None:
    tape = _tape_fixture(tmp_path, ["2026-07-20", "2026-07-21"])
    sessions = discover_tape_sessions(tape)
    assert sorted(sessions) == ["2026-07-20", "2026-07-21"]
    assert all(len(files) == 1 for files in sessions.values())


def test_discovery_refuses_a_pre_window_partition(tmp_path: Path) -> None:
    """One stale directory poisons the batch; it is refused, not filtered."""

    tape = _tape_fixture(tmp_path, ["2026-07-20", "2026-07-17"])
    with pytest.raises(ValueError, match="RP3_EVAL_WINDOW_VIOLATION:2026-07-17"):
        discover_tape_sessions(tape)


def test_discovery_refuses_an_empty_root(tmp_path: Path) -> None:
    empty = tmp_path / "rp3" / "tape" / "full_tape_eval"
    empty.mkdir(parents=True)
    with pytest.raises(ValueError, match="RP3_EVAL_NO_SESSIONS"):
        discover_tape_sessions(empty)


def test_the_inventory_rows_are_block1_shaped(tmp_path: Path) -> None:
    """Blocks 5 and 6 index by (session_date, asset) over these exact keys."""

    tape = _tape_fixture(tmp_path, ["2026-07-20"])
    sessions = discover_tape_sessions(tape)
    output = tmp_path / "eval_inventory.jsonl"
    rows = write_eval_inventory(sessions, ["AAPL", "MSFT"], output)
    assert rows == 2  # one file x two assets
    lines = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert len(lines) == 2
    for row in lines:
        assert sorted(row) == ["asset", "path", "role", "session_date", "size_bytes", "source"]
        assert row["role"] == EVAL_ROLE
        assert row["session_date"] == "2026-07-20"
        assert row["size_bytes"] > 0
    assert {row["asset"] for row in lines} == {"AAPL", "MSFT"}


def test_the_inventory_writer_guards_its_own_input(tmp_path: Path) -> None:
    """A hand-assembled session map is guarded too, not only the discovery path."""

    output = tmp_path / "inv.jsonl"
    fake = tmp_path / "f.parquet"
    fake.write_bytes(b"x")
    with pytest.raises(ValueError, match="RP3_EVAL_WINDOW_VIOLATION"):
        write_eval_inventory({"2026-07-17": [fake]}, ["AAPL"], output)
    with pytest.raises(ValueError, match="RP3_EVAL_NO_ASSETS"):
        write_eval_inventory({"2026-07-20": [fake]}, [], output)


def test_the_dry_run_reports_the_wiring_it_found(tmp_path: Path) -> None:
    import importlib.util

    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(
        "rp3_build_eval_panels", root / "scripts" / "rp3_build_eval_panels.py"
    )
    assert spec is not None and spec.loader is not None
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)

    _tape_fixture(tmp_path, ["2026-07-20"])
    plan = driver.dry_run(tmp_path)
    assert plan["sessions"] == ["2026-07-20"]
    assert plan["tape_files"] == 1
    assert plan["builders"] == "reachable"
    stores = plan["bar_stores"]
    assert isinstance(stores, dict)
    # The fixture has no bar store: the dry run must SAY so, not fail or pretend.
    assert all(store["present"] is False for store in stores.values())


def test_eval_bar_loader_uses_the_shared_normalizer(tmp_path: Path) -> None:
    """The adapter survives Block 3 moving normalization into the shared bar module."""

    import importlib.util

    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(
        "rp3_build_eval_panels", root / "scripts" / "rp3_build_eval_panels.py"
    )
    assert spec is not None and spec.loader is not None
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)

    store = tmp_path / "rp3" / "data" / "fmp" / "underlying_1min_eval.parquet"
    store.parent.mkdir(parents=True)
    pl.DataFrame(
        {
            "asset": ["AAPL"],
            "bar_start_utc": [datetime(2026, 7, 20, 13, 30, tzinfo=UTC)],
            "close": [200.0],
        }
    ).write_parquet(store)

    bars = load_eval_bars(tmp_path)
    assert bars.select("session_date", "minute", "role").row(0) == (
        datetime(2026, 7, 20).date(),
        0,
        EVAL_ROLE,
    )


def test_join_market_controls_uses_the_origin_key(tmp_path: Path) -> None:
    """The b0-controls join is keyed on origin_minute (block 4's own key), and an
    empty controls frame skips the join — the inline version briefly used a
    nonexistent ``minute`` column, which only a real build would have hit."""

    import importlib.util

    root = Path(__file__).resolve().parents[2]
    spec = importlib.util.spec_from_file_location(
        "rp3_build_eval_panels", root / "scripts" / "rp3_build_eval_panels.py"
    )
    assert spec is not None and spec.loader is not None
    driver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(driver)

    b0 = pl.DataFrame(
        {"session_date": ["2026-08-31"], "origin_minute": [60], "ret_30": [0.01]}
    )
    controls = pl.DataFrame(
        {"session_date": ["2026-08-31"], "origin_minute": [60], "SPY_rv_30": [0.1]}
    )
    joined = driver.join_market_controls(b0, controls)
    assert joined["SPY_rv_30"].to_list() == [0.1]

    empty = pl.DataFrame({"session_date": [], "origin_minute": []})
    assert driver.join_market_controls(b0, empty).columns == b0.columns
