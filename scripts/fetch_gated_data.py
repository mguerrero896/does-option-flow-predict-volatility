"""Download gated research data from owner-issued signed URLs and verify hashes.

Usage: create a JSON file mapping repo paths to the signed URLs the author issued,
then run:  uv run python scripts/fetch_gated_data.py --manifest my_urls.json
Every download is verified against the committed SHA-256 in
data/GATED_DATA_POINTERS.json before being written to its final path.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import httpx

from mds650.sealed import guard_sealed_access

REPO = Path(__file__).resolve().parents[1]
POINTERS = REPO / "data" / "GATED_DATA_POINTERS.json"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    urls: dict[str, str] = json.loads(parser.parse_args().manifest.read_text(encoding="utf-8"))
    # Guard what THIS invocation will fetch, not the whole registry: gating every
    # pointer entry refused a manifest asking only for an unrelated clean file.
    guard_sealed_access(sorted(urls), operation="gated data download")
    pointers = {
        entry["path"]: entry
        for entry in json.loads(POINTERS.read_text(encoding="utf-8"))["files"]
    }
    with httpx.Client(timeout=600, follow_redirects=True) as client:
        for path, url in urls.items():
            if path not in pointers:
                raise SystemExit(f"UNKNOWN_PATH_NOT_IN_POINTERS: {path}")
            response = client.get(url)
            response.raise_for_status()
            digest = hashlib.sha256(response.content).hexdigest()
            expected = pointers[path]["sha256"]
            if digest != expected:
                raise SystemExit(f"HASH_MISMATCH for {path}: got {digest[:16]}...")
            destination = (REPO / path).resolve()
            # The pointers file is repo-controlled, but a traversal entry in it must
            # still not let a download land outside the repository.
            if not destination.is_relative_to(REPO):
                raise SystemExit(f"PATH_ESCAPES_REPO: {path}")
            destination.parent.mkdir(parents=True, exist_ok=True)
            # tmp + replace: an interrupted download can never leave a half-written
            # file at a path whose name promises verified frozen bytes.
            partial = destination.with_name(destination.name + ".partial")
            partial.write_bytes(response.content)
            partial.replace(destination)
            print(f"ok  {path}  ({len(response.content):,} bytes, sha256 verified)")
    print("all files verified against data/GATED_DATA_POINTERS.json")


if __name__ == "__main__":
    main()
