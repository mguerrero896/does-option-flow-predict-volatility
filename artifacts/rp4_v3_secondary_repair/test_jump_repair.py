"""Synthetic-only objective, convergence and training-boundary regression tests."""

from __future__ import annotations

from types import SimpleNamespace

import numpy as np
import pandas as pd
import pytest
from artifacts.rp4_v3_code import models as original
from artifacts.rp4_v3_secondary_repair import jump_repair as repair
from scipy import linalg
from scipy.optimize._numdiff import approx_derivative
from scipy.special import expit

OPTIONS = {"maxiter": 1000, "gtol": 1e-8, "ftol": 1e-12}


@pytest.fixture(scope="module")
def cases() -> dict:
    rng = np.random.default_rng(20260907)
    n, width = 2000, 139
    raw = rng.standard_normal((n, width))
    rotation, _ = np.linalg.qr(rng.standard_normal((width, width)))
    target = (rng.random(n) < expit(-0.4 + 0.8 * raw[:, 0] - 0.2 * raw[:, 1])).astype(float)
    ill = (raw * np.geomspace(1.0, 1e-4, width)) @ rotation.T
    return {
        "well": original._ridge_design(raw, raw[:7], []).fitted,
        "ill": original._ridge_design(ill, ill[:7], []).fitted,
        "target": target,
    }


def test_objective_gradient_and_unpenalized_intercept(cases: dict) -> None:
    fitted, target = cases["well"][:, :6], cases["target"]
    beta = np.array([-0.3, 0.2, -0.1, 0.3, -0.05, 0.4])
    penalty = 3.0
    value, gradient = repair.objective_original(fitted, target, beta, penalty)
    raw = fitted @ beta
    expected = (np.sum(np.logaddexp(0.0, raw) - target * raw) + penalty * sum(beta[1:] ** 2)) / len(
        target
    )
    analytic = fitted.T @ (expit(raw) - target) / len(target)
    analytic[1:] += 2 * penalty * beta[1:] / len(target)
    numerical = approx_derivative(
        lambda b: repair.objective_original(fitted, target, b, penalty)[0],
        beta,
        method="3-point",
        abs_step=1e-5,
    ).ravel()
    assert value == pytest.approx(expected, abs=1e-15)
    np.testing.assert_allclose(gradient, analytic, atol=1e-14, rtol=0)
    np.testing.assert_allclose(gradient, numerical, atol=1e-9, rtol=0)
    assert gradient[0] == pytest.approx(np.mean(expit(raw) - target), abs=1e-15)


def test_cholesky_coordinates_preserve_objective_gradient_and_coefficients(cases: dict) -> None:
    fitted, target = cases["well"][:, :6], cases["target"]
    penalty = 0.0001
    factor = repair.fisher_factor(fitted, target, penalty, fitted.T @ fitted)
    beta = np.linspace(-0.4, 0.4, fitted.shape[1])
    theta = factor.T @ beta
    recovered = linalg.solve_triangular(factor.T, theta, lower=False)
    np.testing.assert_allclose(recovered, beta, atol=1e-15, rtol=0)
    value, gradient = repair.objective_original(fitted, target, beta, penalty)
    transformed_gradient = linalg.solve_triangular(factor, gradient, lower=True)

    def transformed(coordinate):
        b = linalg.solve_triangular(factor.T, coordinate, lower=False)
        return repair.objective_original(fitted, target, b, penalty)[0]

    assert transformed(theta) == pytest.approx(value, abs=1e-15)
    numerical = approx_derivative(transformed, theta, method="3-point", abs_step=1e-5).ravel()
    np.testing.assert_allclose(transformed_gradient, numerical, atol=1e-9, rtol=0)


def test_equivalent_to_original_when_well_conditioned(cases: dict) -> None:
    fitted, target = cases["well"], cases["target"]
    old, old_diag = original._logistic_coefficient(fitted, target, 0.0001, OPTIONS)
    new, diag = repair.logistic_coefficient(fitted, target, 0.0001, OPTIONS)
    assert old_diag["converged"] and diag["converged"]
    assert diag["gradient_inf_norm_objective_over_n"] <= OPTIONS["gtol"]
    assert diag["objective_total_divided_by_n"] <= old_diag["objective_total_divided_by_n"] + 1e-12
    np.testing.assert_allclose(expit(fitted @ new), expit(fitted @ old), atol=2e-6, rtol=0)


def test_repairs_pinned_correlated_failure_without_changing_objective(cases: dict) -> None:
    fitted, target = cases["ill"], cases["target"]
    with pytest.raises(original.ModelConvergenceError) as caught:
        original._logistic_coefficient(fitted, target, 0.0001, OPTIONS)
    assert caught.value.diagnostics["iterations"] == 1000
    coefficient, diag = repair.logistic_coefficient(fitted, target, 0.0001, OPTIONS)
    assert diag["converged"] and diag["iterations"] < 100
    assert diag["gradient_inf_norm_objective_over_n"] <= 1e-8
    assert diag["literal_original_objective_abs_difference"] < 1e-12
    assert diag["literal_original_gradient_max_abs_difference"] < 1e-12
    assert (
        diag["objective_total_divided_by_n"]
        < caught.value.diagnostics["objective_total_divided_by_n"]
    )
    assert np.isfinite(coefficient).all()


@pytest.mark.parametrize("label", [0.0, 1.0])
def test_single_class_exception_is_exactly_unchanged(label: float) -> None:
    fitted = np.column_stack([np.ones(20), np.linspace(-1, 1, 20)])
    target = np.full(20, label)
    old, _ = original._logistic_coefficient(fitted, target, 1.0, OPTIONS)
    new, diag = repair.logistic_coefficient(fitted, target, 1.0, OPTIONS)
    np.testing.assert_array_equal(new, old)
    assert diag["single_class_training"] and not diag["original_gradient_certificate_applicable"]


def test_scipy_success_flag_alone_is_not_a_convergence_certificate(
    cases: dict, monkeypatch
) -> None:
    def pretend(fun, start, **kwargs):
        return SimpleNamespace(
            x=np.zeros_like(start), nit=1, nfev=1, success=True, status=0, message="false success"
        )

    monkeypatch.setattr(repair, "minimize", pretend)
    with pytest.raises(original.ModelConvergenceError) as caught:
        repair.logistic_coefficient(cases["well"], cases["target"], 1.0, OPTIONS)
    assert caught.value.diagnostics["gradient_inf_norm_objective_over_n"] > 1e-8


def test_iteration_cap_does_not_silently_emit_probability(cases: dict) -> None:
    with pytest.raises(original.ModelConvergenceError):
        repair.logistic_coefficient(cases["well"], cases["target"], 1.0, {**OPTIONS, "maxiter": 1})


def test_nonfinite_coordinates_produce_serializable_numerical_failure(
    cases: dict, monkeypatch
) -> None:
    def bad_result(fun, start, **kwargs):
        return SimpleNamespace(x=np.full_like(start, np.nan), nit=1)

    monkeypatch.setattr(repair, "minimize", bad_result)
    with pytest.raises(original.ModelConvergenceError) as caught:
        repair.logistic_coefficient(cases["well"], cases["target"], 1.0, OPTIONS)
    assert caught.value.diagnostics["reason"] == "nonfinite_or_wrong_shape_coordinates"


def test_full_linear_fit_uses_only_training_labels_and_registered_grid() -> None:
    rng = np.random.default_rng(121)
    days = np.repeat(pd.bdate_range("2023-01-02", periods=24).strftime("%Y-%m-%d").to_numpy(), 24)
    assets = np.tile(["A", "B"], len(days) // 2)
    design = rng.normal(size=(len(days), 4))
    design[::6, 3] = np.nan
    target = (rng.random(len(days)) < expit(0.3 * design[:, 0])).astype(float)
    train = days < days[-1]
    test = ~train
    validation_dates = np.unique(days[train])[-10:]
    valid = train & np.isin(days, validation_dates)
    inner = train & ~valid
    options = {"lambda_grid": list(repair.REGISTERED_GRID), "logistic": OPTIONS}
    args = (design, target, train, inner, valid, test, [3], days, assets, options)
    prediction, diagnostics = repair.fit_jump_linear(*args)
    changed = target.copy()
    changed[test] = np.nan
    again, second = repair.fit_jump_linear(
        design, changed, train, inner, valid, test, [3], days, assets, options
    )
    np.testing.assert_array_equal(again, prediction)
    assert second == diagnostics
    assert diagnostics["lambda_grid"] == list(repair.REGISTERED_GRID)
    assert len(diagnostics["candidates"]) == 5
    assert len(diagnostics["inner_valid_sessions"]) == 10
    assert max(diagnostics["inner_valid_sessions"]) < days[-1]
    assert diagnostics["solver_refit"]["converged"]
    with pytest.raises(ValueError, match="REGISTERED_LAMBDA"):
        repair.fit_jump_linear(*args[:-1], {**options, "lambda_grid": [1.0]})
