from __future__ import annotations

from datetime import UTC, date, datetime

import polars as pl
import pytest

from mds650.canonical_validation import (
    B2V2_FEATURES,
    _calibration_summary,
    _canonical_prediction_frame,
    _contrast_summary,
    _finite_float,
    _metric_drift,
    _paired_loss_frame,
    assert_causal_audit,
    assert_identical_origin_sets,
    build_causal_audit,
    canonical_model_parameters,
    evaluate_canonical_predictions,
    summarize_b2_redundancy,
    validate_claim_eligibility,
)
from mds650.temporal_validation import FoldDefinition


def _frame(origin_ids: tuple[str, ...]) -> pl.DataFrame:
    return pl.DataFrame({"origin_id": origin_ids})


def _valid_panel() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "origin_id": ["AAPL:train", "AAPL:test"],
            "session_date": ["2025-01-02", "2025-01-03"],
            "forecast_origin_utc": [
                datetime(2025, 1, 2, 20, 0, tzinfo=UTC),
                datetime(2025, 1, 3, 14, 35, tzinfo=UTC),
            ],
        }
    )


def _fold() -> FoldDefinition:
    return FoldDefinition(
        fold=1,
        train_end=date(2025, 1, 2),
        test_start=date(2025, 1, 3),
        test_end=date(2025, 1, 3),
    )


def test_build_causal_audit_records_strict_gap_for_every_role() -> None:
    audit = build_causal_audit(
        _valid_panel(),
        (_fold(),),
        model_roles=("gamma_glm_confirmatory", "ridge_fixed_extension"),
        target_horizon_minutes=30,
        embargo_minutes=30,
        block="fixture",
    )

    assert audit.height == 2
    assert audit["causal_pass"].to_list() == [True, True]
    assert audit["observed_gap_minutes"].min() >= 60.0
    assert_causal_audit(audit)


def test_assert_causal_audit_rejects_training_after_test_start() -> None:
    audit = pl.DataFrame(
        {
            "block": ["fixture"],
            "fold": [1],
            "model_role": ["ridge_fixed_extension"],
            "observed_gap_minutes": [29.0],
            "required_protected_minutes": [60],
            "causal_pass": [False],
        }
    )

    with pytest.raises(ValueError, match="CANONICAL_CAUSALITY_VIOLATION"):
        assert_causal_audit(audit)


def test_identical_origins_rejects_one_missing_b2_row() -> None:
    with pytest.raises(ValueError, match="CANONICAL_ORIGIN_SET_MISMATCH"):
        assert_identical_origin_sets(
            {
                "B0v2": _frame(("a", "b")),
                "B1v2a": _frame(("a", "b")),
                "B2v2": _frame(("a",)),
            }
        )


def test_identical_origins_rejects_duplicate_key() -> None:
    with pytest.raises(ValueError, match="CANONICAL_ORIGIN_KEY_INVALID"):
        assert_identical_origin_sets(
            {
                "B0v2": _frame(("a", "a")),
                "B1v2a": _frame(("a", "a")),
                "B2v2": _frame(("a", "a")),
            }
        )


def _predictions() -> pl.DataFrame:
    origin = datetime(2025, 1, 3, 14, 35, tzinfo=UTC)
    return pl.DataFrame(
        [
            {
                "block": "phase6",
                "fold": 1,
                "model_role": "gamma_glm_confirmatory",
                "information_set": information_set,
                "origin_id": "AAPL:1",
                "asset": "AAPL",
                "session_date": "2025-01-03",
                "forecast_origin_utc": origin,
                "session_tercile": "first",
                "volatility_regime": "normal",
                "rv30": 0.01,
                "forecast": forecast,
                "analysis_status": "HISTORICAL_REGISTERED_REFERENCE",
            }
            for information_set, forecast in (
                ("B0v2", 0.008),
                ("B1v2a", 0.009),
                ("B2v2", 0.01),
            )
        ]
    )


def test_canonical_origin_and_causal_input_guards_fail_closed() -> None:
    with pytest.raises(ValueError, match="CANONICAL_ORIGIN_SET_INVALID"):
        assert_identical_origin_sets({})
    with pytest.raises(ValueError, match="CANONICAL_ORIGIN_KEY_INVALID"):
        assert_identical_origin_sets({"B0v2": pl.DataFrame({"wrong": ["a"]})})
    with pytest.raises(ValueError, match="CANONICAL_CAUSAL_AUDIT_INPUT_INVALID"):
        build_causal_audit(
            pl.DataFrame(),
            (),
            model_roles=(),
            target_horizon_minutes=-1,
            embargo_minutes=30,
            block="",
        )
    with pytest.raises(ValueError, match="CANONICAL_ORIGIN_KEY_INVALID"):
        build_causal_audit(
            pl.concat([_valid_panel(), _valid_panel().head(1)]),
            (_fold(),),
            model_roles=("ridge",),
            target_horizon_minutes=30,
            embargo_minutes=30,
            block="fixture",
        )
    with pytest.raises(ValueError, match="CANONICAL_CAUSAL_AUDIT_FOLD_EMPTY"):
        build_causal_audit(
            _valid_panel(),
            (
                FoldDefinition(
                    fold=1,
                    train_end=date(2024, 1, 1),
                    test_start=date(2024, 1, 2),
                    test_end=date(2024, 1, 2),
                ),
            ),
            model_roles=("ridge",),
            target_horizon_minutes=30,
            embargo_minutes=30,
            block="fixture",
        )
    string_timestamps = _valid_panel().with_columns(pl.col("forecast_origin_utc").cast(pl.String))
    with pytest.raises(ValueError, match="CANONICAL_CAUSAL_AUDIT_TIMESTAMP_INVALID"):
        build_causal_audit(
            string_timestamps,
            (_fold(),),
            model_roles=("ridge",),
            target_horizon_minutes=30,
            embargo_minutes=30,
            block="fixture",
        )
    with pytest.raises(ValueError, match="CANONICAL_CAUSAL_AUDIT_INVALID"):
        assert_causal_audit(pl.DataFrame())


def test_canonical_model_parameter_guards_reject_unfrozen_or_invalid_roles() -> None:
    cases = [
        ("unknown", {}, "CANONICAL_MODEL_ROLE_INVALID"),
        ("gamma_glm_confirmatory", {}, "CANONICAL_FROZEN_PARAMETER_MISSING"),
        (
            "gamma_glm_confirmatory",
            {"gamma_glm_confirmatory": {"alpha": True}},
            "CANONICAL_FROZEN_PARAMETER_INVALID",
        ),
        (
            "lightgbm_robustness",
            {"lightgbm_robustness": {}},
            "CANONICAL_FROZEN_PARAMETER_MISSING",
        ),
    ]
    for role, frozen, error in cases:
        with pytest.raises(ValueError, match=error):
            canonical_model_parameters(role, phase6_frozen=frozen)

    assert canonical_model_parameters("har_rv_fixed_extension", phase6_frozen={}) == {}


def test_canonical_prediction_frame_rejects_schema_key_value_and_set_drift() -> None:
    valid = _predictions()
    cases = [
        (pl.DataFrame(), "CANONICAL_PREDICTION_COLUMNS_INVALID"),
        (valid.with_columns(pl.lit("unknown").alias("model_role")), "CANONICAL_MODEL_ROLE_INVALID"),
        (
            valid.with_columns(pl.lit("unknown").alias("information_set")),
            "CANONICAL_INFORMATION_SET_INVALID",
        ),
        (pl.concat([valid, valid.head(1)]), "CANONICAL_PREDICTION_DUPLICATE_KEY"),
        (
            valid.with_columns(pl.lit(float("nan")).alias("forecast")),
            "CANONICAL_PREDICTION_VALUES_INVALID",
        ),
        (
            valid.filter(pl.col("information_set") != "B2v2"),
            "CANONICAL_INFORMATION_SET_MISSING",
        ),
    ]

    for frame, error in cases:
        with pytest.raises(ValueError, match=error):
            _canonical_prediction_frame(frame)

    assert _canonical_prediction_frame(valid).get_column("canonical_qlike_loss").is_finite().all()


def test_canonical_numeric_calibration_and_pairing_guards() -> None:
    for value in (True, "1", float("nan")):
        with pytest.raises(ValueError, match="NUMERIC_INVALID"):
            _finite_float(value, "NUMERIC_INVALID")

    descriptive = _calibration_summary(
        pl.DataFrame({"rv30": [1.0, 2.0, 4.0], "forecast": [1.0, 1.5, 3.0]})
    )
    assert descriptive["status"] == "DESCRIPTIVE"
    assert (
        _calibration_summary(pl.DataFrame({"rv30": [1.0, 1.0], "forecast": [1.0, 1.0]}))["status"]
        == "NON_IDENTIFIABLE"
    )

    valid = _canonical_prediction_frame(_predictions())
    with pytest.raises(ValueError, match="CANONICAL_CONTRAST_UNPAIRED"):
        _paired_loss_frame(
            valid.filter(
                ~((pl.col("information_set") == "B1v2a") & (pl.col("origin_id") == "AAPL:1"))
            ),
            baseline="B0v2",
            expanded="B1v2a",
        )
    drifted = valid.with_columns(
        pl.when(pl.col("information_set") == "B1v2a")
        .then(pl.lit(0.02))
        .otherwise(pl.col("rv30"))
        .alias("rv30")
    )
    with pytest.raises(ValueError, match="CANONICAL_CONTRAST_TARGET_DRIFT"):
        _paired_loss_frame(drifted, baseline="B0v2", expanded="B1v2a")

    paired, _ = _paired_loss_frame(valid, baseline="B0v2", expanded="B1v2a")
    summary = _contrast_summary(
        paired,
        block="phase6",
        role="gamma_glm_confirmatory",
        name="delta_b1v2",
        baseline="B0v2",
        expanded="B1v2a",
        bootstrap_seed=1,
        draws=100,
        mde=0.001,
    )
    assert summary["status"] == "INSUFFICIENT_DAY_CLUSTERS"


def test_canonical_evaluation_and_claim_guards_cover_all_outcomes() -> None:
    valid_mde = {"delta_b1v2": 0.001, "delta_b2v2": 0.001}
    with pytest.raises(ValueError, match="CANONICAL_BOOTSTRAP_SETTINGS_INVALID"):
        evaluate_canonical_predictions(
            _predictions(), bootstrap_seed=-1, draws=99, mde_by_contrast=valid_mde
        )
    with pytest.raises(ValueError, match="CANONICAL_MDE_CONTRACT_INVALID"):
        evaluate_canonical_predictions(
            _predictions(), bootstrap_seed=1, draws=100, mde_by_contrast={"delta_b1v2": 0.0}
        )

    assert (
        validate_claim_eligibility({"gamma_b2": 1.0, "lightgbm_b2": 1.0, "mde_pass": True})
        == "GLOBAL_EDGE"
    )
    assert (
        validate_claim_eligibility({"gamma_b2": 1.0, "lightgbm_b2": 1.0, "mde_pass": False})
        == "CONDITIONAL"
    )
    assert (
        validate_claim_eligibility({"gamma_b2": -1.0, "lightgbm_b2": -1.0, "mde_pass": True})
        == "NOT_SUPPORTED"
    )
    with pytest.raises(ValueError, match="CANONICAL_CLAIM_INPUT_INVALID"):
        validate_claim_eligibility({"gamma_b2": "bad", "lightgbm_b2": 1.0, "mde_pass": True})
    with pytest.raises(ValueError, match="CANONICAL_CLAIM_INPUT_INVALID"):
        validate_claim_eligibility({"contrasts": "bad"})
    with pytest.raises(ValueError, match="CANONICAL_CLAIM_INPUT_INVALID"):
        validate_claim_eligibility({"contrasts": ["bad"]})
    assert validate_claim_eligibility({"contrasts": []}) == "NOT_SUPPORTED"

    def row(role: str, estimate: float, *, strong: bool = True) -> dict[str, object]:
        return {
            "block": "phase6",
            "model_role": role,
            "registered_status": "REGISTERED_OOS",
            "estimate": estimate,
            "status": "RUN",
            "ci_low": 0.1 if strong else -0.1,
            "p_value_holm": 0.01,
            "mde_pass": True,
        }

    assert (
        validate_claim_eligibility({"contrasts": [row("gamma_glm_confirmatory", 1.0)]})
        == "NOT_SUPPORTED"
    )
    assert (
        validate_claim_eligibility(
            {
                "contrasts": [
                    row("gamma_glm_confirmatory", 1.0),
                    row("lightgbm_robustness", -1.0),
                ]
            }
        )
        == "MODEL_FAMILY_DEPENDENT"
    )
    assert (
        validate_claim_eligibility(
            {
                "contrasts": [
                    row("gamma_glm_confirmatory", -1.0),
                    row("lightgbm_robustness", -1.0),
                ]
            }
        )
        == "NOT_SUPPORTED"
    )
    assert (
        validate_claim_eligibility(
            {
                "contrasts": [
                    row("gamma_glm_confirmatory", 1.0, strong=False),
                    row("lightgbm_robustness", 1.0),
                ]
            }
        )
        == "CONDITIONAL"
    )


def test_metric_drift_and_b2_redundancy_are_target_blind() -> None:
    metric = {"model_role": "gamma_glm_confirmatory", "information_set": "B2v2"}
    drift = _metric_drift(
        [
            {**metric, "block": "phase6", "qlike": 1.0, "mae": 2.0, "rmse": 3.0},
            {
                **metric,
                "block": "independent_replication",
                "qlike": 1.5,
                "mae": 2.5,
                "rmse": 3.5,
            },
        ]
    )
    assert drift[0]["qlike_difference"] == pytest.approx(0.5)

    with pytest.raises(ValueError, match="CANONICAL_B2_REDUNDANCY_COLUMNS_INVALID"):
        summarize_b2_redundancy(pl.DataFrame(), block="fixture")
    data = {
        feature: [float(index), float(index + 1), float(index + 2)]
        for index, feature in enumerate(B2V2_FEATURES)
    }
    data[B2V2_FEATURES[0]][0] = float("nan")
    with pytest.raises(ValueError, match="CANONICAL_B2_REDUNDANCY_VALUES_INVALID"):
        summarize_b2_redundancy(pl.DataFrame(data), block="fixture")
    data[B2V2_FEATURES[0]][0] = 0.0
    rows = summarize_b2_redundancy(pl.DataFrame(data), block="fixture")
    assert len(rows) == len(B2V2_FEATURES)
    assert {row["status"] for row in rows} == {"TARGET_BLIND_DESCRIPTIVE"}
