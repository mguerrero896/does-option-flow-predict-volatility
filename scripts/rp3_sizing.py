"""Honest sizing of the RP3 program: how many virgin sessions the primary test needs.

RP3's primary contrast is DeltaB2|B1 on RV30 in the lightgbm_qlike family, with B2
compressed to the ONE frozen linear index of ``artifacts/rp3/b2_index_theta.json``. RV60
was the exploratory sweep's preferred target and this script is what killed it: its
development effect through the same index is negative, so the artifact records rv_60 as
NOT_ACHIEVABLE and the primary is the replication of the rv_30 cell that had already
cleared the sequential budget. Both measurements are kept. The
sealed read happens once, so the read date has to be justified before Phase B trains
anything: this script measures the effect the D role actually shows on each listed target, the
long-run variance of the per-session QLIKE-difference series that the inference machinery
will test, and asks the only sizing question that survives the winner's curse — the
selection came from a 36-target exploratory sweep, so the expected effect is the observed
D effect divided by two, and N_PRIMARY is the smallest session count whose minimum
detectable effect reaches that halved target. If the D effect on rv_60 is not positive,
the honest answer is NOT_ACHIEVABLE and the artifact says so without decoration.

The secondary test (direction at 120 minutes) is NOT re-measured here. Its power was
frozen in ``artifacts/rp2_ext4_power/power.json`` (sessions_for_80pct ~= 42 on the V
role); halving the effect quadruples the sessions, so 168 nominal sessions are recorded as
a citation of that artifact, caveat included.

Everything downstream reads ``artifacts/rp3/sizing.json``; like the theta artifact it
carries a canonical self-hash so an edited copy cannot pose as the frozen plan.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Final

import numpy as np
import polars as pl

from mds650.metrics import qlike_losses
from mds650.rp2.inference import (
    DEFAULT_ALPHA,
    DEFAULT_POWER,
    SESSION_BLOCK_LENGTH,
    aggregate_by_session,
    minimum_detectable_effect_from_long_run_variance,
    newey_west_variance,
    session_contrast,
)
from mds650.rp2.ladder import LADDER
from mds650.rp2.panel import (
    B0_FEATURES,
    B1_FEATURES,
    B2_FEATURES,
    JOIN_KEYS,
    chronological_split,
    common_evaluation_mask,
    load_merged_panel,
    mask_sha256,
    session_rank,
)
from mds650.rp2.preprocessing import fold_design

ROOT: Final = Path(__file__).resolve().parents[1]
DEFAULT_PANEL_ROOT: Final = ROOT / "artifacts" / "rp2_v3" / "rp2-v3-20260824-remeasure"
DEFAULT_THETA: Final = ROOT / "artifacts" / "rp3" / "b2_index_theta.json"
DEFAULT_POWER_ARTIFACT: Final = ROOT / "artifacts" / "rp2_ext4_power" / "power.json"
DEFAULT_OUTPUT: Final = ROOT / "artifacts" / "rp3" / "sizing.json"

ROLE: Final = "D"
TRAIN_SHARE: Final = 0.6
MODEL_FAMILY: Final = "lightgbm_qlike"
#: The primary is the prospective replication of the one development cell that cleared
#: the sequential budget: delta B2|B1 via the frozen index on rv_30 (+0.00101 in D). The
#: exploratory selection was rv_60 - chosen from the 36-target information sweep - and its
#: measured D effect through the same frozen index is negative, so it is measured and
#: recorded here as the dead end it is, not promoted and not deleted.
PRIMARY_TARGET: Final = "rv_30"
MEASURED_TARGETS: Final = ("rv_30", "rv_60")
#: The exploratory sweep looked at 36 targets before this one was chosen, so the expected
#: out-of-sample effect is the observed one divided by two. Declared, not tuned.
WINNER_CURSE_DIVISOR: Final = 2.0
#: Sizing search cap. MDE decays like 1/sqrt(N), so a target this many sessions cannot
#: reach is a target the program cannot reach on any calendar anyone will live to read.
MAX_SESSIONS: Final = 100_000
#: The virgin window: sessions strictly after the frozen D+V partition end (2026-07-17).
WINDOW_OPENS: Final = "2026-07-18"
#: Nominal accrual rate of the session bank, stated for the reader; the read date itself
#: is computed on the Mon-Fri business-day calendar below, not from this round number.
SESSIONS_PER_MONTH_NOMINAL: Final = 21
CALENDAR_NOTE: Final = (
    "Mon-Fri business days from the window opening, no exchange holiday calendar; "
    "US holidays (~9-10/year) push every date a few sessions later, never earlier."
)
#: Where the frozen secondary power lives and what its 80%-power session count must round
#: to. The citation is pinned to the V-role direction row for the chosen secondary target.
SECONDARY_DETAIL: Final = "y_signed_return_120 via b2_5m_strike_hhi"
SECONDARY_ROLE: Final = "V"
SECONDARY_SESSIONS_FOR_80PCT_ROUNDED: Final = 42

NOT_ACHIEVABLE: Final = "NOT_ACHIEVABLE"


def sha256_file(path: Path) -> str:
    """Content hash of one input parquet, so the artifact names its exact inputs."""

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_sha256(payload: dict[str, object]) -> str:
    """Hash of the canonical JSON serialisation, excluding the self-hash field itself."""

    body = {key: value for key, value in payload.items() if key != "self_sha256"}
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def load_frozen_theta(path: Path) -> dict[str, object]:
    """Read the frozen index and refuse a copy whose self-hash no longer verifies."""

    if not path.is_file():
        raise FileNotFoundError(f"RP3_SIZING_THETA_MISSING:{path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("RP3_SIZING_THETA_MALFORMED")
    if payload.get("self_sha256") != canonical_sha256(payload):
        raise ValueError("RP3_SIZING_THETA_HASH_MISMATCH")
    return payload


def mde_at_sessions(
    long_run_variance: float,
    sessions: int,
    *,
    alpha: float = DEFAULT_ALPHA,
    power: float = DEFAULT_POWER,
) -> float:
    """The smallest mean ``sessions`` sessions of this long-run variance could detect.

    Exactly `minimum_detectable_effect`'s mechanics — a t-based two-sided test at ``alpha``
    with target ``power`` on a Newey-West long-run variance — but parametric in the session
    count instead of reading it off the observed series, which is what a sizing curve is.
    """

    if sessions < 3:
        raise ValueError("RP3_SIZING_TOO_FEW_SESSIONS")
    return minimum_detectable_effect_from_long_run_variance(
        long_run_variance,
        sessions,
        alpha=alpha,
        power=power,
    )


def smallest_sufficient_sessions(long_run_variance: float, target_effect: float) -> int | None:
    """The first N whose MDE is within the target effect, or None if no N under the cap is.

    Linear scan rather than a closed form because the t quantiles move with the degrees of
    freedom; the scan is exact and the cap makes 'unreachable' a checked answer rather than
    a hung loop.
    """

    if target_effect <= 0.0:
        return None
    for sessions in range(3, MAX_SESSIONS + 1):
        if mde_at_sessions(long_run_variance, sessions) <= target_effect:
            return sessions
    return None


def read_date_for(sessions: int) -> str:
    """The calendar date on which the virgin bank holds ``sessions`` business days.

    The window opens on WINDOW_OPENS (a Saturday); the first banked session is the first
    business day on or after it, and the N-th session lands N-1 business days later.
    """

    start = np.datetime64(WINDOW_OPENS, "D")
    date = np.busday_offset(start, sessions - 1, roll="forward")
    return str(date)


def cite_secondary_power(path: Path) -> dict[str, object]:
    """Pin the frozen direction-120 power row and apply the winner's-curse rescale.

    No re-measurement: the row was computed once, from the frozen extension-4 artifact,
    and this program's plan divides its effect by two. Power scales with (effect^2 * N),
    so halving the effect multiplies the required sessions by four: 42 -> 168 nominal.
    """

    if not path.is_file():
        raise FileNotFoundError(f"RP3_SIZING_POWER_ARTIFACT_MISSING:{path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise ValueError("RP3_SIZING_POWER_ARTIFACT_MALFORMED")
    matches = [
        row
        for row in rows
        if isinstance(row, dict)
        and row.get("contrast") == "direction"
        and row.get("detail") == SECONDARY_DETAIL
        and row.get("role") == SECONDARY_ROLE
    ]
    if len(matches) != 1:
        raise ValueError(f"RP3_SIZING_SECONDARY_ROW_NOT_UNIQUE:{len(matches)}")
    row = matches[0]
    sessions_for_80pct = row.get("sessions_for_80pct")
    if not isinstance(sessions_for_80pct, float):
        raise ValueError("RP3_SIZING_SECONDARY_SESSIONS_MISSING")
    rounded = int(round(sessions_for_80pct))
    if rounded != SECONDARY_SESSIONS_FOR_80PCT_ROUNDED:
        raise ValueError(f"RP3_SIZING_SECONDARY_SESSIONS_DRIFTED:{sessions_for_80pct}")
    nominal = 4 * rounded
    return {
        "test": "direction_120",
        "cited_artifact": "artifacts/rp2_ext4_power/power.json",
        "cited_power_sha256": payload.get("power_sha256"),
        "cited_detail": SECONDARY_DETAIL,
        "cited_role": SECONDARY_ROLE,
        "cited_sessions_for_80pct": sessions_for_80pct,
        "cited_observed_t": row.get("observed_t"),
        "cited_caveat": payload.get("caveat"),
        "winner_curse_divisor": WINNER_CURSE_DIVISOR,
        "sessions_multiplier": 4,
        "n_secondary_nominal": nominal,
        "note": (
            "Citation only, not re-measured. Halving the effect quadruples the required "
            "sessions; the cited row is itself an upper bound on power because the target "
            "was found by searching 36 candidates."
        ),
    }


def measure_target(
    panel_root: Path, theta_payload: dict[str, object], target_column: str
) -> dict[str, object]:
    """Measure the D effect of the frozen index on one target and the noise it must beat."""

    paths = {
        "b0_panel": panel_root / "rp2_block4_b0" / "b0_panel.parquet",
        "b1_surface_panel": panel_root / "rp2_block5_surface" / "b1_surface_panel.parquet",
        "b2_flow_panel": panel_root / "rp2_block6_flow" / "b2_flow_panel.parquet",
        "target_panel": panel_root / "rp2_block3_target" / "target_panel.parquet",
    }
    for label, path in paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"RP3_SIZING_INPUT_MISSING:{label}:{path}")

    # The theta artifact names the exact parquets it was fitted on; sizing against any
    # other bytes would measure an effect the frozen index was never derived from.
    recorded = theta_payload["input_parquet_sha256"]
    assert isinstance(recorded, dict)
    hashes = {label: sha256_file(path) for label, path in paths.items()}
    for label, expected in recorded.items():
        if hashes[label] != expected:
            raise ValueError(f"RP3_SIZING_PANEL_MISMATCH:{label}")

    panel = load_merged_panel(
        paths["b0_panel"], paths["b1_surface_panel"], paths["b2_flow_panel"]
    )
    frame = panel.filter(pl.col("role") == ROLE).sort(
        ["session_date", "asset", "origin_minute"]
    )

    # Two evaluation universes, and the difference is a finding, not a nuisance. rv30
    # lives in the merged B0 panel over EVERY common-mask origin - the block-10 universe
    # the budget-clearing cell was measured on, so the rv_30 primary must be measured
    # there or it is a different experiment (measured: on the target-panel grid the same
    # contrast reads -0.000177, because the grid drops the early/late-session origins
    # where the index earns its keep). rv_60 exists only in the target panel, whose grid
    # keeps the origins where every forward window fits; that restriction is inherent to
    # a 60-minute-forward target and is recorded per measurement as evaluation_universe.
    if target_column == "rv_30":
        target_source = frame["rv30"]
        universe = "block10_common_mask"
    else:
        targets = pl.read_parquet(paths["target_panel"])
        for key in (*JOIN_KEYS, target_column):
            if key not in targets.columns:
                raise ValueError(f"RP3_SIZING_TARGET_COLUMN_MISSING:{key}")
        right = targets.select([*JOIN_KEYS, target_column])
        duplicated = right.height - right.select(list(JOIN_KEYS)).unique().height
        if duplicated:
            raise ValueError(f"RP3_SIZING_JOIN_AMBIGUOUS:right_duplicates={duplicated}")
        joined = frame.join(right, on=list(JOIN_KEYS), how="left")
        if joined.height != frame.height:
            raise ValueError(
                f"RP3_SIZING_JOIN_AMBIGUOUS:cardinality={frame.height}->{joined.height}"
            )
        frame = joined
        target_source = frame[target_column]
        universe = "target_panel_grid"

    # Same common mask as the theta fit (finite positive rv30, valid keys, valid
    # availability), then restrict to origins where the forward target exists. The mask
    # digest published below is of exactly the rows the contrast scored.
    rv30 = np.asarray(frame["rv30"].to_numpy(), dtype=np.float64)
    base_keep = common_evaluation_mask(frame, rv30)
    frozen_rows = theta_payload["rows"]
    assert isinstance(frozen_rows, int)
    if int(base_keep.sum()) != frozen_rows:
        raise ValueError("RP3_SIZING_PANEL_DRIFT")
    forward_raw = target_source.cast(pl.Float64).to_numpy()
    forward = np.nan_to_num(np.asarray(forward_raw, dtype=np.float64), nan=-1.0)
    keep = base_keep & np.isfinite(forward) & (forward > 0.0)
    kept_target = np.asarray(forward_raw, dtype=np.float64)[keep]
    frame = frame.filter(pl.Series(keep))
    target = kept_target

    rank = session_rank(frame["session_date"].to_numpy())
    train, test = chronological_split(rank, train_share=TRAIN_SHARE)
    clusters = rank[test]
    digest = mask_sha256(test)

    b01 = [c for mapping in (B0_FEATURES, B1_FEATURES) for c in mapping]
    x01, _, _ = fold_design(frame, b01, train)
    x2, b2_columns, _ = fold_design(frame, list(B2_FEATURES), train, intercept=False)

    # The frozen theta is a coefficient per named design column; a fold whose design
    # resolved to different columns would be silently multiplying premiums by latency
    # coefficients. Exact order match or nothing.
    frozen_columns = theta_payload["b2_design_columns"]
    assert isinstance(frozen_columns, list)
    if list(b2_columns) != frozen_columns:
        raise ValueError("RP3_SIZING_INDEX_COLUMNS_MISMATCH")
    theta_values = theta_payload["theta"]
    assert isinstance(theta_values, list)
    theta = np.asarray([float(value) for value in theta_values], dtype=np.float64)
    train_mean = theta_payload["index_train_mean"]
    train_std = theta_payload["index_train_std"]
    epsilon = theta_payload["standardisation_epsilon"]
    assert isinstance(train_mean, float)
    assert isinstance(train_std, float)
    assert isinstance(epsilon, float)
    index = (x2 @ theta - train_mean) / (train_std + epsilon)

    fitter = LADDER[MODEL_FAMILY]
    base_forecast = fitter(x01, target, train)
    expanded_forecast = fitter(np.column_stack([x01, index]), target, train)
    base_loss = qlike_losses(target[test], base_forecast[test])
    expanded_loss = qlike_losses(target[test], expanded_forecast[test])
    contrast = session_contrast(
        base_loss,
        expanded_loss,
        clusters,
        model_family=MODEL_FAMILY,
        base_information_set="B0+B1",
        expanded_information_set="B0+B1+b2_index",
        common_mask_sha256=digest,
        seed=650,
    )

    # The noise term the sizing curve is built from: the long-run variance of the
    # per-session QLIKE-difference series, with the same Bartlett lags the published MDE
    # uses. Measured on the test sessions because those are draws of the quantity the
    # sealed read will average.
    session_values, _ = aggregate_by_session(base_loss - expanded_loss, clusters)
    long_run_variance = newey_west_variance(session_values, lags=SESSION_BLOCK_LENGTH)

    return {
        "contrast": "delta_b2_given_b1_via_frozen_index",
        "target": target_column,
        "evaluation_universe": universe,
        "model_family": MODEL_FAMILY,
        "base_information_set": "B0+B1",
        "expanded_information_set": "B0+B1+b2_index",
        "train_share": TRAIN_SHARE,
        "rows_evaluated": int(target.size),
        "train_rows": int(train.sum()),
        "test_rows": int(test.sum()),
        "test_sessions": int(np.unique(clusters).size),
        "observed": contrast.as_record(),
        "long_run_variance": float(long_run_variance),
        "long_run_lags": SESSION_BLOCK_LENGTH,
        "input_parquet_sha256": hashes,
    }


def build_sizing(panel_root: Path, theta_path: Path, power_path: Path) -> dict[str, object]:
    """Assemble the full sizing artifact: measured effect, curve, N_PRIMARY, read date."""

    theta_payload = load_frozen_theta(theta_path)

    # Every listed target is measured and recorded; the primary is a named choice among
    # them, not the survivor of a silent race. The winner's curse discount is the declared
    # plan, applied before anyone sees the virgin window: the target the sealed read must
    # detect is HALF the effect D shows. A non-positive D effect leaves nothing to halve,
    # and the measurement says so instead of being dropped.
    measurements: dict[str, dict[str, object]] = {}
    for column in MEASURED_TARGETS:
        measured = measure_target(panel_root, theta_payload, column)
        observed = measured["observed"]
        assert isinstance(observed, dict)
        effect = observed["estimate"]
        long_run_variance = measured["long_run_variance"]
        assert isinstance(effect, float)
        assert isinstance(long_run_variance, float)
        target_effect = max(effect / WINNER_CURSE_DIVISOR, 0.0)
        n_sessions = smallest_sufficient_sessions(long_run_variance, target_effect)
        grid = sorted({*range(5, 401, 5), *([n_sessions] if n_sessions is not None else [])})
        measured["target_effect"] = target_effect
        measured["mde_curve"] = [
            {"sessions": sessions, "mde": mde_at_sessions(long_run_variance, sessions)}
            for sessions in grid
        ]
        measured["n_sessions"] = n_sessions if n_sessions is not None else NOT_ACHIEVABLE
        measured["read_date"] = (
            read_date_for(n_sessions) if n_sessions is not None else NOT_ACHIEVABLE
        )
        measurements[column] = measured

    primary = measurements[PRIMARY_TARGET]
    n_primary_value = primary["n_sessions"]

    run_id = panel_root.name
    run_identity = panel_root / "run_identity.json"
    if run_identity.is_file():
        recorded = json.loads(run_identity.read_text(encoding="utf-8")).get("run_id")
        if isinstance(recorded, str) and recorded:
            run_id = recorded

    payload: dict[str, object] = {
        "schema": "rp3_sizing/2",
        "run_id": run_id,
        "role": ROLE,
        "theta_artifact": "artifacts/rp3/b2_index_theta.json",
        "theta_self_sha256": theta_payload["self_sha256"],
        "measurements": measurements,
        "primary_target": PRIMARY_TARGET,
        "primary_rationale": (
            "rv_60 was the exploratory selection (36-target information sweep) and its "
            "measured D effect through the frozen index is negative - the winner's curse "
            "caught before sealing, recorded under measurements.rv_60. The primary is the "
            "prospective replication of the one development cell that cleared the "
            "sequential budget: delta B2|B1 via the same frozen index on rv_30."
        ),
        "winner_curse_divisor": WINNER_CURSE_DIVISOR,
        "alpha": DEFAULT_ALPHA,
        "power": DEFAULT_POWER,
        "n_primary": n_primary_value,
        "session_bank": {
            "window_opens": WINDOW_OPENS,
            "sessions_per_month_nominal": SESSIONS_PER_MONTH_NOMINAL,
            "calendar": CALENDAR_NOTE,
            "read_date": primary["read_date"],
        },
        "secondary": cite_secondary_power(power_path),
    }
    payload["self_sha256"] = canonical_sha256(payload)
    return payload


def print_summary(payload: dict[str, object]) -> None:
    """The table a reader wants before opening the JSON."""

    measurements = payload["measurements"]
    assert isinstance(measurements, dict)
    bank = payload["session_bank"]
    assert isinstance(bank, dict)
    for column, measured in measurements.items():
        assert isinstance(measured, dict)
        observed = measured["observed"]
        assert isinstance(observed, dict)
        marker = " (PRIMARY)" if column == payload["primary_target"] else ""
        print(f"RP3 sizing - {column}{marker} via frozen index, lightgbm_qlike, role D")
        print(
            f"  rows={measured['rows_evaluated']} train={measured['train_rows']} "
            f"test={measured['test_rows']} test_sessions={measured['test_sessions']}"
        )
        print(
            f"  effect_D={observed['estimate']:+.6f} "
            f"ci=[{observed['ci_low']:+.6f},{observed['ci_high']:+.6f}] "
            f"p_wild={observed['wild_cluster_p_value']:.4f} mde_observed={observed['mde']:.6f}"
        )
        print(
            f"  long_run_variance={measured['long_run_variance']:.3e} "
            f"target_effect(effect/2)={measured['target_effect']:+.6f} "
            f"N={measured['n_sessions']}  read_date={measured['read_date']}"
        )
    print(f"  N_PRIMARY={payload['n_primary']}  READ_DATE={bank['read_date']}")
    secondary = payload["secondary"]
    assert isinstance(secondary, dict)
    print(
        f"  secondary (cited): sessions_for_80pct="
        f"{secondary['cited_sessions_for_80pct']:.1f} -> x4 = "
        f"{secondary['n_secondary_nominal']} nominal sessions"
    )
    print(f"  self_sha256={payload['self_sha256']}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Size the RP3 program: N_PRIMARY and the estimated read date."
    )
    parser.add_argument(
        "--panel-root",
        type=Path,
        default=DEFAULT_PANEL_ROOT,
        help="Run directory holding rp2_block{3,4,5,6} panels of the remeasured run.",
    )
    parser.add_argument(
        "--theta",
        type=Path,
        default=DEFAULT_THETA,
        help="Frozen B2 index artifact (never refitted here).",
    )
    parser.add_argument(
        "--power-artifact",
        type=Path,
        default=DEFAULT_POWER_ARTIFACT,
        help="Frozen extension-4 power artifact cited for the secondary test.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Where the sizing artifact is written.",
    )
    arguments = parser.parse_args()

    payload = build_sizing(arguments.panel_root, arguments.theta, arguments.power_artifact)
    output: Path = arguments.output
    output.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    output.write_bytes(text.encode("utf-8"))
    print(f"written: {output}")
    print_summary(payload)


if __name__ == "__main__":
    main()
