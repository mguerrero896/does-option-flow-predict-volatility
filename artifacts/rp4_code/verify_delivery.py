"""Verify the sanitized RP4 publication; never run models or provider requests.

Historical receipts retain original execution hashes. The projection manifest
separately binds the published bytes; --original-root also checks the preserved
private source checkout, without reading any licensed panel.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

PERSONAL_PATH = re.compile(rb"(?i)[a-z]:[\\/]+users[\\/]+[^\\/\s\"']+")


def sha256(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def safe_path(root: Path, name: str) -> Path:
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()) or path == root.resolve():
        raise ValueError("RP4_PROJECTION_PATH_ESCAPE")
    return path


def scan_payload(payload: bytes, name: str) -> int:
    if PERSONAL_PATH.search(payload):
        raise ValueError(f"RP4_PUBLIC_PERSONAL_PATH:{name}")
    count = 1
    if name.endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            for entry in archive.infolist():
                if entry.is_dir():
                    continue
                if entry.filename.endswith(".zip"):
                    raise ValueError("RP4_NESTED_ARCHIVE_UNSUPPORTED")
                count += scan_payload(archive.read(entry), entry.filename)
    return count


def verify(root: Path, original_root: Path | None = None) -> dict[str, object]:
    manifest_path = root / "artifacts/rp4_publication_v1/manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest["schema_version"] != "rp4-public-projection-v1":
        raise ValueError("RP4_PROJECTION_SCHEMA")
    payloads = scan_payload(manifest_path.read_bytes(), manifest_path.name)
    for name, item in manifest["files"].items():
        payload = safe_path(root, name).read_bytes()
        if sha256(payload) != item["public_sha256"]:
            raise ValueError(f"RP4_PUBLIC_BYTES_DRIFT:{name}")
        if original_root is not None:
            original = safe_path(original_root, name).read_bytes()
            if sha256(original) != item["original_sha256"]:
                raise ValueError(f"RP4_PRESERVED_ORIGINAL_DRIFT:{name}")
        payloads += scan_payload(payload, name)
    for name, expected in manifest["additions_sha256"].items():
        payload = safe_path(root, name).read_bytes()
        if sha256(payload) != expected:
            raise ValueError(f"RP4_PUBLIC_ADDITION_DRIFT:{name}")
        payloads += scan_payload(payload, name)
    for name in manifest["scientific_bytes_unchanged"]:
        item = manifest["files"][name]
        if item["original_sha256"] != item["public_sha256"]:
            raise ValueError(f"RP4_SCIENTIFIC_BYTES_CHANGED:{name}")
    freeze = json.loads((root / "artifacts/rp4_a1/freeze.json").read_text())
    for key in ("specification", "document"):
        item = freeze[key]
        if manifest["files"][item["path"]]["original_sha256"] != item["sha256"]:
            raise ValueError(f"RP4_ORIGINAL_FREEZE_POINTER_DRIFT:{key}")
    endpoints = 0
    for contrast, base, expanded in (("B1_over_B0", "B0", "B1"), ("B2_over_B1", "B1", "B2")):
        svg = ElementTree.parse(root / f"artifacts/rp4_b4/{contrast}.svg")
        curves = [node.attrib for node in svg.iter() if "data-endpoint" in node.attrib]
        if len(curves) != 4:
            raise ValueError("RP4_FIGURE_CURVE_COUNT")
        for window, stage in (("primary", "b2"), ("confirmation", "b3")):
            with (root / f"artifacts/rp4_{stage}/session_losses.csv").open(newline="") as stream:
                rows = list(csv.DictReader(stream))
            for family in ("log_ols_harq", "lightgbm_qlike"):
                curve = next(
                    c for c in curves if c["data-family"] == family and c["data-window"] == window
                )
                expected = math.fsum(
                    float(r[f"loss__{family}__{base}"]) - float(r[f"loss__{family}__{expanded}"])
                    for r in rows
                )
                if not math.isclose(
                    float(curve["data-endpoint"]), expected, rel_tol=1e-12, abs_tol=1e-12
                ):
                    raise ValueError("RP4_FIGURE_ENDPOINT_DRIFT")
                endpoints += 1
    return {
        "status": "PASS_RP4_PUBLIC_PROJECTION",
        "original_checkout_verified": original_root is not None,
        "files_verified": len(manifest["files"]),
        "figure_endpoints_verified": endpoints,
        "payloads_scanned": payloads,
        "models_fitted": 0,
        "licensed_panels_read": 0,
        "live_collector_verified": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-root", type=Path)
    args = parser.parse_args()
    print(json.dumps(verify(Path(__file__).resolve().parents[2], args.original_root)))


if __name__ == "__main__":
    main()
