"""Block 8 - the boosted round count must be chosen from data, inside the training fold.

`_LIGHTGBM_ROUNDS = 300` was a module constant nobody chose and the published Delta_B1 for
`lightgbm_qlike` is a monotone increasing function of it (+0.001365 at 25 rounds,
+0.003275 at 300, +0.004440 at 600 on the development panel). A headline that moves by a
factor of three with a literal is not a measurement of the information set.

These tests pin the honest alternative: the number of rounds is selected by early stopping
on QLIKE over the LAST sessions of the training fold, so it is data-determined, it never
looks at the evaluated rows, and the number that was chosen is reported.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import numpy.typing as npt
import pytest

from mds650.rp2.ladder import fit_lightgbm, fit_lightgbm_qlike

type FloatArray = npt.NDArray[np.float64]


def _panel(
    *, signal: bool, sessions: int = 60, per_session: int = 40, seed: int = 11
) -> tuple[FloatArray, FloatArray, npt.NDArray[np.bool_], npt.NDArray[np.int64]]:
    """A session-structured panel, with or without anything for a tree to learn."""

    rng = np.random.default_rng(seed)
    size = sessions * per_session
    session_index = np.repeat(np.arange(sessions, dtype=np.int64), per_session)
    driver = rng.normal(size=size)
    extra = rng.normal(size=size)
    noise = rng.normal(scale=0.4, size=size)
    mean_log = -9.0 + (1.2 * driver - 0.5 * driver**2 if signal else 0.0)
    target = np.asarray(np.exp(mean_log + noise), dtype=np.float64)
    design = np.column_stack([np.ones(size), driver, driver**2, extra])
    train = session_index < int(sessions * 0.6)
    return design, target, train, session_index


def test_the_number_of_boosting_rounds_actually_run_depends_on_the_data(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The direct reproduction: today every fit runs the same literal, whatever it is fed."""

    import lightgbm as lgb

    real_train = lgb.train
    requested: list[int] = []

    def spy(*args: Any, **kwargs: Any) -> Any:
        requested.append(int(kwargs["num_boost_round"]))
        return real_train(*args, **kwargs)

    monkeypatch.setattr(lgb, "train", spy)
    for signal in (True, False):
        design, target, train, sessions = _panel(signal=signal)
        fit_lightgbm_qlike(design, target, train, sessions=sessions)

    assert len(set(requested)) > 1, (
        f"every boosted fit ran the same literal number of rounds: {requested}"
    )


def test_a_boosted_fit_refuses_to_select_rounds_without_real_session_ranks() -> None:
    """Rows are not a valid surrogate for the session-level stopping protocol."""

    design, target, train, _ = _panel(signal=True)
    with pytest.raises(ValueError, match="RP2_LADDER_BOOSTED_SESSIONS_REQUIRED"):
        fit_lightgbm_qlike(design, target, train)


def test_the_boosted_round_count_is_data_determined_and_not_a_module_constant() -> None:
    """A panel with nothing to learn must stop far earlier than one with structure."""

    noise_record: dict[str, object] = {}
    signal_record: dict[str, object] = {}
    design, target, train, sessions = _panel(signal=False)
    fit_lightgbm_qlike(design, target, train, sessions=sessions, record=noise_record)
    design, target, train, sessions = _panel(signal=True)
    fit_lightgbm_qlike(design, target, train, sessions=sessions, record=signal_record)

    assert int(noise_record["selected_rounds"]) >= 1  # type: ignore[call-overload]
    assert noise_record["selected_rounds"] != signal_record["selected_rounds"], (
        "the round count is the same on a panel with signal and on one without: "
        "it is not being chosen from the data"
    )
    assert not noise_record["cap_reached"]
    # The published run's literal. Nothing may reproduce it by construction.
    assert int(noise_record["selected_rounds"]) != 300  # type: ignore[call-overload]


def test_the_round_count_is_selected_on_qlike_over_held_out_training_sessions() -> None:
    """The criterion that decides the programme is the criterion that stops the booster."""

    record: dict[str, object] = {}
    design, target, train, sessions = _panel(signal=True)
    fit_lightgbm_qlike(design, target, train, sessions=sessions, record=record)

    assert record["selection_metric"] == "qlike"
    assert int(record["inner_validation_sessions"]) >= 1  # type: ignore[call-overload]
    # The rows the round count was chosen on are training rows and only training rows.
    assert int(record["inner_validation_rows"]) < int(train.sum())  # type: ignore[call-overload]
    # The sensitivity is published rather than left to be rediscovered: what the training
    # fold scored at the count it chose, and what it scored at the constant it replaced.
    assert record["superseded_rounds"] == 300
    assert isinstance(record["inner_validation_loss_at_selected"], float)
    at_superseded = record["inner_validation_loss_at_superseded"]
    assert at_superseded is None or float(at_superseded) >= float(
        record["inner_validation_loss_at_selected"]  # type: ignore[arg-type]
    )


def test_the_round_count_never_looks_at_the_evaluated_rows() -> None:
    """Corrupting every held-out row must leave the selected number of rounds untouched."""

    design, target, train, sessions = _panel(signal=True)
    clean: dict[str, object] = {}
    corrupted: dict[str, object] = {}
    fit_lightgbm_qlike(design, target, train, sessions=sessions, record=clean)
    poisoned = target.copy()
    poisoned[~train] *= 1000.0
    fit_lightgbm_qlike(design, poisoned, train, sessions=sessions, record=corrupted)

    assert clean["selected_rounds"] == corrupted["selected_rounds"]


def test_both_tree_families_stop_on_the_criterion_that_decides_the_programme() -> None:
    """The other tree fitter carried the same literal and gets the same treatment.

    Both boosters stop on QLIKE, not on their own training loss. The two families exist to
    isolate the effect of the training objective; selecting their complexity by different
    criteria would put a second difference inside that comparison.
    """

    record: dict[str, object] = {}
    design, target, train, sessions = _panel(signal=True)
    fit_lightgbm(design, target, train, sessions=sessions, record=record)

    assert record["selection_metric"] == "qlike"
    assert int(record["selected_rounds"]) >= 1  # type: ignore[call-overload]
    assert not record["cap_reached"]
    assert int(record["selected_rounds"]) != 300  # type: ignore[call-overload]
