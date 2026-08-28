"""The RP3 banking step, end to end on synthetic panels — with the REAL frozen models.

What is pinned here, in the order the program cares:

- A synthetic two-session batch flows merge → mask → predict → returns → bank and
  produces exactly the runbook's row schema, scored by the actual hash-verified
  frozen boosters committed in `artifacts/rp3/frozen` (no model is faked).
- `signed_return_120` is **equivalent to the ext1 recipe that defined it**: the same
  synthetic bars run through `rp2_ext1_mechanism_utility.build_target_battery` and
  the values must match exactly — the divergence hazard the contract map flagged.
- Idempotency is verified (a reused batch re-hashes its parquet), duplicated origins
  across batches are refused (they would inflate the N=662 trigger), a pre-window
  session is refused, a spent look counter halts banking, and the module source
  carries no aggregation machinery (no QLIKE, no contrast — the anti-look tripwire).
"""

from __future__ import annotations

import importlib.util
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import numpy as np
import polars as pl
import pytest

from mds650.rp2.panel import B0_FEATURES, B1_FEATURES, B2_FEATURES

ROOT = Path(__file__).resolve().parents[2]

#: One constant per-minute log return: signed_return_120 == 120 * RET, exactly.
RET = 0.0005
SESSIONS = ("2026-08-31", "2026-09-01")
ORIGINS = (60.0, 65.0, 70.0)


def _load(name: str):  # type: ignore[no-untyped-def]  # a script module has no stub
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def scorer():  # type: ignore[no-untyped-def]
    return _load("rp3_score_batch")


@pytest.fixture(autouse=True)
def _future_clock(scorer, monkeypatch):  # type: ignore[no-untyped-def]
    """Pin the exchange clock past the synthetic sessions, so they read as complete."""

    from datetime import date as date_type

    monkeypatch.setattr(scorer, "_ny_today", lambda: date_type(2026, 9, 2))


def _feature_value(name: str) -> float:
    """Finite, positive, deterministic per name — safe under every registry transform."""

    return 0.1 + (hash(name) % 7) * 0.05


def _panel_rows(session: str) -> dict[str, list]:  # type: ignore[type-arg]
    n = len(ORIGINS)
    return {
        "asset": ["AAPL"] * n,
        "session_date": [session] * n,
        # Int64, like the real block outputs — the bank join must cast, not crash.
        "origin_minute": [int(origin) for origin in ORIGINS],
    }


def _write_batch(batch_dir: Path, sessions: tuple[str, ...] = SESSIONS) -> None:
    """A synthetic batch in exactly the adapter's on-disk layout."""

    b0_frames, b1_frames, b2_frames = [], [], []
    for session in sessions:
        base = _panel_rows(session)
        b0 = dict(base)
        b0["role"] = ["RP3"] * len(ORIGINS)
        b0["source"] = ["rp3_eval"] * len(ORIGINS)
        b0["rv30"] = [1e-4] * len(ORIGINS)
        for name in B0_FEATURES:
            b0[name] = [_feature_value(name)] * len(ORIGINS)
        b0_frames.append(pl.DataFrame(b0))
        b1 = dict(base)
        for name in B1_FEATURES:
            b1[name] = [_feature_value(name)] * len(ORIGINS)
        b1_frames.append(pl.DataFrame(b1))
        b2 = dict(base)
        for name in B2_FEATURES:
            b2[name] = [_feature_value(name)] * len(ORIGINS)
        b2["b2_5m_is_empty_window"] = [0.0] * len(ORIGINS)
        b2_frames.append(pl.DataFrame(b2))
    (batch_dir / "rp2_block4_b0").mkdir(parents=True)
    (batch_dir / "rp2_block5_surface").mkdir(parents=True)
    (batch_dir / "rp2_block6_flow").mkdir(parents=True)
    pl.concat(b0_frames).write_parquet(batch_dir / "rp2_block4_b0" / "b0_panel.parquet")
    pl.concat(b1_frames).write_parquet(
        batch_dir / "rp2_block5_surface" / "b1_surface_panel.parquet"
    )
    pl.concat(b2_frames).write_parquet(
        batch_dir / "rp2_block6_flow" / "b2_flow_panel.parquet"
    )


def _raw_bars(
    skip_open_minutes: int = 0, gap: tuple[int, int] | None = None
) -> pl.DataFrame:
    """Full 390-minute sessions of constant log-return closes, in the store's shape."""

    rows = []
    for session in SESSIONS:
        year, month, day = (int(part) for part in session.split("-"))
        open_utc = datetime(year, month, day, 13, 30, tzinfo=UTC)  # 09:30 New York, EDT
        start = skip_open_minutes if session == SESSIONS[0] else 0
        skipped = range(*gap) if gap is not None and session == SESSIONS[0] else range(0)
        for minute in range(start, 390):
            if minute in skipped:
                continue
            rows.append(
                {
                    "asset": "AAPL",
                    "bar_start_utc": open_utc + timedelta(minutes=minute),
                    "open": 100.0,
                    "high": 101.0,
                    "low": 99.0,
                    "close": float(100.0 * np.exp(RET * minute)),
                    "volume": 1000.0,
                }
            )
    return pl.DataFrame(rows)


def _write_store(
    data_root: Path, skip_open_minutes: int = 0, gap: tuple[int, int] | None = None
) -> None:
    from mds650.rp3.eval_inventory import EVAL_BAR_SOURCES

    (_, _, relative), = EVAL_BAR_SOURCES
    store = data_root / relative
    store.parent.mkdir(parents=True)
    _raw_bars(skip_open_minutes, gap).write_parquet(store)


@pytest.fixture()
def batch_env(tmp_path: Path):  # type: ignore[no-untyped-def]
    batch_dir = tmp_path / "batches" / "rp3-batch-test"
    _write_batch(batch_dir)
    data_root = tmp_path / "data"
    _write_store(data_root)
    bank_root = tmp_path / "bank"
    return batch_dir, data_root, bank_root


def test_score_batch_banks_the_runbook_row_schema(scorer, batch_env) -> None:  # type: ignore[no-untyped-def]
    batch_dir, data_root, bank_root = batch_env
    manifest = scorer.score_batch(batch_dir, data_root, bank_root)

    assert manifest["status"] == "PASS"
    assert manifest["rows"] == len(SESSIONS) * len(ORIGINS)
    assert manifest["sessions"] == list(SESSIONS)
    assert len(manifest["evaluation_mask_sha256"]) == 64

    bank = pl.read_parquet(bank_root / "rp3-batch-test.parquet")
    assert bank.columns == list(scorer.BANK_COLUMNS)
    assert bank.height == len(SESSIONS) * len(ORIGINS)
    # The REAL frozen boosters scored these rows: strictly positive variance forecasts.
    assert (bank["b1"] > 0).all()
    assert (bank["b1_plus_index"] > 0).all()
    assert np.isfinite(bank["index"].to_numpy()).all()
    assert (bank["rv30"] == 1e-4).all()
    # Constant per-minute log return ⇒ the 120-minute forward return is exactly 120·r.
    assert np.allclose(bank["signed_return_120"].to_numpy(), 120 * RET, atol=1e-12)


def test_signed_return_matches_the_ext1_recipe_exactly(scorer, batch_env, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """The equivalence pin the contract map demanded: same bars, same values."""

    _, data_root, _ = batch_env
    bars = scorer.load_eval_bars(data_root)
    origins_by_key = {
        ("AAPL", session): np.asarray(ORIGINS, dtype=np.float64) for session in SESSIONS
    }
    ours = scorer.signed_return_frame(bars, origins_by_key).sort(
        ["session_date", "origin_minute"]
    )

    ext1 = _load("rp2_ext1_mechanism_utility")
    monkeypatch.setattr(ext1, "load_bar_sources", lambda root: bars)
    battery = ext1.build_target_battery(Path("unused"), origins_by_key).sort(
        ["session_date", "origin_minute"]
    )
    assert np.array_equal(
        ours["signed_return_120"].to_numpy(),
        battery["y_signed_return_120"].to_numpy(),
    )


def test_rescoring_a_batch_is_a_verified_no_op(scorer, batch_env) -> None:  # type: ignore[no-untyped-def]
    batch_dir, data_root, bank_root = batch_env
    first = scorer.score_batch(batch_dir, data_root, bank_root)
    again = scorer.score_batch(batch_dir, data_root, bank_root)
    assert again == first  # reused from the verified manifest, not recomputed

    # A tampered bank parquet breaks the verification: conflict, never silent reuse.
    bank_path = bank_root / "rp3-batch-test.parquet"
    bank_path.write_bytes(b"tampered")
    with pytest.raises(RuntimeError, match="RP3_BANK_BATCH_CONFLICT"):
        scorer.score_batch(batch_dir, data_root, bank_root)


def test_duplicate_origins_across_batches_are_refused(scorer, batch_env) -> None:  # type: ignore[no-untyped-def]
    """The same origin banked twice would inflate the N=662 trigger. Refused."""

    batch_dir, data_root, bank_root = batch_env
    scorer.score_batch(batch_dir, data_root, bank_root)
    clone = batch_dir.parent / "rp3-batch-clone"
    _write_batch(clone)
    with pytest.raises(RuntimeError, match="RP3_BANK_DUPLICATE_ORIGIN:2026-08-31:AAPL"):
        scorer.score_batch(clone, data_root, bank_root)


def test_a_pre_window_session_is_refused(scorer, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    """The refusal fires at the merge, before a bar store is even needed."""

    batch_dir = tmp_path / "batches" / "rp3-batch-bad"
    _write_batch(batch_dir, sessions=("2026-07-17",))
    with pytest.raises(ValueError, match="RP3_EVAL_WINDOW_VIOLATION:2026-07-17"):
        scorer.score_batch(batch_dir, tmp_path / "data", tmp_path / "bank")


def test_an_orphan_parquet_names_its_recovery(scorer, batch_env) -> None:  # type: ignore[no-untyped-def]
    """Crash between parquet and manifest: recoverable, and NOT the tamper signal."""

    batch_dir, data_root, bank_root = batch_env
    bank_root.mkdir(parents=True)
    (bank_root / "rp3-batch-test.parquet").write_bytes(b"orphan-from-a-crash")
    with pytest.raises(RuntimeError, match="RP3_BANK_ORPHAN_PARQUET.*delete it and re-run"):
        scorer.score_batch(batch_dir, data_root, bank_root)


def test_rebuilt_inputs_refuse_stale_reuse(scorer, batch_env) -> None:  # type: ignore[no-untyped-def]
    """Rebuilding the panels under the same batch id must not silently reuse old rows."""

    batch_dir, data_root, bank_root = batch_env
    scorer.score_batch(batch_dir, data_root, bank_root)
    b0_path = batch_dir / "rp2_block4_b0" / "b0_panel.parquet"
    rebuilt = pl.read_parquet(b0_path).with_columns(rv30=pl.lit(2e-4))
    rebuilt.write_parquet(b0_path)
    with pytest.raises(RuntimeError, match="RP3_BANK_INPUT_DRIFT:rp3-batch-test"):
        scorer.score_batch(batch_dir, data_root, bank_root)


def test_an_unfilled_open_names_the_session(scorer, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    """Leading minutes forward-fill cannot reach: a named refusal, not a cryptic crash."""

    batch_dir = tmp_path / "batches" / "rp3-batch-test"
    _write_batch(batch_dir)
    data_root = tmp_path / "data"
    _write_store(data_root, skip_open_minutes=5)
    with pytest.raises(
        RuntimeError, match=f"RP3_SCORE_SESSION_UNFILLED_OPEN:AAPL:{SESSIONS[0]}"
    ):
        scorer.score_batch(batch_dir, data_root, tmp_path / "bank")


def test_a_gated_session_banks_nan_where_ext1_drops_it(scorer, tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """The one deliberate divergence, pinned: the bank keeps the row, valued NaN."""

    data_root = tmp_path / "data"
    _write_store(data_root, gap=(100, 131))  # 31 filled minutes: fill_share > 0.05
    bars = scorer.load_eval_bars(data_root)
    origins_by_key = {
        ("AAPL", session): np.asarray(ORIGINS, dtype=np.float64) for session in SESSIONS
    }
    ours = scorer.signed_return_frame(bars, origins_by_key)
    gated = ours.filter(pl.col("session_date") == SESSIONS[0])
    clean = ours.filter(pl.col("session_date") == SESSIONS[1])
    assert gated.height == len(ORIGINS)
    assert np.isnan(gated["signed_return_120"].to_numpy()).all()
    assert np.allclose(clean["signed_return_120"].to_numpy(), 120 * RET, atol=1e-12)

    ext1 = _load("rp2_ext1_mechanism_utility")
    monkeypatch.setattr(ext1, "load_bar_sources", lambda root: bars)
    battery = ext1.build_target_battery(Path("unused"), origins_by_key)
    assert battery.filter(pl.col("session_date") == SESSIONS[0]).height == 0  # dropped
    assert np.allclose(
        battery.filter(pl.col("session_date") == SESSIONS[1])["y_signed_return_120"].to_numpy(),
        clean["signed_return_120"].to_numpy(),
    )


def test_a_bank_root_inside_the_repo_is_refused(scorer, batch_env) -> None:  # type: ignore[no-untyped-def]
    """Licensed rows outside the gitignored default but inside the repo: refused."""

    batch_dir, data_root, _ = batch_env
    unsafe = ROOT / "artifacts" / "rp3" / "bank2"
    with pytest.raises(RuntimeError, match="RP3_BANK_ROOT_UNSAFE"):
        scorer.score_batch(batch_dir, data_root, unsafe)
    assert not unsafe.exists()


def test_a_held_lock_refuses_a_second_writer(scorer, batch_env) -> None:  # type: ignore[no-untyped-def]
    batch_dir, data_root, bank_root = batch_env
    bank_root.mkdir(parents=True)
    (bank_root / ".lock").write_bytes(b"")
    with pytest.raises(RuntimeError, match="RP3_BANK_LOCKED"):
        scorer.score_batch(batch_dir, data_root, bank_root)
    # The foreign lock is not cleaned up by the refused process.
    assert (bank_root / ".lock").exists()


def test_a_session_missing_from_the_bar_store_is_refused(scorer, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    """No bars for a panel session must refuse, never bank null realizations."""

    batch_dir = tmp_path / "batches" / "rp3-batch-test"
    _write_batch(batch_dir)
    data_root = tmp_path / "data"
    from mds650.rp3.eval_inventory import EVAL_BAR_SOURCES

    (_, _, relative), = EVAL_BAR_SOURCES
    store = data_root / relative
    store.parent.mkdir(parents=True)
    only_first = _raw_bars().filter(
        pl.col("bar_start_utc").dt.date().cast(pl.Utf8) == SESSIONS[0]
    )
    only_first.write_parquet(store)
    with pytest.raises(
        RuntimeError, match=f"RP3_SCORE_BARS_MISSING_SESSION:AAPL:{SESSIONS[1]}"
    ):
        scorer.score_batch(batch_dir, data_root, tmp_path / "bank")


def test_fabricated_session_dates_are_refused(scorer, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    """Strings that pass a lexicographic window check are still not trading days."""

    cases = {
        "2099-99-99": "RP3_SCORE_INVALID_SESSION",  # not a calendar date at all
        "2026-08-30": "RP3_SCORE_NON_TRADING_SESSION",  # a Sunday
        "2026-09-15": "RP3_SCORE_INCOMPLETE_SESSION",  # after the pinned NY clock
    }
    for session, expected in cases.items():
        with pytest.raises(ValueError, match=f"{expected}:{session}"):
            scorer._assert_bankable_session(session)


def test_the_census_counts_only_verified_batches(scorer, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    """A stray or tampered parquet contributes nothing toward the read trigger."""

    bank_root = tmp_path / "bank"
    bank_root.mkdir()
    good = bank_root / "rp3-batch-a.parquet"
    good.write_bytes(b"good-bytes")
    import hashlib

    (bank_root / "rp3-batch-a.manifest.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "batch_id": "rp3-batch-a",
                "sessions": ["2026-08-31"],
                "parquet_sha256": hashlib.sha256(b"good-bytes").hexdigest(),
            }
        ),
        encoding="utf-8",
    )
    (bank_root / "stray.parquet").write_bytes(b"who-put-this-here")  # no manifest
    tampered = bank_root / "rp3-batch-b.parquet"
    tampered.write_bytes(b"changed-after-banking")
    (bank_root / "rp3-batch-b.manifest.json").write_text(
        json.dumps(
            {
                "status": "PASS",
                "batch_id": "rp3-batch-b",
                "sessions": ["2026-09-01"],
                "parquet_sha256": "0" * 64,
            }
        ),
        encoding="utf-8",
    )
    assert scorer.banked_sessions(bank_root) == {"2026-08-31"}


def test_a_spent_look_counter_halts_banking(scorer, batch_env, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    batch_dir, data_root, bank_root = batch_env
    spent = tmp_path / "look_counter.json"
    spent.write_text(json.dumps({"confirmatory_reads": 1}), encoding="utf-8")
    with pytest.raises(RuntimeError, match="RP3_LOOK_COUNTER_NOT_ZERO:1"):
        scorer.score_batch(batch_dir, data_root, bank_root, look_counter=spent)


def test_the_scoring_module_carries_no_aggregation_machinery(scorer) -> None:  # type: ignore[no-untyped-def]
    """Anti-look tripwire: the module cannot even IMPORT the comparison machinery.

    Prose can mention QLIKE (this module's docstring rightly does); what must never
    appear is the machinery itself — so the pin inspects the actual imports and the
    actual call names, not words in strings.
    """

    import ast

    source = (ROOT / "scripts" / "rp3_score_batch.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    modules: set[str] = set()
    calls: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
            modules.update(f"{node.module}.{alias.name}" for alias in node.names)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                calls.add(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                calls.add(node.func.attr)
    for forbidden in ("qlike", "inference", "contrast", "bootstrap", "spa"):
        offenders = {m for m in modules if forbidden in m.lower()}
        assert not offenders, f"forbidden import machinery: {offenders}"
    # Aggregation call names too: an adversarial review showed a one-line
    # numpy aggregate over the bank frame would slip past an import-only pin.
    # (cumsum is the ext1 arithmetic and is not an aggregate across rows.)
    banned_calls = {
        "session_contrast", "clark_west", "giacomini_white",
        "mean", "nanmean", "average", "median", "std", "corr", "cov", "dot", "sum",
    }
    hit = banned_calls & calls
    assert not hit, f"forbidden aggregation call: {hit}"
    assert "confirmatory_reads" in source  # it checks the counter, never moves it