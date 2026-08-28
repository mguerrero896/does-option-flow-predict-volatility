"""Upload the 14 gated parquets to the private Supabase bucket, hash-verified.

Owner runs this once, locally, with the project's service-role key in the
environment (the key is never committed or printed):

    $env:SUPABASE_SERVICE_KEY = "<service_role key from the dashboard>"
    uv run python scripts/upload_gated_data.py

Each file is uploaded to bucket 'research-data' at its pointer's bucket_object
path, then downloaded back and verified against the committed SHA-256 before
being counted as stored.
"""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import httpx

from mds650.sealed import guard_sealed_access

REPO = Path(__file__).resolve().parents[1]
POINTERS = REPO / "data" / "GATED_DATA_POINTERS.json"
PROJECT_REF = "eqpyjikcewqaegnbaemf"
BUCKET = "research-data"
BASE = f"https://{PROJECT_REF}.supabase.co/storage/v1"


def main() -> None:
    key = os.environ.get("SUPABASE_SERVICE_KEY")
    if not key:
        raise SystemExit(
            "SUPABASE_SERVICE_KEY missing. Dashboard -> project mds650-research-data "
            "-> Settings -> API keys -> service_role (secret) -> copy, then set the "
            "env var and rerun. Never commit or share this key."
        )
    headers = {"Authorization": f"Bearer {key}", "apikey": key}
    entries = json.loads(POINTERS.read_text(encoding="utf-8"))["files"]
    # Guard the entries this run will actually upload.
    guard_sealed_access([e["path"] for e in entries], operation="gated upload")
    stored = 0
    with httpx.Client(timeout=600, headers=headers) as client:
        # The bucket must still be private before a single byte moves: a bucket
        # flipped public would make every upload an instant publication.
        bucket_info = client.get(f"{BASE}/bucket/{BUCKET}")
        is_private = bucket_info.status_code == 200 and bucket_info.json().get("public") is False
        if not is_private:
            raise SystemExit(
                f"BUCKET_PRIVACY_UNVERIFIED: {BUCKET} answered {bucket_info.status_code}; "
                "refusing to upload until the bucket is confirmed private"
            )
        for entry in entries:
            path = REPO / entry["path"]
            data = path.read_bytes()
            local_hash = hashlib.sha256(data).hexdigest()
            if local_hash != entry["sha256"]:
                raise SystemExit(f"LOCAL_HASH_MISMATCH: {entry['path']}")
            object_path = entry["bucket_object"]
            response = client.post(
                f"{BASE}/object/{BUCKET}/{object_path}",
                content=data,
                # x-upsert false: a frozen object is immutable, and re-uploading over
                # it must FAIL (409), never silently replace bytes something hashes.
                headers={"Content-Type": "application/octet-stream", "x-upsert": "false"},
            )
            if response.status_code == 409:
                print(f"[upload] {entry['path']}: already stored (frozen, not replaced)")
                continue
            if response.status_code not in (200, 201):
                raise SystemExit(
                    f"UPLOAD_FAILED {entry['path']}: {response.status_code} {response.text[:200]}"
                )
            check = client.get(f"{BASE}/object/{BUCKET}/{object_path}")
            check.raise_for_status()
            remote_hash = hashlib.sha256(check.content).hexdigest()
            if remote_hash != entry["sha256"]:
                raise SystemExit(f"REMOTE_HASH_MISMATCH: {entry['path']}")
            stored += 1
            print(f"ok  {object_path}  ({len(data):,} bytes, sha256 verified round-trip)")
    print(f"stored and verified: {stored}/{len(entries)} files in bucket '{BUCKET}'")


if __name__ == "__main__":
    main()
