# Options Order Flow and Intraday Volatility

**Can options trading activity improve forecasts of how much a stock's price will move?**

Author: Miguel Guerrero · Master of Data Science research project, Sydney Polytechnic Institute, September 2026

## Overview

This study examines six stocks over roughly two years of historical intraday data.<br>
It compares three nested information sets: price history, option state, then order flow.<br>
Two model families are evaluated chronologically, with the rule written before this calculation.<br>
Earlier studies returned null or adverse validation results; the reused history is disclosed below.

**The linear model improves 15-minute forecast loss by 0.623% when option flow is added, but the tree model does not improve and prospective replication remains pending.**

![Four forecast-loss comparisons: option state improves both families; option flow improves the linear family only](docs/figures/public_refresh/result_matrix.svg)

[PNG alternative](docs/figures/public_refresh/result_matrix.png) ·
[Saved statistics](artifacts/rp4_v4_b4/primary_statistics.csv) ·
[Scientific findings and earlier null results](docs/scientific_findings_ledger.md).

## Question and data

The original proposal asked whether options activity adds information about future
intraday realized variance beyond a competitive price-history baseline. Trading
activity and position-sensitive option state might contain different information;
the evaluation separates those contributions with three nested sets:

- **B0 — 29 predictors:** price and volatility history.
- **B1 — 69 predictors:** B0 plus the implied volatility surface and option state.
- **B2 — 138 predictors:** B1 plus options order flow, composition and signed imbalance.

These counts precede family-specific indicators and asset effects.
[Proposal alignment and deviations](docs/rp4/DEFENSE_PACKAGE/revision_2/correction_7/examiner_qa.md).

![Three nested information sets with 29, 69 and 138 predictors](docs/figures/public_refresh/information_sets.svg)

[PNG alternative](docs/figures/public_refresh/information_sets.png).

The six stocks are **AAPL, AMZN, META, MSFT, NVDA and TSLA**. Licensed one-minute
bars and options trades come from FMP, Unusual Whales and Massive. Availability
uses a **120-second source-time proxy**; historical receipt by a trading client
is unproven. The Unusual Whales gap **2025-01-25–2025-02-24** is retained without filling.
[Data access](data/DATA_ACCESS.md) · [Availability limits](docs/pit_v22_claims_and_limitations.md).

## Method in five lines

1. Forecast **15-minute realized variance** as the primary target, with **5 minutes** secondary; the change from 30 minutes is a disclosed design change, not evidence of an optimal horizon.
2. Compare a winsorized linear model with rank filtering (nominal ridge) and a LightGBM tree model across the same nested information sets.
3. Train in expanding chronological windows: **60 warm-up sessions**, the last **10 training sessions** for selection, **60-minute purge/embargo**, and a calendar partition at **2026-08-01**.
4. Measure **QLIKE**, a forecast-loss score: the first test asks whether option state improves B1 over B0; only a successful first test opens the second test, option flow improving B2 over B1.
5. Evaluate **419 sessions** and estimate uncertainty with **9,999** circular bootstrap resamples of **five-session blocks**, using a one-sided 5% sequence within each family.

![From the research question through data, chronological evaluation and prospective replication](docs/figures/public_refresh/proposal_to_replication_readme.workflow.svg)

[PNG alternative](docs/figures/public_refresh/proposal_to_replication_readme.workflow.png) ·
[Full report](docs/rp4/results_v4.md) ·
[Registered design](docs/rp4/specification_v4.md) ·
[Decisions and deviations](docs/research_decisions_current.md).

## Results

The primary results below measure **percentage reduction in QLIKE loss**; a negative
number means worse forecasts. The p-values belong to the declared one-sided sequence.

| Model family | First test: option state, B1/B0 | Second test: option flow, B2/B1 |
| --- | ---: | ---: |
| Linear | +0.880% (p = 0.0390) | +0.623% (p = 0.0032) |
| Trees | +1.170% (p = 0.0135) | −0.115% (p = 0.6280) |

The linear flow difference has a positive **95% interval [0.000335; 0.001932]** in
QLIKE units. Its **bilateral Holm-adjusted p = 0.0248** comes from a separate
comparability analysis; it is not another adjustment to the one-sided sequence.
[Saved statistics](artifacts/rp4_v4_b4/primary_statistics.csv) ·
[Loss comparisons and uncertainty figure](docs/figures/rp4/thesis_summary.svg).

![Accumulated daily forecast-loss difference after adding option flow](docs/figures/rp4/v4_B2_over_B1_cumulative_v2.svg)

[PNG alternative](docs/figures/rp4/v4_B2_over_B1_cumulative_v2.png).

The next figure separates the six stocks. Linear flow ends with a positive
improvement in **six of six assets**; the paths show how gains and reversals
accumulate through the historical period. These are forecast-loss differences,
not trading returns.

![Cumulative option-flow forecast-loss differences for each of the six stocks](docs/figures/public_refresh/cumulative_by_asset_rv15.svg)

[PNG alternative](docs/figures/public_refresh/cumulative_by_asset_rv15.png) ·
[Aggregate figure data and import receipt](artifacts/rp4_readme_figures_v1/import_receipt.json) ·
[Stability checks](artifacts/rp4_v4_b4/robustness.csv).

At the secondary five-minute horizon, linear flow improves **0.256%**, with positive
signs in **three of six assets**. Positive tree medians are also secondary and do not
replace the primary mean test. The complete historical comparison appears below;
the [canonical defense](docs/rp4/DEFENSE_PACKAGE/revision_2/correction_7/README.md)
provides the detailed numerical argument.

## Limits

This is the **fourth evaluation of reused historical windows**: the design was fixed on **2026-09-07**, after the historical sample had been observed, so chronology within each fit does not make the design an unseen-data preregistration.<br>
The **final 25-session window does not confirm the full test sequence**, and prospective replication remains pending.<br>
The **120-second availability proxy** does not establish actual historical client receipt, while the gap in the source data remains unfilled.<br>
A small forecasting improvement establishes neither the dealer-hedging mechanism, economic alpha, profitability nor broader generalization.

[Findings](docs/scientific_findings_ledger.md) ·
[Defects and resolutions](docs/known_defects_and_resolutions.md) ·
[Validity](docs/threats_to_validity_matrix_v1.md).

## Extensions

- [Closed exploratory comparison of five model families](docs/rp4/results_v5.md): the primary selector fails its first test; the secondary ensemble has adjusted p = 0.0498, rising to 0.249 under the declared historical-version bound.
- [Closed eight-asset extension](docs/rp4/results_universe_v1.md): adding SPY/QQQ gives linear state/flow improvements of **1.40% / 0.56%** (p = **0.0208 / 0.0093**); trees fail the first test, so the joint claim across both families fails.

## Reproduce

[![Tier 1 CI](https://github.com/mguerrero896/does-option-flow-predict-volatility/actions/workflows/ci.yml/badge.svg)](https://github.com/mguerrero896/does-option-flow-predict-volatility/actions/workflows/ci.yml)

From a clean clone, install Python 3.12 and `uv`, then install the locked environment:

```sh
uv sync --frozen
git config --local core.hooksPath scripts/hooks
uv run --frozen python scripts/verify_public_projection.py --output-dir ../public-verification
uv run --frozen python scripts/sync_supabase_catalog.py --rp4-v4 --dry-run
```

Public aggregate CSVs support numerical cross-checks, figure regeneration and
artifact-hash verification. Rebuilding feature panels or refitting the study requires
licensed inputs and their recorded hashes. Exact checked commands and boundaries:
[reproduction guide](docs/reproduce.md) ·
[reproducibility contract](docs/reproducibility_contract_v1.md) ·
[numbered reading route](docs/INDEX.md). A public check is not a new scientific evaluation.

## History and prospective replication

The earlier validation study, here called **RP2**, found null or negative comparisons
across the tested families and no usable economic value. An earlier point-in-time
study, the **PIT successor**, did not confirm a global forecasting advantage. An
exploratory 20-session bridge, **Phase 8**, produced mixed findings: it was consumed
once, its audit found **no aggregation change**, and its sensitivity improved only
**one of eight B1-inclusive primary cells**. These outcomes remain distinct from
the small family-specific forecast-loss reduction above.
[Findings and corrections](docs/scientific_findings_ledger.md) ·
[Phase 8 record](reports/phase8a_exploratory_bridge_addendum_v13.md).

The intraday forecasting study presented here, **RP4**, had four historical
specifications, **v1–v4**; **v4** supplies the headline. The first test (option state)
and the second test (option flow) are abbreviated **H1** and **H2** in the full reports.
The first two specifications use bilateral Holm-adjusted p-values; the third and
fourth use the one-sided sequence at 5% per family, with H2 opened only if H1 rejects.
Cross-version search is not adjusted. RV30, RV15 and RV5 mean realized variance
over 30, 15 and 5 minutes, respectively. Cells show percentage QLIKE reduction (p).

| Version / target | Linear B1/B0 | Linear B2/B1 | Trees B1/B0 | Trees B2/B1 | Sessions |
| --- | ---: | ---: | ---: | ---: | ---: |
| v1 · RV30 | +0.290 % (1.0000) | −167,448.32 % (1.0000) | +1.204 % (0.4724) | −0.073 % (1.0000) | 418 |
| v2 · RV30 | +1.715 % (0.1842) | −8.714 % (0.3752) | +2.091 % (0.0264) | −0.063 % (0.8858) | 419 |
| v3 · RV30 | +1.729 % (0.0439) | +0.554 % (0.0525) | +2.091 % (0.0053) | −0.159 % (0.6631) | 419 |
| v4 · RV15, primary | +0.880 % (0.0390) | +0.623 % (0.0032) | +1.170 % (0.0135) | −0.115 % (0.6280) | 419 |
| v4 · RV5, secondary | +0.377 % (0.0092) | +0.256 % (0.0172) | +0.536 % (0.0608) | +0.160 % (not opened; nominal 0.1927) | 419 |

[All 40 comparison cells and source hashes](artifacts/rp4_closeout_figures/comparison_v1_v4.csv).
v1's numerical failure is retained. Coverage and specification changed between
versions; their differences do not isolate one repair's causal effect.

The closed registered model-combination extension, **v5**, compares five RV15
families. Its primary selector fails H1 (**p = 0.3594**), leaving H2 unopened.
The secondary top2 ensemble passes both tests; Holm across the two selector chains
gives **p = 0.0498**. The declared Bonferroni **×5** bound across historical versions
is **0.249** and does not pass; it does not correct all adaptive search. Its disclosed
post hoc averaging analysis also reuses these sessions. Both that extension and
the eight-asset extension motivate further tests and supply no independent confirmation.
[Exploratory extension](docs/rp4/results_v5.md).

The prospective plan distinguishes **20 new sessions**, a **40-session** stability
check, a secondary **45-session combination of 25 historical + 20 new**, and a final
**335-session** extension. The 335-session target is a normal-approximation power plan
for the option-flow test, not guaranteed success or 80% joint H1/H2 power. The earlier
**537-session** RP2 plan concerned a different effect and does not contradict it.
[Reconciliation and sources](docs/scientific_findings_ledger.md).

A separately registered long-run study, **RP3**, retains its gate: **2029-01-30**
is the estimated read date, not a completed read.
[RP3 preregistration](docs/rp3/PREREGISTRATION.md).

![Research programme timeline, including historical findings and prospective gates](docs/figures/public_refresh/programme_timeline.architecture.svg)

[PNG alternative](docs/figures/public_refresh/programme_timeline.architecture.png).

<details>
<summary>Historical bundle identity retained for audit</summary>

The historical RP2 bundle `rp2-v3-20260831-b1-spot-cutoff-remediation` retains scientific
hash `033f2eb6be35e5db06aec2f9e01ef5f3379a8be68b0372087f24e40fa681bea4`.
Its measurements are superseded and are not current claims.
[Superseded measurements](docs/rp2_v3/SUPERSEDED_RESULTS.md) ·
[Machine-readable state](data/CANONICAL_STATE.json) · [Generated state](STATUS.md).

</details>

## How to cite

Miguel Guerrero (2026). *Options Order Flow and Intraday Volatility*.
Master of Data Science research project, Sydney Polytechnic Institute.
Use [CITATION.cff](CITATION.cff) and include the commit used when citing results.

The [documentation index](docs/INDEX.md) holds the detailed reading route.
[Contributing](CONTRIBUTING.md) · [Development guide](docs/DEVELOPER_GUIDE.md) ·
[Computational assistance](docs/AI_ASSISTANCE_STATEMENT.md) ·
[Scripts](scripts/README.md) · [Reports](reports/INDEX.md) ·
[Database](supabase/README.md) ·
[Issues](https://github.com/mguerrero896/does-option-flow-predict-volatility/issues) ·
[License](LICENSE) · [Security](SECURITY.md).

Research only. Not investment advice. Capital deployment is not authorized.
