"""Reproduce the closed-primary MZ arithmetic audit; no model calls or file writes.

This preserves the previous inline verification, with input/custody checks.
The only empirical inputs are the immutable primary session records and closure.
"""

import hashlib
import json
import math
from pathlib import Path

import numpy as np

COMMAND = "uv run --offline --frozen --no-sync python -B artifacts/rp4_v3_b4/audit_mz_identity.py"
repo = Path(__file__).resolve().parents[2]
private = Path("private-input/8d3d30ddb3633ff9c2d1")
summary_path = repo / "artifacts/rp4_v3_b2/summary.json"
receipt_path = repo / "artifacts/rp4_v3_b2/receipt.json"


def digest(path):
    with Path(path).open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


receipt_sha_before = digest(receipt_path)
receipt = json.loads(receipt_path.read_bytes())
assert (receipt["status"], receipt["exit_code"], receipt["window"], receipt["stage"]) == (
    "COMPLETE",
    0,
    "primary",
    "B2",
)
assert receipt.get("execution_failure") is None
assert receipt["commands"] and all(
    r["exit_code"] == 0 and r["command"] for r in receipt["commands"]
)
expected_artifacts = {
    summary_path.resolve(),
    (repo / "artifacts/rp4_v3_b2/session_losses.csv").resolve(),
    (private / "fit_diagnostics.json").resolve(),
}
assert {Path(p).resolve() for p in receipt["artifacts_sha256"]} == expected_artifacts
for path, sha in receipt["artifacts_sha256"].items():
    assert digest(path) == sha, (path, "closure pin")
summary = json.loads(summary_path.read_bytes())
source_pins = {
    p.relative_to(repo).as_posix(): digest(p)
    for p in (
        summary_path,
        receipt_path,
        repo / "artifacts/rp4_v3_code/models.py",
        repo / "artifacts/rp4_v3_code/evaluate_v3.py",
        repo / "artifacts/rp4_v3_code/aggregate_v3.py",
        repo / "artifacts/rp4_v3_a1_empty_window/specification.json",
        Path(__file__).resolve(),
    )
}
for rel, sha in receipt["evaluation_code_sha256"].items():
    assert (repo / rel).resolve().is_relative_to(repo)
    assert digest(repo / rel) == sha, rel
names = ("B0", "B1", "B2")
stats = {
    name: dict(
        N_origins=0,
        N_sessions=0,
        floor_hits=0,
        strictly_negative_affine=0,
        exact_zero_affine=0,
        positive_at_or_below_floor=0,
        nonfinite_origin_fallbacks=0,
        training_identity_fallbacks=0,
        coefficient_negative_intercept_sessions=0,
        coefficient_negative_slope_sessions=0,
        formula_stored_max_abs_difference=0.0,
        floor_counter_disagreements=0,
        scale_relative_error_max=0.0,
        closed_form_intercept_abs_error_max=0.0,
        closed_form_slope_abs_error_max=0.0,
        validation_init_score_parity_abs_difference_max=0.0,
    )
    for name in names
}
session_rows = {name: [] for name in names}
examples = {name: None for name in names}
session_pins = {}
for path in sorted((private / "sessions").glob("*.json")):
    data = path.read_bytes()
    sha = hashlib.sha256(data).hexdigest()
    assert sha == summary["completed_session_sha256"][path.name], path
    session_pins[path.name] = sha
    record = json.loads(data)
    assert record["binding"]["window"] == "primary"
    assert record["binding"]["release_sha256"] == receipt["release_sha256"]
    assert record["binding"]["code_sha256"] == receipt["evaluation_code_sha256"]
    assert path.stem == record["session"]
    target = np.asarray(record["target"], dtype=float)
    assets = np.asarray([r["asset"] for r in record["keys"]])
    assert len(
        set((k["asset"], k["session_date"], k["origin_minute"]) for k in record["keys"])
    ) == len(target)
    assert np.isfinite(target).all() and (target > 0).all()
    asset_names = np.unique(assets)

    def equal_asset_mean(values, assets=assets, asset_names=asset_names):
        return float(np.mean([np.mean(values[assets == asset]) for asset in asset_names]))

    for name in names:
        fit = record["fits"]["mean__lightgbm_qlike__" + name]
        c = fit["mz_secondary"]["calibration"]
        s = stats[name]
        forecast = np.asarray(record["forecasts"]["lightgbm_qlike"][name], dtype=float)
        saved = np.asarray(record["mz_forecasts"][name], dtype=float)
        assert forecast.shape == saved.shape == target.shape
        assert np.isfinite(forecast).all() and (forecast > 0).all()
        a = c["applied_coefficients"]["intercept"]
        b = c["applied_coefficients"]["slope"]
        assert math.isfinite(a) and math.isfinite(b)
        affine = a + b * forecast
        nonfinite = ~np.isfinite(affine)
        applied = np.where(nonfinite, forecast, affine)
        floor = 1e-12
        assert c["floor"] == floor
        expected = np.maximum(applied, floor)
        maximum = float(np.max(np.abs(expected - saved)))
        s["formula_stored_max_abs_difference"] = max(
            s["formula_stored_max_abs_difference"], maximum
        )
        assert np.array_equal(expected, saved), (
            record["session"],
            name,
            "formula mismatch",
            maximum,
        )
        hit = applied <= floor
        hits = int(hit.sum())
        assert hits == c["count_floor"]
        assert len(target) == c["prediction_rows"]
        assert int(nonfinite.sum()) == c["origin_identity_fallback_count"]
        s["N_origins"] += len(target)
        s["N_sessions"] += 1
        s["floor_hits"] += hits
        s["strictly_negative_affine"] += int((np.isfinite(affine) & (affine < 0)).sum())
        s["exact_zero_affine"] += int((affine == 0).sum())
        s["positive_at_or_below_floor"] += int(((affine > 0) & (affine <= floor)).sum())
        s["nonfinite_origin_fallbacks"] += int(nonfinite.sum())
        s["training_identity_fallbacks"] += int(c["training_identity_fallback"])
        s["coefficient_negative_intercept_sessions"] += int(a < 0)
        s["coefficient_negative_slope_sessions"] += int(b < 0)
        dates = c["calibration_sessions"]
        assert len(dates) == 10 and len(set(dates)) == 10 and max(dates) < record["session"]
        assert c["inner_fit_last_session"] < min(dates)
        assert c["N_sessions"] == c["N_valid_pairs"] == 10
        observed = np.asarray(c["session_target_means"], dtype=float)
        predicted = np.asarray(c["session_forecast_means"], dtype=float)
        scale = float(observed.mean())
        scale_error = abs(scale - c["target_scale"]) / scale
        s["scale_relative_error_max"] = max(s["scale_relative_error_max"], scale_error)
        centered = predicted - predicted.mean()
        slope_check = float(centered @ (observed - observed.mean()) / (centered @ centered))
        intercept_check = float(observed.mean() - slope_check * predicted.mean())
        if not c["training_identity_fallback"]:
            s["closed_form_intercept_abs_error_max"] = max(
                s["closed_form_intercept_abs_error_max"], abs(intercept_check - a)
            )
            s["closed_form_slope_abs_error_max"] = max(
                s["closed_form_slope_abs_error_max"], abs(slope_check - b)
            )
            assert math.isclose(a, intercept_check, rel_tol=1e-9, abs_tol=1e-14)
            assert math.isclose(b, slope_check, rel_tol=1e-9, abs_tol=1e-12)
            assert c["applied_coefficients"] == c["attempted_coefficients"]
        for candidate in fit["candidates"]:
            s["validation_init_score_parity_abs_difference_max"] = max(
                s["validation_init_score_parity_abs_difference_max"],
                candidate["init_score_prediction_parity_abs_difference"],
            )
        ratio = target / saved
        losses = ratio - np.log(ratio) - 1.0
        raw_ratio = target / forecast
        raw_losses = raw_ratio - np.log(raw_ratio) - 1.0
        row = dict(
            session=record["session"],
            N_origins=len(target),
            floor_hits=hits,
            raw_qlike=equal_asset_mean(raw_losses),
            recalibrated_qlike=equal_asset_mean(losses),
            floor_qlike_contribution=equal_asset_mean(np.where(hit, losses, 0.0)),
            minimum_affine=float(affine.min()),
            intercept=a,
            slope=b,
        )
        session_rows[name].append(row)
        if hits:
            ix = int(np.argmax(np.where(hit, losses, -np.inf)))
            example = dict(
                session=record["session"],
                **record["keys"][ix],
                information_set=name,
                intercept=a,
                slope=b,
                raw_forecast=float(forecast[ix]),
                affine_before_floor=float(affine[ix]),
                stored_mz_forecast=float(saved[ix]),
                actual_rv30=float(target[ix]),
                ratio=float(ratio[ix]),
                origin_qlike=float(losses[ix]),
                session_qlike=row["recalibrated_qlike"],
                calibration_forecast_mean_min=float(predicted.min()),
                calibration_forecast_mean_max=float(predicted.max()),
                calibration_target_mean_min=float(observed.min()),
                calibration_target_mean_max=float(observed.max()),
                calibration_sessions=dates,
                inner_fit_last_session=c["inner_fit_last_session"],
                negative_crossing_forecast=-a / b if b else None,
            )
            if examples[name] is None or example["origin_qlike"] > examples[name]["origin_qlike"]:
                examples[name] = example
assert len(session_pins) == summary["N_sessions"] == 419
out = {}
for name in names:
    s = stats[name]
    rows = session_rows[name]
    recorded = next(
        r for r in summary["mz_secondary"]["model_losses"] if r["information_set"] == name
    )
    calculated = float(np.mean([r["recalibrated_qlike"] for r in rows]))
    raw = float(np.mean([r["raw_qlike"] for r in rows]))
    contribution = float(np.mean([r["floor_qlike_contribution"] for r in rows]))
    assert s["N_origins"] == summary["N_origins"] == 160832
    assert math.isclose(calculated, recorded["recalibrated_qlike"], rel_tol=1e-12, abs_tol=1e-10)
    assert math.isclose(raw, recorded["raw_qlike"], rel_tol=1e-12, abs_tol=1e-14)
    hit_dates = [r["session"] for r in rows if r["floor_hits"]]
    out[name] = {
        **s,
        "floor_hit_percent": 100 * s["floor_hits"] / s["N_origins"],
        "sessions_with_floor_hits": len(hit_dates),
        "first_floor_session": min(hit_dates) if hit_dates else None,
        "last_floor_session": max(hit_dates) if hit_dates else None,
        "raw_qlike_recomputed": raw,
        "mz_qlike_recomputed": calculated,
        "mz_qlike_published": recorded["recalibrated_qlike"],
        "published_minus_recomputed": recorded["recalibrated_qlike"] - calculated,
        "floor_weighted_qlike_contribution": contribution,
        "floor_loss_share_percent": 100 * contribution / calculated,
        "nonfloor_weighted_qlike_contribution": calculated - contribution,
        "top5_sessions_by_mz_loss": sorted(
            rows, key=lambda r: (-r["recalibrated_qlike"], r["session"])
        )[:5],
        "largest_floor_loss_example": examples[name],
    }
for rel, sha in source_pins.items():
    assert digest(repo / rel) == sha, ("source changed", rel)
assert digest(receipt_path) == receipt_sha_before
closed_artifact_pins = {
    (
        "private/evaluation/primary/" + Path(p).name
        if Path(p).resolve().is_relative_to(private.resolve())
        else Path(p).resolve().relative_to(repo).as_posix()
    ): sha
    for p, sha in receipt["artifacts_sha256"].items()
}
print(
    json.dumps(
        {
            "command": COMMAND,
            "models_fitted": 0,
            "files_written": 0,
            "closed_artifact_sha256": closed_artifact_pins,
            "scope": "PRIMARY_CLOSED_ARITHMETIC_ONLY",
            "no_model_refits": True,
            "confirmation_reads": 0,
            "session_hashes_verified": len(session_pins),
            "source_sha256": source_pins,
            "results": out,
            "status": "PASS_NO_MZ_FORMULA_SCALE_LINKAGE_DEFECT_DEMONSTRATED",
        },
        indent=2,
        allow_nan=False,
    )
)
