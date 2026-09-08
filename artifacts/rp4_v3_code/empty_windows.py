"""Register and materialize only the owner's pre-evaluation empty-window addition."""

from __future__ import annotations

import argparse
import copy
import io
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import polars as pl
from artifacts.rp4_code.evaluate import sha256, write_bytes_once, write_json_once
from polars.testing import assert_frame_equal

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL_SHA = "49b625a4dbca7b725a6b38defc25e76109be7b280d711355a55ce97a7443048b"
INDICATORS = ["b2_5m_window_empty", "b2_30m_window_empty"]
SHAPES = {
    "interarrival_cv",
    "contract_entropy",
    "strike_hhi",
    "expiry_hhi",
    "d_mid_rel",
    "d_iv",
    "d_spread",
    "decay_intensity_innovation",
}
KEYS = ["asset", "session_date", "origin_minute"]
SPEC = ROOT / "artifacts/rp4_v3_a1_empty_window/specification.json"


def affected_columns(features: list[str], minutes: int) -> list[str]:
    prefix = f"b2_{minutes}m_"
    return [
        c
        for c in features
        if c.startswith(prefix) and (c.endswith("_share") or c.removeprefix(prefix) in SHAPES)
    ]


def register() -> None:
    source = ROOT / "artifacts/rp4_v3_a1/specification.json"
    if sha256(source) != ORIGINAL_SHA:
        raise ValueError("RP4_V3_ORIGINAL_FREEZE_DRIFT")
    spec = copy.deepcopy(json.loads(source.read_text(encoding="utf-8")))
    spec["original_v3_specification_sha256"] = ORIGINAL_SHA
    spec["authority_decisions"].append(132)
    spec["empty_window_addendum"] = {
        "md_path": "docs/rp4/v3_window_empty_addendum.md",
        "md_sha256": sha256(ROOT / "docs/rp4/v3_window_empty_addendum.md"),
        "decision_path": "docs/rp4/decision_132_v3_empty_windows.md",
        "decision_sha256": sha256(ROOT / "docs/rp4/decision_132_v3_empty_windows.md"),
        "counts": ["b2_5m_trades", "b2_30m_trades"],
        "indicators": INDICATORS,
        "columns_to_nan": {
            str(m): affected_columns(spec["feature_sets"]["B2"], m) for m in (5, 30)
        },
        "unknown_count": "unknown_indicator_no_recode",
        "no_origin_or_session_exclusion": True,
        "activity_values_unchanged": True,
        "diagnostics": "census_and_B2_over_B1_inside_outside",
    }
    spec["feature_sets"]["B2"] += INDICATORS
    spec["missing_allowed"] += INDICATORS
    spec["feature_transforms"].update(dict.fromkeys(INDICATORS, "raw"))
    spec["evaluation_panel_relative_path"] = "materialized_empty_windows/panel.parquet"
    assert [len(spec["feature_sets"][x]) for x in ("B0", "B1", "B2")] == [29, 69, 138]
    write_json_once(SPEC, spec)
    frozen = {
        "schema_version": "rp4-v3-effective-empty-window-freeze-v1",
        "registered_at_utc": datetime.now(UTC).isoformat(),
        "specification_sha256": sha256(SPEC),
        "original_v3_specification_sha256": ORIGINAL_SHA,
        "original_v3_freeze_sha256": sha256(source.parent / "freeze.json"),
        "addendum": spec["empty_window_addendum"],
        "producer_sha256": sha256(Path(__file__)),
        "v3_models_fitted": 0,
        "v3_materialization_executed": False,
        "capital_go": False,
    }
    write_json_once(SPEC.parent / "freeze.json", frozen)
    print(
        json.dumps(
            {
                "status": "RP4_V3_EMPTY_WINDOW_SPECIFICATION_FROZEN",
                **frozen,
                "freeze_sha256": sha256(SPEC.parent / "freeze.json"),
            }
        ),
        flush=True,
    )


def recode(panel: pl.DataFrame, rule: dict[str, Any]) -> tuple[pl.DataFrame, list[dict[str, Any]]]:
    if panel.select(KEYS).is_duplicated().any() or set(INDICATORS) & set(panel.columns):
        raise ValueError("RP4_V3_EMPTY_WINDOW_KEYS_OR_INDICATORS_INVALID")
    result = panel
    audit = []
    for minutes, indicator in zip((5, 30), INDICATORS, strict=True):
        count = f"b2_{minutes}m_trades"
        values = panel[count]
        valid = values.is_finite().fill_null(False)
        if ((valid & ((values < 0) | (values != values.floor()))).fill_null(False)).any():
            raise ValueError("RP4_V3_EMPTY_WINDOW_INVALID_TRADE_COUNT")
        empty = (valid & (values == 0)).fill_null(False)
        columns = rule["columns_to_nan"][str(minutes)]
        if set(columns) - set(panel.columns):
            raise ValueError("RP4_V3_EMPTY_WINDOW_REGISTERED_COLUMN_MISSING")
        result = result.with_columns(
            [pl.when(empty).then(float("nan")).otherwise(pl.col(c)).alias(c) for c in columns]
        ).with_columns(
            pl.when(valid)
            .then((pl.col(count) == 0).cast(pl.Float64))
            .otherwise(float("nan"))
            .alias(indicator)
        )
        for column in columns:
            before, after = panel[column], result[column]
            if not after.filter(empty).is_nan().all():
                raise ValueError("RP4_V3_EMPTY_WINDOW_RECODE_FAILED")
            assert_frame_equal(
                panel.filter(~empty).select(column),
                result.filter(~empty).select(column),
                check_exact=True,
            )
            audit.append(
                {
                    "window_minutes": minutes,
                    "column": column,
                    "empty_rows": int(empty.sum()),
                    "finite_values_replaced": int(before.filter(empty).is_finite().sum()),
                    "unknown_count_rows": int((~valid).sum()),
                }
            )
    changed = set(rule["columns_to_nan"]["5"]) | set(rule["columns_to_nan"]["30"])
    unchanged = [c for c in panel.columns if c not in changed]
    assert_frame_equal(result.select(unchanged), panel.select(unchanged), check_exact=True)
    return result, audit


def materialize(expected_sha: str) -> None:
    if sha256(SPEC) != expected_sha:
        raise ValueError("RP4_V3_EMPTY_WINDOW_EFFECTIVE_SPEC_HASH_DRIFT")
    spec = json.loads(SPEC.read_text(encoding="utf-8"))
    root = Path(spec["data_root"])
    source = root / "materialized/panel.parquet"
    source_manifest = source.parent / "manifest.json"
    manifest = json.loads(source_manifest.read_text(encoding="utf-8"))
    if (
        manifest["spec_sha256"] != ORIGINAL_SHA
        or manifest["preserved_values_exact_by_keys"] is not True
    ):
        raise ValueError("RP4_V3_EMPTY_WINDOW_GAMMA_SOURCE_CONTRACT")
    pins = {Path(name).resolve(): value for name, value in manifest["artifacts"].items()}
    if pins.get(source.resolve()) != sha256(source):
        raise ValueError("RP4_V3_EMPTY_WINDOW_SOURCE_PANEL_DRIFT")
    panel = pl.read_parquet(source)
    result, audit = recode(panel, spec["empty_window_addendum"])
    output = root / "materialized_empty_windows"
    buffer = io.BytesIO()
    result.write_parquet(buffer)
    write_bytes_once(output / "panel.parquet", buffer.getvalue())
    write_json_once(output / "recode_audit.json", audit)
    census = (
        result.group_by(["asset", "session_date"])
        .agg(
            [
                pl.len().alias("N_origins"),
                *[(pl.col(c) == 1).sum().alias(c + "_count") for c in INDICATORS],
                *[
                    (~pl.col(c).is_finite()).fill_null(True).sum().alias(c + "_unknown")
                    for c in INDICATORS
                ],
            ]
        )
        .sort(["session_date", "asset"])
    )
    write_bytes_once(output / "census.csv", census.write_csv().encode())
    receipt = {
        "status": "RP4_V3_EMPTY_WINDOW_PANEL_COMPLETE",
        "spec_sha256": expected_sha,
        "base_panel_sha256": spec["base_panel"]["sha256"],
        "source_gamma_panel_sha256": sha256(source),
        "source_gamma_manifest_sha256": sha256(source_manifest),
        "preserved_unaffected_values_exact_by_keys": True,
        "preserved_values_exact_by_keys": False,
        "changed_columns_only": spec["empty_window_addendum"]["columns_to_nan"],
        "changed_origins_only": "finite_corresponding_trade_count_equal_zero",
        "excluded_origins": 0,
        "excluded_sessions": 0,
        "model_fits": 0,
        "rows": result.height,
        "columns": result.width,
        "recode_producer_sha256": sha256(Path(__file__)),
        "artifacts": {
            str(p): sha256(p)
            for p in [output / "panel.parquet", output / "recode_audit.json", output / "census.csv"]
        },
        "capital_go": False,
    }
    write_json_once(output / "manifest.json", receipt)
    print(json.dumps({**receipt, "manifest_sha256": sha256(output / "manifest.json")}), flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--register", action="store_true")
    parser.add_argument("--spec-sha256")
    args = parser.parse_args()
    if args.register:
        register()
    elif args.spec_sha256:
        materialize(args.spec_sha256)
    else:
        parser.error("choose --register or --spec-sha256 for materialization")


if __name__ == "__main__":
    main()
