"""The PBO estimator has to be pinned by its known answers, not by running.

Two properties carry the whole method. Under pure noise the in-sample winner is equally
likely to land anywhere out of sample, so PBO must sit near 0.5; a estimator that returns a
comfortable number on noise would certify every search ever run. And when one candidate is
genuinely better on every session, PBO must be 0; a estimator that cannot recognise a real
winner would condemn every search instead. Everything else here guards a boundary.
"""

from __future__ import annotations

import numpy as np
import pytest

from mds650.rp2.pbo import (
    BacktestOverfitting,
    probability_of_backtest_overfitting,
    session_performance_matrix,
)

SESSIONS = 320
ORIGINS_PER_SESSION = 4


def _sessions() -> np.ndarray:
    return np.repeat(np.arange(SESSIONS, dtype=np.int64), ORIGINS_PER_SESSION)


def _noise(candidates: int, seed: int) -> dict[str, np.ndarray]:
    rng = np.random.default_rng(seed)
    size = SESSIONS * ORIGINS_PER_SESSION
    return {f"family|set{i}": rng.normal(1.0, 0.25, size) for i in range(candidates)}


def test_pure_noise_lands_near_one_half_on_average() -> None:
    """No candidate is better, so the in-sample winner is a coin flip out of sample.

    Averaged, not measured once. A single draw of identically distributed candidates has a
    standard deviation of roughly 0.24 around 0.5 -- one seed can return 0.94 and mean
    nothing -- so a single-draw assertion here would either be flaky or so loose it would
    pass for a broken estimator. Twelve seeds bring the standard error of the mean to about
    0.07, which is tight enough to fail an estimator that is actually biased.
    """

    values = [
        probability_of_backtest_overfitting(_noise(6, seed=seed), _sessions(), blocks=10).pbo
        for seed in range(2000, 2012)
    ]
    mean = float(np.mean(values))
    assert 0.35 <= mean <= 0.65, f"noise should not be certified: mean PBO={mean:.3f}"


def test_pbo_falls_as_the_real_separation_grows() -> None:
    """The estimator has to be monotone in the thing it claims to measure.

    Candidates identical but for a constant offset in true mean, with the offset swept from
    none to several standard errors of a candidate's total mean. If PBO did not fall, it
    would be reporting sampling noise rather than the stability of the winner.
    """

    def average_pbo(separation: float) -> float:
        values = []
        for seed in range(3000, 3008):
            rng = np.random.default_rng(seed)
            draw = rng.normal(1.0, 0.25, (SESSIONS, 5)) - np.arange(5) * separation
            losses = {f"family|set{i}": draw[:, i] for i in range(5)}
            values.append(
                probability_of_backtest_overfitting(
                    losses, np.arange(SESSIONS, dtype=np.int64), blocks=10
                ).pbo
            )
        return float(np.mean(values))

    none, some, plenty = average_pbo(0.0), average_pbo(0.015), average_pbo(0.040)
    assert none > some > plenty, f"not monotone: {none:.3f} -> {some:.3f} -> {plenty:.3f}"
    assert plenty < 0.10


def test_candidates_with_identical_total_means_are_pure_selection() -> None:
    """A hard algebraic anchor, not a statistical one.

    With complementary halves of equal size the total mean fixes one from the other:
    ``mean_out = 2 * mean_total - mean_in``. If every candidate carries the same total, then
    ``mean_out = constant - mean_in`` exactly, so the in-sample maximum *is* the
    out-of-sample minimum on every single split and PBO must be exactly 1. Any deviation
    here means the complement is being formed wrongly or the rank is inverted.
    """

    rng = np.random.default_rng(19)
    draw = rng.normal(1.0, 0.25, (SESSIONS, 6))
    draw = draw - draw.mean(axis=0, keepdims=True) + 1.0
    losses = {f"family|set{i}": draw[:, i] for i in range(6)}
    result = probability_of_backtest_overfitting(losses, np.arange(SESSIONS, dtype=np.int64))
    assert result.pbo == 1.0
    assert result.degraded_share > 0.0


def test_a_genuinely_better_candidate_drives_pbo_to_zero() -> None:
    """One candidate has a lower loss on every session; no split can rank it below median."""

    losses = _noise(6, seed=12)
    winner = np.full(SESSIONS * ORIGINS_PER_SESSION, 0.10)
    losses["family|winner"] = winner
    result = probability_of_backtest_overfitting(losses, _sessions())
    assert result.pbo == 0.0
    assert result.median_logit > 0.0
    assert result.degraded_share == 0.0


def test_a_candidate_that_only_wins_early_is_caught() -> None:
    """A candidate tuned to the first half is exactly what PBO exists to expose.

    Its loss is far lower on the early sessions and far higher on the late ones. Splits
    whose in-sample half is early crown it, and out of sample it is last.
    """

    size = SESSIONS * ORIGINS_PER_SESSION
    losses = _noise(5, seed=13)
    half = size // 2
    tuned = np.empty(size)
    tuned[:half] = 0.10
    tuned[half:] = 5.00
    losses["family|overfit"] = tuned
    result = probability_of_backtest_overfitting(losses, _sessions())
    assert result.pbo > 0.30, f"a half-sample winner should be flagged: PBO={result.pbo}"


def test_identical_candidates_report_no_winner() -> None:
    """A degenerate field must average its tied ranks, not crown whoever sorts first."""

    size = SESSIONS * ORIGINS_PER_SESSION
    flat = np.full(size, 0.5)
    losses = {f"family|set{i}": flat.copy() for i in range(4)}
    result = probability_of_backtest_overfitting(losses, _sessions())
    assert result.pbo == 1.0, "all-tied means the winner is never above median"
    assert result.median_logit == pytest.approx(0.0, abs=1e-12)


def test_session_is_the_unit_not_the_origin() -> None:
    """Origins inside a session are collapsed before any split is drawn."""

    matrix, names = session_performance_matrix(_noise(3, seed=14), _sessions())
    assert matrix.shape == (SESSIONS, 3)
    assert names == ("family|set0", "family|set1", "family|set2")


def test_a_session_missing_for_one_candidate_is_refused() -> None:
    """Ranking candidates over different session sets would rank the filter, not the model."""

    losses = _noise(3, seed=15)
    losses["family|set1"][:ORIGINS_PER_SESSION] = np.nan
    with pytest.raises(ValueError, match="RP2_PBO_SESSION_SET_MISMATCH"):
        session_performance_matrix(losses, _sessions())


def test_two_candidates_are_refused() -> None:
    with pytest.raises(ValueError, match="RP2_PBO_TOO_FEW_CANDIDATES"):
        probability_of_backtest_overfitting(_noise(2, seed=16), _sessions())


def test_odd_or_tiny_block_counts_are_refused() -> None:
    for blocks in (3, 15, 2):
        with pytest.raises(ValueError, match="RP2_PBO_BLOCKS_INVALID"):
            probability_of_backtest_overfitting(_noise(4, seed=17), _sessions(), blocks=blocks)


def test_too_few_sessions_for_the_block_count_is_refused() -> None:
    sessions = np.repeat(np.arange(10, dtype=np.int64), 2)
    losses = {f"family|set{i}": np.full(20, float(i) + 1.0) for i in range(3)}
    with pytest.raises(ValueError, match="RP2_PBO_TOO_FEW_SESSIONS"):
        probability_of_backtest_overfitting(losses, sessions)


def test_the_split_count_is_the_full_combinatorial_family() -> None:
    """C(16, 8) = 12,870. A shortcut here would quietly turn PBO into a sample of splits."""

    result = probability_of_backtest_overfitting(_noise(4, seed=18), _sessions())
    assert result.splits == 12870
    assert result.blocks == 16
    assert result.sessions == SESSIONS
    assert isinstance(result, BacktestOverfitting)
    assert set(result.as_dict()) == {
        "pbo",
        "median_logit",
        "degraded_share",
        "candidates",
        "sessions",
        "blocks",
        "splits",
        "sessions_per_block",
    }
    assert result.sessions_per_block == SESSIONS / 16
