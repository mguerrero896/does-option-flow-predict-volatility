# Examiner questions — evidence, objections and scope

The answers distinguish primary results, descriptive diagnostics and prospective tests with no results yet. “Better” means lower QLIKE loss for the stated sample, weighting, horizon and family. The retained tables also expose adverse signs. Question numbers are editorial references, not results.

## Proposal → delivery

**Original source and comparison scope.** The complete local English and Spanish copies of the proposal dated **2026-07-26** were compared. Their sections and text match the commitments examined; the date is declared in the document, not an independent timestamp or authentication of the version submitted to the university. The [verbatim extracts and original hashes](../../../../archive/rp4/DEFENSE_PACKAGE/revision_2/correction_4/proposal_source_extract.json) support quotation checks without publishing the cover or personal identifiers. The original equation defines RV30 as the sum of thirty squared one-minute log returns, without a square root or annualization; the [target producer](../../../../../src/mds650/rp2/realized.py) preserves that definition. The [alignment evidence](../../../../archive/rp4/DEFENSE_PACKAGE/revision_2/correction_4/proposal_alignment_evidence.json) links each finding to files and selectors; “pending” does not necessarily mean that a file is missing.

### First, the original questions at RV30

The questions below translate section **2.3** of the [Spanish proposal](../../../../archive/rp4/DEFENSE_PACKAGE/revision_2/correction_4/proposal_source_extract.json); the answers use the v3 primary RV30 sample and the one-sided H1→H2 sequence within each family. These are retrospective development results, not independent confirmation. The [saved summary](../../../../../artifacts/rp4_v3_b2/summary.json) identifies the [effective empty-window specification](../../../../../artifacts/rp4_v3_a1_empty_window/specification.json).

| Original question | RV30 answer before the extension | Evidence available for examination |
| --- | --- | --- |
| RQ1: “Does conventional option-state information improve RV30 relative to an underlying-market benchmark?” | **Yes**, B1 > B0 in both families: one-sided p **0.0439** for the linear family and **0.0053** for trees. The first rejection is marginal and depends on the declared inference rule. | [v3 primary sample](../../../../../artifacts/rp4_v3_b2/summary.json) · [Sensitivity and historical search](#26-multiplicity-between-versions-what-survives-the-old-bilateralholm-rule) |
| RQ2: “Does trade-derived activity add incremental predictive value beyond that conventional options benchmark?” | **Not detected at 5 %**: H2 p is **0.0525** for the linear family and **0.6631** for trees. The linear estimate is favorable but does not cross the threshold; non-rejection establishes neither a zero effect, equivalence nor causal absorption of flow. | [v3 contrasts and decisions](../../../../../artifacts/rp4_v3_b2/summary.json) |
| RQ3: “Are improvements stable across assets, time segments, volatility regimes and conservative timing assumptions?” | **Partial**: B1 has a favorable sign in all six assets in both families, but none of the **12** secondary asset contrasts rejects after Holm within its four-contrast subset; the smallest adjusted p is **0.0624**. Time/calendar breakdowns and documented learning, instrument and expiry circumstances do not establish all proposed stability or PIT variants. | [RV30 secondaries](../../../../../artifacts/rp4_v3_b2/summary.json) · [Saved profiles](../../../../../artifacts/rp4_closeout_audit/descriptive_profiles.csv) · [Expiry audit](../../../../../artifacts/rp4_market_audit/REPORT.md) |

The learning period is documented through expanding training and profiles by training size; interruptions attributed to the provider are distinguished from counted empty windows and the accepted unfilled gap; the expiry change is placed at its first recorded presence on **2026-01-26**. These are descriptive circumstances, not three predefined statistical volatility regimes or causal explanations. The inspected secondary inventory contains time segments, calendar terms and flow/gamma proxies, but does not establish a specific contrast of volatility regimes or alternative PIT cutoffs. The saved `last_hour` label uses `origin_minute >= 300`, so it is not interpreted as exactly the last sixty minutes of the regular session. [Profiles and limits](../../../../../artifacts/rp4_closeout_audit/REPORT.md) · [Stratum definitions](../../../../../artifacts/rp4_v3_code/aggregate_v3.py) · [First presence by asset](../../../../../artifacts/rp4_market_audit/summary.json).

### Then, the horizon extension and deviations

Primary RV15 and secondary RV5 are presented as the **pre-declared v4 extension**, after the RV30 answer above. The conditional predecessor declares **2026-09-07 20:20 Australia/Sydney**; the executable v4 registration was frozen at **2026-09-08T02:37:21.501511+10:00**, before its evaluations. Its recorded motivation is the hypothesis of short-lived flow and hedging over minutes, not a demonstrated mechanism. Changing the primary horizon after reading RV30 is a **DECLARED DEVIATION**, with a local documentary sequence and uncorrected historical search. The complete chronology in the version question distinguishes predecessor, freeze, verification and execution; the seal is not from a third party. [Original predecessor](../../../predeclaration_v4_text.md) · [v4 freeze](../../../../../artifacts/rp4_v4_a1/freeze_manifest.json) · [Chronology](../../../../archive/rp4/DEFENSE_PACKAGE/revision_2/correction_2/examiner_evidence.json).

| Proposal commitment | Observed delivery | Status and limit | Evidence |
| --- | --- | --- | --- |
| Incremental question and B0 ⊂ B1 ⊂ B2; one-minute bars, contract/quote state and trade-level activity | The nested price/history, state/surface and composition/activity/imbalance layers are retained. | **ALIGNED** in question and information types; this does not imply three independent providers: surface and flow can share trades and provider fields. | [Proposal](../../../../archive/rp4/DEFENSE_PACKAGE/revision_2/correction_4/proposal_source_extract.json) · [Inputs and variables](../../../specification_v1.md) · [Effective registration](../../../../../artifacts/rp4_v3_a1_empty_window/specification.json) |
| Origins every five minutes; chronological expanding walk-forward; primary QLIKE and day-block intervals | Five-minute grid and past-only training; circular bootstrap of **5 sessions / 9,999 replicates**. | **ALIGNED**; origins are not treated as independent observations and only eligible keys are used. The proposal did not fix this block length or replicate count: these are execution-registration decisions. | [Grid](../../../../../scripts/rp2_block4_b0_panel.py) · [Validation](../../../../../artifacts/rp4_code/evaluate.py) · [Registered inference](../../../../../artifacts/rp4_v3_a1_empty_window/specification.json) |
| Non-annualized RV30 target and original questions | v3 answers RV30; v4 moves to primary RV15 and secondary RV5 while retaining estimator, keys and procedure. | **ALIGNED** for RV30; **DECLARED DEVIATION** of the primary horizon for the extension, after reading RV30. | [Target](../../../../../src/mds650/rp2/realized.py) · [RV30 results](../../../../../artifacts/rp4_v3_b2/summary.json) · [v4 registration](../../../specification_v4.md) |
| Initial universe: SPY, QQQ, AAPL, MSFT, NVDA, TSLA, AMZN and META | Targets: AAPL, AMZN, META, MSFT, NVDA and TSLA; SPY/QQQ enter B0 as market context. | **DECLARED DEVIATION**: eight proposed targets become six. Their roles are fixed in the specification; **no written reason was located** for the reduction in the inspected decisions and specifications. Coverage, liquidity and results are not assumed to explain it. | [Original scope](../../../../archive/rp4/DEFENSE_PACKAGE/revision_2/correction_4/proposal_source_extract.json) · [Fixed universe](../../../specification_v1.md) · [Decisions](../../../../methodology_decisions.md) · [Search scope](../../../../archive/rp4/DEFENSE_PACKAGE/revision_2/correction_4/proposal_alignment_evidence.json) |
| Model comparison: seasonal persistence, Corsi HAR-RV, regularized linear models and trees | Winsorized linear model with rank filtering—nominal ridge—and LightGBM; HAR/HARQ and seasonality form part of B0. | **DECLARED DEVIATION** in the compared set; separate HAR-RV/seasonal-persistence comparisons remain **PENDING**. Including these predictors does not deliver those benchmark rows or make almost unpenalized ridge substantively regularized. | [Committed models](../../../../archive/rp4/DEFENSE_PACKAGE/revision_2/correction_4/proposal_source_extract.json) · [Implementation](../../../../../artifacts/rp4_v3_code/models.py) · [Version table](../../../../../artifacts/rp4_closeout_figures/comparison_v1_v4.csv) |
| Secondary MAE and RMSE evaluation | Absent from the inspected RP4 results; shared functions could calculate them. | **PENDING**, without execution in this review. The absence concerns the examined RP4 workflow and outputs, not the entire repository. | [Commitment](../../../../archive/rp4/DEFENSE_PACKAGE/revision_2/correction_4/proposal_source_extract.json) · [Shared metrics](../../../../../src/mds650/metrics.py) · [Primary table](../../../../../artifacts/rp4_v4_b4/primary_statistics.csv) |
| Conservative timing sensitivities | A single source-time proxy at **120 seconds** is applied, without cutoff-variant results in the inspected outputs. | **PENDING** PIT sensitivity; a fixed cutoff neither compares cutoffs nor proves client availability. | [Registration](../../../../../artifacts/rp4_v4_a1/specification.json) · [Bounded inventory](../../../../archive/rp4/DEFENSE_PACKAGE/revision_2/correction_4/proposal_alignment_evidence.json) |
| Placebo tests | No placebo output was found in the inspected RP4 workflow and aggregates. | **PENDING**, without execution in this review; coverage or convergence diagnostics do not substitute for it. | [Commitment](../../../../archive/rp4/DEFENSE_PACKAGE/revision_2/correction_4/proposal_source_extract.json) · [Bounded inventory](../../../../archive/rp4/DEFENSE_PACKAGE/revision_2/correction_4/proposal_alignment_evidence.json) |
| Asset and regime analysis | Asset, time, calendar and activity/exposure-proxy secondaries exist, alongside descriptive chronological profiles. | **ALIGNED** for delivered breakdowns; RQ3 remains **partial**, without claiming stability under every original volatility regime and timing assumption. | [RV30](../../../../../artifacts/rp4_v3_b2/summary.json) · [v4 robustness](../../../../../artifacts/rp4_v4_b4/robustness.csv) · [v4 secondaries](../../../../../artifacts/rp4_v4_b4/regime_secondary.csv) |

### The commitment to accept adverse results

The Spanish proposal states, translated: **“Model choice will depend on the benchmark and simplicity, not on B2 producing a favorable sign.”** The English version states: **“Model choice will follow benchmark performance and simplicity, not whether B2 produces a favourable sign.”** The [original extract](../../../../archive/rp4/DEFENSE_PACKAGE/revision_2/correction_4/proposal_source_extract.json) retains both statements. Within each family, the [executed selector](../../../../../artifacts/rp4_v3_code/models.py) uses validation QLIKE, breaking ties toward greater penalization or fewer leaves/rounds. This supports the principle within fitting, without erasing adaptation between versions.

Alongside that commitment, the [v4 pre-declaration](../../../predeclaration_v4_text.md) states, translated: **“Otherwise, the project closes with B1 > B0 as the main result and B2 as an informative null at 30, 15 and 5 minutes. There is no v5.”** The qualification in the [executed specification](../../../specification_v4.md) is also retained: non-rejection establishes neither equivalence to zero nor causal absorption. Both documents express willingness to publish an adverse result, but **they are not the same inference rule**: v3 required both families for the joint conclusion and v4 permits at least one, with RV5 secondary and no global control of cross-version search. The proposal did not pre-specify that success rule. This difference is disclosed rather than presenting closure as evidence of no historical selection.

Showing flow non-rejection at RV30 and tree-mean non-rejection preserves the Spanish statement, translated **“a null or negative result would be equally valuable”**, and the English original **“a null or negative result would be equally informative”**. The [expected-results section](../../../../archive/rp4/DEFENSE_PACKAGE/revision_2/correction_4/proposal_source_extract.json) links them to a verifiable protocol's contribution; “informative null” here means an undetected result, not proof that flow is useless. The Spanish formulations corresponding to “will follow performance” and “equally informative” were paraphrases in the request; the original copies inspected are retained in the source extract.

### The ten committed deliverables

**ALIGNED** means a delivery serving that function exists, not institutional approval or completion of every subcommitment. **DECLARED DEVIATION** identifies a documented difference in scope or access; **PENDING** includes existing files that still describe the earlier design. The list follows the [proposal's](../../../../archive/rp4/DEFENSE_PACKAGE/revision_2/correction_4/proposal_source_extract.json) expected-results section.

| Committed deliverable | Status | Verified path and scope |
| --- | --- | --- |
| Final report | **ALIGNED** | [RESULTADO_FINAL_revision_2.md](../../../RESULTADO_FINAL_revision_2.md) and [executive summary](executive_summary.md): question, design, versions, estimate, uncertainty and limits; institutional-format acceptance is not established. |
| Presentation | **ALIGNED** | [defense_slides.md](defense_slides.md) and [figure manifest](../../../../../artifacts/rp4_closeout_figures_revision2/manifest.json): Markdown script with notes and charts; no native-slide delivery or validated duration is claimed. |
| Literature matrix | **ALIGNED**, with a pending subcommitment | [docs/literature_matrix.csv](../../../../literature_matrix.csv) and [access ledger](../../../../literature_evidence_ledger_v2.csv): **10** studies; one row is identified as a FEDS working paper. The proposal requires at least ten peer-reviewed studies; this matrix alone does not establish that its rows satisfy the requirement, and this review does not extend the project's publication-status inventory. Full text, working versions and metadata remain distinct; the literature review is not expanded here. |
| Data dictionary | **PENDING** RP4 update | [docs/data_dictionary.md](../../../../data_dictionary.md) exists but retains earlier blocked bars/B1 states and the RV30 target; the [current variable registration](../../../../../artifacts/rp4_v4_a1/specification.json) does not replace an updated dictionary of fields, units and transformations. |
| Reproducible extraction and quality code | **ALIGNED** as a delivery | [Clients](../../../../../src/mds650/providers/fmp.py), [quality](../../../../../src/mds650/quality.py), [manifests](../../../../../src/mds650/manifests.py), [evaluator](../../../../../artifacts/rp4_v4_code/evaluate_v4.py), [lockfile](../../../../../uv.lock) and [OPERATING_GUIDE.md](../../../OPERATING_GUIDE.md). Code and procedure are available; full reproduction from licensed originals was not executed in this review. |
| Versioned analytical panel | **DECLARED DEVIATION** in access | [Specification](../../../../../artifacts/rp4_v4_a1/specification.json), [freeze](../../../../../artifacts/rp4_v4_a1/freeze_manifest.json), [receipt](../../../../../artifacts/rp4_v4_a2/receipt.json) and [release](../../../../../artifacts/rp4_v4_a2/evaluation_release_rv15.json) fix identities and hashes. The payload remains privately held under its license; metadata are verified here without opening it or claiming complete public reconstruction. |
| Comparison tables | **ALIGNED** | [comparison_v1_v4.csv](../../../../../artifacts/rp4_closeout_figures/comparison_v1_v4.csv) and [primary_statistics.csv](../../../../../artifacts/rp4_v4_b4/primary_statistics.csv): versions, windows, families, contrasts and adverse signs are included; pending separate benchmarks are not treated as delivered. |
| Uncertainty intervals | **ALIGNED** | [primary_statistics.csv](../../../../../artifacts/rp4_v4_b4/primary_statistics.csv): contrast intervals and bootstrap rule. The percentage interval uses a fixed mean denominator, not a bootstrap ratio; it was not regenerated. |
| Robustness analysis | **ALIGNED** for the analyses present | [robustness.csv](../../../../../artifacts/rp4_v4_b4/robustness.csv), [regime_secondary.csv](../../../../../artifacts/rp4_v4_b4/regime_secondary.csv) and [audit report](../../../../../artifacts/rp4_closeout_audit/REPORT.md). These do not imply that MAE/RMSE, PIT variants, placebo or all of RQ3 were executed. |
| Examiner notebook | **PENDING** RP4 update | [canonical_rv30_defense.ipynb](../../../../../notebooks/canonical_rv30_defense.ipynb) and [research_pipeline.ipynb](../../../../../notebooks/research_pipeline.ipynb) exist but point to earlier evaluations; the latter retains infeasible B1 and an alternative comparison. Cells were inspected as text, without execution or use of outputs. This Markdown guide is not presented as the promised notebook. |

**Documented outstanding work, without execution.** MAE/RMSE, PIT variants, placebo and separate HAR-RV/seasonal-persistence benchmarks remain committed robustness work outside this historical documentary review. Dictionary/notebook updates and verification of the bibliographic requirement are also documented; they were not silently completed during the alignment audit. This review adds text, tables and contracts over saved evidence; it adds no losses, fits, intervals or data and changes no prospective registration.

The timing-variant status in this inventory reflects the earlier documentary inspection's scope. Visibility cutoffs of 60 and 300 seconds were assigned to a separate evaluation; no readiness, execution or result is inspected or claimed here. These are information-cutoff sensitivities, not target horizons. [Assignment and limits](horizon_pit_evidence.json).

## 1. What exactly does this work claim?

In the development sample, option state and surface add mean predictive information beyond prices and volatility history in both families at RV30 and RV15 under the v3/v4 tests. Flow adds a smaller improvement in the linear family at RV15: QLIKE reduction +0.6227941 %, delta +0.0011337597 and 95 % interval [0.00033503697, 0.0019321616], with one-sided p 0.0032 after passing H1. The linear sequence also rejects at RV5, but that horizon is secondary. The tree mean does not confirm the B2 increment.

The defensible claim is a predictive hierarchy conditional on family and horizon. It does not encompass every month, other assets, historical client receipt, mechanism causality or profitability. The final window does not confirm the complete sequence either.

B0 includes 29 registered predictors: past realized variance at 5/15/30 minutes, session-to-date, previous day and week; logarithmic HAR components and quarticity attenuation; positive- and negative-return semivariances, jump proxy, Parkinson range, returns, volume and dollar volume; past SPY/QQQ returns and variances; weekday, distance from open/close and intraday clock terms. This is not a comparison against mere persistence. The ideas come from multiscale HAR in [Corsi (2009)](https://doi.org/10.1093/jjfinec/nbp001), HARQ in [Bollerslev, Patton and Quaedvlieg (2016)](https://scholars.duke.edu/publication/1072550) and semivariances in [Patton and Sheppard (2015)](https://scholars.duke.edu/publication/1082826); the intraday implementation is original, not an exact reproduction of those papers.

B0 composition is verified in `feature_sets.B0` of the [executable registration](../../../../../artifacts/rp4_v4_a1/specification.json), the [price-feature producer](../../../../../scripts/rp2_block4_b0_panel.py), the [HAR/HARQ components](../../../../../src/mds650/har.py) and their [integration](../../../../../artifacts/rp4_code/materialize.py). Corsi's article identification was corroborated on the [author's institutional page](https://people.unipi.it/fulvio_corsi/pubblicazioni/); its formulation was read in the [2004 working predecessor](https://www.greta.it/old/jae/poster/06_1_Corsi.pdf), without presenting that reading as full access to the 2009 published version. The [review record](../../../../archive/rp4/DEFENSE_PACKAGE/revision_2/correction_2/examiner_evidence.json) separates metadata, inspected text and each reference's scope.

Linear H1 is marginal at RV30 (p 0.0439) and RV15 (0.0390); linear B1/B0 did not reject in v1/v2. The completed sensitivity using saved bilateral p-values and Holm across four contrasts leaves both linear H1 tests unrejected; the question 26 table retains every horizon and does not combine families to open H2.

Sources: [primary and final-window comparison](../../../results_v4.md), [saved statistics and decisions](../../../../../artifacts/rp4_v4_b4/primary_statistics.csv), [final result](../../../RESULTADO_FINAL_revision_2.md).

## 2. Why were there four versions? Was the study changed until significance appeared?

There was adaptation, and it must be disclosed. V1 retains the initial design and its numerical failure; v2 changes coverage, capacity and stability; v3 adds imbalance and empty-window handling; v4 changes the target horizon through a local conditional predecessor. The final specification retains v3 predictors, eligible keys and training rules, but that does not make the entire trajectory free of adaptation.

The same windows were evaluated successively. V1/v2 p-values are bilateral with Holm, whereas v3/v4 p-values belong to a one-sided sequence: they are not interchangeable. Cross-version search is uncorrected and the local predecessor has no independent timestamp. Retaining every result makes the evolution auditable; it does not eliminate programme selection bias. Prospective replication can test a rule fixed before its new sample.

Adaptation includes five decisions: (a) v1/v2 use bilateral p-values with Holm across four contrasts, while v3/v4 use sequential one-sided tests at 5 % within each family, without cross-family Holm; this change was registered before executing v3 and makes the corresponding decision less demanding; (b) v3 expands B2 with gamma imbalance and its indicators after adverse B2 results in v1/v2; (c) decision 132 fixes empty-window representation after the v2 diagnosis; (d) v4 changes only the scientific horizon, with RV15 primary and RV5 secondary; (e) the August 1 split was fixed on September 7 with the sample already observed.

The v4 predecessor is **pre-declared and locally sealed, without a third-party timestamp**. Its rationale is that flow could be short-lived and hedging could operate over minutes; this is a hypothesis for shortening the horizon, not evidence that the mechanism generated the result. The [projected pre-declaration text](../../../predeclaration_v4_text.md) exposes motivation and provenance redactions while keeping the local original's hash separate.

The proposal specified RV30, and v3 answered that objective: B1>B0 is detected in both families and B2>B1 is not detected at 5 %. The conditional v4 predecessor pre-declared primary RV15 and secondary RV5 under the hypothesis that flow information could be short-lived; that hypothesis does not prove that intermediary hedging caused the result. The executable registration was frozen after v3 closure verification and before v4 fits; the predecessor's declared time is not authenticated by a third party. In the linear family's primary window, B2/B1 reduces QLIKE +0.623 % at 15 minutes, with positive signs in 6/6 assets, versus +0.256 % and 3/6 at 5. The largest estimate observed among the examined horizons is at 15; it does not increase monotonically as the horizon shortens. These describe different targets and asset signs, not tests of a temporal optimum, a difference between horizons or six independent replications. [Figures](../../../../../artifacts/rp4_v4_b4/primary_statistics.csv) · [Predecessor](../../../predeclaration_v4_text.md) · [Chronology and selectors](horizon_pit_evidence.json).

The 120-second PIT rule is a predictor-visibility cutoff: at origin t, a provider record with a creation timestamp must satisfy `created_at <= t − 120 seconds`, alongside window and quality rules. `created_at` is the record-creation timestamp and `executed_at` identifies exchange execution; gamma imbalance also requires `executed_at <= t − 120 seconds`, implemented with the maximum of both clocks. This rule does not prove when the record was published or when a client received it. The 120 seconds are not a forecast horizon, are not added to RV15/RV5 and are not reapplied to columns that already incorporate the cutoff. Alternative cutoffs of 60 and 300 seconds were assigned to a separate visibility-sensitivity evaluation; no execution, readiness or results are claimed here. [Flow code](../../../../../scripts/rp2_block6_flow_panel.py) · [Clock intersection for imbalance](../../../../../artifacts/rp4_v3_code/materialize_gamma.py) · [Assignment and limits](horizon_pit_evidence.json).

The [v4 specification](../../../specification_v4.md) fixed this closure rule, translated:

> If neither rejects, investigation of this mechanism closes with B1>B0 as the main result observed at 30 minutes and B2 not detected at 30/15/5 according to each estimate and interval. Non-rejection establishes neither equivalence to zero nor causal absorption; “informative null” describes closure, not proof of absence.

The predecessor also states, translated, “There is no v5.” This closure does not permit promoting RV5 to rescue an adverse RV15 result. The prospective comparison applies the same scientific specification, with looks declared in its amendments; it is not a new version search. The [v3 decision](../../../decision_131_v3.md), its [specification](../../../specification_v3.md), the [empty-window decision](../../../decision_132_v3_empty_windows.md) and the question 26 sensitivity document the trajectory's inference cost.

Complete chronology of the inspected receipts; dates without a clock time are not assigned an invented one. The UTC and Australia/Sydney columns convert the same instant rather than recording separate events:

| Event and evidence type | UTC | Australia/Sydney | Source |
| --- | --- | --- | --- |
| Last historical session: 2026-09-04 | Time not recorded | Time not recorded | [Registration](../../../../../artifacts/rp4_v4_b3_rv15/summary.json) |
| Split 2026-08-01; design declared 2026-09-07 | Time not recorded | Time not recorded | [Registration](../../../../../artifacts/rp4_v4_a1/specification.json) |
| v1 freeze: date 2026-09-07, no stored time/zone | Time not recorded | Time not recorded | [Registration](../../../../../artifacts/rp4_a1/freeze.json) |
| v3 registration; v1/v2 already known | 2026-09-07T08:18:58.166170+00:00 | 2026-09-07T18:18:58.166170+10:00 | [Registration](../../../../../artifacts/rp4_v3_a1/freeze.json) |
| v3 empty-window registration | 2026-09-07T08:30:43.053218+00:00 | 2026-09-07T18:30:43.053218+10:00 | [Registration](../../../../../artifacts/rp4_v3_a1_empty_window/freeze.json) |
| Conditional v4 predecessor: time declared in the text | 2026-09-07T10:20:00+00:00 | 2026-09-07T20:20:00+10:00 | [Registration](../../../predeclaration_v4_text_receipt.json) |
| v3 closure verification | 2026-09-07T16:18:46+00:00 | 2026-09-08T02:18:46+10:00 | [Registration](../../../../../artifacts/rp4_v3_b4/receipt.json) |
| Executable v4 freeze | 2026-09-07T16:37:21.501511+00:00 | 2026-09-08T02:37:21.501511+10:00 | [Registration](../../../../../artifacts/rp4_v4_a1/freeze_manifest.json) |
| Primary RV15 started | 2026-09-07T17:24:29.535011+00:00 | 2026-09-08T03:24:29.535011+10:00 | [Registration](../../../../../artifacts/rp4_v4_b2_rv15/receipt.json) |
| Primary RV15 finished | 2026-09-07T18:13:29.790569+00:00 | 2026-09-08T04:13:29.790569+10:00 | [Registration](../../../../../artifacts/rp4_v4_b2_rv15/receipt.json) |
| Final RV15 started | 2026-09-07T18:14:50.222385+00:00 | 2026-09-08T04:14:50.222385+10:00 | [Registration](../../../../../artifacts/rp4_v4_b3_rv15/receipt.json) |
| Final RV15 finished | 2026-09-07T18:23:27.273395+00:00 | 2026-09-08T04:23:27.273395+10:00 | [Registration](../../../../../artifacts/rp4_v4_b3_rv15/receipt.json) |
| Primary RV5 started | 2026-09-07T18:24:38.947836+00:00 | 2026-09-08T04:24:38.947836+10:00 | [Registration](../../../../../artifacts/rp4_v4_b2_rv5/receipt.json) |
| Primary RV5 finished | 2026-09-07T19:16:40.533194+00:00 | 2026-09-08T05:16:40.533194+10:00 | [Registration](../../../../../artifacts/rp4_v4_b2_rv5/receipt.json) |
| Final RV5 started | 2026-09-07T19:17:15.307438+00:00 | 2026-09-08T05:17:15.307438+10:00 | [Registration](../../../../../artifacts/rp4_v4_b3_rv5/receipt.json) |
| Final RV5 finished | 2026-09-07T19:25:22.707101+00:00 | 2026-09-08T05:25:22.707101+10:00 | [Registration](../../../../../artifacts/rp4_v4_b3_rv5/receipt.json) |
| v4 report generated no later than | 2026-09-07T19:26:27+00:00 | 2026-09-08T05:26:27+10:00 | [Registration](../../../../../artifacts/rp4_v4_b4/receipt.json) |
| Prospective v1 registration | 2026-09-08T04:24:01.918499+00:00 | 2026-09-08T14:24:01.918499+10:00 | [Registration](../../../prospective_confirmation_v1_receipt.json) |
| Amendment 1 | 2026-09-08T04:31:58.752153+00:00 | 2026-09-08T14:31:58.752153+10:00 | [Registration](../../../prospective_confirmation_v1_amendment_1_receipt.json) |
| Amendment 2 | 2026-09-08T05:27:15.316335+00:00 | 2026-09-08T15:27:15.316335+10:00 | [Registration](../../../prospective_confirmation_v1_amendment_2_receipt.json) |
| Amendment 3 | 2026-09-08T06:56:21.897094+00:00 | 2026-09-08T16:56:21.897094+10:00 | [Registration](../../../prospective_confirmation_v1_amendment_3_receipt.json) |

The time 2026-09-07 20:20 Australia/Sydney, equivalent to 10:20 UTC, is a **claim in the predecessor text**; it is neither authenticated by a third party nor inferred from file modification time. v3 closure verification is recorded at 16:18:46 UTC, and the executable v4 registration linking the predecessor's hash was frozen later, at 16:37:21.501511 UTC. This chain traces local content but does not independently prove the predecessor was written before v3 became known. The public projection follows the results and has its own hash; the sealed local original's hash is `6f8ad8d53a8f4336851415a99c25b316bf44db74165e29246110a3bb133eabee`.

The v3 registration already declares v1/v2 results known; the inspected receipts do not assign an exact execution time to each. The sample ends on 2026-09-04, before the September 7 design decision. Training therefore remains separated from its future targets, but the historical design was fixed with the sample already observed; prospective replication establishes a different registration/acquisition relationship. [Selectors, hashes and each time's limits](../../../../archive/rp4/DEFENSE_PACKAGE/revision_2/correction_2/examiner_evidence.json).

The file-drawer review is bounded and reproducible: searching literally for `rv_10|rv_20|rv_60|rv_45` in 62 allowed files—27 code files and 35 v3/v4 registrations/aggregates—yielded zero matches, empty stdout and stderr, and `rg` exit code 1 for no matches. The six primary-contrast summaries contain only the linear and LightGBM families; registrations fix RV30 for v3 and primary RV15/secondary RV5 for v4. This inventory contains no evidence of other primary horizons or families. The search does not prove no other experiment ever occurred outside the inspected scope or deny the documented secondaries. No panels, reserved results or new data were opened. [Inventory, patterns, command and search hashes](../../../../archive/rp4/DEFENSE_PACKAGE/revision_2/correction_2/examiner_evidence.json).

Sources: [complete version table](../../../RESULTADO_FINAL_revision_2.md), [aggregate comparison data](../../../../../artifacts/rp4_closeout_figures/comparison_v1_v4.csv), [v4 predecessor and scope](../../../specification_v4.md), [prospective registration](../../../prospective_confirmation_v1.md), [secondary amendment](../../../prospective_confirmation_v1_amendment_2.md).

## 3. Why is “at least one family” sufficient? Does the study have a global 5 % error rate?

The declared closure rule allows a conclusion that an increment was detected within one considered family. H1 compares B1 with B0; only rejection opens H2, B2 against B1, with a one-sided 5 % threshold and positive estimate. This sequence prevents opening H2 without establishing the preceding improvement in the same family.

“At least one family” is an operational closure rule, not a cross-family correction. The specification expressly states that it provides no global 5 % control across families or versions. The result is therefore attributed to the linear family rather than universal confirmation. The new replication fixes its primary decision in linear RV15 beforehand, without permitting a later family switch.

Amendment 3 also registers a final cumulative look at 335 prospective sessions under the same linear RV15 sequence. It does not permit declaring success by selecting either the 20 or 335 look: each result retains its verdict, and no global 5 % control is demonstrated across looks, secondaries and historical search. [Current scope and final-look rules](../../../prospective_confirmation_v1_amendment_3.md).

Sources: [closure rule and limits](../../../specification_v4.md), [primary decisions](../../../../../artifacts/rp4_v4_b4/primary_statistics.csv), [prospective decision](../../../prospective_confirmation_v1.md), [secondary amendment](../../../prospective_confirmation_v1_amendment_2.md).

## 4. Why do trees not confirm B2 when some diagnostics are favorable?

Because the primary statistic is the mean loss difference. For tree B2/B1 at RV15, delta is −0.00021290307, its interval is [−0.0020441248, 0.0011041695] and one-sided p is 0.628. H1 opens H2, but H2 does not reject. At RV5, H1 p is 0.0608 and H2 stays closed: its nominal p of 0.1927 is diagnostic even though the B2/B1 estimate is positive.

Favorable secondaries do not replace those decisions. Nor does non-rejection imply that flow contains no information for any tree, configuration or population: it bounds the evidence from this test. This is neither an equivalence test between B1 and B2 nor proof of causal flow absorption by the surface.

Two sessions illustrate heterogeneity in different windows, without removing them from the calculation:

- 2025-04-07 belongs to the primary window. Mean coverage by asset is around 20 cells per origin and presence of the near-price, immediate-expiry option cell (ATM) is 0 %, with 65 origins per asset. The session's RV15 B2/B1 delta is −0.344417 for trees and +0.011539 for the linear family.
- 2026-08-31 belongs to the final window. Mean coverage by asset ranges from 20.4 to 24.0 cells per origin, rounded to one decimal, with ATM presence of 100 % and 65 origins per asset. For AMZN, the 14:00 New York bar has a log return of −151.7 basis points and the next +71.3; their volumes are respectively 3.0 and 11.1 times the session median. The aggregate session's RV15 B2/B1 delta is +0.116 for the linear family and −0.080 for trees, rounded to three decimals.

Deltas weight assets equally within each session; the August deltas are not AMZN-only effects. The cell range compares asset means, not the minima and maxima of every origin. ATM uses the coverage census definition: moneyness 0.97–1.03 and expiry within 0–1 days. Its absence does not mean the entire surface is absent. These aggregates are consistent with fragility of the tree increment in extremes; they do not prove the shock caused deterioration, that every price is correct or that trees universally cannot extrapolate. The bar check establishes internal provider consistency, not independent external validation. These dates are not treated as a new inference sample.

Sources: [horizon comparison and extreme sessions](../../../results_v4.md), [registered asset/session weighting](../../../specification_v4.md), [formal p, nominal p and hypothesis status](../../../../../artifacts/rp4_v4_b4/primary_statistics.csv), [coverage/bar audit and limits](../../../../../artifacts/rp4_market_audit/REPORT.md), [aggregate transcription, denominators and example hashes](../../../../archive/rp4/DEFENSE_PACKAGE/revision_2/additions_evidence.json).

## 5. Can B2 ≥ B1 be claimed “in the median”? Is this the same hierarchy?

Only as a description of the secondary estimand: the median paired session difference favors B2 for trees at RV15 and RV5. Bilateral p-values are 0.0435 and 0.0038; after Holm they are 0.0870 and 0.0096. RV15 therefore fails that adjustment, while RV5 passes as a secondary. The phrase means neither session-by-session dominance nor non-inferiority.

A positive median and negative mean can coexist: larger adverse losses can weigh more heavily on the mean. The statistic is not changed here to rescue the primary result. A median of paired differences is also not a difference between two series' medians. The prospective protocol retains this distinction for the tree secondary; amendment 2 includes it in Holm alongside A and C, keeping its single look at 20 sessions.

Sources: [registered secondary distributions](../../../../../artifacts/rp4_v4_b4/distribution_secondary.csv), [readable secondary tables](../../../results_v4.md), [secondary B and current multiplicity](../../../prospective_confirmation_v1_amendment_2.md).

## 6. How can a positive interval coexist with a non-rejecting p-value?

The saved interval and p-value are not inversions of the same procedure. The interval is a bilateral 95 % percentile interval; the p-value uses a bootstrap distribution centered under the null. For example, tree H1 at RV15 in the final window has interval [0.0016443642, 0.016807137] and p 0.0568. The registered decision is non-rejection even though the percentile interval excludes zero.

The sign of the interval must not replace the p-value rule when they differ. Both are shown and their construction identified; asymptotic diagnostics also do not replace the primary test. This calibration discrepancy limits the inference used; it does not authorize choosing the favorable result.

Saved Diebold–Mariano (DM) and Giacomini–White (GW) diagnostics provide complementary comparisons for the four primary RV15 increments, with 419 sessions and six-decimal rounding:

| RV15, primary window | DM HAC(5), statistic | Bilateral DM p | GW statistic | GW p |
| --- | ---: | ---: | ---: | ---: |
| Linear H1 B1/B0 | 1.911952 | 0.055882 | 7.029704 | 0.029752 |
| Linear H2 B2/B1 | 2.734853 | 0.006241 | 7.618946 | 0.022160 |
| Trees H1 B1/B0 | 2.425315 | 0.015295 | 7.128308 | 0.028321 |
| Trees H2 B2/B1 | −0.257628 | 0.796694 | 0.057964 | 0.971434 |

DM uses a bilateral normal approximation with lag-5 HAC variance. GW uses a constant and the previous session's delta, HAC(5) and two degrees of freedom; it does not test the same unconditional null as DM. These are not multiplicity-adjusted here and do not replace the registered circular bootstrap. For example, linear H1 does not reject under DM (0.055882), although it does under its one-sided bootstrap (0.0390). The discrepancy must be shown rather than resolved by choosing the favorable test. [Original rows and recipes](../../../../../artifacts/rp4_v4_b4/primary_statistics.csv) · [Typed transcription and formulas](../../../../archive/rp4/DEFENSE_PACKAGE/revision_2/correction_2/examiner_evidence.json).

Sources: [intervals and decision rule](../../../results_v4.md), [`interval` field and null calibration](../../../../../artifacts/rp4_v4_b4/primary_statistics.csv), [specified inference](../../../specification_v4.md).

## 7. If the gamma mechanism is unproven, what does B2 actually explain?

What is demonstrated is incremental usefulness of the entire B2 set within a particular predictive representation. The audit finds larger mean absolute magnitudes for some premium shares than for gamma imbalance, but this comparison does not identify each variable's marginal contribution. Coefficients act on transformed, training-only standardized and clipped inputs; columns are related and the output applies corrections and bounds.

The variable `rp4_gamma_imb_signed_trades` counts trades with identifiable direction: it is not signed net buying and selling. Small medians and larger absolute means for some premium shares also do not establish a stable effect every session. Without ablation, actual inventories or causal identification, the gain cannot be attributed to intermediary hedging or entirely to flow composition. The registered prospective ablation compares the full block with its removal without rewriting this historical evidence.

Sources: [coefficient scale, signs and limits](../../../../../artifacts/rp4_closeout_audit/REPORT.md), [column/horizon summary](../../../../../artifacts/rp4_closeout_audit/b2_coefficient_summary.csv), [secondary A definition](../../../prospective_confirmation_v1_amendment_1.md), [current A/B/C multiplicity](../../../prospective_confirmation_v1_amendment_2.md).

## 8. Did provider interruptions manufacture the flow improvement?

The closeout identifies 2025-05-15 and 2025-09-18 as instrument incidents. The census establishes windows without available eligible trades; alone it neither proves a publication interruption nor distinguishes economic absence from provider coverage or latency. The v3 rule retains zero activity counts, marks shapes and ratios undefined when no trades exist, and adds indicators. It does not remove rows to favor B2. There remain 412 empty five-minute windows in the primary sample and none in the final window.

In those rows, linear B1/B2 QLIKE moves from 0.102703519 to 0.202126323 under equal session/asset weights: the damage remains adverse. The origin mean differs, moving from 0.185885062 to 0.247087047, and must not be substituted. The correction addresses a representation problem; it neither proves every absence is true inactivity nor identifies the gain without interruptions. No new exclusion-based test is calculated.

Sources: [incidents identified at closeout](../../../RESULTADO_FINAL_revision_2.md), [rule and unresolved causal attribution](../../../v3_window_empty_addendum.md), [empty-window census](../../../../../artifacts/rp4_v4_b4/empty_census.csv), [empty-window comparison and weights](../../../../../artifacts/rp4_closeout_audit/REPORT.md).

## 9. What happened on January 26? Did the market being learned change?

The census documents the first presence of Monday and Wednesday expiries across all six assets on 2026-01-26, consistent with the listing announcement recorded in the audit. The first expiries on those weekdays with an intraday remaining term appear on 2026-02-02 and 2026-02-04. The initial listing date is not inferred from a later coverage increase: expiry counts and cell counts measure different things.

Overall mean coverage per origin changes from 20.036718 to 23.095318 cells before and after the cutoff. The final window is entirely in the new regime while much of training comes from the previous one. This limits transportability and stability; descriptive comparisons do not identify the change as the cause of QLIKE behavior. The audit distinguishes announcement, first observed presence and first expiration, and bounds the period actually inspected.

Sources: [census, recorded announcement and interpretation limits](../../../../../artifacts/rp4_market_audit/REPORT.md), [weekday coverage](../../../../../artifacts/rp4_market_audit/coverage_weekday.csv).

## 10. Was the learning period too short? Would extending it have sufficed?

The design uses 60 initial sessions exclusively for training, followed by expanding training. The evaluated segment from October 2024 to February 2025 contains 64 sessions; linear B1's RV15 gain is negative there. This is evidence of early difficulty, not proof that another warm-up would have solved it.

Training size rises with calendar time and regimes. Training-size terciles and the early segment are different partitions. No experiment holds the regime fixed while changing only learning; retrospectively extending warm-up would also exclude previously seen observations. The defense retains this segment and adverse months.

Sources: [training rules](../../../specification_v4.md), [early profile and terciles](../../../../../artifacts/rp4_closeout_audit/REPORT.md), [complete descriptive profiles](../../../../../artifacts/rp4_closeout_audit/descriptive_profiles.csv).

## 11. Was ridge almost unpenalized? Is calling it regularized accurate?

The implementation penalizes the sum of squared errors without dividing by training size. The same lambda therefore does not have comparable strength to a mean-error formulation. B2 selected lambda 0.0001 in 111 of 419 RV15 sessions; the grid can be weakly restrictive in large samples. The closeout's descriptive name is “winsorized linear model with rank filtering, nominal ridge.”

Stability also depends on transformations, rank pruning and bounds. In B2, between 88 and 97 columns were removed, including presence indicators: not all were constant and the count was not always the same. This does not guarantee stability of correlated coefficients. Changing penalty scaling would be another design; it is not done on the closed sample, and no unobserved result is attributed to that change.

Sources: [regularization and pruning](../../../../../artifacts/rp4_closeout_audit/REPORT.md), [lambda selection](../../../../../artifacts/rp4_closeout_audit/ridge_lambda_counts.csv), [rank/bounds summary](../../../../../artifacts/rp4_closeout_audit/ridge_bounds_pruning_summary.csv), [registered model](../../../specification_v4.md).

## 12. What does v1's extreme result mean? Was a failing model hidden?

The result remains visible: v1 linear B2/B1 shows −167448.32 % QLIKE reduction, an extreme deterioration, with Holm p 1. The initial version used 418 sessions and 92261 origins; v2–v4 use different coverage and the linear family incorporates stability changes. The closeout acknowledges numerical failure instead of interpreting the value as a structural economic relationship.

The version table is not a controlled ablation assigning all recovery to a particular correction. Retaining the adverse value and its denominators matters: showing only the final version would hide the fragility that motivated revisions. The later result does not retrospectively validate the initial implementation.

Sources: [v1/v2 comparison with denominators](../../../results_v2.md), [untrimmed aggregate comparison](../../../../../artifacts/rp4_closeout_figures/comparison_v1_v4.csv), [final interpretation of the failure](../../../RESULTADO_FINAL_revision_2.md).

## 13. Does the 25-session window confirm the main finding?

No. In linear RV15, H1 p is 0.3908, so H2 does not open; H2's nominal p is 0.1758. Tree RV15 H1 p is 0.0568 and also leaves H2 closed. A favorable point estimate in one contrast does not pass the complete sequence.

“Confirmation” is also a calendar-window name, not a guarantee of independence from development: the split was fixed on 2026-09-07, and a partially overlapping July 20–August 28 window had already been read in an earlier bridge evaluation under another specification. Its 25 sessions and 9750 origins are reported separately. A short, reused sample is not rescued by adding it to the primary sample, and its non-rejection is not equivalence.

Concentration is substantial: for linear RV15 B2/B1, 2026-08-31 contributes +0.1162479043 to a final-window delta sum of +0.1191828314; 100 × contribution / sum = 97.54 %, rounded to two decimals. The other 24 sessions sum to +0.0029349271. This is an arithmetic decomposition of the 25 saved sessions, not a new estimate excluding the day. The final point gain depends heavily on that session and does not prove persistence.

The six assets are US technology-related megacaps sharing risk factors; their variances are not treated as independent. Six favorable signs in this homogeneous sample are not six replications and do not justify generalization to other sectors, sizes or markets. Resampling operates on aggregate sessions while retaining the assets jointly. [Concentration, row and source hash](../../../../archive/rp4/DEFENSE_PACKAGE/revision_2/correction_2/examiner_evidence.json).

Date-verified overlap is 20 of the 25 final sessions, or 80 %: sessions from 2026-08-03 through 2026-08-28 lie in the declared bridge window; the five from 2026-08-31 through 2026-09-04 do not. Only `session_date` in final aggregates is counted, without reopening the bridge evaluation. The [historical README](../../../../../README.md) declares opening on 2026-08-30 and mixed/exploratory, non-confirmatory results without aggregation changes; a sensitivity improved only one of eight primary cells containing B1. This review compares that statement with the retained addendum and public aggregates without repeating the evaluation or verifying each person's historical knowledge. The record identifies the earlier reading under another specification as an owner declaration; alone it does not independently verify each person's knowledge. It is disclosed because these sessions were not unknown when the split was fixed. [Counted dates, statement source and limits](../../../../archive/rp4/DEFENSE_PACKAGE/revision_2/correction_2/examiner_evidence.json).

Sources: [final window and disclosures](../../../results_v4.md), [decisions and sizes](../../../../../artifacts/rp4_v4_b4/primary_statistics.csv), [scope of the prior reading](../../../RESULTADO_FINAL_revision_2.md).

## 14. If the split was fixed after the evaluated dates, in what sense is it out of sample?

It is out of sample relative to each daily fit: predictions use training before the evaluated session, selection over the last ten training sessions, transformations estimated only there and 60-minute purging/embargo. This limits direct use of future targets in fitting.

That differs from not knowing the sample while designing the study. The calendar was fixed retrospectively and versions reuse windows, so causal training controls do not remove methodological adaptation. The full label is “walk-forward out of sample, design fixed with the sample already observed and split fixed on 2026-09-07.” Omitting the latter overstates confirmation. The new replication retains causal training and fixes the rule before incorporating future sessions.

The chronology in question 2 distinguishes the predecessor's content date, evaluation closeouts and local prospective-registration seals. An individual prediction using only the past does not imply design decisions were blind to the historical sample. Temporal fitting evaluation and prospective replication have this temporal separation; retrospective development does not acquire it through a later hash. [Verifiable chronology](../../../../archive/rp4/DEFENSE_PACKAGE/revision_2/correction_2/examiner_evidence.json) · [Projected pre-declaration](../../../predeclaration_v4_text.md).

Overlap reaches 20/25 final sessions (80 %), August 3–28, according to the date count in question 13; the mixed bridge result is attributed to the historical README. The complete table in question 2 retains both verified times and the predecessor's declared time without confusing them.

Sources: [design and disclosures](../../../RESULTADO_FINAL_revision_2.md), [timing masks and verification limits](../../../../../artifacts/rp4_closeout_audit/REPORT.md), [v4 specification](../../../specification_v4.md), [prospective cohort](../../../prospective_confirmation_v1.md), [secondary amendment](../../../prospective_confirmation_v1_amendment_2.md).

## 15. Are there really 160832 independent observations? How is dependence handled?

Origins are not interpreted as independent trials. The v2–v4 primary sample has 160832 origins in 419 sessions; loss is aggregated first by asset/session and then with equal weights across assets and sessions. Inference uses a circular bootstrap with five-session blocks and 9999 replicates, retaining the registered time unit.

Intraday overlap, assets and regimes motivate distinguishing forecast count from temporal support. The resampling procedure does not prove it captures all long-range dependence or structural breaks. Block length is retained rather than selected according to the resulting p-value. Alternative diagnostics are preserved without replacing the primary test.

The four primary RV15 diagnostics retain DM/GW p-values, respectively: linear H1 0.055882/0.029752; linear H2 0.006241/0.022160; trees H1 0.015295/0.028321; trees H2 0.796694/0.971434. DM is bilateral normal with HAC(5); GW includes a constant and prior delta, HAC(5), and two degrees of freedom. Complete statistics appear in question 6 and the [typed record](../../../../archive/rp4/DEFENSE_PACKAGE/revision_2/correction_2/examiner_evidence.json). These are complementary asymptotic diagnostics, not new primary verdicts. The six assets share exposures, and their 160832 origins do not make the contrast that many independent experiments.

Sources: [inference method](../../../specification_v4.md), [saved sizes and parameters](../../../../../artifacts/rp4_v4_b4/primary_statistics.csv), [coverage](../../../../../artifacts/rp4_v4_b4/coverage.csv).

## 16. Does such a small QLIKE reduction matter? Is the interval a percentage?

The effect answers a predictive-accuracy question. The registered percentage reduction is 100 × mean(delta) / mean(baseline QLIKE), with delta equal to baseline minus expanded loss and fixed asset/session weighting. It is neither a percentage change in volatility nor a return. Operational usefulness would require a further evaluation aligned with a concrete decision; this study does not measure it.

The original interval concerns the QLIKE difference. When a figure expresses it as a percentage, it divides its endpoints by the observed baseline mean and multiplies by 100. This is a fixed-denominator re-expression, not a new bootstrap ratio interval. In particular, linear RV15 +0.6227941 % must be read alongside delta interval [0.00033503697, 0.0019321616], cross-version adaptation and lack of complete final-window confirmation.

In primary RV15, linear B2/B1 is favorable in 249 of 419 sessions: 100 × 249 / 419 = 59.43 %, rounded to two decimals; 59 % is its integer rounding. There are 170 adverse sessions and no ties. The mean difference is also positive in 6/6 assets and 3/3 chronological blocks. These describe frequency and distribution, not six significant tests, three independent replications or guaranteed profitability.

HARQ provides methodological context: Bollerslev, Patton and Quaedvlieg (2016) use quarticity to adapt persistence to time-varying measurement error. They study daily and longer forecasts against HAR; five-minute returns construct the measure rather than define an RV5 target. Their comparators, samples and windows differ from intraday B2/B1. A paper percentage is therefore not used as a comparable threshold or validation of the observed magnitude. [Original article, sections 2.3, 3.1, 3.3 and 3.5](https://public.econ.duke.edu/~ap172/BPQ_Exploiting_Errors_JoE_2016.pdf).

Sources: [definition, effect and original interval](../../../results_v4.md), [original estimates](../../../../../artifacts/rp4_v4_b4/primary_statistics.csv), [explicit rescaled-interval definition](../../../../../artifacts/rp4_closeout_figures/comparison_v1_v4.csv), [aggregate counts and hashes](../../../../archive/rp4/DEFENSE_PACKAGE/revision_2/additions_evidence.json), [bibliographic identification at Duke](https://scholars.duke.edu/publication/1072550).

## 17. Why can QLIKE not be translated into trading profitability?

QLIKE evaluates disagreement between realized variation and forecast: `y/f − log(y/f) − 1`. None of these terms defines a position, execution price, holding horizon or cost. B2 can improve a forecast without offering a profitable trade at available prices.

A tradable rule and evaluation of its costs, liquidity, exposure and risk are absent. Profits, Sharpe, capacity and return cannot be inferred from this result. The retained conclusion is predictive research and keeps `RESEARCH_ONLY`, `NOT INVESTMENT ADVICE` and `capital_go=false`.

Sources: [loss and result scope](../../../specification_v4.md), [explicit conclusion limits](../../../RESULTADO_FINAL_revision_2.md).

## 18. What does PIT establish, and what remains a proxy?

A source-time threshold of 120 seconds is applied and registered availability logic is retained. The audit distinguishes the provider's available clocks and version selection. This controls retained data and timestamps; it does not observe when a historical client received each datum.

Forecast origin, bar-start timestamp and bar completion are different. One-minute bars must be complete at the visibility cutoff; start labels do not permit premature use of their closes. Records with these clocks must satisfy `created_at <= t − 120 seconds` and, for gamma imbalance, also `executed_at <= t − 120 seconds`. The target retains its index convention and registered horizon: the visibility cutoff neither shifts the target nor is reapplied to inherited predictors. [Bar rule](../../../../../src/mds650/rp2/b1_snapshot.py) · [HAR integration](../../../../../artifacts/rp4_code/materialize.py) · [Preserved target](../../../../../artifacts/rp4_v4_code/materialize_targets.py) · [Clocks and selectors](horizon_pit_evidence.json).

The signals therefore cannot be claimed executable in real time at that latency. Prospective downloading after close also does not turn these timestamps into historical client receipts. New replication improves separation between registration and sample observation but retains this instrument limitation and the absence of actual intermediary inventories.

Sources: [clock method and limits](../../../../../artifacts/rp4_market_audit/REPORT.md), [PIT disclosure](../../../RESULTADO_FINAL_revision_2.md), [prospective-acquisition limits](../../../prospective_confirmation_v1.md), [secondary amendment](../../../prospective_confirmation_v1_amendment_2.md).

## 19. Do the results depend on extreme days or a few favorable months?

The descriptive evidence retains heterogeneity. October and November 2025 are negative for linear B2 at both RV30 and RV15. In the primary sample, linear B2 is positive in all three chronological blocks at both horizons, but by asset it is positive in only three of six at RV5, versus all six at RV15. The aggregate mean does not imply a uniform advantage.

Extremes and cumulative curves help locate contributing sessions. Temporal proximity does not establish an event's cause or authorize exclusions to improve p-values. The first observable hour is also distinguished from the market's first hour: their denominators and effects are not interchangeable. Subsequent slices remain descriptive.

“Six of six” at RV15 is descriptive consistency within six US technology-related megacaps, with common factors and possible dependence between their variances; no cross-correlation is measured here, and these are not six independent replications. At RV5 only three of six assets are positive. Transportability to a diversified population is not claimed, and resampling retains the session as its time unit rather than treating each asset as a replication.

The final window shows concentration distinct from these primary counts: 2026-08-31 contributes +0.1162479043 of +0.1191828314 in cumulative linear B2/B1 delta, or 97.54 %; the remaining 24 sum to +0.0029349271. This description neither removes the day nor recalculates alternative inference. Its magnitude prevents presenting the favorable final mean as uniformly distributed evidence. [Arithmetic decomposition and saved source](../../../../archive/rp4/DEFENSE_PACKAGE/revision_2/correction_2/examiner_evidence.json).

Sources: [block/asset robustness](../../../../../artifacts/rp4_v4_b4/robustness.csv), [month/hour profiles](../../../../../artifacts/rp4_closeout_audit/descriptive_profiles.csv), [slice and weighting distinctions](../../../../../artifacts/rp4_closeout_audit/REPORT.md), [summary retaining signs](../../../RESULTADO_FINAL_revision_2.md).

## 20. Are the extreme bars data errors that should have been removed?

The AMZN audit for 2026-08-31 and TSLA audit for 2026-08-17 reproduced extreme movements and reversals in retained bars, checking timestamp integrity, OHLCV prices and volume. Files match their historical hashes and receipts. This establishes internal consistency of the examined data.

It does not independently establish that those prices were correct market executions or identify a news event or cause. They are therefore neither removed, replaced nor assigned an economic mechanism without external evidence. The defense exposes the anomaly and its validation limit; an integrity check is not external price validation.

Sources: [extreme bars, checks and limits](../../../../../artifacts/rp4_market_audit/REPORT.md), [census sources and hashes](../../../../../artifacts/rp4_market_audit/sources.json), [largest-loss days](../../../../../artifacts/rp4_v4_b4/top_loss_sessions.csv).

## 21. Do jump and MZ recalibration failures invalidate the primary endpoint?

These are distinct endpoints and retain separate statuses. The final jump closeout contains 419 primary sessions, not the partial 418-session closeout; it combines retained valid components with numerical resolution of eligible failures, without selecting a pass by its AUC. Aggregates do not reject H1 and do not open H2. The `jump30 > 0` label represents positive RV−BPV excess, not a formal significant-jump test.

MZ recalibration remains unverifiable as a useful result. Neither secondary changes saved primary losses, masks or decisions, and a favorable secondary cannot rescue them. V4 excludes quantiles, jumps and MZ from its fits. The classifier result does not prove an absence of information about economically relevant jumps defined differently.

Sources: [combined closeout and preserved failures](../../../results_v3_revision2.md), [label audit and scope](../../../../../artifacts/rp4_closeout_audit/REPORT.md), [v4 endpoints](../../../specification_v4.md).

## 22. What will prospective replication actually change?

It will change the sample and its temporal relationship with registration while retaining the primary v4 test. First acquisition is scheduled for 2026-09-09 at 10:00 Australia/Sydney and corresponds to the New York market session of 2026-09-08. Sample dates are market sessions, not the computer's civil dates. Hashes and receipts record what was fixed before acquisition; these are local records, not independent timestamps.

The early primary decision is read once the first 20 eligible sessions are complete: it confirms only if H1 and H2 reject in linear RV15 under the registered sequence. It does not permit switching afterward to trees, RV5, median or trimmed mean. The first 40 cumulative sessions, if read, assess stability and neither rescue a negative first look nor form an independent replication. The 20, 40 and pooled 45 looks are consistency checks with limited power, not high-power designs; their original rules and verdicts are retained.

Amendment 2 retains A, ablation, and B, tree median, and adds C, tree paired trimmed mean, and D, pooling the 25 already-observed final historical sessions with the first 20 new ones for a total of 45. A/B/C use Holm across three; D has its own secondary H1→H2 sequence. A, B, C and D are each read once when the 20-session look is complete, even if the primary does not confirm; they are not repeated at 40 and do not alter the primary verdict. The pool contains known historical information and is not an independent replication.

Amendment 3, **pre-declared and locally sealed without a third-party timestamp**, uses the saved historical linear RV15 H2 CI, [0.00033503697025205506, 0.0019321615865300122], and 419 sessions. It approximates SE419 = CI width / (2 × Φ⁻¹(0.975)) = 0.000407437235805319; with effect 0.0011337596590923558, z = 2.7826608848143843. It scales SE(n) = SE419 × √(419/n) and calculates Φ(effect/SE(n) − Φ⁻¹(0.95)); the same approximation is repeated separately using H1's saved CI.

| Assumed sessions | Marginal H2 power | Marginal H1 power | Scope |
| --- | ---: | ---: | --- |
| 20 | 14.99 % | 11.27 % | Early primary consistency |
| 40 | 21.62 % | 15.08 % | Cumulative stability |
| 45 | 23.18 % | 15.96 % | Hypothetical new-session scenario; not D's power |
| 120 | 43.81 % | 27.91 % | Planning only; no look |
| 146 | 49.91 % | 31.69 % | Planning only; no look |
| 335 | 80.05 % | 54.98 % | Final cumulative look; 80 % applies only to H2 alone |

The new final look uses the first 335 eligible prospective sessions once, under the same primary linear RV15 H1→H2 rule at 5 %, approximately January 2028 if acquisition and eligibility permit. **The 80.05 % is not joint power:** under these approximations, the probability of rejecting both steps cannot exceed the smaller marginal power, 54.98 %. The 20 and 335 looks share data, retain their verdicts and do not permit success by either look. There is no rescue, additional look at 120/146 or repetition of A/B/C/D at 40 or 335; nor is global 5 % control demonstrated across looks.

The 45-new-session assumption is hypothetical planning only: D contains 25 known and 20 new sessions and does not have that conditional power. No justified power estimate exists for A or Holm-adjusted B/C. As a sensitivity for another estimand, a one-sided binomial sign test at 5 %, assuming independence and a positive-sign probability of 0.59, would give 10.79 % with 20 and 27.95 % with 45; using 249/419 would give 11.52 % and 29.95 %. This is neither a newly registered test nor power for the bootstrap median.

These calculations do not rerun the bootstrap: they approximate a normal standard error from a saved percentile CI, which is not the exact dual of the centered p-value. They assume stable effect and dependence despite historical adaptation, regime changes and learning; the selected magnitude may be optimistic. Only four five-session block lengths fit in 20 sessions, so the calculation also does not validate finite-sample bootstrap size or power. [Full amendment 3](../../../prospective_confirmation_v1_amendment_3.md) · [Verifiable calculations and seal](../../../prospective_confirmation_v1_amendment_3_receipt.json).

Sources: [cohort, look and complete-session criterion](../../../prospective_confirmation_v1.md), [current secondary and multiplicity amendment](../../../prospective_confirmation_v1_amendment_2.md), [amendment 2 receipt](../../../prospective_confirmation_v1_amendment_2_receipt.json), [retained collector schedule](../../../prospective_confirmation_v1_amendment_1.md).

**Predecessor registered before RP4.** RP2 block 12 is dated 2026-08-19; its JSON retains UTC generation time 2026-08-18T18:18:30.733580+00:00. For development LightGBM B2/B1, session sigma 0.02043, effect +0.00322 and MDE at 60 sessions 0.00962 led to a continuous requirement of 537.3386, displayed as 537 in the document. It was the smallest finite requirement, not the only contrast with a finite size. The warning for a 60–120-session campaign, “is not a test” translated from the original, concerned that RV30 effect and one-sided alpha 0.0025 with target power 0.80; it means neither zero power nor guaranteed null results. This limitation predates RP4, but the calculation establishes neither joint power nor equivalence to the linear RV15 look at 335. [Historical protocol](../../../../rp2/block12_prospective_protocol_v1.md) · [Saved design](../../../../../artifacts/rp2_block12_prospective/design.json) · [Documentary addendum without editing the previous seal](../../../prospective_confirmation_v1_amendment_3_context_1.md).

**Long-term programme.** RP3 documents a seal dated 2026-08-24, required N = 662, a zero prior-read counter and estimated date 2029-01-30; this review neither verifies a live counter nor accesses its bank. Its frozen tree index and RV30 target differ from RP4's linear RV15 sequence. The guide documents planned window overlap with Phase 8 without verifying actual bank inclusion here; decision 128 withdraws Phase 9 as RP4's sealed cohort and leaves C10 inactive while retaining RP3. [Guide and dependence](../../../../rp3/EXECUTION_GUIDE.md) · [Protocol](../../../../rp3/PREREGISTRATION.md) · [Decisions](../../../../methodology_decisions.md).

## 23. What can prospective ablation answer that historical coefficients cannot?

It will compare full B2 with B2 minus the four registered gamma-imbalance columns and their presence indicators: 138 versus 134 raw predictors. The three historical gamma-exposure columns remain. Both use the same keys, masks and rules; the reduced model is fit and selected on its own causal training. This tests the block's joint predictive contribution within linear RV15, not merely coefficient magnitude.

A is that ablation with a one-sided p-value; B is the median paired tree RV15 delta with a bilateral p-value; C is the mean of those deltas trimmed by 5 % in each tail, also with a bilateral p-value. A/B/C are calculated on the first 20 prospective sessions and decisions require a positive sign and Holm across the three at 5 %. For C, floor(0.05 × 20) = 1: one observation is removed from each tail and the remaining 18 averaged, applying the same recipe inside every resample. The two series are not trimmed separately and shock dates are not selected. Amendment 2 supersedes amendment 1's two-test Holm without changing its nominal A/B recipes.

D answers another question: whether the 25 final historical sessions plus 20 prospective sessions jointly support the hierarchy in linear RV15. Each of the 45 sessions receives weight 1/45, rather than giving each window half the weight. It has its own secondary one-sided H1→H2 sequence at 5 %, separate from Holm A/B/C; if H1 fails, H2 remains nominal only. Frozen historical losses are reused literally, without new historical fits or changes to their original p-values. The 25 already-observed sessions motivated part of this analysis, so it cannot be called independent confirmation.

All secondaries are read once alongside the first 20 and are not repeated at 40 or 335. They do not change the primary, and no global control over their union is claimed. Favorable ablation would not establish actual inventory or causal hedging: the block includes a trade count as well as imbalance measures; a favorable median or trimmed mean also does not eliminate tail risk.

Amendment 3 keeps these recipes intact and relabels early looks as consistency checks; it adds only the final cumulative primary-sequence look at 335 prospective sessions. The hypothetical power row for 45 new sessions does not describe D, whose historical portion is already observed. No verified power exists for ablation or Holm B/C decisions. [Registered scope and power](../../../prospective_confirmation_v1_amendment_3.md).

Sources: [original A/B comparators and training](../../../prospective_confirmation_v1_amendment_1.md), [current A/B/C rules, D pooling and seal chain](../../../prospective_confirmation_v1_amendment_2.md), [secondary receipt](../../../prospective_confirmation_v1_amendment_2_receipt.json), [historical-coefficient limits](../../../../../artifacts/rp4_closeout_audit/REPORT.md).

## 24. What if sessions are missing or the collector reports success with insufficient coverage?

Replication takes the first complete eligible sessions chronologically. Download success is insufficient: components, hashes, keys, calendar minutes and v4 eligibility must be checked before looking at losses or signs. Missingness is recorded with objective reasons; gaps are neither filled nor days selected by performance. A reduced model does not receive a more permissive mask than the full model.

The task does not wake the computer and may run when it becomes available again; the collector retrieves the most recently closed session and does not promise automatic recovery from a prolonged interruption. This is an accumulation/calendar risk, not grounds to redefine a complete session. Without the first 20 complete sessions, the primary look and its secondaries remain closed.

If A, B or C is uncomputable, it retains its status and position in the three-test Holm family with administrative value 1; the family is not reduced and that value is not presented as a scientific estimate. If the 45-session union or D inference fails, it is reported unverifiable without excluding dates, repeating the look or changing the criterion. Secondaries are neither rescued nor repeated at 40 or 335.

The first time 335 eligible prospective sessions are complete, the final cumulative look in amendment 3 opens, not on a results-selected date. January 2028 is approximate scheduling, not permission to substitute sessions. Interim monitoring checks acquisition, integrity and eligibility only, without inspecting losses, effects or p-values; 120 and 146 are planning scenarios without a look. [Final-look restrictions](../../../prospective_confirmation_v1_amendment_3.md).

Sources: [completeness and missingness criteria](../../../prospective_confirmation_v1.md), [collector limitations](../../../prospective_confirmation_v1_amendment_1.md), [current A/B/C handling and D failures](../../../prospective_confirmation_v1_amendment_2.md).

## 25. What can an examiner verify without licensed data?

The examiner can compare each claim with aggregate statistics, check signs and denominators between versions, review formulas and follow artifact hashes. Documentary verification checks numerical and byte agreement; alone it proves neither complete provenance of every datum, historical client receipt nor correct strategy execution.

Recalculation from licensed originals requires those inputs, the environment and receipts; it is distinct from checking the package. Complete reproduction from scratch is not claimed during this preparation. Documentary corrections are added without replacing frozen results, and reserved cohorts remain outside scope. Prospective evidence remains pending until its registered look.

The public projection excludes private administrative operator-instruction and support-tracking records. The front page identifies this correction as the current documentary version and retains earlier versions as history; the [manifest](evidence_manifest.json), [receipt](receipt.json) and [SHA256SUMS](SHA256SUMS) document sources and sealing. This is verifiable local custody, not a third-party timestamp or additional empirical validation.

Sources: [verification and reproduction operations](../../../OPERATING_GUIDE.md), [v4 report manifest](../../../../../artifacts/rp4_v4_b4/report_manifest.json), [descriptive-audit scope](../../../../../artifacts/rp4_closeout_audit/findings.json), [prospective custody](../../../prospective_confirmation_v1.md), [secondary amendment](../../../prospective_confirmation_v1_amendment_2.md).

## 26. Multiplicity between versions: what survives the old bilateral/Holm rule?

This sensitivity uses **saved bilateral p-values** and bilateral Holm across four contrasts within each horizon of the primary window. RV5 remains secondary. The table supersedes earlier approximations as the answer under the old rule; previous documents remain sealed. A one-sided p-value is not automatically doubled: the centered distribution's tails can be asymmetric.

| Horizon | Family / contrast | Registered one-sided p | Saved bilateral p | Bilateral Holm across four contrasts | Individual rejection |
| --- | --- | ---: | ---: | ---: | --- |
| RV15 | Linear B1/B0 | 0.0390 | 0.0459 | 0.0918 | No |
| RV15 | Linear B2/B1 | 0.0032 | 0.0062 | 0.0248 | Yes |
| RV15 | Trees B1/B0 | 0.0135 | 0.0149 | 0.0447 | Yes |
| RV15 | Trees B2/B1 | 0.6280 | 0.8048 | 0.8048 | No |
| RV30 | Linear B1/B0 | 0.0439 | 0.0467 | 0.1401 | No |
| RV30 | Linear B2/B1 | 0.0525 | 0.1013 | 0.2026 | No |
| RV30 | Trees B1/B0 | 0.0053 | 0.0066 | 0.0264 | Yes |
| RV30 | Trees B2/B1 | 0.6631 | 0.7249 | 0.7249 | No |
| RV5 | Linear B1/B0 | 0.0092 | 0.0099 | 0.0396 | Yes |
| RV5 | Linear B2/B1 | 0.0172 | 0.0343 | 0.1029 | No |
| RV5 | Trees B1/B0 | 0.0608 | 0.0731 | 0.1462 | No |
| RV5 | Trees B2/B1 | 0.1927 (nominal) | 0.4014 | 0.4014 | No |

Under the v1/v2 bilateral/Holm sensitivity, flow survives only in linear RV15, and state survives for trees at RV30 and RV15 and for linear RV5. The complete linear RV15 sequence would not open if H1 after Holm were additionally required, because that H1 does not reject. V1/v2 did not use H1→H2: the preceding sentence is a conditional interpretation, not a retrospective attribution of that sequence to those versions. A tree H1 rejection does not open linear H2.

The tree RV5 H2 one-sided p is **nominal**, with empty `p_for_decision`, `hypothesis_status=NOT_TESTED` and `nominal_p_role=NO_PROMOTABLE`; inclusion in this sensitivity does not reopen the registered test. Each cell retains its exact CSV column and index in the matrix. Holm covers four contrasts per horizon, not one global family encompassing horizons, versions and adaptive decisions. This later reading neither makes reused samples independent nor changes original decisions.

Sources: [saved p-values](../../../../../artifacts/rp4_v4_b4/primary_statistics.csv), [exact rows and scope](../../../../archive/rp4/DEFENSE_PACKAGE/revision_2/correction_5/holm_evidence.json), [original v1 rule](../../../specification_v1.md), [v2 rule](../../../specification_v2.md), [v3 sequence](../../../specification_v3.md) and [v4 closure](../../../specification_v4.md).

RESEARCH_ONLY · NOT INVESTMENT ADVICE · capital_go=false.

## 27. Do earlier programmes converge, or are the same results being counted repeatedly?

There is **convergence, not identical replication**: option state gives recurring positive signals with family/window exceptions; these are neither four independent replications nor four uniformly positive designs. The Gamma +0.008171 and PIT result belong to the **same evaluation**, not two confirmations. RP2 is a superseded predecessor whose validation is not positive in every family. The table retains these limits and distinguishes the historical programme from its successor.

| Programme and historical disposition | Estimand, loss and window | Family | STATE: B1 over B0 | FLOW: B2 over B1 | Artifact |
|---|---|---|---|---|---|
| RP2, superseded history; no current claim | Mean QLIKE delta, RV30; D/V roles, 156/32 evaluated sessions | Log ridge, Gamma GLM and LightGBM | Positive in all three families in D; mixed signs and intervals crossing zero in V; Gamma D +0.002564 and V −0.001496 | All six D/V intervals cross zero; no confirmed positive increment | [Historical verdict](../../../../rp2_v3/VERDICT.md), [inference](../../../../../artifacts/rp2_v3/rp2-v3-20260831-b1-spot-cutoff-remediation/rp2_block10_inference/inference.json), [supersessions](../../../../rp2_v3/SUPERSEDED_RESULTS.md) |
| PIT v2.2 successor, `GLOBAL_EDGE_NOT_CONFIRMED` | Mean QLIKE delta, RV30; 32-session holdout, read 2026-09-02 | Confirmatory Gamma GLM; robustness LightGBM | Gamma B1a +0.008171, CI [0.002658; 0.014024], Holm 0.0084; baseline QLIKE 0.2129; effect below MDE 0.008416 | Gamma −0.003127, CI [−0.013923; 0.008609], Holm 0.5595; not confirmed for trees either | [Result and limits](../../../../pit_v22_claims_and_limitations_v2.md), [aggregate](../../../../../artifacts/target_blind_v22/successor_evaluation_result_v2.json) |
| Phase 8A, `MIXED_EXPLORATORY`; opened 2026-08-30 | Primary total delta; state/flow disaggregated, QLIKE RV30; 20 primary sessions, 2026-08-03–2026-08-28; sensitivity 30, 2026-07-20–2026-08-28 | D/V training roles × Gamma GLM/LightGBM | Four of four primary cells positive; descriptive Holm < 0.05 in three | Four of four primary intervals cross zero | [Addendum](../../../../../reports/phase8a_exploratory_bridge_addendum_v13.md), [protocol](../../../../phase8_bridge_protocol_v2.md), [aggregate](../../../../../artifacts/phase8_bridge/materialized_remediation_20260831_v1.json) |
| RP4 v3/v4, historical development closure; final window unconfirmed | Mean QLIKE delta; v3 RV30, v4 primary RV15/secondary RV5; 419 primary and 25 final sessions | Linear and LightGBM | Both families: at 30 minutes +1.729 %/+2.091 %; at 15 +0.880 %/+1.170 %, linear/trees respectively | Linear: +0.623 % at 15 and +0.256 % at 5 under H1→H2; at 30 no rejection; tree mean unconfirmed and positive median at 15/5 | [Version table](../../../RESULTADO_FINAL_revision_2.md), [contrasts](../../../results_v4.md), [aggregates](../../../../../artifacts/rp4_closeout_figures/comparison_v1_v4.csv) |

All these forecast contrasts use QLIKE; there is no evidence here of convergence across different losses. Information sets, principal targets, horizons, masks, training and windows do differ. In Phase 8 the primary estimand is total information over B0; state and flow contrasts are disaggregations and Holm is descriptive. Its four cells cross two training roles and two families on the same sessions. Positive state results do not extend throughout the thirty-session sensitivity: D-trained Gamma is negative there. Flow also has positive point estimates outside RP4; linear RP4 at fifteen and five minutes detects the mean-improvement sequence under its rule, rather than the exclusive emergence of any favorable sign.

RP2 and PIT windows are identified by role and evaluated sessions; the consulted aggregates do not fix calendar endpoints, and dates are not invented.

**What Gamma variants mean.** In the same PIT successor, B1b adds +0.02234 and B1c +0.02997. These are information-set robustness variants with different masks, not other programmes or primary confirmations: B1a uses 12,640 origins and baseline QLIKE 0.212916; B1b uses 12,545 and 0.214005; B1c uses 12,543 and 0.213756. Denominators are not shared and these deltas are not converted into new percentages. [Saved variants and masks](../../../../../artifacts/target_blind_v22/successor_evaluation_result_v2.json).

**Dependence and prior reading.** The full bridge window, 2026-07-20–2026-08-28, contains Phase 8's twenty primary sessions, 2026-08-03–2026-08-28. They coincide with 20 of RP4's 25 final sessions, or 80 % according to the saved count; no new sessions were counted and no sealed-bank data read. The [bridge protocol](../../../../phase8_bridge_protocol_v2.md) fixes dates and the [earlier count](../../../../archive/rp4/DEFENSE_PACKAGE/revision_2/correction_2/examiner_evidence.json) retains matches. This discloses actual dependence; it does not permit combining p-values or adding sample sizes as if independent.

**New documentary clarification.** The addendum attributes 11,700 origins to its primary QLIKE table; those values correspond to `primary_20` rows with 7,800 common keys in the aggregate. The 11,700 belong to the global grid and thirty-session sensitivity. The frozen addendum is retained and correct scope noted here: no QLIKE value or contrast changes. “One of eight cells improves after repair” is also distinct from “four state deltas are positive”: the first compares instrument versions; the second compares information sets within the corrected version. [Original comparison rows](../../../../../artifacts/phase8_bridge/materialized_remediation_20260831_v1.json).

**Provenance and dispositions.** The [README history](../../../../../README.md) retains RP2 as model/sample dependent, PIT without confirmed global edge, Phase 8 as mixed/exploratory, and RP4 with its corrections and closure; no disposition is promoted. Its traceability section labels RP2 `HISTORICAL_MEASUREMENT_NOT_CURRENT_CLAIM`, superseded by the PIT successor. Aggregates, selectors and documentary quotations are in the [convergence evidence](../../../../archive/rp4/DEFENSE_PACKAGE/revision_2/correction_3/convergence_evidence.json), and every figure has a source and hash in the [matrix](claims_matrix.csv).

RP3 is a long-term confirmatory programme with another contrast: a frozen flow index over B1 in trees, RV30, and a directional secondary conditional on the primary. Its protocol documents a seal dated 2026-08-24, required N = 662 and estimated reading date 2029-01-30; it does not claim that this size has already been acquired. The zero prior-read counter is documented: this review neither verifies a live counter nor opens the cohort. The [execution guide](../../../../rp3/EXECUTION_GUIDE.md) documents planned window overlap with Phase 8 and an acquisition barrier until the bridge's authorized reading; that shared eligibility prevents assuming independence, and actual bank inclusion was not verified. Decision 128 withdraws Phase 9 as RP4's sealed cohort, retains historical objects and does not activate C10; it neither cancels RP3 nor makes its test an identical RP4 replication. [Pre-registration](../../../../rp3/PREREGISTRATION.md) · [Decisions 93 and 128](../../../../methodology_decisions.md).

## 28. What remains of the failed secondaries, and what does “repaired” mean?

The jump-classification endpoint has computable final AUC in both windows and families. No H1 rejects; every H2 retains `NOT_TESTED`, and its nominal p-value cannot decide the test. Repairing convergence permits reporting the registered contrast, but it neither converts adverse results into favorable evidence nor establishes absence of information.

The attempt sequence is retained: the first repair pass left one linear component uncertified; Newton subsequently resolved only that failed component while reusing completed ones. The repaired attempt changed its numerical procedure, not the objective function, temporal selection, registered sample or threshold. The stricter repair certificate is not retroactively attributed to every original fit.

For Mincer–Zarnowitz, calibration diagnostics for original forecasts, available in both families, must be separated from applied affine recalibration, which concerns LightGBM only. Saved receipts reproduce the origin formula and aggregates within numerical precision. Negative affine outputs, clipped to the registered positive floor, generate very large QLIKE losses; arithmetic identity does not establish useful recalibration. The usefulness closeout remains `NO VERIFICABLE` (unverifiable), with explicit numerical and statistical causes, without implying the arithmetic cannot be reproduced.

Among the AUC and MZ endpoints examined here, no final aggregate is identified as still irreproducible in the saved receipts. This review compares saved aggregates and provenance; it neither reruns models nor rereads individual predictions. Revised results and the final result already included these secondaries; the new edition adds a bounded public projection and explanation while retaining failed attempts and previous tables.

**Evidence.** [Repaired v3 secondaries](../../../results_v3_revision3.md) · [Verifiable projection](../../../../../artifacts/rp4_v3_secondary_repair/evidence.json) · [Previous revision](../../../results_v3_revision2.md) · [Retained final result](../../../RESULTADO_FINAL_revision_2.md).
