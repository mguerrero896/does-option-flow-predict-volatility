# Block 3 — target-horizon validation

**Status:** `CURRENT BLOCK-LEVEL MEASUREMENT` · exploratory, not confirmatory
**Run:** `rp2-v3-20260831-b1-spot-cutoff-remediation`
**Artifact:** `artifacts/rp2_v3/rp2-v3-20260831-b1-spot-cutoff-remediation/rp2_block3_target/comparison.json`
**Recorded comparison SHA-256:** `10ed954256a12b882569596d8731dc7e6100b18c0f8c78e394f04db4c7680dd3`

The overall RP2-v3 run remains ineligible because PIT v2.2 forbids reconciliation into a
current claim. That does not turn this block into a headline; it remains the latest
target-horizon diagnostic and is cited only for the standing RV30 design choice.

## Design

The producer builds candidate targets from one-minute closes on a common intraday origin
grid. Every horizon is evaluated on compatible origins, so a longer horizon is not credited
for using an easier row set. Measures include realized variance (RV), bipower variation,
jump variation, continuous variation, realized quarticity, and upside/downside semivariance.

The current artifact contains 111,348 rows over 464 sessions:

| Role | Rows |
| --- | ---: |
| Development (D) | 92,150 |
| Validation (V) | 19,198 |

The session audit records 3,752 session-assets seen, 40 rejected as too short, and none
rejected for the missing-grid threshold.

## Current measurement

Out-of-sample log-scale R² for the price-history RV baseline:

| Role | RV5 | RV15 | RV30 | RV60 | RV120 |
| --- | ---: | ---: | ---: | ---: | ---: |
| D | 0.55242 | 0.73767 | 0.79624 | **0.81260** | 0.76951 |
| V | 0.53287 | 0.69509 | 0.74621 | **0.74980** | 0.71474 |

Median relative measurement noise falls with the horizon:

| Horizon | 5 | 15 | 30 | 60 | 120 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Relative noise | 52.07% | 34.22% | 25.62% | 19.00% | 14.07% |

The date-derived role repair moves 12,360 rows previously mislabelled V back to D. Under
the corrected partition, RV60 exceeds RV30 by 0.01636 log-R² in D and 0.00359 in V. This is
a retrospective ranking on already-read roles, not authority to replace the frozen RV30
target or a claim that RV60 has adequate prospective power.

Jump variation remains much less predictable than total RV, but this is room for an
exploratory association test, not evidence that option information causes a volatility
mechanism.

## Standing decision

RV30 remains the sole primary target under `docs/target_horizon_decision.md`. This diagnostic
does not justify changing a frozen target after observing D/V. RV60 may be evaluated only as
a clearly labelled secondary target or in a future protocol frozen before its evaluation.

## Verification

The table above is read directly from the recorded `comparison` and
`validation_comparison` fields. The producer and unit tests are:

- `scripts/rp2_block3_target_panel.py`
- `src/mds650/rp2/realized.py`
- `tests/unit/test_rp2_realized.py`
