# Phase 8A exploratory bridge addendum

**Evidence date:** 2026-08-30  
**Classification:** `MIXED_EXPLORATORY`  
**Claim boundary:** `EXPLORATORY_DESCRIPTIVE_NOT_CONFIRMATORY`

This addendum reports the sole Phase 8A read under
`phase8a-exploratory-bridge-20of30-v2`, contract SHA-256
`b383ef36210f3f0c2d38b55f97e3ee0cc85fabc1c357f18be54a534982e0801e`.
The owner authorization is
`phase8a-one-shot-4e7c4139-97bd-4d60-8ad7-29a87da8cf75`. The atomic claim was
recorded at 2026-08-29T14:55:12Z and advanced `sealed_cohorts_read` from 0 to 1.
No second execution or sealed-store read is permitted.

## Result

Positive deltas mean that the expanded information set reduced QLIKE relative to its
base. The primary window contains the 20 strictly unobserved sessions. Intervals are the
registered wild-cluster bootstrap intervals; Holm p-values are descriptive.

| Training role | Model | Δ total (95% CI) | Holm p | ΔB1 | ΔB2\|B1 | Cell label |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| D | Gamma GLM | 0.001723 (−0.004424, 0.008023) | 0.9802 | 0.002615 | −0.000892 | `IMPRECISE_EXPLORATORY` |
| D | LightGBM | 0.010459 (0.001514, 0.019479) | 0.0276 | 0.003000 | 0.007459 | `DIRECTIONALLY_SUPPORTIVE_EXPLORATORY` |
| V | Gamma GLM | 0.003398 (0.000742, 0.006103) | 0.0130 | 0.003386 | 0.000012 | `DIRECTIONALLY_SUPPORTIVE_EXPLORATORY` |
| V | LightGBM | 0.004369 (−0.000567, 0.009304) | 0.3704 | 0.006203 | −0.001834 | `IMPRECISE_EXPLORATORY` |

All four primary total estimates are positive, but only two intervals exclude zero. B1 is
positive in all four primary cells. The incremental B2 estimate conditional on B1 is
positive in two cells and negative in two, and every primary interval for that contrast
crosses zero. The 30-session sensitivity window retains a mixed pattern. The evidence is
consistent with an exploratory option-state contribution concentrated in B1; it does not
establish a stable incremental B2 contribution.

The exact four cells, two windows and five registered contrasts are published in
`artifacts/phase8_bridge/result_20260830_v1.json`. No causal, universal, confirmatory,
formal-equivalence, profitability or trading claim follows from this result.

## Execution custody and limitation

The frozen evaluator created the one-shot claim and then stopped with
`RP3_EVAL_NO_SESSIONS`, caused by asset-partitioned materialization not matching direct
date discovery. Recovery reused the materialized bytes without reopening the sealed store.
It applied the six compatibility controls recorded in
`artifacts/phase8_bridge/execution_recovery_20260830_v1.json`, then ran the frozen scoring
logic. The forecast cube contains 190,000 rows across 30 sessions with no nulls; independent
recomputation matched all 16 loss hashes and all 40 contrast statistics.

The recovery means the frozen executable did not demonstrate an uninterrupted end-to-end
run. This engineering deviation is part of the evidence boundary and cannot be removed by
the favorable cells. The aggregate result remains exploratory and descriptive. The
granular forecast cube stays outside public Git as private gated evidence, pinned by SHA-256
`71e1ccf9a4970fc6053a0204ce4981634dc9fc1ba3637d093e0b76ed9fd19002`.
