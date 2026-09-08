"""Target-blind daily acquisition into one new, explicitly configured private root."""

from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime
from functools import partial
from pathlib import Path
from typing import Any

for _thread_variable in (
    "OPENBLAS_NUM_THREADS",
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "POLARS_MAX_THREADS",
):
    os.environ[_thread_variable] = "2"

import acquire as legacy  # noqa: E402
import httpx  # noqa: E402
import polars as pl  # noqa: E402
from evaluate import write_bytes_once  # noqa: E402

from mds650.providers.fmp import FMPProvider, parse_minute_payload  # noqa: E402

TASK_NAME = "OptionsVolatility-Daily-Collection"
ASSETS = ("AAPL", "AMZN", "META", "MSFT", "NVDA", "TSLA", "SPY", "QQQ")
MINIMUM_FREE_BYTES = 100 * 1024**3


def load_config(path: Path, expected_sha256: str) -> dict[str, Any]:
    """Verify local configuration and source pins without reading any credentials."""
    if legacy.sha256(path) != expected_sha256:
        raise ValueError("DAILY_CONFIG_HASH_MISMATCH")
    config = json.loads(path.read_text(encoding="utf-8-sig"))
    if config["task_name"] != TASK_NAME or config["schema"] != "daily_collection_v1":
        raise ValueError("DAILY_CONFIG_IDENTITY_MISMATCH")
    repo = Path(config["repo_root"]).resolve()
    if Path(__file__).resolve() != repo / "artifacts/rp4_daily_collector_code/collector.py":
        raise ValueError("DAILY_CHECKOUT_MISMATCH")
    for relative, digest in config["source_sha256"].items():
        source = legacy.bound(repo / relative, repo)
        if legacy.sha256(source) != digest:
            raise ValueError("DAILY_SOURCE_PIN_MISMATCH")
    if Path(legacy.__file__).resolve() != repo / "artifacts/rp4_code/acquire.py":
        raise ValueError("DAILY_IMPORTED_ADAPTER_MISMATCH")
    root = Path(config["data_root"]).resolve()
    if root == Path(root.anchor) or root == repo or root.is_relative_to(repo):
        raise ValueError("DAILY_OUTPUT_ROOT_INVALID")
    return {**config, "config_sha256": expected_sha256}


def plan(now: datetime | None = None) -> dict[str, Any]:
    """Calendar-only plan: no filesystem mutation, secrets, models, or network."""
    current = now or datetime.now(UTC)
    day = legacy.latest_closed(current)
    return {
        "status": "DRY_RUN_NO_NETWORK",
        "session_date": day.isoformat(),
        "calendar": "XNYS",
        "session_timezone": "America/New_York",
        "close_utc": legacy.CALENDAR.session_close(str(day)).isoformat(),
        "close_grace_minutes": 30,
        "uw_full_tape_sessions": 1,
        "fmp_one_minute_assets": list(ASSETS),
        "credential_reads": 0,
        "network_requests": 0,
        "target_reads": 0,
        "model_fits": 0,
        "numeric_thread_limit": 2,
    }


def _write_json(root: Path, relative: str, payload: dict[str, Any]) -> Path:
    path: Path = legacy.bound(root / relative, root)
    write_bytes_once(path, (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode())
    return path


@contextmanager
def session_lock(root: Path, day: date) -> Iterator[None]:
    """Same nonblocking kernel-lock pattern as RP4, with an explicit new root."""
    path = legacy.bound(root / "locks" / f"{day}.lock", root)
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


def _file(root: Path, path: Path) -> dict[str, Any]:
    path = legacy.bound(path, root)
    return {
        "relative_path": path.relative_to(root).as_posix(),
        "sha256": legacy.sha256(path),
        "bytes": path.stat().st_size,
    }


def _reuse(root: Path, relative: str, config_sha256: str) -> dict[str, Any] | None:
    path = legacy.bound(root / relative, root)
    if not path.exists():
        return None
    record = json.loads(path.read_text())
    if record.get("status") != "PASS" or record.get("config_sha256") != config_sha256:
        raise ValueError("DAILY_RECEIPT_IDENTITY_MISMATCH")
    for item in record["files"]:
        source = legacy.bound(root / item["relative_path"], root)
        if source.stat().st_size != item["bytes"] or legacy.sha256(source) != item["sha256"]:
            raise ValueError("DAILY_COMPLETED_BYTES_CHANGED")
    return dict(record)


def _disk_space(root: Path) -> None:
    if shutil.disk_usage(root).free < MINIMUM_FREE_BYTES:
        raise RuntimeError("DAILY_INSUFFICIENT_FREE_SPACE")


def download_tape(root: Path, day: date) -> tuple[list[Path], dict[str, Any]]:
    """Small root-aware stream adapter; shared retry and ZIP validators are reused."""
    path = legacy.bound(root / f"raw/full_tape/{day}/full_tape_{day}.zip", root)
    if not path.exists():
        key = os.environ.get("UNUSUALWHALES_API_KEY")
        if not key:
            raise RuntimeError("DAILY_UW_CREDENTIAL_UNAVAILABLE")
        _disk_space(root)
        path.parent.mkdir(parents=True, exist_ok=True)
        partial = legacy.bound(path.with_suffix(".zip.part"), root)
        with (
            httpx.Client(timeout=httpx.Timeout(180, connect=30), follow_redirects=True) as client,
            client.stream(
                "GET",
                legacy.tape_core.ENDPOINT.format(day=str(day)),
                headers={"Authorization": f"Bearer {key}"},
            ) as response,
        ):
            response.raise_for_status()
            with partial.open("wb") as stream:
                for block in response.iter_bytes(8 * 1024**2):
                    _disk_space(root)
                    stream.write(block)
        legacy.tape_core._validate_zip(partial, None)  # noqa: SLF001
        partial.rename(path)
    member, fields, uncompressed = legacy.tape_core._validate_zip(path, None)  # noqa: SLF001
    return [path], {
        "crc_valid": True,
        "csv_member_count": 1,
        "fields_count": len(fields),
        "csv_uncompressed_bytes": uncompressed,
        "csv_member_name_recorded": bool(member),
        "row_level_quality": "NOT_EVALUATED_COLLECTION_ONLY",
        "open_interest_asof": "PROVIDER_OPAQUE_NO_ASOF_ASSERTION",
        "timing_status": "SOURCE_TIME_PROXY_NOT_CLIENT_AVAILABILITY_PROOF",
    }


def download_bars(root: Path, day: date, asset: str) -> tuple[list[Path], dict[str, Any]]:
    """Persist one bounded raw response and normalized observed regular-session bars."""
    if asset not in ASSETS:
        raise ValueError("DAILY_ASSET_NOT_ALLOWED")
    raw = legacy.bound(root / f"raw/fmp/{day}/{asset}.json", root)
    if raw.exists():
        payload = json.loads(raw.read_text())
    else:
        key = os.environ.get("FMP_API_KEY") or os.environ.get("MDS650_FMP_API_KEY")
        if not key:
            raise RuntimeError("DAILY_FMP_CREDENTIAL_UNAVAILABLE")
        provider = FMPProvider(key, max_retries=1)
        try:
            payload = provider.minute_bars(asset, from_date=str(day), to_date=str(day)).payload
        finally:
            provider.close()
    bars = parse_minute_payload(
        payload,
        asset=asset,
        run_id="options-volatility-daily",
        source_response_id=f"daily:{day}:{asset}",
        source_timezone="America/New_York",
    )
    opening = legacy.CALENDAR.session_open(str(day)).to_pydatetime()
    closing = legacy.CALENDAR.session_close(str(day)).to_pydatetime()
    rows: list[dict[str, Any]] = [
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
    if not rows or any(
        row["bar_start_utc"].second or row["bar_start_utc"].microsecond for row in rows
    ):
        raise ValueError("DAILY_REGULAR_MINUTE_BARS_INVALID")
    frame = pl.DataFrame(rows).sort("bar_start_utc")
    parquet = legacy.bound(root / f"data/fmp/date={day}/asset={asset}.parquet", root)
    _disk_space(root)
    write_bytes_once(raw, (json.dumps(payload, sort_keys=True) + "\n").encode())
    # Bytes are generated in memory for this bounded one-session, one-asset frame.
    import io

    buffer = io.BytesIO()
    frame.write_parquet(buffer)
    write_bytes_once(parquet, buffer.getvalue())
    expected = int((closing - opening).total_seconds() / 60)
    return [raw, parquet], {
        "rows": frame.height,
        "raw_rows": len(bars),
        "expected_minutes": expected,
        "missing_minutes": expected - frame.height,
        "coverage_fraction": frame.height / expected,
        "quality": "CANONICAL_SCHEMA_AND_UNIQUE_KEYS_NO_IMPUTATION",
        "complete_minute_coverage": frame.height == expected,
    }


def collect(config: dict[str, Any], now: datetime | None = None) -> dict[str, Any]:
    """One latest closed session only; successful components never download again."""
    planned = plan(now)
    day = date.fromisoformat(planned["session_date"])
    root = Path(config["data_root"]).resolve()
    marker = root / "collector_root.json"
    expected_marker = {"task_name": TASK_NAME, "config_sha256": config["config_sha256"]}
    if not marker.is_file() or json.loads(marker.read_text()) != expected_marker:
        raise ValueError("DAILY_PRIVATE_ROOT_NOT_INITIALIZED_BY_LAUNCHER")
    digest = config["config_sha256"]
    with session_lock(root, day):
        if previous := _reuse(root, f"manifests/sessions/{day}.json", digest):
            return {
                "status": "REUSED",
                "session_date": str(day),
                "network_requests": 0,
                "manifest_sha256": legacy.sha256(root / f"manifests/sessions/{day}.json"),
                "files_verified": len(previous["files"]),
            }
        jobs: list[tuple[str, Callable[[], tuple[list[Path], dict[str, Any]]]]] = [
            ("uw_tape", lambda: download_tape(root, day))
        ]
        for asset in ASSETS:
            jobs.append((f"fmp_{asset}", partial(download_bars, root, day, asset)))
        records = []
        for name, action in jobs:
            relative = f"manifests/components/{day}/{name}.json"
            attempts: list[dict[str, Any]] = []
            try:
                prior = _reuse(root, relative, digest)
                if prior is not None:
                    record = prior
                else:
                    paths, quality = legacy.retry(action, attempts)
                    record = {
                        "status": "PASS",
                        "session_date": str(day),
                        "component": name,
                        "config_sha256": digest,
                        "files": [_file(root, p) for p in paths],
                        "attempts": attempts,
                        "quality": quality,
                    }
                    _write_json(root, relative, record)
            except Exception as error:
                # Never persist exception strings, provider response bodies, headers or URLs.
                record = {
                    "status": "MISSING",
                    "component": name,
                    "error_type": type(error).__name__,
                    "attempts": attempts,
                }
            records.append(record)
        missing = [r["component"] for r in records if r["status"] != "PASS"]
        result = {
            "status": "PARTIAL" if missing else "PASS",
            "session_date": str(day),
            "config_sha256": digest,
            "records": records,
            "missing_components": missing,
            "files": [item for r in records for item in r.get("files", [])],
            "target_reads": 0,
            "model_fits": 0,
            "phase9_reads_or_writes": 0,
            "capital_go": False,
            "data_status": "PRIVATE_LICENSED_COLLECTION_ONLY",
        }
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        _write_json(root, f"operations/{day}/{stamp}.json", result)
        if not missing:
            _write_json(root, f"manifests/sessions/{day}.json", result)
        return {
            "status": result["status"],
            "session_date": str(day),
            "missing_components": missing,
            "target_reads": 0,
            "model_fits": 0,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--config-sha256", required=True)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--now", type=datetime.fromisoformat)
    args = parser.parse_args(argv)
    if args.now is not None and not args.dry_run:
        parser.error("--now is permitted only with --dry-run")
    logging.disable(logging.CRITICAL)
    try:
        config = load_config(args.config, args.config_sha256)
        result = plan(args.now) if args.dry_run else collect(config)
    except Exception as error:
        print(
            json.dumps(
                {
                    "status": "FAILED",
                    "error_type": type(error).__name__,
                    "details": "PRIVATE_LOCAL_DIAGNOSTIC_REQUIRED_NO_SECRET_OUTPUT",
                }
            )
        )
        return 2
    print(json.dumps(result, sort_keys=True))
    return 2 if result["status"] == "PARTIAL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
