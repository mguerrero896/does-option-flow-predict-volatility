# RP4 v5 — family tournament with selection within training

**English translation. Historical seals refer to the preserved original bytes.**

Owner: Miguel. Authorisation: 2026-09-08, 17:00 Australia/Sydney; decision 134 in `docs/methodology_decisions.md`. Complete instruction: locally preserved tournament authorisation, SHA-256 `6fe35ddedcbafc871306a09a10756533bea7f6a37c199fd191a51167f71ef8d0`. RESEARCH_ONLY; NOT INVESTMENT ADVICE; capital_go=false.

## Registration, estimand and previous closeout

v5 is a new development stage; it does not modify the “there is no v5” closeout of programme v4, its artifacts or its pre-declared-test status. It is reported as a fifth read of the same historical windows, with Bonferroni ×5 as a declared bound. Causal training by session does not make adaptive development untouched. Inference is retrospective for the selector procedure fixed here; it is neither an independent replication nor control of every earlier search decision.

The primary estimand is the paired QLIKE delta B1/B0 and B2/B1 of the primary selector at RV15 on development. v4 retains the headline until a prospective replication supports v5. The original proposal, section 4.4, is quoted under the owner's authorisation: “model choice will follow benchmark performance and simplicity”; no independent documentary verification of that quotation is claimed.

## Data, predictors and time

The executable v4 contract, SHA-256 `0a45b0a608110e2ca0dcf38accc2a0c2521ebbe9d223eb002e36ec51f78afd04`, and effective v3 contract, SHA-256 `930f3ddb6ef6284f1129dda26ed705699a666ade005c6ad363cb67864794e6f5`, are inherited. The v5 JSON enumerates literally the same predictors, transformations, required and optional variables, and assets: AAPL, AMZN, META, MSFT, NVDA and TSLA. B0 ⊂ B1 ⊂ B2 have **29/69/138** predictors plus five asset fixed effects. SPY/QQQ remain previously registered controls; the universe is not expanded. The tournament chooses families and their parameters, never a list of variables using results.

Panel: locally preserved base panel, SHA-256 `a63ff5e61092d2bc00917c5de4e0e73f928005acc475f46370348eaca6ad4637`. RV15/RV5 targets: locally preserved target panel, SHA-256 `b2357a10a8a4955499e94b576b7853129e957ad70702da09bebbc9b6befd35db`. RV30 is `rv30` from the base panel. Join one to one by asset, session and origin minute, not by position. Retain exactly v3 eligibility, including valid RV30, authorised NaNs, presence/empty-window indicators and quality controls. An invalid selected target on an eligible row stops execution. Targets and prices are not imputed, and rows are not excluded based on a family's performance.

Partition: **2026-08-01**. Only sessions 2024-08-02–2026-07-31 are read through a Parquet filter. First 60 sessions: warm-up. Inherited schedule: 419 sessions, 2024-10-28–2026-07-31. Sessions without eligible origins are recorded using the same inherited rule and do not count as zero losses. Both the scheduled calendar and number actually evaluated are reported. Neither the subsequent window is evaluated here nor prospective data read.

Expanding walk-forward, pooled assets and equal weights per origin during fitting. Reuse `causal_masks`: train requires an earlier date and original RV30 target end ≤ first evaluated origin −60 minutes. Validation: last ten eligible train sessions; inner_fit excludes those ten and requires RV30 end ≤ first validation origin −60 minutes. Purge/embargo: 60 minutes. PIT: source-time proxy **120 seconds**; it does not prove historical client receipt. Retain the UW gap 2025-01-25–2025-02-24 without filling it.

## Fixed horizons and families

RV15 is primary; RV5 is a registered secondary; RV30 is reported for the proposal's questions. RV3/RV1 are excluded without searching their results. The three horizons use the same conservative RV30 mask and the same information sets.

Each family produces validation forecasts from inner_fit, chooses parameters using only those ten sessions and refits on complete train to forecast the next session. Selection QLIKE is the asset/session mean followed by an equal mean across sessions. Neither bounds, preprocessing nor refitting consult the evaluated session's target.

| Family / key | Fixed grid and rule |
| --- | --- |
| Seasonal persistence / `seasonal_persistence` | K ∈ [1,5,20]. Arithmetic mean of targets from the last K available sessions for the same asset and origin minute within the fitting mask. If the group is missing, use the asset's fitting mean; if that is also missing, use the global fitting mean. Floor 1e-12. Tie: smaller K. By definition this reference ignores additional regressors and is identical in B0/B1/B2; it does not change other models' lists. |
| Augmented log-linear HAR-RV / `log_har` | HAR-X/HARQ log-OLS over the full registered set, including HAR lags, rq_attenuation and controls; it is not presented as classical HAR with three regressors. Unpenalised least squares with tolerance 1e-10, unrestricted intercept, Duan and training bounds. Model without hyperparameters: singleton grid. |
| Current logarithmic ridge / `log_ridge_harq` | Reuse `rp4_v3_code.models.fit_ridge` unchanged; lambda [0.0001,0.01,1,100,10000], ties favour larger lambda. |
| Logarithmic elastic net / `log_elastic_net` | scikit-learn ElasticNet; alpha [0.0001,0.01,1] × l1_ratio [0.1,0.5,0.9]; cyclic selection, max_iter 10000, tol 1e-6, intercept. Tie: grid order. Numerical non-convergence does not authorise silently dropping a candidate. |
| LightGBM QLIKE / `lightgbm_qlike` | Reuse `rp4_v2_code.models.fit_lightgbm` unchanged: leaves **[7,15,31,63,127]**, expanded from [15,31,63]; learning rate 0.05, minimum 100/leaf, max_bin 63, maximum 2000 rounds, patience 50, seed 20260908, CPU 4 threads, deterministic, force_col_wise, feature_fraction=bagging_fraction=1. Tie: fewer leaves and rounds. Init score log(mean fitting target), applied once only. |
| Small dense network / `mlp_log` | scikit-learn MLPRegressor; layers [(32),(64,32)] × alpha [0.0001,0.01], ReLU, Adam, batch_size 1024, learning_rate_init 0.001, max_iter 100, shuffle=False, random_state 20260908, early_stopping=False, n_iter_no_change 20, tol 1e-4. No internal random split. The training-loss criterion may stop before the maximum; reaching the limit is reported as budget reached, without excluding the candidate. Tie: grid order. CPU for every final run. |
| Ensemble / `ensemble_top2` | Arithmetic mean of forecasts in levels from the two best individual families by validation QLIKE. Choose two different families, not two hyperparameters of one family. Fixed weights 1/2, no meta-fitting. This is the secondary selector; it does not compete again against the six families in the primary. |

The linear families and MLP use inherited pointwise transformations and v3 `_ridge_design`: fitting-only medians for optional variables, explicit presence, fitting population mean/standard deviation, winsorisation ±5, removal of zero variance and pivoted QR with tolerance 1e-10. An optional column never observed is removed without fabricating a median. Rank selection addresses identifiability only, not supervised variable search. Elastic net and MLP use slopes without duplicating their own intercept. MLP's log target is centred/scaled using its fitting mean and standard deviation; if the deviation is zero, use divisor one. Reverse this before Duan. HAR, ridge, elastic net and MLP use Duan with fitting residuals and bounds [0.5×P1,2×P99] from that fit's selected target (linear quantiles). Bounds and preprocessing are recalculated separately in inner_fit and train. LightGBM retains inherited native NaNs, log clip [-30,30] and floor 1e-12. If QR leaves zero slopes, ElasticNet/MLP receive a technical zero column to retain the estimator with an intercept, without inventing an observed variable. BLAS threads are also limited to four with threadpoolctl. ElasticNet precomputes the Gram matrix (`precompute=True`) to reduce iteration cost on large training samples while retaining the registered objective.

## Selector and inference

For each session, information set and horizon, `selector_primary` chooses the family with the lowest `selected.validation_qlike`. Exact ties follow the six families' order in the table. The chosen candidate and ranking of the top two are retained; the evaluation session determines neither. The secondary selector is `ensemble_top2`. Each selector is one procedure, not six tests selected afterwards.

QLIKE = y/f − log(y/f) −1. MAE in levels; RMSE = square root of the weighted mean of squared errors. Average first across origins within asset/session, then equally across assets present in the session, then equally across sessions. Delta = baseline − expanded loss; reduction % = 100×mean(delta)/mean(baseline loss).

Circular bootstrap with five-session blocks, 9999 resamples, seed **20260908**, centred null, +1 correction, one-sided p-value and two-sided 95% percentile CI; minimum ten sessions, declared degeneracy, no tail removal. Reuse v3 `session_contrast` with explicit parameters. No IID bootstrap of origins.

Within each selector: H1 B1/B0 followed by H2 B2/B1, one-sided at 5%, positive effect; H2 can be promoted only after H1. Both nominal p-values and intervals are shown, with H2 closed if H1 does not pass. For **Holm across the two selectors**, register each chain's joint claim through q_s=max(p_H1,p_H2); apply Holm to the two q_s and require both positive signs. This controls joint hierarchy claims across selectors; it does not promise global control of each isolated H1. Report p_Holm_chain and min(1,5×p_Holm_chain), as well as min(1,5×p) for each contrast as a descriptive bound across versions. RV5/RV30 and family tables are secondary/descriptive; they are not promoted according to their results.

**Decision rule fixed now:** v5 “improves on v4” only if the primary selector's B2/B1 delta at RV15 is positive, one-sided p <0.05 and the 95% CI excludes zero. Report separately whether that nominal condition also passes H1 and chain Holm; meeting only the nominal criterion does not support a global hierarchy claim. This label means meeting the owner's rule for the B2/B1 increment, not a direct test of performance differences between versions. Even if it is met, v4 retains the headline until prospective support. If it is not met, report the tournament without replacing anything. Nothing is refitted after reading.

## Screening, cost and execution

The owner's direct message permits GPU screening and first requires a sealed decision and specification. The route adopted has no prior adaptive screening: all preceding configurations are fixed by design. **Closed archive drawer: configurations tested to choose this grid before sealing = none; GPU screening = not executed.** No other engine will be installed to replace CPU estimators. The RTX 5090 Laptop is present; PyTorch is not installed in the inherited environment. GPU performance is not attributed to a CPU execution.

Initial estimate communicated before fitting: **6–18 hours**, provisional. Measured basis: v4 RV15/development, 2940.2563865 seconds =49.0043 minutes for eight shards. Approximate tree extrapolation: 49.0043×3 horizons×5/3 =245.0215 minutes (4.0837 hours). Added network/elastic-net cost and the load of other tasks have not yet been measured; they explain the range, which is no guarantee. A timing measurement after sealing may refine it, never change the grid. The estimate is communicated again with its hash before launching the complete run.

Deterministic CPU, eight disjoint shards by session (calendar index i with i%8), at most four threads per estimator, fixed seeds; each shard retains all permitted history. Horizon order: RV15, RV5, RV30. Numerical libraries and versions, code and input hashes are fixed in the release before the run. No prospective models or data, training downloads, new automations, push or writes outside the authorised worktree.

Components/sessions are written once with keys, selection, masks, input, target, code, specification and hash receipt. Resume only intact artifacts from the same release; do not overwrite results or repeat a complete read. A failure stops its shard, is preserved and reported. Synthetic tests verify causality, poisoning of the evaluation target, validation-only selection, determinism, equal masks, contracts/hashes and aggregation. Synthetic tests are not equivalent to complete evaluation.

## Universe and prospective work

`docs/rp4/v5_universe_feasibility.md` is not part of the public release; its historical citation is retained. It is the availability, timing and quota appendix for the two RP4 providers. Its receipt and hash are bound to the seal before running. SPY/QQQ are not added without a further written decision from Miguel. Endpoint support or sampling does not establish exhaustive coverage of the window.

Prepare `docs/rp4/prospective_confirmation_v1_amendment_4_draft.md` **without sealing**; the draft is not part of the public release and its historical citation is retained. It places the primary v5 selector as an additional secondary prospective test and v4 primary. It is linked to this specification's hash; any eventual seal must precede any prospective read. This work neither opens prospective data nor consumes a read or authorisation from existing registrations.

## Required deliverables

`docs/rp4/results_v5.md`: complete family × information set × horizon table with QLIKE, MAE, RMSE, counts and v4 comparison in the same table (RV30: v3 as reference; v4 did not execute RV30); selection frequencies, deltas and intervals for both selectors, nominal/Holm/Bonferroni p-values and chronology of every incident. `artifacts/rp4_v5_*/` artifacts: executable specification, receipts, costs, contracts, per-file hashes, private forecasts and reproducible aggregates. Integration note for defence revision 3. Other tasks' packages are not altered.
