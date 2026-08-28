"""`_window_sum` must lose only the origins whose own window holds the absent minute.

`bars.build_session_grid` writes NaN into the volume of a minute whose price moved on a
recorded volume of zero: a price cannot move without trades, so that zero is an absence
and not a count. That repair is correct. What this pins is the amplification downstream:
a running sum over the minute series carries the NaN from the minute it appears to the
end of the session-asset, so every later origin loses `volume_30` and `dollar_volume_30`
whether or not its own 30-minute window contains the absent minute. The signature of the
amplification is that the lost origins form a contiguous suffix rather than the short
run of origins that straddle the gap.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import numpy as np

REPO = Path(__file__).resolve().parents[2]


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "rp2_block4_b0_panel", REPO / "scripts" / "rp2_block4_b0_panel.py"
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


BLOCK4 = _load()


def test_absent_minute_only_voids_the_windows_that_contain_it() -> None:
    """One NaN at index 3, a window of 3, and eight minutes of explicit values.

    Only the origins 3, 4 and 5 have index 3 inside ``[origin - 2, origin]``. Origins 6
    and 7 read minutes 4-6 and 5-7, none of which is absent, so both must carry a finite
    sum.
    """

    values = np.array([1.0, 2.0, 3.0, np.nan, 5.0, 6.0, 7.0, 8.0], dtype=np.float64)
    origins = np.array([2, 3, 4, 5, 6, 7], dtype=np.int64)

    result = BLOCK4._window_sum(values, origins, 3)

    assert np.array_equal(np.isnan(result), [False, True, True, True, False, False]), (
        f"expected the NaN to touch exactly origins 3-5, got {result!r}"
    )
    np.testing.assert_allclose(result[[0, 4, 5]], [6.0, 18.0, 21.0])


def test_a_single_absence_does_not_void_every_later_origin() -> None:
    """The amplification's own signature: a contiguous suffix of lost origins.

    With a 30-minute window over a full session, one absent minute early on must cost at
    most the handful of origins whose window straddles it - never every origin from there
    to the close.
    """

    minutes = 390
    values = np.ones(minutes, dtype=np.float64)
    values[40] = np.nan
    origins = np.arange(30, minutes, 5, dtype=np.int64)

    lost = np.isnan(BLOCK4._window_sum(values, origins, 30))

    assert lost.sum() <= 7, f"one absent minute cost {int(lost.sum())} of {origins.size} origins"
    assert not lost[-1], "the last origin of the session lost its window sum"


def test_a_clean_series_is_unchanged() -> None:
    values = np.arange(1.0, 9.0, dtype=np.float64)
    origins = np.array([2, 4, 7], dtype=np.int64)

    np.testing.assert_allclose(BLOCK4._window_sum(values, origins, 3), [6.0, 12.0, 21.0])
