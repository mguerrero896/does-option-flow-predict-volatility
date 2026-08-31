# RP2-v3 timing-and-partition-role remediation

> **HISTORICAL_MEASUREMENT_NOT_CURRENT_CLAIM.** The partition-role and market-clock
> defects are repaired and the complete rebuild finished. The only remaining eligibility
> blocker is `PIT_V22_RECONCILIATION_BLOCKED`; no number below is a current headline.

Measured on `rp2-v3-20260831-timing-role-remediation`, scientific hash
`7d544aa334b70ce8bc2d25d26bd1f984068b8f753aebe039fc59ae2a44719db3` at commit
`cbdd0b5840da`. D contains 389 sessions and V contains 80. The aggregate bundle is under
`artifacts/rp2_v3/rp2-v3-20260831-timing-role-remediation/`; granular Parquet panels remain
local and licensed. The run completed 13/13 steps, recorded a 6,836,768,768-byte peak,
ran for 1,694.783 seconds and used `--forbid-sealed-cohorts`.

This run supersedes `rp2-v3-20260827-remediation3`. Three defects changed the admissible
data: bar-source roles were trusted as literals instead of checked against partition dates,
B0 observed the underlying three minutes later than the 120-second B1/B2 cutoff, and B1
assumed every option expiry closed at 16:00 ET instead of using XNYS. The repair derives
roles by date, shifts every B0 predictor and market control by three one-minute bars while
leaving the forward RV30 target at the origin, and shares the XNYS expiry calendar with B2.

## Twelve registered contrasts

A positive delta means the larger information set has lower QLIKE. These are retrospective
D/V measurements, not confirmatory tests.

| Family | Role | Contrast | Δ | 95% CI | Contains 0 |
| --- | --- | --- | ---: | ---: | :---: |
| `gamma_glm` | D | ΔB1 | +0.00258 | [+0.00102, +0.00418] | no |
| `gamma_glm` | D | ΔB2\|B1 | +0.00018 | [−0.00033, +0.00074] | yes |
| `gamma_glm` | V | ΔB1 | −0.00152 | [−0.00500, +0.00223] | yes |
| `gamma_glm` | V | ΔB2\|B1 | −0.00272 | [−0.00598, −0.00011] | **no** |
| `ridge_log` | D | ΔB1 | +0.00288 | [+0.00154, +0.00438] | no |
| `ridge_log` | D | ΔB2\|B1 | +0.00028 | [−0.00029, +0.00087] | yes |
| `ridge_log` | V | ΔB1 | −0.00092 | [−0.00318, +0.00148] | yes |
| `ridge_log` | V | ΔB2\|B1 | −0.00251 | [−0.00676, +0.00050] | yes |
| `lightgbm_qlike` | D | ΔB1 | +0.00267 | [+0.00060, +0.00519] | no |
| `lightgbm_qlike` | D | ΔB2\|B1 | +0.00096 | [+0.00012, +0.00183] | no |
| `lightgbm_qlike` | V | ΔB1 | +0.00136 | [−0.00548, +0.00819] | yes |
| `lightgbm_qlike` | V | ΔB2\|B1 | −0.00202 | [−0.00517, +0.00131] | yes |

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
| `gamma_glm` | +0.00258 | 0.00496 | No — roughly 119 sessions would be needed |
| `ridge_log` | +0.00288 | 0.00311 | Marginally not: ~38 sessions needed, 32 available |
| `lightgbm_qlike` | +0.00267 | 0.01037 | No — roughly 484 sessions would be needed |

Ten of the twelve contrasts sit below their own minimum detectable effect. Validation
therefore cannot turn a wide interval into evidence of absence. `gamma_glm` and
`ridge_log` have negative validation ΔB1; `lightgbm_qlike` has a positive but very imprecise
validation ΔB1. This mixed pattern is not a replicated section-21 result.

## What the timing-and-role correction moved

| Family | ΔB1 in D, before → after | ΔB1 in V, before → after |
| --- | ---: | ---: |
| `gamma_glm` | +0.00219 → **+0.00258** | −0.00113 → **−0.00152** |
| `ridge_log` | +0.00229 → **+0.00288** | −0.00083 → **−0.00092** |
| `lightgbm_qlike` | +0.00253 → **+0.00267** | +0.00211 → **+0.00136** |

The common panel falls from 184,632 to 181,829 rows because B0's valid origin grid moves
from minutes 30–360 to 35–355. B1 core coverage is 99.3367%, B1 expiry coverage is
99.7828%, all 12 B2 core features have 100% coverage, provider failures are zero and B2
records zero PIT violations. These exceed the 86% floor. The rebuild measures the three
repairs jointly; it is not an ablation that assigns each numerical movement to one defect.

## Treatment × coverage factorial

The preregistered factorial uses the exact ten Ext1 `CORE_TREATMENTS` and the exact twelve
current `B2_CORE` features over the three-source August coverage and the complete
five-source coverage. All cells use the same cross-fitted partial-out DML estimator,
B0+B1 nuisance set, session clustering, five folds and one-session purge. The 40 joint
tests share one Holm family. Each entry is `Wald / df / raw p / Holm p`.

| Treatment set / coverage | D 60m | D 120m | V 60m | V 120m |
| --- | ---: | ---: | ---: | ---: |
| Ext1 exact / August | 12.593 / 10 / 0.247302 / 1.000000 | 11.769 / 10 / 0.300784 / 1.000000 | 27.793 / 10 / 0.001948 / 0.070123 | 29.554 / 10 / 0.001013 / 0.038488 |
| Ext1 exact / complete | 12.976 / 10 / 0.225014 / 1.000000 | 17.634 / 10 / 0.061464 / 1.000000 | 27.793 / 10 / 0.001948 / 0.070123 | 29.554 / 10 / 0.001013 / 0.038488 |
| B2 panel 12 / August | 29.405 / 12 / 0.003429 / 0.109729 | 22.717 / 12 / 0.030231 / 0.816240 | 30.457 / 12 / 0.002382 / 0.080985 | 26.444 / 12 / 0.009284 / 0.269236 |
| B2 panel 12 / complete | 33.065 / 12 / 0.000946 / 0.036878 | 37.072 / 12 / 0.000217 / 0.008699 | 30.457 / 12 / 0.002382 / 0.080985 | 26.444 / 12 / 0.009284 / 0.269236 |

On the registered `log(Wald / df)` scale, the median absolute treatment-set main effect
is 0.405764 and the coverage main effect is 0.036811, a ratio of 11.02. The registered
classification is therefore `TREATMENT_SET`, descriptively rather than causally because
the two treatment sets are not nested. This does not explain the frozen-to-current V
decline: August and complete coverage use identical V masks, and switching to the twelve
panel features does not restore the frozen V 120-minute Wald. For that historical decline,
the evidence says `NEITHER_TREATMENT_SET_NOR_COVERAGE`; the unresolved remainder is in the
unhashed historical inputs, preprocessing, estimator or session identity.

Ext1 names `b2_5m_hawkes_innovation`, which is absent from the current panel. The frozen
contract records a `RECORDED_SEMANTIC_RENAME` to
`b2_5m_decay_intensity_innovation`: the producer maps the historical label in memory,
retains the ten-column Ext1 coefficient identity and does not recompute the feature. The
obsolete bytes are unavailable, so historical byte equality cannot be confirmed. The v2
factorial result records both requested and resolved names, commit `cbdd0b58`, all panel
and bar hashes, `sealed_cohorts_read=0`, semantic self-hash
`42f919d3a88d840c41e357c54f27de1bfee9b119fdf9360f92aed6d357fc7fdb` and
LF-normalized file SHA-256
`04b5b94fd60d53defbca29282ba7ae86dd22e80779591479552ddae5b829a7c2`.

The DML diagnostics remain associational. Their joint Wald tests do not identify a causal
mechanism, and provider source timestamps do not establish historical client receipt time.

## Eligibility boundary

- `PIT_V22_RECONCILIATION_BLOCKED` remains active.
- `SAFE_TO_RECONCILE_EXISTING_RESULTS=NO` and
  `SAFE_TO_OPEN_OR_EVALUATE_OOS=NO` remain binding.
- This rebuild itself read no sealed cohort. At this run's execution snapshot, C,
  Phase 8 and Phase 9 were closed and `sealed_cohorts_read=0`. Phase 8 later consumed
  its separately authorized exploratory read; current counters live in
  `data/CANONICAL_STATE.json`.
- No economic, live-trading or causal claim is made; `capital_go=false`.

The reproducible numerical tables are emitted by:

```text
uv run python scripts/rp2_verdict_tables.py --run-id rp2-v3-20260831-timing-role-remediation
```

`tests/contract/test_verdict_matches_artifact.py` checks every table value and count against
the inference artifact named by this document.
