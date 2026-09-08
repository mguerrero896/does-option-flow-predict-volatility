# Eight-asset RV15 results

## Eight-asset extension (registered, closed)

The registered extension completed 419 historical sessions per family and 214,209 origins. Ridge passes both option-state and flow tests. LightGBM fails H1, so H2 is not formally tested. **The joint claim across both families is not satisfied. V4 retains the headline.**

The inherited v4 field `predeclared_closure.satisfied=true` means at least one family succeeds; Ridge meets it. The universe registration requires both families for a joint claim, and `global_joint_reject=false` is retained. These rules were not reinterpreted after seeing the results.

Source commit: `a11a5c93446cb3fccafc1d1663d9d334d522f01a`. Native completion was 2026-09-08T17:31:43.093588+00:00; closure verification was 2026-09-08T17:34:38.049094+00:00. The registered source describes the sixth read of the same sessions for the six stocks and the first evaluation of SPY/QQQ as forecast targets. It is neither a new sample nor independent confirmation of the original six-asset result.

This English public account preserves the primary results, all 32 per-asset contrasts, counts, original-six control and material limits. The complete historical [report](../archive/rp4/presentation_originals/results_universe_v1.md.original) and [registration](../archive/rp4/presentation_originals/specification_universe_v1.md.original) retain their original language and seals. Omitted private execution records and detailed secondary diagnostics are not claimed to have been reproduced by this publication.

## Pooled results for eight assets

| Family | Contrast | Delta QLIKE | Reduction | 95% interval | One-sided p | H1→H2 |
| --- | --- | --- | --- | --- | --- | --- |
| Ridge | B1_over_B0 | 0.00274973 | 1.4042% | [0.00091204, 0.00535212] | 0.0208 | REJECTED |
| Ridge | B2_over_B1 | 0.00108789 | 0.5634% | [0.00022321, 0.00197850] | 0.0093 | REJECTED |
| LightGBM | B1_over_B0 | 0.00216036 | 1.0830% | [-0.00041481, 0.00532034] | 0.0794 | NOT_REJECTED |
| LightGBM | B2_over_B1 | -0.00029303 | -0.1485% | [-0.00186356, 0.00101312] | 0.6738 | NOT_TESTED |

Delta is base loss minus expanded loss; positive values favor added information. Percentage reduction is 100 × mean session delta / mean baseline session loss. QLIKE(y,f)=y/f−log(y/f)−1 measures forecast loss, not trading returns. `REJECTED` rejects delta≤0, `NOT_REJECTED` means insufficient evidence, and `NOT_TESTED` means the H1 gate stayed closed. LightGBM H2 p=0.6738 is a nominal diagnostic only.

The saved inference uses paired circular blocks of five sessions, 9,999 resamples and seed 20260907; two-sided percentile 95% intervals and a centered-null one-sided p with the +1 correction. The interval is not an inversion of that p. H1→H2 uses 5% within each family. These p-values do not adjust search across versions, universes, horizons or families; selecting the favorable family does not establish global 5% control. No new Holm result or bootstrap is introduced here.

## Registered sample and weighting

The source window is 2024-08-02–2026-07-31: 479 common sessions, including 60 initial warm-up sessions. Evaluation covers 2024-10-28–2026-07-31. All eight assets occur in all 419 sessions, giving 3,352 asset-sessions and weight 1/8 per asset within each session. Origins are averaged within asset/session, then assets and sessions receive equal weight. Combined panels had 247,639 rows before warm-up and eligibility; those panels are not distributed here.

B0/B1/B2 retain 29/69/138 predictors plus seven asset effects, with AAPL as reference. Expanding walk-forward uses the last ten eligible training sessions for inner validation, 60-minute purge/embargo and a 120-second source-time proxy. RV15 retains the common eligibility mask and conservative RV30 target-end purge, while its outcome ends at +15 minutes. No sample is shortened to improve the result. No cohort after 2026-07-31 is used.

## Appendix: all eight assets

Each cell gives percentage QLIKE reduction and its one-sided p. All 32 contrasts are secondary and nominal, without a joint correction; they cannot rescue the primary result or justify selecting assets. Full deltas and intervals remain in the [32-row aggregate CSV](../../artifacts/rp4_universe_public_v1/by_asset.csv).

| Asset | RV15 origins | Sessions | Weight/session | Linear B1/B0 (p) | Linear B2/B1 (p) | Trees B1/B0 (p) | Trees B2/B1 (p) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AAPL | 26898 | 419 | 12.5% | +1.4906% (0.0163) | +0.9724% (0.0134) | +0.3135% (0.3441) | -0.1550% (0.6404) |
| AMZN | 26743 | 419 | 12.5% | +1.4132% (0.0330) | +0.0148% (0.4882) | +1.1031% (0.1152) | -0.4038% (0.7828) |
| META | 26853 | 419 | 12.5% | +1.3570% (0.0253) | -0.2407% (0.7620) | +0.9755% (0.0937) | +0.3019% (0.3143) |
| MSFT | 26729 | 419 | 12.5% | +0.7357% (0.1323) | -0.1138% (0.5682) | +1.6822% (0.1216) | -0.4381% (0.8053) |
| NVDA | 26764 | 419 | 12.5% | +0.9240% (0.0139) | +1.1270% (0.0001) | +1.5965% (0.0430) | +0.0635% (0.4209) |
| TSLA | 26845 | 419 | 12.5% | +0.7052% (0.0855) | +0.7462% (0.0325) | +3.0443% (0.0393) | +0.3421% (0.3835) |
| SPY | 26791 | 419 | 12.5% | +2.5381% (0.0572) | +1.2581% (0.0204) | -0.0317% (0.5317) | -0.9878% (0.8019) |
| QQQ | 26586 | 419 | 12.5% | +1.6190% (0.0086) | +0.5434% (0.0843) | +0.5322% (0.3236) | +0.2902% (0.3416) |

Linear flow is positive for six of eight assets; META and MSFT are slightly negative in this jointly trained model. SPY has the largest linear flow reduction, +1.2581% (p=0.0204); QQQ gives +0.5434% (p=0.0843). These asset-level observations are not independent confirmatory replications.

## Original six-asset control

The closed control reproduces the original v4 RV15 losses without refitting models or repeating inference. Its result matches the [already public primary statistics](../../artifacts/rp4_v4_b4/primary_statistics.csv):

| Family | Contrast | Delta QLIKE | Reduction | 95% interval | One-sided p | H1→H2 |
| --- | --- | --- | --- | --- | --- | --- |
| Ridge | B1_over_B0 | 0.00161631 | 0.8801% | [0.00025299, 0.00345353] | 0.0390 | REJECTED |
| Ridge | B2_over_B1 | 0.00113376 | 0.6228% | [0.00033504, 0.00193216] | 0.0032 | REJECTED |
| LightGBM | B1_over_B0 | 0.00219662 | 1.1700% | [0.00061099, 0.00410267] | 0.0135 | REJECTED |
| LightGBM | B2_over_B1 | -0.00021290 | -0.1147% | [-0.00204412, 0.00110417] | 0.6280 | NOT_REJECTED |

The saved RV15 control has 419 sessions and 160,832 origins. Its 2,514 session-loss cells and 1,676 session deltas have maximum absolute differences of zero. The public contract compares the six copied loss columns against the original public session-loss CSV; session-mean forecasts and actuals are omitted from this copy. The historical audit also reports three RV15/RV30/RV5 controls with 5,028 exact deltas. That broader audit is recorded evidence, not a newly repeated check here.

RV15/RV5 had matching historical hashes for all four masks. RV30 v3 did not preserve that hash vector: its control reconstructed masks from pinned sources and verified keys, targets, counts and time bounds. A reconstructed mask is not a nonexistent historical hash. These controls are not new eight-asset RV30/RV5 evaluations.

Separately, restricting the eight-asset model's saved aggregate losses to the original six names gives equal weight 1/6 within each session:

| Family | Contrast | Delta QLIKE | Reduction |
| --- | --- | --- | --- |
| Ridge | B1_over_B0 | 0.00205679 | 1.1142% |
| Ridge | B2_over_B1 | 0.00076239 | 0.4177% |
| LightGBM | B1_over_B0 | 0.00270309 | 1.4337% |
| LightGBM | B2_over_B1 | -0.00008286 | -0.0446% |

This is descriptive transport, not invariance: the expanded model changes training and asset effects. No p-values are recalculated for this restriction, and differences are not causally attributed to including ETFs.

## Distribution and material limits

| Family | Contrast | Median delta | Mean trimmed 5% in each tail |
| --- | --- | --- | --- |
| Ridge | B1_over_B0 | 0.00135209 | 0.00153356 |
| Ridge | B2_over_B1 | 0.00079190 | 0.00084314 |
| LightGBM | B1_over_B0 | 0.00112998 | 0.00107910 |
| LightGBM | B2_over_B1 | 0.00031828 | 0.00042264 |

Medians and trimmed means are secondary; they do not replace the primary mean. Detailed chronological blocks, block exclusions, the last 30 sessions, regimes and high-loss-session diagnostics remain in the closed source summary; the public summary explicitly lists its selected fields. No economic benefit after costs is established.

SPY and QQQ overlap economically with the six stocks; equal statistical weights do not create independent exposures. The source report's current holdings diagnostic is descriptive, not historical weights or model inputs; no raw holdings response is copied.

The closed materialization reports 958/958 ETF-sessions. Identical observed bar duplicates were removed; conflicting duplicates were rejected. The eligibility repair restored an inherited default only where the column was absent. Missing SPY bars on 2026-03-09 retain six invalid origins. ETF dividends were missing in 958 ETF-sessions and remain NaN, not zero. The native counter `etf_gamma_numeric_valid_rows=0` covers 61,910 ETF rows; it does not mean every gamma column is NaN, and observed ETF gamma cannot explain the B2 gain. Historical identity of the volume overlay and the ETF `high_flow` classification remain unproven.

The source-time, aggressor/dealer and gamma variables remain proxies; actual historical client receipt, participant identities and dealer inventories are not observed. CPU execution was retained after a GPU B2 QLIKE difference of 0.00055754 exceeded 1e-6. A memory allocation failure preserved 338 completed sessions before continuation. A restart reused earlier admission evidence without a new prior receipt; the later D07 record acknowledges that gap and does not manufacture retrospective approval. Publication does not replay that execution or claim cross-hardware identity.

## Source custody and reproduction boundary

Original report SHA-256: `1a0418e2d6f74c39bd1bfb63ec24133d885b008aa0afeb67260588a8811851b2`. Original registration SHA-256: `aafde61fa8a5373c88cd4a21199fff86cfb69f7448d70197729bed0c17686d9a`. Closed full summary SHA-256: `74bd1bdcbd9fb1a0e4018af19fdc74d221751e039f25c373c6cb34d337d446a3`. The [import receipt](../../artifacts/rp4_universe_public_v1/import_receipt.json) binds every copied source and explicitly selected public field to commit `a11a5c93446cb3fccafc1d1663d9d334d522f01a`. Public derivatives carry separate hashes; original pins never authenticate changed bytes.

The final historical receipt says `PASS_FINAL_RV15_REPORT_AND_NATIVE_CUSTODY`; the closure record says `PASS_RV15_CLOSED_AND_PROCESSES_EXITED`. The independent family/control audit alone explicitly excluded final aggregation acceptance. Together the closed records cover 838 family sessions, 2,514 components, 19 control artifacts and 2,581 source pins. This publication verifies selected public aggregates and those recorded statements, not inaccessible checkpoint custody.

The read-only check `python -m scripts.build_rp4_universe_english` verifies this presentation; `--write` regenerates only this document from public aggregates. No model or inference module is imported. Eight-asset RV30/RV5, the v5 selector in this extension and its final window remain unexecuted/deferred; they do not start automatically. The original six-asset v4 result remains the primary public presentation.

RESEARCH_ONLY. NOT INVESTMENT ADVICE. capital_go=false.
