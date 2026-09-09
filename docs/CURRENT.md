# Current scientific evidence

**Status: CURRENT. Evidence version: RP4 v4; reviewed 2026-09-09.**
Historical evidence: completed. Independent prospective confirmation: pending.
Economic/trading value: not demonstrated. Causality: not established.

## Question and design

Does option-market information improve intraday realized-volatility forecasts, and does trade-derived option flow add predictive information beyond option state?

- **B0:** price and volatility history.
- **B1:** B0 + option state / implied-volatility surface.
- **B2:** B1 + trade-derived option flow, composition and imbalance information.

These are nested information sets, not necessarily independent economic feeds. The valid incremental interpretation is information beyond the implemented B1 representation. The primary target is RV15 (15-minute realized variance); RV5 is secondary. The families are winsorized log-variance ridge regression with rank filtering and LightGBM.

The six stocks are AAPL, AMZN, META, MSFT, NVDA and TSLA. FMP supplies one-minute bars; Unusual Whales supplies options records. Massive was audited but does not feed these results. A 120-second **source-time availability proxy** is not historical receipt proof; the provider gap remains unfilled.

**160,832 forecast origins are not 160,832 independent statistical observations.** They form **2,514 asset-sessions (419 × 6)** across **419 evaluated sessions**. Chronological expanding walk-forward fitting uses 60 warm-up sessions, 10 selection sessions and 60-minute purge/embargo. Primary inference uses session-level paired losses and 9,999 circular bootstrap resamples of five-session blocks, retaining joint asset composition. H1 tests B1/B0; H2 tests B2/B1 only after H1 rejects, at one-sided 5% within each family. [Design](rp4/specification_v4.md) · [Coverage](../artifacts/rp4_v4_b4/coverage.csv).

## Primary historical result

| Model family | B1/B0: QLIKE reduction; p | B2/B1: QLIKE reduction; p |
| --- | ---: | ---: |
| Linear | +0.880%; 0.0390 | +0.623%; 0.0032 |
| LightGBM | +1.170%; 0.0135 | −0.115%; 0.6280 |

**Historical development evidence. This is the fourth evaluation of overlapping historical data. Cross-version research search is not multiplicity-adjusted. Independent prospective confirmation is pending.**

Option state historically improves both families. Incremental flow improves the linear mean but slightly worsens the tree mean. The linear B2/B1 difference is 0.001134 QLIKE units, with 95% interval **[0.000335; 0.001932]**. Percentage reduction is 100 × mean paired session loss difference / mean baseline loss. Positive values favor the richer information set. [Saved statistics](../artifacts/rp4_v4_b4/primary_statistics.csv) · [Full historical report](rp4/results_v4.md).

**Stricter sensitivity:** bilateral Holm p-values are linear **0.0918 / 0.0248**, LightGBM **0.0447 / 0.8048** (H1/H2). Neither model family passes both sequential steps under this stricter bilateral Holm sensitivity. This separate comparison does not replace the registered primary inference.

**Secondary and adverse evidence:** at RV5, linear B2/B1 improves 0.256% (p = 0.0172); tree H1 fails (p = 0.0608), closing H2. The **final historical window** has 25 sessions and 9,750 origins: linear H1 p = **0.3908**, tree H1 p = **0.0568**; both H2 gates are closed. Linear H2's +1.997% and nominal p = 0.1758 are not a formal rejection; 97.54% of its window gain comes from 31 August 2026. **The final historical window did not confirm the complete registered sequence.** Original files retain the historical label “confirmation”; it does not mean independent prospective replication. [Statistics](../artifacts/rp4_v4_b4/primary_statistics.csv) · [Concentration evidence](rp4/DEFENSE_PACKAGE/revision_2/correction_7/examiner_qa.md).

## History and interpretation limits

| Version | Historical contribution |
| --- | --- |
| v1, RV30 | Numerical linear-flow failure retained; 418 sessions and 92,261 origins. |
| v2, RV30 | Coverage, model and numerical repairs; historical evaluation retained. |
| v3, RV30 | State improves both families; linear flow p = 0.0525 misses H2; tree flow does not improve. |
| v4, RV15 | Shorter-horizon hypothesis; favorable historical linear flow result, adverse tree comparison. |

The v4 design was frozen at **2026-09-07T16:37Z (8 September 2026, 02:37 Australia/Sydney)** before v4 fits, but after earlier results and the historical sample were known. [Freeze manifest](../artifacts/rp4_v4_a1/freeze_manifest.json) · [Historical ledger](scientific_findings_ledger.md). The original report's “There is no v5” describes that closeout, not the subsequently registered [five-family exploratory extension](rp4/results_v5.md). That extension and the [eight-asset extension](rp4/results_universe_v1.md) reuse historical data and do not replace the headline.

**OOS fitting ≠ prospective scientific design. Predictive information ≠ causality. Predictive information ≠ tradability. Statistical significance ≠ economic significance.** Correlated stocks are not six independent replications. Historical source timing does not demonstrate execution feasibility. Neither a causal dealer-hedging/informed-trading mechanism, profitable strategy, cost-adjusted alpha, broad-market generalization nor an optimal horizon is established. The ridge/tree discrepancy remains unresolved; additive signal, representation and regularization are hypotheses, not measured mechanisms. [Validity limits](threats_to_validity_matrix_v1.md).

## Next evidence and claim governance

The [registered prospective protocol](rp4/prospective_confirmation_v1.md), with its [final amendment](rp4/prospective_confirmation_v1_amendment_3.md), fixes reads at **20** new sessions, **40** cumulative sessions for stability and **335** cumulative sessions for the final extension. Approximate marginal planning power at 20 is 11% for H1 / 15% for H2; at 335 it is 55% / 80%. These are assumption-dependent sensitivities; 80% for H2 is not 80% for the sequence. A favorable early read would be encouraging; a null cannot authorize redesign or a rescue at 40. Cumulative reads are dependent and do not have a claimed global 5% error rate.

Successful registered evaluation on genuinely future sessions could support replication. Failure, inadequate coverage or instability would narrow the interpretation and remain recorded. Economic value requires a separately authorized study. No further retrospective specification search is authorized by this document.

Before any headline or evidence-status change, verify the authorizing protocol, genuinely new data, open gate, specification changes, additional multiplicity and confirmatory/exploratory status. No script or documentation update can bypass these checks. The [existing canonical state](../data/CANONICAL_STATE.json) is the machine-readable authority; this page is its concise scientific reading surface. [Current decisions](research_decisions_current.md).

The [evidence map](EVIDENCE_MAP.md) connects each claim to saved statistics, producer code, receipts and hashes. The [reproduction guide](reproduce.md) separates public aggregate checks from scientific refits requiring licensed inputs. Research only. Not investment advice.
