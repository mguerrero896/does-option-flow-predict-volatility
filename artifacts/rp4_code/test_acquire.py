"""Fixture-only RP4 acquisition boundary and calendar checks."""

import json
from datetime import UTC, date, datetime, timedelta

import acquire
import close_b1
import httpx
import pytest


def test_closeout_hash_detects_changed_bytes_and_path_escape(tmp_path, monkeypatch):
    monkeypatch.setattr(close_b1, "DATA", tmp_path)
    path = tmp_path / "fixture.json"
    path.write_text("original", encoding="utf-8")
    expected = acquire.sha256(path)
    assert close_b1.checked_hash(path, expected) == expected
    path.write_text("changed", encoding="utf-8")
    with pytest.raises(ValueError, match="CUSTODY_HASH_MISMATCH"):
        close_b1.checked_hash(path, expected)
    with pytest.raises(ValueError):
        close_b1.checked_hash(tmp_path / "../outside.json", expected)


def test_retry_five_total_attempts(monkeypatch):
    sleeps = []
    monkeypatch.setattr(acquire.time, "sleep", sleeps.append)
    attempts = []

    def broken():
        raise RuntimeError("fixture failure")

    with pytest.raises(RuntimeError):
        acquire.retry(broken, attempts)
    assert len(attempts) == 5
    assert sleeps == [1, 2, 4, 8]
    assert all("fixture failure" not in str(row) for row in attempts)


def test_retry_success_stops(monkeypatch):
    monkeypatch.setattr(acquire.time, "sleep", lambda _: None)
    attempts = []
    assert acquire.retry(lambda: 42, attempts) == 42
    assert attempts == [{"attempt": 1, "status": "PASS"}]


def test_output_bound_rejects_source_and_root(tmp_path):
    root = tmp_path / "rp4"
    assert acquire.bound(root / "new.json", root) == root / "new.json"
    for candidate in [root, root / "../phase9/bars.parquet"]:
        with pytest.raises(ValueError, match="OUTSIDE"):
            acquire.bound(candidate, root)


def test_exchange_holiday_and_early_close():
    assert acquire.latest_closed(datetime(2026, 9, 7, 21, tzinfo=UTC)) == date(2026, 9, 4)
    # Black Friday closes 13:00 New York, not the usual 16:00.
    assert acquire.latest_closed(datetime(2025, 11, 28, 18, 31, tzinfo=UTC)) == date(2025, 11, 28)
    assert acquire.latest_closed(datetime(2025, 11, 28, 18, 29, tzinfo=UTC)) == date(2025, 11, 26)


def test_receipt_is_immutable(tmp_path):
    path = tmp_path / "receipt.json"
    acquire.write_receipt(path, {"status": "PASS"})
    with pytest.raises(ValueError, match="IMMUTABLE_OUTPUT_MISMATCH"):
        acquire.write_receipt(path, {"status": "different"})


def test_batch_calendar():
    assert len(acquire.sessions(date(2026, 7, 20), date(2026, 9, 4))) == 35
    assert len(acquire.sessions(date(2026, 8, 3), date(2026, 8, 18))) == 12


def test_phase9_copy_preserves_source_and_checks_reuse(tmp_path, monkeypatch):
    root = tmp_path / "rp4"
    source = tmp_path / "phase9"
    day = date(2026, 8, 19)
    session = source / str(day)
    session.mkdir(parents=True)
    bars = session / "bars.parquet"
    bars.write_bytes(b"fixture-only-not-real-parquet")
    (session / "session_manifest.json").write_text(
        json.dumps(
            {
                "sha256": {"bars.parquet": acquire.sha256(bars)},
            }
        )
    )
    before = {path.name: acquire.sha256(path) for path in session.iterdir()}
    monkeypatch.setattr(acquire, "ROOT", root)
    monkeypatch.setattr(acquire, "PHASE9", source)
    monkeypatch.setattr(acquire, "authorization", lambda _: None)
    monkeypatch.setattr(acquire, "space", lambda: None)
    first = acquire.copy_phase9(day, "a" * 64)
    second = acquire.copy_phase9(day, "a" * 64)
    assert first == second
    assert before == {path.name: acquire.sha256(path) for path in session.iterdir()}
    copy = root / "phase9_copies" / str(day) / "bars.parquet"
    copy.write_bytes(b"corruption")
    with pytest.raises(ValueError, match="REUSE_HASH_MISMATCH"):
        acquire.copy_phase9(day, "a" * 64)


def test_source_manifest_mismatch_is_not_copied(tmp_path, monkeypatch):
    source = tmp_path / "phase9"
    session = source / "2026-08-19"
    session.mkdir(parents=True)
    (session / "bars.parquet").write_bytes(b"fixture")
    (session / "session_manifest.json").write_text(
        json.dumps(
            {
                "sha256": {"bars.parquet": "a" * 64},
            }
        )
    )
    monkeypatch.setattr(acquire, "ROOT", tmp_path / "rp4")
    monkeypatch.setattr(acquire, "PHASE9", source)
    monkeypatch.setattr(acquire, "authorization", lambda _: None)
    with pytest.raises(ValueError, match="SOURCE_HASH_MISMATCH"):
        acquire.copy_phase9(date(2026, 8, 19), "a" * 64)


def test_fomc_only_statement_links_not_minutes():
    html = " ".join(
        [
            "<strong>Statement:</strong>/newsevents/pressreleases/monetary20240918a.htm</div>",
            "<strong>Statement:</strong>/newsevents/pressreleases/monetary20250129a.htm</div>",
            "<strong>Statement:</strong>/newsevents/pressreleases/monetary20260729a.htm</div>",
            "/newsevents/pressreleases/monetary20250822a.htm goals (notation vote)</div>",
            "/monetarypolicy/fomcminutes20260819.htm",
            "/newsevents/pressreleases/monetary20260916a.htm",
        ]
    )
    assert acquire.fomc_dates(html) == ["2024-09-18", "2025-01-29", "2026-07-29"]
    with pytest.raises(ValueError, match="INCOMPLETE"):
        acquire.fomc_dates("not a calendar")


def test_local_tape_reuse_exact_hash(tmp_path, monkeypatch):
    real_path = acquire.Path
    source_root = tmp_path / "uw_source"
    source = source_root / "2026-08-17/historical_tape_2026-08-17.zip"
    source.parent.mkdir(parents=True)
    source.write_bytes(b"fixture: CRC is checked later by existing tape filter")
    monkeypatch.setattr(
        acquire,
        "Path",
        lambda value: real_path(
            str(value).replace(
                "private-input/bb1d8627685c6f6dd347",
                str(source_root),
            )
        ),
    )
    monkeypatch.setattr(acquire, "ROOT", tmp_path / "rp4")
    monkeypatch.setattr(acquire, "authorization", lambda _: None)
    monkeypatch.setattr(acquire, "space", lambda: None)
    first = acquire.reuse_local_tape(date(2026, 8, 17), "a" * 64)
    assert first["source_sha256"] == acquire.sha256(source)
    assert acquire.reuse_local_tape(date(2026, 8, 17), "a" * 64) == first
    assert acquire.reuse_local_tape(date(2026, 8, 18), "a" * 64) is None


def test_tape_kernel_lock_exclusive_and_released(tmp_path, monkeypatch):
    monkeypatch.setattr(acquire, "ROOT", tmp_path / "rp4")
    day = date(2026, 8, 19)
    with acquire.tape_lock(day):
        with pytest.raises(OSError), acquire.tape_lock(day):
            pytest.fail("Concurrent writer acquired the same session lock")
        with acquire.tape_lock(date(2026, 8, 20)):
            pass
    with acquire.tape_lock(day):
        pass


def test_cli_worker_sets_disjoint_and_complete(monkeypatch, capsys):
    monkeypatch.setattr(acquire, "authorization", lambda _: None)
    groups = {}
    for group in ("all", "requested", "copied"):
        monkeypatch.setattr(
            acquire.sys,
            "argv",
            [
                "acquire.py",
                "--spec-hash",
                "a" * 64,
                "--dry-run",
                "--tape-group",
                group,
            ],
        )
        assert acquire.main() == 0
        groups[group] = set(json.loads(capsys.readouterr().out)["tape_sessions"])
    assert len(groups["all"]) == 25
    assert len(groups["requested"]) == 14
    assert len(groups["copied"]) == 11
    assert not groups["requested"] & groups["copied"]
    assert groups["requested"] | groups["copied"] == groups["all"]


def test_cached_calendar_predicate_matches_original_on_boundaries():
    for day in (date(2026, 8, 3), date(2025, 11, 28), date(2025, 3, 10)):
        opening, closing = acquire.regular_bounds(day)
        for reference in (opening, closing):
            for offset in (-1, 0, 1):
                timestamp = reference + timedelta(microseconds=offset)
                assert acquire.regular_cached(timestamp, day) == acquire.tape_core._regular(
                    timestamp, day
                )


def test_cli_rejects_unregistered_tape_subset(monkeypatch):
    monkeypatch.setattr(acquire, "authorization", lambda _: None)
    monkeypatch.setattr(
        acquire.sys,
        "argv",
        ["acquire.py", "--spec-hash", "a" * 64, "--dry-run", "--tape-sessions", "2026-10-01"],
    )
    with pytest.raises(ValueError, match="SUBSET_OUTSIDE_AUTHORIZED_WINDOW"):
        acquire.main()


def test_dividends_refreshed_in_new_root_and_receipt_is_immutable(tmp_path, monkeypatch):
    monkeypatch.setattr(acquire, "ROOT", tmp_path / "rp4")
    monkeypatch.setattr(acquire, "authorization", lambda _: None)
    monkeypatch.setenv("FMP_API_KEY", "fixture-not-a-secret")
    client = httpx.Client
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200, json=[{"declarationDate": "2026-08-26", "dividend": 0.01}]
        )
    )
    monkeypatch.setattr(
        acquire.httpx, "Client", lambda **kwargs: client(transport=transport, **kwargs)
    )
    first = acquire.acquire_dividends("NVDA", "spec")
    assert first["rows"] == 1 and first["old_source_unchanged"]
    assert acquire.acquire_dividends("NVDA", "spec") == first
    receipt = acquire.ROOT / "manifests/dividends/NVDA.json"
    before = receipt.read_bytes()
    with pytest.raises(ValueError, match="IMMUTABLE_OUTPUT_MISMATCH"):
        acquire.write_receipt(receipt, {"status": "changed"})
    assert receipt.read_bytes() == before
