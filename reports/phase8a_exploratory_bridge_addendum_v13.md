# Phase 8A exploratory bridge addendum v13

**Evidence date:** 2026-08-31

**Classification:** `MIXED_EXPLORATORY`

**Claim boundary:** `POST_HOC_REMEDIATION_SENSITIVITY_NOT_CONFIRMATORY`

**Current authority:** This addendum supersedes v12 for the current Phase 8A
interpretation. The historical one-shot result and addenda v1–v12 remain immutable audit
evidence; this sensitivity does not replace or promote them.

## Decision first

The remediation improves the validity of Phase 8, not its absolute predictive score. On
the paired primary grid, only one of eight B1-inclusive role/model/information-set cells
has lower QLIKE after correction. The result is therefore `MIXED`, not a general forecast
improvement.

The scientific pattern nevertheless survives the repair. All four primary ΔB1 estimates
remain positive and three of four have descriptive Holm p-values below 0.05. Every
ΔB2 conditional on B1 interval crosses zero and none has a descriptive Holm p-value below
0.05. The evidence still locates the prospective contribution in the B1 option-state
block, not in an established incremental B2 flow effect.

## What was regenerated, and what was not

The frozen 2026-08-30 evaluator used contemporaneous underlying `close[m]` while its
option snapshot admitted information only through `t−120s`. The corrected producers use
the last start-labelled one-minute close available at that cutoff, `close[m−3]`, for both
B0 and B1. A replay of the historical forecast cube cannot apply that change because the
cube stores targets and forecasts, not the underlying B0/B1 feature rows.

Under the owner's 2026-08-31 direction, the project therefore performed an append-only
post-hoc reconstruction from the already materialized Phase 8 bytes:

- the same 30 sessions and the same six target assets;
- zero newly collected Phase 8 sessions;
- zero sealed-store reads and `sealed_store_reopened = false`;
- the same D/V training roles, Gamma GLM and LightGBM families, four information sets,
  twenty-session primary window, thirty-session sensitivity window and registered
  inference;
- the same five target-blind D/V warm-up sessions used by the historical recovery, only
  to initialize lagged features, with zero warm-up rows written or scored as Phase 8; and
- no tuning, subgroup selection or model fitting on Phase 8 targets.

The canonical one-shot read counter remains one. This is not a second canonical read or a
new confirmation exercise; it is a labelled post-hoc sensitivity over bytes that had
already been materialized by the consumed read.

## Coverage is not one number

Source completeness is full for this reconstruction: all 180 session-assets have tape and
bar grids. Across the ten B1 core features, the minimum current-grid finite coverage is
11,664/11,700 = 99.6923% (`b1_risk_reversal_25`); every other B1 core feature is finite on
all 11,700 origins. All twelve B2 core features are finite on all 11,700 origins, B2 has
no provider failure and those values are exactly equal to historical B2 on the paired grid.

The current origin grid is deliberately smaller than the historical grid. It has 11,700
origins versus 11,875 historically: 175 historical `origin_minute = 30` rows, or 1.47%,
are removed because a full trailing thirty-minute B0 window does not exist at the
`t−120s` as-of point. There are no remediated-only origins, and `rv30` is exactly equal on
all 11,700 paired keys. This is stricter admissibility, not loss of source coverage.

The directional factorial's “complete coverage” is a separate experiment. It adds rows
only in D; August and complete coverage have identical V masks. Its normalized treatment
effect is 0.405476 versus 0.037680 for coverage, a 10.76 ratio. Those cells cannot be used
to claim that Phase 8 forecast QLIKE improved.

## Paired primary QLIKE

The table compares the historical and remediated forecasts only on the 11,700 common
origin keys. `Historical − remediated > 0` means the remediation lowered QLIKE.

| Role | Model | Information set | Historical QLIKE | Remediated QLIKE | Historical − remediated | Improved |
| --- | --- | --- | ---: | ---: | ---: | --- |
| D | Gamma GLM | B0+B1 | 0.141036946 | 0.146485986 | −0.005449040 | No |
| D | Gamma GLM | B0+B1+B2 | 0.141937123 | 0.147124381 | −0.005187258 | No |
| D | LightGBM | B0+B1 | 0.131287263 | 0.135277725 | −0.003990462 | No |
| D | LightGBM | B0+B1+B2 | 0.123727541 | 0.130432172 | −0.006704632 | No |
| V | Gamma GLM | B0+B1 | 0.139886354 | 0.144459075 | −0.004572721 | No |
| V | Gamma GLM | B0+B1+B2 | 0.139887468 | 0.144085348 | −0.004197880 | No |
| V | LightGBM | B0+B1 | 0.133696473 | 0.135913852 | −0.002217379 | No |
| V | LightGBM | B0+B1+B2 | 0.135652265 | 0.135384016 | +0.000268249 | Yes |

The absolute-score deterioration is consistent with removing information that was not
available at the registered forecast cutoff. It is not evidence that the old pipeline was
better: its lower QLIKE was measured with an inadmissible information clock. The
machine-readable artifact reports all sixteen primary cells and all sixteen
thirty-session sensitivity cells, not only the B1-inclusive subset shown here.

## Corrected primary contrasts

Positive deltas mean that the expanded information set lowers QLIKE relative to its base.
Intervals are the registered studentized session-cluster bootstrap intervals; Holm
p-values are descriptive within each model's five-contrast family.

| Role | Model | Δ total (95% CI) | Holm p | ΔB1 (95% CI) | Holm p | ΔB2\|B1 (95% CI) | Holm p |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| D | Gamma GLM | 0.000774 (−0.006538, 0.008256) | 1.0000 | 0.001413 (−0.005457, 0.008304) | 1.0000 | −0.000638 (−0.002155, 0.000871) | 1.0000 |
| D | LightGBM | 0.009113 (0.002247, 0.016011) | 0.0035 | 0.004267 (0.001387, 0.007177) | 0.0164 | 0.004846 (−0.001146, 0.010862) | 0.4410 |
| V | Gamma GLM | 0.004691 (0.000796, 0.008694) | 0.0350 | 0.004317 (0.000799, 0.007910) | 0.0350 | 0.000374 (−0.000279, 0.001027) | 0.3186 |
| V | LightGBM | 0.005783 (0.001211, 0.010429) | 0.0348 | 0.005253 (0.002150, 0.008410) | 0.0055 | 0.000530 (−0.001926, 0.002997) | 1.0000 |

The qualitative Phase 8 reading is unchanged, but the numbers above supersede the v12
cells for any statement about the corrected information clock. They remain exploratory:
no causal, universal, confirmatory, profitability or trading claim follows.

## Reproducibility and custody

The preregistered remediation contract SHA-256 is
`5f02db3c46b220f38b22a43147fe9738522a2effb66909621a372f259ab1ec51`.
The target-blind warm-up and paired-grid amendments were committed before the first
remediation model fit, with semantic hashes
`6216fa3640177a585196689000890b2745bd3dbfa9d462fce71daf87130158db` and
`72edf9700265ed2e53d39bcaeb742f6f629ddb028bcfa7b8d5139475d51eb447`.

The public, path-free result is
`artifacts/phase8_bridge/materialized_remediation_20260831_v1.json`, file SHA-256
`bda8f8ca2b4a4a3158bc8842e599ca1295abd855a1c56b26741e1e3a3fc366df` and
semantic self-hash
`1b10d63d344cb460add2ed1d0fe54d6f432f7f98909717a5cff31dd8c29855d4`.
The private remediated 187,200-row forecast cube has SHA-256
`54dcb9bf7b9a0377b0965839a3d3d43161884bf8790bf84ed66ae164358fc4d5`,
no nulls and no duplicate forecast keys. The 132-file executable closure SHA-256 is
`404dbed679e43badd7bd325848bcafc1c1aa2a5ee9af6fc0a93c7b3a68348fdc`.

The historical one-shot result remains at
`artifacts/phase8_bridge/result_20260830_v1.json`; the v11 dispersion audit remains the
exact replay of that historical cube. Neither should be cited as if it incorporated the
corrected B0/B1 cutoff.
