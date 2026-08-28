"""Gate 5.2: +7-day reconciliation of live UW observations vs historical tape.

For every collected session at least ``RECONCILE_AFTER_DAYS`` old and not yet
reconciled, downloads the historical full tape for that session and verifies
that each live aggregate flow alert has supporting trades for the same option
contract inside the alert's time window. Receipt-minus-created_at remains an
operational latency proxy. The two channels cannot identify a backfill or
revision rate, so those metrics fail closed instead of comparing unlike rows.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import io
import json
import os
import zipfile
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import httpx
import numpy as np
import polars as pl

from mds650.config import effective_data_root

ASSETS = ("AAPL", "AMZN", "META", "MSFT", "NVDA", "TSLA")
NY = ZoneInfo("America/New_York")
RECONCILE_AFTER_DAYS = 7
TAPE_URL = "https://api.unusualwhales.com/api/option-trades/full-tape/{date}"


def _paths() -> tuple[Path, Path]:
    """Resolve operational roots on real work; module import and ``--help`` stay inert."""

    root = effective_data_root()
    return root / "uw_latency" / "sessions", root / "logs"


def _alert(message: str) -> None:
    _, logs = _paths()
    logs.mkdir(parents=True, exist_ok=True)
    with (logs / "UW_LATENCY_ALERT.txt").open("a", encoding="utf-8") as handle:
        handle.write(f"{dt.datetime.now(dt.UTC).isoformat()} {message}\n")
    print(f"[uw-reconcile] ALERT: {message}")


def _epoch_ms(value: Any) -> int | None:
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def _parse_timestamp(value: Any) -> dt.datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=dt.UTC)


def _download_tape(session: dt.date, api_key: str, destination: Path) -> Path:
    url = TAPE_URL.format(date=session.isoformat())
    with httpx.Client(timeout=600, follow_redirects=True) as client:
        response = client.get(url, headers={"Authorization": f"Bearer {api_key}"})
        response.raise_for_status()
        destination.write_bytes(response.content)
    return destination


def _tape_rows(zip_path: Path) -> Iterator[dict[str, Any]]:
    with zipfile.ZipFile(zip_path) as archive:
        for name in archive.namelist():
            with archive.open(name) as handle:
                text = io.TextIOWrapper(handle, encoding="utf-8")
                if name.lower().endswith(".csv"):
                    rows: Iterator[Any] = iter(csv.DictReader(text))
                    for row in rows:
                        if str(row.get("underlying_symbol") or "") in ASSETS:
                            yield row
                    continue
                first = text.read(1)
                text.seek(0)
                if first == "[":
                    rows = iter(json.load(text))
                else:
                    rows = (json.loads(line) for line in text if line.strip())
                for row in rows:
                    if isinstance(row, dict) and str(
                        row.get("underlying_symbol") or row.get("ticker_symbol") or ""
                    ) in ASSETS:
                        yield row


def _reconcile(session: dt.date, api_key: str) -> None:
    store, _ = _paths()
    session_dir = store / session.isoformat()
    observations_path = session_dir / "observations.jsonl"
    if not observations_path.exists():
        _alert(f"session {session}: no observations to reconcile")
        return
    session_start = dt.datetime.combine(session, dt.time.min, tzinfo=NY).astimezone(dt.UTC)
    session_end = session_start + dt.timedelta(days=1)
    live_total = 0
    live: dict[str, dict[str, Any]] = {}
    latencies: list[dict[str, Any]] = []
    with observations_path.open(encoding="utf-8") as handle:
        for line in handle:
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if row.get("kind") != "observation":
                continue
            live_total += 1
            record = row.get("record") or {}
            if not isinstance(record, dict):
                continue
            start_ms = _epoch_ms(record.get("start_time"))
            if start_ms is None:
                continue
            start_utc = dt.datetime.fromtimestamp(start_ms / 1000, tz=dt.UTC)
            if not session_start <= start_utc < session_end:
                continue
            record_id = str(record.get("id") or row.get("record_id") or "")
            contract = str(record.get("option_chain") or "")
            if not record_id or not contract:
                continue
            end_ms = _epoch_ms(record.get("end_time")) or start_ms
            live[record_id] = {
                "receipt_utc": row.get("receipt_utc"),
                "record": record,
                "contract": contract,
                "start_ms": start_ms,
                "end_ms": max(start_ms, end_ms),
            }
            created_utc = _parse_timestamp(record.get("created_at"))
            receipt_utc = _parse_timestamp(row.get("receipt_utc"))
            if created_utc is not None and receipt_utc is not None:
                latencies.append(
                    {
                        "asset": str(record.get("ticker") or row.get("asset") or ""),
                        "ny_hour": created_utc.astimezone(NY).hour,
                        "latency_seconds": (receipt_utc - created_utc).total_seconds(),
                    }
                )
    zip_path = session_dir / f"historical_tape_{session.isoformat()}.zip"
    if not zip_path.exists():
        try:
            _download_tape(session, api_key, zip_path)
        except httpx.HTTPError as error:
            _alert(
                f"session {session}: tape download failed: "
                f"{type(error).__name__}"
            )
            raise
    tape_count = 0
    windows: dict[str, list[tuple[int, int, str]]] = {}
    for record_id, observation in live.items():
        windows.setdefault(observation["contract"], []).append(
            (observation["start_ms"], observation["end_ms"], record_id)
        )
    supported: set[str] = set()
    for row in _tape_rows(zip_path):
        tape_count += 1
        candidates = windows.get(str(row.get("option_chain_id") or ""))
        if not candidates:
            continue
        executed = _parse_timestamp(row.get("executed_at"))
        if executed is None:
            continue
        executed_ms = int(executed.timestamp() * 1000)
        for start_ms, end_ms, record_id in candidates:
            if start_ms <= executed_ms <= end_ms:
                supported.add(record_id)
    summary: dict[str, Any] = {
        "session": session.isoformat(),
        "reconciled_utc": dt.datetime.now(dt.UTC).isoformat(),
        "status": "PROXY_ONLY_CROSS_CHANNEL",
        "tape_rows_outcome_assets": tape_count,
        "live_observations_total": live_total,
        "live_flow_alerts_in_session": len(live),
        "live_observations_out_of_session": live_total - len(live),
        "flow_alerts_with_tape_support": len(supported),
        "unmatched_flow_alerts": len(live) - len(supported),
        "flow_alert_tape_support_rate": len(supported) / len(live) if live else None,
        "backfill_upper_bound_rate": None,
        "backfill_rate_reason": "CROSS_CHANNEL_NOT_IDENTIFIABLE",
        "revision_rate_among_matched": None,
        "revision_rate_reason": "AGGREGATE_ALERT_VS_INDIVIDUAL_TRADE_NOT_COMPARABLE",
        "note": (
            "flow-alerts contains aggregate alerts while full tape contains individual trades; "
            "contract-window support is measurable, backfill and revision rates are not"
        ),
    }
    if latencies:
        frame = pl.DataFrame(latencies)
        latency_values = frame["latency_seconds"].to_numpy()
        summary["latency_seconds_quantiles"] = {
            str(quantile): float(np.quantile(latency_values, quantile))
            for quantile in (0.1, 0.5, 0.9, 0.99)
        }
        summary["latency_by_asset_median"] = {
            str(asset[0]): float(np.median(group["latency_seconds"].to_numpy()))
            for asset, group in frame.group_by("asset")
        }
    (session_dir / "reconciliation.json").write_text(
        json.dumps(summary, indent=1), encoding="utf-8"
    )
    print(
        f"[uw-reconcile] {session}: tape support for {len(supported)}/{len(live)} "
        "in-session flow alerts; report written"
    )


def main(argv: list[str] | None = None) -> None:
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    store, _ = _paths()
    api_key = os.environ.get("UNUSUAL_WHALES_API_KEY") or os.environ.get("UNUSUALWHALES_API_KEY")
    if not api_key:
        _alert("RECONCILE_CREDENTIALS_MISSING")
        raise SystemExit(1)
    if not store.exists():
        print("[uw-reconcile] no sessions collected yet")
        return
    today = dt.datetime.now(NY).date()
    for session_dir in sorted(store.iterdir()):
        if not session_dir.is_dir():
            continue
        session = dt.date.fromisoformat(session_dir.name)
        age = (today - session).days
        if age >= RECONCILE_AFTER_DAYS and not (session_dir / "reconciliation.json").exists():
            try:
                _reconcile(session, api_key)
            except Exception as error:
                _alert(f"session {session}: reconciliation failed: {type(error).__name__}")
                raise


if __name__ == "__main__":
    main()
