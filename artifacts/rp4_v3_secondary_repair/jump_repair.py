"""Train-only numerical repair of the unchanged RP4 v3 logistic objective.

This module has no empirical runner or data-loading side effects. Completed v3
components belong to the original immutable evaluation and must be reused by a
separately authorized caller, not fitted again through this module.
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
from scipy import linalg
from scipy.optimize import minimize
from scipy.special import expit

FLOOR = original.PROBABILITY_FLOOR
REGISTERED_GRID = (0.0001, 0.01, 1.0, 100.0, 10000.0)


def objective_original(
    fitted: Array, target: Array, coefficient: Array, penalty: float
) -> tuple[float, Array]:
    """Original coordinates and SUM loss + lambda L2, divided entirely by N."""
    raw = fitted @ coefficient
    sign = 2.0 * target - 1.0
    # Algebraically identical to logaddexp(0, raw) - target*raw; no cancellation
    # for a correctly classified positive label with a large positive logit.
    loss = np.logaddexp(0.0, -sign * raw)
    slopes = coefficient.copy()
    slopes[0] = 0.0
    value = float((loss.sum() + penalty * np.dot(slopes, slopes)) / len(target))
    residual = -sign * expit(-sign * raw)
    gradient = (fitted.T @ residual + 2.0 * penalty * slopes) / len(target)
    return value, np.asarray(gradient, dtype=np.float64)


def fisher_factor(fitted: Array, target: Array, penalty: float, gram: Array) -> Array:
    """Cholesky metric only: no ridge jitter, objective or feature alteration."""
    frequency = float(target.mean())
    matrix = frequency * (1.0 - frequency) * gram / len(target)
    matrix = (matrix + matrix.T) * 0.5
    diagonal = np.arange(1, fitted.shape[1])
    matrix[diagonal, diagonal] += 2.0 * penalty / len(target)
    return np.asarray(linalg.cholesky(matrix, lower=True, check_finite=True))


def logistic_coefficient(
    fitted: Array,
    target: Array,
    penalty: float,
    options: Mapping[str, Any],
    *,
    gram: Array | None = None,
) -> tuple[Array, dict[str, Any]]:
    """Equivalent Fisher-preconditioned L-BFGS with original-gradient certificate.

    For M=L L.T, theta=L.T beta, hence beta=L^-T theta and
    gradient_theta=L^-1 gradient_beta. The entire penalized objective, including
    the unpenalized intercept, is evaluated in beta coordinates. An initial
    relative-function stop without original-coordinate convergence is continued
    once with ftol=0, sharing the original total 1000-iteration budget. No candidate
    lambda is omitted when it fails the certificate.
    """
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
        raise ValueError("RP4_JUMP_REPAIR_INVALID_TRAINING_INPUT")
    maximum = int(options.get("maxiter", 1000))
    gtol = float(options.get("gtol", 1e-8))
    ftol = float(options.get("ftol", 1e-12))
    if maximum < 1 or not all(math.isfinite(x) and x > 0 for x in (gtol, ftol)):
        raise ValueError("RP4_JUMP_REPAIR_INVALID_SOLVER_OPTIONS")
    frequency = float(target.mean())
    if frequency in (0.0, 1.0):
        # The original explicitly registered empirical-frequency exception.
        coefficient, diagnostics = original._logistic_coefficient(fitted, target, penalty, options)
        return coefficient, {
            **diagnostics,
            "numerical_repair": "unchanged_single_class_exception",
            "original_gradient_certificate_applicable": False,
        }
    start = np.zeros(fitted.shape[1], dtype=np.float64)
    start[0] = math.log(frequency) - math.log1p(-frequency)
    gram_value = fitted.T @ fitted if gram is None else np.asarray(gram, dtype=np.float64)
    if gram_value.shape != (fitted.shape[1], fitted.shape[1]) or not np.isfinite(gram_value).all():
        raise ValueError("RP4_JUMP_REPAIR_INVALID_GRAM")
    try:
        factor = fisher_factor(fitted, target, penalty, gram_value)
    except linalg.LinAlgError as error:
        raise original.ModelConvergenceError(
            "LOGISTIC_REPAIR",
            {"converged": False, "reason": "fisher_cholesky_failed", "lambda": penalty},
        ) from error
    norm_bound = float(np.max(np.abs(factor).sum(axis=1)))
    theta_gtol = gtol / max(1.0, norm_bound)
    initial_objective = objective_original(fitted, target, start, penalty)[0]

    def recover(theta: Array) -> Array:
        return np.asarray(
            linalg.solve_triangular(factor.T, theta, lower=False, check_finite=False),
            dtype=np.float64,
        )

    def transformed(theta: Array) -> tuple[float, Array]:
        value, gradient = objective_original(fitted, target, recover(theta), penalty)
        return value, np.asarray(
            linalg.solve_triangular(factor, gradient, lower=True, check_finite=False)
        )

    theta = factor.T @ start
    phases: list[dict[str, Any]] = []
    iterations = 0
    value, gradient = objective_original(fitted, target, start, penalty)
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
                "LOGISTIC_REPAIR",
                {
                    "converged": False,
                    "reason": "nonfinite_or_wrong_shape_coordinates",
                    "lambda": penalty,
                },
            )
        coefficient = recover(theta)
        value, gradient = objective_original(fitted, target, coefficient, penalty)
        if not (
            np.isfinite(coefficient).all() and math.isfinite(value) and np.isfinite(gradient).all()
        ):
            raise original.ModelConvergenceError(
                "LOGISTIC_REPAIR",
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
        if (
            np.isfinite(coefficient).all()
            and math.isfinite(value)
            and np.isfinite(gradient).all()
            and float(np.max(np.abs(gradient))) <= gtol
            and value <= initial_objective + ftol
        ):
            break
    coordinate_value, coordinate_gradient = transformed(theta)
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
    difference = abs(literal_value - value)
    gradient_difference = float(np.max(np.abs(literal_gradient - gradient)))
    finite = bool(
        np.isfinite(coefficient).all()
        and np.isfinite(gradient).all()
        and math.isfinite(value)
        and math.isfinite(coordinate_value)
    )
    gradient_norm = float(np.max(np.abs(gradient)))
    original_gradient_norm = float(np.max(np.abs(literal_gradient)))
    converged = bool(
        finite
        and max(gradient_norm, original_gradient_norm) <= gtol
        and value <= initial_objective + ftol
        and difference <= 1e-10 * max(1.0, abs(value))
        and gradient_difference <= 1e-10
    )
    diagnostics = {
        "solver": "scipy_L-BFGS-B_in_initial_Fisher_Cholesky_coordinates",
        "numerical_repair": "invertible_parameter_preconditioning_same_objective",
        "converged": converged,
        "iterations": iterations,
        "maxiter": maximum,
        "gtol": gtol,
        "ftol": ftol,
        "transformed_gtol": theta_gtol,
        "fisher_cholesky_infinity_norm": norm_bound,
        "fisher_diagonal_min": float(np.diag(factor).min()),
        "fisher_diagonal_max": float(np.diag(factor).max()),
        "objective_initial_divided_by_n": initial_objective,
        "objective_total_sum_scale": value * len(target),
        "objective_total_divided_by_n": value,
        "gradient_inf_norm_objective_over_n": original_gradient_norm,
        "stable_gradient_inf_norm": gradient_norm,
        "transformed_gradient_inf_norm": float(np.max(np.abs(coordinate_gradient))),
        "literal_original_objective_abs_difference": difference,
        "literal_original_gradient_max_abs_difference": gradient_difference,
        "coordinate_objective_abs_difference": abs(coordinate_value - value),
        "original_gradient_certificate_applicable": True,
        "lambda": penalty,
        "single_class_training": False,
        "intercept_penalized": False,
        "training_frequency": frequency,
        "phases": phases,
    }
    if not converged:
        raise original.ModelConvergenceError("LOGISTIC_REPAIR", diagnostics)
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
    """Unchanged v3 preprocessing/validation; only the missing linear solver changes."""
    original._validate_binary_inputs(
        design, target, train, inner_fit, inner_valid, test, dates, assets
    )
    penalties = original._penalties(options)
    if penalties != REGISTERED_GRID:
        raise ValueError("RP4_JUMP_REPAIR_REGISTERED_LAMBDA_GRID_REQUIRED")
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
        prediction = np.clip(expit(inner.predicting @ coefficient), FLOOR, 1.0 - FLOOR)
        score = equal_session_asset_mean(
            original._binary_loss(target[inner_valid], prediction),
            dates[inner_valid].tolist(),
            assets[inner_valid].tolist(),
        )
        if not math.isfinite(score):
            raise ValueError("RP4_JUMP_REPAIR_NONFINITE_VALIDATION_LOGLOSS")
        choices.append({"lambda": penalty, "validation_logloss": score, "solver": diagnostics})
    selected = min(choices, key=lambda row: (row["validation_logloss"], -row["lambda"]))
    refit = original._ridge_design(
        design[train], design[test], nullable_indices, qr_relative_tolerance=tolerance
    )
    coefficient, diagnostics = logistic_coefficient(
        refit.fitted, target[train], selected["lambda"], logistic
    )
    raw_probability = np.asarray(expit(refit.predicting @ coefficient))
    probability = np.clip(raw_probability, FLOOR, 1.0 - FLOOR)
    return probability, {
        "method": "L2_logistic_jump30_positive",
        "objective": "sum_binary_logloss_plus_lambda_l2_slopes",
        "numerical_repair": "Fisher_preconditioned_original_gradient_certified",
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
        "probability_clip": [FLOOR, 1.0 - FLOOR],
        "count_probability_low": int(np.count_nonzero(raw_probability <= FLOOR)),
        "count_probability_high": int(np.count_nonzero(raw_probability >= 1.0 - FLOOR)),
        "prediction_rows": int(test.sum()),
    }
