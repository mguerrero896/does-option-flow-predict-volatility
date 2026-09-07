"""Read-only attribution of the largest completed primary log-OLS B2 loss."""

import csv
import json
from pathlib import Path

import numpy as np
from evaluate import ROOT, sha256, write_json_once

from mds650.metrics import qlike_losses


def main() -> None:
    public = ROOT / "artifacts/rp4_b2"
    summary = json.loads((public / "summary.json").read_text())
    losses_path = public / "session_losses.csv"
    with losses_path.open(newline="") as handle:
        sessions = list(csv.DictReader(handle))
    column = "loss__log_ols_harq__B2"
    largest = max(sessions, key=lambda row: float(row[column]))
    checkpoint = (
        Path("D:/MDS650/artifacts/rp4_20260907/evaluation/primary/sessions")
        / f"{largest['session_date']}.json"
    )
    record = json.loads(checkpoint.read_text())
    assert sha256(checkpoint) == summary["completed_session_sha256"][checkpoint.name]
    assert record["binding"] == summary["binding"]
    actual = np.asarray(record["target"])
    forecast = np.asarray(record["forecasts"]["log_ols_harq"]["B2"])
    losses = qlike_losses(actual, forecast)
    assets = np.asarray([key["asset"] for key in record["keys"]])
    by_asset = []
    for asset in sorted(set(assets)):
        mask = assets == asset
        by_asset.append(
            {
                "asset": str(asset),
                "origins": int(mask.sum()),
                "qlike": float(losses[mask].mean()),
                "forecast_min": float(forecast[mask].min()),
                "forecast_max": float(forecast[mask].max()),
                "forecasts_at_frozen_floor": int((forecast[mask] == 1e-12).sum()),
                "target_min": float(actual[mask].min()),
                "target_max": float(actual[mask].max()),
            }
        )
    daily = float(np.mean([row["qlike"] for row in by_asset]))
    assert np.isclose(daily, float(largest[column]), rtol=1e-12)
    total = sum(float(row[column]) for row in sessions)
    output = {
        "scope": "Completed forecasts only; no refit, exclusion, or changed result",
        "session": largest["session_date"],
        "N_sessions": len(sessions),
        "equal_asset_session_qlike": daily,
        "share_of_summed_session_B2_qlike_pct": 100 * daily / total,
        "by_asset": by_asset,
        "fit": record["fits"]["log_ols_harq__B2"],
        "inputs": {
            f"private/evaluation/primary/sessions/{checkpoint.name}": sha256(checkpoint),
            losses_path.relative_to(ROOT).as_posix(): sha256(losses_path),
        },
        "code_sha256": sha256(Path(__file__)),
        "interpretation": (
            "The frozen QLIKE ratio penalizes near-zero positive variance forecasts severely. "
            "This is retained adverse model behavior, not grounds to remove observations. "
            "Saved fit metadata alone cannot identify a causal feature attribution."
        ),
    }
    destination = public / "tail_diagnostic.json"
    write_json_once(destination, output)
    print(json.dumps(output, indent=2))
    print(f"diagnostic_sha256={sha256(destination)}")


if __name__ == "__main__":
    main()
