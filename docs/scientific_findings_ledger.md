# Scientific findings and their current meaning

The program has produced null, adverse and conditional positive results. RP4 v4 is
the current public presentation; earlier results retain their own sample, estimand,
measurement version and inference rule. None of the findings establishes trading
profitability or a universal causal mechanism. A later result does not erase an
earlier null or turn an exploratory comparison into replication.

## RP2: nulls, corrections and scope

The [canonical state](../data/CANONICAL_STATE.json) retains the historical bundle's
machine status `HISTORICAL_MEASUREMENT_NOT_CURRENT_CLAIM` and reason
`SUPERSEDED_BY_PIT_V22_SUCCESSOR_V2`. The README preserves its identity and explains
that its measurements are superseded; these machine labels belong in this ledger.

| Finding | Evidence and quantity | Status today and connection to the next step |
| --- | --- | --- |
| Original prospective nested comparisons were null | [Historical reconciliation](results_reconciliation_v2.md), [methodology decision 53](methodology_decisions.md) | Retained historical null. Later sample reuse cannot change its evidentiary status. |
| Validation did not establish forecast improvement | [RP2 final report, section 2.3](rp2/FINAL_REPORT.md#23-null-and-negative-findings) reports null/adverse comparisons across the tested families. | Historical measurements, with later repair/supersession markers. Motivates separating information sets and valid chronological evaluation; it does not prove zero information. |
| Discovery DML did not replicate in validation | [Corrected Block 7](rp2/block7_dml_v1.md): joint p = 9.673e-17 in discovery, 0.832088 in validation. | Exploratory, model/sample dependent. The older headline p = 3.0 × 10⁻⁴⁶ and its replication narrative are superseded, not current evidence. |
| Apparent replication depended on defective panels | [Superseded-results register](rp2_v3/SUPERSEDED_RESULTS.md) records grid, duplicate-origin, information-set and spot-cutoff defects. | Withdrawn claims remain documented. Corrected producers, not a favorable old p-value, determine admissible comparisons. |
| Market controls can worsen a forecast | [RP2 final report](rp2/FINAL_REPORT.md): historical same-row B0 QLIKE 0.12801 → 0.14072 after controls. | Historical diagnostic; adding information is not a guarantee of improvement. It is not an ablation of RP4 v4. |
| Strong baseline matters | [Block 4](rp2/block4_b0_baseline_v1.md) compares B0 with persistence, intraday mean, EWMA, HAR and GARCH. | Retain competitive baselines and corrected EWMA/market features. Performance against an artificially weak baseline is insufficient. |
| RV60 versus RV30 is sample-dependent | [Target comparison](rp2/block3_target_validation_v1.md), [historical target decision](target_horizon_decision.md). | Historical RP2 diagnostic. It is neither a pending target decision nor proof of an optimal RP4 horizon. |
| Trade-selected option surfaces distort skew | [Independent surface diagnostic](rp2/block5b_independent_surface_v1.md): slope −0.2485 versus −0.4611; historical report describes about 46% flattening. | Measurement/proxy limitation. An observed option-state contribution does not validate every surface characteristic. |
| Flow/jump hypotheses were not supported uniformly | [RP2 final report](rp2/FINAL_REPORT.md): core jump DML p = 0.164 / 0.224; delta-log-RV residuals coincide with log-RV residuals once trailing RV is partialled out. | Historical null and non-distinct estimand. Do not count algebraically identical endpoints as independent corroboration. |
| Decomposing the target did not rescue predictability | [RP2 final report](rp2/FINAL_REPORT.md): continuous variance and semivariances; upside/downside comparison. | Historical negative diagnostic. RP4's shorter horizon answers a different question. |
| Hierarchical pooling added little | [RP2 final report](rp2/FINAL_REPORT.md): between-asset variance approximately 1.4 × 10⁻⁴. | Historical measurement, subject to the documented variance-denominator correction. No general claim against pooling. |
| Economic tests found no usable value | [Block 11](rp2/block11_economics_v1.md): deflated Sharpe **probability** ≤ 0.19 in the buffer sweep, reaching 0.000 at the selective buffer; option-informed performance worsened in discovery and was mixed in validation. | Negative economic evidence for those tested rules. The bound applies to the buffer sweep, not every co-pinned economic artifact (decision 114 records discovery probabilities 0.92–0.97 elsewhere). It is a probability, not a Sharpe ratio. V4 has no validated trading-alpha result. |
| Sequential budget was not cleared | [Block 10](rp2/block10_inference_v1.md), [RP2 final report](rp2/FINAL_REPORT.md): best SPA p = 0.0070 in D and 0.0250 in V against α₃ = 0.00417; Reality Check rejected nothing. | Historical inference result. A retrospective budget sensitivity does not retroactively create preregistration. |
| Era and regime composition changed | [RP2 final report](rp2/FINAL_REPORT.md): OOS log-R² 0.796 → 0.553; discovery flow concentration near close/expiry. | Exploratory state dependence, not causal attribution and not validation replication. Motivates explicit regime limits. |
| The 537-session RP2 plan was infeasible at the proposed size | [Block 12](rp2/block12_prospective_protocol_v1.md): observed LightGBM effect +0.00322, session σ = 0.02043, α = 0.00250, nominal power 0.80 → 537 sessions. Other reported requirements: 3,209 and 14,753; nonpositive effects cannot support that calculation. | Optimistic, selection-biased historical bounds; the proposed 60–120 sessions were inadequate. These are not the inputs to the v4 power plan. |
| The 42-session direction claim was withdrawn | [Extensions 1–4](rp2/extensions_1_4_v1.md), [validation audit](rp2/VALIDATION_REPORT.md). | Winner's-curse sizing at a selected effect cannot justify a short confirmation campaign. Preserve the withdrawal. |
| Validation lacked power for many observed effects | [RP2-v3 verdict](rp2_v3/VERDICT.md), [validation audit](rp2/VALIDATION_REPORT.md). Ten of twelve contrasts were below their relevant minimum detectable effect. | Absence of evidence is not evidence of absence. Discovery/validation reuse and underpower are separate limitations. |
| Directional-utility follow-up did not justify pursuit | [Registered extension](rp2/extension_b2_directional_utility_v2.md): `DO_NOT_PURSUE`. | Negative registered development/validation closeout; no confirmatory or economic claim. |

## PIT successor and Phase 8

| Finding | Evidence and quantity | Status today and next implication |
| --- | --- | --- |
| PIT successor did not establish global edge | [Successor-v2 report](pit_v22_claims_and_limitations_v2.md): `GLOBAL_EDGE_NOT_CONFIRMED`. | Reportable after independent custody validation, without edge/capital eligibility. It is a distinct study, not a v4 replication. |
| Gamma option-state increment was positive | Same report: ΔB1 = 0.00817124731841; raw p = 0.004199580042; Holm = 0.00839916008399; development MDE = 0.00841614346016. | Positive but below its MDE and family-specific. |
| Gamma flow increment was adverse and uncertain | Same report: ΔB2 = −0.00312662105094; Holm p = 0.559544045595; interval spans zero. | No supported incremental flow effect. |
| Tree option-state increment was positive | Same report: ΔB1 = 0.00417580612338; raw p = 0.002399760024; no formal Holm value in that robustness row. | Positive robustness measurement, not an additional confirmatory family. |
| Tree flow increment remained uncertain | Same report: ΔB2 = 0.00136801409755; p = 0.201779822018; interval spans zero. | No universal B2 conclusion. |
| Missing-data handling stayed conservative | Same report: missing TSLA minute had independent existence evidence, but provider bars were not substituted. | Eligibility before evaluation; no interpolation or source substitution. |
| Phase 8 was mixed and exploratory | [Bridge addendum v13](../reports/phase8a_exploratory_bridge_addendum_v13.md): `MIXED_EXPLORATORY`; the one-shot read was consumed on 2026-08-30. | The historical bridge is not still sealed and is not confirmation of v4. |
| Correcting the information clock improved validity, not overall loss | Same addendum: only one of eight B1-inclusive primary cells had lower QLIKE after correction. | Post-hoc remediation sensitivity. The audit supports no aggregation change and no causal claim. |
| B1 signs survived the Phase 8 repair, B2 uncertainty did too | Same addendum: four primary B1 signs positive; three descriptive Holm p-values below 0.05. Every conditional B2 interval crosses zero; none clears descriptive Holm. | Descriptive evidence favors option state in that specification. It does not establish incremental flow. |
| Coverage and grid validity are different | Same addendum: 180 session-assets complete; 11,700 paired origins versus 11,875 historical, with 175 inadmissible early origins removed. | Full source coverage does not imply an unchanged evaluation grid. The already consumed read counter remains one. |

## RP4 v1–v4

All version comparisons are sourced from the [40-cell aggregate table](../artifacts/rp4_closeout_figures/comparison_v1_v4.csv)
and its saved source hashes. Positive percentages mean lower mean QLIKE. v1/v2 use
bilateral Holm values; v3/v4 use the within-family one-sided H1→H2 sequence. They are
not interchangeable p-values and do not adjust the search across versions.

| Finding | Evidence and quantity | Status today and next implication |
| --- | --- | --- |
| v1 retained a severe numerical failure | RV30, 418 sessions: linear B2/B1 −167,448.32043932768% QLIKE reduction. | Adverse result retained. Later stability fixes do not retroactively validate it. |
| v2 improved coverage/stability without a flow success | 419 sessions: linear B1/B0 +1.715%, B2/B1 −8.714%; trees +2.091% / −0.063%. | Historical specification, with numerical/capacity repairs and bilateral inference. |
| v3 option-state evidence strengthened; flow narrowly missed the sequence | RV30: linear B1/B0 +1.729%, p = 0.0439; B2/B1 +0.554%, p = 0.0525. Trees +2.091%, p = 0.0053; flow −0.159%, p = 0.6631. | Reported as measured. The conditional horizon extension does not turn p = 0.0525 into success. |
| v4 option state improves the primary mean in both families | [Saved v4 statistics](../artifacts/rp4_v4_b4/primary_statistics.csv): RV15 linear +0.8800546830738928%, p = 0.039; trees +1.169968713660752%, p = 0.0135. | Positive under the registered family-specific sequence, not every period or a global family claim. |
| v4 linear flow improves the primary mean modestly | Same table: +0.622794096399778%, ΔQLIKE = 0.0011337596590923558; 95% interval [0.00033503697025205506, 0.0019321615865300122]; one-sided p = 0.0032. | Current conditional finding in 419 sessions / 160,832 origins. The saved bilateral Holm comparability p = 0.0248 is a distinct analysis. |
| v4 tree flow fails the primary mean test | Same table: −0.1147393674343757%, p = 0.628; interval spans zero. | No universal flow benefit; positive secondary statistics do not replace this result. |
| Asset stability is horizon-specific | [Robustness](../artifacts/rp4_v4_b4/robustness.csv): linear-flow signs positive in six of six assets at 15 minutes, three of six at 5 minutes. | Scope must accompany the sign count. Six assets are not six independent prospective replications. |
| RV5 remains secondary | Linear flow +0.256%, p = 0.0172; tree H1 p = 0.0608, so H2 is not formally opened despite nominal p = 0.1927. | Descriptive extension of a different estimand. It cannot replace the RV15 primary. |
| Tree medians differ from primary means | [v4 report](rp4/results_v4.md): median bilateral p = 0.0435 / 0.0038 and Holm = 0.0870 / 0.0096 at 15 / 5 minutes. | Secondary distributional result, retained alongside adverse/uncertain mean evidence. |
| Final-window sequence is unconfirmed | [Full report](rp4/results_v4.md): 25 sessions / 9,750 origins; RV15 H2 is not opened in either family. | No independent full-sequence confirmation. The historical window also overlaps earlier program knowledge. |
| Four evaluations reused the same windows | [v4 specification](rp4/specification_v4.md), [defense package](rp4/DEFENSE_PACKAGE/revision_2/correction_7/README.md). | Chronological training prevents one form of leakage; it does not erase adaptive specification search. |
| Provider outages and empty windows remain a limitation | [Final narrative](rp4/RESULTADO_FINAL.md), [saved audit](../artifacts/rp4_closeout_audit/REPORT.md): v3 recoding limits, but does not eliminate, harm. | No favorable-row filtering or silent gap filling. |
| Numerical bounds and coefficient magnitudes do not identify mechanism | Same audit: loss normalization, weak large-sample ridge penalty, correlated columns, clipping and rank pruning. | Nominal ridge is described accurately. Dealer inventory and causal hedging channels remain unobserved. |
| Market structure changes limit transportability | [Market audit](../artifacts/rp4_market_audit/REPORT.md) documents the expiry-calendar change and source-consistent extreme moves. | Event coincidence is not causal attribution; source consistency is not independent price validation. |
| Secondary convergence repairs have bounded claims | [Saved v3 secondary correction](rp4/results_v3_revision3.md), [defense](rp4/DEFENSE_PACKAGE/revision_2/correction_7/examiner_qa.md). | Calibration/numerical diagnostics retain their own status and do not alter the v4 primary means. |

## Completed linear RV15 placebo

**Status: CURRENT.** This robustness check was registered after the primary read
and does not replace the original v4 decision or provide prospective confirmation.
The [closed summary](../artifacts/rp4_robustness_public_v1/placebo_log_ridge_harq_rv15_summary.csv)
reports observed B2/B1 delta 0.0011337596590923558 QLIKE and a mean within-asset-session
shuffled-flow delta of 0.0009255190521628708: 81.63% is retained. Twelve of 50
permutations exceed the observed; empirical p = 13/51 = 0.2549019607843137 and
ascending rank = 39/51. Placebo percentiles 2.5/97.5 are
0.0004563956748538585/0.0012831122415478523, not an effect confidence interval.
Most of the gain survives the shuffle, consistent with session-level information;
the control does not identify its causal source. Timely order flow is not
demonstrated. The completed 60 / 120 / 300-second sensitivity is recorded below.
The [import receipt](../artifacts/rp4_robustness_public_v1/import_receipt.json)
binds source closure, exact CSV copies and explicitly sanitized JSON derivatives.

## Completed linear RV30 placebo

**Status: CURRENT.** The [closed summary](../artifacts/rp4_robustness_public_v1/placebo_log_ridge_harq_rv30_summary.csv)
reports observed B2/B1 delta 0.000802389659514178 QLIKE and mean within-asset-session
shuffled-flow delta 0.001210658368310869, or 150.9% of the observed increment.
Thirty-eight of 50 permutations exceed the observed, without ties:
empirical p = 39/51 = 0.7647058823529411; ascending rank = 13/51.
The joint 69-column flow block is shuffled within each asset-session, with 419 sessions per permutation,
with 20,950 fits. At 30 minutes, shuffled flow performs better on average than
aligned flow, so the control does not support a minute-by-minute alignment
advantage. This is consistent with the [registered v3 RV30 H2](rp4/results_v3.md)
not rejecting (p = 0.0525). It is not a causal decomposition, an executable
real-time information set, a joint test across horizons or a change to the RV15
headline. The [import receipt](../artifacts/rp4_robustness_public_v1/import_receipt.json)
binds exact CSV copies and declared JSON derivatives to the closed source.

## Completed 60 / 120 / 300-second source-time sensitivity

**Status: CURRENT.** The [linear RV15 contrasts](../artifacts/rp4_robustness_public_v1/pit_300_contrasts.csv)
retain the exact 120-second primary controls. At 300 seconds, B1/B0 has mean
QLIKE difference 0.0016749730376443763 (0.912%), interval
[0.0003716566564679534; 0.0035104181544605784], nominal p = 0.0342.
B2/B1 falls to 0.00035341060297070507 (0.194%), interval
[-0.00044476664487292755; 0.0011497008367131625], nominal p = 0.1948;
217 of 419 sessions favor flow, with 160,832 origins retained. Option state
remains supported; the flow interval crosses zero. This does not prove no flow
information or test the difference between cutoff effects. Stability under
conservative timing assumptions is not established; the primary decision remains
unchanged. This is post-primary source-time proxy sensitivity, not receipt proof
or prospective confirmation.

The [closed 60-second contrasts](../artifacts/rp4_robustness_public_v1/pit_60_contrasts.csv)
add B1/B0 mean QLIKE difference 0.0015451316625903163 (0.841%), interval
[0.00019280807734032142; 0.003383983561590049], nominal p = 0.0460;
B2/B1 is 0.002634716418246107 (1.447%), interval
[0.0017097048946607982; 0.0035821943155032927], nominal p = 0.0001.
There are 277 of 419 sessions favoring flow and 160,832 origins.
The flow series at 60 / 120 / 300 seconds is 1.447% / 0.623% / 0.194%
(p = 0.0001 / 0.0032 / 0.1948); state stays between 0.84% and 0.91%.
Flow decreases monotonically as the assumption becomes more conservative, a
descriptive ordering rather than a tested difference between cutoff effects.
The 60-second result does not strengthen the registered finding: historical
records cannot verify this less conservative assumption. The pattern is consistent
with predictive flow information concentrated near the origin, not proof of that
mechanism or actual receipt. Observed receipt times remain missing evidence.
The [import receipt](../artifacts/rp4_robustness_public_v1/import_receipt.json)
binds three exact CSV copies and two declared JSON derivatives per sensitivity
to their source closures. The linear robustness campaign is complete: RV15 and
RV30 placebos and 60 / 120 / 300-second timing comparisons. Tree-model placebos
at RV15 and RV30 remain deferred for computational cost.

## Closed registered exploratory v5 extension

The [full English report](rp4/results_v5.md), [registered specification](rp4/specification_v5.md)
and [saved post hoc table](../artifacts/rp4_v5_part34/table.csv) preserve the
five-family RV15 comparison and its distinct inferential scopes. V4 remains primary.

| Finding | Evidence and quantity | Status today and next implication |
| --- | --- | --- |
| The registered primary selector fails its rule | 419 sessions / 160,832 origins; H1 p = 0.3594. H2 nominal p = 0.0692 is not opened. | Negative primary verdict. Selecting a family each session did not establish the full hierarchy. |
| The secondary top2 ensemble clears its two-link chain | H1 p = 0.0236, H2 p = 0.0249; Holm across the two selector-chain maxima gives p = 0.0498. The declared Bonferroni ×5 bound across historical versions gives 0.249. | Favorable secondary result, not an adaptive-search-adjusted global success or independent replication. |
| Model diversity can help without choosing the daily winner | Post hoc four-family average: B2 QLIKE = 0.179102244, 0.999% below original v4 ridge and 0.629% below top2. | Descriptive comparison after observing results; no statistical superiority between procedures is demonstrated. |
| Post hoc chains retain their search limitation | Three-linear-family average H1/H2 p = 0.0355/0.0018; four-family average 0.0214/0.0037. | Nominal chains pass, but the post hoc procedure search is not adjusted. |
| Selection discrepancy was investigated with saved predictions | Recalculated losses for five families and two selectors agree with the closed report to maximum absolute error 4.44e-16. B0 selection frequencies are reproduced. | No selector implementation error detected by this audit. Validation optimism is a historical association, not a universal causal claim. |
| Independent-audit p-values are not fully reconciled | The report compares seeds and weights. Losses agree within 1e-4, while some p-value differences exceed that tolerance. | Exact cause remains unconfirmed without the independent code, contrast vectors and resampling indices; it is not attributed solely to rounding. |
| Recalculated ridge is not byte-identical v4 evidence | B1 and B2 mean-loss differences are +0.000006900532755 and +0.000003191997672. | The numerical drift is measured; its cause is not isolated. The claim that a new ridge Gram implementation explains it is unsupported by code review. |
| Some proposed models were not evaluated in the completed run | Five families completed RV15; MLP, RV5 and RV30 were deferred in A3. | No missing results are imputed. Earlier partial hardware probes do not establish completed scientific evaluation. |
| Prospective combinations are secondary | [Decision 136](rp4/prospective_combination_decision_136.md) adds top2 and the four-family mean, retaining v4 as primary and the exact 20/40/45/335 roles. | Registered future evidence, not a reported prospective outcome. |

## Eight-asset extension (registered, closed)

The [closed English report](rp4/results_universe_v1.md) and its
[aggregate import receipt](../artifacts/rp4_universe_public_v1/import_receipt.json)
retain the source commit and explicit public selection. V4 remains the headline.

| Finding | Evidence and quantity | Status today and next implication |
| --- | --- | --- |
| Ridge passes both links with eight assets | RV15, 419 sessions and 214,209 origins: option state +1.4042%, p = 0.0208; flow +0.5634%, p = 0.0093. | Registered closed extension; six historical reads for the original stocks and the first target evaluation of SPY/QQQ. No independent replication. |
| The joint claim across families fails | Trees: option state +1.0830%, p = 0.0794; flow −0.1485%, nominal p = 0.6738, with H2 unopened. `global_joint_reject=false`. | The inherited at-least-one-family closure field is true, while the registered both-family joint claim remains false. These rules are not interchangeable. |
| ETF and stock flow effects are heterogeneous | Ridge flow: SPY +1.26%, p = 0.020; QQQ +0.54%, p = 0.084; positive signs in 6/8 assets, with META/MSFT slightly negative. | Asset-level diagnostics are not eight independent confirmations. The original-six control exactly recovers the v4 primary comparison; the expanded model's six-stock subset is a different comparison. |

## Reconciling the apparent contradictions

**537 sessions versus 335.** The RP2 figure uses its observed LightGBM effect,
session dispersion and α = 0.00250; it was explicitly downgraded to an optimistic,
selection-biased bound. RP4's [amendment 3](rp4/prospective_confirmation_v1_amendment_3.md)
instead uses the saved RV15 linear H2 interval at 419 sessions: SE419 =
0.000407437235805319 and Δ/SE419 = 2.7826608848143843. Under normal approximation,
SE(n) = SE419 × √(419/n), one-sided α = 0.05 and target marginal power 0.80 give
335 sessions after rounding up. Different effect, uncertainty and alpha produce a
different requirement. This is a planning approximation, not calibrated bootstrap
power, guaranteed success, or 80% joint power for the full H1→H2 sequence.

**No RP2 economic value versus lower v4 forecast loss.** QLIKE reduction describes
prediction accuracy. Profitable trading additionally requires an executable rule,
spreads, slippage, financing, liquidity, impact, capacity and risk controls. V4's
small forecasting improvement does not reverse RP2's economic failures or establish alpha.

**Underpowered RP2 validation versus RP4 walk-forward evaluation.** Walk-forward
defines how past data train each forecast; power describes what a test can reliably
detect. RP4's 419 historical sessions offer a different sample and estimand, while
its 25-session final window does not confirm the hierarchy. Neither chronological
training nor a positive historical p-value cures earlier sample reuse or guarantees
prospective replication.

**Prospective checks remain future evidence.** Twenty new sessions, forty-session
stability, the secondary 25+20 combination, and the final 335-session extension have
different roles. RP3 remains governed by its own registration. No prospective data
were read to construct this ledger.

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.
