# Block 3 — target-horizon validation

**Status:** `CURRENT BLOCK-LEVEL MEASUREMENT` · exploratory, not confirmatory
**Run:** `rp2-v3-20260827-remediation3`
**Artifact:** `artifacts/rp2_v3/rp2-v3-20260827-remediation3/rp2_block3_target/comparison.json`
**Recorded comparison SHA-256:** `054848bf3253f185e55459a19cb3783cb8aebb60b18312d4fed96853571fca0d`

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
| Development (D) | 79,790 |
| Validation (V) | 31,558 |

The session audit records 3,752 session-assets seen, 40 rejected as too short, and none
rejected for the missing-grid threshold.

## Current measurement

Out-of-sample log-scale R² for the price-history RV baseline:

| Role | RV5 | RV15 | RV30 | RV60 | RV120 |
| --- | ---: | ---: | ---: | ---: | ---: |
| D | 0.59654 | 0.77049 | 0.82413 | **0.83944** | 0.80557 |
| V | 0.59966 | 0.74588 | **0.78528** | 0.77994 | 0.72262 |

Median relative measurement noise falls with the horizon:

| Horizon | 5 | 15 | 30 | 60 | 120 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Relative noise | 52.07% | 34.22% | 25.62% | 19.00% | 14.07% |

The old statement that RV60 wins in both roles is withdrawn. RV60 exceeds RV30 in D by
0.01531 log-R², while RV30 exceeds RV60 in V by 0.00534. The horizon preference is therefore
role-dependent, not a replicated universal ranking.

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
