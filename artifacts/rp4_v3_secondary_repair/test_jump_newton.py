"""Synthetic-only tests for the isolated, same-objective Newton polish."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pytest
from artifacts.rp4_v3_secondary_repair import jump_newton as new
from artifacts.rp4_v3_secondary_repair import jump_repair as prior
from scipy.special import expit


def synthetic_design(n=180, p=7):
    rng = np.random.default_rng(20260907)
    fitted = np.column_stack((np.ones(n), rng.normal(size=(n, p))))
    coefficient = np.arange(p + 1, dtype=float) * 0.08 - 0.2
    target = (rng.random(n) < expit(fitted @ coefficient)).astype(float)
    return fitted, target


def test_analytic_hessian_matches_central_difference_and_unpenalized_intercept():
    fitted, target = synthetic_design()
    coefficient = np.arange(fitted.shape[1], dtype=float) * 0.03
    penalty = 100.0
    epsilon = 1e-5
    numerical = np.column_stack(
        [
            (
                prior.objective_original(
                    fitted, target, coefficient + epsilon * direction, penalty
                )[1]
                - prior.objective_original(
                    fitted, target, coefficient - epsilon * direction, penalty
                )[1]
            )
            / (2 * epsilon)
            for direction in np.eye(fitted.shape[1])
        ]
    )
    actual = new.analytic_hessian(fitted, coefficient, penalty)
    np.testing.assert_allclose(actual, numerical, rtol=1e-8, atol=1e-10)
    expected_penalty = np.eye(fitted.shape[1]) * 2 * penalty / len(target)
    expected_penalty[0, 0] = 0.0
    np.testing.assert_allclose(
        actual - new.analytic_hessian(fitted, coefficient, 0.0), expected_penalty, atol=1e-15
    )


def test_ulp_exception_is_precise_and_never_allows_objective_increase():
    value = 0.7
    ulp = np.nextafter(value, np.inf) - value
    slope = -ulp / (2 * new.ARMIJO)
    assert new.accept_step(value, 1e-7, value, 9e-8, slope, 1.0) == (
        "ULP_NONINCREASE_STRICT_ORIGINAL_GRADIENT_IMPROVEMENT"
    )
    assert new.accept_step(value, 1e-7, np.nextafter(value, np.inf), 1e-10, slope, 1.0) is None
    assert new.accept_step(value, 1e-7, value, 1e-7, slope, 1.0) is None
    assert new.accept_step(value, 1e-7, value, 2e-7, slope, 1.0) is None
    assert new.accept_step(value, 1e-7, value, 1e-10, -2 * ulp / new.ARMIJO, 1.0) is None
    assert new.accept_step(value, 1e-7, value - 0.01, 1e-8, -0.1, 1.0) == "ARMIJO"
    assert new.accept_step(value, 1e-7, value - 0.01, 1e-8, 0.1, 1.0) is None
    assert new.accept_step(value, 1e-7, float("nan"), 1e-8, slope, 1.0) is None


@pytest.mark.parametrize("penalty", [0.0001, 0.01, 1.0, 100.0, 10000.0])
def test_successful_frozen_two_phase_solution_stays_exact_without_newton(penalty):
    fitted, target = synthetic_design()
    before, metadata_before = prior.logistic_coefficient(fitted, target, penalty, {})
    after, metadata_after = new.logistic_coefficient(fitted, target, penalty, {})
    np.testing.assert_array_equal(after, before)
    assert metadata_after["phases"] == metadata_before["phases"]
    assert metadata_after["newton"]["attempted"] is False
    assert metadata_after["gradient_inf_norm_objective_over_n"] <= 1e-8


def test_newton_polishes_perturbed_solution_without_relaxing_certificate():
    fitted, target = synthetic_design(n=300)
    optimum, _ = prior.logistic_coefficient(fitted, target, 0.0001, {})
    start = optimum + np.linspace(1e-5, -1e-5, len(optimum))
    initial = prior.objective_original(fitted, target, start, 0.0001)[0]
    before = new.literal_certificate(fitted, target, start, 0.0001)
    assert new.original_gradient_norm(before) > 1e-8
    coefficient, metadata = new.newton_polish(
        fitted, target, start, 0.0001, initial_objective=initial, iterations_used=27
    )
    final = new.literal_certificate(fitted, target, coefficient, 0.0001)
    assert metadata["reason"] == "original_gradient_certificate_satisfied"
    assert 1 <= metadata["iterations"] <= 8
    assert new.certificate_ok(final, initial, 1e-8, 1e-12)
    assert final["objective"] <= initial
    assert final["literal_original_objective_abs_difference"] <= 1e-10
    assert final["literal_original_gradient_max_abs_difference"] <= 1e-10


@pytest.mark.parametrize("multiple,expected_attempt", [(1.02, True), (0.98, False)])
def test_synthetic_gradient_immediately_above_and_below_unchanged_certificate(
    multiple, expected_attempt
):
    # Exactly balanced labels at both orthogonal feature values: beta=0 is the
    # analytic optimum. Only the intercept is perturbed; no empirical fit/data.
    fitted = np.column_stack((np.ones(400), np.tile([-1.0, -1.0, 1.0, 1.0], 100)))
    target = np.tile([0.0, 1.0, 0.0, 1.0], 100)
    probability = 0.5 + multiple * 1e-8
    start = np.array([np.log(probability / (1.0 - probability)), 0.0])
    before = new.literal_certificate(fitted, target, start, 0.0001)
    np.testing.assert_allclose(new.original_gradient_norm(before) / 1e-8, multiple, atol=1e-7)
    coefficient, metadata = new.newton_polish(
        fitted,
        target,
        start,
        0.0001,
        initial_objective=before["objective"],
        iterations_used=27,
    )
    assert metadata["attempted"] is expected_attempt
    after = new.literal_certificate(fitted, target, coefficient, 0.0001)
    assert new.certificate_ok(after, before["objective"], 1e-8, 1e-12)
    assert after["objective"] <= before["objective"]
    if expected_attempt:
        assert metadata["accepted_steps"] >= 1
        assert new.original_gradient_norm(after) < new.original_gradient_norm(before)
    else:
        np.testing.assert_array_equal(coefficient, start)


def test_mock_ftol_stagnation_reaches_newton_only_after_the_frozen_two_phases(monkeypatch):
    fitted, target = synthetic_design(n=240)
    penalty = 0.0001
    optimum, _ = prior.logistic_coefficient(fitted, target, penalty, {})
    stalled = optimum + np.linspace(1e-5, -1e-5, len(optimum))
    factor = prior.fisher_factor(fitted, target, penalty, fitted.T @ fitted)
    calls = []

    def optimizer(fun, initial, *, method, jac, options):
        calls.append(options.copy())
        assert method == "L-BFGS-B" and jac is True
        return SimpleNamespace(
            x=factor.T @ stalled,
            nit=17 if len(calls) == 1 else 10,
            nfev=20,
            success=True,
            status=0,
            message="CONVERGENCE: RELATIVE REDUCTION OF F <= FACTR*EPSMCH",
        )

    monkeypatch.setattr(new, "minimize", optimizer)
    _, metadata = new.logistic_coefficient(fitted, target, penalty, {})
    assert [x["ftol"] for x in calls] == [1e-12, 0.0]
    assert [x["maxiter"] for x in calls] == [1000, 983]
    assert metadata["lbfgs_iterations"] == 27
    assert metadata["newton"]["attempted"] is True
    assert metadata["iterations"] <= 35
    assert metadata["gradient_inf_norm_objective_over_n"] <= 1e-8


def test_newton_cannot_borrow_iterations_beyond_original_budget():
    fitted, target = synthetic_design()
    start = np.zeros(fitted.shape[1])
    initial = prior.objective_original(fitted, target, start, 1.0)[0]
    _, exhausted = new.newton_polish(
        fitted, target, start, 1.0, initial_objective=initial, iterations_used=1000
    )
    assert exhausted["attempted"] is False and exhausted["iterations"] == 0
    assert exhausted["reason"] == "newton_budget_exhausted"
    _, one = new.newton_polish(
        fitted, target, start, 1.0, initial_objective=initial, iterations_used=999
    )
    assert one["maximum_steps"] == 1 and one["iterations"] <= 1


def test_no_jitter_or_forecast_when_hessian_is_not_spd(monkeypatch):
    fitted, target = synthetic_design()
    start = np.zeros(fitted.shape[1])
    initial = prior.objective_original(fitted, target, start, 1.0)[0]
    monkeypatch.setattr(new, "analytic_hessian", lambda *args: -np.eye(fitted.shape[1]))
    coefficient, metadata = new.newton_polish(
        fitted, target, start, 1.0, initial_objective=initial, iterations_used=27
    )
    np.testing.assert_array_equal(coefficient, start)
    assert metadata["reason"] == "newton_hessian_not_spd_or_nonfinite"
    assert metadata["accepted_steps"] == 0 and metadata["objective_jitter"] == 0


def test_backtracking_has_exactly_twenty_halvings_and_fails_closed(monkeypatch):
    fitted, target = synthetic_design()
    start = np.zeros(fitted.shape[1])
    initial = prior.objective_original(fitted, target, start, 1.0)[0]
    monkeypatch.setattr(new, "accept_step", lambda *args: None)
    coefficient, metadata = new.newton_polish(
        fitted, target, start, 1.0, initial_objective=initial, iterations_used=27
    )
    np.testing.assert_array_equal(coefficient, start)
    assert metadata["reason"] == "newton_no_accepted_step_within_twenty_halvings"
    assert len(metadata["steps"][0]["trials"]) == 21
    assert metadata["steps"][0]["trials"][-1]["halvings"] == 20
    assert metadata["accepted_steps"] == 0


def test_single_class_exception_is_literal_frozen_behavior():
    fitted, _ = synthetic_design()
    for label in (0.0, 1.0):
        target = np.full(len(fitted), label)
        before, before_record = prior.logistic_coefficient(fitted, target, 1.0, {})
        after, after_record = new.logistic_coefficient(fitted, target, 1.0, {})
        np.testing.assert_array_equal(before, after)
        assert before_record == after_record
