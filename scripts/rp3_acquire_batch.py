"""Acquire one RP3 evaluation batch: UW full-tape ZIPs and FMP 1-minute bars.

This is the acquisition step the RP3 runbook's operating cycle names first, built
entirely from the two verified provider cores this repository already trusts:

- **Tape** reuses ``scripts/download_calibration_20d.py`` verbatim by import — the same
  documented ZIP endpoint (``docs/reference/provider_http_reference.md``), the same
  Bearer auth via ``_secret`` (the key value is never printed), the same CRC-validated
  stream filter into ``date=``/``asset=`` parquet partitions with disk-backed dedup.
  The only change is where the partitions land: an ``RP3StorageConfig`` points the
  event root at ``<data-root>/tape/full_tape_eval``, exactly where
  ``scripts/rp3_build_eval_panels.py`` discovers batches. The filter's asset universe
  is the same eight-asset candidate store every RP2 tape store on disk carries.
- **Bars** reuse ``mds650.providers.fmp`` the way ``scripts/acquire_gate3_dev_bars.py``
  does — ``apikey`` header (never Bearer), one session per request because FMP
  truncates wide 1-minute ranges to the trailing ~1,500 rows — for the six frozen
  target assets plus SPY and QQQ, appended idempotently into
  ``<data-root>/data/fmp/underlying_1min_eval.parquet`` (the batch adapter reads it
  through ``EVAL_BAR_SOURCES``; the composition of the two scripts' data roots is
  pinned by test).

Three fail-closed guards make a wrong batch impossible rather than unlikely, and all
three hold **in depth** — enforced per session inside both acquisition legs, not only
at planning time, so a future helper that imports a leg directly cannot lose them:

1. ``RP3_EVAL_WINDOW_VIOLATION`` — no session at or before 2026-07-17 is ever acquired.
2. ``RP3_ACQUIRE_INCOMPLETE_SESSION`` — only completed sessions are acquired, and
   "today" is measured on the **America/New_York clock**, because this machine runs
   ahead of the exchange: at local midnight the NYSE session is still trading.
3. ``RP3_ACQUIRE_PHASE8_SEALED`` / ``..._RESULT_REQUIRED`` — the Phase 8
   prospective cohort (sessions 2026-07-20..2026-08-28, one-shot read 2026-08-29,
   ``docs/phase8_bridge_protocol_v2.md``) is sealed: ``sealed_cohorts_read = 0``
   admits no acquisition-time exception, so those sessions are refused until the
   calendar passes the read date AND the completed evaluator result proves the read
   occurred (``--phase8-result``, covering the protocol's slip-day contingency).

Idempotency is verified, not trusted: a tape session is reused only when its PASS
manifest's recorded SHA-256 still matches the ZIP on disk, a bar session only while
the store it fed still exists, and a pre-existing ZIP that fails CRC validation is
deleted and re-downloaded once rather than wedging its session forever. Manifests are
written atomically and a corrupt manifest reads as "not reusable", never as a crash.
Every run ends with a summary manifest carrying the bar store's SHA-256.

    uv run python scripts/rp3_acquire_batch.py --dry-run
    uv run python scripts/rp3_acquire_batch.py --phase8-result <result.json>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Final

import polars as pl

from mds650.config import provisional_data_root
from mds650.exchange_clock import ny_today
from mds650.phase5_storage import Phase5StorageConfig, storage_preflight
from mds650.providers.fmp import FMPProvider, parse_minute_payload
from mds650.rp2.panel import TARGET_ASSETS
from mds650.rp3.eval_inventory import assert_eval_session

ROOT: Final = Path(__file__).resolve().parents[1]

#: The acquirer's root IS the rp3 subtree; the batch adapter takes its configured parent
#: and reaches this subtree through its relative paths. The
#: composition is pinned by ``test_the_two_scripts_data_roots_compose``.
DEFAULT_DATA_ROOT: Final = provisional_data_root() / "rp3"

#: Bar acquisition universe: the six frozen targets plus the two market controls —
#: identical, by construction, to the eight-asset tape universe (`CANDIDATE_ASSETS`),
#: which `tests/unit/test_rp3_acquire_batch.py` pins.
BAR_ASSETS: Final = tuple(sorted((*TARGET_ASSETS, "SPY", "QQQ")))

#: The Phase 8 prospective cohort and its one-shot read date (decision 55; see
#: `docs/phase8_bridge_protocol_v2.md`). Sessions inside the cohort are sealed until
#: the read has both calendar-passed and been proven by the evaluator result.
PHASE8_COHORT_END: Final = date(2026, 8, 28)
PHASE8_READ_DATE: Final = date(2026, 8, 29)

#: NYSE full-closure holidays in the acquirable remainder of 2026. Early-close days
#: still trade and are acquired normally. Extend when the window reaches 2027.
MARKET_HOLIDAYS: Final = frozenset(
    {date(2026, 9, 7), date(2026, 11, 26), date(2026, 12, 25)}
)

GIB: Final = 1024**3


def _phase8_result_complete(path: Path | None) -> bool:
    """Accept only the self-hashed result emitted after the authorized bridge read."""

    if path is None:
        return False
    try:
        result = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("RP3_ACQUIRE_PHASE8_RESULT_INVALID") from error
    expected = {
        "status": "EXPLORATORY_BRIDGE_EVALUATION_COMPLETE",
        "claim_classification": "EXPLORATORY_DESCRIPTIVE_NOT_CONFIRMATORY",
        "protocol_id": "phase8a-exploratory-bridge-20of30-v2",
        "sealed_cohorts_read": 1,
        "confirmatory_promotion_allowed": False,
    }
    body = {key: value for key, value in result.items() if key != "result_sha256"}
    digest = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    if any(result.get(key) != value for key, value in expected.items()) or result.get(
        "result_sha256"
    ) != digest:
        raise ValueError("RP3_ACQUIRE_PHASE8_RESULT_INVALID")
    return True


class RP3StorageConfig(Phase5StorageConfig):
    """The Phase 5 storage contract, with the tape landing where the RP3 runbook says.

    Everything else — raw ZIP root, manifest root, bounded temporary root, the
    80 GiB free-space floor — is inherited unchanged, so `filter_session` and
    `storage_preflight` behave exactly as they did for every RP2 acquisition.
    """

    @property
    def event_root(self) -> Path:
        """Return the RP3 evaluation tape root the batch adapter discovers."""
        return self.data_root / "tape" / "full_tape_eval"


def _ny_today() -> date:
    """Today on the exchange's clock, not the machine's — see mds650.exchange_clock.

    A module-level indirection (rather than a bare import alias) so the tests can
    monkeypatch the clock at this seam, the way they always have.
    """

    return ny_today()


def business_days(start: date, end: date) -> list[date]:
    """Return the trading days in [start, end]: weekdays minus full-closure holidays."""

    days = []
    day = start
    while day <= end:
        if day.weekday() < 5 and day not in MARKET_HOLIDAYS:
            days.append(day)
        day += timedelta(days=1)
    return days


def _assert_acquirable(day: date, *, today: date, phase8_read_complete: bool) -> None:
    """All three session guards; raised, never filtered. Shared by planning and legs."""

    assert_eval_session(day.isoformat())
    if day >= today:
        raise ValueError(f"RP3_ACQUIRE_INCOMPLETE_SESSION:{day.isoformat()}")
    if day <= PHASE8_COHORT_END:
        if today <= PHASE8_READ_DATE:
            raise ValueError(
                f"RP3_ACQUIRE_PHASE8_SEALED:{day.isoformat()}: the Phase 8 cohort "
                f"(sessions through {PHASE8_COHORT_END.isoformat()}) is sealed until "
                f"its one-shot read on {PHASE8_READ_DATE.isoformat()} completes"
            )
        if not phase8_read_complete:
            raise ValueError(
                f"RP3_ACQUIRE_PHASE8_RESULT_REQUIRED:{day.isoformat()}: pass the "
                "self-hashed evaluator result with --phase8-result; an operator flag "
                "alone cannot prove that the authorized read completed"
            )


def plan_sessions(
    start: date,
    end: date,
    *,
    today: date,
    phase8_read_complete: bool,
) -> list[date]:
    """Enumerate and guard the batch's sessions; every refusal is an exception."""

    days = business_days(start, end)
    if not days:
        raise ValueError(f"RP3_ACQUIRE_NO_SESSIONS:{start.isoformat()}..{end.isoformat()}")
    for day in days:
        _assert_acquirable(day, today=today, phase8_read_complete=phase8_read_complete)
    return days


def _load_calibration() -> Any:  # a script module has no stub
    """Import the verified UW downloader script as a module, the way the suite does."""

    import importlib.util

    path = ROOT / "scripts" / "download_calibration_20d.py"
    spec = importlib.util.spec_from_file_location("download_calibration_20d", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_manifest(path: Path, record: dict[str, Any]) -> None:
    """Atomic write: an interrupted run leaves the previous manifest, never a torn one."""

    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_bytes((json.dumps(record, sort_keys=True, indent=2) + "\n").encode("utf-8"))
    os.replace(tmp, path)


def _reusable(manifest_path: Path) -> dict[str, Any] | None:
    """A PASS manifest, or None; a corrupt or unreadable manifest is just not reusable."""

    try:
        record: dict[str, Any] = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return record if isinstance(record, dict) and record.get("status") == "PASS" else None


def acquire_tape(
    days: list[date],
    config: RP3StorageConfig,
    *,
    phase8_read_complete: bool = False,
) -> list[dict[str, Any]]:
    """Download, validate and filter one full-tape ZIP per session, idempotently.

    Reuse is verified, not trusted: a PASS manifest is honored only while the ZIP it
    recorded still exists with the same SHA-256 — the same three-way check the
    verified downloader's own main() performs. A pre-existing ZIP that fails CRC
    validation is deleted and downloaded again once, so a corrupt partial file can
    never wedge its session. ``expected_fields`` follows the core's semantics: the
    first fresh session of a batch accepts any header that carries every required
    field, and later sessions must match it exactly (intra-batch schema stability).
    """

    calibration = _load_calibration()
    key = calibration._secret("UNUSUALWHALES_API_KEY")  # noqa: SLF001
    today = _ny_today()
    expected_fields: set[str] | None = None
    records = []
    for day in days:
        _assert_acquirable(day, today=today, phase8_read_complete=phase8_read_complete)
        manifest_path = config.manifest_root / f"{day.isoformat()}.json"
        zip_path = config.raw_root / day.isoformat() / f"full_tape_{day.isoformat()}.zip"
        reused = _reusable(manifest_path)
        if (
            reused is not None
            and zip_path.is_file()
            and _sha256(zip_path) == reused.get("zip_sha256")
        ):
            print(f"[tape] {day.isoformat()}: PASS (reused, zip verified)")
            records.append(reused)
            continue
        zip_path.parent.mkdir(parents=True, exist_ok=True)
        if zip_path.exists():
            # A leftover from an interrupted run: probe it once, discard if corrupt.
            try:
                calibration._validate_zip(zip_path, expected_fields)  # noqa: SLF001
            except Exception:
                zip_path.unlink()
        if not zip_path.exists():
            calibration._stream_download(day, key, zip_path)  # noqa: SLF001
        counters = calibration.filter_session(day, zip_path, expected_fields, config)
        if expected_fields is None and "schema_fields" in counters:
            expected_fields = set(counters["schema_fields"])
        record: dict[str, Any] = {
            "schema": "rp3_acquire_tape/1",
            "session": day.isoformat(),
            "zip_sha256": _sha256(zip_path),
            "status": "PASS",
            **counters,
        }
        _write_manifest(manifest_path, record)
        print(f"[tape] {day.isoformat()}: rows_retained={counters['rows_retained']}")
        records.append(record)
    return records


def _merge_bars(store: Path, fresh: pl.DataFrame) -> int:
    """Append fresh rows into the bar store, deduplicated and atomically replaced."""

    frames = [pl.read_parquet(store), fresh] if store.exists() else [fresh]
    combined = (
        pl.concat(frames, how="vertical")
        .unique(subset=["asset", "bar_start_utc"], keep="first")
        .sort("asset", "bar_start_utc")
    )
    store.parent.mkdir(parents=True, exist_ok=True)
    tmp = store.with_suffix(".parquet.tmp")
    combined.write_parquet(tmp)
    os.replace(tmp, store)
    return combined.height


def acquire_bars(
    days: list[date],
    data_root: Path,
    run_id: str,
    *,
    phase8_read_complete: bool = False,
    transport: Any = None,
) -> tuple[list[dict[str, Any]], Path]:
    """Acquire FMP 1-minute bars, one session per request per asset, idempotently.

    Reuse is anchored to the store as well as the manifest (the gate3 pattern): a
    PASS manifest is honored only while the store it fed still exists. A provider
    failure mid-session writes nothing — no manifest, no store rows — so the next
    run redoes the whole session cleanly.

    ``transport`` exists for the hermetic tests only: an ``httpx.MockTransport``
    exercises this whole leg — auth header, payload parsing, store append,
    manifest reuse — without a network byte. Production passes nothing.
    """

    api_key = os.environ.get("FMP_API_KEY") or os.environ.get("MDS650_FMP_API_KEY")
    if not api_key:
        raise RuntimeError("MISSING_SECRET:FMP_API_KEY")
    store = data_root / "data" / "fmp" / "underlying_1min_eval.parquet"
    manifest_root = data_root / "manifests" / "fmp_eval"
    today = _ny_today()
    provider = FMPProvider(api_key, transport=transport)
    records = []
    try:
        for day in days:
            iso = day.isoformat()
            _assert_acquirable(day, today=today, phase8_read_complete=phase8_read_complete)
            manifest_path = manifest_root / f"{iso}.json"
            reused = _reusable(manifest_path)
            if reused is not None and store.is_file():
                print(f"[bars] {iso}: PASS (reused, store present)")
                records.append(reused)
                continue
            frames = []
            rows_by_asset: dict[str, int] = {}
            for asset in BAR_ASSETS:
                response = provider.minute_bars(asset, from_date=iso, to_date=iso)
                bars = parse_minute_payload(
                    response.payload,
                    asset=asset,
                    run_id=run_id,
                    source_response_id=f"{run_id}:{asset}:{iso}",
                    source_timezone="America/New_York",
                )
                rows_by_asset[asset] = len(bars)
                if bars:
                    frames.append(
                        pl.DataFrame(
                            [
                                {
                                    "asset": bar.asset,
                                    "bar_start_utc": bar.bar_start_utc,
                                    "open": bar.open,
                                    "high": bar.high,
                                    "low": bar.low,
                                    "close": bar.close,
                                    "volume": bar.volume,
                                }
                                for bar in bars
                            ]
                        )
                    )
                time.sleep(0.15)
            if not frames:
                raise RuntimeError(f"RP3_ACQUIRE_EMPTY_SESSION:{iso}")
            store_rows = _merge_bars(store, pl.concat(frames, how="vertical"))
            record: dict[str, Any] = {
                "schema": "rp3_acquire_bars/1",
                "session": iso,
                "assets": list(BAR_ASSETS),
                "rows_by_asset": rows_by_asset,
                "store_rows_after": store_rows,
                "status": "PASS",
            }
            _write_manifest(manifest_path, record)
            total = sum(rows_by_asset.values())
            print(f"[bars] {iso}: {total} rows across {len(BAR_ASSETS)} assets")
            records.append(record)
    finally:
        provider.close()
    return records, store


def _default_end(today: date) -> date:
    """Return the last completed trading day strictly before today."""

    day = today - timedelta(days=1)
    while day.weekday() >= 5 or day in MARKET_HOLIDAYS:
        day -= timedelta(days=1)
    return day


def execute(arguments: argparse.Namespace, *, today: date) -> int:
    """The whole run with the clock injected, so every path is testable."""

    end = arguments.end if arguments.end is not None else _default_end(today)
    phase8_read_complete = _phase8_result_complete(getattr(arguments, "phase8_result", None))
    try:
        days = plan_sessions(
            arguments.start,
            end,
            today=today,
            phase8_read_complete=phase8_read_complete,
        )
    except ValueError as refusal:
        print(json.dumps({"status": "REFUSED", "error": str(refusal)}, indent=2))
        return 1

    config = RP3StorageConfig(
        sessions=tuple(days),
        excluded_dates=frozenset(),
        data_root=arguments.data_root,
        minimum_free_bytes=80 * GIB,
        projected_peak_additional_bytes=60 * GIB,
    )
    if arguments.dry_run:
        plan = {
            "status": "PLANNED",
            "sessions": [day.isoformat() for day in days],
            "bar_assets": list(BAR_ASSETS),
            "tape_root": str(config.event_root),
            "bar_store": str(arguments.data_root / "data" / "fmp" / "underlying_1min_eval.parquet"),
        }
        print(json.dumps(plan, indent=2, sort_keys=True))
        return 0

    # Both secrets must be present before the first network byte: the verified
    # downloader preflights its keys too, and discovering a missing FMP key only
    # after an hour of tape downloads would be a poor way to find out.
    if not (os.environ.get("FMP_API_KEY") or os.environ.get("MDS650_FMP_API_KEY")):
        raise RuntimeError("MISSING_SECRET:FMP_API_KEY")

    arguments.data_root.mkdir(parents=True, exist_ok=True)
    # The verified downloader's main() pre-creates its roots before the first session;
    # mirror that so a partial filesystem can never surprise the filter mid-stream.
    for root in (config.raw_root, config.event_root, config.manifest_root, config.temporary_root):
        root.mkdir(parents=True, exist_ok=True)
    capacity = storage_preflight(config)
    run_id = f"rp3_eval_{days[0].isoformat()}_{days[-1].isoformat()}"
    tape_records = acquire_tape(
        days, config, phase8_read_complete=phase8_read_complete
    )
    bar_records, store = acquire_bars(
        days,
        arguments.data_root,
        run_id,
        phase8_read_complete=phase8_read_complete,
    )
    store_sha = _sha256(store)
    summary: dict[str, Any] = {
        "schema": "rp3_acquire_summary/1",
        "acquired_at_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "run_id": run_id,
        "sessions": [day.isoformat() for day in days],
        "tape_sessions_pass": sum(1 for r in tape_records if r["status"] == "PASS"),
        "bar_sessions_pass": sum(1 for r in bar_records if r["status"] == "PASS"),
        "bar_store_sha256": store_sha,
        "storage_preflight": capacity,
    }
    _write_manifest(
        arguments.data_root / "manifests" / f"rp3_acquire_summary_{end.isoformat()}.json",
        summary,
    )
    print(f"batch {run_id}: {len(days)} sessions acquired, store sha256 {store_sha[:16]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA_ROOT)
    parser.add_argument("--start", type=date.fromisoformat, default=date(2026, 7, 20))
    parser.add_argument("--end", type=date.fromisoformat, default=None)
    parser.add_argument(
        "--phase8-result",
        type=Path,
        help="self-hashed result.json emitted by the authorized Phase 8 bridge evaluator",
    )
    parser.add_argument("--dry-run", action="store_true")
    arguments = parser.parse_args(argv)
    return execute(arguments, today=_ny_today())


if __name__ == "__main__":
    raise SystemExit(main())
