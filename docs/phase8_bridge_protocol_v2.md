# Phase 8A exploratory bridge protocol v2

**Status:** `TARGET_BLIND_METHOD_FROZEN_READ_NOT_AUTHORIZED`
**Owner authorization:** 2026-08-27, recorded as methodology decision 99
**Machine-readable contract:** `artifacts/phase8_bridge/bridge_contract_v2.json`
**Sealed cohort reads while designing this protocol:** `0`

Version 2 preserves the authorized method from version 1 while correcting provenance:
the machine contract hashes this frozen protocol instead of the append-only methodology
ledger, so later unrelated decisions cannot invalidate deterministic regeneration.

## What the authorization changes

It cancels the plan to wait for a new Phase 8B cohort. The existing 30-session Phase 8A
acquisition remains sealed, immutable and useful, but it is no longer described as a
pristine confirmation of the current scientific specification.

The bridge has two declared views of the same preserved cohort:

| Role | Sessions | Window | Interpretation |
| --- | ---: | --- | --- |
| Primary | 20 | 2026-08-03..2026-08-28 | Strictly unobserved; descriptive/exploratory evidence |
| Sensitivity | 30 | 2026-07-20..2026-08-28 | Includes the 10 C2-overlap sessions; robustness only |

The first ten dates, 2026-07-20..2026-07-31, were already part of C2. They may not enter
the primary 20-session analysis and cannot be used to claim a new one-read confirmation.

## Scientific question and estimands

The primary estimand is the current total-information contrast
`Delta_Total = L(B0) - L(B0+B1+B2)`, where positive means that the complete option
information set lowers QLIKE. The other four decision-65 quantities are always reported
beside it: `Delta_B1`, `Delta_B2|B1`, `Delta_B2|B0` and `Delta_Interaction`. No favorable
contrast may be selected after the read while unfavorable ones are omitted.

## Models and fitting boundary

The two current independent families are Gamma GLM and LightGBM. Their implementation and
fixed settings come from `src/mds650/rp2/ladder.py`. D and V may supply training,
preprocessing and the already-completed specification choice; no Phase 8 row may be used
for fitting, early stopping, tuning or feature selection. Because D and V were already used
adaptively, this bridge remains exploratory even though its 20-session primary window was
not previously observed.

## Inference, multiplicity and power

The independent unit is the XNYS session, not the five-minute origin. The primary window
uses session-clustered studentized inference, Newey-West sensitivity and 9,999 wild-cluster
bootstrap draws with seed 650. All five contrasts are Holm-adjusted within each registered
model family; raw and adjusted values are descriptive, not promotion gates. The 30-session
sensitivity receives estimates and uncertainty but does not create a second decision.

The historical Phase 8 sequential slot is not recycled: its reference budget remains 0.025,
and the first Holm step for five contrasts is 0.005. Because the bridge is explicitly
non-confirmatory, crossing either number cannot yield `CONFIRMED`.

Power is recalibrated from D/V-only session dispersion in the current Block-12 design at
80% power and alpha 0.005 for n=20 and n=30. That source supports `Delta_B1` and
`Delta_B2|B1`. It does not expose a session-sigma estimate for the new primary
`Delta_Total`; the contract therefore records its power as unavailable rather than
substituting a proxy or looking at sealed outcomes. This is a limitation, not a gate to be
removed after the result is known.

## What remains prohibited

- Opening, scoring or evaluating any Phase 8 payload before a separate one-shot authority.
- Replacing a missing session, changing the 20/30 windows or altering the model after read.
- Calling the result confirmatory, formally equivalent or preregistered under the current
  estimand.
- Running a retrospective salvage analysis after seeing an unfavorable or imprecise result.

The future one-shot authorization permits exactly one execution against this frozen
contract. Until then, `safe_to_open_or_evaluate_oos=false` and `sealed_cohorts_read=0`.
