# Linear RV15 placebo: result and interpretation

**Status: CURRENT.** Read [current scientific evidence](../CURRENT.md) for the
unchanged primary decision and the wider limitations. This is committed
post-primary robustness evidence, not independent prospective confirmation.

## Method and scope

The completed control jointly shuffles the 69 additional B2 columns, including
nulls and indicators, within each asset-session. This preserves their joint
within-session distribution but breaks alignment with forecast origins; it does
not preserve the exact conditional profile by minute of day. B0/B1, targets and
the comparison mask remain unchanged. Shuffling applies to training, validation
and evaluation; it is a negative control, not an implementable real-time predictor.

The family is `log_ridge_harq`, horizon RV15. Each of 50 permutations uses 419
primary sessions and 160,832 origins, from 2024-10-28 through 2026-07-31. The
recorded seeds are `20260908 + k`, for `k=0,...,49`, using PCG64. B2 was refitted
under the recorded chronological rules; observed forecasts were reused. This
publication does not repeat those fits or permutations.

The measured increment is mean QLIKE(B1) minus mean QLIKE(B2), in realized
variance without annualization. Positive values favor B2. Losses are averaged
within asset-session, then equally across assets and sessions.

## Saved results

| Measure | Value |
| --- | ---: |
| Observed increment | 0.0011337596590923558 |
| Completed permutations | 50 |
| Placebo mean | 0.0009255190521628708 |
| Placebo median | 0.0009321480381643524 |
| Sample standard deviation | 0.000250351849242259 |
| Minimum / maximum | 0.00028114413787626996 / 0.001287204999106369 |
| 2.5th / 97.5th percentiles | 0.0004563956748538585 / 0.0012831122415478523 |
| Exceedances / ties | 12 / 0 |
| Empirical p-value | 13/51 = 0.2549019607843137 |
| Ascending observed rank, including observed | 39/51 |

The rule counts placebo increments greater than or equal to the exact observed
increment, with a plus-one correction. All twelve exceedances are strict here.
The percentiles describe the placebo distribution, not a confidence interval for
the observed effect.

The placebo mean divided by the observed increment is 0.8163273800937719:
81.63%, approximately 82%. Their difference is 0.00020824060692948502 QLIKE.
These are descriptive contrasts, not a causal decomposition. Most of the gain
survives the shuffle, consistent with session-level information; timely order
flow beyond this control is not demonstrated. Non-rejection does not establish
the absence of all temporal information. The registered H1/H2 decision is unchanged.

## Provenance and limits

The [import receipt](../../artifacts/rp4_robustness_public_v1/import_receipt.json)
records the closed source status, original/public hashes and this report's source
identity. The [summary](../../artifacts/rp4_robustness_public_v1/placebo_log_ridge_harq_rv15_summary.csv),
[50 draws](../../artifacts/rp4_robustness_public_v1/placebo_log_ridge_harq_rv15_draws.csv)
and [20,950 session deltas](../../artifacts/rp4_robustness_public_v1/placebo_log_ridge_harq_rv15_session_deltas.csv)
support public arithmetic checks. The source summary records 6,431 legacy and
14,519 Gram units; the final execution receipt records 19,407 reused units and
1,543 new units, not the cost of the entire study.

This is a condensed English public derivative of the source report, not its
original bytes. Private execution paths and unavailable local links are omitted;
the interpretation explicitly avoids causal attribution. Original protocol/code
hashes remain recorded provenance, not proof of licensed reproduction in a public
clone. Public checks do not revalidate every private checkpoint or rerun the
scientific execution.

Only the linear RV15 placebo is closed here. RV30 and tree placebos and
point-in-time sensitivity at 300 and 60 seconds are not certified by this result.
It establishes neither historical client receipt nor economic usefulness.

Research only. Not investment advice.
