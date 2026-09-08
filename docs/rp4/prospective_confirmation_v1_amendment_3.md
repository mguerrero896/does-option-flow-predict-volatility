# Prospective v4 replication — amendment 3 to registration v1

**English translation. Historical seals refer to the preserved original bytes.**

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.

**Local seal: 2026-09-08T06:56:21.897094+00:00.** This amendment is pre-declared and sealed locally, without a third-party timestamp, before the first scheduled acquisition: **2026-09-09 at 10:00 Australia/Sydney**. The collector observation before sealing shows the task enabled, with no recorded execution and no acquisition directory. No prospective data were acquired or read to prepare this amendment. This is evidence of the local state, not a claim about every person's knowledge. See the [receipt](prospective_confirmation_v1_amendment_3_receipt.json) and [sidecar](prospective_confirmation_v1_amendment_3.sha256).

## Complete seal chain

| Document | UTC seal | Document SHA-256 |
|---|---|---|
| [v1](prospective_confirmation_v1.md) | 2026-09-08T04:24:01.918499+00:00 | `317530c37d2785bb0ce0bfd6a947fc034c78a02bbd5bb102fd17efe8f91b977d` |
| [Amendment 1](prospective_confirmation_v1_amendment_1.md) | 2026-09-08T04:31:58.752153+00:00 | `036f81894975a1e452fb2817c7f3989ed89dd6fe601a9378587d70559d3c7bb3` |
| [Amendment 2](prospective_confirmation_v1_amendment_2.md) | 2026-09-08T05:27:15.316335+00:00 | `b545c36faa4a48764a3433b008d859780a2116f5275a8553b95765d3a2d50cf9` |

None of those documents, receipts or hashes is edited. The initial v1 schedule is a historical antecedent; amendment 1 records the current 10:00 schedule. This amendment changes the scope labels and adds a cumulative read; it changes no previously written rule and creates no new scientific specification.

## Planning power, calculated before acquisition

Only the estimands and intervals from the [historical RV15 summary, primary window](../../artifacts/rp4_v4_b2_rv15/summary.json), SHA-256 `451e53869bb5f5058a635302bb08ad920ce11b8771fd2c6780545255b1ac25f4`, are used. No bootstrap is rerun and no model is fitted. A standard error is approximated from the width of the saved percentile interval; no saved bootstrap power distribution is available here.

For linear H2 B2/B1, with 419 sessions, delta = 0.0011337596590923558 and 95% CI [0.00033503697025205506; 0.0019321615865300122]. With standard-normal Φ, SE419 = (upper CI − lower CI)/(2 × Φ⁻¹(0.975)) = 0.000407437235805319; delta/SE419 = 2.7826608848143843. Assume SE(n) = SE419 × √(419/n) and marginal power = Φ(delta/SE(n) − Φ⁻¹(0.95)). Apply the same approximation separately to H1's saved CI.

| Assumed sessions | Marginal H2 power | Marginal H1 power | Role |
|---|---:|---:|---|
| 20 | 14.99% | 11.27% | Early primary consistency |
| 40 | 21.62% | 15.08% | Cumulative stability |
| 45 | 23.18% | 15.96% | Hypothetical scenario; D is not independent |
| 120 | 43.81% | 27.91% | Planning only, no read |
| 146 | 49.91% | 31.69% | Planning only, no read |
| 335 | 80.05% | 54.98% | Final cumulative read; 80% applies only to H2 |

The values 120 and 146 are planning scenarios: **they do not authorise reads**. The row for 45 hypothetically assumes 45 new sessions from a stable distribution; **it does not estimate the conditional power of D**, which contains 25 already observed sessions and only 20 new ones. No justified power estimates are available for ablation A or Holm-adjusted secondaries B/C; they are declared unavailable and are not assigned H2's power.

As a sensitivity for a different estimand, a one-sided binomial sign test at 5%, under independent signs with positive probability 0.59, has exact power 10.79% with 20 sessions and 27.95% with 45. Using the exact historical frequency 249/419, these values are 11.52% and 29.95%. This calculation registers no additional test, is not the power of the paired-bootstrap median and replaces no decision. Independence of signs is an assumption of the sensitivity, not a demonstrated property of these sessions.

**The reads at 20, 40 and 45 are consistency checks with limited power, not tests designed for high power.** At 335 sessions, 80.05% applies exclusively to isolated H2; H1 reaches approximately 54.98%. Joint H1→H2 power cannot exceed the smaller marginal power, approximately 54.98% under these approximations. Power of 80% to confirm the entire hierarchy has not been demonstrated.

The width of a percentile CI is not an exact normal standard error, and that CI does not invert the registered centred p-value. Scaling assumes an effect, long-run variance, dependence and composition comparable to history. The effect was estimated after adaptations on an observed sample and may be optimistic; regime or learning changes would invalidate extrapolation. Only four five-session block lengths fit within 20 sessions: this calculation does not validate the bootstrap's finite-sample size or power. These figures are planning sensitivities, not verified probabilities of future success.

## Earlier reads: rules and verdicts retained

- **20 prospective:** early consistency read, with the original primary intact: linear RV15 family, H1 B1/B0 followed by H2 B2/B1, both with a positive estimand and one-sided p ≤ 0.05; H2 opens only if H1 rejects. Its verdict is retained literally, favourable or adverse. A, B, C and D are read once only on completing these 20, even if the primary fails, according to amendment 2.
- **40 prospective:** a single cumulative stability read if the original calendar permits; it does not rescue the primary or repeat A/B/C/D.
- **45 pooled:** consistency secondary D, formed by the 25 historical and first 20 prospective sessions; it retains equal weight per session, its own nominal sequence and its partly observed status. It is not an independent replication and does not rescue the primary.

A/B/C retain the three-member Holm family and D its separate sequence. Neither p-values, thresholds, estimands nor the sample of one read change according to the result of another.

## New final read, once only on completing 335 prospective sessions

The read is now fixed to **the first 335 eligible prospective sessions**, in chronological order and under the complete v1 eligibility rules. It is cumulative and includes the sessions of the early reads; it does not incorporate D's 25 historical sessions. It is executed once only upon reaching the fixed number, regardless of what earlier reads showed. The indicative calendar is approximately January 2028, conditional on eligible sessions and continuous acquisition; the date does not determine the sample, and delay does not permit substitution or session selection.

The same v4 specification is retained: B0 ⊂ B1 ⊂ B2, families, transformations, common mask, causal temporal selection and expanding training; primary RV15 and secondary RV5. The registered decision for this read applies exclusively to the linear RV15 family: **H1→H2 at one-sided 5%, both with a positive estimand and p ≤ 0.05; H2 opens only after H1 rejects in the same sample**. Use the already registered recipe: circular session bootstrap, five-session blocks, 9,999 resamples, seed 20260907, centred null, +1 correction and two-sided 95% percentile CI. This amendment does not extend the A/B/C/D reads to 335.

Nominal support for the sequence at the final read will be published only if both steps reject. If H1 fails, H2 remains nominal and unopened; if coverage is missing or inference is not computable, record that limitation without substitutions or repetition. Final success does not rewrite or rescue the verdict at 20. **There is no rule defining success by rejection at either of the two reads.** The 5% thresholds apply per read; no global 5% control is claimed across cumulative reads, secondaries or historical search. The reads share data and are not independent replications.

**No additional intermediate read is permitted**: 120 and 146 are not inspection points; 45 is D on reaching 20 prospective sessions, not a read of 45 prospective sessions. Acquisition monitoring is limited to availability, integrity and eligibility, without looking at losses, effects or p-values outside registered reads. There is no rescue, optional stopping based on results or new specification after an adverse result. Limitations on temporal availability as a proxy, causality and profitability remain intact.
