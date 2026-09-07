"""Verify B1 custody and emit public metadata only, never licensed rows."""

import argparse
import json
from collections import Counter
from pathlib import Path

from evaluate import ROOT, load_spec, sha256, write_bytes_once, write_json_once

DATA = Path("D:/MDS650")
PRIVATE = DATA / "artifacts/rp4_20260907"


def checked_hash(path: Path, expected: str) -> str:
    path.resolve().relative_to(DATA.resolve())
    actual = sha256(path)
    if actual != expected:
        raise ValueError("RP4_B1_CUSTODY_HASH_MISMATCH")
    return actual


def close(acquisition_path: Path) -> None:
    specification = ROOT / "artifacts/rp4_a1/specification.json"
    digest = "865865558087108356f4eb6da7f9d431f1c4d32fd330f20ea78eb126ec6462a5"
    load_spec(specification, digest)
    acquisition = json.loads(acquisition_path.read_text())
    if acquisition["spec_sha256"] != digest:
        raise ValueError("RP4_B1_ACQUISITION_SPEC_MISMATCH")
    final = {
        row["job"]: row for row in acquisition["records"] + acquisition.get("final_retries", [])
    }
    records = []
    original_files = 0
    for name, row in sorted(final.items()):
        files = []
        for item in row.get("files", []):
            path = Path(item["path"])
            file = {
                "path_under_data_root": path.relative_to(DATA).as_posix(),
                "sha256": checked_hash(path, item["sha256"]),
                "bytes": path.stat().st_size,
            }
            if "source" in item:
                source = Path(item["source"])
                source.resolve().relative_to((DATA / "phase9/raw").resolve())
                if item["source_sha256"] != item["sha256"]:
                    raise ValueError("RP4_B1_COPY_SOURCE_RECEIPT_MISMATCH")
                file["source_sha256_rechecked"] = checked_hash(source, item["source_sha256"])
                original_files += 1
            files.append(file)
        records.append(
            {
                "job": name,
                "status": row["status"],
                "acquire_code_sha256": row.get("acquire_code_sha256"),
                "files": files,
            }
        )
    missing = sorted(row["job"] for row in records if row["status"] != "PASS")
    if missing != acquisition["missing"]:
        raise ValueError("RP4_B1_MISSING_LIST_MISMATCH")
    lineage_path = PRIVATE / "b1_complete_v1/manifest.json"
    lineage = json.loads(lineage_path.read_text())
    if lineage["spec_sha256"] != digest or not lineage["development_prefix_equal_by_keys"]:
        raise ValueError("RP4_B1_PREFIX_PROOF_INVALID")
    for directory, field in (
        ("a2_combined_v2", "development_panel_sha256"),
        ("b1_extension_v1", "extension_panel_sha256"),
        ("b1_complete_v1", "combined_panel_sha256"),
    ):
        checked_hash(PRIVATE / directory / "panel.parquet", lineage[field])
    extension_path = PRIVATE / "b1_extension_v1/manifest.json"
    extension = json.loads(extension_path.read_text())
    refresh_path = PRIVATE / "b1_extension_v1/exogenous_refresh_comparison.json"
    refresh = json.loads(refresh_path.read_text())
    destination = ROOT / "artifacts/rp4_b1"
    coverage_path = PRIVATE / "b1_extension_v1/coverage.csv"
    write_bytes_once(destination / "coverage.csv", coverage_path.read_bytes())
    output = {
        "status": "PARTIAL" if missing else "PASS",
        "specification_sha256": digest,
        "missing": missing,
        "jobs_by_type": dict(Counter(row["job"].split(":")[0] for row in records)),
        "records": records,
        "phase9_original_files_rehashed": original_files,
        "phase9_modified": False,
        "panel_lineage": {key: value for key, value in lineage.items() if key != "artifacts"},
        "extension": {
            key: extension[key]
            for key in (
                "rows",
                "sessions",
                "assets",
                "first_session",
                "last_session",
                "target_rows_finite",
                "code_sha256",
                "exclusions",
            )
            if key in extension
        },
        "exogenous_development_differences": {
            "development_unchanged": refresh["development_unchanged"],
            "changed_asset_sessions": len(refresh["changed_prior_rate_or_cash"]),
            "by_asset": dict(
                Counter(row["asset"] for row in refresh["changed_prior_rate_or_cash"])
            ),
        },
        "private_metadata_sha256": {
            path.relative_to(PRIVATE).as_posix(): sha256(path)
            for path in (
                acquisition_path,
                lineage_path,
                extension_path,
                refresh_path,
                coverage_path,
            )
        },
        "code_sha256": sha256(Path(__file__)),
        "licensed_rows_published": 0,
        "models_fitted": 0,
    }
    write_json_once(destination / "summary.json", output)
    print(
        json.dumps(
            {
                "status": output["status"],
                "jobs": len(records),
                "jobs_by_type": output["jobs_by_type"],
                "missing": missing,
                "phase9_original_files_rehashed": original_files,
                "summary_sha256": sha256(destination / "summary.json"),
            }
        ),
        flush=True,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--acquisition-summary", type=Path, required=True)
    close(parser.parse_args().acquisition_summary)
