"""RP4 v2: narrow per-trade IV eligibility; reuse frozen v1 producers and keys."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import math
from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from types import FunctionType
from typing import Any

import materialize as v1
import numpy as np
import polars as pl
import rp2_block5_surface_panel as surface_v1
import rp2_block6_flow_panel as flow_v1
from evaluate import write_bytes_once, write_json_once
from polars.testing import assert_frame_equal

from mds650.rp2.bars import (
    BAR_SOURCES,
    _tag_validated_bar_source,
    build_session_grid,
    deduplicate_bar_sources,
    normalise_bars,
)

ROOT = Path(__file__).resolve().parents[2]
OLD_ROOT = Path("private-input/66c0e77362caa29dd928")
OUTPUT_ROOT = Path("private-input/c153d5c8978c23bc439f")
KEYS = v1.KEYS
OLD_MANIFESTS = {
    "a2_combined_v2/manifest.json": (
        "323d404eb6c5d3327722fe318d3b81247a50813d76cfbae135ff877edef01579"
    ),
    "b1_complete_v1/manifest.json": (
        "abe40d6990fbc59bcee6f3912bda1d2dc5c85f488a38ef95dd835cff537577e1"
    ),
}
OLD_PANELS = {
    "a2_combined_v2/panel.parquet": (
        "51f04c5937a7922757f929ef0ca53941b7766719cf2799673669f8545f97a949"
    ),
    "b1_complete_v1/panel.parquet": (
        "ecb1c6cce76cb6464d3cdf3d4ef409c60e204adf2df22fba6851e32199819d93"
    ),
}
V1_CODE = {
    "artifacts/rp4_code/materialize.py": (
        "f1de9af7f07480650ff17ab5dc6d785c823193e2e400f32dc532c2a05d31ded0"
    ),
    "scripts/rp2_block5_surface_panel.py": (
        "60a1c427c67a20da7a0ceb0433a85d1b57f9d6fc86a78f2fc97c24dfb010ee14"
    ),
    "scripts/rp2_block6_flow_panel.py": (
        "87db0062bc3f3a74dc55345152095aed5de3c39795d12c333dca2e127bf87ae8"
    ),
    "src/mds650/rp2/flow.py": "cec7d0beec3595c9be06750e25e480f07ba61eac50f12ea84f6aca2f7b84b1ed",
}
TAPE_COLUMNS = list(dict.fromkeys([*v1.TAPE_COLUMNS, *flow_v1.TAPE_COLUMNS]))


def verify_pin(path: Path, expected: str) -> None:
    if v1.sha256(path) != expected:
        raise ValueError(f"RP4_V2_INPUT_HASH_MISMATCH:{path}")


def pinned_json(path: Path, expected: str) -> dict[str, Any]:
    verify_pin(path, expected)
    value: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return value


def iv_filter(tape: pl.DataFrame) -> pl.DataFrame:
    """The only new tape rule; boundaries are inclusive and non-finite IV is absent."""
    return tape.filter(
        pl.col("implied_volatility").is_finite()
        & pl.col("implied_volatility").is_between(0.03, 3.0, closed="both")
    )


def iv_counts(tape: pl.DataFrame) -> dict[str, int | float]:
    values = tape["implied_volatility"].cast(pl.Float64)
    finite = values.is_finite().fill_null(False)
    old = values.is_between(0.01, 5.0).fill_null(False)
    new = (finite & values.is_between(0.03, 3.0)).fill_null(False)
    rejected = int((~new).sum())
    return {
        "raw_asset_rows": tape.height,
        "iv_null_rows": values.null_count(),
        "iv_nonfinite_nonnull_rows": int((~finite & values.is_not_null()).sum()),
        "iv_below_003_rows": int((finite & (values < 0.03)).sum()),
        "iv_above_3_rows": int((finite & (values > 3.0)).sum()),
        "iv_rejected_total_rows": rejected,
        "iv_rejected_percent": 100.0 * rejected / tape.height if tape.height else 0.0,
        "old_iv_eligible_rows": int(old.sum()),
        "new_iv_eligible_rows": int(new.sum()),
        "newly_rejected_within_old_iv_range": int((old & ~new).sum()),
    }


def bind_reader(producer: Callable[..., Any], tape: pl.DataFrame) -> Callable[..., Any]:
    """Copy function globals, not code: bind this call's reader without global monkeypatches.

    The v1 producer, its helpers, clocks, Greeks and window formulas are unchanged.
    Each worker owns its namespace, so concurrent sessions cannot share a tape.
    """
    namespace = dict(producer.__globals__)
    namespace["_read_tape"] = lambda _paths, _asset: tape
    bound = FunctionType(
        producer.__code__, namespace, producer.__name__, producer.__defaults__, producer.__closure__
    )
    bound.__kwdefaults__ = producer.__kwdefaults__
    return bound


def reader_frames(raw: pl.DataFrame, *, filtered: bool) -> tuple[pl.DataFrame, pl.DataFrame]:
    """Apply the exact existing two readers' projections/quality rules, then v2 IV."""
    surface = (
        raw.select(surface_v1.TAPE_COLUMNS)
        .filter(
            (pl.col("nbbo_bid") > 0.0)
            & (pl.col("nbbo_ask") > pl.col("nbbo_bid"))
            & pl.col("implied_volatility").is_between(0.01, 5.0)
            & pl.col("strike").is_not_null()
        )
        .sort("created_at")
    )
    flow = (
        raw.select(flow_v1.TAPE_COLUMNS)
        .filter(
            (pl.col("size") > 0)
            & pl.col("strike").is_not_null()
            & pl.col("implied_volatility").is_between(0.01, 5.0)
        )
        .sort("created_at")
    )
    return (iv_filter(surface), iv_filter(flow)) if filtered else (surface, flow)


def new_tape(raw: pl.DataFrame) -> pl.DataFrame:
    """Exactly v1.read_new_tape's identity check on its projected columns."""
    tape = raw.select(v1.TAPE_COLUMNS)
    if tape["id"].null_count():
        raise ValueError("RP4_TAPE_EVENT_ID_MISSING")
    duplicates = tape.filter(pl.col("id").is_duplicated())
    if duplicates.height and duplicates.unique().height != duplicates["id"].n_unique():
        raise ValueError("RP4_TAPE_DUPLICATE_ID_CONFLICT")
    return tape.unique(subset="id", keep="first", maintain_order=True)


def complete_columns(
    frame: pl.DataFrame | None, keys: pl.DataFrame, names: list[str]
) -> pl.DataFrame:
    if frame is None or frame.is_empty():
        return keys.with_columns(pl.lit(None, pl.Float64).alias(name) for name in names)
    missing = [name for name in names if name not in frame.columns]
    frame = frame.with_columns(pl.lit(None, pl.Float64).alias(name) for name in missing)
    return keys.join(frame.select(KEYS + names), on=KEYS, how="left", validate="1:1")


def option_features(
    raw: pl.DataFrame,
    base: pl.DataFrame,
    grid: Any,
    columns: list[str],
    *,
    filtered: bool,
) -> pl.DataFrame:
    asset, session = str(base["asset"][0]), str(base["session_date"][0])
    origins = base["origin_minute"].to_numpy().astype(np.int64)
    keys = base.select(KEYS)
    surface_tape, flow_tape = reader_frames(raw, filtered=filtered)
    surface = bind_reader(surface_v1.build_session_surface, surface_tape)(
        asset, session, [], origins, grid.close, base["rv_back_30"].to_numpy()
    )
    flow, _ = bind_reader(flow_v1.build_session_flow, flow_tape)(
        asset, session, [], origins, grid.close, grid.open
    )
    tape = new_tape(raw)
    if filtered:
        tape = iv_filter(tape)
    carry = []
    for name in ("rate", "dividend_cash_prior365"):
        if base[name].n_unique() != 1:
            raise ValueError(f"RP4_V2_SESSION_CARRY_NOT_CONSTANT:{asset}:{session}:{name}")
        value = base[name][0]
        carry.append(float(value) if value is not None else math.nan)
    new = v1.build_new_option_features(tape, asset, session, origins, grid.close, *carry)
    result = keys
    for frame, names in (
        (surface, [name for name in columns if name.startswith("b1_")]),
        (flow, [name for name in columns if name.startswith("b2_")]),
        (new, [name for name in columns if name.startswith("rp4_")]),
    ):
        result = result.join(
            complete_columns(frame, keys, names), on=KEYS, how="left", validate="1:1"
        )
    return result.select(KEYS + columns)


def parity(original: pl.DataFrame, rebuilt: pl.DataFrame, columns: list[str]) -> None:
    """Any non-IV producer drift is an error, not an improvement attributed to v2."""
    assert_frame_equal(original.select(KEYS).sort(KEYS), rebuilt.select(KEYS).sort(KEYS))
    left = original.sort(KEYS).select(columns).to_numpy()
    right = rebuilt.sort(KEYS).select(columns).to_numpy()
    same = np.isclose(left, right, rtol=1e-10, atol=1e-12, equal_nan=True)
    if not same.all():
        bad = [columns[i] for i in np.flatnonzero((~same).any(axis=0))]
        raise ValueError(f"RP4_V2_UNFILTERED_V1_PRODUCER_PARITY:{bad}")


def replace_columns(
    base: pl.DataFrame, replacement: pl.DataFrame, columns: list[str]
) -> pl.DataFrame:
    v1.assert_unique(base)
    v1.assert_unique(replacement)
    assert_frame_equal(base.select(KEYS).sort(KEYS), replacement.select(KEYS).sort(KEYS))
    result = base.drop(columns).join(replacement.select(KEYS + columns), on=KEYS, validate="1:1")
    result = result.select(base.columns).sort(KEYS)
    preserved = [name for name in base.columns if name not in columns]
    assert_frame_equal(
        base.select(preserved).sort(KEYS), result.select(preserved), check_exact=True
    )
    return result


def write_parquet_once(path: Path, frame: pl.DataFrame) -> None:
    buffer = io.BytesIO()
    frame.write_parquet(buffer)
    write_bytes_once(path, buffer.getvalue())


def load_lineage() -> tuple[dict[tuple[str, str], dict[str, Any]], dict[str, str]]:
    manifests = {
        name: pinned_json(OLD_ROOT / name, digest) for name, digest in OLD_MANIFESTS.items()
    }
    pins = {str(OLD_ROOT / name): digest for name, digest in OLD_MANIFESTS.items()}
    pins.update({str(OLD_ROOT / name): digest for name, digest in OLD_PANELS.items()})
    parts = dict(manifests["a2_combined_v2/manifest.json"]["parts"])
    parts[str(OLD_ROOT / "b1_extension_v1/manifest.json")] = manifests[
        "b1_complete_v1/manifest.json"
    ]["extension_manifest_sha256"]
    receipts: dict[tuple[str, str], dict[str, Any]] = {}
    for name, digest in parts.items():
        path = Path(name)
        manifest = pinned_json(path, digest)
        pins[str(path)] = digest
        for input_path, input_hash in manifest["input_sha256"].items():
            if input_path in pins and pins[input_path] != input_hash:
                raise ValueError("RP4_V2_INCONSISTENT_SOURCE_PIN")
            pins[input_path] = input_hash
        for receipt_path in sorted((path.parent / "sessions").glob("*.json")):
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            session, asset = receipt_path.stem.split("_", 1)
            if (asset, session) in receipts:
                raise ValueError("RP4_V2_DUPLICATE_SESSION_RECEIPT")
            receipts[asset, session] = receipt
            pins[str(receipt_path)] = v1.sha256(receipt_path)
            for source, source_hash in receipt["source_sha256"].items():
                if source in pins and pins[source] != source_hash:
                    raise ValueError("RP4_V2_INCONSISTENT_TAPE_PIN")
                pins[source] = source_hash
    return receipts, pins


def load_price_grids(pins: dict[str, str]) -> dict[tuple[str, str], Any]:
    """Pinned v1 bar loader for close/open only; no new discovery or volume overlay read.

    The volume overlay never changes close/open or the close-based fill gate. B0 and
    HARQ are copied, not rebuilt. The per-session unfiltered producer parity proves
    these marks reproduce the v1 option features before the new rule is applied.
    """
    paths = {Path(name).resolve() for name in pins}
    original = []
    for name, role_scope, relative in BAR_SOURCES:
        path = v1.DATA_ROOT / relative
        if path.resolve() in paths:
            frame = normalise_bars(pl.read_parquet(path))
            original.append(_tag_validated_bar_source(frame, name=name, role_scope=role_scope))
    bars = deduplicate_bar_sources(pl.concat(original, how="diagonal"))
    added_root = (OLD_ROOT / "data/fmp").resolve()
    added = [
        normalise_bars(pl.read_parquet(path)).with_columns(
            source=pl.lit("rp4_acquired"), role=pl.lit("RP4")
        )
        for path in sorted(paths)
        if path.suffix == ".parquet" and path.is_relative_to(added_root)
    ]
    bars = deduplicate_bar_sources(pl.concat([bars, *added], how="diagonal_relaxed"))
    return {
        (str(asset), str(session)): build_session_grid(group, session=session)
        for (asset, session), group in bars.group_by(["asset", "session_date"])
    }


def run_session(
    base: pl.DataFrame,
    receipt: dict[str, Any],
    grid: Any,
    columns: list[str],
    output: Path,
    identity: str,
) -> dict[str, Any]:
    asset, session = str(base["asset"][0]), str(base["session_date"][0])
    shard = output / "sessions" / f"{session}_{asset}.parquet"
    receipt_path = shard.with_suffix(".json")
    if receipt_path.exists():
        previous: dict[str, Any] = json.loads(receipt_path.read_text(encoding="utf-8"))
        if previous["identity"] != identity:
            raise ValueError("RP4_V2_SHARD_IDENTITY_CHANGED")
        verify_pin(shard, previous["sha256"])
        return previous
    paths = list(receipt["source_sha256"])
    # All original RP4 receipts contain one file; a changed order cannot be invented.
    if len(paths) != 1:
        raise ValueError("RP4_V2_ORIGINAL_TAPE_ORDER_NOT_PINNED")
    raw = pl.read_parquet(paths[0], columns=TAPE_COLUMNS).filter(
        pl.col("underlying_symbol") == asset
    )
    counts = iv_counts(raw)
    if counts["newly_rejected_within_old_iv_range"] == 0:
        # Equality of old/new eligible row sets proves all three unchanged producers
        # see the same inputs, including predecessor, intensity and snapshot histories.
        replacement = base.select(KEYS + columns)
        reused = True
    else:
        unfiltered = option_features(raw, base, grid, columns, filtered=False)
        parity(base, unfiltered, columns)
        replacement = option_features(raw, base, grid, columns, filtered=True)
        reused = False
    write_parquet_once(shard, replacement)
    result = {
        "asset": asset,
        "session_date": session,
        "identity": identity,
        "sha256": v1.sha256(shard),
        "source_sha256": receipt["source_sha256"],
        "origins": base.height,
        "reused_identical_iv_eligibility": reused,
        "unfiltered_parity_verified": not reused,
        **counts,
    }
    write_json_once(receipt_path, result)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--spec-sha256", required=True)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args(argv)
    if args.output_root.resolve() != OUTPUT_ROOT.resolve() or not 1 <= args.workers <= 6:
        raise ValueError("RP4_V2_OUTPUT_OR_WORKERS_INVALID")
    spec = pinned_json(args.spec, args.spec_sha256)
    verify_pin(ROOT / "docs/rp4/specification_v2.md", spec["specification_md_sha256"])
    for path, digest in V1_CODE.items():
        verify_pin(ROOT / path, digest)
    output = args.output_root / "materialized"
    if (output / "manifest.json").exists():
        raise ValueError("RP4_V2_MATERIALIZATION_ALREADY_COMPLETE")
    columns = [
        name for name in spec["feature_sets"]["B2"] if name.startswith(("b1_", "b2_", "rp4_"))
    ]
    if len(columns) != len(set(columns)) or set(spec["feature_sets"]["B0"]) & set(columns):
        raise ValueError("RP4_V2_REPLACEMENT_COLUMNS_INVALID")
    receipts, pins = load_lineage()
    for name, digest in pins.items():
        verify_pin(Path(name), digest)
    pins[str(args.spec.resolve())] = args.spec_sha256
    pins[str(Path(__file__).resolve())] = v1.sha256(Path(__file__))
    identity = hashlib.sha256(json.dumps(pins, sort_keys=True).encode()).hexdigest()
    write_json_once(output / "input_pins.json", {"identity": identity, "sha256": pins})
    panel = pl.read_parquet(OLD_ROOT / "b1_complete_v1/panel.parquet").sort(KEYS)
    development = pl.read_parquet(OLD_ROOT / "a2_combined_v2/panel.parquet").sort(KEYS)
    assert_frame_equal(
        panel.filter(pl.col("session_date") <= "2026-07-31"), development, check_exact=True
    )
    grids = load_price_grids(pins)
    results = []
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending = {}
        for key, base in panel.group_by(["asset", "session_date"], maintain_order=True):
            asset, session = map(str, key)
            if (asset, session) not in receipts or (asset, session) not in grids:
                raise ValueError(f"RP4_V2_ORIGINAL_SESSION_INPUT_MISSING:{asset}:{session}")
            future = pool.submit(
                run_session,
                base,
                receipts[asset, session],
                grids[asset, session],
                columns,
                output,
                identity,
            )
            pending[future] = (asset, session)
        for future in as_completed(pending):
            try:
                results.append(future.result())
            except Exception as error:
                asset, session = pending[future]
                for remaining in pending:
                    remaining.cancel()
                raise ValueError(f"RP4_V2_SESSION_FAILED:{asset}:{session}:{error}") from error
            if len(results) % 20 == 0:
                print(
                    json.dumps(
                        {"materialized_session_assets": len(results), "total": len(pending)}
                    ),
                    flush=True,
                )
    replacements = pl.concat(
        [
            pl.read_parquet(output / "sessions" / f"{row['session_date']}_{row['asset']}.parquet")
            for row in results
        ],
        how="vertical_relaxed",
    )
    changed = replace_columns(panel, replacements, columns)
    write_parquet_once(output / "panel.parquet", changed)
    counts = pl.DataFrame(
        [
            {
                key: value
                for key, value in row.items()
                if key not in {"source_sha256", "identity", "sha256"}
            }
            for row in results
        ]
    ).sort("asset", "session_date")
    write_bytes_once(output / "iv_filter_counts.csv", counts.write_csv().encode())
    write_bytes_once(output / "coverage.csv", v1.coverage_table(changed).write_csv().encode())
    for name, digest in pins.items():
        verify_pin(Path(name), digest)
    manifest = {
        "schema_version": "rp4-v2-iv-materialization-v1",
        "spec_sha256": args.spec_sha256,
        "code_sha256": v1.sha256(Path(__file__)),
        "input_identity": identity,
        "v1_code_sha256": V1_CODE,
        "rows": changed.height,
        "sessions": changed["session_date"].n_unique(),
        "replaced_columns": columns,
        "preserved_columns": [name for name in panel.columns if name not in columns],
        "preserved_values_exact_by_keys": True,
        "iv_inclusive_bounds": [0.03, 3.0],
        "raw_asset_rows": int(counts["raw_asset_rows"].sum()),
        "iv_rejected_total_rows": int(counts["iv_rejected_total_rows"].sum()),
        "newly_rejected_within_old_iv_range": int(
            counts["newly_rejected_within_old_iv_range"].sum()
        ),
        "reused_session_assets": int(counts["reused_identical_iv_eligibility"].sum()),
        "unfiltered_parity_session_assets": int(counts["unfiltered_parity_verified"].sum()),
        "artifacts": {
            str(output / name): v1.sha256(output / name)
            for name in ["panel.parquet", "iv_filter_counts.csv", "coverage.csv", "input_pins.json"]
        },
        "model_fits": 0,
        "provider_requests": 0,
        "phase9_modified": False,
        "RESEARCH_ONLY": True,
        "capital_go": False,
    }
    write_json_once(output / "manifest.json", manifest)
    print(
        json.dumps(
            {
                "status": "PASS_RP4_V2_IV_MATERIALIZATION",
                "manifest_sha256": v1.sha256(output / "manifest.json"),
                "rows": changed.height,
            }
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
