"""Block 8 - the model ladder.

Level 1 (smooth / parametric), level 2 (non-linear tabular) and level 3 (hierarchical
partial pooling) are implemented here behind one interface: every model is fitted on a
boolean training mask and returns a variance forecast for **all** rows, so the caller
decides what is in and out of sample.

Level 4 (trade-sequence networks) is intentionally absent: the program gates it behind
"only after demonstrating that the tabular baseline does not capture the signal", and no
deep-learning stack is installed in this environment.  Its absence is reported, not faked.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Final

import numpy as np
import numpy.typing as npt
from sklearn.linear_model import (  # type: ignore[import-untyped]
    GammaRegressor,
    Ridge,
    TweedieRegressor,
)
from sklearn.preprocessing import SplineTransformer  # type: ignore[import-untyped]

from mds650.rp2.qlike_objective import EXPONENT_CLIP, lightgbm_metric, lightgbm_objective

if TYPE_CHECKING:  # lightgbm is imported lazily at call time; the types are not.
    import lightgbm as lgb

type FloatArray = npt.NDArray[np.float64]

VARIANCE_FLOOR: Final = 1e-12
#: An upper bound on the search, not a choice. `_LIGHTGBM_ROUNDS = 300` used to be the
#: number of rounds every boosted fit ran, and the published Delta_B1 for lightgbm_qlike is
#: a monotone increasing function of it: +0.001365 at 25 rounds, +0.003275 at 300 (the
#: published figure), +0.004440 at 600, while the test QLIKE of B0 is minimised at 150. A
#: headline that triples with a literal nobody chose is not a measurement of an information
#: set. The count is now chosen by early stopping inside the training fold; this cap only
#: bounds the run time, and `cap_reached` in the fit record says when it bound the answer.
_LIGHTGBM_MAX_ROUNDS: Final = 2000
#: Patience of the early stop, in rounds without an improvement on the inner validation.
_LIGHTGBM_EARLY_STOPPING_ROUNDS: Final = 50
#: The constant this replaced. Every fit reports what its own training fold thought of it,
#: beside what the fold chose, so the sensitivity of the old headline does not have to be
#: rediscovered by anyone reading the artifact.
_LIGHTGBM_SUPERSEDED_ROUNDS: Final = 300
#: The last share of the TRAINING sessions, held out to choose the round count. Fixed here
#: before any contrast was looked at; it never touches the evaluated rows.
_LIGHTGBM_INNER_VALIDATION_SHARE: Final = 0.2
_LIGHTGBM_LEAVES: Final = 31
_LIGHTGBM_LEARNING_RATE: Final = 0.05


def _log(values: FloatArray) -> FloatArray:
    return np.log(np.maximum(values, VARIANCE_FLOOR))


def _smearing(residuals: FloatArray) -> float:
    return float(np.exp(0.5 * float(np.var(residuals))))


def canonical_float_array_sha256(values: FloatArray) -> str:
    """Hash one forecast or loss vector in a platform-independent representation."""

    array = np.ascontiguousarray(np.asarray(values, dtype=np.dtype("<f8")))
    if array.ndim != 1:
        raise ValueError("RP2_LADDER_HASH_VECTOR_REQUIRED")
    header = f"RP2_FLOAT64_LE_V1:{array.size}".encode("ascii")
    return hashlib.sha256(header + b"\0" + array.tobytes()).hexdigest()


def _canonical_mask_sha256(mask: npt.NDArray[np.bool_]) -> str:
    """Hash the exact inner-validation membership rather than its row count."""

    values = np.asarray(mask, dtype=np.bool_)
    packed = np.packbits(values, bitorder="little")
    header = f"RP2_BOOL_MASK_V1:{values.size}".encode("ascii")
    return hashlib.sha256(header + b"\0" + packed.tobytes()).hexdigest()


def _require_boosted_sessions(
    train: npt.NDArray[np.bool_], sessions: npt.NDArray[np.int64] | None
) -> npt.NDArray[np.int64]:
    """Require the real session ranks used by the outer split for boosted fitting."""

    if sessions is None:
        raise ValueError("RP2_LADDER_BOOSTED_SESSIONS_REQUIRED")
    index = np.asarray(sessions)
    if index.ndim != 1 or index.shape != train.shape:
        raise ValueError("RP2_LADDER_BOOSTED_SESSION_SHAPE")
    if not np.issubdtype(index.dtype, np.integer):
        raise ValueError("RP2_LADDER_BOOSTED_SESSION_RANKS_REQUIRED")
    return np.asarray(index, dtype=np.int64)


def fit_log_ols(design: FloatArray, target: FloatArray, train: npt.NDArray[np.bool_]) -> FloatArray:
    """Ordinary least squares on log variance with lognormal retransformation."""

    response = _log(target)
    coefficients, *_ = np.linalg.lstsq(design[train], response[train], rcond=None)
    fitted = design @ coefficients
    return np.asarray(np.exp(fitted) * _smearing(response[train] - fitted[train]))


def fit_ridge_log(
    design: FloatArray, target: FloatArray, train: npt.NDArray[np.bool_], *, alpha: float = 1.0
) -> FloatArray:
    """Ridge on log variance - the regularised sibling of :func:`fit_log_ols`."""

    response = _log(target)
    model = Ridge(alpha=alpha, fit_intercept=False)
    model.fit(design[train], response[train])
    fitted = np.asarray(model.predict(design), dtype=np.float64)
    return np.asarray(np.exp(fitted) * _smearing(response[train] - fitted[train]))


def fit_gamma_glm(
    design: FloatArray, target: FloatArray, train: npt.NDArray[np.bool_], *, alpha: float = 1e-4
) -> FloatArray:
    """Gamma GLM with a log link, fitted on the variance scale directly."""

    model = GammaRegressor(alpha=alpha, fit_intercept=False, max_iter=500)
    model.fit(design[train], np.maximum(target[train], VARIANCE_FLOOR))
    return np.asarray(model.predict(design), dtype=np.float64)


def fit_tweedie_glm(
    design: FloatArray, target: FloatArray, train: npt.NDArray[np.bool_], *, power: float = 1.7
) -> FloatArray:
    """Tweedie GLM, a compromise between Poisson and Gamma variance functions."""

    model = TweedieRegressor(power=power, alpha=1e-4, fit_intercept=False, max_iter=500)
    model.fit(design[train], np.maximum(target[train], VARIANCE_FLOOR))
    return np.asarray(model.predict(design), dtype=np.float64)


def fit_spline_additive(
    design: FloatArray, target: FloatArray, train: npt.NDArray[np.bool_], *, knots: int = 6
) -> FloatArray:
    """Additive spline model: a GAM in the generalised-additive sense, on log variance.

    Each column gets its own B-spline basis and the bases are summed - no interactions -
    which is what makes it a genuinely different family from a boosted tree.
    """

    response = _log(target)
    transformer = SplineTransformer(n_knots=knots, degree=3, include_bias=False)
    transformer.fit(design[train])
    basis = np.asarray(transformer.transform(design), dtype=np.float64)
    basis = np.column_stack([np.ones(basis.shape[0]), basis])
    model = Ridge(alpha=1.0, fit_intercept=False)
    model.fit(basis[train], response[train])
    fitted = np.asarray(model.predict(basis), dtype=np.float64)
    return np.asarray(np.exp(fitted) * _smearing(response[train] - fitted[train]))


def _inner_validation_split(
    train: npt.NDArray[np.bool_], sessions: npt.NDArray[np.int64] | None
) -> tuple[npt.NDArray[np.bool_], npt.NDArray[np.int64]]:
    """Split the TRAINING fold in two along time, and never touch anything else.

    The last ``_LIGHTGBM_INNER_VALIDATION_SHARE`` of the training sessions is held out to
    choose the number of boosting rounds. It is a strict subset of ``train``, so no
    evaluated row is ever consulted and the choice cannot be a look at the answer.

    ``sessions`` must be the same session rank the outer split is cut on, so a session is
    never split across the two sides. A row index is not a valid fallback: it can straddle
    a session and invalidate the early-stopping protocol.
    """

    index = _require_boosted_sessions(train, sessions)
    train_sessions = np.unique(index[train])
    if train_sessions.size < 2:
        raise ValueError("RP2_LADDER_INNER_SPLIT_TOO_SMALL")
    cut = int(round(train_sessions.size * (1.0 - _LIGHTGBM_INNER_VALIDATION_SHARE)))
    cut = min(max(cut, 1), train_sessions.size - 1)
    boundary = train_sessions[cut]
    return train & (index >= boundary), index


def _fit_boosted(
    parameters: dict[str, object],
    design: FloatArray,
    label: FloatArray,
    train: npt.NDArray[np.bool_],
    *,
    sessions: npt.NDArray[np.int64] | None,
    init_score: float | None,
    objective: Callable[[FloatArray], Any] | None,
    metric: Callable[[FloatArray], Any],
    criterion: FloatArray,
    metric_name: str,
    record: dict[str, object] | None,
) -> lgb.Booster:
    """Choose the number of rounds on held-out training sessions, then refit on all of them.

    Two fits, and the reason for the second is that the round count is the only thing this
    procedure is allowed to take from the inner split. Refitting on the whole training fold
    keeps the fitted sample identical to the one the frozen protocol declares, so the change
    against the published run is the round count and nothing else.

    ``objective`` and ``metric`` are factories, not callables: the QLIKE objective and the
    QLIKE eval function each capture the target of the rows they are given, and the search
    and the refit are given different rows.
    """

    import lightgbm as lgb

    def dataset(mask: npt.NDArray[np.bool_]) -> lgb.Dataset:
        scores = None if init_score is None else np.full(int(mask.sum()), init_score)
        return lgb.Dataset(
            design[mask], label=label[mask], init_score=scores, free_raw_data=False
        )

    def bound(mask: npt.NDArray[np.bool_]) -> dict[str, object]:
        if objective is None:
            return parameters
        return {**parameters, "objective": objective(criterion[mask])}

    inner_valid, index = _inner_validation_split(train, sessions)
    inner_fit = train & ~inner_valid
    feval = metric(criterion[inner_valid])
    history: dict[str, dict[str, list[float]]] = {}
    search = lgb.train(
        bound(inner_fit),
        dataset(inner_fit),
        num_boost_round=_LIGHTGBM_MAX_ROUNDS,
        valid_sets=[dataset(inner_valid)],
        feval=feval,
        callbacks=[
            lgb.early_stopping(_LIGHTGBM_EARLY_STOPPING_ROUNDS, verbose=False),
            lgb.record_evaluation(history),
        ],
    )
    selected = max(int(search.best_iteration), 1)
    if record is not None:
        curve = next(iter(next(iter(history.values())).values()))
        record.update(
            {
                "selected_rounds": selected,
                "max_rounds": _LIGHTGBM_MAX_ROUNDS,
                "early_stopping_rounds": _LIGHTGBM_EARLY_STOPPING_ROUNDS,
                "inner_validation_share": _LIGHTGBM_INNER_VALIDATION_SHARE,
                "inner_validation_sessions": int(np.unique(index[inner_valid]).size),
                "inner_validation_rows": int(inner_valid.sum()),
                "inner_validation_split_sha256": _canonical_mask_sha256(inner_valid),
                "selection_metric": metric_name,
                "cap_reached": selected >= _LIGHTGBM_MAX_ROUNDS,
                "inner_validation_loss_at_selected": float(curve[selected - 1]),
                # None when the search stopped before reaching it, which is itself the
                # statement that the training fold never wanted that many rounds.
                "superseded_rounds": _LIGHTGBM_SUPERSEDED_ROUNDS,
                "inner_validation_loss_at_superseded": (
                    float(curve[_LIGHTGBM_SUPERSEDED_ROUNDS - 1])
                    if len(curve) >= _LIGHTGBM_SUPERSEDED_ROUNDS
                    else None
                ),
            }
        )
    return lgb.train(bound(train), dataset(train), num_boost_round=selected)


def fit_lightgbm(
    design: FloatArray,
    target: FloatArray,
    train: npt.NDArray[np.bool_],
    *,
    monotone: Sequence[int] | None = None,
    seed: int = 20260818,
    sessions: npt.NDArray[np.int64] | None = None,
    record: dict[str, object] | None = None,
) -> FloatArray:
    """Gradient-boosted trees on log variance, optionally with monotone constraints."""

    response = _log(target)
    parameters: dict[str, object] = {
        "objective": "regression",
        # No built-in metric: the early stop must see QLIKE and only QLIKE. The callback
        # stops on whichever tracked metric runs out of patience first, so leaving l2 on
        # would let the training loss decide when the criterion has stopped improving.
        "metric": "None",
        "num_leaves": _LIGHTGBM_LEAVES,
        "learning_rate": _LIGHTGBM_LEARNING_RATE,
        "verbose": -1,
        "seed": seed,
        "deterministic": True,
        "force_row_wise": True,
    }
    if monotone is not None:
        parameters["monotone_constraints"] = list(monotone)
    # How many rounds to run is a decision, and every decision in this programme is made on
    # QLIKE. Stopping this family on its own training loss instead would make the round
    # count of the log-MSE tree and the round count of the QLIKE tree answers to different
    # questions, and the comparison between them - which exists to isolate the objective -
    # would carry a second difference nobody asked for. One caveat, stated rather than
    # hidden: the returned forecast multiplies by a smearing factor that the eval does not
    # apply, so the level the stop sees is the raw one.
    booster = _fit_boosted(
        parameters,
        design,
        response,
        train,
        sessions=sessions,
        init_score=None,
        objective=None,
        metric=lightgbm_metric,
        criterion=target,
        metric_name="qlike",
        record=record,
    )
    fitted = np.asarray(booster.predict(design), dtype=np.float64)
    return np.asarray(np.exp(fitted) * _smearing(response[train] - fitted[train]))


def fit_lightgbm_qlike(
    design: FloatArray,
    target: FloatArray,
    train: npt.NDArray[np.bool_],
    *,
    monotone: Sequence[int] | None = None,
    seed: int = 20260818,
    sessions: npt.NDArray[np.int64] | None = None,
    record: dict[str, object] | None = None,
) -> FloatArray:
    """Gradient-boosted trees that descend QLIKE itself.

    The decision criterion of this programme is QLIKE, and the log-MSE variant is judged on
    it after being trained on something else. Log-MSE is symmetric in log space: it charges
    the same for over-forecasting a variance by a factor of two as for under-forecasting it
    by a factor of two. QLIKE does not, and QLIKE is what decides the result.

    No smearing correction is applied and none is needed. The minimiser of
    ``E[y e^{-z} + z]`` is ``e^z = E[y | x]``, so the raw score already targets the
    conditional mean of the variance rather than of its logarithm — the retransformation
    bias the log-MSE fit has to correct for never arises.
    """

    parameters: dict[str, object] = {
        "metric": "None",
        "num_leaves": _LIGHTGBM_LEAVES,
        "learning_rate": _LIGHTGBM_LEARNING_RATE,
        "verbose": -1,
        "seed": seed,
        "deterministic": True,
        "force_row_wise": True,
    }
    if monotone is not None:
        parameters["monotone_constraints"] = list(monotone)
    # The booster starts from the training mean log variance rather than from zero: a first
    # step of exp(0) = 1 against a target near 1e-8 is a gradient of -1e8.
    start = float(np.mean(_log(target[train])))
    # The objective and the metric are bound to whatever rows the fit is given, and the
    # early-stopping search and the refit are given different ones, so both are built by
    # `_fit_boosted` from the mask in hand rather than from `train` once. `lightgbm_metric`
    # was written for exactly this and had no caller outside the tests.
    booster = _fit_boosted(
        parameters,
        design,
        _log(target),
        train,
        sessions=sessions,
        init_score=start,
        objective=lightgbm_objective,
        metric=lightgbm_metric,
        criterion=target,
        metric_name="qlike",
        record=record,
    )
    raw = start + np.asarray(booster.predict(design), dtype=np.float64)
    return np.asarray(np.exp(np.clip(raw, -EXPONENT_CLIP, EXPONENT_CLIP)), dtype=np.float64)


@dataclass(frozen=True, slots=True)
class PooledIntercepts:
    """Empirical-Bayes partial pooling of per-group offsets."""

    grand_mean: float
    between_variance: float
    offsets: dict[int, float]
    #: The sampling variance of each group's mean, with the SESSION as the unit. Published
    #: so a reader can see the term tau^2 is measured against rather than infer it.
    sampling_variance: dict[int, float]

    def apply(self, groups: npt.NDArray[np.int64]) -> FloatArray:
        return np.array([self.offsets.get(int(g), 0.0) for g in groups], dtype=np.float64)


def session_weighted_level(losses: FloatArray, sessions: npt.NDArray[np.int64]) -> float:
    """Mean loss with the session as the unit, matching the contrasts beside it.

    The contrasts aggregate to the session first, because origins five minutes apart share
    overlapping thirty-minute targets: a busy session would otherwise outweigh a quiet one
    and an early close would count for less than a full day. The published LEVELS averaged
    every evaluated row instead, so `level(base) - level(expanded)` did not reproduce the
    published delta - by 2.2 % for gamma_glm and 2.0 % for ridge_log on the RP2-v3
    development panel. Two numbers in one record that do not describe the same quantity are
    worse than either alone.
    """

    if losses.shape != sessions.shape:
        raise ValueError("RP2_LADDER_LEVEL_SHAPE_MISMATCH")
    finite = np.isfinite(losses)
    if not finite.any():
        return float("nan")
    values, labels = losses[finite], sessions[finite]
    means = np.array([values[labels == label].mean() for label in np.unique(labels)])
    return float(means.mean())


def partial_pooling(
    residuals: FloatArray,
    groups: npt.NDArray[np.int64],
    train: npt.NDArray[np.bool_],
    *,
    sessions: npt.NDArray[np.int64],
) -> PooledIntercepts:
    """Shrink per-group mean residuals toward zero by their own signal-to-noise ratio.

    ``theta_g ~ N(mu, tau^2)`` estimated by moments: the shrinkage weight is
    ``tau^2 / (tau^2 + v_g)``, where ``v_g`` is the sampling variance of group g's mean.
    Total pooling when groups are indistinguishable, none when they are sharply different.
    This is the level-3 model the program asks for, without a sampler.

    ``v_g`` is measured with the SESSION as the unit. It was ``sigma^2 / n_g`` with ``n_g``
    the number of ORIGINS in the group - 15,270 per asset in the published fit - which is
    the sampling variance only if residuals inside a group are independent. They are not:
    origins are five minutes apart and share overlapping thirty-minute targets, which is
    why `aggregate_by_session`, `_contrast` and `session_weighted_level` all refuse to
    treat them as the unit. On the published development fit the origin-based term was
    1.4473e-5 against a session-clustered 8.5937e-5, 5.9 times smaller, so tau^2 came out
    inflated and the intercepts were shrunk too little: weight 0.969 against 0.817.
    """

    if residuals.shape != groups.shape or residuals.shape != train.shape:
        raise ValueError("RP2_POOLING_SHAPE_MISMATCH")
    if sessions.shape != residuals.shape:
        raise ValueError("RP2_POOLING_SESSION_SHAPE_MISMATCH")
    usable = train & np.isfinite(residuals)
    if not usable.any():
        return PooledIntercepts(
            grand_mean=0.0, between_variance=0.0, offsets={}, sampling_variance={}
        )
    grand = float(np.mean(residuals[usable]))
    means: dict[int, float] = {}
    sampling: dict[int, float] = {}
    for group in np.unique(groups[usable]):
        mask = usable & (groups == group)
        block = residuals[mask]
        means[int(group)] = float(np.mean(block))
        # One value per session, then the variance of those over their own count. A group
        # observed on many origins of few sessions has the precision of the few sessions.
        labels = sessions[mask]
        per_session = np.array(
            [block[labels == label].mean() for label in np.unique(labels)], dtype=np.float64
        )
        sampling[int(group)] = (
            float(np.var(per_session, ddof=1)) / per_session.size if per_session.size > 1 else 0.0
        )
    # The sample variance of G group means, not the population variance of them. With the
    # six assets this programme runs, `np.var`'s default divisor of G understates the
    # spread by a sixth, and tau^2 is the numerator of the shrinkage weight: a smaller tau
    # pulls every per-asset intercept harder toward the grand mean than the data supports.
    # The subtraction below floors at zero, so an understated spread can collapse the term
    # entirely and turn partial pooling into total pooling without saying so.
    spread = float(np.var(list(means.values()), ddof=1)) if len(means) > 1 else 0.0
    # E[Var(m_g | theta_g)] over the groups, each measured on its own sessions.
    between = max(spread - float(np.mean(list(sampling.values()))), 0.0) if sampling else 0.0
    offsets: dict[int, float] = {}
    for group, mean in means.items():
        weight = between / (between + sampling[group]) if between > 0.0 else 0.0
        offsets[group] = weight * (mean - grand)
    return PooledIntercepts(
        grand_mean=grand,
        between_variance=between,
        offsets=offsets,
        sampling_variance=sampling,
    )


#: Every model the ladder runs, keyed by name.
Fitter = Callable[[FloatArray, FloatArray, npt.NDArray[np.bool_]], FloatArray]

#: The families whose round count is chosen inside the training fold. They take the session
#: ranks so the inner split never cuts a session, and a dict to write the chosen count into,
#: because a number selected by a procedure and then not reported is still a number nobody
#: can check.
BoostedFitter = Callable[..., FloatArray]

#: The three primary families of the frozen research contract. No fourth family is added
#: until these are closed; a family introduced after the numbers arrive is a search over
#: model space wearing the costume of a robustness check.
PRIMARY_MODELS: Final[tuple[str, ...]] = ("gamma_glm", "ridge_log", "lightgbm_qlike")

LADDER: Final[dict[str, Fitter]] = {
    "log_ols": fit_log_ols,
    "ridge_log": fit_ridge_log,
    "gamma_glm": fit_gamma_glm,
    "tweedie_glm": fit_tweedie_glm,
    "spline_additive": fit_spline_additive,
    "lightgbm": fit_lightgbm,
    "lightgbm_qlike": fit_lightgbm_qlike,
}

BOOSTED_LADDER: Final[dict[str, BoostedFitter]] = {
    "lightgbm": fit_lightgbm,
    "lightgbm_qlike": fit_lightgbm_qlike,
}


def fit_ladder_model(
    model_name: str,
    design: FloatArray,
    target: FloatArray,
    train: npt.NDArray[np.bool_],
    *,
    sessions: npt.NDArray[np.int64] | None = None,
    record: dict[str, object] | None = None,
) -> FloatArray:
    """Fit one registered family, making session-ranked boosting the only boosted route."""

    if model_name in BOOSTED_LADDER:
        return BOOSTED_LADDER[model_name](
            design,
            target,
            train,
            sessions=_require_boosted_sessions(train, sessions),
            record=record,
        )
    if model_name not in LADDER:
        raise ValueError(f"RP2_LADDER_MODEL_UNKNOWN:{model_name}")
    if record is not None:
        raise ValueError("RP2_LADDER_NONBOOSTED_RECORD")
    return LADDER[model_name](design, target, train)

#: Families that count as genuinely independent for the two-family requirement.
def assert_primary_models(models: Sequence[str]) -> None:
    """Refuse a run that would report results without one of the deciding families.

    The contract freezes three families and the programme's conclusions are read off them.
    A run that quietly dropped one would still produce an artifact, and the artifact would
    look complete.
    """

    fitted = set(models)
    for name in PRIMARY_MODELS:
        if name not in fitted:
            raise ValueError(f"RP2_PRIMARY_MODEL_MISSING:{name}")


INDEPENDENT_FAMILIES: Final[dict[str, str]] = {
    "log_ols": "smooth_linear",
    "ridge_log": "smooth_linear",
    "gamma_glm": "smooth_glm",
    "tweedie_glm": "smooth_glm",
    "spline_additive": "smooth_additive",
    "lightgbm": "tree",
    "lightgbm_qlike": "tree",
}
