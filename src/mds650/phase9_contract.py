"""Pure Phase 9 calendar and manifest contract shared by collector and verifier."""

from __future__ import annotations

import datetime as dt
import json
import re
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import exchange_calendars  # type: ignore[import-untyped]

ASSETS = ("AAPL", "AMZN", "META", "MSFT", "NVDA", "TSLA")
NY = ZoneInfo("America/New_York")
WINDOW_START = dt.date(2026, 8, 19)
TARGET_SESSIONS = 60
SHA256 = re.compile(r"^[0-9a-f]{64}$")


def last_checkpoint(session_dir: Path) -> str | None:
    path = session_dir / "collector_checkpoint.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "unreadable"
    stage = payload.get("stage") if isinstance(payload, dict) else None
    stamp = payload.get("utc") if isinstance(payload, dict) else None
    return f"{stage} at {stamp}" if isinstance(stage, str) and isinstance(stamp, str) else "invalid"


def last_closed_session(now: dt.datetime | None = None) -> dt.date | None:
    """Return the latest XNYS session whose close is at least 30 minutes old."""

    calendar = exchange_calendars.get_calendar("XNYS")
    probe = now.astimezone(NY) if now is not None else dt.datetime.now(NY)
    for offset in range(7):
        day = probe.date() - dt.timedelta(days=offset)
        if calendar.is_session(day.isoformat()):
            close_ny = dt.datetime.combine(day, dt.time(16, 0), tzinfo=NY)
            if probe > close_ny + dt.timedelta(minutes=30):
                return day
    return None


def origins_utc(session: dt.date) -> list[dt.datetime]:
    origins: list[dt.datetime] = []
    cursor = dt.datetime.combine(session, dt.time(10, 0), tzinfo=NY)
    end = dt.datetime.combine(session, dt.time(15, 30), tzinfo=NY)
    while cursor <= end:
        origins.append(cursor.astimezone(dt.UTC))
        cursor += dt.timedelta(minutes=5)
    return origins


def capture_problems(manifest: dict[str, Any]) -> list[str]:
    """Validate manifest metadata without opening any sealed raw file."""

    try:
        session = dt.date.fromisoformat(str(manifest["session"]))
    except (KeyError, TypeError, ValueError):
        return ["session is absent or invalid"]
    expected_origins = len(origins_utc(session))
    expected_quotes = len(ASSETS) * expected_origins
    problems: list[str] = []
    bars_by_asset = manifest.get("bars_by_asset")
    if not isinstance(bars_by_asset, dict):
        problems.append("bars_by_asset missing")
    else:
        for asset in ASSETS:
            if int(bars_by_asset.get(asset, 0)) < 380:
                problems.append(f"bars_by_asset[{asset}]={bars_by_asset.get(asset)}")
    if int(manifest.get("bars_rows", 0)) < len(ASSETS) * 380:
        problems.append(f"bars_rows={manifest.get('bars_rows')}")
    if int(manifest.get("tape_bytes", 0)) < 1_000_000:
        problems.append(f"tape_bytes={manifest.get('tape_bytes')}")
    quote_ok_by_asset = manifest.get("quote_ok_by_asset")
    if not isinstance(quote_ok_by_asset, dict):
        problems.append("quote_ok_by_asset missing")
    else:
        for asset in ASSETS:
            if int(quote_ok_by_asset.get(asset, 0)) != expected_origins:
                problems.append(f"quote_ok_by_asset[{asset}]={quote_ok_by_asset.get(asset)}")
    if int(manifest.get("quote_rows", 0)) != expected_quotes:
        problems.append(f"quote_rows={manifest.get('quote_rows')}")
    if int(manifest.get("quote_ok", 0)) != expected_quotes:
        problems.append(f"quote_ok={manifest.get('quote_ok')}")
    hashes = manifest.get("sha256")
    required_hashes = {"bars.parquet", "quotes.parquet", f"full_tape_{session.isoformat()}.zip"}
    if not isinstance(hashes, dict):
        problems.append("sha256 missing")
    else:
        for name in required_hashes:
            if not SHA256.fullmatch(str(hashes.get(name, ""))):
                problems.append(f"sha256[{name}] invalid")
    return problems


def session_is_complete(manifest: dict[str, Any]) -> bool:
    return not capture_problems(manifest)
