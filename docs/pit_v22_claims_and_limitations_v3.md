# PIT v2.2 successor — holdout-exposure addendum v3

**Status:** `PASS_RETROSPECTIVE_EXPOSURE_VERIFIED`

**Scope:** a target-free session-calendar audit. It read only `session_date` and
`common_predictor_complete` from the signed predictor panel; it read no target, forecast,
loss, metric, Phase 8/9 payload or C cohort.

## Verified exposure

`artifacts/target_blind_v22/successor_holdout_exposure_v1.json` has semantic audit SHA-256
`2df4b74a0c663944d5428aac12afcf131017799261d0d24d1fa18857f71189c7` and file SHA-256
`42d9f3c86e2a767b9b3baa8e59a8be0a6ad51c042c252f180602d887f2017340`.

The signed runner's chronological 60% split of the 159-session target-free calendar is:

| Role | Sessions | Window |
| --- | ---: | --- |
| Development | 95 | 2025-08-04 to 2025-12-17 |
| Validation | 32 | 2025-12-18 to 2026-02-04 |
| Holdout | 32 | 2026-02-05 to 2026-03-23 |

All 32 holdout sessions intersect the 160-session Phase 6 C3 calendar and the 389-session
RP2-v3 development window. Neither intersects the Phase 8 primary or sensitivity windows.
This conclusion comes from dates and the frozen split only, not from any newly read outcome.

## Reclassification and claim boundary

The successor is `RETROSPECTIVE_REMEASUREMENT_UNDER_PIT_V22` and
`EXPLORATORY_DESCRIPTIVE`. Its `one-shot` label describes only the executed contract's
access custody; it is not a claim that the outcomes were prospectively unobserved. Its MDE
role is `EXPLORATORY_DESCRIPTIVE`, so it cannot retain
`CONFIRMATORY_THRESHOLD` without an explicit overriding methodology decision.

The immutable estimates, intervals, p-values and custody records are preserved. The
reclassification neither reruns nor recalibrates the result, and it authorizes no global
edge, causal, profitability or capital claim. `capital_go=false`, `RESEARCH_ONLY`, and
`NOT INVESTMENT ADVICE` remain binding.

## Reproduction

```powershell
uv run python scripts/audit_successor_holdout_exposure_v1.py
uv run pytest tests/contract/test_outcome_exposure_labels.py -q
```
