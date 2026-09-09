# Prospective research priorities

**Status: PROSPECTIVE - NOT YET EVALUATED.** These proposals identify future
questions and the evidence needed to resolve them. They authorize no evaluation,
collection, spending or change to an existing registration. The
[registered prospective protocol](prospective_confirmation_v1.md) and its
[current amendment](prospective_confirmation_v1_amendment_3.md) retain their
decision rules, sample restrictions and reading schedule. A proposed extension
requires a separate specification before its evaluation data are observed.

The [current evidence](../CURRENT.md) supports a conditional historical forecast
result. It establishes neither independent prospective confirmation, a causal
mechanism nor economic value. No experiment is reported in this document.

## Dependence sensitivity

Before inspecting future outcomes, specify alternative bootstrap block lengths,
a stationary bootstrap only if justified, and HAC bandwidth sensitivities. Define
the estimand, resampling unit, joint treatment of assets, dependence assumptions,
primary method and reporting or multiplicity rule in advance. Report the full
registered set, including adverse results; selecting the smallest p-value after
evaluation would invalidate the intended sensitivity analysis.

The existing five-session circular bootstrap remains the registered analysis.
Alternative methods would examine whether a conclusion depends materially on
that dependence approximation, not replace an unfavorable registered verdict.
The short early looks and the assumptions behind approximate power require
explicit treatment. [Current inference](specification_v4.md) and
[power and look restrictions](prospective_confirmation_v1_amendment_3.md).

## B2 block ablation

A separately registered decomposition could compare activity/intensity,
premium/composition, aggressor/direction, gamma/exposure and tenor/0DTE blocks.
Freeze the feature-to-block map, treatment of shared fields and presence
indicators, comparators, sample eligibility, target, model selection and multiple
comparison rule before evaluation. Fit each reduced model using its own eligible
training history while keeping evaluation keys and masks comparable.

The decisive question is which block adds out-of-sample predictive information
beyond the specified comparator. Ridge coefficient magnitudes do not answer that
question and cannot establish causal or economic importance. Correlated blocks
can share information, so a removal contrast need not identify a unique source.
This broader proposal does not amend or repeat the already registered gamma-block
ablation or its single secondary look. [Existing ablation](prospective_confirmation_v1_amendment_1.md),
[secondary decision rules](prospective_confirmation_v1_amendment_2.md) and
[historical coefficient limits](../rp4/DEFENSE_PACKAGE/revision_2/correction_7/examiner_qa.md).

## Receipt-time telemetry

Future infrastructure could record `request_start_time`, the provider/source
timestamp, `client_receive_time`, persistence time and forecast eligibility time.
Specify UTC representation, clock synchronization and measured uncertainty,
timestamp semantics, request/response identity, retries and persistence failures.
An eligibility decision must be traceable to information actually received and
available before that decision; a provider event timestamp alone is insufficient.

The current 120-second rule remains a **source-time availability proxy**, with
**no historical receipt proof**. Future telemetry cannot reconstruct missing
historical arrival evidence or retroactively strengthen that claim. Its useful
test is whether prospective forecasts can be audited against observed arrival and
persistence records, with violations and uncertain clocks retained.
[Timing boundary](../provider_timing_pit_contract_v22.md) and
[current data scope](data_and_execution_v1.md).

## A genuinely new universe

A future generalization test should select genuinely new assets before reading
their evaluation outcomes, with different sectors, liquidity levels and volatility
characteristics. Non-megacap names and ETF comparisons may be suitable when their
roles are methodologically justified. Register eligibility, data access,
survivorship handling, weighting, dependence treatment and the decision rule;
coverage or results must not determine favorable replacements after evaluation.

AAPL, AMZN, META, MSFT, NVDA and TSLA are correlated assets. Six favorable signs
are not six independent replications. The historical SPY/QQQ extension also does
not constitute independent prospective replication. The new study should assess
transportability with uncertainty that respects shared dates and market exposure.
[Current universe](specification_v4.md) and
[historical eight-asset extension](results_universe_v1.md).

## Economic value as a separate study

A trading-value study needs its own protocol, frozen decision rule, entry and exit
conditions, eligible instruments and executable bid/ask assumptions. Specify
transaction costs, spread, slippage, financing where applicable, latency, turnover,
liquidity and capacity assumptions before evaluation. Define position sizing,
exposure constraints and treatment of failed or partial executions as part of the
policy rather than inferring them from forecast accuracy.

Report PnL, drawdown and Sharpe or an appropriate risk-adjusted measure, together
with uncertainty, tail behavior and sensitivity to realistic implementation
assumptions. An untouched evaluation and a declared benchmark must distinguish
policy development from its final assessment. A favorable QLIKE change cannot be
retrospectively converted into alpha or a profitable strategy claim.
[Current economic boundary](../CURRENT.md) and
[threats to validity](../threats_to_validity_matrix_v1.md).

## Value, cost and decisive evidence

These are qualitative planning assessments, not measured budgets or promised
outcomes. Each study remains contingent on its own specification and authorization.

| Proposal | Potential value | Main cost or constraint | Decisive evidence |
| --- | --- | --- | --- |
| Dependence sensitivity | Establish whether inference relies on one dependence approximation. | Valid finite-sample methods and prospective multiplicity planning. | Complete preregistered sensitivity results with no favorable-method selection. |
| B2 block ablation | Localize predictive contribution within the implemented representation. | Additional training and correlated-block interpretation. | Registered removal contrasts on common eligible future observations. |
| Receipt telemetry | Replace an assumed arrival boundary with observable future custody. | Clock quality, storage and reliable request/response linkage. | Auditable receipt-to-eligibility ordering, including uncertainty and failures. |
| New universe | Test transportability beyond correlated large technology stocks. | Licensed coverage, heterogeneity and dependence-aware evaluation. | Fixed-rule results on genuinely new assets and observations. |
| Economic study | Determine whether forecasts support an implementable policy. | Execution data, realistic costs and a separate evaluation budget. | Untouched net performance under declared execution and risk assumptions. |

Research only. Not investment advice.
