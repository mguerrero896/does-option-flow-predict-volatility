# What the B2 improvement does—and does not—identify

**Status: CURRENT.** This note interprets published aggregates. It reports no new
fit, cohort read, inferential test or ablation. [Current evidence](CURRENT.md)
retains the registered historical decisions.

## 1. B2 is a heterogeneous information block

The [frozen predictor specification](../artifacts/rp4_v4_a1/specification.json)
contains 29 B0, 69 B1 and 138 B2 predictors, before model-specific indicators and
asset effects. The set difference `feature_sets.B2 - feature_sets.B1` has **69
additional columns**. “Flow” is a short label for this implemented block, not an
isolated measure of informed trading.

| Information represented | Examples from the frozen specification |
| --- | --- |
| Activity and composition | `b2_5m_trades`, `b2_30m_rate_per_second`, `b2_5m_buy_premium_share`, `b2_30m_zero_dte_premium_share` |
| Changes in option state/prices | `b2_5m_d_iv`, `b2_30m_d_mid_rel`, `b2_30m_d_spread` |
| Exposure and directional proxies | `rp4_dealer_gamma_net`, `rp4_gamma_imb_total`, `b2_5m_vega_flow` |
| Empty-window/data representation | `b2_5m_window_empty`, `b2_30m_window_empty`; the specification's `empty_window_addendum` and presence encoding |

These examples are not a newly frozen feature partition. Related fields can share
information. `rp4_gamma_imb_signed_trades` counts trades with identifiable direction;
it is not net signed buying. Exposure proxies are not observed dealer inventories
or a causal measure of dealer hedging. A B2/B1 comparison measures incremental
predictive performance beyond **this B1 representation**, not the unique economic
contribution of each component. [Coefficient audit](../artifacts/rp4_closeout_audit/REPORT.md)
is descriptive, not a substitute for ablation.

The [registered prospective ablation](rp4/prospective_confirmation_v1_amendment_1.md)
removes only four `gamma_imbalance.columns` and their presence indicators; the
three `dealer_columns` remain. Its [current secondary rules](rp4/prospective_confirmation_v1_amendment_2.md)
and reading restrictions remain unchanged. It cannot separate every component
above, and this note reports no result from it.

## 2. Final-window concentration is not historical-wide concentration

The [saved statistics](../artifacts/rp4_v4_b4/primary_statistics.csv) show that
neither family passes H1 in the 25-session final historical window: linear
`p=0.3908`, LightGBM `p=0.0568`. Both H2 gates are closed. Linear H2's nominal
`p=0.1758` and +1.997% point gain do not confirm the sequence or establish a zero
effect. The historical file label `confirmation` does not imply independent
prospective confirmation.

The [25 saved session losses](../artifacts/rp4_v4_b3_rv15/session_losses.csv)
give a cumulative linear B2/B1 loss difference of **0.11918283137061729**;
2026-08-31 contributes **0.11624790425816478**. Dividing the latter by the former
and multiplying by 100 gives **97.537458% (97.54%)**. The remaining 24 sum to
0.00293492711245251. This is concentration of a **signed net gain**, not a causal
decomposition or a new analysis excluding a selected shock.

The [419 development session losses](../artifacts/rp4_v4_b2_rv15/session_losses.csv)
tell a different story. Write `d_s = loss_B1,s - loss_B2,s` and `b_s = loss_B1,s`.
For each omitted session `j`, the descriptive percentage is
`100 * (sum(d_s) - d_j) / (sum(b_s) - b_j)`.
Its range is **0.543199789% to 0.706946107%**, positive for every individual
omission. These calculations reuse saved losses without refitting models or
recomputing p-values; they do not test removing a session from training. They
show that the extreme final-window concentration cannot fairly be attributed to
the entire development result. Neither diagnostic proves future stability.

## 3. Availability assumptions are not observed delivery latency

| Assumed source-time cutoff | Linear B2/B1 QLIKE reduction | Nominal p-value |
| --- | ---: | ---: |
| 60 seconds | 1.447% | 0.0001 |
| 120 seconds, primary | 0.623% | 0.0032 |
| 300 seconds | 0.194% | 0.1948 |

Sources: [60/120-second contrasts](../artifacts/rp4_robustness_public_v1/pit_60_contrasts.csv),
[300/120-second contrasts](../artifacts/rp4_robustness_public_v1/pit_300_contrasts.csv)
and [denominators and complete table](CURRENT.md). Option-state gains remain
approximately 0.84–0.91%. Each percentage uses its own cutoff's baseline mean loss.

These cuts are applied to source timestamps, not measured client receipt times.
The ordering is descriptive; it is neither a causal estimate of value lost per
second nor a statistical test comparing cutoff effects. The precise conclusion
is: **the estimated historical B2 contribution is sensitive to the assumed
availability cutoff**. The 60-second result cannot strengthen the registered
finding by assuming information arrives earlier. Historical receipt remains
unobserved; forecast-loss improvement is not trading value.

## 4. The placebo does not isolate timely information

The [completed placebo](rp4/robustness_committed_v1_placebo_linear_rv15.md)
jointly shuffled the 69 additional columns within each asset-session. Mean gain
was 0.0009255190521628708 versus observed 0.0011337596590923558 QLIKE units:
**81.63%** survives. Twelve of 50 permutations exceed the observed gain;
the plus-one empirical p-value is `(12+1)/(50+1) = 0.25490196`.

The control does not show that correctly timed flow beats the shuffled block.
Nor does it show that 81.63% is an exploitable daily signal or a causal fraction.
A whole-session shuffle can move information from after a forecast origin to
before it; it is a negative control, **not an implementable real-time predictor**.
Non-rejection does not prove all temporal information absent.

## What would resolve the remaining questions?

**Proposed, not executed or authorized by this note:** extend the
[existing research priorities](rp4/PROSPECTIVE_RESEARCH.md) with a frozen broad
ablation of activity/composition, option-price changes, exposure proxies and
coverage representation. Correlated blocks may substitute for one another;
removal contrasts do not necessarily identify a unique source. This proposal
does not amend the narrower registered gamma-block ablation.

A useful timing comparison would pit complete B2 against simpler controls whose
inputs are available by the same origin/cutoff:

- Activity accumulated only up to the eligible cutoff, never the full session.
- Fixed prior-window summaries ending before that cutoff.
- Summaries of preceding completed sessions, with explicit availability rules.

Before any evaluation, fix feature definitions, eligibility and receipt/source
assumptions, common evaluation keys, training-only transformations, model
selection, estimands and multiplicity. Report all registered comparisons,
including adverse ones. No new observations, inferential results or independent
reproduction are supplied by an editorial correction.

Research only. Not investment advice.
