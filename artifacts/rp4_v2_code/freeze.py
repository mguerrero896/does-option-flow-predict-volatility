"""Register the narrowly scoped RP4 v2 contract without opening targets or fitting."""

from __future__ import annotations

import copy
import json
from pathlib import Path

from artifacts.rp4_code.evaluate import sha256, write_json_once

ROOT = Path(__file__).resolve().parents[2]
V1_SHA = "865865558087108356f4eb6da7f9d431f1c4d32fd330f20ea78eb126ec6462a5"
REMOVED = [
    "b1_implied_rate",
    "b1_implied_dividend_yield",
    "b1_pcp_residual",
    "b2_5m_late_arrival_share",
    "b2_30m_late_arrival_share",
    "b2_5m_mean_provider_latency_s",
    "b2_30m_mean_provider_latency_s",
    "b2_5m_is_empty_window",
    "b2_30m_is_empty_window",
    "b2_5m_observed_span_s",
    "b2_30m_observed_span_s",
    "b1_median_quote_age_s",
]


def main() -> None:
    source = ROOT / "artifacts/rp4_a1/specification.json"
    if sha256(source) != V1_SHA:
        raise ValueError("RP4_V2_PARENT_SPEC_HASH_MISMATCH")
    spec = copy.deepcopy(json.loads(source.read_text(encoding="utf-8")))
    spec.update(
        {
            "schema_version": "rp4-walkforward-v2",
            "authority_decisions": [128, 129, 130],
            "parent_specification_sha256": V1_SHA,
            "data_root": "private-input/c153d5c8978c23bc439f",
            "v1_data_root": "private-input/66c0e77362caa29dd928",
            "specification_md_path": "docs/rp4/specification_v2.md",
            "specification_md_sha256": sha256(ROOT / "docs/rp4/specification_v2.md"),
            "decision_sha256": sha256(ROOT / "docs/rp4/decision_130_v2.md"),
            "allow_missing_only_grid": False,
            "removed_in_v2": REMOVED,
        }
    )
    for name in ("B0", "B1", "B2"):
        spec["feature_sets"][name] = [c for c in spec["feature_sets"][name] if c not in REMOVED]
    if [len(spec["feature_sets"][x]) for x in ("B0", "B1", "B2")] != [29, 69, 132]:
        raise ValueError("RP4_V2_FEATURE_COUNT_MISMATCH")
    spec["mandatory_predictors"] = spec["feature_sets"]["B0"]
    spec["missing_allowed"] = [
        c for c in spec["feature_sets"]["B2"] if c not in spec["mandatory_predictors"]
    ]
    for family in ("B1", "B2"):
        spec["excluded_registered_predictors"][family] = sorted(
            set(spec["excluded_registered_predictors"][family])
            | {c for c in REMOVED if c.startswith(family.lower() + "_")}
        )
    spec["model"]["families"] = ["log_ridge_harq", "lightgbm_qlike"]
    del spec["model"]["ols"]
    spec["model"]["ridge"] = {
        "lambda_grid": [1e-4, 1e-2, 1.0, 1e2, 1e4],
        "objective": "sum_squared_log_residuals_plus_lambda_l2_slopes",
        "smearing": "duan_arithmetic_training",
        "imputation": "training_median_after_v1_pointwise_transforms",
        "indicators": "presence_all_optional_predictors",
        "standardization": "training_mean_population_sd",
        "all_missing": "drop_without_inventing_median",
        "collinearity": "pivoted_qr",
        "qr_relative_tolerance": 1e-10,
        "tie_break": "larger_lambda",
        "forecast_bounds": [0.1, 10.0],
        "forecast_bounds_reference": "minimum_and_maximum_positive_training_rv30",
    }
    spec["model"]["lightgbm"].update(
        {"num_leaves": [15, 31, 63], "num_boost_round": 2000, "early_stopping_rounds": 50}
    )
    spec["iv_filter"] = {
        "lower": 0.03,
        "upper": 3.0,
        "inclusive": True,
        "nonfinite": "discard",
        "scope": "trade_rows_before_all_three_option_producers",
        "keep_non_option_columns_exact": True,
    }
    spec["secondary"]["tails"] = {
        "contrast_median": True,
        "symmetric_trim_each_tail": 0.05,
        "trim_rounding": "floor",
        "top_loss_sessions": 10,
        "top_loss_scope": "per_family_and_information_set",
        "tie_break": "date_ascending",
    }
    spec["input_panels"] = {
        "development": {
            "path": "private-input/c1ae6ab902047da171cf",
            "sha256": "51f04c5937a7922757f929ef0ca53941b7766719cf2799673669f8545f97a949",
        },
        "combined": {
            "path": "private-input/16baf18760d99542f617",
            "sha256": "ecb1c6cce76cb6464d3cdf3d4ef409c60e204adf2df22fba6851e32199819d93",
        },
    }
    out = ROOT / "artifacts/rp4_v2_a1"
    write_json_once(out / "specification.json", spec)
    frozen = {
        "schema_version": "rp4-v2-freeze-v1",
        "specification_sha256": sha256(out / "specification.json"),
        "specification_md_sha256": spec["specification_md_sha256"],
        "decision_sha256": spec["decision_sha256"],
        "parent_specification_sha256": V1_SHA,
        "models_fitted": 0,
        "target_values_read": 0,
        "capital_go": False,
    }
    write_json_once(out / "freeze.json", frozen)
    print(
        json.dumps(
            {
                "status": "RP4_V2_SPECIFICATION_FROZEN",
                **frozen,
                "freeze_sha256": sha256(out / "freeze.json"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
