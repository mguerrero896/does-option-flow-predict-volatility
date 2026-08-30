# Future incremental B2 edge route

Status: **DESIGN ONLY - NO CURRENT GLOBAL B2 EDGE.** This document does not authorize
collection or an outcome read. It uses only already released evidence and target-blind
planning quantities; `sealed_cohorts_read=0`.

## Decision first

Do not launch another B2 campaign now. Current evidence does not show that trade-flow
features improve RV30 forecasts beyond contemporaneous option state across model families:

- Phase 8 reports four `Delta B2 given B1` intervals crossing zero and no Holm-adjusted
  p-value below 0.05 for that contrast.
- The preregistered directional extension is `DO_NOT_PURSUE`; its positive estimates do not
  clear their familywise MDE.
- The canonical result state remains `NO_CURRENT_ELIGIBLE_RESULT` while PIT-v2.2
  reconciliation is blocked.

A route can test an edge; it cannot create one or reinterpret these results as favorable.

## Why the existing prospective programs cannot decide this claim

Phase 8 cannot be reopened: its one exploratory read is consumed and its bridge contract
forbids confirmatory promotion or a second read.

Phase 9 cannot establish the incremental claim through its frozen global rule. Its primary
estimand is total contribution, `QLIKE(B0HAR) - QLIKE(B2)`. The B1-to-B2 stage is secondary,
and the `GLOBAL_POSITIVE` decision is defined only for the total contrast. Editing that rule
after collection began would invalidate the protocol hash. A Phase 9 secondary estimate may
inform whether a later, disjoint study is worth launching; it is not that later confirmation.

## Minimum valid sequence

1. **Finish Phase 9 unchanged.** Wait for 60 complete/36 scored sessions and obtain separate
   authority for its single read. Report every sign and retain the frozen total-contribution
   classification.
2. **Apply a launch screen, not a claim.** Continue only if the secondary B1-to-B2 point
   estimate is positive in both registered families. A failed screen means `DO_NOT_PURSUE`;
   no feature or subgroup salvage follows.
3. **Repair eligibility before prediction.** A later study requires a PIT-corrected panel
   whose inputs, availability rules, feature registry and executable closure all pass the
   then-current provenance gate. A blocked or reconciled historical result is not an input
   claim.
4. **Freeze a new protocol before its first outcome.** Its cohort begins strictly after the
   last Phase 9 session used in evaluation. Bind the exact B1 and B2 panel hashes, sessions,
   assets, origins, target, two model families, preprocessing, seed, inference and MDE. The
   same pre-outcome contract must fix the familywise alpha, multiplicity procedure, interval
   level and sidedness, wild-cluster bootstrap weights/repetitions/seed, and the complete
   hypothesis family. An unspecified error budget is not an eligible protocol.
5. **Use one paired incremental estimand.** On identical eligible origins, compute
   `Delta = mean_session[QLIKE(B1) - QLIKE(B2)]`; positive values favor B2. Equal-session
   weighting, clustered inference, Newey-West and 9,999-draw wild-cluster bootstrap remain
   fixed. Missingness cannot change the B1/B2 mask.
6. **Require family agreement.** A global incremental edge requires `Delta > 0`, the lower
   bound from the prospectively frozen interval above zero, and `Delta >= MDE` in both fixed
   log-OLS and LightGBM. Any discordance is `MIXED`; effects below MDE are `DO_NOT_PURSUE`,
   even if nominally positive.

No model selection, feature search, era selection or subgroup promotion may use the future
cohort. Exploratory mechanism work belongs in development and must finish before the new
contract is hashed.

## Power reality

Phase 9's target-blind planning policy gives a recent-regime, nominal-alpha-0.05 MDE of
0.01980 for log-OLS at 36 scored sessions. Under the usual square-root sample-size
approximation,

```text
n_required = ceil(36 * (0.01980 / target_effect)^2)
```

This yields 565 scored sessions for a 0.005 target effect and 142 for 0.010, before missing
sessions, dependence-model error or bootstrap inflation. Retaining Phase 9's stricter
0.008333 alpha approximation raises the 0.005 figure to 906. These are planning
approximations, not observed effects or exact cluster-bootstrap power.

The implication is operational, not cosmetic: detecting a small, model-family-independent
B2 increment is a multi-year collection problem. The economical next action is to finish
Phase 9 without alteration and let its predeclared secondary contrast decide whether sizing
a separate protocol is defensible.

## Evidence boundaries

- Current state: `data/CANONICAL_STATE.json`.
- Phase 8 evidence: `artifacts/phase8_bridge/result_20260830_v1.json` and
  `artifacts/phase8_bridge/dispersion_audit_20260830_v9.json`.
- Directional closeout: `artifacts/rp2_ext1_directional_v2/results.json` and
  `docs/rp2/extension_b2_directional_utility_v2.md`.
- Frozen Phase 9 design: `docs/phase9_total_contribution_protocol_v1.md`.
- Target-blind sizing inputs: `docs/phase9_academic_reporting_policy_v2.md` and
  `artifacts/phase9/power_deadline_audit_v1.json`.

No scientific result artifact is relabeled, regenerated or opened by this design.
