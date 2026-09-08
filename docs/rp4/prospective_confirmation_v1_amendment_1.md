# Prospective v4 replication — amendment 1 to registration v1

**English translation. Historical seals refer to the preserved original bytes.**

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.

**Amendment sealed: 2026-09-08T04:31:58.752153+00:00.** It is added before the collector's first execution, scheduled for **2026-09-09 at 10:00 Australia/Sydney**. The local check records no task execution and its acquisition directory does not yet exist; no prospective cohort has been read or produced in this task.

## Seal chain and scope

The [v1 registration](prospective_confirmation_v1.md) remains intact: SHA-256 `317530c37d2785bb0ce0bfd6a947fc034c78a02bbd5bb102fd17efe8f91b977d`, sealed at **2026-09-08T04:24:01.918499+00:00**, according to its [original receipt](prospective_confirmation_v1_receipt.json). This amendment has its own hash and [sidecar](prospective_confirmation_v1_amendment_1.sha256); its [receipt](prospective_confirmation_v1_amendment_1_receipt.json) links both seals. These are local records of bytes and sequence, not independent third-party timestamps.

**The primary analysis and its decision rule do not change:** replication confirms only if H1 and H2 reject in the linear family at 15 minutes in the primary read of 20 complete sessions, using the v1 sequence and threshold. The cumulative 40-session read planned in v1 retains only its stability role and does not rescue a negative primary result. The two new secondaries are read **once only, alongside the primary, on completing the first 20 sessions**; they are not retested at 40 sessions and do not modify the primary verdict.

The inherited scientific specification is [v4](../../artifacts/rp4_v4_a1/specification.json), SHA-256 `0a45b0a608110e2ca0dcf38accc2a0c2521ebbe9d223eb002e36ec51f78afd04`. Neither v3 nor v4 is edited or reevaluated. A prospective ablation is added as a new secondary; it is not presented as a historical result or a v5.

## Secondary A — predictive contribution of the imbalance block

**Question:** does adding the registered gamma-imbalance block improve the linear family's forecast at 15 minutes compared with the same B2 without that block?

The baseline is B2 without the four `gamma_imbalance.columns`, also removing their corresponding presence indicators; the expansion is complete B2. The four columns, fixed by name before observing data, are:

- `rp4_gamma_imb_total`;
- `rp4_gamma_imb_near_spot`;
- `rp4_gamma_imb_near_short`;
- `rp4_gamma_imb_signed_trades`.

There remain 134 baseline predictors versus the 138 in complete B2, before fixed effects, indicators and rank filtering. The final variable counts trades with identifiable direction: it is not a signed exposure balance. The three historical gamma-exposure columns in `dealer_columns` remain; removing those as well would answer another question and is not registered here.

Retain the same v4 sample and mask as the primary, the same QLIKE loss, asset/session aggregation, expanding training, transformation, temporal selection, grid, seed, purge, embargo and bounds. The reduced model has its own training and selection under those same rules; it does not retrospectively inherit the full model's best hyperparameter. Common masks are retained even if the reduced model could admit more rows. Observations are not removed because of their loss and no new variable selection is performed.

For each session, form delta = reduced-B2 QLIKE − complete-B2 QLIKE, after the same asset means. H0 is a non-positive mean contribution and the alternative is positive. Use v4 mean inference: circular session bootstrap, five-session blocks, 9,999 resamples, seed 20260907, centred null and +1 correction, one-sided p-value and two-sided 95% percentile CI. Publish delta, the effect relative to reduced-model QLIKE, the interval, and nominal and adjusted p-values.

**Rule:** this secondary supports a predictive contribution from the block only if mean delta is positive and its Holm-adjusted p-value across these two secondaries is ≤ 0.05. Non-rejection is reported as “contribution not detected”, never as equivalence or proof that everything is flow composition. Rejection identifies the joint contribution of these columns and their indicators in this family: it does not demonstrate actual dealer inventory, causal hedging or an isolated gamma contribution as distinct from the trade count.

## Secondary B — paired median for trees

**Question:** does the improvement from B2 over B1 in LightGBM at 15 minutes occur in the typical session, even though the historical mean does not confirm it?

Use exactly B1 and B2 of the v4 trees and the same first 20 complete sessions. Form each session's delta = B1 QLIKE − B2 QLIKE, with the same asset/session aggregation. The estimand is the **median of paired deltas**, not the difference between the medians of two series or the median by origin.

Retain the v4 median bootstrap: circular five-session blocks, 9,999 resamples, seed 20260907, two-sided 95% percentile interval and two-sided p-value using the [inference producer](../../artifacts/rp4_v3_code/inference.py) recipe. Also report the sign. The two-sided test retains the possibility of revealing deterioration in the typical session.

**Rule:** this secondary supports a median improvement only if median delta is positive and its Holm-adjusted p-value across these two secondaries is ≤ 0.05. An adverse result is published with its sign; a positive result does not replace the mean or change the primary. Non-rejection does not demonstrate B2 equal to B1.

## Multiplicity, reading and failures

Nominal p-values use the preceding v4 recipes. A separate multiplicity family is fixed for the two new secondary decisions: Holm at 5% over A's one-sided p-value and B's two-sided p-value. Ordered from smallest to largest, they are compared first with 0.025 and then 0.05, and the sequence stops if the first step fails; a positive sign is additionally required to declare improvement. Adjustment affects only these new secondary decisions and does not alter the primary H1→H2 sequence of v1. No global 5% control is claimed over the union of the primary and both secondaries.

Both secondaries are read even if the primary does not confirm. Searches by asset, horizon or variant are not added as substitutes for these decisions. If a test is not computable, publish that status and do not shrink the multiplicity family: use p = 1 in the unavailable position when adjusting the other, without presenting that administrative value as an estimated p-value. Do not consume another read to obtain a favourable result.

Before the first fit, pin by hash in new files the ablation producer, data manifest, common keys/masks and environment, checking that the reduced model differs only in the four specified columns and indicators. This registration performs no fits, opens no losses and does not implement an automatic evaluation launcher.

## Collector operational correction

Retain the task identity, script, arguments and configuration with SHA-256 `5e6ac9f09c5e2db74cae856f04ec74f5a56e80f3853a82138729d06ddcc160f6`. The action now uses PowerShell installed at the stable system location; the observed version is **7.6.3**. The daily trigger is set to **10:00 civil time in Australia/Sydney**, without a fixed UTC offset in `StartBoundary`. This replaces only the operational 08:00 time documented in v1; the initial cohort remains the XNYS session of 2026-09-08, collected the following day in Sydney.

For an ordinary New York close at 16:00:

| New York / Sydney regime | New York UTC | Sydney UTC | New York time when Sydney is at 10:00 | Margin after close |
| --- | --- | --- | --- | --- |
| EDT / AEST | −4 | +10 | 20:00 the previous day | 4 hours |
| EDT / AEDT | −4 | +11 | 19:00 the previous day | 3 hours |
| EST / AEDT | −5 | +11 | 18:00 the previous day | 2 hours |
| EST / AEST | −5 | +10 | 19:00 the previous day | 3 hours |

Calculation: New York time = 10 − Sydney offset + New York offset, reduced modulo 24; margin = that time − 16. The table covers the four requested offset combinations without asserting that all occur in every year. The smallest margin is two hours and exceeds the registered 30-minute grace period; early closes have more margin.

`WakeToRun=false` and `StartWhenAvailable=true`: the task does not wake the computer and can run when it becomes available again. The collector retrieves only the latest closed session; prolonged sleep or shutdown can leave sessions uncollected and does not amount to automatic backfill. Those absences are recorded according to v1.

The private registration receipt retains actions and before/after state, both `launch.ps1 -DryRun` outputs with exit 0, the executable and the new trigger; this amendment's public receipt fixes its hash without exposing private locations. The task is enabled, but its first real download has not yet occurred. No result from this amendment is available.
