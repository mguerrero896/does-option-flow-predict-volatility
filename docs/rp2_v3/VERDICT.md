# RP2-v3 B1 spot-cutoff remediation

> **HISTORICAL_MEASUREMENT_NOT_CURRENT_CLAIM.** The partition-role and market-clock
> defects are repaired and the complete rebuild finished. The only remaining eligibility
> blocker is `PIT_V22_RECONCILIATION_BLOCKED`; no number below is a current headline.

Measured on `rp2-v3-20260831-b1-spot-cutoff-remediation`, scientific hash
`033f2eb6be35e5db06aec2f9e01ef5f3379a8be68b0372087f24e40fa681bea4` at commit
`b70c54ba14fd`. D contains 389 sessions and V contains 80. The aggregate bundle is under
`artifacts/rp2_v3/rp2-v3-20260831-b1-spot-cutoff-remediation/`; granular Parquet panels remain
local and licensed. The run completed 13/13 steps, recorded a 6,962,065,408-byte peak,
ran for 1,690.594 seconds and used `--forbid-sealed-cohorts`.

This run supersedes `rp2-v3-20260831-timing-role-remediation`. That run repaired three
defects but left B1's underlying spot outside its own information boundary: option rows
stopped at `t-120 s`, while parity, moneyness and delta used `close[m]`, which ends at
`t+60 s` for start-labelled bars. The corrected run uses `close[m-3]` for B1 spot, matching
the last close available at the option cutoff. The prior repairs remain: roles are derived
by date, every B0 predictor and market control observes the same cutoff, the forward RV30
target stays anchored at the origin, and B1 shares the XNYS expiry calendar with B2.

## Twelve registered contrasts

A positive delta means the larger information set has lower QLIKE. These are retrospective
D/V measurements, not confirmatory tests.

| Family | Role | Contrast | Δ | 95% CI | Contains 0 |
| --- | --- | --- | ---: | ---: | :---: |
| `gamma_glm` | D | ΔB1 | +0.00256 | [+0.00100, +0.00417] | no |
| `gamma_glm` | D | ΔB2\|B1 | +0.00012 | [−0.00039, +0.00069] | yes |
| `gamma_glm` | V | ΔB1 | −0.00150 | [−0.00511, +0.00224] | yes |
| `gamma_glm` | V | ΔB2\|B1 | −0.00264 | [−0.00586, +0.00002] | yes |
| `ridge_log` | D | ΔB1 | +0.00287 | [+0.00153, +0.00437] | no |
| `ridge_log` | D | ΔB2\|B1 | +0.00028 | [−0.00029, +0.00088] | yes |
| `ridge_log` | V | ΔB1 | −0.00088 | [−0.00315, +0.00156] | yes |
| `ridge_log` | V | ΔB2\|B1 | −0.00250 | [−0.00674, +0.00051] | yes |
| `lightgbm_qlike` | D | ΔB1 | +0.00320 | [+0.00106, +0.00590] | no |
| `lightgbm_qlike` | D | ΔB2\|B1 | +0.00052 | [−0.00013, +0.00111] | yes |
| `lightgbm_qlike` | V | ΔB1 | +0.00280 | [−0.00518, +0.01030] | yes |
| `lightgbm_qlike` | V | ΔB2\|B1 | +0.00198 | [−0.00276, +0.00829] | yes |

Eight of twelve deltas are positive. Nine of twelve intervals contain zero.
Two of the six family-role pairs for ΔB2\|B1 are negative. The signs are family- and
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
| `gamma_glm` | +0.00256 | 0.00506 | No — roughly 125 sessions would be needed |
| `ridge_log` | +0.00287 | 0.00315 | Marginally not: ~39 sessions needed, 32 available |
| `lightgbm_qlike` | +0.00320 | 0.01198 | No — roughly 449 sessions would be needed |

Ten of the twelve contrasts sit below their own minimum detectable effect. Validation
therefore cannot turn a wide interval into evidence of absence. `gamma_glm` and
`ridge_log` have negative validation ΔB1; `lightgbm_qlike` has a positive but very imprecise
validation ΔB1. This mixed pattern is not a replicated section-21 result.

## What the B1 spot-cutoff correction moved

| Family | ΔB1 in D, before → after | ΔB1 in V, before → after |
| --- | ---: | ---: |
| `gamma_glm` | +0.00258 → **+0.00256** | −0.00152 → **−0.00150** |
| `ridge_log` | +0.00288 → **+0.00287** | −0.00092 → **−0.00088** |
| `lightgbm_qlike` | +0.00267 → **+0.00320** | +0.00136 → **+0.00280** |

The common panel remains at 181,829 rows relative to the immediately prior
timing-and-role run; this rerun changes the B1 spot used inside those rows, not their
membership. B1 core coverage is 99.3389%, B1 expiry coverage is
99.7828%, all 12 B2 core features have 100% coverage, provider failures are zero and B2
records zero PIT violations. These exceed the registered 90% floor. The new rebuild
isolates the B1 spot correction relative to the immediately prior timing-and-role run; it
does not decompose individual B1 feature movements.

## Treatment × coverage factorial

The preregistered factorial uses the exact ten Ext1 `CORE_TREATMENTS` and the exact twelve
current `B2_CORE` features over the three-source August coverage and the complete
five-source coverage. All cells use the same cross-fitted partial-out DML estimator,
B0+B1 nuisance set, session clustering, five folds and one-session purge. The 40 joint
tests share one Holm family. Each entry is `Wald / df / raw p / Holm p`.

| Treatment set / coverage | D 60m | D 120m | V 60m | V 120m |
| --- | ---: | ---: | ---: | ---: |
| Ext1 exact / August | 12.567 / 10 / 0.248901 / 1.000000 | 11.793 / 10 / 0.299176 / 1.000000 | 27.846 / 10 / 0.001910 / 0.068774 | 29.575 / 10 / 0.001005 / 0.038196 |
| Ext1 exact / complete | 12.981 / 10 / 0.224741 / 1.000000 | 17.623 / 10 / 0.061665 / 1.000000 | 27.846 / 10 / 0.001910 / 0.068774 | 29.575 / 10 / 0.001005 / 0.038196 |
| B2 panel 12 / August | 29.378 / 12 / 0.003461 / 0.110753 | 22.729 / 12 / 0.030119 / 0.813202 | 30.497 / 12 / 0.002349 / 0.079872 | 26.468 / 12 / 0.009209 / 0.267060 |
| B2 panel 12 / complete | 33.068 / 12 / 0.000945 / 0.036843 | 37.078 / 12 / 0.000217 / 0.008680 | 30.497 / 12 / 0.002349 / 0.079872 | 26.468 / 12 / 0.009209 / 0.267060 |

On the registered `log(Wald / df)` scale, the median absolute treatment-set main effect
is 0.405476 and the coverage main effect is 0.037680, a ratio of 10.76. The registered
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
obsolete bytes are unavailable, so historical byte equality cannot be confirmed. The v3
factorial result records both requested and resolved names, commit `d67fe13c`, all panel
and bar hashes, `sealed_cohorts_read=0`, semantic self-hash
`ca495aa4b6a7b3745d1ddb6eaae8a849fa5ed58eef92021140bed796632d6121` and
LF-normalized file SHA-256
`1a3f5783a16f67877d80919c7635d1b0df6740d49e88c9725afeff1113dfccc4`.

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
uv run python scripts/rp2_verdict_tables.py --run-id rp2-v3-20260831-b1-spot-cutoff-remediation
```

`tests/contract/test_verdict_matches_artifact.py` checks every table value and count against
the inference artifact named by this document.
