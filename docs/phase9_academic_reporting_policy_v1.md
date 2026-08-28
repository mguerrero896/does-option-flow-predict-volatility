# Phase 9 academic reporting policy (v1, 2026-08-28)

> **Superseded for planning arithmetic by
> `docs/phase9_academic_reporting_policy_v2.md`.** This file remains as the
> decision-100 audit record; it is not the current power statement.

This policy was recorded before any Phase 9 outcome read. It does not edit or replace the
frozen v1 protocol, whose 60-session, one-read design and recorded SHA-256 remain binding.

## Decision

Phase 9 is a prospective follow-up, not a gate for submitting or defending the capstone.
An academic version completed before the Phase 9 read reports the campaign as **ongoing**
and reports no Phase 9 estimate, interval, p-value or verdict. Operational metadata may be
reported: the frozen target, complete-session count, recorded misses, projected completion
date and `sealed_cohorts_read=0`.

The existing 60-session endpoint is retained. Reducing it would not merely shorten the
calendar: it would change the frozen experiment and reduce its already limited precision.

## Calendar and usable evaluation sessions

The frozen design uses a 24-session warm-up followed by 12-session test blocks. Calendar
dates below are XNYS-only projections from 2026-08-19 and roll forward the two misses
recorded by decision 97 (2026-08-25 and 2026-08-26). Any later miss moves the date later.

| Complete sessions | Scored sessions under the frozen folds | Earliest nominal date | MDE relative to n=60 |
|---:|---:|---:|---:|
| 20 | 0 | 2026-09-18 | 1.732x |
| 30 | 6, not one complete 12-session block | 2026-10-02 | 1.414x |
| 36 | 12, one block | 2026-10-12 | 1.291x |
| 48 | 24, two blocks | 2026-10-28 | 1.118x |
| 60 | 36, three blocks | 2026-11-13 | 1.000x |

The MDE ratios use the same alpha, power and session dispersion and therefore scale as
`sqrt(60 / n)`. They are relative planning quantities, not observed power and not Phase 9
results. Decision 64 additionally binds the final confirmatory threshold to alpha
`0.05 / (2 * 3) = 0.008333...`, which is stricter than the v1 protocol's nominal 0.05.

## Submission rule

At the manuscript evidence cutoff:

1. report the current scientific bundle under its actual eligibility label;
2. report any separately authorized Phase 8 bridge result under its exploratory label;
3. report Phase 9 only as an ongoing preregistered prospective follow-up; and
4. continue collection to 60 without backfill, counter edits or outcome access.

This makes the academic deadline independent of provider collection time without turning
an incomplete prospective sample into a claimed result.

## If an early Phase 9 result later becomes mandatory

The v1 protocol has no interim look. An early read would require a separately authorized
v2 protocol recorded before outcome access, would supersede the v1 one-read claim, and
would need a group-sequential alpha allocation plus the decision-64 e-value/martingale
reporting. The first fold-compatible look is n=36, but it has only twelve scored sessions;
n=48 has twenty-four. Neither is activated by this policy.

`sealed_cohorts_read=0`.
