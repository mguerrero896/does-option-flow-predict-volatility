# RP4 v5 — registered exploratory extension: attempt A3, technical amendment 2

**English translation. Historical seals refer to the preserved original bytes.**

Status: **COMPLETE**. Updated: 2026-09-08T15:31:33.840073+00:00. RV15 only.

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.

## Coverage and progress

Exact calendar of 419 sessions from preflight A1. The same keys, targets and B0/B1/B2 sets are retained. PARTIAL contains completed sessions only; families may cover different dates and no winner is declared from that incomplete sample.

| horizon_minutes | family | N_sessions | N_calendar | N_remaining | N_origins | cpu_seconds | status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 15 | seasonal_persistence | 419 | 419 | 0 | 160832 | 186.84375 | COMPLETE |
| 15 | log_har | 419 | 419 | 0 | 160832 | 13088.141 | COMPLETE |
| 15 | log_ridge_harq | 419 | 419 | 0 | 160832 | 9645.5 | COMPLETE |
| 15 | log_elastic_net | 419 | 419 | 0 | 160832 | 13735.031 | COMPLETE |
| 15 | lightgbm_qlike | 419 | 419 | 0 | 160832 | 101485.89 | COMPLETE |

## Metrics by family and information set

QLIKE and MAE average origins within asset/session and give equal weight to assets and sessions. RMSE takes the square root after averaging squared error.

| version | horizon_minutes | family | information_set | qlike | mae | rmse | N_sessions | N_origins | N_asset_sessions | N_calendar | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v5 | 15 | seasonal_persistence | B0 | 0.41705236 | 6.9665818e-06 | 3.7487636e-05 | 419 | 160832 | 2514 | 419 | COMPLETE |
| v5 | 15 | seasonal_persistence | B1 | 0.41705236 | 6.9665818e-06 | 3.7487636e-05 | 419 | 160832 | 2514 | 419 | COMPLETE |
| v5 | 15 | seasonal_persistence | B2 | 0.41705236 | 6.9665818e-06 | 3.7487636e-05 | 419 | 160832 | 2514 | 419 | COMPLETE |
| v5 | 15 | log_har | B0 | 0.18322849 | 4.6689574e-06 | 3.3623951e-05 | 419 | 160832 | 2514 | 419 | COMPLETE |
| v5 | 15 | log_har | B1 | 0.18220759 | 4.7215803e-06 | 3.3537769e-05 | 419 | 160832 | 2514 | 419 | COMPLETE |
| v5 | 15 | log_har | B2 | 0.18067891 | 4.6949872e-06 | 3.3512211e-05 | 419 | 160832 | 2514 | 419 | COMPLETE |
| v5 | 15 | log_ridge_harq | B0 | 0.18366037 | 4.6811776e-06 | 3.3641832e-05 | 419 | 160832 | 2514 | 419 | COMPLETE |
| v5 | 15 | log_ridge_harq | B1 | 0.18205096 | 4.7191701e-06 | 3.3551349e-05 | 419 | 160832 | 2514 | 419 | COMPLETE |
| v5 | 15 | log_ridge_harq | B2 | 0.18091349 | 4.6910489e-06 | 3.3519003e-05 | 419 | 160832 | 2514 | 419 | COMPLETE |
| v5 | 15 | log_elastic_net | B0 | 0.18350021 | 4.6577801e-06 | 3.3650313e-05 | 419 | 160832 | 2514 | 419 | COMPLETE |
| v5 | 15 | log_elastic_net | B1 | 0.18224496 | 4.6863855e-06 | 3.3559636e-05 | 419 | 160832 | 2514 | 419 | COMPLETE |
| v5 | 15 | log_elastic_net | B2 | 0.1809996 | 4.6542663e-06 | 3.352214e-05 | 419 | 160832 | 2514 | 419 | COMPLETE |
| v5 | 15 | lightgbm_qlike | B0 | 0.18775026 | 4.737404e-06 | 3.4772374e-05 | 419 | 160832 | 2514 | 419 | COMPLETE |
| v5 | 15 | lightgbm_qlike | B1 | 0.18555364 | 4.7704735e-06 | 3.4857009e-05 | 419 | 160832 | 2514 | 419 | COMPLETE |
| v5 | 15 | lightgbm_qlike | B2 | 0.18576654 | 4.7803196e-06 | 3.487629e-05 | 419 | 160832 | 2514 | 419 | COMPLETE |
| v5 | 15 | selector_primary | B0 | 0.18433699 | 4.6534259e-06 | 3.3680118e-05 | 419 | 160832 | 2514 | 419 | COMPLETE |
| v5 | 15 | selector_primary | B1 | 0.1838239 | 4.7217884e-06 | 3.4272834e-05 | 419 | 160832 | 2514 | 419 | COMPLETE |
| v5 | 15 | selector_primary | B2 | 0.18124475 | 4.6583347e-06 | 3.3542048e-05 | 419 | 160832 | 2514 | 419 | COMPLETE |
| v5 | 15 | ensemble_top2 | B0 | 0.1824836 | 4.6471938e-06 | 3.3657977e-05 | 419 | 160832 | 2514 | 419 | COMPLETE |
| v5 | 15 | ensemble_top2 | B1 | 0.18107002 | 4.6727522e-06 | 3.3869828e-05 | 419 | 160832 | 2514 | 419 | COMPLETE |
| v5 | 15 | ensemble_top2 | B2 | 0.18023514 | 4.6451389e-06 | 3.3916121e-05 | 419 | 160832 | 2514 | 419 | COMPLETE |
| v5 | 15 | mlp_log | B0 | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | 0 | 0 | 0 | 419 | DEFERRED_COST_NOT_EVALUATED_IN_THIS_RUN |
| v5 | 15 | mlp_log | B1 | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | 0 | 0 | 0 | 419 | DEFERRED_COST_NOT_EVALUATED_IN_THIS_RUN |
| v5 | 15 | mlp_log | B2 | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | 0 | 0 | 0 | 419 | DEFERRED_COST_NOT_EVALUATED_IN_THIS_RUN |

MLP: deferred for cost, not evaluated in this A3 run. Its state is DEFERRED_COST_NOT_EVALUATED_IN_THIS_RUN; neither losses nor selection frequencies are imputed. A1 did fit the network in a partial component, and A2 fitted it in the memory/GPU test session. There is no claim that it was never evaluated. RV5 and RV30 remain deferred.

## Historical reference v4, RV15

| version | horizon_minutes | family | information_set | qlike | mae | N_sessions | N_origins | rmse | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| v4 | 15 | lightgbm_qlike | B0 | 0.18775026 | 4.737404e-06 | 419 | 160832 | 3.4772374e-05 | EXISTING_HISTORICAL_RESULT |
| v4 | 15 | lightgbm_qlike | B1 | 0.18555364 | 4.7704735e-06 | 419 | 160832 | 3.4857009e-05 | EXISTING_HISTORICAL_RESULT |
| v4 | 15 | lightgbm_qlike | B2 | 0.18576654 | 4.7803196e-06 | 419 | 160832 | 3.487629e-05 | EXISTING_HISTORICAL_RESULT |
| v4 | 15 | log_ridge_harq | B0 | 0.18366037 | 4.6811776e-06 | 419 | 160832 | 3.3641832e-05 | EXISTING_HISTORICAL_RESULT |
| v4 | 15 | log_ridge_harq | B1 | 0.18204406 | 4.7195749e-06 | 419 | 160832 | 3.3551646e-05 | EXISTING_HISTORICAL_RESULT |
| v4 | 15 | log_ridge_harq | B2 | 0.1809103 | 4.6911436e-06 | 419 | 160832 | 3.3519018e-05 | EXISTING_HISTORICAL_RESULT |

The comparators retain all 419 sessions. A PARTIAL table is not a paired comparison against them. v4 retains the headline; there is no direct v5/v4 test.

## Selector and inference

The selector and top2 ensemble use the five families: persistence, HAR, ridge, Elastic Net and LightGBM. They are chosen exclusively by temporal-validation QLIKE, with ties broken in that order; top2 averages levels with weights 0.5/0.5. They are calculated only when the five families complete all 419 sessions.

| family | contrast | estimate | ci_low | ci_high | p_nominal | p_for_decision | p_bonferroni5 | hypothesis_status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| selector_primary | B1_over_B0 | 0.00051309616 | -0.0022070785 | 0.0025541992 | 0.3594 | 0.3594 | 1 | NOT_REJECTED |
| selector_primary | B2_over_B1 | 0.002579149 | 0.00030468091 | 0.0062202819 | 0.0692 | NOT AVAILABLE | 0.346 | NOT_TESTED |
| ensemble_top2 | B1_over_B0 | 0.0014135833 | 0.00018892871 | 0.0028089323 | 0.0236 | 0.0236 | 0.118 | REJECTED |
| ensemble_top2 | B2_over_B1 | 0.00083487248 | -3.3644923e-05 | 0.0016685559 | 0.0249 | 0.0249 | 0.1245 | REJECTED |

| family | q_chain | p_holm_chain | p_holm_chain_bonferroni5 | chain_holm_rejected |
| --- | --- | --- | --- | --- |
| selector_primary | 0.3594 | 0.3594 | 1 | no |
| ensemble_top2 | 0.0249 | 0.0498 | 0.249 | yes |

H1→H2 is retained: H2 opens only after positive rejection of H1 at 5%. Its nominal p-value is disclosed even when the gate remains closed. Each chain uses max(pH1,pH2), Holm across the two selectors and Bonferroni ×5 as the declared bound across versions. Session bootstrap: block 5, 9,999 repetitions, seed 20260908; two-sided pointwise 95% intervals. Cost amendments are disclosed historical reads; ×5 does not correct all adaptive search or turn these results into prospective confirmation.

Nominal RV15 B2/B1 selector rule: NOT_SATISFIED. It requires positive delta, one-sided p <0.05 and a 95% interval excluding zero. It is reported separately from H1 and Holm results.

## Selector frequencies and deferred family

| horizon_minutes | information_set | family | selected_sessions | N_sessions | selection_frequency | top2_sessions | mean_top2_weight | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 15 | B0 | seasonal_persistence | 0 | 419 | 0 | 2 | 0.0023866348 | COMPLETE |
| 15 | B0 | log_har | 29 | 419 | 0.069212411 | 72 | 0.085918854 | COMPLETE |
| 15 | B0 | log_ridge_harq | 68 | 419 | 0.16229117 | 240 | 0.28639618 | COMPLETE |
| 15 | B0 | log_elastic_net | 119 | 419 | 0.28400955 | 299 | 0.35680191 | COMPLETE |
| 15 | B0 | lightgbm_qlike | 203 | 419 | 0.48448687 | 225 | 0.26849642 | COMPLETE |
| 15 | B0 | mlp_log | NOT AVAILABLE | 0 | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | DEFERRED_COST_NOT_EVALUATED_IN_THIS_RUN |
| 15 | B1 | seasonal_persistence | 0 | 419 | 0 | 1 | 0.0011933174 | COMPLETE |
| 15 | B1 | log_har | 23 | 419 | 0.054892601 | 73 | 0.087112172 | COMPLETE |
| 15 | B1 | log_ridge_harq | 77 | 419 | 0.18377088 | 248 | 0.29594272 | COMPLETE |
| 15 | B1 | log_elastic_net | 107 | 419 | 0.25536993 | 293 | 0.349642 | COMPLETE |
| 15 | B1 | lightgbm_qlike | 212 | 419 | 0.50596659 | 223 | 0.26610979 | COMPLETE |
| 15 | B1 | mlp_log | NOT AVAILABLE | 0 | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | DEFERRED_COST_NOT_EVALUATED_IN_THIS_RUN |
| 15 | B2 | seasonal_persistence | 0 | 419 | 0 | 1 | 0.0011933174 | COMPLETE |
| 15 | B2 | log_har | 37 | 419 | 0.088305489 | 93 | 0.11097852 | COMPLETE |
| 15 | B2 | log_ridge_harq | 48 | 419 | 0.11455847 | 231 | 0.27565632 | COMPLETE |
| 15 | B2 | log_elastic_net | 146 | 419 | 0.34844869 | 302 | 0.36038186 | COMPLETE |
| 15 | B2 | lightgbm_qlike | 188 | 419 | 0.44868735 | 211 | 0.25178998 | COMPLETE |
| 15 | B2 | mlp_log | NOT AVAILABLE | 0 | NOT AVAILABLE | NOT AVAILABLE | NOT AVAILABLE | DEFERRED_COST_NOT_EVALUATED_IN_THIS_RUN |

## Elastic Net: candidates and exclusions by stage

| horizon_minutes | information_set | family | stage | alpha | l1_ratio | N_sessions | N_calendar | eligible_sessions | attempted_sessions | converged_sessions | excluded_sessions | active_after_stage_sessions | not_attempted_sessions | selected_sessions | exclusion_frequency | status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 15 | B0 | log_elastic_net | inner_fit | 0.0001 | 0.1 | 419 | 419 | 419 | 419 | 419 | 0 | 419 | 0 | 77 | 0 | COMPLETE |
| 15 | B0 | log_elastic_net | refit | 0.0001 | 0.1 | 419 | 419 | 419 | 77 | 77 | 0 | 419 | 342 | 77 | 0 | COMPLETE |
| 15 | B0 | log_elastic_net | inner_fit | 0.0001 | 0.5 | 419 | 419 | 419 | 419 | 419 | 0 | 419 | 0 | 15 | 0 | COMPLETE |
| 15 | B0 | log_elastic_net | refit | 0.0001 | 0.5 | 419 | 419 | 419 | 15 | 15 | 0 | 419 | 404 | 15 | 0 | COMPLETE |
| 15 | B0 | log_elastic_net | inner_fit | 0.0001 | 0.9 | 419 | 419 | 419 | 419 | 419 | 0 | 419 | 0 | 167 | 0 | COMPLETE |
| 15 | B0 | log_elastic_net | refit | 0.0001 | 0.9 | 419 | 419 | 419 | 167 | 167 | 0 | 419 | 252 | 167 | 0 | COMPLETE |
| 15 | B0 | log_elastic_net | inner_fit | 0.01 | 0.1 | 419 | 419 | 419 | 419 | 419 | 0 | 419 | 0 | 62 | 0 | COMPLETE |
| 15 | B0 | log_elastic_net | refit | 0.01 | 0.1 | 419 | 419 | 419 | 62 | 62 | 0 | 419 | 357 | 62 | 0 | COMPLETE |
| 15 | B0 | log_elastic_net | inner_fit | 0.01 | 0.5 | 419 | 419 | 419 | 419 | 419 | 0 | 419 | 0 | 21 | 0 | COMPLETE |
| 15 | B0 | log_elastic_net | refit | 0.01 | 0.5 | 419 | 419 | 419 | 21 | 21 | 0 | 419 | 398 | 21 | 0 | COMPLETE |
| 15 | B0 | log_elastic_net | inner_fit | 0.01 | 0.9 | 419 | 419 | 419 | 419 | 419 | 0 | 419 | 0 | 73 | 0 | COMPLETE |
| 15 | B0 | log_elastic_net | refit | 0.01 | 0.9 | 419 | 419 | 419 | 73 | 73 | 0 | 419 | 346 | 73 | 0 | COMPLETE |
| 15 | B0 | log_elastic_net | inner_fit | 1 | 0.1 | 419 | 419 | 419 | 419 | 419 | 0 | 419 | 0 | 3 | 0 | COMPLETE |
| 15 | B0 | log_elastic_net | refit | 1 | 0.1 | 419 | 419 | 419 | 3 | 3 | 0 | 419 | 416 | 3 | 0 | COMPLETE |
| 15 | B0 | log_elastic_net | inner_fit | 1 | 0.5 | 419 | 419 | 419 | 419 | 419 | 0 | 419 | 0 | 1 | 0 | COMPLETE |
| 15 | B0 | log_elastic_net | refit | 1 | 0.5 | 419 | 419 | 419 | 1 | 1 | 0 | 419 | 418 | 1 | 0 | COMPLETE |
| 15 | B0 | log_elastic_net | inner_fit | 1 | 0.9 | 419 | 419 | 419 | 419 | 419 | 0 | 419 | 0 | 0 | 0 | COMPLETE |
| 15 | B0 | log_elastic_net | refit | 1 | 0.9 | 419 | 419 | 419 | 0 | 0 | 0 | 419 | 419 | 0 | 0 | COMPLETE |
| 15 | B1 | log_elastic_net | inner_fit | 0.0001 | 0.1 | 419 | 419 | 419 | 419 | 419 | 0 | 419 | 0 | 103 | 0 | COMPLETE |
| 15 | B1 | log_elastic_net | refit | 0.0001 | 0.1 | 419 | 419 | 419 | 103 | 103 | 0 | 419 | 316 | 103 | 0 | COMPLETE |
| 15 | B1 | log_elastic_net | inner_fit | 0.0001 | 0.5 | 419 | 419 | 419 | 419 | 419 | 0 | 419 | 0 | 37 | 0 | COMPLETE |
| 15 | B1 | log_elastic_net | refit | 0.0001 | 0.5 | 419 | 419 | 419 | 37 | 37 | 0 | 419 | 382 | 37 | 0 | COMPLETE |
| 15 | B1 | log_elastic_net | inner_fit | 0.0001 | 0.9 | 419 | 419 | 419 | 419 | 419 | 0 | 419 | 0 | 109 | 0 | COMPLETE |
| 15 | B1 | log_elastic_net | refit | 0.0001 | 0.9 | 419 | 419 | 419 | 109 | 109 | 0 | 419 | 310 | 109 | 0 | COMPLETE |
| 15 | B1 | log_elastic_net | inner_fit | 0.01 | 0.1 | 419 | 419 | 419 | 419 | 419 | 0 | 419 | 0 | 57 | 0 | COMPLETE |
| 15 | B1 | log_elastic_net | refit | 0.01 | 0.1 | 419 | 419 | 419 | 57 | 57 | 0 | 419 | 362 | 57 | 0 | COMPLETE |
| 15 | B1 | log_elastic_net | inner_fit | 0.01 | 0.5 | 419 | 419 | 419 | 419 | 419 | 0 | 419 | 0 | 25 | 0 | COMPLETE |
| 15 | B1 | log_elastic_net | refit | 0.01 | 0.5 | 419 | 419 | 419 | 25 | 25 | 0 | 419 | 394 | 25 | 0 | COMPLETE |
| 15 | B1 | log_elastic_net | inner_fit | 0.01 | 0.9 | 419 | 419 | 419 | 419 | 419 | 0 | 419 | 0 | 74 | 0 | COMPLETE |
| 15 | B1 | log_elastic_net | refit | 0.01 | 0.9 | 419 | 419 | 419 | 74 | 74 | 0 | 419 | 345 | 74 | 0 | COMPLETE |
| 15 | B1 | log_elastic_net | inner_fit | 1 | 0.1 | 419 | 419 | 419 | 419 | 419 | 0 | 419 | 0 | 14 | 0 | COMPLETE |
| 15 | B1 | log_elastic_net | refit | 1 | 0.1 | 419 | 419 | 419 | 14 | 14 | 0 | 419 | 405 | 14 | 0 | COMPLETE |
| 15 | B1 | log_elastic_net | inner_fit | 1 | 0.5 | 419 | 419 | 419 | 419 | 419 | 0 | 419 | 0 | 0 | 0 | COMPLETE |
| 15 | B1 | log_elastic_net | refit | 1 | 0.5 | 419 | 419 | 419 | 0 | 0 | 0 | 419 | 419 | 0 | 0 | COMPLETE |
| 15 | B1 | log_elastic_net | inner_fit | 1 | 0.9 | 419 | 419 | 419 | 419 | 419 | 0 | 419 | 0 | 0 | 0 | COMPLETE |
| 15 | B1 | log_elastic_net | refit | 1 | 0.9 | 419 | 419 | 419 | 0 | 0 | 0 | 419 | 419 | 0 | 0 | COMPLETE |
| 15 | B2 | log_elastic_net | inner_fit | 0.0001 | 0.1 | 419 | 419 | 419 | 419 | 419 | 0 | 419 | 0 | 127 | 0 | COMPLETE |
| 15 | B2 | log_elastic_net | refit | 0.0001 | 0.1 | 419 | 419 | 419 | 127 | 127 | 0 | 419 | 292 | 127 | 0 | COMPLETE |
| 15 | B2 | log_elastic_net | inner_fit | 0.0001 | 0.5 | 419 | 419 | 419 | 419 | 419 | 0 | 419 | 0 | 30 | 0 | COMPLETE |
| 15 | B2 | log_elastic_net | refit | 0.0001 | 0.5 | 419 | 419 | 419 | 30 | 30 | 0 | 419 | 389 | 30 | 0 | COMPLETE |
| 15 | B2 | log_elastic_net | inner_fit | 0.0001 | 0.9 | 419 | 419 | 419 | 419 | 419 | 0 | 419 | 0 | 63 | 0 | COMPLETE |
| 15 | B2 | log_elastic_net | refit | 0.0001 | 0.9 | 419 | 419 | 419 | 63 | 63 | 0 | 419 | 356 | 63 | 0 | COMPLETE |
| 15 | B2 | log_elastic_net | inner_fit | 0.01 | 0.1 | 419 | 419 | 419 | 419 | 419 | 0 | 419 | 0 | 70 | 0 | COMPLETE |
| 15 | B2 | log_elastic_net | refit | 0.01 | 0.1 | 419 | 419 | 419 | 70 | 70 | 0 | 419 | 349 | 70 | 0 | COMPLETE |
| 15 | B2 | log_elastic_net | inner_fit | 0.01 | 0.5 | 419 | 419 | 419 | 419 | 419 | 0 | 419 | 0 | 54 | 0 | COMPLETE |
| 15 | B2 | log_elastic_net | refit | 0.01 | 0.5 | 419 | 419 | 419 | 54 | 54 | 0 | 419 | 365 | 54 | 0 | COMPLETE |
| 15 | B2 | log_elastic_net | inner_fit | 0.01 | 0.9 | 419 | 419 | 419 | 419 | 419 | 0 | 419 | 0 | 62 | 0 | COMPLETE |
| 15 | B2 | log_elastic_net | refit | 0.01 | 0.9 | 419 | 419 | 419 | 62 | 62 | 0 | 419 | 357 | 62 | 0 | COMPLETE |
| 15 | B2 | log_elastic_net | inner_fit | 1 | 0.1 | 419 | 419 | 419 | 419 | 419 | 0 | 419 | 0 | 13 | 0 | COMPLETE |
| 15 | B2 | log_elastic_net | refit | 1 | 0.1 | 419 | 419 | 419 | 13 | 13 | 0 | 419 | 406 | 13 | 0 | COMPLETE |
| 15 | B2 | log_elastic_net | inner_fit | 1 | 0.5 | 419 | 419 | 419 | 419 | 419 | 0 | 419 | 0 | 0 | 0 | COMPLETE |
| 15 | B2 | log_elastic_net | refit | 1 | 0.5 | 419 | 419 | 419 | 0 | 0 | 0 | 419 | 419 | 0 | 0 | COMPLETE |
| 15 | B2 | log_elastic_net | inner_fit | 1 | 0.9 | 419 | 419 | 419 | 419 | 419 | 0 | 419 | 0 | 0 | 0 | COMPLETE |
| 15 | B2 | log_elastic_net | refit | 1 | 0.9 | 419 | 419 | 419 | 0 | 0 | 0 | 419 | 419 | 0 | 0 | COMPLETE |

### Exclusions by session

NOT AVAILABLE.

## Cost, environment and custody

[Technical amendment 2](specification_v5_technical_amendment_2.md). LightGBM returns to the frozen CPU producer rp4_v2_code.models.fit_lightgbm, with leaves [15,31,63], seed 20260908 and deterministic=True. A3 neither fits MLP nor uses GPU.

Part 18 reported approximately 193 seconds per session for LightGBM GPU in A2 and RV15 extrapolations of 22.49 h for LightGBM GPU and 28.22 h for MLP GPU. These are A2 measurements/extrapolations, not observed A3 times; they motivated the reduction in scope. The subsequent instruction fixes a 15% memory margin: 0.85 of allocatable memory is used to calculate shards from the newly measured peak.

| field | value |
| --- | --- |
| dependencies | {<br>  "lightgbm": "4.7.0",<br>  "numpy": "2.5.2",<br>  "pandas": "3.0.5",<br>  "polars": "1.44.1",<br>  "psutil": "7.2.2",<br>  "pyarrow": "25.0.1",<br>  "scikit-learn": "1.9.0",<br>  "scipy": "1.18.0",<br>  "threadpoolctl": "3.6.0",<br>  "torch": null<br>} |
| device | "CPU_ONLY" |
| lightgbm_binary | {<br>  "path": "LOCAL_LIGHTGBM_LIBRARY",<br>  "sha256": "7e366d2e49cd061aac3ab21676b2f99b0c7a758dc3e888d4b23812af1b7d301c"<br>} |
| prior_gpu_probe_sha256 | "f6d9053f9b27786bf799bd6dc7fec9d2d3759b9a0d55a8652b09504aff07eea0" |
| prior_gpu_seconds_per_session_three_sets | {<br>  "lightgbm_qlike": 193.20759619999444,<br>  "mlp_log": 242.4896918000013<br>} |
| python_executable | "LOCAL_PYTHON_EXECUTABLE" |

Attempts A1/A2, their seals, tests and receipts are preserved. The A3 execution is independent of the chat, retains per-session receipts and updates progress.json at least every five minutes. Each publication saves an immutable snapshot and receipt.

Binding: {
  "execution_sha256": "5cd6b4a92f3319d12f20044f32e9b87d8cc3ae731ce5cde66780d9fd2a9befb4",
  "release_sha256": "69db4672b7ad705300c820b42abb8f8430d8380a3f0360e2d1008b7b10b7f855",
  "specification_sha256": "a318736f7e5a08e21c089b59ec90aae1c5bccb015cb6d286bb59dd078fd2ee3e"
}

Calendar SHA256: 284b64adef635ce2db53a8ea54fedac981feaeece13b6161d8464bd886b5d925. Records SHA256: 0e846be59bdfecc48d5cb793fbe816d953ed35404172967adb85257c360006b3.

## Operational incidents and resumptions (technical amendment 3)

On 8 September 2026, at 21:54 Sydney time, Windows rejected replacement of progress.json (WinError 5). Execution resumed at 21:59 with 1,193 preserved receipts; subsequent verification confirmed their hashes unchanged. At 22:58:44 the same write failure recurred, preserving 1,634 receipts, including 377 for ElasticNet. The second resumption is dated and verified in artifacts/rp4_v5_a3_operations/resume_part27/verification.json.

These interruptions involved state writing, not model fitting. The responsible reader was not identified. Technical amendment 3 implements 60 attempts separated by 250 ms, in-place writing as fallback, and a warning without interrupting calculation if both mechanisms fail. Original scientific checkpoints and seals are preserved. The underlying scientific snapshot remains immutable; report_annotation_<update_id>.json distinguishes its hash from this annotated copy's hash. LightGBM allocation is registered before starting it in lightgbm_part21.json.

## Post hoc sensitivity: combining instead of selecting

**POST HOC.** Procedures chosen after seeing historical results; the following p-values do not control the search or replace the v4 headline or registered selector. Only saved forecasts are combined, without refitting models. Verification covered 2,095 records/receipts and all 419 sessions, with common keys and targets. Recalculated losses of the five families and two selectors agree with the closed report: maximum absolute error 4.44e-16. B0 frequencies are reproduced: LightGBM 203, ElasticNet 119, ridge 68 and HAR 29. No selector error is detected.

The combination is the arithmetic mean of positive levels before QLIKE. The canonical producer is used: equal weights by asset/session, then by session; circular bootstrap with block 5, 9,999 resamples, historical v5 seed 20260908, centred null, +1 correction, one tail. H1 compares B1/B0; H2 compares B2/B1. Reduction = 100 × mean(baseline − expanded loss) / mean(baseline loss).

| Procedure | B0 | B1 | B2 | H1 | H2 |
|---|---:|---:|---:|---:|---:|
| Ridge recalculated in v5 (v4 reference) | 0.183660372 | 0.182050961 | 0.180913492 | +0.876 %, p=0.0383 | +0.625 %, p=0.0032 |
| HAR/ridge/ElasticNet average | 0.183103100 | 0.181502807 | 0.180338627 | +0.874 %, p=0.0355 | +0.641 %, p=0.0018 |
| Four-family average with LightGBM | 0.181840402 | 0.180002994 | 0.179102244 | +1.010 %, p=0.0214 | +0.500 %, p=0.0037 |

The four-family average has the lowest B2 QLIKE among the procedures in this historical comparison: 0.999% below original v4 ridge and 0.629% below top2, calculated as 100 × (1 − combination QLIKE / reference QLIKE). This does not demonstrate statistical superiority between models or prospective success. The three nominal chains in this sensitivity pass H1→H2, without correction for their post hoc search.

### Diagnosis and scope

B2 gap = realised loss minus internal-validation QLIKE, averaged across sessions. Validation uses equal weights by asset/session; the second column changes only realised loss to equal weights per origin within session and reproduces the auditor's approximate figures:

| Family | Canonical gap | Gap with realised loss weighted by origin |
|---|---:|---:|
| lightgbm_qlike | +0.001069393 | +0.000979818 |
| log_elastic_net | +0.000373013 | +0.000290751 |
| log_ridge_harq | -0.000626224 | -0.000717045 |
| log_har | -0.001638082 | -0.001707866 |

This documents relative historical validation optimism for LightGBM and pessimism for HAR/ridge. It is compatible with selection being too favourable to trees in this sample; it does not prove a universal causal bias from ten-session windows. Diversity can be used by averaging forecasts, without requiring the daily winner to be identified correctly.

The ex post oracle takes the lowest loss among the **five** families per session, including persistence: canonical B2 0.174352218 versus the best fixed family, HAR, at 0.180678912. With realised loss weighted by origin: 0.174274154 and 0.180609128, reproducing the auditor's 0.1743 and 0.1806 after rounding. This is a bound with knowledge of the outcome, not a strategy available before the session. Persistence is not excluded from the oracle.

Part 34 also reports these post hoc filters with weighting by origin: selection by previous realised QLIKE over 10/20/40/60 sessions, 0.1833/0.1834/0.1811/0.1809; hysteresis 0.002/0.005/0.01, 0.1834/0.1833/0.1819; selector among three linear families, 0.1810; fixed-ridge reference, 0.180823. These are recorded as **results attributed to the auditor, not reproduced in this receipt**: the instruction supplies neither their implementation, initialisation nor exact hysteresis rule. They do not justify claiming that no filter could work; they describe only the candidates reported. They are not mixed into the canonical table or used to change the selector or registration.

### Reconciliation with the independent audit

All losses in the requested table agree within 1e-4. Percentage reductions are compatible with rounding to three decimal places: differences up to 0.0005 percentage points; for example, H1 of the four-family average is 1.0104506% versus the reported 1.010%. P-values differ beyond 1e-4. The registered executable recipe is retained, without selecting a seed for its significance. The additional contrast with the auditor's seed separates its effect; changing the weighting as well does not reproduce the auditor's p-values:

| Contrast | Auditor-reported p | Canonical 20260908 | Canonical 20260907 | By origin 20260907 |
|---|---:|---:|---:|---:|
| Ridge recalculated in v5 (v4 reference) H1 | 0.0460 | 0.0383 | 0.0400 | 0.0361 |
| Ridge recalculated in v5 (v4 reference) H2 | 0.0023 | 0.0032 | 0.0037 | 0.0038 |
| HAR/ridge/ElasticNet average H1 | 0.0420 | 0.0355 | 0.0372 | 0.0343 |
| HAR/ridge/ElasticNet average H2 | 0.0007 | 0.0018 | 0.0016 | 0.0014 |
| Four-family average with LightGBM H1 | 0.0250 | 0.0214 | 0.0219 | 0.0200 |
| Four-family average with LightGBM H2 | 0.0028 | 0.0037 | 0.0034 | 0.0033 |

The seed explains the difference between the two canonical columns, but not the entire discrepancy with the auditor. Without the auditor's code, contrast vector and resampling indices, **the exact cause of that discrepancy cannot be confirmed**. It is not attributed exclusively to rounding or weighting. The receipt retains the complete session vectors, parameters, p-values, exceedance counts and CIs for comparison. The two-sided percentile CI does not invert the centred one-sided p-value.

### Numerical ridge drift relative to v4

| Information set | Ridge v4 | Ridge v5 | v5 − v4 |
|---|---:|---:|---:|
| B0 | 0.1836603717937846 | 0.18366037179378455 | ≈ 0 |
| B1 | 0.1820440600908625 | 0.18205096062361725 | +0.000006900532755 |
| B2 | 0.1809103004317701 | 0.18091349242944227 | +0.000003191997672 |

LightGBM agrees to eight decimal places in B0/B1/B2 (CSV rounding differences). Part 34 attributes ridge drift to Gram in technical amendment 1. Code review does not substantiate that attribution: `precompute=True` is introduced for ElasticNet in `artifacts/rp4_v5_a2_code/models.py::_elastic_candidate`; ridge still calls `artifacts/rp4_v3_code/models.py::fit_ridge`, which already calculated Gram. This audit without refits does not isolate the exact causal source of the millionths. The measured difference is disclosed; its cause is not invented and recalculated ridge is not presented as an identical reproduction of v4.

### Prospective registration and receipt for this sensitivity

[Decision 136](prospective_combination_decision_136.md), SHA-256 `e500c487b015b7662c52a7f381180996d740c88d1d317debf594330c3ddf15b0`, adds top2 and the four-family combination as secondaries; v4 remains primary. Reads 20/40/45/335 retain their exact cohorts and H1→H2 rules; 45 = 25 historical + 20 prospective. The registration was sealed before any prospective read in this task, without asserting third parties' knowledge.

Evidence is in [summary.json](../../artifacts/rp4_v5_part34/summary.json), the [table](../../artifacts/rp4_v5_part34/table.csv), [receipt with hashes](../../artifacts/rp4_v5_part34/public_receipt_v3.json) and [reproducible producer](../../artifacts/rp4_v5_part34/audit.py). The [previous report](../archive/rp4/presentation_originals/v5_before_part34_results_v5.md.original.public) is preserved byte for byte, alongside snapshot 5_control and its receipts. The old publication routine reconstructs only that earlier report: this section is restored by `artifacts/rp4_v5_part34/publish.py`, without changing frozen results.
