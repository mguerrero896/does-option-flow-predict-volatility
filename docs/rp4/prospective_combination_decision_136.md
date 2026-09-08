# Decision 136 — prospective top2 and four-family combination secondaries

**English translation. Historical seals refer to the preserved original bytes.**

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.

New registration authorised by Miguel through part 34 of 2026-09-09 and his instruction in this task. Its receipt and sidecar pin the bytes and local UTC time. Previous registrations, decision 134 and draft amendment 4, which remains unsealed, are not changed. These candidates were selected after observing historical development results: this is not historical confirmation.

**v4 ridge RV15 remains primary. Top2 and the equal-weight combination of HAR, ridge, elastic net and LightGBM are secondaries registered now.** Instruction 34 explicitly extends their scope to reads 20/40/45/335; top2 is not presented as already sealed in the earlier draft 4.

## Fixed forecasts

For each asset/session/origin key and each B0/B1/B2 set, the combination is `(f_HAR + f_ridge + f_elastic_net + f_LightGBM) / 4`, over **positive variance levels**, before calculating QLIKE. Neither logarithms, losses nor p-values are averaged. Weights are always 0.25: they are neither estimated nor selected by session.

Top2 retains the A3 rule: rank the five families seasonal_persistence, log_har, log_ridge_harq, log_elastic_net, lightgbm_qlike by internal-validation QLIKE, with that same order for ties, and average the two selected forecasts in levels with weights 0.5. Selection and hyperparameters use only the last ten sessions of causal training; never losses from the predicted session or aggregate prospective performance.

Both secondaries inherit the complete A3 scientific contract `artifacts/rp4_v5_a3/specification.json`, SHA-256 `a318736f7e5a08e21c089b59ec90aae1c5bccb015cb6d286bb59dd078fd2ee3e`, and the producers fixed by `artifacts/rp4_v5_a3/freeze.json`, SHA-256 `69db4672b7ad705300c820b42abb8f8430d8380a3f0360e2d1008b7b10b7f855`. Grids, transformations, calibrations and bounds per family are retained, ElasticNet with precomputed Gram, max_iter 500000 and tolerance 1e-6, CPU LightGBM with the v4 grid and A3 scientific seeds. The deferred network is not added. Prospective inference uses seed 20260907 from the prospective registration, different from seed 20260908 of the historical v5 report.

Scope: RV15; nested sets 29/69/138; six assets AAPL, AMZN, META, MSFT, NVDA and TSLA; inherited common masks, source PIT proxy of 120 s, purge/embargo of 60 minutes and expanding training. Neither assets nor horizons are expanded. Each family retains its causal learning, and earlier targets enter only when observable under the registered masks. If a forecast is missing or fails integrity, weights are not redistributed and families are not replaced: the affected read is UNVERIFIABLE.

## Cohorts and reads

The complete eligibility definition from prospective registration v1 and amendments 1–3 is incorporated. Begin with XNYS sessions from 2026-09-08, acquisition scheduled from 2026-09-09 10:00 Australia/Sydney under amendment 1. Acquisition PASS does not equal scientific eligibility. The census records absences and failures without choosing dates by losses, signs or significance.

| Read | Exact cohort and role |
|---|---|
| 20 | First 20 complete prospective sessions: early consistency; v4 retains its original primary decision. |
| 40 | First 40 cumulative prospective sessions: stability; same administrative condition of v1 fixed before opening 20; without an administrative date, scheduled upon reaching 40. Does not rescue 20. |
| 45 | The 25 historical sessions from 2026-08-03 to 2026-09-04 and the first 20 prospective sessions, a single read upon reaching 20 new sessions. Weight 1/45 per session. These are not 45 prospective sessions; partly observed analysis. |
| 335 | First 335 cumulative prospective sessions, excluding the 25 historical ones, once only regardless of the earlier result. Does not rewrite 20. |

For 45, a separate manifest of HAR/ridge/ElasticNet/LightGBM forecasts and validations for those same 25 dates is required, with code and inputs frozen before calculation/reading. This registration neither claims that they exist nor authorises replacing them with v4 ridge losses. If they are unavailable or their provenance cannot be established, report NOT_AVAILABLE for the affected secondary, without replacing dates or turning the sample into 45 prospective sessions.

## Inference and comparison fixed before prospective reads

QLIKE = y/f − log(y/f) − 1; mean across assets within session and equal weights across sessions. Delta = baseline − expanded loss; percentage reduction = 100 × mean(delta) / mean(baseline loss). Each candidate and read applies the same sequence **H1 B1/B0 → H2 B2/B1**, with a positive estimand and one-sided p ≤ 0.05 required for rejection; H2 opens only after H1 rejects in that same sample. If H1 fails, H2's p-value is diagnostic only. No CI-based requirement is added. Circular session bootstrap, five-session blocks, 9,999 resamples, seed 20260907, centred null and +1 correction; two-sided 95% percentile CI. `artifacts/rp4_v3_code/inference.py::session_contrast` is inherited unchanged.

Each new secondary has its own separate nominal sequence. It changes neither Holm A/B/C, sequence D nor the primary v4 decision. **No global control at 5% is claimed across candidates, cumulative reads or historical search**; nominal p-values do not correct post hoc candidate selection. There is no success criterion based on rejection at any of the reads, stopping for significance or additional inspections at 120/146 or other thresholds. Adverse or non-computable results are reported without discretionary repetition.

B0/B1/B2 losses and both chains will be published for all three procedures on the same eligible keys. If the combination has the lowest prospective B2 QLIKE, it will be reported as the descriptive winner of that registered comparison, with absolute/relative differences against v4 and top2, even if it contradicts the historical ranking. This does not imply statistical superiority between models: H1/H2 evaluate information within a model. Whether its nominal chain rejects is reported separately. v4 retains the primary role, and no ranking rewrites earlier verdicts or demonstrates profitability or causality.

## Custody

The new receipt retains hashes of antecedents, the instruction and producers without overwriting them. Before executing prospective forecasts, a new manifest will seal inputs, calendar, code, environment and deterministic resources; new outputs, without reusing closed executions. This registration neither executes models nor opens prospective stores. This task has read only registration documents and historical results from 2024-10-28–2026-07-31. The absence of reads evidenced here is limited to this task; neither global knowledge of third parties nor current absence of data is claimed from not inspecting them. The hash and local time are neither the maintainer's signature nor an external timestamp. No push or external publication.
