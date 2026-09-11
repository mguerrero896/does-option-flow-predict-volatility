"""Public saved-loss arithmetic; no model refit or sealed-data access."""

import csv
import json
from math import fsum, isclose
from pathlib import Path


def test_development_leave_one_session_out_and_final_concentration():
    root = Path(__file__).resolve().parents[2]
    specification = json.loads((root / "artifacts/rp4_v4_a1/specification.json").read_text("utf-8"))
    sets = specification["feature_sets"]
    added = set(sets["B2"]) - set(sets["B1"])
    assert len(added) == 69
    assert {
        "b2_5m_d_iv",
        "b2_30m_d_mid_rel",
        "b2_30m_d_spread",
        "rp4_dealer_gamma_net",
        "b2_5m_window_empty",
    } <= added
    windows = {}
    for block, count in (("b2", 419), ("b3", 25)):
        path = root / f"artifacts/rp4_v4_{block}_rv15/session_losses.csv"
        with path.open(encoding="utf-8", newline="") as source:
            rows = list(csv.DictReader(source))
        assert len(rows) == count
        assert len({row["session_date"] for row in rows}) == count
        baseline = [float(row["loss__log_ridge_harq__B1"]) for row in rows]
        delta = [
            value - float(row["loss__log_ridge_harq__B2"])
            for value, row in zip(baseline, rows, strict=True)
        ]
        windows[block] = (rows, baseline, delta)

    _, baseline, delta = windows["b2"]
    total_loss, total_delta = fsum(baseline), fsum(delta)
    omitted = [
        100 * (total_delta - d) / (total_loss - b) for b, d in zip(baseline, delta, strict=True)
    ]
    assert min(omitted) > 0
    assert isclose(min(omitted), 0.5431997891123251, abs_tol=1e-12)
    assert isclose(max(omitted), 0.706946106808249, abs_tol=1e-12)

    rows, _, delta = windows["b3"]
    event = delta[next(i for i, row in enumerate(rows) if row["session_date"] == "2026-08-31")]
    assert isclose(fsum(delta), 0.11918283137061729, abs_tol=1e-14)
    assert isclose(100 * event / fsum(delta), 97.53745813998502, abs_tol=1e-10)
