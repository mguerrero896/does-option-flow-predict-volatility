"""The probability of backtest overfitting, by combinatorially symmetric cross-validation.

`docs/research_program_v2.md` lists "probability of backtest overfitting" among the
metrics the programme reports. Nothing computed it. Hansen's SPA, already in
`inference.py`, answers a neighbouring question -- *does any candidate genuinely beat the
benchmark once selection is accounted for* -- but it does not answer the one a reader of a
twelve-cell search actually asks: **if I pick the cell that looked best, how often is that
cell below median out of sample?**

The method is Bailey, Borwein, Lopez de Prado and Zhu (2014), *The Probability of Backtest
Overfitting*. Split the evaluated sessions into ``blocks`` contiguous, equal sub-periods.
For every way of choosing half of them as in-sample -- there are C(blocks, blocks/2), and
the complement is out-of-sample -- take the configuration that wins in-sample and read the
rank it achieves out-of-sample. Its relative rank omega gives a logit
``lambda = log(omega / (1 - omega))``, and PBO is the share of splits whose logit is at or
below zero: the share on which the in-sample winner lands in the bottom half.

Why combinatorially symmetric rather than one chronological split: a single split gives one
number and no distribution, so a lucky boundary is indistinguishable from a real edge. Every
combination is used as both training and testing exactly once across the family, which is
what makes the procedure symmetric and its null well defined -- under pure noise the
in-sample winner is equally likely to land anywhere out of sample, so PBO tends to 0.5.

The unit is the session, never the origin. Five-minute origins share overlapping
thirty-minute targets, so a per-origin split would slice a block through the middle of a
target that both sides can see. `inference.aggregate_by_session` is the same collapse the
rest of block 10 applies, for the same reason.

The scope of the candidate set is a methodological choice and this module does not make it.
`inference.assert_family_matched` states the house rule: a family compared against itself
across information sets isolates the information, while a family compared against another
family confounds estimator with information. The caller passes whichever universe it means
and labels the result accordingly.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from itertools import combinations
from typing import Final

import numpy as np
import numpy.typing as npt

from mds650.rp2.inference import aggregate_by_session

type FloatArray = npt.NDArray[np.float64]
type IntArray = npt.NDArray[np.int64]

#: Sub-periods the evaluated sessions are cut into. Sixteen gives C(16,8) = 12,870 splits,
#: which is enough resolution for a share without the combinatorics running away. The paper
#: uses the same figure.
DEFAULT_BLOCKS: Final = 16
#: Below this the split count collapses and PBO stops being a distribution.
MIN_BLOCKS: Final = 4
#: Two candidates cannot produce a meaningful rank: the in-sample winner is either first or
#: second out of sample, and PBO degenerates to a coin flip by construction.
MIN_CANDIDATES: Final = 3


@dataclass(frozen=True)
class BacktestOverfitting:
    """One PBO measurement over one candidate universe."""

    #: Share of splits whose in-sample winner ranks at or below the out-of-sample median.
    pbo: float
    #: Median of the logits; positive means the winner usually holds up.
    median_logit: float
    #: Share of splits on which the in-sample winner has a *worse* out-of-sample score than
    #: the median candidate's in-sample score -- performance degradation, reported by the
    #: same paper alongside PBO.
    degraded_share: float
    candidates: tuple[str, ...]
    sessions: int
    blocks: int
    splits: int
    #: Sessions per sub-period. At two the method is at its floor: a block is a pair of
    #: sessions, so the in-sample mean it contributes is barely an estimate. A reader
    #: comparing a PBO from 156 sessions with one from 32 needs to see this.
    sessions_per_block: float

    def as_dict(self) -> dict[str, object]:
        return {
            "pbo": self.pbo,
            "median_logit": self.median_logit,
            "degraded_share": self.degraded_share,
            "candidates": list(self.candidates),
            "sessions": self.sessions,
            "blocks": self.blocks,
            "splits": self.splits,
            "sessions_per_block": self.sessions_per_block,
        }


def session_performance_matrix(
    losses: Mapping[str, FloatArray], sessions: IntArray
) -> tuple[FloatArray, tuple[str, ...]]:
    """Collapse per-origin losses to a sessions x candidates matrix of *performance*.

    Performance is negated loss, so that larger is better and "the winner" means the
    maximum throughout. Candidates are sorted by name so the matrix is reproducible.

    A session that is not finite for every candidate is dropped whole. Dropping per column
    instead would let two candidates be ranked on different sessions, and the rank would
    then be partly a statement about which rows each one survived.
    """

    if len(losses) < MIN_CANDIDATES:
        raise ValueError(f"RP2_PBO_TOO_FEW_CANDIDATES:{len(losses)}")
    names = tuple(sorted(losses))
    columns: list[FloatArray] = []
    labels: IntArray | None = None
    for name in names:
        values = np.asarray(losses[name], dtype=np.float64)
        if values.shape != sessions.shape:
            raise ValueError(f"RP2_PBO_SHAPE_MISMATCH:{name}")
        # Aggregate on the raw losses, then negate: the mean of a negation is the negation
        # of the mean, but doing it in this order keeps the session filter identical to the
        # one every other statistic in block 10 applies.
        means, means_labels = aggregate_by_session(values, sessions)
        if labels is None:
            labels = means_labels
        elif not np.array_equal(labels, means_labels):
            # One candidate was finite on a session another was not. Intersecting silently
            # would hide that; the caller has a common evaluation mask for exactly this.
            raise ValueError(f"RP2_PBO_SESSION_SET_MISMATCH:{name}")
        columns.append(-means)
    matrix = np.column_stack(columns)
    finite = np.isfinite(matrix).all(axis=1)
    return matrix[finite], names


def _relative_rank(values: FloatArray, index: int) -> float:
    """Where ``index`` sits among ``values``, on (0, 1), larger being better.

    Ties share the average rank, so a flat field cannot be read as a win. The endpoints are
    excluded by construction -- with n candidates the extreme ranks map to 1/(n+1) and
    n/(n+1) -- which is what keeps the logit finite without an arbitrary clamp.
    """

    order = np.argsort(np.argsort(values))  # dense ranks, 0-based, ties broken by position
    # Average the ranks of exact ties so a degenerate universe reports 0.5, not a winner.
    tied = values == values[index]
    rank = float(order[tied].mean())
    return (rank + 1.0) / (values.size + 1.0)


def probability_of_backtest_overfitting(
    losses: Mapping[str, FloatArray],
    sessions: IntArray,
    *,
    blocks: int = DEFAULT_BLOCKS,
) -> BacktestOverfitting:
    """PBO over one candidate universe, by combinatorially symmetric cross-validation.

    ``losses`` maps a candidate label to its per-origin loss; lower loss is better.
    ``sessions`` labels every origin with its session. Returns the share of splits on which
    the in-sample winner lands at or below the out-of-sample median.

    Read it as a probability, not a gate: 0.5 is what pure noise gives, so a value near 0.5
    says the search learned nothing that survives resampling, and a value near 0 says the
    winner is stable across every way of cutting the sample in half.
    """

    if blocks < MIN_BLOCKS or blocks % 2 != 0:
        raise ValueError(f"RP2_PBO_BLOCKS_INVALID:{blocks}")
    matrix, names = session_performance_matrix(losses, sessions)
    rows = matrix.shape[0]
    if rows < blocks * 2:
        # Fewer than two sessions per block: a block would be a single session and the
        # in-sample mean it produces is that session, not an estimate of anything.
        raise ValueError(f"RP2_PBO_TOO_FEW_SESSIONS:{rows}:{blocks}")

    # Contiguous, chronological blocks. np.array_split handles a remainder by making the
    # earlier blocks one longer, which keeps every session in exactly one block.
    partitions = np.array_split(np.arange(rows), blocks)
    half = blocks // 2
    logits: list[float] = []
    degraded = 0
    for chosen in combinations(range(blocks), half):
        in_sample = np.concatenate([partitions[b] for b in chosen])
        complement = [b for b in range(blocks) if b not in set(chosen)]
        out_sample = np.concatenate([partitions[b] for b in complement])
        in_scores = matrix[in_sample].mean(axis=0)
        out_scores = matrix[out_sample].mean(axis=0)
        winner = int(np.argmax(in_scores))
        omega = _relative_rank(out_scores, winner)
        logits.append(float(np.log(omega / (1.0 - omega))))
        # Performance degradation: the winner's out-of-sample score against the median
        # in-sample score of the field it beat.
        if out_scores[winner] < float(np.median(in_scores)):
            degraded += 1

    values = np.asarray(logits, dtype=np.float64)
    return BacktestOverfitting(
        pbo=float((values <= 0.0).mean()),
        median_logit=float(np.median(values)),
        degraded_share=float(degraded / values.size),
        candidates=names,
        sessions=rows,
        blocks=blocks,
        splits=int(values.size),
        sessions_per_block=round(rows / blocks, 2),
    )
