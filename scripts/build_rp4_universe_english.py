"""Render the closed eight-asset report from public aggregates; no scientific execution."""

# Long document paragraphs retain stable Markdown lines.
# ruff: noqa: E501

from __future__ import annotations

import argparse
import csv
import json
from importlib import import_module
from os.path import relpath
from pathlib import Path
from statistics import fmean
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "artifacts/rp4_universe_public_v1"
REPORT = ROOT / "docs/rp4/results_universe_v1.md"
ASSETS = ("AAPL", "AMZN", "META", "MSFT", "NVDA", "TSLA", "SPY", "QQQ")
FAMILIES = ("log_ridge_harq", "lightgbm_qlike")
LABELS = {"log_ridge_harq": "Ridge", "lightgbm_qlike": "LightGBM"}
CONTRASTS = (("B1_over_B0", "B0", "B1"), ("B2_over_B1", "B1", "B2"))


def historical_document_link(name: str) -> str:
    """Resolve a preserved source or its separately recorded public redaction."""
    archive = import_module("scripts.rp4_archive_sources")
    path = archive.original_path(ROOT / "docs/rp4" / name)
    return Path(relpath(path, REPORT.parent)).as_posix()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def table(headers: list[str], rows: list[list[Any]]) -> str:
    return "\n".join(
        "| " + " | ".join(map(str, row)) + " |" for row in [headers, ["---"] * len(headers), *rows]
    )


def result_table(rows: list[dict[str, Any]]) -> str:
    return table(
        ["Family", "Contrast", "Delta QLIKE", "Reduction", "95% interval", "One-sided p", "H1→H2"],
        [
            [
                LABELS[row["family"]],
                row["contrast"],
                f"{float(row['estimate']):.8f}",
                f"{float(row['percent_reduction_mean']):.4f}%",
                f"[{float(row['ci_low']):.8f}, {float(row['ci_high']):.8f}]",
                f"{float(row['p_raw']):.4f}",
                row["hypothesis_status"],
            ]
            for row in rows
        ],
    )


def appendix_rows() -> list[list[Any]]:
    records = read_csv(DATA / "by_asset.csv")
    indexed = {(r["asset"], r["family"], r["contrast"]): r for r in records}
    rows = []
    for asset in ASSETS:
        base = indexed[(asset, FAMILIES[0], CONTRASTS[0][0])]
        row: list[Any] = [asset, base["N_origins"], base["N_sessions"], "12.5%"]
        for family in FAMILIES:
            for contrast, _, _ in CONTRASTS:
                result = indexed[(asset, family, contrast)]
                row.append(
                    f"{float(result['percent_reduction_mean']):+.4f}% "
                    f"({float(result['p_raw']):.4f})"
                )
        rows.append(row)
    return rows


def transport_rows() -> list[list[Any]]:
    records = read_csv(DATA / "by_asset.csv")
    rows = []
    for family in FAMILIES:
        for contrast, _, _ in CONTRASTS:
            selected = [
                r
                for r in records
                if r["asset"] in ASSETS[:6] and r["family"] == family and r["contrast"] == contrast
            ]
            baseline = [float(r["baseline_loss"]) for r in selected]
            expanded = [float(r["expanded_loss"]) for r in selected]
            delta = fmean(a - b for a, b in zip(baseline, expanded, strict=True))
            rows.append(
                [LABELS[family], contrast, f"{delta:.8f}", f"{100 * delta / fmean(baseline):.4f}%"]
            )
    return rows


def render() -> str:
    saved = json.loads((DATA / "primary_summary.json").read_bytes())
    receipt = json.loads((DATA / "import_receipt.json").read_bytes())
    control = [
        row
        for row in read_csv(ROOT / "artifacts/rp4_v4_b4/primary_statistics.csv")
        if row["window"] == "primary" and row["horizon_minutes"] == "15"
    ]
    pooled = result_table(saved["contrasts"])
    original_six = result_table(control)
    report_original = historical_document_link("results_universe_v1.md")
    specification_original = historical_document_link("specification_universe_v1.md")
    appendix = table(
        [
            "Asset",
            "RV15 origins",
            "Sessions",
            "Weight/session",
            "Linear B1/B0 (p)",
            "Linear B2/B1 (p)",
            "Trees B1/B0 (p)",
            "Trees B2/B1 (p)",
        ],
        appendix_rows(),
    )
    transport = table(["Family", "Contrast", "Delta QLIKE", "Reduction"], transport_rows())
    tails = table(
        ["Family", "Contrast", "Median delta", "Mean trimmed 5% in each tail"],
        [
            [
                LABELS[r["family"]],
                r["contrast"],
                f"{r['median_paired_contrast']:.8f}",
                f"{r['trimmed_mean_5pct_each_tail']:.8f}",
            ]
            for r in saved["tail_secondary"]
        ],
    )
    return f"""# Eight-asset RV15 results

## Eight-asset extension (registered, closed)

The registered extension completed 419 historical sessions per family and 214,209 origins. Ridge passes both option-state and flow tests. LightGBM fails H1, so H2 is not formally tested. **The joint claim across both families is not satisfied. V4 retains the headline.**

The inherited v4 field `predeclared_closure.satisfied=true` means at least one family succeeds; Ridge meets it. The universe registration requires both families for a joint claim, and `global_joint_reject=false` is retained. These rules were not reinterpreted after seeing the results.

Source commit: `{receipt["source_commit"]}`. Native completion was 2026-09-08T17:31:43.093588+00:00; closure verification was 2026-09-08T17:34:38.049094+00:00. The registered source describes the sixth read of the same sessions for the six stocks and the first evaluation of SPY/QQQ as forecast targets. It is neither a new sample nor independent confirmation of the original six-asset result.

This English public account preserves the primary results, all 32 per-asset contrasts, counts, original-six control and material limits. The complete historical [report]({report_original}) and [registration]({specification_original}) retain their original language and seals. Omitted private execution records and detailed secondary diagnostics are not claimed to have been reproduced by this publication.

## Pooled results for eight assets

{pooled}

Delta is base loss minus expanded loss; positive values favor added information. Percentage reduction is 100 × mean session delta / mean baseline session loss. QLIKE(y,f)=y/f−log(y/f)−1 measures forecast loss, not trading returns. `REJECTED` rejects delta≤0, `NOT_REJECTED` means insufficient evidence, and `NOT_TESTED` means the H1 gate stayed closed. LightGBM H2 p=0.6738 is a nominal diagnostic only.

The saved inference uses paired circular blocks of five sessions, 9,999 resamples and seed 20260907; two-sided percentile 95% intervals and a centered-null one-sided p with the +1 correction. The interval is not an inversion of that p. H1→H2 uses 5% within each family. These p-values do not adjust search across versions, universes, horizons or families; selecting the favorable family does not establish global 5% control. No new Holm result or bootstrap is introduced here.

## Registered sample and weighting

The source window is 2024-08-02–2026-07-31: 479 common sessions, including 60 initial warm-up sessions. Evaluation covers 2024-10-28–2026-07-31. All eight assets occur in all 419 sessions, giving 3,352 asset-sessions and weight 1/8 per asset within each session. Origins are averaged within asset/session, then assets and sessions receive equal weight. Combined panels had 247,639 rows before warm-up and eligibility; those panels are not distributed here.

B0/B1/B2 retain 29/69/138 predictors plus seven asset effects, with AAPL as reference. Expanding walk-forward uses the last ten eligible training sessions for inner validation, 60-minute purge/embargo and a 120-second source-time proxy. RV15 retains the common eligibility mask and conservative RV30 target-end purge, while its outcome ends at +15 minutes. No sample is shortened to improve the result. No cohort after 2026-07-31 is used.

## Appendix: all eight assets

Each cell gives percentage QLIKE reduction and its one-sided p. All 32 contrasts are secondary and nominal, without a joint correction; they cannot rescue the primary result or justify selecting assets. Full deltas and intervals remain in the [32-row aggregate CSV](../../artifacts/rp4_universe_public_v1/by_asset.csv).

{appendix}

Linear flow is positive for six of eight assets; META and MSFT are slightly negative in this jointly trained model. SPY has the largest linear flow reduction, +1.2581% (p=0.0204); QQQ gives +0.5434% (p=0.0843). These asset-level observations are not independent confirmatory replications.

## Original six-asset control

The closed control reproduces the original v4 RV15 losses without refitting models or repeating inference. Its result matches the [already public primary statistics](../../artifacts/rp4_v4_b4/primary_statistics.csv):

{original_six}

The saved RV15 control has 419 sessions and 160,832 origins. Its 2,514 session-loss cells and 1,676 session deltas have maximum absolute differences of zero. The public contract compares the six copied loss columns against the original public session-loss CSV; session-mean forecasts and actuals are omitted from this copy. The historical audit also reports three RV15/RV30/RV5 controls with 5,028 exact deltas. That broader audit is recorded evidence, not a newly repeated check here.

RV15/RV5 had matching historical hashes for all four masks. RV30 v3 did not preserve that hash vector: its control reconstructed masks from pinned sources and verified keys, targets, counts and time bounds. A reconstructed mask is not a nonexistent historical hash. These controls are not new eight-asset RV30/RV5 evaluations.

Separately, restricting the eight-asset model's saved aggregate losses to the original six names gives equal weight 1/6 within each session:

{transport}

This is descriptive transport, not invariance: the expanded model changes training and asset effects. No p-values are recalculated for this restriction, and differences are not causally attributed to including ETFs.

## Distribution and material limits

{tails}

Medians and trimmed means are secondary; they do not replace the primary mean. Detailed chronological blocks, block exclusions, the last 30 sessions, regimes and high-loss-session diagnostics remain in the closed source summary; the public summary explicitly lists its selected fields. No economic benefit after costs is established.

SPY and QQQ overlap economically with the six stocks; equal statistical weights do not create independent exposures. The source report's current holdings diagnostic is descriptive, not historical weights or model inputs; no raw holdings response is copied.

The closed materialization reports 958/958 ETF-sessions. Identical observed bar duplicates were removed; conflicting duplicates were rejected. The eligibility repair restored an inherited default only where the column was absent. Missing SPY bars on 2026-03-09 retain six invalid origins. ETF dividends were missing in 958 ETF-sessions and remain NaN, not zero. The native counter `etf_gamma_numeric_valid_rows=0` covers 61,910 ETF rows; it does not mean every gamma column is NaN, and observed ETF gamma cannot explain the B2 gain. Historical identity of the volume overlay and the ETF `high_flow` classification remain unproven.

The source-time, aggressor/dealer and gamma variables remain proxies; actual historical client receipt, participant identities and dealer inventories are not observed. CPU execution was retained after a GPU B2 QLIKE difference of 0.00055754 exceeded 1e-6. A memory allocation failure preserved 338 completed sessions before continuation. A restart reused earlier admission evidence without a new prior receipt; the later D07 record acknowledges that gap and does not manufacture retrospective approval. Publication does not replay that execution or claim cross-hardware identity.

## Source custody and reproduction boundary

Original report SHA-256: `{receipt["source_report_original_sha256"]}`. Original registration SHA-256: `{receipt["source_specification_original_sha256"]}`. Closed full summary SHA-256: `{receipt["source_result_summary_original_sha256"]}`. The [import receipt](../../artifacts/rp4_universe_public_v1/import_receipt.json) binds every copied source and explicitly selected public field to commit `{receipt["source_commit"]}`. Public derivatives carry separate hashes; original pins never authenticate changed bytes.

The final historical receipt says `PASS_FINAL_RV15_REPORT_AND_NATIVE_CUSTODY`; the closure record says `PASS_RV15_CLOSED_AND_PROCESSES_EXITED`. The independent family/control audit alone explicitly excluded final aggregation acceptance. Together the closed records cover 838 family sessions, 2,514 components, 19 control artifacts and 2,581 source pins. This publication verifies selected public aggregates and those recorded statements, not inaccessible checkpoint custody.

The read-only check `python -m scripts.build_rp4_universe_english` verifies this presentation; `--write` regenerates only this document from public aggregates. No model or inference module is imported. Eight-asset RV30/RV5, the v5 selector in this extension and its final window remain unexecuted/deferred; they do not start automatically. The original six-asset v4 result remains the primary public presentation.

RESEARCH_ONLY. NOT INVESTMENT ADVICE. capital_go=false.
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    expected = render()
    if args.write:
        REPORT.write_text(expected, encoding="utf-8", newline="\n")
    assert REPORT.read_text(encoding="utf-8") == expected, "Eight-asset presentation changed"
    print("PASS: closed eight-asset presentation matches public aggregates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
