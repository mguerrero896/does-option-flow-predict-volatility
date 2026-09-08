"""Descriptive audit of immutable RP4 forecasts/coefficients; no estimators or inference.

All new files are confined to artifacts/rp4_closeout_audit. Input hashes and
session receipts are checked before extraction. Dropped coefficients are encoded
as zero contribution, not as estimated zeros or evidence of no effect.
"""

from __future__ import annotations

import collections
import datetime as dt
import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any

for _variable in (
    "OPENBLAS_NUM_THREADS",
    "OMP_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "POLARS_MAX_THREADS",
):
    os.environ[_variable] = "2"

import numpy as np  # noqa: E402 - cap thread pools before importing numerical libraries.
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "artifacts/rp4_closeout_audit"
FAMILIES = ("log_ridge_harq", "lightgbm_qlike")
SETS = ("B0", "B1", "B2")
SPECS = {
    30: (
        "artifacts/rp4_v3_a1_empty_window/specification.json",
        "930f3ddb6ef6284f1129dda26ed705699a666ade005c6ad363cb67864794e6f5",
    ),
    15: (
        "artifacts/rp4_v4_a1/specification.json",
        "0a45b0a608110e2ca0dcf38accc2a0c2521ebbe9d223eb002e36ec51f78afd04",
    ),
    5: (
        "artifacts/rp4_v4_a1/specification.json",
        "0a45b0a608110e2ca0dcf38accc2a0c2521ebbe9d223eb002e36ec51f78afd04",
    ),
}
PINS: dict[str, str] = {}
OUTPUTS: dict[str, str] = {}


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1048576), b""):
            h.update(block)
    return h.hexdigest()


def load(path: Path, expected: str | None = None) -> Any:
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if expected is not None and digest != expected:
        raise ValueError(f"INPUT_HASH_MISMATCH:{path}")
    previous = PINS.setdefault(str(path), digest)
    if previous != digest:
        raise ValueError(f"INPUT_CHANGED_DURING_AUDIT:{path}")
    return json.loads(raw)


def new_file(name: str, raw: bytes) -> None:
    path = OUTPUT / name
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError(f"OUTPUT_EXISTS_DIFFERENT:{path}")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(raw)
    OUTPUTS[name] = hashlib.sha256(raw).hexdigest()


def csv(name: str, rows: list[dict[str, Any]] | pd.DataFrame) -> None:
    frame = rows if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows)
    new_file(name, frame.to_csv(index=False, lineterminator="\n").encode())


def coefficient_rows(fit: dict[str, Any], spec: dict[str, Any]) -> list[dict[str, Any]]:
    """Map original numerical design indices including five asset effects/presences."""
    features = list(spec["feature_sets"]["B2"])
    names = features + ["asset_effect:" + asset for asset in spec["assets"][1:]]
    pre = fit["preprocessing"]["refit"]
    assert pre["input_columns"] == len(names)
    active = dict(zip(pre["active_columns"], fit["coefficients"], strict=True))
    removed = {row["column"]: row["reason"] for row in pre["removed_columns"]}
    encoded = pre["encoded_columns_before_rank_filter"]
    centers = dict(zip(encoded, pre["centers"], strict=True))
    scales = dict(zip(encoded, pre["scales_population_sd"], strict=True))
    labels = ["intercept"] + [f"feature:{i}" for i in range(len(names))]
    labels += [f"presence:{i}" for i in pre["presence_indices"]]
    assert set(labels) == set(active) | set(removed)
    assert not set(active) & set(removed)
    result = []
    for label in labels:
        if label == "intercept":
            name, kind, transform, index = "intercept", "intercept", "identity", None
        else:
            kind, value = label.split(":")
            index = int(value)
            name = names[index]
            transform = spec["feature_transforms"].get(name, "raw")
            if name.startswith("rp4_gamma_imb_"):
                transform = "log1p_count" if name.endswith("signed_trades") else "signed_log1p"
            if kind == "presence":
                name, transform = "presence:" + name, "finite_presence_binary"
        coefficient = float(active.get(label, 0.0))
        result.append(
            {
                "design_label": label,
                "column": name,
                "kind": kind,
                "pointwise_transform": transform,
                "coefficient_standardized": coefficient,
                "coefficient_absolute": abs(coefficient),
                "positive": coefficient > 0,
                "negative": coefficient < 0,
                "zero": coefficient == 0,
                "active": label in active,
                "removed_reason": removed.get(label, ""),
                "zero_semantics": "fitted_coefficient"
                if label in active
                else "dropped_zero_contribution_not_estimated",
                "training_median": pre["medians"][index]
                if index is not None and kind != "presence"
                else None,
                "training_center": centers.get(label, 0.0 if label == "intercept" else None),
                "training_sd_before_winsor": scales.get(
                    label, 1.0 if label == "intercept" else None
                ),
                "finite_training_count": pre["finite_training_counts"][index]
                if index is not None
                else pre["training_rows"],
            }
        )
    return result


def paired_profile(frame: pd.DataFrame, family: str, base: str, rich: str) -> dict[str, Any]:
    """Report both origin pooling and original equal-session/equal-asset weighting."""
    if frame.empty:
        return {
            "N_origins": 0,
            "N_sessions": 0,
            "N_asset_sessions": 0,
            "base_qlike_pooled": None,
            "rich_qlike_pooled": None,
            "delta_pooled": None,
            "delta_equal_session_asset": None,
        }
    b, r = f"loss__{family}__{base}", f"loss__{family}__{rich}"
    cells = frame.groupby(["session_date", "asset"])[[b, r]].mean()
    sessions = cells.groupby("session_date").mean()
    mean = sessions.mean()
    delta = sessions[b] - sessions[r]
    return {
        "N_origins": len(frame),
        "N_sessions": frame.session_date.nunique(),
        "N_asset_sessions": len(cells),
        "first_session": frame.session_date.min(),
        "last_session": frame.session_date.max(),
        "base_qlike_pooled": frame[b].mean(),
        "rich_qlike_pooled": frame[r].mean(),
        "delta_pooled": (frame[b] - frame[r]).mean(),
        "percent_reduction_pooled": 100 * (frame[b] - frame[r]).mean() / frame[b].mean(),
        "base_qlike_equal_session_asset": mean[b],
        "rich_qlike_equal_session_asset": mean[r],
        "delta_equal_session_asset": mean[b] - mean[r],
        "percent_reduction_equal_session_asset": 100 * (mean[b] - mean[r]) / mean[b],
        "N_positive_session_deltas": int((delta > 0).sum()),
        "N_negative_session_deltas": int((delta < 0).sum()),
        "N_zero_session_deltas": int((delta == 0).sum()),
        "minimum_session_delta": delta.min(),
        "median_session_delta": delta.median(),
        "new_p_value": None,
        "inference_role": "POSTHOC_DESCRIPTIVE_ONLY",
    }


def window_paths(horizon: int, window: str) -> tuple[Path, Path]:
    stage = "b2" if window == "primary" else "b3"
    if horizon == 30:
        return ROOT / f"artifacts/rp4_v3_{stage}", Path("private-input/e820144cbf4f5cf80cbd")
    return ROOT / f"artifacts/rp4_v4_{stage}_rv{horizon}", Path(
        "private-input/f82224c56f4c7faf8db4"
    )


def profile_groups(frame: pd.DataFrame, metadata: pd.DataFrame) -> list[tuple[str, str, pd.Series]]:
    m = frame.origin_minute
    tariff = frame.session_date.between("2025-04-07", "2025-04-10")
    groups = [("all", "all", pd.Series(True, index=frame.index))]
    for value, mask in {
        "first_market_hour_origin_lt60": m < 60,
        "middle_registered_origin60_299": (m >= 60) & (m < 300),
        "last_registered_block_origin_ge300": m >= 300,
        "last_market_hour_origin_ge330": m >= 330,
        "first_observed_hour_origin35_94": (m >= 35) & (m < 95),
    }.items():
        groups.append(("intraday", value, mask))
    for value in sorted(frame.session_date.str[:7].unique()):
        groups.append(("month", value, frame.session_date.str[:7] == value))
    # Size terciles are descriptive partitions, never used for fitting/tuning.
    low, high = metadata.train_rows.quantile([1 / 3, 2 / 3], interpolation="linear")
    size = frame.session_date.map(metadata.set_index("session")["train_rows"])
    for value, mask in {
        "T1": size <= low,
        "T2": (size > low) & (size <= high),
        "T3": size > high,
    }.items():
        groups.append(("training_size_tercile", value, mask))
    groups.append(
        ("calendar_early", "2024-10-28_to_2025-02-28", frame.session_date <= "2025-02-28")
    )
    for value, mask in {
        "four_days_all": tariff,
        "four_days_first_market_hour_origin_lt60": tariff & (m < 60),
        "four_days_first_observed_hour_origin35_94": tariff & (m >= 35) & (m < 95),
        "outside_four_days_first_market_hour_origin_lt60": ~tariff & (m < 60),
        "outside_four_days_remainder_origin_ge60": ~tariff & (m >= 60),
        "outside_four_days_first_observed_hour_origin35_94": ~tariff & (m >= 35) & (m < 95),
        "outside_four_days_remainder_origin_ge95": ~tariff & (m >= 95),
    }.items():
        groups.append(("tariff_calendar", value, mask))
    for field in ["window_empty_5m", "window_empty_30m", "third_friday"]:
        for state in [True, False, None]:
            mask = frame[field].isna() if state is None else frame[field].eq(state)
            groups.append(
                (field, "unknown" if state is None else "inside" if state else "outside", mask)
            )
    return groups


def run() -> dict[str, Any]:
    started = time.perf_counter()
    coefficients, diagnostics, profiles, equality, sessions_meta = [], [], [], [], []
    headline, parity = [], []
    for horizon in [30, 15, 5]:
        spec_path, spec_sha = SPECS[horizon]
        spec = load(ROOT / spec_path, spec_sha)
        for window in ["primary", "confirmation"]:
            public, private = window_paths(horizon, window)
            receipt = load(public / "receipt.json")
            assert receipt["status"] == "COMPLETE" and receipt["exit_code"] == 0
            for name, digest in receipt["artifacts_sha256"].items():
                path = Path(name)
                assert sha(path) == digest
                PINS[str(path)] = digest
            summary = load(public / "summary.json")
            source_csv = pd.read_csv(public / "session_losses.csv").set_index("session_date")
            frames, metadata = [], []
            for filename, digest in sorted(summary["completed_session_sha256"].items()):
                rec = load(private / "sessions" / filename, digest)
                stamp = load(private / "session_receipts" / filename)
                assert stamp["sha256"] == digest and stamp["binding"] == rec["binding"]
                date = rec["session"]
                target = np.asarray(rec["target"], dtype=float)
                assert np.isfinite(target).all() and (target > 0).all()
                frame = pd.DataFrame(rec["keys"])
                assert len(frame) == len(target) and not frame.duplicated().any()
                frame["target"] = target
                for field, values in rec["secondary"].items():
                    frame[field] = values
                fit0 = rec["fits"]["mean__log_ridge_harq__B0"]
                meta = {
                    "horizon_minutes": horizon,
                    "window": window,
                    "session": date,
                    "train_sessions": rec["train_sessions"],
                    "train_rows": fit0["train_rows"],
                    "N_origins": len(frame),
                    "session_sha256": digest,
                }
                metadata.append(meta)
                for family in FAMILIES:
                    for info in SETS:
                        predictions = np.asarray(rec["forecasts"][family][info], dtype=float)
                        assert (
                            predictions.shape == target.shape
                            and np.isfinite(predictions).all()
                            and (predictions > 0).all()
                        )
                        frame[f"forecast__{family}__{info}"] = predictions
                        ratio = target / np.maximum(predictions, 1e-12)
                        losses = ratio - np.log(ratio) - 1.0
                        name = f"loss__{family}__{info}"
                        frame[name] = losses
                        cell_mean = frame.groupby("asset")[name].mean().mean()
                        error = abs(cell_mean - float(source_csv.loc[date, name]))
                        assert error < 1e-12, (horizon, date, name, error)
                        parity.append(error)
                        if family == "log_ridge_harq":
                            fit = rec["fits"][f"mean__{family}__{info}"]
                            pre = fit["preprocessing"]["refit"]
                            count = collections.Counter(x["reason"] for x in pre["removed_columns"])
                            diagnostics.append(
                                {
                                    **meta,
                                    "information_set": info,
                                    "lambda": fit["selected"]["lambda"],
                                    "lambda_over_train_rows": fit["selected"]["lambda"]
                                    / fit["train_rows"],
                                    "input_columns": pre["input_columns"],
                                    "optional_presence_columns": len(pre["presence_indices"]),
                                    "active_including_intercept": len(pre["active_columns"]),
                                    "removed_columns": len(pre["removed_columns"]),
                                    "all_missing": count["all_missing_training"],
                                    "zero_variance": count["zero_variance_training"],
                                    "collinear_qr": count["collinear_qr"],
                                    "count_low": fit["count_low"],
                                    "count_high": fit["count_high"],
                                    "lower_bound": fit["bounds"]["refit"]["lower"],
                                    "upper_bound": fit["bounds"]["refit"]["upper"],
                                    "log_smearing": fit["log_smearing"],
                                    "objective": fit["objective"],
                                }
                            )
                            if info == "B2":
                                for row in coefficient_rows(fit, spec):
                                    coefficients.append(
                                        {**meta, "lambda": fit["selected"]["lambda"], **row}
                                    )
                    for asset, group in frame.groupby("asset"):
                        pred = [group[f"forecast__{family}__{info}"].to_numpy() for info in SETS]
                        equality.append(
                            {
                                "horizon_minutes": horizon,
                                "window": window,
                                "session": date,
                                "asset": asset,
                                "family": family,
                                "N_origins": len(group),
                                **{
                                    f"constant_{info}": bool(np.ptp(values) == 0)
                                    for info, values in zip(SETS, pred, strict=True)
                                },
                                "B0_B1_identical": bool(np.array_equal(pred[0], pred[1])),
                                "B1_B2_identical": bool(np.array_equal(pred[1], pred[2])),
                                "B0_B2_identical": bool(np.array_equal(pred[0], pred[2])),
                                "B0_B1_max_absolute_difference": float(
                                    np.max(np.abs(pred[0] - pred[1]))
                                ),
                                "B1_B2_max_absolute_difference": float(
                                    np.max(np.abs(pred[1] - pred[2]))
                                ),
                            }
                        )
                frames.append(frame)
            whole = pd.concat(frames, ignore_index=True)
            md = pd.DataFrame(metadata)
            assert len(whole) == summary["N_origins"] and len(md) == summary["N_sessions"]
            sessions_meta.extend(metadata)
            for kind, label, mask in profile_groups(whole, md):
                sub = whole.loc[mask]
                for family in FAMILIES:
                    for base, rich in [("B0", "B1"), ("B1", "B2")]:
                        profiles.append(
                            {
                                "horizon_minutes": horizon,
                                "window": window,
                                "profile": kind,
                                "stratum": label,
                                "family": family,
                                "contrast": f"{rich}_over_{base}",
                                **paired_profile(sub, family, base, rich),
                            }
                        )
            tariff = whole.loc[
                whole.session_date.between("2025-04-07", "2025-04-10") & (whole.origin_minute < 95)
            ].copy()
            tariff["horizon_minutes"] = horizon
            tariff["first_market_hour_origin_lt60"] = tariff.origin_minute < 60
            if len(tariff):
                keep = [
                    "horizon_minutes",
                    "asset",
                    "session_date",
                    "origin_minute",
                    "first_market_hour_origin_lt60",
                ]
                keep += [c for c in tariff if c.startswith("loss__")]
                csv(f"tariff_origins_rv{horizon}_{window}.csv", tariff[keep])
            headline.append(
                {
                    "horizon_minutes": horizon,
                    "window": window,
                    "N_sessions": len(md),
                    "N_origins": len(whole),
                }
            )
            print(
                f"DESCRIPTIVE_CLOSED_WINDOW:RV{horizon}:{window}:{len(md)}:{len(whole)}", flush=True
            )
    coef = pd.DataFrame(coefficients)
    csv("b2_standardized_coefficients_by_session.csv", coef)
    aggregates = (
        coef.groupby(
            ["horizon_minutes", "window", "column", "kind", "pointwise_transform"], sort=True
        )
        .agg(
            N_sessions=("coefficient_standardized", "size"),
            mean=("coefficient_standardized", "mean"),
            median=("coefficient_standardized", "median"),
            absolute_mean=("coefficient_absolute", "mean"),
            minimum=("coefficient_standardized", "min"),
            maximum=("coefficient_standardized", "max"),
            positive_count=("positive", "sum"),
            negative_count=("negative", "sum"),
            zero_count=("zero", "sum"),
            active_sessions=("active", "sum"),
        )
        .reset_index()
    )
    aggregates["positive_share"] = aggregates.positive_count / aggregates.N_sessions
    aggregates["negative_share"] = aggregates.negative_count / aggregates.N_sessions
    csv("b2_coefficient_summary.csv", aggregates)
    csv("ridge_diagnostics_by_session.csv", diagnostics)
    diag = pd.DataFrame(diagnostics)
    csv(
        "ridge_lambda_counts.csv",
        diag.groupby(["horizon_minutes", "window", "information_set", "lambda"])
        .size()
        .rename("N_sessions")
        .reset_index(),
    )
    csv(
        "ridge_bounds_pruning_summary.csv",
        diag.groupby(["horizon_minutes", "window", "information_set"])
        .agg(
            N_sessions=("session", "size"),
            count_low=("count_low", "sum"),
            count_high=("count_high", "sum"),
            removed_min=("removed_columns", "min"),
            removed_median=("removed_columns", "median"),
            removed_max=("removed_columns", "max"),
            active_min=("active_including_intercept", "min"),
            active_median=("active_including_intercept", "median"),
            active_max=("active_including_intercept", "max"),
            train_rows_min=("train_rows", "min"),
            train_rows_max=("train_rows", "max"),
        )
        .reset_index(),
    )
    csv("descriptive_profiles.csv", profiles)
    csv("sessions_training_sizes.csv", sessions_meta)
    csv("forecast_equality_by_asset_session.csv", equality)
    eq = pd.DataFrame(equality)
    flags = [c for c in eq if c.startswith("constant_") or c.endswith("_identical")]
    eqsum = eq.groupby(["horizon_minutes", "window"])[flags].sum()
    eqsum["N_asset_session_family_units"] = eq.groupby(["horizon_minutes", "window"]).size()
    csv("forecast_equality_summary.csv", eqsum.reset_index())
    conclusions = {
        "status": "PASS_DESCRIPTIVE_EXTRACTION",
        "windows": headline,
        "coefficient_rows": len(coef),
        "coefficient_summary_rows": len(aggregates),
        "forecast_asset_session_family_units": len(equality),
        "stored_session_qlike_comparisons": len(parity),
        "max_session_qlike_absolute_difference": max(parity),
        "model_fits": 0,
        "new_p_values": 0,
        "bootstrap_runs": 0,
        "raw_tape_reads": 0,
        "threads_max": 2,
        "elapsed_seconds": time.perf_counter() - started,
        "coefficient_semantics": (
            "Coefficient on train-only centered/population-SD-scaled, clipped [-5,5] "
            "pointwise transformed input. No restandardization after clipping. Log-target "
            "mean fit before Duan smear and nonlinear output bounds. Dropped column 0 "
            "means no contribution in that fitted representation, not estimated null effect."
        ),
        "presence_semantics": (
            "presence:<exact raw column> indicates finiteness before train-only median "
            "imputation; it is not the raw column slope."
        ),
        "intraday_semantics": (
            "First market hour origin<60; first observed hour35<=origin<95. Registered "
            "last_hour is origin>=300, not the final market hour origin>=330."
        ),
        "inference_limit": (
            "Post-hoc descriptive strata and associations; no ablations, causal "
            "interpretation, new p-values or rescue of the registered primary decision."
        ),
    }
    new_file("findings.json", (json.dumps(conclusions, indent=2) + "\n").encode())
    manifest = {
        "status": "PASS",
        "source_sha256": PINS,
        "artifacts_sha256": OUTPUTS,
        "producer_path": str(Path(__file__).relative_to(ROOT)),
        "producer_sha256": sha(Path(__file__)),
        "created_at_utc": dt.datetime.now(dt.UTC).isoformat(),
        "model_fits": 0,
        "new_p_values": 0,
        "bootstrap_runs": 0,
        "RESEARCH_ONLY": True,
        "capital_go": False,
    }
    new_file("manifest.json", (json.dumps(manifest, indent=2) + "\n").encode())
    return conclusions


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
