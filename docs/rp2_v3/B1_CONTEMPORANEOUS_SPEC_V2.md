# B1 as a cutoff-aligned option-state snapshot — v2

Frozen specification for the timing-remediated RP2-v3 B1 block. It supersedes
`B1_CONTEMPORANEOUS_SPEC.md` without rewriting that historical contract.

## What changed and why

The original contemporaneous specification correctly limited option rows to the empirical
availability cutoff, `t - 120 s`, but constructed parity, moneyness and delta diagnostics
with the underlying close at `t`. Because minute bars are labelled by their start, that close
finishes at `t + 60 s`: it is three bar indices later than the last close available at the
cutoff. Version 2 binds the underlying spot to the same information boundary as the quotes.

The B1/B2 row-overlap decision is unchanged. The contrast is conditional —
`E[Y | B0, B1, B2]` against `E[Y | B0, B1]` — so B1 and B2 may be correlated; neither may
read observations after the common cutoff.

## Frozen parameters

```text
Forecast origin: t
Availability cutoff: t - 120 seconds
Underlying spot: close of the start-labelled bar ending at t - 120 seconds (index t - 3 min)
Maximum quote age: 30 minutes
Sensitivity maximum age: 60 minutes
Contract state: last available NBBO per contract
Primary source label: trade_sampled_contemporaneous_nbbo
Post-cutoff observations: forbidden
```

## Algorithm

For each origin `t`:

1. set `c_t = t - 120 s`;
2. keep only option rows with `created_at <= c_t`;
3. drop option rows older than `c_t - 30 min`;
4. group by contract and keep its last available observation;
5. use the underlying close whose timestamp ends exactly at `c_t`;
6. build parity, moneyness, delta and surface diagnostics from only those inputs.

Quote age remains measured against the forecast origin, not against the cutoff, because the
age of the state at prediction time is the operational quantity. The cutoff is a floor on
that age. The target remains forward from `t`; changing it would change the estimand rather
than repair the information set.

## B1-core

The primary information set remains the same ten high-coverage features:

```text
b1_iv_7d
b1_iv_30d
b1_iv_60d
b1_term_slope
b1_smile_level
b1_risk_reversal_25
b1_median_relative_spread
b1_median_quote_age_s
b1_surface_coverage
b1_iv_minus_trailing_rv_30d
```

`b1_smile_level` is the fitted at-the-money level on the expiry bucket nearest 30 calendar
days. `b1_surface_coverage` is the share of four grid requirements met at the origin: at least
three contracts, both wings, and at least two expiries.

## B1-rich and failure policy

The implied rate, implied dividend yield, arbitrage diagnostics and low-coverage curvature
diagnostics remain reported but outside the primary set. A row is never discarded because implied rate
or implied dividend yield failed to fit. A failed diagnostic is missing evidence, not a
missing origin.

## Targets and invariants

| Metric | RP2-v3 target |
| --- | ---: |
| B1-core coverage | > 90 % |
| Median quote age against the origin | < 900 s |
| P95 quote age | <= 1 800 s |
| Rows discarded for rate or dividend | 0 |
| Post-cutoff option observations | 0 |
| Underlying closes after the cutoff | 0 |
| Duplicate contracts per snapshot | 0 |

The regression invariant mutates every underlying bar after `t - 120 s` through the origin
while holding the option snapshot fixed; every emitted B1 feature must remain unchanged.

## What this does not buy

A contract enters the surface only because somebody traded it, so selection of quotes is
still driven by flow. Aligning the underlying clock removes a point-in-time violation; it
does not remove that sampling limitation or turn the analysis into causal evidence.
