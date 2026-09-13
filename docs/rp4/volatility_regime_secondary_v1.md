# Volatility-regime stability: secondary analysis specification

**Status: REGISTERED BEFORE COMPUTATION.** Written and hashed before the contrasts below
were calculated. Author: Miguel Guerrero. Date: 2026-09-11.

## Why this exists

RQ3 of the original proposal asks whether improvements are stable "across assets,
time-of-day segments, volatility regimes, and conservative timing assumptions". Three of
those four dimensions are already answered: assets and session segments in
`artifacts/rp4_v4_b4/regime_secondary.csv`, and timing in
`artifacts/rp4_robustness_public_v1/pit_60_contrasts.csv` and `pit_300_contrasts.csv`.

The volatility-regime dimension was specified in the proposal and never executed. This
document fixes its rule before the calculation so that the result is a completion of a
pre-specified commitment rather than a new search.

## Input

Single file: `artifacts/rp4_v4_b2_rv15/session_losses.csv` (419 evaluated sessions, RV15,
primary window). It carries, per session date, the paired QLIKE losses for both model
families at B0, B1 and B2, and the realised outcome in column `actual`.

No licensed input, no refitting, no change to the panel. The analysis is arithmetic on a
frozen public aggregate.

## Regime definition

Sessions are ranked by `actual`, the session-level realised variance, and split into
**terciles** across the 419 evaluated sessions:

- `vol_low`: lowest third
- `vol_mid`: middle third
- `vol_high`: highest third

Boundaries follow the empirical 33.3rd and 66.7th percentiles of `actual` with linear
interpolation. Ties are broken by session date ascending. No other bucketing is examined,
and the tercile rule is not revised after the contrasts are seen.

## Contrasts

Within each regime, for each model family (`log_ridge_harq`, `lightgbm_qlike`):

- `B1_over_B0`: mean paired session loss difference, baseline B0 minus richer B1.
- `B2_over_B1`: mean paired session loss difference, baseline B1 minus richer B2.

Positive values favour the richer information set.

## Statistics

Matching the convention already used in `artifacts/rp4_v4_b4/regime_secondary.csv`:

- **`mean`** is the registered statistic and carries the reported result.
- `median` and `trimmed_mean_5pct` are reported alongside as the stability descriptions
  that Section 3.7 already declares. They do not override the mean.

## Inference

Identical to the registered secondary convention:

- Circular block bootstrap, block length 5 sessions, 9,999 replicates, seed 20260907.
- Blocks are drawn over the regime subset ordered by session date.
- Interval: two-sided percentile 95%. It is not an inversion of the centred-null p.
- Centred null: each resampled statistic has the observed statistic subtracted.
- Two-sided p with the +1 correction: `p = (1 + #{|D*_b - D| >= |D|}) / 10000`.
- Holm adjustment across the four contrasts within each regime (two families times two
  contrasts), family size 4, matching the existing regime file.

## Evidential role

**SECONDARY, nominal.** This analysis cannot promote a failed primary test, cannot change
the registered headline, and is not a confirmation. It answers one stability dimension of
RQ3 descriptively.

## Declared limitation, stated before the result

Tercile membership is **not contiguous in time**. The circular block bootstrap assumes a
contiguous series, so on a scattered subset it preserves less of the original dependence
structure than it does on the full window. The same limitation already applies to the
`event` subset in the existing regime file. Intervals here should be read as indicative.

## Binding commitment

The result is reported as it comes out, for all three regimes, both families and both
contrasts, whatever the signs and probabilities. No regime is dropped, no statistic is
selected after the fact, and an adverse or null outcome is published in the same table as
a favourable one.
