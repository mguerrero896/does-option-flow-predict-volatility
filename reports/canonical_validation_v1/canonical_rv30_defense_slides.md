# Canonical RV30 — Defense Slide Outline

> Portable outline only. It does not modify the approved PowerPoint source.

## Slide 1 — One question

Can ordinary option state improve a 30-minute realised-variance forecast beyond
underlying/market controls, and can trade-derived activity add further value?

## Slide 2 — What is forecast

- A row = an asset at a five-minute forecast origin.
- RV30 = thirty one-minute log returns from 31 observed minute closes.
- No predictor is allowed after the forecast origin.

## Slide 3 — Three nested information sets

- B0: underlying and market controls.
- B1a: B0 + point-in-time ATM implied volatility.
- B2: B1a + nine target-blind trade-activity features.

## Slide 4 — Why the data are credible but not public

- Licensed historical datasets are retained outside Git.
- Reproducibility comes from hashes, manifests, causal audits, fixed contracts, and portable code.
- Each future Full Tape session requires availability, hash, calendar, and point-in-time validation.

## Slide 5 — Evaluation protocol

- Gamma GLM confirmatory; LightGBM nonlinear robustness.
- Identical origins across B0/B1a/B2.
- QLIKE primary; bootstrap clustered by trading day; Holm adjustment; MDE frozen before outcomes.

## Slide 6 — Registered results

- Independent Gamma B2: +0.03291534 with 95% interval [+0.02444358, +0.04162629]; MDE met: yes.
- Independent LightGBM B2: -0.00180221 with 95% interval [-0.00240038, -0.00119407]; MDE met: no.
- Full signed table: `tables/canonical_registered_contrasts.csv`.

## Slide 7 — Correct conclusion

`MODEL_FAMILY_DEPENDENT`: targeted Gamma evidence is not an all-model claim because the
registered LightGBM robustness model disagrees. This is a result to report, not a reason to
remove or replace a model.

## Slide 8 — Boundaries and next step

- No claim of trader intent, causality, or deployable strategy.
- No new DL/RL method is added after outcomes are read.
- A newly sealed replication, with method frozen before target access, is required to test
  whether the disagreement persists.
