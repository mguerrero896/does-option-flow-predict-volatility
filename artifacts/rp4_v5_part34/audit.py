"""Part 34: historical saved forecasts only; no fitting or prospective readers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from artifacts.rp4_v3_code.inference import session_contrast
from artifacts.rp4_v5_a2_code.reporting import _session_losses
from artifacts.rp4_v5_a3_code import reporting as report
from artifacts.rp4_v5_code.report import INFERENCE

from mds650.metrics import qlike_losses

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
RUN = ROOT / "artifacts/rp4_v5_run_a3_20260908"
LEARNED = ("log_har", "log_ridge_harq", "log_elastic_net", "lightgbm_qlike")
METHODS = ("log_ridge_harq", "average_linear3", "average_learned4")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.write_text(
        json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )


def average(forecasts, families):
    return {name: np.mean([forecasts[f][name] for f in families], axis=0) for name in report.SETS}


def self_check():
    forecasts = {f: {b: [i + 1.0, i + 2.0] for b in report.SETS} for i, f in enumerate(LEARNED)}
    assert np.array_equal(average(forecasts, LEARNED)["B0"], [2.5, 3.5])
    record = {
        "session": "2024-10-28",
        "horizon_minutes": 15,
        "target": [1.0, 1.0, 1.0],
        "keys": [{"asset": a} for a in ["A", "A", "B"]],
    }
    prediction = {b: [1.0, 1.0, 2.0] for b in report.SETS}
    result = _session_losses(record, {"check": prediction})[0]["qlike"]
    assert np.isclose(result, qlike_losses([1.0], [2.0])[0] / 2)
    assert not np.isclose(result, qlike_losses([1.0, 1.0, 1.0], [1.0, 1.0, 2.0]).mean())
    assert not np.isclose(
        qlike_losses([1.0], [1.5])[0], qlike_losses([1.0, 1.0], [1.0, 2.0]).mean()
    )


def main():
    self_check()
    paths = sorted((RUN / "seasonal_persistence/sessions").glob("????-??-??.json"))
    calendar = [p.stem for p in paths]
    report.a2._calendar(calendar)
    losses, diagnostics, inputs, frequencies = [], [], {}, []
    expected_binding = json.loads(paths[0].with_suffix(".receipt.json").read_text())["binding"]
    for index, date in enumerate(calendar):
        records = []
        for family in report.BASE_FAMILIES:
            path = RUN / family / "sessions" / f"{date}.json"
            receipt_path = path.with_suffix(".receipt.json")
            receipt = json.loads(receipt_path.read_text())
            digest = sha(path)
            assert receipt["sha256"] == digest and receipt["binding"] == expected_binding
            record = json.loads(path.read_text())
            assert record["binding"] == expected_binding
            assert record["session"] == date and record["family"] == family
            records.append(record)
            inputs[str(path.relative_to(ROOT))] = digest
            inputs[str(receipt_path.relative_to(ROOT))] = sha(receipt_path)
        (session,) = report.assemble_sessions(records)
        forecasts = session["forecasts"]
        forecasts["average_linear3"] = average(forecasts, LEARNED[:3])
        forecasts["average_learned4"] = average(forecasts, LEARNED)
        session_losses = _session_losses(session, forecasts)
        for row in session_losses:
            row["qlike_origin"] = float(
                qlike_losses(
                    session["target"], forecasts[row["family"]][row["information_set"]]
                ).mean()
            )
        losses.extend(session_losses)
        for b in report.SETS:
            frequencies.append(
                {
                    "session": date,
                    "information_set": b,
                    "family": session["selection"][b]["primary"],
                }
            )
        for family in report.BASE_FAMILIES:
            canonical = next(
                row["qlike"]
                for row in session_losses
                if row["family"] == family and row["information_set"] == "B2"
            )
            origin = float(qlike_losses(session["target"], forecasts[family]["B2"]).mean())
            diagnostics.append(
                {
                    "session": date,
                    "family": family,
                    "realized_canonical": canonical,
                    "realized_origin": origin,
                    "validation": session["fits"]["B2"][family]["selected"]["validation_qlike"],
                }
            )
        if (index + 1) % 100 == 0:
            print(f"Verified {index + 1}/419 historical sessions", flush=True)
    frame = pd.DataFrame(losses)
    # Exact round-trip of every existing family and selector session loss.
    old = pd.read_csv(RUN / "reports/5_control/losses.csv")
    keys = ["horizon_minutes", "session_date", "family", "information_set"]
    joined = old.merge(frame, on=keys, validate="one_to_one", suffixes=("_old", "_new"))
    assert len(joined) == len(old) == 419 * 7 * 3
    max_error = float(np.max(np.abs(joined.qlike_old - joined.qlike_new)))
    assert max_error < 1e-14
    table = frame.groupby(["family", "information_set"]).qlike.mean().unstack()
    contrasts = []
    for method in METHODS:
        pivot = (
            frame[frame.family.eq(method)]
            .pivot(index="session_date", columns="information_set", values="qlike")
            .sort_index()
        )
        assert tuple(pivot.index) == tuple(calendar)
        for seed in (INFERENCE["seed"], 20260907):
            gate = True
            for name, base, expanded in [("H1", "B0", "B1"), ("H2", "B1", "B2")]:
                result = session_contrast(
                    (pivot[base] - pivot[expanded]).to_numpy(), **{**INFERENCE, "seed": seed}
                )
                assert result["status"] == "COMPUTED"
                result.update(
                    method=method,
                    contrast=name,
                    gate_open=gate,
                    reduction_percent=100 * result["estimate"] / pivot[base].mean(),
                )
                contrasts.append(result)
                gate = gate and result["estimate"] > 0 and result["p_raw"] <= 0.05
    diagnostic = pd.DataFrame(diagnostics)
    diagnostic["gap_canonical"] = diagnostic.realized_canonical - diagnostic.validation
    diagnostic["gap_origin"] = diagnostic.realized_origin - diagnostic.validation
    diag_table = diagnostic.groupby("family").mean(numeric_only=True)
    oracle = {}
    for weight in ("canonical", "origin"):
        pivot = diagnostic.pivot(index="session", columns="family", values=f"realized_{weight}")
        oracle[weight] = {
            "ex_post_oracle_B2": float(pivot.min(axis=1).mean()),
            "best_fixed_B2": float(pivot.mean().min()),
            "best_fixed_family": pivot.mean().idxmin(),
        }
    comparison = pd.read_csv(RUN / "reports/5_control/comparison.csv")
    drift = [
        {
            **row,
            "v5_qlike": table.loc[row["family"], row["information_set"]],
            "v5_minus_v4": table.loc[row["family"], row["information_set"]] - row["qlike"],
        }
        for row in comparison[comparison.version.eq("v4")].to_dict("records")
    ]
    frequency = pd.DataFrame(frequencies).groupby(["information_set", "family"]).size()
    assert frequency.loc["B0"].to_dict() == {
        "lightgbm_qlike": 203,
        "log_elastic_net": 119,
        "log_har": 29,
        "log_ridge_harq": 68,
    }
    frame.to_csv(OUT / "session_losses.csv", index=False)
    table.to_csv(OUT / "table.csv")
    diag_table.to_csv(OUT / "diagnostics.csv")
    origin_contrasts = []
    for method in METHODS:
        pivot = (
            frame[frame.family.eq(method)]
            .pivot(index="session_date", columns="information_set", values="qlike_origin")
            .sort_index()
        )
        for name, base, expanded in [("H1", "B0", "B1"), ("H2", "B1", "B2")]:
            result = session_contrast(
                (pivot[base] - pivot[expanded]).to_numpy(), **{**INFERENCE, "seed": 20260907}
            )
            origin_contrasts.append({**result, "method": method, "contrast": name})
    summary = {
        "status": "VERIFIED_HISTORICAL_POST_HOC",
        "sessions": len(calendar),
        "session_family_records": len(inputs) // 2,
        "refits": 0,
        "prospective_data_reads": 0,
        "canonical_roundtrip_max_abs_error": max_error,
        "contrasts": contrasts,
        "oracle": oracle,
        "origin_weight_auditor_seed_contrasts": origin_contrasts,
        "ridge_lightgbm_drift": drift,
        "canonical_seed": INFERENCE["seed"],
        "auditor_comparison_seed": 20260907,
        "input_binding": expected_binding,
        "method_families": {"average_linear3": LEARNED[:3], "average_learned4": LEARNED},
    }
    write_json(OUT / "summary.json", summary)
    write_json(OUT / "input_hashes.json", inputs)
    print(table.loc[list(METHODS)].to_string())
    print(diag_table.to_string())
    print(json.dumps(oracle))
    for row in contrasts:
        print(
            row["method"],
            row["bootstrap_seed"],
            row["contrast"],
            row["reduction_percent"],
            row["p_raw"],
        )
    for row in origin_contrasts:
        print("Origin diagnostic", row["method"], row["contrast"], row["p_raw"])


if __name__ == "__main__":
    main()
