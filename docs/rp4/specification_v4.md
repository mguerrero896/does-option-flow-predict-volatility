# RP4 v4 — flow horizon, final specification

**English translation. Historical seals refer to the preserved original bytes.**

Owner: Miguel. Decision 133. New registration, before constructing RV15/RV5 or any v4 fit; it does not modify v1/v2/v3. Label: “out-of-sample walk-forward, split fixed 2026-09-07”. RESEARCH_ONLY; NOT INVESTMENT ADVICE; capital_go=false.

## Antecedent, trigger and scope

The complete locally retained conditional pre-registration is adopted, SHA-256 `6f8ad8d53a8f4336851415a99c25b316bf44db74165e29246110a3bb133eabee`. Its file and sidecar agree. The content date is 2026-09-07 20:20 Sydney; local metadata precede the v3 primary fit but do not constitute an independent timestamp. The trigger is met: H2 is not rejected in either v3 primary family (ridge 0.0525; LightGBM 0.6631).

The only scientific change from v3 is the target horizon. Primary `rv_15`; registered secondary `rv_5`. Quantile, jump and MZ recalibration/diagnostic endpoints are excluded from v4. RV30 is not the target of any v4 fit. Robust, temporal and regime QLIKE secondaries are retained.

## Data, sets and sample

Immutable locally retained panel, SHA-256 `a63ff5e61092d2bc00917c5de4e0e73f928005acc475f46370348eaca6ad4637`. The `feature_sets` lists, transformations, mandatory and optional columns are inherited literally from the effective v3 specification, SHA-256 `930f3ddb6ef6284f1129dda26ed705699a666ade005c6ad363cb67864794e6f5`. The v4 JSON enumerates them again for execution: nested B0/B1/B2 with 29/69/138 predictors. The `rv_back_*` lags, HARQ, gamma, NaN, presence and empty-window indicators are retained without recalculating or selecting predictors.

v3 eligibility is retained exactly by keys `(asset, session_date, origin_minute)`, including its already fixed quality checks and valid RV30. The availability endpoints of the original 30-minute target are also retained for training and validation masks: this conservative choice isolates the horizon without expanding the sample or admitting rows into training earlier. New targets must be finite and positive on all those rows; any failure is recorded in the census and investigated before evaluation, never silently excluded or imputed. Ineligible keys and rows remain in the target file and census.

Split 2026-08-01. Primary: 2024-08-02 to 2026-07-31, first 60 sessions for training only; inherited schedule of 419 evaluable sessions. Confirmation: 2026-08-03 to 2026-09-04, 25 sessions. No new provider data are read. Phase 9 and frozen files are not modified.

## Target derivation and validation

For each panel key, construct RV_h = sum of squared future one-minute log returns, h=15 or 5, using `mds650.rp2.realized.log_returns/forward_measures`, the same bars, grids and conventions as RP4 RV30. Require h+1 observed closes and inherited quality checks; do not fill missing prices. The new endpoint is origin+h and must lie within the original origin+30 bound. Do not execute the Block3 CLI, which also fits models; use only its measurement functions.

Targets go in a separate new file, joined one-to-one by keys, never by position. Compare against `registered_runs/rp2_v3/rp2-v3-20260901-flow-session-loss-registration/rp2_block3_target/target_panel.parquet` (SHA-256 `fdab55c524a6ee2cd94bb3f1f544dec527e1c8813f9a03d6e17ed8029f842831`), columns rv_15/rv_5, through 2026-07-17. “Byte for byte” means the Float64 representation of each aligned finite pair, not the Parquet container bytes: report N, finiteness masks, maximum/mean differences, discrepancies and causes. A difference is not accepted on tolerance without investigation before evaluation. Confirmation has no earlier reference, and this is disclosed.

## Models and temporal control, with unchanged procedures

Expanding walk-forward by session, pooling six assets with fixed effects and equal fitting weights per origin. Purge and embargo of 60 minutes and the last ten training sessions for tuning, with the preceding conservative causal masks. No evaluation statistic determines transformations, hyperparameters or bounds.

Log ridge: v3 transformations, training-only median for optional variables, presence indicators, standardisation using training mean/population deviation, winsorisation at ±5, zero-variance/collinearity removal by pivoted QR with tolerance 1e-10. Lambda in [0.0001, 0.01, 1, 100, 10000], validation QLIKE, ties favouring larger lambda; Duan using training residuals. Bounds [0.5 × P1, 2 × P99], linear quantiles of the selected target in current training, not RV30; report validation and evaluation bound hits by session/set. Reuse `v3.models.fit_ridge` with the explicit target vector.

LightGBM QLIKE on log forecasts: leaves 15/31/63, rate 0.05, minimum 100 per leaf, max_bin 63, maximum 2,000 rounds, patience 50, last ten sessions, ties favouring fewer leaves and rounds. Initialise with the log mean of the selected training target; apply the initial scale only once. Seed 20260907, deterministic, four threads. Reuse the v2 primary, identical to the v3 primary, without invoking the MZ secondary. Report selected rounds and leaves by session.

## Inference and secondaries

QLIKE = y/f − log(y/f) − 1. Average origins by asset/session, then equal averages over assets and sessions. Delta = baseline − expanded-model loss. Percentage reduction = 100 × mean(delta) / mean(baseline loss). Per family and window: H1 B1/B0 > 0 at 5%; H2 B2/B1 > 0 only if H1 rejects, also at 5%; a positive estimate is required. Closed H2 retains a diagnostic nominal p-value, not a formal p-value. Retain circular bootstrap blocks of five sessions, 9,999 resamples, seed 20260907, a one-sided test with a centred null and +1 correction, two-sided percentile 95% CI and a minimum of ten sessions.

Secondaries that cannot be promoted: paired median and mean trimmed by 5% per tail (floor), with their bootstrap; two-sided/Holm p-values for four contrasts per window for comparability; a conditional Gaussian posterior for the mean with flat prior and plug-in HAC5 variance; inherited session DM and GW diagnostics; assets, three chronological blocks, exclusion of each block and last thirty sessions. None replaces the primary decision.

Inherited regimes: first hour, last hour origin≥300, calendar Friday as a proxy for weekly expiration, third Friday, high flow based on preceding-day premium and a tercile calculated only in training, high absolute gamma imbalance available at the origin with a training threshold, earnings/FOMC/monthly expiration. An unknown calendar is not absence. Census of empty 5/30-minute windows and inside/outside contrast, without excluding empty windows; high-gamma versus rest contrast. Ten highest-loss days by family/set, with signs of both contrasts and ties broken by date. All signs are reported.

## Order, performance and custody

One logical evaluation per window and horizon: primary RV15, confirmation RV15, primary RV5, confirmation RV5. Eight disjoint session shards and four threads each (maximum 32 threads), each shard with access to the complete permitted past; not eight different models or a split of training. Adopt the authorised configuration directly, without an additional trial on evaluated windows. Summarise actual time and resources; five hours is an operational target, not a promise of a result or duration.

Resume only components whose complete checkpoint matches the specification, code, target, panel and keys, without repeating complete fits; separate roots and bindings by horizon/window. Release hashes before fitting, commands and exit codes by stage. v3 secondary repairs remain outside the v4 release, with low priority and at most two threads, without changing the v4 budget. No publication, downloads, collectors or v5.

## Closeout and limits

If primary RV15 rejects H2 in at least one family after H1, report it as a result for that family and RV5 only as secondary. Also report whether both families reject; “at least one” does not by itself provide global 5% control across families or versions. If neither rejects, close this mechanism investigation with B1>B0 as the main result observed at 30 minutes and B2 undetected at 30/15/5 according to each estimate and interval. Non-rejection establishes neither equivalence to zero nor causal absorption; “informative null” describes the closeout, not proof of absence.

The report compares v3 and v4 and discloses the fourth evaluation of the same windows: v1 initial design; v2 coverage/capacity/regularisation; v3 mechanism and empty windows; v4 a predeclared conditional horizon. Horizon comparisons describe different estimands, not independent replications.

The window from 20 July to 28 August was read once by the Phase 8 bridge under another specification. PIT uses a source-time proxy at 120 s, as in the literature.

Accepted UW gap: 2025-01-25 to 2025-02-24, without filling. The local v4 freeze does not remove the earlier adaptive search or demonstrate historical client availability or actual dealer inventories.
