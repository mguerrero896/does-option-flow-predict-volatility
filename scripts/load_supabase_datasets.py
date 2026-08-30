"""Load the gated research datasets into their private Supabase tables.

Streams each frozen parquet into a STAGING table, then promotes it to the live
table in a single server-side transaction. The repo parquets remain the source of
truth — these tables are a queryable private view, never an editing surface (RLS
enabled, no policies, and since 2026-08-26 no grants at all for anon or
authenticated: a read is refused at the privilege level).

This script was on an audit hold between 2026-08-25 and 2026-08-26, because five
properties made re-running it unsafe. All five are now fixed rather than gated:

1. **Identity was a row count.** Different content with the same number of rows
   read as "already loaded". Identity is now the parquet's SHA-256, recorded in
   `public.dataset_loads` at promotion time, so a changed file is always noticed
   and an unchanged one is never re-sent.
2. **It deleted before loading.** An interruption left the live table empty or
   half-filled. Loading now targets `<table>__staging`; the live table is not
   touched until everything has arrived.
3. **There was no transaction.** `public.promote_dataset()` does the delete, the
   insert and the digest record in ONE transaction, so promotion either happens
   completely or not at all. It refuses to promote empty staging, which would
   otherwise be a silent way to wipe a table.
4. **Retries had no idempotency key.** Every run now owns a UUID-scoped slice of
   staging. Promotion reads and deletes only that slice, so concurrent runs cannot
   truncate or promote each other's rows.
5. **Six targets have no primary key.** Still true, and it is why identity lives
   in `dataset_loads` keyed by table name rather than in the rows themselves.

Run:  $env:SUPABASE_SERVICE_KEY set, then  uv run python scripts/load_supabase_datasets.py
      --source-root <canonical-local-repo> when the filtered public worktree does not
      contain the licensed parquets.
      --force re-promotes even when the digest already matches.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import os
import uuid
from pathlib import Path

import httpx
import polars as pl
import polars.selectors as cs

from mds650.sealed import guard_sealed_access
from mds650.supabase_auth import api_key_headers

REPO = Path(__file__).resolve().parents[1]
PROJECT_REF = "eqpyjikcewqaegnbaemf"
REST = f"https://{PROJECT_REF}.supabase.co/rest/v1"
BATCH_CELLS = 200_000  # rows per batch scaled by column count; wide tables get smaller batches

DATASETS: dict[str, str] = {
    "dev_training_all_origins": "artifacts/phase5/development_all_origins_80d.parquet",
    "dev_training_common": "artifacts/phase5/common_development_80d.parquet",
    "c1_development_forecasts": "artifacts/phase5/development_forecasts.parquet",
    "c5_frozen_evaluation_forecasts": (
        "artifacts/b2_confirmation/frozen_evaluation_forecasts.parquet"
    ),
    "b1v3_features": "artifacts/b1v3_target_blind/b1v3_features.parquet",
    "b2_mechanism_forecasts": "artifacts/methodology/b2_mechanism_forecasts.parquet",
}


def file_digest(path: Path) -> str:
    """SHA-256 of the file's bytes — the identity a row count could not provide."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def required_sources(root: Path | None = None) -> dict[str, Path]:
    """Return every required parquet, refusing a run that could only be partial."""
    source_root = (root or REPO).resolve()
    sources = {
        table: (source_root / relative).resolve() for table, relative in DATASETS.items()
    }
    escaped = [
        f"{table} ({path})"
        for table, path in sources.items()
        if not path.is_relative_to(source_root)
    ]
    if escaped:
        raise SystemExit(f"DATASET_PATH_ESCAPES_SOURCE_ROOT: {', '.join(escaped)}")
    missing = [
        f"{table} ({path.relative_to(source_root)})"
        for table, path in sources.items()
        if not path.is_file()
    ]
    if missing:
        raise SystemExit(f"DATASET_SOURCES_MISSING: {', '.join(missing)}")
    return sources


def _recorded_load(client: httpx.Client, table: str) -> tuple[str, int] | None:
    """The digest and row count last promoted into *table*, or None."""
    response = client.get(
        f"{REST}/dataset_loads",
        params={"table_name": f"eq.{table}", "select": "source_sha256,row_count"},
    )
    if response.status_code != 200:
        raise SystemExit(
            f"DATASET_LOAD_REGISTRY_READ_FAILED {table}: "
            f"{response.status_code} {response.text[:300]}"
        )
    rows = response.json()
    return (str(rows[0]["source_sha256"]), int(rows[0]["row_count"])) if rows else None


def _row_count(
    client: httpx.Client, table: str, load_id: uuid.UUID | None = None
) -> int:
    params = {"select": "*"}
    if load_id is not None:
        params["load_id"] = f"eq.{load_id}"
    response = client.head(
        f"{REST}/{table}",
        params=params,
        headers={"Prefer": "count=exact", "Range-Unit": "items", "Range": "0-0"},
    )
    total = response.headers.get("content-range", "").rsplit("/", 1)[-1]
    if response.status_code not in (200, 206) or not total.isdigit():
        raise SystemExit(
            f"DATASET_ROW_COUNT_FAILED {table}: {response.status_code} "
            f"{response.text[:300]}"
        )
    return int(total)


def _send(client: httpx.Client, staging: str, frame: pl.DataFrame, load_id: uuid.UUID) -> None:
    batch_rows = max(2_000, BATCH_CELLS // frame.width)
    sent = 0
    for offset in range(0, frame.height, batch_rows):
        chunk = frame.slice(offset, batch_rows).with_columns(
            cs.float().fill_nan(None), pl.lit(str(load_id)).alias("load_id")
        )
        buffer = io.BytesIO()
        chunk.write_json(buffer)
        payload = buffer.getvalue()
        for attempt in range(4):
            try:
                response = client.post(
                    f"{REST}/{staging}",
                    content=payload,
                    headers={"Content-Type": "application/json"},
                )
            except httpx.HTTPError:
                response = None
            if response is not None and response.status_code in (200, 201):
                break
            if attempt == 3:
                detail = (
                    f"{response.status_code} {response.text[:300]}"
                    if response is not None
                    else "transport error"
                )
                raise SystemExit(f"STAGING_LOAD_FAILED {staging} offset {offset}: {detail}")
        sent += chunk.height
        if sent % 100_000 < batch_rows:
            print(f"[load] {staging}: {sent:,}/{frame.height:,}", flush=True)


def _promote(
    client: httpx.Client, table: str, relative: str, digest: str, load_id: uuid.UUID
) -> int:
    """Staging -> live in one server-side transaction."""
    response = client.post(
        f"{REST}/rpc/promote_dataset_v2",
        json={
            "p_table": table,
            "p_source_path": relative,
            "p_sha256": digest,
            "p_load_id": str(load_id),
        },
    )
    if response.status_code not in (200, 201):
        raise SystemExit(f"PROMOTE_FAILED {table}: {response.status_code} {response.text[:300]}")
    return int(response.json())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--force",
        action="store_true",
        help="re-promote even when the recorded digest already matches the file",
    )
    parser.add_argument(
        "--source-root",
        type=Path,
        default=REPO,
        help="root containing the fixed licensed artifact paths (default: this worktree)",
    )
    arguments = parser.parse_args()

    guard_sealed_access([*DATASETS, *DATASETS.values()], operation="gated dataset load")
    sources = required_sources(arguments.source_root)
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not key:
        raise SystemExit("SUPABASE_SERVICE_KEY missing (User env var; see DATA_ACCESS.md).")

    headers = api_key_headers(key)
    with httpx.Client(timeout=300, headers=headers) as client:
        for table, path in sources.items():
            relative = DATASETS[table]
            digest = file_digest(path)
            recorded = _recorded_load(client, table)
            if not arguments.force and recorded is not None and recorded[0] == digest:
                live_rows = _row_count(client, table)
                if live_rows == recorded[1]:
                    print(f"[load] {table}: unchanged (sha256 {digest[:12]}…), skipped")
                    continue
                print(
                    f"[load] {table}: registry/live row drift "
                    f"({recorded[1]:,} != {live_rows:,}); re-promoting",
                    flush=True,
                )

            frame = pl.read_parquet(path)
            staging = f"{table}__staging"
            load_id = uuid.uuid4()
            _send(client, staging, frame, load_id)

            staged = _row_count(client, staging, load_id)
            if staged != frame.height:
                raise SystemExit(
                    f"STAGING_COUNT_MISMATCH {table}: staged {staged} != parquet "
                    f"{frame.height}; the live table was NOT touched"
                )
            promoted = _promote(client, table, relative, digest, load_id)
            print(f"[load] {table}: promoted {promoted:,} rows (sha256 {digest[:12]}…)")
    print("[load] done")


if __name__ == "__main__":
    main()
