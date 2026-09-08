"""Freeze RP4 v3's complete contract before materialization or model evaluation."""

from __future__ import annotations

import copy
import json
from datetime import UTC, datetime
from pathlib import Path

from artifacts.rp4_code.evaluate import sha256, write_json_once

ROOT = Path(__file__).resolve().parents[2]
V2_SHA = "08a749049f56a0d1dda09cef1f280328e7c84d59fc39d57e71c48caee81670a5"
BASE_SHA = "5b7dd5cc4b2b1e64446d305a5ee0de92f6d18e790f94b5840664947da00fd19d"
ADDENDUM_SHA = "81a20523b205e014bd2e910272e280e6c412af120037a6fb1c565e263dd7fce5"
FEATURES = [
    "rp4_gamma_imb_total",
    "rp4_gamma_imb_near_spot",
    "rp4_gamma_imb_near_short",
    "rp4_gamma_imb_signed_trades",
]


def main() -> None:
    parent = ROOT / "artifacts/rp4_v2_a1/specification.json"
    addendum = ROOT / "docs/rp4/v3_addendum_stability_calibration.md"
    if sha256(parent) != V2_SHA or sha256(addendum) != ADDENDUM_SHA:
        raise ValueError("RP4_V3_PARENT_HASH_MISMATCH")
    spec = copy.deepcopy(json.loads(parent.read_text(encoding="utf-8")))
    spec.update(
        {
            "schema_version": "rp4-walkforward-v3",
            "authority_decisions": [128, 129, 130, 131],
            "parent_specification_sha256": V2_SHA,
            "addendum_sha256": ADDENDUM_SHA,
            "data_root": "private-input/e63a7488cbab65e3773b",
            "v2_data_root": "private-input/c153d5c8978c23bc439f",
            "specification_md_path": "docs/rp4/specification_v3.md",
            "specification_md_sha256": sha256(ROOT / "docs/rp4/specification_v3.md"),
            "decision_sha256": sha256(ROOT / "docs/rp4/decision_131_v3.md"),
            "base_panel": {
                "path": "private-input/52abad6fed9842f1a1ba",
                "sha256": BASE_SHA,
                "preserve_every_existing_column_exactly": True,
            },
            "candidate_gamma": {
                "path": (
                    "private-input/f6b35c089aa7336a7df9"
                    "gamma_imbalance_2024-08-02_2026-09-04.parquet"
                ),
                "sha256": "edc0263c8d8a76c897fc6d8e54462fd3ffb8f3aa475eb7ee4b55551b4a7fdfcc",
                "manifest_sha256": (
                    "8619bfd4191e80d14e7c025dc7f3358d9d0f881eb65f55a341fc16bddaae645d"
                ),
            },
        }
    )
    spec["feature_sets"]["B2"] += FEATURES
    spec["missing_allowed"] += FEATURES
    spec["feature_transforms"].update(dict.fromkeys(FEATURES[:3], "signed"))
    spec["feature_transforms"][FEATURES[3]] = "log1p"
    spec["new_transforms_also_apply_to_lightgbm"] = FEATURES
    assert [len(spec["feature_sets"][x]) for x in ("B0", "B1", "B2")] == [29, 69, 136]
    spec["gamma_imbalance"] = {
        "columns": FEATURES,
        "iv_range": [0.03, 3.0],
        "dte_inclusive": [0, 90],
        "cutoff": "created_at_and_executed_at_le_origin_minus_120s",
        "history_order": "max_created_executed_then_stable_source_order",
        "empty_valid_prefix": "NaN",
        "valid_unsigned_prefix": 0,
        "direction": "ask_only_plus_one_bid_only_minus_one_neither_or_both_zero",
        "multileg": "rp2_block6_multileg_size_positive_forces_zero",
        "duplicates": "first_available_version_immutable_later_conflicts_audit_only_stable_ties",
        "spot": "mark_price_previous_minute_close_or_minute_zero_open",
        "year_days": 365.25,
        "carry": "pinned_real_rate_and_cash_dividend_over_trade_spot",
        "near_spot_fraction": 0.05,
        "near_spot_tolerance": 1e-12,
        "short_dte_maximum": 7,
        "contract_multiplier": 100,
        "fourth_column": "raw_count_of_finite_exposure_nonzero_direction_trades",
        "comparison_atol": 1e-8,
        "comparison_rtol": 1e-10,
        "audit_bridges": ["independent_legacy", "independent_iv_only", "causal_production"],
    }
    spec["jump_target"] = {
        "column": "jump30",
        "definition": "max_forward_rv_minus_bipower_0",
        "producer": "mds650.rp2.realized.forward_measures",
        "validity": "same_31_observed_closes_and_grid_quality_as_reconstruct_rv30",
        "compare_rv30_do_not_replace": True,
        "missing": "separate_classifier_mask",
        "classification": "jump30_gt_0_not_formal_jump_test",
    }
    spec["model"]["ridge"].update(
        {
            "winsorized_standardized_slopes": [-5.0, 5.0],
            "qr_after_winsorization_intercept_aware": True,
            "forecast_bounds": [0.5, 2.0],
            "forecast_quantiles": [0.01, 0.99],
            "forecast_bounds_reference": "positive_training_rv30_linear_quantiles",
            "quantile_method": "linear",
            "clip_log_before_exp": True,
        }
    )
    spec["model"]["mz_secondary"] = {
        "calibration_sessions": 10,
        "predictions": "selected_inner_fit_model",
        "fit": "session_equal_asset_means_levels_scaled_OLS_rcond_1e-10",
        "training_degeneracy": "session_identity",
        "application_nonfinite": "origin_identity",
        "floor": 1e-12,
        "promotable": False,
    }
    spec["tail_models"] = {
        "secondary_only": True,
        "quantile": 0.9,
        "linear_quantile": {
            "objective": "sum_pinball_plus_lambda_l2_slopes",
            "solver": "exact_ADMM",
            "rho_initial": 1.0,
            "maxiter": 5000,
            "absolute_tolerance": 1e-5,
            "relative_tolerance": 1e-4,
            "dual_residual_scale": "objective_divided_by_N",
            "balance_every": 25,
            "balance_ratio": 10,
            "balance_factor": 2,
            "warm_start": "descending_lambdas_same_inner_fit_only",
            "refit_initialization": "training_unconditional_quantile",
            "bounds": "same_v3_ridge_percentile_bounds_in_log",
            "smearing": False,
        },
        "linear_jump": {
            "objective": "sum_binary_logloss_plus_lambda_l2_slopes",
            "solver": "L-BFGS-B",
            "maxiter": 1000,
            "gtol": 1e-8,
            "ftol": 1e-12,
        },
        "lightgbm_quantile_objective": "quantile",
        "lightgbm_jump_objective": "binary",
        "hyperparameters": "same_lambda_or_leaves_rounds_as_primary",
        "tuning": "equal_asset_session_pinball_or_logloss_not_evaluation_AUC",
        "probability_clip": [1e-12, 1 - 1e-12],
        "single_class_training": "clipped_empirical_frequency",
        "failed_fit": "NO_VERIFICABLE_count_common_endpoint_session_exclusion_keep_other_endpoints",
    }
    spec["inference"]["bootstrap"]["p_value"] = "greater_centered_null_plus_one"
    spec["inference"]["fixed_sequence"] = {
        "order": ["B1_over_B0", "B2_over_B1"],
        "alpha": 0.05,
        "scope": "each_family_endpoint_window",
        "require_positive_estimate": True,
        "joint_primary": "both_contrasts_reject_in_both_families",
        "H2_if_H1_fails": "nominal_p_only_not_formally_tested",
    }
    spec["inference"]["holm"]["role"] = "bilateral_comparability_secondary"
    spec["inference"]["posterior"] = {
        "prior": "flat_on_session_mean_delta",
        "likelihood": "normal_mean_HAC5_long_run_variance_over_N_plugin",
        "probability": "normal_cdf_mean_over_HAC_se",
        "invalid_variance": "NO_VERIFICABLE",
    }
    spec["inference"]["auc"] = {
        "point": "pooled_origins_equal_weight_ties_half",
        "delta": "richer_minus_base",
        "bootstrap": "shared_circular_session_block_multiplicities_recompute_pooled_AUC",
        "monoclass_replicates": "count_and_mark_CI_p_gate_NO_VERIFICABLE_no_redraw",
    }
    spec["secondary"].update(
        {
            "last_hour": "origin_minute_ge_300",
            "weekly_expiration_proxy": "calendar_friday",
            "third_friday": "calendar_friday_day_15_to_21",
            "high_gamma": (
                "abs_current_start_near_spot_above_training_only_asset_linear_2of3_quantile"
            ),
            "high_gamma_hypothesis": "B2_increment_larger_in_high_than_remaining",
            "mean_median_trimmed_bootstrap": True,
            "all_secondary_nonpromotable": True,
        }
    )
    out = ROOT / "artifacts/rp4_v3_a1"
    write_json_once(out / "specification.json", spec)
    frozen = {
        "schema_version": "rp4-v3-freeze-v1",
        "registered_at_utc": datetime.now(UTC).isoformat(),
        "specification_sha256": sha256(out / "specification.json"),
        "specification_md_sha256": spec["specification_md_sha256"],
        "decision_sha256": spec["decision_sha256"],
        "parent_specification_sha256": V2_SHA,
        "addendum_sha256": ADDENDUM_SHA,
        "freeze_producer_sha256": sha256(Path(__file__)),
        "v3_models_fitted": 0,
        "v3_materialization_executed": False,
        "prior_v1_v2_results_known": True,
        "capital_go": False,
    }
    write_json_once(out / "freeze.json", frozen)
    print(
        json.dumps(
            {
                "status": "RP4_V3_SPECIFICATION_FROZEN",
                **frozen,
                "freeze_sha256": sha256(out / "freeze.json"),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
