"""The RP3 acquirer's guards, pinned hermetically — no network, no secret, no real disk.

What is load-bearing here, in the order the adversarial review demanded it:

- The Phase 8 cohort seal refuses in both modes (calendar and result proof) at planning
  time AND in depth inside both acquisition legs — a caller that imports a leg directly
  cannot acquire a sealed session.
- Session completeness is measured on the America/New_York clock, injected everywhere
  (`_ny_today` is monkeypatched), because this machine's local date runs ahead of the
  exchange.
- Idempotency is verified, not trusted: tape reuse requires the recorded ZIP SHA-256 to
  still match disk, bar reuse requires the store to exist, a corrupt manifest reads as
  not-reusable, and a corrupt pre-existing ZIP is discarded and re-downloaded.
- A provider failure mid-session leaves no partial state, and the rerun completes.
- The asset universes cannot drift from the frozen ones, and the two scripts' data
  roots compose (the acquirer writes exactly where the batch adapter reads).
- main()'s CLI wiring is executed in both its PLANNED and REFUSED forms.

The FMP leg runs end to end through an `httpx.MockTransport` that enforces the auth
contract (`apikey` header, never Bearer) and returns schema-exact rows the real
normalizer parses; the UW leg runs through a calibration-module double with the exact
five attributes the acquirer uses.
"""

from __future__ import annotations

import importlib.util
import json
from datetime import date
from pathlib import Path

import pytest

from mds650.contracts import CANDIDATE_ASSETS
from mds650.rp2.panel import TARGET_ASSETS

ROOT = Path(__file__).resolve().parents[2]


def _load(name: str):  # type: ignore[no-untyped-def]  # a script module has no stub
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def acquirer():  # type: ignore[no-untyped-def]
    return _load("rp3_acquire_batch")


def _clock(monkeypatch, acquirer, today: date) -> None:  # type: ignore[no-untyped-def]
    """Pin the New York clock the acquirer consults everywhere."""

    monkeypatch.setattr(acquirer, "_ny_today", lambda: today)


# ─── Planning guards ────────────────────────────────────────────────────────────


def test_business_days_skip_weekends_and_holidays(acquirer) -> None:  # type: ignore[no-untyped-def]
    days = acquirer.business_days(date(2026, 9, 4), date(2026, 9, 8))
    # 2026-09-05/06 is a weekend and 2026-09-07 is Labor Day.
    assert days == [date(2026, 9, 4), date(2026, 9, 8)]


def test_the_window_boundary_refuses_at_the_door(acquirer) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError, match="RP3_EVAL_WINDOW_VIOLATION:2026-07-17"):
        acquirer.plan_sessions(
            date(2026, 7, 17),
            date(2026, 7, 17),
            today=date(2026, 9, 1),
            phase8_read_complete=True,
        )


def test_the_phase8_cohort_is_sealed_by_calendar(acquirer) -> None:  # type: ignore[no-untyped-def]
    """Before the read date the flag changes nothing: the seal is not attestable away."""

    for flag in (False, True):
        with pytest.raises(ValueError, match="RP3_ACQUIRE_PHASE8_SEALED:2026-07-20"):
            acquirer.plan_sessions(
                date(2026, 7, 20),
                date(2026, 8, 21),
                today=date(2026, 8, 25),
                phase8_read_complete=flag,
            )


def test_the_phase8_cohort_requires_result_proof_after_the_read(acquirer) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(ValueError, match="RP3_ACQUIRE_PHASE8_RESULT_REQUIRED"):
        acquirer.plan_sessions(
            date(2026, 7, 20),
            date(2026, 8, 21),
            today=date(2026, 8, 31),
            phase8_read_complete=False,
        )
    days = acquirer.plan_sessions(
        date(2026, 7, 20),
        date(2026, 8, 21),
        today=date(2026, 8, 31),
        phase8_read_complete=True,
    )
    assert days[0] == date(2026, 7, 20)
    assert days[-1] == date(2026, 8, 21)
    assert all(day.weekday() < 5 for day in days)


def test_post_cohort_sessions_need_no_phase8_result(acquirer) -> None:  # type: ignore[no-untyped-def]
    days = acquirer.plan_sessions(
        date(2026, 8, 31),
        date(2026, 9, 1),
        today=date(2026, 9, 2),
        phase8_read_complete=False,
    )
    assert days == [date(2026, 8, 31), date(2026, 9, 1)]


def test_phase8_result_must_be_self_hashed_evaluator_output(acquirer, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    import hashlib

    result = {
        "status": "EXPLORATORY_BRIDGE_EVALUATION_COMPLETE",
        "claim_classification": "EXPLORATORY_DESCRIPTIVE_NOT_CONFIRMATORY",
        "protocol_id": "phase8a-exploratory-bridge-20of30-v2",
        "sealed_cohorts_read": 1,
        "confirmatory_promotion_allowed": False,
    }
    result["result_sha256"] = hashlib.sha256(
        json.dumps(result, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    path = tmp_path / "result.json"
    path.write_text(json.dumps(result), encoding="utf-8")
    assert acquirer._phase8_result_complete(path)
    result["sealed_cohorts_read"] = 0
    path.write_text(json.dumps(result), encoding="utf-8")
    with pytest.raises(ValueError, match="RP3_ACQUIRE_PHASE8_RESULT_INVALID"):
        acquirer._phase8_result_complete(path)


def test_incomplete_sessions_are_refused(acquirer) -> None:  # type: ignore[no-untyped-def]
    """day >= today refuses: on the NY clock a same-day session is still trading."""

    with pytest.raises(ValueError, match="RP3_ACQUIRE_INCOMPLETE_SESSION:2026-08-31"):
        acquirer.plan_sessions(
            date(2026, 8, 31),
            date(2026, 8, 31),
            today=date(2026, 8, 31),
            phase8_read_complete=True,
        )


def test_the_clock_is_new_york_not_the_machine(acquirer) -> None:  # type: ignore[no-untyped-def]
    """The injected clock exists and reads America/New_York, not the local zone."""

    from datetime import datetime
    from zoneinfo import ZoneInfo

    assert acquirer._ny_today() == datetime.now(ZoneInfo("America/New_York")).date()


# ─── Storage layout and universe pins ───────────────────────────────────────────


def _config(acquirer, tmp_path: Path, day: date):  # type: ignore[no-untyped-def]
    return acquirer.RP3StorageConfig(
        sessions=(day,),
        excluded_dates=frozenset(),
        data_root=tmp_path,
        minimum_free_bytes=80 * acquirer.GIB,
        projected_peak_additional_bytes=1,
    )


def test_the_storage_config_lands_tape_where_the_adapter_looks(  # type: ignore[no-untyped-def]
    acquirer, tmp_path: Path
) -> None:
    config = _config(acquirer, tmp_path, date(2026, 8, 31))
    assert config.event_root == tmp_path / "tape" / "full_tape_eval"
    assert config.raw_root == tmp_path / "raw" / "full_tape"
    assert config.manifest_root == tmp_path / "manifests" / "full_tape"
    assert config.temporary_root == tmp_path / "tmp"


def test_the_asset_universes_cannot_drift(acquirer) -> None:  # type: ignore[no-untyped-def]
    """Bars == tape candidates == targets + market controls; GOOGL never was one."""

    assert set(acquirer.BAR_ASSETS) == set(CANDIDATE_ASSETS)
    assert set(TARGET_ASSETS) | {"SPY", "QQQ"} == set(acquirer.BAR_ASSETS)
    assert "TSLA" in TARGET_ASSETS
    assert "GOOGL" not in CANDIDATE_ASSETS
    adapter = _load("rp3_build_eval_panels")
    assert adapter.TARGET_ASSETS is TARGET_ASSETS


def test_the_two_scripts_data_roots_compose(acquirer) -> None:  # type: ignore[no-untyped-def]
    """The acquirer writes exactly where the batch adapter reads, by default."""

    from mds650.rp3.eval_inventory import EVAL_BAR_SOURCES

    adapter = _load("rp3_build_eval_panels")
    adapter_root = acquirer.DEFAULT_DATA_ROOT.parent
    acquirer_root = acquirer.DEFAULT_DATA_ROOT
    assert adapter_root / adapter.TAPE_RELATIVE == acquirer_root / "tape" / "full_tape_eval"
    (_, _, bars_relative), = EVAL_BAR_SOURCES
    assert (
        adapter_root / bars_relative
        == acquirer_root / "data" / "fmp" / "underlying_1min_eval.parquet"
    )


# ─── Small helpers ──────────────────────────────────────────────────────────────


def test_default_end_walks_back_to_a_trading_day(acquirer) -> None:  # type: ignore[no-untyped-def]
    # 2026-09-08 is a Tuesday; the day before is Labor Day, before that a weekend.
    assert acquirer._default_end(date(2026, 9, 8)) == date(2026, 9, 4)
    assert acquirer._default_end(date(2026, 9, 1)) == date(2026, 8, 31)


def test_reusable_accepts_only_an_intact_pass_manifest(acquirer, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    assert acquirer._reusable(tmp_path / "none.json") is None
    failed = tmp_path / "failed.json"
    failed.write_text(json.dumps({"status": "FAIL"}), encoding="utf-8")
    assert acquirer._reusable(failed) is None
    corrupt = tmp_path / "corrupt.json"
    corrupt.write_text('{"status": "PA', encoding="utf-8")  # torn write
    assert acquirer._reusable(corrupt) is None
    passed = tmp_path / "passed.json"
    passed.write_text(json.dumps({"status": "PASS", "x": 1}), encoding="utf-8")
    assert acquirer._reusable(passed) == {"status": "PASS", "x": 1}


def test_manifest_writes_are_atomic_and_leave_no_tmp(acquirer, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    target = tmp_path / "m.json"
    acquirer._write_manifest(target, {"status": "PASS"})
    assert json.loads(target.read_text(encoding="utf-8")) == {"status": "PASS"}
    assert not target.with_suffix(".json.tmp").exists()


def _bar_row(asset: str, when: object, price: float) -> dict[str, object]:
    return {
        "asset": asset,
        "bar_start_utc": when,
        "open": price,
        "high": price + 1.0,
        "low": price - 0.5,
        "close": price + 0.5,
        "volume": 10.0,
    }


def test_merge_bars_appends_dedupes_and_leaves_no_tmp(acquirer, tmp_path: Path) -> None:  # type: ignore[no-untyped-def]
    from datetime import UTC, datetime

    import polars as pl

    store = tmp_path / "store.parquet"
    t0 = datetime(2026, 8, 31, 13, 30, tzinfo=UTC)
    t1 = datetime(2026, 8, 31, 13, 31, tzinfo=UTC)
    first = pl.DataFrame([_bar_row("AAPL", t0, 1.0), _bar_row("AAPL", t1, 1.5)])
    assert acquirer._merge_bars(store, first) == 2
    # The append path re-reads the parquet and concatenates a fresh python-built
    # frame: a dtype mismatch would raise here, today — not on 2026-08-30.
    second = pl.DataFrame([_bar_row("AAPL", t1, 9.0), _bar_row("MSFT", t0, 3.0)])
    assert acquirer._merge_bars(store, second) == 3
    back = pl.read_parquet(store)
    kept = back.filter((pl.col("asset") == "AAPL") & (pl.col("bar_start_utc") == t1))
    assert kept["open"].to_list() == [1.5]  # the duplicate keeps the first write
    assert not store.with_suffix(".parquet.tmp").exists()


# ─── The FMP leg, end to end without a network byte ─────────────────────────────


def _fmp_mock_transport(requests_log: list, rows_per_asset: int = 2):  # type: ignore[no-untyped-def]
    """A faithful FMP double: asserts the auth contract, returns schema-exact rows."""

    import httpx

    def handler(request: httpx.Request) -> httpx.Response:
        requests_log.append(request)
        assert request.headers.get("apikey"), "FMP must authenticate via the apikey header"
        assert "authorization" not in request.headers, "Bearer with FMP is forbidden"
        assert request.url.path == "/stable/historical-chart/1min"
        day = request.url.params["from"]
        assert request.url.params["to"] == day
        rows = [
            {
                "date": f"{day} 09:{30 + minute:02d}:00",
                "open": 1.0,
                "high": 2.0,
                "low": 0.5,
                "close": 1.5,
                "volume": 100,
            }
            for minute in range(rows_per_asset)
        ]
        return httpx.Response(200, json=rows)

    return httpx.MockTransport(handler)


@pytest.fixture()
def bars_env(acquirer, monkeypatch):  # type: ignore[no-untyped-def]
    import time as time_module

    monkeypatch.setenv("FMP_API_KEY", "hermetic-test-key")
    monkeypatch.setattr(time_module, "sleep", lambda seconds: None)
    _clock(monkeypatch, acquirer, date(2026, 9, 2))


def test_acquire_bars_hermetic_end_to_end(acquirer, tmp_path: Path, bars_env) -> None:  # type: ignore[no-untyped-def]
    import polars as pl

    log: list = []
    day = date(2026, 8, 31)

    records, store = acquirer.acquire_bars(
        [day], tmp_path, "test-run", transport=_fmp_mock_transport(log)
    )
    assert len(log) == len(acquirer.BAR_ASSETS)
    # Every asset was requested, each exactly once — a wrong-symbol regression shows.
    assert {r.url.params["symbol"] for r in log} == set(acquirer.BAR_ASSETS)
    assert records[0]["status"] == "PASS"
    assert records[0]["rows_by_asset"] == {asset: 2 for asset in acquirer.BAR_ASSETS}
    frame = pl.read_parquet(store)
    assert frame.height == 2 * len(acquirer.BAR_ASSETS)
    assert set(frame["asset"].unique().to_list()) == set(acquirer.BAR_ASSETS)
    manifest_path = tmp_path / "manifests" / "fmp_eval" / f"{day.isoformat()}.json"
    assert json.loads(manifest_path.read_text(encoding="utf-8"))["status"] == "PASS"
    assert not manifest_path.with_suffix(".json.tmp").exists()

    # Second run: the manifest short-circuits and zero requests leave the process.
    log.clear()
    records, _ = acquirer.acquire_bars(
        [day], tmp_path, "test-run", transport=_fmp_mock_transport(log)
    )
    assert log == []
    assert records[0]["status"] == "PASS"

    # A later session APPENDS through the read-back path with real normalizer dtypes.
    records, _ = acquirer.acquire_bars(
        [date(2026, 9, 1)], tmp_path, "test-run", transport=_fmp_mock_transport(log)
    )
    assert pl.read_parquet(store).height == 4 * len(acquirer.BAR_ASSETS)


def test_acquire_bars_reuse_is_anchored_to_the_store(acquirer, tmp_path: Path, bars_env) -> None:  # type: ignore[no-untyped-def]
    """A PASS manifest with the store gone is not honored — the session re-acquires."""

    log: list = []
    day = date(2026, 8, 31)
    _, store = acquirer.acquire_bars(
        [day], tmp_path, "test-run", transport=_fmp_mock_transport(log)
    )
    store.unlink()
    log.clear()
    records, store = acquirer.acquire_bars(
        [day], tmp_path, "test-run", transport=_fmp_mock_transport(log)
    )
    assert len(log) == len(acquirer.BAR_ASSETS)  # it went back to the provider
    assert store.is_file()
    assert records[0]["status"] == "PASS"


def test_acquire_bars_mid_batch_failure_leaves_no_partial_state(  # type: ignore[no-untyped-def]
    acquirer, tmp_path: Path, bars_env
) -> None:
    """A provider failure mid-session writes nothing; the rerun completes cleanly."""

    import httpx

    from mds650.errors import ProviderBlockedError

    day = date(2026, 8, 31)
    calls: list = []

    def failing(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if request.url.params["symbol"] == sorted(acquirer.BAR_ASSETS)[3]:
            return httpx.Response(500)
        row = {"date": "2026-08-31 09:30:00", "open": 1.0, "high": 2.0}
        row.update({"low": 0.5, "close": 1.5, "volume": 1})
        return httpx.Response(200, json=[row])

    with pytest.raises(ProviderBlockedError):
        acquirer.acquire_bars(
            [day], tmp_path, "test-run", transport=httpx.MockTransport(failing)
        )
    manifest_path = tmp_path / "manifests" / "fmp_eval" / f"{day.isoformat()}.json"
    assert not manifest_path.exists()
    assert not (tmp_path / "data" / "fmp" / "underlying_1min_eval.parquet").exists()

    records, store = acquirer.acquire_bars(
        [day], tmp_path, "test-run", transport=_fmp_mock_transport([])
    )
    assert records[0]["status"] == "PASS"
    assert store.is_file()


def test_acquire_bars_refuses_an_empty_session(acquirer, tmp_path: Path, bars_env) -> None:  # type: ignore[no-untyped-def]
    import httpx

    empty = httpx.MockTransport(lambda request: httpx.Response(200, json=[]))
    with pytest.raises(RuntimeError, match="RP3_ACQUIRE_EMPTY_SESSION:2026-08-31"):
        acquirer.acquire_bars([date(2026, 8, 31)], tmp_path, "test-run", transport=empty)


def test_acquire_bars_guards_all_three_rules_in_depth(  # type: ignore[no-untyped-def]
    acquirer, tmp_path: Path, monkeypatch
) -> None:
    """Even a caller that bypasses planning meets the window, the seal, and the clock."""

    monkeypatch.setenv("FMP_API_KEY", "hermetic-test-key")
    transport = _fmp_mock_transport([])
    _clock(monkeypatch, acquirer, date(2026, 9, 2))
    with pytest.raises(ValueError, match="RP3_EVAL_WINDOW_VIOLATION:2026-07-17"):
        acquirer.acquire_bars([date(2026, 7, 17)], tmp_path, "test-run", transport=transport)
    with pytest.raises(ValueError, match="RP3_ACQUIRE_INCOMPLETE_SESSION:2026-09-02"):
        acquirer.acquire_bars([date(2026, 9, 2)], tmp_path, "test-run", transport=transport)
    _clock(monkeypatch, acquirer, date(2026, 8, 25))
    with pytest.raises(ValueError, match="RP3_ACQUIRE_PHASE8_SEALED:2026-08-21"):
        acquirer.acquire_bars([date(2026, 8, 21)], tmp_path, "test-run", transport=transport)
    _clock(monkeypatch, acquirer, date(2026, 9, 2))
    with pytest.raises(ValueError, match="RP3_ACQUIRE_PHASE8_RESULT_REQUIRED"):
        acquirer.acquire_bars([date(2026, 8, 21)], tmp_path, "test-run", transport=transport)


# ─── The UW leg, through a faithful calibration double ──────────────────────────


def _fake_calibration(downloads: list, *, schema_fields=("id", "underlying_symbol")):  # type: ignore[no-untyped-def]
    """A calibration-module double with the exact five attributes the acquirer uses."""

    from types import SimpleNamespace

    filter_calls: list = []

    def stream_download(day, key, destination):  # type: ignore[no-untyped-def]
        assert key == "hermetic-uw-key"
        assert destination.parent.is_dir(), "the acquirer must create the zip parent"
        downloads.append(day)
        destination.write_bytes(b"zip-bytes-for-" + day.isoformat().encode("utf-8"))

    validate_calls: list = []

    def validate_zip(path, fields):  # type: ignore[no-untyped-def]
        validate_calls.append(path)
        if path.read_bytes() == b"corrupt-partial":
            raise RuntimeError("FULL_TAPE_ZIP_CRC_FAILURE")
        return ("member.csv", set(schema_fields), 8)

    def filter_session(day, zip_path, fields, config):  # type: ignore[no-untyped-def]
        filter_calls.append(fields)
        return {
            "rows_seen": 9,
            "rows_retained": 7,
            "schema_fields": sorted(schema_fields),
        }

    fake = SimpleNamespace(
        EVENT_FIELDS=tuple(schema_fields),
        _secret=lambda name: "hermetic-uw-key",
        _stream_download=stream_download,
        _validate_zip=validate_zip,
        filter_session=filter_session,
    )
    fake.filter_calls = filter_calls
    fake.validate_calls = validate_calls
    return fake


@pytest.fixture()
def tape_clock(acquirer, monkeypatch):  # type: ignore[no-untyped-def]
    _clock(monkeypatch, acquirer, date(2026, 9, 2))


def test_acquire_tape_writes_manifests_and_reuses_them(  # type: ignore[no-untyped-def]
    acquirer, tmp_path: Path, monkeypatch, tape_clock
) -> None:
    import hashlib

    downloads: list = []
    fresh_fake = _fake_calibration(downloads)
    monkeypatch.setattr(acquirer, "_load_calibration", lambda: fresh_fake)
    day = date(2026, 8, 31)
    config = _config(acquirer, tmp_path, day)

    records = acquirer.acquire_tape([day], config)
    assert downloads == [day]
    # A fresh download is validated once, inside filter_session — never re-probed.
    assert fresh_fake.validate_calls == []
    zip_path = config.raw_root / day.isoformat() / f"full_tape_{day.isoformat()}.zip"
    assert zip_path.is_file()
    manifest_path = config.manifest_root / f"{day.isoformat()}.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest["status"] == "PASS"
    assert manifest["rows_retained"] == 7
    assert manifest["zip_sha256"] == hashlib.sha256(zip_path.read_bytes()).hexdigest()
    assert records[0] == manifest
    assert not manifest_path.with_suffix(".json.tmp").exists()

    # Second run: the verified PASS manifest short-circuits; re-downloading is a failure.
    def refuse(day, key, destination):  # type: ignore[no-untyped-def]
        raise AssertionError("a verified PASS session must never be re-downloaded")

    fake = _fake_calibration(downloads)
    fake._stream_download = refuse
    monkeypatch.setattr(acquirer, "_load_calibration", lambda: fake)
    records = acquirer.acquire_tape([day], config)
    assert records[0]["status"] == "PASS"


def test_acquire_tape_reuse_requires_the_recorded_zip(  # type: ignore[no-untyped-def]
    acquirer, tmp_path: Path, monkeypatch, tape_clock
) -> None:
    """A PASS manifest whose ZIP is missing or altered is not trusted: re-acquire."""

    downloads: list = []
    monkeypatch.setattr(acquirer, "_load_calibration", lambda: _fake_calibration(downloads))
    day = date(2026, 8, 31)
    config = _config(acquirer, tmp_path, day)
    acquirer.acquire_tape([day], config)
    zip_path = config.raw_root / day.isoformat() / f"full_tape_{day.isoformat()}.zip"

    # Tampered ZIP: sha mismatch → the fresh path runs again (probe accepts the bytes).
    zip_path.write_bytes(b"tampered-but-valid")
    downloads.clear()
    records = acquirer.acquire_tape([day], config)
    assert records[0]["status"] == "PASS"
    assert json.loads(
        (config.manifest_root / f"{day.isoformat()}.json").read_text(encoding="utf-8")
    )["zip_sha256"] == acquirer._sha256(zip_path)

    # Missing ZIP → a full re-download happens.
    zip_path.unlink()
    downloads.clear()
    acquirer.acquire_tape([day], config)
    assert downloads == [day]


def test_acquire_tape_discards_a_corrupt_leftover_zip(  # type: ignore[no-untyped-def]
    acquirer, tmp_path: Path, monkeypatch, tape_clock
) -> None:
    """A corrupt partial ZIP from an interrupted run cannot wedge its session."""

    downloads: list = []
    fake = _fake_calibration(downloads)
    monkeypatch.setattr(acquirer, "_load_calibration", lambda: fake)
    day = date(2026, 8, 31)
    config = _config(acquirer, tmp_path, day)
    zip_path = config.raw_root / day.isoformat() / f"full_tape_{day.isoformat()}.zip"
    zip_path.parent.mkdir(parents=True)
    zip_path.write_bytes(b"corrupt-partial")

    records = acquirer.acquire_tape([day], config)
    assert downloads == [day]  # discarded, then downloaded fresh
    assert len(fake.validate_calls) == 1  # probed the leftover once, not the fresh zip
    assert records[0]["status"] == "PASS"
    assert zip_path.read_bytes().startswith(b"zip-bytes-for-")


def test_acquire_tape_pins_the_first_sessions_schema(  # type: ignore[no-untyped-def]
    acquirer, tmp_path: Path, monkeypatch, tape_clock
) -> None:
    """The core's semantics: first fresh session None, later sessions pinned to it."""

    downloads: list = []
    fake = _fake_calibration(downloads)
    monkeypatch.setattr(acquirer, "_load_calibration", lambda: fake)
    days = [date(2026, 8, 31), date(2026, 9, 1)]
    config = acquirer.RP3StorageConfig(
        sessions=tuple(days),
        excluded_dates=frozenset(),
        data_root=tmp_path,
        minimum_free_bytes=80 * acquirer.GIB,
        projected_peak_additional_bytes=1,
    )
    acquirer.acquire_tape(days, config)
    assert fake.filter_calls == [None, {"id", "underlying_symbol"}]


def test_acquire_tape_guards_all_three_rules_in_depth(  # type: ignore[no-untyped-def]
    acquirer, tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setattr(acquirer, "_load_calibration", lambda: _fake_calibration([]))
    _clock(monkeypatch, acquirer, date(2026, 8, 25))
    sealed = date(2026, 8, 21)
    with pytest.raises(ValueError, match="RP3_ACQUIRE_PHASE8_SEALED:2026-08-21"):
        acquirer.acquire_tape([sealed], _config(acquirer, tmp_path, sealed))
    _clock(monkeypatch, acquirer, date(2026, 9, 2))
    with pytest.raises(ValueError, match="RP3_ACQUIRE_PHASE8_RESULT_REQUIRED"):
        acquirer.acquire_tape([sealed], _config(acquirer, tmp_path, sealed))
    pre_window = date(2026, 7, 17)
    with pytest.raises(ValueError, match="RP3_EVAL_WINDOW_VIOLATION:2026-07-17"):
        acquirer.acquire_tape([pre_window], _config(acquirer, tmp_path, pre_window))
    # The tape leg reads its own clock: a same-day session is incomplete here too.
    same_day = date(2026, 9, 2)
    with pytest.raises(ValueError, match="RP3_ACQUIRE_INCOMPLETE_SESSION:2026-09-02"):
        acquirer.acquire_tape([same_day], _config(acquirer, tmp_path, same_day))


def test_execute_preflights_the_fmp_secret_before_any_tape_work(  # type: ignore[no-untyped-def]
    acquirer, tmp_path: Path, monkeypatch
) -> None:
    """A missing FMP key aborts before the tape leg, not an hour into it."""

    import argparse

    monkeypatch.delenv("FMP_API_KEY", raising=False)
    monkeypatch.delenv("MDS650_FMP_API_KEY", raising=False)

    def tape_must_not_run():  # type: ignore[no-untyped-def]
        raise AssertionError("the tape leg must not start without the FMP key")

    monkeypatch.setattr(acquirer, "_load_calibration", tape_must_not_run)
    arguments = argparse.Namespace(
        data_root=tmp_path,
        start=date(2026, 8, 31),
        end=date(2026, 9, 1),
        phase8_read_complete=False,
        dry_run=False,
    )
    with pytest.raises(RuntimeError, match="MISSING_SECRET:FMP_API_KEY"):
        acquirer.execute(arguments, today=date(2026, 9, 2))


# ─── The CLI wiring ─────────────────────────────────────────────────────────────


def test_main_dry_run_plans_a_legal_batch(acquirer, tmp_path: Path, monkeypatch, capsys) -> None:  # type: ignore[no-untyped-def]
    _clock(monkeypatch, acquirer, date(2026, 9, 2))
    code = acquirer.main(
        [
            "--dry-run",
            "--start",
            "2026-08-31",
            "--end",
            "2026-09-01",
            "--data-root",
            str(tmp_path),
        ]
    )
    assert code == 0
    plan = json.loads(capsys.readouterr().out)
    assert plan["status"] == "PLANNED"
    assert plan["sessions"] == ["2026-08-31", "2026-09-01"]
    assert plan["tape_root"] == str(tmp_path / "tape" / "full_tape_eval")


def test_main_dry_run_refuses_the_sealed_backlog_today(  # type: ignore[no-untyped-def]
    acquirer, tmp_path: Path, monkeypatch, capsys
) -> None:
    _clock(monkeypatch, acquirer, date(2026, 8, 25))
    code = acquirer.main(["--dry-run", "--data-root", str(tmp_path)])
    assert code == 1
    refusal = json.loads(capsys.readouterr().out)
    assert refusal["status"] == "REFUSED"
    assert "RP3_ACQUIRE_PHASE8_SEALED" in refusal["error"]
