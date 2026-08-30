# Phase 8A exploratory bridge addendum v6

**Evidence date:** 2026-08-30  
**Classification:** `MIXED_EXPLORATORY`  
**Claim boundary:** `EXPLORATORY_DESCRIPTIVE_NOT_CONFIRMATORY`  
**Current authority:** This addendum supersedes v5 for the Phase 8A interpretation. The
v1–v5 paths remain frozen as audit evidence.

This addendum reports the sole Phase 8A read under
`phase8a-exploratory-bridge-20of30-v2`, contract SHA-256
`b383ef36210f3f0c2d38b55f97e3ee0cc85fabc1c357f18be54a534982e0801e`.
The atomic claim advanced `sealed_cohorts_read` from 0 to 1. No second execution or
sealed-store read is permitted.

## Primary result

Positive deltas mean that the expanded information set reduced QLIKE relative to its
base. The primary window contains 20 strictly unobserved sessions. Intervals are the
registered studentized wild-cluster bootstrap intervals; Holm p-values are descriptive
within each model's five-contrast family.

| Role | Model | Δ total (95% CI) | Holm p | ΔB1 (95% CI) | Holm p | ΔB2\|B1 (95% CI) | Holm p |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| D | Gamma GLM | 0.001723 (−0.004424, 0.008023) | 0.9802 | 0.002615 (−0.003147, 0.008357) | 0.9802 | −0.000892 (−0.002096, 0.000325) | 0.5756 |
| D | LightGBM | 0.010459 (0.001514, 0.019479) | 0.0276 | 0.003000 (0.001295, 0.004786) | 0.0050 | 0.007459 (−0.001343, 0.016246) | 0.3940 |
| V | Gamma GLM | 0.003398 (0.000742, 0.006103) | 0.0130 | 0.003386 (0.000636, 0.006179) | 0.0208 | 0.000012 (−0.000387, 0.000412) | 0.9528 |
| V | LightGBM | 0.004369 (−0.000567, 0.009304) | 0.3704 | 0.006203 (0.002401, 0.010003) | 0.0040 | −0.001834 (−0.006532, 0.002725) | 1.0000 |

All four ΔB1 estimates are positive, and three of four have descriptive Holm p-values
below 0.05. ΔB2 conditional on B1 has mixed signs; all four intervals cross zero and all
four Holm p-values exceed 0.39. The prospective contribution is concentrated in the B1
option-state block. These data do not establish an incremental B2 flow contribution.

The exact four cells, two windows and five registered contrasts remain in
`artifacts/phase8_bridge/result_20260830_v1.json`. No causal, universal, confirmatory,
formal-equivalence, profitability or trading claim follows from this result.

## Dispersion and the registered MDE

An observed effect below a registered MDE can have a descriptive p-value below 0.05. The
MDE is the ex-ante effect size that gives 80% power at the contract's one-sided
`alpha = 0.005`; it is not a minimum significance threshold. The contract calibrates each
D/V and model cell separately. Its multiplier is
`z(0.995) + z(0.80) = 3.41745`, not the alpha-0.05 approximation 2.954.

The intervals are studentized bootstrap intervals and are asymmetric. Their widths do not
identify a normal-theory standard error. The direct Phase 8 standard error is the sample
standard deviation of the 20 session means divided by `sqrt(20)`.

| Role | Model | ΔB1 | MDE n=20 | Effect/MDE | Phase 8 σ | Phase 8 SE | Contract σ / Phase 8 σ | Current D/V σ / Phase 8 σ |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| D | Gamma GLM | 0.002615 | 0.013975 | 0.19 | 0.013891 | 0.003106 | 1.32 | 0.56 |
| D | LightGBM | 0.003000 | 0.014645 | 0.20 | 0.003803 | 0.000850 | 5.04 | 1.71 |
| V | Gamma GLM | 0.003386 | 0.007664 | 0.44 | 0.007378 | 0.001650 | 1.36 | 1.38 |
| V | LightGBM | 0.006203 | 0.018778 | 0.33 | 0.008672 | 0.001939 | 2.83 | 2.41 |

The three cells with ΔB1 Holm p below 0.05 have lower Phase 8 session dispersion than both
references. Relative to the current same-estimator D/V reference, the standard-deviation
reductions are 1.71-fold for D/LightGBM, 1.38-fold for V/Gamma GLM and 2.41-fold for
V/LightGBM. D/Gamma GLM is the exception: Phase 8 is noisier than its current D reference,
and that cell is not significant.

The contract reference is the frozen 2026-08-18 Block 12 design. It uses the same QLIKE
estimand and equal-session aggregation, but its producer and D/V panel bytes predate the
Phase 8 preprocessing and model-selection pipeline. The design output remains
hash-verifiable. The public root retains only a recorded producer commit and digest; those
producer bytes and the historical panel bytes are not available, so the historical
producer identity cannot be independently rehashed from this checkout.

The second comparison remeasures the current RP2-v3 D/V panels through a verified 126-file
executable closure. The closure contains
`scripts/rp2_block12_prospective_design.py`, the complete importable `src/mds650` tree
and `uv.lock`; its aggregate SHA-256 is
`939a238b1ff703e57b597582bca24205bf8e2b947227e264fcc0140fb08dd95d`.
The closure is checked before measurement and recorded with every file digest.

The pointer manifest is independently pinned at SHA-256
`2bf6a92c8ae46bbca56f4ce8e7943ed13abd04f91c2aa7f37f33b740b315e125`.
The B0, B1 and B2 panel hashes are fixed in the producer and must equal both the manifest
and the supplied bytes. The Phase 8 result, contract and Block 12 design files are also
checked against fixed file digests before parsing; the result and contract semantic
self-hashes are then verified. The D/V evaluation tails contain 156 D sessions and 32 V
sessions.

The measured resolution is narrower than “a calmer market.” Phase 8 has lower realized
session dispersion in every descriptively significant ΔB1 cell. The data do not identify
whether market regime, fitted-model behavior or both caused that reduction.

## Aggregation and execution custody

The audit reads only the materialized forecast cube pinned at SHA-256
`71e1ccf9a4970fc6053a0204ce4981634dc9fc1ba3637d093e0b76ed9fd19002` and
the D/V panels. It does not open the sealed store. The cube has 190,000 rows, no nulls and
no duplicate forecast keys. Each primary cell has 7,917 origins, with 395–396 origins per
session.

Replaying the registered QLIKE calculation, within-session mean, equal-session weighting,
studentized bootstrap and Holm adjustment reproduces all 20 primary contrast rows and all
140 published fields exactly. The recovery did not change the aggregation or narrow the
reported intervals. The aggregation-change hypothesis is not supported.

The frozen evaluator still did not complete an uninterrupted end-to-end run: recovery
used a script outside the frozen executable closure. That engineering deviation remains
part of the claim boundary. It is distinct from interval calibration and does not explain
the three ΔB1 cells.

The machine-readable comparison is
`artifacts/phase8_bridge/dispersion_audit_20260830_v5.json`. Its writer refuses any
registered output path. The artifact records both D/V references, the verified current D/V
executable closure, fixed source identities, the exact replay, the unresolved
historical-producer identity, the unavailable historical panel bytes and
`sealed_store_reopened = false`.
