# RP2-v3 corrected-protocol measurement

> **HISTORICAL_MEASUREMENT_NOT_CURRENT_CLAIM.** The Block 8/Block 10 protocol
> divergence is repaired and the rebuild completed. The only remaining eligibility
> blocker is `PIT_V22_RECONCILIATION_BLOCKED`; no number below is a current headline.

Measured on `rp2-v3-20260827-remediation3`, scientific hash
`386610a4908d601c1ad09688d8371cfa3fdd70e4e7ddf50c416e8d3b0907cb47` at commit
`e7728ebbaf3f`. D contains 389 sessions and V contains 80. The aggregate bundle is under
`artifacts/rp2_v3/rp2-v3-20260827-remediation3/`; granular Parquet panels remain local and
licensed. The run completed 13/13 steps, recorded a 7,137,103,872-byte peak and used
`--forbid-sealed-cohorts`.

This run supersedes `rp2-v3-20260824-remeasure` as the corrected-protocol historical
measurement. The older run fitted `lightgbm_qlike` under different internal session rules
in Block 8 and Block 10. The new run uses the same selected boosting rounds in both
producers and compares provenance only across the three registered primary families;
ladder-only diagnostic families are not falsely required in Block 10.

## Twelve registered contrasts

A positive delta means the larger information set has lower QLIKE. These are retrospective
D/V measurements, not confirmatory tests.

| Family | Role | Contrast | Δ | 95% CI | Contains 0 |
| --- | --- | --- | ---: | ---: | :---: |
| `gamma_glm` | D | ΔB1 | +0.00219 | [+0.00098, +0.00342] | no |
| `gamma_glm` | D | ΔB2\|B1 | −0.00002 | [−0.00045, +0.00045] | yes |
| `gamma_glm` | V | ΔB1 | −0.00113 | [−0.00411, +0.00198] | yes |
| `gamma_glm` | V | ΔB2\|B1 | −0.00215 | [−0.00437, −0.00032] | **no** |
| `ridge_log` | D | ΔB1 | +0.00229 | [+0.00121, +0.00352] | no |
| `ridge_log` | D | ΔB2\|B1 | +0.00017 | [−0.00030, +0.00065] | yes |
| `ridge_log` | V | ΔB1 | −0.00083 | [−0.00283, +0.00131] | yes |
| `ridge_log` | V | ΔB2\|B1 | −0.00194 | [−0.00505, +0.00020] | yes |
| `lightgbm_qlike` | D | ΔB1 | +0.00253 | [+0.00064, +0.00502] | no |
| `lightgbm_qlike` | D | ΔB2\|B1 | +0.00060 | [+0.00022, +0.00100] | no |
| `lightgbm_qlike` | V | ΔB1 | +0.00211 | [−0.00797, +0.01211] | yes |
| `lightgbm_qlike` | V | ΔB2\|B1 | +0.00336 | [−0.00001, +0.00692] | yes |

Seven of twelve deltas are positive. Seven of twelve intervals contain zero.
Three of the six family-role pairs for ΔB2\|B1 are negative. The signs are family- and
partition-dependent; they do not establish a universal B1 or B2 contribution.

Retrospective inference, intervals, MDEs and session requirements share the exploratory
two-sided contract α = 0.05 and power = 0.80. The run also records 0.00417 as the budget
reserved for a future preregistered campaign. It is not the decision threshold for D/V and
is not mixed into their power arithmetic. A non-binding post-hoc sensitivity check finds no
validation p-value below 0.00417; that does not convert the retrospective analysis into
confirmation. The small development B2 intervals for `gamma_glm` and `ridge_log` are
compatible with the recorded margin, but are not formal multiplicity-adjusted TOST claims.

## Detectability under the same exploratory α = 0.05 contract

| Family | Effect in D | MDE in V (α = 0.05) | Could V have detected it? |
| --- | ---: | ---: | --- |
| `gamma_glm` | +0.00219 | 0.00411 | No — roughly 113 sessions would be needed |
| `ridge_log` | +0.00229 | 0.00271 | No — roughly 45 sessions would be needed |
| `lightgbm_qlike` | +0.00253 | 0.01517 | No — roughly 1148 sessions would be needed |

Nine of the twelve contrasts sit below their own minimum detectable effect. Validation
therefore cannot turn a wide interval into evidence of absence. `gamma_glm` and
`ridge_log` have negative validation ΔB1; `lightgbm_qlike` has a positive but very imprecise
validation ΔB1. This mixed pattern is not a replicated section-21 result.

## What the protocol correction moved

| Family | ΔB1 in D, before → after | ΔB1 in V |
| --- | ---: | ---: |
| `gamma_glm` | +0.00219 → **+0.00219** | −0.00113, unchanged |
| `ridge_log` | +0.00229 → **+0.00229** | −0.00083, unchanged |
| `lightgbm_qlike` | +0.00123 → **+0.00253** | +0.00211, moved |

The two GLM families were already fitted identically. LightGBM was not: harmonizing the
session-aware round selection moves its development ΔB1 from +0.00123 to +0.00253 and its
validation ΔB1 from −0.00383 to +0.00211. That movement is why the previous run could not
be retained as the current bundle even though its row masks matched.

The DML diagnostics remain associational. Their joint Wald tests do not identify a causal
mechanism, and provider source timestamps do not establish historical client receipt time.

## Eligibility boundary

- `PIT_V22_RECONCILIATION_BLOCKED` remains active.
- `SAFE_TO_RECONCILE_EXISTING_RESULTS=NO` and
  `SAFE_TO_OPEN_OR_EVALUATE_OOS=NO` remain binding.
- No sealed cohort was read: C, Phase 8 and Phase 9 remain closed;
  `sealed_cohorts_read=0`.
- No economic, live-trading or causal claim is made; `capital_go=false`.

The reproducible numerical tables are emitted by:

```text
uv run python scripts/rp2_verdict_tables.py --run-id rp2-v3-20260827-remediation3
```

`tests/contract/test_verdict_matches_artifact.py` checks every table value and count against
the inference artifact named by this document.
