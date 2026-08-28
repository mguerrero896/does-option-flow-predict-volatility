# Phase 9 academic reporting policy (v2, 2026-08-28)

This policy supersedes v1's planning arithmetic. It does not edit or replace the frozen
Phase 9 protocol: the 60-complete-session endpoint, 24-session warm-up, three 12-session
test blocks, one-read rule and recorded protocol SHA-256 remain binding.

## Decision

Phase 9 remains a prospective follow-up and is not a gate for submitting or defending
the capstone. The academic report uses the eligible evidence available at its editorial
cutoff and describes Phase 9 as ongoing. It reports no Phase 9 estimate, interval,
p-value, power calculated from outcomes or verdict.

The endpoint remains **60 complete sessions, of which 36 are scored**. No interim look,
backfill, counter edit or outcome access is activated. A smaller endpoint would be a
different study and would not solve the three-week academic deadline.

## Corrected planning denominator

The v1 planning table treated 60 complete sessions as though all 60 were scored. Under
the frozen folds, the first 24 sessions are warm-up observations, so the endpoint has
only 36 scored sessions. The target-blind audit recomputes planning MDEs from the same
Gate 11 session-level standard errors, without reading any Phase 9 outcome path.

At 80% power, the corrected endpoint MDEs are:

| Planning scenario | Nominal two-sided alpha 0.05 | Binding alpha 0.008333... |
|---|---:|---:|
| Recent log OLS | 0.01980 | 0.02507 |
| Recent LightGBM | 0.01760 | 0.02228 |
| P6 log OLS | 0.00873 | 0.01105 |
| P6 LightGBM | 0.01437 | 0.01820 |

These are design approximations, not observed effects or post-hoc power. The binding
alpha is decision 64's Phase 9 allocation, `0.05 / (2 * 3)`.

## Calendar versus the academic deadline

The projections below use XNYS sessions from 2026-08-19, exclude the recorded misses on
2026-08-25 and 2026-08-26, and assume no later miss. Dates move later if collection fails.

| Complete sessions | Scored sessions | Complete test blocks | Earliest nominal date | Read status |
|---:|---:|---:|---:|---|
| 20 | 0 | 0 | 2026-09-18 | No look exists |
| 30 | 6 | 0 | 2026-10-02 | No complete block |
| 36 | 12 | 1 | 2026-10-12 | Interim not activated |
| 48 | 24 | 2 | 2026-10-28 | Interim not activated |
| 60 | 36 | 3 | 2026-11-13 | Frozen one-shot endpoint; separate read authority required |

By the three-week Sydney horizon of 2026-09-18, the best-case natural collection is 19
complete sessions and **zero scored sessions**. Therefore no Phase 9 result can exist by
that deadline under the frozen design. Forced backfill would not create prospective
evidence and remains prohibited.

## Academic use

The submission and defence proceed from the current scientific bundle and, if separately
authorized, the exploratory Phase 8 bridge. Phase 9 continues unchanged after submission
as prospective follow-up evidence. Creating a short fixed-model pilot would be a new,
exploratory protocol and would duplicate the role already assigned to Phase 8; it is not
activated here.

Reproducible audit: `artifacts/phase9/power_deadline_audit_v1.json`, canonical audit
SHA-256 `1cfa5cdab57e5bb17580d33a7f4a8823e06bf4f2ba31823b37108734fa15f93a`.

`sealed_cohorts_read=0`.
