"""Equivalent analytic Newton polish, isolated from the frozen first repair.

No data loading or empirical execution occurs on import. A separate, hash-bound
failed-only adapter must authorize every component before calling this module.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np
import numpy.typing as npt
from artifacts.rp4_code.evaluate import Array, Mask, equal_session_asset_mean
from artifacts.rp4_v2_code.models import QR_RELATIVE_TOLERANCE
from artifacts.rp4_v3_code import models as original
from artifacts.rp4_v3_secondary_repair import jump_repair as prior
from scipy import linalg
from scipy.optimize import minimize
from scipy.special import expit

MAX_NEWTON_STEPS = 8
MAX_HALVINGS = 20
ARMIJO = 1e-4


def literal_certificate(
    fitted: Array, target: Array, coefficient: Array, penalty: float
) -> dict[str, float]:
    value, gradient = prior.objective_original(fitted, target, coefficient, penalty)
    raw = fitted @ coefficient
    literal_value = float(
        (
            np.sum(np.logaddexp(0.0, raw) - target * raw)
            + penalty * np.dot(coefficient[1:], coefficient[1:])
        )
        / len(target)
    )
    literal_gradient = fitted.T @ (expit(raw) - target) / len(target)
    literal_gradient[1:] += 2.0 * penalty * coefficient[1:] / len(target)
    return {
        "objective": value,
        "literal_objective": literal_value,
        "stable_gradient_inf_norm": float(np.max(np.abs(gradient))),
        "gradient_inf_norm_objective_over_n": float(np.max(np.abs(literal_gradient))),
        "literal_original_objective_abs_difference": abs(literal_value - value),
        "literal_original_gradient_max_abs_difference": float(
            np.max(np.abs(literal_gradient - gradient))
        ),
    }


def original_gradient_norm(certificate: Mapping[str, float]) -> float:
    return max(
        certificate["stable_gradient_inf_norm"],
        certificate["gradient_inf_norm_objective_over_n"],
    )


def certificate_ok(
    certificate: Mapping[str, float], initial: float, gtol: float, ftol: float
) -> bool:
    return bool(
        all(math.isfinite(value) for value in certificate.values())
        and original_gradient_norm(certificate) <= gtol
        and certificate["objective"] <= initial + ftol
        and certificate["literal_original_objective_abs_difference"]
        <= 1e-10 * max(1.0, abs(certificate["objective"]))
        and certificate["literal_original_gradient_max_abs_difference"] <= 1e-10
    )


def analytic_hessian(fitted: Array, coefficient: Array, penalty: float) -> Array:
    raw = fitted @ coefficient
    weights = expit(raw) * expit(-raw)
    matrix = (fitted.T @ (weights[:, None] * fitted)) / len(fitted)
    diagonal = np.arange(1, fitted.shape[1])
    matrix[diagonal, diagonal] += 2.0 * penalty / len(fitted)
    return np.asarray((matrix + matrix.T) * 0.5, dtype=np.float64)


def accept_step(
    value: float,
    gradient_norm: float,
    candidate_value: float,
    candidate_gradient_norm: float,
    directional_derivative: float,
    step_size: float,
) -> str | None:
    """No objective increase, including the explicit one-ULP stagnation exception."""
    if (
        not all(
            math.isfinite(x)
            for x in (
                value,
                gradient_norm,
                candidate_value,
                candidate_gradient_norm,
                directional_derivative,
                step_size,
            )
        )
        or directional_derivative >= 0
        or step_size <= 0
    ):
        return None
    required_decrease = -ARMIJO * step_size * directional_derivative
    if candidate_value < value and candidate_value <= value - required_decrease:
        return "ARMIJO"
    ulp = float(np.nextafter(value, np.inf) - value)
    if (
        candidate_value <= value
        and 0 <= value - candidate_value <= ulp
        and required_decrease <= ulp
        and candidate_gradient_norm < gradient_norm
    ):
        return "ULP_NONINCREASE_STRICT_ORIGINAL_GRADIENT_IMPROVEMENT"
    return None


def newton_polish(
    fitted: Array,
    target: Array,
    coefficient: Array,
    penalty: float,
    *,
    initial_objective: float,
    iterations_used: int,
    maximum_iterations: int = 1000,
    gtol: float = 1e-8,
    ftol: float = 1e-12,
) -> tuple[Array, dict[str, Any]]:
    """At most eight analytic steps inside the existing total iteration budget."""
    current = coefficient.copy()
    certificate = literal_certificate(fitted, target, current, penalty)
    remaining = max(0, maximum_iterations - iterations_used)
    limit = min(MAX_NEWTON_STEPS, remaining)
    steps: list[dict[str, Any]] = []
    reason = "newton_budget_exhausted"
    if certificate_ok(certificate, initial_objective, gtol, ftol):
        return current, {
            "attempted": False,
            "iterations": 0,
            "accepted_steps": 0,
            "steps": [],
            "reason": "certificate_already_satisfied",
        }
    for number in range(limit):
        value, gradient = prior.objective_original(fitted, target, current, penalty)
        hessian = analytic_hessian(fitted, current, penalty)
        try:
            factor = linalg.cholesky(hessian, lower=True, check_finite=True)
            direction = np.asarray(linalg.cho_solve((factor, True), -gradient, check_finite=True))
        except (linalg.LinAlgError, ValueError) as error:
            reason = "newton_hessian_not_spd_or_nonfinite"
            steps.append(
                {"step": number + 1, "status": "FAILED", "reason": reason, "error": str(error)}
            )
            break
        slope = float(np.dot(gradient, direction))
        if not np.isfinite(direction).all() or not math.isfinite(slope) or slope >= 0:
            reason = "newton_direction_not_finite_strict_descent"
            steps.append({"step": number + 1, "status": "FAILED", "reason": reason})
            break
        trials = []
        accepted = False
        for halving in range(MAX_HALVINGS + 1):
            alpha = 2.0 ** (-halving)
            candidate = current + alpha * direction
            candidate_certificate = literal_certificate(fitted, target, candidate, penalty)
            decision = accept_step(
                value,
                original_gradient_norm(certificate),
                candidate_certificate["objective"],
                original_gradient_norm(candidate_certificate),
                slope,
                alpha,
            )
            valid_algebra = bool(
                np.isfinite(candidate).all()
                and all(math.isfinite(x) for x in candidate_certificate.values())
                and candidate_certificate["literal_original_objective_abs_difference"]
                <= 1e-10 * max(1.0, abs(candidate_certificate["objective"]))
                and candidate_certificate["literal_original_gradient_max_abs_difference"] <= 1e-10
            )
            trials.append(
                {
                    "halvings": halving,
                    "step_size": alpha,
                    "objective": candidate_certificate["objective"],
                    "original_gradient_inf": original_gradient_norm(candidate_certificate),
                    "acceptance": decision if valid_algebra else None,
                }
            )
            if decision is not None and valid_algebra:
                steps.append(
                    {
                        "step": number + 1,
                        "status": "ACCEPTED",
                        "trials": trials,
                        "objective_before": value,
                        "original_gradient_inf_before": original_gradient_norm(certificate),
                        "directional_derivative": slope,
                        "direction_inf_norm": float(np.max(np.abs(direction))),
                        "objective_ulp": float(np.nextafter(value, np.inf) - value),
                    }
                )
                current, certificate = candidate, candidate_certificate
                accepted = True
                break
        if not accepted:
            reason = "newton_no_accepted_step_within_twenty_halvings"
            steps.append(
                {"step": number + 1, "status": "FAILED", "reason": reason, "trials": trials}
            )
            break
        if certificate_ok(certificate, initial_objective, gtol, ftol):
            reason = "original_gradient_certificate_satisfied"
            break
    return current, {
        "attempted": bool(limit),
        "maximum_steps": limit,
        "maximum_halvings": MAX_HALVINGS,
        "armijo_constant": ARMIJO,
        "iterations_used_before_newton": iterations_used,
        "iterations": len(steps),
        "accepted_steps": sum(x["status"] == "ACCEPTED" for x in steps),
        "steps": steps,
        "reason": reason,
        "final_certificate": certificate,
        "objective_jitter": 0.0,
        "intercept_penalized": False,
    }


def logistic_coefficient(
    fitted: Array,
    target: Array,
    penalty: float,
    options: Mapping[str, Any],
    *,
    gram: Array | None = None,
) -> tuple[Array, dict[str, Any]]:
    """The frozen two L-BFGS phases, followed only if needed by bounded Newton."""
    if (
        fitted.ndim != 2
        or not len(fitted)
        or fitted.shape[1] == 0
        or target.shape != (len(fitted),)
        or not np.isfinite(fitted).all()
        or not np.array_equal(fitted[:, 0], np.ones(len(fitted)))
        or not np.isin(target, [0.0, 1.0]).all()
        or not math.isfinite(penalty)
        or penalty <= 0
    ):
        raise ValueError("RP4_JUMP_NEWTON_INVALID_TRAINING_INPUT")
    maximum = int(options.get("maxiter", 1000))
    gtol, ftol = float(options.get("gtol", 1e-8)), float(options.get("ftol", 1e-12))
    if maximum < 1 or not all(math.isfinite(x) and x > 0 for x in (gtol, ftol)):
        raise ValueError("RP4_JUMP_NEWTON_INVALID_SOLVER_OPTIONS")
    frequency = float(target.mean())
    if frequency in (0.0, 1.0):
        return prior.logistic_coefficient(fitted, target, penalty, options, gram=gram)
    start = np.zeros(fitted.shape[1], dtype=np.float64)
    start[0] = math.log(frequency) - math.log1p(-frequency)
    gram_value = fitted.T @ fitted if gram is None else np.asarray(gram, dtype=np.float64)
    if gram_value.shape != (fitted.shape[1], fitted.shape[1]) or not np.isfinite(gram_value).all():
        raise ValueError("RP4_JUMP_NEWTON_INVALID_GRAM")
    try:
        factor = prior.fisher_factor(fitted, target, penalty, gram_value)
    except linalg.LinAlgError as error:
        raise original.ModelConvergenceError(
            "LOGISTIC_NEWTON",
            {
                "converged": False,
                "reason": "fisher_cholesky_failed",
                "lambda": penalty,
            },
        ) from error
    norm_bound = float(np.max(np.abs(factor).sum(axis=1)))
    theta_gtol = gtol / max(1.0, norm_bound)
    initial = prior.objective_original(fitted, target, start, penalty)[0]

    def recover(theta: Array) -> Array:
        return np.asarray(
            linalg.solve_triangular(factor.T, theta, lower=False, check_finite=False),
            dtype=np.float64,
        )

    def transformed(theta: Array) -> tuple[float, Array]:
        value, gradient = prior.objective_original(fitted, target, recover(theta), penalty)
        return value, np.asarray(
            linalg.solve_triangular(factor, gradient, lower=True, check_finite=False)
        )

    theta = factor.T @ start
    phases: list[dict[str, Any]] = []
    iterations = 0
    coefficient = start
    for phase_ftol in (ftol, 0.0):
        if iterations >= maximum:
            break
        result = minimize(
            transformed,
            theta,
            method="L-BFGS-B",
            jac=True,
            options={"maxiter": maximum - iterations, "gtol": theta_gtol, "ftol": phase_ftol},
        )
        iterations += int(result.nit)
        theta = np.asarray(result.x, dtype=np.float64)
        if theta.shape != start.shape or not np.isfinite(theta).all():
            raise original.ModelConvergenceError(
                "LOGISTIC_NEWTON",
                {
                    "converged": False,
                    "reason": "nonfinite_or_wrong_shape_coordinates",
                    "lambda": penalty,
                },
            )
        coefficient = recover(theta)
        value, gradient = prior.objective_original(fitted, target, coefficient, penalty)
        if not (
            np.isfinite(coefficient).all() and math.isfinite(value) and np.isfinite(gradient).all()
        ):
            raise original.ModelConvergenceError(
                "LOGISTIC_NEWTON",
                {
                    "converged": False,
                    "reason": "nonfinite_original_objective_or_gradient",
                    "lambda": penalty,
                },
            )
        phases.append(
            {
                "scipy_success": bool(result.success),
                "status": int(result.status),
                "message": str(result.message),
                "iterations": int(result.nit),
                "function_evaluations": int(result.nfev),
                "ftol": phase_ftol,
                "original_gradient_inf": float(np.max(np.abs(gradient))),
                "objective_over_n": value,
            }
        )
        if float(np.max(np.abs(gradient))) <= gtol and value <= initial + ftol:
            break
    certificate = literal_certificate(fitted, target, coefficient, penalty)
    newton: dict[str, Any] = {
        "attempted": False,
        "iterations": 0,
        "accepted_steps": 0,
        "steps": [],
        "reason": "not_eligible_for_newton_algebra_or_objective_guard",
    }
    algebra_finite = bool(
        np.isfinite(coefficient).all()
        and all(math.isfinite(x) for x in certificate.values())
        and certificate["objective"] <= initial + ftol
        and certificate["literal_original_objective_abs_difference"]
        <= 1e-10 * max(1.0, abs(certificate["objective"]))
        and certificate["literal_original_gradient_max_abs_difference"] <= 1e-10
    )
    if algebra_finite and original_gradient_norm(certificate) > gtol:
        coefficient, newton = newton_polish(
            fitted,
            target,
            coefficient,
            penalty,
            initial_objective=initial,
            iterations_used=iterations,
            maximum_iterations=maximum,
            gtol=gtol,
            ftol=ftol,
        )
        certificate = literal_certificate(fitted, target, coefficient, penalty)
    elif certificate_ok(certificate, initial, gtol, ftol):
        newton["reason"] = "original_certificate_satisfied"
    converged = bool(
        np.isfinite(coefficient).all() and certificate_ok(certificate, initial, gtol, ftol)
    )
    diagnostics = {
        "solver": "frozen_Fisher_LBFGS_then_bounded_analytic_Newton",
        "numerical_repair": "same_objective_analytic_hessian_newton_polish",
        "converged": converged,
        "iterations": iterations + newton.get("iterations", 0),
        "lbfgs_iterations": iterations,
        "maxiter": maximum,
        "gtol": gtol,
        "ftol": ftol,
        "transformed_gtol": theta_gtol,
        "fisher_cholesky_infinity_norm": norm_bound,
        "lambda": penalty,
        "single_class_training": False,
        "training_frequency": frequency,
        "intercept_penalized": False,
        "original_gradient_certificate_applicable": True,
        "objective_initial_divided_by_n": initial,
        "objective_total_divided_by_n": certificate["objective"],
        "objective_total_sum_scale": certificate["objective"] * len(target),
        **{k: v for k, v in certificate.items() if k not in ("objective", "literal_objective")},
        "phases": phases,
        "newton": newton,
    }
    if not converged:
        raise original.ModelConvergenceError("LOGISTIC_NEWTON", diagnostics)
    return coefficient, diagnostics


def fit_jump_linear(
    design: Array,
    target: Array,
    train: Mask,
    inner_fit: Mask,
    inner_valid: Mask,
    test: Mask,
    nullable_indices: Sequence[int],
    dates: npt.NDArray[Any],
    assets: npt.NDArray[Any],
    options: Mapping[str, Any],
) -> tuple[Array, dict[str, Any]]:
    """Unchanged preprocessing, five lambdas, validation and probability clipping."""
    original._validate_binary_inputs(
        design, target, train, inner_fit, inner_valid, test, dates, assets
    )
    penalties = original._penalties(options)
    if penalties != prior.REGISTERED_GRID:
        raise ValueError("RP4_JUMP_NEWTON_REGISTERED_LAMBDA_GRID_REQUIRED")
    tolerance = float(options.get("qr_relative_tolerance", QR_RELATIVE_TOLERANCE))
    logistic = options.get("logistic", {})
    inner = original._ridge_design(
        design[inner_fit], design[inner_valid], nullable_indices, qr_relative_tolerance=tolerance
    )
    gram = inner.fitted.T @ inner.fitted
    choices: list[dict[str, Any]] = []
    for penalty in penalties:
        coefficient, diagnostics = logistic_coefficient(
            inner.fitted, target[inner_fit], penalty, logistic, gram=gram
        )
        prediction = np.clip(expit(inner.predicting @ coefficient), prior.FLOOR, 1.0 - prior.FLOOR)
        score = equal_session_asset_mean(
            original._binary_loss(target[inner_valid], prediction),
            dates[inner_valid].tolist(),
            assets[inner_valid].tolist(),
        )
        if not math.isfinite(score):
            raise ValueError("RP4_JUMP_NEWTON_NONFINITE_VALIDATION_LOGLOSS")
        choices.append({"lambda": penalty, "validation_logloss": score, "solver": diagnostics})
    selected = min(choices, key=lambda row: (row["validation_logloss"], -row["lambda"]))
    refit = original._ridge_design(
        design[train], design[test], nullable_indices, qr_relative_tolerance=tolerance
    )
    coefficient, diagnostics = logistic_coefficient(
        refit.fitted, target[train], selected["lambda"], logistic
    )
    raw_probability = np.asarray(expit(refit.predicting @ coefficient))
    probability = np.clip(raw_probability, prior.FLOOR, 1.0 - prior.FLOOR)
    return probability, {
        "method": "L2_logistic_jump30_positive",
        "objective": "sum_binary_logloss_plus_lambda_l2_slopes",
        "numerical_repair": "Fisher_LBFGS_with_bounded_analytic_Newton_original_gradient_certified",
        "selected": selected,
        "candidates": choices,
        "lambda_grid": list(penalties),
        "train_rows": int(train.sum()),
        "inner_fit_rows": int(inner_fit.sum()),
        "inner_valid_rows": int(inner_valid.sum()),
        "inner_valid_sessions": np.unique(dates[inner_valid]).tolist(),
        "preprocessing": {"inner_fit": inner.record, "refit": refit.record},
        "solver_refit": diagnostics,
        "coefficients": coefficient.tolist(),
        "intercept_penalized": False,
        "tie_break": "larger_lambda",
        "class_weights": None,
        "probability_clip": [prior.FLOOR, 1.0 - prior.FLOOR],
        "count_probability_low": int(np.count_nonzero(raw_probability <= prior.FLOOR)),
        "count_probability_high": int(np.count_nonzero(raw_probability >= 1.0 - prior.FLOOR)),
        "prediction_rows": int(test.sum()),
    }
