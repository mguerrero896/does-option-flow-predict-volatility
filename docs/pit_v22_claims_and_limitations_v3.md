# PIT v2.2 successor — holdout-exposure audit addendum v3

**Status:** `NO_VERIFICABLE_DATE_VECTOR_UNAVAILABLE`

**Scope:** metadata-only audit; no new outcome read, model fit, scoring, rerun or sealed-store access.
**Authority:** this additive note does not alter any frozen successor artifact or replace
the canonical result while the successor date vector is unavailable.

## What was verified

`artifacts/target_blind_v22/successor_holdout_exposure_v1.json` has semantic audit SHA-256
`a4a83452ec36684956aed9bdf3c40d5bcafb56b15897c85da8fc9d3af75eba0a` and file SHA-256
`e44602d9b1ea7949dc9bd32cff9ed0da820585b6d09c45ff2f61533e2da4f41c`.

The audit verified three prior read windows from their public metadata:

| Earlier read | Sessions | Window |
| --- | ---: | --- |
| Phase 6 C3 test folds | 100 | 2025-10-28 to 2026-03-23 |
| RP2 development | 389 | 2024-08-02 to 2026-03-23 |
| Phase 8 primary / sensitivity | 20 / 30 | 2026-08-03 to 2026-08-28 / 2026-07-20 to 2026-08-28 |

It also verified the target-blind predictor manifest's 180-session input universe and the
successor freeze's chronological 60% training split. Neither permitted file carries the
materialized validation or holdout session-date vector. Exact overlap counts and a
retrospective classification are therefore **not verifiable** from this audit.

## Claim boundary

No reclassification is applied. The existing `GLOBAL_EDGE_NOT_CONFIRMED` disposition,
one-shot custody, `capital_go=false`, `RESEARCH_ONLY`, and `NOT INVESTMENT ADVICE` remain
unchanged; this addendum does not promote them.

If a separately auditable, non-outcome date vector later proves any holdout intersection
with a prior read window, its role must be
`RETROSPECTIVE_REMEASUREMENT_UNDER_PIT_V22` and `EXPLORATORY_DESCRIPTIVE`; its MDE role may
not remain `CONFIRMATORY_THRESHOLD` without an explicit overriding methodology decision.
The contract test is `tests/contract/test_outcome_exposure_labels.py`.

## Reproduction

```powershell
uv run python scripts/audit_successor_holdout_exposure_v1.py
uv run pytest tests/contract/test_outcome_exposure_labels.py -q
```
