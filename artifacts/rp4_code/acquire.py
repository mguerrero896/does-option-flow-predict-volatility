"""Bounded RP4 acquisition: new roots only, immutable receipts, no Phase 9 writes."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import time
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, date, datetime, timedelta
from functools import lru_cache, partial
from pathlib import Path
from typing import Any

import download_calibration_20d as tape_core
import exchange_calendars as xcals  # type: ignore[import-untyped]
import httpx
import polars as pl
from evaluate import write_bytes_once

from mds650.b1q_exogenous_provenance_v1 import parse_treasury_yield_curve_xml
from mds650.phase5_storage import Phase5StorageConfig
from mds650.providers.fmp import FMPProvider, parse_earnings_payload, parse_minute_payload

REPO = Path(__file__).resolve().parents[2]
ROOT = Path("private-input/66c0e77362caa29dd928")
PHASE9 = Path("private-input/ec845f87196cb7f24b60")
ASSETS = ("AAPL", "AMZN", "META", "MSFT", "NVDA", "TSLA", "SPY", "QQQ")
SPEC = REPO / "artifacts/rp4_a1/specification.json"
CALENDAR = xcals.get_calendar("XNYS")
CODE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def sha256(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def write_receipt(path: Path, payload: dict[str, Any]) -> dict[str, Any]:
    """Exclusive output; a completed receipt is never replaced on a retry."""
    payload = {"acquire_code_sha256": CODE_SHA256, **payload}
    write_bytes_once(
        path, (json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n").encode()
    )
    return payload


def bound(path: Path, root: Path | None = None) -> Path:
    root = ROOT if root is None else root
    resolved = path.resolve()
    if resolved == root.resolve() or not resolved.is_relative_to(root.resolve()):
        raise ValueError("RP4_OUTPUT_OUTSIDE_NEW_ROOT")
    return resolved


def authorization(spec_hash: str) -> None:
    if len(spec_hash) != 64 or sha256(SPEC) != spec_hash:
        raise ValueError("RP4_SPEC_HASH_MISMATCH")
    metadata = json.loads(SPEC.read_text(encoding="utf-8"))
    if sha256(REPO / "docs/rp4/specification_v1.md") != metadata["specification_md_sha256"]:
        raise ValueError("RP4_SPEC_MARKDOWN_HASH_MISMATCH")


def sessions(start: date, end: date) -> list[date]:
    return [stamp.date() for stamp in CALENDAR.sessions_in_range(start, end)]


def latest_closed(now: datetime | None = None) -> date:
    """Respect actual exchange close, including early closes, plus 30 minutes."""
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        raise ValueError("RP4_CLOCK_TIMEZONE_REQUIRED")
    days = sessions(current.date() - timedelta(days=10), current.date())
    for day in reversed(days):
        close = CALENDAR.session_close(day.isoformat()).to_pydatetime()
        if current >= close + timedelta(minutes=30):
            return day
    raise RuntimeError("RP4_NO_CLOSED_SESSION")


def retry[T](call: Callable[[], T], attempts: list[dict[str, Any]]) -> T:
    """Five total attempts, sanitized errors and exponential backoff."""
    for number in range(1, 6):
        try:
            result = call()
        except Exception as error:  # each missing session must not stop other sessions
            attempts.append({"attempt": number, "error_type": type(error).__name__})
            if number == 5:
                raise
            time.sleep(2 ** (number - 1))
        else:
            attempts.append({"attempt": number, "status": "PASS"})
            return result
    raise AssertionError("UNREACHABLE")


def _reuse(receipt: Path, spec_hash: str) -> dict[str, Any] | None:
    if not receipt.exists():
        return None
    record = json.loads(receipt.read_text(encoding="utf-8"))
    if record.get("status") != "PASS" or record.get("spec_sha256") != spec_hash:
        raise ValueError("RP4_COMPLETED_RECEIPT_INVALID")
    for item in record["files"]:
        path = bound(Path(item["path"]))
        if not path.is_file() or sha256(path) != item["sha256"]:
            raise ValueError("RP4_REUSE_HASH_MISMATCH")
    return dict(record)


def file_record(path: Path) -> dict[str, Any]:
    return {"path": str(path), "sha256": sha256(path), "bytes": path.stat().st_size}


@lru_cache(maxsize=64)
def regular_bounds(day: date) -> tuple[datetime, datetime]:
    session = tape_core.XNYS.date_to_session(day.isoformat())
    return (
        tape_core.XNYS.session_open(session).to_pydatetime(),
        tape_core.XNYS.session_close(session).to_pydatetime(),
    )


def regular_cached(timestamp: datetime, day: date) -> bool:
    """Identical calendar predicate; avoid two calendar lookups for every trade."""
    opening, closing = regular_bounds(day)
    return bool(opening <= timestamp.astimezone(UTC) < closing)


def space() -> None:
    if shutil.disk_usage(ROOT.parent).free < 100 * 1024**3:
        raise RuntimeError("RP4_DISK_BELOW_100_GIB_NEEDS_SCOPED_CACHE_CLEANUP")


def copy_phase9(day: date, spec_hash: str) -> dict[str, Any]:
    authorization(spec_hash)
    source = PHASE9 / day.isoformat()
    output = ROOT / "phase9_copies" / day.isoformat()
    receipt = ROOT / "manifests/phase9_copy" / f"{day}.json"
    if prior := _reuse(receipt, spec_hash):
        return prior
    if not source.is_dir():
        raise FileNotFoundError("RP4_PHASE9_SESSION_ABSENT")
    manifest = source / "session_manifest.json"
    claims = json.loads(manifest.read_text()).get("sha256", {}) if manifest.exists() else {}
    files = []
    for path in sorted(source.iterdir()):
        if not path.is_file() or path.is_symlink():
            raise ValueError("RP4_PHASE9_UNEXPECTED_PATH")
        before = sha256(path)
        if path.name in claims and claims[path.name] != before:
            raise ValueError("RP4_PHASE9_SOURCE_HASH_MISMATCH")
        target = bound(output / path.name)
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            if sha256(target) != before:
                raise ValueError("RP4_EXISTING_COPY_MISMATCH")
        else:
            space()
            partial = bound(target.with_suffix(target.suffix + ".copy.part"))
            with path.open("rb") as incoming, partial.open("wb") as outgoing:
                shutil.copyfileobj(incoming, outgoing, length=8 * 1024**2)
            if sha256(partial) != before:
                raise ValueError("RP4_COPY_PARTIAL_HASH_MISMATCH")
            partial.rename(target)
        if sha256(target) != before or sha256(path) != before:
            raise ValueError("RP4_COPY_CUSTODY_MISMATCH")
        files.append({**file_record(target), "source": str(path), "source_sha256": before})
    return write_receipt(
        receipt,
        {
            "status": "PASS",
            "session": str(day),
            "spec_sha256": spec_hash,
            "source_manifest_present": manifest.exists(),
            "files": files,
        },
    )


def _download_tape(day: date, path: Path) -> dict[str, Any]:
    key = os.environ.get("UNUSUALWHALES_API_KEY")
    if not key:
        raise RuntimeError("RP4_UW_SECRET_ABSENT")
    space()
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = bound(path.with_suffix(".zip.part"))
    with (
        httpx.Client(timeout=httpx.Timeout(180, connect=30), follow_redirects=True) as client,
        client.stream(
            "GET",
            tape_core.ENDPOINT.format(day=day.isoformat()),
            headers={"Authorization": f"Bearer {key}"},
        ) as response,
    ):
        response.raise_for_status()
        with partial.open("wb") as handle:
            for block in response.iter_bytes(8 * 1024**2):
                handle.write(block)
    tape_core._validate_zip(partial, None)  # noqa: SLF001
    if path.exists():
        raise ValueError("RP4_TAPE_ALREADY_PRESENT")
    partial.rename(path)
    return {"http_status": response.status_code, "endpoint": tape_core.ENDPOINT}


def reuse_local_tape(day: date, spec_hash: str) -> dict[str, Any] | None:
    """Reuse known local full archives by exact bytes before another provider call."""
    authorization(spec_hash)
    receipt = ROOT / "manifests/local_tape_copy" / f"{day}.json"
    if prior := _reuse(receipt, spec_hash):
        return prior
    source = Path(f"private-input/11eabcc4192384c90f68")
    if not source.is_file():
        return None
    before = sha256(source)
    target = bound(ROOT / "raw/full_tape" / str(day) / f"full_tape_{day}.zip")
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        if sha256(target) != before:
            raise ValueError("RP4_LOCAL_TAPE_COPY_CONFLICT")
    else:
        space()
        partial = bound(target.with_suffix(".zip.copy.part"))
        with source.open("rb") as incoming, partial.open("wb") as outgoing:
            shutil.copyfileobj(incoming, outgoing, length=8 * 1024**2)
        if sha256(partial) != before or sha256(source) != before:
            raise ValueError("RP4_LOCAL_TAPE_SOURCE_CHANGED")
        partial.rename(target)
    return write_receipt(
        receipt,
        {
            "status": "PASS",
            "spec_sha256": spec_hash,
            "session": str(day),
            "files": [file_record(target)],
            "source": str(source),
            "source_sha256": before,
            "crc_and_schema_validation": "required_at_filter_session_before_materialized_PASS",
        },
    )


def acquire_tape(day: date, spec_hash: str, *, allow_download: bool) -> dict[str, Any]:
    """All callers share one kernel lock per day; process exit releases the lock."""
    authorization(spec_hash)
    with tape_lock(day):
        return _acquire_tape_locked(day, spec_hash, allow_download=allow_download)


@contextmanager
def tape_lock(day: date) -> Iterator[None]:
    path = bound(ROOT / "tmp/locks" / f"uw_{day}.lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        handle.seek(0)
        if not handle.read(1):
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        if sys.platform == "win32":
            import msvcrt

            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            yield
        finally:
            handle.seek(0)
            if sys.platform == "win32":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _acquire_tape_locked(day: date, spec_hash: str, *, allow_download: bool) -> dict[str, Any]:
    authorization(spec_hash)
    receipt = ROOT / "manifests/tape" / f"{day}.json"
    if prior := _reuse(receipt, spec_hash):
        return prior
    config = Phase5StorageConfig(
        (day,),
        frozenset(),
        ROOT,
        100 * 1024**3,
        2 * 1024**3,
    )
    copied = ROOT / "phase9_copies" / day.isoformat() / f"full_tape_{day}.zip"
    path = copied if copied.is_file() else config.raw_root / str(day) / f"full_tape_{day}.zip"
    if not path.exists():
        reuse_local_tape(day, spec_hash)
    if not path.exists():
        if not allow_download:
            raise FileNotFoundError("RP4_LOCAL_PHASE9_TAPE_ABSENT")
        _download_tape(day, path)
    original_regular = tape_core._regular
    try:
        # Only the immutable calendar lookup is cached; parser and all row gates are unchanged.
        tape_core._regular = regular_cached
        counters = tape_core.filter_session(day, path, None, config)
    finally:
        tape_core._regular = original_regular
    files = [file_record(path)] + [
        file_record(part)
        for part in sorted(config.event_root.glob(f"date={day}/asset=*/*.parquet"))
    ]
    return write_receipt(
        receipt,
        {
            "status": "PASS",
            "session": str(day),
            "spec_sha256": spec_hash,
            "source": "phase9_hash_copy" if copied == path else "uw_full_tape",
            "files": files,
            "quality": counters,
            "open_interest_asof": "provider_opaque_no_asof_field",
        },
    )


def acquire_bars(day: date, asset: str, spec_hash: str) -> dict[str, Any]:
    authorization(spec_hash)
    receipt = ROOT / "manifests/fmp" / str(day) / f"{asset}.json"
    if prior := _reuse(receipt, spec_hash):
        return prior
    key = os.environ.get("FMP_API_KEY") or os.environ.get("MDS650_FMP_API_KEY")
    if not key:
        raise RuntimeError("RP4_FMP_SECRET_ABSENT")
    provider = FMPProvider(key, max_retries=1)
    try:
        response = provider.minute_bars(asset, from_date=str(day), to_date=str(day))
    finally:
        provider.close()
    bars = parse_minute_payload(
        response.payload,
        asset=asset,
        run_id="rp4_20260907",
        source_response_id=f"rp4:{day}:{asset}",
        source_timezone="America/New_York",
    )
    if not bars:
        raise ValueError("RP4_FMP_EMPTY_SESSION")
    opening = CALENDAR.session_open(str(day)).to_pydatetime()
    closing = CALENDAR.session_close(str(day)).to_pydatetime()
    rows = [
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
        if opening <= bar.bar_start_utc < closing
    ]
    if not rows:
        raise ValueError("RP4_FMP_NO_REGULAR_BARS")
    frame = pl.DataFrame(rows).sort("bar_start_utc")
    path = bound(ROOT / "data/fmp" / f"date={day}" / f"asset={asset}.parquet")
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = bound(path.with_suffix(".parquet.part"))
    frame.write_parquet(partial)
    if path.exists():
        if sha256(path) != sha256(partial):
            raise ValueError("RP4_FMP_UNRECEIPTED_OUTPUT_DIFFERS")
        partial.unlink()
    else:
        partial.rename(path)
    return write_receipt(
        receipt,
        {
            "status": "PASS",
            "session": str(day),
            "asset": asset,
            "spec_sha256": spec_hash,
            "files": [file_record(path)],
            "rows": frame.height,
            "expected_minutes": int((closing - opening).total_seconds() / 60),
            "raw_rows": len(bars),
            "http_status": response.status_code,
            "quality": "canonical_normalizer_no_imputation_unique_keys",
        },
    )


def acquire_treasury(year: int, spec_hash: str) -> dict[str, Any]:
    authorization(spec_hash)
    if year not in (2024, 2026):
        raise ValueError("RP4_TREASURY_UNAUTHORIZED_YEAR")
    receipt = ROOT / f"manifests/treasury_{year}.json"
    if prior := _reuse(receipt, spec_hash):
        return prior
    path = bound(ROOT / f"raw/exogenous/treasury_{year}.xml")
    url = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml"
    with httpx.Client(timeout=90, follow_redirects=True) as client:
        response = client.get(
            url,
            params={
                "data": "daily_treasury_yield_curve",
                "field_tdr_date_value": str(year),
            },
        )
        response.raise_for_status()
    rates = parse_treasury_yield_curve_xml(response.content)
    if not rates or any(not stamp.startswith(f"{year}-") for stamp in rates):
        raise ValueError("RP4_TREASURY_YEAR_INVALID")
    old_path = Path(f"private-input/be33a52a4d6b4b0d9eee")
    old = parse_treasury_yield_curve_xml(old_path.read_bytes()) if old_path.is_file() else {}
    changes = {
        stamp: {"old": old[stamp], "new": rates[stamp]}
        for stamp in old.keys() & rates.keys()
        if old[stamp] != rates[stamp]
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if sha256(path) != hashlib.sha256(response.content).hexdigest():
            raise ValueError("RP4_TREASURY_UNRECEIPTED_OUTPUT_DIFFERS")
    else:
        with path.open("xb") as handle:
            handle.write(response.content)
    return write_receipt(
        receipt,
        {
            "status": "PASS",
            "spec_sha256": spec_hash,
            "files": [file_record(path)],
            "http_status": response.status_code,
            "rate_dates": len(rates),
            "source_url": str(response.url),
            "old_source": file_record(old_path) if old_path.is_file() else None,
            "overlap_rate_changes": changes,
        },
    )


def _new_bytes(path: Path, content: bytes) -> None:
    path = bound(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if sha256(path) != hashlib.sha256(content).hexdigest():
            raise ValueError("RP4_EXISTING_RAW_BYTES_DIFFER")
    else:
        with path.open("xb") as handle:
            handle.write(content)


def acquire_dividends(asset: str, spec_hash: str) -> dict[str, Any]:
    """Refresh a real exogenous input in RP4, never modify the A2 source snapshot."""
    authorization(spec_hash)
    if asset not in ASSETS[:6]:
        raise ValueError("RP4_DIVIDEND_ASSET_NOT_REGISTERED")
    receipt = ROOT / "manifests/dividends" / f"{asset}.json"
    if prior := _reuse(receipt, spec_hash):
        return prior
    key = os.environ.get("FMP_API_KEY") or os.environ.get("MDS650_FMP_API_KEY")
    if not key:
        raise RuntimeError("RP4_FMP_SECRET_ABSENT")
    url = "https://financialmodelingprep.com/stable/dividends"
    with httpx.Client(timeout=90, follow_redirects=True) as client:
        response = client.get(url, params={"symbol": asset}, headers={"apikey": key})
        response.raise_for_status()
    payload = response.json()
    if not isinstance(payload, list) or not all(isinstance(row, dict) for row in payload):
        raise ValueError("RP4_DIVIDEND_SCHEMA_INVALID")
    path = ROOT / "raw/exogenous" / f"dividends_{asset}.json"
    _new_bytes(path, response.content)
    return write_receipt(
        receipt,
        {
            "status": "PASS",
            "spec_sha256": spec_hash,
            "asset": asset,
            "files": [file_record(path)],
            "source_url": url,
            "rows": len(payload),
            "http_status": response.status_code,
            "captured_utc": datetime.now(UTC).isoformat(),
            "old_source_unchanged": True,
            "used_for": "B1_extension_only_not_A2_rewrite",
        },
    )


def acquire_earnings(asset: str, spec_hash: str) -> dict[str, Any]:
    authorization(spec_hash)
    if asset not in ASSETS[:6]:
        raise ValueError("RP4_EARNINGS_UNAUTHORIZED_ASSET")
    receipt = ROOT / "manifests/events" / f"earnings_{asset}.json"
    if prior := _reuse(receipt, spec_hash):
        return prior
    key = os.environ.get("FMP_API_KEY") or os.environ.get("MDS650_FMP_API_KEY")
    if not key:
        raise RuntimeError("RP4_FMP_SECRET_ABSENT")
    provider = FMPProvider(key, max_retries=1)
    try:
        response = provider.earnings(asset)
    finally:
        provider.close()
    raw_path = ROOT / "raw/events" / f"earnings_{asset}.json"
    encoded = (json.dumps(response.payload, sort_keys=True) + "\n").encode()
    _new_bytes(raw_path, encoded)
    events = parse_earnings_payload(
        response.payload,
        run_id="rp4_20260907",
        source_response_id=f"rp4:earnings:{asset}",
    )
    if any(event.asset != asset for event in events):
        raise ValueError("RP4_EARNINGS_SYMBOL_MISMATCH")
    retained = sorted(
        {
            str(event.event_date_ny)
            for event in events
            if event.event_date_ny is not None
            and date(2024, 8, 2) <= event.event_date_ny <= date(2026, 9, 4)
        }
    )
    if not retained:
        raise ValueError("RP4_EARNINGS_WINDOW_EMPTY")
    return write_receipt(
        receipt,
        {
            "status": "PASS",
            "spec_sha256": spec_hash,
            "files": [file_record(raw_path)],
            "asset": asset,
            "event_type": "earnings",
            "session_dates": retained,
            "source_url": response.request_url,
            "event_timestamp_quality": "date_only",
            "not_a_predictor": True,
            "raw_record_count": len(events),
        },
    )


def fomc_dates(html: str) -> list[str]:
    """Meeting Statement blocks, excluding minutes and notation-only goal votes."""
    blocks = re.findall(r"<strong>Statement:</strong>(.*?)</div>", html, flags=re.DOTALL)
    stamps = re.findall(
        r"/newsevents/pressreleases/monetary(20\d{6})a\.htm",
        "\n".join(blocks),
    )
    dates = sorted(
        {
            str(datetime.strptime(stamp, "%Y%m%d").date())
            for stamp in stamps
            if "20240802" <= stamp <= "20260904"
        }
    )
    if not dates or {stamp[:4] for stamp in dates} != {"2024", "2025", "2026"}:
        raise ValueError("RP4_FOMC_CALENDAR_INCOMPLETE")
    return dates


def acquire_fomc(spec_hash: str) -> dict[str, Any]:
    authorization(spec_hash)
    receipt = ROOT / "manifests/events/fomc_meetings_v1.json"
    if prior := _reuse(receipt, spec_hash):
        return prior
    url = "https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm"
    path = ROOT / "raw/events/fomccalendars.html"
    if not path.exists():
        with httpx.Client(timeout=60, follow_redirects=True) as client:
            response = client.get(url)
            response.raise_for_status()
        _new_bytes(path, response.content)
    html = path.read_text(encoding="utf-8")
    dates = fomc_dates(html)
    all_stamps = re.findall(r"/newsevents/pressreleases/monetary(20\d{6})a\.htm", html)
    old_dates = {
        str(datetime.strptime(stamp, "%Y%m%d").date())
        for stamp in all_stamps
        if "20240802" <= stamp <= "20260904"
    }
    return write_receipt(
        receipt,
        {
            "status": "PASS",
            "spec_sha256": spec_hash,
            "files": [file_record(path)],
            "event_type": "FOMC",
            "session_dates": dates,
            "source_url": url,
            "definition": "calendar_meeting_Statement_block_release_day_not_minutes_or_notation",
            "excluded_nonmeeting_links": sorted(old_dates - set(dates)),
            "supersedes_date_selection_only": "manifests/events/fomc.json",
            "not_a_predictor": True,
        },
    )


def run_job(job: tuple[str, Callable[[], dict[str, Any]]]) -> dict[str, Any]:
    name, call = job
    attempts: list[dict[str, Any]] = []
    try:
        result = retry(call, attempts)
    except Exception as error:
        result = {"status": "MISSING", "error_type": type(error).__name__}
        if str(error).startswith("RP4_"):
            result["reason_code"] = str(error)
        if isinstance(error, httpx.HTTPStatusError):
            result["http_status"] = error.response.status_code
    record = {"job": name, "attempts": attempts, **result}
    print(json.dumps({"job": name, "status": record["status"]}), flush=True)
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec-hash", required=True)
    parser.add_argument("--mode", choices=("batch", "daily"), default="batch")
    parser.add_argument(
        "--leg",
        choices=("all", "bars", "tape", "copy", "treasury", "events", "dividends"),
        default="all",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--tape-group", choices=("all", "requested", "copied"), default="all")
    parser.add_argument("--tape-sessions", nargs="+", type=date.fromisoformat)
    args = parser.parse_args()
    authorization(args.spec_hash)
    if args.mode == "batch":
        bar_days = sessions(date(2026, 7, 20), date(2026, 9, 4))
        download_days = set(sessions(date(2026, 8, 3), date(2026, 8, 18))) | {
            date(2026, 8, 26),
            date(2026, 9, 3),
            date(2026, 9, 4),
        }
        phase9_days = sessions(date(2026, 8, 19), date(2026, 9, 2))
    else:
        bar_days = [latest_closed()]
        download_days = set(bar_days)
        phase9_days = []
    tape_days = sorted(download_days | set(phase9_days))
    if args.tape_group == "requested":
        tape_days = sorted(download_days - set(phase9_days))
    elif args.tape_group == "copied":
        tape_days = sorted(set(phase9_days))
    if args.tape_sessions is not None:
        if set(args.tape_sessions) - set(tape_days):
            raise ValueError("RP4_TAPE_SUBSET_OUTSIDE_AUTHORIZED_WINDOW")
        tape_days = sorted(set(args.tape_sessions))
    if args.dry_run:
        print(
            json.dumps(
                {
                    "status": "PLANNED_ONLY",
                    "bars": len(bar_days) * len(ASSETS),
                    "uw_download_sessions": sorted(map(str, download_days)),
                    "phase9_copy_sessions": list(map(str, phase9_days)),
                    "data_root": str(ROOT),
                    "tape_group": args.tape_group,
                    "tape_sessions": list(map(str, tape_days)),
                },
                indent=2,
            )
        )
        return 0
    ROOT.mkdir(parents=True, exist_ok=True)
    jobs: list[tuple[str, Callable[[], dict[str, Any]]]] = []
    if args.leg in {"all", "dividends"}:
        jobs.extend(
            (f"dividends:{asset}", partial(acquire_dividends, asset, args.spec_hash))
            for asset in ASSETS[:6]
        )
    if args.leg in {"all", "treasury"}:
        jobs.extend(
            (f"treasury_{year}", partial(acquire_treasury, year, args.spec_hash))
            for year in (2024, 2026)
        )
    if args.leg in {"all", "events"}:
        jobs.append(("fomc", partial(acquire_fomc, args.spec_hash)))
        jobs.extend(
            (f"earnings:{asset}", partial(acquire_earnings, asset, args.spec_hash))
            for asset in ASSETS[:6]
        )
    if args.leg in {"all", "bars"}:
        jobs.extend(
            (f"fmp:{day}:{asset}", partial(acquire_bars, day, asset, args.spec_hash))
            for day in bar_days
            for asset in ASSETS
        )
    results: list[dict[str, Any]] = []
    if jobs:
        with ThreadPoolExecutor(max_workers=2) as executor:
            results.extend(executor.map(run_job, jobs))
    copy_jobs: list[tuple[str, Callable[[], dict[str, Any]]]] = []
    if args.leg in {"all", "tape", "copy"}:
        copy_jobs = [
            (f"phase9:{day}", partial(copy_phase9, day, args.spec_hash)) for day in phase9_days
        ]
        results.extend(map(run_job, copy_jobs))
    tape_jobs: list[tuple[str, Callable[[], dict[str, Any]]]] = []
    if args.leg in {"all", "tape"}:
        tape_jobs = [
            (
                f"uw:{day}",
                partial(acquire_tape, day, args.spec_hash, allow_download=day in download_days),
            )
            for day in tape_days
        ]
        results.extend(map(run_job, tape_jobs))
    by_name = dict(jobs + copy_jobs + tape_jobs)
    failed = [record for record in results if record["status"] != "PASS"]
    final_retries = [run_job((record["job"], by_name[record["job"]])) for record in failed]
    final = {record["job"]: record for record in results + final_retries}
    missing = sorted(name for name, record in final.items() if record["status"] != "PASS")
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    path = ROOT / "manifests" / f"acquisition_{args.mode}_{args.leg}_{stamp}.json"
    payload = {
        "status": "PARTIAL" if missing else "PASS",
        "spec_sha256": args.spec_hash,
        "mode": args.mode,
        "leg": args.leg,
        "tape_group": args.tape_group,
        "tape_session_allowlist": list(map(str, tape_days)),
        "missing": missing,
        "records": results,
        "final_retries": final_retries,
        "phase9_modified": False,
        "collector_only_no_model_refits": True,
        "capital_go": False,
    }
    write_receipt(path, payload)
    print(
        json.dumps(
            {
                "summary": str(path),
                "sha256": sha256(path),
                "status": payload["status"],
                "missing": missing,
            }
        ),
        flush=True,
    )
    return 2 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
