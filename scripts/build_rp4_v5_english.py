"""Render English copies of closed historical documents; no model or data execution.

Only the four named Markdown originals and their custody map are read. The default
checks the public copies; --write regenerates those four presentation files.
"""

# Full translated paragraphs are intentional presentation literals.
# ruff: noqa: E501

from __future__ import annotations

import argparse
import importlib
import json
import os
import re
from pathlib import Path
from urllib.parse import urlsplit

_archive_sources = importlib.import_module("scripts.rp4_archive_sources")
assert_historical_sha256 = _archive_sources.assert_historical_sha256
original_path = _archive_sources.original_path
public_path = _archive_sources.public_path

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / "docs/archive/rp4/presentation_originals"
LABEL = "**English translation. Historical seals refer to the preserved original bytes.**"

TRANSLATIONS = {
    "results_v5.md": {
        0: "# RP4 v5 — registered exploratory extension: attempt A3, technical amendment 2",
        1: "Status: **COMPLETE**. Updated: 2026-09-08T15:31:33.840073+00:00. RV15 only.",
        3: "## Coverage and progress",
        4: "Exact calendar of 419 sessions from preflight A1. The same keys, targets and B0/B1/B2 sets are retained. PARTIAL contains completed sessions only; families may cover different dates and no winner is declared from that incomplete sample.",
        6: "## Metrics by family and information set",
        7: "QLIKE and MAE average origins within asset/session and give equal weight to assets and sessions. RMSE takes the square root after averaging squared error.",
        9: "MLP: deferred for cost, not evaluated in this A3 run. Its state is DEFERRED_COST_NOT_EVALUATED_IN_THIS_RUN; neither losses nor selection frequencies are imputed. A1 did fit the network in a partial component, and A2 fitted it in the memory/GPU test session. There is no claim that it was never evaluated. RV5 and RV30 remain deferred.",
        10: "## Historical reference v4, RV15",
        12: "The comparators retain all 419 sessions. A PARTIAL table is not a paired comparison against them. v4 retains the headline; there is no direct v5/v4 test.",
        13: "## Selector and inference",
        14: "The selector and top2 ensemble use the five families: persistence, HAR, ridge, Elastic Net and LightGBM. They are chosen exclusively by temporal-validation QLIKE, with ties broken in that order; top2 averages levels with weights 0.5/0.5. They are calculated only when the five families complete all 419 sessions.",
        17: "H1→H2 is retained: H2 opens only after positive rejection of H1 at 5%. Its nominal p-value is disclosed even when the gate remains closed. Each chain uses max(pH1,pH2), Holm across the two selectors and Bonferroni ×5 as the declared bound across versions. Session bootstrap: block 5, 9,999 repetitions, seed 20260908; two-sided pointwise 95% intervals. Cost amendments are disclosed historical reads; ×5 does not correct all adaptive search or turn these results into prospective confirmation.",
        18: "Nominal RV15 B2/B1 selector rule: NOT_SATISFIED. It requires positive delta, one-sided p <0.05 and a 95% interval excluding zero. It is reported separately from H1 and Holm results.",
        19: "## Selector frequencies and deferred family",
        21: "## Elastic Net: candidates and exclusions by stage",
        23: "### Exclusions by session",
        24: "NOT AVAILABLE.",
        25: "## Cost, environment and custody",
        26: "[Technical amendment 2](specification_v5_technical_amendment_2.md). LightGBM returns to the frozen CPU producer rp4_v2_code.models.fit_lightgbm, with leaves [15,31,63], seed 20260908 and deterministic=True. A3 neither fits MLP nor uses GPU.",
        27: "Part 18 reported approximately 193 seconds per session for LightGBM GPU in A2 and RV15 extrapolations of 22.49 h for LightGBM GPU and 28.22 h for MLP GPU. These are A2 measurements/extrapolations, not observed A3 times; they motivated the reduction in scope. The subsequent instruction fixes a 15% memory margin: 0.85 of allocatable memory is used to calculate shards from the newly measured peak.",
        29: "Attempts A1/A2, their seals, tests and receipts are preserved. The A3 execution is independent of the chat, retains per-session receipts and updates progress.json at least every five minutes. Each publication saves an immutable snapshot and receipt.",
        31: "Calendar SHA256: 284b64adef635ce2db53a8ea54fedac981feaeece13b6161d8464bd886b5d925. Records SHA256: 0e846be59bdfecc48d5cb793fbe816d953ed35404172967adb85257c360006b3.",
        32: "## Operational incidents and resumptions (technical amendment 3)",
        33: "On 8 September 2026, at 21:54 Sydney time, Windows rejected replacement of progress.json (WinError 5). Execution resumed at 21:59 with 1,193 preserved receipts; subsequent verification confirmed their hashes unchanged. At 22:58:44 the same write failure recurred, preserving 1,634 receipts, including 377 for ElasticNet. The second resumption is dated and verified in artifacts/rp4_v5_a3_operations/resume_part27/verification.json.",
        34: "These interruptions involved state writing, not model fitting. The responsible reader was not identified. Technical amendment 3 implements 60 attempts separated by 250 ms, in-place writing as fallback, and a warning without interrupting calculation if both mechanisms fail. Original scientific checkpoints and seals are preserved. The underlying scientific snapshot remains immutable; report_annotation_<update_id>.json distinguishes its hash from this annotated copy's hash. LightGBM allocation is registered before starting it in lightgbm_part21.json.",
        35: "## Post hoc sensitivity: combining instead of selecting",
        36: "**POST HOC.** Procedures chosen after seeing historical results; the following p-values do not control the search or replace the v4 headline or registered selector. Only saved forecasts are combined, without refitting models. Verification covered 2,095 records/receipts and all 419 sessions, with common keys and targets. Recalculated losses of the five families and two selectors agree with the closed report: maximum absolute error 4.44e-16. B0 frequencies are reproduced: LightGBM 203, ElasticNet 119, ridge 68 and HAR 29. No selector error is detected.",
        37: "The combination is the arithmetic mean of positive levels before QLIKE. The canonical producer is used: equal weights by asset/session, then by session; circular bootstrap with block 5, 9,999 resamples, historical v5 seed 20260908, centred null, +1 correction, one tail. H1 compares B1/B0; H2 compares B2/B1. Reduction = 100 × mean(baseline − expanded loss) / mean(baseline loss).",
        39: "The four-family average has the lowest B2 QLIKE among the procedures in this historical comparison: 0.999% below original v4 ridge and 0.629% below top2, calculated as 100 × (1 − combination QLIKE / reference QLIKE). This does not demonstrate statistical superiority between models or prospective success. The three nominal chains in this sensitivity pass H1→H2, without correction for their post hoc search.",
        40: "### Diagnosis and scope",
        41: "B2 gap = realised loss minus internal-validation QLIKE, averaged across sessions. Validation uses equal weights by asset/session; the second column changes only realised loss to equal weights per origin within session and reproduces the auditor's approximate figures:",
        43: "This documents relative historical validation optimism for LightGBM and pessimism for HAR/ridge. It is compatible with selection being too favourable to trees in this sample; it does not prove a universal causal bias from ten-session windows. Diversity can be used by averaging forecasts, without requiring the daily winner to be identified correctly.",
        44: "The ex post oracle takes the lowest loss among the **five** families per session, including persistence: canonical B2 0.174352218 versus the best fixed family, HAR, at 0.180678912. With realised loss weighted by origin: 0.174274154 and 0.180609128, reproducing the auditor's 0.1743 and 0.1806 after rounding. This is a bound with knowledge of the outcome, not a strategy available before the session. Persistence is not excluded from the oracle.",
        45: "Part 34 also reports these post hoc filters with weighting by origin: selection by previous realised QLIKE over 10/20/40/60 sessions, 0.1833/0.1834/0.1811/0.1809; hysteresis 0.002/0.005/0.01, 0.1834/0.1833/0.1819; selector among three linear families, 0.1810; fixed-ridge reference, 0.180823. These are recorded as **results attributed to the auditor, not reproduced in this receipt**: the instruction supplies neither their implementation, initialisation nor exact hysteresis rule. They do not justify claiming that no filter could work; they describe only the candidates reported. They are not mixed into the canonical table or used to change the selector or registration.",
        46: "### Reconciliation with the independent audit",
        47: "All losses in the requested table agree within 1e-4. Percentage reductions are compatible with rounding to three decimal places: differences up to 0.0005 percentage points; for example, H1 of the four-family average is 1.0104506% versus the reported 1.010%. P-values differ beyond 1e-4. The registered executable recipe is retained, without selecting a seed for its significance. The additional contrast with the auditor's seed separates its effect; changing the weighting as well does not reproduce the auditor's p-values:",
        49: "The seed explains the difference between the two canonical columns, but not the entire discrepancy with the auditor. Without the auditor's code, contrast vector and resampling indices, **the exact cause of that discrepancy cannot be confirmed**. It is not attributed exclusively to rounding or weighting. The receipt retains the complete session vectors, parameters, p-values, exceedance counts and CIs for comparison. The two-sided percentile CI does not invert the centred one-sided p-value.",
        50: "### Numerical ridge drift relative to v4",
        52: "LightGBM agrees to eight decimal places in B0/B1/B2 (CSV rounding differences). Part 34 attributes ridge drift to Gram in technical amendment 1. Code review does not substantiate that attribution: `precompute=True` is introduced for ElasticNet in `artifacts/rp4_v5_a2_code/models.py::_elastic_candidate`; ridge still calls `artifacts/rp4_v3_code/models.py::fit_ridge`, which already calculated Gram. This audit without refits does not isolate the exact causal source of the millionths. The measured difference is disclosed; its cause is not invented and recalculated ridge is not presented as an identical reproduction of v4.",
        53: "### Prospective registration and receipt for this sensitivity",
        54: "[Decision 136](prospective_combination_decision_136.md), SHA-256 `e500c487b015b7662c52a7f381180996d740c88d1d317debf594330c3ddf15b0`, adds top2 and the four-family combination as secondaries; v4 remains primary. Reads 20/40/45/335 retain their exact cohorts and H1→H2 rules; 45 = 25 historical + 20 prospective. The registration was sealed before any prospective read in this task, without asserting third parties' knowledge.",
        55: "Evidence is in [summary.json](../../artifacts/rp4_v5_part34/summary.json), the [table](../../artifacts/rp4_v5_part34/table.csv), [receipt with hashes](../../artifacts/rp4_v5_part34/receipt.json) and [reproducible producer](../../artifacts/rp4_v5_part34/audit.py). The [previous report](../../artifacts/rp4_v5_part34/results_v5_before_part34.md) is preserved byte for byte, alongside snapshot 5_control and its receipts. The old publication routine reconstructs only that earlier report: this section is restored by `artifacts/rp4_v5_part34/publish.py`, without changing frozen results.",
    },
    "specification_v5.md": {
        0: "# RP4 v5 — family tournament with selection within training",
        1: "Owner: Miguel. Authorisation: 2026-09-08, 17:00 Australia/Sydney; decision 134 in `docs/methodology_decisions.md`. Complete instruction: locally preserved tournament authorisation, SHA-256 `6fe35ddedcbafc871306a09a10756533bea7f6a37c199fd191a51167f71ef8d0`. RESEARCH_ONLY; NOT INVESTMENT ADVICE; capital_go=false.",
        2: "## Registration, estimand and previous closeout",
        3: "v5 is a new development stage; it does not modify the “there is no v5” closeout of programme v4, its artifacts or its pre-declared-test status. It is reported as a fifth read of the same historical windows, with Bonferroni ×5 as a declared bound. Causal training by session does not make adaptive development untouched. Inference is retrospective for the selector procedure fixed here; it is neither an independent replication nor control of every earlier search decision.",
        4: "The primary estimand is the paired QLIKE delta B1/B0 and B2/B1 of the primary selector at RV15 on development. v4 retains the headline until a prospective replication supports v5. The original proposal, section 4.4, is quoted under the owner's authorisation: “model choice will follow benchmark performance and simplicity”; no independent documentary verification of that quotation is claimed.",
        5: "## Data, predictors and time",
        6: "The executable v4 contract, SHA-256 `0a45b0a608110e2ca0dcf38accc2a0c2521ebbe9d223eb002e36ec51f78afd04`, and effective v3 contract, SHA-256 `930f3ddb6ef6284f1129dda26ed705699a666ade005c6ad363cb67864794e6f5`, are inherited. The v5 JSON enumerates literally the same predictors, transformations, required and optional variables, and assets: AAPL, AMZN, META, MSFT, NVDA and TSLA. B0 ⊂ B1 ⊂ B2 have **29/69/138** predictors plus five asset fixed effects. SPY/QQQ remain previously registered controls; the universe is not expanded. The tournament chooses families and their parameters, never a list of variables using results.",
        7: "Panel: locally preserved base panel, SHA-256 `a63ff5e61092d2bc00917c5de4e0e73f928005acc475f46370348eaca6ad4637`. RV15/RV5 targets: locally preserved target panel, SHA-256 `b2357a10a8a4955499e94b576b7853129e957ad70702da09bebbc9b6befd35db`. RV30 is `rv30` from the base panel. Join one to one by asset, session and origin minute, not by position. Retain exactly v3 eligibility, including valid RV30, authorised NaNs, presence/empty-window indicators and quality controls. An invalid selected target on an eligible row stops execution. Targets and prices are not imputed, and rows are not excluded based on a family's performance.",
        8: "Partition: **2026-08-01**. Only sessions 2024-08-02–2026-07-31 are read through a Parquet filter. First 60 sessions: warm-up. Inherited schedule: 419 sessions, 2024-10-28–2026-07-31. Sessions without eligible origins are recorded using the same inherited rule and do not count as zero losses. Both the scheduled calendar and number actually evaluated are reported. Neither the subsequent window is evaluated here nor prospective data read.",
        9: "Expanding walk-forward, pooled assets and equal weights per origin during fitting. Reuse `causal_masks`: train requires an earlier date and original RV30 target end ≤ first evaluated origin −60 minutes. Validation: last ten eligible train sessions; inner_fit excludes those ten and requires RV30 end ≤ first validation origin −60 minutes. Purge/embargo: 60 minutes. PIT: source-time proxy **120 seconds**; it does not prove historical client receipt. Retain the UW gap 2025-01-25–2025-02-24 without filling it.",
        10: "## Fixed horizons and families",
        11: "RV15 is primary; RV5 is a registered secondary; RV30 is reported for the proposal's questions. RV3/RV1 are excluded without searching their results. The three horizons use the same conservative RV30 mask and the same information sets.",
        12: "Each family produces validation forecasts from inner_fit, chooses parameters using only those ten sessions and refits on complete train to forecast the next session. Selection QLIKE is the asset/session mean followed by an equal mean across sessions. Neither bounds, preprocessing nor refitting consult the evaluated session's target.",
        13: "| Family / key | Fixed grid and rule |\n| --- | --- |\n| Seasonal persistence / `seasonal_persistence` | K ∈ [1,5,20]. Arithmetic mean of targets from the last K available sessions for the same asset and origin minute within the fitting mask. If the group is missing, use the asset's fitting mean; if that is also missing, use the global fitting mean. Floor 1e-12. Tie: smaller K. By definition this reference ignores additional regressors and is identical in B0/B1/B2; it does not change other models' lists. |\n| Augmented log-linear HAR-RV / `log_har` | HAR-X/HARQ log-OLS over the full registered set, including HAR lags, rq_attenuation and controls; it is not presented as classical HAR with three regressors. Unpenalised least squares with tolerance 1e-10, unrestricted intercept, Duan and training bounds. Model without hyperparameters: singleton grid. |\n| Current logarithmic ridge / `log_ridge_harq` | Reuse `rp4_v3_code.models.fit_ridge` unchanged; lambda [0.0001,0.01,1,100,10000], ties favour larger lambda. |\n| Logarithmic elastic net / `log_elastic_net` | scikit-learn ElasticNet; alpha [0.0001,0.01,1] × l1_ratio [0.1,0.5,0.9]; cyclic selection, max_iter 10000, tol 1e-6, intercept. Tie: grid order. Numerical non-convergence does not authorise silently dropping a candidate. |\n| LightGBM QLIKE / `lightgbm_qlike` | Reuse `rp4_v2_code.models.fit_lightgbm` unchanged: leaves **[7,15,31,63,127]**, expanded from [15,31,63]; learning rate 0.05, minimum 100/leaf, max_bin 63, maximum 2000 rounds, patience 50, seed 20260908, CPU 4 threads, deterministic, force_col_wise, feature_fraction=bagging_fraction=1. Tie: fewer leaves and rounds. Init score log(mean fitting target), applied once only. |\n| Small dense network / `mlp_log` | scikit-learn MLPRegressor; layers [(32),(64,32)] × alpha [0.0001,0.01], ReLU, Adam, batch_size 1024, learning_rate_init 0.001, max_iter 100, shuffle=False, random_state 20260908, early_stopping=False, n_iter_no_change 20, tol 1e-4. No internal random split. The training-loss criterion may stop before the maximum; reaching the limit is reported as budget reached, without excluding the candidate. Tie: grid order. CPU for every final run. |\n| Ensemble / `ensemble_top2` | Arithmetic mean of forecasts in levels from the two best individual families by validation QLIKE. Choose two different families, not two hyperparameters of one family. Fixed weights 1/2, no meta-fitting. This is the secondary selector; it does not compete again against the six families in the primary. |",
        14: "The linear families and MLP use inherited pointwise transformations and v3 `_ridge_design`: fitting-only medians for optional variables, explicit presence, fitting population mean/standard deviation, winsorisation ±5, removal of zero variance and pivoted QR with tolerance 1e-10. An optional column never observed is removed without fabricating a median. Rank selection addresses identifiability only, not supervised variable search. Elastic net and MLP use slopes without duplicating their own intercept. MLP's log target is centred/scaled using its fitting mean and standard deviation; if the deviation is zero, use divisor one. Reverse this before Duan. HAR, ridge, elastic net and MLP use Duan with fitting residuals and bounds [0.5×P1,2×P99] from that fit's selected target (linear quantiles). Bounds and preprocessing are recalculated separately in inner_fit and train. LightGBM retains inherited native NaNs, log clip [-30,30] and floor 1e-12. If QR leaves zero slopes, ElasticNet/MLP receive a technical zero column to retain the estimator with an intercept, without inventing an observed variable. BLAS threads are also limited to four with threadpoolctl. ElasticNet precomputes the Gram matrix (`precompute=True`) to reduce iteration cost on large training samples while retaining the registered objective.",
        15: "## Selector and inference",
        16: "For each session, information set and horizon, `selector_primary` chooses the family with the lowest `selected.validation_qlike`. Exact ties follow the six families' order in the table. The chosen candidate and ranking of the top two are retained; the evaluation session determines neither. The secondary selector is `ensemble_top2`. Each selector is one procedure, not six tests selected afterwards.",
        17: "QLIKE = y/f − log(y/f) −1. MAE in levels; RMSE = square root of the weighted mean of squared errors. Average first across origins within asset/session, then equally across assets present in the session, then equally across sessions. Delta = baseline − expanded loss; reduction % = 100×mean(delta)/mean(baseline loss).",
        18: "Circular bootstrap with five-session blocks, 9999 resamples, seed **20260908**, centred null, +1 correction, one-sided p-value and two-sided 95% percentile CI; minimum ten sessions, declared degeneracy, no tail removal. Reuse v3 `session_contrast` with explicit parameters. No IID bootstrap of origins.",
        19: "Within each selector: H1 B1/B0 followed by H2 B2/B1, one-sided at 5%, positive effect; H2 can be promoted only after H1. Both nominal p-values and intervals are shown, with H2 closed if H1 does not pass. For **Holm across the two selectors**, register each chain's joint claim through q_s=max(p_H1,p_H2); apply Holm to the two q_s and require both positive signs. This controls joint hierarchy claims across selectors; it does not promise global control of each isolated H1. Report p_Holm_chain and min(1,5×p_Holm_chain), as well as min(1,5×p) for each contrast as a descriptive bound across versions. RV5/RV30 and family tables are secondary/descriptive; they are not promoted according to their results.",
        20: "**Decision rule fixed now:** v5 “improves on v4” only if the primary selector's B2/B1 delta at RV15 is positive, one-sided p <0.05 and the 95% CI excludes zero. Report separately whether that nominal condition also passes H1 and chain Holm; meeting only the nominal criterion does not support a global hierarchy claim. This label means meeting the owner's rule for the B2/B1 increment, not a direct test of performance differences between versions. Even if it is met, v4 retains the headline until prospective support. If it is not met, report the tournament without replacing anything. Nothing is refitted after reading.",
        21: "## Screening, cost and execution",
        22: "The owner's direct message permits GPU screening and first requires a sealed decision and specification. The route adopted has no prior adaptive screening: all preceding configurations are fixed by design. **Closed archive drawer: configurations tested to choose this grid before sealing = none; GPU screening = not executed.** No other engine will be installed to replace CPU estimators. The RTX 5090 Laptop is present; PyTorch is not installed in the inherited environment. GPU performance is not attributed to a CPU execution.",
        23: "Initial estimate communicated before fitting: **6–18 hours**, provisional. Measured basis: v4 RV15/development, 2940.2563865 seconds =49.0043 minutes for eight shards. Approximate tree extrapolation: 49.0043×3 horizons×5/3 =245.0215 minutes (4.0837 hours). Added network/elastic-net cost and the load of other tasks have not yet been measured; they explain the range, which is no guarantee. A timing measurement after sealing may refine it, never change the grid. The estimate is communicated again with its hash before launching the complete run.",
        24: "Deterministic CPU, eight disjoint shards by session (calendar index i with i%8), at most four threads per estimator, fixed seeds; each shard retains all permitted history. Horizon order: RV15, RV5, RV30. Numerical libraries and versions, code and input hashes are fixed in the release before the run. No prospective models or data, training downloads, new automations, push or writes outside the authorised worktree.",
        25: "Components/sessions are written once with keys, selection, masks, input, target, code, specification and hash receipt. Resume only intact artifacts from the same release; do not overwrite results or repeat a complete read. A failure stops its shard, is preserved and reported. Synthetic tests verify causality, poisoning of the evaluation target, validation-only selection, determinism, equal masks, contracts/hashes and aggregation. Synthetic tests are not equivalent to complete evaluation.",
        26: "## Universe and prospective work",
        27: "`docs/rp4/v5_universe_feasibility.md` is not part of the public release; its historical citation is retained. It is the availability, timing and quota appendix for the two RP4 providers. Its receipt and hash are bound to the seal before running. SPY/QQQ are not added without a further written decision from Miguel. Endpoint support or sampling does not establish exhaustive coverage of the window.",
        28: "Prepare `docs/rp4/prospective_confirmation_v1_amendment_4_draft.md` **without sealing**; the draft is not part of the public release and its historical citation is retained. It places the primary v5 selector as an additional secondary prospective test and v4 primary. It is linked to this specification's hash; any eventual seal must precede any prospective read. This work neither opens prospective data nor consumes a read or authorisation from existing registrations.",
        29: "## Required deliverables",
        30: "`docs/rp4/results_v5.md`: complete family × information set × horizon table with QLIKE, MAE, RMSE, counts and v4 comparison in the same table (RV30: v3 as reference; v4 did not execute RV30); selection frequencies, deltas and intervals for both selectors, nominal/Holm/Bonferroni p-values and chronology of every incident. `artifacts/rp4_v5_*/` artifacts: executable specification, receipts, costs, contracts, per-file hashes, private forecasts and reproducible aggregates. Integration note for defence revision 3. Other tasks' packages are not altered.",
    },
    "specification_v5_technical_amendment_2.md": {
        0: "# RP4 v5 — technical amendment 2, attempt A3",
        1: "Miguel, 2026-09-08. Parts 18→17→17b read completely in that order and subsequent direct message: 15% memory reserve. New registration before the CPU probe and relaunch. RESEARCH_ONLY; NOT INVESTMENT ADVICE; capital_go=false.",
        2: "Decision 134, specification v5, A1, amendment 1/A2 and their results are preserved byte for byte. The previous registration is not reinterpreted. v4 retains the headline; v5 remains historical development with disclosed cost amendments.",
        3: "## Authorised changes and scope of this run",
        4: "RV15 only and five families, in this order: seasonal persistence, log-HAR, log-ridge-HARQ, log-ElasticNet and LightGBM-QLIKE. The selector and top2 ensemble use only these five families. The dense network is **deferred for cost, not evaluated in A3**; metrics and frequencies are unavailable, never zero performance. A1 did have a partial fit and A2 a network probe: both are disclosed. RV5/RV30 are deferred; any subsequent network appendix requires results separate from the current five and is outside this launch.",
        5: "LightGBM returns to the original CPU producer `rp4_v2_code.models.fit_lightgbm`, v4 grid `[15,31,63]`, `deterministic=True`, the other v5 parameters unchanged and seed 20260908. Threads per estimator=floor(32/F). A2 GPU measured 193.2075962 s per session with all three information sets and extrapolated 22.49 h for RV15; the network measured 242.4896918 s and extrapolated 28.22 h. GPU is dropped for cost. The cited v4 comparison (~19 s per session and set) has a different measurement scope: no speedup is attributed before observing the new CPU probe.",
        6: "ElasticNet retains `precompute=True`, `max_iter=500000`, `tol=1e-6`, cyclic selection, alpha=[0.0001,0.01,1] and l1_ratio=[0.1,0.5,0.9]. A1 already precomputed Gram; it is not a new improvement attributable to A3. A2 exclusions for non-convergence are inherited only for alpha 0.0001, with stage/cause/iterations/dual gap and the next convergent candidate in the same internal ranking for refit. Other alpha values do not receive that exception. All cells are recorded. MLP configurations inherited in JSON are a parameter archive for the appendix; the adapter rejects fitting them in this run.",
        7: "## Scientific invariants",
        8: "No changes to assets, panels, B0/B1/B2 (29/69/138 variables), eligibility, common RV30 mask, PIT 120 s, partition 2026-08-01, warm-up of 60 sessions, 419 development sessions, purge of 60 min or internal validation over 10 sessions. Only train|test is materialised; each selection/preprocessing uses only earlier training/validation. QLIKE, equal asset/session aggregation, circular bootstrap block 5/9999/seed 20260908, H1→H2, Holm across two chains and Bonferroni×5 bound are retained. This bound does not correct all adaptive search; no amendment turns development into prospective confirmation.",
        9: "## Memory and registered estimate",
        10: "A2 matrices and targets are verified by SHA256 and opened as read-only mmap shared across processes; only the session window and required information set are copied. Memory is released between sets and sessions. Torch is not loaded. Probe: RV15/2026-07-31, five families and B0/B1/B2, 32 threads, CPU affinity 0–23. Its predictions are not reused as tournament records. Peak is the process's maximum working set, corroborated by RSS samples every 10 ms.",
        11: "Allocatable=min(free physical RAM, free Windows commit). The direct message replaces 0.7 with 0.85: **F=min(8,floor(0.85×allocatable/measured peak))**. Record bytes, rounding and F; if F<1, do not allocate an impossible worker. If F=1, run with 32 threads. Own CPU affinity 0–23 respects CPU 24–31 reserved by the parallel task; 32 software threads do not imply 32 available CPUs.",
        12: "Prior estimate: measured seconds per family×419/F. Reference range 1–2 times, without a promised bound; window size, threads and external load affect actual time. `execution.json` fixes F/threads/measurements; `estimate_reported.json` binds the notice to the user. Amendment and code are committed locally before the run. Parameters are not changed after observing results.",
        13: "## Unattended execution and deliverables",
        14: "Independent launch through hidden Start-Process, log under `artifacts/rp4_v5_run_a3_20260908/logs/`. `progress.json` at that root reports running/done/failed, error, time, counts by family/RV15, F/threads and ETA. Ordinary update every 10 seconds (required maximum 5 min). Per-session receipts verify identity, hash and seal; the same command resumes without refitting complete sessions. Mutual exclusion per run and shard. Up to 3 attempts per worker with every error recorded; persistent failure requires diagnosis.",
        15: "Each family publishes a partial table after 419 sessions, with snapshot/receipt/hash. Selector inference only after 419×5 records. Final control: repeat the first session RV15/2024-10-28 under another shard identity with the same F/threads for all five families; binary identity of CPU forecasts is required. CPU/GPU control does not apply to A3 because it does not fit on GPU. The A2 probe is disclosed. A final receipt is written and hourly progress, completion or failure reported.",
        16: "No prospective or sealed cohorts are read. No push. The live `results_v5.md` report is updated while retaining every previous snapshot and the A1 historical archive. Code, specification, authorisations and environment are bound by hashes in `artifacts/rp4_v5_a3/freeze.json`.",
    },
    "prospective_combination_decision_136.md": {
        0: "# Decision 136 — prospective top2 and four-family combination secondaries",
        2: "New registration authorised by Miguel through part 34 of 2026-09-09 and his instruction in this task. Its receipt and sidecar pin the bytes and local UTC time. Previous registrations, decision 134 and draft amendment 4, which remains unsealed, are not changed. These candidates were selected after observing historical development results: this is not historical confirmation.",
        3: "**v4 ridge RV15 remains primary. Top2 and the equal-weight combination of HAR, ridge, elastic net and LightGBM are secondaries registered now.** Instruction 34 explicitly extends their scope to reads 20/40/45/335; top2 is not presented as already sealed in the earlier draft 4.",
        4: "## Fixed forecasts",
        5: "For each asset/session/origin key and each B0/B1/B2 set, the combination is `(f_HAR + f_ridge + f_elastic_net + f_LightGBM) / 4`, over **positive variance levels**, before calculating QLIKE. Neither logarithms, losses nor p-values are averaged. Weights are always 0.25: they are neither estimated nor selected by session.",
        6: "Top2 retains the A3 rule: rank the five families seasonal_persistence, log_har, log_ridge_harq, log_elastic_net, lightgbm_qlike by internal-validation QLIKE, with that same order for ties, and average the two selected forecasts in levels with weights 0.5. Selection and hyperparameters use only the last ten sessions of causal training; never losses from the predicted session or aggregate prospective performance.",
        7: "Both secondaries inherit the complete A3 scientific contract `artifacts/rp4_v5_a3/specification.json`, SHA-256 `a318736f7e5a08e21c089b59ec90aae1c5bccb015cb6d286bb59dd078fd2ee3e`, and the producers fixed by `artifacts/rp4_v5_a3/freeze.json`, SHA-256 `69db4672b7ad705300c820b42abb8f8430d8380a3f0360e2d1008b7b10b7f855`. Grids, transformations, calibrations and bounds per family are retained, ElasticNet with precomputed Gram, max_iter 500000 and tolerance 1e-6, CPU LightGBM with the v4 grid and A3 scientific seeds. The deferred network is not added. Prospective inference uses seed 20260907 from the prospective registration, different from seed 20260908 of the historical v5 report.",
        8: "Scope: RV15; nested sets 29/69/138; six assets AAPL, AMZN, META, MSFT, NVDA and TSLA; inherited common masks, source PIT proxy of 120 s, purge/embargo of 60 minutes and expanding training. Neither assets nor horizons are expanded. Each family retains its causal learning, and earlier targets enter only when observable under the registered masks. If a forecast is missing or fails integrity, weights are not redistributed and families are not replaced: the affected read is UNVERIFIABLE.",
        9: "## Cohorts and reads",
        10: "The complete eligibility definition from prospective registration v1 and amendments 1–3 is incorporated. Begin with XNYS sessions from 2026-09-08, acquisition scheduled from 2026-09-09 10:00 Australia/Sydney under amendment 1. Acquisition PASS does not equal scientific eligibility. The census records absences and failures without choosing dates by losses, signs or significance.",
        11: "| Read | Exact cohort and role |\n|---|---|\n| 20 | First 20 complete prospective sessions: early consistency; v4 retains its original primary decision. |\n| 40 | First 40 cumulative prospective sessions: stability; same administrative condition of v1 fixed before opening 20; without an administrative date, scheduled upon reaching 40. Does not rescue 20. |\n| 45 | The 25 historical sessions from 2026-08-03 to 2026-09-04 and the first 20 prospective sessions, a single read upon reaching 20 new sessions. Weight 1/45 per session. These are not 45 prospective sessions; partly observed analysis. |\n| 335 | First 335 cumulative prospective sessions, excluding the 25 historical ones, once only regardless of the earlier result. Does not rewrite 20. |",
        12: "For 45, a separate manifest of HAR/ridge/ElasticNet/LightGBM forecasts and validations for those same 25 dates is required, with code and inputs frozen before calculation/reading. This registration neither claims that they exist nor authorises replacing them with v4 ridge losses. If they are unavailable or their provenance cannot be established, report NOT_AVAILABLE for the affected secondary, without replacing dates or turning the sample into 45 prospective sessions.",
        13: "## Inference and comparison fixed before prospective reads",
        14: "QLIKE = y/f − log(y/f) − 1; mean across assets within session and equal weights across sessions. Delta = baseline − expanded loss; percentage reduction = 100 × mean(delta) / mean(baseline loss). Each candidate and read applies the same sequence **H1 B1/B0 → H2 B2/B1**, with a positive estimand and one-sided p ≤ 0.05 required for rejection; H2 opens only after H1 rejects in that same sample. If H1 fails, H2's p-value is diagnostic only. No CI-based requirement is added. Circular session bootstrap, five-session blocks, 9,999 resamples, seed 20260907, centred null and +1 correction; two-sided 95% percentile CI. `artifacts/rp4_v3_code/inference.py::session_contrast` is inherited unchanged.",
        15: "Each new secondary has its own separate nominal sequence. It changes neither Holm A/B/C, sequence D nor the primary v4 decision. **No global control at 5% is claimed across candidates, cumulative reads or historical search**; nominal p-values do not correct post hoc candidate selection. There is no success criterion based on rejection at any of the reads, stopping for significance or additional inspections at 120/146 or other thresholds. Adverse or non-computable results are reported without discretionary repetition.",
        16: "B0/B1/B2 losses and both chains will be published for all three procedures on the same eligible keys. If the combination has the lowest prospective B2 QLIKE, it will be reported as the descriptive winner of that registered comparison, with absolute/relative differences against v4 and top2, even if it contradicts the historical ranking. This does not imply statistical superiority between models: H1/H2 evaluate information within a model. Whether its nominal chain rejects is reported separately. v4 retains the primary role, and no ranking rewrites earlier verdicts or demonstrates profitability or causality.",
        17: "## Custody",
        18: "The new receipt retains hashes of antecedents, the instruction and producers without overwriting them. Before executing prospective forecasts, a new manifest will seal inputs, calendar, code, environment and deterministic resources; new outputs, without reusing closed executions. This registration neither executes models nor opens prospective stores. This task has read only registration documents and historical results from 2024-10-28–2026-07-31. The absence of reads evidenced here is limited to this task; neither global knowledge of third parties nor current absence of data is claimed from not inspecting them. The hash and local time are neither the maintainer's signature nor an external timestamp. No push or external publication.",
    },
}

TABLE_LABELS = {
    "NO DISPONIBLE": "NOT AVAILABLE",
    "| sí |": "| yes |",
    "| campo | valor |": "| field | value |",
    "| Procedimiento |": "| Procedure |",
    "Ridge recalculada en v5 (referencia v4)": "Ridge recalculated in v5 (v4 reference)",
    "Promedio HAR/ridge/ElasticNet": "HAR/ridge/ElasticNet average",
    "Promedio de cuatro con LightGBM": "Four-family average with LightGBM",
    "| Familia | Brecha canónica | Brecha con realizado por origen |": "| Family | Canonical gap | Gap with realised loss weighted by origin |",
    "| Contraste | p informado auditor | Canónico 20260908 | Canónico 20260907 | Por origen 20260907 |": "| Contrast | Auditor-reported p | Canonical 20260908 | Canonical 20260907 | By origin 20260907 |",
    "| Conjunto |": "| Information set |",
}


def translated_document(name: str) -> str:
    sources = json.loads((ARCHIVE / "original_paths.json").read_bytes())
    entry = sources["docs/rp4/" + name]
    logical = ROOT / "docs/rp4" / name
    assert_historical_sha256(logical, entry["sha256"])
    original = original_path(logical).read_bytes()
    blocks = re.split(r"\n\s*\n", original.decode("utf-8").strip())
    translated = []
    for index, block in enumerate(blocks):
        if index in TRANSLATIONS[name]:
            block = TRANSLATIONS[name][index]
        elif block.startswith("|"):
            for old, new in TABLE_LABELS.items():
                block = block.replace(old, new)
            if name == "results_v5.md" and index == 28:
                # Local executable roots add no scientific evidence; retain binary identity.
                block = re.sub(r'("path":\s*)"[^"\n]*"', r'\1"LOCAL_LIGHTGBM_LIBRARY"', block)
                block = re.sub(
                    r'(\| python_executable \| )"[^"\n]*"',
                    r'\1"LOCAL_PYTHON_EXECUTABLE"',
                    block,
                )
            if name == "results_v5.md" and index == 51:
                block = re.sub(r"(?<=\d),(?=\d)", ".", block)
        elif block.startswith(("RESEARCH_ONLY", "Binding: {")):
            pass
        else:
            raise ValueError(f"Untranslated block: {name}:{index}")
        translated.append(block)
    translated.insert(1, LABEL)
    text = "\n\n".join(translated) + "\n"

    def locate(match: re.Match[str]) -> str:
        target = urlsplit(match[2])
        if target.scheme or target.netloc or not target.path:
            return match[0]
        path = public_path(logical.parent / target.path)
        relative = Path(os.path.relpath(path, public_path(logical).parent)).as_posix()
        return match[1] + "(" + relative + ("#" + target.fragment if target.fragment else "") + ")"

    return re.sub(r"(!?\[[^\]]*\])\(([^)]*)\)", locate, text)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    for name in TRANSLATIONS:
        expected = translated_document(name)
        destination = public_path(ROOT / "docs/rp4" / name)
        if args.write:
            destination.write_text(expected, encoding="utf-8", newline="\n")
        elif destination.read_text(encoding="utf-8") != expected:
            raise SystemExit(f"English presentation differs: {name}")
        print(name)
    if args.write:
        import hashlib

        receipt_path = ROOT / "docs/rp4/v5_translation_receipt.json"
        receipt = json.loads(receipt_path.read_bytes())
        for row in receipt["documents"]:
            row.setdefault("translation_source_english_sha256", row["english_sha256"])
            row["english_sha256"] = hashlib.sha256(
                (ROOT / row["path"]).read_bytes().replace(b"\r\n", b"\n")
            ).hexdigest()
        for name in receipt["presentation_and_contracts_sha256"]:
            receipt["presentation_and_contracts_sha256"][name] = hashlib.sha256(
                (ROOT / name).read_bytes().replace(b"\r\n", b"\n")
            ).hexdigest()
        for key in ("verification", "latest_focused_verification"):
            receipt[key]["scope"] = (
                "Historical focused translation checks before final projection; "
                "current candidate gates are reported separately."
            )
        receipt["current_presentation_hash_scope"] = "LF-normalized text, matching Git text attributes"
        receipt_path.write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", "utf-8", newline="\n"
        )


if __name__ == "__main__":
    main()
