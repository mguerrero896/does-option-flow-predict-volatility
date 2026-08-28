"""Re-measure the Supabase access posture against the live endpoint.

`data/access_posture.json` records what the anonymous key can reach. This asks the endpoint
whether that is still true, table by table and view by view, and exits non-zero on any
disagreement. It is the half of the check that needs a network and a key; the half that needs
neither is `tests/contract/test_access_posture_matches_documentation.py`, which holds the
published prose to the same record and runs in every checkout.

Nothing here skips. A script that cannot reach the endpoint exits with a diagnosis rather
than a pass, because "I could not check" reported as success is the defect this whole file
exists to prevent -- the policy page asserted for six days that anonymous keys read nothing,
and nothing ever asked.

Read-only by construction: every request is a GET with `limit=1`, and the key is the
publishable anonymous key, which cannot write anywhere in this project.

    SUPABASE_ANON_KEY=... uv run python scripts/verify_access_posture.py
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Final

from mds650.sealed import guard_sealed_access

ROOT: Final = Path(__file__).resolve().parents[1]
POSTURE: Final = ROOT / "data" / "access_posture.json"
KEY_VARIABLE: Final = "SUPABASE_ANON_KEY"
TIMEOUT_SECONDS: Final = 20


def _get(url: str, key: str, profile: str | None = None) -> tuple[int, str]:
    request = urllib.request.Request(url, method="GET")
    request.add_header("apikey", key)
    request.add_header("Authorization", f"Bearer {key}")
    if profile is not None:
        request.add_header("Accept-Profile", profile)
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            return response.status, response.read(4096).decode("utf-8", "replace")
    except urllib.error.HTTPError as error:  # a 4xx is an answer, not a failure to ask
        return error.code, error.read(4096).decode("utf-8", "replace")


def _rows(body: str) -> int | None:
    """How many rows came back, or None when the body is not a JSON array."""

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return None
    return len(payload) if isinstance(payload, list) else None


def _is_explicit_access_denial(status: int, body: str) -> bool:
    """A PostgREST insufficient-privilege response proves a valid anon role was denied."""
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        return False
    return status in (401, 403) and isinstance(payload, dict) and payload.get("code") == "42501"


def main() -> int:
    posture = json.loads(POSTURE.read_text(encoding="utf-8"))
    every_surface = [
        *posture["closed_tables"]["tables"],
        *posture["closed_views"]["views"],
        *posture["anon_readable_tables"]["tables"],
        *posture["anon_readable_views"]["views"],
    ]
    guard_sealed_access(every_surface, operation="access-posture probe")
    key = os.environ.get(KEY_VARIABLE, "").strip()
    if not key:
        print(
            f"ACCESS_POSTURE_UNVERIFIED: {KEY_VARIABLE} is not set, so the posture in "
            f"{POSTURE.name} could not be re-measured. This is not a pass. Export the "
            f"project's publishable anonymous key and run again.",
            file=sys.stderr,
        )
        return 2

    base = f"https://{posture['project_ref']}.supabase.co/rest/v1"
    failures: list[str] = []
    checked = 0

    unverified: list[str] = []
    for table in posture["closed_tables"]["tables"]:
        # `select=*&limit=1` on purpose. A review suggested `select=count` to avoid
        # asking for row content; PostgREST reads that as a COLUMN named `count`,
        # which no closed table has, so every probe returned 400 and the whole
        # verification exited UNVERIFIED even against a correct posture. The proof
        # of closure IS attempting to read a row: RLS returns an empty array, and a
        # row coming back is exactly the drift this must report.
        status, body = _get(f"{base}/{table}?select=*&limit=1", key)
        checked += 1
        rows = _rows(body)
        # Closure is proven by either an RLS-filtered empty array or an explicit
        # Postgres insufficient-privilege response. An invalid key does not carry
        # SQLSTATE 42501, so it cannot make every object look closed.
        if status == 200 and rows:
            failures.append(
                f"{table}: declared CLOSED and returned {rows} row(s) to the anonymous key"
            )
        elif not _is_explicit_access_denial(status, body) and (status != 200 or rows is None):
            unverified.append(f"{table}: closed-check answered HTTP {status} — not proof")

    for view in posture["closed_views"]["views"]:
        status, body = _get(f"{base}/{view}?select=*&limit=1", key, profile="api")
        checked += 1
        rows = _rows(body)
        if status == 200 and rows:
            failures.append(
                f"api.{view}: declared CLOSED and returned {rows} row(s) to the anonymous key"
            )
        elif not _is_explicit_access_denial(status, body) and (status != 200 or rows is None):
            unverified.append(f"api.{view}: closed-check answered HTTP {status} — not proof")

    for table in posture["anon_readable_tables"]["tables"]:
        status, body = _get(f"{base}/{table}?select=*&limit=1", key)
        checked += 1
        if status != 200:
            failures.append(
                f"{table}: declared anon-readable and answered HTTP {status}. The posture is "
                f"stale -- tighter than recorded, which is safe, but still undocumented."
            )

    for view in posture["anon_readable_views"]["views"]:
        status, body = _get(f"{base}/{view}?select=*&limit=1", key, profile="api")
        checked += 1
        if status != 200:
            failures.append(
                f"api.{view}: declared anon-readable and answered HTTP {status}; the posture "
                f"no longer describes the endpoint."
            )

    if failures:
        print(f"ACCESS_POSTURE_DRIFT: {len(failures)} of {checked} checks disagree with "
              f"{POSTURE.name}:", file=sys.stderr)
        for line in failures:
            print(f"  - {line}", file=sys.stderr)
        return 1
    if unverified:
        print(f"ACCESS_POSTURE_UNVERIFIED: {len(unverified)} closed-table check(s) did not "
              f"produce the one response that proves closure:", file=sys.stderr)
        for line in unverified:
            print(f"  - {line}", file=sys.stderr)
        return 2

    print(f"[access] posture holds: {checked} checks agree with {POSTURE.name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
