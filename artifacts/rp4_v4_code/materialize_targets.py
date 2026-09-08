"""RP4 v4 target-only sidecar using the unchanged RP2 realized-variance estimator.

No fitting, target selection, predictor changes, or evaluation-mask changes occur here.
The 15/5-minute targets use the same full-session float64 prefix sums as RV30 and
require every one of their h+1 price anchors to be actually observed. A separate
30-minute reconstruction is an alignment control; it never replaces base-panel RV30.
Real inputs are read only by the hash-gated CLI, never at module import.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import sys
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import numpy.typing as npt
import polars as pl
from artifacts.rp4_code.evaluate import sha256, write_bytes_once, write_json_once
from artifacts.rp4_v2_code.evaluate_v2 import panel_masks
from polars.testing import assert_frame_equal

from mds650.rp2.bars import BAR_SOURCES, SessionGrid
from mds650.rp2.realized import forward_measures, log_returns

ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = Path("private-input/841df58180063dcccac1")
OUTPUT_ROOT = DATA_ROOT / "artifacts/rp4_v4_20260908"
BASE_PANEL = DATA_ROOT / "artifacts/rp4_v3_20260907/materialized_empty_windows/panel.parquet"
BASE_SHA = "a63ff5e61092d2bc00917c5de4e0e73f928005acc475f46370348eaca6ad4637"
PIN_MANIFEST = DATA_ROOT / "artifacts/rp4_v3_20260907/materialized/input_pins.json"
PIN_MANIFEST_SHA = "ca610184b4ccffe2d5792e86d8babefc12ebee52b38e5b1d16f8c2f7465606db"
REFERENCE = DATA_ROOT / (
    "registered_runs/rp2_v3/rp2-v3-20260901-flow-session-loss-registration/"
    "rp2_block3_target/target_panel.parquet"
)
REFERENCE_SHA = "fdab55c524a6ee2cd94bb3f1f544dec527e1c8813f9a03d6e17ed8029f842831"
REFERENCE_BYTES = 37_068_944
ADDED_BAR_ROOT = DATA_ROOT / "artifacts/rp4_20260907/data/fmp"
KEYS = ["asset", "session_date", "origin_minute"]
HORIZONS = (15, 5)
CONTROL_HORIZON = 30
PRODUCER_PATH = "artifacts/rp4_v4_code/materialize_targets.py"
SOURCE_CODE_SHA256 = {
    "artifacts/rp4_v3_code/materialize_gamma.py": (
        "2f59184b5a36b301252bb11eaf779c8128cef0f45266368f44b1a7d35f3644a3"
    ),
    "artifacts/rp4_v2_code/materialize_iv.py": (
        "3741c28773d50e89d6c65bb3307536ba8defcc085edcd92a358d6dc735d43972"
    ),
    "artifacts/rp4_code/materialize.py": (
        "f1de9af7f07480650ff17ab5dc6d785c823193e2e400f32dc532c2a05d31ded0"
    ),
    "scripts/rp2_block3_target_panel.py": (
        "8f6c8fb8e653ff4eafbdb9dbe54835c19754cda9d8c76096fbc7d5fcb2146eec"
    ),
    "src/mds650/rp2/realized.py": (
        "3d177f2e2425341c72bba39f18d5bd4dcbd81b900a4fba7addbee9c2ed45e5c8"
    ),
    "src/mds650/rp2/bars.py": ("e5da1a151d8af1d33e6ae8ca12062b7be5489530b062101b57b1c27bd26ead69"),
    "uv.lock": "960c8a2638cdf39be44acb6d06b0e355eceab4e6658357f089f2b9aa159d61d0",
}
type FloatArray = npt.NDArray[np.float64]
type Mask = npt.NDArray[np.bool_]


def assert_keys(frame: pl.DataFrame) -> None:
    """Reject duplicate/null/incorrectly typed identities before any keyed alignment."""
    expected = {"asset": pl.String, "session_date": pl.String, "origin_minute": pl.Int64}
    if any(frame.schema.get(name) != dtype for name, dtype in expected.items()):
        raise ValueError("RP4_V4_TARGET_KEY_SCHEMA")
    keys = frame.select(KEYS)
    if keys.null_count().sum_horizontal().item() or keys.n_unique() != frame.height:
        raise ValueError("RP4_V4_TARGET_KEY_NOT_UNIQUE_NONNULL")


def session_targets(
    keys: pl.DataFrame,
    grid: SessionGrid | None,
    observed_bars: pl.DataFrame | None,
) -> pl.DataFrame:
    """Compute targets on supplied keys; retain NaNs and explicit per-horizon reasons.

    A forward-fill outside the target anchors remains governed by the inherited 5%
    full-session gate. Within a target, h+1 actual finite/positive closes are required.
    The estimator sees the full close tail from the first valid session minute: never
    restart its prefix sum per origin, rescale, annualize, or shift by predictor latency.
    """
    assert_keys(keys)
    if keys.height and keys.select("asset", "session_date").n_unique() != 1:
        raise ValueError("RP4_V4_TARGET_MULTIPLE_SESSION_ASSETS")
    result = keys.select(KEYS)
    count = keys.height
    origins = keys["origin_minute"].to_numpy().astype(np.int64)
    observed_prefix: npt.NDArray[np.int64] | None = None
    returns: FloatArray | None = None
    first = 0
    close: FloatArray = np.empty(0, dtype=np.float64)
    grid_valid = False
    if grid is not None and observed_bars is not None:
        if (
            observed_bars.select("asset", "session_date").n_unique() != 1
            or (
                keys.height
                and tuple(map(str, observed_bars.select("asset", "session_date").row(0)))
                != tuple(map(str, keys.select("asset", "session_date").row(0)))
            )
            or observed_bars["minute"].n_unique() != observed_bars.height
        ):
            raise ValueError("RP4_V4_TARGET_OBSERVED_BAR_IDENTITY")
        present = np.flatnonzero(grid.valid)
        first = int(present[0]) if present.size else grid.minutes
        close = grid.close[first:]
        grid_valid = bool(
            grid.fill_share <= 0.05
            and close.size >= 2
            and np.isfinite(close).all()
            and (close > 0).all()
        )
        if grid_valid:
            returns = log_returns(close)
            observed = np.zeros(grid.minutes, dtype=np.int64)
            actual_minutes = observed_bars["minute"].to_numpy().astype(np.int64)
            actual_close = observed_bars["close"].cast(pl.Float64).to_numpy()
            actual = (actual_minutes >= 0) & (actual_minutes < grid.minutes)
            actual &= np.isfinite(actual_close) & (actual_close > 0)
            observed[actual_minutes[actual]] = 1
            observed_prefix = np.r_[0, np.cumsum(observed)]
    for horizon in (*HORIZONS, CONTROL_HORIZON):
        values = np.full(count, np.nan, dtype=np.float64)
        reason = np.full(count, "missing_bar_grid", dtype=object)
        if grid is not None and observed_bars is not None:
            reason[:] = "session_quality"
            if grid_valid and close.size >= horizon + 1:
                assert observed_prefix is not None and returns is not None
                inside = (origins >= first) & (origins + horizon < grid.minutes)
                reason[:] = "outside_target_grid"
                complete = np.zeros(count, dtype=bool)
                complete[inside] = (
                    observed_prefix[origins[inside] + horizon + 1]
                    - observed_prefix[origins[inside]]
                    == horizon + 1
                )
                reason[inside] = "unobserved_target_close"
                valid = inside & complete
                if valid.any():
                    values[valid] = forward_measures(returns, origins[valid] - first, horizon).rv
                reason[valid] = "observed_target"
        name = f"rv_{horizon}" if horizon != CONTROL_HORIZON else "rv30_reconstructed"
        result = result.with_columns(
            pl.Series(name, values, dtype=pl.Float64),
            pl.Series(f"target_status_{horizon}", reason, dtype=pl.String),
        )
    return result


def attach_target_ends(base: pl.DataFrame, reconstructed: pl.DataFrame) -> pl.DataFrame:
    """Produce exactly the target sidecar; the inherited 30-minute end stays in base."""
    assert_keys(base)
    assert_keys(reconstructed)
    assert_frame_equal(base.select(KEYS).sort(KEYS), reconstructed.select(KEYS).sort(KEYS))
    clock_type = pl.Datetime("us", "UTC")
    if (
        base.schema.get("forecast_origin_utc") != clock_type
        or base.schema.get("target_end_utc") != clock_type
        or base["forecast_origin_utc"].null_count()
        or base["target_end_utc"].null_count()
    ):
        raise ValueError("RP4_V4_TARGET_CLOCK_SCHEMA")
    if not base.select(
        (pl.col("forecast_origin_utc") + pl.duration(minutes=30) == pl.col("target_end_utc"))
        .all()
        .alias("same")
    ).item():
        raise ValueError("RP4_V4_INHERITED_THIRTY_MINUTE_END_MISMATCH")
    clocks = base.select(
        *KEYS,
        *[
            (pl.col("forecast_origin_utc") + pl.duration(minutes=horizon)).alias(
                f"target_end_{horizon}_utc"
            )
            for horizon in HORIZONS
        ],
    )
    return (
        reconstructed.select(KEYS + [f"rv_{h}" for h in HORIZONS])
        .join(clocks, on=KEYS, how="inner", validate="1:1")
        .sort(KEYS)
    )


def compare_float_columns(
    joined: pl.DataFrame, left: str, right: str, *, label: str
) -> tuple[dict[str, Any], pl.DataFrame]:
    """Distinguish actual float64 bit equality, null/NaN masks, and tolerance equality."""
    a = joined[left].cast(pl.Float64).to_numpy()
    b = joined[right].cast(pl.Float64).to_numpy()
    null_a = joined[left].is_null().to_numpy()
    null_b = joined[right].is_null().to_numpy()
    both_nonnull = ~null_a & ~null_b
    finite_a, finite_b = np.isfinite(a), np.isfinite(b)
    both_finite = finite_a & finite_b
    bits_equal = a.view(np.uint64) == b.view(np.uint64)
    both_nan = np.isnan(a) & np.isnan(b) & both_nonnull
    semantic_equal = (null_a & null_b) | both_nan | (both_nonnull & bits_equal)
    byte_equal = (null_a & null_b) | (both_nonnull & bits_equal)
    magnitude = np.abs(a[both_finite] - b[both_finite])
    tolerance_equal = np.isclose(a, b, rtol=1e-8, atol=1e-12, equal_nan=True)
    reason = np.full(joined.height, "finite_float_bits_differ", dtype=object)
    reason[finite_a != finite_b] = "finite_mask_mismatch"
    reason[null_a != null_b] = "null_mask_mismatch"
    reason[both_nan & ~bits_equal] = "nan_payload_bits_differ"
    mismatches = (
        joined.filter(pl.Series(~byte_equal))
        .select(
            *KEYS,
            pl.lit(label).alias("comparison"),
            pl.col(left).alias("reconstructed"),
            pl.col(right).alias("reference"),
        )
        .with_columns(pl.Series("reason", reason[~byte_equal], dtype=pl.String))
    )
    summary = {
        "comparison": label,
        "matched_keys": joined.height,
        "finite_pairs": int(both_finite.sum()),
        "finite_bit_mismatches": int((both_finite & ~bits_equal).sum()),
        "finite_mask_mismatches": int((finite_a != finite_b).sum()),
        "null_mask_mismatches": int((null_a != null_b).sum()),
        "both_null": int((null_a & null_b).sum()),
        "both_nan_nonnull": int(both_nan.sum()),
        "nan_payload_bit_mismatches": int((both_nan & ~bits_equal).sum()),
        "all_value_bit_mismatches": int((~byte_equal).sum()),
        "semantic_mismatches": int((~semantic_equal).sum()),
        "tolerance_mismatches": int((~tolerance_equal | (null_a != null_b)).sum()),
        "max_abs_difference_finite": float(magnitude.max()) if magnitude.size else None,
        "mean_abs_difference_finite": float(magnitude.mean()) if magnitude.size else None,
        "atol_for_separate_tolerance_audit": 1e-12,
        "rtol_for_separate_tolerance_audit": 1e-8,
    }
    return summary, mismatches


def reference_comparison(
    reconstructed: pl.DataFrame, registered: pl.DataFrame
) -> tuple[dict[str, Any], pl.DataFrame]:
    assert_keys(reconstructed)
    assert_keys(registered)
    renamed = registered.select(KEYS + [f"rv_{h}" for h in HORIZONS]).rename(
        {f"rv_{h}": f"reference_{h}" for h in HORIZONS}
    )
    joined = reconstructed.join(renamed, on=KEYS, how="inner", validate="1:1").sort(KEYS)
    summaries = {}
    differences = []
    for horizon in HORIZONS:
        summary, mismatch = compare_float_columns(
            joined, f"rv_{horizon}", f"reference_{horizon}", label=f"registered_rv_{horizon}"
        )
        summaries[f"rv_{horizon}"] = summary
        differences.append(mismatch)
    return {
        "registered_rows": registered.height,
        "reconstructed_rows": reconstructed.height,
        "intersecting_keys": joined.height,
        "registered_only_keys": registered.join(
            reconstructed.select(KEYS), on=KEYS, how="anti"
        ).height,
        "reconstructed_only_keys": reconstructed.join(
            registered.select(KEYS), on=KEYS, how="anti"
        ).height,
        "by_target": summaries,
        "mask_difference": (
            "Original Block3 permits session forward-fill <=5%; RP4 additionally requires "
            "h+1 actual finite positive closes in each target window. No target is filled."
        ),
    }, pl.concat(differences)


def keyed_float_digest(frame: pl.DataFrame, column: str) -> str:
    """Hash canonical sorted key CSV, null bytes, then little-endian float64 value bytes."""
    assert_keys(frame)
    ordered = frame.sort(KEYS)
    key_bytes = ordered.select(KEYS).write_csv().encode("utf-8")
    values = ordered[column].cast(pl.Float64)
    raw = np.asarray(values.to_numpy(), dtype="<f8")
    digest = hashlib.sha256()
    digest.update(
        json.dumps({"column": column, "keys_bytes": len(key_bytes)}, sort_keys=True).encode()
    )
    digest.update(key_bytes)
    digest.update(values.is_null().to_numpy().astype(np.uint8).tobytes())
    digest.update(raw.tobytes())
    return digest.hexdigest()


def inherited_census(
    base: pl.DataFrame, reconstructed: pl.DataFrame, specification: dict[str, Any]
) -> tuple[dict[str, int], pl.DataFrame, pl.DataFrame]:
    """Use the original mask before target joining; never shrink it to fit a new target."""
    assert_keys(base)
    assert_keys(reconstructed)
    assert_frame_equal(base.select(KEYS).sort(KEYS), reconstructed.select(KEYS).sort(KEYS))
    eligible, _, _, _ = panel_masks(base.to_pandas(), specification)
    keyed = base.select(KEYS).with_columns(pl.Series("eligible_v3", eligible))
    joined = keyed.join(reconstructed, on=KEYS, how="left", validate="1:1")
    failures = []
    counts = {}
    coverage = []
    for horizon in HORIZONS:
        name = f"rv_{horizon}"
        finite_positive = pl.col(name).is_finite().fill_null(False) & (pl.col(name) > 0).fill_null(
            False
        )
        failure = joined.filter(pl.col("eligible_v3") & ~finite_positive).select(
            *KEYS,
            pl.lit(name).alias("target"),
            pl.col(name).alias("value"),
            pl.col(f"target_status_{horizon}").alias("status"),
        )
        counts[name] = failure.height
        failures.append(failure)
        coverage.append(
            joined.group_by("asset")
            .agg(
                pl.len().alias("origins"),
                pl.col("eligible_v3").sum().alias("eligible_v3"),
                pl.col(name).is_finite().fill_null(False).sum().alias("finite"),
                finite_positive.sum().alias("finite_positive"),
                (pl.col("eligible_v3") & ~finite_positive).sum().alias("eligible_v3_invalid"),
            )
            .with_columns(pl.lit(name).alias("target"))
        )
    return counts, pl.concat(failures), pl.concat(coverage).sort("target", "asset")


def select_bar_pins(all_pins: dict[str, str]) -> dict[str, str]:
    original = {(DATA_ROOT / relative).resolve() for _, _, relative in BAR_SOURCES}
    selected = {
        str(Path(name).resolve()): value
        for name, value in all_pins.items()
        if Path(name).resolve() in original
        or (
            Path(name).suffix == ".parquet"
            and Path(name).resolve().is_relative_to(ADDED_BAR_ROOT.resolve())
        )
    }
    if not original.issubset({Path(name) for name in selected}) or len(selected) != 285:
        raise ValueError("RP4_V4_PINNED_BAR_SET_INCOMPLETE")
    return selected


def verify_pins(pins: dict[str, str]) -> None:
    for name, expected in pins.items():
        if sha256(Path(name)) != expected:
            raise ValueError(f"RP4_V4_TARGET_SOURCE_DRIFT:{name}")


def write_parquet_once(path: Path, frame: pl.DataFrame) -> None:
    import io

    buffer = io.BytesIO()
    frame.write_parquet(buffer)
    write_bytes_once(path, buffer.getvalue())


def selected_base_columns(
    schema: Mapping[str, pl.DataType], specification: dict[str, Any]
) -> list[str]:
    """Match panel_masks: rp4_eligible is optional, not a new mandatory predictor."""
    required = list(
        dict.fromkeys(
            KEYS
            + ["rv30", "forecast_origin_utc", "target_end_utc"]
            + specification["mandatory_predictors"]
        )
    )
    if not set(required).issubset(schema):
        raise ValueError("RP4_V4_REQUIRED_BASE_COLUMN_MISSING")
    return required + (["rp4_eligible"] if "rp4_eligible" in schema else [])


def input_contract(
    specification_path: Path, specification_sha256: str, producer_sha256: str
) -> tuple[dict[str, Any], dict[str, str], dict[str, str]]:
    """Bind authorization, inherited contract and every input before opening any labels."""
    verify_pins({str(specification_path.resolve()): specification_sha256})
    specification: dict[str, Any] = json.loads(specification_path.read_text(encoding="utf-8"))
    if (
        specification.get("schema_version") != "rp4-walkforward-v4"
        or specification.get("primary_horizon_minutes") != 15
        or specification.get("secondary_horizon_minutes") != 5
        or specification.get("mask_policy")
        != "exact_v3_eligibility_and_30min_causal_end_require_selected_target_finite_positive"
        or specification.get("target_panel_relative_path") != "targets/panel.parquet"
        or Path(specification["data_root"]).resolve() != OUTPUT_ROOT.resolve()
        or specification.get("target_validation", {}).get("strict_observed_closes") != "h_plus_one"
    ):
        raise ValueError("RP4_V4_TARGET_SPECIFICATION_CONTRACT")
    identities = {
        "base_panel": (BASE_PANEL, BASE_SHA),
        "target_reference": (REFERENCE, REFERENCE_SHA),
        "bar_input_pins": (PIN_MANIFEST, PIN_MANIFEST_SHA),
    }
    for field, (path, expected) in identities.items():
        if (
            Path(specification[field]["path"]).resolve() != path.resolve()
            or specification[field]["sha256"] != expected
        ):
            raise ValueError(f"RP4_V4_TARGET_SPEC_SOURCE_CHANGED:{field}")
    if (
        specification["target_reference"]["bytes"] != REFERENCE_BYTES
        or REFERENCE.stat().st_size != REFERENCE_BYTES
    ):
        raise ValueError("RP4_V4_REGISTERED_TARGET_SIZE_MISMATCH")
    parent = specification["parent_specification"]
    freeze_path = specification_path.parent / "freeze_manifest.json"
    frozen: dict[str, Any] = json.loads(freeze_path.read_text(encoding="utf-8"))
    if (
        frozen.get("specification_sha256") != specification_sha256
        or frozen.get("new_targets_opened") != 0
        or frozen.get("model_fits") != 0
        or frozen.get("status") != "FROZEN_BEFORE_TARGET_MATERIALIZATION_AND_FITS"
        or datetime.fromisoformat(frozen["frozen_at_utc"]) >= datetime.now(UTC)
    ):
        raise ValueError("RP4_V4_TARGET_FREEZE_NOT_PRIOR")
    pins = {str(path.resolve()): expected for path, expected in identities.values()} | {
        str(specification_path.resolve()): specification_sha256,
        str(freeze_path.resolve()): sha256(freeze_path),
        str(Path(parent["path"]).resolve()): parent["sha256"],
        str(ROOT / specification["specification_md_path"]): specification[
            "specification_md_sha256"
        ],
        str(ROOT / "docs/rp4/decision_133_v4.md"): specification["decision_sha256"],
        str(ROOT / "artifacts/rp4_v4_code/freeze.py"): frozen["freeze_code_sha256"],
        str(ROOT / PRODUCER_PATH): producer_sha256,
    }
    pins.update({str(ROOT / name): value for name, value in SOURCE_CODE_SHA256.items()})
    verify_pins(pins)
    old = json.loads(Path(parent["path"]).read_text(encoding="utf-8"))
    if any(
        specification[name] != old[name]
        for name in ("mandatory_predictors", "feature_sets", "feature_transforms", "windows")
    ):
        raise ValueError("RP4_V4_TARGET_INHERITED_SAMPLE_CHANGED")
    inherited = json.loads(PIN_MANIFEST.read_text(encoding="utf-8"))["sha256"]
    bar_pins = select_bar_pins(inherited)
    verify_pins(bar_pins)
    pins.update(bar_pins)
    mask_path = ROOT / "artifacts/rp4_v2_code/evaluate_v2.py"
    if (
        Path(inspect.getfile(panel_masks)).resolve() != mask_path
        or Path(inspect.getfile(forward_measures)).resolve() != ROOT / "src/mds650/rp2/realized.py"
    ):
        raise ValueError("RP4_V4_TARGET_IMPORT_OUTSIDE_CHECKOUT")
    pins[str(mask_path)] = sha256(mask_path)
    pins[str(ROOT / "artifacts/rp4_code/evaluate.py")] = sha256(
        ROOT / "artifacts/rp4_code/evaluate.py"
    )
    return specification, pins, bar_pins


def run(args: argparse.Namespace) -> tuple[dict[str, Any], int]:
    if args.output_root.resolve() != OUTPUT_ROOT.resolve() or not 1 <= args.workers <= 4:
        raise ValueError("RP4_V4_TARGET_OUTPUT_OR_WORKERS_INVALID")
    output = args.output_root.resolve() / "targets"
    if (output / "manifest.json").exists():
        raise ValueError("RP4_V4_TARGET_MATERIALIZATION_ALREADY_COMPLETE")
    specification, pins, bar_pins = input_contract(
        args.spec, args.spec_sha256, args.producer_sha256
    )
    started = datetime.now(UTC)
    input_pin_path = output / f"input_pins_{args.producer_sha256[:12]}.json"
    write_json_once(input_pin_path, {"sha256": pins, "bar_files": len(bar_pins)})
    # Import only after verifying the unchanged loader's source hashes. The wrapper
    # enriches its returned grid with observed closes, without a global monkeypatch.
    from artifacts.rp4_v3_code.materialize_gamma import paired_price_grids

    selected_columns = selected_base_columns(pl.read_parquet_schema(BASE_PANEL), specification)
    base = pl.read_parquet(BASE_PANEL, columns=selected_columns).sort(KEYS)
    assert_keys(base)
    if base.height != 195_479 or base["session_date"].n_unique() != 504:
        raise ValueError("RP4_V4_TARGET_BASE_KEY_UNIVERSE_CHANGED")
    eligible, _, _, _ = panel_masks(base.to_pandas(), specification)
    keyed_eligibility = base.select(KEYS).with_columns(pl.Series("eligible_v3", eligible))
    grids = paired_price_grids(bar_pins)
    reconstructed = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        tasks = {}
        for (asset, session), group in base.select(KEYS).group_by(
            ["asset", "session_date"], maintain_order=True
        ):
            grid, observed = grids.get((str(asset), str(session)), (None, None))
            tasks[pool.submit(session_targets, group, grid, observed)] = (asset, session)
        for number, task in enumerate(as_completed(tasks), 1):
            try:
                reconstructed.append(task.result())
            except Exception as error:
                asset, session = tasks[task]
                for other in tasks:
                    other.cancel()
                raise ValueError(
                    f"RP4_V4_TARGET_SESSION_FAILED:{asset}:{session}:{error}"
                ) from error
            if number % 200 == 0 or number == len(tasks):
                print(
                    json.dumps({"completed_session_assets": number, "total": len(tasks)}),
                    flush=True,
                )
    rebuilt = pl.concat(reconstructed).sort(KEYS)
    assert_frame_equal(base.select(KEYS), rebuilt.select(KEYS), check_exact=True)
    sidecar = attach_target_ends(base, rebuilt)
    counts, failures, coverage = inherited_census(base, rebuilt, specification)
    statuses = rebuilt.select(KEYS + [f"target_status_{h}" for h in (*HORIZONS, 30)]).join(
        keyed_eligibility, on=KEYS, validate="1:1"
    )
    census = pl.concat(
        [
            statuses.group_by("asset", "session_date", "eligible_v3", f"target_status_{h}")
            .len()
            .rename({f"target_status_{h}": "status"})
            .with_columns(pl.lit(h).alias("horizon"))
            for h in (*HORIZONS, 30)
        ]
    ).sort("session_date", "asset", "horizon", "eligible_v3", "status")
    reference = pl.read_parquet(REFERENCE, columns=KEYS + [f"rv_{h}" for h in HORIZONS])
    reference_summary, reference_differences = reference_comparison(rebuilt, reference)
    eligible_keys = keyed_eligibility.filter(pl.col("eligible_v3")).select(KEYS)
    reference_summary["eligible_v3_only"] = reference_comparison(
        rebuilt.join(eligible_keys, on=KEYS, validate="1:1"), reference
    )[0]["by_target"]
    reference_differences = reference_differences.join(keyed_eligibility, on=KEYS, validate="m:1")
    control, control_differences = compare_float_columns(
        rebuilt.join(base.select(KEYS + ["rv30"]), on=KEYS, validate="1:1"),
        "rv30_reconstructed",
        "rv30",
        label="unchanged_base_rv30_control",
    )
    reference_clean = all(
        record["finite_bit_mismatches"] == 0 and record["finite_mask_mismatches"] == 0
        for record in reference_summary["by_target"].values()
    )
    control_clean = control["finite_bit_mismatches"] == 0 and control["finite_mask_mismatches"] == 0
    preflight_pass = not any(counts.values()) and reference_clean and control_clean
    artifact_paths = []
    for name, frame in {
        "panel.parquet": sidecar,
        "target_status.parquet": statuses,
        "reference_discrepancies.parquet": reference_differences,
        "rv30_control_discrepancies.parquet": control_differences,
        "invalid_eligible.parquet": failures,
    }.items():
        path = output / name
        write_parquet_once(path, frame)
        artifact_paths.append(path)
    for name, frame in {"coverage.csv": coverage, "session_census.csv": census}.items():
        path = output / name
        write_bytes_once(path, frame.write_csv().encode("utf-8"))
        artifact_paths.append(path)
    for name, value in {
        "reference_comparison.json": reference_summary,
        "rv30_control.json": control,
    }.items():
        path = output / name
        write_json_once(path, value)
        artifact_paths.append(path)
    verify_pins(pins)
    artifact_paths.append(input_pin_path)
    manifest = {
        "schema_version": "rp4-v4-target-materialization-v1",
        "status": "PASS" if preflight_pass else "TARGET_PREFLIGHT_REQUIRES_INVESTIGATION",
        "spec_sha256": args.spec_sha256,
        "producer_path": PRODUCER_PATH,
        "producer_sha256": args.producer_sha256,
        "base_panel_sha256": BASE_SHA,
        "base_panel_unchanged_sha256": True,
        "source_hashes_verified_before_and_after": True,
        "key_set_exact": True,
        "rows": sidecar.height,
        "sessions": sidecar["session_date"].n_unique(),
        "columns": sidecar.columns,
        "dtypes": {name: str(dtype) for name, dtype in sidecar.schema.items()},
        "eligible_v3_rows": int(eligible.sum()),
        "eligible_v3_keys_sha256": hashlib.sha256(
            eligible_keys.sort(KEYS).write_csv().encode("utf-8")
        ).hexdigest(),
        "eligible_v3_invalid": counts,
        "preflight_pass": preflight_pass,
        "reference_float64_exact": reference_clean,
        "rv30_control_exact": control_clean,
        "reference_comparison": reference_summary,
        "rv30_control": control,
        "keyed_float_sha256": {f"rv_{h}": keyed_float_digest(sidecar, f"rv_{h}") for h in HORIZONS},
        "keyed_float_hash_format": (
            "sorted UTF8 key CSV; column+keylength JSON; null uint8 mask; "
            "little-endian float64 bytes"
        ),
        "units": (
            "sum_squared_decimal_natural_log_returns; "
            "no sqrt, annualization, normalization or floor"
        ),
        "target_anchor": (
            "returns[origin-first:origin-first+h], prices origin through origin+h inclusive"
        ),
        "target_observed_rule": (
            "h_plus_one_actual_finite_positive_closes; full_session_fill_share_le_0.05"
        ),
        "inherited_training_end_unchanged": "forecast_origin_utc_plus_30_minutes",
        "confirmation_reference": "NO_VERIFICABLE: registered target reference ends 2026-07-17",
        "excluded_origins": 0,
        "excluded_sessions": 0,
        "model_fits": 0,
        "started_at_utc": started.isoformat(),
        "completed_at_utc": datetime.now(UTC).isoformat(),
        "command_argv": sys.argv,
        "artifacts": {str(path.resolve()): sha256(path) for path in artifact_paths},
        "RESEARCH_ONLY": True,
        "capital_go": False,
    }
    write_json_once(output / "manifest.json", manifest)
    exit_code = 0 if preflight_pass else 2
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "rows": sidecar.height,
                "eligible_v3_invalid": counts,
                "exit_code": exit_code,
                "manifest_sha256": sha256(output / "manifest.json"),
            }
        ),
        flush=True,
    )
    return manifest, exit_code


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--spec-sha256", required=True)
    parser.add_argument("--producer-sha256", required=True)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--workers", type=int, default=4)
    arguments = parser.parse_args(argv)
    return run(arguments)[1]


if __name__ == "__main__":
    raise SystemExit(main())
