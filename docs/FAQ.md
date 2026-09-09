# Research questions and answers

**Status: CURRENT.** This guide explains saved evidence; it reports no new experiment.
OOS fitting ≠ prospective scientific design. Predictive information ≠ causality.
Predictive information ≠ tradability. Statistical significance ≠ economic significance.
[Current evidence](CURRENT.md) and the [historical examiner account](rp4/DEFENSE_PACKAGE/revision_2/correction_7/examiner_qa.md)
provide the broader context.

## 1. Why RV15 instead of the original RV30?

RV30 remains the original question. Its linear flow increment did not reject at
5% (p = 0.0525). RV15 primary and RV5 secondary were a declared horizon extension
after reading RV30, motivated by a hypothesis of short-lived flow information.
Registration before the v4 evaluation preserves that sequence, but does not erase
earlier adaptation or demonstrate the proposed mechanism.
[V4 specification](rp4/specification_v4.md) and [proposal alignment](rp4/DEFENSE_PACKAGE/revision_2/correction_7/examiner_qa.md).

## 2. Why is p = 0.0032 not a clean prospective confirmatory p-value?

It is the registered one-sided linear RV15 H2 result in the historical development
sample, after H1 rejects at p = 0.0390. The horizon and closure rule followed earlier
analyses of reused data. The family-specific H1-to-H2 sequence does not provide a
global 5% error rate across families, versions and historical search. The number
supports its stated historical comparison, not an untouched prospective test.
[Saved primary statistics](../artifacts/rp4_v4_b4/primary_statistics.csv) and [version and multiplicity account](rp4/DEFENSE_PACKAGE/revision_2/correction_7/examiner_qa.md).

## 3. Why are 160,832 origins not independent observations?

Forecasts share dates, assets and overlapping target windows. The 160,832 origins
form 2,514 asset-sessions across 419 evaluated sessions and six assets. Inference
uses paired session losses, retaining joint asset composition, rather than treating
each origin as an independent replicate.
[Coverage](../artifacts/rp4_v4_b4/coverage.csv) and [evaluation specification](rp4/specification_v4.md).

## 4. Why five-session bootstrap blocks?

Five sessions is the registered circular-block length, with 9,999 resamples. Blocks
retain short-range temporal dependence that independent resampling would discard.
This is a design choice, not proof that five captures all dependence or is optimal.
Only four such block lengths fit in a 20-session look; saved power approximations
do not validate that small-sample bootstrap's size or power.
[Registered inference](rp4/specification_v4.md) and [prospective power limitations](rp4/prospective_confirmation_v1_amendment_3.md).

## 5. Why does Ridge show B2 improvement but LightGBM does not?

The linear RV15 mean QLIKE improvement is +0.623% (p = 0.0032); the tree increment
is -0.115% (p = 0.6280). Different representations, fitting and sensitivity to
extremes are possible explanations, not identified causes. Saved diagnostics are
consistent with adverse tails affecting the tree mean. A favorable median cannot
replace the primary mean; tree RV15 median p = 0.0435 becomes 0.0870 after Holm.
These results establish neither universal linear superiority nor absence of flow
information in every tree model.
[Primary statistics](../artifacts/rp4_v4_b4/primary_statistics.csv) and [tree diagnostics and median qualification](rp4/DEFENSE_PACKAGE/revision_2/correction_7/examiner_qa.md).

## 6. What exactly does B2 measure?

B2 adds trade-derived activity, composition and imbalance features to B1's option
state and B0's price history. The result concerns that full implemented information
set, not an isolated gamma variable or observed dealer inventory. State and flow
can share source records. The 120-second source-time proxy does not prove historical
client receipt, and the accepted provider gap remains unfilled.
[Variable specification](rp4/specification_v4.md) and [data and execution boundary](rp4/data_and_execution_v1.md).

## 7. Can the coefficients be interpreted causally?

No. Related predictors undergo training-only transformations, scaling and clipping;
coefficient magnitude does not identify a variable's marginal contribution or a
dealer-hedging mechanism. The prospective block ablation can examine incremental
predictive contribution within the registered model. It cannot by itself establish
causal hedging or actual intermediary positions.
[Coefficient audit](../artifacts/rp4_closeout_audit/REPORT.md) and [registered ablation](rp4/prospective_confirmation_v1_amendment_1.md).

## 8. Why were historical failures retained?

They expose the research path, adverse results and demonstrated defects that later
versions address. Deleting them would hide selection and break provenance. Retention
does not restore withdrawn claims: current conclusions follow the findings ledger,
while frozen sources and their maps remain evidence of what was recorded.
[Findings ledger](scientific_findings_ledger.md), [document status map](DOCUMENT_STATUS_MAP.md) and [archive](archive/README.md).

## 9. Why does the final historical window fail to confirm the sequence?

In its 25 sessions, RV15 H1 does not reject for linear models (p = 0.3908) or trees
(p = 0.0568), so H2 is not opened in either family. A favorable linear H2 estimate
cannot bypass that gate. Limited precision and distribution changes are possible
contributors, not demonstrated explanations. The report's historical
"Confirmation comparison" heading does not mean independent prospective
confirmation, and non-rejection does not establish a zero effect.
[Saved window comparisons](rp4/results_v4.md) and [current interpretation](CURRENT.md).

## 10. Why is the prospective test scientifically more important than another historical model?

New eligible sessions test whether the fixed interpretation carries beyond data
that informed its development. The registered linear RV15 sequence has looks at
20, 40 and 335 prospective sessions; the early looks are consistency checks.
Approximate power is 11% for H1 and 15% for H2 at 20, and 55% and 80% at 335.
Eighty percent for H2 is not power for the complete sequence. Each verdict is
retained: later looks cannot rescue earlier failures. Secondaries are read once
at 20 and are not repeated at 40 or 335; the 25-historical-plus-20-new pool is not
independent confirmation. No prospective outcome is reported here.
[Protocol](rp4/prospective_confirmation_v1.md), [secondary rules](rp4/prospective_confirmation_v1_amendment_2.md) and [335-session amendment and assumptions](rp4/prospective_confirmation_v1_amendment_3.md).

## 11. Does the project demonstrate profitable trading?

No. Lower QLIKE measures forecast accuracy, not strategy returns. This evidence
does not establish profitability after spread, slippage, financing, liquidity and
execution constraints, nor a deployable trading policy. Predictive usefulness,
causal interpretation and economic value remain separate claims.
[Current evidence and economic boundary](CURRENT.md) and [threats to validity](threats_to_validity_matrix_v1.md).

## 12. What would falsify the current interpretation?

The claim of prospective generalization would lack support if the registered
sequence fails on eligible new sessions; an adverse estimate would challenge its
direction. A demonstrated timing leak, invalid loss construction or provenance
failure could invalidate the corresponding historical claim. Non-rejection alone
does not prove zero effect, especially at low power. All outcomes retain their
registered interpretation without switching horizon, family, statistic or session
selection to obtain a favorable verdict.
[Registered decision rules](rp4/prospective_confirmation_v1_amendment_3.md), [known defects](known_defects_and_resolutions.md) and [claim-level evidence](scientific_findings_ledger.md).

RESEARCH_ONLY. NOT INVESTMENT ADVICE. capital_go=false.
