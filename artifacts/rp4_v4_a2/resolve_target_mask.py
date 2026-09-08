"""Explain target-mask discrepancies from pinned bars without altering materialization.

Original Block3 allows forward-filled interior closes. RP4 requires actual closes.
This audit replays only that measurement convention on the discrepant keys, verifies
its bits against the registered values, and proves every discrepancy was ineligible
under unchanged v3. No fitted model or evaluation score is read or generated.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import polars as pl
from artifacts.rp4_code.evaluate import sha256, write_bytes_once, write_json_once
from artifacts.rp4_v3_code.materialize_gamma import paired_price_grids
from artifacts.rp4_v4_code import materialize_targets as target

from mds650.rp2.bars import SessionGrid
from mds650.rp2.realized import forward_measures, log_returns

OUTPUT = target.OUTPUT_ROOT / "targets"
CODE_PATH = "artifacts/rp4_v4_a2/resolve_target_mask.py"


def missing_anchors(
    grid: SessionGrid, observed: pl.DataFrame, origin: int, horizon: int
) -> list[int]:
    if origin < 0 or origin + horizon >= grid.minutes:
        raise ValueError("RP4_V4_RESOLUTION_ORIGIN_OUTSIDE_GRID")
    close = observed["close"].cast(pl.Float64).to_numpy()
    minutes = observed["minute"].to_numpy().astype(np.int64)
    present = set(minutes[np.isfinite(close) & (close > 0)].tolist())
    return sorted(set(range(origin, origin + horizon + 1)) - present)


def audit_pair(row: dict[str, Any], grid: SessionGrid, observed: pl.DataFrame) -> dict[str, Any]:
    horizon = int(str(row["comparison"]).rsplit("_", 1)[1])
    origin = int(row["origin_minute"])
    if (
        horizon not in (15, 5)
        or row["eligible_v3"] is not False
        or row["reason"] != "finite_mask_mismatch"
        or not np.isnan(row["reconstructed"])
        or not np.isfinite(row["reference"])
    ):
        raise ValueError("RP4_V4_RESOLUTION_NOT_AN_INELIGIBLE_MISSING_TARGET")
    missing = missing_anchors(grid, observed, origin, horizon)
    if not missing or grid.fill_share > 0.05:
        raise ValueError("RP4_V4_RESOLUTION_MISSING_CLOSE_CAUSE_NOT_PROVEN")
    first = int(np.flatnonzero(grid.valid)[0])
    replayed = forward_measures(
        log_returns(grid.close[first:]), np.array([origin - first], dtype=np.int64), horizon
    ).rv[0]
    same_bits = bool(
        np.float64(replayed).view(np.uint64) == np.float64(row["reference"]).view(np.uint64)
    )
    if not same_bits:
        raise ValueError("RP4_V4_RESOLUTION_REGISTERED_FILL_RULE_NOT_BIT_EXACT")
    return {
        **{name: row[name] for name in target.KEYS},
        "horizon": horizon,
        "eligible_v3": False,
        "missing_minutes": ";".join(map(str, missing)),
        "missing_closes": len(missing),
        "observed_closes": horizon + 1 - len(missing),
        "required_closes": horizon + 1,
        "reference_finite": True,
        "reconstructed_finite": False,
        "reason": "missing_observed_closes",
        "session_fill_share": grid.fill_share,
        "registered_fill_rule_reproduction_bit_exact": same_bits,
        "resolution": "registered_forward_fill_versus_strict_actual_close_rule",
    }


def run(expected_manifest_sha256: str) -> dict[str, Any]:
    manifest_path = OUTPUT / "manifest.json"
    target.verify_pins({str(manifest_path): expected_manifest_sha256})
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (
        manifest["status"] != "TARGET_PREFLIGHT_REQUIRES_INVESTIGATION"
        or manifest["preflight_pass"]
    ):
        raise ValueError("RP4_V4_RESOLUTION_UNEXPECTED_INITIAL_PREFLIGHT")
    target.verify_pins(manifest["artifacts"])
    code_path = target.ROOT / CODE_PATH
    code_sha = sha256(code_path)
    pin_path = next(
        Path(name) for name in manifest["artifacts"] if Path(name).name.startswith("input_pins_")
    )
    original_pins = json.loads(pin_path.read_text(encoding="utf-8"))["sha256"]
    target.verify_pins(original_pins)
    bar_pins = target.select_bar_pins(original_pins)
    grids = paired_price_grids(bar_pins)
    differences_path = OUTPUT / "reference_discrepancies.parquet"
    differences = pl.read_parquet(differences_path)
    rows = []
    for row in differences.iter_rows(named=True):
        grid, observed = grids[row["asset"], row["session_date"]]
        rows.append(audit_pair(row, grid, observed))
    audited = pl.DataFrame(rows).sort("asset", "session_date", "origin_minute", "horizon")
    counts = {f"rv_{h}": audited.filter(pl.col("horizon") == h).height for h in target.HORIZONS}
    reference = manifest["reference_comparison"]
    if any(
        reference["by_target"][name]["finite_bit_mismatches"] != 0
        or reference["by_target"][name]["finite_mask_mismatches"] != count
        or reference["eligible_v3_only"][name]["all_value_bit_mismatches"] != 0
        for name, count in counts.items()
    ):
        raise ValueError("RP4_V4_RESOLUTION_REFERENCE_CENSUS_NOT_EXHAUSTIVE")
    null_path = OUTPUT / "rv30_control_discrepancies.parquet"
    nulls = pl.read_parquet(null_path)
    status_path = OUTPUT / "target_status.parquet"
    statuses = pl.read_parquet(status_path)
    base_nulls = pl.read_parquet(target.BASE_PANEL, columns=target.KEYS + ["rv30"]).select(
        *target.KEYS, pl.col("rv30").is_null().alias("base_rv30_is_null")
    )
    nulls = nulls.join(statuses, on=target.KEYS, validate="1:1").join(
        base_nulls, on=target.KEYS, validate="1:1"
    )
    null_rows = []
    for row in nulls.iter_rows(named=True):
        if (
            row["eligible_v3"] is not False
            or row["base_rv30_is_null"] is not True
            or row["reference"] is not None
            or not np.isnan(row["reconstructed"])
            or row["target_status_30"] != "unobserved_target_close"
        ):
            raise ValueError("RP4_V4_RESOLUTION_RV30_NULL_SEMANTICS_MISMATCH")
        grid, observed = grids[row["asset"], row["session_date"]]
        missing = missing_anchors(grid, observed, row["origin_minute"], 30)
        if not missing:
            raise ValueError("RP4_V4_RESOLUTION_RV30_MISSING_ANCHOR_NOT_PROVEN")
        null_rows.append(
            {
                **{name: row[name] for name in target.KEYS},
                "base_is_null": True,
                "control_is_nan": True,
                "eligible_v3": False,
                "missing_minutes": ";".join(map(str, missing)),
                "resolution": "same_missing_target_null_in_base_and_nan_in_control_only",
            }
        )
    control = manifest["rv30_control"]
    if (
        control["finite_bit_mismatches"] != 0
        or control["finite_mask_mismatches"] != 0
        or control["null_mask_mismatches"] != len(null_rows)
        or control["all_value_bit_mismatches"] != len(null_rows)
        or any(manifest["eligible_v3_invalid"].values())
    ):
        raise ValueError("RP4_V4_RESOLUTION_CONTROL_OR_ELIGIBILITY_NOT_CLOSED")
    audit_path = OUTPUT / "resolution_rows.csv"
    null_audit_path = OUTPUT / "rv30_null_rows.csv"
    write_bytes_once(audit_path, audited.write_csv().encode("utf-8"))
    write_bytes_once(
        null_audit_path, pl.DataFrame(null_rows).sort(target.KEYS).write_csv().encode("utf-8")
    )
    target.verify_pins(original_pins)
    target.verify_pins(manifest["artifacts"])
    target.verify_pins({str(code_path): code_sha, str(manifest_path): expected_manifest_sha256})
    resolution = {
        "status": "PASS_DISCREPANCIES_EXPLAINED_OUTSIDE_V3_ELIGIBILITY",
        "spec_sha256": manifest["spec_sha256"],
        "base_panel_sha256": target.BASE_SHA,
        "target_panel_sha256": sha256(OUTPUT / "panel.parquet"),
        "original_manifest_sha256": expected_manifest_sha256,
        "producer_sha256": manifest["producer_sha256"],
        "finite_pair_mismatches": 0,
        "eligible_key_changes": 0,
        "eligible_invalid_targets": manifest["eligible_v3_invalid"],
        "eligible_rows": manifest["eligible_v3_rows"],
        "eligible_reference_finite_pairs": {
            name: record["finite_pairs"] for name, record in reference["eligible_v3_only"].items()
        },
        "discrepancies": {
            "total": audited.height,
            **counts,
            "unique_origin_keys": audited.select(target.KEYS).n_unique(),
            "all_outside_v3_eligibility": True,
            "all_caused_by_missing_observed_closes": True,
            "registered_filled_values_reproduced_bit_exact": True,
        },
        "rv30_nulls": {
            "total": len(null_rows),
            "all_outside_v3_eligibility": True,
            "all_control_nan": True,
            "all_base_null": True,
            "all_have_missing_actual_closes": True,
        },
        "source_files_sha256": bar_pins,
        "evidence_artifacts_sha256": {
            str(path.resolve()): sha256(path)
            for path in (
                audit_path,
                null_audit_path,
                differences_path,
                null_path,
                status_path,
                OUTPUT / "reference_comparison.json",
                OUTPUT / "rv30_control.json",
            )
        },
        "resolution_code_path": CODE_PATH,
        "resolution_code_sha256": code_sha,
        "original_artifacts_modified": False,
        "original_materialization_exit_code": 2,
        "model_fits": 0,
        "completed_at_utc": datetime.now(UTC).isoformat(),
        "RESEARCH_ONLY": True,
        "capital_go": False,
    }
    resolution_path = OUTPUT / "resolution.json"
    write_json_once(resolution_path, resolution)
    digest = sha256(resolution_path)
    write_bytes_once(OUTPUT / "resolution.sha256", f"{digest}  resolution.json\n".encode("ascii"))
    print(
        json.dumps(
            {
                "status": resolution["status"],
                "discrepancies": resolution["discrepancies"],
                "rv30_nulls": resolution["rv30_nulls"],
                "resolution_sha256": digest,
            }
        ),
        flush=True,
    )
    return resolution


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest-sha256", required=True)
    run(parser.parse_args().manifest_sha256)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
