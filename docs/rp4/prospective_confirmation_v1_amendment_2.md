# Prospective v4 replication — amendment 2 to registration v1

**English translation. Historical seals refer to the preserved original bytes.**

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.

**Local seal: 2026-09-08T05:27:15.316335+00:00.** This amendment is added before the collector's first scheduled execution, **2026-09-09 at 10:00 Australia/Sydney**. The local observation before sealing shows the task enabled, with no recorded execution or acquisition directory; no prospective data have been acquired or read by this task. The [receipt](prospective_confirmation_v1_amendment_2_receipt.json) and [sidecar](prospective_confirmation_v1_amendment_2.sha256) pin this evidence. The seal is local, not independent time certification.

## Seal chain and primary rule

[v1](prospective_confirmation_v1.md), sealed at **2026-09-08T04:24:01.918499+00:00**, retains SHA-256 `317530c37d2785bb0ce0bfd6a947fc034c78a02bbd5bb102fd17efe8f91b977d`. [Amendment 1](prospective_confirmation_v1_amendment_1.md), sealed at **2026-09-08T04:31:58.752153+00:00**, retains SHA-256 `036f81894975a1e452fb2817c7f3989ed89dd6fe601a9378587d70559d3c7bb3`. Both documents and their receipts remain intact.

**The primary does not change:** first 20 complete prospective sessions, linear family, RV15, one-sided H1→H2 sequence at 5%, positive estimates and H2 opened only after H1 rejects in that same family and sample. RV5 remains secondary. The cumulative 40-session read retains only its stability role; it does not rescue the primary or repeat the secondary decisions registered here.

This amendment adds two secondary analyses. To retain the previous names, A is the ablation and B the median from amendment 1; C is the new trimmed mean and D the new pooling. **A, B, C and D are read once only on completing the first 20 prospective sessions**, even if the primary does not confirm. They are neither available results nor a v5.

## Secondary D — pooled post-split read

The sample concatenates the **25 historical confirmation sessions, 2026-08-03–2026-09-04**, and the **first 20 complete prospective sessions** of v1: **45 sessions**. The 25 historical sessions have already been observed and motivate part of this analysis; pooling is therefore secondary and not an independent replication. A favourable result does not turn that earlier information into unknown information or rescue primary prospective confirmation.

Reuse literally the linear B0/B1/B2 RV15 session losses saved in [the historical aggregate](../../artifacts/rp4_v4_b3_rv15/session_losses.csv), SHA-256 `d3efc32f62b82feb581d38ec410290c2a421fd80642d3d69024d9ac3c997f231`. Do not refit historical models, change predictions, reopen v3/v4 or recalculate their p-values. Prospective losses will come from the already registered v4 procedure with the same sets, transformations, temporal selection, seeds and masks; this registration does not execute that procedure.

Concatenate historical and prospective rows by market session with unique keys, time order and no overlap. Require the same v4 aggregation: average origins within asset/session, equal average across assets and then equal weight per session. Each of the 45 sessions therefore weighs 1/45; half the weight is not assigned to each window. Retain the observed calendar, including disclosed gaps, without inventing intervening sessions. Before opening the read, seal the new losses, their keys, the union and the environment; incomplete coverage is not replaced with a sample selected by losses.

Apply a single sequence H1: B1/B0 → H2: B2/B1 in the **linear family at 15 minutes** over those 45 rows. Delta is baseline minus expanded-model loss. Retain the v4 circular session bootstrap: five-session blocks, 9,999 resamples, seed 20260907, one-sided p-value with a centred null and +1 correction and two-sided 95% percentile CI. H1 must have a positive mean and p ≤ 0.05; only then is H2 decided under the same conditions. If H1 does not reject, retain H2's p-value exclusively as unopened nominal evidence.

**Pooled secondary decision:** report support for the hierarchy in the pooled sample only if both steps reject within this same family, horizon and sample. D retains its own sequence at 5%; it does not belong to Holm A/B/C. No global 5% control is claimed over D, A/B/C, the primary or historical search. If the union or inference is not computable, record it as unverifiable without excluding days, repeating the read or changing the criterion.

## Secondary C — paired trimmed mean for trees

Use LightGBM B1 and B2 at RV15 on the same **20 complete prospective sessions**. Each session's delta is B1 QLIKE minus B2 QLIKE after the same asset/session aggregation. The estimand is the **mean of the paired-delta vector trimmed by 5% at each tail**, not a difference between separately trimmed means or a selection of shock dates.

Retain the `trimmed_mean_5pct` recipe from the [inherited v4 producer](../../artifacts/rp4_v3_code/inference.py): sort deltas and remove `floor(0.05 × N)` from each end. With N = 20, remove one observation per tail and average the remaining 18. Apply exactly the same rule in each resample, with circular five-session blocks, 9,999 resamples and seed 20260907. The p-value is two-sided with the resample centred relative to the observed statistic and +1 correction; the CI is a two-sided 95% percentile interval. Trimming was fixed before observing these sessions; retrospective diagnostics are not used to choose days to remove.

**Decision C:** support a trimmed improvement only if the estimand is positive and its Holm-adjusted p-value alongside A and B is ≤ 0.05. A favourable median or trimmed mean does not replace the primary mean or demonstrate absence of tail risk. Publish the effect, CI, nominal and adjusted p-values and trimmed count; report a computational failure without repeating the analysis.

## Explicit update to secondary multiplicity

The nominal recipes of A (one-sided mean) and B (two-sided median) are retained. **Only their two-member Holm family is replaced by the three-member A/B/C family**, before the first prospective acquisition. Amendment 1 remains sealed as the antecedent; its text is not edited.

Order the three p-values, including unavailable positions, and apply the exact thresholds 0.05/3, 0.05/2 and 0.05, stopping at the first non-rejection. Adjusted p-values are the cumulative maximum of ordered p-values multiplied by 3, 2 and 1, capped at 1. A positive sign is additionally required to declare improvement in any of A/B/C. A non-computable p-value retains its position with administrative value 1 for adjustment, without publication as a scientific estimate. The family is not reduced based on the result, no contrast is added after looking, and there is no second A/B/C read at 40 sessions.

The producer, data union and their hashes will be fixed in new files before any authorised fit or read. This amendment registers rules; it performs no fits, resampling or evaluations. It retains the v1 and v4 restrictions on coverage, missing data, temporal availability as a proxy, and absence of causal or profitability inference.
