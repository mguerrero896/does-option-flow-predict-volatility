"""Check the final narrative against stored results, without new inference."""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PINS = dict(
    [
        (
            "docs/rp4/results_v4.md",
            "c42316748a57cfc1ce73681a98bacb1fb157ee3ec13983e222e3494d1996a2c7",
        ),
        (
            "docs/rp4/results_v3_revision2.md",
            "05f263b019a74a8591f3840d69aa86947f5cc9bf343eb85d5a30601e8a0f142e",
        ),
        (
            "artifacts/rp4_v4_b4/robustness.csv",
            "09925f9cefe4fcf2c19f4a915ad2994c125bbafdb94dfd332cc821ce1f180acb",
        ),
        (
            "artifacts/rp4_v4_b4/distribution_secondary.csv",
            "62312356720ac370fe3928eb5212db5a99ad7aa63f8ce4fe568ae149faed96cb",
        ),
    ]
)


def rows(name: str) -> list[dict[str, str]]:
    with (ROOT / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def check() -> dict[str, object]:
    for name, expected in PINS.items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == expected, name
    report = (ROOT / "docs/rp4/RESULTADO_FINAL.md").read_text(encoding="utf-8")
    assert report.splitlines()[0] == ("fuera de muestra walk-forward, partición fijada 2026-09-07.")
    for text in (
        "−167.448,32 %",
        "0,0032",
        "0,0172",
        "Holm 0,0870/0,0096",
        "tres de los seis a 5 minutos",
        "25 sesiones",
        "cuarta evaluación",
        "2025-01-25–2025-02-24",
        "proxy de tiempo fuente a 120 s",
        "ridge nominal",
        "sin una v5",
        "capital_go=false",
    ):
        assert text in report, text
    stability = rows("artifacts/rp4_v4_b4/robustness.csv")
    counts: dict[str, int] = {}
    for horizon, expected in ((15, 6), (5, 3)):
        selected = [
            row
            for row in stability
            if row["horizon_minutes"] == str(horizon)
            and row["window"] == "primary"
            and row["family"] == "log_ridge_harq"
            and row["contrast"] == "B2_over_B1"
        ]
        assets = [r for r in selected if r["subset"].startswith("asset_")]
        blocks = [r for r in selected if r["subset"].startswith("chronological_block_")]
        assert len(assets) == 6 and len(blocks) == 3
        counts[f"rv{horizon}_positive_assets"] = sum(float(r["estimate"]) > 0 for r in assets)
        assert counts[f"rv{horizon}_positive_assets"] == expected
        assert all(float(r["estimate"]) > 0 for r in blocks)
    comparisons = 0
    statistics = rows("artifacts/rp4_v4_b4/primary_statistics.csv")
    for horizon in (15, 5):
        for stage in ("b2", "b3"):
            losses = rows(f"artifacts/rp4_v4_{stage}_rv{horizon}/session_losses.csv")
            assert len(losses) == (419 if stage == "b2" else 25)
            for family in ("log_ridge_harq", "lightgbm_qlike"):
                for base, richer in (("B0", "B1"), ("B1", "B2")):
                    delta = math.fsum(
                        float(r[f"loss__{family}__{base}"]) - float(r[f"loss__{family}__{richer}"])
                        for r in losses
                    ) / len(losses)
                    assert math.isfinite(delta)
                    matching = [
                        row
                        for row in statistics
                        if row["horizon_minutes"] == str(horizon)
                        and row["window"] == ("primary" if stage == "b2" else "confirmation")
                        and row["family"] == family
                        and row["contrast"] == f"{richer}_over_{base}"
                    ]
                    assert len(matching) == 1
                    assert math.isclose(delta, float(matching[0]["estimate"]), abs_tol=1e-14)
                    comparisons += 1
    return {
        "status": "PASS",
        "source_pins": len(PINS),
        "stored_contrasts_checked": comparisons,
        **counts,
        "new_fits": 0,
        "new_bootstraps": 0,
        "final_report_sha256": hashlib.sha256(report.encode()).hexdigest(),
    }


if __name__ == "__main__":
    print(json.dumps(check(), sort_keys=True))
