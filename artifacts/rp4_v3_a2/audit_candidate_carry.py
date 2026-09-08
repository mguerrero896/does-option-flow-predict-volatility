"""Target-blind attribution of the seven NVDA candidate/legacy discrepancies.

This diagnostic never modifies a materialization or invokes a model. It changes
only dividend_cash in the already frozen independent legacy derivation.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import polars as pl

import materialize_gamma as m


def main() -> int:
    output = m.OUTPUT_ROOT / "operations" / "candidate_carry_audit.json"
    if output.exists():
        raise ValueError("CARRY_AUDIT_ALREADY_EXISTS")
    pins_path = m.OUTPUT_ROOT / "materialized" / "input_pins.json"
    m.rp4_v2.verify_pin(
        pins_path, "ca610184b4ccffe2d5792e86d8babefc12ebee52b38e5b1d16f8c2f7465606db"
    )
    pins = json.loads(pins_path.read_text())["sha256"]
    m.rp4_v2.verify_pin(
        m.ROOT / "artifacts/rp4_v3_code/materialize_gamma.py",
        "2f59184b5a36b301252bb11eaf779c8128cef0f45266368f44b1a7d35f3644a3",
    )
    m.rp4_v2.verify_pin(m.CANDIDATE, m.SOURCE_PINS[str(m.CANDIDATE)])
    m.rp4_v2.verify_pin(m.V2_ROOT / "panel.parquet", m.SOURCE_PINS[str(m.V2_ROOT / "panel.parquet")])
    legacy_path = m.OUTPUT_ROOT / "materialized" / "independent_legacy.parquet"
    m.rp4_v2.verify_pin(
        legacy_path, "4c46cb656833955df1c83830e069baa3f56647aecc95a89b52d8950e3f429cc9"
    )
    base = pl.read_parquet(
        m.V2_ROOT / "panel.parquet", columns=m.KEYS + ["rate", "dividend_cash_prior365"]
    )
    candidate = pl.read_parquet(m.CANDIDATE)
    legacy = pl.read_parquet(legacy_path)
    old_rates, old_dividends, old_paths = m.rp4.exogenous_sources(m.rp4_v2.OLD_ROOT)
    new_rates, new_dividends, new_paths = m.rp4.exogenous_sources(
        m.rp4_v2.OLD_ROOT, updated_dividends=True
    )
    exogenous_pins = {}
    for path in dict.fromkeys(old_paths + new_paths):
        digest = pins[str(path)]
        m.rp4_v2.verify_pin(path, digest)
        exogenous_pins[str(path)] = digest
    carry_changes = []
    carry = base.select("asset", "session_date", "rate", "dividend_cash_prior365").unique()
    for asset, session, rate, cash in carry.sort("asset", "session_date").iter_rows():
        old = m.rp4.carry_for_session(session, asset, old_rates, old_dividends)
        updated = m.rp4.carry_for_session(session, asset, new_rates, new_dividends)
        if old != (rate, cash):
            assert old[0] == rate
            assert updated == (rate, cash)
            assert abs(cash - old[1] - 0.25) < 1e-12
            carry_changes.append(
                {
                    "asset": asset,
                    "session_date": session,
                    "rate": rate,
                    "candidate_old_cash": old[1],
                    "pinned_v2_cash": cash,
                }
            )
    expected_sessions = [
        "2026-08-27", "2026-08-28", "2026-08-31", "2026-09-01",
        "2026-09-02", "2026-09-03", "2026-09-04",
    ]
    assert [(row["asset"], row["session_date"]) for row in carry_changes] == [
        ("NVDA", session) for session in expected_sessions
    ]
    grids = m.rp4_v2.load_price_grids(pins)
    tape_index = m.rp4.tape_index(m.rp4_v2.OLD_ROOT)
    parts = []
    selected_source_pins = {}
    rows = []
    for item in carry_changes:
        asset, session = item["asset"], item["session_date"]
        subset = base.filter((pl.col("asset") == asset) & (pl.col("session_date") == session))
        source_paths = tape_index.get((session, asset)) or tape_index[session, "__ALL__"]
        receipt_path = m.OUTPUT_ROOT / "materialized/sessions" / f"{session}_{asset}.json"
        receipt = json.loads(receipt_path.read_text())
        assert {str(Path(path).resolve()) for path in source_paths} == {
            str(Path(path).resolve()) for path in receipt["source_sha256"]
        }
        for path in source_paths:
            digest = pins[str(path)]
            m.rp4_v2.verify_pin(Path(path), digest)
            selected_source_pins[str(path)] = digest
        raw = pl.concat(
            [
                pl.read_parquet(path, columns=m.TAPE_COLUMNS).filter(
                    pl.col("underlying_symbol") == asset
                )
                for path in source_paths
            ],
            how="vertical_relaxed",
        )
        grid = grids[asset, session]
        reconstructed, _ = m.derive_session(
            raw, asset, session, subset["origin_minute"].to_numpy().astype(np.int64),
            grid.close, grid.open, item["rate"], item["candidate_old_cash"],
            iv_bounds=m.IV_LEGACY, causal=False,
        )
        expected = candidate.filter(
            (pl.col("asset") == asset) & (pl.col("session_date") == session)
        )
        comparisons = m.compare_panels(expected, reconstructed, "old_cash_only", "cash only")
        for comparison in comparisons:
            if comparison["asset"] == "ALL":
                assert comparison["outside_tolerance_pairs"] == 0
                assert comparison["only_left_finite"] == comparison["only_right_finite"] == 0
                rows.append({**item, **comparison})
        parts.append(reconstructed)
        print(json.dumps({"carry_attribution_session_pass": session}), flush=True)
    replacement = pl.concat(parts)
    other = legacy.join(replacement.select(m.KEYS), on=m.KEYS, how="anti")
    audit_bridge = pl.concat([other, replacement]).sort(m.KEYS)
    final_comparison = [
        row for row in m.compare_panels(candidate, audit_bridge, "candidate_cash_restored", "cash only")
        if row["asset"] == "ALL"
    ]
    for row in final_comparison:
        assert row["outside_tolerance_pairs"] == 0
        assert row["maximum_absolute_difference"] == 0.0
    old_events = old_dividends["NVDA"]
    new_events = new_dividends["NVDA"]
    new_event = [event for event in new_events if event not in old_events]
    result = {
        "status": "PASS_EXACT_CANDIDATE_DIFFERENCE_ATTRIBUTION",
        "code_sha256": m.rp4.sha256(Path(__file__)),
        "materializer_unchanged_sha256": m.rp4.sha256(m.ROOT / "artifacts/rp4_v3_code/materialize_gamma.py"),
        "source_input_pins_sha256": m.rp4.sha256(pins_path),
        "cause": "Candidate uses old dividend snapshot; v2 extension uses verified updated snapshot",
        "changed_parameter": "dividend_cash only; rates/tape/bars/formula/directions/keys unchanged",
        "affected_asset_sessions": carry_changes,
        "affected_origins": replacement.height,
        "unchanged_asset_sessions": carry.height - len(carry_changes),
        "updated_dividend_events_not_in_old_snapshot": new_event,
        "per_session_comparisons": rows,
        "all_195479_rows_after_cash_only_attribution": final_comparison,
        "exogenous_source_sha256": exogenous_pins,
        "selected_tape_sha256": selected_source_pins,
        "production_files_modified": False,
        "model_fits": 0,
        "target_columns_read": [],
        "new_predictor_or_model_selection": False,
    }
    m.rp4_v2.write_json_once(output, result)
    print(json.dumps({"status": result["status"], "receipt": str(output), "sha256": m.rp4.sha256(output)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
