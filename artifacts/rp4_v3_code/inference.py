"""Pure RP4 v3 inference: no data readers, fits, evaluation runners or file writes.

Loss contrasts arrive already equally aggregated by asset/session, chronological.
AUC instead pools equally weighted origins and resamples their entire sessions.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal

import numpy as np
import numpy.typing as npt
from scipy import sparse
from scipy.special import ndtr

from mds650.metrics import holm_adjust
from mds650.rp2.inference import newey_west_variance, session_block_draws

type Array = npt.NDArray[np.float64]
type IntArray = npt.NDArray[np.int64]
type Statistic = Literal["mean", "median", "trimmed_mean_5pct"]
type Alternative = Literal["greater", "two-sided"]

REPETITIONS = 9999
BLOCK_LENGTH = 5
SEED = 20260907
FAMILIES = ("log_ridge_harq", "lightgbm_qlike")
SETS = ("B0", "B1", "B2")
CONTRASTS = (("B1_over_B0", "B0", "B1"), ("B2_over_B1", "B1", "B2"))


def _vector(values: npt.ArrayLike) -> Array:
    result = np.asarray(values, dtype=np.float64)
    if result.ndim != 1:
        raise ValueError("RP4_V3_INFERENCE_REQUIRES_VECTOR")
    return result


def _parameters(repetitions: int, block_length: int, minimum_sessions: int) -> None:
    if repetitions < 1 or block_length < 1 or minimum_sessions < 3:
        raise ValueError("RP4_V3_INFERENCE_INVALID_PARAMETERS")


def _statistic(values: Array, name: Statistic, axis: int) -> Any:
    if name == "mean":
        return np.mean(values, axis=axis)
    if name == "median":
        return np.median(values, axis=axis)
    if name != "trimmed_mean_5pct":
        raise ValueError("RP4_V3_INFERENCE_UNKNOWN_STATISTIC")
    trim = int(np.floor(values.shape[axis] * 0.05))
    ordered = np.sort(values, axis=axis)
    selected = np.take(ordered, np.arange(trim, values.shape[axis] - trim), axis=axis)
    return np.mean(selected, axis=axis)


def _bootstrap_summary(estimate: float, draws: Array, alternative: Alternative) -> dict[str, Any]:
    if alternative not in ("greater", "two-sided"):
        raise ValueError("RP4_V3_INFERENCE_UNKNOWN_ALTERNATIVE")
    result: dict[str, Any] = {
        "estimate": estimate if np.isfinite(estimate) else None,
        "ci_low": None,
        "ci_high": None,
        "p_raw": None,
        "alternative": alternative,
        "interval": "two-sided percentile 95%; not inversion of centered-null p",
        "null": "delta <= 0" if alternative == "greater" else "delta = 0",
        "null_calibration": "resampled statistic minus observed statistic; +1 correction",
    }
    if not np.isfinite(estimate) or not np.isfinite(draws).all():
        return {**result, "status": "NO VERIFICABLE", "reason": "nonfinite bootstrap statistic"}
    if np.ptp(draws) == 0:
        return {**result, "status": "NO VERIFICABLE", "reason": "degenerate bootstrap statistic"}
    centered = draws - estimate
    exceed = (
        np.count_nonzero(centered >= estimate)
        if alternative == "greater"
        else np.count_nonzero(np.abs(centered) >= abs(estimate))
    )
    interval = np.quantile(draws, [0.025, 0.975], method="linear")
    return {
        **result,
        "status": "COMPUTED",
        "ci_low": float(interval[0]),
        "ci_high": float(interval[1]),
        "p_raw": float((exceed + 1) / (len(draws) + 1)),
        "null_exceedances": int(exceed),
        "bootstrap_repetitions": len(draws),
    }


def session_contrast(
    values: npt.ArrayLike,
    *,
    statistic: Statistic = "mean",
    alternative: Alternative = "greater",
    repetitions: int = REPETITIONS,
    block_length: int = BLOCK_LENGTH,
    seed: int = SEED,
    minimum_sessions: int = 10,
) -> dict[str, Any]:
    """Infer a paired session statistic; never drop nonfinite sessions or clip tails."""
    _parameters(repetitions, block_length, minimum_sessions)
    vector = _vector(values)
    if statistic not in ("mean", "median", "trimmed_mean_5pct") or alternative not in (
        "greater",
        "two-sided",
    ):
        raise ValueError("RP4_V3_INFERENCE_UNKNOWN_STATISTIC_OR_ALTERNATIVE")
    valid = bool(vector.size and np.isfinite(vector).all())
    with np.errstate(over="ignore", invalid="ignore"):
        estimate = float(_statistic(vector, statistic, 0)) if valid else None
    if estimate is not None and not np.isfinite(estimate):
        valid, estimate = False, None
    result: dict[str, Any] = {
        "estimate": estimate,
        "statistic": statistic,
        "N_sessions": len(vector),
        "bootstrap_block_length": block_length,
        "bootstrap_repetitions": repetitions,
        "bootstrap_seed": seed,
        "removed_each_tail": int(np.floor(0.05 * len(vector)))
        if statistic == "trimmed_mean_5pct"
        else 0,
        "ci_low": None,
        "ci_high": None,
        "p_raw": None,
        "alternative": alternative,
    }
    if len(vector) < minimum_sessions or not valid:
        return {**result, "status": "NO VERIFICABLE", "reason": "insufficient finite sessions"}
    if np.ptp(vector) == 0:
        return {**result, "status": "NO VERIFICABLE", "reason": "degenerate session variance"}
    draws = session_block_draws(
        vector, repetitions=repetitions, block_length=block_length, seed=seed
    )
    reduced = np.asarray(_statistic(draws, statistic, 1), dtype=np.float64)
    assert estimate is not None
    return {**result, **_bootstrap_summary(estimate, reduced, alternative)}


def posterior_probability_mean(
    values: npt.ArrayLike, *, minimum_sessions: int = 10
) -> dict[str, Any]:
    """Conditional Gaussian/HAC plug-in approximation, not a bootstrap sign frequency.

    Likelihood: sample mean | delta,v ~ Normal(delta,v), v=HAC5/n fixed at its
    estimate; prior p(delta) proportional to 1 on R. Conditional posterior is
    Normal(sample mean,v). Assumes a valid mean CLT, short-memory dependence and
    a consistent long-run variance estimate; ignores variance-estimation uncertainty.
    """
    if minimum_sessions < 3:
        raise ValueError("RP4_V3_INFERENCE_INVALID_PARAMETERS")
    vector = _vector(values)
    result: dict[str, Any] = {
        "status": "NO VERIFICABLE",
        "probability_positive": None,
        "mean": None,
        "HAC_SE": None,
        "HAC_lags": 5,
        "N_sessions": len(vector),
        "likelihood": "mean | delta,v ~ Normal(delta,v); v=HAC5/N plug-in",
        "prior": "flat improper prior on real-valued delta",
        "interpretation": "CONDITIONAL_ASYMPTOTIC_GAUSSIAN_APPROXIMATION",
        "not_bootstrap_sign_frequency": True,
        "variance_uncertainty_integrated": False,
        "assumptions": "mean CLT; short memory; finite variance; consistent HAC estimate",
    }
    if len(vector) < minimum_sessions or not np.isfinite(vector).all():
        return {**result, "reason": "insufficient finite sessions"}
    with np.errstate(over="ignore", invalid="ignore"):
        mean = float(vector.mean())
        long_run = newey_west_variance(vector, lags=5)
    if not np.isfinite(mean):
        return {**result, "reason": "nonfinite mean"}
    if not np.isfinite(long_run) or long_run <= 0:
        return {**result, "mean": mean, "reason": "nonpositive or nonfinite HAC variance"}
    standard_error = float(np.sqrt(long_run / len(vector)))
    return {
        **result,
        "status": "COMPUTED",
        "mean": mean,
        "HAC_SE": standard_error,
        "HAC_long_run_variance": long_run,
        "probability_positive": float(ndtr(mean / standard_error)),
    }


def _records(records: Sequence[Mapping[str, Any]], families: Sequence[str]) -> list[dict[str, Any]]:
    expected = {(family, c[0]) for family in families for c in CONTRASTS}
    actual = [(r["family"], r["contrast"]) for r in records]
    if len(families) != 2 or len(set(families)) != 2 or len(actual) != 4 or set(actual) != expected:
        raise ValueError("RP4_V3_INFERENCE_REQUIRES_FOUR_FAMILY_CONTRASTS")
    return [dict(r) for r in records]


def _available(row: Mapping[str, Any]) -> bool:
    p = row.get("p_raw")
    estimate = row.get("estimate")
    return bool(
        row.get("status") == "COMPUTED"
        and p is not None
        and estimate is not None
        and np.isfinite(p)
        and 0 <= p <= 1
        and np.isfinite(estimate)
    )


def holm_four(
    records: Sequence[Mapping[str, Any]], *, required_families: Sequence[str] = FAMILIES
) -> list[dict[str, Any]]:
    """Four bilateral secondary tests; invalid tests retain their multiplicity slot."""
    rows = _records(records, required_families)
    if any(r.get("alternative") != "two-sided" for r in rows):
        raise ValueError("RP4_V3_HOLM_SECONDARY_REQUIRES_BILATERAL_P")
    p_values = {str(i): float(r["p_raw"]) if _available(r) else 1.0 for i, r in enumerate(rows)}
    adjusted = holm_adjust(p_values)
    return [
        {
            **r,
            "p_holm": adjusted[str(i)] if _available(r) else None,
            "holm_family_size": 4,
            "holm_unavailable_treated_as_one": not _available(r),
            "inference_role": "SECONDARY",
        }
        for i, r in enumerate(rows)
    ]


def family_fixed_sequence(
    records: Sequence[Mapping[str, Any]],
    *,
    endpoint: str = "qlike_mean",
    primary: bool = True,
    required_families: Sequence[str] = FAMILIES,
    alpha: float = 0.05,
) -> dict[str, Any]:
    """H1 then H2 in each family. Global rejection requires ALL four directional gates."""
    if not 0 < alpha < 1 or (primary and endpoint != "qlike_mean"):
        raise ValueError("RP4_V3_SEQUENCE_INVALID_SCOPE")
    rows = _records(records, required_families)
    if any(r.get("alternative") != "greater" for r in rows):
        raise ValueError("RP4_V3_SEQUENCE_REQUIRES_DIRECTIONAL_P")
    if primary and any(r.get("statistic", "mean") != "mean" for r in rows):
        raise ValueError("RP4_V3_PRIMARY_SEQUENCE_REQUIRES_MEAN")
    if primary and any(
        r.get("inference_role", "PRIMARY") != "PRIMARY" or r.get("endpoint", endpoint) != endpoint
        for r in rows
    ):
        raise ValueError("RP4_V3_PRIMARY_SEQUENCE_SECONDARY_INPUT")
    output = []
    outcomes = {}
    for family in required_families:
        opened = True
        for contrast, _, _ in CONTRASTS:
            row = next(r for r in rows if (r["family"], r["contrast"]) == (family, contrast))
            available = _available(row)
            reject = bool(opened and available and row["estimate"] > 0 and row["p_raw"] <= alpha)
            state = (
                "NOT_TESTED"
                if not opened
                else "NO_VERIFICABLE"
                if not available
                else "REJECTED"
                if reject
                else "NOT_REJECTED"
            )
            output.append(
                {
                    **row,
                    "endpoint": endpoint,
                    "hypothesis_status": state,
                    "rejected": reject,
                    "p_for_decision": row["p_raw"] if opened and available else None,
                    "nominal_p_role": "USED_FOR_FIXED_SEQUENCE"
                    if opened and available
                    else "NO_PROMOTABLE",
                    "alpha": alpha,
                    "inference_role": "PRIMARY" if primary else "SECONDARY",
                }
            )
            opened = reject
        outcomes[family] = {"both_rejected": opened}
    return {
        "endpoint": endpoint,
        "scope": "PRIMARY_GLOBAL_JOINT" if primary else "SECONDARY_ENDPOINT_JOINT",
        "contrasts": output,
        "families": outcomes,
        "global_joint_reject": all(r["both_rejected"] for r in outcomes.values()),
        "claim_rule": "intersection-union: both ordered hypotheses in both required families",
        "any_family_claim_allowed": False,
    }


def quantile_loss_log_rv(
    log_rv: npt.ArrayLike, log_quantile_prediction: npt.ArrayLike, *, tau: float = 0.90
) -> Array:
    """Pinball loss in natural-log RV units; predictions are quantiles, not RV levels."""
    actual, forecast = _vector(log_rv), _vector(log_quantile_prediction)
    if not 0 < tau < 1 or actual.shape != forecast.shape:
        raise ValueError("RP4_V3_QUANTILE_INPUT_SHAPE_OR_TAU")
    if not np.isfinite(actual).all() or not np.isfinite(forecast).all():
        raise ValueError("RP4_V3_QUANTILE_NONFINITE_INPUT")
    with np.errstate(over="ignore", invalid="ignore"):
        difference = actual - forecast
        loss = np.where(difference >= 0, tau * difference, (tau - 1) * difference)
    if not np.isfinite(loss).all():
        raise ValueError("RP4_V3_QUANTILE_NONFINITE_LOSS")
    return np.asarray(loss, dtype=np.float64)


@dataclass(frozen=True)
class SessionAUC:
    """Exact Mann-Whitney pair counts U[positive_session,negative_session], ties=1/2."""

    pair_counts: Array
    positive_counts: Array
    negative_counts: Array
    session_labels: tuple[str, ...]

    @classmethod
    def from_predictions(
        cls,
        labels: npt.ArrayLike,
        predictions: npt.ArrayLike,
        sessions: npt.ArrayLike,
        *,
        group_chunk_size: int = 1024,
    ) -> SessionAUC:
        truth, scores = _vector(labels), _vector(predictions)
        ids = np.asarray(sessions)
        if (
            ids.ndim != 1
            or ids.shape != truth.shape
            or scores.shape != truth.shape
            or not truth.size
        ):
            raise ValueError("RP4_V3_AUC_INPUT_SHAPE")
        if np.isin(ids.astype(str), ["", "None", "nan", "NaT"]).any():
            raise ValueError("RP4_V3_AUC_INVALID_SESSION_LABEL")
        if (
            group_chunk_size < 1
            or not np.isfinite(scores).all()
            or not np.isin(truth, [0, 1]).all()
        ):
            raise ValueError("RP4_V3_AUC_INVALID_INPUT")
        names, codes = np.unique(ids, return_inverse=True)
        size = len(names)
        pos: Array = np.bincount(codes[truth == 1], minlength=size).astype(np.float64)
        neg: Array = np.bincount(codes[truth == 0], minlength=size).astype(np.float64)
        order = np.argsort(scores, kind="stable")
        scores, truth, codes = scores[order], truth[order], codes[order]
        starts = np.r_[0, np.flatnonzero(scores[1:] != scores[:-1]) + 1, len(scores)]
        matrix: Array = np.zeros((size, size), dtype=np.float64)
        previous_negatives: Array = np.zeros(size, dtype=np.float64)
        for start in range(0, len(starts) - 1, group_chunk_size):
            stop = min(start + group_chunk_size, len(starts) - 1)
            left, right = int(starts[start]), int(starts[stop])
            group: IntArray = np.repeat(np.arange(stop - start), np.diff(starts[start : stop + 1]))
            group_truth, group_codes = truth[left:right], codes[left:right]
            negatives: Array = np.zeros((stop - start, size), dtype=np.float64)
            mask = group_truth == 0
            np.add.at(negatives, (group[mask], group_codes[mask]), 1)
            # Scores below the current tie group win; ties contribute half a pair.
            below = previous_negatives + np.cumsum(negatives, axis=0) - 0.5 * negatives
            mask = group_truth == 1
            positives = sparse.csr_matrix(
                (np.ones(int(mask.sum())), (group_codes[mask], group[mask])),
                shape=(size, stop - start),
            )
            matrix += np.asarray(positives @ below)
            previous_negatives += negatives.sum(axis=0)
        return cls(matrix, pos, neg, tuple(str(name) for name in names))

    def evaluate(self, multiplicities: npt.ArrayLike, *, batch_size: int = 128) -> Array:
        """AUC of session-multiplicity resamples without re-sorting or duplicating origins."""
        counts = np.asarray(multiplicities, dtype=np.float64)
        if counts.ndim == 1:
            counts = counts[None, :]
        if (
            counts.ndim != 2
            or counts.shape[1] != len(self.session_labels)
            or batch_size < 1
            or not np.isfinite(counts).all()
            or (counts < 0).any()
            or not np.equal(counts, np.floor(counts)).all()
        ):
            raise ValueError("RP4_V3_AUC_INVALID_SESSION_MULTIPLICITIES")
        result: Array = np.full(len(counts), np.nan, dtype=np.float64)
        for start in range(0, len(counts), batch_size):
            subset = counts[start : start + batch_size]
            denominator = (subset @ self.positive_counts) * (subset @ self.negative_counts)
            numerator = np.sum((subset @ self.pair_counts) * subset, axis=1)
            np.divide(
                numerator,
                denominator,
                out=result[start : start + len(subset)],
                where=denominator > 0,
            )
        return result


def pooled_auc_inference(
    labels: npt.ArrayLike,
    predictions: Mapping[str, npt.ArrayLike],
    session_ids: npt.ArrayLike,
    *,
    family: str,
    repetitions: int = REPETITIONS,
    block_length: int = BLOCK_LENGTH,
    seed: int = SEED,
    minimum_sessions: int = 10,
) -> dict[str, Any]:
    """Secondary pooled AUC, paired whole-session draws and richer-minus-base deltas.

    Draws lacking either class are never silently removed or resampled. One such
    draw makes all CI/p/gates unavailable, while original point AUCs are retained.
    Sorting happens once per model. Pair matrices cost O(N*S); repeated AUC uses
    O(R*S^2), not R separate O(N log N) ranking calls. Memory is O(S^2+R*S).
    """
    _parameters(repetitions, block_length, minimum_sessions)
    if set(predictions) != set(SETS):
        raise ValueError("RP4_V3_AUC_REQUIRES_COMMON_B0_B1_B2")
    matrices = {
        key: SessionAUC.from_predictions(labels, predictions[key], session_ids) for key in SETS
    }
    first = matrices["B0"]
    size = len(first.session_labels)
    points = {key: float(value.evaluate(np.ones(size))[0]) for key, value in matrices.items()}
    result: dict[str, Any] = {
        "family": family,
        "endpoint": "jump_auc",
        "inference_role": "SECONDARY",
        "weighting": "pooled origins, one unit per origin; complete-session multiplicities",
        "ties": 0.5,
        "N_origins": len(_vector(labels)),
        "N_sessions": size,
        "bootstrap_repetitions": repetitions,
        "bootstrap_block_length": block_length,
        "bootstrap_seed": seed,
        "invalid_class_resamples": 0,
        "classless_policy": "no rerolls; any classless draw makes intervals/p/gates unavailable",
        "auc": {},
        "contrasts": [],
    }
    reason = ""
    draws: dict[str, Array] = {}
    if not all(np.isfinite(v) for v in points.values()):
        reason = "original pooled sample has one class"
    elif size < minimum_sessions:
        reason = "insufficient sessions"
    else:
        indices = session_block_draws(
            np.arange(size, dtype=np.float64),
            repetitions=repetitions,
            block_length=block_length,
            seed=seed,
        ).astype(np.int64)
        counts: Array = np.zeros((repetitions, size), dtype=np.float64)
        np.add.at(counts, (np.repeat(np.arange(repetitions), size), indices.ravel()), 1)
        del indices
        draws = {key: matrix.evaluate(counts) for key, matrix in matrices.items()}
        invalid = ~np.isfinite(draws["B0"])
        if any(not np.array_equal(~np.isfinite(draw), invalid) for draw in draws.values()):
            raise ValueError("RP4_V3_AUC_CLASS_MASK_DRIFT")
        result["invalid_class_resamples"] = int(invalid.sum())
        if invalid.any():
            reason = "classless session bootstrap draws"
    for name, point in points.items():
        item: dict[str, Any] = {
            "estimate": point if np.isfinite(point) else None,
            "ci_low": None,
            "ci_high": None,
            "status": "NO VERIFICABLE" if reason else "COMPUTED",
        }
        if reason:
            item["reason"] = reason
        else:
            interval = np.quantile(draws[name], [0.025, 0.975], method="linear")
            item.update(ci_low=float(interval[0]), ci_high=float(interval[1]))
        result["auc"][name] = item
    for contrast, base, expanded in CONTRASTS:
        delta = points[expanded] - points[base]
        item = (
            {
                "estimate": delta if np.isfinite(delta) else None,
                "ci_low": None,
                "ci_high": None,
                "p_raw": None,
                "status": "NO VERIFICABLE",
                "reason": reason,
                "alternative": "greater",
            }
            if reason
            else _bootstrap_summary(delta, draws[expanded] - draws[base], "greater")
        )
        result["contrasts"].append(
            {
                **item,
                "family": family,
                "contrast": contrast,
                "endpoint": "jump_auc",
                "inference_role": "SECONDARY",
                "sign": "richer_minus_base",
                "N_sessions": size,
                "N_origins": result["N_origins"],
            }
        )
    result["status"] = "NO VERIFICABLE" if reason else "COMPUTED"
    return result
